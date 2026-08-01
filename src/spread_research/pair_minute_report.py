"""Notebook-02 analysis body: preflight + A-006 battery for one pair, emitted
as a flat {key: compact string} dict.

Separated from the QC driver (`lean/research/qc_pair_minute_analysis.py`) for
two reasons: the repo convention is that logic lives in `src/` and callers stay
thin, and — more practically — a QC backtest is an expensive, slow way to find
a typo. Everything here runs and is tested locally on synthetic series.

The dict-of-strings shape exists because QuantConnect's free tier caps logs at
10KB/day, making `set_summary_statistic` the only reliable bulk output channel
(~110 keys/run, string values). Every value is pipe-delimited with a documented
layout so `scripts/ingest_qc_pair_minute.py` can parse it back into frames.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .intraday_reversion import (
    conditional_reversion, event_clock_profile, half_life_within_session,
    held_position_roll_shock, roll_window_diagnostics, rth_frame,
    subsample_within_session, variance_ratio,
)
from .signals import rolling_zscore

ZS_LOOKBACK = 390        # research_config signals.zscore_lookback_bars
BETA_LOOKBACK = 1950     # research_config hedge.lookback_bars (~1 RTH week)
ENTRY_GRID = (1.5, 2.0, 2.5, 3.0)
HORIZONS = (5, 15, 30, 60, 120)
Q_GRID = (2, 5, 15, 30, 60, 120)
SEED = 20260801


def fmt(x, nd: int = 4) -> str:
    """Compact fixed-width formatter. NaN stays 'nan' rather than silently
    becoming a number downstream."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "nan"
    return "nan" if v != v else str(round(v, nd))


def rolling_beta(y: pd.Series, x: pd.Series, window: int) -> pd.Series:
    """Trailing OLS slope through t-1 (same estimator as
    `hedge_ratios.rolling_ols_beta(shifted=True)`)."""
    mx, my = x.rolling(window).mean(), y.rolling(window).mean()
    cov = (x * y).rolling(window).mean() - mx * my
    var = (x * x).rolling(window).mean() - mx * mx
    return (cov / var.replace(0.0, np.nan)).shift(1)


def rolling_ols_residual(y: pd.Series, x: pd.Series, window: int) -> pd.Series:
    """Deviation from the TRAILING fitted line, intercept included:

        resid_t = (y_t - my_{t-1}) - beta_{t-1} * (x_t - mx_{t-1})

    where `mx`, `my`, and `beta` are estimated on the `window` bars ending at
    t-1, so nothing at t enters its own residual.

    Why the intercept is not optional here. An OLS slope is defined on demeaned
    data, so the matching residual must be measured around the full fitted line.
    Dropping the intercept and computing `y_t - beta_t * x_t` on log PRICES
    multiplies every wobble in beta by the log price LEVEL: MYM near 38,000 has
    log(x) ~ 10.5, so a beta that moves by only 0.001 between refits injects
    ~10 bps of spurious residual movement — larger than the effect this study
    is trying to measure, and it shows up as violent, sign-flipping "reversion"
    that is pure hedge-estimation noise (L-007, L-011).

    `pair_builder.build_residual` deliberately keeps the no-intercept form,
    which is correct for a hedge ratio that is NOT fitted (notional, DV01).
    Fitted betas must come through this function instead.
    """
    mx, my = x.rolling(window).mean(), y.rolling(window).mean()
    cov = (x * y).rolling(window).mean() - mx * my
    var = (x * x).rolling(window).mean() - mx * mx
    beta = (cov / var.replace(0.0, np.nan)).shift(1)
    return ((y - my.shift(1)) - beta * (x - mx.shift(1))).dropna()


def residual_specs(log_a: pd.Series, log_b: pd.Series, *,
                   beta_lookback: int = BETA_LOOKBACK
                   ) -> tuple[dict[str, pd.Series], dict]:
    """The three D-010 specifications. None is privileged after the fact.

    S1  beta = 1 log ratio            estimation-free anchor
    S2  trailing OLS residual         look-ahead safe, carries L-007 hedge noise
    S3  full-sample static OLS        LOOK-AHEAD CONTAMINATED — diagnostic only

    S2 and S3 are residuals around the FITTED LINE (intercept included) — see
    `rolling_ols_residual` for why omitting the intercept on log prices
    manufactures hedge noise an order of magnitude larger than the effect
    under study. D-010 froze "trailing-window OLS beta"; taking the residual
    around the full OLS fit is the faithful reading of that, not a departure
    from it.
    """
    beta_roll = rolling_beta(log_a, log_b, beta_lookback)
    beta_static, alpha_static = (float(v) for v in
                                 np.polyfit(log_b.values, log_a.values, 1))
    specs = {
        "S1": (log_a - log_b).rename("S1"),
        "S2": rolling_ols_residual(log_a, log_b, beta_lookback).rename("S2"),
        "S3": (log_a - alpha_static - beta_static * log_b).rename("S3"),
    }
    info = {"beta_static": beta_static, "beta_roll": beta_roll}
    return specs, info


def pair_minute_report(close_a: pd.Series, close_b: pd.Series, *,
                       roll_timestamps, factors_a: pd.Series,
                       factors_b: pd.Series, n_boot: int = 400,
                       q_grid=Q_GRID, entry_grid=ENTRY_GRID,
                       horizons=HORIZONS, seed: int = SEED) -> dict[str, str]:
    """Full notebook-02 battery for one pair. Inputs are CONSTRUCTED
    (own-splice) close series that have already passed `splice_audit`; this
    function does not re-gate them and must not be called on unvetted data.

    `factors_a` / `factors_b` are the per-roll splice factors indexed by roll
    timestamp (the `factor` column of `build_continuous`'s splice table), used
    only for the held-position shock.
    """
    out: dict[str, str] = {}
    a, b = rth_frame(close_a), rth_frame(close_b)
    df = pd.concat({"a": a, "b": b}, axis=1, join="inner").dropna()
    if df.empty:
        return {"S_ALIGN": "EMPTY|no overlapping RTH bars"}
    log_a, log_b = np.log(df["a"]), np.log(df["b"])

    per_session = pd.Series(1, index=df.index).groupby(df.index.normalize()).sum()
    out["S_ALIGN"] = (
        f"bars={len(df)}|sessions={len(per_session)}|"
        f"medbars={int(per_session.median())}|first={df.index[0].date()}|"
        f"last={df.index[-1].date()}|dropA={len(a) - len(df)}|"
        f"dropB={len(b) - len(df)}")

    specs, info = residual_specs(log_a, log_b)
    br = info["beta_roll"]
    out["S_BETA"] = (
        f"static={fmt(info['beta_static'])}|roll_med={fmt(br.median())}|"
        f"roll_p5={fmt(br.quantile(.05))}|roll_p95={fmt(br.quantile(.95))}|"
        f"n={int(br.notna().sum())}")

    out.update(_preflight(specs["S1"], df.index, roll_timestamps,
                          factors_a, factors_b))
    out.update(_conditional_block(specs, entry_grid, horizons))
    out.update(_vr_blocks(specs, log_a, log_b, q_grid, n_boot, seed))
    return out


def _preflight(res1: pd.Series, index, roll_timestamps,
               factors_a: pd.Series, factors_b: pd.Series) -> dict[str, str]:
    """z-score behaviour around OUR splices + the shock a HELD position eats.

    The two are deliberately reported together. On an own-spliced series the
    bucket diagnostics are EXPECTED to look like baseline — that is what the
    construction is for — so an exclusion window cannot be justified from them
    alone. The held-position shock is the quantity that actually argues for
    one, because a real trade must close the expiring pair and reopen the new
    one at genuinely different prices.
    """
    out: dict[str, str] = {}
    z = rolling_zscore(res1, ZS_LOOKBACK)
    rolls = [t for t in pd.to_datetime(pd.Index(roll_timestamps))
             if index[0] <= t <= index[-1]]
    out["S_PF_NROLLS"] = f"in_window={len(rolls)}|total={len(roll_timestamps)}"
    for _, r in roll_window_diagnostics(res1, z, rolls).iterrows():
        key = "S_PF_" + str(r["bucket"]).replace(",", "_")
        out[key] = (f"n={int(r['n_bars'])}|sd={fmt(r['sd_dres_bps'], 3)}|"
                    f"mz={fmt(r['mean_abs_z'], 3)}|p99={fmt(r['p99_abs_z'], 3)}|"
                    f"tail={fmt(r['frac_abs_z_gt2'])}")

    common = factors_a.index.intersection(factors_b.index)
    shocks = np.array([held_position_roll_shock(float(factors_a[t]),
                                                float(factors_b[t]), 1.0)
                       for t in common])
    if len(shocks):
        s = np.abs(shocks)
        out["S_PF_SHOCK"] = (
            f"n={len(s)}|med={fmt(np.median(s), 2)}|"
            f"p90={fmt(np.percentile(s, 90), 2)}|max={fmt(s.max(), 2)}|"
            f"units=bps_of_S1_residual")
        recs = [f"{pd.Timestamp(t).strftime('%y%m%d')}:{fmt(v, 1)}"
                for t, v in zip(common, shocks)]
        for i in range(0, len(recs), 10):
            out[f"S_PF_SH{i // 10}"] = "|".join(recs[i:i + 10])
    return out


def _conditional_block(specs, entry_grid, horizons) -> dict[str, str]:
    """D-010 primary statistic. Layout per key:
    horizon:mean_bps:t_clustered:hit_rate:n_events, pipe-separated."""
    out: dict[str, str] = {}
    for name, res in specs.items():
        z = rolling_zscore(res, ZS_LOOKBACK)
        for ez in entry_grid:
            cr = conditional_reversion(res, z, entry_z=ez, horizons=horizons)
            out[f"S_CR_{name}_{str(ez).replace('.', '')}"] = "|".join(
                f"{int(r['horizon_bars'])}:{fmt(r['mean_bps'], 3)}:"
                f"{fmt(r['t_clustered'], 2)}:{fmt(r['hit_rate'], 3)}:"
                f"{int(r['n_events'])}" for _, r in cr.iterrows())
        if name == "S1":
            prof = event_clock_profile(z, 2.0)
            out["S_CLOCK"] = "|".join(
                f"{int(r['minutes_from_open'])}:{fmt(r['share'], 3)}"
                for _, r in prof.iterrows())
            raw, zz = half_life_within_session(res), half_life_within_session(z.dropna())
            out["S_HL"] = (
                f"raw_b={fmt(raw['b'], 7)}|raw_hl={fmt(raw['half_life_bars'], 1)}|"
                f"z_b={fmt(zz['b'], 7)}|z_hl={fmt(zz['half_life_bars'], 1)}|"
                f"n={int(zz['n'])}")
    return out


def _vr_blocks(specs, log_a, log_b, q_grid, n_boot, seed) -> dict[str, str]:
    """Variance-ratio curves. Layout per key: q:vr:ci_lo:ci_hi:p_lt_1.

    The leg curves are not decoration: a residual VR below 1 means nothing
    until it is compared against the bounce baseline its own legs set.
    """
    out: dict[str, str] = {}
    blocks = [("RES1", specs["S1"], (1, 5, 15)), ("RES2", specs["S2"], (1,)),
              ("LEGA", log_a, (1, 15)), ("LEGB", log_b, (1, 15))]
    for tag, x, steps in blocks:
        for st in steps:
            xs = subsample_within_session(x, st) if st > 1 else x
            parts = []
            for q in q_grid:
                v = variance_ratio(xs, q, n_boot=n_boot, seed=seed + q)
                parts.append(f"{q}:{fmt(v['vr'])}:{fmt(v['ci_lo'])}:"
                             f"{fmt(v['ci_hi'])}:{fmt(v['p_lt_1'], 3)}")
            out[f"S_VR_{tag}_s{st}"] = "|".join(parts)
    return out
