"""Notebook-15 battery: the same A-006/A-009 statistics measured on FIVE
session windows (D-024), for the four Treasury pairs.

Why this module exists at all, rather than another function in
`pair_minute_report.py`: L-020. QC's `files/update` rejects any file above
32,000 characters, and both `intraday_reversion.py` and `pair_minute_report.py`
sit within ~2,600 chars of that cap. `crosscorr.py` was split out for the same
reason.

Why the experiment exists (D-024 §1): D-020 and D-022 both carried a hard
ceiling of AMBIGUOUS / MICROSTRUCTURE because criterion (b) — the variance
ratio and its base-sampling checks — is computed on the RESIDUAL, and no
z-score and no entry bar enters it. **A session change is not like that.** It
changes which bars form the panel, hence the residual, hence the variance
ratios, the leg baselines, the per-session block counts and the bootstrap's
resampling unit. Criterion (b) must therefore be RECOMPUTED per window, and
this is the first battery since notebook 03 that can move a Treasury verdict on
its own terms.

The defect this battery also measures (L-021): `rth_frame` filters on the clock
the DATA carries. LEAN stamps CBOT Treasury bars in America/Chicago and index
bars in America/New_York, so `(09:30, 16:00]` gave the Treasury pairs
10:31-17:00 ET, not the documented 09:30-16:00 ET. **Every window below is
therefore expressed in the DATA's own stamps**, with its true ET span recorded
beside it, and a timezone witness is emitted so the assumption is checked
rather than trusted.
"""

from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

from .intraday_reversion import (
    conditional_reversion, event_clock_profile, first_minutes_mask, rth_frame,
    session_ids, subsample_within_session, variance_ratio,
)
from .pair_minute_report import (
    BETA_LOOKBACK, ENTRY_GRID, HORIZONS, Q_GRID, SEED, ZS_LOOKBACK, fmt,
    residual_specs,
)
from .signals import rolling_zscore

# ---------------------------------------------------------------------------
# The five windows, frozen by D-024 §2. Times are in the DATA's own stamps,
# which for the CBOT Treasuries is America/Chicago (L-021).
#
#   tag  name        stamps (CT)        true ET        bars   displacement
#   U    S-USED      (09:30, 16:00]     10:31-17:00    390     0   <- banked
#   H    S-HALF      (09:00, 15:30]     10:01-16:30    390    -30  <- PLACEBO
#   R    S-RTH       (08:30, 15:00]     09:31-16:00    390    -60
#   S    S-SETTLE    (08:30, 14:00]     09:31-15:00    330     -
#   C    S-CASH      (07:20, 14:00]     08:21-15:00    400     -   <- conditional
#
# S-HALF is anchored to nothing: 09:00 and 15:30 CT are neither an open, a
# close, nor a settlement. It measures how far this statistic moves per unit of
# window displacement ALONE, which is the control that lets a S-RTH movement be
# read as more than ordinary window sensitivity.
# ---------------------------------------------------------------------------

WINDOWS = {
    "U": ("S-USED",   time(9, 30), time(16, 0),  390),
    "H": ("S-HALF",   time(9, 0),  time(15, 30), 390),
    "R": ("S-RTH",    time(8, 30), time(15, 0),  390),
    "S": ("S-SETTLE", time(8, 30), time(14, 0),  330),
    "C": ("S-CASH",   time(7, 20), time(14, 0),  400),
}

# Which windows each backtest part computes AND emits. Splitting by window (as
# opposed to D-022's compute-everything-emit-half) keeps every part inside the
# L-019 ceiling without recomputing four variance-ratio batteries three times.
# The cross-part identity check still holds because the shared diagnostics are
# computed BEFORE any session filter.
PART_WINDOWS = {1: ("U", "H"), 2: ("R", "S"), 3: ("C",)}

# S-HALF is a placebo for the effect-size statistic only, so it carries no
# variance-ratio block: criterion (b) is never read off it.
VR_WINDOWS = ("U", "R", "S", "C")

OPEN_WINDOW_MINUTES = 30      # L-018(i) subset width, matching the event clock
CASH_PRE_LO = time(7, 20)     # the S-CASH block that regular-session fetches
CASH_PRE_HI = time(8, 30)     # do not deliver — its fill density is a FINDING

# LEAN's regular session for the CBOT Treasuries in the data's own (Chicago)
# stamps. Used as the denominator reference for every per-day rate: an extended
# Globex fetch spans 17:00 -> 16:00 and carries Sunday-evening dates with no
# 07:21-08:30 block at all, so counting every calendar date that holds any bar
# inflates the denominator ~1.2x and pushes every leg under the D-024 coverage
# floor for purely arithmetic reasons.
REGULAR_OPEN, REGULAR_CLOSE = time(8, 30), time(16, 0)


def session_window_analysis_keys(part: int | None = None) -> list[str]:
    """The frozen ANALYSIS-side key manifest (D-024 §5 gate 5).

    Single source of truth: the report filters its emission through this list
    and the ingest builds its per-part expected set from it, so the
    set-equality gate and the code cannot drift apart.
    """
    if part not in (None, 1, 2, 3):
        raise ValueError(f"part must be None, 1, 2 or 3, got {part!r}")
    tags = PART_WINDOWS[part] if part else tuple(WINDOWS)
    ezs = [str(ez).replace(".", "") for ez in ENTRY_GRID]
    # S_TZWIT is emitted by EVERY part: it is gate 1, and part 3 fetches
    # extended hours, so its delivered span is a different (and load-bearing)
    # observation from parts 1-2's. S_ACT is descriptive and needs one copy.
    keys = ["S_ALIGN", "S_SPECS", "S_SESSCFG", "S_TZWIT"]
    # S_ACT belongs to PART 3: it exists so a future experiment can define the
    # session open empirically, and only the extended fetch delivers the
    # pre-open bars it would look at. On a regular fetch the profile simply
    # starts at 08:30 CT and says nothing about 07:20.
    if part in (None, 3):
        keys += ["S_ACT"]
    for w in tags:
        keys += [f"S_CR{w}_{s}_{ez}" for s in ("S1", "S2", "S3") for ez in ezs]
        keys += [f"S_OPEN{w}", f"S_CLK{w}", f"S_GEO{w}"]
        if w in VR_WINDOWS:
            keys += [f"S_VRA{w}", f"S_VRB{w}"]
        if w == "C":
            keys += ["S_CASHCOV"]
    return keys


def _cr_value(cr: pd.DataFrame, sep: str = "|") -> str:
    """Grid-cell layout shared with notebooks 02/03/06/14, unchanged so the
    D-024 reproduction gate can compare against banked CSVs directly:
    horizon:mean_bps:mean_session_bps:t_clustered:hit_rate:n_events.

    `sep` exists because the open-window subset packs FOUR entry thresholds
    into one key: the outer join is "|", so the inner cells must not also be
    "|" or the two levels are indistinguishable on the way back.
    """
    return sep.join(
        f"{int(r['horizon_bars'])}:{fmt(r['mean_bps'], 3)}:"
        f"{fmt(r['mean_session_bps'], 3)}:{fmt(r['t_clustered'], 2)}:"
        f"{fmt(r['hit_rate'], 3)}:{int(r['n_events'])}"
        for _, r in cr.iterrows())


def _vr_pack(blocks) -> str:
    """Several variance-ratio curves in ONE key: tag_step~q:vr:lo:hi:p|...

    Packing is what keeps a five-window battery inside the L-019 ceiling. Each
    curve is ~180 chars, so four fit comfortably under the 960-char cap.
    """
    out = []
    for tag, x, step, q_grid, n_boot, seed in blocks:
        xs = subsample_within_session(x, step) if step > 1 else x
        cells = []
        for q in q_grid:
            v = variance_ratio(xs, q, n_boot=n_boot, seed=seed + q)
            cells.append(f"{q}:{fmt(v['vr'])}:{fmt(v['ci_lo'])}:"
                         f"{fmt(v['ci_hi'])}:{fmt(v['p_lt_1'], 3)}")
        out.append(f"{tag}_s{step}~" + ";".join(cells))
    return "|".join(out)


def _min_blocks(x: pd.Series, q: int) -> float:
    """Median non-overlapping VR blocks per session at horizon `q`.

    D-024 §5 gate 4's witness. A shorter session yields fewer blocks
    (`nblk = (len(seg)-1)//q`), so without this a degenerate variance-ratio
    tail on a 330-bar window could be mistaken for criterion (b) moving.
    """
    counts = []
    for lo, hi in _session_slices_of(x):
        n = hi - lo - 1
        if n >= q:
            counts.append(n // q)
    return float(np.median(counts)) if counts else float("nan")


def _session_slices_of(x: pd.Series):
    s = session_ids(x.index)
    change = np.flatnonzero(s[1:] != s[:-1]) + 1
    bounds = np.concatenate([[0], change, [len(s)]])
    return list(zip(bounds[:-1], bounds[1:]))


def _timezone_witness(close_a: pd.Series, close_b: pd.Series,
                      legs: tuple[str, str]) -> str:
    """D-024 §5 gate 1. Emits the observed time-of-day span and bars per
    calendar day of the CONSTRUCTED series, before any session filter.

    Bar count may never be used as a timezone witness — any 390-minute window
    inside a 23-hour session yields 390 bars, which is exactly how L-021 hid
    for seven runs. What discriminates is WHERE the delivered day starts and
    ends: a Chicago-stamped Treasury series reads 08:31/16:00, a New-York
    stamped index series 09:31/17:00.
    """
    parts = []
    for name, s in zip(legs, (close_a, close_b)):
        t = s.index.time
        per_day = pd.Series(1, index=s.index).groupby(s.index.normalize()).sum()
        parts.append(f"{name}={min(t).strftime('%H:%M')}-{max(t).strftime('%H:%M')}"
                     f":{int(per_day.median())}")
    return "|".join(parts) + "|note=stamps_are_exchange_tz_not_ET"


def _trading_days(s: pd.Series) -> int:
    """Dates carrying at least one REGULAR-session bar.

    The correct denominator for any per-day rate on an extended series: Sunday
    evenings and the post-close hour add calendar dates that never contain a
    regular session, and counting them silently deflates every density.
    """
    t = s.index.time
    reg = s.index[(t > REGULAR_OPEN) & (t <= REGULAR_CLOSE)]
    return max(1, pd.DatetimeIndex(reg).normalize().nunique())


def _activity_profile(close_a: pd.Series, close_b: pd.Series,
                      bucket: int = 30) -> str:
    """DESCRIPTIVE bar-count profile across the delivered day (D-024 §2).

    Emitted so a FUTURE experiment can define the session open empirically —
    which is why PART 3 owns it: only the extended fetch delivers the pre-open
    bars such a definition would have to look at. Fenced by D-024 §7: no branch
    label, no evidence-tag change, no open-thread consequence. In particular an
    activity peak near 07:20 CT may NOT promote the 08:20 ET open from a
    convention to a sourced boundary.

    Both legs are reported, because a window is tradable only if BOTH print.
    """
    out = []
    for s in (close_a, close_b):
        mins = np.asarray(s.index.hour * 60 + s.index.minute)
        b = (mins // bucket) * bucket
        counts = pd.Series(b).value_counts().sort_index()
        d = _trading_days(s)
        out.append({int(m): c / d for m, c in counts.items()})
    buckets = sorted(set(out[0]) | set(out[1]))
    return "|".join(f"{m}:{out[0].get(m, 0):.1f}/{out[1].get(m, 0):.1f}"
                    for m in buckets)


def _cash_coverage(close_a: pd.Series, close_b: pd.Series,
                   legs: tuple[str, str]) -> str:
    """Fill density of the 07:20-08:30 CT block that a regular-session fetch
    does not deliver (D-024 §5 gate 4).

    Reported as a FINDING, not gated to a hard bar count: outside the regular
    session `fill_forward=False` leaves minutes genuinely unpopulated (ZT fills
    ~70.7% of them), so a 400-bar requirement would fail on liquidity rather
    than on mechanics. A pre-open that does not print cannot be traded, which
    is itself an answer to A-013.
    """
    span = (CASH_PRE_HI.hour * 60 + CASH_PRE_HI.minute
            - CASH_PRE_LO.hour * 60 - CASH_PRE_LO.minute)
    parts = []
    for name, s in zip(legs, (close_a, close_b)):
        t = s.index.time
        blk = s[(t > CASH_PRE_LO) & (t <= CASH_PRE_HI)]
        parts.append(f"{name}={len(blk) / _trading_days(s) / span:.3f}")
    return "|".join(parts) + f"|span_min={span}|floor=0.80"


def session_window_report(close_a: pd.Series, close_b: pd.Series, *,
                          part: int | None = None, anchor: str = "vol_ratio",
                          entry_grid=ENTRY_GRID, horizons=HORIZONS,
                          q_grid=Q_GRID, n_boot: int = 400, seed: int = SEED,
                          legs_names: tuple[str, str] = ("A", "B"),
                          open_minutes: int = OPEN_WINDOW_MINUTES,
                          ) -> dict[str, str]:
    """The D-024 battery for one pair.

    Everything except the session window is frozen exactly as in
    D-010/A1/A2: the same three residual specifications (S3 look-ahead and
    never evidence), the same 4x5 entry/horizon grid, the same position-P&L
    outcome with beta frozen at the signal bar, the same session-clustered
    inference, the same seed, the same `rolling_zscore(residual, 390)` score.
    L-018 forbids introducing a session-anchored score here: it is not a strict
    improvement, and it would confound the session change with a signal change.

    Declared, not hidden (D-024 §7): 390 bars is exactly one session under
    S-USED/S-HALF/S-RTH, 1.18 sessions under S-SETTLE and 0.975 under S-CASH,
    so a Q2 movement is attributable to the window OR its interaction with the
    fixed 390-bar score — never to session structure alone.
    """
    out: dict[str, str] = {}
    # S_ALIGN describes the CONSTRUCTED series before any window is applied, so
    # it is one of the keys the cross-part identity gate compares. S_SESSCFG
    # (names the part) and S_SPECS (names the window its betas came from)
    # legitimately vary across parts and are NOT identity keys.
    out["S_ALIGN"] = (
        f"rawbars={len(close_a)}|rawdays={close_a.index.normalize().nunique()}|"
        f"first={close_a.index[0].date()}|last={close_a.index[-1].date()}")
    out["S_SESSCFG"] = (
        "|".join(f"{w}={WINDOWS[w][0]}@{WINDOWS[w][1].strftime('%H%M')}-"
                 f"{WINDOWS[w][2].strftime('%H%M')}:{WINDOWS[w][3]}"
                 for w in WINDOWS)
        + f"|part={part if part is not None else 'all'}|z=rolling{ZS_LOOKBACK}"
          f"|beta_lb={BETA_LOOKBACK}|anchor={anchor}|stamps=data_native")
    out["S_TZWIT"] = _timezone_witness(close_a, close_b, legs_names)
    out["S_ACT"] = _activity_profile(close_a, close_b)
    out["S_CASHCOV"] = _cash_coverage(close_a, close_b, legs_names)

    spec_line = None
    for w in (PART_WINDOWS[part] if part else tuple(WINDOWS)):
        _, open_t, close_t, want_bars = WINDOWS[w]
        a = rth_frame(close_a, open_t=open_t, close_t=close_t)
        b = rth_frame(close_b, open_t=open_t, close_t=close_t)
        df = pd.concat({"a": a, "b": b}, axis=1, join="inner").dropna()
        if df.empty:
            out[f"S_GEO{w}"] = "EMPTY|no overlapping bars"
            continue
        log_a, log_b = np.log(df["a"]), np.log(df["b"])
        specs, info = residual_specs(log_a, log_b, anchor=anchor)
        betas, legs = info["betas"], (log_a, log_b)

        per_session = pd.Series(1, index=df.index).groupby(
            df.index.normalize()).sum()
        out[f"S_GEO{w}"] = (
            f"bars={len(df)}|sessions={len(per_session)}|"
            f"medbars={int(per_session.median())}|want={want_bars}|"
            f"blocks_q120={fmt(_min_blocks(specs['S1'], 120), 1)}|"
            f"dropA={len(a) - len(df)}|dropB={len(b) - len(df)}")

        if spec_line is None:
            b1 = betas["S1"]
            spec_line = (f"anchor={anchor}|S1_beta_med={fmt(b1.median())}|"
                         f"S1_beta_p5={fmt(b1.quantile(.05))}|"
                         f"S1_beta_p95={fmt(b1.quantile(.95))}|win={w}")

        for name, res in specs.items():
            z = rolling_zscore(res, ZS_LOOKBACK)
            for ez in entry_grid:
                cr = conditional_reversion(res, z, entry_z=ez,
                                           horizons=horizons, legs=legs,
                                           beta=betas[name])
                out[f"S_CR{w}_{name}_{str(ez).replace('.', '')}"] = _cr_value(cr)

        # L-018(i): every window here uses the overnight-spanning score, so
        # each owes its open-window subset separately. EXPLORATORY, fenced by
        # D-024 §7 — descriptive only, no branch label, no consequence.
        z1 = rolling_zscore(specs["S1"], ZS_LOOKBACK)
        is_open = first_minutes_mask(specs["S1"].index, open_minutes,
                                     open_t=open_t)
        subs = []
        for ez in entry_grid:
            cr = conditional_reversion(specs["S1"], z1, entry_z=ez,
                                       horizons=horizons, legs=legs,
                                       beta=betas["S1"], event_filter=is_open)
            subs.append(f"{str(ez).replace('.', '')}~"
                        + _cr_value(cr, sep=";"))
        out[f"S_OPEN{w}"] = "|".join(subs)

        prof = event_clock_profile(z1, 2.0, open_t=open_t)
        # Never emit an EMPTY value: the summary-statistic channel may drop one
        # silently, which would fail the set-equality gate for a reason that has
        # nothing to do with the science.
        out[f"S_CLK{w}"] = "|".join(
            f"{int(r['minutes_from_open'])}:{fmt(r['share'], 3)}"
            for _, r in prof.iterrows()) or "none|no_crossings"

        if w in VR_WINDOWS:
            out[f"S_VRA{w}"] = _vr_pack([
                ("RES1", specs["S1"], 1, q_grid, n_boot, seed),
                ("RES1", specs["S1"], 5, q_grid, n_boot, seed),
                ("RES1", specs["S1"], 15, q_grid, n_boot, seed),
                ("RES2", specs["S2"], 1, q_grid, n_boot, seed)])
            out[f"S_VRB{w}"] = _vr_pack([
                ("LEGA", log_a, 1, q_grid, n_boot, seed),
                ("LEGA", log_a, 15, q_grid, n_boot, seed),
                ("LEGB", log_b, 1, q_grid, n_boot, seed),
                ("LEGB", log_b, 15, q_grid, n_boot, seed)])

    out["S_SPECS"] = spec_line or "no window produced a panel"

    keep = session_window_analysis_keys(part)
    missing = [k for k in keep if k not in out]
    if missing:
        raise RuntimeError(f"emission does not cover manifest: {missing}")
    return {k: out[k] for k in keep}
