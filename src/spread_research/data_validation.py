"""Automated data-quality checks (mandate §8.5).

Philosophy: data that fails validation is FLAGGED, never silently filled.
Every check returns rows in a tidy issues DataFrame; callers decide exclusion.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ISSUE_COLUMNS = ["timestamp", "symbol", "check", "severity", "detail"]


def _issues(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=ISSUE_COLUMNS)


def check_monotonic_unique_index(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    rows = []
    dup = df.index[df.index.duplicated()]
    for ts in dup:
        rows.append({"timestamp": ts, "symbol": symbol, "check": "duplicate_timestamp",
                     "severity": "error", "detail": "duplicate bar"})
    if not df.index.is_monotonic_increasing:
        rows.append({"timestamp": df.index[0], "symbol": symbol,
                     "check": "non_monotonic_index", "severity": "error",
                     "detail": "index not sorted ascending"})
    return _issues(rows)


def check_positive_prices(df: pd.DataFrame, symbol: str,
                          price_cols: tuple[str, ...] = ("open", "high", "low", "close")) -> pd.DataFrame:
    rows = []
    cols = [c for c in price_cols if c in df.columns]
    bad = df[(df[cols] <= 0).any(axis=1)]
    for ts in bad.index:
        rows.append({"timestamp": ts, "symbol": symbol, "check": "nonpositive_price",
                     "severity": "error", "detail": str(bad.loc[ts, cols].to_dict())})
    return _issues(rows)


def check_missing_bars(df: pd.DataFrame, symbol: str, freq: str = "1min",
                       session_gaps_ok_minutes: int = 65) -> pd.DataFrame:
    """Flag gaps larger than expected bar spacing but smaller than a session break.
    Larger gaps than `session_gaps_ok_minutes` are reported separately so genuine
    session halts are distinguishable from data outages by the reviewer."""
    rows = []
    if len(df) < 2:
        return _issues(rows)
    deltas = df.index.to_series().diff().dropna()
    expected = pd.Timedelta(freq)
    ok_break = pd.Timedelta(minutes=session_gaps_ok_minutes)
    for ts, d in deltas[deltas > expected].items():
        sev = "warning" if d <= ok_break else "info_session_or_outage"
        rows.append({"timestamp": ts, "symbol": symbol, "check": "gap",
                     "severity": sev, "detail": f"gap of {d} (expected {expected})"})
    return _issues(rows)


def check_abnormal_jumps(df: pd.DataFrame, symbol: str, price_col: str = "close",
                         mad_mult: float = 15.0) -> pd.DataFrame:
    """Flag bar-to-bar log returns beyond mad_mult * median-absolute-deviation.
    Deliberately loose: better to review a few real moves than miss a bad print
    or an unadjusted roll gap."""
    rows = []
    r = np.log(df[price_col]).diff().dropna()
    if len(r) < 50:
        return _issues(rows)
    mad = (r - r.median()).abs().median()
    if mad == 0:
        return _issues(rows)
    outliers = r[(r - r.median()).abs() > mad_mult * mad * 1.4826]
    for ts, val in outliers.items():
        rows.append({"timestamp": ts, "symbol": symbol, "check": "abnormal_jump",
                     "severity": "warning",
                     "detail": f"log-return {val:.5f} beyond {mad_mult}x MAD"})
    return _issues(rows)


def check_stale_prices(df: pd.DataFrame, symbol: str, price_col: str = "close",
                       max_repeats: int = 60) -> pd.DataFrame:
    """Flag runs of identical closes longer than max_repeats bars (stale feed)."""
    rows = []
    s = df[price_col]
    run_id = (s != s.shift()).cumsum()
    run_lengths = s.groupby(run_id).transform("size")
    stale_starts = df.index[(run_lengths > max_repeats) & (run_id != run_id.shift())]
    for ts in stale_starts:
        rows.append({"timestamp": ts, "symbol": symbol, "check": "stale_price",
                     "severity": "warning",
                     "detail": f"identical close for >{max_repeats} bars"})
    return _issues(rows)


def check_pair_alignment(a: pd.DataFrame, b: pd.DataFrame, sym_a: str, sym_b: str) -> pd.DataFrame:
    """Flag timestamps present in one leg but not the other (misaligned pair)."""
    rows = []
    only_a = a.index.difference(b.index)
    only_b = b.index.difference(a.index)
    for ts in only_a[:1000]:
        rows.append({"timestamp": ts, "symbol": sym_a, "check": "pair_misalignment",
                     "severity": "warning", "detail": f"bar missing in {sym_b}"})
    for ts in only_b[:1000]:
        rows.append({"timestamp": ts, "symbol": sym_b, "check": "pair_misalignment",
                     "severity": "warning", "detail": f"bar missing in {sym_a}"})
    return _issues(rows)


def run_all_checks(df: pd.DataFrame, symbol: str, freq: str = "1min") -> pd.DataFrame:
    """Run the single-series battery; returns a tidy issues DataFrame."""
    parts = [
        check_monotonic_unique_index(df, symbol),
        check_positive_prices(df, symbol),
        check_missing_bars(df, symbol, freq=freq),
        check_abnormal_jumps(df, symbol),
        check_stale_prices(df, symbol),
    ]
    return pd.concat(parts, ignore_index=True)
