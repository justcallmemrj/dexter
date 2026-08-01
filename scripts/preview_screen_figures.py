"""Figures for the daily preview screen report (D-007).

Run from repo root: .venv/Scripts/python.exe scripts/preview_screen_figures.py
Writes reports/figures/preview_*.png
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from spread_research.data_loader import load_local
from spread_research.hedge_ratios import rolling_ols_beta
from spread_research.pair_builder import align_pair

FIG_DIR = Path("reports/figures")
FIG_DIR.mkdir(parents=True, exist_ok=True)
RESEARCH_START = "2019-06-01"


def _static_resid(a, b, use_log=True):
    df = align_pair(a, b)
    x = np.log(df["b"]) if use_log else df["b"].astype(float)
    y = np.log(df["a"]) if use_log else df["a"].astype(float)
    X = np.vstack([np.ones(len(x)), x.values]).T
    coef, *_ = np.linalg.lstsq(X, y.values, rcond=None)
    return y - (coef[0] + coef[1] * x.values)


def fig_residual(sym_a, sym_b, title, fname, start=RESEARCH_START, use_log=True):
    a = load_local(sym_a, "daily")["close"].loc[start:]
    b = load_local(sym_b, "daily")["close"].loc[start:]
    res = _static_resid(a, b, use_log)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(res.index, res.values, lw=0.8)
    ax.axhline(res.mean(), color="k", lw=0.8, ls="--")
    ax.set_title(title)
    ax.set_ylabel("static-OLS residual (log space)" if use_log else "residual")
    fig.tight_layout()
    fig.savefig(FIG_DIR / fname, dpi=130)
    plt.close(fig)
    print(f"wrote {FIG_DIR / fname}")


def fig_rolling_beta(sym_a, sym_b, title, fname, start="2010-01-01",
                     use_log=False, window=126):
    a = load_local(sym_a, "daily")["close"].loc[start:]
    b = load_local(sym_b, "daily")["close"].loc[start:]
    df = align_pair(a, b)
    y = np.log(df["a"]) if use_log else df["a"].astype(float)
    x = np.log(df["b"]) if use_log else df["b"].astype(float)
    beta = rolling_ols_beta(y, x, window=window, shifted=True)
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(beta.index, beta.values, lw=0.9)
    ax.set_title(title)
    ax.set_ylabel(f"rolling OLS beta ({window}d, shifted)")
    fig.tight_layout()
    fig.savefig(FIG_DIR / fname, dpi=130)
    plt.close(fig)
    print(f"wrote {FIG_DIR / fname}")


if __name__ == "__main__":
    fig_residual("MES", "MYM",
                 "MES–MYM static-OLS residual, 2019-06 → 2026-07 (daily preview; "
                 "the only pair with daily-horizon structure)",
                 "preview_MES_MYM_residual.png")
    fig_residual("MES", "MNQ",
                 "MES–MNQ static-OLS residual, 2019-06 → 2026-07 (daily preview; "
                 "secular tech divergence → no daily cointegration)",
                 "preview_MES_MNQ_residual.png")
    fig_rolling_beta("ZT", "ZN",
                     "ZT–ZN rolling hedge ratio, 2010 → 2026 (daily preview; "
                     "rate-regime break ~2022 — adaptive hedging is mandatory)",
                     "preview_ZT_ZN_rolling_beta.png")
