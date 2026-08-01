"""Parse the QC data-inventory audit log lines into repo artifacts.

Input:  a text file containing the backtest log (lines with 'DEXTER_ROW {json}')
Output: reports/machine_readable/qc_data_inventory.json (+ printed summary table)

Usage:  .venv/Scripts/python.exe scripts/ingest_qc_inventory.py <logfile>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


def parse_log(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        for marker in ("DEXTER_ROW2 ", "DEXTER_ROW "):
            if marker in line:
                payload = line.split(marker, 1)[1].strip()
                rows.append(json.loads(payload))
                break
    return rows


def main(path: str) -> int:
    text = Path(path).read_text(encoding="utf-8")
    rows = parse_log(text)
    if not rows:
        print("No DEXTER_ROW lines found — is this the right log file?")
        return 1
    out = Path("reports/machine_readable/qc_data_inventory.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rows, indent=2))

    table = pd.DataFrame([{
        "sym": r["sym"],
        "first_bar": r["first"],
        "last_bar": r["last"],
        "total_minute_bars": r["total"],
        "years_covered": len(r["per_year"]),
        "rolls_total": sum(r["rolls_per_year"].values()),
        "first_contract": r.get("mapped_first"),
        "last_contract": r.get("mapped_last"),
    } for r in rows])
    print(table.to_string(index=False))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
