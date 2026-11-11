"""Phase 3 electricity reference table: monthly commercial and industrial prices by state.

Source: U.S. Energy Information Administration, Form EIA-861M, Sales and Revenue (monthly),
sheet "Monthly-States", archived under data/raw/eia/ (public domain). Columns used: Year,
Month, State, Data Status, and for COMMERCIAL and INDUSTRIAL the Revenue (thousand dollars)
and Sales (megawatthours).

Price = revenue / sales, in USD per kWh (thousand dollars / MWh = dollars / kWh). EIA's own
"Price" column (cents/kWh) is kept as a check. The US row is the sum of revenue and of sales
over the 50 states and DC, matching gel.models.p3_market_calibration.

States: the proposal's main data-centre states (VA, TX, OR, GA, AZ, OH) and the US.

Output: data/processed/eia_state_prices.parquet and paper/tables/eia_state_prices_latest12.csv
(mean over the latest 12 months by state and sector).

Usage: uv run python -m gel.build.eia_states
"""

from __future__ import annotations

import argparse
import glob
import sys
from datetime import date
from pathlib import Path

import openpyxl
import polars as pl

EIA_GLOB = "data/raw/eia/*/*-eia861m_sales_revenue.xlsx"
SHEET = "Monthly-States"
STATES = ["VA", "TX", "OR", "GA", "AZ", "OH"]
# Column positions in the sheet (0-based), checked against its three header rows.
COLS = {"commercial": (8, 9, 11), "industrial": (12, 13, 15)}  # revenue, sales, price
OUT = Path("data/processed/eia_state_prices.parquet")
OUT_TABLE = Path("paper/tables/eia_state_prices_latest12.csv")


def check_header(rows: list[tuple]) -> None:
    sectors, measures, units = rows[0], rows[1], rows[2]
    for sector, (rev, mwh, price) in COLS.items():
        if str(sectors[rev]).strip().lower() != sector:
            raise ValueError(f"EIA layout changed: column {rev} is {sectors[rev]!r}, not {sector}")
        got = (measures[rev], measures[mwh], measures[price])
        if got != ("Revenue", "Sales", "Price"):
            raise ValueError(f"EIA layout changed for {sector}: {got}")
        if (units[rev], units[mwh], units[price]) != (
            "Thousand Dollars",
            "Megawatthours",
            "Cents/kWh",
        ):
            raise ValueError(f"EIA units changed for {sector}")
    if tuple(units[:4]) != ("Year", "Month", "State", "Data Status"):
        raise ValueError(f"EIA key columns changed: {units[:4]}")


def read_sheet(path: Path) -> pl.DataFrame:
    ws = openpyxl.load_workbook(path, read_only=True)[SHEET]
    rows = list(ws.iter_rows(values_only=True))
    check_header(rows[:3])
    out = []
    for row in rows[3:]:
        if not isinstance(row[0], int | float):
            continue
        for sector, (rev, mwh, price) in COLS.items():
            out.append(
                {
                    "month": date(int(row[0]), int(row[1]), 1),
                    "state": row[2],
                    "data_status": row[3],
                    "sector": sector,
                    "revenue_k_usd": float(row[rev] or 0.0),
                    "sales_mwh": float(row[mwh] or 0.0),
                    "eia_price_cents_kwh": None if row[price] in (None, "") else float(row[price]),
                }
            )
    return pl.DataFrame(out)


def build(raw: pl.DataFrame, source: str) -> pl.DataFrame:
    states = raw.filter(pl.col("state").is_in(STATES))
    us = (
        raw.group_by("month", "sector")
        .agg(
            pl.col("revenue_k_usd").sum(),
            pl.col("sales_mwh").sum(),
            pl.when((pl.col("data_status") == "Preliminary").any())
            .then(pl.lit("Preliminary"))
            .otherwise(pl.lit("Final"))
            .first()
            .alias("data_status"),
        )
        .with_columns(
            pl.lit("US").alias("state"), pl.lit(None, dtype=pl.Float64).alias("eia_price_cents_kwh")
        )
    )
    cols = [
        "month",
        "state",
        "sector",
        "data_status",
        "revenue_k_usd",
        "sales_mwh",
        "eia_price_cents_kwh",
    ]
    df = pl.concat([states.select(cols), us.select(cols)])
    return df.with_columns(
        pl.when(pl.col("sales_mwh") > 0)
        .then(pl.col("revenue_k_usd") / pl.col("sales_mwh"))
        .otherwise(None)
        .alias("usd_kwh"),
        pl.lit(source).alias("source_file"),
    ).sort("state", "sector", "month")


def latest12(df: pl.DataFrame) -> pl.DataFrame:
    last = df["month"].max()
    first = date(last.year - 1, last.month, 1)
    window = df.filter(pl.col("month") > first)
    return (
        window.group_by("state", "sector")
        .agg(
            pl.col("usd_kwh").mean().round(4).alias("mean_usd_kwh"),
            pl.col("month").min().alias("from_month"),
            pl.col("month").max().alias("to_month"),
            pl.len().alias("months"),
        )
        .sort("sector", "state")
    )


def run(path: Path | None = None) -> pl.DataFrame:
    src = path or Path(max(glob.glob(EIA_GLOB)))
    df = build(read_sheet(src), str(src))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(OUT)
    latest12(df).write_csv(OUT_TABLE)
    return df


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the EIA state electricity price table.")
    ap.add_argument("--xlsx", type=Path, default=None)
    args = ap.parse_args(argv)
    df = run(args.xlsx)
    print(f"wrote {OUT} ({df.height} rows, {df['month'].min()} to {df['month'].max()})")
    print(latest12(df))
    return 0


if __name__ == "__main__":
    sys.exit(main())
