"""Download the daily PREVIEW dataset (yfinance) into the canonical schema.

Run from the repo root:  .venv/Scripts/python.exe scripts/download_preview_daily.py

Writes:
- data/raw/yf_<TICKER>_daily.csv          untouched provider frames
- data/processed/<SYMBOL>_daily.csv       canonical frames (load_local-ready)
- reports/machine_readable/preview_data_quality.csv   full issues table
and prints a per-symbol summary. Screening tier only — see A-015 / D-007.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd

from spread_research.data_validation import run_all_checks
from spread_research.preview_data import (
    YF_SYMBOL_MAP, download_yf_daily, save_canonical,
)

# Micros exist from 2019-05-06; everything else gets long history for context.
START_BY_ROLE = {"micro": "2019-05-01", "treasury": "2010-01-01",
                 "parent_proxy": "2010-01-01"}


def main() -> int:
    all_issues = []
    summary_rows = []
    for sym, (ticker, role) in YF_SYMBOL_MAP.items():
        start = START_BY_ROLE[role]
        frames = download_yf_daily([sym], start=start)
        df = frames[sym]
        path = save_canonical(df, sym, "daily")
        issues = run_all_checks(df, sym, freq="1D")
        # Weekend/holiday gaps are expected cadence at daily resolution — count
        # them but keep only non-gap issues and >4-day gaps as noteworthy.
        gaps = issues[issues["check"] == "gap"]
        big_gaps = gaps[gaps["detail"].str.extract(r"gap of (\d+) days", expand=False)
                        .astype(float).fillna(0) > 4]
        non_gap = issues[issues["check"] != "gap"]
        noteworthy = pd.concat([non_gap, big_gaps], ignore_index=True)
        all_issues.append(issues.assign(role=role))
        summary_rows.append({
            "symbol": sym, "ticker": ticker, "role": role,
            "rows": len(df), "start": df.index[0].date(), "end": df.index[-1].date(),
            "nan_volume": int(df["volume"].isna().sum()),
            "zero_volume": int((df["volume"] == 0).sum()),
            "weekend_holiday_gaps": len(gaps) - len(big_gaps),
            "gaps_gt_4d": len(big_gaps),
            "other_issues": len(non_gap),
            "file": str(path),
        })
        print(f"{sym:4s} ({role:12s}) {len(df):5d} rows  "
              f"{df.index[0].date()} -> {df.index[-1].date()}  "
              f"gaps>4d={len(big_gaps)}  other_issues={len(non_gap)}")

    out_dir = Path("reports/machine_readable")
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.concat(all_issues, ignore_index=True).to_csv(
        out_dir / "preview_data_quality.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(
        out_dir / "preview_data_summary.csv", index=False)
    print(f"\nIssues table -> {out_dir / 'preview_data_quality.csv'}")
    print(f"Summary      -> {out_dir / 'preview_data_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
