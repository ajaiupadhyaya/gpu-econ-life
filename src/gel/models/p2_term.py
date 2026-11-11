"""P2: decay implied by the rental term structure (handoff section 4; Decisions 12-14).

Observed F/R0: reserved (1-, 3- and Azure's 5-year) price / on-demand price for the same provider,
chip and month, from the Phase 2 history plus the live collector's November files. Medians are
taken across providers and months, separately for hyperscalers and neoclouds (hyperscaler
on-demand list prices are sticky and high, so their ratios mix decay with an on-demand premium).

For each chip x provider type:
- Level 2/3: one constant delta fitted by least squares across the available tenors, on the grid
  r in {5, 8, 12}% x pi in {0, 1, 2, 3}%/yr.
- Level 4: (beta0, beta1, tau) where three or more tenors exist (r = 8%, pi = 0).
- L_50 = ln 2 / delta (constant) or the Level 4 half-life.
- L_opex = age today + ln(R_now / opex) / delta: the age at which today's rent, decaying at delta,
  falls below operating cost. R_now is the group's current median on-demand price (M4 panel).
  opex per GPU-hour = e x PUE x w_load / 1000 + maintenance (4% of the Epoch release price per year
  where Epoch has one; power-only otherwise, flagged).

Outputs: paper/tables/p2_implied_decay.csv, p2_level4.csv; figures P2-a/b/c.
Usage: uv run python -m gel.models.p2_term
"""

from __future__ import annotations

import glob
import json
import math
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
from scipy import optimize

from gel.models import term_structure as ts

TABLES, FIGURES = Path("paper/tables"), Path("paper/figures")
OBS_DATE = date(2026, 11, 11)
R_GRID = (0.05, 0.08, 0.12)
PI_GRID = (0.0, 0.01, 0.02, 0.03)
CHIPS = ("a100_80gb", "h100_sxm", "h200", "l40s", "b200")
LABEL_OF = {"a100_80gb": "A100_SXM", "h100_sxm": "H100_SXM", "h200": "H200_SXM", "l40s": "L40S"}
HYPERSCALERS = {"aws", "azure", "google_cloud"}


def fit_constant_delta(tenors_m, ratios, r: float, pi: float) -> float:
    """Least-squares constant delta across tenors (months); NaN if no positive decay fits."""
    t = np.asarray(tenors_m, dtype=float) / 12.0
    y = np.asarray(ratios, dtype=float)
    if np.any(1 - pi * t <= 0):
        return math.nan
    target = y / (1 - pi * t)
    if np.all(target >= 1.0):
        return math.nan

    def resid(p):
        return [ts.flat_ratio(p[0], ti, r) - yi for ti, yi in zip(t, target, strict=True)]

    sol = optimize.least_squares(
        resid, x0=[0.2], bounds=([1e-6], [ts.DELTA_BRACKET[1]]), xtol=1e-14, ftol=1e-14, gtol=1e-14
    )
    d = float(sol.x[0])
    return math.nan if d <= 1e-5 else d


def life_opex_from_now(rent_now: float, opex: float, delta: float, age_now: float) -> float:
    if not (delta > 0) or rent_now is None or not math.isfinite(rent_now):
        return math.nan
    if rent_now <= opex:
        return age_now
    return age_now + math.log(rent_now / opex) / delta


def observed_ratios() -> pl.DataFrame:
    from gel.build.historical import load_history

    hist = load_history(Path("."))
    live = [pl.read_parquet(p) for p in sorted(glob.glob("data/interim/live/*/2026-11-*.parquet"))]
    df = pl.concat([hist, *live], how="diagonal_relaxed").with_columns(
        pl.col("retrieved_at").str.slice(0, 7).alias("month")
    )
    od = (
        df.filter(pl.col("contract_type") == "on_demand")
        .group_by("provider", "chip", "month")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("r0"))
    )
    term = (
        df.filter(
            pl.col("contract_type").is_in(["reserved_1y", "reserved_3y"])
            | ((pl.col("contract_type") == "other") & (pl.col("term_months") == 60))
        )
        .group_by("provider", "chip", "month", "term_months")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("f"))
    )
    j = term.join(od, on=["provider", "chip", "month"]).with_columns(
        (pl.col("f") / pl.col("r0")).alias("ratio"),
        pl.when(pl.col("provider").is_in(list(HYPERSCALERS)))
        .then(pl.lit("hyperscaler"))
        .otherwise(pl.lit("neocloud"))
        .alias("provider_type"),
    )
    return (
        j.filter(pl.col("chip").is_in(list(CHIPS)))
        .group_by("chip", "provider_type", "term_months")
        .agg(
            pl.col("ratio").median().alias("observed_ratio"),
            pl.len().alias("n_obs"),
            pl.col("provider").unique().sort().str.join(",").alias("providers"),
        )
        .sort("chip", "provider_type", "term_months")
    )


def chip_inputs() -> dict:
    from gel.viz import style

    cal = json.loads(Path("data/processed/p3_calibration.json").read_text())
    market = json.loads(Path("data/processed/p3_market.json").read_text())
    epoch = pl.read_csv(
        max(glob.glob("data/raw/indices/epoch/*/*-ml_hardware.csv")), infer_schema_length=0
    )
    dates = style.release_dates()
    panel = pl.read_parquet("data/processed/spot_panel.parquet").filter(
        pl.col("billing") == "on_demand"
    )
    e, pue = market["electricity"]["mean_usd_kwh"], 1.3
    out = {}
    for chip in CHIPS:
        lab = LABEL_OF.get(chip)
        g = cal["best_available"]["gpus"].get(lab) if lab else None
        name = style.EPOCH_NAMES.get(chip)
        hit = epoch.filter(pl.col("Hardware name") == name) if name else pl.DataFrame()
        price = hit["Release price (USD)"][0] if not hit.is_empty() else None
        capex = float(price) if price not in (None, "") else None
        power = e * pue * g["w_load"] / 1000.0 if g else None
        maint = 0.04 * capex / 8760.0 if capex else 0.0
        rel = dates.get(chip)
        rents = {}
        for ptype in ("neocloud", "hyperscaler"):
            p = panel.filter((pl.col("chip_id") == chip) & (pl.col("provider_type") == ptype))
            rents[ptype] = float(p["price_per_gpu_hr"].median()) if not p.is_empty() else None
        out[chip] = {
            "age_now": (OBS_DATE - date.fromisoformat(rel)).days / 365.25 if rel else math.nan,
            "opex_hr": (power + maint) if power is not None else math.nan,
            "opex_basis": ("power+maintenance" if capex else "power only") if power else "n/a",
            "rent_now": rents,
        }
    return out


def implied_table(obs: pl.DataFrame, inputs: dict) -> pl.DataFrame:
    rows = []
    for (chip, ptype), g in obs.group_by(["chip", "provider_type"], maintain_order=True):
        tenors, ratios = g["term_months"].to_list(), g["observed_ratio"].to_list()
        inp = inputs[chip]
        for r in R_GRID:
            for pi in PI_GRID:
                d = fit_constant_delta(tenors, ratios, r, pi)
                rows.append(
                    {
                        "chip": chip,
                        "provider_type": ptype,
                        "tenors_m": ",".join(str(t) for t in tenors),
                        "ratios": ",".join(f"{x:.3f}" for x in ratios),
                        "n_obs": int(g["n_obs"].sum()),
                        "r": r,
                        "pi": pi,
                        "delta": d,
                        "L50_y": math.log(2) / d if d == d else math.nan,
                        "age_now_y": inp["age_now"],
                        "rent_now": inp["rent_now"][ptype],
                        "opex_hr": inp["opex_hr"],
                        "opex_basis": inp["opex_basis"],
                        "L_opex_y": life_opex_from_now(
                            inp["rent_now"][ptype] or math.nan, inp["opex_hr"], d, inp["age_now"]
                        ),
                    }
                )
    return pl.DataFrame(rows)


def level4_table(obs: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for (chip, ptype), g in obs.group_by(["chip", "provider_type"], maintain_order=True):
        if g.height < 3:
            continue
        fit = ts.fit_age_varying(
            np.array(g["term_months"].to_list()) / 12.0,
            np.array(g["observed_ratio"].to_list()),
            r=0.08,
        )
        rows.append(
            {
                "chip": chip,
                "provider_type": ptype,
                "level": fit.level,
                "beta0": fit.beta0,
                "beta1": fit.beta1,
                "tau": fit.tau,
                "rmse": fit.rmse,
                "L50_y": ts.life_half(fit.beta0, fit.beta1, fit.tau),
            }
        )
    return pl.DataFrame(rows)


def main() -> int:
    from gel.viz import p2_figures

    obs = observed_ratios()
    inputs = chip_inputs()
    table = implied_table(obs, inputs)
    l4 = level4_table(obs)
    TABLES.mkdir(parents=True, exist_ok=True)
    obs.write_csv(TABLES / "p2_observed_ratios.csv")
    table.write_csv(TABLES / "p2_implied_decay.csv")
    l4.write_csv(TABLES / "p2_level4.csv")
    p2_figures.render(obs, table, l4)
    pl.Config.set_tbl_rows(40)
    pl.Config.set_tbl_width_chars(220)
    print(obs.with_columns(pl.col("observed_ratio").round(3)))
    base = table.filter((pl.col("r") == 0.08) & (pl.col("pi") == 0.0))
    print(
        base.select(
            "chip",
            "provider_type",
            "tenors_m",
            "ratios",
            pl.col("delta").round(3),
            pl.col("L50_y").round(2),
            pl.col("age_now_y").round(2),
            "rent_now",
            pl.col("opex_hr").round(3),
            "opex_basis",
            pl.col("L_opex_y").round(2),
        )
    )
    print(l4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
