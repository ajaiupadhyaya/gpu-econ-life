"""P3 market calibration: OU fitting and markup arithmetic (Decision 12)."""

import numpy as np
import pytest

from gel.models import p3_market_calibration as mc
from gel.models import retirement_model as rm


def test_ou_fit_recovers_known_parameters():
    rng = np.random.default_rng(0)
    x = rm.ou_path(rng, n=1, months=60_000, x0=0.5, mean=0.5, kappa=2.0, sigma=0.3, floor=-9)[0]
    mean, kappa, sigma = mc.ou_fit(x)
    assert mean == pytest.approx(0.5, abs=0.02)
    assert kappa == pytest.approx(2.0, rel=0.1)
    assert sigma == pytest.approx(0.3, rel=0.05)


def test_ou_fit_hand_case_no_noise():
    # x_{t+1} = 1 + 0.5 (x_t - 1) exactly: phi = 0.5 = 1 - kappa/12 -> kappa = 6, sigma = 0
    x = [3.0]
    for _ in range(20):
        x.append(1 + 0.5 * (x[-1] - 1))
    mean, kappa, sigma = mc.ou_fit(np.array(x))
    assert mean == pytest.approx(1.0)
    assert kappa == pytest.approx(6.0)
    assert sigma == pytest.approx(0.0, abs=1e-9)


def test_cost_per_sold_hour_hand_case():
    # K $33,600, r 8%, n 60 -> A = 676.81/month (annuity). opex at e $0.08, PUE 1.3,
    # w 549 W, idle 118 W, u 0.7: kWh = 730 (0.7*549 + 0.3*118)/1000 = 306.38 -> $31.86;
    # maintenance 4%: 112.00. Total 820.67 / (730 * 0.7) = $1.6060 per sold GPU-hour.
    c = mc.cost_per_sold_hour(
        K=33_600, r=0.08, n=60, e=0.08, pue=1.3, w_load=549, w_idle=118, u=0.7, maint_frac=0.04
    )
    a = rm.annuity_payment(33_600, 0.08, 60)
    opex = 0.08 * 1.3 * 730 * (0.7 * 549 + 0.3 * 118) / 1000 + 0.04 * 33_600 / 12
    assert c == pytest.approx((a + opex) / (730 * 0.7))
    assert c == pytest.approx(1.6060, abs=1e-3)


def test_markup_from_price():
    assert mc.markup(3.23, 1.615) == pytest.approx(1.0, abs=1e-3)


def test_deseasonalize_removes_month_means():
    months = np.tile(np.arange(1, 13), 5)
    x = np.sin(months / 12 * 2 * np.pi) + 2.0
    d = mc.deseasonalize(x, months)
    assert np.allclose(d, d.mean())
