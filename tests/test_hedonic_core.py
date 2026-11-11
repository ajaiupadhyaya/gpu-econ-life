"""Phase 5 estimation engine against pyfixest and hand cases (Decision 23)."""

import numpy as np
import pandas as pd
import polars as pl
import pyfixest as pf
import pytest

from gel.models import hedonic_core as hc


@pytest.fixture
def panel() -> pl.DataFrame:
    rng = np.random.default_rng(7)
    n = 3000
    chip = rng.integers(0, 7, n)
    month = rng.integers(0, 40, n)
    prov = rng.integers(0, 5, n)
    x1 = rng.normal(size=n)
    x2 = rng.normal(size=n) + 0.3 * x1
    chip_fe = rng.normal(size=7)[chip]
    month_fe = rng.normal(size=40)[month]
    cluster_shock = rng.normal(scale=0.3, size=7)[chip]
    y = 0.5 * x1 - 0.25 * x2 + chip_fe + month_fe + cluster_shock * x1 + rng.normal(size=n)
    return pl.DataFrame(
        {
            "y": y,
            "x1": x1,
            "x2": x2,
            "chip": chip.astype(str),
            "month": month.astype(str),
            "prov": prov.astype(str),
            "w": rng.uniform(0.5, 2.0, n),
        }
    )


def test_coefficients_match_pyfixest(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    ref = pf.feols("y ~ x1 + x2 | chip + month", data=panel.to_pandas())
    np.testing.assert_allclose(fit.coef, ref.coef().to_numpy(), rtol=1e-6)


def test_weighted_coefficients_match_pyfixest(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"], weights="w")
    ref = pf.feols("y ~ x1 + x2 | chip + month", data=panel.to_pandas(), weights="w")
    np.testing.assert_allclose(fit.coef, ref.coef().to_numpy(), rtol=1e-6)


def test_cr1_matches_pyfixest_without_fixef_dof(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    ref = pf.feols(
        "y ~ x1 + x2 | chip + month",
        data=panel.to_pandas(),
        vcov={"CRV1": "prov"},
        ssc=pf.ssc(k_adj=True, k_fixef="none", G_adj=True),
    )
    clusters = hc._codes(panel, ["prov"]).ravel().astype(np.int64)
    se = hc.cr1_se(fit, fit.combo({"x1": 1.0}), clusters)
    assert se == pytest.approx(ref.se()["x1"], rel=1e-6)


def test_no_fe_adds_intercept():
    df = pl.DataFrame({"y": [1.0, 3.0, 5.0, 7.0], "x": [0.0, 1.0, 2.0, 3.0]})
    fit = hc.fit_ols(df, "y", ["x"], [])
    assert fit.names == ["(Intercept)", "x"]
    np.testing.assert_allclose(fit.coef, [1.0, 2.0], atol=1e-10)


def test_absorbed_column_is_dropped(panel):
    # A regressor that is a function of chip only is absorbed by the chip fixed effect.
    df = panel.with_columns(pl.col("chip").cast(pl.Int64).cast(pl.Float64).alias("chip_num"))
    fit = hc.fit_ols(df, "y", ["x1", "chip_num"], ["chip", "month"])
    assert fit.dropped == ["chip_num"]
    assert fit.names == ["x1"]


def test_linear_age_is_dropped_with_chip_and_month_effects():
    # age = month - vintage exactly: the Hall (1968) collinearity.
    rows = [(c, m, m - c) for c in range(4) for m in range(c, 12)]
    df = pl.DataFrame(rows, schema=["chip", "month", "age"], orient="row").with_columns(
        pl.col("age").cast(pl.Float64),
        (pl.col("age") ** 2).cast(pl.Float64).alias("age2"),
        pl.lit(1.0).alias("y") + pl.col("age") * 0.0,
    )
    df = df.with_columns((pl.col("y") + pl.col("age2") * 0.01).alias("y"))
    fit = hc.fit_ols(df, "y", ["age", "age2"], ["chip", "month"])
    assert "age" in fit.dropped
    assert fit.coef[fit.index("age2")] == pytest.approx(0.01, abs=1e-8)


def test_twoway_se_at_least_positive(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    a = hc._codes(panel, ["prov"]).ravel().astype(np.int64)
    b = hc._codes(panel, ["month"]).ravel().astype(np.int64)
    assert hc.twoway_se(fit, fit.combo({"x1": 1.0}), a, b) > 0


def test_wild_bootstrap_interval_contains_truth_and_is_reproducible(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    clusters = hc._codes(panel, ["chip"]).ravel().astype(np.int64)
    r = fit.combo({"x1": 1.0})
    res = hc.wild_cluster_bootstrap(fit, r, clusters, draws=1999)
    assert res.ci_low < 0.5 < res.ci_high
    assert res.clusters == 7
    again = hc.wild_cluster_bootstrap(fit, r, clusters, draws=1999)
    assert (res.ci_low, res.ci_high, res.p_value) == (again.ci_low, again.ci_high, again.p_value)


def test_wild_bootstrap_rejects_a_large_effect(panel):
    df = panel.with_columns((pl.col("y") + 3.0 * pl.col("x2")).alias("y"))
    fit = hc.fit_ols(df, "y", ["x1", "x2"], ["chip", "month"])
    clusters = hc._codes(df, ["chip"]).ravel().astype(np.int64)
    res = hc.wild_cluster_bootstrap(fit, fit.combo({"x2": 1.0}), clusters, draws=1999)
    assert res.p_value < 0.05
    assert res.ci_low > 2.0


def test_linear_combination(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    r = fit.combo({"x1": 1.0, "x2": -1.0})
    assert float(r @ fit.coef) == pytest.approx(fit.coef[0] - fit.coef[1])
    assert isinstance(pd.Series(fit.coef), pd.Series)


def test_many_matches_single(panel):
    fit = hc.fit_ols(panel, "y", ["x1", "x2"], ["chip", "month"])
    clusters = hc._codes(panel, ["chip"]).ravel().astype(np.int64)
    rs = np.vstack([fit.combo({"x1": 1.0}), fit.combo({"x2": 1.0})])
    many = hc.wild_cluster_bootstrap_many(fit, rs, clusters, draws=999)
    one = hc.wild_cluster_bootstrap(fit, rs[0], clusters, draws=999)
    assert many[0] == one
    assert many[1].estimate == pytest.approx(fit.coef[1])
