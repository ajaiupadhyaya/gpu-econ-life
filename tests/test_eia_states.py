"""Phase 3 EIA state electricity table: layout checks and the revenue / sales price."""

from datetime import date

import polars as pl
import pytest

from gel.build import eia_states as es

HEADER = [
    (
        "",
        None,
        None,
        None,
        "RESIDENTIAL",
        None,
        None,
        None,
        "COMMERCIAL",
        None,
        None,
        None,
        "INDUSTRIAL",
        None,
        None,
        None,
    ),
    (
        "",
        None,
        None,
        None,
        "Revenue",
        "Sales",
        "Customers",
        "Price",
        "Revenue",
        "Sales",
        "Customers",
        "Price",
        "Revenue",
        "Sales",
        "Customers",
        "Price",
    ),
    (
        "Year",
        "Month",
        "State",
        "Data Status",
        "Thousand Dollars",
        "Megawatthours",
        "Count",
        "Cents/kWh",
        "Thousand Dollars",
        "Megawatthours",
        "Count",
        "Cents/kWh",
        "Thousand Dollars",
        "Megawatthours",
        "Count",
        "Cents/kWh",
    ),
]


def test_header_check_accepts_current_layout():
    es.check_header(HEADER)


def test_header_check_rejects_moved_columns():
    bad = [list(r) for r in HEADER]
    bad[0][8], bad[0][12] = "INDUSTRIAL", "COMMERCIAL"
    with pytest.raises(ValueError, match="layout changed"):
        es.check_header([tuple(r) for r in bad])


def _raw():
    rows = []
    for state, status, rev, mwh in [
        ("VA", "Final", 100.0, 1000.0),  # $0.10/kWh
        ("TX", "Final", 60.0, 1000.0),  # $0.06/kWh
        ("CA", "Preliminary", 240.0, 1000.0),  # not a listed state, but in the US sum
    ]:
        rows.append(
            {
                "month": date(2026, 8, 1),
                "state": state,
                "data_status": status,
                "sector": "industrial",
                "revenue_k_usd": rev,
                "sales_mwh": mwh,
                "eia_price_cents_kwh": rev / mwh * 100,
            }
        )
    return pl.DataFrame(rows)


def test_price_is_revenue_over_sales():
    df = es.build(_raw(), "x.xlsx")
    va = df.filter(pl.col("state") == "VA")["usd_kwh"].item()
    assert va == pytest.approx(0.10)


def test_us_is_sales_weighted_sum_over_all_states():
    df = es.build(_raw(), "x.xlsx")
    us = df.filter(pl.col("state") == "US").row(0, named=True)
    # (100 + 60 + 240) / 3000 MWh = $0.1333/kWh, not the mean of state prices of listed states
    assert us["usd_kwh"] == pytest.approx(400 / 3000)
    assert us["data_status"] == "Preliminary"


def test_unlisted_states_are_dropped():
    df = es.build(_raw(), "x.xlsx")
    assert set(df["state"]) == {"VA", "TX", "US"}


def test_zero_sales_gives_missing_price():
    raw = _raw().with_columns(pl.lit(0.0).alias("sales_mwh"))
    df = es.build(raw, "x.xlsx")
    assert df.filter(pl.col("state") == "VA")["usd_kwh"].item() is None
