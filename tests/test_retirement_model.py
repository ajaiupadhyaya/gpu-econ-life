"""P3 retirement model: hand-computed cases (docs/handoff_extension.md section 5, Decision 8)."""

import math

import numpy as np
import pytest

from gel.models import retirement_model as rm

# ---- finance helpers ----


def test_monthly_rate():
    assert rm.monthly_rate(0.08) == pytest.approx(1.08 ** (1 / 12) - 1)


def test_annuity_payment_hand_value():
    # K = $30,000, r = 8%/yr, n = 60 months: r_m = 0.0064340, A = K r_m / (1 - (1+r_m)^-60)
    assert rm.annuity_payment(30_000, 0.08, 60) == pytest.approx(604.2916, rel=1e-6)


def test_annuity_payment_zero_rate_is_straight_line():
    assert rm.annuity_payment(30_000, 0.0, 60) == pytest.approx(500.0)


# ---- monthly economics (Decision 8: idle draw is charged) ----


def test_monthly_economics_hand_case():
    # p = $2e-7/token, q = 1,000 tok/s, u = 0.7:
    #   revenue = 2e-7 * 1000 * 3600 * 730 * 0.7 = $367.92
    # e = $0.08/kWh, PUE 1.3, w_load 700 W, w_idle 100 W, maintenance $20:
    #   kWh = 730 * (0.7*700 + 0.3*100) / 1000 = 730 * 520 / 1000 = 379.6
    #   opex = 0.08 * 1.3 * 379.6 + 20 = 39.4784 + 20 = 59.4784
    rev, opex, margin = rm.monthly_economics(
        p=2e-7, q=1000.0, u=0.7, e=0.08, w_load=700.0, w_idle=100.0, pue=1.3, maint=20.0
    )
    assert rev == pytest.approx(367.92)
    assert opex == pytest.approx(59.4784)
    assert margin == pytest.approx(367.92 - 59.4784)


def test_idle_draw_is_charged():
    _, opex_idle, _ = rm.monthly_economics(0, 1, 0.5, 0.1, 400, 100, 1.0, 0)
    _, opex_none, _ = rm.monthly_economics(0, 1, 0.5, 0.1, 400, 0, 1.0, 0)
    assert opex_idle - opex_none == pytest.approx(0.1 * 730 * 0.5 * 100 / 1000)


# ---- retirement rules ----


def test_retire_after_three_consecutive_months():
    cond = np.zeros((1, 20), dtype=bool)
    cond[0, 10:] = True
    assert rm.first_sustained(cond, start=np.array([0]), hold=3)[0] == 12


def test_two_month_blip_does_not_retire():
    cond = np.zeros((1, 20), dtype=bool)
    cond[0, 5:7] = True
    cond[0, 15:] = True
    assert rm.first_sustained(cond, start=np.array([0]), hold=3)[0] == 17


def test_condition_before_launch_is_ignored():
    cond = np.ones((2, 10), dtype=bool)
    got = rm.first_sustained(cond, start=np.array([0, 4]), hold=3)
    assert got.tolist() == [2, 6]


def test_never_retires_returns_minus_one():
    cond = np.zeros((1, 10), dtype=bool)
    assert rm.first_sustained(cond, start=np.array([0]), hold=3)[0] == -1


def test_constrained_rule_hand_case():
    # Old chip: margin $100/month at 0.4 kW -> $250 per kW.
    # Frontier: margin $900 at 0.7 kW, annuitized capex $600 -> (900 - 600)/0.7 = $428.6 per kW.
    # Old earns less per kW than a new chip in the same slot would after paying for it -> evict.
    assert rm.obsolete_in_power_slot(100.0, 400.0, 900.0, 600.0, 700.0)
    # With frontier capex of $800: (900 - 800)/0.7 = $142.9 per kW < $250 -> keep.
    assert not rm.obsolete_in_power_slot(100.0, 400.0, 900.0, 800.0, 700.0)


# ---- stochastic processes ----


def test_ou_deterministic_when_sigma_zero():
    rng = np.random.default_rng(0)
    x = rm.ou_path(rng, n=1, months=3, x0=1.0, mean=0.0, kappa=1.2, sigma=0.0, floor=-1.0)
    # x_{t+1} = x_t + kappa (mean - x_t) / 12 = 0.9 x_t
    assert x[0].tolist() == pytest.approx([1.0, 0.9, 0.81])


def test_ou_respects_floor():
    rng = np.random.default_rng(1)
    x = rm.ou_path(rng, n=200, months=120, x0=0.0, mean=-0.4, kappa=2.0, sigma=2.0, floor=-0.5)
    assert x.min() >= -0.5


def test_markov_identity_stays_put():
    rng = np.random.default_rng(2)
    s = rm.markov_regime(
        rng,
        n=50,
        months=60,
        p_stay_constrained=1.0,
        p_stay_unconstrained=1.0,
        start_constrained=True,
    )
    assert s.all()


def test_markov_long_run_share():
    # Stationary share constrained = (1 - p_uu) / (2 - p_cc - p_uu) = 0.1 / 0.3 = 1/3
    rng = np.random.default_rng(3)
    s = rm.markov_regime(
        rng,
        n=4000,
        months=240,
        p_stay_constrained=0.8,
        p_stay_unconstrained=0.9,
        start_constrained=True,
    )
    assert s[:, 120:].mean() == pytest.approx(1 / 3, abs=0.01)


def test_weibull_failure_median():
    rng = np.random.default_rng(4)
    ages = rm.weibull_failure_month(rng, 200_000, scale_months=96.0, shape=1.5)
    # median = scale * ln(2)^(1/shape) = 75.19 months; ceil adds up to one month
    assert np.median(ages) == pytest.approx(75.19 + 0.5, abs=1.0)
    assert ages.min() >= 1


# ---- economic value ----


def test_value_constant_margin_is_annuity():
    # $100/month for 12 months, alive throughout, r = 8%/yr. The handoff's sum starts at s = a with
    # discount factor 1 (annuity-due): V(0) = 100 * (1 - (1+r_m)^-12) / r_m * (1 + r_m) = 1158.69
    r_m = rm.monthly_rate(0.08)
    margins = np.full((3, 12), 100.0)
    alive = np.ones((3, 12), dtype=bool)
    v = rm.value_by_age(margins, alive, 0.08, ages=[0, 6])
    assert v[0] == pytest.approx(100 * (1 - (1 + r_m) ** -12) / r_m * (1 + r_m), rel=1e-9)
    assert v[0] == pytest.approx(1158.693, rel=1e-6)
    assert v[6] == pytest.approx(100 * (1 - (1 + r_m) ** -6) / r_m * (1 + r_m), rel=1e-9)


def test_value_conditions_on_survival():
    margins = np.full((2, 4), 10.0)
    alive = np.array([[True] * 4, [True, False, False, False]])
    v = rm.value_by_age(margins, alive, 0.0, ages=[0, 1])
    assert v[0] == pytest.approx((40 + 10) / 2)  # both alive at age 0
    assert v[1] == pytest.approx(30.0)  # only path 0 alive at age 1


def test_value_nan_when_nobody_alive():
    v = rm.value_by_age(np.ones((1, 3)), np.array([[True, False, False]]), 0.0, ages=[2])
    assert math.isnan(v[2])
