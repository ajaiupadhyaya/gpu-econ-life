"""Estimation engine for Phase 5 (Decision 23): OLS after partialling out fixed effects, with
cluster-robust and wild-cluster-bootstrap inference on linear combinations of coefficients.

Fixed effects are removed with pyfixest's alternating-projections demeaning (Frisch-Waugh-Lovell),
so the coefficient on each regressor equals what pyfixest's feols reports (tested).

Wild cluster bootstrap (Cameron, Gelbach and Miller 2008; Webb 2023 six-point weights, suited to
few clusters): unrestricted (WCU), percentile-t. For a linear combination theta = r'b:

    y* = X b + w_g u,   w_g in {+-sqrt(1/2), +-1, +-sqrt(3/2)} drawn once per cluster
    t* = (theta* - theta) / se*(theta*),  se from CR1 at the same clustering
    CI = [theta - q(0.975) se, theta - q(0.025) se];  p = share of |t*| >= |t|

The fixed effects stay fixed across draws, which FWL allows because demeaning is linear.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import polars as pl
from pyfixest.estimation import demean

WEBB = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])


def _codes(df: pl.DataFrame, cols: list[str]) -> np.ndarray:
    if not cols:
        return np.zeros((df.height, 0), dtype=np.uint64)
    out = [
        df.select(pl.col(c).cast(pl.String).fill_null("<null>").rank("dense") - 1)
        .to_numpy()
        .ravel()
        .astype(np.uint64)
        for c in cols
    ]
    return np.column_stack(out)


def partial_out(
    y: np.ndarray, x: np.ndarray, flist: np.ndarray, weights: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Demean y and the columns of x on the fixed effects (weighted). No FE: weighted centring
    is not applied, the caller adds an intercept."""
    yx = np.column_stack([y, x]).astype(np.float64)
    if flist.shape[1] == 0:
        return yx[:, 0], yx[:, 1:]
    out, ok = demean(yx, flist, weights, tol=1e-10, maxiter=100_000)
    if not ok:
        raise RuntimeError("fixed-effect demeaning did not converge")
    return out[:, 0], out[:, 1:]


@dataclass
class Fit:
    names: list[str]
    coef: np.ndarray
    xtx_inv: np.ndarray
    x: np.ndarray  # partialled-out, sqrt-weighted regressors
    resid: np.ndarray  # sqrt-weighted residuals
    n: int
    dropped: list[str] = field(default_factory=list)
    condition: float = float("nan")

    def index(self, name: str) -> int:
        return self.names.index(name)

    def combo(self, weights: dict[str, float]) -> np.ndarray:
        r = np.zeros(len(self.names))
        for k, v in weights.items():
            if k in self.names:
                r[self.index(k)] = v
        return r


def fit_ols(
    df: pl.DataFrame,
    y: str,
    x: list[str],
    fe: list[str],
    weights: str | None = None,
    intercept_if_no_fe: bool = True,
) -> Fit:
    """OLS of y on x after absorbing the fixed effects in `fe`. Collinear columns are dropped
    (pivoted QR, tolerance 1e-9 relative) and listed in `dropped`."""
    w = df[weights].to_numpy().astype(float) if weights else np.ones(df.height)
    yv = df[y].to_numpy().astype(float)
    xv = df.select(x).to_numpy().astype(float) if x else np.zeros((df.height, 0))
    names = list(x)
    if not fe and intercept_if_no_fe:
        xv = np.column_stack([np.ones(df.height), xv])
        names = ["(Intercept)", *names]
    yd, xd = partial_out(yv, xv, _codes(df, fe), w)
    sw = np.sqrt(w)
    yd, xd = yd * sw, xd * sw[:, None]
    # Drop columns that the fixed effects (or other columns) absorb.
    keep: list[int] = []
    scale = np.linalg.norm(xv * sw[:, None], axis=0) + 1e-300
    for j in range(xd.shape[1]):
        trial = keep + [j]
        sub = xd[:, trial] / scale[trial]
        s = np.linalg.svd(sub, compute_uv=False)
        if s[-1] > 1e-7 * s[0] and np.linalg.norm(xd[:, j]) > 1e-9 * scale[j]:
            keep.append(j)
    dropped = [names[j] for j in range(len(names)) if j not in keep]
    xd = xd[:, keep]
    names = [names[j] for j in keep]
    xtx = xd.T @ xd
    xtx_inv = np.linalg.inv(xtx)
    coef = xtx_inv @ (xd.T @ yd)
    resid = yd - xd @ coef
    s = np.linalg.svd(xd / np.linalg.norm(xd, axis=0), compute_uv=False)
    return Fit(names, coef, xtx_inv, xd, resid, df.height, dropped, float(s[0] / s[-1]))


def cr1_se(fit: Fit, r: np.ndarray, clusters: np.ndarray) -> float:
    """CR1 standard error of r'b with one-way clustering."""
    z = fit.x @ (fit.xtx_inv @ r)
    g = clusters.max() + 1
    q = np.bincount(clusters, weights=z * fit.resid, minlength=g)
    n_g = len(np.unique(clusters))
    k = len(fit.names)
    c = n_g / (n_g - 1) * (fit.n - 1) / max(fit.n - k, 1)
    return float(np.sqrt(c * np.sum(q**2)))


def twoway_se(fit: Fit, r: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    """Cameron-Gelbach-Miller two-way CR1: V_a + V_b - V_ab (floored at V_a's value if negative)."""
    ab = _codes(pl.DataFrame({"a": a, "b": b}), ["a", "b"])
    ab_id = ab[:, 0].astype(np.int64) * (int(ab[:, 1].max()) + 1) + ab[:, 1].astype(np.int64)
    _, ab_id = np.unique(ab_id, return_inverse=True)
    va = cr1_se(fit, r, a) ** 2
    vb = cr1_se(fit, r, b) ** 2
    vab = cr1_se(fit, r, ab_id) ** 2
    v = va + vb - vab
    return float(np.sqrt(v if v > 0 else va))


@dataclass(frozen=True)
class BootResult:
    estimate: float
    se_cr1: float
    ci_low: float
    ci_high: float
    p_value: float
    draws: int
    clusters: int


def wild_cluster_bootstrap_many(
    fit: Fit,
    rs: np.ndarray,
    clusters: np.ndarray,
    draws: int = 9999,
    seed: int = 20261111,
    alpha: float = 0.05,
    chunk: int = 250,
) -> list[BootResult]:
    """WCU percentile-t bootstrap for several theta_j = r_j'b (rows of `rs`), one set of draws.

    Webb weights, CR1 standard errors at the same clustering. Per draw the residual
    y* - X b* is used for se*, so each t* is studentized exactly like t-hat."""
    rs = np.atleast_2d(rs)
    rng = np.random.default_rng(seed)
    g = int(clusters.max()) + 1
    n_g = len(np.unique(clusters))
    k = len(fit.names)
    c = n_g / (n_g - 1) * (fit.n - 1) / max(fit.n - k, 1)
    theta = rs @ fit.coef  # m
    se = np.array([cr1_se(fit, r, clusters) for r in rs])
    t_hat = np.where(se > 0, theta / np.where(se > 0, se, 1.0), np.nan)
    z = fit.x @ (fit.xtx_inv @ rs.T)  # n x m
    fitted = fit.x @ fit.coef
    onehot = np.zeros((g, fit.n))
    onehot[clusters, np.arange(fit.n)] = 1.0
    zc = [onehot * z[:, j][None, :] for j in range(rs.shape[0])]  # m arrays, g x n
    t_star = []
    done = 0
    while done < draws:
        b = min(chunk, draws - done)
        wts = WEBB[rng.integers(0, 6, size=(g, b))]  # cluster x draw
        y_star = fitted[:, None] + fit.resid[:, None] * wts[clusters, :]
        coef_star = fit.xtx_inv @ (fit.x.T @ y_star)  # k x b
        resid_star = y_star - fit.x @ coef_star
        theta_star = rs @ coef_star  # m x b
        se_star = np.stack([np.sqrt(c * np.sum((zc_j @ resid_star) ** 2, axis=0)) for zc_j in zc])
        t_star.append((theta_star - theta[:, None]) / se_star)
        done += b
    t_all = np.concatenate(t_star, axis=1)  # m x draws
    out = []
    for j in range(rs.shape[0]):
        lo_q, hi_q = np.quantile(t_all[j], [alpha / 2, 1 - alpha / 2])
        p = float(np.mean(np.abs(t_all[j]) >= abs(t_hat[j]))) if np.isfinite(t_hat[j]) else np.nan
        out.append(
            BootResult(
                float(theta[j]),
                float(se[j]),
                float(theta[j] - hi_q * se[j]),
                float(theta[j] - lo_q * se[j]),
                p,
                draws,
                n_g,
            )
        )
    return out


def wild_cluster_bootstrap(
    fit: Fit,
    r: np.ndarray,
    clusters: np.ndarray,
    draws: int = 9999,
    seed: int = 20261111,
    alpha: float = 0.05,
) -> BootResult:
    """WCU percentile-t bootstrap for theta = r'b, clustered on `clusters` (Webb weights)."""
    return wild_cluster_bootstrap_many(fit, r[None, :], clusters, draws, seed, alpha)[0]


def wild_cluster_bootstrap_restricted(
    fit: Fit,
    r: np.ndarray,
    clusters: np.ndarray,
    theta0: float = 0.0,
    draws: int = 9999,
    seed: int = 20261111,
    chunk: int = 250,
) -> float:
    """WCR p-value for H0: r'b = theta0 (restricted residuals, Webb weights, CR1 t-statistic).

    Restricted estimate: b_R = b - A r (r'A r)^-1 (r'b - theta0), A = (X'X)^-1. Draws are built
    from b_R and its residuals, so the bootstrap DGP satisfies H0 (MacKinnon and Webb's WCR)."""
    rng = np.random.default_rng(seed)
    a_r = fit.xtx_inv @ r
    theta = float(r @ fit.coef)
    se = cr1_se(fit, r, clusters)
    t_hat = (theta - theta0) / se
    b_r = fit.coef - a_r * (theta - theta0) / float(r @ a_r)
    yd = fit.x @ fit.coef + fit.resid
    fitted_r = fit.x @ b_r
    resid_r = yd - fitted_r
    g = int(clusters.max()) + 1
    n_g = len(np.unique(clusters))
    k = len(fit.names)
    c = n_g / (n_g - 1) * (fit.n - 1) / max(fit.n - k, 1)
    z = fit.x @ a_r
    onehot = np.zeros((g, fit.n))
    onehot[clusters, np.arange(fit.n)] = 1.0
    zc = onehot * z[None, :]
    exceed = 0
    done = 0
    while done < draws:
        b = min(chunk, draws - done)
        wts = WEBB[rng.integers(0, 6, size=(g, b))]
        y_star = fitted_r[:, None] + resid_r[:, None] * wts[clusters, :]
        coef_star = fit.xtx_inv @ (fit.x.T @ y_star)
        resid_star = y_star - fit.x @ coef_star
        se_star = np.sqrt(c * np.sum((zc @ resid_star) ** 2, axis=0))
        t_star = (r @ coef_star - theta0) / se_star
        exceed += int(np.sum(np.abs(t_star) >= abs(t_hat)))
        done += b
    return exceed / draws
