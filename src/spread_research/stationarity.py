"""Stationarity and cointegration tests (mandate notebook 05).

Wrappers return plain dicts so notebooks can tabulate them directly. Interpretation
discipline: ADF's null is unit root (non-stationary); KPSS's null is stationarity.
Agreement (ADF rejects AND KPSS fails to reject) is the evidence standard used in
this project — either test alone is weak evidence.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss, coint


def adf_test(series: pd.Series, regression: str = "c", autolag: str = "AIC") -> dict:
    s = series.dropna()
    stat, pvalue, usedlag, nobs, crit, _ = adfuller(s, regression=regression, autolag=autolag)
    return {"test": "ADF", "stat": stat, "pvalue": pvalue, "lags": usedlag,
            "nobs": nobs, "crit_5pct": crit["5%"],
            "rejects_unit_root_5pct": pvalue < 0.05}


def kpss_test(series: pd.Series, regression: str = "c") -> dict:
    import warnings
    s = series.dropna()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # kpss warns when p-value is off-table
        stat, pvalue, lags, crit = kpss(s, regression=regression, nlags="auto")
    return {"test": "KPSS", "stat": stat, "pvalue": pvalue, "lags": lags,
            "crit_5pct": crit["5%"],
            "rejects_stationarity_5pct": pvalue < 0.05}


def stationarity_verdict(series: pd.Series) -> dict:
    """Combined verdict:
    - 'stationary'          ADF rejects unit root AND KPSS p >= 0.05
    - 'stationary_marginal' ADF rejects AND 0.01 <= KPSS p < 0.05 (KPSS is known
                            to over-reject for strongly autocorrelated stationary
                            series; a marginal KPSS with a decisive ADF is kept
                            visible rather than collapsed into 'ambiguous')
    - 'non_stationary'      ADF fails to reject AND KPSS rejects
    - 'ambiguous'           anything else
    """
    a = adf_test(series)
    k = kpss_test(series)
    if a["rejects_unit_root_5pct"] and k["pvalue"] >= 0.05:
        verdict = "stationary"
    elif a["rejects_unit_root_5pct"] and k["pvalue"] >= 0.01:
        verdict = "stationary_marginal"
    elif not a["rejects_unit_root_5pct"] and k["rejects_stationarity_5pct"]:
        verdict = "non_stationary"
    else:
        verdict = "ambiguous"
    return {"verdict": verdict, "adf": a, "kpss": k}


def engle_granger(y: pd.Series, x: pd.Series, trend: str = "c") -> dict:
    """Engle–Granger cointegration test of y on x."""
    df = pd.concat([y, x], axis=1).dropna()
    stat, pvalue, crit = coint(df.iloc[:, 0], df.iloc[:, 1], trend=trend)
    return {"test": "EngleGranger", "stat": stat, "pvalue": pvalue,
            "crit_5pct": crit[1], "cointegrated_5pct": pvalue < 0.05}


def rolling_adf_pvalue(series: pd.Series, window: int, step: int) -> pd.Series:
    """Rolling ADF p-value — stability of stationarity across sub-periods.
    Reported at window END (uses only data within the window)."""
    s = series.dropna()
    out = {}
    for end in range(window, len(s) + 1, step):
        chunk = s.iloc[end - window:end]
        try:
            out[s.index[end - 1]] = adfuller(chunk, autolag="AIC")[1]
        except Exception:
            out[s.index[end - 1]] = np.nan
    return pd.Series(out, name="adf_pvalue")
