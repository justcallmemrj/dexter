"""Pair construction: align two legs, build hedged residual series."""

from __future__ import annotations

import numpy as np
import pandas as pd


def align_pair(price_a: pd.Series, price_b: pd.Series,
               how: str = "inner") -> pd.DataFrame:
    """Align two price series on timestamps. Inner join by default: bars missing
    on either leg are dropped, never filled (see data_validation for flagging)."""
    df = pd.concat({"a": price_a, "b": price_b}, axis=1, join=how)
    return df.dropna()


def build_residual(price_a: pd.Series, price_b: pd.Series, beta: pd.Series,
                   use_log: bool = True) -> pd.Series:
    """Hedged residual: res_t = P_a - beta_t * P_b (log or raw prices).

    `beta` must already be look-ahead safe (fitted through t-1; see hedge_ratios —
    estimators return shifted series when shifted=True).
    """
    a = np.log(price_a) if use_log else price_a.astype(float)
    b = np.log(price_b) if use_log else price_b.astype(float)
    df = pd.concat({"a": a, "b": b, "beta": beta}, axis=1).dropna()
    return (df["a"] - df["beta"] * df["b"]).rename("residual")
