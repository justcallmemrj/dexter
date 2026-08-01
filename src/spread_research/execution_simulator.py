"""Execution-risk experiments beyond the baseline backtester (mandate §4.3):
legging delay (one leg fills late) and its PnL impact."""

from __future__ import annotations

import pandas as pd

from .backtester import BacktestResult, run_spread_backtest
from .costs import CostModel


def legging_delay_study(
    exec_price_a: pd.Series, exec_price_b: pd.Series, positions: pd.Series,
    contracts_a: int, contracts_b: int, mult_a: float, mult_b: float,
    cost_model: CostModel | None, symbol_a: str, symbol_b: str,
    scenario: str = "base", delays: tuple[int, ...] = (0, 1, 2),
) -> pd.DataFrame:
    """Approximate the cost of the hedge leg (B) filling `d` bars after leg A by
    delaying leg B's position series. During the mismatch window the book carries
    outright exposure to leg A — exactly the risk being measured.

    Implementation: run the baseline (both legs synchronized) and a variant where
    leg B's effective position lags by d bars; report the PnL difference as the
    legging cost estimate.
    """
    rows = []
    base = run_spread_backtest(exec_price_a, exec_price_b, positions,
                               contracts_a, contracts_b, mult_a, mult_b,
                               cost_model, symbol_a, symbol_b, scenario)
    for d in delays:
        if d == 0:
            rows.append({"delay_bars": 0, "total_pnl": float(base.bar_pnl.sum()),
                         "legging_cost": 0.0})
            continue
        # Leg A executes at t+1 (baseline); leg B at t+1+d.
        df = pd.concat({"pa": exec_price_a, "pb": exec_price_b,
                        "target": positions}, axis=1).dropna()
        eff_a = df["target"].shift(1).fillna(0.0)
        eff_b = df["target"].shift(1 + d).fillna(0.0)
        pnl = (eff_a.shift(1).fillna(0.0) * df["pa"].diff() * mult_a * contracts_a
               - eff_b.shift(1).fillna(0.0) * df["pb"].diff() * mult_b * contracts_b)
        cost_per_switch = 0.0
        if cost_model is not None:
            cost_per_switch = (cost_model.fill_cost(symbol_a, contracts_a, scenario)
                               + cost_model.fill_cost(symbol_b, contracts_b, scenario))
        costs = eff_a.diff().fillna(eff_a).abs() * cost_per_switch
        total = float((pnl - costs).sum())
        rows.append({"delay_bars": d, "total_pnl": total,
                     "legging_cost": total - float(base.bar_pnl.sum())})
    return pd.DataFrame(rows)
