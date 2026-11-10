"""P1 energy integration and metrics vs hand-computed cases (handoff_extension.md 3.5)."""

import math

import numpy as np
import pytest

from gel.bench import energy, metrics

# ---- energy ------------------------------------------------------------------------------------


def test_trapezoid_full_window():
    # 100 W, 200 W, 100 W at 0, 1, 2 s -> 0.5*(100+200) + 0.5*(200+100) = 300 J
    t = np.array([0, 1000, 2000])
    p = np.array([100.0, 200.0, 100.0])
    res = energy.integrate_window(t, p, 0, 2000)
    assert res.joules == pytest.approx(300.0)
    assert res.covered


def test_trapezoid_interpolates_window_edges():
    # Window [0.5 s, 1.5 s]: p(0.5)=150, p(1)=200, p(1.5)=150 -> 87.5 + 87.5 = 175 J
    t = np.array([0, 1000, 2000])
    p = np.array([100.0, 200.0, 100.0])
    res = energy.integrate_window(t, p, 500, 1500)
    assert res.joules == pytest.approx(175.0)
    assert res.mean_watts == pytest.approx(175.0)


def test_window_not_spanned_is_missing():
    t = np.array([1000, 2000])
    p = np.array([100.0, 100.0])
    res = energy.integrate_window(t, p, 0, 2000)
    assert math.isnan(res.joules)
    assert not res.covered


def test_gap_larger_than_limit_flags_window():
    t = np.array([0, 1000, 5000, 6000])
    p = np.array([100.0, 100.0, 100.0, 100.0])
    res = energy.integrate_window(t, p, 0, 6000, max_gap_s=2.5)
    assert res.joules == pytest.approx(600.0)  # still integrated, but flagged
    assert not res.covered
    assert res.max_gap_s == pytest.approx(4.0)


def test_nan_power_samples_are_dropped():
    t = np.array([0, 1000, 2000])
    p = np.array([100.0, np.nan, 100.0])
    res = energy.integrate_window(t, p, 0, 2000, max_gap_s=2.5)
    assert res.joules == pytest.approx(200.0)
    assert res.max_gap_s == pytest.approx(2.0)


def test_unsorted_samples_are_sorted():
    t = np.array([2000, 0, 1000])
    p = np.array([100.0, 100.0, 200.0])
    assert energy.integrate_window(t, p, 0, 2000).joules == pytest.approx(300.0)


# ---- metrics -----------------------------------------------------------------------------------


def test_cost_per_million_tokens():
    # $2.99/h at 1,000 tok/s: 2.99 / 3.6e6 * 1e6 = $0.830556 per million tokens
    assert metrics.cost_per_mtok(2.99, 1000.0) == pytest.approx(2.99 / 3.6)


def test_energy_cost_per_million_tokens():
    # 700 W for 100 s = 70,000 J over 100,000 tokens = 0.7 J/token.
    # 0.7e6 J = 0.194444 kWh; * $0.08 * 1.3 PUE = $0.0202222
    got = metrics.energy_cost_per_mtok(70_000.0, 100_000, price_kwh=0.08, pue=1.3)
    assert got == pytest.approx(0.7e6 / 3.6e6 * 0.08 * 1.3)
    assert got == pytest.approx(0.0202222, rel=1e-5)


def test_tokens_per_joule():
    assert metrics.tokens_per_joule(100_000, 70_000.0) == pytest.approx(1.4285714, rel=1e-6)
    assert math.isnan(metrics.tokens_per_joule(10, 0.0))


def test_obsolescence_discount_premium():
    # Old chip costs half as much but makes a quarter of the output: (0.5/0.25) - 1 = +1.0
    assert metrics.obsolescence_discount(1.5, 3.0, 500.0, 2000.0) == pytest.approx(1.0)


def test_obsolescence_discount_discount():
    # Old chip costs a quarter as much and makes half the output: (0.25/0.5) - 1 = -0.5
    assert metrics.obsolescence_discount(1.0, 4.0, 1000.0, 2000.0) == pytest.approx(-0.5)


def test_obsolescence_discount_frontier_is_zero():
    assert metrics.obsolescence_discount(3.0, 3.0, 2000.0, 2000.0) == pytest.approx(0.0)


def test_obsolescence_discount_equals_cost_ratio_minus_one():
    # D is also the ratio of $/M tokens, minus one.
    d = metrics.obsolescence_discount(1.2, 3.5, 700.0, 2600.0)
    ratio = metrics.cost_per_mtok(1.2, 700.0) / metrics.cost_per_mtok(3.5, 2600.0)
    assert d == pytest.approx(ratio - 1)
