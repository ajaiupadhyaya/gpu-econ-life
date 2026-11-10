"""P2 term-structure inversion. Hand-checked cases: docs/handoff_extension.md section 4.3."""

import math

import numpy as np
import pytest

from gel.models import term_structure as ts

# ---- Level 1: constant decay, no discounting -------------------------------------------------


def test_level1_ratio_hand_value():
    # delta = 0.1, T = 5: (1 - e^-0.5) / 0.5 = 0.786938680...
    assert ts.flat_ratio(0.1, 5.0) == pytest.approx(0.7869386805747332, abs=1e-12)


def test_level1_ratio_zero_decay_is_one():
    assert ts.flat_ratio(0.0, 5.0) == pytest.approx(1.0)
    assert ts.flat_ratio(1e-12, 5.0) == pytest.approx(1.0)


def test_level1_inversion_a100_ornn_point():
    # Handoff 4.3: F/R0 = 0.80, T = 5 -> delta ~ 0.092 (+-0.002)
    assert ts.implied_delta(0.80, 5.0) == pytest.approx(0.092, abs=0.002)


def test_level1_inversion_b200_ornn_point():
    # Handoff 4.3: F/R0 = 0.54, T = 5 -> delta ~ 0.278 (+-0.003)
    assert ts.implied_delta(0.54, 5.0) == pytest.approx(0.278, abs=0.003)


def test_inversion_round_trips():
    for delta in (0.01, 0.2, 0.9, 3.0):
        ratio = ts.flat_ratio(delta, 3.0)
        assert ts.implied_delta(ratio, 3.0) == pytest.approx(delta, rel=1e-8)


def test_ratio_at_or_above_one_is_missing_not_clipped():
    res = ts.solve_delta(1.02, 5.0)
    assert math.isnan(res.delta)
    assert "non-positive" in res.reason
    assert math.isnan(ts.implied_delta(1.0, 5.0))


def test_ratio_below_bracket_floor_is_missing():
    # delta = 5 at T = 5 gives (1 - e^-25)/25 = 0.04; anything lower needs delta > 5.
    res = ts.solve_delta(0.01, 5.0)
    assert math.isnan(res.delta)
    assert "above" in res.reason


# ---- Level 2: discounting ---------------------------------------------------------------------


def test_level2_hand_value():
    # r = 0.08, delta = 0.1, T = 5:
    # num = (1 - e^-0.9)/0.18 = 3.29684, den = (1 - e^-0.4)/0.08 = 4.12100 -> 0.800009
    num = (1 - math.exp(-0.9)) / 0.18
    den = (1 - math.exp(-0.4)) / 0.08
    assert ts.flat_ratio(0.1, 5.0, r=0.08) == pytest.approx(num / den, rel=1e-12)


def test_level2_converges_to_level1_as_r_goes_to_zero():
    # Handoff 4.3: tolerance 1e-6
    for delta in (0.05, 0.278):
        assert ts.flat_ratio(delta, 5.0, r=1e-9) == pytest.approx(
            ts.flat_ratio(delta, 5.0), abs=1e-6
        )
    assert ts.implied_delta(0.80, 5.0, r=1e-9) == pytest.approx(
        ts.implied_delta(0.80, 5.0), abs=1e-6
    )


def test_discounting_raises_implied_delta():
    # Discounting puts more weight on early (higher) rents, so the same observed ratio needs
    # faster decay to match.
    assert ts.implied_delta(0.80, 5.0, r=0.08) > ts.implied_delta(0.80, 5.0)


# ---- Level 3: term premium --------------------------------------------------------------------


def test_level3_zero_premium_equals_level2():
    assert ts.implied_delta(0.8, 5.0, r=0.08, pi=0.0) == pytest.approx(
        ts.implied_delta(0.8, 5.0, r=0.08)
    )


def test_level3_premium_lowers_implied_delta():
    # A positive term premium explains part of the discount, so naive delta (pi = 0) is biased up.
    naive = ts.implied_delta(0.8, 5.0, r=0.08, pi=0.0)
    adjusted = ts.implied_delta(0.8, 5.0, r=0.08, pi=0.02)
    assert adjusted < naive
    # Hand check: adjusted ratio = 0.8 / (1 - 0.1) = 0.8889, which Level 2 then inverts.
    assert adjusted == pytest.approx(ts.implied_delta(0.8 / 0.9, 5.0, r=0.08), rel=1e-10)


def test_level3_premium_too_large_is_missing():
    res = ts.solve_delta(0.8, 5.0, pi=0.25)  # 1 - pi*T <= 0
    assert math.isnan(res.delta)


# ---- Level 4: age-varying decay ---------------------------------------------------------------


def test_cumulative_hazard_hand_value():
    # beta0 = 0.1, beta1 = 0.4, tau = 1, t = 2: 0.2 + 0.4*(1 - e^-2) = 0.545866...
    h = ts.cumulative_hazard(2.0, 0.1, 0.4, 1.0)
    assert h == pytest.approx(0.2 + 0.4 * (1 - math.exp(-2.0)), rel=1e-12)


def test_level4_with_beta1_zero_reproduces_level1_and_level2():
    for r in (0.0, 0.08):
        for tenor in (1.0, 3.0, 5.0):
            assert ts.flat_ratio_age_varying(tenor, 0.15, 0.0, 1.0, r=r) == pytest.approx(
                ts.flat_ratio(0.15, tenor, r=r), rel=1e-9
            )


def test_level4_fit_recovers_known_parameters():
    true = (0.08, 0.5, 0.75)
    tenors = np.array([0.5, 1.0, 2.0, 3.0, 5.0])
    ratios = np.array([ts.flat_ratio_age_varying(t, *true, r=0.08) for t in tenors])
    fit = ts.fit_age_varying(tenors, ratios, r=0.08)
    assert fit.level == 4
    assert fit.beta0 == pytest.approx(true[0], abs=1e-3)
    assert fit.beta1 == pytest.approx(true[1], abs=1e-2)
    assert fit.tau == pytest.approx(true[2], abs=1e-2)


def test_level4_needs_three_tenors_else_level2():
    fit = ts.fit_age_varying(np.array([1.0, 3.0]), np.array([0.9, 0.75]), r=0.08)
    assert fit.level == 2
    assert fit.beta1 == 0.0
    assert "fewer than 3 tenors" in fit.note


def test_level4_respects_bounds():
    tenors = np.array([1.0, 2.0, 3.0, 5.0])
    ratios = np.array([0.95, 0.9, 0.86, 0.8])
    fit = ts.fit_age_varying(tenors, ratios, r=0.08)
    assert fit.beta0 >= 0
    assert fit.beta0 + fit.beta1 >= -1e-12
    assert 0.25 <= fit.tau <= 5.0


# ---- Implied economic lives -------------------------------------------------------------------


def test_l50_constant_decay_is_ln2_over_delta():
    assert ts.life_half(0.1, 0.0, 1.0) == pytest.approx(math.log(2) / 0.1)


def test_l50_age_varying_hits_half():
    life = ts.life_half(0.05, 0.6, 1.0)
    assert math.exp(-ts.cumulative_hazard(life, 0.05, 0.6, 1.0)) == pytest.approx(0.5)


def test_lopex_constant_decay_hand_value():
    # R0 = $2.00/h, opex = $0.25/h, delta = 0.2: ln(8)/0.2 = 10.397 years
    assert ts.life_opex(2.0, 0.25, 0.2, 0.0, 1.0) == pytest.approx(math.log(8) / 0.2)


def test_lopex_opex_above_rent_is_zero():
    assert ts.life_opex(1.0, 1.5, 0.2, 0.0, 1.0) == 0.0


def test_lives_infinite_when_no_decay():
    assert math.isinf(ts.life_half(0.0, 0.0, 1.0))
    # beta0 = 0 with a decaying early term plateaus at exp(-beta1*tau) and may never reach half.
    assert math.isinf(ts.life_half(0.0, 0.3, 1.0))  # floor exp(-0.3) = 0.74 > 0.5
