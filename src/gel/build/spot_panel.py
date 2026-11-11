"""M4: cross-provider current price panel (handoff 3.6, Decisions 6 and 13).

Sources, one snapshot (benchmark week, 2026-11-10/11):
- hand-recorded neocloud rows: data/raw/manual/prices_spot_panel.csv (Nebius, Together,
  CoreWeave), each with source URL, date and (where terms allow) a saved page copy
- the daily collector's parsed rows for the target day: AWS and Azure (offer files / Retail
  API), Google Cloud and AWS spot (SkyPilot), Lambda (pricing page)
- the RunPod price actually paid for each benchmarked GPU (our invoice, from run_meta.json)

Each provider contributes one price per chip and billing type (the median across its regions and
SKUs). Hyperscalers are flagged and medians are reported with and without them. Google Cloud's
SkyPilot rows are accelerator-only (Decision 4); they are kept but flagged by price_basis.

Outputs: data/processed/spot_panel.parquet, paper/tables/m4_spot_medians.csv
Usage: uv run python -m gel.build.spot_panel [--day 2026-11-10]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import polars as pl

MANUAL = Path("data/raw/manual/prices_spot_panel.csv")
LIVE = Path("data/interim/live")
BENCH = Path("data/raw/bench")
OUT = Path("data/processed/spot_panel.parquet")
TABLE = Path("paper/tables/m4_spot_medians.csv")
CHIPS = ["a40", "a100_80gb", "h100_sxm", "h200", "l40s", "b200"]
HYPERSCALERS = {"aws", "azure", "google_cloud"}
COLS = [
    "provider",
    "provider_type",
    "chip_id",
    "billing",
    "price_per_gpu_hr",
    "price_basis",
    "observed",
    "source",
]


def one_per_provider(rows: pl.DataFrame) -> pl.DataFrame:
    return rows.group_by("provider", "provider_type", "chip_id", "billing").agg(
        pl.col("price_per_gpu_hr").median()
    )


def medians(panel: pl.DataFrame) -> pl.DataFrame:
    neo = pl.col("provider_type") != "hyperscaler"
    return (
        panel.group_by("chip_id", "billing")
        .agg(
            pl.len().alias("n_providers"),
            pl.col("price_per_gpu_hr").median().alias("median_all"),
            neo.sum().alias("n_neocloud"),
            pl.col("price_per_gpu_hr").filter(neo).median().alias("median_neocloud"),
            pl.col("price_per_gpu_hr").min().alias("min"),
            pl.col("price_per_gpu_hr").max().alias("max"),
            pl.col("provider").sort().str.join(",").alias("providers"),
        )
        .sort("chip_id", "billing")
    )


def manual_rows(path: Path = MANUAL) -> pl.DataFrame:
    m = pl.read_csv(path)
    return m.select(
        "provider",
        "provider_type",
        "chip_id",
        "billing",
        "price_per_gpu_hr",
        pl.lit("instance").alias("price_basis"),
        pl.col("observed_date").alias("observed"),
        pl.col("source_url").alias("source"),
    )


def live_rows(day: str, root: Path = LIVE) -> pl.DataFrame:
    frames = [pl.read_parquet(p) for p in sorted(root.glob(f"*/{day}.parquet"))]
    if not frames:
        raise FileNotFoundError(f"no collector output for {day} under {root}")
    df = pl.concat(frames, how="diagonal_relaxed").filter(
        pl.col("chip").is_in(CHIPS) & pl.col("contract_type").is_in(["on_demand", "spot"])
    )
    return df.select(
        "provider",
        pl.when(pl.col("provider").is_in(list(HYPERSCALERS)))
        .then(pl.lit("hyperscaler"))
        .otherwise(pl.lit("neocloud"))
        .alias("provider_type"),
        pl.col("chip").alias("chip_id"),
        pl.col("contract_type").alias("billing"),
        pl.col("price_usd_per_gpu_hour").alias("price_per_gpu_hr"),
        "price_basis",
        pl.col("retrieved_at").str.slice(0, 10).alias("observed"),
        pl.col("source_url").alias("source"),
    )


def paid_rows(root: Path = BENCH) -> pl.DataFrame:
    rows = []
    for meta_path in sorted(root.glob("*/*/run_meta.json")):
        meta = json.loads(meta_path.read_text())
        if meta.get("dry_run") or meta["chip_id"] not in CHIPS:
            continue
        rows.append(
            {
                "provider": "runpod_paid",
                "provider_type": "neocloud",
                "chip_id": meta["chip_id"],
                "billing": "on_demand",
                "price_per_gpu_hr": float(meta["price_per_hr_usd"]),
                "price_basis": "instance",
                "observed": meta["utc_start"][:10],
                "source": f"price paid at launch ({meta_path.parent.name})",
            }
        )
    return pl.DataFrame(rows)


def build(day: str) -> tuple[pl.DataFrame, pl.DataFrame]:
    raw = pl.concat([manual_rows(), live_rows(day), paid_rows()], how="diagonal_relaxed")
    meta = raw.group_by("provider", "chip_id", "billing").agg(
        pl.col("price_basis").first(), pl.col("observed").max(), pl.col("source").first()
    )
    panel = one_per_provider(raw).join(meta, on=["provider", "chip_id", "billing"])
    return panel.select(COLS).sort("chip_id", "billing", "provider"), medians(panel)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the M4 cross-provider price panel.")
    ap.add_argument("--day", default="2026-11-10")
    args = ap.parse_args(argv)
    panel, med = build(args.day)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.write_parquet(OUT)
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    med.write_csv(TABLE)
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_width_chars(220)
    pl.Config.set_fmt_str_lengths(90)
    print(med.with_columns(pl.col(pl.Float64).round(3)))
    print(f"wrote {OUT} ({len(panel)} rows) and {TABLE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
