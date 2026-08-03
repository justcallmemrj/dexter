"""D-020: the session-anchored z-score and the event filters it needs.

Everything here runs on synthetic series with known answers, which is the point:
a QuantConnect backtest is a slow and expensive place to discover that a signal
definition does not mean what the pre-registration says it means.

The two tests that matter most are the ones that pin D-020's validity gates
before the run rather than after it — `test_z0_grid_reproduces_the_notebook_02
_battery` (the reproduction gate) and `test_session_anchor_removes_the_open
_clustering` (the implementation gate).
"""

import numpy as np
import pandas as pd
import pytest

from spread_research.intraday_reversion import (
    conditional_reversion, event_clock_profile, first_minutes_mask,
    session_anchored_zscore,
)
from spread_research.pair_minute_report import (
    ENTRY_GRID, HORIZONS, pair_minute_report, pair_signal_report,
)
from spread_research.signals import rolling_zscore

BARS = 390
WARMUP = 30


def _index(n_sessions):
    days = pd.bdate_range("2021-01-04", periods=n_sessions)
    return pd.DatetimeIndex(np.concatenate([
        (d + pd.Timedelta(minutes=571) + pd.to_timedelta(np.arange(BARS), "m")
         ).values for d in days]))


def _series(values, n_sessions):
    return pd.Series(values, index=_index(n_sessions))


# --- the z-score itself ----------------------------------------------------

def test_zscore_is_the_expanding_within_session_statistic():
    rng = np.random.default_rng(11)
    x = _series(rng.normal(size=2 * BARS), 2)
    z = session_anchored_zscore(x, warmup_bars=WARMUP)

    # Warm-up is silent in every session, not just the first.
    assert z.iloc[:WARMUP].isna().all()
    assert z.iloc[BARS:BARS + WARMUP].isna().all()

    for pos in (WARMUP, 100, BARS + WARMUP, BARS + 250):
        session_start = (pos // BARS) * BARS
        prior = x.values[session_start:pos]
        expected = (x.values[pos] - prior.mean()) / prior.std(ddof=1)
        assert z.iloc[pos] == pytest.approx(expected)


def test_no_bar_from_a_prior_session_enters():
    """The whole point of L-013. Session 2 sits at a completely different level;
    a window that leaked across the break would score its open as a ~50-sigma
    dislocation, which is exactly what the 390-bar score does."""
    a = np.random.default_rng(3).normal(0, 1, BARS)
    b = np.random.default_rng(4).normal(500, 1, BARS)     # overnight repricing
    x = _series(np.concatenate([a, b]), 2)

    anchored = session_anchored_zscore(x, warmup_bars=WARMUP)
    overnight = rolling_zscore(x, BARS)

    second = anchored.iloc[BARS:].dropna()
    assert second.abs().max() < 6.0
    # The configured score puts the repricing straight into the signal.
    assert overnight.iloc[BARS:BARS + 60].abs().max() > 20.0


def test_a_short_session_produces_no_signal_rather_than_a_noisy_one():
    idx = _index(1)[:WARMUP - 1]
    z = session_anchored_zscore(pd.Series(np.arange(len(idx), dtype=float), idx),
                                warmup_bars=WARMUP)
    assert z.isna().all()


def test_warmup_must_be_large_enough_to_estimate_a_dispersion():
    with pytest.raises(ValueError):
        session_anchored_zscore(_series(np.zeros(BARS), 1), warmup_bars=1)


def test_first_minutes_mask_matches_the_event_clocks_leading_bucket():
    idx = _index(1)
    mask = first_minutes_mask(idx, 30)
    assert mask.sum() == 29                       # 09:31-09:59 inclusive
    assert mask.iloc[0] and not mask.iloc[29]
    assert idx[mask.values][-1].strftime("%H:%M") == "09:59"


# --- event selection -------------------------------------------------------

def _reverting_pair(n_sessions=40, seed=5):
    """Leg A = leg B plus an OU residual, so events exist to be filtered."""
    rng = np.random.default_rng(seed)
    n = n_sessions * BARS
    common = 100 + np.cumsum(rng.normal(0, 0.02, n))
    ou = np.zeros(n)
    phi = np.exp(-np.log(2) / 40.0)
    eps = rng.normal(0, 0.05, n)
    for t in range(1, n):
        ou[t] = phi * ou[t - 1] + eps[t]
    idx = _index(n_sessions)
    return (pd.Series(common + ou, idx), pd.Series(common, idx))


def test_event_filter_selects_a_strict_subset_and_partitions_the_events():
    a, b = _reverting_pair()
    res = np.log(a) - np.log(b)
    z = rolling_zscore(res, BARS)
    not_open = ~first_minutes_mask(res.index, 30)

    full = conditional_reversion(res, z, entry_z=2.0, horizons=(15,))
    kept = conditional_reversion(res, z, entry_z=2.0, horizons=(15,),
                                 event_filter=not_open)
    dropped = conditional_reversion(res, z, entry_z=2.0, horizons=(15,),
                                    event_filter=~not_open)

    assert kept["n_events"].iloc[0] < full["n_events"].iloc[0]
    assert (kept["n_events"].iloc[0] + dropped["n_events"].iloc[0]
            == full["n_events"].iloc[0])


def test_an_all_true_filter_changes_nothing():
    a, b = _reverting_pair()
    res = np.log(a) - np.log(b)
    z = rolling_zscore(res, BARS)
    everything = pd.Series(True, index=res.index)
    base = conditional_reversion(res, z, entry_z=2.0)
    same = conditional_reversion(res, z, entry_z=2.0, event_filter=everything)
    pd.testing.assert_frame_equal(base, same)


def test_session_bounded_events_blocks_a_crossing_across_the_close():
    """With a per-session warm-up the alignment drops those bars, leaving a
    session's first scored bar next to the PREVIOUS session's last bar. Without
    the guard a crossing is detected across the overnight close."""
    idx = _index(2)
    res = pd.Series(np.zeros(len(idx)), idx)
    z = pd.Series(np.nan, idx)
    z.iloc[BARS - 1] = 0.0                       # quiet at yesterday's close
    z.iloc[BARS + WARMUP:BARS + WARMUP + 20] = 3.0  # dislocated after warm-up

    unguarded = conditional_reversion(res, z, entry_z=2.0, horizons=(5,),
                                      min_events=1)
    guarded = conditional_reversion(res, z, entry_z=2.0, horizons=(5,),
                                    min_events=1, session_bounded_events=True)
    assert unguarded["n_events"].iloc[0] == 1
    assert guarded["n_events"].iloc[0] == 0


def test_event_clock_honours_the_same_guard():
    idx = _index(2)
    z = pd.Series(np.nan, idx)
    z.iloc[BARS - 1] = 0.0
    z.iloc[BARS + WARMUP] = 3.0
    assert len(event_clock_profile(z, 2.0)) == 1
    assert len(event_clock_profile(z, 2.0, session_bounded=True)) == 0


# --- the two D-020 validity gates, pinned before the run -------------------

def test_z0_grid_reproduces_the_notebook_02_battery():
    """D-020's reproduction gate. The signal-definition run re-emits Z0 so that
    a mismatch against the banked notebook-02/03 grid proves the pipeline moved.
    That only works if the two batteries compute Z0 identically — here, on a
    synthetic pair whose answer neither of them knows."""
    a, b = _reverting_pair(n_sessions=30, seed=9)
    nb02 = pair_minute_report(a, b, roll_timestamps=[],
                              factors_a=pd.Series(dtype=float),
                              factors_b=pd.Series(dtype=float), n_boot=5)
    nb06 = pair_signal_report(a, b)

    shared = [k for k in nb02 if k.startswith("S_CR_")]
    assert len(shared) == 3 * len(ENTRY_GRID)
    for key in shared:
        assert nb06[key.replace("S_CR_", "S_CR0_")] == nb02[key]
    assert nb06["S_CLOCK0"] == nb02["S_CLOCK"]


def test_session_anchor_removes_the_open_clustering():
    """D-020's implementation gate: no event may fire inside the warm-up, and
    the leading-bucket share must go to zero under Z1."""
    a, b = _reverting_pair(n_sessions=60, seed=13)
    rep = pair_signal_report(a, b)

    open0 = float(rep["S_OPENSHARE0"].split("|")[0].split("=")[1])
    open1 = float(rep["S_OPENSHARE1"].split("|")[0].split("=")[1])
    assert open1 == 0.0
    assert open1 < open0 or open0 == 0.0

    z1_clock = dict(kv.split(":") for kv in rep["S_CLOCK1"].split("|"))
    assert all(int(m) >= 30 for m in z1_clock)


def test_signal_report_emits_every_pre_registered_variant():
    a, b = _reverting_pair(n_sessions=30, seed=21)
    rep = pair_signal_report(a, b)
    for tag in ("0", "1", "2"):
        for spec in ("S1", "S2", "S3"):
            for ez in ENTRY_GRID:
                key = f"S_CR{tag}_{spec}_{str(ez).replace('.', '')}"
                assert key in rep, key
                assert len(rep[key].split("|")) == len(HORIZONS)
    # The open-only subset is EXPLORATORY and S1-only by design.
    assert f"S_CRO_S1_20" in rep
    assert "S_CRO_S2_20" not in rep
    assert rep["S_SIGDEF"].startswith("z0=rolling390|z1=session_anchored")


def test_the_ingest_parser_decodes_what_the_battery_encodes():
    """The emitted key layout and its decoder are written in different files and
    run in different places (QC vs local), so nothing but a test keeps them
    agreeing. A silent mismatch here reads as 'the gate suppressed the
    analysis' — which is exactly what a real failure looks like."""
    import importlib.util
    import pathlib

    script = (pathlib.Path(__file__).resolve().parents[2] / "scripts"
              / "ingest_qc_signal_definition.py")
    spec = importlib.util.spec_from_file_location("ingest_sigdef", script)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    a, b = _reverting_pair(n_sessions=30, seed=33)
    grids = mod.parse_grids(pair_signal_report(a, b))
    clocks = mod.parse_clocks(pair_signal_report(a, b))

    assert set(grids["signal"]) == {"0", "1", "2", "O"}
    assert len(grids) == (3 * 3 + 1) * len(ENTRY_GRID) * len(HORIZONS)
    assert grids["t_clustered"].notna().any()
    assert set(clocks["signal"]) == {"0", "1"}

    ok, why = mod.implementation_gate(clocks, {})
    assert ok, why


def test_z2_events_are_z0_events_minus_the_open():
    a, b = _reverting_pair(n_sessions=60, seed=17)
    rep = pair_signal_report(a, b)

    def n_events(key):
        return [int(cell.split(":")[-1]) for cell in rep[key].split("|")]

    z0 = n_events("S_CR0_S1_20")
    z2 = n_events("S_CR2_S1_20")
    zo = n_events("S_CRO_S1_20")
    assert [x + y for x, y in zip(z2, zo)] == z0
