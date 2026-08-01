"""Data loading layer.

Canonical local schema (data/processed/<SYMBOL>_<resolution>.parquet or .csv):
    index: tz-aware UTC DatetimeIndex named 'timestamp' (bar END time)
    columns: open, high, low, close, volume
    optional: mapped_contract (e.g. 'MESU26') — required for roll audits,
              open_interest, bid, ask (when quote data exists)

Two loaders:
- load_local(): reads that schema from disk (any licensed data drop).
- load_quantbook(): thin wrapper for QuantConnect Research; import-guarded so the
  package works outside QC. It NEVER runs in this container (no QC access) —
  see reports/00_repository_audit.md L-001.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLS = ("open", "high", "low", "close", "volume")


def load_local(symbol: str, resolution: str = "minute",
               data_dir: str | Path = "data/processed") -> pd.DataFrame:
    """Load a locally stored series in the canonical schema. Raises with a clear
    message when the file is absent (data is a hard prerequisite, not an option)."""
    base = Path(data_dir)
    for ext in ("parquet", "csv"):
        path = base / f"{symbol}_{resolution}.{ext}"
        if path.exists():
            df = (pd.read_parquet(path) if ext == "parquet"
                  else pd.read_csv(path, index_col=0, parse_dates=True))
            missing = [c for c in REQUIRED_COLS if c not in df.columns]
            if missing:
                raise ValueError(f"{path}: missing required columns {missing}")
            if df.index.tz is None:
                raise ValueError(f"{path}: index must be tz-aware (UTC)")
            return df.sort_index()
    raise FileNotFoundError(
        f"No local data for {symbol} ({resolution}) under {base}. "
        "This environment has no market data (see reports/00_repository_audit.md); "
        "run inside QuantConnect Research or drop licensed data in the canonical schema."
    )


def load_quantbook(symbol_str: str, start, end, resolution: str = "minute",
                   contract_depth_offset: int = 0):
    """QuantConnect Research loader. Only callable inside QC (QuantBook available).

    Returns (continuous_df, mapped_contract_series):
    - continuous adjusted series for indicator work,
    - the mapped underlying contract symbol per bar for roll auditing and
      executable-price retrieval.

    Mapping/normalization modes come from config/research_config.yaml and are a
    tested assumption (D-004), not a constant.
    """
    try:
        from QuantConnect.Research import QuantBook           # noqa: F401
        from QuantConnect import Resolution                   # noqa: F401
        from QuantConnect.Data.UniverseSelection import (     # noqa: F401
            ContractDepthOffset,
        )
    except ImportError as e:
        raise RuntimeError(
            "load_quantbook() requires the QuantConnect Research environment. "
            "Use load_local() with a licensed data drop otherwise."
        ) from e
    raise NotImplementedError(
        "Implement inside QC Research per notebook 00 §data-inventory; kept "
        "unimplemented here so no untested QC API usage is committed as if verified."
    )
