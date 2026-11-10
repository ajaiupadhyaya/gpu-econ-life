"""P3 Monte Carlo: behaviour checks on SYNTHETIC inputs.

The capex and maintenance numbers below are test fixtures, not data or assumptions. They exist
only to exercise the code; the real values have no source yet (docs/open_questions.md).
"""

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


def synthetic(n=1500, **over):
    cfg = mc.deep_merge(
        CFG,
        {
            "n_paths": n,
            "capex": {"K0_usd": 30_000.0, "growth_per_generation": 1.3},  # SYNTHETIC
            "maintenance_usd_per_month": 50.0,  # SYNTHETIC
        },
    )
    cfg = mc.deep_merge(cfg, over)
    return mc.resolve(cfg, SYNTHETIC_CAL)


def run(n=1500, seed=7, **over):
    p = synthetic(n, **over)
    return mc.summarize(mc.simulate(p, seed=seed), p, "test")


def test_refuses_unsourced_inputs():
    with pytest.raises(mc.MissingInput) as exc:
        mc.resolve(CFG, SYNTHETIC_CAL)
    msg = str(exc.value)
    assert "capex.K0_usd" in msg and "maintenance_usd_per_month" in msg


def test_cli_stops_cleanly_without_inputs(tmp_path, capsys):
    assert mc.main(["--out-dir", str(tmp_path), "--scenarios", "base"]) == 2
    assert "unsourced" in capsys.readouterr().err


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
        markup={"mean": 0.0, "x0": 0.0, "sigma": 0.0},
        regime={"p_stay_constrained": 1.0, "p_stay_unconstrained": 0.0, "start_constrained": True},
    )
    assert r["share_obsolescence"] == pytest.approx(0.0, abs=0.01)


def test_no_failure_when_scale_is_huge():
    r = run(failure={"scale_years": 1e6, "shape": 1.5})
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
    cfg = mc.deep_merge(CFG, {"maintenance_usd_per_month": 50.0})  # SYNTHETIC maintenance
    p = mc.resolve(cfg, SYNTHETIC_CAL, {"K0_usd": 33_600.0, "growth_per_generation": 1.627})
    assert p["capex"]["K0_usd"] == 33_600.0
    assert p["hardware"]["gen0"]["eta"] == 8.75
