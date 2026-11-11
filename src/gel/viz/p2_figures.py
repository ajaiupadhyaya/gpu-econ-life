"""P2 figures (handoff 4.4), drawn by gel.models.p2_term.render().

Fig P2-a  observed F/R0 vs tenor, one series per chip, fitted constant-delta curves (r 8%, pi 0);
          neocloud and hyperscaler panels share the y axis
Fig P2-b  implied decay rate delta(age) by chip: Level 4 curves where three tenors exist,
          constant delta otherwise
Fig P2-c  implied L_opex (years) over the (r, pi) grid for the H100, neocloud and hyperscaler
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from matplotlib.colors import LinearSegmentedColormap

from gel.models import term_structure as ts
from gel.viz import style

FIGURES = Path("paper/figures")
NAMES = {
    "a100_80gb": "A100 80GB",
    "h100_sxm": "H100 SXM",
    "h200": "H200 SXM",
    "l40s": "L40S",
    "b200": "B200",
}
CHIP_COLOR = {
    "a100_80gb": style.COLOR["A100_SXM"],
    "h100_sxm": style.COLOR["H100_SXM"],
    "h200": style.COLOR["H200_SXM"],
    "l40s": style.COLOR["L40S"],
    "b200": style.SLOTS[5],
}


def fig_a(obs: pl.DataFrame, table: pl.DataFrame) -> None:
    base = table.filter((pl.col("r") == 0.08) & (pl.col("pi") == 0.0))
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.8), sharey=True)
    grid = np.linspace(1, 62, 120)
    for ax, ptype in zip(axes, ("neocloud", "hyperscaler"), strict=True):
        labels = []
        for chip in NAMES:
            o = obs.filter((pl.col("chip") == chip) & (pl.col("provider_type") == ptype))
            if o.is_empty():
                continue
            c = CHIP_COLOR[chip]
            ax.plot(
                o["term_months"], o["observed_ratio"], "o", color=c, markersize=7, label=NAMES[chip]
            )
            d = base.filter((pl.col("chip") == chip) & (pl.col("provider_type") == ptype))
            delta = d["delta"][0] if not d.is_empty() else math.nan
            if delta == delta:
                ax.plot(
                    grid,
                    [ts.flat_ratio(delta, t / 12, 0.08) for t in grid],
                    color=c,
                    lw=1.5,
                    alpha=0.8,
                )
                last = o.sort("term_months").tail(1).row(0, named=True)
                labels.append(
                    [
                        last["observed_ratio"],
                        last["term_months"],
                        last["observed_ratio"],
                        f"{NAMES[chip]}  δ={delta:.2f}",
                    ]
                )
        labels.sort()
        for i in range(1, len(labels)):  # >= 0.045 apart on the ratio axis (~one text line)
            if labels[i][1] == labels[i - 1][1]:
                labels[i][0] = max(labels[i][0], labels[i - 1][0] + 0.045)
        for ly, x, y, text in labels:
            ax.annotate(
                text,
                (x, y),
                xytext=(x + 2.5, ly),
                textcoords="data",
                va="center",
                fontsize=7,
                color=style.INK,
            )
        ax.set_title(f"{ptype.capitalize()}s", fontsize=9)
        ax.set_xlabel("Contract tenor (months)")
        ax.set_xticks([12, 36, 60])
        ax.set_xlim(0, 85)
        ax.set_ylim(0, 1.15)
        ax.axhline(1.0, color=style.INK_2, lw=0.8, ls=":")
    axes[0].set_ylabel("Reserved / on-demand price (F/R0)")
    fig.suptitle(
        "P2-a  Observed term ratios and fitted constant decay (r = 8%, π = 0)",
        fontsize=10,
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(FIGURES / "p2a_term_ratios.png")
    plt.close(fig)


def fig_b(table: pl.DataFrame, l4: pl.DataFrame) -> None:
    base = table.filter((pl.col("r") == 0.08) & (pl.col("pi") == 0.0))
    s = np.linspace(0, 8, 160)
    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    for r in base.iter_rows(named=True):
        if not math.isfinite(r["delta"]):
            continue
        ls = "-" if r["provider_type"] == "neocloud" else "--"
        lv = (
            l4.filter(
                (pl.col("chip") == r["chip"]) & (pl.col("provider_type") == r["provider_type"])
            )
            if l4.height
            else l4
        )
        if lv.height and lv["level"][0] == 4:
            row = lv.row(0, named=True)
            y = row["beta0"] + row["beta1"] * np.exp(-s / row["tau"])
            tag = "Level 4"
        else:
            y = np.full_like(s, r["delta"])
            tag = "constant"
        ax.plot(
            s,
            y,
            ls=ls,
            color=CHIP_COLOR[r["chip"]],
            label=f"{NAMES[r['chip']]} ({r['provider_type']}, {tag})",
        )
    ax.set_xlabel("Age (years)")
    ax.set_ylabel("Implied decay rate δ (per year)")
    ax.set_title("P2-b  Implied decay by generation (r = 8%, π = 0)")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    fig.tight_layout()
    fig.savefig(FIGURES / "p2b_decay_by_age.png", bbox_inches="tight")
    plt.close(fig)


def fig_c(table: pl.DataFrame, chip: str = "h100_sxm") -> None:
    cmap = LinearSegmentedColormap.from_list("seq_blue", style.SEQ)
    sub = table.filter(pl.col("chip") == chip)
    ptypes = [p for p in ("neocloud", "hyperscaler") if p in sub["provider_type"].to_list()]
    vals = sub.filter(pl.col("L_opex_y").is_finite())["L_opex_y"]
    vmin, vmax = (float(vals.min()), float(vals.max())) if len(vals) else (0, 1)
    fig, axes = plt.subplots(
        1,
        len(ptypes),
        figsize=(3.6 * len(ptypes) + 1.0, 3.6),
        squeeze=False,
        sharey=True,
        layout="constrained",
    )
    rs = sorted(sub["r"].unique().to_list())
    pis = sorted(sub["pi"].unique().to_list())
    im = None
    for ax, ptype in zip(axes[0], ptypes, strict=True):
        m = np.full((len(rs), len(pis)), np.nan)
        for row in sub.filter(pl.col("provider_type") == ptype).iter_rows(named=True):
            m[rs.index(row["r"]), pis.index(row["pi"])] = row["L_opex_y"]
        im = ax.imshow(m, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto", origin="lower")
        for i in range(len(rs)):
            for j in range(len(pis)):
                v = m[i, j]
                txt = "n/a" if not np.isfinite(v) else f"{v:.1f}"
                dark = np.isfinite(v) and (v - vmin) / max(vmax - vmin, 1e-9) > 0.35
                ax.text(
                    j,
                    i,
                    txt,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#ffffff" if dark else style.INK,
                )
        ax.set_xticks(range(len(pis)), [f"{p:.0%}" for p in pis])
        ax.set_yticks(range(len(rs)), [f"{r:.0%}" for r in rs])
        ax.set_xlabel("Term premium π (per year)")
        if ax is axes[0][0]:
            ax.set_ylabel("Discount rate r")
        ax.set_title(f"{NAMES[chip]}, {ptype}s", fontsize=9)
        ax.grid(False)
    if im is not None:
        fig.colorbar(im, ax=axes[0].tolist(), label="L_opex (years since release)")
    fig.suptitle("P2-c  Implied economic life to operating cost", fontsize=10, fontweight="bold")
    fig.savefig(FIGURES / "p2c_lopex_heatmap.png", bbox_inches="tight")
    plt.close(fig)


def render(obs: pl.DataFrame, table: pl.DataFrame, l4: pl.DataFrame) -> None:
    style.apply()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig_a(obs, table)
    fig_b(table, l4)
    fig_c(table)
