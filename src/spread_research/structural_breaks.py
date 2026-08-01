"""Structural-break detection for pair relationships (mandate §4.1/§4.4).

Two cheap, interpretable detectors for V1:
- rolling-correlation collapse (relationship weakening),
- CUSUM of standardized residual innovations (mean shift in the spread).
Both are diagnostics for research review, not automatic trading signals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_correlation(ret_a: pd.Series, ret_b: pd.Series, window: int) -> pd.Series:
    return ret_a.rolling(window).corr(ret_b).rename("rolling_corr")


def correlation_break_flags(ret_a: pd.Series, ret_b: pd.Series, window: int,
                            floor: float = 0.5) -> pd.Series:
    """True where rolling correlation drops below `floor` — candidate periods in
    which the pair should not be traded."""
    return (rolling_correlation(ret_a, ret_b, window) < floor).rename("corr_break")


def cusum_mean_shift(residual: pd.Series, lookback: int = 390,
                     threshold: float = 5.0, drift: float = 0.5) -> pd.DataFrame:
    """Two-sided CUSUM on standardized LEVEL deviations of the residual from its
    prior rolling mean (shifted — no look-ahead). A level shift keeps the
    standardized deviation elevated until the rolling window adapts, so it
    accumulates; the `drift` allowance (classic CUSUM k, default 0.5) keeps the
    statistic bounded under no-change noise. Returns cusum_pos/neg and an alarm
    flag when either exceeds `threshold`."""
    mu = residual.rolling(lookback).mean().shift(1)
    sd = residual.rolling(lookback).std().shift(1)
    z = ((residual - mu) / sd.replace(0.0, np.nan)).fillna(0.0).values
    n = len(z)
    cp = np.zeros(n)
    cn = np.zeros(n)
    for t in range(1, n):
        cp[t] = max(0.0, cp[t - 1] + z[t] - drift)
        cn[t] = min(0.0, cn[t - 1] + z[t] + drift)
    out = pd.DataFrame({"cusum_pos": cp, "cusum_neg": cn}, index=residual.index)
    out["alarm"] = (out["cusum_pos"] > threshold) | (out["cusum_neg"] < -threshold)
    return out
