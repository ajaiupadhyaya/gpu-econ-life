"""P3 validation checks (handoff 5.4).

1. Cross-section: the model prices every generation at the same token price, so its rent ratio
   between two chips at a date equals their throughput ratio (P1, c=32, best precision). Compared
   with observed rent ratios at matched months in the Phase 2 panel (neoclouds).
2. Term structure: the model's flat-rate ratio F/R0 for 12- and 36-month contracts (base scenario)
   against observed reserved/on-demand ratios in the panel, with the implied constant decay delta
   (P2 Level 2, r = 8%).
3. Scarcity: in `scarcity_jump` the markup jumps to the 2026 boom level at month 36. Pass if the
   oldest generation's rent rises across the jump while its efficiency gap to the frontier does
   not shrink (the 2026 H100 pattern).
4. Sensitivity: tornado of base median retirement age, one parameter at a time, low and high.

Outputs: paper/tables/p3_validation_*.csv, paper/tables/p3_tornado.csv, paper/figures/p3_tornado.png
Usage: uv run python -m gel.models.p3_validation
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import yaml  # noqa: E402

from gel.models import monte_carlo as mc  # noqa: E402
from gel.models import term_structure as ts  # noqa: E402

TABLES, FIGURES = Path("paper/tables"), Path("paper/figures")
INK, BAR_LO, BAR_HI, SURFACE = "#3d3d3a", "#9fbbe0", "#256abf", "#fcfcfb"
CROSS_SECTION_TOLERANCE = 0.25  # model/observed within +-25% counts as agreement


def load_inputs(cfg_path: Path = mc.CONFIG):
    cfg = yaml.safe_load(cfg_path.read_text())

    def j(path):
        return json.loads(Path(path).read_text())

    return (
        cfg,
        j(cfg["hardware"]["calibration_file"]),
        j(cfg["capex"]["source_file"]),
        j(cfg["market_file"]),
    )


def params(cfg, cal, capex, market, scenario="base", **over):
    merged = mc.deep_merge(mc.deep_merge(cfg, cfg["scenarios"][scenario]), over)
    return mc.resolve(merged, cal, capex, market)


def median_age(p) -> float:
    sim = mc.simulate(p)
    return float(np.percentile(sim["retirements"]["retire_age_months"].to_numpy() / 12.0, 50))


# ---- 1. cross-section ----


def check_cross_section(history: pl.DataFrame, cal: dict) -> pl.DataFrame:
    gpus = cal["best_available"]["gpus"]
    pairs = [
        ("a100_80gb", "A100_SXM", "h100_sxm", "H100_SXM"),
        ("h100_sxm", "H100_SXM", "h200", "H200_SXM"),
    ]
    od = history.filter(pl.col("contract_type") == "on_demand").with_columns(
        pl.col("retrieved_at").str.slice(0, 7).alias("month")
    )
    rows = []
    for old_chip, old_lab, new_chip, new_lab in pairs:
        model = gpus[old_lab]["q"] / gpus[new_lab]["q"]
        for prov in ("lambda", "coreweave", "google_cloud", "aws"):
            g = (
                od.filter(pl.col("provider") == prov)
                .group_by("month", "chip")
                .agg(
                    pl.col("price_usd_per_gpu_hour").median().alias("p"),
                    pl.col("price_basis").first().alias("basis"),
                )
            )
            a = g.filter(pl.col("chip") == old_chip)
            b = g.filter(pl.col("chip") == new_chip)
            j = a.join(b, on="month", suffix="_new").filter(pl.col("basis") == pl.col("basis_new"))
            if j.is_empty():
                continue
            obs = float((j["p"] / j["p_new"]).median())
            note = (
                "basis mismatch: GCP SkyPilot A100 rows accelerator-only, H100 VM-inclusive "
                "(Decision 4)"
                if prov == "google_cloud"
                else ""
            )
            rows.append(
                {
                    "pair": f"{old_lab}/{new_lab}",
                    "provider": prov,
                    "note": note,
                    "months": len(j),
                    "observed_rent_ratio": obs,
                    "model_rent_ratio": model,
                    "model_over_observed": model / obs,
                    "agrees": abs(model / obs - 1) <= CROSS_SECTION_TOLERANCE,
                }
            )
    return pl.DataFrame(rows)


# ---- 2. term structure ----


def observed_term_ratios(history: pl.DataFrame, r: float = 0.08) -> pl.DataFrame:
    h = history.with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
    od = (
        h.filter(pl.col("contract_type") == "on_demand")
        .group_by("provider", "chip", "month")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("r0"))
    )
    term = (
        h.filter(pl.col("contract_type").is_in(["reserved_1y", "reserved_3y"]))
        .group_by("provider", "chip", "month", "term_months")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("f"))
    )
    j = term.join(od, on=["provider", "chip", "month"]).with_columns(
        (pl.col("f") / pl.col("r0")).alias("ratio")
    )
    agg = (
        j.group_by("provider", "chip", "term_months")
        .agg(pl.col("ratio").median().alias("observed_ratio"), pl.len().alias("months"))
        .sort("provider", "chip", "term_months")
    )
    deltas = [
        ts.solve_delta(row["observed_ratio"], row["term_months"] / 12.0, r=r).delta
        for row in agg.iter_rows(named=True)
    ]
    return agg.with_columns(pl.Series("implied_delta_level2", deltas))


def check_term_structure(history, base_summary: dict) -> pl.DataFrame:
    obs = observed_term_ratios(history)
    model = base_summary["implied_flat_ratio"]
    return obs.with_columns(
        pl.col("term_months")
        .map_elements(lambda t: model.get(t, model.get(str(t))), return_dtype=pl.Float64)
        .alias("model_ratio"),
        pl.col("provider")
        .replace_strict(
            {"aws": "hyperscaler", "google_cloud": "hyperscaler", "azure": "hyperscaler"},
            default="neocloud",
        )
        .alias("provider_type"),
    ).with_columns(
        # Level 3: (F/R0)_obs = (F/R0)_model x (1 - pi T)  =>  pi = (1 - obs/model) / T
        (
            (1 - pl.col("observed_ratio") / pl.col("model_ratio")) / (pl.col("term_months") / 12)
        ).alias("implied_term_premium_pa"),
    )


# ---- 3. scarcity jump ----


def check_scarcity(cfg, cal, capex, market) -> dict:
    p = params(cfg, cal, capex, market, "scarcity_jump")
    jump = int(p["markup"]["jump_month"])
    sim = mc.simulate(p)
    rent0 = sim["price"] * sim["q"][:, :1] * 3600.0  # generation 0, launched at month 0
    eta_f = np.take_along_axis(sim["eta"], sim["frontier"], axis=1)
    lag = eta_f / sim["eta"][:, :1]
    before, after = slice(jump - 3, jump), slice(jump, jump + 3)
    out = {
        "jump_month": jump,
        "rent_gen0_before": float(rent0[:, before].mean()),
        "rent_gen0_after": float(rent0[:, after].mean()),
        "efficiency_gap_before": float(lag[:, before].mean()),
        "efficiency_gap_after": float(lag[:, after].mean()),
    }
    out["passes"] = (
        out["rent_gen0_after"] > out["rent_gen0_before"]
        and out["efficiency_gap_after"] >= out["efficiency_gap_before"] - 1e-12
    )
    return out


# ---- 4. tornado ----


def tornado(cfg, cal, capex, market) -> pl.DataFrame:
    base = params(cfg, cal, capex, market)
    b = median_age(base)
    mk = base["market"]
    refresh = cal["best_available"]["generation_step_refresh"]["log_eta_ratio"]
    spec = market["generation_step"]["spec_mean_log_step"]
    e0 = base["electricity"]["mean"]
    cases = [
        (
            "Generation step G (refresh x1.14 / spec x1.75)",
            {"hardware": {"mu_G": refresh}},
            {"hardware": {"mu_G": spec}},
        ),
        (
            "Cadence (36 / 18 months)",
            {"cadence": {"months": [36], "probs": [1.0]}},
            {"cadence": {"months": [18], "probs": [1.0]}},
        ),
        (
            "Electricity (-50% / +50%)",
            {"electricity": {"mean": 0.5 * e0, "x0": 0.5 * e0}},
            {"electricity": {"mean": 1.5 * e0, "x0": 1.5 * e0}},
        ),
        ("PUE (1.1 / 1.5)", {"market": {"pue": 1.1}}, {"market": {"pue": 1.5}}),
        (
            "Utilisation (0.5 / 0.9)",
            {"market": {"utilization": 0.5}},
            {"market": {"utilization": 0.9}},
        ),
        (
            "Discount rate (5% / 12%)",
            {"market": {"discount_rate_annual": 0.05}},
            {"market": {"discount_rate_annual": 0.12}},
        ),
        (
            "Annuity term (48 / 72 months)",
            {"market": {"annuity_months": 48}},
            {"market": {"annuity_months": 72}},
        ),
        (
            "Maintenance (0% / 12.5% of capex)",
            {"maintenance_fraction_of_capex_per_year": 0.0},
            {"maintenance_fraction_of_capex_per_year": 0.125},
        ),
        (
            "Failure hazard (0.5% / 11% per year)",
            {"failure": {"annual_hazard": market["failure"]["low_annual_hazard"]}},
            {"failure": {"annual_hazard": market["failure"]["upper_bound_annual_hazard"]}},
        ),
        (
            "Markup mean (half / 2026 boom)",
            {"markup": {"mean": mk_half(base)}},
            {"markup": {"mean": market["markup"]["boom_mean"]}},
        ),
    ]
    rows = []
    for name, lo, hi in cases:
        a_lo = median_age(mc.deep_merge(base, lo))
        a_hi = median_age(mc.deep_merge(base, hi))
        rows.append(
            {
                "parameter": name,
                "base_median_y": b,
                "low_case_median_y": a_lo,
                "high_case_median_y": a_hi,
                "swing_y": abs(a_hi - a_lo),
            }
        )
    del mk
    return pl.DataFrame(rows).sort("swing_y", descending=True)


def mk_half(base: dict) -> float:
    return 0.5 * base["markup"]["mean"]


def plot_tornado(t: pl.DataFrame, path: Path) -> None:
    t = t.sort("swing_y")
    fig, ax = plt.subplots(figsize=(8, 0.45 * len(t) + 1.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    base = t["base_median_y"][0]
    y = np.arange(len(t))
    lo = t["low_case_median_y"].to_numpy() - base
    hi = t["high_case_median_y"].to_numpy() - base
    ax.barh(y, lo, color=BAR_LO, label="low case (first value)")
    ax.barh(y, hi, color=BAR_HI, label="high case (second value)")
    ax.axvline(0, color=INK, lw=0.8)
    ax.set_yticks(y, t["parameter"].to_list(), fontsize=8, color=INK)
    ax.set_xlabel(f"Change in median retirement age (years) from base {base:.2f} y", color=INK)
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def main() -> int:
    from gel.build.historical import load_history

    cfg, cal, capex, market = load_inputs()
    history = load_history(Path("."))
    TABLES.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)

    cs = check_cross_section(history, cal)
    cs.write_csv(TABLES / "p3_validation_cross_section.csv")
    base = params(cfg, cal, capex, market)
    base_summary = mc.summarize(mc.simulate(base), base, "base")
    term = check_term_structure(history, base_summary)
    term.write_csv(TABLES / "p3_validation_term_structure.csv")
    sc = check_scarcity(cfg, cal, capex, market)
    (TABLES / "p3_validation_scarcity.json").write_text(json.dumps(sc, indent=2) + "\n")
    t = tornado(cfg, cal, capex, market)
    t.write_csv(TABLES / "p3_tornado.csv")
    plot_tornado(t, FIGURES / "p3_tornado.png")

    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_width_chars(200)
    print("== Check 1: cross-section (model rent ratio = throughput ratio)")
    print(cs)
    print("== Check 2: term structure (observed vs model F/R0)")
    print(
        term.select(
            "provider",
            "chip",
            "term_months",
            "months",
            pl.col("observed_ratio").round(3),
            pl.col("model_ratio").round(3),
            pl.col("implied_delta_level2").round(3),
        )
    )
    print("== Check 3: scarcity jump", json.dumps(sc))
    print("== Check 4: tornado (median retirement age, years)")
    print(t.with_columns(pl.col(pl.Float64).round(2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
