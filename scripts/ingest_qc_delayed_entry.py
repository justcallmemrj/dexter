"""Parse the notebook-14 (D-022) QC runs' summary statistics into frames.

Two backtest parts (L-019: the channel has never returned more than 57 keys
intact, so the battery ships as halves; both compute everything, each emits
its half). This script holds the FROZEN per-part key manifests and enforces
the D-022 validity gates. With ``--compare-banked`` it writes NOTHING on any
gate failure — the D-020 pattern: a voided run produces no files to
misread.

Two modes:

  # check one part right after retrieval, before spending the second backtest
  python scripts/ingest_qc_delayed_entry.py --check raw_part1.json --part 1

  # full ingest: both parts, all gates, writes the nb14 CSVs
  python scripts/ingest_qc_delayed_entry.py --part1 raw1.json --part2 raw2.json \
      --run1 "<name>" --run2 "<name>" --compare-banked

Key layouts (mirrors `pair_minute_report.pair_delayed_entry_report`):
  S_CR<z>_<spec>_<entryz>       unmatched d=1 REPRODUCTION grids
                                (z = 0 vs banked nb02; z = 2 vs banked nb06)
  S_DE<z>_<spec>_<entryz>_d<d>  matched delay grids, d in {1, 2, 5, 15}
  S_XC_AB / S_XC_BA             k:point:ci_lo:ci_hi:n_pairs | ...
  S_XC_AS                       asym per k, then c0:point:lo:hi:n, then nboot
  S_ALIGN, S_SPECS, S_DELAYCFG, S_PAIR, S_GATE, S_BUILD_*, S_FLAG_*, S_KEYS

Gates (D-022 "validity gates, applied BEFORE anything is read"):
  1   unmatched d=1 Z0 grid == nb02_MES_M2K_conditional_reversion.csv and
      unmatched d=1 Z2 grid == nb06_MES_M2K_signal_grids.csv signal-2 rows,
      cell for cell (tol 0.0005; 0.5 on n_events), all three specs
  2   matched n_events identical across the four delays, <= unmatched d=1
  2b  shared diagnostics identical across parts, character for character
  3   c(0) > 0.5; n_pairs positive per lag; exactly 1,000 replicates; all 15
      CIs finite with strictly positive width
  4   per part, retrieved key SET == frozen manifest and S_KEYS == its size
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from spread_research.pair_minute_report import (  # noqa: E402
    DELAYS, XCORR_LAGS, XCORR_NBOOT, delayed_entry_analysis_keys,
)

OUT = REPO / "reports" / "machine_readable"
PAIR = "MES_M2K"
Z_LABEL = {"0": "z0_rolling390", "2": "z2_open_excluded"}

# Driver-side keys, frozen for THIS pair and window: the banked runs
# established MES flags = 0 and M2K flags = exactly one (M2KM19 2019-06-13,
# sign_mismatch, reproduced identically three times).
DRIVER_KEYS = ["S_HOLIDAYS", "S_BUILD_MES", "S_BUILD_M2K", "S_FLAG_M2K190613",
               "S_GATE", "S_PAIR", "S_KEYS"]

# Gate 2b: shared diagnostics that must come back identical from both parts.
# S_DELAYCFG and S_PAIR legitimately differ (they name the part); S_KEYS
# differs (different manifest sizes).
SHARED_IDENTICAL = ["S_ALIGN", "S_SPECS", "S_GATE", "S_HOLIDAYS",
                    "S_BUILD_MES", "S_BUILD_M2K", "S_FLAG_M2K190613"]


def manifest(part: int) -> set[str]:
    return set(delayed_entry_analysis_keys(part)) | set(DRIVER_KEYS)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _grid_rows(key: str, val: str) -> list[dict]:
    """One S_CR / S_DE key -> per-horizon rows."""
    parts = key.split("_")
    if parts[1].startswith("CR") and len(parts) == 4:
        variant, spec, ez = parts[1][2:], parts[2], parts[3]
        delay, matched = 1, False
    elif parts[1].startswith("DE") and len(parts) == 5 and parts[4][:1] == "d":
        variant, spec, ez = parts[1][2:], parts[2], parts[3]
        delay, matched = int(parts[4][1:]), True
    else:
        return []                    # e.g. S_DELAYCFG shares the S_DE prefix
    entry_z = float(ez[0] + "." + ez[1:]) if len(ez) > 1 else float(ez)
    rows = []
    for cell in str(val).split("|"):
        p = cell.split(":")
        if len(p) != 6:
            continue
        rows.append({"signal": variant, "signal_label": Z_LABEL.get(variant, variant),
                     "spec": spec, "entry_z": entry_z, "delay": delay,
                     "matched": matched, "horizon_bars": int(p[0]),
                     "mean_bps": _num(p[1]), "mean_session_bps": _num(p[2]),
                     "t_clustered": _num(p[3]), "hit_rate": _num(p[4]),
                     "n_events": _num(p[5])})
    return rows


def parse_grids(stats: dict) -> pd.DataFrame:
    rows = []
    for key, val in stats.items():
        if key.startswith(("S_CR", "S_DE")):
            rows.extend(_grid_rows(key, val))
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["signal", "spec", "entry_z", "horizon_bars", "matched", "delay"]
    ).reset_index(drop=True)


def parse_crosscorr(stats: dict) -> pd.DataFrame:
    rows, nboot = [], None
    for key, prefix in (("S_XC_AB", "ab"), ("S_XC_BA", "ba"), ("S_XC_AS", "asym")):
        for cell in str(stats.get(key, "")).split("|"):
            p = cell.split(":")
            if p[0] == "nboot" and len(p) == 2:
                nboot = int(p[1])
            elif p[0] == "c0" and len(p) == 5:
                rows.append({"stat": "c0", "point": _num(p[1]),
                             "ci_lo": _num(p[2]), "ci_hi": _num(p[3]),
                             "n_pairs": _num(p[4])})
            elif len(p) == 5:
                rows.append({"stat": f"{prefix}_{p[0]}", "point": _num(p[1]),
                             "ci_lo": _num(p[2]), "ci_hi": _num(p[3]),
                             "n_pairs": _num(p[4])})
    df = pd.DataFrame(rows)
    if not df.empty:
        df.attrs["nboot"] = nboot
    return df


# --- gates ------------------------------------------------------------------


def gate_4_emission(stats: dict, part: int) -> tuple[bool, str]:
    got = {k for k in stats if k.startswith("S_")}
    want = manifest(part)
    missing, extra = sorted(want - got), sorted(got - want)
    if missing or extra:
        return False, f"missing={missing or 'none'} extra={extra or 'none'}"
    skeys = int(str(stats.get("S_KEYS", "0")))
    if skeys != len(want):
        return False, f"S_KEYS says {skeys} emitted, manifest holds {len(want)}"
    return True, f"{len(want)} keys, set-identical to the part-{part} manifest"


def gate_1_reproduction(grids: pd.DataFrame, part: int) -> tuple[bool, str]:
    repro = grids[(~grids["matched"]) & (grids["signal"] == ("0" if part == 1 else "2"))]
    keys = ["spec", "entry_z", "horizon_bars"]
    if part == 1:
        banked = pd.read_csv(OUT / f"nb02_{PAIR}_conditional_reversion.csv")
    else:
        nb06 = pd.read_csv(OUT / f"nb06_{PAIR}_signal_grids.csv")
        banked = nb06[nb06["signal"].astype(str) == "2"][
            keys + ["mean_bps", "mean_session_bps", "t_clustered", "hit_rate",
                    "n_events"]]
    merged = banked.merge(repro[keys + ["mean_bps", "mean_session_bps",
                                        "t_clustered", "hit_rate", "n_events"]],
                          on=keys, suffixes=("_banked", "_nb14"))
    if len(merged) != len(banked) or len(banked) == 0:
        return False, (f"grid shape differs: {len(banked)} banked cells vs "
                       f"{len(merged)} matched")
    bad = []
    for col in ("mean_bps", "mean_session_bps", "t_clustered", "hit_rate",
                "n_events"):
        d = (merged[f"{col}_banked"] - merged[f"{col}_nb14"]).abs()
        tol = 0.0005 if col != "n_events" else 0.5
        if (d > tol).any():
            worst = merged.loc[d.idxmax()]
            bad.append(f"{col}: max |diff| {d.max():.4g} at "
                       f"{worst['spec']}/z={worst['entry_z']}/"
                       f"h={int(worst['horizon_bars'])}")
    if bad:
        return False, "; ".join(bad)
    return True, f"{len(merged)} cells reproduced exactly"


def gate_2_matched_sets(grids: pd.DataFrame) -> tuple[bool, str]:
    matched = grids[grids["matched"]]
    if matched.empty:
        return False, "no matched delay grids found"
    bad = []
    keys = ["signal", "spec", "entry_z", "horizon_bars"]
    for name, g in matched.groupby(keys):
        if len(set(g["delay"])) != len(DELAYS):
            bad.append(f"{name}: delays present {sorted(set(g['delay']))}")
        elif g["n_events"].nunique() != 1:
            bad.append(f"{name}: n_events varies {sorted(set(g['n_events']))}")
    un = grids[(~grids["matched"])].set_index(keys)["n_events"]
    for name, g in matched.groupby(keys):
        if name in un.index and float(g["n_events"].iloc[0]) > float(un.loc[name]) + 0.5:
            bad.append(f"{name}: matched n exceeds unmatched")
    if bad:
        return False, "; ".join(bad[:4]) + (f" (+{len(bad)-4} more)" if len(bad) > 4 else "")
    n_fam = len(matched.groupby(keys))
    return True, f"n_events constant across {{1,2,5,15}} in all {n_fam} cells"


def gate_2b_cross_part(s1: dict, s2: dict) -> tuple[bool, str]:
    bad = [k for k in SHARED_IDENTICAL if str(s1.get(k)) != str(s2.get(k))]
    if bad:
        return False, f"differs across parts: {bad}"
    return True, f"{len(SHARED_IDENTICAL)} shared diagnostics identical"


def gate_3_crosscorr(xc: pd.DataFrame) -> tuple[bool, str]:
    if xc.empty:
        return False, "no cross-correlation keys"
    r = xc.set_index("stat")
    expected = (["c0"] + [f"ab_{k}" for k in XCORR_LAGS]
                + [f"ba_{k}" for k in XCORR_LAGS]
                + [f"asym_{k}" for k in XCORR_LAGS])
    missing = [s for s in expected if s not in r.index]
    if missing:
        return False, f"missing stats: {missing}"
    if not float(r.loc["c0", "point"]) > 0.5:
        return False, f"c0 = {r.loc['c0', 'point']:.4f} <= 0.5 (alignment defect)"
    if (r["n_pairs"] <= 0).any():
        return False, "a lag has zero within-session pairs"
    if xc.attrs.get("nboot") != XCORR_NBOOT:
        return False, f"nboot = {xc.attrs.get('nboot')} != {XCORR_NBOOT}"
    ci = r.drop("c0")[["ci_lo", "ci_hi"]]
    widths = ci["ci_hi"] - ci["ci_lo"]
    if ci.isna().any().any() or (widths <= 0).any():
        return False, "a bootstrap CI is non-finite or zero-width"
    return True, (f"c0 = {r.loc['c0', 'point']:.3f}, 15 finite CIs, "
                  f"{XCORR_NBOOT} replicates")


def _load(path: str) -> dict:
    stats = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if "statistics" in stats and isinstance(stats["statistics"], dict):
        stats = stats["statistics"]
    return {k: v for k, v in stats.items() if k.startswith("S_")}


def _code_hashes() -> dict[str, str]:
    """Record the upload manifest's normalised hashes (D-022 retry policy:
    the analysis-code hash must be unchanged and is recorded here).

    `build_qc_upload.py` writes the manifest as a top-level JSON LIST of
    per-file entries; tolerate a dict wrapper too so a future builder change
    cannot crash the success path."""
    mpath = REPO / "data" / "interim" / "qc_upload" / "manifest.json"
    if not mpath.exists():
        return {}
    m = json.loads(mpath.read_text(encoding="utf-8"))
    entries = m if isinstance(m, list) else m.get("manifest", m.get("files", []))
    return {f"code_sha_{f['dest']}": f["sha256_upload_norm"]
            for f in entries
            if isinstance(f, dict) and "sha256_upload_norm" in f}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", help="single part JSON: gates 1/2/4 only, writes nothing")
    ap.add_argument("--part", type=int, choices=(1, 2),
                    help="which part --check is validating")
    ap.add_argument("--part1", help="part-1 statistics JSON")
    ap.add_argument("--part2", help="part-2 statistics JSON")
    ap.add_argument("--run1", default="", help="part-1 QC backtest name")
    ap.add_argument("--run2", default="", help="part-2 QC backtest name")
    ap.add_argument("--compare-banked", action="store_true",
                    help="enforce every gate and refuse to write on failure")
    args = ap.parse_args()

    if args.check:
        if not args.part:
            print("--check needs --part {1,2}")
            return 1
        stats = _load(args.check)
        grids = parse_grids(stats)
        checks = [("gate 4 (emission set)", *gate_4_emission(stats, args.part)),
                  ("gate 1 (reproduction)", *gate_1_reproduction(grids, args.part)),
                  ("gate 2 (matched sets)", *gate_2_matched_sets(grids))]
        if args.part == 2:
            checks.append(("gate 3 (crosscorr)", *gate_3_crosscorr(parse_crosscorr(stats))))
        ok = True
        for name, passed, why in checks:
            print(f"  D-022 {name:<22}: {'PASS' if passed else 'FAIL'} — {why}")
            ok &= passed
        print(f"\npart {args.part} {'VALID' if ok else 'VOID'} (check mode: nothing written)")
        return 0 if ok else 2

    if not (args.part1 and args.part2):
        print("need --part1 and --part2 (or --check with --part)")
        return 1
    s1, s2 = _load(args.part1), _load(args.part2)
    g1, g2 = parse_grids(s1), parse_grids(s2)
    xc = parse_crosscorr(s2)

    gates = [("gate 4 part 1 (emission)", *gate_4_emission(s1, 1)),
             ("gate 4 part 2 (emission)", *gate_4_emission(s2, 2)),
             ("gate 1 Z0 (vs nb02)     ", *gate_1_reproduction(g1, 1)),
             ("gate 1 Z2 (vs nb06)     ", *gate_1_reproduction(g2, 2)),
             ("gate 2 part 1 (matched) ", *gate_2_matched_sets(g1)),
             ("gate 2 part 2 (matched) ", *gate_2_matched_sets(g2)),
             ("gate 2b (cross-part)    ", *gate_2b_cross_part(s1, s2)),
             ("gate 3 (crosscorr)      ", *gate_3_crosscorr(xc))]
    all_ok = True
    for name, passed, why in gates:
        print(f"  D-022 {name}: {'PASS' if passed else 'FAIL'} — {why}")
        all_ok &= passed
    if args.compare_banked and not all_ok:
        print("\nVALIDITY GATE FAILED — nothing written. Per D-022 the run is "
              "void and no verdict may be read from it.")
        return 2

    grids = pd.concat([g1, g2], ignore_index=True).sort_values(
        ["signal", "spec", "entry_z", "horizon_bars", "matched", "delay"]
    ).reset_index(drop=True)
    scalar = {k: str(v) for k, v in {**s1, **s2}.items()
              if not k.startswith(("S_CR", "S_DE", "S_XC"))}
    scalar["S_DELAYCFG_P1"] = str(s1.get("S_DELAYCFG"))
    scalar["S_DELAYCFG_P2"] = str(s2.get("S_DELAYCFG"))
    scalar["RUN_P1"], scalar["RUN_P2"] = args.run1, args.run2
    for name, passed, why in gates:
        tag = ("D022_" + name.strip().upper().replace(" ", "_")
               .replace("(", "").replace(")", "").replace("-", "_"))
        scalar[tag] = f"{'PASS' if passed else 'FAIL'}|{why}"
    scalar.update(_code_hashes())

    OUT.mkdir(parents=True, exist_ok=True)
    for tag, stats, run in (("part1", s1, args.run1), ("part2", s2, args.run2)):
        (OUT / f"qc_delayed_entry_{PAIR}_{tag}.json").write_text(
            json.dumps({"run": run, "pair": PAIR, "part": tag,
                        "statistics": stats}, indent=1), encoding="utf-8")
    written = {"delay_grids": grids, "crosscorr": xc,
               "scalars": pd.DataFrame([{"key": k, "value": v}
                                        for k, v in scalar.items()])}
    for name, df in written.items():
        path = OUT / f"nb14_{PAIR}_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {path.name:<40} {len(df):>4} rows")
    print(f"\n{len(s1)} + {len(s2)} statistics keys ingested "
          f"(runs={args.run1!r}, {args.run2!r})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
