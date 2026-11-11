"""Phase 5 figures and LaTeX tables from paper/tables/p5_*.csv (Decision 23).

Fig 5a  observed cohort paths by chip (no month effects), all months and pre-2026
Fig 5b  age profiles from the strategies that identify a linear term (1a, 1b, 2), with
        chip-level wild-cluster-bootstrap 95% bands
Fig 5c  strategy 4: the same curvature under assumed linear terms d = 0 ... -0.40 per year
Fig 5d  successor event study (H2): event-time coefficients with 95% bands

Tables: paper/tables/p5_strategies.tex (headline), p5_h3_h4.tex (by contract and period).

Usage: uv run python -m gel.viz.hedonic_figures
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import polars as pl

from gel.viz import panel_figures as pf
from gel.viz import style

TABLES = Path("paper/tables")
FIGURES = Path("paper/figures")
SPEC_LABEL = {
    "s1a_tflops": "1a quality index (TFLOP/s)",
    "s1b_three_specs": "1b three specs",
    "s2_frontier": "2 frontier-relative",
    "s4_shape": "4 shape only",
}
SPEC_COLOR = {
    "s1a_tflops": style.SLOTS[0],
    "s1b_three_specs": style.SLOTS[1],
    "s2_frontier": style.SLOTS[2],
}
MEASURE_LABEL = {
    "d2": "$g(2)-g(0)$",
    "d4": "$g(4)-g(0)$",
    "rate_0_2": "rate, yrs 0--2",
    "rate_2_4": "rate, yrs 2--4",
    "early_minus_late_rate": "early $-$ late rate (H1: $<0$)",
}


def fig_a(paths: pl.DataFrame) -> None:
    chips = [c for c in pf.CHIPS if c in paths["chip"].unique().to_list()]
    fig, axes = pf._grid(len(chips))
    colors = {"all": style.SLOTS[0], "pre_2026": style.SLOTS[1]}
    for ax, chip in zip(axes, chips, strict=False):
        for sample, color in colors.items():
            d = paths.filter((pl.col("chip") == chip) & (pl.col("sample") == sample)).sort(
                "age_months_from"
            )
            if d.is_empty():
                continue
            first = d["first_bin_months_from"][0]
            x = [first / 12, *(d["age_months_from"] / 12).to_list()]
            y = [0.0, *d["estimate"].to_list()]
            lo = [0.0, *d["ci_low"].to_list()]
            hi = [0.0, *d["ci_high"].to_list()]
            ax.fill_between(x, lo, hi, color=color, alpha=0.15, linewidth=0)
            ax.plot(x, y, color=color, marker="o", markersize=2.5, label=sample.replace("_", " "))
        ax.axhline(0, color=style.INK_2, linewidth=0.8)
        ax.set_title(pf.CHIPS[chip])
    axes[0].set_ylabel("log price vs first bin")
    for ax in axes[max(0, len(chips) - 3) : len(chips)]:
        ax.set_xlabel("years since release")
    axes[0].legend(fontsize=7)
    pf._finish(
        fig,
        axes,
        len(chips),
        "p5a_cohort_paths.png",
        "Chip x 6-month age-bin effects with provider-region, contract, GPU-count, basis and form "
        "controls; no month effects. 95% bands: CR1 by provider-region.",
    )


def fig_b(profiles: pl.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    for spec, color in SPEC_COLOR.items():
        d = profiles.filter(pl.col("spec") == spec).sort("age")
        ax.fill_between(d["age"], d["ci_low"], d["ci_high"], color=color, alpha=0.12, linewidth=0)
        ax.plot(d["age"], d["g"], color=color, label=SPEC_LABEL[spec])
    ax.axhline(0, color=style.INK_2, linewidth=0.8)
    ax.set_xlabel("years since release")
    ax.set_ylabel("log price relative to age 0")
    ax.legend(fontsize=7, loc="lower left")
    fig.text(
        0.01,
        0.005,
        "95% bands: wild cluster bootstrap at the chip level (7 clusters, Webb).",
        fontsize=7,
        color=style.INK_2,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "p5b_strategy_profiles.png")
    plt.close(fig)


def fig_c(sweep: pl.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    deltas = sorted(sweep["delta"].unique().to_list(), reverse=True)
    for i, d in enumerate(deltas):
        s = sweep.filter(pl.col("delta") == d).sort("age")
        shade = style.SEQ[min(len(style.SEQ) - 1, i * len(style.SEQ) // len(deltas))]
        ax.plot(s["age"], s["g"], color=shade, linewidth=1.6)
        ax.annotate(
            f"{d:+.2f}",
            (s["age"][-1], s["g"][-1]),
            fontsize=6,
            color=style.INK_2,
            xytext=(3, 0),
            textcoords="offset points",
            va="center",
        )
    ax.axhline(0, color=style.INK_2, linewidth=0.8)
    ax.set_xlabel("years since release")
    ax.set_ylabel("log price relative to age 0")
    ax.set_xlim(0, 6.6)
    fig.text(
        0.01,
        0.005,
        "Strategy 4: estimated curvature, detrended over ages 0-6, plus an assumed "
        "average rate d per year (labels).",
        fontsize=7,
        color=style.INK_2,
    )
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / "p5c_strategy4_sweep.png")
    plt.close(fig)


def fig_d(ev: pl.DataFrame) -> None:
    order = ["ev_-18_-13", "ev_-12_-7", "ref", "ev_+0_+5", "ev_+6_+11", "ev_+12_+17"]
    mid = {
        "ev_-18_-13": -15.5,
        "ev_-12_-7": -9.5,
        "ref": -3.5,
        "ev_+0_+5": 2.5,
        "ev_+6_+11": 8.5,
        "ev_+12_+17": 14.5,
    }
    rows = {r["measure"]: r for r in ev.iter_rows(named=True)}
    xs, ys, lo, hi = [], [], [], []
    for k in order:
        xs.append(mid[k])
        if k == "ref":
            ys.append(0.0), lo.append(0.0), hi.append(0.0)
        else:
            r = rows[k]
            ys.append(r["estimate"]), lo.append(r["wcb_ci_low"]), hi.append(r["wcb_ci_high"])
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.fill_between(xs, lo, hi, color=style.SLOTS[0], alpha=0.15, linewidth=0)
    ax.plot(xs, ys, color=style.SLOTS[0], marker="o", markersize=5)
    ax.axhline(0, color=style.INK_2, linewidth=0.8)
    ax.axvline(0, color=style.INK_2, linewidth=0.8, linestyle=":")
    ax.set_xlabel("months relative to successor's release (bin midpoints)")
    ax.set_ylabel("log price vs months -6 to -1")
    fig.text(
        0.01,
        0.005,
        "Pooled: V100->A100, A100->H100, H100->B200. Chip and month effects, curvature, "
        "controls. 95%: chip-level wild bootstrap.",
        fontsize=7,
        color=style.INK_2,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIGURES / "p5d_event_study.png")
    plt.close(fig)


def _cell(r: dict) -> str:
    est = f"{r['estimate']:.2f}"
    return f"{est} [{r['wcb_ci_low']:.2f}, {r['wcb_ci_high']:.2f}]"


def latex_strategies(summary: pl.DataFrame) -> str:
    d = summary.filter(pl.col("sample") == "all")
    measures = list(MEASURE_LABEL)
    lines = [
        "% Generated by gel.viz.hedonic_figures from p5_summary.csv. Do not edit.",
        "\\begin{tabular}{l" + "c" * len(measures) + "}",
        "\\hline",
        "Strategy & " + " & ".join(MEASURE_LABEL[m] for m in measures) + " \\\\",
        "\\hline",
    ]
    for spec in SPEC_LABEL:
        cells = []
        for m in measures:
            hit = d.filter((pl.col("spec") == spec) & (pl.col("measure") == m))
            cells.append(_cell(hit.row(0, named=True)) if hit.height else "--")
        lines.append(f"{SPEC_LABEL[spec]} & " + " & ".join(cells) + " \\\\")
    lines += ["\\hline", "\\end{tabular}", ""]
    return "\n".join(lines)


def latex_h3_h4(summary: pl.DataFrame) -> str:
    samples = [s for s in summary["sample"].unique().sort().to_list() if s != "all"]
    lines = [
        "% Generated by gel.viz.hedonic_figures from p5_summary.csv. Do not edit.",
        "% Rates in log points per year; early - late = rate(0-2) - rate(2-4); H1 predicts < 0.",
        "\\begin{tabular}{llccc}",
        "\\hline",
        "Sample & Strategy & rate, yrs 0--2 & rate, yrs 2--4 & early $-$ late (H1: $<0$) \\\\",
        "\\hline",
    ]
    for smp in samples:
        for spec in ("s1a_tflops", "s2_frontier", "s4_shape"):
            row = []
            for m in ("rate_0_2", "rate_2_4", "early_minus_late_rate"):
                hit = summary.filter(
                    (pl.col("sample") == smp) & (pl.col("spec") == spec) & (pl.col("measure") == m)
                )
                if not hit.height:
                    row.append("--")
                    continue
                r = hit.row(0, named=True)
                mark = "$^\\dagger$" if r["extrapolated"] and m != "early_minus_late_rate" else ""
                row.append(_cell(r) + mark)
            lines.append(
                f"{smp.replace('_', ' ')} & {SPEC_LABEL[spec]} & " + " & ".join(row) + " \\\\"
            )
    lines += [
        "\\hline",
        "\\end{tabular}",
        "% dagger: within-chip age span under 4 years with chip effects (extrapolated).",
        "",
    ]
    return "\n".join(lines)


def run() -> None:
    style.apply()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig_a(pl.read_csv(TABLES / "p5_cohort_paths.csv"))
    fig_b(pl.read_csv(TABLES / "p5_profiles.csv"))
    fig_c(pl.read_csv(TABLES / "p5_strategy4_sweep.csv"))
    fig_d(pl.read_csv(TABLES / "p5_event_study.csv"))
    summary = pl.read_csv(TABLES / "p5_summary.csv")
    (TABLES / "p5_strategies.tex").write_text(latex_strategies(summary))
    (TABLES / "p5_h3_h4.tex").write_text(latex_h3_h4(summary))


def main() -> int:
    run()
    print("wrote paper/figures/p5a-d and paper/tables/p5_strategies.tex, p5_h3_h4.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
