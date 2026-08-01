"""Walk-forward validation machinery (mandate notebook 09).

Splits an index into (train, test) windows with an embargo gap; a runner applies
user-supplied fit/evaluate callables. The splitter is pure — leakage protection
is structural (train end + embargo < test start, asserted)."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardWindow:
    fold: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def make_windows(index: pd.DatetimeIndex,
                 train_months: int, test_months: int, step_months: int,
                 embargo_days: int = 0, anchored: bool = False) -> list[WalkForwardWindow]:
    if len(index) == 0:
        return []
    start, end = index[0], index[-1]
    windows: list[WalkForwardWindow] = []
    fold = 0
    t0 = start
    while True:
        train_start = start if anchored else t0
        train_end = t0 + pd.DateOffset(months=train_months)
        test_start = train_end + pd.Timedelta(days=embargo_days)
        test_end = test_start + pd.DateOffset(months=test_months)
        if test_end > end:
            break
        assert train_end + pd.Timedelta(days=embargo_days) <= test_start
        windows.append(WalkForwardWindow(fold, train_start, train_end,
                                         test_start, test_end))
        fold += 1
        t0 = t0 + pd.DateOffset(months=step_months)
    return windows


def run_walk_forward(index: pd.DatetimeIndex, windows: list[WalkForwardWindow],
                     fit_fn, eval_fn) -> pd.DataFrame:
    """fit_fn(train_slice) -> params; eval_fn(params, test_slice) -> dict of metrics.
    Slices are boolean masks over `index`; the caller applies them to its data."""
    rows = []
    for w in windows:
        train_mask = (index >= w.train_start) & (index < w.train_end)
        test_mask = (index >= w.test_start) & (index < w.test_end)
        params = fit_fn(train_mask)
        metrics = eval_fn(params, test_mask)
        rows.append({"fold": w.fold, "train_start": w.train_start,
                     "train_end": w.train_end, "test_start": w.test_start,
                     "test_end": w.test_end, "params": params, **metrics})
    return pd.DataFrame(rows)


def acceptance_check(fold_results: pd.DataFrame, pnl_col: str,
                     min_fraction_profitable: float,
                     max_single_window_share: float) -> dict:
    """Consistency-based acceptance (config/walk_forward_config.yaml)."""
    pnl = fold_results[pnl_col]
    total = pnl.sum()
    frac_pos = float((pnl > 0).mean()) if len(pnl) else 0.0
    max_share = float(pnl.max() / total) if total > 0 and len(pnl) else float("nan")
    return {
        "n_folds": int(len(pnl)),
        "total_pnl": float(total),
        "fraction_profitable_folds": frac_pos,
        "max_single_window_share": max_share,
        "passes": bool(len(pnl) > 0 and total > 0
                       and frac_pos >= min_fraction_profitable
                       and (max_share == max_share and max_share <= max_single_window_share)),
    }
