"""P1 report tables (handoff section 3.7).

- paper/tables/p1_benchmark_summary.csv: mean and sd over repeats per GPU, mode and concurrency.
- paper/tables/p1_obsolescence_discount.csv: D_g against a frontier GPU at matched concurrency,
  for two comparisons: "like_for_like" (BF16 on both) and "best_available" (each GPU's fastest
  precision mode at that concurrency).

This module uses the price actually paid (the handoff's spec (a)). Spec (b), the median
cross-provider spot price, is the primary specification and is added once the hand-recorded
spot panel exists.

Usage: uv run python -m gel.bench.report [--frontier B200]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import polars as pl

from gel.bench import metrics

WINDOWS = Path("data/interim/bench/bench_windows.parquet")
KEYS = ["gpu_label", "chip_id", "precision_mode", "concurrency"]


def add_price(summary: pl.DataFrame, windows: pl.DataFrame) -> pl.DataFrame:
    """Attach each GPU's paid price (one run per GPU) to the summary table."""
    price = windows.group_by("gpu_label").agg(pl.col("price_paid_per_hr").first())
    return summary.join(price, on="gpu_label", how="left")


def best_precision(summary: pl.DataFrame) -> pl.DataFrame:
    """Each GPU's fastest precision mode at each concurrency."""
    return (
        summary.sort("output_tok_per_s_mean", descending=True)
        .group_by(["gpu_label", "concurrency"], maintain_order=True)
        .first()
        .with_columns(pl.lit("best_available").alias("comparison"))
        .sort(["gpu_label", "concurrency"])
    )


def _discount(rows: pl.DataFrame, frontier: str, price_col: str) -> pl.DataFrame:
    f = rows.filter(pl.col("gpu_label") == frontier).select(
        "concurrency",
        pl.col("output_tok_per_s_mean").alias("q_f"),
        pl.col(price_col).alias("p_f"),
        pl.col("precision_mode").alias("mode_f"),
    )
    if f.is_empty():
        return pl.DataFrame()
    joined = rows.join(f, on="concurrency", how="inner")
    return joined.with_columns(
        pl.struct(price_col, "p_f", "output_tok_per_s_mean", "q_f")
        .map_elements(
            lambda r: metrics.obsolescence_discount(
                r[price_col], r["p_f"], r["output_tok_per_s_mean"], r["q_f"]
            ),
            return_dtype=pl.Float64,
        )
        .alias("discount"),
        pl.lit(frontier).alias("frontier"),
    )


def obsolescence_discount_table(
    summary: pl.DataFrame, frontier: str, price_col: str = "price_paid_per_hr"
) -> pl.DataFrame:
    """D_g = (P_g/P_f)/(q_g/q_f) - 1 at matched concurrency and matched precision mode."""
    out = []
    for mode in summary["precision_mode"].unique().sort().to_list():
        rows = summary.filter(pl.col("precision_mode") == mode)
        d = _discount(rows, frontier, price_col)
        if not d.is_empty():
            out.append(d.filter(pl.col("mode_f") == pl.col("precision_mode")))
    if not out:
        return pl.DataFrame()
    return pl.concat(out).sort(["precision_mode", "concurrency", "gpu_label"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build P1 report tables.")
    ap.add_argument("--windows", type=Path, default=WINDOWS)
    ap.add_argument("--frontier", default="B200")
    ap.add_argument("--out-dir", type=Path, default=Path("paper/tables"))
    args = ap.parse_args(argv)

    windows = pl.read_parquet(args.windows)
    windows = windows.filter(~pl.col("dry_run"))
    from gel.bench.parse import summarize

    summary = add_price(summarize(windows), windows)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    summary.write_csv(args.out_dir / "p1_benchmark_summary.csv")
    print(f"wrote {args.out_dir / 'p1_benchmark_summary.csv'} ({len(summary)} rows)")

    like = obsolescence_discount_table(
        summary.filter(pl.col("precision_mode") == "bf16"), args.frontier
    )
    best = best_precision(summary)
    best_d = _discount(best, args.frontier, "price_paid_per_hr")
    if like.is_empty():
        print(f"frontier {args.frontier} not benchmarked yet; no discount table written")
        return 0
    cols = [
        "gpu_label",
        "chip_id",
        "concurrency",
        "precision_mode",
        "mode_f",
        "price_paid_per_hr",
        "p_f",
        "output_tok_per_s_mean",
        "q_f",
        "discount",
        "frontier",
    ]
    table = pl.concat(
        [
            like.with_columns(pl.lit("like_for_like").alias("comparison")).select(
                cols + ["comparison"]
            ),
            best_d.with_columns(pl.lit("best_available").alias("comparison")).select(
                cols + ["comparison"]
            ),
        ]
    )
    table.write_csv(args.out_dir / "p1_obsolescence_discount.csv")
    print(f"wrote {args.out_dir / 'p1_obsolescence_discount.csv'} ({len(table)} rows)")
    median_table = median_price_discounts(summary, args.frontier, MEDIANS)
    if median_table is not None:
        median_table.write_csv(args.out_dir / "p1_obsolescence_discount_median.csv")
        print(
            f"wrote {args.out_dir / 'p1_obsolescence_discount_median.csv'} "
            f"({len(median_table)} rows)"
        )
    return 0


MEDIANS = Path("paper/tables/m4_spot_medians.csv")


def median_price_discounts(summary: pl.DataFrame, frontier: str, path: Path):
    """Handoff spec (b), the primary one: D on the median cross-provider on-demand price
    (Decision 13: neocloud median primary, all-provider median alongside). n_neocloud is kept so
    single-source prices (A40) are visible."""
    if not path.exists():
        return None
    med = (
        pl.read_csv(path)
        .filter(pl.col("billing") == "on_demand")
        .select("chip_id", "median_neocloud", "median_all", "n_neocloud", "n_providers")
    )
    s = summary.join(med, on="chip_id", how="left")
    out = []
    for price_col in ("median_neocloud", "median_all"):
        like = obsolescence_discount_table(
            s.filter(pl.col("precision_mode") == "bf16"), frontier, price_col
        )
        best = _discount(best_precision(s), frontier, price_col)
        for name, t in (("like_for_like", like), ("best_available", best)):
            if t.is_empty():
                continue
            out.append(
                t.select(
                    "gpu_label",
                    "chip_id",
                    "concurrency",
                    "precision_mode",
                    "n_neocloud",
                    "n_providers",
                    pl.col(price_col).alias("price"),
                    pl.col("p_f").alias("price_f"),
                    "output_tok_per_s_mean",
                    "q_f",
                    "discount",
                    "frontier",
                ).with_columns(
                    pl.lit(name).alias("comparison"), pl.lit(price_col).alias("price_spec")
                )
            )
    return pl.concat(out) if out else None


if __name__ == "__main__":
    sys.exit(main())
