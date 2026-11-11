"""Fig T-1: per generation, the P1, P2 and P3 life intervals beside the accounting lives.

Rows are generations. Each method is an interval on the same years axis: P1-implied L_opex
(provider price min-median-max), P2 L_opex (r x pi grid, both provider types), P3 retirement age
P10-P90 with the median dot and markers for the always-constrained and power-abundant medians.
Vertical lines mark the 4, 5, 5.5 and 6-year accounting lives.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

from gel.viz import style

FIGURES = Path("paper/figures")
METHODS = [
    ("P1  cross-section: life to opex", style.SLOTS[0]),
    ("P2  term structure: life to opex", style.SLOTS[1]),
    ("P3  retirement model (base)", style.SLOTS[2]),
]


def render(tri: pl.DataFrame) -> None:
    style.apply()
    FIGURES.mkdir(parents=True, exist_ok=True)
    rows = tri.to_dicts()
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    gap = 0.24
    yticks, ylabels = [], []
    for i, r in enumerate(rows[::-1]):
        y0 = i * 1.2
        yticks.append(y0)
        ylabels.append(f"{r['generation']}\n(age {r['age_now_y']:.1f} y)")
        intervals = [
            (r["p1_Lopex_low"], r["p1_Lopex_high"], None),
            (r["p2_Lopex_low"], r["p2_Lopex_high"], None),
            (r["p3_p10"], r["p3_p90"], r["p3_median"]),
        ]
        for j, ((lo, hi, mid), (_, color)) in enumerate(zip(intervals, METHODS, strict=True)):
            y = y0 + (1 - j) * gap
            if lo == lo and hi == hi:
                ax.plot([lo, hi], [y, y], color=color, lw=6, solid_capstyle="round", alpha=0.85)
            if mid is not None:
                ax.plot(
                    mid,
                    y,
                    "o",
                    color="#ffffff",
                    markersize=6,
                    markeredgecolor=color,
                    markeredgewidth=2,
                    zorder=4,
                )
                ax.plot(
                    r["p3_constrained_median"],
                    y,
                    "|",
                    color=style.INK,
                    markersize=11,
                    markeredgewidth=2,
                    zorder=4,
                )
                ax.plot(
                    r["p3_abundant_median"],
                    y,
                    "|",
                    color=style.INK,
                    markersize=11,
                    markeredgewidth=2,
                    zorder=4,
                )
    ax.axvspan(4.0, 6.0, color=style.GRID, alpha=0.6, zorder=0)
    for life in (4.0, 5.0, 5.5, 6.0):
        ax.axvline(life, color=style.INK_2, lw=0.8, ls=(0, (3, 3)), zorder=1)
    ax.annotate(
        "accounting lives\n4 / 5 / 5.5 / 6 y",
        (5.0, yticks[-1] + 0.5),
        ha="center",
        fontsize=7,
        color=style.INK_2,
        bbox={"boxstyle": "round,pad=0.25", "fc": style.SURFACE, "ec": "none"},
    )
    for label, color in METHODS:
        ax.plot([], [], color=color, lw=6, label=label)
    ax.plot(
        [],
        [],
        "o",
        color="#ffffff",
        markeredgecolor=style.INK,
        markeredgewidth=2,
        label="P3 median (bar: P10-P90)",
    )
    ax.plot(
        [],
        [],
        "|",
        color=style.INK,
        markersize=11,
        markeredgewidth=2,
        label="P3 always-constrained / power-abundant medians",
    )
    ax.set_yticks(yticks, ylabels, fontsize=8)
    ax.set_xlim(0, max(20, ax.get_xlim()[1]))
    ax.set_ylim(-0.5, yticks[-1] + 0.95)
    ax.set_xlabel("Economic life (years since release)")
    ax.set_title("T-1  Three estimates of GPU economic life vs accounting lives (dashed)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=2, fontsize=7.5)
    fig.tight_layout()
    fig.savefig(FIGURES / "t1_triangulation.png", bbox_inches="tight")
    plt.close(fig)
