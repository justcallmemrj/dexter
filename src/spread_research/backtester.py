"""Minimal honest spread backtester for research (mandate notebook 08).

Design rules:
- DECIDE at bar t (using signals whose inputs end at t), EXECUTE at bar t+1 close.
  One full bar of delay is the baseline; extra legging delay via execution_simulator.
- PnL is computed on EXECUTABLE (mapped raw) prices passed in by the caller;
  the z-score/residual may come from a different (continuous adjusted) series.
  Passing adjusted prices as executable prices is the classic fake-PnL bug —
  callers must not do it, and notebook 01 tests the difference.
- Costs are charged on every entry and exit fill via CostModel.
- No position pyramiding in V1: one spread unit at a time.

This is NOT a fill simulator: no queues, no partial fills, no intrabar paths.
Its purpose is relative evaluation of signals under conservative assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .costs import CostModel


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity: pd.Series
    bar_pnl: pd.Series
    params: dict = field(default_factory=dict)


def run_spread_backtest(
    exec_price_a: pd.Series,
    exec_price_b: pd.Series,
    positions: pd.Series,           # target spread position decided at t (-1/0/+1)
    contracts_a: int,
    contracts_b: int,
    mult_a: float,
    mult_b: float,
    cost_model: CostModel | None,
    symbol_a: str,
    symbol_b: str,
    scenario: str = "base",
    execution_lag_bars: int = 1,
) -> BacktestResult:
    """Vectorized spread backtest.

    positions: +1 long spread (long A, short B), -1 short spread, 0 flat — the
    TARGET decided at each bar. Effective position = positions.shift(execution_lag_bars).
    """
    df = pd.concat({"pa": exec_price_a, "pb": exec_price_b,
                    "target": positions}, axis=1).dropna()
    eff = df["target"].shift(execution_lag_bars).fillna(0.0)

    # Per-bar PnL of holding the spread over bar t (close_{t-1} -> close_t):
    dpa = df["pa"].diff()
    dpb = df["pb"].diff()
    leg_a_pnl = dpa * mult_a * contracts_a
    leg_b_pnl = dpb * mult_b * contracts_b
    bar_pnl = eff.shift(1).fillna(0.0) * (leg_a_pnl - leg_b_pnl)

    # Cost events: any change of effective position.
    changes = eff.diff().fillna(eff)
    cost_per_switch = 0.0
    if cost_model is not None:
        # entering or exiting the spread = one fill per leg
        cost_per_switch = (cost_model.fill_cost(symbol_a, contracts_a, scenario)
                           + cost_model.fill_cost(symbol_b, contracts_b, scenario))
    costs = changes.abs() * cost_per_switch
    bar_pnl_net = bar_pnl - costs

    equity = bar_pnl_net.cumsum()

    trades = _extract_trades(df.index, eff.values, bar_pnl_net.values)
    return BacktestResult(
        trades=trades, equity=equity, bar_pnl=bar_pnl_net,
        params={"contracts_a": contracts_a, "contracts_b": contracts_b,
                "scenario": scenario, "execution_lag_bars": execution_lag_bars},
    )


def _extract_trades(index, eff: np.ndarray, pnl: np.ndarray) -> pd.DataFrame:
    """Group consecutive nonzero effective-position runs into trades."""
    trades = []
    open_i = None
    for t in range(len(eff)):
        if eff[t] != 0 and (t == 0 or eff[t - 1] == 0):
            open_i = t
        elif eff[t] == 0 and t > 0 and eff[t - 1] != 0 and open_i is not None:
            seg = pnl[open_i:t + 1]  # include exit bar (carries exit costs)
            trades.append({
                "entry_time": index[open_i], "exit_time": index[t],
                "direction": eff[open_i], "bars_held": t - open_i,
                "pnl": float(np.nansum(seg)),
                "max_adverse_excursion": float(np.nanmin(np.nancumsum(seg))),
            })
            open_i = None
    return pd.DataFrame(trades)
