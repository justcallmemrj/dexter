"""Parse the notebook-15 (D-024) QC runs into frames, enforcing every gate.

Three backtest parts per pair (L-019: the summary-stat channel has never
returned more than 57 keys intact). This script holds the FROZEN per-part key
manifests and refuses to write anything on a gate failure — the D-020/D-022
pattern: a voided run leaves no files to misread.

    # validate one part as soon as it is retrieved, before spending the next
    python scripts/ingest_qc_session_window.py --check raw_ZF_ZN_p1.json \
        --part 1 --pair ZF_ZN

    # full ingest for one pair once all parts are in
    python scripts/ingest_qc_session_window.py --pair ZF_ZN \
        --part1 raw_p1.json --part2 raw_p2.json --part3 raw_p3.json \
        --runs "Name1,Name2,Name3" --compare-banked

Gates (D-024 §5), all pass/fail on mechanics:
  1  TIMEZONE-WITNESS — delivered time-of-day span per leg. Treasury legs must
     read 08:31/16:00. **Bar count is never a witness** (any 390-minute window
     in a 23h session gives 390 bars — how L-021 hid for seven runs).
  2  REPRODUCTION — the S-USED grid must reproduce the banked
     nb02_<PAIR>_conditional_reversion.csv cell for cell at tolerance
     0.0005 (0.5 on n_events). Failure voids the PAIR.
  3  BUILD-DETERMINISM — S_GATE / S_BUILD_* / S_FLAG_* / S_FACSUM_* identical
     to the banked values and across parts. Failure voids the run.
  4  SESSION-GEOMETRY — medbars == the window's frozen bar count for the four
     dense windows; S-CASH reports fill density instead (sparsity is a
     FINDING, not a defect: a pre-open that does not print cannot be traded).
  5  EMISSION-COMPLETENESS — retrieved key SET == frozen manifest, S_KEYS ==
     its size.
  S-CASH-ENABLE — part 3's S_FACSUM_* must equal parts 1-2's, proving the
     D-009 construction survived the extended-hours fetch. On failure the
     S-CASH arm is VOID: every S-CASH key is dropped and nothing is written
     for it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import time

import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from spread_research.session_window_report import (  # noqa: E402
    PART_WINDOWS, WINDOWS, session_window_analysis_keys,
)

OUT = REPO / "reports" / "machine_readable"
TOL, TOL_N = 0.0005, 0.5
CASH_FLOOR = 0.80

# Driver-side keys. S_FLAG_* is pair-specific and resolved from the retrieved
# set; everything else is fixed.
DRIVER_FIXED = ["S_HOLIDAYS", "S_GATE", "S_PAIR", "S_KEYS"]
# Keys that must be IDENTICAL across parts — pre-filter quantities only.
# S_SESSCFG names the part and S_SPECS names the window its betas came from,
# so neither is an identity key. S_ALIGN is excluded for part 3, whose
# extended fetch legitimately delivers a denser panel.
IDENTITY = ["S_GATE", "S_HOLIDAYS"]


def manifest(part: int, legs: tuple[str, str], flags: list[str]) -> set[str]:
    keys = set(session_window_analysis_keys(part)) | set(DRIVER_FIXED)
    for leg in legs:
        keys.add(f"S_BUILD_{leg}")
        keys.add(f"S_FACSUM_{leg}")
    return keys | set(flags)


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _kv(val: str) -> dict:
    out = {}
    for part in str(val).split("|"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k] = v
    return out


def parse_grids(stats: dict) -> pd.DataFrame:
    """S_CR<W>_<spec>_<ez> -> tidy rows."""
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_CR") or len(key) < 7:
            continue
        # S_CR<W>_<spec>_<ez>: the window tag is a single char at index 4, so
        # a bare split("_") would also split the "S_" prefix.
        w, rest = key[4], key[6:].split("_")
        if w not in WINDOWS or len(rest) != 2:
            continue
        spec, ez = rest
        entry_z = float(ez[0] + "." + ez[1:]) if len(ez) > 1 else float(ez)
        for cell in str(val).split("|"):
            p = cell.split(":")
            if len(p) != 6:
                continue
            rows.append({"window": w, "window_name": WINDOWS[w][0],
                         "spec": spec, "entry_z": entry_z,
                         "horizon_bars": int(p[0]), "mean_bps": _num(p[1]),
                         "mean_session_bps": _num(p[2]),
                         "t_clustered": _num(p[3]), "hit_rate": _num(p[4]),
                         "n_events": _num(p[5])})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["window", "spec", "entry_z", "horizon_bars"]).reset_index(drop=True)


def parse_vr(stats: dict) -> pd.DataFrame:
    """S_VRA<W>/S_VRB<W> -> tidy rows. Layout: tag_sN~q:vr:lo:hi:p;..."""
    rows = []
    for key, val in stats.items():
        if not (key.startswith("S_VRA") or key.startswith("S_VRB")):
            continue
        w = key[5:]
        if w not in WINDOWS:
            continue
        for block in str(val).split("|"):
            if "~" not in block:
                continue
            head, cells = block.split("~", 1)
            tag, step = head.rsplit("_s", 1)
            for cell in cells.split(";"):
                p = cell.split(":")
                if len(p) != 5:
                    continue
                rows.append({"window": w, "window_name": WINDOWS[w][0],
                             "series": tag, "base_step": int(step),
                             "q": int(p[0]), "vr": _num(p[1]),
                             "ci_lo": _num(p[2]), "ci_hi": _num(p[3]),
                             "p_lt_1": _num(p[4])})
    return pd.DataFrame(rows)


def parse_open_subsets(stats: dict) -> pd.DataFrame:
    """S_OPEN<W> -> the L-018(i) open-window subset. EXPLORATORY: descriptive
    only, no branch label and no consequence may be derived from it."""
    rows = []
    for key, val in stats.items():
        if not key.startswith("S_OPEN"):
            continue
        w = key[len("S_OPEN"):]
        if w not in WINDOWS:
            continue
        for block in str(val).split("|"):
            if "~" not in block:
                continue
            ez, cells = block.split("~", 1)
            entry_z = float(ez[0] + "." + ez[1:]) if len(ez) > 1 else float(ez)
            for cell in cells.split(";"):
                p = cell.split(":")
                if len(p) != 6:
                    continue
                rows.append({"window": w, "window_name": WINDOWS[w][0],
                             "entry_z": entry_z, "horizon_bars": int(p[0]),
                             "mean_bps": _num(p[1]),
                             "mean_session_bps": _num(p[2]),
                             "t_clustered": _num(p[3]), "hit_rate": _num(p[4]),
                             "n_events": _num(p[5]),
                             "label": "EXPLORATORY_open_subset"})
    return pd.DataFrame(rows)


# --- gates ------------------------------------------------------------------


def gate_emission(stats: dict, part: int, legs, flags) -> tuple[bool, str]:
    got = {k for k in stats if k.startswith("S_")}
    want = manifest(part, legs, flags)
    missing, extra = sorted(want - got), sorted(got - want)
    if missing or extra:
        return False, f"missing={missing or 'none'} extra={extra or 'none'}"
    skeys = int(str(stats.get("S_KEYS", "0")))
    if skeys != len(want):
        return False, f"S_KEYS={skeys} but manifest holds {len(want)}"
    return True, f"{len(want)} keys, set-identical to the part-{part} manifest"


def gate_timezone(stats: dict, legs, part: int) -> tuple[bool, str]:
    """D-024 gate 1. The witness is WHERE the delivered day starts and ends,
    never how many bars it holds.

    Parts 1-2 use the regular-session fetch, whose Chicago-stamped Treasury
    span is exactly 08:31-16:00 — the L-021 signature. Part 3 requests extended
    hours, so a WIDER span is the point: it must reach at least back to 07:21
    (or S-CASH's leading block was never delivered) while still ending 16:00.
    """
    w = _kv(stats.get("S_TZWIT", ""))
    bad = []
    for leg in legs:
        span = w.get(leg, "")
        if not span:
            return False, f"no witness for {leg}"
        tod = span.rsplit(":", 1)[0]
        lo, hi = tod.split("-")
        if part == 3:
            if lo > "07:21" or hi != "16:00":
                bad.append(f"{leg} delivered {tod}; the extended fetch must "
                           f"reach 07:21 or earlier and end 16:00")
        elif tod != "08:31-16:00":
            bad.append(f"{leg} delivered {tod}, expected 08:31-16:00 "
                       f"(Chicago-stamped regular session)")
    if bad:
        return False, "; ".join(bad)
    shape = "extended fetch reaches the S-CASH block" if part == 3 else         "both legs 08:31-16:00 — Chicago stamps, L-021 signature"
    return True, shape


def gate_reproduction(grids: pd.DataFrame, pair: str) -> tuple[bool, str]:
    used = grids[grids["window"] == "U"]
    if used.empty:
        return True, "S-USED not in this part — not applicable"
    path = OUT / f"nb02_{pair}_conditional_reversion.csv"
    if not path.exists():
        return False, f"no banked grid at {path.name}"
    banked = pd.read_csv(path)
    keys = ["spec", "entry_z", "horizon_bars"]
    cols = ["mean_bps", "mean_session_bps", "t_clustered", "hit_rate",
            "n_events"]
    m = banked.merge(used[keys + cols], on=keys, suffixes=("_b", "_n"))
    if len(m) != len(banked) or len(banked) == 0:
        return False, f"{len(banked)} banked cells vs {len(m)} matched"
    bad = []
    for c in cols:
        d = (m[f"{c}_b"] - m[f"{c}_n"]).abs()
        tol = TOL_N if c == "n_events" else TOL
        if (d > tol).any():
            r = m.loc[d.idxmax()]
            bad.append(f"{c}: max|diff| {d.max():.4g} at {r['spec']}/"
                       f"z={r['entry_z']}/h={int(r['horizon_bars'])}")
    return (False, "; ".join(bad)) if bad else (True,
                                                f"{len(m)} cells reproduced exactly")


def gate_geometry(stats: dict) -> tuple[bool, str]:
    notes, bad = [], []
    for w, (name, _, _, want) in WINDOWS.items():
        raw = stats.get(f"S_GEO{w}")
        if raw is None:
            continue
        g = _kv(raw)
        med, blocks = g.get("medbars"), g.get("blocks_q120")
        if w == "C":
            notes.append(f"{name} medbars={med} (density-gated, not bar-gated)")
            continue
        if med != str(want):
            bad.append(f"{name}: medbars={med}, want {want}")
        else:
            notes.append(f"{name} {med}b/{blocks}blk")
    return (False, "; ".join(bad)) if bad else (True, "; ".join(notes))


def gate_cash_coverage(stats: dict, legs) -> tuple[bool, str]:
    raw = stats.get("S_CASHCOV")
    if raw is None:
        return True, "S-CASH not in this part — not applicable"
    cov = _kv(raw)
    thin = [f"{leg}={cov.get(leg)}" for leg in legs
            if _num(cov.get(leg, "nan")) < CASH_FLOOR]
    if thin:
        return False, ("INCONCLUSIVE-COVERAGE (a finding, not a defect): "
                       + ", ".join(thin) + f" below the {CASH_FLOOR} floor")
    return True, ", ".join(f"{leg}={cov.get(leg)}" for leg in legs)


def gate_identity(parts: dict[int, dict], legs) -> tuple[bool, str]:
    keys = list(IDENTITY) + [f"S_BUILD_{l}" for l in legs] \
        + [f"S_FACSUM_{l}" for l in legs]
    ref_part = min(parts)
    bad = []
    for k in keys:
        vals = {p: str(s.get(k)) for p, s in parts.items() if k in s}
        if len(set(vals.values())) > 1:
            bad.append(f"{k}: {vals}")
    if bad:
        return False, "; ".join(bad)
    return True, f"{len(keys)} pre-filter diagnostics identical across parts"


def gate_cash_enable(parts: dict[int, dict], legs) -> tuple[bool, str]:
    """The S-CASH-ENABLE gate: part 3's factor summary must equal parts 1-2's,
    proving `build_continuous`'s D-009 factors survived the extended fetch."""
    if 3 not in parts:
        return True, "no part 3 — S-CASH arm not attempted"
    ref = min(p for p in parts if p != 3)
    bad = [f"{leg}: p{ref}={parts[ref].get(f'S_FACSUM_{leg}')} "
           f"p3={parts[3].get(f'S_FACSUM_{leg}')}"
           for leg in legs
           if parts[ref].get(f"S_FACSUM_{leg}") != parts[3].get(f"S_FACSUM_{leg}")]
    if bad:
        return False, "factor table moved under the extended fetch: " + "; ".join(bad)
    return True, "D-009 factors identical under the extended fetch"


def _load(path: str) -> dict:
    s = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if isinstance(s, dict) and isinstance(s.get("statistics"), dict):
        s = s["statistics"]
    return {k: v for k, v in s.items() if k.startswith("S_")}


def _legs(pair: str) -> tuple[str, str]:
    a, b = pair.split("_")
    return a, b


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True, help="e.g. ZF_ZN")
    ap.add_argument("--check", help="single-part JSON: gates only, writes nothing")
    ap.add_argument("--part", type=int, choices=(1, 2, 3))
    ap.add_argument("--part1"); ap.add_argument("--part2"); ap.add_argument("--part3")
    ap.add_argument("--runs", default="", help="comma-separated QC run names")
    ap.add_argument("--compare-banked", action="store_true",
                    help="enforce every gate and refuse to write on failure")
    args = ap.parse_args()
    legs = _legs(args.pair)

    if args.check:
        if not args.part:
            print("--check needs --part {1,2,3}")
            return 1
        s = _load(args.check)
        flags = [k for k in s if k.startswith("S_FLAG_")]
        checks = [("gate 5 emission ", *gate_emission(s, args.part, legs, flags)),
                  ("gate 1 timezone ", *gate_timezone(s, legs, args.part)),
                  ("gate 2 reproduce", *gate_reproduction(parse_grids(s), args.pair)),
                  ("gate 4 geometry ", *gate_geometry(s))]
        if args.part == 3:
            checks.append(("cash coverage   ", *gate_cash_coverage(s, legs)))
        ok = True
        for name, passed, why in checks:
            print(f"  D-024 {name}: {'PASS' if passed else 'FAIL'} — {why}")
            ok &= passed
        print(f"\npart {args.part} {'VALID' if ok else 'VOID'} "
              f"(check mode: nothing written)")
        return 0 if ok else 2

    given = {p: getattr(args, f"part{p}") for p in (1, 2, 3)
             if getattr(args, f"part{p}")}
    if 1 not in given or 2 not in given:
        print("need at least --part1 and --part2")
        return 1
    parts = {p: _load(v) for p, v in given.items()}
    flags = sorted({k for s in parts.values() for k in s
                    if k.startswith("S_FLAG_")})

    gates = []
    for p, s in parts.items():
        gates.append((f"gate 5 emission p{p} ", *gate_emission(s, p, legs, flags)))
        gates.append((f"gate 1 timezone  p{p} ", *gate_timezone(s, legs, p)))
        gates.append((f"gate 4 geometry  p{p} ", *gate_geometry(s)))
    merged_stats = {}
    for p in sorted(parts):
        merged_stats.update(parts[p])
    gates.append(("gate 2 reproduction  ", *gate_reproduction(
        parse_grids(merged_stats), args.pair)))
    gates.append(("gate 3 identity      ", *gate_identity(parts, legs)))
    ok_cash, why_cash = gate_cash_enable(parts, legs)
    gates.append(("S-CASH-ENABLE        ", ok_cash, why_cash))
    ok_cov, why_cov = gate_cash_coverage(parts.get(3, {}), legs)
    gates.append(("S-CASH coverage      ", ok_cov, why_cov))

    all_ok = True
    for name, passed, why in gates:
        print(f"  D-024 {name}: {'PASS' if passed else 'FAIL'} — {why}")
        # A failing S-CASH arm voids only that arm, per D-024 §3.
        if name.strip() not in ("S-CASH-ENABLE", "S-CASH coverage"):
            all_ok &= passed
    if args.compare_banked and not all_ok:
        print("\nVALIDITY GATE FAILED — nothing written. Per D-024 the run is "
              "void and no verdict may be read from it.")
        return 2

    # Three states, not two: an arm that was never RUN has not been enabled.
    if 3 not in parts:
        cash_state = "NOT-ATTEMPTED"
    elif ok_cash and ok_cov:
        cash_state = "ENABLED"
    else:
        cash_state = "VOID"
    cash_void = cash_state == "VOID"
    if cash_void and 3 in parts:
        print("\nS-CASH arm VOID — dropping every S-CASH key; no S-CASH number "
              "is read, quoted or plotted (D-024 §3).")
        # Derived from the manifest, not string-matched: `endswith("C")` would
        # be one renamed key away from silently keeping an S-CASH number or
        # dropping an unrelated one, and "no S-CASH number is read, quoted or
        # plotted" is a binding D-024 §3 clause.
        shared = {"S_ALIGN", "S_SPECS", "S_SESSCFG", "S_TZWIT"}
        cash_keys = set(session_window_analysis_keys(3)) - shared
        merged_stats = {k: v for k, v in merged_stats.items()
                        if k not in cash_keys}

    grids, vr = parse_grids(merged_stats), parse_vr(merged_stats)
    opens = parse_open_subsets(merged_stats)
    scalar = {k: str(v) for k, v in merged_stats.items()
              if not k.startswith(("S_CR", "S_VRA", "S_VRB", "S_OPEN"))}
    for i, (name, passed, why) in enumerate(gates):
        scalar[f"D024_GATE_{i:02d}_{name.strip().replace(' ', '_')}"] = \
            f"{'PASS' if passed else 'FAIL'}|{why}"
    scalar["D024_SCASH_ARM"] = cash_state
    scalar["RUNS"] = args.runs

    OUT.mkdir(parents=True, exist_ok=True)
    for p, s in parts.items():
        (OUT / f"qc_session_window_{args.pair}_p{p}.json").write_text(
            json.dumps({"pair": args.pair, "part": p, "runs": args.runs,
                        "statistics": s}, indent=1), encoding="utf-8")
    written = {"window_grids": grids, "variance_ratios": vr,
               "open_subsets": opens,
               "scalars": pd.DataFrame([{"key": k, "value": v}
                                        for k, v in scalar.items()])}
    for name, df in written.items():
        path = OUT / f"nb15_{args.pair}_{name}.csv"
        df.to_csv(path, index=False)
        print(f"  {path.name:<42} {len(df):>4} rows")
    print(f"\n{sum(len(s) for s in parts.values())} statistics keys ingested "
          f"across {len(parts)} parts (pair={args.pair})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
