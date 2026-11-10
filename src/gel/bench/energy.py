"""Energy over a benchmark window, integrated from the ~1 Hz nvidia-smi power log.

Board power only: nvidia-smi's power.draw excludes host CPU, memory, fans and facility overhead.
PUE is applied later, in metrics.energy_cost_per_mtok, and the paper says so.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DEFAULT_MAX_GAP_S = 2.5


@dataclass(frozen=True)
class WindowEnergy:
    joules: float
    mean_watts: float
    n_samples: int
    max_gap_s: float
    covered: bool


def integrate_window(
    t_ms, power_w, start_ms: float, end_ms: float, max_gap_s: float = DEFAULT_MAX_GAP_S
) -> WindowEnergy:
    """Trapezoidal integral of power over [start_ms, end_ms], in joules.

    Power at the window edges is linearly interpolated from neighbouring samples. A window is
    `covered` only if samples exist on or beyond both edges and no gap between consecutive
    samples inside it exceeds `max_gap_s`. An unspanned window returns NaN energy; a window with
    a long gap is still integrated but flagged.
    """
    t = np.asarray(t_ms, dtype=float)
    p = np.asarray(power_w, dtype=float)
    ok = np.isfinite(t) & np.isfinite(p)
    t, p = t[ok], p[ok]
    order = np.argsort(t, kind="stable")
    t, p = t[order], p[order]

    if end_ms <= start_ms or len(t) < 2 or t[0] > start_ms or t[-1] < end_ms:
        return WindowEnergy(math.nan, math.nan, int(len(t)), math.nan, False)

    inside = (t > start_ms) & (t < end_ms)
    grid = np.concatenate(([start_ms], t[inside], [end_ms]))
    vals = np.interp(grid, t, p)
    seconds = grid / 1000.0
    joules = float(np.trapezoid(vals, seconds))
    duration = (end_ms - start_ms) / 1000.0

    # Gaps are measured between real samples that bracket or fall inside the window.
    lo = max(int(np.searchsorted(t, start_ms, side="right")) - 1, 0)
    hi = min(int(np.searchsorted(t, end_ms, side="left")), len(t) - 1)
    real = t[lo : hi + 1] / 1000.0
    max_gap = float(np.max(np.diff(real))) if len(real) > 1 else math.nan
    covered = bool(np.isfinite(max_gap) and max_gap <= max_gap_s)

    return WindowEnergy(joules, joules / duration, int(inside.sum()), max_gap, covered)
