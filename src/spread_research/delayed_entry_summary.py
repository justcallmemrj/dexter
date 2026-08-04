"""The D-022 verdict rule, exactly as frozen, computed from the banked nb14
CSVs — so the report cannot drift from its own evidence (the report-13
pattern, `program_summary.py`).

Everything decision-bearing here was fixed in the pre-registration BEFORE any
number existed: the 37-cell read set (enumerated in D-022 from the banked
nb02/nb06 grids), the denominator floor, the inclusion rule, the summary
statistics rho(d) / S(d) / X, and the branch thresholds. This module only
mechanises that text. If this module and D-022 ever disagree, D-022 wins and
the discrepancy is a defect here.
"""

from __future__ import annotations

import pandas as pd

# The frozen read set R: banked cells with session-clustered t >= +3 in
# S1/S2 (sources of record: nb02_MES_M2K_conditional_reversion.csv and the
# signal-2 rows of nb06_MES_M2K_signal_grids.csv). (spec, entry_z, horizon).
READ_SET_Z0 = [
    ("S1", 2.0, 120), ("S1", 2.5, 30), ("S1", 2.5, 60), ("S1", 2.5, 120),
    ("S1", 3.0, 15), ("S1", 3.0, 30), ("S1", 3.0, 60), ("S1", 3.0, 120),
    ("S2", 2.5, 120), ("S2", 3.0, 15), ("S2", 3.0, 30), ("S2", 3.0, 120),
]
READ_SET_Z2 = [
    ("S1", 1.5, 60), ("S1", 1.5, 120),
    ("S1", 2.0, 5), ("S1", 2.0, 15), ("S1", 2.0, 30), ("S1", 2.0, 60),
    ("S1", 2.0, 120),
    ("S1", 2.5, 5), ("S1", 2.5, 15), ("S1", 2.5, 30), ("S1", 2.5, 60),
    ("S1", 2.5, 120),
    ("S1", 3.0, 5), ("S1", 3.0, 15), ("S1", 3.0, 30), ("S1", 3.0, 60),
    ("S1", 3.0, 120),
    ("S2", 2.0, 30), ("S2", 2.0, 60), ("S2", 2.0, 120),
    ("S2", 2.5, 15), ("S2", 2.5, 30),
    ("S2", 3.0, 5), ("S2", 3.0, 15), ("S2", 3.0, 30),
]
assert len(READ_SET_Z0) == 12 and len(READ_SET_Z2) == 25

DELAYS = (1, 2, 5, 15)
RATIO_FLOOR_BPS = 0.5     # denominator floor on the matched d=1 session mean
RATIO_MIN_T = 2.0         # matched d=1 must keep t >= 2 to enter the ratios
MIN_INCLUDED = 12         # fewer than this of the 37 -> MATCHING DEGENERATE


def _cells(grids: pd.DataFrame, signal: str, read_set) -> pd.DataFrame:
    m = grids[(grids["matched"].astype(bool))
              & (grids["signal"].astype(str) == signal)]
    keys = pd.MultiIndex.from_tuples(read_set)
    m = m.set_index(["spec", "entry_z", "horizon_bars"])
    out = m[m.index.isin(keys)].reset_index()
    return out


def delayed_entry_summary(grids: pd.DataFrame,
                          crosscorr: pd.DataFrame) -> dict:
    """Apply the frozen D-022 rule. Inputs are the banked nb14 CSVs
    (`nb14_MES_M2K_delay_grids.csv`, `nb14_MES_M2K_crosscorr.csv`)."""
    per_cell = []
    for signal, read_set in (("0", READ_SET_Z0), ("2", READ_SET_Z2)):
        cells = _cells(grids, signal, read_set)
        for (spec, ez, h), g in cells.groupby(["spec", "entry_z",
                                               "horizon_bars"]):
            g = g.set_index("delay")
            ms1 = float(g.loc[1, "mean_session_bps"])
            t1 = float(g.loc[1, "t_clustered"])
            included = (ms1 >= RATIO_FLOOR_BPS) and (t1 >= RATIO_MIN_T)
            row = {"signal": signal, "spec": spec, "entry_z": ez,
                   "horizon_bars": h, "included": included,
                   "ms_d1": ms1, "t_d1": t1,
                   "n_events": int(g.loc[1, "n_events"])}
            for d in DELAYS:
                row[f"ms_d{d}"] = float(g.loc[d, "mean_session_bps"])
                row[f"t_d{d}"] = float(g.loc[d, "t_clustered"])
                row[f"ratio_d{d}"] = (float(g.loc[d, "mean_session_bps"]) / ms1
                                      if included else float("nan"))
            per_cell.append(row)
    cells = pd.DataFrame(per_cell)
    if len(cells) != 37:
        raise ValueError(f"read set resolved to {len(cells)} cells, not 37")

    inc = cells[cells["included"]]
    out = {"n_read_set": 37, "n_included": int(len(inc)),
           "n_excluded": int(37 - len(inc)), "per_cell": cells}

    xr = crosscorr.set_index("stat")
    out["c0"] = float(xr.loc["c0", "point"])
    out["ab_1"] = float(xr.loc["ab_1", "point"])
    out["ab_1_ci_lo"] = float(xr.loc["ab_1", "ci_lo"])
    out["ba_1"] = float(xr.loc["ba_1", "point"])
    out["asym_1"] = float(xr.loc["asym_1", "point"])
    out["asym_1_ci_lo"] = float(xr.loc["asym_1", "ci_lo"])
    out["X"] = bool(out["ab_1_ci_lo"] > 0 and out["asym_1_ci_lo"] > 0)

    if len(inc) < MIN_INCLUDED:
        out["verdict"] = "INCONCLUSIVE - MATCHING DEGENERATE"
        return out

    for d in DELAYS:
        out[f"rho_{d}"] = float(inc[f"ratio_d{d}"].median())
        out[f"rho_{d}_z0"] = float(
            inc[inc["signal"] == "0"][f"ratio_d{d}"].median())
        out[f"rho_{d}_z2"] = float(
            inc[inc["signal"] == "2"][f"ratio_d{d}"].median())
        out[f"S_{d}"] = float((inc[f"t_d{d}"] >= 3).mean())

    rho5, s5 = out["rho_5"], out["S_5"]
    rho15, s15 = out["rho_15"], out["S_15"]
    if (rho5 <= 1 / 3 and s5 <= 0.20 and rho15 <= 1 / 3 and s15 <= 0.20
            and out["X"]):
        out["verdict"] = "LEAD-LAG CONFIRMED"
    elif rho5 >= 2 / 3 and s5 >= 0.50 and rho15 >= 1 / 3:
        out["verdict"] = "DELAY-ROBUST"
    else:
        out["verdict"] = "MIXED / UNRESOLVED"
    return out
