"""Phase 6: from rents to asset values and economic life (proposal Step 3; Decision 25).

    V(a) = sum_{m >= 0, a + m/12 < H} 730 max(u p(a + m/12) - o, 0) S(m) / (1 + r)^((m+1)/12)

with p the real rent per GPU-hour on the chip's rent path, o the operating cost per GPU-hour
(power x PUE x electricity price + maintenance), S(m) = exp(-h m / 12) the survival of a unit
alive at age a, and H the horizon (no rent beyond the oldest age observed in the panel). Net rent
is floored at zero each month. Economic life T* is the first age at which u p <= o.

Rent paths. p(a) = p_now * exp(g(a) - g(a_now)): the chip's current neocloud median on-demand rent
(M4 snapshot) moved along a log-rent profile g. Profiles: "realized_older" chain-links the observed
cohort paths of the older chips; the projection strategies come from Phase 5 (to age 6) and borrow
the realized increments beyond that.

Summary per chip x profile x grid point: V(0), V(0)/capex, share of value lost by years 1-6,
T*, and a straight-line-equivalent life L_SL = 2 * integral_0^H V(a)/V(0) da (the straight-line
life with the same average book value). The base case also yields depreciation schedules
(share of initial value lost in each year of life) for the Phase 7 restatement.

Outputs: paper/tables/p6_value_curves.csv, p6_summary.csv, p6_schedules.csv, p6_summary.tex,
paper/figures/p6_value_curves.png
Usage: uv run python -m gel.models.asset_value
"""

from __future__ import annotations

import itertools
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import yaml

CONFIG = Path("config/assumptions.yaml")
TABLES, FIGURES = Path("paper/tables"), Path("paper/figures")
CHIPS = Path("data/processed/chips.parquet")
HOURS_PER_MONTH = 730.0
SL_LIVES = (5.0, 5.5, 6.0)


# ---- valuation core ---------------------------------------------------------------------------


def opex_per_hour(power_kw: float, pue: float, elec: float, capex: float, maint: float) -> float:
    """Operating cost per GPU-hour: power x PUE x $/kWh plus maintenance as a share of capex."""
    return power_kw * pue * elec + maint * capex / 8760.0


def value_path(
    rent: np.ndarray, opex: float, u: float, r: float, h: float
) -> tuple[np.ndarray, float]:
    """Values at every month of a monthly rent path (rent[m] = rent at age m months).

    Returns V[m] for m = 0..len(rent) (V at the horizon is 0) and T* in years (np.inf if net rent
    stays positive to the horizon)."""
    n = len(rent)
    net = HOURS_PER_MONTH * np.maximum(u * rent - opex, 0.0)
    disc = (1.0 + r) ** (-1.0 / 12.0)
    surv = np.exp(-h / 12.0)
    v = np.zeros(n + 1)
    # Backward recursion: V[m] = net[m] * disc + surv * disc * V[m+1]
    for m in range(n - 1, -1, -1):
        v[m] = disc * (net[m] + surv * v[m + 1])
    below = np.nonzero(u * rent <= opex)[0]
    t_star = below[0] / 12.0 if below.size else np.inf
    return v, t_star


def sl_equivalent_life(v: np.ndarray) -> float:
    """2 x integral of V(a)/V(0) over the horizon (monthly trapezoid), in years."""
    if v[0] <= 0:
        return float("nan")
    share = v / v[0]
    return float(2.0 * np.trapezoid(share, dx=1.0 / 12.0))


# ---- rent profiles ----------------------------------------------------------------------------


def realized_profile(paths: pl.DataFrame, older: list[str], max_months: int) -> np.ndarray:
    """Monthly g(a) chain-linking the older chips' observed cohort paths.

    Each chip's path is relative to its own first 6-month bin, so only the increments between
    consecutive bins are pooled (mean over the chips that have both bins). Bin values sit at bin
    midpoints (b + 3 months); g is flat before the first midpoint and linear in between."""
    p = paths.filter((pl.col("sample") == "all") & pl.col("chip").is_in(older))
    est: dict[str, dict[int, float]] = {}
    for c in older:
        rows = p.filter(pl.col("chip") == c)
        if rows.is_empty():
            continue
        first = int(rows["first_bin_months_from"][0])
        est[c] = {first: 0.0} | dict(
            zip(rows["age_months_from"].to_list(), rows["estimate"].to_list(), strict=True)
        )
    bins = sorted({b for e in est.values() for b in e})
    g = {bins[0]: 0.0}
    for b0, b1 in itertools.pairwise(bins):
        steps = [e[b1] - e[b0] for e in est.values() if b0 in e and b1 in e]
        g[b1] = g[b0] + (float(np.mean(steps)) if steps else 0.0)
    mids = np.array([b + 3.0 for b in bins])
    vals = np.array([g[b] for b in bins])
    ages = np.arange(max_months + 1, dtype=float)
    out = np.interp(ages, mids, vals)  # flat beyond the ends
    return out - out[0]


def grid_profile(ages_years: np.ndarray, g: np.ndarray, max_months: int) -> np.ndarray:
    """Monthly g from a profile on an age grid in years (linear interpolation)."""
    m = np.arange(max_months + 1) / 12.0
    return np.interp(m, ages_years, g)


def splice(g_strategy: np.ndarray, g_borrow: np.ndarray, from_month: int) -> np.ndarray:
    """Beyond `from_month`, continue the strategy profile with the borrowed profile's increments."""
    out = g_strategy.copy()
    out[from_month:] = g_strategy[from_month] + (g_borrow[from_month:] - g_borrow[from_month])
    return out


def build_profiles(cfg: dict, max_months: int) -> dict[str, np.ndarray]:
    paths = pl.read_csv(TABLES / "p5_cohort_paths.csv")
    real = realized_profile(paths, cfg["older_chips"], max_months)
    borrow = {
        "realized_older": real,
        "v100": realized_profile(paths, ["v100"], max_months),
        "flat": np.zeros(max_months + 1),
    }[cfg["borrow_beyond_age6"]]
    six = 72
    out = {"realized_older": real}
    prof = pl.read_csv(TABLES / "p5_profiles.csv")
    for spec in ("s1a_tflops", "s1b_three_specs", "s2_frontier"):
        d = prof.filter(pl.col("spec") == spec).sort("age")
        g = grid_profile(d["age"].to_numpy(), d["g"].to_numpy(), max_months)
        out[spec] = splice(g, borrow, six)
    sweep = pl.read_csv(TABLES / "p5_strategy4_sweep.csv")
    for delta in cfg["s4_deltas"]:
        d = sweep.filter((pl.col("delta") - delta).abs() < 1e-9).sort("age")
        g = grid_profile(d["age"].to_numpy(), d["g"].to_numpy(), max_months)
        out[f"s4_d{delta:+.2f}".replace("+0.00", "0.00")] = splice(g, borrow, six)
    return out


# ---- run ---------------------------------------------------------------------------------------


def chip_ages(valuation: date) -> dict[str, float]:
    chips = pl.read_parquet(CHIPS)
    return {
        r["chip_id"]: (valuation - r["release_date"]).days / 365.25
        for r in chips.iter_rows(named=True)
        if r["release_date"] is not None
    }


def rent_anchors(cfg: dict) -> dict[str, float]:
    m4 = pl.read_csv(TABLES / "m4_spot_medians.csv").filter(pl.col("billing") == "on_demand")
    col = cfg["rent_anchor"]
    return {r["chip_id"]: float(r[col]) for r in m4.iter_rows(named=True) if r[col] is not None}


def run(cfg: dict | None = None) -> dict[str, pl.DataFrame]:
    cfg = cfg or yaml.safe_load(CONFIG.read_text())
    base = cfg["base"]
    max_months = int(round(cfg["horizon_years"] * 12))
    profiles = build_profiles(cfg, max_months)
    ages_now = chip_ages(date.fromisoformat(cfg["valuation_date"]))
    anchors = rent_anchors(cfg)
    grid = cfg["grid"]
    points = [
        dict(r=r, u=u, pue=pue, h=base["failure_rate_per_year"], power_basis=base["power_basis"])
        for r, u, pue in itertools.product(grid["discount_rate"], grid["utilization"], grid["pue"])
    ]
    base_pt = dict(
        r=base["discount_rate"],
        u=base["utilization"],
        pue=base["pue"],
        h=base["failure_rate_per_year"],
        power_basis=base["power_basis"],
    )
    sens = (
        [dict(base_pt, power_basis="tdp")]
        + [dict(base_pt, h=h) for h in cfg["failure_rate_sensitivity"] if h != base_pt["h"]]
        + [dict(base_pt, horizon=hz) for hz in cfg["horizon_sensitivity"]]
    )
    tdp = {
        r["chip_id"]: r["tdp_w"] / 1000.0
        for r in pl.read_parquet(CHIPS).iter_rows(named=True)
        if r["tdp_w"] is not None
    }
    curves, summary = [], []
    for chip, ccfg in cfg["chips"].items():
        if chip not in anchors:
            continue
        a_now = ages_now[chip]
        i_now = min(int(round(a_now * 12)), max_months)
        for pname, g in profiles.items():
            rent = anchors[chip] * np.exp(g - g[i_now])[:max_months]
            for case, pt in (
                [("base", base_pt)]
                + [("grid", p) for p in points]
                + [("sensitivity", p) for p in sens]
            ):
                power = (
                    ccfg["system_power_kw_per_gpu"]
                    if pt["power_basis"] == "system_max"
                    else tdp[chip]
                )
                o = opex_per_hour(
                    power,
                    pt["pue"],
                    base["electricity_usd_per_kwh"],
                    ccfg["capex_usd"],
                    base["maintenance_share_of_capex"],
                )
                n_m = int(round(pt.get("horizon", cfg["horizon_years"]) * 12))
                v, t_star = value_path(rent[:n_m], o, pt["u"], pt["r"], pt["h"])
                row = {
                    "chip": chip,
                    "profile": pname,
                    "case": case,
                    **{k: pt[k] for k in ("r", "u", "pue", "h", "power_basis")},
                    "horizon": pt.get("horizon", cfg["horizon_years"]),
                    "rent_now": anchors[chip],
                    "age_now": a_now,
                    "rent_age0": float(rent[0]),
                    "opex_per_hour": o,
                    "capex_usd": ccfg["capex_usd"],
                    "v0": float(v[0]),
                    "v0_over_capex": float(v[0] / ccfg["capex_usd"]),
                    "t_star": t_star,
                    "sl_equivalent_life": sl_equivalent_life(v),
                }
                for k in range(1, 7):
                    vk = v[12 * k] if 12 * k < len(v) else 0.0
                    row[f"share_lost_y{k}"] = float(1 - vk / v[0]) if v[0] > 0 else np.nan
                summary.append(row)
                if case in ("base", "grid"):
                    for q in range(0, max_months + 1, 3):
                        curves.append(
                            {
                                "chip": chip,
                                "profile": pname,
                                "case": case,
                                "r": pt["r"],
                                "u": pt["u"],
                                "pue": pt["pue"],
                                "age": q / 12.0,
                                "value_usd": float(v[q]),
                                "value_share": float(v[q] / v[0]) if v[0] > 0 else np.nan,
                                "rent": float(rent[min(q, max_months - 1)]),
                            }
                        )
    out = {
        "p6_value_curves": pl.DataFrame(curves),
        "p6_summary": pl.DataFrame(summary, infer_schema_length=None),
    }
    out["p6_schedules"] = schedules(out["p6_summary"], cfg, profiles, anchors, ages_now)
    return out


def schedules(
    summary: pl.DataFrame,
    cfg: dict,
    profiles: dict[str, np.ndarray],
    anchors: dict[str, float],
    ages_now: dict[str, float],
) -> pl.DataFrame:
    """Base-case depreciation schedules: share of initial value lost in each year of life,
    for the configured chip and profiles. A profile whose value rises in any year is skipped
    (a book schedule cannot appreciate) and listed in the log."""
    base = cfg["base"]
    chip = cfg["schedule_chip"]
    ccfg = cfg["chips"][chip]
    max_months = int(round(cfg["horizon_years"] * 12))
    i_now = min(int(round(ages_now[chip] * 12)), max_months)
    o = opex_per_hour(
        ccfg["system_power_kw_per_gpu"],
        base["pue"],
        base["electricity_usd_per_kwh"],
        ccfg["capex_usd"],
        base["maintenance_share_of_capex"],
    )
    rows = []
    for pname in cfg["schedule_profiles"]:
        key = pname
        if key not in profiles:
            print(f"schedule profile {pname} not found; skipped")
            continue
        g = profiles[key]
        rent = anchors[chip] * np.exp(g - g[i_now])[:max_months]
        v, _ = value_path(rent, o, base["utilization"], base["discount_rate"], 0.0)
        years = int(cfg["horizon_years"])
        shares = [(v[12 * (k - 1)] - v[12 * k]) / v[0] for k in range(1, years + 1)]
        if min(shares) < -1e-12:
            print(f"schedule {pname}: value rises in some year; skipped")
            continue
        for k, s in enumerate(shares, start=1):
            rows.append({"schedule": f"market_{pname}_{chip}", "year": k, "dep_share": s})
    return pl.DataFrame(rows)


# ---- outputs ----------------------------------------------------------------------------------

LABEL = {
    "realized_older": "Realized (V100, A100)",
    "s1a_tflops": "1a quality index",
    "s1b_three_specs": "1b three specs",
    "s2_frontier": "2 frontier-relative",
}
CHIP_LABEL = {"a100_80gb": "A100 80GB", "h100_sxm": "H100 SXM", "h200": "H200", "b200": "B200"}


def plabel(p: str) -> str:
    if p.startswith("s4_d"):
        return f"4 shape, d = {float(p[4:]):.2f}"
    return LABEL.get(p, p)


def latex_summary(summary: pl.DataFrame) -> str:
    base = summary.filter(pl.col("case") == "base")
    grid = summary.filter(pl.col("case") == "grid")
    lines = [
        "% Generated by gel.models.asset_value from p6_summary.csv. Do not edit.",
        "% Base case r = 10%, u = 70%, PUE 1.3, system power, 2%/yr failure; brackets: min-max over"
        " the r x u x PUE grid.",
        "\\begin{tabular}{llcccc}",
        "\\hline",
        "Chip & Rent path & $V(0)$/capex & Share lost by yr 3 & SL-equivalent life (yrs) & $T^*$"
        " (yrs) \\\\",
        "\\hline",
    ]
    for chip in CHIP_LABEL:
        for p in ("realized_older", "s2_frontier", "s4_d-0.20", "s4_d-0.40"):
            b = base.filter((pl.col("chip") == chip) & (pl.col("profile") == p))
            g = grid.filter((pl.col("chip") == chip) & (pl.col("profile") == p))
            if b.is_empty():
                continue
            r = b.row(0, named=True)

            def rng(col: str, fmt: str, gg: pl.DataFrame = g) -> str:
                lo, hi = gg[col].min(), gg[col].max()
                return f"[{lo:{fmt}}, {hi:{fmt}}]"

            ts = "$>$9" if not np.isfinite(r["t_star"]) else f"{r['t_star']:.1f}"
            lines.append(
                f"{CHIP_LABEL[chip]} & {plabel(p)}"
                f" & {r['v0_over_capex']:.2f} {rng('v0_over_capex', '.2f')}"
                f" & {r['share_lost_y3']:.2f} {rng('share_lost_y3', '.2f')}"
                f" & {r['sl_equivalent_life']:.1f} {rng('sl_equivalent_life', '.1f')} & {ts} \\\\"
            )
    lines += ["\\hline", "\\end{tabular}", ""]
    return "\n".join(lines)


def figure(curves: pl.DataFrame) -> None:
    from gel.viz import style

    style.apply()
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(8.0, 6.2), sharex=True, sharey=True)
    colors = {
        "realized_older": style.SLOTS[0],
        "s2_frontier": style.SLOTS[2],
        "s4_d-0.20": style.SLOTS[1],
        "s4_d-0.40": style.SLOTS[3],
    }
    for ax, chip in zip(axes.ravel(), CHIP_LABEL, strict=True):
        c = curves.filter(pl.col("chip") == chip)
        for p, col in colors.items():
            g = c.filter((pl.col("profile") == p) & (pl.col("case") == "grid"))
            band = (
                g.group_by("age")
                .agg(
                    pl.col("value_share").min().alias("lo"), pl.col("value_share").max().alias("hi")
                )
                .sort("age")
            )
            b = c.filter((pl.col("profile") == p) & (pl.col("case") == "base")).sort("age")
            if b.is_empty():
                continue
            if p == "realized_older":
                ax.fill_between(band["age"], band["lo"], band["hi"], color=col, alpha=0.15, lw=0)
            ax.plot(b["age"], b["value_share"], color=col, label=plabel(p))
        for life, ls in zip(SL_LIVES, (":", "--", "-."), strict=True):
            a = np.linspace(0, life, 50)
            ax.plot(
                a, 1 - a / life, color=style.INK_2, lw=1.0, ls=ls, label=f"straight-line {life:g} y"
            )
        ax.set_title(CHIP_LABEL[chip])
        ax.set_ylim(0, 1.25)
        ax.set_xlim(0, 9)
    for ax in axes[1]:
        ax.set_xlabel("Age (years since release)")
    for ax in axes[:, 0]:
        ax.set_ylabel("Value / value at age 0")
    axes[0, 0].legend(fontsize=7, loc="upper right")
    fig.tight_layout()
    FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURES / "p6_value_curves.png")
    plt.close(fig)


def main(argv: list[str] | None = None) -> int:
    out = run()
    TABLES.mkdir(parents=True, exist_ok=True)
    for name, t in out.items():
        t.write_csv(TABLES / f"{name}.csv")
        print(f"wrote {TABLES / name}.csv ({t.height} rows)")
    (TABLES / "p6_summary.tex").write_text(latex_summary(out["p6_summary"]))
    figure(out["p6_value_curves"])
    print(f"wrote {TABLES / 'p6_summary.tex'} and {FIGURES / 'p6_value_curves.png'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
