"""Research-phase risk accounting: exposure, margin proxy, and limit checks
against config/risk_limits.yaml."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml


def load_risk_limits(path: str | Path = "config/risk_limits.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def spread_exposures(notional_a: float, notional_b: float) -> dict:
    return {
        "gross_notional": notional_a + notional_b,
        "net_notional": notional_a - notional_b,
    }


def check_trade_limits(size, equity: float, limits: dict) -> list[str]:
    """Return list of violated per-trade limits (empty = pass).
    `size` is a position_sizing.SpreadSize."""
    v = []
    per = limits["per_trade"]
    if size.gross_notional > equity * per["max_gross_notional_pct"] / 100:
        v.append("max_gross_notional_pct")
    if max(size.contracts_a, size.contracts_b) > per["max_contracts_per_leg"]:
        v.append("max_contracts_per_leg")
    return v


def daily_loss_stop_hit(equity_curve: pd.Series, ref_equity: float,
                        daily_stop_pct: float) -> pd.Series:
    """Per-day flag: True once the day's PnL breaches -daily_stop_pct% of
    reference equity (halt new entries for the rest of that day)."""
    day = equity_curve.index.date
    day_pnl = equity_curve.groupby(day).transform(lambda e: e - e.iloc[0])
    return (day_pnl <= -ref_equity * daily_stop_pct / 100).rename("daily_stop")
