"""Standard research figures. All savers write into reports/figures/ so notebooks
stay thin and figures are reproducible artifacts."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless research containers
import matplotlib.pyplot as plt
import pandas as pd

FIGDIR = Path("reports/figures")


def _save(fig, name: str) -> Path:
    FIGDIR.mkdir(parents=True, exist_ok=True)
    path = FIGDIR / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_pair_overview(price_a: pd.Series, price_b: pd.Series, residual: pd.Series,
                       z: pd.Series, name: str) -> Path:
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    axes[0].plot(price_a.index, price_a / price_a.iloc[0], label="leg A (rebased)")
    axes[0].plot(price_b.index, price_b / price_b.iloc[0], label="leg B (rebased)")
    axes[0].legend(); axes[0].set_title(f"{name}: rebased prices")
    axes[1].plot(residual.index, residual.values)
    axes[1].set_title("hedged residual")
    axes[2].plot(z.index, z.values)
    for lvl in (-2, 2):
        axes[2].axhline(lvl, ls="--", lw=0.8)
    axes[2].set_title("z-score (shifted-window)")
    return _save(fig, f"{name}_overview")


def plot_equity(equity: pd.Series, name: str) -> Path:
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(equity.index, equity.values)
    ax.set_title(f"{name}: cumulative PnL (USD)"); ax.set_ylabel("USD")
    return _save(fig, f"{name}_equity")


def plot_roll_events(raw: pd.Series, adjusted: pd.Series,
                     roll_ts: list[pd.Timestamp], name: str,
                     window_bars: int = 60) -> Path:
    n = min(len(roll_ts), 6)
    fig, axes = plt.subplots(n, 1, figsize=(12, 2.5 * n))
    if n == 1:
        axes = [axes]
    for ax, ts in zip(axes, roll_ts[:n]):
        if ts not in raw.index:
            continue
        i = raw.index.get_loc(ts)
        sl = slice(max(0, i - window_bars), i + window_bars)
        ax.plot(raw.index[sl], raw.iloc[sl], label="raw mapped")
        ax.plot(adjusted.index[sl], adjusted.iloc[sl], label="adjusted continuous")
        ax.axvline(ts, color="k", ls=":", lw=1)
        ax.legend(fontsize=8); ax.set_title(str(ts), fontsize=9)
    return _save(fig, f"{name}_rolls")
