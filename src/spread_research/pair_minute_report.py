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
    conditional_reversion, event_clock_profile, first_minutes_mask,
    half_life_within_session, held_position_roll_shock, roll_window_diagnostics,
    rth_frame, session_anchored_zscore, session_ids, subsample_within_session,
    variance_ratio,
)
from .signals import rolling_zscore

ZS_LOOKBACK = 390        # research_config signals.zscore_lookback_bars
BETA_LOOKBACK = 1950     # research_config hedge.lookback_bars (~1 RTH week)
ENTRY_GRID = (1.5, 2.0, 2.5, 3.0)
HORIZONS = (5, 15, 30, 60, 120)
Q_GRID = (2, 5, 15, 30, 60, 120)
SEED = 20260801

# D-020 (notebook 06 / L-013). Both are frozen by the pre-registration and are
# not tuning parameters: the warm-up is set by the precision of a standard
# deviation from n observations, and the open window matches the event clock's
# leading bucket so the signal and the diagnostic cannot disagree about which
# events are "at the open".
SESSION_WARMUP_BARS = 30
OPEN_WINDOW_MINUTES = 30


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


def vol_ratio_beta(y: pd.Series, x: pd.Series, window: int) -> pd.Series:
    """Volatility-ratio hedge in LOG space: beta = sigma_y / sigma_x on
    trailing within-session log returns, shifted so nothing at t is used.

    Derivation (why prices and multipliers vanish). Holding 1 contract of A and
    n_b of B, dollar P&L ~ mult_a*P_a*dlog(P_a) - n_b*mult_b*P_b*dlog(P_b).
    Dollar-vol neutrality sets n_b = (mult_a*P_a*sigma_a)/(mult_b*P_b*sigma_b),
    and normalising the spread by leg A's notional leaves

        beta = n_b*mult_b*P_b / (mult_a*P_a) = sigma_a / sigma_b.

    This is the estimation-LIGHT adaptive hedge D-008 mandates for the Treasury
    pairs: it uses one robust moment per leg rather than a regression, so it
    carries far less estimation noise than OLS (L-007), while still adapting to
    the regime shifts the daily screen found (ZT-ZN 126d beta ranged 0.0-0.4
    over 2010-26). A unit beta is NOT a sensible anchor across the curve — ZT
    has roughly a fifth of ZN's duration, so a 1:1 log spread is just the long
    leg with noise.
    """
    ry, rx = y.diff(), x.diff()
    same = pd.Series(session_ids(y.index), index=y.index)
    boundary = same != same.shift(1)
    ry[boundary], rx[boundary] = np.nan, np.nan
    sy = ry.rolling(window, min_periods=window // 2).std()
    sx = rx.rolling(window, min_periods=window // 2).std()
    return (sy / sx.replace(0.0, np.nan)).shift(1)


def centered_residual(y: pd.Series, x: pd.Series, beta: pd.Series,
                      window: int) -> pd.Series:
    """Deviation from the TRAILING fitted line for ANY supplied (shifted) beta:

        resid_t = (y_t - my_{t-1}) - beta_{t-1} * (x_t - mx_{t-1})

    The centering is not cosmetic. Dropping it and computing `y_t - beta_t*x_t`
    on log PRICES multiplies every wobble in beta by the log price LEVEL, and
    that level is large: log(38,000) = 10.5 for MYM, log(110) = 4.7 for a
    Treasury future. A beta moving just 0.001 between refits therefore injects
    ~105 bps of spurious residual on MYM and ~5 bps on ZN — in both cases
    larger than the effect under study (L-011).
    """
    mx, my = x.rolling(window).mean(), y.rolling(window).mean()
    return ((y - my.shift(1)) - beta * (x - mx.shift(1))).dropna()


def rolling_ols_residual(y: pd.Series, x: pd.Series, window: int) -> pd.Series:
    """Deviation from the TRAILING OLS fitted line, intercept included:

        resid_t = (y_t - my_{t-1}) - beta_{t-1} * (x_t - mx_{t-1})

    where `mx`, `my`, and `beta` are estimated on the `window` bars ending at
    t-1, so nothing at t enters its own residual.

    Why the intercept is not optional here. An OLS slope is defined on demeaned
    data, so the matching residual must be measured around the full fitted line.
    See `centered_residual` for the magnitude: on MYM a 0.001 beta wobble
    injects ~105 bps of spurious residual, which shows up as violent,
    sign-flipping "reversion" that is pure hedge-estimation noise (L-007,
    L-011).

    `pair_builder.build_residual` deliberately keeps the no-intercept form,
    which is correct for a hedge ratio that is NOT fitted (notional, DV01).
    Fitted betas must come through this function instead.
    """
    return centered_residual(y, x, rolling_beta(y, x, window), window)


def residual_specs(log_a: pd.Series, log_b: pd.Series, *,
                   beta_lookback: int = BETA_LOOKBACK,
                   anchor: str = "unit") -> tuple[dict[str, pd.Series], dict]:
    """The three D-010 specifications. None is privileged after the fact.

    `anchor` selects what S1 is, and it is an ECONOMIC choice, not a knob:

      "unit"      S1 = log ratio, beta = 1. Correct for the equity-index pairs,
                  where both legs are large-cap index futures of similar
                  duration and volatility.
      "vol_ratio" S1 = volatility-ratio hedge, beta = sigma_a/sigma_b. Required
                  for the Treasury pairs: ZT has ~1/5 of ZN's duration, so a
                  1:1 log spread is the long leg plus noise, not a spread.
                  This is also D-008's mandated adaptive hedge for the curve.

    S2  trailing OLS residual         look-ahead safe, carries L-007 hedge noise
    S3  full-sample static OLS        LOOK-AHEAD CONTAMINATED — diagnostic only,
                                      and per D-008 a CONTROL for Treasuries

    S2 and S3 are residuals around the FITTED LINE (intercept included) — see
    `rolling_ols_residual` for why omitting the intercept on log prices
    manufactures hedge noise an order of magnitude larger than the effect
    under study. D-010 froze "trailing-window OLS beta"; taking the residual
    around the full OLS fit is the faithful reading of that, not a departure
    from it.
    """
    if anchor not in ("unit", "vol_ratio"):
        raise ValueError(f"unknown anchor {anchor!r}")
    beta_roll = rolling_beta(log_a, log_b, beta_lookback)
    beta_static, alpha_static = (float(v) for v in
                                 np.polyfit(log_b.values, log_a.values, 1))
    if anchor == "unit":
        beta_1 = pd.Series(1.0, index=log_a.index)
        s1 = (log_a - log_b).rename("S1")
    else:
        beta_1 = vol_ratio_beta(log_a, log_b, beta_lookback)
        s1 = centered_residual(log_a, log_b, beta_1, beta_lookback).rename("S1")
    specs = {
        "S1": s1,
        "S2": rolling_ols_residual(log_a, log_b, beta_lookback).rename("S2"),
        "S3": (log_a - alpha_static - beta_static * log_b).rename("S3"),
    }
    # The hedge ratio each spec would actually trade, known at the signal bar.
    # conditional_reversion needs this to price a POSITION rather than to
    # difference a residual whose reference point moves (see its docstring).
    betas = {
        "S1": beta_1,
        "S2": beta_roll,
        "S3": pd.Series(beta_static, index=log_a.index),
    }
    info = {"beta_static": beta_static, "beta_roll": beta_roll,
            "betas": betas, "anchor": anchor}
    return specs, info


def pair_minute_report(close_a: pd.Series, close_b: pd.Series, *,
                       roll_timestamps, factors_a: pd.Series,
                       factors_b: pd.Series, n_boot: int = 400,
                       q_grid=Q_GRID, entry_grid=ENTRY_GRID,
                       horizons=HORIZONS, seed: int = SEED,
                       anchor: str = "unit") -> dict[str, str]:
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

    specs, info = residual_specs(log_a, log_b, anchor=anchor)
    b1 = info["betas"]["S1"]
    out["S_SPECS"] = (
        f"anchor={anchor}|S1={'log_ratio_beta1' if anchor == 'unit' else 'vol_ratio_sigma_a_over_sigma_b'}"
        f"|S1_beta_med={fmt(b1.median())}|S1_beta_p5={fmt(b1.quantile(.05))}"
        f"|S1_beta_p95={fmt(b1.quantile(.95))}")
    br = info["beta_roll"]
    out["S_BETA"] = (
        f"static={fmt(info['beta_static'])}|roll_med={fmt(br.median())}|"
        f"roll_p5={fmt(br.quantile(.05))}|roll_p95={fmt(br.quantile(.95))}|"
        f"n={int(br.notna().sum())}")

    out.update(_preflight(specs["S1"], df.index, roll_timestamps,
                          factors_a, factors_b))
    out.update(_conditional_block(specs, info["betas"], (log_a, log_b),
                                  entry_grid, horizons))
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


def _conditional_block(specs, betas, legs, entry_grid, horizons) -> dict[str, str]:
    """D-010 primary statistic, measured as POSITION P&L (amendment A2).

    Layout per key, pipe-separated:
    horizon:mean_bps:mean_session_bps:t_clustered:hit_rate:n_events

    `mean_session_bps` is the mean of per-session means — the quantity the
    session-clustered t-statistic actually refers to. It is reported next to
    the event-pooled mean because the two weight differently and can even
    disagree in sign when high-event-count sessions behave unlike the typical
    session; quoting the pooled mean beside a clustered t would be a mismatch.
    """
    out: dict[str, str] = {}
    for name, res in specs.items():
        z = rolling_zscore(res, ZS_LOOKBACK)
        for ez in entry_grid:
            cr = conditional_reversion(res, z, entry_z=ez, horizons=horizons,
                                       legs=legs, beta=betas[name])
            out[f"S_CR_{name}_{str(ez).replace('.', '')}"] = "|".join(
                f"{int(r['horizon_bars'])}:{fmt(r['mean_bps'], 3)}:"
                f"{fmt(r['mean_session_bps'], 3)}:{fmt(r['t_clustered'], 2)}:"
                f"{fmt(r['hit_rate'], 3)}:{int(r['n_events'])}"
                for _, r in cr.iterrows())
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


# ---------------------------------------------------------------------------
# Notebook 06 — signal definition (L-013), pre-registered in D-020
# ---------------------------------------------------------------------------


def pair_signal_report(close_a: pd.Series, close_b: pd.Series, *,
                       entry_grid=ENTRY_GRID, horizons=HORIZONS,
                       anchor: str = "unit",
                       warmup_bars: int = SESSION_WARMUP_BARS,
                       open_minutes: int = OPEN_WINDOW_MINUTES,
                       ) -> dict[str, str]:
    """The D-020 battery: one pair, one data path, three signal definitions.

    Z0  `rolling_zscore(residual, 390)` — the configured score, whose window is
        exactly one RTH session and therefore reaches back across the overnight
        break. Re-emitted here ONLY as a reproduction gate: it must match the
        banked notebook-02/03 grid for the same pair cell for cell, otherwise
        the pipeline changed and no Z0-vs-Z1 comparison means anything.
    Z1  `session_anchored_zscore(residual, warmup_bars)` — the fix under test.
    Z2  Z0's events with those in the first `open_minutes` of the session
        dropped. Z2 exists because Z1 changes two things at once (how the open
        is SCORED and whether it TRADES); without Z2 a difference could not be
        attributed to either.

    Everything else is frozen as in D-010/A1/A2: same residual specifications,
    same 4x5 grid, same position-P&L outcome with beta frozen at the signal
    bar, same session-clustered inference.

    Variance-ratio blocks are deliberately absent. They are functions of the
    residual and the sampling interval only — no z-score enters them — so
    criterion (b) is inherited unchanged from EXP-008/009/010/011 and
    recomputing it here would spend the run's output budget reproducing
    identical numbers. This is also why the D-020 test CANNOT move a pair to
    REVERSION PRESENT: (b) already failed everywhere and a signal change cannot
    touch it.

    The open-only subset is reported for S1 alone and is EXPLORATORY: overnight
    gap reversion is a different hypothesis from A-006, and D-020 issues no
    verdict on it.
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
    out["S_SIGDEF"] = (f"z0=rolling{ZS_LOOKBACK}|z1=session_anchored"
                       f"|warmup={warmup_bars}|open_win={open_minutes}"
                       f"|vr=inherited_from_nb02")

    specs, info = residual_specs(log_a, log_b, anchor=anchor)
    betas, legs = info["betas"], (log_a, log_b)
    b1 = betas["S1"]
    out["S_SPECS"] = (
        f"anchor={anchor}|S1_beta_med={fmt(b1.median())}|"
        f"S1_beta_p5={fmt(b1.quantile(.05))}|S1_beta_p95={fmt(b1.quantile(.95))}")

    for name, res in specs.items():
        z0 = rolling_zscore(res, ZS_LOOKBACK)
        z1 = session_anchored_zscore(res, warmup_bars)
        not_open = ~first_minutes_mask(res.index, open_minutes)

        variants = [("0", z0, None, False), ("1", z1, None, True),
                    ("2", z0, not_open, False)]
        if name == "S1":
            variants.append(("O", z0, ~not_open, False))    # EXPLORATORY
        for tag, z, filt, bounded in variants:
            for ez in entry_grid:
                cr = conditional_reversion(
                    res, z, entry_z=ez, horizons=horizons, legs=legs,
                    beta=betas[name], event_filter=filt,
                    session_bounded_events=bounded)
                out[f"S_CR{tag}_{name}_{str(ez).replace('.', '')}"] = "|".join(
                    f"{int(r['horizon_bars'])}:{fmt(r['mean_bps'], 3)}:"
                    f"{fmt(r['mean_session_bps'], 3)}:{fmt(r['t_clustered'], 2)}:"
                    f"{fmt(r['hit_rate'], 3)}:{int(r['n_events'])}"
                    for _, r in cr.iterrows())

        if name == "S1":
            out.update(_signal_diagnostics(res, z0, z1, open_minutes))
    return out


def _signal_diagnostics(res: pd.Series, z0: pd.Series, z1: pd.Series,
                        open_minutes: int) -> dict[str, str]:
    """The D-020 implementation gate, plus the coverage cost of the warm-up.

    The gate is mechanical and is read BEFORE any grid: under Z1 the share of
    crossings inside the warm-up must be zero by construction, and the profile
    must flatten. If it does not, the anchor is not doing what L-013 says it
    does and the run is void rather than interesting.
    """
    out: dict[str, str] = {}
    for tag, z, bounded in (("0", z0, False), ("1", z1, True)):
        prof = event_clock_profile(z, 2.0, session_bounded=bounded)
        out[f"S_CLOCK{tag}"] = "|".join(
            f"{int(r['minutes_from_open'])}:{fmt(r['share'], 3)}"
            for _, r in prof.iterrows())
        lead = prof[prof["minutes_from_open"] < open_minutes]["share"].sum()
        out[f"S_OPENSHARE{tag}"] = (
            f"share={fmt(lead, 4)}|n_events={int(prof['n_events'].sum())}")

    sess = session_ids(res.index)
    first_bar = np.concatenate([[True], sess[1:] != sess[:-1]])
    az0 = z0.abs().values
    cross0 = np.concatenate([[False], (az0[1:] >= 2.0) & (az0[:-1] < 2.0)])
    out["S_ZCOVER"] = (
        f"z0_defined={int(z0.notna().sum())}|z1_defined={int(z1.notna().sum())}|"
        f"bars={len(res)}|z0_first_bar_events={int((cross0 & first_bar).sum())}")

    hl = half_life_within_session(z1.dropna())
    out["S_HL1"] = (f"z1_b={fmt(hl['b'], 7)}|z1_hl={fmt(hl['half_life_bars'], 1)}|"
                    f"n={int(hl['n'])}")
    return out
