"""Parse and analyze the QC roll-audit log (notebook 01 evidence, A-004/D-004).

Input:  text file(s) containing backtest log lines with DEXTER_ROLL /
        DEXTER_ROLLSTATS markers (pages saved from the QC log API).
Output: reports/machine_readable/qc_roll_audit.csv        every roll event
        reports/machine_readable/qc_roll_audit_summary.csv per-symbol summary
        printed verdict table for the validation report

Usage:  .venv/Scripts/python.exe scripts/ingest_qc_rolls.py <log1> [<log2> ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def parse_logs(paths: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rolls, stats = [], []
    for p in paths:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if "DEXTER_ROLL " in line:
                rolls.append(json.loads(line.split("DEXTER_ROLL ", 1)[1]))
            elif "DEXTER_ROLLSTATS " in line:
                stats.append(json.loads(line.split("DEXTER_ROLLSTATS ", 1)[1]))
    rolls_df = pd.DataFrame(rolls)
    stats_df = pd.DataFrame(stats)
    if not rolls_df.empty:
        rolls_df = rolls_df.drop_duplicates(subset=["s", "d", "o", "n"])
    return rolls_df, stats_df


def summarize(rolls: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym, g in rolls.groupby("s"):
        st = stats[stats["s"] == sym]
        on_med = float(st["on_med_pct"].iloc[0]) if len(st) else float("nan")
        on_mad = float(st["on_mad_pct"].iloc[0]) if len(st) else float("nan")
        abs_ar = g["ar"].abs().dropna() if "ar" in g else pd.Series(dtype=float)
        abs_gp = g["gp"].abs().dropna() if "gp" in g else pd.Series(dtype=float)
        rows.append({
            "sym": sym,
            "n_rolls": len(g),
            "dte_min": g["dte"].min(), "dte_med": g["dte"].median(),
            "dte_max": g["dte"].max(),
            "gap_pct_med": abs_gp.median(), "gap_pct_max": abs_gp.max(),
            "splice_ret_pct_med": abs_ar.median(),
            "splice_ret_pct_max": abs_ar.max(),
            "overnight_med_pct": on_med, "overnight_mad_pct": on_mad,
            # Artifact ratio: splice return vs normal first-bar-of-day return.
            # ~1 means splices look like ordinary overnight bars (clean);
            # >> 1 means the roll gap leaks into the adjusted series (artifact).
            "artifact_ratio_med": (abs_ar.median() / on_med) if on_med else None,
            "vol_share_new_med": g["vs"].median() if "vs" in g else None,
            "vol_share_new_min": g["vs"].min() if "vs" in g else None,
        })
    return pd.DataFrame(rows).sort_values("sym")


def main(paths: list[str]) -> int:
    rolls, stats = parse_logs(paths)
    if rolls.empty:
        print("No DEXTER_ROLL lines found.")
        return 1
    out = Path("reports/machine_readable")
    out.mkdir(parents=True, exist_ok=True)
    rolls.to_csv(out / "qc_roll_audit.csv", index=False)
    summary = summarize(rolls, stats)
    summary.to_csv(out / "qc_roll_audit_summary.csv", index=False)
    pd.set_option("display.width", 200)
    print(f"{len(rolls)} roll events, {rolls['s'].nunique()} symbols")
    print(summary.to_string(index=False))
    print(f"\nwrote {out / 'qc_roll_audit.csv'} and _summary.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
