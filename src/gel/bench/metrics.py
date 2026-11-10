"""P1 metrics. Formulas from docs/handoff_extension.md section 3.5."""

from __future__ import annotations

import math

J_PER_KWH = 3.6e6


def cost_per_mtok(price_per_hr: float, tokens_per_s: float) -> float:
    """Rental cost per million output tokens: price / (q * 3600) * 1e6."""
    if not tokens_per_s > 0:
        return math.nan
    return price_per_hr / (tokens_per_s * 3600.0) * 1e6


def tokens_per_joule(tokens: float, joules: float) -> float:
    if not joules > 0:
        return math.nan
    return tokens / joules


def energy_cost_per_mtok(joules: float, tokens: float, price_kwh: float, pue: float) -> float:
    """Electricity cost per million output tokens: (E/tokens) * 1e6 / 3.6e6 * price * PUE."""
    if not tokens > 0:
        return math.nan
    return (joules / tokens) * 1e6 / J_PER_KWH * price_kwh * pue


def obsolescence_discount(price_g: float, price_f: float, q_g: float, q_f: float) -> float:
    """D_g = (P_g / P_f) / (q_g / q_f) - 1, relative to frontier GPU f at matched concurrency.

    D < 0: the old chip is priced below what its output alone would justify.
    D > 0: the old chip carries a premium (scarcity, availability, flexibility).
    """
    if not (price_f > 0 and q_g > 0 and q_f > 0):
        return math.nan
    return (price_g / price_f) / (q_g / q_f) - 1.0
