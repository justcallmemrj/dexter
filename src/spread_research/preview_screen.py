"""Daily-resolution pair SCREENING metrics (D-007 preview tier).

What a daily screen CAN say: whether the pair's relationship structure at daily
horizon (cointegration, residual stationarity, hedge stability) is consistent
with, or already disqualifying for, the intraday hypothesis.

What it CANNOT say: anything about INTRADAY mean reversion (A-006/A-009 are
intraday hypotheses — invisible in daily bars), executable edge, or costs.
A screen never validates a pair; it only deprioritizes or flags one.

All functions are pure; drivers pass in canonical close series.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .hedge_ratios import rolling_ols_beta
from .mean_reversion import half_life_ar1
from .pair_builder import align_pair, build_residual
from .stationarity import engle_granger, stationarity_verdict


def screen_pair(close_a: pd.Series, close_b: pd.Series, *, pair_name: str,
                use_log: bool, ols_window_bars: int = 126,
                recent_bars: int = 252) -> dict:
    """Compute the screening metric set for one pair of daily close series.

    Returns a flat dict (one row of the screening table). Half-life units are
    DAILY BARS. Two residual variants are reported deliberately:
    - static full-sample OLS residual (in-sample by construction — structure
      check only, mirrors what Engle-Granger tests), and
    - rolling look-ahead-safe OLS residual (window = ols_window_bars, shifted),
      whose half-life is the more honest, hedge-noise-inflated figure (L-007).
    """
    df = align_pair(close_a, close_b)
    a = np.log(df["a"]) if use_log else df["a"].astype(float)
    b = np.log(df["b"]) if use_log else df["b"].astype(float)
    n = len(df)
    out: dict = {
        "pair": pair_name, "n_obs": n,
        "start": str(df.index[0].date()) if n else None,
        "end": str(df.index[-1].date()) if n else None,
        "space": "log" if use_log else "price",
    }
    if n < max(ols_window_bars + 30, 120):
        out["status"] = "insufficient_data"
        return out
    out["status"] = "ok"

    ret_corr = a.diff().corr(b.diff())
    out["daily_ret_corr"] = float(ret_corr)

    # Static full-sample OLS (structure check, in-sample by construction)
    x = np.vstack([np.ones(n), b.values]).T
    coef, *_ = np.linalg.lstsq(x, a.values, rcond=None)
    beta_static = float(coef[1])
    out["beta_static"] = beta_static
    resid_static = a - (coef[0] + beta_static * b.values)

    eg = engle_granger(a, b)
    out["eg_pvalue"] = float(eg["pvalue"])
    out["eg_cointegrated_5pct"] = bool(eg["cointegrated_5pct"])

    sv = stationarity_verdict(resid_static)
    out["static_resid_verdict"] = sv["verdict"]
    out["static_resid_adf_p"] = float(sv["adf"]["pvalue"])
    out["static_resid_kpss_p"] = float(sv["kpss"]["pvalue"])
    hl_static = half_life_ar1(resid_static)
    out["static_resid_half_life_days"] = float(hl_static["half_life_bars"])

    # Rolling look-ahead-safe hedge + residual (L-007-inflated, honest variant)
    beta_roll = rolling_ols_beta(a, b, window=ols_window_bars, shifted=True)
    resid_roll = build_residual(df["a"], df["b"], beta_roll, use_log=use_log)
    hl_roll = half_life_ar1(resid_roll)
    out["rolling_resid_half_life_days"] = float(hl_roll["half_life_bars"])

    # Hedge stability: distribution of the rolling beta + recent-vs-full shift
    br = beta_roll.dropna()
    out["beta_roll_median"] = float(br.median())
    out["beta_roll_p5"] = float(br.quantile(0.05))
    out["beta_roll_p95"] = float(br.quantile(0.95))
    recent = br.iloc[-recent_bars:] if len(br) > recent_bars else br
    full_med = br.median()
    out["beta_recent_vs_full_shift_pct"] = (
        float(100.0 * (recent.median() - full_med) / abs(full_med))
        if full_med != 0 else np.nan
    )
    return out


def screen_tier(row: dict, *, eg_alpha: float = 0.05,
                max_beta_shift_pct: float = 25.0) -> str:
    """Map one screening row to a triage tier. Tiers order minute-level effort;
    they are NOT validation verdicts (a screen cannot validate — module docstring).

    Naming is deliberate: the tiers describe DAILY-HORIZON structure only. A
    'no_daily_structure' pair has a dead long-horizon/static-hedge version; its
    intraday hypothesis (short z-lookback, adaptive hedge) remains UNTESTED and
    is settled only by the minute-resolution program.

    - 'daily_structure_present' cointegration evidence AND residual verdict at
                                least marginal AND hedge not drifting wildly
    - 'daily_structure_weak'    mixed evidence
    - 'no_daily_structure'      no cointegration evidence AND non-stationary
                                residual, or hedge shift beyond
                                max_beta_shift_pct (regime break)
    """
    if row.get("status") != "ok":
        return "insufficient_data"
    coint = row["eg_pvalue"] < eg_alpha
    verdict = row["static_resid_verdict"]
    stationary_ok = verdict in ("stationary", "stationary_marginal")
    shift = abs(row.get("beta_recent_vs_full_shift_pct") or 0.0)
    if shift > max_beta_shift_pct:
        return "no_daily_structure"
    if coint and stationary_ok:
        return "daily_structure_present"
    if (not coint) and verdict == "non_stationary":
        return "no_daily_structure"
    return "daily_structure_weak"
