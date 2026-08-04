"""Leg-level lead-lag cross-correlation (D-022's discriminator module).

Split out of `intraday_reversion.py` for an operational reason discovered
during the notebook-14 upload: QuantConnect's `files/update` rejects any file
above 32,000 characters, and the delayed-entry additions pushed that module
past the cap. The statistics here are exactly the ones D-022 froze; only the
file boundary moved. Uploaded to QC as `crosscorr.py`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .intraday_reversion import _session_slices, session_ids


def leg_crosscorr_profile(log_a: pd.Series, log_b: pd.Series,
                          lags=(1, 2, 3, 4, 5), *, n_boot: int = 1000,
                          seed: int = 20260801) -> pd.DataFrame:
    """Lead-lag structure of the LEG returns (D-022's discriminator).

    A spread against a lagging leg mechanically "reverts" as the laggard
    catches up (L-014). That mechanism is directional and must be visible in
    the legs themselves: corr(r_a(t−k), r_b(t)) — "a leads b" — exceeding its
    mirror. Symmetric reversion of the spread produces no such asymmetry,
    which is what makes this block, and not the delayed-entry decay alone,
    able to separate lead-lag from genuinely fast convergence.

    Rows: ``c0`` (contemporaneous), ``ab_k`` = corr(r_a(t−k), r_b(t)),
    ``ba_k`` = corr(r_b(t−k), r_a(t)), ``asym_k`` = ab_k − ba_k, for each k.
    Columns: point estimate, bootstrap 95% CI, n_pairs.

    Returns are within-session only (per-session diff of the log price; a
    pair (t−k, t) never straddles a close). Inference is a session bootstrap
    from per-session sufficient statistics, and — deliberately, per D-022 —
    **one session draw per replicate is SHARED across every statistic**, so
    each asym_k replicate is the paired difference on the same resampled
    sessions. Independent draws would lose the covariance between ab_k and
    ba_k and widen the asym CI. The replicate sums are formed as a
    counts-matrix product rather than a gather, so peak memory stays at the
    counts matrix (~chunk x n_sessions), not chunk x n_sessions x 66.
    """
    df = pd.concat({"a": log_a, "b": log_b}, axis=1).dropna()
    va, vb = df["a"].values.astype(float), df["b"].values.astype(float)
    sess = session_ids(df.index)
    lags = tuple(int(k) for k in lags)
    if any(k < 1 for k in lags):
        raise ValueError(f"lags must be >= 1, got {lags}")

    # 11 statistic sets: c0, then ab_k and ba_k per lag. 6 sufficient
    # statistics each: n, Sx, Sy, Sxx, Syy, Sxy.
    labels = ["c0"] + [f"ab_{k}" for k in lags] + [f"ba_{k}" for k in lags]
    pairs_spec = [(0, "ab")] + [(k, "ab") for k in lags] + [(k, "ba") for k in lags]
    slices = _session_slices(sess)
    stats = np.zeros((len(slices), len(labels), 6))
    for si, (lo, hi) in enumerate(slices):
        ra, rb = np.diff(va[lo:hi]), np.diff(vb[lo:hi])
        for li, (k, direction) in enumerate(pairs_spec):
            x, y = (ra, rb) if direction == "ab" else (rb, ra)
            if k:
                x, y = x[:-k], y[k:]
            if len(x) == 0:
                continue
            stats[si, li] = (len(x), x.sum(), y.sum(),
                             (x * x).sum(), (y * y).sum(), (x * y).sum())

    def corr(tot: np.ndarray) -> np.ndarray:
        n, sx, sy, sxx, syy, sxy = (tot[..., i] for i in range(6))
        with np.errstate(divide="ignore", invalid="ignore"):
            cov = sxy - sx * sy / n
            vx, vy = sxx - sx * sx / n, syy - sy * sy / n
            c = cov / np.sqrt(vx * vy)
        return np.where((n > 2) & (vx > 0) & (vy > 0), c, np.nan)

    point = corr(stats.sum(axis=0))
    n_pairs = stats[:, :, 0].sum(axis=0).astype(int)

    n_sess = len(slices)
    reps = np.empty((n_boot, len(labels)))
    if n_sess >= 10:
        rng = np.random.default_rng(seed)
        flat = stats.reshape(n_sess, -1)
        chunk = max(1, min(n_boot, 20_000_000 // max(n_sess, 1)))
        for lo in range(0, n_boot, chunk):
            hi = min(lo + chunk, n_boot)
            idx = rng.integers(0, n_sess, size=(hi - lo, n_sess))
            counts = np.zeros((hi - lo, n_sess))
            for r in range(hi - lo):
                counts[r] = np.bincount(idx[r], minlength=n_sess)
            reps[lo:hi] = corr((counts @ flat).reshape(hi - lo, len(labels), 6))
    else:
        reps[:] = np.nan

    rows = []
    ab_cols = {k: labels.index(f"ab_{k}") for k in lags}
    ba_cols = {k: labels.index(f"ba_{k}") for k in lags}
    for li, lab in enumerate(labels):
        r = reps[:, li]
        r = r[np.isfinite(r)]
        lo_hi = (np.percentile(r, [2.5, 97.5]) if len(r) >= n_boot // 2
                 else (np.nan, np.nan))
        rows.append({"stat": lab, "point": float(point[li]),
                     "ci_lo": float(lo_hi[0]), "ci_hi": float(lo_hi[1]),
                     "n_pairs": int(n_pairs[li])})
    for k in lags:                       # paired difference, SAME draws
        d = reps[:, ab_cols[k]] - reps[:, ba_cols[k]]
        d = d[np.isfinite(d)]
        lo_hi = (np.percentile(d, [2.5, 97.5]) if len(d) >= n_boot // 2
                 else (np.nan, np.nan))
        rows.append({"stat": f"asym_{k}",
                     "point": float(point[ab_cols[k]] - point[ba_cols[k]]),
                     "ci_lo": float(lo_hi[0]), "ci_hi": float(lo_hi[1]),
                     "n_pairs": int(min(n_pairs[ab_cols[k]],
                                        n_pairs[ba_cols[k]]))})
    return pd.DataFrame(rows)
