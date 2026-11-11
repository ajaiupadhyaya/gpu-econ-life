"""Phase 3 CPI-U deflator table (Decision 21).

Source: BLS flat file cu.data.1.AllItems, archived by gel.collect.bls_cpi under
data/raw/indices/bls_cpi/. Series (confirmed in the archived cu.series):

- CUUR0000SA0: "All items in U.S. city average, all urban consumers, not seasonally adjusted"
  (1982-84=100). Used for deflating.
- CUSR0000SA0: the seasonally adjusted counterpart, kept for reference.

Real dollars are constant 2025 dollars: real = nominal x CPI_2025 / CPI_t, where CPI_2025 is
the BLS annual average (period M13) of CUUR0000SA0 for 2025.

Gaps: BLS did not publish October 2025 (footnote X, "Data unavailable due to the 2025 lapse in
appropriations"; archived cu.footnote). cpi_u_nsa keeps the gap. cpi_u_nsa_filled fills an
isolated missing month with the geometric mean of its two neighbours and sets cpi_imputed;
the deflator uses the filled series. Longer gaps stay missing.

Output: data/processed/cpi.parquet (month, cpi_u_nsa, cpi_u_sa, cpi_u_nsa_filled,
cpi_imputed, to_2025_usd) and
paper/tables/cpi_base.csv (the base value and its source).

Usage: uv run python -m gel.build.cpi
"""

from __future__ import annotations

import argparse
import glob
import sys
from datetime import date
from pathlib import Path

import polars as pl

RAW_GLOB = "data/raw/indices/bls_cpi/*/*-cu.data.1.AllItems.txt"
NSA, SA = "CUUR0000SA0", "CUSR0000SA0"
BASE_YEAR = 2025
OUT = Path("data/processed/cpi.parquet")
OUT_TABLE = Path("paper/tables/cpi_base.csv")


def read_data(path: Path) -> pl.DataFrame:
    """Parse a BLS time-series data file (tab-separated, padded with spaces)."""
    df = pl.read_csv(path, separator="\t", infer_schema_length=0)
    df = df.rename({c: c.strip() for c in df.columns})
    return df.select(
        pl.col("series_id").str.strip_chars(),
        pl.col("year").str.strip_chars().cast(pl.Int32),
        pl.col("period").str.strip_chars(),
        pl.col("value").str.strip_chars().replace("-", None).cast(pl.Float64),
    )


def monthly(df: pl.DataFrame, series_id: str) -> pl.DataFrame:
    return (
        df.filter(
            (pl.col("series_id") == series_id) & pl.col("period").str.contains(r"^M(0\d|1[0-2])$")
        )
        .with_columns(
            pl.date(pl.col("year"), pl.col("period").str.slice(1).cast(pl.Int32), 1).alias("month")
        )
        .select("month", "value")
        .sort("month")
    )


def annual_average(df: pl.DataFrame, series_id: str, year: int) -> float:
    hit = df.filter(
        (pl.col("series_id") == series_id) & (pl.col("year") == year) & (pl.col("period") == "M13")
    )
    if hit.height != 1:
        raise ValueError(f"no BLS annual average (M13) for {series_id} {year}")
    return float(hit["value"].item())


def fill_isolated_gaps(values: pl.Series) -> tuple[pl.Series, pl.Series]:
    """Fill single missing months with the geometric mean of their neighbours."""
    v = values.to_list()
    filled, imputed = list(v), [False] * len(v)
    for i in range(1, len(v) - 1):
        if v[i] is None and v[i - 1] is not None and v[i + 1] is not None:
            filled[i] = (v[i - 1] * v[i + 1]) ** 0.5
            imputed[i] = True
    return pl.Series(filled, dtype=pl.Float64), pl.Series(imputed, dtype=pl.Boolean)


def build(df: pl.DataFrame, base_year: int = BASE_YEAR) -> tuple[pl.DataFrame, float]:
    base = annual_average(df, NSA, base_year)
    nsa = monthly(df, NSA).rename({"value": "cpi_u_nsa"})
    sa = monthly(df, SA).rename({"value": "cpi_u_sa"})
    out = nsa.join(sa, on="month", how="left")
    filled, imputed = fill_isolated_gaps(out["cpi_u_nsa"])
    out = (
        out.with_columns(filled.alias("cpi_u_nsa_filled"), imputed.alias("cpi_imputed"))
        .filter(pl.col("month") >= date(2010, 1, 1))
        .with_columns((base / pl.col("cpi_u_nsa_filled")).alias(f"to_{base_year}_usd"))
    )
    return out, base


def run(path: Path | None = None) -> pl.DataFrame:
    src = path or Path(max(glob.glob(RAW_GLOB)))
    out, base = build(read_data(src))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT_TABLE.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(OUT)
    pl.DataFrame(
        {
            "series_id": [NSA],
            "base": [f"{BASE_YEAR} annual average (M13)"],
            "value": [base],
            "first_month": [out["month"].min()],
            "last_month": [out["month"].max()],
            "source": [f"BLS cu.data.1.AllItems, archived at {src}"],
        }
    ).write_csv(OUT_TABLE)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the CPI-U deflator table.")
    ap.add_argument("--data", type=Path, default=None)
    args = ap.parse_args(argv)
    out = run(args.data)
    print(f"wrote {OUT} ({out.height} months, {out['month'].min()} to {out['month'].max()})")
    print(out.tail(3))
    return 0


if __name__ == "__main__":
    sys.exit(main())
