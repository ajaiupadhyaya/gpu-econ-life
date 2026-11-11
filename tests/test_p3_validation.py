"""P3 validation helpers on a tiny synthetic price history (test fixture, not data)."""

import polars as pl
import pytest

from gel.models import p3_validation as v
from gel.models import term_structure as ts


def history():
    rows = []
    for month in ("2025-01", "2025-02"):
        for chip, od, r1, r3 in (("a100_80gb", 2.0, 1.6, 1.2), ("h100_sxm", 4.0, None, None)):
            rows.append(("lambda", chip, "on_demand", None, od, month))
            if r1:
                rows.append(("lambda", chip, "reserved_1y", 12, r1, month))
                rows.append(("lambda", chip, "reserved_3y", 36, r3, month))
    return pl.DataFrame(
        rows,
        orient="row",
        schema=[
            "provider",
            "chip",
            "contract_type",
            "term_months",
            "price_usd_per_gpu_hour",
            "month",
        ],
    ).with_columns(
        (pl.col("month") + "-15T00:00:00Z").alias("retrieved_at"),
        pl.lit("instance").alias("price_basis"),
    )


def test_observed_term_ratios_and_delta():
    t = v.observed_term_ratios(history())
    row = t.filter(pl.col("term_months") == 36).row(0, named=True)
    assert row["observed_ratio"] == pytest.approx(0.6)  # 1.2 / 2.0
    assert row["implied_delta_level2"] == pytest.approx(ts.implied_delta(0.6, 3.0, r=0.08))


def test_cross_section_uses_throughput_ratio():
    cal = {
        "best_available": {
            "gpus": {
                "A100_SXM": {"q": 2000.0},
                "H100_SXM": {"q": 4000.0},
                "H200_SXM": {"q": 4400.0},
            }
        }
    }
    cs = v.check_cross_section(history(), cal)
    row = cs.filter(pl.col("pair") == "A100_SXM/H100_SXM").row(0, named=True)
    assert row["observed_rent_ratio"] == pytest.approx(0.5)  # 2.0 / 4.0
    assert row["model_rent_ratio"] == pytest.approx(0.5)
    assert row["agrees"]
