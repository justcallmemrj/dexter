"""D-024 machinery: the same statistics measured on five session windows.

The defects this suite exists to catch are the ones the D-024 review found by
hand, plus the one L-021 hid for seven runs:

- a session that does not open at 09:30 must NOT silently produce negative
  event-clock buckets (the `event_clock_profile` hard-coding);
- bar count must never be usable as a timezone witness — two panels an hour
  apart both give 390 bars, which is exactly how L-021 survived;
- the S-USED window must reproduce the banked computation path cell for cell,
  because that is validity gate 2's whole content;
- every window's geometry must come out at its frozen bar count.
"""

import json
import pathlib
from datetime import time

import numpy as np
import pandas as pd
import pytest

from spread_research.intraday_reversion import event_clock_profile, rth_frame
from spread_research.pair_minute_report import _conditional_block, residual_specs
from spread_research.session_window_report import (
    PART_WINDOWS, VR_WINDOWS, WINDOWS, session_window_analysis_keys,
    session_window_report,
)
from spread_research.signals import rolling_zscore

SEED = 20260801
# A synthetic "delivered day" of 07:01-16:00 in the data's own stamps — wide
# enough to contain every D-024 window including S-CASH.
DAY_OPEN, DAY_BARS = 7 * 60, 540


def _index(n_sessions: int, first_min: int = DAY_OPEN, bars: int = DAY_BARS):
    days = pd.bdate_range("2020-01-02", periods=n_sessions)
    return pd.DatetimeIndex(np.concatenate([
        (d + pd.Timedelta(minutes=first_min + 1)
         + pd.to_timedelta(np.arange(bars), "m")).values for d in days]))


def _pair(n_sessions=40, phi=0.995, seed=SEED, **kw):
    """Two legs sharing a common factor plus a stationary AR(1) wedge, so the
    hedged residual mean-reverts and the grid is populated."""
    rng = np.random.default_rng(seed)
    idx = _index(n_sessions, **kw)
    n = len(idx)
    common = np.cumsum(rng.normal(0, 1e-4, n))
    w = np.empty(n)
    w[0] = 0.0
    e = rng.normal(0, 2e-4, n)
    for i in range(1, n):
        w[i] = phi * w[i - 1] + e[i]
    a = pd.Series(110 * np.exp(common + w / 2), index=idx)
    b = pd.Series(108 * np.exp(common - w / 2), index=idx)
    return a, b


# --- the event-clock hard-coding, and its default ---------------------------


def test_event_clock_default_is_unchanged():
    """Every banked result must reproduce, so the default must still be 09:30."""
    idx = _index(6)
    z = pd.Series(np.tile(np.linspace(-3, 3, DAY_BARS), 6), index=idx)
    assert event_clock_profile(z, 2.0).equals(
        event_clock_profile(z, 2.0, open_t=time(9, 30)))


def test_event_clock_anchored_to_an_earlier_open_has_no_negative_buckets():
    """With a 07:20 session open and the old hard-coded 09:30 anchor, the
    leading bars land in NEGATIVE buckets and the profile mislabels the open."""
    a, b = _pair(n_sessions=30)
    open_t, close_t = WINDOWS["C"][1], WINDOWS["C"][2]
    fa, fb = rth_frame(a, open_t=open_t, close_t=close_t), rth_frame(b, open_t=open_t, close_t=close_t)
    df = pd.concat({"a": fa, "b": fb}, axis=1, join="inner").dropna()
    res = np.log(df["a"]) - np.log(df["b"])
    z = rolling_zscore(res, 390)

    wrong = event_clock_profile(z, 2.0)                    # old behaviour
    right = event_clock_profile(z, 2.0, open_t=open_t)     # D-024
    assert (wrong["minutes_from_open"] < 0).any(), "fixture must exercise the bug"
    assert (right["minutes_from_open"] >= 0).all()
    assert right["share"].sum() == pytest.approx(1.0)


# --- window geometry: the frozen bar counts ---------------------------------


def test_every_window_yields_its_frozen_bar_count():
    a, _ = _pair(n_sessions=10)
    for tag, (_, open_t, close_t, want) in WINDOWS.items():
        kept = rth_frame(a, open_t=open_t, close_t=close_t)
        per = kept.groupby(kept.index.normalize()).size()
        assert set(per) == {want}, f"{tag}: got {set(per)}, want {want}"


def test_windows_all_contain_the_splice_minute():
    """D-024 gate 4: 10:30 in the data's stamps must fall INSIDE every window —
    the review caught the original index control excluding it on the half-open
    left boundary."""
    for tag, (_, open_t, close_t, _) in WINDOWS.items():
        assert open_t < time(10, 30) <= close_t, tag


def test_placebo_is_displaced_but_the_same_length_as_its_references():
    """S-USED, S-HALF and S-RTH must differ ONLY in displacement, or the
    placebo does not isolate window sensitivity."""
    lengths = {t: WINDOWS[t][3] for t in ("U", "H", "R")}
    assert set(lengths.values()) == {390}
    mins = lambda t: WINDOWS[t][1].hour * 60 + WINDOWS[t][1].minute
    assert mins("U") - mins("H") == 30
    assert mins("U") - mins("R") == 60


# --- the manifest -----------------------------------------------------------


def test_parts_partition_the_manifest_and_stay_under_the_l019_ceiling():
    full = session_window_analysis_keys(None)
    parts = {p: session_window_analysis_keys(p) for p in (1, 2, 3)}
    union = set().union(*(set(v) for v in parts.values()))
    assert union == set(full)
    shared = {"S_ALIGN", "S_SPECS", "S_SESSCFG", "S_TZWIT"}
    assert set(parts[1]) & set(parts[2]) == shared
    assert set(parts[2]) & set(parts[3]) == shared
    for p, keys in parts.items():
        assert len(keys) + 8 <= 57, f"part {p}: {len(keys)} analysis keys + driver"
    with pytest.raises(ValueError, match="part"):
        session_window_analysis_keys(4)


def test_only_the_placebo_lacks_a_variance_ratio_block():
    """Criterion (b) is never read off the placebo, and IS read off the rest."""
    assert "H" not in VR_WINDOWS
    for w in ("U", "R", "S", "C"):
        assert f"S_VRA{w}" in session_window_analysis_keys(None)
    assert "S_VRAH" not in session_window_analysis_keys(None)


# --- the battery ------------------------------------------------------------


def _report(part, n_sessions=40, **kw):
    a, b = _pair(n_sessions=n_sessions)
    return session_window_report(a, b, part=part, q_grid=(2, 15), n_boot=20,
                                 legs_names=("ZF", "ZN"), **kw)


def test_report_emits_exactly_its_part_manifest():
    for part in (1, 2, 3):
        out = _report(part)
        assert set(out) == set(session_window_analysis_keys(part))
        assert all(isinstance(v, str) for v in out.values())
        assert all(len(v) <= 960 for v in out.values()), "L-019 value ceiling"


def test_shared_diagnostics_are_identical_across_parts():
    """Local analogue of the cross-part identity gate.

    Only PRE-FILTER quantities can be identity-checked. `S_ALIGN` describes the
    constructed series before any window is applied, so it must match exactly.
    `S_SESSCFG` names the part and `S_SPECS` names the window its betas came
    from, so both legitimately vary — asserting their equality would be
    asserting a bug.
    """
    p1, p2 = _report(1), _report(2)
    assert p1["S_ALIGN"] == p2["S_ALIGN"]
    assert "part=1" in p1["S_SESSCFG"] and "part=2" in p2["S_SESSCFG"]
    assert p1["S_SPECS"].endswith("win=U") and p2["S_SPECS"].endswith("win=R")


def test_geometry_keys_report_the_frozen_bar_counts():
    out = {**_report(1), **_report(2), **_report(3)}
    for w in WINDOWS:
        geo = dict(kv.split("=") for kv in out[f"S_GEO{w}"].split("|"))
        assert geo["medbars"] == geo["want"] == str(WINDOWS[w][3]), w


def test_s_used_reproduces_the_banked_computation_path():
    """Validity gate 2's local analogue: on identical bars the S-USED window
    must reproduce, cell for cell, what the notebook-02 path computes."""
    a, b = _pair(n_sessions=40)
    out = session_window_report(a, b, part=1, q_grid=(2,), n_boot=20)

    fa = rth_frame(a, open_t=WINDOWS["U"][1], close_t=WINDOWS["U"][2])
    fb = rth_frame(b, open_t=WINDOWS["U"][1], close_t=WINDOWS["U"][2])
    df = pd.concat({"a": fa, "b": fb}, axis=1, join="inner").dropna()
    log_a, log_b = np.log(df["a"]), np.log(df["b"])
    specs, info = residual_specs(log_a, log_b, anchor="vol_ratio")
    banked = _conditional_block(specs, info["betas"], (log_a, log_b),
                                (1.5, 2.0, 2.5, 3.0), (5, 15, 30, 60, 120))

    n = 0
    for key, val in banked.items():
        if not key.startswith("S_CR_"):
            continue
        mirror = key.replace("S_CR_", "S_CRU_")
        assert out[mirror] == val, f"{mirror} diverged from the banked path"
        n += 1
    assert n == 12


def test_min_blocks_witness_falls_with_the_shorter_window():
    """A 330-bar session yields fewer non-overlapping q=120 blocks than a
    390-bar one — without this witness a degenerate VR tail could be read as
    criterion (b) moving."""
    out = {**_report(1), **_report(2)}
    blocks = {}
    for w in ("U", "S"):
        geo = dict(kv.split("=") for kv in out[f"S_GEO{w}"].split("|"))
        blocks[w] = float(geo["blocks_q120"])
    assert blocks["U"] == 3.0 and blocks["S"] == 2.0


# --- the L-021 witness ------------------------------------------------------


def test_bar_count_cannot_distinguish_two_windows_an_hour_apart():
    """The reason L-021 hid for seven runs, pinned as a property."""
    a, _ = _pair(n_sessions=8)
    used = rth_frame(a, open_t=time(9, 30), close_t=time(16, 0))
    shifted = rth_frame(a, open_t=time(8, 30), close_t=time(15, 0))
    assert set(used.groupby(used.index.normalize()).size()) == {390}
    assert set(shifted.groupby(shifted.index.normalize()).size()) == {390}
    assert used.index[0].time() != shifted.index[0].time()


def test_timezone_witness_reports_the_delivered_span_not_the_count():
    """A Chicago-stamped Treasury series reads 08:31-16:00; a New-York stamped
    index series reads 09:31-17:00. That span, not the bar count, is the
    witness."""
    ct_a, ct_b = _pair(n_sessions=6, first_min=8 * 60 + 30, bars=450)
    et_a, et_b = _pair(n_sessions=6, first_min=9 * 60 + 30, bars=450)
    w_ct = session_window_report(ct_a, ct_b, part=3, q_grid=(2,), n_boot=20,
                                 legs_names=("ZF", "ZN"))["S_TZWIT"]
    w_et = session_window_report(et_a, et_b, part=3, q_grid=(2,), n_boot=20,
                                 legs_names=("MES", "MYM"))["S_TZWIT"]
    assert "ZF=08:31-16:00:450" in w_ct
    assert "MES=09:31-17:00:450" in w_et


def test_cash_coverage_measures_fill_density_of_the_undelivered_block():
    """S-CASH's 07:20-08:30 block is the part a regular-session fetch omits;
    its density is a FINDING, not a hard gate (ZT fills only ~70.7%)."""
    full, full_b = _pair(n_sessions=6)
    cov = session_window_report(full, full_b, part=3, q_grid=(2,), n_boot=20,
                                legs_names=("ZF", "ZN"))["S_CASHCOV"]
    assert "ZF=1.000" in cov and "span_min=70" in cov and "floor=0.80" in cov

    drop = ((full.index.time > time(7, 20)) & (full.index.time <= time(8, 30))
            & (np.arange(len(full)) % 2 == 0))
    cov2 = session_window_report(full[~drop], full_b[~drop], part=3,
                                 q_grid=(2,), n_boot=20,
                                 legs_names=("ZF", "ZN"))["S_CASHCOV"]
    assert 0.45 < float(cov2.split("ZF=")[1].split("|")[0]) < 0.6


# --- the ingest inverts the emission, and its gates discriminate ------------


def _ingest():
    import importlib.util
    path = (pathlib.Path(__file__).resolve().parents[2]
            / "scripts" / "ingest_qc_session_window.py")
    spec = importlib.util.spec_from_file_location("ingest_sw", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _driver_keys(n_analysis, legs=("ZF", "ZN")):
    d = {"S_HOLIDAYS": "n=96|memorial21=1|span=2018-2027",
         "S_GATE": "PASS|both legs adjudicated non-gap-shaped",
         "S_PAIR": "ZF_ZN|markets=cbot/cbot|anchor=vol_ratio|rolls=treasury|nb=15"}
    for leg in legs:
        d[f"S_BUILD_{leg}"] = "rolls=27|flags=0|med_ovl=390|nonmedian=0"
        d[f"S_FACSUM_{leg}"] = "n=27|first=0.981|last=1.014|prod=0.994"
    d["S_KEYS"] = str(n_analysis + len(d) + 1)
    return d


def _part_stats(part, first_min=8 * 60 + 30, bars=450):
    """A conforming part emission: the real battery plus driver keys."""
    a, b = _pair(n_sessions=30, first_min=first_min, bars=bars)
    out = session_window_report(a, b, part=part, q_grid=(2, 15), n_boot=20,
                                legs_names=("ZF", "ZN"))
    out.update(_driver_keys(len(out)))
    return out


def test_ingest_emission_gate_is_set_equality_not_a_count():
    ing = _ingest()
    s = _part_stats(1)
    ok, why = ing.gate_emission(s, 1, ("ZF", "ZN"), [])
    assert ok, why
    broken = dict(s)
    del broken["S_CRU_S1_20"]          # drop one grid key ...
    broken["S_STRAY"] = "x"            # ... and add a stray, keeping the count
    ok, why = ing.gate_emission(broken, 1, ("ZF", "ZN"), [])
    assert not ok and "S_CRU_S1_20" in why


def test_ingest_timezone_gate_is_part_aware():
    ing = _ingest()
    reg = _part_stats(1)
    ok, why = ing.gate_timezone(reg, ("ZF", "ZN"), 1)
    assert ok and "08:31-16:00" in why
    # the regular span is NOT acceptable for part 3 — it never delivered S-CASH
    ok, why = ing.gate_timezone(reg, ("ZF", "ZN"), 3)
    assert not ok and "07:21" in why
    ext = _part_stats(3, first_min=7 * 60, bars=540)
    ok, why = ing.gate_timezone(ext, ("ZF", "ZN"), 3)
    assert ok, why


def test_ingest_geometry_gate_catches_a_wrong_window():
    ing = _ingest()
    s = _part_stats(1)
    ok, why = ing.gate_geometry(s)
    assert ok, why
    bad = dict(s)
    bad["S_GEOU"] = bad["S_GEOU"].replace("medbars=390", "medbars=330")
    ok, why = ing.gate_geometry(bad)
    assert not ok and "S-USED" in why


def test_ingest_cash_enable_gate_detects_a_moved_factor_table():
    ing = _ingest()
    p1, p3 = _part_stats(1), _part_stats(3, first_min=7 * 60, bars=540)
    ok, why = ing.gate_cash_enable({1: p1, 3: p3}, ("ZF", "ZN"))
    assert ok, why
    p3_bad = dict(p3)
    p3_bad["S_FACSUM_ZN"] = "n=27|first=0.980|last=1.014|prod=0.994"
    ok, why = ing.gate_cash_enable({1: p1, 3: p3_bad}, ("ZF", "ZN"))
    assert not ok and "factor table moved" in why


def test_ingest_parsers_invert_the_emission():
    ing = _ingest()
    s = {**_part_stats(1), **_part_stats(2)}
    grids = ing.parse_grids(s)
    assert set(grids["window"]) == {"U", "H", "R", "S"}
    assert len(grids) == 4 * 3 * 4 * 5          # windows x specs x entries x h
    vr = ing.parse_vr(s)
    assert set(vr["window"]) == {"U", "R", "S"}  # the placebo carries no VR
    assert set(vr["series"]) == {"RES1", "RES2", "LEGA", "LEGB"}
    opens = ing.parse_open_subsets(s)
    assert set(opens["label"]) == {"EXPLORATORY_open_subset"}


def test_ingest_main_writes_nothing_when_a_gate_fails(tmp_path, monkeypatch, capsys):
    ing = _ingest()
    monkeypatch.setattr(ing, "OUT", tmp_path)
    p1, p2 = _part_stats(1), _part_stats(2)
    p1["S_GEOU"] = p1["S_GEOU"].replace("medbars=390", "medbars=331")
    f1, f2 = tmp_path / "p1.json", tmp_path / "p2.json"
    f1.write_text(json.dumps(p1)); f2.write_text(json.dumps(p2))
    monkeypatch.setattr("sys.argv", ["ingest", "--pair", "ZF_ZN",
                                     "--part1", str(f1), "--part2", str(f2),
                                     "--compare-banked"])
    assert ing.main() == 2, capsys.readouterr().out
    assert not list(tmp_path.glob("nb15_*.csv"))


def test_ingest_main_success_path_end_to_end(tmp_path, monkeypatch, capsys):
    """The path the unit gates cannot see — a crash here is exactly the class
    of bug that survived review in the notebook-14 build."""
    ing = _ingest()
    monkeypatch.setattr(ing, "OUT", tmp_path)
    p1, p2 = _part_stats(1), _part_stats(2)

    banked = ing.parse_grids(p1)
    banked = banked[banked["window"] == "U"][
        ["spec", "entry_z", "horizon_bars", "mean_bps", "mean_session_bps",
         "t_clustered", "hit_rate", "n_events"]]
    banked.to_csv(tmp_path / "nb02_ZF_ZN_conditional_reversion.csv", index=False)

    f1, f2 = tmp_path / "p1.json", tmp_path / "p2.json"
    f1.write_text(json.dumps(p1)); f2.write_text(json.dumps(p2))
    monkeypatch.setattr("sys.argv", ["ingest", "--pair", "ZF_ZN",
                                     "--part1", str(f1), "--part2", str(f2),
                                     "--runs", "RunA,RunB", "--compare-banked"])
    assert ing.main() == 0, capsys.readouterr().out
    for name in ("window_grids", "variance_ratios", "open_subsets", "scalars"):
        assert (tmp_path / f"nb15_ZF_ZN_{name}.csv").exists(), name
    scal = pd.read_csv(tmp_path / "nb15_ZF_ZN_scalars.csv")
    keys = set(scal["key"])
    assert any(k.startswith("D024_GATE") for k in keys)
    assert "D024_SCASH_ARM" in keys
    # No part 3 was supplied, so the arm was never attempted — labelling that
    # "ENABLED" would overstate what ran.
    assert scal.loc[scal["key"] == "D024_SCASH_ARM",
                    "value"].iloc[0] == "NOT-ATTEMPTED"
