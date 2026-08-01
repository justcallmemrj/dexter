"""Daily-resolution PREVIEW data layer (yfinance) — screening tier only.

Scope and honesty rules (D-007, A-015):
- Yahoo Finance ``=F`` series are front-month continuous quotes with an
  UNDOCUMENTED roll methodology. They are usable for daily-resolution pair
  SCREENING (relationship structure, hedge stability, obvious disqualifiers)
  and for nothing else. Never execution simulation, never minute-level claims.
- Daily bars from Yahoo carry a date, not a bar-end time. Canonical frames
  stamp each bar at 00:00 UTC of its trade date; this is a labeling convention
  for alignment, not a claim about session close times.
- Parent contracts (ES/NQ/RTY/YM) are downloaded ONLY as clearly-labeled
  long-history proxies for the micro relationship (mandate rule 7): separate
  symbols, separate files, never merged with micro series.

Network access happens only in ``download_yf_daily``; everything else is pure
and unit-tested offline.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .data_loader import REQUIRED_COLS

# Canonical symbol -> (Yahoo ticker, role). Roles: micro | treasury | parent_proxy
YF_SYMBOL_MAP: dict[str, tuple[str, str]] = {
    "MES": ("MES=F", "micro"),
    "MNQ": ("MNQ=F", "micro"),
    "M2K": ("M2K=F", "micro"),
    "MYM": ("MYM=F", "micro"),
    "ZT": ("ZT=F", "treasury"),
    "ZF": ("ZF=F", "treasury"),
    "ZN": ("ZN=F", "treasury"),
    "ZB": ("ZB=F", "treasury"),
    # Long-history proxies for index-pair structure (labeled, never merged):
    "ES": ("ES=F", "parent_proxy"),
    "NQ": ("NQ=F", "parent_proxy"),
    "RTY": ("RTY=F", "parent_proxy"),
    "YM": ("YM=F", "parent_proxy"),
}

_RENAME = {"Open": "open", "High": "high", "Low": "low", "Close": "close",
           "Volume": "volume", "Adj Close": "adj_close"}


def canonicalize_yf_daily(raw: pd.DataFrame) -> pd.DataFrame:
    """Convert a yfinance download frame (single ticker; flat or MultiIndex
    columns) to the canonical schema: tz-aware UTC index named 'timestamp',
    lowercase open/high/low/close/volume, sorted, deduplicated.

    Rows with any missing OHLC are DROPPED (a daily bar without prices is not a
    bar); missing volume is kept as NaN — flagged downstream, never filled.
    """
    if raw is None or len(raw) == 0:
        raise ValueError("empty yfinance frame")
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        # yfinance shape: (field, ticker) — single ticker, so drop level 1
        df.columns = df.columns.get_level_values(0)
    df = df.rename(columns=_RENAME)
    missing = [c for c in ("open", "high", "low", "close") if c not in df.columns]
    if missing:
        raise ValueError(f"yfinance frame missing price columns {missing}")
    if "volume" not in df.columns:
        df["volume"] = pd.NA
    df = df[[c for c in REQUIRED_COLS]]
    df = df.dropna(subset=["open", "high", "low", "close"])
    idx = pd.DatetimeIndex(df.index)
    idx = idx.tz_localize("UTC") if idx.tz is None else idx.tz_convert("UTC")
    df.index = idx
    df.index.name = "timestamp"
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def save_canonical(df: pd.DataFrame, symbol: str, resolution: str = "daily",
                   data_dir: str | Path = "data/processed") -> Path:
    """Write a canonical frame where data_loader.load_local() will find it."""
    base = Path(data_dir)
    base.mkdir(parents=True, exist_ok=True)
    path = base / f"{symbol}_{resolution}.csv"
    df.to_csv(path, date_format="%Y-%m-%dT%H:%M:%S%z")
    return path


def download_yf_daily(symbols: list[str], start: str, end: str | None = None,
                      raw_dir: str | Path = "data/raw") -> dict[str, pd.DataFrame]:
    """Download daily bars for canonical symbols via yfinance (network).

    Saves the untouched provider frame to data/raw/yf_<TICKER>_daily.csv and
    returns {symbol: canonical frame}. Raises KeyError for unknown symbols so a
    typo cannot silently screen the wrong instrument.
    """
    import yfinance as yf

    out: dict[str, pd.DataFrame] = {}
    raw_base = Path(raw_dir)
    raw_base.mkdir(parents=True, exist_ok=True)
    for sym in symbols:
        ticker, _role = YF_SYMBOL_MAP[sym]
        raw = yf.download(ticker, start=start, end=end, interval="1d",
                          auto_adjust=False, progress=False)
        if raw is None or len(raw) == 0:
            raise RuntimeError(f"yfinance returned no data for {sym} ({ticker})")
        raw.to_csv(raw_base / f"yf_{ticker.replace('=', '')}_daily.csv")
        out[sym] = canonicalize_yf_daily(raw)
    return out
