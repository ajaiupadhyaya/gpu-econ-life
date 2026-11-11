"""M8 triangulation helpers: blended fleet life and the cross-sectional rent-age slope."""

import math

import pytest

from gel.models import triangulate as tr


def test_blended_life_hand_case():
    # s = 0.5, L_gpu = 4, L_other = 6: 1 / (0.5/4 + 0.5/6) = 1 / 0.208333 = 4.8
    assert tr.blended_life(0.5, 4.0, 6.0) == pytest.approx(4.8)
    assert tr.blended_life(1.0, 4.0, 6.0) == pytest.approx(4.0)
    assert tr.blended_life(0.0, 4.0, 7.0) == pytest.approx(7.0)


def test_cross_section_slope_hand_case():
    # rent halves every 2 years of age: ln P = c - (ln 2 / 2) * age -> delta = 0.3466
    ages = [2.0, 4.0, 6.0]
    prices = [8.0, 4.0, 2.0]
    assert tr.cross_section_delta(ages, prices) == pytest.approx(math.log(2) / 2)


def test_cross_section_slope_rising_rents_is_nan():
    assert math.isnan(tr.cross_section_delta([2.0, 4.0], [3.0, 4.0]))


def test_markup_share_of_rent():
    # m = 0.9: rent = cost x 1.9, so 0.9 / 1.9 = 47.4% of rent is markup
    assert tr.markup_share(0.9) == pytest.approx(0.9 / 1.9)
