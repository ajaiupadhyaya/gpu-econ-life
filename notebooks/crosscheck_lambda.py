"""Exploration only: do archived Lambda pages agree with SkyPilot where the two overlap?

uv run python notebooks/crosscheck_lambda.py
"""

import glob

import polars as pl

wb = pl.read_parquet("data/interim/wayback/listings.parquet").filter(
    (pl.col("provider") == "lambda") & (pl.col("contract_type") == "on_demand")
)
sky = pl.concat(
    [pl.read_parquet(p) for p in glob.glob("data/interim/skypilot_history/lambda/*.parquet")]
)
key = ["month", "chip", "gpu_count"]


def monthly(frame):
    return (
        frame.with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
        .group_by(key)
        .agg(pl.col("price_usd_per_gpu_hour").sort().alias("prices"))
    )


joined = monthly(wb).join(monthly(sky), on=key, suffix="_sky")
joined = joined.with_columns(
    pl.struct("prices", "prices_sky")
    .map_elements(
        lambda r: any(abs(a - b) < 0.006 for a in r["prices"] for b in r["prices_sky"]),
        return_dtype=pl.Boolean,
    )
    .alias("agree")
)
print(joined.height, "chip-size-months overlap;", joined["agree"].sum(), "agree")
pl.Config.set_tbl_rows(30)
pl.Config.set_tbl_width_chars(100)
print(joined.filter(~pl.col("agree")).sort("month").select(*key, "prices", "prices_sky").head(25))
series = (
    wb.filter(pl.col("gpu_count") == 8)
    .with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
    .group_by("month", "chip")
    .agg(pl.col("price_usd_per_gpu_hour").median().round(3).alias("p"))
    .sort("month")
    .pivot(on="chip", index="month", values="p")
)
print(series.select(sorted(series.columns)).head(70))
