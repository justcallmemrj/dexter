"""Pin the D-022 verdict machinery to the banked nb14 evidence (the
report-13 pattern: a report can no longer drift from its own numbers).

Two layers: synthetic grids that exercise every branch of the frozen rule,
and — when the banked CSVs exist — pins of the actual notebook-14 outcome.
"""

import pathlib

import numpy as np
import pandas as pd
import pytest

from spread_research.delayed_entry_summary import (
    DELAYS, READ_SET_Z0, READ_SET_Z2, delayed_entry_summary,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
MR = REPO / "reports" / "machine_readable"


def _grids(retention, t_at=lambda d: 5.0, ms1=3.0):
    """Matched grids covering the full 37-cell read set with a given
    retention profile ratio(d) = retention(d)."""
    rows = []
    for signal, rs in (("0", READ_SET_Z0), ("2", READ_SET_Z2)):
        for spec, ez, h in rs:
            for d in DELAYS:
                rows.append({"signal": signal, "spec": spec, "entry_z": ez,
                             "horizon_bars": h, "delay": d, "matched": True,
                             "mean_bps": 0.0,
                             "mean_session_bps": ms1 * retention(d),
                             "t_clustered": t_at(d), "hit_rate": 0.5,
                             "n_events": 1000})
    return pd.DataFrame(rows)


def _xc(ab1=0.03, ab1_lo=0.02, asym1=0.028, asym1_lo=0.01):
    rows = [{"stat": "c0", "point": 0.8, "ci_lo": 0.79, "ci_hi": 0.81,
             "n_pairs": 600000}]
    for k in range(1, 6):
        for pre, p, lo in (("ab", ab1, ab1_lo), ("ba", 0.004, -0.005),
                           ("asym", asym1, asym1_lo)):
            rows.append({"stat": f"{pre}_{k}", "point": p, "ci_lo": lo,
                         "ci_hi": p + 0.02, "n_pairs": 600000})
    return pd.DataFrame(rows)


def test_lead_lag_branch_needs_decay_at_both_horizons_and_x():
    dead = _grids(lambda d: 1.0 if d == 1 else 0.05,
                  t_at=lambda d: 5.0 if d == 1 else 0.5)
    s = delayed_entry_summary(dead, _xc())
    assert s["verdict"] == "LEAD-LAG CONFIRMED"
    # same decay but no leg-level signature -> MIXED, never CONFIRMED
    s2 = delayed_entry_summary(dead, _xc(ab1_lo=-0.01, asym1_lo=-0.01))
    assert not s2["X"] and s2["verdict"] == "MIXED / UNRESOLVED"
    # decay at d=5 that rebounds by d=15 is not the catch-up story
    rebound = _grids(lambda d: {1: 1.0, 2: 0.3, 5: 0.2, 15: 0.8}[d],
                     t_at=lambda d: 5.0 if d in (1, 15) else 0.5)
    assert delayed_entry_summary(rebound, _xc())["verdict"] == "MIXED / UNRESOLVED"


def test_delay_robust_branch_matches_ar1_retention():
    phi = 2.0 ** (-1.0 / 40.0)
    s = delayed_entry_summary(_grids(lambda d: phi ** (d - 1)), _xc())
    assert s["verdict"] == "DELAY-ROBUST"
    assert s["rho_5"] == pytest.approx(phi ** 4, abs=1e-9)


def test_matching_degenerate_when_baseline_collapses():
    s = delayed_entry_summary(_grids(lambda d: 1.0, ms1=0.1), _xc())
    assert s["verdict"] == "INCONCLUSIVE - MATCHING DEGENERATE"
    assert s["n_included"] == 0


def test_partial_decay_lands_in_mixed():
    s = delayed_entry_summary(_grids(lambda d: {1: 1.0, 2: 0.7, 5: 0.5,
                                                15: 0.2}[d]), _xc())
    assert s["verdict"] == "MIXED / UNRESOLVED"


BANKED = (MR / "nb14_MES_M2K_delay_grids.csv").exists()


@pytest.mark.skipif(not BANKED, reason="nb14 CSVs not banked yet")
def test_banked_nb14_verdict_is_pinned():
    """The notebook-14 outcome, pinned. If these numbers move, the banked
    evidence changed and every document quoting it must be revisited."""
    grids = pd.read_csv(MR / "nb14_MES_M2K_delay_grids.csv")
    xc = pd.read_csv(MR / "nb14_MES_M2K_crosscorr.csv")
    s = delayed_entry_summary(grids, xc)
    assert s["verdict"] == "DELAY-ROBUST"
    assert s["n_included"] == 37 and s["n_excluded"] == 0
    assert s["rho_2"] == pytest.approx(0.932, abs=5e-3)
    assert s["rho_5"] == pytest.approx(0.849, abs=5e-3)
    assert s["rho_15"] == pytest.approx(0.536, abs=5e-3)
    assert s["S_5"] == pytest.approx(27 / 37, abs=1e-9)
    assert s["S_15"] == pytest.approx(22 / 37, abs=1e-9)
    assert s["c0"] == pytest.approx(0.788, abs=5e-4)
    assert s["ab_1"] == pytest.approx(0.033, abs=5e-4)
    assert s["ba_1"] == pytest.approx(0.0041, abs=5e-4)
    assert s["asym_1"] == pytest.approx(0.0289, abs=5e-4)
    assert s["X"] is True


@pytest.mark.skipif(not BANKED, reason="nb14 CSVs not banked yet")
def test_banked_headline_cells_are_pinned():
    """The cells the report quotes, straight from the banked grid."""
    grids = pd.read_csv(MR / "nb14_MES_M2K_delay_grids.csv")
    grids["signal"] = grids["signal"].astype(str)
    m = grids[grids["matched"].astype(bool)].set_index(
        ["signal", "spec", "entry_z", "horizon_bars", "delay"])

    def ms(sig, spec, ez, h, d):
        return float(m.loc[(sig, spec, ez, h, d), "mean_session_bps"])

    # Z2 S1 3.0/120 — the program's largest honest cell, now across delays
    # (matched baseline 6.676 vs unmatched 6.767: matching trims 4 events)
    assert ms("2", "S1", 3.0, 120, 1) == pytest.approx(6.676, abs=1e-3)
    assert ms("2", "S1", 3.0, 120, 5) == pytest.approx(4.739, abs=1e-3)
    assert ms("2", "S1", 3.0, 120, 15) == pytest.approx(2.243, abs=1e-3)
    # Z0 S1 3.0/60 — the highest banked honest t, across delays
    assert ms("0", "S1", 3.0, 60, 1) == pytest.approx(5.624, abs=1e-3)
    assert ms("0", "S1", 3.0, 60, 5) == pytest.approx(4.749, abs=1e-3)
    assert ms("0", "S1", 3.0, 60, 15) == pytest.approx(3.063, abs=1e-3)
