"""Phase 4 analysis panel (Decision 22).

Merges the historical rows (Wayback, AWS offer-file history, SkyPilot catalog history) with the
live collector rows into data/processed/panel.parquet, one row per listing-month.

Unit of observation (proposal, "Unit of observation"; owner's choices 2026-11-11): one posted
price for a (provider, SKU, chip, GPUs per instance, interconnect, region, contract type, term)
listing in a month, in USD per GPU-hour. Steps, each counted in docs/cleaning_report.md:

1. Load and drop unusable rows (no chip in scope, missing or non-positive price).
2. Drop exact duplicate rows.
3. Spot prices recorded by zone become one regional price per day: the median across zones
   (owner's choice), with the zone count kept.
4. Each collector's observations of a listing in a month become one row: the median price, with
   the observation count and first/last dates kept (owner's choice: one row per month, keyed to
   the first day of the month).
5. When several collectors record the same listing-month, the row from the most direct source is
   kept (provider's own file or API, then the Wayback page, then SkyPilot's catalog). Agreement
   between the kept and dropped rows is reported.
6. Join the chip table (age in months since Epoch's release date) and the CPI table (2025
   dollars). Listings before a chip's release month and extreme prices are flagged, not dropped.

Usage: uv run python -m gel.build.panel
"""

from __future__ import annotations

import argparse
import glob
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

HISTORY_GLOBS = [
    "data/interim/wayback/listings.parquet",
    "data/interim/aws_history/*.parquet",
    "data/interim/skypilot_history/*/*.parquet",
]
LIVE_GLOB = "data/interim/live/*/*.parquet"
CHIPS = Path("data/processed/chips.parquet")
CPI = Path("data/processed/cpi.parquet")
OUT = Path("data/processed/panel.parquet")
REPORT = Path("docs/cleaning_report.md")
COVERAGE = Path("paper/tables/panel_coverage.csv")

LISTING = [
    "provider",
    "provider_type",
    "sku",
    "chip",
    "gpu_count",
    "interconnect",
    "region",
    "contract_type",
    "term_months",
    "price_basis",
    "price_kind",
]
# Lower is more direct. Provider files and APIs first, archived provider pages next, SkyPilot's
# third-party catalog last.
COLLECTOR_RANK = {
    "aws_history": 0,
    "aws": 0,
    "azure": 0,
    "lambda": 0,
    "wayback": 1,
    "skypilot": 2,
    "skypilot_history": 2,
}
OUTLIER_FACTOR = 4.0  # flag a price above 4x or below 1/4 of its chip-month-contract median


def load_rows() -> tuple[pl.DataFrame, dict[str, int]]:
    hist = [p for g in HISTORY_GLOBS for p in sorted(glob.glob(g))]
    live = sorted(glob.glob(LIVE_GLOB))
    frames = [pl.read_parquet(p).with_columns(pl.lit("history").alias("origin")) for p in hist]
    frames += [pl.read_parquet(p).with_columns(pl.lit("live").alias("origin")) for p in live]
    df = pl.concat(frames, how="diagonal_relaxed")
    counts = {
        "history": df.filter(pl.col("origin") == "history").height,
        "live": df.filter(pl.col("origin") == "live").height,
    }
    return df, counts


def clean(df: pl.DataFrame, chip_ids: list[str], log: list[dict]) -> pl.DataFrame:
    n0 = df.height
    df = df.filter(pl.col("chip").is_in(chip_ids))
    log.append({"step": "chip not in scope", "dropped": n0 - df.height, "rows": df.height})
    n0 = df.height
    df = df.filter(
        pl.col("price_usd_per_gpu_hour").is_not_null() & (pl.col("price_usd_per_gpu_hour") > 0)
    )
    log.append(
        {"step": "missing or non-positive price", "dropped": n0 - df.height, "rows": df.height}
    )
    n0 = df.height
    df = df.unique(maintain_order=True)
    log.append({"step": "exact duplicate rows", "dropped": n0 - df.height, "rows": df.height})
    return df.with_columns(
        pl.col("retrieved_at").str.slice(0, 10).str.to_date().alias("day"),
        pl.col("term_months").fill_null(0),
        pl.col("interconnect").fill_null(""),
        pl.col("region").fill_null(""),
    )


def collapse_zones(df: pl.DataFrame, log: list[dict]) -> pl.DataFrame:
    """One regional spot price per listing, collector and day: the median across zones."""
    zoned = (
        (pl.col("contract_type") == "spot") & pl.col("zone").is_not_null() & (pl.col("zone") != "")
    )
    spot, rest = df.filter(zoned), df.filter(~zoned)
    keys = [*LISTING, "collector", "origin", "day"]
    spot = spot.group_by(keys).agg(
        pl.col("price_usd_per_gpu_hour").median(),
        pl.col("zone").n_unique().alias("n_zones"),
        pl.col("vcpus").first(),
        pl.col("ram_gb").first(),
        pl.col("gpu_memory_gb").first(),
        pl.col("retrieved_at").min(),
    )
    out = pl.concat(
        [
            rest.select(
                *keys,
                "price_usd_per_gpu_hour",
                pl.lit(None, dtype=pl.UInt32).alias("n_zones"),
                "vcpus",
                "ram_gb",
                "gpu_memory_gb",
                "retrieved_at",
            ),
            spot.select(
                *keys,
                "price_usd_per_gpu_hour",
                "n_zones",
                "vcpus",
                "ram_gb",
                "gpu_memory_gb",
                "retrieved_at",
            ),
        ],
        how="diagonal_relaxed",
    )
    log.append(
        {
            "step": "spot zones -> regional median per day",
            "dropped": df.height - out.height,
            "rows": out.height,
        }
    )
    return out


def collapse_months(df: pl.DataFrame, log: list[dict]) -> pl.DataFrame:
    """One row per listing, collector and month: the median of that month's observations."""
    out = (
        df.with_columns(pl.col("day").dt.truncate("1mo").alias("month"))
        .group_by([*LISTING, "collector", "origin", "month"])
        .agg(
            pl.col("price_usd_per_gpu_hour").median(),
            pl.len().alias("n_obs"),
            pl.col("day").min().alias("first_day"),
            pl.col("day").max().alias("last_day"),
            pl.col("n_zones").max(),
            pl.col("vcpus").drop_nulls().first(),
            pl.col("ram_gb").drop_nulls().first(),
            pl.col("gpu_memory_gb").drop_nulls().first(),
        )
    )
    log.append(
        {
            "step": "observations -> one row per listing-month per collector",
            "dropped": df.height - out.height,
            "rows": out.height,
        }
    )
    return out


def form_factor(sku: pl.Expr, interconnect: pl.Expr) -> pl.Expr:
    """'sxm', 'pcie' or '' from the interconnect field or, failing that, the SKU text."""
    text = (interconnect.fill_null("") + " " + sku.fill_null("")).str.to_lowercase()
    return (
        pl.when(text.str.contains("sxm|nvlink|hgx"))
        .then(pl.lit("sxm"))
        .when(text.str.contains("pcie"))
        .then(pl.lit("pcie"))
        .otherwise(pl.lit(""))
    )


# Two collectors' rows describe the same offer when these match. The SKU text is left out because
# collectors name the same offer differently (Lambda: "8x NVIDIA A100|40GB" on its page,
# "gpu_8x_a100" in SkyPilot); the form factor read from the SKU keeps PCIe and SXM apart.
MATCH = [
    "provider",
    "chip",
    "gpu_count",
    "form_factor",
    "region",
    "contract_type",
    "term_months",
    "price_basis",
    "price_kind",
    "month",
]


def pick_collector(df: pl.DataFrame, log: list[dict]) -> tuple[pl.DataFrame, dict]:
    """Keep the most direct collector for each offer-month; report agreement with the others."""
    df = df.with_columns(
        pl.col("collector").replace_strict(COLLECTOR_RANK, default=9).alias("rank"),
        form_factor(pl.col("sku"), pl.col("interconnect")).alias("form_factor"),
    )
    best = df.group_by(MATCH).agg(pl.col("rank").min().alias("best_rank"))
    df = df.join(best, on=MATCH, how="left", nulls_equal=True)
    kept_all = df.filter(pl.col("rank") == pl.col("best_rank"))
    dropped = df.filter(pl.col("rank") != pl.col("best_rank"))
    n_after_drop = kept_all.height
    # Same-rank collectors for one listing-month (e.g. the AWS history file and the live AWS file
    # in the same month) are merged: median of their medians, counts summed.
    keys = [*LISTING, "form_factor", "month"]
    kept = kept_all.group_by(keys).agg(
        pl.col("price_usd_per_gpu_hour").median(),
        pl.col("n_obs").sum(),
        pl.col("first_day").min(),
        pl.col("last_day").max(),
        pl.col("n_zones").max(),
        pl.col("vcpus").drop_nulls().first(),
        pl.col("ram_gb").drop_nulls().first(),
        pl.col("gpu_memory_gb").drop_nulls().first(),
        pl.col("collector").unique().sort().str.join("+").alias("collector"),
        pl.col("origin").unique().sort().str.join("+").alias("origin"),
    )
    kept_med = kept.group_by(MATCH).agg(
        pl.col("price_usd_per_gpu_hour").median().alias("kept_price")
    )
    cmp = dropped.join(kept_med, on=MATCH, how="inner", nulls_equal=True).with_columns(
        (pl.col("price_usd_per_gpu_hour") / pl.col("kept_price")).log().abs().alias("abs_log_gap")
    )
    agreement = {
        "pairs": cmp.height,
        "by_collector": cmp.group_by("collector").len().sort("collector").rows(),
        "median_abs_pct_gap": float(cmp["abs_log_gap"].median() or 0.0) * 100
        if cmp.height
        else math.nan,
        "share_within_5pct": float((cmp["abs_log_gap"] < 0.05).mean()) if cmp.height else math.nan,
    }
    log.append(
        {
            "step": "same offer-month from a less direct collector",
            "dropped": df.height - n_after_drop,
            "rows": n_after_drop,
        }
    )
    log.append(
        {
            "step": "same listing-month from equally direct collectors, merged",
            "dropped": n_after_drop - kept.height,
            "rows": kept.height,
        }
    )
    return kept, agreement


def join_reference(df: pl.DataFrame, chips: pl.DataFrame, cpi: pl.DataFrame) -> pl.DataFrame:
    rel = chips.select(
        pl.col("chip_id").alias("chip"),
        pl.col("release_date").dt.truncate("1mo").alias("release_month"),
        "tensor_fp16_bf16_tflops",
        "memory_gb",
        "memory_bw_tbs",
    )
    df = df.join(rel, on="chip", how="left").with_columns(
        (
            (pl.col("month").dt.year() - pl.col("release_month").dt.year()) * 12
            + (
                pl.col("month").dt.month().cast(pl.Int32)
                - pl.col("release_month").dt.month().cast(pl.Int32)
            )
        ).alias("age_months")
    )
    df = df.join(cpi.select("month", "to_2025_usd", "cpi_imputed"), on="month", how="left")
    df = df.with_columns(
        (pl.col("price_usd_per_gpu_hour") * pl.col("to_2025_usd")).alias(
            "price_usd_per_gpu_hour_real2025"
        ),
        (pl.col("age_months") < 0).alias("pre_release"),
    )
    med = df.group_by("chip", "month", "contract_type").agg(
        pl.col("price_usd_per_gpu_hour").median().alias("_cell_median")
    )
    df = df.join(med, on=["chip", "month", "contract_type"], how="left").with_columns(
        (
            (pl.col("price_usd_per_gpu_hour") > OUTLIER_FACTOR * pl.col("_cell_median"))
            | (pl.col("price_usd_per_gpu_hour") < pl.col("_cell_median") / OUTLIER_FACTOR)
        ).alias("price_outlier")
    )
    return df.drop("_cell_median", "to_2025_usd").sort("chip", "provider", "month", "sku")


def coverage(df: pl.DataFrame) -> pl.DataFrame:
    return (
        df.group_by("chip", "provider")
        .agg(
            pl.len().alias("listing_months"),
            pl.col("month").n_unique().alias("months"),
            pl.col("month").min().alias("first_month"),
            pl.col("month").max().alias("last_month"),
        )
        .sort("chip", "provider")
    )


def _md(table: pl.DataFrame) -> str:
    head = "| " + " | ".join(table.columns) + " |"
    sep = "| " + " | ".join("---" for _ in table.columns) + " |"
    rows = [
        "| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in table.iter_rows()
    ]
    return "\n".join([head, sep, *rows])


def render_report(counts: dict, log: list[dict], agreement: dict, panel: pl.DataFrame) -> str:
    steps = pl.DataFrame(log)
    flags = pl.DataFrame(
        {
            "flag or gap": [
                "age unknown (chip has no release date)",
                "listed before the chip's release month (pre_release)",
                "price outlier (over 4x or under 1/4 of chip-month-contract median)",
                "no CPI for the month (real price missing)",
                "CPI month imputed (October 2025, BLS shutdown gap)",
            ],
            "listing-months": [
                panel.filter(pl.col("age_months").is_null()).height,
                panel.filter(pl.col("pre_release").fill_null(False)).height,
                panel.filter(pl.col("price_outlier").fill_null(False)).height,
                panel.filter(pl.col("price_usd_per_gpu_hour_real2025").is_null()).height,
                panel.filter(pl.col("cpi_imputed").fill_null(False)).height,
            ],
        }
    )
    by_contract = panel.group_by("contract_type").len("listing_months").sort("contract_type")
    by_type = panel.group_by("provider_type").len("listing_months").sort("provider_type")
    unknown_age = sorted(panel.filter(pl.col("age_months").is_null())["chip"].unique().to_list())
    gap = agreement["median_abs_pct_gap"]
    within = agreement["share_within_5pct"]
    by_coll = ", ".join(f"{c} {n:,}" for c, n in agreement["by_collector"])
    return "\n".join(
        [
            "# Panel cleaning report",
            "",
            f"Generated by `gel.build.panel` on {datetime.now(UTC):%Y-%m-%d}. Do not edit by hand.",
            "Decision 22 in decisions.md explains each step.",
            "",
            f"Input rows: {counts['history']:,} historical and {counts['live']:,} live, "
            f"{counts['history'] + counts['live']:,} in all.",
            "",
            "## Rows at each step",
            "",
            _md(steps),
            "",
            f"Final panel: {panel.height:,} listing-months, "
            f"{panel['month'].min()} to {panel['month'].max()}.",
            "",
            "## Agreement where two collectors saw the same offer-month",
            "",
            f"{agreement['pairs']:,} rows were dropped for a more direct source ({by_coll}). "
            f"Against the kept price for the same offer-month: median absolute gap {gap:.2f}%; "
            f"{within:.0%} within 5%."
            if agreement["pairs"]
            else "No overlapping rows.",
            "",
            "## Flags (kept in the panel, not dropped)",
            "",
            _md(flags),
            "",
            f"Chips with unknown age: {', '.join(unknown_age) if unknown_age else 'none'}.",
            "",
            "## Listing-months by contract type and provider type",
            "",
            _md(by_contract),
            "",
            _md(by_type),
            "",
            "## Coverage by chip and provider",
            "",
            _md(coverage(panel)),
            "",
        ]
    )


def build() -> tuple[pl.DataFrame, str]:
    chips = pl.read_parquet(CHIPS)
    cpi = pl.read_parquet(CPI)
    log: list[dict] = []
    raw, counts = load_rows()
    log.append({"step": "loaded", "dropped": 0, "rows": raw.height})
    df = clean(raw, chips["chip_id"].to_list(), log)
    df = collapse_zones(df, log)
    df = collapse_months(df, log)
    df, agreement = pick_collector(df, log)
    panel = join_reference(df, chips, cpi)
    return panel, render_report(counts, log, agreement, panel)


def run() -> pl.DataFrame:
    panel, report = build()
    for p in (OUT, REPORT, COVERAGE):
        p.parent.mkdir(parents=True, exist_ok=True)
    panel.write_parquet(OUT)
    REPORT.write_text(report)
    coverage(panel).write_csv(COVERAGE)
    return panel


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Build the Phase 4 analysis panel.").parse_args(argv)
    panel = run()
    print(f"wrote {OUT} ({panel.height:,} listing-months), {REPORT}, {COVERAGE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
