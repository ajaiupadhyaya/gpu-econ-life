"""P2: decay rates implied by the rental term structure.

Specification: docs/handoff_extension.md section 4.2. Time is in years, rates are annual and
continuously compounded.

A flat contract rate F for tenor T is compared with the launch (or current spot) rent R0.
Expected spot rent follows R(t) = R0 * exp(-H(t)), where H is the cumulative decay.

Level 1  constant decay, no discounting      F/R0 = (1 - e^(-dT)) / (dT)
Level 2  constant decay, discount rate r     F/R0 = a(r + d, T) / a(r, T)
                                             a(x, T) = (1 - e^(-xT)) / x
Level 3  term premium pi per year            (F/R0)_obs = (F/R0)_model * (1 - pi*T)
Level 4  age-varying decay                   d(s) = b0 + b1 * exp(-s / tau)
                                             H(t) = b0*t + b1*tau*(1 - exp(-t/tau))
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate, optimize

DELTA_BRACKET = (1e-6, 5.0)
TAU_BOUNDS = (0.25, 5.0)


def annuity(x: float, tenor: float) -> float:
    """Integral of exp(-x t) over [0, T]. Equals T in the limit x -> 0."""
    xt = x * tenor
    if abs(xt) < 1e-8:
        return tenor * (1.0 - xt / 2.0)
    return -math.expm1(-xt) / x


def flat_ratio(delta: float, tenor: float, r: float = 0.0) -> float:
    """Model F/R0 under constant decay (Level 1 when r = 0, Level 2 otherwise)."""
    return annuity(r + delta, tenor) / annuity(r, tenor)


@dataclass(frozen=True)
class DeltaSolution:
    delta: float
    reason: str = ""


def solve_delta(ratio: float, tenor: float, r: float = 0.0, pi: float = 0.0) -> DeltaSolution:
    """Invert an observed F/R0 for constant delta, with discount rate r and term premium pi.

    Returns NaN with a reason when no delta in DELTA_BRACKET fits. Values are never clipped.
    """
    if not (ratio > 0 and tenor > 0):
        return DeltaSolution(math.nan, "ratio and tenor must be positive")
    premium_factor = 1.0 - pi * tenor
    if premium_factor <= 0:
        return DeltaSolution(math.nan, f"term premium pi*T = {pi * tenor:.3f} >= 1")
    target = ratio / premium_factor
    lo, hi = DELTA_BRACKET

    def f(d: float) -> float:
        return flat_ratio(d, tenor, r) - target

    f_lo, f_hi = f(lo), f(hi)
    if f_lo <= 0:
        return DeltaSolution(
            math.nan, f"adjusted ratio {target:.4f} implies non-positive decay (rents not falling)"
        )
    if f_hi >= 0:
        return DeltaSolution(math.nan, f"adjusted ratio {target:.4f} implies decay above {hi}/yr")
    return DeltaSolution(optimize.brentq(f, lo, hi, xtol=1e-12, rtol=1e-12))


def implied_delta(ratio: float, tenor: float, r: float = 0.0, pi: float = 0.0) -> float:
    return solve_delta(ratio, tenor, r, pi).delta


# ---- Level 4 ------------------------------------------------------------------------------------


def cumulative_hazard(t, beta0: float, beta1: float, tau: float):
    """H(t) for d(s) = beta0 + beta1 * exp(-s / tau). Works on scalars and arrays."""
    t = np.asarray(t, dtype=float)
    out = beta0 * t + beta1 * tau * (-np.expm1(-t / tau))
    return float(out) if out.ndim == 0 else out


def flat_ratio_age_varying(
    tenor: float, beta0: float, beta1: float, tau: float, r: float = 0.0
) -> float:
    """Model F/R0 for a tenor-T contract when decay varies with age."""

    def integrand(t: float) -> float:
        return math.exp(-r * t - cumulative_hazard(t, beta0, beta1, tau))

    num, _ = integrate.quad(integrand, 0.0, tenor, epsabs=1e-13, epsrel=1e-12)
    return num / annuity(r, tenor)


@dataclass(frozen=True)
class DecayFit:
    level: int
    beta0: float
    beta1: float
    tau: float
    rmse: float
    n_tenors: int
    note: str = ""


def fit_age_varying(tenors, ratios, r: float = 0.0, pi: float = 0.0) -> DecayFit:
    """Least-squares fit of (beta0, beta1, tau) across tenors for one generation.

    Constraints: beta0 >= 0, beta0 + beta1 >= 0, tau in TAU_BOUNDS. The sum constraint is imposed
    by fitting s = beta0 + beta1 >= 0 directly. With fewer than three tenors, falls back to a
    constant-delta (Level 2) fit and says so in `note`.
    """
    tenors = np.asarray(tenors, dtype=float)
    ratios = np.asarray(ratios, dtype=float)
    keep = np.isfinite(tenors) & np.isfinite(ratios)
    tenors, ratios = tenors[keep], ratios[keep]
    if np.any(1.0 - pi * tenors <= 0):
        raise ValueError("term premium pi*T >= 1 for at least one tenor")
    targets = ratios / (1.0 - pi * tenors)
    n = len(tenors)

    if n < 3:
        if n == 0:
            return DecayFit(2, math.nan, 0.0, math.nan, math.nan, 0, "no tenors")

        def resid2(p):
            return [flat_ratio(p[0], t, r) - y for t, y in zip(tenors, targets, strict=True)]

        sol = optimize.least_squares(resid2, x0=[0.2], bounds=([0.0], [DELTA_BRACKET[1]]))
        rmse = float(np.sqrt(np.mean(np.square(sol.fun))))
        return DecayFit(
            2,
            float(sol.x[0]),
            0.0,
            math.nan,
            rmse,
            n,
            f"fewer than 3 tenors ({n}); Level 2 constant decay only",
        )

    def resid4(p):
        b0, s, tau = p
        return [
            flat_ratio_age_varying(t, b0, s - b0, tau, r) - y
            for t, y in zip(tenors, targets, strict=True)
        ]

    lower = [0.0, 0.0, TAU_BOUNDS[0]]
    upper = [DELTA_BRACKET[1], 2 * DELTA_BRACKET[1], TAU_BOUNDS[1]]
    best = None
    # A few starts, because tau is weakly identified when early and late decay look alike.
    for x0 in ([0.1, 0.3, 1.0], [0.05, 0.8, 0.5], [0.2, 0.2, 3.0]):
        sol = optimize.least_squares(
            resid4, x0=x0, bounds=(lower, upper), xtol=1e-14, ftol=1e-14, gtol=1e-14
        )
        if best is None or sol.cost < best.cost:
            best = sol
    b0, s, tau = (float(v) for v in best.x)
    rmse = float(np.sqrt(np.mean(np.square(best.fun))))
    return DecayFit(4, b0, s - b0, tau, rmse, n)


# ---- Implied economic lives ---------------------------------------------------------------------


def _age_where_hazard_reaches(level: float, beta0: float, beta1: float, tau: float) -> float:
    """Smallest t >= 0 with H(t) = level. Infinite if H never gets there."""
    if level <= 0:
        return 0.0
    if beta0 <= 0:
        plateau = beta1 * tau if beta1 > 0 else 0.0
        if plateau <= level:
            return math.inf
    hi = 1.0
    while cumulative_hazard(hi, beta0, beta1, tau) < level:
        hi *= 2.0
        if hi > 1e6:
            return math.inf
    return optimize.brentq(
        lambda t: cumulative_hazard(t, beta0, beta1, tau) - level, 0.0, hi, xtol=1e-12
    )


def life_half(beta0: float, beta1: float, tau: float) -> float:
    """L_50: age at which expected rent falls to half of launch rent (years)."""
    return _age_where_hazard_reaches(math.log(2.0), beta0, beta1, tau)


def life_opex(rent0: float, opex_per_hour: float, beta0: float, beta1: float, tau: float) -> float:
    """L_opex: age at which expected rent falls below operating cost per GPU-hour (years)."""
    if opex_per_hour >= rent0:
        return 0.0
    if opex_per_hour <= 0:
        return math.inf
    return _age_where_hazard_reaches(math.log(rent0 / opex_per_hour), beta0, beta1, tau)
