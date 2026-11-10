"""P3 Monte Carlo driver (handoff 5.2-5.3; Decisions 8 and 9).

Each path simulates a sequence of GPU generations launched at random intervals, a scarcity
markup m(t), an electricity price e(t) and a power regime S(t). The token price is the current
frontier GPU's all-in cost per token (annuitised capex + opex) times (1 + m). Every generation
launched within the tracking window is followed until it is retired:

  negative_margin  margin < 0 for `hold` consecutive months (applies in both regimes)
  obsolescence     power-constrained regime only: margin per kW below the frontier's
                   margin per kW net of its annuitised capex, for `hold` months
  failure          Weibull physical failure
  censored         still running at the horizon

Model property worth stating: with the price anchored at the frontier's full cost, the frontier
earns exactly A_f (1 + m) + m opex_f, so its margin net of capex is m (A_f + opex_f). With no
markup the obsolescence threshold is zero and the constrained rule adds nothing to the
negative-margin rule. The obsolescence channel is therefore driven by scarcity rents.

Usage: uv run python -m gel.models.monte_carlo [--scenarios base,power_abundant] [--n-paths N]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import polars as pl
import yaml

from gel.models import retirement_model as rm

CONFIG = Path("config/p3_model.yaml")
CHANNELS = ("negative_margin", "obsolescence", "failure", "censored")
BOOK_LIVES = (4.0, 5.0, 5.5, 6.0)


class MissingInput(ValueError):
    pass


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        out[k] = (
            deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
        )
    return out


def resolve(cfg: dict, calibration: dict | None = None) -> dict:
    """Fill calibrated values and refuse to proceed with unsourced (null) inputs."""
    missing = []
    if cfg["capex"]["K0_usd"] is None:
        missing.append("capex.K0_usd")
    if cfg["capex"]["growth_per_generation"] is None:
        missing.append("capex.growth_per_generation")
    if cfg["maintenance_usd_per_month"] is None:
        missing.append("maintenance_usd_per_month")
    if missing:
        raise MissingInput(
            "unsourced P3 inputs (CLAUDE.md rule 1): "
            + ", ".join(missing)
            + ". Fill them in config/p3_model.yaml with a logged source."
        )
    p = copy.deepcopy(cfg)
    hw = p["hardware"]
    if calibration is not None:
        c = calibration[hw["comparison"]]
        g0 = c["gpus"][hw["generation0"]]
        hw.setdefault("gen0", {})
        hw["gen0"] = {k: g0[k] for k in ("eta", "w_load", "idle_share")}
        if hw["mu_G"] == "from_calibration":
            hw["mu_G"] = c["mu_G"]
        if hw["power_step"] == "from_calibration":
            hw["power_step"] = c["power_step"]
    for key in ("mu_G", "power_step"):
        if not isinstance(hw[key], int | float):
            raise MissingInput(f"hardware.{key} unresolved; run gel.models.p3_calibration first")
    return p


def simulate(p: dict, seed: int | None = None) -> dict:
    rng = np.random.default_rng(p["seed"] if seed is None else seed)
    n, horizon = int(p["n_paths"]), int(p["horizon_months"])
    mk, hw = p["market"], p["hardware"]
    u, pue, r = mk["utilization"], mk["pue"], mk["discount_rate_annual"]
    maint = float(p["maintenance_usd_per_month"])
    months = np.asarray(p["cadence"]["months"])
    probs = np.asarray(p["cadence"]["probs"], dtype=float)
    probs = probs / probs.sum()
    g_max = int(math.ceil(horizon / months[probs > 0].min())) + 1

    # Generations: launch months, efficiency, power, throughput, capex.
    gaps = rng.choice(months, size=(n, g_max - 1), p=probs)
    launch = np.concatenate([np.zeros((n, 1), dtype=np.int64), np.cumsum(gaps, axis=1)], axis=1)
    log_g = rng.normal(hw["mu_G"], hw["sigma_G"], size=(n, g_max - 1))
    k = np.arange(g_max)
    eta = hw["gen0"]["eta"] * np.exp(np.concatenate([np.zeros((n, 1)), np.cumsum(log_g, 1)], 1))
    w = hw["gen0"]["w_load"] * hw["power_step"] ** k * np.ones((n, 1))
    idle = hw["gen0"]["idle_share"] * w
    q = eta * w
    capex = p["capex"]["K0_usd"] * p["capex"]["growth_per_generation"] ** k * np.ones((n, 1))
    ann = np.array([rm.annuity_payment(c, r, mk["annuity_months"]) for c in capex[0]])
    ann = ann * np.ones((n, 1))

    # Market state.
    m = rm.ou_path(rng, n, horizon, **p["markup"])
    e = rm.ou_path(rng, n, horizon, **p["electricity"])
    s = rm.markov_regime(rng, n, horizon, **p["regime"])

    t = np.arange(horizon)
    f = (launch[:, :, None] <= t[None, None, :]).sum(axis=1) - 1  # frontier index, (n, horizon)

    def at_f(x):
        return np.take_along_axis(x, f, axis=1)

    q_f, w_f, idle_f, ann_f = at_f(q), at_f(w), at_f(idle), at_f(ann)
    hours = rm.SECONDS_PER_HOUR * rm.HOURS_PER_MONTH
    _, opex_f, _ = rm.monthly_economics(0.0, q_f, u, e, w_f, idle_f, pue, maint)
    price = (ann_f + opex_f) / (q_f * hours * u) * (1.0 + m)  # $/token
    margin_f = price * q_f * hours * u - opex_f

    fail_scale = p["failure"]["scale_years"] * 12.0
    rows, margin_age, alive_age, rent_ratio, rent_valid = [], [], [], [], []
    for g in range(g_max):
        lg = launch[:, g]
        tracked = lg <= p["launch_window_months"]
        if not tracked.any():
            continue
        _, _, margin = rm.monthly_economics(
            price, q[:, g, None], u, e, w[:, g, None], idle[:, g, None], pue, maint
        )
        neg = margin < 0
        obs = s & (f != g) & rm.obsolete_in_power_slot(margin, w[:, g, None], margin_f, ann_f, w_f)
        t_neg = rm.first_sustained(neg, lg, p["hold_months"])
        t_econ = rm.first_sustained(neg | obs, lg, p["hold_months"])
        t_fail = lg + rm.weibull_failure_month(rng, n, fail_scale, p["failure"]["shape"])

        econ = np.where(t_econ >= 0, t_econ, np.iinfo(np.int64).max)
        fail_first = (t_fail <= econ) & (t_fail < horizon)
        retire = np.where(fail_first, t_fail, np.where(t_econ >= 0, t_econ, horizon))
        channel = np.where(
            fail_first,
            "failure",
            np.where(
                t_econ < 0, "censored", np.where(t_econ == t_neg, "negative_margin", "obsolescence")
            ),
        )
        idx = lg[:, None] + t[None, :]
        valid = idx < horizon
        idx_c = np.minimum(idx, horizon - 1)
        m_age = np.take_along_axis(margin, idx_c, axis=1) * valid / capex[:, g, None]
        a_age = valid & (idx < retire[:, None])
        rent = np.take_along_axis(price, idx_c, axis=1) * q[:, g, None] * rm.SECONDS_PER_HOUR
        sel = tracked
        rows.append(
            pl.DataFrame(
                {
                    "generation": np.full(sel.sum(), g),
                    "launch_month": lg[sel],
                    "retire_age_months": (retire - lg)[sel],
                    "channel": channel[sel],
                }
            )
        )
        margin_age.append(m_age[sel])
        alive_age.append(a_age[sel])
        rent_ratio.append((rent / rent[:, :1])[sel])
        rent_valid.append(valid[sel])

    return {
        "retirements": pl.concat(rows),
        "margin_by_age": np.concatenate(margin_age),
        "alive_by_age": np.concatenate(alive_age),
        "rent_ratio_by_age": np.concatenate(rent_ratio),
        "rent_valid_by_age": np.concatenate(rent_valid),
        "markup": m,
        "regime": s,
    }


def summarize(sim: dict, p: dict, scenario: str) -> dict:
    ret = sim["retirements"]
    ages_y = ret["retire_age_months"].to_numpy() / 12.0
    shares = {c: float((ret["channel"] == c).mean()) for c in CHANNELS}
    r = p["market"]["discount_rate_annual"]
    v = rm.value_by_age(sim["margin_by_age"], sim["alive_by_age"], r, ages=range(0, 121, 12))
    rv, ok = sim["rent_ratio_by_age"], sim["rent_valid_by_age"]
    rent_path = np.array(
        [rv[ok[:, a], a].mean() if ok[:, a].any() else np.nan for a in range(rv.shape[1])]
    )
    flat = {}
    for tenor in (12, 36, 60):
        d = (1.0 + rm.monthly_rate(r)) ** -np.arange(tenor)
        flat[tenor] = float(np.nansum(rent_path[:tenor] * d) / d.sum())
    return {
        "scenario": scenario,
        "n_tracked": len(ret),
        "retire_age_mean_y": float(ages_y.mean()),
        "retire_age_p10_y": float(np.percentile(ages_y, 10)),
        "retire_age_p50_y": float(np.percentile(ages_y, 50)),
        "retire_age_p90_y": float(np.percentile(ages_y, 90)),
        **{f"share_{c}": shares[c] for c in CHANNELS},
        "value_over_capex": {a // 12: v[a] for a in v},
        "rent_ratio_by_year": {
            y: float(rent_path[12 * y]) for y in range(0, 11) if 12 * y < len(rent_path)
        },
        "implied_flat_ratio": flat,
        "markup_mean": float(sim["markup"].mean()),
        "share_months_constrained": float(sim["regime"].mean()),
    }


def book_value(age_years: float, life: float) -> float:
    return max(0.0, 1.0 - age_years / life)


def run(cfg_path: Path, scenarios: list[str] | None, n_paths: int | None, out_dir: Path) -> list:
    cfg = yaml.safe_load(cfg_path.read_text())
    cal_path = Path(cfg["hardware"]["calibration_file"])
    calibration = json.loads(cal_path.read_text()) if cal_path.exists() else None
    names = scenarios or list(cfg["scenarios"])
    out = []
    for name in names:
        p = resolve(deep_merge(cfg, cfg["scenarios"][name]), calibration)
        if n_paths:
            p["n_paths"] = n_paths
        t0 = time.perf_counter()
        res = summarize(simulate(p), p, name)
        res["runtime_s"] = time.perf_counter() - t0
        print(
            f"{name}: median retirement {res['retire_age_p50_y']:.2f} y "
            f"(P10 {res['retire_age_p10_y']:.2f}, P90 {res['retire_age_p90_y']:.2f}); "
            f"channels "
            + ", ".join(f"{c} {res['share_' + c]:.2f}" for c in CHANNELS)
            + f"; {res['runtime_s']:.1f}s"
        )
        out.append(res)
    out_dir.mkdir(parents=True, exist_ok=True)
    flat_cols = [k for k in out[0] if not isinstance(out[0][k], dict)]
    pl.DataFrame([{k: r[k] for k in flat_cols} for r in out]).write_csv(
        out_dir / "p3_retirement_by_scenario.csv"
    )
    curves = [
        {
            "scenario": r["scenario"],
            "age_years": a,
            "economic_value_over_capex": val,
            **{f"book_sl_{life}y": book_value(a, life) for life in BOOK_LIVES},
        }
        for r in out
        for a, val in r["value_over_capex"].items()
    ]
    pl.DataFrame(curves).write_csv(out_dir / "p3_value_vs_book.csv")
    (out_dir / "p3_summary.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(f"wrote {out_dir}/p3_retirement_by_scenario.csv, p3_value_vs_book.csv, p3_summary.json")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the P3 retirement Monte Carlo.")
    ap.add_argument("--config", type=Path, default=CONFIG)
    ap.add_argument("--scenarios", default=None, help="comma-separated; default all")
    ap.add_argument("--n-paths", type=int, default=None)
    ap.add_argument("--out-dir", type=Path, default=Path("paper/tables"))
    args = ap.parse_args(argv)
    try:
        run(
            args.config,
            args.scenarios.split(",") if args.scenarios else None,
            args.n_paths,
            args.out_dir,
        )
    except MissingInput as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
