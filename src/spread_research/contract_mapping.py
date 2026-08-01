"""Contract-mapping utilities: detect mapping (roll) events from a
mapped_contract column and reason about warm-up windows around them."""

from __future__ import annotations

import pandas as pd


def detect_mapping_changes(mapped_contract: pd.Series) -> pd.DataFrame:
    """Rows where the underlying mapped contract changes (roll events)."""
    s = mapped_contract.dropna()
    changed = s != s.shift(1)
    changed.iloc[0] = False
    events = s[changed]
    return pd.DataFrame({
        "timestamp": events.index,
        "from_contract": s.shift(1)[changed].values,
        "to_contract": events.values,
    })


def bars_since_mapping_change(mapped_contract: pd.Series) -> pd.Series:
    """Bars elapsed since the last mapping change (for post-roll warm-up filters)."""
    s = mapped_contract.dropna()
    change = (s != s.shift(1)).cumsum()
    return s.groupby(change).cumcount().rename("bars_since_roll")


def roll_exclusion_mask(index: pd.DatetimeIndex, roll_events: pd.DataFrame,
                        days_before: int, warmup_bars: int,
                        mapped_contract: pd.Series | None = None) -> pd.Series:
    """True where NEW ENTRIES are disallowed: within `days_before` calendar days
    before each roll and `warmup_bars` bars after (statistics reset)."""
    mask = pd.Series(False, index=index)
    for ts in roll_events["timestamp"]:
        pre = (index >= ts - pd.Timedelta(days=days_before)) & (index < ts)
        mask |= pd.Series(pre, index=index)
    if mapped_contract is not None and warmup_bars > 0:
        since = bars_since_mapping_change(mapped_contract).reindex(index)
        mask |= since < warmup_bars
    return mask.rename("roll_excluded")
