"""P2 implied-decay table: multi-tenor constant-delta fit and remaining-life arithmetic."""

import math

import pytest

from gel.models import p2_term
from gel.models import term_structure as ts


def test_single_tenor_fit_equals_inversion():
    d = p2_term.fit_constant_delta([36], [0.8], r=0.08, pi=0.0)
    assert d == pytest.approx(ts.implied_delta(0.8, 3.0, r=0.08), rel=1e-6)


def test_multi_tenor_fit_recovers_common_delta():
    ratios = [ts.flat_ratio(0.2, t / 12, r=0.08) for t in (12, 36, 60)]
    assert p2_term.fit_constant_delta([12, 36, 60], ratios, r=0.08, pi=0.0) == pytest.approx(
        0.2, rel=1e-6
    )


def test_premium_lowers_fitted_delta():
    base = p2_term.fit_constant_delta([12, 36], [0.85, 0.6], r=0.08, pi=0.0)
    prem = p2_term.fit_constant_delta([12, 36], [0.85, 0.6], r=0.08, pi=0.03)
    assert prem < base


def test_ratios_above_one_give_nan():
    assert math.isnan(p2_term.fit_constant_delta([12], [1.05], r=0.08, pi=0.0))


def test_remaining_life_to_opex_hand_case():
    # rent today $4.50/h, opex $0.25/h, delta 0.3/yr, age 4.1 y: 4.1 + ln(18)/0.3 = 13.73 y
    assert p2_term.life_opex_from_now(4.50, 0.25, 0.3, 4.1) == pytest.approx(
        4.1 + math.log(18) / 0.3
    )
    assert p2_term.life_opex_from_now(0.2, 0.25, 0.3, 4.1) == pytest.approx(4.1)  # already below
