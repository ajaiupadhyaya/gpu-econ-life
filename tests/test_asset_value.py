"""Phase 6 valuation core, checked by hand (Decision 25)."""

import numpy as np
import polars as pl
import pytest

from gel.models import asset_value as av


def test_opex_adds_power_and_maintenance():
    # 1 kW x 1.5 x $0.10 = $0.15/h; maintenance 4% of $8,760 per year = $0.04/h
    assert av.opex_per_hour(1.0, 1.5, 0.10, 8760.0, 0.04) == pytest.approx(0.19)


def test_constant_rent_value_is_a_discounted_annuity():
    rent = np.full(24, 2.0)  # two years of months
    v, t_star = av.value_path(rent, opex=0.5, u=0.5, r=0.0, h=0.0)
    # net = 730 * (0.5*2 - 0.5) = 365 per month, undiscounted
    assert v[0] == pytest.approx(365 * 24)
    assert v[12] == pytest.approx(365 * 12)
    assert v[-1] == 0.0
    assert np.isinf(t_star)


def test_net_rent_is_floored_and_t_star_found():
    rent = np.array([2.0] * 12 + [0.5] * 12)
    v, t_star = av.value_path(rent, opex=0.5, u=1.0, r=0.0, h=0.0)
    assert t_star == pytest.approx(1.0)
    assert v[12] == pytest.approx(0.0)  # no negative contributions after T*
    assert v[0] == pytest.approx(730 * 1.5 * 12)


def test_discounting_and_survival():
    rent = np.array([1.0])
    v, _ = av.value_path(rent, opex=0.0, u=1.0, r=0.10, h=0.0)
    assert v[0] == pytest.approx(730 / 1.10 ** (1 / 12))
    rent = np.ones(2)
    v_s, _ = av.value_path(rent, opex=0.0, u=1.0, r=0.0, h=0.12)
    assert v_s[0] == pytest.approx(730 + 730 * np.exp(-0.01))


def test_straight_line_equivalent_of_a_linear_decline():
    # value falling linearly from 1 to 0 over 5 years -> L = 5
    v = np.linspace(1.0, 0.0, 61)
    assert av.sl_equivalent_life(v) == pytest.approx(5.0, abs=1e-6)


def test_realized_profile_chain_links_increments():
    paths = pl.DataFrame(
        {
            "sample": ["all"] * 3,
            "chip": ["c1", "c1", "c2"],
            "age_months_from": [6, 12, 12],
            "first_bin_months_from": [0, 0, 6],
            "estimate": [-0.1, -0.3, -0.1],
        }
    )
    g = av.realized_profile(paths, ["c1", "c2"], 18)
    # bins 0,6,12: step 0->6 = -0.1 (c1); step 6->12 = mean(-0.2 c1, -0.1 c2) = -0.15
    assert g[3] == pytest.approx(0.0)
    assert g[9] == pytest.approx(-0.1)
    assert g[15] == pytest.approx(-0.25)
    assert g[18] == pytest.approx(-0.25)  # flat beyond the last midpoint
