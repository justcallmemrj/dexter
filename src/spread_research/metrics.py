"""Performance and risk metrics for research evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd


def sharpe(bar_pnl: pd.Series, bars_per_year: float) -> float:
    """Annualized Sharpe of a per-bar USD PnL series (rf ~ 0 at bar horizon).
    NB: on USD PnL this is a per-unit-strategy Sharpe, comparable across configs
    of the same book size, not across books."""
    s = bar_pnl.dropna()
    if len(s) < 2 or s.std() == 0:
        return np.nan
    return float(s.mean() / s.std() * np.sqrt(bars_per_year))


def sortino(bar_pnl: pd.Series, bars_per_year: float) -> float:
    s = bar_pnl.dropna()
    downside = s[s < 0]
    if len(s) < 2 or len(downside) == 0 or downside.std() == 0:
        return np.nan
    return float(s.mean() / downside.std() * np.sqrt(bars_per_year))


def max_drawdown(equity: pd.Series) -> float:
    """Max drawdown in USD (equity is cumulative PnL)."""
    e = equity.dropna()
    if len(e) == 0:
        return 0.0
    return float((e - e.cummax()).min())


def trade_stats(trades: pd.DataFrame) -> dict:
    if trades is None or len(trades) == 0:
        return {"n_trades": 0}
    pnl = trades["pnl"]
    wins = pnl[pnl > 0]
    losses = pnl[pnl <= 0]
    return {
        "n_trades": int(len(trades)),
        "hit_rate": float(len(wins) / len(trades)),
        "avg_pnl": float(pnl.mean()),
        "median_pnl": float(pnl.median()),
        "avg_win": float(wins.mean()) if len(wins) else np.nan,
        "avg_loss": float(losses.mean()) if len(losses) else np.nan,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.inf,
        "avg_bars_held": float(trades["bars_held"].mean()),
        "worst_trade": float(pnl.min()),
        "avg_mae": float(trades["max_adverse_excursion"].mean()),
        "worst_mae": float(trades["max_adverse_excursion"].min()),
    }


def concentration(pnl_by_bucket: pd.Series) -> dict:
    """How dependent is the result on its best bucket (year, pair, window)?
    Guards against the 'one great year' failure mode."""
    total = pnl_by_bucket.sum()
    if total <= 0 or len(pnl_by_bucket) == 0:
        return {"max_bucket_share": np.nan, "positive_bucket_fraction": np.nan}
    return {
        "max_bucket_share": float(pnl_by_bucket.max() / total),
        "positive_bucket_fraction": float((pnl_by_bucket > 0).mean()),
    }


def summarize(result, bars_per_year: float) -> dict:
    """One-line summary dict for the experiment log."""
    out = {
        "sharpe": sharpe(result.bar_pnl, bars_per_year),
        "sortino": sortino(result.bar_pnl, bars_per_year),
        "total_pnl": float(result.bar_pnl.sum()),
        "max_drawdown": max_drawdown(result.equity),
    }
    out.update(trade_stats(result.trades))
    return out
