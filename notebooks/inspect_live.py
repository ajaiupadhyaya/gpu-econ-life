"""Exploration only: sanity-check one day of live rows against known facts. Run from the repo root.

uv run python notebooks/inspect_live.py 2026-10-31
"""

import glob
import sys

import polars as pl

day = sys.argv[1]
df = pl.concat([pl.read_parquet(p) for p in glob.glob(f"data/interim/live/*/{day}.parquet")])
pl.Config.set_tbl_rows(70)
pl.Config.set_tbl_width_chars(130)
pl.Config.set_fmt_str_lengths(34)
print(df.height, "rows")
print(df.group_by("provider", "collector", "contract_type").len().sort("provider", "contract_type"))
print(
    df.group_by("provider", "chip", "contract_type", "gpu_count")
    .agg(
        pl.col("price_usd_per_gpu_hour").median().round(3).alias("median"),
        pl.col("price_usd_per_gpu_hour").min().round(3).alias("min"),
        pl.col("price_usd_per_gpu_hour").max().round(3).alias("max"),
        pl.len().alias("rows"),
    )
    .sort("provider", "chip", "contract_type", "gpu_count")
)
key = ["provider", "sku", "chip", "gpu_count", "region", "zone", "contract_type", "term_months"]
dupes = df.group_by(key).len().filter(pl.col("len") > 1)
print("duplicate keys:", dupes.height)
print(dupes.head(8))
