"""P1 report tables: obsolescence discount at matched concurrency, against hand-computed cases."""

import math

import polars as pl
import pytest

from gel.bench import report


def summary():
    # Two GPUs, one mode, two concurrencies. Old: $1/h; frontier: $4/h.
    return pl.DataFrame(
        {
            "gpu_label": ["OLD", "OLD", "NEW", "NEW"],
            "chip_id": ["old", "old", "new", "new"],
            "precision_mode": ["bf16"] * 4,
            "concurrency": [1, 128, 1, 128],
            "output_tok_per_s_mean": [50.0, 1000.0, 100.0, 4000.0],
            "price_paid_per_hr": [1.0, 1.0, 4.0, 4.0],
        }
    )


def test_discount_at_matched_concurrency():
    d = report.obsolescence_discount_table(summary(), frontier="NEW", price_col="price_paid_per_hr")
    old = {
        r["concurrency"]: r for r in d.filter(pl.col("gpu_label") == "OLD").iter_rows(named=True)
    }
    # c=1:   (1/4) / (50/100)    - 1 = 0.25/0.5  - 1 = -0.5
    # c=128: (1/4) / (1000/4000) - 1 = 0.25/0.25 - 1 =  0.0
    assert old[1]["discount"] == pytest.approx(-0.5)
    assert old[128]["discount"] == pytest.approx(0.0)


def test_frontier_discount_is_zero():
    d = report.obsolescence_discount_table(summary(), frontier="NEW", price_col="price_paid_per_hr")
    assert d.filter(pl.col("gpu_label") == "NEW")["discount"].to_list() == [0.0, 0.0]


def test_missing_frontier_gives_empty_table():
    d = report.obsolescence_discount_table(
        summary(), frontier="B200", price_col="price_paid_per_hr"
    )
    assert d.is_empty()


def test_mode_mismatch_is_not_compared():
    s = summary().with_columns(
        pl.when(pl.col("gpu_label") == "OLD")
        .then(pl.lit("fp8_weight_only"))
        .otherwise(pl.lit("bf16"))
        .alias("precision_mode")
    )
    d = report.obsolescence_discount_table(s, frontier="NEW", price_col="price_paid_per_hr")
    assert d.filter(pl.col("gpu_label") == "OLD").is_empty()


def test_best_precision_picks_fastest_mode_per_concurrency():
    s = pl.DataFrame(
        {
            "gpu_label": ["G"] * 4,
            "chip_id": ["g"] * 4,
            "precision_mode": ["bf16", "fp8", "bf16", "fp8"],
            "concurrency": [1, 1, 128, 128],
            "output_tok_per_s_mean": [10.0, 15.0, 100.0, 90.0],
            "price_paid_per_hr": [1.0] * 4,
        }
    )
    b = report.best_precision(s)
    got = dict(zip(b["concurrency"].to_list(), b["precision_mode"].to_list(), strict=True))
    assert got == {1: "fp8", 128: "bf16"}
    assert set(b["comparison"]) == {"best_available"}
    assert not math.isnan(b["output_tok_per_s_mean"][0])


def test_median_price_discounts(tmp_path):
    med = tmp_path / "m.csv"
    pl.DataFrame(
        {
            "chip_id": ["old", "new"],
            "billing": ["on_demand", "on_demand"],
            "median_neocloud": [1.0, 4.0],
            "median_all": [2.0, 4.0],
            "n_neocloud": [3, 5],
            "n_providers": [4, 7],
        }
    ).write_csv(med)
    s = summary().with_columns(pl.col("chip_id"))
    d = report.median_price_discounts(s, "NEW", med)
    row = d.filter(
        (pl.col("gpu_label") == "OLD")
        & (pl.col("concurrency") == 128)
        & (pl.col("price_spec") == "median_all")
        & (pl.col("comparison") == "like_for_like")
    ).row(0, named=True)
    # (2/4) / (1000/4000) - 1 = 0.5/0.25 - 1 = 1.0
    assert row["discount"] == pytest.approx(1.0)
