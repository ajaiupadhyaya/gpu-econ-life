"""P3 Monte Carlo: behaviour checks on SYNTHETIC inputs.

The capex and maintenance numbers below are test fixtures, not data or assumptions. They exist
only to exercise the code; the real values have no source yet (docs/open_questions.md).
"""

import math
from pathlib import Path

import pytest
import yaml

from gel.models import monte_carlo as mc

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "p3_model.yaml").read_text())

SYNTHETIC_CAL = {
    "best_available": {
        "gpus": {"H100_SXM": {"eta": 8.75, "w_load": 549.0, "idle_share": 0.21}},
        "mu_G": 0.46,
        "power_step": 1.43,
    }
}


SYNTHETIC_MARKET = {  # test fixture mirroring data/processed/p3_market.json
    "generation_step": {"sigma_G": 0.09},
    "markup": {"mean": 0.9, "kappa": 1.0, "sigma": 1.0, "boom_mean": 1.6},
    "electricity": {
        "mean_usd_kwh": 0.089,
        "kappa": 0.43,
        "sigma_usd_kwh": 0.01,
        "virginia_mean_usd_kwh": 0.10,
    },
    "regime": {"p_stay_constrained": 0.979, "p_stay_unconstrained": 0.958},
    "failure": {
        "base_annual_hazard": 0.02,
        "low_annual_hazard": 0.005,
        "upper_bound_annual_hazard": 0.11,
    },
}


def synthetic(n=1500, **over):
    cfg = mc.deep_merge(
        CFG,
        {
            "n_paths": n,
            "capex": {"K0_usd": 30_000.0, "growth_per_generation": 1.3},  # SYNTHETIC
            "maintenance_fraction_of_capex_per_year": 0.04,
        },
    )
    cfg = mc.deep_merge(cfg, over)
    return mc.resolve(cfg, SYNTHETIC_CAL, market=SYNTHETIC_MARKET)


def run(n=1500, seed=7, **over):
    p = synthetic(n, **over)
    return mc.summarize(mc.simulate(p, seed=seed), p, "test")


def test_refuses_unsourced_inputs():
    cfg = mc.deep_merge(CFG, {"maintenance_fraction_of_capex_per_year": None})
    with pytest.raises(mc.MissingInput) as exc:
        # no capex file passed: from_epoch stays unresolved
        mc.resolve(cfg, SYNTHETIC_CAL, market=SYNTHETIC_MARKET)
    msg = str(exc.value)
    assert "capex.K0_usd" in msg and "maintenance_fraction_of_capex_per_year" in msg


def test_cli_stops_cleanly_without_inputs(tmp_path, capsys):
    cfg = mc.deep_merge(CFG, {"maintenance_fraction_of_capex_per_year": None})
    path = tmp_path / "p3.yaml"
    path.write_text(yaml.safe_dump(cfg))
    assert mc.main(["--config", str(path), "--out-dir", str(tmp_path), "--scenarios", "base"]) == 2
    assert "unsourced" in capsys.readouterr().err


def test_maintenance_scales_with_capex():
    lo = run(maintenance_fraction_of_capex_per_year=0.0)
    hi = run(maintenance_fraction_of_capex_per_year=0.30)
    assert hi["retire_age_mean_y"] <= lo["retire_age_mean_y"]


def test_deterministic_given_seed():
    a, b = run(seed=11), run(seed=11)
    assert a["retire_age_p50_y"] == b["retire_age_p50_y"]
    assert a["share_obsolescence"] == b["share_obsolescence"]


def test_channel_shares_sum_to_one_and_ages_in_range():
    r = run()
    total = sum(r[f"share_{c}"] for c in mc.CHANNELS)
    assert total == pytest.approx(1.0)
    assert 0 <= r["retire_age_p10_y"] <= r["retire_age_p50_y"] <= r["retire_age_p90_y"] <= 15


def test_power_constraint_shortens_life():
    con = run(**CFG["scenarios"]["always_constrained"])
    abd = run(**CFG["scenarios"]["power_abundant"])
    assert con["retire_age_p50_y"] <= abd["retire_age_p50_y"]
    assert abd["share_obsolescence"] == 0.0


def test_faster_frontier_shortens_life():
    fast = run(**CFG["scenarios"]["fast_frontier"])
    slow = run(**CFG["scenarios"]["slow_frontier"])
    assert fast["retire_age_mean_y"] <= slow["retire_age_mean_y"]


def test_no_markup_means_no_obsolescence_channel():
    # Price = frontier full cost: the frontier's margin net of capex is m (A_f + opex_f) = 0,
    # so the constrained rule collapses to the negative-margin rule.
    r = run(
        markup={"mean": 0.0, "x0": 0.0, "sigma": 0.0, "process": "level"},
        regime={"p_stay_constrained": 1.0, "p_stay_unconstrained": 0.0, "start_constrained": True},
    )
    assert r["share_obsolescence"] == pytest.approx(0.0, abs=0.01)


def test_no_failure_when_scale_is_huge():
    r = run(failure={"annual_hazard": 1e-12, "shape": 1.0})
    assert r["share_failure"] == 0.0


def test_value_curve_declines_and_book_values():
    r = run()
    v = r["value_over_capex"]
    assert v[0] > v[3]
    assert mc.book_value(2.0, 4.0) == pytest.approx(0.5)
    assert mc.book_value(7.0, 6.0) == 0.0


def test_rent_ratio_starts_at_one():
    r = run()
    assert r["rent_ratio_by_year"][0] == pytest.approx(1.0)
    assert 0 < r["implied_flat_ratio"][60] <= 1.5


def test_from_epoch_values_resolve():
    cfg = CFG
    p = mc.resolve(
        cfg, SYNTHETIC_CAL, {"K0_usd": 33_600.0, "growth_per_generation": 1.627}, SYNTHETIC_MARKET
    )
    assert p["capex"]["K0_usd"] == 33_600.0
    assert p["hardware"]["gen0"]["eta"] == 8.75


def test_missing_market_file_is_refused():
    with pytest.raises(mc.MissingInput, match="p3_market_calibration"):
        mc.resolve(CFG, SYNTHETIC_CAL, {"K0_usd": 1.0, "growth_per_generation": 1.0})


def test_annual_hazard_to_weibull_scale():
    # Shape 1, h = 2%: scale = 12 / -ln(0.98) = 593.98 months, so 12-month survival is exactly 0.98
    scale = mc.failure_scale_months({"annual_hazard": 0.02, "shape": 1.0})
    assert scale == pytest.approx(12 / -math.log(0.98))
    assert math.exp(-((12 / scale) ** 1.0)) == pytest.approx(0.98)
    assert mc.failure_scale_months({"annual_hazard": None, "scale_years": 8, "shape": 1.5}) == 96


def test_markup_jump_lifts_level():
    p = synthetic(
        400, markup={"sigma": 0.0, "x0": 0.9, "jump_month": 24, "jump_mean": 2.0, "jump_to": 2.0}
    )
    m = mc.simulate(p, seed=1)["markup"]
    assert m[:, 23].mean() == pytest.approx(0.9, abs=1e-9)
    assert m[:, 24].mean() == pytest.approx(2.0, abs=1e-9)


def test_log_markup_is_stationary_with_no_drift():
    import numpy as np

    rng = np.random.default_rng(5)
    cfg = {"mean": 0.9, "kappa": 1.0, "sigma": 1.1, "x0": "stationary", "floor": -0.5}
    m = mc.markup_path(rng, 40_000, 120, cfg)
    assert m[:, 0].mean() == pytest.approx(0.9, abs=0.03)
    assert m[:, 119].mean() == pytest.approx(0.9, abs=0.03)
    assert m.min() > -0.5 - 1e-12
