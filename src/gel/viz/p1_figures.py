"""P1 figures (handoff 3.7). Each figure writes its plotted numbers to a CSV beside the tables.

Fig P1-a  output throughput vs concurrency, one line per GPU (BF16), log-log
Fig P1-b  tokens per joule at concurrency 32 by GPU (launch order), BF16 vs best precision
Fig P1-c  $ per million output tokens at concurrency 32 (best precision): rental at the neocloud
          median price and electricity only (EIA price, PUE 1.3), by release date, log y
Fig P1-d  obsolescence discount D vs the H200 at concurrency 32 (BF16, neocloud median price),
          bars spanning the cheapest to dearest neocloud price; paid-price D shown hollow

Usage: uv run python -m gel.viz.p1_figures
"""

from __future__ import annotations

import json
import math
import sys
from datetime import date
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import polars as pl

from gel.bench import metrics
from gel.viz import style

TABLES, FIGURES = Path("paper/tables"), Path("paper/figures")
OP_CONC = 32
FRONTIER = "H200_SXM"


def load() -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame, dict]:
    summary = pl.read_csv(TABLES / "p1_benchmark_summary.csv")
    panel = pl.read_parquet("data/processed/spot_panel.parquet")
    med = pl.read_csv(TABLES / "m4_spot_medians.csv").filter(pl.col("billing") == "on_demand")
    market = json.loads(Path("data/processed/p3_market.json").read_text())
    return summary, panel, med, market


def best_at(summary: pl.DataFrame, conc: int) -> pl.DataFrame:
    return (
        summary.filter(pl.col("concurrency") == conc)
        .sort("output_tok_per_s_mean", descending=True)
        .group_by("gpu_label", maintain_order=True)
        .first()
    )


def fig_a(summary: pl.DataFrame) -> pl.DataFrame:
    d = summary.filter(pl.col("precision_mode") == "bf16").sort("gpu_label", "concurrency")
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    ends = []
    for label, (_, name) in style.GPUS.items():
        g = d.filter(pl.col("gpu_label") == label)
        if g.is_empty():
            continue
        x, y = g["concurrency"].to_list(), g["output_tok_per_s_mean"].to_list()
        ax.errorbar(
            x,
            y,
            yerr=g["output_tok_per_s_sd"].to_list(),
            color=style.COLOR[label],
            marker="o",
            markersize=5,
            capsize=2,
            label=name,
        )
        ends.append([math.log10(y[-1]), y[-1], x[-1], name])
    ends.sort()
    for i in range(1, len(ends)):  # keep right-edge labels >= 0.11 decades apart (~1 line)
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.11)
    for ly, y, x, name in ends:
        ax.annotate(
            name,
            (x, y),
            xytext=(x * 1.12, 10**ly),
            textcoords="data",
            va="center",
            fontsize=8,
            color=style.INK,
        )
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks([1, 8, 32, 128], ["1", "8", "32", "128"])
    ax.set_xlim(0.8, 260)
    ax.set_xlabel("Concurrent requests")
    ax.set_ylabel("Output tokens per second (log)")
    ax.set_title("P1-a  Throughput vs concurrency, Llama 3.1 8B, BF16")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1a_throughput.png")
    plt.close(fig)
    return d.select("gpu_label", "concurrency", "output_tok_per_s_mean", "output_tok_per_s_sd")


def fig_b(summary: pl.DataFrame) -> pl.DataFrame:
    labels = [lab for lab in style.GPUS if lab in summary["gpu_label"].to_list()]
    c = summary.filter(pl.col("concurrency") == OP_CONC)
    bf = {
        r["gpu_label"]: r["tokens_per_joule_mean"]
        for r in c.filter(pl.col("precision_mode") == "bf16").iter_rows(named=True)
    }
    best = {r["gpu_label"]: r for r in best_at(summary, OP_CONC).iter_rows(named=True)}
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    x = range(len(labels))
    w = 0.38
    ax.bar(
        [i - w / 2 for i in x],
        [bf[lab] for lab in labels],
        w * 0.94,
        color=style.SLOTS[0],
        label="BF16 (like-for-like)",
    )
    ax.bar(
        [i + w / 2 for i in x],
        [best[lab]["tokens_per_joule_mean"] for lab in labels],
        w * 0.94,
        color=style.SLOTS[1],
        label="Best available precision",
    )
    for i, lab in enumerate(labels):
        ax.annotate(
            best[lab]["precision_mode"].replace("_", " "),
            (i + w / 2, best[lab]["tokens_per_joule_mean"]),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7,
            color=style.INK_2,
        )
    ax.set_xticks(list(x), [style.GPUS[lab][1] for lab in labels])
    ax.set_ylabel("Output tokens per joule (board power)")
    ax.set_title(f"P1-b  Energy efficiency at concurrency {OP_CONC}, in launch order")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1b_tokens_per_joule.png")
    plt.close(fig)
    return pl.DataFrame(
        {
            "gpu_label": labels,
            "tokens_per_joule_bf16": [bf[lab] for lab in labels],
            "best_mode": [best[lab]["precision_mode"] for lab in labels],
            "tokens_per_joule_best": [best[lab]["tokens_per_joule_mean"] for lab in labels],
        }
    )


def fig_c(summary, med, market) -> pl.DataFrame:
    dates = style.release_dates()
    e, pue = market["electricity"]["mean_usd_kwh"], 1.3
    rows = []
    for r in best_at(summary, OP_CONC).iter_rows(named=True):
        chip = style.GPUS[r["gpu_label"]][0]
        m = med.filter(pl.col("chip_id") == chip)
        price = m["median_neocloud"][0] if not m.is_empty() else None
        n = int(m["n_neocloud"][0]) if not m.is_empty() else 0
        q, eta = r["output_tok_per_s_mean"], r["tokens_per_joule_mean"]
        rows.append(
            {
                "gpu_label": r["gpu_label"],
                "chip_id": chip,
                "release_date": dates.get(chip),
                "mode": r["precision_mode"],
                "neocloud_median_price": price,
                "n_neocloud": n,
                "rental_usd_per_mtok": metrics.cost_per_mtok(price, q) if price else None,
                "energy_usd_per_mtok": metrics.energy_cost_per_mtok(1.0, eta, e, pue),
            }
        )
    d = pl.DataFrame(rows).sort("release_date")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    xs = [date.fromisoformat(s) for s in d["release_date"]]
    for col, color, name in (
        ("rental_usd_per_mtok", style.SLOTS[0], "Rental (neocloud median)"),
        ("energy_usd_per_mtok", style.SLOTS[1], f"Electricity only (${e:.3f}/kWh, PUE {pue})"),
    ):
        ax.plot(xs, d[col].to_list(), color=color, marker="o", markersize=7, label=name)
    for x, r in zip(xs, d.iter_rows(named=True), strict=True):
        single = r["n_neocloud"] <= 1
        ax.annotate(
            style.GPUS[r["gpu_label"]][1] + (" (1 price)" if single else ""),
            (x, r["rental_usd_per_mtok"]),
            xytext=(0, 7),
            textcoords="offset points",
            ha="center",
            fontsize=7.5,
            color=style.INK,
        )
    ax.set_yscale("log")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlabel("Release date")
    ax.set_ylabel("$ per million output tokens (log)")
    ax.set_title(f"P1-c  Cost per token at concurrency {OP_CONC}, best precision")
    ax.legend(loc="center right", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1c_cost_per_mtok.png")
    plt.close(fig)
    return d


def fig_d(summary, panel, med) -> pl.DataFrame:
    bf = summary.filter((pl.col("precision_mode") == "bf16") & (pl.col("concurrency") == OP_CONC))
    q = {r["gpu_label"]: r["output_tok_per_s_mean"] for r in bf.iter_rows(named=True)}
    paid = {r["gpu_label"]: r["price_paid_per_hr"] for r in bf.iter_rows(named=True)}
    neo = panel.filter((pl.col("billing") == "on_demand") & (pl.col("provider_type") == "neocloud"))
    f_chip = style.GPUS[FRONTIER][0]
    p_f = med.filter(pl.col("chip_id") == f_chip)["median_neocloud"][0]
    rows = []
    for label in style.GPUS:
        if label == FRONTIER or label not in q:
            continue
        chip = style.GPUS[label][0]
        prices = neo.filter(pl.col("chip_id") == chip)["price_per_gpu_hr"]
        mrow = med.filter(pl.col("chip_id") == chip)
        p_med = mrow["median_neocloud"][0]

        def disc(p, chip_label=label):
            return metrics.obsolescence_discount(p, p_f, q[chip_label], q[FRONTIER])

        rows.append(
            {
                "gpu_label": label,
                "n_neocloud": len(prices),
                "discount_median": disc(p_med),
                "discount_low": disc(prices.min()),
                "discount_high": disc(prices.max()),
                "discount_paid": metrics.obsolescence_discount(
                    paid[label], paid[FRONTIER], q[label], q[FRONTIER]
                ),
            }
        )
    d = pl.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    y = list(range(len(d)))[::-1]
    for yi, r in zip(y, d.iter_rows(named=True), strict=True):
        c = style.COLOR[r["gpu_label"]]
        ax.plot([r["discount_low"], r["discount_high"]], [yi, yi], color=c, lw=2, alpha=0.6)
        ax.plot(r["discount_median"], yi, "o", color=c, markersize=8)
        ax.plot(
            r["discount_paid"],
            yi,
            "o",
            markerfacecolor="none",
            markeredgecolor=c,
            markersize=8,
            markeredgewidth=1.5,
        )
        right = max(r["discount_high"], r["discount_paid"], r["discount_median"])
        ax.annotate(
            f"n={r['n_neocloud']}",
            (right, yi),
            xytext=(9, 0),
            textcoords="offset points",
            va="center",
            fontsize=7.5,
            color=style.INK_2,
        )
    ax.axvline(0, color=style.INK_2, lw=1)
    ax.set_yticks(y, [style.GPUS[lab][1] for lab in d["gpu_label"]])
    ax.set_xlabel("D = (P_g/P_H200)/(q_g/q_H200) - 1    (<0: priced below its relative output)")
    ax.set_title(f"P1-d  Obsolescence discount vs H200, BF16, concurrency {OP_CONC}")
    ax.plot([], [], "o", color=style.INK_2, label="neocloud median price (bar: min-max)")
    ax.plot(
        [],
        [],
        "o",
        markerfacecolor="none",
        markeredgecolor=style.INK_2,
        label="price paid on RunPod",
    )
    ax.legend(loc="upper right", fontsize=7.5)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(FIGURES / "p1d_obsolescence_discount.png")
    plt.close(fig)
    return d


def main() -> int:
    style.apply()
    FIGURES.mkdir(parents=True, exist_ok=True)
    summary, panel, med, market = load()
    outs = {
        "fig_p1a.csv": fig_a(summary),
        "fig_p1b.csv": fig_b(summary),
        "fig_p1c.csv": fig_c(summary, med, market),
        "fig_p1d.csv": fig_d(summary, panel, med),
    }
    for name, df in outs.items():
        df.write_csv(TABLES / name)
    pl.Config.set_tbl_width_chars(200)
    for name in ("fig_p1c.csv", "fig_p1d.csv"):
        print(name)
        print(outs[name].with_columns(pl.col(pl.Float64).round(3)))
    print("wrote paper/figures/p1a..p1d")
    return 0


if __name__ == "__main__":
    sys.exit(main())
