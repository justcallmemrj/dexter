"""Regime tagging for conditional performance analysis (mandate notebook 11).

V1 keeps regimes simple and observable: realized-volatility terciles and
calendar/event windows supplied from config. No hidden-state models in V1
(see CLAUDE.md gate 6)."""

from __future__ import annotations

import pandas as pd


def vol_regimes(returns: pd.Series, window: int, n_buckets: int = 3,
                labels: tuple[str, ...] = ("low_vol", "mid_vol", "high_vol")) -> pd.Series:
    """Tercile-bucketed rolling realized vol. Bucket edges are computed on an
    EXPANDING basis (only past data) to avoid full-sample look-ahead in labels."""
    vol = returns.rolling(window).std()
    ranks = vol.expanding(min_periods=window * 2).rank(pct=True)
    edges = [i / n_buckets for i in range(1, n_buckets)]
    def bucket(p):
        if p != p:
            return None
        for i, e in enumerate(edges):
            if p <= e:
                return labels[i]
        return labels[-1]
    return ranks.map(bucket).rename("vol_regime")


def event_windows(index: pd.DatetimeIndex, event_times: list[pd.Timestamp],
                  minutes_before: int, minutes_after: int) -> pd.Series:
    """Boolean mask marking bars inside [event - before, event + after]."""
    mask = pd.Series(False, index=index)
    for ts in event_times:
        lo = ts - pd.Timedelta(minutes=minutes_before)
        hi = ts + pd.Timedelta(minutes=minutes_after)
        mask |= pd.Series((index >= lo) & (index <= hi), index=index)
    return mask.rename("event_window")


def performance_by_regime(bar_pnl: pd.Series, regime: pd.Series) -> pd.DataFrame:
    df = pd.concat({"pnl": bar_pnl, "regime": regime}, axis=1).dropna()
    g = df.groupby("regime")["pnl"]
    return pd.DataFrame({"total_pnl": g.sum(), "mean_pnl": g.mean(),
                         "n_bars": g.size(), "share_positive": g.apply(lambda s: (s > 0).mean())})
