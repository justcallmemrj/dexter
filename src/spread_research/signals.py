"""Signal construction with structural look-ahead protection.

Convention used throughout the project:
- The z-score at bar t compares the residual at t against mean/std estimated on
  the window ENDING AT t-1 (shifted rolling stats). The current bar never
  contributes to its own normalization.
- The state machine emits the TARGET position decided at bar t; the backtester
  executes it at bar t+1. Signal code itself never peeks forward.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rolling_zscore(residual: pd.Series, lookback: int,
                   min_periods: int | None = None) -> pd.Series:
    """Z-score of residual vs stats of the PRIOR `lookback` bars (excludes current)."""
    mp = min_periods or lookback
    mean = residual.rolling(lookback, min_periods=mp).mean().shift(1)
    std = residual.rolling(lookback, min_periods=mp).std().shift(1)
    z = (residual - mean) / std.replace(0.0, np.nan)
    return z.rename("zscore")


def zscore_positions(z: pd.Series, entry_z: float, exit_z: float, stop_z: float,
                     max_holding_bars: int) -> pd.DataFrame:
    """Stateful entry/exit logic on a z-score series.

    Position semantics (spread units): -1 = short spread (residual rich: short A,
    long beta*B), +1 = long spread, 0 = flat.

    Exit reasons: 'converged' (|z| <= exit_z), 'stop' (|z| >= stop_z — structural-
    failure guard), 'time' (held max_holding_bars). Re-entry after a stop is
    blocked until |z| first returns inside exit_z (prevents immediately re-shorting
    a structurally broken spread).
    """
    zv = z.values
    n = len(zv)
    pos = np.zeros(n)
    reason = np.array([""] * n, dtype=object)
    holding = 0
    blocked = False
    for t in range(n):
        zt = zv[t]
        prev = pos[t - 1] if t > 0 else 0.0
        if np.isnan(zt):
            pos[t] = 0.0 if prev == 0 else prev  # missing z: hold, never enter
            holding = holding + 1 if pos[t] != 0 else 0
            continue
        if blocked and abs(zt) <= exit_z:
            blocked = False
        if prev == 0:
            if not blocked and abs(zt) >= entry_z and abs(zt) < stop_z:
                pos[t] = -np.sign(zt)   # fade the dislocation
                holding = 1
            else:
                pos[t] = 0.0
        else:
            holding += 1
            if abs(zt) <= exit_z:
                pos[t], reason[t] = 0.0, "converged"
            elif abs(zt) >= stop_z:
                pos[t], reason[t] = 0.0, "stop"
                blocked = True
            elif holding >= max_holding_bars:
                pos[t], reason[t] = 0.0, "time"
            else:
                pos[t] = prev
            if pos[t] == 0:
                holding = 0
    return pd.DataFrame({"position": pos, "exit_reason": reason}, index=z.index)
