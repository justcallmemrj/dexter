"""Notebook-13 aggregation: does the banked evidence still say what reports 02
and 03 say it says?

These tests are not statistics tests — `intraday_reversion` owns those. They are
a RECONCILIATION: every headline figure quoted in the two validation reports is
recomputed here from the machine-readable CSVs those runs emitted. A failure
means a report and its own evidence have drifted apart, which is the one way a
negative program conclusion could quietly become wrong.

The synthetic tests at the bottom pin the parsing and cost arithmetic against
inputs with known answers, so the readers cannot be "verified" by the same
transcription error twice.
"""

import math
from pathlib import Path

import pandas as pd
import pytest

from spread_research.program_summary import (
    HONEST_SPECS, PAIRS, REGISTRY, TICK_BPS, grid_counts, largest_honest_effect,
    leg_vr, matched_elapsed_vr, open_clustering, pair_cost_bps, pair_row,
    parse_fields, program_table, program_totals, read_conditional,
    read_scalars, read_variance_ratio, round_trip_spread_bps, s1_positive_cells,
)

MR = Path(__file__).resolve().parents[2] / "reports" / "machine_readable"

pytestmark = pytest.mark.skipif(
    not (MR / "nb02_MES_MYM_scalars.csv").exists(),
    reason="banked notebook-02/03 artifacts not present",
)


# --- the numbers validation reports 02 and 03 put their names to ------------

# pair -> (S1 cells positive at t>=3, largest honest effect bps, its t)
# Sources: report 02 §3/§11.2/§12.2 and report 03 §1.
PUBLISHED_EFFECT = {
    "MES_MYM": (0, 1.410, 1.93),
    "MES_MNQ": (0, 1.781, 2.84),
    "MES_M2K": (8, 6.305, 5.31),
    "ZF_ZN": (20, 0.286, 6.59),
    "ZT_ZF": (20, 0.202, 6.88),
    "ZN_ZB": (20, 0.664, 6.49),
    "ZT_ZN": (16, 0.166, 4.07),
}

# pair -> residual VR at matched ~30 min elapsed, base 1 / 5 / 15 min.
# Sources: report 02 §4/§11.3/§12.3, report 03 §3.
PUBLISHED_VR_WALK = {
    "MES_MYM": (0.756, 0.852, 0.950),
    "MES_MNQ": (0.928, 0.941, 0.983),
    "MES_M2K": (0.813, 0.897, 0.956),
    "ZF_ZN": (0.134, 0.467, 0.827),
    "ZT_ZF": (0.241, 0.623, 0.904),
    "ZN_ZB": (0.208, 0.594, 0.893),
    "ZT_ZN": (0.322, 0.712, 0.963),
}

# Treasury round-trip costs, report 03 §1/§2, and the L-013 open-clustering
# shares, report 02 §6.4/§11.5/§12.5 and report 03 §6.3.
PUBLISHED_COST = {"ZF_ZN": 3.10, "ZT_ZF": 1.41, "ZN_ZB": 5.85, "ZT_ZN": 1.50}
PUBLISHED_OPEN_SHARE = {
    "MES_MYM": 0.243, "MES_MNQ": 0.247, "MES_M2K": 0.227,
    "ZF_ZN": 0.127, "ZT_ZF": 0.133, "ZN_ZB": 0.136, "ZT_ZN": 0.133,
}
# Report 03 §6.3 quotes the treasury shares as a 12.7-13.6% RANGE rather than
# per pair; the per-pair values above are read off the banked event clocks and
# must stay inside that published range.
TREASURY_OPEN_RANGE = (0.127, 0.136)


@pytest.mark.parametrize("pair", PAIRS)
def test_effect_sizes_match_the_published_reports(pair):
    cond = read_conditional(pair, MR)
    n_pos, n_cells = s1_positive_cells(cond)
    best = largest_honest_effect(cond)
    pub_pos, pub_bps, pub_t = PUBLISHED_EFFECT[pair]
    assert n_cells == 20, "the S1 grid is 4 entry thresholds x 5 horizons"
    assert n_pos == pub_pos
    assert best["mean_session_bps"] == pytest.approx(pub_bps, abs=0.005)
    assert best["t_clustered"] == pytest.approx(pub_t, abs=0.02)


@pytest.mark.parametrize("pair", PAIRS)
def test_base_sampling_walk_matches_the_published_reports(pair):
    walk = matched_elapsed_vr(read_variance_ratio(pair, MR))
    pub = PUBLISHED_VR_WALK[pair]
    assert (walk[1], walk[5], walk[15]) == pytest.approx(pub, abs=0.002)
    # Criterion (b) failed for every pair: the residual VR always walks UP
    # toward 1 as the base bar coarsens. If a pair ever walks the other way,
    # that is a real result and this test should be the thing that says so.
    assert walk[15] > walk[1]


@pytest.mark.parametrize("pair", PAIRS)
def test_open_clustering_matches_and_is_an_equity_open_artifact(pair):
    share = open_clustering(read_scalars(pair, MR))
    assert share == pytest.approx(PUBLISHED_OPEN_SHARE[pair], abs=0.002)
    # L-013: index pairs cluster at the equity open, treasuries do not.
    if REGISTRY[pair].asset_class == "index":
        assert share > 0.20
    else:
        lo, hi = TREASURY_OPEN_RANGE
        assert lo <= share <= hi


@pytest.mark.parametrize("pair", ["ZF_ZN", "ZT_ZF", "ZN_ZB", "ZT_ZN"])
def test_treasury_costs_reproduce_from_verified_tick_specs(pair):
    cost, basis = pair_cost_bps(pair, read_scalars(pair, MR))
    assert cost == pytest.approx(PUBLISHED_COST[pair], abs=0.02)
    assert "spec-derived" in basis


@pytest.mark.parametrize("pair", PAIRS)
def test_no_pair_is_tradable_at_intraday_horizon(pair):
    """D-018 restated as an assertion. The two ways a pair could have advanced
    were a positive look-ahead-safe surface that survives coarsening, or an
    effect that clears its own cost. Neither happened anywhere."""
    row = pair_row(pair, MR)
    if REGISTRY[pair].asset_class == "treasury":
        assert row["effect_over_cost"] < 1.0, "treasury effects are below cost"
    assert row["verdict"] != "REVERSION PRESENT"
    assert row["gate"] == "PASS", "every verdict rests on a passed data gate"


def test_index_pairs_significant_cells_point_at_continuation():
    """The falsified pairs did not merely fail to revert — where they are
    significant they CONTINUE (report 02 §3, §11.2)."""
    for pair in ("MES_MYM", "MES_MNQ"):
        counts = grid_counts(read_conditional(pair, MR))
        assert counts["significant"] > 0
        assert counts["significant_positive"] == 0
        assert counts["significant_negative"] == counts["significant"]


def test_m2k_leg_variance_ratio_is_above_one():
    """Near-miss #2, the tell that the cost-clearing MES-M2K surface was a
    lagging leg catching up rather than a pair relationship (L-014)."""
    legs = leg_vr(read_variance_ratio("MES_M2K", MR), q=2)
    assert legs["LEGB"] > 1.0                      # M2K, lagged adjustment
    assert legs["LEGA"] < 1.0                      # MES, ordinary bounce


def test_program_table_and_totals():
    table = program_table(root=MR)
    assert list(table["pair"]) == list(PAIRS)
    totals = program_totals(table)
    assert totals["pairs_tested"] == 7
    assert totals["gates_passed"] == 7
    assert totals["pairs_reversion_present"] == 0
    assert totals["cells_examined"] == 420        # 7 pairs x 60 cells
    assert totals["pairs_effect_clears_cost"] == 1  # MES-M2K only, and (b) failed
    assert 660_000 < totals["bars_min"] <= totals["bars_max"] < 700_000


# --- parsing and arithmetic, on inputs whose answers are known -------------

def test_parse_fields_handles_named_and_positional_fragments():
    assert parse_fields("PASS|both legs adjudicated") == {
        "0": "PASS", "1": "both legs adjudicated"}
    assert parse_fields("bars=10|sessions=2") == {"bars": "10", "sessions": "2"}


def test_round_trip_cost_is_two_crossings_weighted_by_the_hedge():
    # One tick each leg, in and out, leg B scaled by beta.
    expected = 2.0 * (TICK_BPS["ZF"] + 0.583 * TICK_BPS["ZN"])
    assert round_trip_spread_bps("ZF", "ZN", 0.583) == pytest.approx(expected)
    # Report 03 §2's per-tick bps table, to the precision it was printed at.
    assert TICK_BPS["ZT"] == pytest.approx(0.38, abs=0.005)
    assert TICK_BPS["ZF"] == pytest.approx(0.72, abs=0.005)
    assert TICK_BPS["ZN"] == pytest.approx(1.42, abs=0.005)
    assert TICK_BPS["ZB"] == pytest.approx(2.72, abs=0.005)


def test_thin_second_leg_notionals_are_absent_on_purpose():
    """MNQ and M2K have no representative notional established in this repo, so
    no spec-derived cost may be quoted for them (report 02 §5 band instead)."""
    assert "MNQ" not in TICK_BPS and "M2K" not in TICK_BPS


def test_largest_honest_effect_ignores_the_look_ahead_spec():
    cond = pd.DataFrame({
        "spec": ["S1", "S2", "S3"],
        "entry_z": [2.0, 2.0, 2.0],
        "horizon_bars": [30, 30, 30],
        "mean_bps": [0.1, 0.2, 9.9],
        "mean_session_bps": [0.1, 0.2, 9.9],
        "t_clustered": [1.0, 1.5, 12.0],
        "hit_rate": [0.5, 0.5, 0.6],
        "n_events": [10, 10, 10],
    })
    assert largest_honest_effect(cond)["spec"] in HONEST_SPECS
    assert largest_honest_effect(cond)["mean_session_bps"] == 0.2
    assert grid_counts(cond)["significant"] == 0


def test_matched_elapsed_picks_matched_time_not_matched_q():
    vr = pd.DataFrame({
        "series": ["RES1"] * 4,
        "base_step_min": [1, 1, 15, 15],
        "q": [2, 30, 2, 15],
        "vr": [0.5, 0.6, 0.9, 0.99],
        "ci_lo": [math.nan] * 4, "ci_hi": [math.nan] * 4, "p_lt_1": [0.0] * 4,
    })
    walk = matched_elapsed_vr(vr, base_steps=(1, 15))
    assert walk[1] == 0.6            # 1 x 30 = 30 minutes
    assert walk[15] == 0.9           # 15 x 2 = 30 minutes, not q = 15
