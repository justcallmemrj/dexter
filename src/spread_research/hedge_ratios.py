"""Hedge-ratio estimators (mandate notebook 04).

All rolling estimators are LOOK-AHEAD SAFE by construction: the ratio reported at
time t is fitted on data through t and is intended to be APPLIED from t+1 onward.
Callers (pair_builder / backtester) must shift by one bar before use; the
`shifted=True` convenience does it here.

Estimators return a pd.Series of beta (units: leg-B price move per unit leg-A
price move, in the regression space chosen by the caller — price or log-price).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def notional_ratio(price_a: pd.Series, price_b: pd.Series,
                   mult_a: float, mult_b: float) -> pd.Series:
    """Contract-notional weighting: equal dollar notional per leg.
    beta = (price_a * mult_a) / (price_b * mult_b) in CONTRACT space."""
    return (price_a * mult_a) / (price_b * mult_b)


def rolling_ols_beta(y: pd.Series, x: pd.Series, window: int,
                     shifted: bool = True) -> pd.Series:
    """Rolling OLS slope of y on x (no intercept drift handling — use returns or
    log prices as appropriate; caller's choice is a documented assumption)."""
    x_ = x.astype(float)
    y_ = y.astype(float)
    mx = x_.rolling(window).mean()
    my = y_.rolling(window).mean()
    cov = (x_ * y_).rolling(window).mean() - mx * my
    var = (x_ * x_).rolling(window).mean() - mx * mx
    beta = cov / var.replace(0.0, np.nan)
    return beta.shift(1) if shifted else beta


def rolling_robust_beta(y: pd.Series, x: pd.Series, window: int, step: int = 1,
                        shifted: bool = True) -> pd.Series:
    """Rolling Huber-robust slope (statsmodels RLM). Slower; use step>1 to refit
    every `step` bars and forward-fill between refits."""
    import statsmodels.api as sm

    idx = y.index
    out = pd.Series(np.nan, index=idx)
    for end in range(window, len(idx), step):
        ys = y.iloc[end - window:end].values
        xs = x.iloc[end - window:end].values
        X = sm.add_constant(xs)
        try:
            res = sm.RLM(ys, X, M=sm.robust.norms.HuberT()).fit(maxiter=50)
            out.iloc[end - 1] = res.params[1]
        except Exception:
            out.iloc[end - 1] = np.nan
    out = out.ffill()
    return out.shift(1) if shifted else out


def ewls_beta(y: pd.Series, x: pd.Series, halflife: float,
              shifted: bool = True) -> pd.Series:
    """Exponentially weighted least-squares slope via EW moments."""
    x_ = x.astype(float)
    y_ = y.astype(float)
    mx = x_.ewm(halflife=halflife).mean()
    my = y_.ewm(halflife=halflife).mean()
    cov = (x_ * y_).ewm(halflife=halflife).mean() - mx * my
    var = (x_ * x_).ewm(halflife=halflife).mean() - mx * mx
    beta = cov / var.replace(0.0, np.nan)
    return beta.shift(1) if shifted else beta


def dollar_vol_ratio(ret_a: pd.Series, ret_b: pd.Series,
                     price_a: pd.Series, price_b: pd.Series,
                     mult_a: float, mult_b: float, window: int,
                     shifted: bool = True) -> pd.Series:
    """Dollar-volatility weighting in CONTRACT space:
    ratio = (sigma_a * price_a * mult_a) / (sigma_b * price_b * mult_b).
    Ignores correlation — deliberately simple, hard to overfit."""
    va = ret_a.rolling(window).std() * price_a * mult_a
    vb = ret_b.rolling(window).std() * price_b * mult_b
    r = va / vb.replace(0.0, np.nan)
    return r.shift(1) if shifted else r


def kalman_beta(y: pd.Series, x: pd.Series, delta: float = 1e-5,
                obs_var: float | None = None, shifted: bool = True) -> pd.Series:
    """Kalman-filter dynamic regression y_t = alpha_t + beta_t * x_t + eps.

    State [alpha, beta] follows a random walk with covariance Q = delta/(1-delta)*I.
    Strictly causal: estimate at t uses observations up to and including t.
    `obs_var` defaults to the variance of the first 100 OLS residuals (fitted on
    the first 100 points only — a warm-up choice recorded as an assumption).
    """
    yv = y.astype(float).values
    xv = x.astype(float).values
    n = len(yv)
    if obs_var is None:
        k = min(100, n)
        A = np.vstack([np.ones(k), xv[:k]]).T
        coef, *_ = np.linalg.lstsq(A, yv[:k], rcond=None)
        resid = yv[:k] - A @ coef
        obs_var = float(np.var(resid)) or 1.0

    q = delta / (1.0 - delta)
    Q = q * np.eye(2)
    state = np.zeros(2)          # [alpha, beta]
    P = np.eye(2)
    betas = np.full(n, np.nan)
    for t in range(n):
        H = np.array([1.0, xv[t]])
        # predict
        P = P + Q
        # update
        yhat = H @ state
        S = H @ P @ H + obs_var
        K = (P @ H) / S
        state = state + K * (yv[t] - yhat)
        P = P - np.outer(K, H) @ P
        betas[t] = state[1]
    out = pd.Series(betas, index=y.index)
    return out.shift(1) if shifted else out


def dv01_ratio(dv01_a: pd.Series | float, dv01_b: pd.Series | float) -> pd.Series | float:
    """Approximate DV01-neutral contract ratio: contracts_b per contract_a =
    dv01_a / dv01_b. Only as good as the DV01 inputs (CTD-based); see A-012."""
    return dv01_a / dv01_b


def hedge_stability(beta: pd.Series, window: int = 390) -> pd.DataFrame:
    """Diagnostics for hedge-ratio drift: rolling std, and turnover proxy
    (mean absolute bar-to-bar change)."""
    return pd.DataFrame({
        "beta": beta,
        "beta_roll_std": beta.rolling(window).std(),
        "beta_abs_change": beta.diff().abs(),
    })
