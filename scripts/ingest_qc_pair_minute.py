"""Parse the notebook-02 QC run's summary statistics into machine-readable frames.

The QC free tier caps logs at 10KB/day, so `qc_pair_minute_analysis.py` emits
everything through `set_summary_statistic` as pipe-delimited strings. This is
the matching decoder: paste the statistics dict (as JSON) and it writes tidy
CSVs plus a JSON copy under reports/machine_readable/.

    python scripts/ingest_qc_pair_minute.py --input raw.json --run "<run name>"

Key layouts (mirrors src/spread_research/pair_minute_report.py):
  S_CR_<spec>_<entryz>   horizon:mean_bps:t_clustered:hit_rate:n_events | ...
  S_VR_<tag>_s<step>     q:vr:ci_lo:ci_hi:p_lt_1 | ...
  S_RL<LEG><nn>          yymmdd,splice_ret_pct,factor_gap_pct,flag | ...
  S_PF_<bucket>          n=..|sd=..|mz=..|p99=..|tail=..
  S_PF_SH<n>             yymmdd:shock_bps | ...
  S_CLOCK                minutes_from_open:share | ...
  scalar keys            k=v|k=v|...
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "machine_readable"


def _kv(value: str) -> dict:
    out = {}
    for part in str(value).split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def parse(stats: dict) -> dict[str, pd.DataFrame]:
    frames: dict[str, pd.DataFrame] = {}

    # --- conditional reversion (the D-010 primary statistic) ---------------
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_CR_"):
            continue
        _, _, spec, ez = key.split("_", 3)
        entry_z = float(ez[0] + "." + ez[1:]) if len(ez) > 1 else float(ez)
        for cell in str(val).split("|"):
            p = cell.split(":")
            if len(p) != 5:
                continue
            rows.append({"spec": spec, "entry_z": entry_z, "horizon_bars": int(p[0]),
                         "mean_bps": _num(p[1]), "t_clustered": _num(p[2]),
                         "hit_rate": _num(p[3]), "n_events": _num(p[4])})
    if rows:
        frames["conditional_reversion"] = pd.DataFrame(rows).sort_values(
            ["spec", "entry_z", "horizon_bars"]).reset_index(drop=True)

    # --- variance ratios ---------------------------------------------------
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_VR_"):
            continue
        tag, step = key[len("S_VR_"):].rsplit("_s", 1)
        for cell in str(val).split("|"):
            p = cell.split(":")
            if len(p) != 5:
                continue
            rows.append({"series": tag, "base_step_min": int(step), "q": int(p[0]),
                         "vr": _num(p[1]), "ci_lo": _num(p[2]), "ci_hi": _num(p[3]),
                         "p_lt_1": _num(p[4])})
    if rows:
        frames["variance_ratio"] = pd.DataFrame(rows).sort_values(
            ["series", "base_step_min", "q"]).reset_index(drop=True)

    # --- per-roll splice table (the acceptance gate evidence) --------------
    rows = []
    for key, val in stats.items():
        if not (key.startswith("S_RL") and key[4:].rstrip("0123456789")):
            continue
        leg = key[4:-2]
        for cell in str(val).split("|"):
            p = cell.split(",")
            if len(p) != 4:
                continue
            rows.append({"leg": leg, "roll": "20" + p[0],
                         "splice_ret_pct": _num(p[1]),
                         "factor_gap_pct": _num(p[2]), "artifact_flag": int(p[3])})
    if rows:
        df = pd.DataFrame(rows)
        df["roll"] = pd.to_datetime(df["roll"], format="%Y%m%d")
        frames["splice_gate"] = df.sort_values(["leg", "roll"]).reset_index(drop=True)

    # --- roll-window preflight buckets ------------------------------------
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_PF_") or key.startswith("S_PF_SH") or \
                key in ("S_PF_SHOCK", "S_PF_NROLLS"):
            continue
        kv = _kv(val)
        rows.append({"bucket": key[len("S_PF_"):].replace("_", ","),
                     "n_bars": _num(kv.get("n")), "sd_dres_bps": _num(kv.get("sd")),
                     "mean_abs_z": _num(kv.get("mz")), "p99_abs_z": _num(kv.get("p99")),
                     "frac_abs_z_gt2": _num(kv.get("tail"))})
    if rows:
        frames["roll_buckets"] = pd.DataFrame(rows)

    # --- held-position shock per roll -------------------------------------
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_PF_SH") or key == "S_PF_SHOCK":
            continue
        for cell in str(val).split("|"):
            p = cell.split(":")
            if len(p) == 2:
                rows.append({"roll": "20" + p[0], "shock_bps": _num(p[1])})
    if rows:
        df = pd.DataFrame(rows)
        df["roll"] = pd.to_datetime(df["roll"], format="%Y%m%d")
        frames["held_shock"] = df.sort_values("roll").reset_index(drop=True)

    # --- event clock profile ----------------------------------------------
    if "S_CLOCK" in stats:
        rows = [{"minutes_from_open": int(c.split(":")[0]),
                 "share": _num(c.split(":")[1])}
                for c in str(stats["S_CLOCK"]).split("|") if ":" in c]
        frames["event_clock"] = pd.DataFrame(rows)

    # --- scalars -----------------------------------------------------------
    scalar = {}
    for key in ("S_ALIGN", "S_BETA", "S_HL", "S_BUILD_MES", "S_BUILD_MYM",
                "S_PF_SHOCK", "S_PF_NROLLS", "S_HOLIDAYS", "S_GATE", "S_KEYS",
                "S_FATAL", "S_FATAL_TB", "S_RESOLVE_FAIL", "S_DATA_FAIL"):
        if key in stats:
            scalar[key] = str(stats[key])
    for key, val in stats.items():
        if key.startswith("S_FLAG_"):
            scalar[key] = str(val)
    if scalar:
        frames["scalars"] = pd.DataFrame(
            [{"key": k, "value": v} for k, v in scalar.items()])
    return frames


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file of the statistics dict")
    ap.add_argument("--run", default="", help="QC backtest name, for provenance")
    args = ap.parse_args()

    stats = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    stats = {k: v for k, v in stats.items() if k.startswith("S_")}
    if not stats:
        print("no S_* keys found — is this the right statistics dict?")
        return 1

    frames = parse(stats)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qc_pair_minute_MES_MYM.json").write_text(
        json.dumps({"run": args.run, "statistics": stats}, indent=1), encoding="utf-8")
    for name, df in frames.items():
        path = OUT / f"nb02_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {path.name:<34} {len(df):>4} rows")
    print(f"\n{len(stats)} statistics keys ingested (run={args.run!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
