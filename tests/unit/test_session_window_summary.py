"""D-024 verdict arithmetic, pinned against the banked notebook-15 CSVs.

Same discipline as `test_program_summary.py`: every headline number in report
15 and D-025 is recomputed here from the banked evidence, so the report cannot
drift from the files it claims to describe.

The load-bearing assertion is `test_criterion_b_fails_on_every_window`. If that
ever flips, the D-025 verdict is wrong — (b) failing identically everywhere is
the entire reason the session change moved no branch.
"""

import pandas as pd
import pytest

from spread_research.session_window_summary import (
    B_BASE15_BAR, MOVE_BAR, criterion_b, d010_branch, move_factor,
    pair_summary, verdict, vr_shape,
)

PAIRS = [("ZF_ZN", "ZF", "ZN"), ("ZT_ZF", "ZT", "ZF"),
         ("ZN_ZB", "ZN", "ZB"), ("ZT_ZN", "ZT", "ZN")]
MR = "reports/machine_readable/"


def _load(tag):
    g = pd.read_csv(f"{MR}nb15_{tag}_window_grids.csv")
    v = pd.read_csv(f"{MR}nb15_{tag}_variance_ratios.csv")
    s = pd.read_csv(f"{MR}nb15_{tag}_scalars.csv").set_index("key")["value"]
    return g, v, s


def _summary(tag, a, b):
    g, v, s = _load(tag)
    return pair_summary(g, v, s, a, b)


# --- the move factor's own semantics ---------------------------------------


def test_move_factor_is_directionless():
    """A halving must count exactly as much as a doubling — the first draft of
    D-024 read a halving as '< 1.5', i.e. immaterial."""
    assert move_factor(1.0, 2.0)[0] == pytest.approx(2.0)
    assert move_factor(2.0, 1.0)[0] == pytest.approx(2.0)


def test_sign_change_is_automatically_a_move():
    f, note = move_factor(0.30, -0.10)
    assert f == float("inf") and note == "SIGN_CHANGE"
    assert move_factor(-0.30, -0.10)[1] == "UNDEFINED_non_positive"


# --- the criterion the run existed to move ---------------------------------


def test_criterion_b_fails_on_every_window_of_every_pair():
    """THE load-bearing result. A session change alters the residual, so (b)
    could have moved — and it does not: the base-sampling walk still evaporates
    to 0.81-0.96 at 15-minute bars, the L-016 tick-quantisation signature."""
    for tag, a, b in PAIRS:
        _, v, _ = _load(tag)
        for w in ("U", "R", "S", "C"):
            ok, why = criterion_b(vr_shape(v, w))
            assert not ok, f"{tag}/{w} unexpectedly passed (b): {why}"
            assert vr_shape(v, w)["base15_q2"] >= B_BASE15_BAR


def test_base_sampling_evaporation_is_unchanged_by_the_session():
    """The banked S-USED walk for ZF-ZN is 0.134 -> 0.827; every treasury-native
    window reproduces the same shape."""
    _, v, _ = _load("ZF_ZN")
    u = vr_shape(v, "U")
    assert u["base1_q30"] == pytest.approx(0.134, abs=0.001)
    assert u["base15_q2"] == pytest.approx(0.827, abs=0.001)
    for w in ("R", "S", "C"):
        s = vr_shape(v, w)
        assert 0.80 < s["base15_q2"] < 0.84
        assert s["base1_q30"] < 0.16


# --- the frozen branch table ------------------------------------------------


def test_every_window_lands_in_the_same_d010_branch():
    """No window reaches REVERSION PRESENT and none changes branch, so neither
    Q1 nor Q2 can read MATERIAL on a branch change."""
    for tag, a, b in PAIRS:
        su = _summary(tag, a, b)
        branches = set(su["d010_branch"])
        assert branches == {"AMBIGUOUS / MICROSTRUCTURE + ECONOMICALLY IMMATERIAL"}, \
            f"{tag}: {branches}"


def test_reversion_present_requires_all_three_criteria():
    assert d010_branch(True, True, True, 0.5) == "REVERSION PRESENT"
    assert "AMBIGUOUS" in d010_branch(True, True, False, 0.5)
    assert "(b)-ONLY" in d010_branch(False, False, True, 0.5)
    assert "IMMATERIAL" in d010_branch(True, True, True, 5.0)


# --- the headline numbers report 15 quotes ---------------------------------


def test_no_pair_reaches_the_move_bar():
    """Every move factor is below the pre-registered 2.0 — the session change
    is real in direction but sub-threshold in size."""
    worst = 0.0
    for tag, a, b in PAIRS:
        su = _summary(tag, a, b).dropna(subset=["move_free"])
        worst = max(worst, float(su["move_free"].max()))
        assert not su["moved"].any(), tag
    assert worst == pytest.approx(1.4286, abs=0.001)   # ZT-ZN S-CASH


def test_cost_ratios_improve_but_stay_an_order_of_magnitude_short():
    """The treasury-native session consistently helps and consistently fails to
    matter: every window is still 5.4x-11.8x below its own round trip."""
    got = {}
    for tag, a, b in PAIRS:
        su = _summary(tag, a, b).set_index("window")
        got[tag] = (float(su.loc["U", "cost_ratio"]),
                    float(su.loc["C", "cost_ratio"]))
    assert got["ZF_ZN"][0] == pytest.approx(10.85, abs=0.02)
    assert got["ZN_ZB"][0] == pytest.approx(8.81, abs=0.02)
    assert got["ZN_ZB"][1] == pytest.approx(5.61, abs=0.02)
    assert got["ZT_ZN"][1] == pytest.approx(5.57, abs=0.02)
    for tag, (u, c) in got.items():
        assert c < u, f"{tag}: S-CASH should improve the ratio"
        assert c > 5.0, f"{tag}: still an order of magnitude short"


def test_verdicts_are_immaterial_except_the_degenerate_placebo():
    """Q1 and Q2 read IMMATERIAL everywhere; ZT-ZF trips
    DISPLACEMENT-CONFOUNDED only because both its moves are ~1.01, which is the
    placebo rule's degenerate case (L-022)."""
    v = {tag: verdict(_summary(tag, a, b)) for tag, a, b in PAIRS}
    for tag in ("ZF_ZN", "ZN_ZB", "ZT_ZN"):
        assert v[tag]["Q1_L021"] == "L-021 IMMATERIAL", tag
    assert v["ZT_ZF"]["Q1_L021"].startswith("DISPLACEMENT-CONFOUNDED")
    assert v["ZT_ZF"]["placebo_move"] == pytest.approx(1.015, abs=0.001)
    assert v["ZT_ZF"]["rth_move"] == pytest.approx(1.010, abs=0.001)
    for tag, _, _ in PAIRS:
        assert v[tag]["Q2_A013"] == "A-013 IMMATERIAL", tag


def test_open_subset_does_not_reproduce_l018_on_the_cash_open():
    """D-024's falsifiable prior said L-018 implies CONTINUATION in the
    treasury pre-open. It does not: the S-CASH open subsets carry no
    significant negative cell in any pair."""
    for tag, _, _ in PAIRS:
        o = pd.read_csv(f"{MR}nb15_{tag}_open_subsets.csv")
        c = o[o["window"] == "C"]
        sig_neg = c[(c["t_clustered"] <= -3.0)]
        assert len(sig_neg) == 0, f"{tag}: {len(sig_neg)} significant negative"


def test_banked_l018_cell_still_reproduces_on_the_equity_window():
    """The one place L-018's continuation does show up is the window it was
    found on — ZF-ZN's S-USED open subset, at the banked t = -3.87."""
    o = pd.read_csv(f"{MR}nb15_ZF_ZN_open_subsets.csv")
    u = o[o["window"] == "U"]
    assert float(u["t_clustered"].min()) == pytest.approx(-3.87, abs=0.01)
    assert int((u["mean_session_bps"] < 0).sum()) == 18
