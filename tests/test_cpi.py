"""Phase 3 CPI-U deflator: BLS flat-file parsing, base year, and the shutdown gap (Decision 21)."""

from datetime import date
from pathlib import Path

import polars as pl
import pytest

from gel.build import cpi

SAMPLE = """series_id        \tyear\tperiod\t       value\tfootnote_codes
CUUR0000SA0      \t2025\tM09\t     324.800\t
CUUR0000SA0      \t2025\tM10\t           -\tX
CUUR0000SA0      \t2025\tM11\t     324.122\t
CUUR0000SA0      \t2025\tM13\t     321.943\t
CUSR0000SA0      \t2025\tM09\t     324.245\t
CUSR0000SA0      \t2025\tM10\t           -\tX
CUSR0000SA0      \t2025\tM11\t     325.063\t
CUUR0000AA0      \t2025\tM09\t     999.000\t
"""


@pytest.fixture
def data(tmp_path: Path) -> pl.DataFrame:
    path = tmp_path / "cu.data.1.AllItems.txt"
    path.write_text(SAMPLE)
    return cpi.read_data(path)


def test_dash_is_missing_not_zero(data):
    oct_ = data.filter((pl.col("series_id") == cpi.NSA) & (pl.col("period") == "M10"))
    assert oct_["value"].item() is None


def test_annual_average_is_m13(data):
    assert cpi.annual_average(data, cpi.NSA, 2025) == pytest.approx(321.943)


def test_missing_annual_average_raises(data):
    with pytest.raises(ValueError, match="M13"):
        cpi.annual_average(data, cpi.NSA, 2024)


def test_monthly_excludes_annual_and_other_series(data):
    m = cpi.monthly(data, cpi.NSA)
    assert m["month"].to_list() == [date(2025, 9, 1), date(2025, 10, 1), date(2025, 11, 1)]


def test_isolated_gap_is_geometric_mean_and_flagged(data):
    out, base = cpi.build(data)
    row = out.filter(pl.col("month") == date(2025, 10, 1)).row(0, named=True)
    assert row["cpi_u_nsa"] is None  # raw gap kept
    assert row["cpi_imputed"] is True
    assert row["cpi_u_nsa_filled"] == pytest.approx((324.8 * 324.122) ** 0.5)
    assert out["cpi_imputed"].sum() == 1


def test_deflator_converts_to_base_year_dollars(data):
    out, base = cpi.build(data)
    sep = out.filter(pl.col("month") == date(2025, 9, 1)).row(0, named=True)
    # $10 nominal in Sep 2025 = 10 * 321.943 / 324.8 in 2025 dollars
    assert 10 * sep["to_2025_usd"] == pytest.approx(10 * 321.943 / 324.8)


def test_longer_gaps_stay_missing():
    filled, imputed = cpi.fill_isolated_gaps(pl.Series([1.0, None, None, 4.0]))
    assert filled.to_list() == [1.0, None, None, 4.0]
    assert not imputed.any()


def test_edge_gaps_stay_missing():
    filled, imputed = cpi.fill_isolated_gaps(pl.Series([None, 2.0, None]))
    assert filled.to_list() == [None, 2.0, None]
