"""Calibrate P3's market processes from data (Decision 12).

Writes data/processed/p3_market.json. Every value carries its provenance.

- Electricity e(t): Form EIA-861M monthly industrial revenue / sales, US total (and Virginia for
  sensitivity), last 10 years. Mean = last 12 months; OU kappa and sigma from an AR(1) on the
  deseasonalised log price, sigma converted to $/kWh at the mean.
- Scarcity markup m(t) = rent / (H100 all-in cost per sold GPU-hour) - 1, where the cost uses
  the same capex, annuity, power and maintenance assumptions as the model.
  Level: mean of Lambda's H100 on-demand markup while the H100 was the frontier (first listing
  to the month before the first B200 listing). Dynamics: AR(1) on log AWS spot H100 prices, the
  only series in the panel that moves like a market price; sigma converted to markup units at
  the level. Boom ("2026-like"): Lambda's latest H100 on-demand markup.
- sigma_G: standard deviation of log peak-spec efficiency steps (BF16 FLOP/s per TDP watt)
  between NVIDIA data-centre architectures, Epoch AI hardware data.
- Regime persistence: a constrained spell lasts as long as a grid-interconnection wait, median
  "over 4 years" (LBNL Queued Up 2025 edition), so p_stay_constrained = 1 - 1/48. Unconstrained
  spells are a judgement: half that length (24 months), as new capacity is absorbed faster
  than it is built.

Usage: uv run python -m gel.models.p3_market_calibration
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import openpyxl
import polars as pl
import yaml

from gel.models import retirement_model as rm

OUT = Path("data/processed/p3_market.json")
EIA_GLOB = "data/raw/eia/*/*-eia861m_sales_revenue.xlsx"
EPOCH_GLOB = "data/raw/indices/epoch/*/*-ml_hardware.csv"
ARCHITECTURES = [
    "NVIDIA Tesla V100 SXM2",
    "NVIDIA A100 SXM4 40 GB",
    "NVIDIA H100 SXM5 80GB",
    "NVIDIA B200",
]
LBNL_MEDIAN_QUEUE_MONTHS = 48  # "over 4 years for those built in 2018-2024" (Queued Up 2025)
UNCONSTRAINED_SPELL_MONTHS = 24  # judgement, Decision 12
FAILURE_CSV = Path("data/raw/manual/gpu_failure_evidence.csv")
# Decision 12 judgement: a constant 2%/yr hazard of PERMANENT loss. Incident rates on modern GPUs
# (8-11%/GPU-year) are an upper bound, because many incidents end in a reset, row remap or
# warranty swap rather than the asset's retirement. Titan (Ostrouchov et al., SC20) found neither
# infant mortality nor wear-out over five years, which supports a constant hazard (shape 1).
BASE_ANNUAL_FAILURE_HAZARD = 0.02
LOW_ANNUAL_FAILURE_HAZARD = 0.005


def ou_fit(x: np.ndarray, dt: float = 1.0 / 12.0) -> tuple[float, float, float]:
    """Fit the model's Euler-discretised OU to an evenly spaced series: (mean, kappa, sigma)."""
    x = np.asarray(x, dtype=float)
    x0, x1 = x[:-1], x[1:]
    a_mat = np.column_stack([np.ones_like(x0), x0])
    (a, phi), *_ = np.linalg.lstsq(a_mat, x1, rcond=None)
    phi = float(np.clip(phi, 1e-6, 1 - 1e-6))
    resid = x1 - (a + phi * x0)
    # Same Euler step as retirement_model.ou_path: phi = 1 - kappa dt, eps sd = sigma sqrt(dt)
    kappa = (1.0 - phi) / dt
    sd = float(resid.std(ddof=2)) if len(resid) > 2 else 0.0
    sigma = sd / math.sqrt(dt)
    return float(a / (1 - phi)), kappa, sigma


def deseasonalize(x: np.ndarray, months: np.ndarray) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    out = x.copy()
    for m in np.unique(months):
        sel = months == m
        out[sel] = x[sel] - x[sel].mean() + x.mean()
    return out


def cost_per_sold_hour(K, r, n, e, pue, w_load, w_idle, u, maint_frac) -> float:
    a = rm.annuity_payment(K, r, n)
    _, opex, _ = rm.monthly_economics(0.0, 1.0, u, e, w_load, w_idle, pue, maint_frac * K / 12.0)
    return (a + opex) / (rm.HOURS_PER_MONTH * u)


def markup(price: float, cost: float) -> float:
    return price / cost - 1.0


def electricity(path: Path) -> dict:
    ws = openpyxl.load_workbook(path, read_only=True)["Monthly-States"]
    rows = []
    for row in ws.iter_rows(min_row=4, values_only=True):
        if not isinstance(row[0], int | float):
            continue
        rows.append(
            {
                "year": int(row[0]),
                "month": int(row[1]),
                "state": row[2],
                "rev_k": row[12] or 0.0,
                "mwh": row[13] or 0.0,
            }
        )
    df = pl.DataFrame(rows)

    def series(frame):
        s = (
            frame.group_by("year", "month")
            .agg(pl.col("rev_k").sum(), pl.col("mwh").sum())
            .with_columns((pl.col("rev_k") / pl.col("mwh")).alias("usd_kwh"))
            .sort("year", "month")
        )
        return s.tail(120)

    us, va = series(df), series(df.filter(pl.col("state") == "VA"))
    logp = np.log(us["usd_kwh"].to_numpy())
    _, kappa, sigma_log = ou_fit(deseasonalize(logp, us["month"].to_numpy()))
    mean = float(us["usd_kwh"].tail(12).mean())
    return {
        "mean_usd_kwh": mean,
        "kappa": kappa,
        "sigma_usd_kwh": sigma_log * mean,
        "virginia_mean_usd_kwh": float(va["usd_kwh"].tail(12).mean()),
        "window": f"{us['year'][0]}-{us['month'][0]:02d} to {us['year'][-1]}-{us['month'][-1]:02d}",
        "source": str(path),
    }


def price_series(history: pl.DataFrame, provider: str, contract: str) -> pl.DataFrame:
    return (
        history.filter(
            (pl.col("chip") == "h100_sxm")
            & (pl.col("provider") == provider)
            & (pl.col("contract_type") == contract)
        )
        .with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
        .group_by("month")
        .agg(pl.col("price_usd_per_gpu_hour").median().alias("p"))
        .sort("month")
    )


def markup_calibration(history: pl.DataFrame, cost: float) -> dict:
    hm = history.with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
    b200_first = hm.filter(pl.col("chip") == "b200")["month"].min()
    lam = price_series(history, "lambda", "on_demand")
    frontier = lam.filter(pl.col("month") < b200_first)
    level = float((frontier["p"] / cost - 1.0).mean())
    spot = price_series(history, "aws", "spot")
    _, kappa, sigma_log = ou_fit(np.log(spot["p"].to_numpy()))
    boom_row = lam.tail(1).row(0, named=True)
    return {
        "cost_h100_per_sold_hour": cost,
        "mean": level,
        "level_window": f"{frontier['month'][0]} to {frontier['month'][-1]} (Lambda H100 OD)",
        "kappa": kappa,
        "sigma": sigma_log * (1.0 + level),
        "dynamics_window": f"{spot['month'][0]} to {spot['month'][-1]} (AWS spot H100)",
        "boom_mean": markup(boom_row["p"], cost),
        "boom_basis": f"Lambda H100 on-demand ${boom_row['p']:.2f} in {boom_row['month']}",
        "first_b200_month": b200_first,
    }


def sigma_g_from_epoch(path: Path) -> dict:
    df = pl.read_csv(path, infer_schema_length=0)
    eff = []
    for name in ARCHITECTURES:
        r = df.filter(pl.col("Hardware name") == name).row(0, named=True)
        eff.append(float(r["Tensor-FP16/BF16 performance (FLOP/s)"]) / float(r["TDP (W)"]))
    steps = np.diff(np.log(eff))
    return {
        "sigma_G": float(steps.std(ddof=1)),
        "spec_mean_log_step": float(steps.mean()),
        "steps": [float(s) for s in steps],
        "source": str(path),
    }


def failure_evidence(path: Path = FAILURE_CSV) -> dict:
    """Annualised GPU incident rates from published field studies (upper bounds on removal)."""
    ev = pl.read_csv(path)
    rates = {}
    for r in ev.iter_rows(named=True):
        if r["unit"] == "count":
            rates[r["source_id"]] = r["value"] / (r["exposure_gpus"] * r["exposure_days"] / 365.25)
        elif r["unit"] == "hours per GPU":
            rates[r["source_id"]] = 365.25 * 24 / r["value"]
    upper = max(rates["llama3_gpu_all"], rates["delta_h100_mtbe"])
    return {
        "incident_rates_per_gpu_year": rates,
        "upper_bound_annual_hazard": upper,
        "base_annual_hazard": BASE_ANNUAL_FAILURE_HAZARD,
        "low_annual_hazard": LOW_ANNUAL_FAILURE_HAZARD,
        "basis": "base and low are judgements (Decision 12); upper = highest H100 incident rate",
        "source": str(path),
    }


def calibrate(cfg: dict, calibration: dict, capex: dict, history: pl.DataFrame) -> dict:
    elec = electricity(Path(max(glob.glob(EIA_GLOB))))
    g0 = calibration[cfg["hardware"]["comparison"]]["gpus"][cfg["hardware"]["generation0"]]
    mk = cfg["market"]
    cost = cost_per_sold_hour(
        capex["K0_usd"],
        mk["discount_rate_annual"],
        mk["annuity_months"],
        elec["mean_usd_kwh"],
        mk["pue"],
        g0["w_load"],
        g0["w_idle"],
        mk["utilization"],
        cfg["maintenance_fraction_of_capex_per_year"],
    )
    return {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "electricity": elec,
        "markup": markup_calibration(history, cost),
        "generation_step": sigma_g_from_epoch(Path(max(glob.glob(EPOCH_GLOB)))),
        "failure": failure_evidence(),
        "regime": {
            "p_stay_constrained": 1.0 - 1.0 / LBNL_MEDIAN_QUEUE_MONTHS,
            "p_stay_unconstrained": 1.0 - 1.0 / UNCONSTRAINED_SPELL_MONTHS,
            "basis": "LBNL Queued Up 2025 (median IR-to-COD over 4 years, 2018-2024 builds); "
            "unconstrained spell 24 months is a judgement",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Calibrate P3 market processes from data.")
    ap.add_argument("--config", type=Path, default=Path("config/p3_model.yaml"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    from gel.build.historical import load_history

    cfg = yaml.safe_load(args.config.read_text())
    cal = json.loads(Path(cfg["hardware"]["calibration_file"]).read_text())
    capex = json.loads(Path(cfg["capex"]["source_file"]).read_text())
    out = calibrate(cfg, cal, capex, load_history(Path(".")))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    e, m, g, r = out["electricity"], out["markup"], out["generation_step"], out["regime"]
    print(f"wrote {args.out}")
    print(
        f"electricity: mean ${e['mean_usd_kwh']:.4f}/kWh (VA ${e['virginia_mean_usd_kwh']:.4f}),"
        f" kappa {e['kappa']:.2f}, sigma ${e['sigma_usd_kwh']:.4f} [{e['window']}]"
    )
    print(
        f"markup: H100 cost ${m['cost_h100_per_sold_hour']:.3f}/sold h; mean {m['mean']:.2f} "
        f"[{m['level_window']}]; kappa {m['kappa']:.2f}, sigma {m['sigma']:.2f} "
        f"[{m['dynamics_window']}]; boom {m['boom_mean']:.2f} ({m['boom_basis']})"
    )
    print(
        f"sigma_G {g['sigma_G']:.3f} (spec mean step x{math.exp(g['spec_mean_log_step']):.2f}); "
        f"regime stay c {r['p_stay_constrained']:.4f}, u {r['p_stay_unconstrained']:.4f}"
    )
    f = out["failure"]
    print(
        "failure incident rates/GPU-yr: "
        + ", ".join(f"{k} {v:.3f}" for k, v in f["incident_rates_per_gpu_year"].items())
        + f"; upper {f['upper_bound_annual_hazard']:.3f}, base {f['base_annual_hazard']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
