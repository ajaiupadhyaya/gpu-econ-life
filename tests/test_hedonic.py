"""Phase 5 specifications on synthetic data with known answers (Decision 23)."""

from datetime import date

import numpy as np
import polars as pl
import pytest

from gel.models import hedonic as h

TFLOPS = {
    "v100": 125.0,
    "a100_40gb": 312.0,
    "a100_80gb": 312.0,
    "h100_pcie": 756.0,
    "h100_sxm": 989.5,
    "h200": 989.5,
    "b200": 2250.0,
}
RELEASE = {
    "v100": 0,
    "a100_40gb": 30,
    "a100_80gb": 36,
    "h100_pcie": 60,
    "h100_sxm": 60,
    "h200": 84,
    "b200": 84,
}


def synthetic(age_slope: float = -0.15, curvature: float = 0.0, seed: int = 3) -> pl.DataFrame:
    """Listing-months: y = 0.8 ln TFLOPS + slope*age + curvature*age^2 + month effect + noise."""
    rng = np.random.default_rng(seed)
    month_fx = rng.normal(scale=0.05, size=110)
    rows = []
    for chip, rel in RELEASE.items():
        for m in range(rel + 1, 108):
            for prov in ("p1", "p2", "p3"):
                age = (m - rel) / 12
                y = (
                    0.8 * np.log(TFLOPS[chip])
                    + age_slope * age
                    + curvature * age**2
                    + month_fx[m]
                    + rng.normal(scale=0.03)
                )
                rows.append(
                    {
                        "chip": chip,
                        "m": m,
                        "provider": prov,
                        "y": y,
                        "age": age,
                        "age_months": m - rel,
                    }
                )
    df = pl.DataFrame(rows)
    df = df.with_columns(
        pl.col("m")
        .map_elements(lambda m: date(2017 + m // 12, m % 12 + 1, 1), return_dtype=pl.Date)
        .alias("month"),
        pl.col("chip").replace_strict(TFLOPS, return_dtype=pl.Float64).log().alias("ln_tflops"),
        pl.lit(0.0).alias("ln_bw"),
        pl.lit(0.0).alias("ln_mem"),
        pl.lit(0.0).alias("rel_frontier"),
        pl.concat_str(["provider", pl.lit(":r")]).alias("prov_region"),
        pl.lit("on_demand:0").alias("contract_term"),
        pl.lit(8).alias("gpu_count"),
        pl.lit("instance").alias("price_basis"),
        pl.lit("sxm").alias("form_factor"),
        (pl.col("age_months") // h.BIN_MONTHS).alias("age_bin"),
    )
    basis = h.spline_basis(df["age"].to_numpy())
    return df.with_columns([pl.Series(k, v) for k, v in basis.items()])


def _measure(rows, name):
    return next(r for r in rows if r["measure"] == name)


def test_spline_basis_hand_values():
    b = h.spline_basis(np.array([2.0]))
    assert b["age1"][0] == 2.0 and b["age2"][0] == 4.0 and b["age3"][0] == 8.0
    assert b["knot0"][0] == pytest.approx(0.5**3)  # knot at 1.5
    assert b["knot1"][0] == 0.0 and b["knot2"][0] == 0.0


def test_strategy1_recovers_known_age_slope():
    df = synthetic(age_slope=-0.15)
    _, rows = h.run_spec(h.SPECS["s1a_tflops"], df, draws=199)
    assert _measure(rows, "d2")["estimate"] == pytest.approx(-0.30, abs=0.02)
    assert _measure(rows, "rate_2_4")["estimate"] == pytest.approx(-0.15, abs=0.02)
    assert _measure(rows, "coef_ln_tflops")["estimate"] == pytest.approx(0.8, abs=0.03)


def test_strategy4_shape_is_invariant_to_any_linear_trend():
    # Adding d*age to y changes nothing under chip + month effects (Hall 1968).
    base = synthetic(age_slope=-0.15, curvature=0.02)
    tilted = base.with_columns((pl.col("y") - 0.30 * pl.col("age")).alias("y"))
    _, r0 = h.run_spec(h.SPECS["s4_shape"], base, draws=99)
    _, r1 = h.run_spec(h.SPECS["s4_shape"], tilted, draws=99)
    f0, f1 = (
        _measure(r0, "early_minus_late_rate")["estimate"],
        _measure(r1, "early_minus_late_rate")["estimate"],
    )
    assert f0 == pytest.approx(f1, abs=1e-6)
    # curvature 0.02 per year^2: rate(0-2) - rate(2-4) = 0.02*(4/2) - 0.02*(16-4)/2 = -0.08
    assert f0 == pytest.approx(-0.08, abs=0.01)
    assert [r["measure"] for r in r0] == ["early_minus_late_rate"]


def test_profile_row_includes_linear_only_when_identified():
    df = synthetic()
    fit, _ = h.run_spec(h.SPECS["s1a_tflops"], df, draws=99)
    r_lin = h.profile_row(fit, 2.0, include_linear=True)
    r_nolin = h.profile_row(fit, 2.0, include_linear=False)
    assert r_lin[fit.index("age1")] == 2.0
    assert r_nolin[fit.index("age1")] == 0.0


def test_bin_dummies_reference_bins():
    df = synthetic()
    pooled, cols = h.bin_dummies(df)
    assert "bin00" not in cols and "bin01" in cols
    by_chip, cols_c = h.bin_dummies(df, by_chip=True)
    first_b200 = int(df.filter(pl.col("chip") == "b200")["age_bin"].min())
    assert f"b200__bin{first_b200:02d}" not in cols_c
    assert pooled.height == by_chip.height == df.height


def test_event_dummies_event_time():
    df = pl.DataFrame(
        {
            "chip": ["v100", "v100", "h200"],
            "month": [date(2020, 4, 1), date(2020, 11, 1), date(2020, 11, 1)],
        }
    )
    out, cols = h.event_dummies(df, {"a100_40gb": date(2020, 5, 1)})
    assert out["tau"].to_list() == [-1, 6, None]
    assert out["ev_+6_+11"].to_list() == [0.0, 1.0, 0.0]
    assert "ev_-6_-1" not in cols  # reference bin


def test_extrapolation_flag_for_short_within_chip_spans():
    df = synthetic().filter(pl.col("m") >= 100)  # under a year per chip
    _, rows = h.run_spec(
        h.SPECS["s2_frontier"],
        df.with_columns(pl.col("rel_frontier") + pl.col("age") * 0.0),
        draws=99,
    )
    assert all(r["extrapolated"] for r in rows)


def test_detrended_curvature_has_zero_average_slope_on_grid():
    df = synthetic(age_slope=-0.15, curvature=0.02)
    fit, _ = h.run_spec(h.SPECS["s4_shape"], df, draws=99)
    rows = h.detrended_curvature_rows(fit)
    ages = np.array(sorted(rows))
    vals = np.array([rows[a] @ fit.coef for a in ages])
    slope = np.polyfit(ages, vals, 1)[0]
    assert slope == pytest.approx(0.0, abs=1e-9)
    assert vals[0] == pytest.approx(0.0, abs=1e-12)


def test_chip_trend_check_drops_age2_and_matches_no_trend_reference():
    from gel.models import review_checks as rc

    df = synthetic(age_slope=-0.15, curvature=0.02)
    out = rc.chip_trend_check(df)
    assert set(out["dropped"]) == {"age2"}
    # The shape is linear in the assumed c2 with slope -4.
    x, y = out["assumed_c2"].to_numpy(), out["early_minus_late_rate"].to_numpy()
    assert np.allclose(np.diff(y) / np.diff(x), -4.0)
    assert out["no_trend_estimate"][0] == pytest.approx(-0.08, abs=0.01)


def test_bin_shift_check_covers_six_shifts():
    from gel.models import review_checks as rc

    out = rc.bin_shift_check(synthetic())
    assert sorted(out["shift_k"].unique().to_list()) == [0, 1, 2, 3, 4, 5]
    assert set(out["age_months"].unique().to_list()) == {12, 24, 36, 48}
