"""Intraday mean-reversion characterization for hedged pair residuals
(notebook 02 / hypotheses A-006, A-009).

Design constraints that shaped this module:

1. **It must run inside QuantConnect's backtest sandbox**, where the analysis
   is executed against constructed own-splice minute series (D-009). So:
   numpy/pandas only — no statsmodels, no scipy. Every statistic here is
   closed-form or bootstrap.
2. **Sessions are hard boundaries.** An overnight gap is not an intraday
   return. Every return, every q-period block and every forward horizon is
   computed strictly inside one RTH session; nothing straddles a close.
3. **Microstructure bounce is the null, not the discovery.** Bid-ask bounce
   alone produces negative first-order autocorrelation and hence a variance
   ratio below 1, so "VR < 1" is not by itself evidence of anything. For an
   observed price equal to a random walk of per-bar variance s2 plus i.i.d.
   bounce of variance b2, versus a mean-reverting AR(1) with coefficient phi:

       bounce:    VR(q) = (s2 + 2*b2/q) / (s2 + 2*b2)  ->  s2/(s2+2*b2) > 0
       reversion: VR(q) = (1 - phi**q) / (q*(1 - phi)) ->  ~1/(q*(1-phi)) -> 0

   BOTH fall with q, so the slope alone does not separate them. Two things do:

   (a) **Shape.** Bounce drops fast and then FLATTENS onto a positive floor —
       essentially all of its effect is spent by q ~ 10. Reversion keeps
       decaying like 1/q out to and past its half-life. Compare VR at a long
       q against VR at a medium q rather than against 1.
   (b) **Base sampling frequency.** Coarsen the bars and s2 scales with the
       sampling interval while b2 does not, so a bounce-driven VR marches back
       toward 1 while a genuine reversion signature survives. `variance_ratio`
       is therefore run at several base frequencies via
       `subsample_within_session`.

   This matters most for a hedged residual, where the hedge cancels common
   variance (shrinking s2) while the two legs' bounce ADDS (inflating b2) —
   exactly the configuration that manufactures a spurious VR far below 1 at
   q = 2. Hence the third guard: the same curves are computed on each leg
   alone as a bounce baseline.

   Note that `conditional_reversion` is structurally immune to first-order
   bounce (see its docstring), which is why it, not the variance ratio, is
   the primary evidence here.
4. **Inference is clustered by session.** 7 years of minute bars is ~690k
   observations; i.i.d. standard errors would make economically meaningless
   effects overwhelmingly "significant". Session-level clustering (and a
   session bootstrap for the variance ratio) is the honest unit of
   independence.
5. **No look-ahead.** Entries are measured from the bar AFTER the signal bar
   (matching the signals.py convention), so the close that generated a z-score
   is never the close that fills it — this also removes one bar of bounce.

Effect sizes are reported in basis points of the residual (which is a log
spread, so a difference of 1e-4 is 1 bp of relative price). Whether an effect
in bps survives costs is notebook 07's question, not this module's.
"""

from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

# RTH for the equity-index micros: 09:30-16:00 ET (config research_config.yaml
# session_filter, 08:30-15:00 CT). Half-open on the left so the window contains
# exactly 390 minute bars whether LEAN stamps bars at their start or their end;
# see `rth_frame` for why that ambiguity is harmless here.
RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def rth_frame(df: pd.DataFrame | pd.Series, *, open_t: time = RTH_OPEN,
              close_t: time = RTH_CLOSE) -> pd.DataFrame | pd.Series:
    """Restrict to `(open_t, close_t]` — 390 minute bars per full session.

    The half-open convention is deliberate: LEAN's history frame stamps minute
    bars at one end of the interval and the project has not pinned down which,
    so `(09:30, 16:00]` yields exactly the 390 RTH bars under end-stamping and
    a 390-bar window shifted by one minute under start-stamping. Since the
    first return of each session is discarded anyway (it would be the
    overnight gap), neither reading contaminates any statistic here. Callers
    should report the observed bars-per-session as a diagnostic.
    """
    t = df.index.time
    return df[(t > open_t) & (t <= close_t)]


def session_ids(index: pd.DatetimeIndex) -> np.ndarray:
    """Session label per bar. RTH sits inside one calendar day in ET, so the
    normalized date is the session id."""
    return index.normalize().values


def _session_slices(sessions: np.ndarray) -> list[tuple[int, int]]:
    """Contiguous [start, stop) positions of each session. Requires the input
    to be sorted (it is: constructed series are sorted and de-duplicated)."""
    if len(sessions) == 0:
        return []
    change = np.flatnonzero(sessions[1:] != sessions[:-1]) + 1
    bounds = np.concatenate([[0], change, [len(sessions)]])
    return list(zip(bounds[:-1], bounds[1:]))


def within_session_returns(x: pd.Series) -> pd.Series:
    """First difference, with the first bar of every session dropped so no
    overnight gap enters. `x` is expected in log units (the residual, or a log
    price), so the difference is a return."""
    s = session_ids(x.index)
    d = x.diff()
    d[np.concatenate([[True], s[1:] != s[:-1]])] = np.nan
    return d.dropna().rename("ret")


def bars_per_session(index: pd.DatetimeIndex) -> pd.Series:
    s = session_ids(index)
    return pd.Series(1, index=pd.DatetimeIndex(s)).groupby(level=0).sum()


def subsample_within_session(x: pd.Series, step: int) -> pd.Series:
    """Keep every `step`-th bar of each session (session-anchored, so a
    subsampled bar never pairs across a close).

    Used to separate microstructure bounce from genuine reversion: coarsening
    the base frequency scales the efficient-price variance by `step` while
    leaving the bounce variance untouched, so a bounce-driven variance ratio
    moves back toward 1 and a real reversion signature does not.
    """
    if step < 1:
        raise ValueError(f"step must be >= 1, got {step}")
    if step == 1:
        return x
    keep = np.zeros(len(x), dtype=bool)
    for lo, hi in _session_slices(session_ids(x.index)):
        keep[lo:hi:step] = True
    return x[keep]


# ---------------------------------------------------------------------------
# Session-anchored signal definition (L-013, pre-registered in D-020)
# ---------------------------------------------------------------------------


def session_anchored_zscore(x: pd.Series, warmup_bars: int = 30) -> pd.Series:
    """Z-score against the statistics of THIS SESSION ONLY, up to bar t-1.

    The configured `rolling_zscore(residual, 390)` uses a 390-bar window, which
    is exactly one RTH session — so at the open it reaches back across the
    overnight break and scores the first bars of a session against yesterday's
    mean. An overnight repricing then registers as an intraday dislocation:
    22.7-24.7% of |z| >= 2 crossings in the index pairs land in the first 30
    minutes, against 12.7-13.6% in the Treasury pairs, which trade through the
    night and for which 09:30 ET is not an open at all (L-013).

    This is the fix: an expanding within-session window, so no bar from any
    prior session enters. Because an RTH session is 390 bars, this is the SAME
    object as "trailing 390 bars truncated at the session open" — the fix
    introduces no new window-length parameter.

    `warmup_bars` bars at the start of each session return NaN, because a
    standard deviation from a handful of observations is noisier than the
    artifact being removed (at n = 30 its relative standard error is still
    ~13%). No event can fire inside the warm-up.

    Same convention as `signals.rolling_zscore`: bar t is compared against
    statistics ending at t-1, so the current bar never contributes to its own
    normalization. A NaN anywhere in a session propagates to the rest of that
    session rather than being silently skipped — callers pass NaN-free
    residuals, and a silent skip would corrupt the window rather than announce
    itself.
    """
    if warmup_bars < 2:
        raise ValueError(f"warmup_bars must be >= 2, got {warmup_bars}")
    v = x.values.astype(float)
    out = np.full(len(v), np.nan)
    for lo, hi in _session_slices(session_ids(x.index)):
        seg = v[lo:hi]
        n = len(seg)
        if n <= warmup_bars:
            continue
        k = np.arange(n, dtype=float)                    # prior bars available
        c1 = np.concatenate([[0.0], np.cumsum(seg)])[:n]
        c2 = np.concatenate([[0.0], np.cumsum(seg * seg)])[:n]
        with np.errstate(divide="ignore", invalid="ignore"):
            mean = c1 / k
            var = (c2 - k * mean ** 2) / (k - 1.0)
            sd = np.sqrt(np.where(var > 0, var, np.nan))
            z = (seg - mean) / sd
        z[:warmup_bars] = np.nan
        out[lo:hi] = z
    return pd.Series(out, index=x.index, name="zscore_session")


def first_minutes_mask(index: pd.DatetimeIndex, minutes: int = 30, *,
                       open_t: time = RTH_OPEN) -> pd.Series:
    """True for bars inside the first `minutes` of the session.

    Uses the same arithmetic as `event_clock_profile`, so "first 30 minutes"
    here is exactly that profile's leading bucket and the two diagnostics
    cannot disagree about which events are "at the open".
    """
    mins = np.asarray((index.hour * 60 + index.minute)
                      - (open_t.hour * 60 + open_t.minute))
    return pd.Series((mins >= 0) & (mins < minutes), index=index,
                     name=f"first_{minutes}min")


# ---------------------------------------------------------------------------
# Variance ratio
# ---------------------------------------------------------------------------


_VR_COLS = ("s1", "ss1", "n1", "sq", "ssq", "nq")


def _vr_session_sums(x: pd.Series, q: int) -> np.ndarray:
    """Per-session sums for a NON-OVERLAPPING variance-ratio estimator.

    Non-overlapping blocks are used instead of Lo-MacKinlay overlapping blocks
    because the finite-sample correction for overlapping blocks is a function
    of session length (T=390 vs q=120 makes it a 30% adjustment, not a
    rounding error), and because non-overlapping blocks keep the session
    bootstrap below exactly independent. With ~1,700 sessions the efficiency
    loss is affordable; correctness is not.

    Returns an (n_sessions, 6) float array of the sufficient statistics named
    by `_VR_COLS`. Sufficient statistics rather than raw returns is what makes
    the session bootstrap cheap enough to run inside the QC sandbox.
    """
    vals = x.values.astype(float)
    sess = session_ids(x.index)
    rows = []
    for lo, hi in _session_slices(sess):
        seg = vals[lo:hi]
        if len(seg) < q + 1:
            continue
        r1 = np.diff(seg)                       # within-session 1-bar returns
        nblk = len(r1) // q
        if nblk < 1:
            continue
        rq = r1[:nblk * q].reshape(nblk, q).sum(axis=1)
        rows.append((r1.sum(), (r1 ** 2).sum(), float(len(r1)),
                     rq.sum(), (rq ** 2).sum(), float(nblk)))
    return np.array(rows, dtype=float).reshape(-1, len(_VR_COLS))


def _vr_from_sums(tot: np.ndarray, q: int) -> np.ndarray:
    """Vectorized over any leading axes: `tot[..., :]` holds the column sums in
    `_VR_COLS` order, so one call evaluates the point estimate or a whole stack
    of bootstrap replicates."""
    s1, ss1, n1, sq, ssq, nq = (tot[..., i] for i in range(len(_VR_COLS)))
    with np.errstate(divide="ignore", invalid="ignore"):
        mu = s1 / n1
        var1 = (ss1 - 2 * mu * s1 + n1 * mu ** 2) / (n1 - 1)
        muq = q * mu
        varq = (ssq - 2 * muq * sq + nq * muq ** 2) / (nq - 1)
        vr = varq / (q * var1)
    return np.where((n1 > 1) & (nq > 1) & (var1 > 0), vr, np.nan)


def variance_ratio(x: pd.Series, q: int, *, n_boot: int = 1000,
                   seed: int = 20260801) -> dict:
    """VR(q) = Var(q-bar return) / (q * Var(1-bar return)) on within-session
    non-overlapping blocks.

    VR < 1 => mean reversion at that horizon; VR = 1 => random walk;
    VR > 1 => trending. The confidence interval comes from resampling whole
    SESSIONS with replacement, which is robust to heteroskedasticity, to
    intraday seasonality, and to any within-day dependence structure.

    `p_lt_1` is the bootstrap share of replicates with VR >= 1 — a one-sided
    p-value for the mean-reversion claim.
    """
    if q < 2:
        raise ValueError(f"q must be >= 2, got {q}")
    arr = _vr_session_sums(x, q)
    n_sess = len(arr)
    point = float(_vr_from_sums(arr.sum(axis=0), q)) if n_sess else np.nan
    out = {"q": q, "vr": point, "n_sessions": int(n_sess),
           "n_returns": int(arr[:, 2].sum()) if n_sess else 0,
           "n_blocks": int(arr[:, 5].sum()) if n_sess else 0,
           "ci_lo": np.nan, "ci_hi": np.nan, "p_lt_1": np.nan}
    if n_sess < 10 or point != point:
        return out
    rng = np.random.default_rng(seed)
    reps = np.empty(n_boot)
    chunk = max(1, min(n_boot, 2_000_000 // max(n_sess, 1)))   # bound peak RAM
    for lo in range(0, n_boot, chunk):
        hi = min(lo + chunk, n_boot)
        idx = rng.integers(0, n_sess, size=(hi - lo, n_sess))
        reps[lo:hi] = _vr_from_sums(arr[idx].sum(axis=1), q)
    reps = reps[np.isfinite(reps)]
    if len(reps) < n_boot // 2:
        return out
    out["ci_lo"], out["ci_hi"] = (float(v) for v in
                                  np.percentile(reps, [2.5, 97.5]))
    out["p_lt_1"] = float((reps >= 1.0).mean())
    return out


def variance_ratio_curve(x: pd.Series, qs=(2, 5, 15, 30, 60, 120), *,
                         n_boot: int = 1000, seed: int = 20260801) -> pd.DataFrame:
    """VR across horizons. Read the shape, not just the level: bounce and
    reversion both push VR below 1, but bounce flattens onto a floor by
    q ~ 10 while reversion keeps decaying. Pair this with the same curve on
    `subsample_within_session(x, step)` and on each leg alone before reading
    any VR < 1 as a relationship."""
    return pd.DataFrame([variance_ratio(x, q, n_boot=n_boot, seed=seed + q)
                         for q in qs])


# ---------------------------------------------------------------------------
# Half-life
# ---------------------------------------------------------------------------


def half_life_within_session(x: pd.Series) -> dict:
    """AR(1) half-life estimated on pooled WITHIN-SESSION pairs only.

    d_x = a + b * x_{t-1}, half-life = -ln(2)/ln(1+b), in bars. Pairs that
    straddle a session boundary are excluded, so an overnight gap can never
    masquerade as a reversion step. Feed this the *demeaned* residual (e.g.
    residual minus its trailing rolling mean, or the z-score itself) when the
    question is intraday reversion: run on the raw residual it measures the
    long-run level anchor instead, which is a different claim.
    """
    v = x.astype(float)
    s = session_ids(v.index)
    same = np.concatenate([[False], s[1:] == s[:-1]])
    lag = v.shift(1).values
    d = v.values - lag
    keep = same & np.isfinite(lag) & np.isfinite(d)
    n = int(keep.sum())
    if n < 100:
        return {"b": np.nan, "half_life_bars": np.nan, "n": n}
    X = np.vstack([np.ones(n), lag[keep]]).T
    coef, *_ = np.linalg.lstsq(X, d[keep], rcond=None)
    b = float(coef[1])
    hl = -np.log(2.0) / np.log(1.0 + b) if (-2 < b < 0) else np.nan
    return {"b": b, "half_life_bars": float(hl) if hl == hl else np.nan, "n": n}


# ---------------------------------------------------------------------------
# Conditional forward reversion (the tradable form of the question)
# ---------------------------------------------------------------------------


def conditional_reversion(residual: pd.Series, z: pd.Series, *,
                          entry_z: float, horizons=(5, 15, 30, 60, 120),
                          require_full_horizon: bool = True,
                          min_events: int = 20,
                          legs: tuple[pd.Series, pd.Series] | None = None,
                          beta: pd.Series | float | None = None,
                          event_filter: pd.Series | None = None,
                          session_bounded_events: bool = False,
                          entry_delay: int = 1,
                          feasible_delay: int | None = None) -> pd.DataFrame:
    """Event study: when |z| first crosses `entry_z`, does fading it pay?

    Convention (matches signals.py): the signal is read at bar t; the position
    is entered at the CLOSE OF BAR t+1 and exited at the close of bar t+1+k.
    The outcome is signed so that positive = the residual moved back toward
    its mean:

        pnl_bps = -sign(z_t) * (residual_{t+1+k} - residual_{t+1}) * 1e4

    **Pass `legs` whenever the residual's hedge ratio moves.** With
    `legs=(log_a, log_b)` and `beta` (the ratio KNOWN AT THE SIGNAL BAR, held
    fixed for the life of the trade) the outcome is the position's actual P&L:

        pnl_bps = -sign(z_t) * [ (a_{t+1+k} - a_{t+1})
                                 - beta_t * (b_{t+1+k} - b_{t+1}) ] * 1e4

    The two forms agree exactly when beta is constant, and they must NOT be
    confused when it is not. A residual built around a trailing fit — e.g.
    `pair_minute_report.rolling_ols_residual` — contains the trailing mean
    itself, so its change mixes the price coming back with the REFERENCE POINT
    drifting toward the price. Only the second is tradable; measuring the
    residual would credit a strategy for the window sliding underneath it.

    Events whose entry or exit would fall in a different session are dropped
    (`n_dropped`), never truncated silently — an intraday hypothesis may not
    borrow an overnight gap. Inference is session-clustered: outcomes are
    averaged within a session, and the t-statistic is computed across
    sessions, because minute-level events inside one day are not independent
    draws.

    Why this, and not the variance ratio, is the primary evidence: because the
    fill is at t+1 and the signal is read at t, first-order bid-ask bounce
    cancels in expectation. The entry bounce term enters `res_{t+1}` and the
    exit term enters `res_{t+1+k}`; neither is correlated with `sign(z_t)`,
    which is built from `res_t`. A variance ratio has no such protection.

    This is a MEASUREMENT tool. It applies no costs, no slippage and no
    capacity limit, so its output is an upper bound on any tradable effect.

    Two options exist for the D-020 signal-definition work and both default OFF
    so that notebook-02/03 results reproduce bit for bit:

    `event_filter` — a boolean Series over the residual's index; only crossings
    whose SIGNAL bar is True are kept. Used to build a subset of an existing
    signal's events (e.g. dropping the first 30 minutes of the session) without
    touching the z-score, so the subset is a strict subset of the same events.

    `session_bounded_events` — require the bar before the crossing to be in the
    same session. It matters when z carries a per-session warm-up: those bars
    are dropped by the alignment below, which would otherwise leave a session's
    first scored bar adjacent to the PREVIOUS session's last bar and let a
    crossing be detected across the close. It is left off for the 390-bar
    overnight-spanning score, where such crossings are part of the artifact
    under study (L-013) rather than an alignment defect, and where turning it
    on would silently change the baseline.

    Two options exist for the D-022 delayed-entry work and both default to the
    banked convention so notebook-02/03/06 results reproduce bit for bit:

    `entry_delay` — enter at the close of bar t+d instead of t+1, exit at
    t+d+k. The holding period stays k bars for every delay; only the start
    moves, and beta stays frozen at the SIGNAL bar. If the observed effect is
    a thin leg catching up (L-014), it is spent within the first bars and a
    delayed entry captures nothing; genuine convergence on a tens-of-bars
    half-life survives nearly intact.

    `feasible_delay` — MATCHED event sets across delays: an event enters the
    grid at horizon k only if bar t + feasible_delay + k is still inside the
    signal bar's session (and the sample). Running every delay d <=
    feasible_delay against the same mask makes n_events identical across
    delays at fixed (entry_z, horizon), so a decay profile cannot be
    manufactured by late-session events entering at d = 1 and dropping out at
    d = 15. Feasibility depends only on the signal bar's position in the
    session — known at signal time, no look-ahead.
    """
    if entry_delay < 1:
        raise ValueError(f"entry_delay must be >= 1, got {entry_delay}")
    if feasible_delay is not None and feasible_delay < entry_delay:
        raise ValueError(f"feasible_delay {feasible_delay} < entry_delay "
                         f"{entry_delay}: the matched mask would not cover "
                         f"this delay's own exit")
    cols = {"res": residual, "z": z}
    if event_filter is not None:
        cols["evf"] = event_filter.reindex(residual.index).fillna(False).astype(float)
    if legs is not None:
        cols["la"], cols["lb"] = legs[0], legs[1]
        cols["beta"] = (pd.Series(float(beta), index=residual.index)
                        if beta is None or np.isscalar(beta) else beta)
    df = pd.concat(cols, axis=1).dropna()
    if df.empty:
        return pd.DataFrame(columns=["horizon_bars", "n_events", "n_sessions",
                                     "mean_bps", "mean_session_bps", "sd_bps",
                                     "t_clustered", "hit_rate", "n_dropped"])
    res = df["res"].values.astype(float)
    zv = df["z"].values.astype(float)
    sess = session_ids(df.index)
    la = df["la"].values.astype(float) if legs is not None else None
    lb = df["lb"].values.astype(float) if legs is not None else None
    bt = df["beta"].values.astype(float) if legs is not None else None

    az = np.abs(zv)
    cross = np.concatenate([[False], (az[1:] >= entry_z) & (az[:-1] < entry_z)])
    if session_bounded_events:
        cross &= np.concatenate([[False], sess[1:] == sess[:-1]])
    if event_filter is not None:
        cross &= df["evf"].values.astype(bool)
    ev = np.flatnonzero(cross)
    sign = -np.sign(zv)

    rows = []
    for k in horizons:
        entry, exit_ = ev + entry_delay, ev + entry_delay + k
        # The feasibility bar: the exit of the LARGEST delay in a matched
        # family (or this call's own exit when unmatched). Requiring it to
        # stay inside the signal bar's session covers entry and every exit
        # up to it, so one mask serves the whole delay family identically.
        far = ev + (feasible_delay if feasible_delay is not None
                    else entry_delay) + k
        ok = far < len(res)
        if require_full_horizon:
            ok &= (sess[np.clip(far, 0, len(res) - 1)] == sess[ev])
            ok &= (sess[np.clip(entry, 0, len(res) - 1)] == sess[ev])
        else:
            ok &= exit_ < len(res)
        n_drop = int((~ok).sum())
        e, x_, base = ev[ok], exit_[ok], entry[ok]
        if len(e) < min_events:
            rows.append({"horizon_bars": k, "n_events": len(e), "n_sessions": 0,
                         "mean_bps": np.nan, "mean_session_bps": np.nan,
                         "sd_bps": np.nan, "t_clustered": np.nan,
                         "hit_rate": np.nan, "n_dropped": n_drop})
            continue
        if legs is not None:
            move = (la[x_] - la[base]) - bt[e] * (lb[x_] - lb[base])
        else:
            move = res[x_] - res[base]
        pnl = sign[e] * move * 1e4
        per_session = pd.Series(pnl).groupby(pd.Series(sess[e])).mean()
        ns = len(per_session)
        t = (per_session.mean() / (per_session.std(ddof=1) / np.sqrt(ns))
             if ns > 2 and per_session.std(ddof=1) > 0 else np.nan)
        rows.append({"horizon_bars": k, "n_events": int(len(e)),
                     "n_sessions": int(ns), "mean_bps": float(pnl.mean()),
                     "mean_session_bps": float(per_session.mean()),
                     "sd_bps": float(pnl.std(ddof=1)),
                     "t_clustered": float(t) if t == t else np.nan,
                     "hit_rate": float((pnl > 0).mean()), "n_dropped": n_drop})
    return pd.DataFrame(rows)


def event_clock_profile(z: pd.Series, entry_z: float,
                        bucket_minutes: int = 30,
                        session_bounded: bool = False,
                        open_t: time = RTH_OPEN) -> pd.DataFrame:
    """Where in the session |z| crossings happen.

    The z-score lookback (390 bars = one RTH day, per config) reaches back
    across the overnight break, so the first bars of a session are scored
    against yesterday's mean. If an overnight repricing dominates, crossings
    pile up right after the open and the "intraday reversion" being measured is
    really an open-gap effect. This profile is what makes that visible instead
    of invisible.

    `session_bounded` mirrors `conditional_reversion`'s option of the same name
    and must be set for any z-score carrying a per-session warm-up, so that the
    two diagnostics count the same events.

    `open_t` anchors the buckets. It defaults to `RTH_OPEN` so every banked
    result reproduces, and MUST be passed whenever the panel was framed on a
    different session (D-024): with a session opening before `RTH_OPEN` the
    leading bars otherwise land in negative buckets and the profile silently
    mislabels the open.
    """
    zz = z.dropna()
    if len(zz) < 2:                 # a window can legitimately score nothing
        return pd.DataFrame(columns=["minutes_from_open", "n_events", "share"])
    az = zz.abs()
    cross = np.concatenate([[False], (az.values[1:] >= entry_z)
                            & (az.values[:-1] < entry_z)])
    if session_bounded:
        s = session_ids(zz.index)
        cross &= np.concatenate([[False], s[1:] == s[:-1]])
    idx = zz.index[cross]
    if len(idx) == 0:
        return pd.DataFrame(columns=["minutes_from_open", "n_events", "share"])
    mins = ((idx.hour * 60 + idx.minute) - (open_t.hour * 60 + open_t.minute))
    b = (np.asarray(mins) // bucket_minutes) * bucket_minutes
    counts = pd.Series(b).value_counts().sort_index()
    return pd.DataFrame({"minutes_from_open": counts.index.astype(int),
                         "n_events": counts.values,
                         "share": counts.values / counts.values.sum()})


# ---------------------------------------------------------------------------
# Roll-window diagnostics (notebook-02 preflight, deferred from report 01)
# ---------------------------------------------------------------------------


def roll_window_diagnostics(residual: pd.Series, z: pd.Series,
                            roll_timestamps, *,
                            edges=(-1170, -780, -390, 0, 390, 780, 1170)
                            ) -> pd.DataFrame:
    """Behaviour of the residual and its z-score in bar-offset buckets around
    OUR splice timestamps (D-009 schedule), versus a baseline of every bar
    further than `edges[-1]` bars from any roll.

    Offsets are counted in bars of the supplied (RTH-filtered) series, so 390
    = one RTH day. Reported per bucket: dispersion of the 1-bar residual
    change, the mean and 99th percentile of |z|, and the tail rate P(|z|>2) —
    the quantities that decide the adopted pre-roll exclusion and post-roll
    warm-up. A bucket that matches baseline needs no exclusion; that is a
    legitimate and expected outcome on an own-spliced series, whose whole
    purpose is to have no artifact at the boundary.
    """
    df = pd.concat({"res": residual, "z": z}, axis=1)
    n = len(df)
    d = within_session_returns(df["res"]).reindex(df.index) * 1e4
    pos = df.index.get_indexer(pd.DatetimeIndex(roll_timestamps), method="bfill")
    pos = pos[pos >= 0]

    bucket = np.full(n, "baseline", dtype=object)
    labels = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        lab = f"[{lo},{hi})"
        labels.append(lab)
        for p in pos:
            a, b = max(0, p + lo), min(n, p + hi)
            if a < b:
                bucket[a:b] = lab

    out = []
    for lab in labels + ["baseline"]:
        m = bucket == lab
        sub, dd = df[m], d[m]
        az = sub["z"].abs()
        out.append({
            "bucket": lab, "n_bars": int(m.sum()),
            "sd_dres_bps": float(dd.std(ddof=1)) if dd.notna().sum() > 2 else np.nan,
            "mean_abs_z": float(az.mean()) if az.notna().any() else np.nan,
            "p99_abs_z": float(az.quantile(0.99)) if az.notna().any() else np.nan,
            "frac_abs_z_gt2": float((az > 2).mean()) if az.notna().any() else np.nan,
        })
    return pd.DataFrame(out)


def held_position_roll_shock(factor_a: float, factor_b: float,
                             beta: float) -> float:
    """Level shift, in bps of residual, that a position HELD across a splice
    would absorb: log(f_a) - beta*log(f_b).

    On the own-spliced series this shift is absorbed into history, so the
    constructed residual is continuous by construction and a z-score sees
    nothing. A real position does not get that courtesy: it must close the
    expiring pair and reopen the new one at genuinely different prices. This
    number — not any artifact in the constructed series — is what a pre-roll
    exclusion window exists to avoid.
    """
    return float((np.log(factor_a) - beta * np.log(factor_b)) * 1e4)
