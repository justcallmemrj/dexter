"""Tests for the daily preview data layer and screening metrics (D-007).

Offline only — network download is exercised by the driver script, not here.
"""

import numpy as np
import pandas as pd
import pytest

from spread_research import data_loader
from spread_research.preview_data import (
    YF_SYMBOL_MAP, canonicalize_yf_daily, save_canonical,
)
from spread_research.preview_screen import screen_pair, screen_tier


def _yf_like_frame(multiindex: bool, n: int = 30) -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=n, freq="B")  # naive, like yfinance
    close = 100 + np.arange(n, dtype=float)
    df = pd.DataFrame({
        "Open": close - 0.5, "High": close + 1.0, "Low": close - 1.0,
        "Close": close, "Adj Close": close, "Volume": np.full(n, 1000.0),
    }, index=idx)
    if multiindex:
        df.columns = pd.MultiIndex.from_product([df.columns, ["MES=F"]])
    return df


@pytest.mark.parametrize("multiindex", [False, True])
def test_canonicalize_yf_daily_schema(multiindex):
    out = canonicalize_yf_daily(_yf_like_frame(multiindex))
    assert list(out.columns) == list(data_loader.REQUIRED_COLS)
    assert out.index.tz is not None and str(out.index.tz) == "UTC"
    assert out.index.name == "timestamp"
    assert out.index.is_monotonic_increasing
    assert not out.index.duplicated().any()


def test_canonicalize_drops_priceless_rows_keeps_nan_volume():
    df = _yf_like_frame(False)
    df.iloc[3, df.columns.get_loc("Close")] = np.nan   # bar without a close
    df.iloc[5, df.columns.get_loc("Volume")] = np.nan  # bar without volume
    out = canonicalize_yf_daily(df)
    assert len(out) == len(df) - 1                     # priceless row dropped
    assert out["volume"].isna().sum() == 1             # NaN volume kept, not filled


def test_canonicalize_rejects_missing_price_columns():
    df = _yf_like_frame(False).drop(columns=["Close"])
    with pytest.raises(ValueError, match="missing price columns"):
        canonicalize_yf_daily(df)


def test_save_canonical_round_trips_through_load_local(tmp_path):
    out = canonicalize_yf_daily(_yf_like_frame(True))
    save_canonical(out, "MES", "daily", data_dir=tmp_path)
    loaded = data_loader.load_local("MES", "daily", data_dir=tmp_path)
    assert loaded.index.tz is not None
    pd.testing.assert_index_equal(loaded.index, out.index)
    np.testing.assert_allclose(loaded["close"].values, out["close"].values)


def test_symbol_map_covers_locked_universe():
    micros = {s for s, (_, r) in YF_SYMBOL_MAP.items() if r == "micro"}
    treasuries = {s for s, (_, r) in YF_SYMBOL_MAP.items() if r == "treasury"}
    assert micros == {"MES", "MNQ", "M2K", "MYM"}
    assert treasuries == {"ZT", "ZF", "ZN", "ZB"}
    # proxies are present but distinctly labeled (mandate rule 7)
    assert all(r == "parent_proxy" for s, (_, r) in YF_SYMBOL_MAP.items()
               if s in ("ES", "NQ", "RTY", "YM"))


def _daily_index(n):
    return pd.date_range("2018-01-02", periods=n, freq="B", tz="UTC")


def test_screen_pair_finds_planted_structure(rng):
    n = 2000
    x = 100 + np.cumsum(rng.normal(0, 0.3, n))
    hl = 10.0
    phi = np.exp(-np.log(2) / hl)
    res = np.zeros(n)
    eps = rng.normal(0, 0.4, n)
    for t in range(1, n):
        res[t] = phi * res[t - 1] + eps[t]
    y = 1.5 * x + res
    idx = _daily_index(n)
    row = screen_pair(pd.Series(y, idx), pd.Series(x, idx),
                      pair_name="SYN_COINT", use_log=False)
    assert row["status"] == "ok"
    assert row["eg_cointegrated_5pct"]
    assert row["static_resid_verdict"] in ("stationary", "stationary_marginal")
    assert row["beta_static"] == pytest.approx(1.5, rel=0.05)
    assert row["static_resid_half_life_days"] == pytest.approx(hl, rel=0.5)
    # L-007: rolling-hedge residual half-life must be reported and is expected
    # to be inflated (>= static) on noisy hedges; equality tolerance for luck.
    assert row["rolling_resid_half_life_days"] >= row["static_resid_half_life_days"] * 0.8
    assert screen_tier(row) == "daily_structure_present"


def test_screen_pair_negative_control_random_walks(rng):
    n = 2000
    a = 100 + np.cumsum(rng.normal(0, 0.5, n))
    b = 100 + np.cumsum(rng.normal(0, 0.5, n))
    idx = _daily_index(n)
    row = screen_pair(pd.Series(a, idx), pd.Series(b, idx),
                      pair_name="SYN_RW", use_log=False)
    assert row["status"] == "ok"
    assert not row["eg_cointegrated_5pct"]
    assert screen_tier(row) in ("daily_structure_weak", "no_daily_structure")


def test_screen_pair_insufficient_data():
    idx = _daily_index(50)
    row = screen_pair(pd.Series(np.arange(50.0), idx),
                      pd.Series(np.arange(50.0) + 1, idx),
                      pair_name="SHORT", use_log=False)
    assert row["status"] == "insufficient_data"
    assert screen_tier(row) == "insufficient_data"
