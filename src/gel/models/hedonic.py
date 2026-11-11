"""Phase 5 hedonic age profiles and identification strategies (Decision 23).

Reads data/processed/panel.parquet and data/processed/chips.parquet. Every specification here is
logged in docs/decisions.md (Decision 23); the estimation engine is gel.models.hedonic_core.

Usage: uv run python -m gel.models.hedonic   (writes paper/tables/p5_*.csv and .tex)
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from gel.models import hedonic_core as hc

PANEL = Path("data/processed/panel.parquet")
CHIPS = Path("data/processed/chips.parquet")
CAPEX = Path("data/processed/p3_capex.json")
TABLES = Path("paper/tables")

SAMPLE_CHIPS = ["v100", "a100_40gb", "a100_80gb", "h100_pcie", "h100_sxm", "h200", "b200"]
CONTROLS = ["prov_region", "contract_term", "gpu_count", "price_basis", "form_factor"]
KNOTS = [1.5, 3.0, 5.0]
BIN_MONTHS = 6
CURVATURE = ["age2", "age3", *[f"knot{i}" for i in range(len(KNOTS))]]
SPLINE = ["age1", *CURVATURE]
# Predecessor chip -> successor chip whose Epoch release month is the event date.
EVENTS = {
    "v100": "a100_40gb",
    "a100_40gb": "h100_sxm",
    "a100_80gb": "h100_sxm",
    "h100_sxm": "b200",
    "h100_pcie": "b200",
}
EVENT_BINS = [(-18, -13), (-12, -7), (-6, -1), (0, 5), (6, 11), (12, 17)]
EVENT_REF = (-6, -1)
DELTAS = [0.0, -0.05, -0.10, -0.15, -0.20, -0.25, -0.30, -0.35, -0.40]
SUBPERIODS = {
    "to_2022": (date(2000, 1, 1), date(2022, 12, 1)),
    "2023_2025": (date(2023, 1, 1), date(2025, 12, 1)),
    "from_2026": (date(2026, 1, 1), date(2100, 1, 1)),
}
CONTRACTS = ["on_demand", "spot", "reserved_1y", "reserved_3y"]
DRAWS = 9999
# Below this many chips the chip-level bootstrap is not reported (review_01 point 7).
MIN_CLUSTERS = 6


def spline_basis(age: np.ndarray) -> dict[str, np.ndarray]:
    a = np.asarray(age, dtype=float)
    out = {"age1": a, "age2": a**2, "age3": a**3}
    for i, k in enumerate(KNOTS):
        out[f"knot{i}"] = np.clip(a - k, 0, None) ** 3
    return out


def load_sample(
    panel: pl.DataFrame | None = None, chips: pl.DataFrame | None = None
) -> pl.DataFrame:
    panel = pl.read_parquet(PANEL) if panel is None else panel
    chips = pl.read_parquet(CHIPS) if chips is None else chips
    df = panel.filter(
        pl.col("chip").is_in(SAMPLE_CHIPS)
        & pl.col("age_months").is_not_null()
        & ~pl.col("price_outlier")
        & pl.col("price_usd_per_gpu_hour_real2025").is_not_null()
    )
    rel = chips.filter(pl.col("release_date").is_not_null()).select(
        pl.col("release_date").dt.truncate("1mo").alias("rm"), "tensor_fp16_bf16_tflops"
    )
    frontier = {
        m: float(rel.filter(pl.col("rm") <= m)["tensor_fp16_bf16_tflops"].max() or np.nan)
        for m in df["month"].unique().to_list()
    }
    df = df.with_columns(
        pl.col("price_usd_per_gpu_hour_real2025").log().alias("y"),
        (pl.col("age_months") / 12.0).alias("age"),
        (pl.col("age_months") // BIN_MONTHS).alias("age_bin"),
        pl.concat_str(["provider", "region"], separator=":").alias("prov_region"),
        pl.concat_str(
            ["contract_type", pl.col("term_months").cast(pl.String)], separator=":"
        ).alias("contract_term"),
        pl.col("tensor_fp16_bf16_tflops").log().alias("ln_tflops"),
        pl.col("memory_bw_tbs").log().alias("ln_bw"),
        pl.col("memory_gb").log().alias("ln_mem"),
        pl.col("month").replace_strict(frontier, return_dtype=pl.Float64).alias("frontier_tflops"),
    ).with_columns(
        (pl.col("ln_tflops") - pl.col("frontier_tflops").log()).alias("rel_frontier"),
        pl.concat_str(["provider", "chip", pl.col("month").cast(pl.String)]).alias("pcm"),
    )
    basis = spline_basis(df["age"].to_numpy())
    df = df.with_columns([pl.Series(k, v) for k, v in basis.items()])
    # Each provider-chip-month counts once in the weighted robustness run.
    df = df.with_columns((1.0 / pl.len().over("pcm")).alias("w_pcm"))
    return df


def bin_dummies(df: pl.DataFrame, by_chip: bool = False) -> tuple[pl.DataFrame, list[str]]:
    """6-month age-bin dummies. Pooled: reference bin 0. By chip: reference = each chip's first
    observed bin."""
    cols: list[str] = []
    exprs = []
    if not by_chip:
        for b in sorted(df["age_bin"].unique().to_list()):
            if b == 0:
                continue
            name = f"bin{b:02d}"
            exprs.append((pl.col("age_bin") == b).cast(pl.Float64).alias(name))
            cols.append(name)
    else:
        for chip in SAMPLE_CHIPS:
            bins = sorted(df.filter(pl.col("chip") == chip)["age_bin"].unique().to_list())
            for b in bins[1:]:
                name = f"{chip}__bin{b:02d}"
                exprs.append(
                    ((pl.col("chip") == chip) & (pl.col("age_bin") == b))
                    .cast(pl.Float64)
                    .alias(name)
                )
                cols.append(name)
    return df.with_columns(exprs), cols


def event_dummies(
    df: pl.DataFrame, successor_month: dict[str, date]
) -> tuple[pl.DataFrame, list[str]]:
    """Event-time bins for predecessor chips around their successor's release (pooled)."""
    ev = {c: successor_month[s] for c, s in EVENTS.items() if s in successor_month}
    tau = pl.lit(None, dtype=pl.Int32)
    for chip, d in ev.items():
        tau = (
            pl.when(pl.col("chip") == chip)
            .then(
                (pl.col("month").dt.year() - d.year) * 12
                + pl.col("month").dt.month().cast(pl.Int32)
                - d.month
            )
            .otherwise(tau)
        )
    df = df.with_columns(tau.alias("tau"))
    cols, exprs = [], []
    lo_end = EVENT_BINS[0][0]
    exprs.append((pl.col("tau") < lo_end).fill_null(False).cast(pl.Float64).alias("ev_pre_far"))
    cols.append("ev_pre_far")
    for lo, hi in EVENT_BINS:
        if (lo, hi) == EVENT_REF:
            continue
        name = f"ev_{lo:+d}_{hi:+d}"
        exprs.append(pl.col("tau").is_between(lo, hi).fill_null(False).cast(pl.Float64).alias(name))
        cols.append(name)
    exprs.append(
        (pl.col("tau") > EVENT_BINS[-1][1]).fill_null(False).cast(pl.Float64).alias("ev_post_far")
    )
    cols.append("ev_post_far")
    return df.with_columns(exprs), cols


# ---- summaries ------------------------------------------------------------------------------


def profile_row(fit: hc.Fit, age: float, include_linear: bool) -> np.ndarray:
    """r such that r'b = g(age) - g(0) for the spline terms present in the fit."""
    b = spline_basis(np.array([age]))
    w = {k: float(v[0]) for k, v in b.items() if include_linear or k != "age1"}
    return fit.combo(w)


MEASURES = {
    "d1": lambda f, lin: profile_row(f, 1.0, lin),
    "d2": lambda f, lin: profile_row(f, 2.0, lin),
    "d4": lambda f, lin: profile_row(f, 4.0, lin),
    "rate_0_2": lambda f, lin: profile_row(f, 2.0, lin) / 2.0,
    "rate_2_4": lambda f, lin: (profile_row(f, 4.0, lin) - profile_row(f, 2.0, lin)) / 2.0,
    "early_minus_late_rate": lambda f, lin: (
        profile_row(f, 2.0, lin) / 2.0 - (profile_row(f, 4.0, lin) - profile_row(f, 2.0, lin)) / 2.0
    ),
}


def _ids(df: pl.DataFrame, col: str) -> np.ndarray:
    return hc._codes(df, [col]).ravel().astype(np.int64)


def infer(
    fit: hc.Fit,
    df: pl.DataFrame,
    rs: dict[str, np.ndarray],
    draws: int = DRAWS,
    cluster: str = "chip",
) -> list[dict]:
    names = list(rs)
    mat = np.vstack([rs[n] for n in names])
    boot = hc.wild_cluster_bootstrap_many(fit, mat, _ids(df, cluster), draws=draws)
    prov, month = _ids(df, "provider"), _ids(df, "month")
    out = []
    for n, r, b in zip(names, mat, boot, strict=True):
        out.append(
            {
                "measure": n,
                "estimate": b.estimate,
                "wcb_ci_low": b.ci_low,
                "wcb_ci_high": b.ci_high,
                "wcb_p": b.p_value,
                "se_cr1_cluster": b.se_cr1,
                "se_cr1_provider": hc.cr1_se(fit, r, prov),
                "se_twoway_provider_month": hc.twoway_se(fit, r, prov, month),
                "clusters": b.clusters,
                "p_floor": 1.0 / (draws + 1),
                "cluster_var": cluster,
            }
        )
    return out


@dataclass
class Spec:
    name: str
    x: list[str]
    fe: list[str]
    linear_identified: bool
    assumption: str


SPECS = {
    "s1a_tflops": Spec(
        "s1a_tflops",
        ["ln_tflops", *SPLINE],
        ["month", *CONTROLS],
        True,
        "vintage effect = f(ln BF16 TFLOP/s); no chip effects",
    ),
    "s1b_three_specs": Spec(
        "s1b_three_specs",
        ["ln_tflops", "ln_bw", "ln_mem", *SPLINE],
        ["month", *CONTROLS],
        True,
        "vintage effect = f(ln TFLOP/s, ln bandwidth, ln memory); no chip effects",
    ),
    "s2_frontier": Spec(
        "s2_frontier",
        ["rel_frontier", *SPLINE],
        ["chip", *CONTROLS],
        True,
        "time effects act only through the frontier-relative performance term",
    ),
    "s4_shape": Spec(
        "s4_shape",
        CURVATURE,
        ["chip", "month", *CONTROLS],
        False,
        "chip + month effects; curvature only, linear term assumed (swept)",
    ),
}


def run_spec(
    spec: Spec, df: pl.DataFrame, weights: str | None = None, draws: int = DRAWS
) -> tuple[hc.Fit, list[dict]]:
    fit = hc.fit_ols(df, "y", spec.x, spec.fe, weights=weights)
    # Without an identified linear term only the shape measure is meaningful; cumulative changes
    # for strategy 4 come from the sweep over assumed linear terms.
    keep = (
        MEASURES
        if spec.linear_identified
        else {"early_minus_late_rate": MEASURES["early_minus_late_rate"]}
    )
    rs = {m: f(fit, spec.linear_identified) for m, f in keep.items()}
    if "rel_frontier" in fit.names:
        rs["coef_rel_frontier"] = fit.combo({"rel_frontier": 1.0})
    if "ln_tflops" in fit.names:
        rs["coef_ln_tflops"] = fit.combo({"ln_tflops": 1.0})
    rows = infer(fit, df, rs, draws=draws)
    span = df.group_by("chip").agg((pl.col("age").max() - pl.col("age").min()).alias("s"))["s"]
    for r in rows:
        r.update(
            within_chip_age_span_max=float(span.max()),
            extrapolated=spec.fe[:1] == ["chip"] and float(span.max()) < 4.0,
            spec=spec.name,
            n=fit.n,
            dropped=";".join(fit.dropped),
            condition=fit.condition,
            linear_identified=spec.linear_identified,
        )
    return fit, rows


def profile_curve(fit: hc.Fit, df: pl.DataFrame, spec: str, draws: int = DRAWS) -> pl.DataFrame:
    """g(a) - g(0) on a 0.25-year grid to 6 years, for a spec whose linear term is identified."""
    ages = np.round(np.arange(0.25, 6.01, 0.25), 2)
    rs = {f"{a:.2f}": profile_row(fit, float(a), include_linear=True) for a in ages}
    rows = [
        {
            "spec": spec,
            "age": float(r["measure"]),
            "g": r["estimate"],
            "ci_low": r["wcb_ci_low"],
            "ci_high": r["wcb_ci_high"],
        }
        for r in infer(fit, df, rs, draws=draws)
    ]
    zero = pl.DataFrame(
        {"spec": [spec], "age": [0.0], "g": [0.0], "ci_low": [0.0], "ci_high": [0.0]}
    )
    return pl.concat([zero, pl.DataFrame(rows)])


SWEEP_AGES = np.round(np.arange(0.0, 6.01, 0.25), 2)


def detrended_curvature_rows(fit: hc.Fit) -> dict[float, np.ndarray]:
    """r(a) with r(a)'b = c(a) - c(0) - beta_c * a, where beta_c is the least-squares slope of
    c(a) on the age grid 0-6. Removing that slope makes an assumed linear term d equal to the
    average annual log change over ages 0-6 (Decision 23, amendment)."""
    ages = SWEEP_AGES
    raw = {float(a): profile_row(fit, float(a), include_linear=False) for a in ages}
    abar = ages.mean()
    denom = float(np.sum((ages - abar) ** 2))
    r_beta = sum((float(a) - abar) * raw[float(a)] for a in ages) / denom
    return {float(a): raw[float(a)] - float(a) * r_beta for a in ages}


def strategy4_sweep(fit: hc.Fit, df: pl.DataFrame, draws: int = DRAWS) -> pl.DataFrame:
    """g_d(a) = d*a + detrended curvature(a) over the d grid; CI from the curvature part."""
    rows_r = detrended_curvature_rows(fit)
    rs = {f"a{a:.2f}": r for a, r in rows_r.items() if a > 0}
    res = {r["measure"]: r for r in infer(fit, df, rs, draws=draws)}
    rows = []
    for d in DELTAS:
        for a in SWEEP_AGES:
            if a == 0:
                rows.append({"delta": d, "age": 0.0, "g": 0.0, "ci_low": 0.0, "ci_high": 0.0})
                continue
            r = res[f"a{a:.2f}"]
            rows.append(
                {
                    "delta": d,
                    "age": float(a),
                    "g": d * a + r["estimate"],
                    "ci_low": d * a + r["wcb_ci_low"],
                    "ci_high": d * a + r["wcb_ci_high"],
                    "curvature_only": r["estimate"],
                }
            )
    return pl.DataFrame(rows, infer_schema_length=None)


def baseline_bins(df: pl.DataFrame, draws: int = DRAWS) -> tuple[pl.DataFrame, dict]:
    d, cols = bin_dummies(df)
    fit = hc.fit_ols(d, "y", cols, ["chip", "month", *CONTROLS])
    rs = {c: fit.combo({c: 1.0}) for c in fit.names}
    rows = infer(fit, d, rs, draws=draws)
    out = pl.DataFrame(rows).with_columns(
        (pl.col("measure").str.slice(3).cast(pl.Int32) * BIN_MONTHS).alias("age_months_from")
    )
    return out, {"dropped": fit.dropped, "condition": fit.condition, "n": fit.n}


def cohort_paths(df: pl.DataFrame, label: str) -> pl.DataFrame:
    """Observed path of each chip, no month effects: chip x bin dummies plus controls, relative to
    the chip's first bin. Inference: CR1 by provider-region (within-chip paths have one chip)."""
    d, cols = bin_dummies(df, by_chip=True)
    fit = hc.fit_ols(d, "y", cols, ["chip", *CONTROLS])
    pr = _ids(d, "prov_region")
    rows = []
    for c in fit.names:
        chip, b = c.split("__bin")
        r = fit.combo({c: 1.0})
        se = hc.cr1_se(fit, r, pr)
        est = float(r @ fit.coef)
        first = int(d.filter(pl.col("chip") == chip)["age_bin"].min())
        rows.append(
            {
                "sample": label,
                "chip": chip,
                "age_months_from": int(b) * BIN_MONTHS,
                "first_bin_months_from": first * BIN_MONTHS,
                "estimate": est,
                "ci_low": est - 1.96 * se,
                "ci_high": est + 1.96 * se,
                "se_cr1_prov_region": se,
                "n_bin": int(d[c].sum()),
            }
        )
    return pl.DataFrame(rows)


def event_study(
    df: pl.DataFrame, chips: pl.DataFrame, capex: dict, draws: int = DRAWS
) -> tuple[pl.DataFrame, pl.DataFrame]:
    succ = {
        r["chip_id"]: r["release_date"].replace(day=1)
        for r in chips.iter_rows(named=True)
        if r["release_date"] is not None
    }
    d, cols = event_dummies(df, succ)
    fit = hc.fit_ols(d, "y", [*cols, *CURVATURE], ["chip", "month", *CONTROLS])
    rs = {c: fit.combo({c: 1.0}) for c in cols if c in fit.names}
    post = [c for c in ("ev_+0_+5", "ev_+6_+11") if c in fit.names]
    rs["h2_first_year_after"] = fit.combo({c: 1.0 / len(post) for c in post})
    gap_years = float(np.mean([g["months"] for g in capex["architecture_gaps"]])) / 12.0
    rs["s3_implied_annual_rate"] = rs["h2_first_year_after"] / gap_years
    rows = infer(fit, d, rs, draws=draws)
    coefs = pl.DataFrame(rows).with_columns(pl.lit(gap_years).alias("mean_architecture_gap_years"))
    counts = (
        d.filter(pl.col("tau").is_not_null())
        .group_by("chip")
        .agg(pl.col("tau").min().alias("tau_min"), pl.col("tau").max().alias("tau_max"), pl.len())
        .sort("chip")
    )
    return coefs, counts


def run_all(draws: int = DRAWS) -> dict[str, pl.DataFrame]:
    df = load_sample()
    chips = pl.read_parquet(CHIPS)
    capex = json.loads(CAPEX.read_text())
    out: dict[str, pl.DataFrame] = {}

    # Observed cohort paths, with and without 2026.
    out["p5_cohort_paths"] = pl.concat(
        [
            cohort_paths(df, "all"),
            cohort_paths(df.filter(pl.col("month") < date(2026, 1, 1)), "pre_2026"),
        ]
    )

    # Strategies on the full sample, plus robustness runs.
    rows: list[dict] = []
    fits: dict[str, hc.Fit] = {}
    for name, spec in SPECS.items():
        fit, r = run_spec(spec, df, draws=draws)
        fits[name] = fit
        rows += [dict(x, sample="all") for x in r]
    for name in ("s1a_tflops", "s2_frontier", "s4_shape"):
        _, r = run_spec(SPECS[name], df, weights="w_pcm", draws=draws)
        rows += [dict(x, sample="weighted_provider_chip_month") for x in r]
        no_jul = df.filter(
            ~(
                (pl.col("provider") == "google_cloud")
                & (pl.col("month") == date(2026, 7, 1))
                & pl.col("collector").str.contains("skypilot")
            )
        )
        _, r = run_spec(SPECS[name], no_jul, draws=draws)
        rows += [dict(x, sample="drop_google_2026_07") for x in r]
        # H3: by contract type; H4: by sub-period.
        for ct in CONTRACTS:
            sub = df.filter(pl.col("contract_type") == ct)
            if sub["chip"].n_unique() >= MIN_CLUSTERS:
                _, r = run_spec(SPECS[name], sub, draws=draws)
                rows += [dict(x, sample=f"contract:{ct}") for x in r]
        for label, (lo, hi) in SUBPERIODS.items():
            sub = df.filter(pl.col("month").is_between(lo, hi))
            if sub["chip"].n_unique() >= MIN_CLUSTERS:
                _, r = run_spec(SPECS[name], sub, draws=draws)
                rows += [dict(x, sample=f"period:{label}") for x in r]
    out["p5_summary"] = pl.DataFrame(rows, infer_schema_length=None)

    out["p5_profiles"] = pl.concat(
        [
            profile_curve(fits[n], df, n, draws=draws)
            for n in ("s1a_tflops", "s1b_three_specs", "s2_frontier")
        ]
    )
    out["p5_strategy4_sweep"] = strategy4_sweep(fits["s4_shape"], df, draws=draws)
    bins, meta = baseline_bins(df, draws=draws)
    out["p5_baseline_bins"] = bins.with_columns(
        pl.lit(meta["condition"]).alias("condition"),
        pl.lit("diagnostic only: level set by the bin edges (review_01 point 4)").alias("note"),
        pl.lit(";".join(meta["dropped"])).alias("dropped"),
    )
    ev, counts = event_study(df, chips, capex, draws=draws)
    out["p5_event_study"] = ev
    out["p5_event_coverage"] = counts
    out["p5_sample"] = (
        df.group_by("chip")
        .agg(
            pl.len().alias("listing_months"),
            pl.col("provider").n_unique().alias("providers"),
            pl.col("month").min().alias("first_month"),
            pl.col("month").max().alias("last_month"),
            pl.col("age_months").min().alias("min_age_months"),
            pl.col("age_months").max().alias("max_age_months"),
        )
        .sort("chip")
    )
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or [])
    if argv and argv[0] == "sweep":  # recompute only the strategy 4 sweep table
        df = load_sample()
        fit = hc.fit_ols(df, "y", SPECS["s4_shape"].x, SPECS["s4_shape"].fe)
        strategy4_sweep(fit, df).write_csv(TABLES / "p5_strategy4_sweep.csv")
        print(f"wrote {TABLES / 'p5_strategy4_sweep.csv'}")
        return 0
    draws = int(argv[0]) if argv else DRAWS
    TABLES.mkdir(parents=True, exist_ok=True)
    out = run_all(draws=draws)
    for name, table in out.items():
        table.write_csv(TABLES / f"{name}.csv")
        print(f"wrote {TABLES / name}.csv ({table.height} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
