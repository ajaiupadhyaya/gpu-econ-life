"""P3: power-constrained retirement model, building blocks.

Specification: docs/handoff_extension.md section 5, with Decision 8 (idle draw is charged).
Time is in months. All functions are vectorised over Monte Carlo paths (axis 0).

A data-centre GPU is rarely retired because it breaks. It is evicted when the power slot it
occupies would earn more running a newer chip (power-constrained regime), or when it stops
covering its own operating cost (unconstrained regime). Physical failure is a third channel.
"""

from __future__ import annotations

import numpy as np

HOURS_PER_MONTH = 730.0
SECONDS_PER_HOUR = 3600.0


# ---- finance ----


def monthly_rate(r_annual: float) -> float:
    return (1.0 + r_annual) ** (1.0 / 12.0) - 1.0


def annuity_payment(capex: float, r_annual: float, n_months: int) -> float:
    """Monthly payment that amortises `capex` over `n_months`: K r / (1 - (1+r)^-n)."""
    r = monthly_rate(r_annual)
    if r == 0:
        return capex / n_months
    return capex * r / (1.0 - (1.0 + r) ** -n_months)


# ---- monthly economics (Decision 8) ----


def monthly_economics(p, q, u, e, w_load, w_idle, pue, maint):
    """Revenue, opex and margin per GPU-month.

    p      token price, $/token          q       throughput at the operating point, tokens/s
    u      utilisation (share of hours sold)
    e      electricity, $/kWh            w_load / w_idle   board power, W
    pue    facility overhead multiplier   maint   $/GPU-month
    """
    revenue = p * q * SECONDS_PER_HOUR * HOURS_PER_MONTH * u
    kwh = HOURS_PER_MONTH * (w_load * u + w_idle * (1.0 - u)) / 1000.0
    opex = e * pue * kwh + maint
    return revenue, opex, revenue - opex


def obsolete_in_power_slot(margin_g, w_g, margin_f, annuity_f, w_f):
    """Constrained rule: evict g if its margin per kW is below what the frontier chip would earn
    per kW in the same slot after paying for itself: Margin_g/w_g < (Margin_f - A_f)/w_f."""
    return margin_g / (w_g / 1000.0) < (margin_f - annuity_f) / (w_f / 1000.0)


# ---- retirement timing ----


def first_sustained(cond: np.ndarray, start: np.ndarray, hold: int) -> np.ndarray:
    """First month t >= start at which `cond` has held for `hold` consecutive months (counting
    from start), i.e. the month the decision is taken. -1 if never. cond: (n, months) bool."""
    n, months = cond.shape
    run = np.zeros(n, dtype=np.int64)
    out = np.full(n, -1, dtype=np.int64)
    for t in range(months):
        active = (t >= start) & (out < 0)
        run = np.where(active & cond[:, t], run + 1, 0)
        hit = active & (run >= hold)
        out[hit] = t
    return out


# ---- stochastic processes ----


def ou_path(rng, n, months, x0, mean, kappa, sigma, floor, dt=1.0 / 12.0):
    """Euler-discretised Ornstein-Uhlenbeck path, floored. Parameters are annual."""
    x = np.empty((n, months))
    x[:, 0] = x0
    shocks = rng.standard_normal((n, months - 1))
    for t in range(1, months):
        nxt = (
            x[:, t - 1] + kappa * (mean - x[:, t - 1]) * dt + sigma * np.sqrt(dt) * shocks[:, t - 1]
        )
        x[:, t] = np.maximum(nxt, floor)
    return x


def markov_regime(rng, n, months, p_stay_constrained, p_stay_unconstrained, start_constrained=True):
    """Two-state monthly Markov chain. True = power-constrained."""
    s = np.empty((n, months), dtype=bool)
    s[:, 0] = start_constrained
    u = rng.random((n, months - 1))
    for t in range(1, months):
        stay = np.where(s[:, t - 1], p_stay_constrained, p_stay_unconstrained)
        s[:, t] = np.where(u[:, t - 1] < stay, s[:, t - 1], ~s[:, t - 1])
    return s


def weibull_failure_month(rng, size, scale_months, shape):
    """Age (whole months, >= 1) at which a chip physically fails."""
    x = scale_months * (-np.log(rng.random(size))) ** (1.0 / shape)
    return np.maximum(np.ceil(x), 1).astype(np.int64)


# ---- economic value ----


def value_by_age(margins_by_age: np.ndarray, alive_by_age: np.ndarray, r_annual: float, ages):
    """V(a) = E[ sum_{s>=a} Margin(s) (1+r_m)^-(s-a) | alive at a ].

    margins_by_age, alive_by_age: (n, A) arrays indexed by age in months. Margins after
    retirement are excluded (alive mask). Returns {age: value}; NaN where no path is alive.
    """
    r = monthly_rate(r_annual)
    m = np.where(alive_by_age, margins_by_age, 0.0)
    a_max = m.shape[1]
    out = {}
    for a in ages:
        if a >= a_max:
            out[a] = float("nan")
            continue
        disc = (1.0 + r) ** -np.arange(a_max - a)
        pv = (m[:, a:] * disc).sum(axis=1)
        alive = alive_by_age[:, a]
        out[a] = float(pv[alive].mean()) if alive.any() else float("nan")
    return out
