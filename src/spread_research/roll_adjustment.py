"""Roll-adjustment auditing: quantify gaps between raw mapped prices and
adjusted continuous prices around roll events (mandate §8.4).

The point is not to build our own continuous series (QC provides those) but to
VERIFY that (a) adjusted series contain no artificial return jumps at rolls and
(b) raw series gaps are excluded from signal statistics."""

from __future__ import annotations

import numpy as np
import pandas as pd


def roll_gap_report(raw_close: pd.Series, adjusted_close: pd.Series,
                    roll_events: pd.DataFrame, window_bars: int = 30) -> pd.DataFrame:
    """For each roll event: raw price gap, adjusted-series return at the event,
    and whether the adjusted return looks like an artifact (exceeds 10x the
    local MAD of adjusted returns)."""
    adj_ret = np.log(adjusted_close).diff()
    rows = []
    for _, ev in roll_events.iterrows():
        ts = ev["timestamp"]
        if ts not in raw_close.index:
            continue
        i = raw_close.index.get_loc(ts)
        if isinstance(i, slice) or i == 0:
            continue
        raw_gap = float(raw_close.iloc[i] - raw_close.iloc[i - 1])
        local = adj_ret.iloc[max(0, i - window_bars):i + window_bars].dropna()
        mad = float((local - local.median()).abs().median()) or np.nan
        ev_ret = float(adj_ret.iloc[i]) if not np.isnan(adj_ret.iloc[i]) else np.nan
        rows.append({
            "timestamp": ts,
            "from_contract": ev.get("from_contract"),
            "to_contract": ev.get("to_contract"),
            "raw_price_gap": raw_gap,
            "adjusted_log_return_at_roll": ev_ret,
            "local_mad": mad,
            "artifact_flag": bool(mad == mad and ev_ret == ev_ret
                                  and abs(ev_ret) > 10 * mad * 1.4826),
        })
    return pd.DataFrame(rows)
