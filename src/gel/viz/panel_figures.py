"""Phase 4 descriptive figures from data/processed/panel.parquet (Decision 22).

Fig 4a  median on-demand price per GPU-hour by chip over time, one line per provider type
Fig 4b  real (2025 USD) on-demand price against age since release, by chip, with a LOWESS fit
Fig 4c  price dispersion across providers per chip-month: max / min of provider medians
        (on-demand), where at least two providers list the chip
Fig 4d  our monthly median on-demand price against getdeploying.com's weekly ON_DEMAND median
        (CC BY 4.0), averaged by month; getdeploying pools A100 40/80GB and H100 SXM/PCIe

All panels are small multiples by chip, so no figure needs more than two hues. Each figure has a
CSV of its plotted values in paper/tables/.

Usage: uv run python -m gel.viz.panel_figures
"""

from __future__ import annotations

import glob
import sys
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import polars as pl
from statsmodels.nonparametric.smoothers_lowess import lowess

from gel.viz import style

PANEL = Path("data/processed/panel.parquet")
GETDEPLOYING_GLOB = "data/raw/indices/getdeploying/*/weekly.csv"
FIGURES = Path("paper/figures")
TABLES = Path("paper/tables")
CHIPS = {
    "v100": "V100",
    "a100_40gb": "A100 40GB",
    "a100_80gb": "A100 80GB",
    "h100_pcie": "H100 PCIe",
    "h100_sxm": "H100 SXM",
    "l40s": "L40S",
    "mi300x": "MI300X",
    "h200": "H200",
    "b200": "B200",
}
PTYPE_COLOR = {"hyperscaler": style.SLOTS[0], "neocloud": style.SLOTS[1]}
# getdeploying slug -> our chip ids pooled to match it
GD_SLUGS = {
    "nvidia-v100": ["v100"],
    "nvidia-a100": ["a100_40gb", "a100_80gb"],
    "nvidia-h100": ["h100_sxm", "h100_pcie"],
    "nvidia-l40s": ["l40s"],
    "amd-mi300x": ["mi300x"],
    "nvidia-h200": ["h200"],
    "nvidia-b200": ["b200"],
}


def on_demand(panel: pl.DataFrame) -> pl.DataFrame:
    return panel.filter((pl.col("contract_type") == "on_demand") & ~pl.col("price_outlier"))


def _grid(n: int, ncols: int = 3, h: float = 2.3, sharex: bool = False):
    nrows = -(-n // ncols)
    fig, axes = plt.subplots(nrows, ncols, figsize=(7.6, h * nrows), squeeze=False, sharex=sharex)
    return fig, axes.ravel()


def _date_axis(ax, start: date | None = None, end: date | None = None) -> None:
    loc = mdates.AutoDateLocator(minticks=3, maxticks=5)
    ax.xaxis.set_major_locator(loc)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(loc))
    ax.tick_params(axis="x", labelsize=7, labelbottom=True)
    if start and end:
        ax.set_xlim(start, end)


def _gaps(months: pl.Series, values: pl.Series):
    """Arrays with a NaN inserted wherever a month is skipped, so lines break at gaps."""
    xs, ys = [], []
    prev = None
    for m, v in zip(months.to_list(), values.to_list(), strict=True):
        if prev is not None and (m.year - prev.year) * 12 + m.month - prev.month > 1:
            xs.append(prev)
            ys.append(np.nan)
        xs.append(m)
        ys.append(np.nan if v is None else v)
        prev = m
    return xs, ys


FULL_RANGE = (date(2017, 7, 1), date(2027, 1, 1))


def _finish(fig, axes, used: int, name: str, note: str, top: float = 1.0) -> None:
    for ax in axes[used:]:
        ax.set_visible(False)
    fig.text(0.01, 0.005, note, fontsize=7, color=style.INK_2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.03, 1, top))
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / name)
    plt.close(fig)


def fig_a(panel: pl.DataFrame) -> pl.DataFrame:
    data = (
        on_demand(panel)
        .group_by("chip", "provider_type", "month")
        .agg(
            pl.col("price_usd_per_gpu_hour").median().alias("median_usd_per_gpu_hour"),
            pl.len().alias("listings"),
        )
        .sort("chip", "provider_type", "month")
    )
    chips = [c for c in CHIPS if c in data["chip"].unique().to_list()]
    fig, axes = _grid(len(chips), sharex=True)
    for ax, chip in zip(axes, chips, strict=False):
        for ptype, color in PTYPE_COLOR.items():
            d = data.filter((pl.col("chip") == chip) & (pl.col("provider_type") == ptype))
            if d.is_empty():
                continue
            ax.plot(
                *_gaps(d["month"], d["median_usd_per_gpu_hour"]),
                color=color,
                label=ptype,
                marker="o",
                markersize=1.8,
            )
        ax.set_title(CHIPS[chip])
        ax.set_ylim(bottom=0)
        _date_axis(ax, *FULL_RANGE)
    axes[0].set_ylabel("USD per GPU-hour")
    handles, labels = [], []
    for ax in axes[: len(chips)]:
        for h_, l_ in zip(*ax.get_legend_handles_labels(), strict=True):
            if l_ not in labels:
                handles.append(h_)
                labels.append(l_)
    fig.legend(handles, labels, loc="upper center", ncols=2, fontsize=8, bbox_to_anchor=(0.5, 1.0))
    _finish(
        fig,
        axes,
        len(chips),
        "p4a_price_by_chip.png",
        "Median on-demand list price across listings, nominal. Outlier-flagged listings excluded.",
        top=0.96,
    )
    return data


def fig_b(panel: pl.DataFrame) -> pl.DataFrame:
    data = on_demand(panel).filter(
        pl.col("age_months").is_not_null() & pl.col("price_usd_per_gpu_hour_real2025").is_not_null()
    )
    chips = [c for c in CHIPS if c in data["chip"].unique().to_list()]
    fig, axes = _grid(len(chips))
    fits = []
    for ax, chip in zip(axes, chips, strict=False):
        d = data.filter(pl.col("chip") == chip)
        x = d["age_months"].to_numpy().astype(float)
        y = d["price_usd_per_gpu_hour_real2025"].to_numpy()
        ax.scatter(x, y, s=6, color=style.SLOTS[0], alpha=0.25, linewidths=0)
        if np.unique(x).size >= 5:
            fit = lowess(y, x, frac=0.5, return_sorted=True)
            ax.plot(fit[:, 0], fit[:, 1], color=style.INK, linewidth=2)
            fits.append(pl.DataFrame({"chip": chip, "age_months": fit[:, 0], "lowess": fit[:, 1]}))
        ax.set_title(CHIPS[chip])
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("2025 USD per GPU-hour")
    for ax in axes[max(0, len(chips) - 3) : len(chips)]:
        ax.set_xlabel("months since release")
    _finish(
        fig,
        axes,
        len(chips),
        "p4b_price_vs_age.png",
        "On-demand listing-months in 2025 dollars; line is LOWESS (frac 0.5). "
        "Age from Epoch release dates; L40S has none.",
    )
    return pl.concat(fits) if fits else pl.DataFrame()


def fig_c(panel: pl.DataFrame) -> pl.DataFrame:
    prov = (
        on_demand(panel)
        .group_by("chip", "month", "provider")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("p"))
    )
    data = (
        prov.group_by("chip", "month")
        .agg(
            pl.col("p").max().alias("max_provider_median"),
            pl.col("p").min().alias("min_provider_median"),
            pl.len().alias("providers"),
        )
        .filter(pl.col("providers") >= 2)
        .with_columns(
            (pl.col("max_provider_median") / pl.col("min_provider_median")).alias("max_over_min")
        )
        .sort("chip", "month")
    )
    chips = [c for c in CHIPS if c in data["chip"].unique().to_list()]
    fig, axes = _grid(len(chips), sharex=True)
    for ax, chip in zip(axes, chips, strict=False):
        d = data.filter(pl.col("chip") == chip)
        ax.plot(*_gaps(d["month"], d["max_over_min"]), color=style.SLOTS[0])
        ax.axhline(1.0, color=style.INK_2, linewidth=0.8)
        ax.set_title(CHIPS[chip])
        ax.set_ylim(bottom=0)
        _date_axis(ax, *FULL_RANGE)
    axes[0].set_ylabel("highest / lowest provider")
    _finish(
        fig,
        axes,
        len(chips),
        "p4c_dispersion.png",
        "Ratio of the highest to the lowest provider median on-demand price in each month "
        "(months with 2+ providers).",
    )
    return data


def fig_d(panel: pl.DataFrame) -> pl.DataFrame:
    path = max(glob.glob(GETDEPLOYING_GLOB))
    gd = (
        pl.read_csv(path)
        .filter(pl.col("billing_type") == "ON_DEMAND")
        .with_columns(pl.col("date").str.to_date().dt.truncate("1mo").alias("month"))
        .group_by("gpu_slug", "month")
        .agg(pl.col("median_price").mean().alias("getdeploying"))
    )
    od = on_demand(panel)
    rows = []
    for slug, ids in GD_SLUGS.items():
        ours = (
            od.filter(pl.col("chip").is_in(ids))
            .group_by("month")
            .agg(pl.col("price_usd_per_gpu_hour").median().alias("this_panel"))
        )
        both = (
            gd.filter(pl.col("gpu_slug") == slug)
            .join(ours, on="month", how="full", coalesce=True)
            .with_columns(pl.lit(slug).alias("gpu_slug"))
        )
        rows.append(both)
    data = pl.concat(rows, how="diagonal_relaxed")
    start = data.filter(pl.col("getdeploying").is_not_null())["month"].min()
    data = data.filter(pl.col("month") >= start).sort("gpu_slug", "month")
    slugs = [s for s in GD_SLUGS if not data.filter(pl.col("gpu_slug") == s).is_empty()]
    fig, axes = _grid(len(slugs), sharex=True)
    for ax, slug in zip(axes, slugs, strict=False):
        d = data.filter(pl.col("gpu_slug") == slug)
        g = d.filter(pl.col("getdeploying").is_not_null())
        o = d.filter(pl.col("this_panel").is_not_null())
        ax.plot(*_gaps(g["month"], g["getdeploying"]), color=style.SLOTS[1], label="getdeploying")
        ax.plot(*_gaps(o["month"], o["this_panel"]), color=style.SLOTS[0], label="this panel")
        ax.set_title(slug.split("-", 1)[1].upper())
        ax.set_ylim(bottom=0)
        _date_axis(ax, start, date(2026, 12, 1))
    axes[0].set_ylabel("USD per GPU-hour")
    axes[0].legend(fontsize=7)
    _finish(
        fig,
        axes,
        len(slugs),
        "p4d_vs_getdeploying.png",
        "getdeploying.com GPU price dataset (CC BY 4.0), weekly ON_DEMAND median, monthly mean; "
        "this panel: on-demand median.",
    )
    return data


def facts(a: pl.DataFrame, b: pl.DataFrame, c: pl.DataFrame, d: pl.DataFrame) -> pl.DataFrame:
    """Per-chip numbers quoted in docs/memo_01_descriptives.md, computed from the figure data."""
    rows = []
    for chip in CHIPS:
        r: dict = {"chip": chip}
        aa = a.filter(pl.col("chip") == chip)
        wide = aa.pivot(on="provider_type", index="month", values="median_usd_per_gpu_hour")
        if {"hyperscaler", "neocloud"} <= set(wide.columns):
            both = wide.drop_nulls(["hyperscaler", "neocloud"])
            if both.height:
                ratio = both["hyperscaler"] / both["neocloud"]
                r["months_both_types"] = both.height
                r["median_hyperscaler_over_neocloud"] = round(float(ratio.median()), 2)
        bb = b.filter(pl.col("chip") == chip) if b.height else b
        if bb.height:
            r["lowess_first_age"] = round(float(bb["age_months"].min()), 1)
            r["lowess_first"] = round(float(bb.sort("age_months")["lowess"][0]), 2)
            r["lowess_last_age"] = round(float(bb["age_months"].max()), 1)
            r["lowess_last"] = round(float(bb.sort("age_months")["lowess"][-1]), 2)
        cc = c.filter(pl.col("chip") == chip)
        if cc.height:
            r["median_max_over_min"] = round(float(cc["max_over_min"].median()), 2)
            r["months_2plus_providers"] = cc.height
        slug = next((k for k, v in GD_SLUGS.items() if chip in v), None)
        dd = d.filter(pl.col("gpu_slug") == slug).drop_nulls(["getdeploying", "this_panel"])
        if dd.height:
            r["gd_overlap_months"] = dd.height
            r["median_panel_over_getdeploying"] = round(
                float((dd["this_panel"] / dd["getdeploying"]).median()), 2
            )
        rows.append(r)
    return pl.DataFrame(rows, infer_schema_length=None)


def run() -> None:
    style.apply()
    panel = pl.read_parquet(PANEL)
    TABLES.mkdir(parents=True, exist_ok=True)
    a, b, c, d = fig_a(panel), fig_b(panel), fig_c(panel), fig_d(panel)
    a.write_csv(TABLES / "fig_p4a.csv")
    b.write_csv(TABLES / "fig_p4b.csv")
    c.write_csv(TABLES / "fig_p4c.csv")
    d.write_csv(TABLES / "fig_p4d.csv")
    facts(a, b, c, d).write_csv(TABLES / "p4_descriptive_facts.csv")


def main() -> int:
    run()
    print("wrote paper/figures/p4a-d, paper/tables/fig_p4a-d.csv and p4_descriptive_facts.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
