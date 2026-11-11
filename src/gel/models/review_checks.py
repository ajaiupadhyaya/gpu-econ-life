"""Checks requested by the Phase 5 adversarial review, docs/review_01.md points 1, 4 and 7.

Point 1  identification of the strategy 4 shape: (a) chip-specific linear time trends, (b) the
         chip time slopes against release date, (c) randomization inference over release dates.
Point 4  sensitivity of the pooled 6-month-bin baseline to where the bin edges fall.
Point 7  restricted wild bootstrap (WCR) p-values, a test-inversion interval for the shape, and a
         Monte Carlo of interval coverage on this panel's design.
Extra    points 3 (repricing), 5 (frontier variants), 6 (event dating), 8 (weighting), 9 (leave
         one chip out), 13 (nominal cohort paths) and the shortage-window check; point estimates
         with CR1-by-provider standard errors (indicative only, 6 clusters).

Outputs paper/tables/p5_review_*.csv. Usage:
    uv run python -W ignore -m gel.models.review_checks [trends|perm|bins|wcr|mc|extra|all]
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import polars as pl

from gel.models import hedonic as h
from gel.models import hedonic_core as hc

TABLES = Path("paper/tables")
S4_FE = ["chip", "month", *h.CONTROLS]


def _shape_row(fit: hc.Fit) -> np.ndarray:
    return h.MEASURES["early_minus_late_rate"](fit, False)


def _time_years(df: pl.DataFrame) -> pl.Expr:
    first = df["month"].min()
    return (
        (pl.col("month").dt.year() - first.year) * 12
        + pl.col("month").dt.month().cast(pl.Int32)
        - first.month
    ) / 12.0


# ---- point 1 ----------------------------------------------------------------------------------


def chip_trend_check(df: pl.DataFrame) -> pl.DataFrame:
    """Strategy 4 with a linear time trend per chip. The a^2 coefficient is then not identified
    (a^2 = t^2 - 2vt + v^2 and -2vt is a chip trend), so the shape is reported as a function of an
    assumed a^2 coefficient c2; the identified part comes from the cubic and knot terms."""
    chips = h.SAMPLE_CHIPS
    d = df.with_columns(_time_years(df).alias("t"))
    trends = []
    for c in chips[1:]:
        d = d.with_columns(((pl.col("chip") == c).cast(pl.Float64) * pl.col("t")).alias(f"tr_{c}"))
        trends.append(f"tr_{c}")
    # Trends enter first so the collinearity check drops age2 (the unidentified term), not a trend.
    fit = hc.fit_ols(d, "y", [*trends, *h.CURVATURE], S4_FE)
    if "age2" not in fit.dropped:
        raise RuntimeError(f"expected age2 to be dropped with chip trends; dropped {fit.dropped}")
    base = hc.fit_ols(df, "y", h.CURVATURE, S4_FE)
    base_c2 = float(base.coef[base.index("age2")])
    shape_identified = float(_shape_row(fit) @ fit.coef)  # with c2 = 0 (age2 dropped)
    # Contribution of c2 to rate(0-2) - rate(2-4): c2 * [(4-0)/2 - (16-4)/2] = -4 c2.
    rows = []
    for c2 in (0.0, base_c2 / 2, base_c2, 2 * base_c2):
        rows.append(
            {
                "assumed_c2": c2,
                "c2_label": {0.0: "0 (reviewer's normalization)"}.get(
                    c2, f"{c2 / base_c2:.1f} x no-trend estimate"
                ),
                "early_minus_late_rate": shape_identified - 4.0 * c2,
                "dropped": ";".join(fit.dropped),
                "no_trend_estimate": float(_shape_row(base) @ base.coef),
                "no_trend_c2": base_c2,
            }
        )
    return pl.DataFrame(rows)


def chip_time_slopes(df: pl.DataFrame, chips_table: pl.DataFrame) -> pl.DataFrame:
    """Each chip's calendar-time slope (log points per year) relative to the V100, from a model
    with chip and month effects and controls but no age terms. This is the variation the strategy
    4 curvature is fitted through."""
    d = df.with_columns(_time_years(df).alias("t"))
    cols = []
    for c in h.SAMPLE_CHIPS[1:]:
        d = d.with_columns(((pl.col("chip") == c).cast(pl.Float64) * pl.col("t")).alias(f"tr_{c}"))
        cols.append(f"tr_{c}")
    fit = hc.fit_ols(d, "y", cols, S4_FE)
    pr = h._ids(d, "provider")
    rel = {r["chip_id"]: r["release_date"] for r in chips_table.iter_rows(named=True)}
    rows = [
        {"chip": "v100", "slope_vs_v100": 0.0, "se_cr1_provider": 0.0, "release_date": rel["v100"]}
    ]
    for c in cols:
        r = fit.combo({c: 1.0})
        rows.append(
            {
                "chip": c[3:],
                "slope_vs_v100": float(r @ fit.coef),
                "se_cr1_provider": hc.cr1_se(fit, r, pr),
                "release_date": rel[c[3:]],
            }
        )
    return pl.DataFrame(rows)


def permutation_test(df: pl.DataFrame, chips_table: pl.DataFrame) -> tuple[pl.DataFrame, dict]:
    """Randomization inference: reassign release months across the 7 chips (all distinct
    assignments), rebuild age and the curvature basis, refit strategy 4, record the shape."""
    rel = {
        r["chip_id"]: r["release_date"].replace(day=1)
        for r in chips_table.iter_rows(named=True)
        if r["chip_id"] in h.SAMPLE_CHIPS
    }
    chips = h.SAMPLE_CHIPS
    dates = [rel[c] for c in chips]
    perms = sorted(set(itertools.permutations(dates)))
    month_ix = pl.col("month").dt.year() * 12 + pl.col("month").dt.month().cast(pl.Int32)
    base = df.with_columns(month_ix.alias("_mi"))
    rows = []
    for k, perm in enumerate(perms):
        mapping = {c: d.year * 12 + d.month for c, d in zip(chips, perm, strict=True)}
        d = base.with_columns(
            (
                (pl.col("_mi") - pl.col("chip").replace_strict(mapping, return_dtype=pl.Int32))
                / 12.0
            ).alias("age")
        )
        basis = h.spline_basis(d["age"].to_numpy())
        d = d.with_columns([pl.Series(n, basis[n]) for n in h.CURVATURE])
        fit = hc.fit_ols(d, "y", h.CURVATURE, S4_FE)
        shape = float(_shape_row(fit) @ fit.coef) if "age2" in fit.names else np.nan
        rows.append(
            {"perm": k, "actual": tuple(perm) == tuple(dates), "early_minus_late_rate": shape}
        )
    out = pl.DataFrame(rows)
    obs = float(out.filter(pl.col("actual"))["early_minus_late_rate"].item())
    vals = out.filter(pl.col("early_minus_late_rate").is_not_nan())["early_minus_late_rate"]
    summary = {
        "assignments": out.height,
        "observed": obs,
        "p_two_sided": float((vals.abs() >= abs(obs) - 1e-12).mean()),
        "p_one_sided_ge": float((vals >= obs - 1e-12).mean()),
        "share_positive": float((vals > 0).mean()),
    }
    return out, summary


# ---- point 4 ----------------------------------------------------------------------------------


def bin_shift_check(df: pl.DataFrame) -> pl.DataFrame:
    """Pooled 6-month bins with chip and month effects, edges shifted by k = 0..5 months. Reports
    each bin's level and its detrended value (least-squares line through the bin midpoints
    removed, reference bin included), at the bins covering 12, 24, 36 and 48 months."""
    rows = []
    for k in range(6):
        d = df.with_columns(((pl.col("age_months") + k) // h.BIN_MONTHS).alias("age_bin"))
        d, cols = h.bin_dummies(d)
        fit = hc.fit_ols(d, "y", cols, S4_FE)
        coef = {0: 0.0} | {int(n[3:]): float(fit.coef[fit.index(n)]) for n in fit.names}
        bins = np.array(sorted(coef))
        mids = bins * h.BIN_MONTHS - k + (h.BIN_MONTHS - 1) / 2  # age-month midpoint of each bin
        vals = np.array([coef[b] for b in bins])
        slope, intercept = np.polyfit(mids, vals, 1)
        detr = vals - (slope * mids + intercept)
        for target in (12, 24, 36, 48):
            b = (target + k) // h.BIN_MONTHS
            i = int(np.where(bins == b)[0][0])
            rows.append(
                {
                    "shift_k": k,
                    "age_months": target,
                    "level": vals[i],
                    "detrended": detr[i] - detr[0],
                    "fitted_linear_slope_per_year": slope * 12,
                }
            )
    return pl.DataFrame(rows)


# ---- point 7 ----------------------------------------------------------------------------------


def wcr_table(df: pl.DataFrame, draws: int = h.DRAWS) -> pl.DataFrame:
    rows = []
    chips = h._ids(df, "chip")
    for name in ("s1a_tflops", "s1b_three_specs", "s2_frontier", "s4_shape"):
        spec = h.SPECS[name]
        fit = hc.fit_ols(df, "y", spec.x, spec.fe)
        keep = (
            h.MEASURES
            if spec.linear_identified
            else {"early_minus_late_rate": h.MEASURES["early_minus_late_rate"]}
        )
        for m, f in keep.items():
            r = f(fit, spec.linear_identified)
            wcu = hc.wild_cluster_bootstrap(fit, r, chips, draws=draws)
            p_wcr = hc.wild_cluster_bootstrap_restricted(fit, r, chips, 0.0, draws=draws)
            rows.append(
                {
                    "spec": name,
                    "measure": m,
                    "estimate": wcu.estimate,
                    "wcu_p": wcu.p_value,
                    "wcr_p": p_wcr,
                    "p_floor": 1.0 / (draws + 1),
                    "se_cr1_chip": wcu.se_cr1,
                }
            )
    return pl.DataFrame(rows)


def wcr_inversion(df: pl.DataFrame, draws: int = 1999, tol: float = 0.005) -> dict:
    """95% interval for the strategy 4 shape by inverting the WCR test (bisection each side)."""
    spec = h.SPECS["s4_shape"]
    fit = hc.fit_ols(df, "y", spec.x, spec.fe)
    r = _shape_row(fit)
    chips = h._ids(df, "chip")
    est = float(r @ fit.coef)
    se = hc.cr1_se(fit, r, chips)

    def p(theta0: float) -> float:
        return hc.wild_cluster_bootstrap_restricted(fit, r, chips, theta0, draws=draws)

    def edge(direction: float) -> float:
        inside, outside = est, est + direction * 10 * se
        while p(outside) > 0.05:
            outside += direction * 10 * se
        while abs(outside - inside) > tol:
            mid = (inside + outside) / 2
            inside, outside = (mid, outside) if p(mid) > 0.05 else (inside, mid)
        return (inside + outside) / 2

    return {"estimate": est, "wcr_ci_low": edge(-1.0), "wcr_ci_high": edge(1.0), "draws": draws}


def monte_carlo(
    df: pl.DataFrame, reps: int = 200, draws: int = 399, seed: int = 11
) -> pl.DataFrame:
    """Coverage of 95% intervals for the strategy 4 shape when the truth is zero curvature.

    Errors keep the panel's design (same rows, fixed effects, regressors) and mimic the residual
    structure of the actual fit: a chip x month component, a provider x month component and an
    idiosyncratic one, with variances matched to the actual residuals. Two versions of the chip x
    month component: i.i.d. across months, and a random walk within chip (persistent
    chip-specific demand, the review's point 1)."""
    spec = h.SPECS["s4_shape"]
    fit = hc.fit_ols(df, "y", spec.x, spec.fe)
    r = _shape_row(fit)
    flist = hc._codes(df, spec.fe)
    w = np.ones(df.height)
    resid = fit.resid
    cm = hc._codes(df, ["chip", "month"])
    cm_id = np.unique(
        cm[:, 0].astype(np.int64) * 1000 + cm[:, 1].astype(np.int64), return_inverse=True
    )[1]
    pm = hc._codes(df, ["provider", "month"])
    pm_id = np.unique(
        pm[:, 0].astype(np.int64) * 1000 + pm[:, 1].astype(np.int64), return_inverse=True
    )[1]

    def share(ids: np.ndarray, x: np.ndarray) -> float:
        means = np.bincount(ids, weights=x) / np.bincount(ids)
        return float(np.var(means[ids]) / np.var(x))

    v = float(np.var(resid))
    s_cm, s_pm = share(cm_id, resid), share(pm_id, resid)
    s_cm, s_pm = min(s_cm, 0.9), min(s_pm, 0.9 - min(s_cm, 0.9))
    s_e = max(1.0 - s_cm - s_pm, 0.05)
    chip_ix = hc._codes(df, ["chip"]).ravel().astype(np.int64)
    month_ix = hc._codes(df, ["month"]).ravel().astype(np.int64)
    prov = h._ids(df, "provider")
    n_months = int(month_ix.max()) + 1
    rng = np.random.default_rng(seed)
    rows = []
    for dgp in ("iid_chip_month", "random_walk_chip"):
        hits = {"wcu": 0, "wcr": 0, "cr1_chip": 0, "cr1_provider": 0}
        for rep in range(reps):
            if dgp == "iid_chip_month":
                cm_shock = rng.normal(size=cm_id.max() + 1)[cm_id]
            else:
                walk = np.cumsum(rng.normal(size=(7, n_months)), axis=1)
                walk /= np.sqrt(np.var(walk[chip_ix, month_ix]))
                cm_shock = walk[chip_ix, month_ix]
            e = (
                np.sqrt(s_cm * v) * cm_shock
                + np.sqrt(s_pm * v) * rng.normal(size=pm_id.max() + 1)[pm_id]
                + np.sqrt(s_e * v) * rng.normal(size=df.height)
            )
            ed, _ = hc.partial_out(e, np.zeros((df.height, 0)), flist, w)
            coef = fit.xtx_inv @ (fit.x.T @ ed)
            sim = hc.Fit(fit.names, coef, fit.xtx_inv, fit.x, ed - fit.x @ coef, fit.n)
            theta = float(r @ coef)
            se_c = hc.cr1_se(sim, r, chip_ix)
            se_p = hc.cr1_se(sim, r, prov)
            hits["cr1_chip"] += abs(theta) <= 1.96 * se_c
            hits["cr1_provider"] += abs(theta) <= 1.96 * se_p
            b = hc.wild_cluster_bootstrap(sim, r, chip_ix, draws=draws, seed=seed + rep)
            hits["wcu"] += b.ci_low <= 0.0 <= b.ci_high
            p = hc.wild_cluster_bootstrap_restricted(
                sim, r, chip_ix, 0.0, draws=draws, seed=seed + rep
            )
            hits["wcr"] += p > 0.05
        for method, k in hits.items():
            rows.append(
                {
                    "dgp": dgp,
                    "method": method,
                    "coverage": k / reps,
                    "reps": reps,
                    "share_chip_month": s_cm,
                    "share_provider_month": s_pm,
                }
            )
    return pl.DataFrame(rows)


# ---- points 3, 5, 6, 8, 9 and 13: point estimates for the supplementary checks ---------------

LISTING_KEY = [
    "provider",
    "sku",
    "chip",
    "gpu_count",
    "interconnect",
    "region",
    "contract_type",
    "term_months",
    "price_basis",
    "price_kind",
    "form_factor",
]


def _measures(fit: hc.Fit, linear: bool, df: pl.DataFrame) -> dict:
    """Point estimates of the summary measures with CR1-by-provider standard errors."""
    keep = (
        ["rate_0_2", "rate_2_4", "early_minus_late_rate"] if linear else ["early_minus_late_rate"]
    )
    prov = h._ids(df, "provider")
    out = {}
    for m in keep:
        r = h.MEASURES[m](fit, linear)
        out[m] = float(r @ fit.coef)
        out[f"{m}_se_provider"] = hc.cr1_se(fit, r, prov)
    return out


def _run(df: pl.DataFrame, spec_name: str, label: str, weights: str | None = None) -> dict:
    spec = h.SPECS[spec_name]
    fit = hc.fit_ols(df, "y", spec.x, spec.fe, weights=weights)
    row = {"check": label, "spec": spec_name, "n": df.height, "chips": df["chip"].n_unique()}
    row.update(_measures(fit, spec.linear_identified, df))
    row["dropped"] = ";".join(fit.dropped)
    return row


def transitions(df: pl.DataFrame) -> pl.DataFrame:
    """Month-to-month transitions within a listing, with `_same` = nominal price unchanged."""
    s = df.sort([*LISTING_KEY, "month"]).with_columns(
        pl.col("price_usd_per_gpu_hour").shift(1).over(LISTING_KEY).alias("_prev")
    )
    return s.filter(pl.col("_prev").is_not_null()).with_columns(
        ((pl.col("price_usd_per_gpu_hour") / pl.col("_prev") - 1).abs() < 1e-6).alias("_same")
    )


def repricing_check(df: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Point 3. Share of month-to-month transitions with an unchanged nominal price, by provider
    and contract; and the strategy 4 shape on listings whose price changes at least once."""
    s = transitions(df)
    stick = (
        s.group_by("provider", "contract_type")
        .agg(pl.len().alias("transitions"), pl.col("_same").mean().alias("share_unchanged"))
        .sort("provider", "contract_type")
    )
    movers = s.filter(~pl.col("_same")).select(LISTING_KEY).unique()
    d_move = df.join(movers, on=LISTING_KEY, how="semi", nulls_equal=True)
    rows = [
        _run(df, "s4_shape", "all listings"),
        _run(d_move, "s4_shape", "listings that change price at least once"),
        _run(
            d_move.filter(pl.col("contract_type") != "spot"),
            "s4_shape",
            "non-spot listings that change price",
        ),
    ]
    return stick, pl.DataFrame(rows)


def frontier_check(df: pl.DataFrame, chips_table: pl.DataFrame) -> pl.DataFrame:
    """Point 5. Strategy 2 with the frontier built from in-sample chips only, dated by release or
    by each chip's first panel listing, and with calendar-year effects added."""
    tf = (
        df.group_by("chip")
        .agg(pl.col("tensor_fp16_bf16_tflops").first(), pl.col("month").min().alias("first"))
        .rows(named=True)
    )
    rel = {
        r["chip_id"]: r["release_date"].replace(day=1)
        for r in chips_table.iter_rows(named=True)
        if r["chip_id"] in h.SAMPLE_CHIPS
    }

    def with_frontier(dates: dict) -> pl.DataFrame:
        months = df["month"].unique().to_list()
        fr = {
            m: max([t["tensor_fp16_bf16_tflops"] for t in tf if dates[t["chip"]] <= m] or [np.nan])
            for m in months
        }
        return df.with_columns(
            pl.col("month").replace_strict(fr, return_dtype=pl.Float64).alias("_fr")
        ).with_columns((pl.col("ln_tflops") - pl.col("_fr").log()).alias("rel_frontier"))

    first = {t["chip"]: t["first"] for t in tf}
    d_rel, d_first = with_frontier(rel), with_frontier(first)
    rows = [
        _run(df, "s2_frontier", "baseline (any chip in the reference table, by release)"),
        _run(d_rel.drop_nulls("rel_frontier"), "s2_frontier", "in-sample chips, by release"),
        _run(
            d_first.drop_nulls("rel_frontier"),
            "s2_frontier",
            "in-sample chips, by first panel listing",
        ),
    ]
    spec = h.SPECS["s2_frontier"]
    d_year = df.with_columns(pl.col("month").dt.year().cast(pl.String).alias("_year"))
    fit = hc.fit_ols(d_year, "y", spec.x, [*spec.fe, "_year"])
    row = {"check": "baseline + calendar-year effects", "spec": "s2_frontier"}
    row.update({"n": df.height, "chips": 7})
    row.update(_measures(fit, True, d_year))
    row["dropped"] = ";".join(fit.dropped)
    rows.append(row)
    return pl.DataFrame(rows)


def event_dating_check(df: pl.DataFrame, chips_table: pl.DataFrame) -> pl.DataFrame:
    """Point 6. The successor event study with events dated by Epoch release (baseline) and by
    the successor's first listing in the panel; point estimates with CR1-by-provider SEs."""
    rel = {
        r["chip_id"]: r["release_date"].replace(day=1)
        for r in chips_table.iter_rows(named=True)
        if r["release_date"] is not None
    }
    first = {r[0]: r[1] for r in df.group_by("chip").agg(pl.col("month").min()).rows()}
    prov = h._ids(df, "provider")
    rows = []
    for label, dates in (("epoch release", rel), ("first panel listing", first)):
        d, cols = h.event_dummies(df, dates)
        fit = hc.fit_ols(d, "y", [*cols, *h.CURVATURE], ["chip", "month", *h.CONTROLS])
        for c in cols:
            if c not in fit.names:
                continue
            r = fit.combo({c: 1.0})
            rows.append(
                {
                    "event_date": label,
                    "measure": c,
                    "estimate": float(r @ fit.coef),
                    "se_cr1_provider": hc.cr1_se(fit, r, prov),
                }
            )
        for succ in ("a100_40gb", "h100_sxm", "b200"):
            rows.append(
                {
                    "event_date": label,
                    "measure": f"date_{succ}",
                    "estimate": float(dates[succ].year * 100 + dates[succ].month),
                    "se_cr1_provider": float("nan"),
                }
            )
    return pl.DataFrame(rows)


def weighting_check(df: pl.DataFrame) -> pl.DataFrame:
    """Point 8. Headline specs on unique price points (duplicate per-GPU prices across GPU counts
    and SKUs collapsed) and with each provider weighted equally."""
    uniq = df.unique(
        subset=[
            "provider",
            "region",
            "chip",
            "contract_type",
            "term_months",
            "month",
            "price_usd_per_gpu_hour",
        ],
        keep="first",
        maintain_order=True,
    )
    eq = df.with_columns((1.0 / pl.len().over("provider")).alias("_w")).with_columns(
        (pl.col("_w") / pl.col("_w").mean()).alias("_w")
    )
    rows = []
    for name in ("s1a_tflops", "s2_frontier", "s4_shape"):
        rows.append(_run(df, name, "all rows (baseline)"))
        rows.append(_run(uniq, name, "unique price points"))
        rows.append(_run(eq, name, "providers weighted equally", weights="_w"))
        rows.append(_run(df.filter(pl.col("provider") != "google_cloud"), name, "without Google"))
    return pl.DataFrame(rows)


def leave_one_out(df: pl.DataFrame) -> pl.DataFrame:
    """Point 9. Each headline spec with one chip left out."""
    rows = []
    for drop in [None, *h.SAMPLE_CHIPS]:
        sub = df if drop is None else df.filter(pl.col("chip") != drop)
        for name in ("s1a_tflops", "s2_frontier", "s4_shape"):
            row = _run(sub, name, f"drop {drop}" if drop else "all chips")
            row["dropped_chip"] = drop or ""
            rows.append(row)
    return pl.DataFrame(rows)


def shortage_window_check(df: pl.DataFrame) -> pl.DataFrame:
    """Open question from memo 02: does the shape survive removing the young-age shortage windows
    (H100 SXM/PCIe 2023-01 to 2024-06; H200 and B200 from 2025-01)?"""
    from datetime import date

    win = (pl.col("chip").is_in(["h100_sxm", "h100_pcie"])) & pl.col("month").is_between(
        date(2023, 1, 1), date(2024, 6, 1)
    )
    win2 = pl.col("chip").is_in(["h200", "b200"]) & (pl.col("month") >= date(2025, 1, 1))
    rows = [
        _run(df, "s4_shape", "all"),
        _run(df.filter(~win), "s4_shape", "without H100 2023-01..2024-06"),
        _run(df.filter(~win & ~win2), "s4_shape", "also without H200/B200 (2025-)"),
        _run(df.filter(pl.col("contract_type") != "spot"), "s4_shape", "without spot"),
        _run(df.filter(pl.col("contract_type") == "on_demand"), "s4_shape", "on-demand only"),
    ]
    return pl.DataFrame(rows)


def nominal_cohort_paths(df: pl.DataFrame) -> pl.DataFrame:
    """Point 13. Observed cohort paths in nominal dollars, beside the real ones."""
    real = h.cohort_paths(df, "real")
    nom = h.cohort_paths(
        df.with_columns(pl.col("price_usd_per_gpu_hour").log().alias("y")), "nominal"
    )
    return pl.concat([real, nom]).sort("chip", "age_months_from", "sample")


def main(argv: list[str] | None = None) -> int:
    part = (argv or ["all"])[0]
    df = h.load_sample()
    chips_table = pl.read_parquet(h.CHIPS)
    TABLES.mkdir(parents=True, exist_ok=True)
    if part in ("trends", "all"):
        chip_trend_check(df).write_csv(TABLES / "p5_review_chip_trends.csv")
        chip_time_slopes(df, chips_table).write_csv(TABLES / "p5_review_chip_slopes.csv")
    if part in ("perm", "all"):
        perm, summ = permutation_test(df, chips_table)
        perm.write_csv(TABLES / "p5_review_permutations.csv")
        pl.DataFrame([summ]).write_csv(TABLES / "p5_review_permutation_summary.csv")
    if part in ("bins", "all"):
        bin_shift_check(df).write_csv(TABLES / "p5_review_bin_shift.csv")
    if part in ("wcr", "all"):
        wcr_table(df).write_csv(TABLES / "p5_review_wcr.csv")
        pl.DataFrame([wcr_inversion(df)]).write_csv(TABLES / "p5_review_wcr_interval.csv")
    if part in ("mc", "all"):
        monte_carlo(df).write_csv(TABLES / "p5_review_monte_carlo.csv")
    if part in ("extra", "all"):
        stick, movers = repricing_check(df)
        stick.write_csv(TABLES / "p5_review_repricing.csv")
        movers.write_csv(TABLES / "p5_review_repricing_shape.csv")
        frontier_check(df, chips_table).write_csv(TABLES / "p5_review_frontier.csv")
        event_dating_check(df, chips_table).write_csv(TABLES / "p5_review_event_dating.csv")
        weighting_check(df).write_csv(TABLES / "p5_review_weighting.csv")
        leave_one_out(df).write_csv(TABLES / "p5_review_leave_one_out.csv")
        shortage_window_check(df).write_csv(TABLES / "p5_review_shortage.csv")
        nominal_cohort_paths(df).write_csv(TABLES / "p5_review_cohort_nominal.csv")
    print(f"review checks done: {part}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
