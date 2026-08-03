"""Parse the notebook-06 (D-020) QC run's summary statistics into frames.

Same channel and the same decoding discipline as
`ingest_qc_pair_minute.py` — the free tier caps logs at 10KB/day, so everything
comes back through `set_summary_statistic` as pipe-delimited strings — but the
grids are namespaced by SIGNAL DEFINITION rather than emitted once:

    python scripts/ingest_qc_signal_definition.py --input raw.json --run "<name>"

Key layouts (mirrors `pair_minute_report.pair_signal_report`):
  S_CR<z>_<spec>_<entryz>  horizon:mean_bps:mean_session_bps:t_clustered:
                           hit_rate:n_events | ...
                           z = 0 (configured 390-bar score, REPRODUCTION GATE)
                               1 (session-anchored, the fix under test)
                               2 (Z0 events minus the first 30 minutes)
                               O (the open subset alone — EXPLORATORY, S1 only)
  S_CLOCK<z>               minutes_from_open:share | ...
  S_OPENSHARE<z>           share=..|n_events=..
  S_ZCOVER, S_HL1, S_SIGDEF, S_SPECS, S_ALIGN, S_PAIR, S_GATE, S_BUILD_*,
  S_FLAG_*                 scalar keys, k=v|k=v|...

The Z0 reproduction gate is checked here rather than by eye:
`--compare-nb02` diffs this run's Z0 grid against the banked
`nb02_<PAIR>_conditional_reversion.csv` cell for cell and refuses to write
anything if they disagree, because a Z0 mismatch means the pipeline moved and
no Z0-vs-Z1 comparison is valid (D-020 validity gate 1).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "reports" / "machine_readable"

Z_LABEL = {"0": "z0_rolling390", "1": "z1_session_anchored",
           "2": "z2_open_excluded", "O": "zO_open_only_EXPLORATORY"}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def parse_grids(stats: dict) -> pd.DataFrame:
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_CR"):
            continue
        parts = key.split("_")            # S | CR<z> | <spec> | <entryz>
        if len(parts) != 4:
            continue
        variant, spec, ez = parts[1][len("CR"):], parts[2], parts[3]
        if variant not in Z_LABEL:
            continue
        entry_z = float(ez[0] + "." + ez[1:]) if len(ez) > 1 else float(ez)
        for cell in str(val).split("|"):
            p = cell.split(":")
            if len(p) != 6:
                continue
            rows.append({"signal": variant, "signal_label": Z_LABEL[variant],
                         "spec": spec, "entry_z": entry_z,
                         "horizon_bars": int(p[0]), "mean_bps": _num(p[1]),
                         "mean_session_bps": _num(p[2]),
                         "t_clustered": _num(p[3]), "hit_rate": _num(p[4]),
                         "n_events": _num(p[5])})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["signal", "spec", "entry_z", "horizon_bars"]).reset_index(drop=True)


def parse_clocks(stats: dict) -> pd.DataFrame:
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_CLOCK"):
            continue
        variant = key[len("S_CLOCK"):] or "0"
        for cell in str(val).split("|"):
            if ":" not in cell:
                continue
            m, s = cell.split(":")
            rows.append({"signal": variant, "signal_label": Z_LABEL.get(variant, variant),
                         "minutes_from_open": int(m), "share": _num(s)})
    return pd.DataFrame(rows)


def reproduction_gate(grids: pd.DataFrame, pair: str) -> tuple[bool, str]:
    """D-020 validity gate 1: this run's Z0 grid must reproduce the banked
    notebook-02/03 grid for the same pair, cell for cell, at emitted precision."""
    banked_path = OUT / f"nb02_{pair}_conditional_reversion.csv"
    if not banked_path.exists():
        return False, f"no banked grid at {banked_path.name} to reproduce"
    banked = pd.read_csv(banked_path)
    z0 = grids[grids["signal"] == "0"].drop(columns=["signal", "signal_label"])
    keys = ["spec", "entry_z", "horizon_bars"]
    merged = banked.merge(z0, on=keys, suffixes=("_nb02", "_nb06"))
    if len(merged) != len(banked):
        return False, (f"grid shape differs: {len(banked)} banked cells vs "
                       f"{len(merged)} matched")
    bad = []
    for col in ("mean_bps", "mean_session_bps", "t_clustered", "hit_rate",
                "n_events"):
        d = (merged[f"{col}_nb02"] - merged[f"{col}_nb06"]).abs()
        tol = 0.0005 if col != "n_events" else 0.5
        if (d > tol).any():
            worst = merged.loc[d.idxmax()]
            bad.append(f"{col}: max |diff| {d.max():.4g} at "
                       f"{worst['spec']}/z={worst['entry_z']}/h={int(worst['horizon_bars'])}")
    if bad:
        return False, "; ".join(bad)
    return True, f"{len(merged)} cells reproduced exactly"


def implementation_gate(clocks: pd.DataFrame, stats: dict) -> tuple[bool, str]:
    """D-020 validity gate 2: under Z1 no crossing may fire inside the warm-up,
    and the leading bucket's share must fall relative to Z0."""
    z1 = clocks[clocks["signal"] == "1"]
    if z1.empty:
        return False, "no Z1 event clock emitted"
    lead1 = float(z1[z1["minutes_from_open"] < 30]["share"].sum())
    z0 = clocks[clocks["signal"] == "0"]
    lead0 = float(z0[z0["minutes_from_open"] < 30]["share"].sum())
    if lead1 > 0:
        return False, f"Z1 fired {lead1:.3%} of crossings inside the warm-up"
    if lead0 <= 0:
        return False, "Z0 leading bucket is empty — nothing to remove"
    return True, f"open share {lead0:.1%} (Z0) -> {lead1:.1%} (Z1)"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="JSON file of the statistics dict")
    ap.add_argument("--run", default="", help="QC backtest name, for provenance")
    ap.add_argument("--pair", default=None,
                    help="e.g. MES_MYM. Defaults to the run's S_PAIR key.")
    ap.add_argument("--compare-nb02", action="store_true",
                    help="enforce D-020 validity gate 1 and refuse to write on "
                         "a mismatch")
    args = ap.parse_args()

    stats = json.loads(pathlib.Path(args.input).read_text(encoding="utf-8"))
    stats = {k: v for k, v in stats.items() if k.startswith("S_")}
    if not stats:
        print("no S_* keys found — is this the right statistics dict?")
        return 1

    pair = args.pair or str(stats.get("S_PAIR", "MES_MYM")).split("|")[0]
    grids, clocks = parse_grids(stats), parse_clocks(stats)
    if grids.empty:
        print("no S_CR<z>_* grids found — did the gate suppress the analysis?")
        print(f"  S_GATE = {stats.get('S_GATE')}")
        print(f"  S_FATAL = {stats.get('S_FATAL')}")
        return 1

    ok_repro, why_repro = reproduction_gate(grids, pair)
    ok_impl, why_impl = implementation_gate(clocks, stats)
    print(f"  D-020 gate 1 (Z0 reproduces nb02) : "
          f"{'PASS' if ok_repro else 'FAIL'} — {why_repro}")
    print(f"  D-020 gate 2 (Z1 clock flattens)  : "
          f"{'PASS' if ok_impl else 'FAIL'} — {why_impl}")
    if args.compare_nb02 and not (ok_repro and ok_impl):
        print("\nVALIDITY GATE FAILED — nothing written. Per D-020 the run is "
              "void and no verdict may be read from it.")
        return 2

    scalar = {k: str(v) for k, v in stats.items()
              if not k.startswith(("S_CR", "S_CLOCK"))}
    scalar.update({"D020_GATE1_REPRODUCTION": f"{'PASS' if ok_repro else 'FAIL'}|{why_repro}",
                   "D020_GATE2_IMPLEMENTATION": f"{'PASS' if ok_impl else 'FAIL'}|{why_impl}"})

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"qc_signal_definition_{pair}.json").write_text(
        json.dumps({"run": args.run, "pair": pair, "statistics": stats}, indent=1),
        encoding="utf-8")
    written = {"signal_grids": grids, "event_clocks": clocks,
               "scalars": pd.DataFrame([{"key": k, "value": v}
                                        for k, v in scalar.items()])}
    for name, df in written.items():
        path = OUT / f"nb06_{pair}_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {path.name:<44} {len(df):>4} rows")
    print(f"\n{len(stats)} statistics keys ingested (pair={pair}, run={args.run!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
