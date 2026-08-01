"""Tests for the own-splice continuous constructor (D-009).

Philosophy mirrors the rest of the suite: known-answer synthetic checks,
planted-defect negative controls, and cross-checks against REAL facts
established by the QC roll audit (validation report 01).
"""

from datetime import date, time

import numpy as np
import pandas as pd
import pytest

from spread_research.contract_mapping import detect_mapping_changes
from spread_research.roll_adjustment import (
    build_continuous, index_expiry, index_roll_schedule, last_business_day_of_month,
    measure_splice_factor, parse_contract, splice_audit, third_friday,
    treasury_roll_schedule,
)

# ---------------------------------------------------------------------------
# Contract-code arithmetic — cross-checked against REAL audit-observed dates
# ---------------------------------------------------------------------------


def test_parse_contract_handles_digit_roots():
    assert parse_contract("M2KZ25") == ("M2K", 12, 2025)
    assert parse_contract("MESU19") == ("MES", 9, 2019)
    assert parse_contract("ZNH26") == ("ZN", 3, 2026)
    with pytest.raises(ValueError):
        parse_contract("MESX25")  # not a quarterly month code
    with pytest.raises(ValueError):
        parse_contract("Z25")


def test_index_expiry_matches_audit_observed_flip_dates():
    """QC's OpenInterest flip fired at expiry-day open (dte=0) — so the
    audit's index roll dates ARE third Fridays. Cross-check a sample from
    reports/machine_readable/qc_roll_audit.csv."""
    assert index_expiry("MESM19") == date(2019, 6, 21)
    assert index_expiry("M2KH23") == date(2023, 3, 17)  # MES leak date
    assert index_expiry("M2KM24") == date(2024, 6, 21)  # M2K leak date
    assert index_expiry("MYMZ24") == date(2024, 12, 20)
    assert index_expiry("MNQU25") == date(2025, 9, 19)


def test_third_friday_edge_cases():
    assert third_friday(2026, 3) == date(2026, 3, 20)
    assert third_friday(2021, 1) == date(2021, 1, 15)  # month starts Friday


def test_last_business_day_of_month():
    assert last_business_day_of_month(2025, 11) == date(2025, 11, 28)  # Fri
    assert last_business_day_of_month(2025, 8) == date(2025, 8, 29)    # Fri
    assert last_business_day_of_month(2026, 5) == date(2026, 5, 29)    # Sun->Fri


def test_index_roll_schedule_eight_days_before_expiry():
    sched = index_roll_schedule(["MESM25", "MESU25", "MESZ25"], days_before=8,
                                splice_time=time(14, 30))
    assert list(sched["from_contract"]) == ["MESM25", "MESU25"]
    assert list(sched["to_contract"]) == ["MESU25", "MESZ25"]
    # expiries 2025-06-20 / 2025-09-19 -> rolls the Thursday 8 days prior
    assert sched["timestamp"].iloc[0] == pd.Timestamp("2025-06-12 14:30", tz="UTC")
    assert sched["timestamp"].iloc[1] == pd.Timestamp("2025-09-11 14:30", tz="UTC")
    assert sched["timestamp"].iloc[0].weekday() == 3  # Thursday


def test_treasury_roll_schedule_month_end_prior_to_delivery():
    sched = treasury_roll_schedule(["ZNZ25", "ZNH26"])
    # delivery Dec 2025 -> roll last business day of Nov 2025
    assert sched["timestamp"].iloc[0].date() == date(2025, 11, 28)
    sched2 = treasury_roll_schedule(["ZTH26", "ZTM26"])
    assert sched2["timestamp"].iloc[0].date() == date(2026, 2, 27)


# ---------------------------------------------------------------------------
# Splice factors
# ---------------------------------------------------------------------------


def _minutes(start: str, n: int) -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="1min", tz="UTC")


def test_measure_splice_factor_median_robust_to_bad_print(rng):
    idx = _minutes("2025-06-12 12:00", 120)
    ts = pd.Timestamp("2025-06-12 14:30", tz="UTC")  # after the window
    old = pd.Series(5000 + rng.normal(0, 1.0, 120), idx)
    new = old * 1.0100
    new.iloc[-1] = old.iloc[-1] * 1.25   # planted bad print on the LAST bar
    f, n, method = measure_splice_factor(old, new, ts, window_bars=120,
                                         min_overlap=30)
    assert method == "median_ratio"
    assert n == 120
    assert f == pytest.approx(1.0100, abs=2e-4)  # median shrugs off the print
    # the naive last-close ratio would have been ~1.25 — the exact failure
    # mode the median guards against
    assert abs(new.iloc[-1] / old.iloc[-1] - 1.25) < 1e-9


def test_measure_splice_factor_fallback_and_failure():
    idx_old = _minutes("2025-06-12 12:00", 10)
    idx_new = _minutes("2025-06-12 13:00", 10)   # no overlap
    ts = pd.Timestamp("2025-06-12 14:30", tz="UTC")
    old = pd.Series(100.0, idx_old)
    new = pd.Series(101.0, idx_new)
    f, _, method = measure_splice_factor(old, new, ts, min_overlap=30)
    assert method == "last_close_ratio"
    assert f == pytest.approx(1.01)
    with pytest.raises(ValueError, match="no data"):
        measure_splice_factor(old.iloc[:0], new, ts)


# ---------------------------------------------------------------------------
# Continuous construction — known-answer + negative controls
# ---------------------------------------------------------------------------


def _make_segment(idx, closes):
    closes = pd.Series(closes, idx, dtype=float)
    return pd.DataFrame({
        "open": closes.values, "high": closes.values + 0.5,
        "low": closes.values - 0.5, "close": closes.values,
        "volume": 100.0,
    }, index=idx)


def _two_contract_world(gap_ratio: float, rng, n=600, roll_at=400):
    """One underlying random walk observed through two contracts; the new
    contract trades at `gap_ratio` x the old (calendar spread). Known truth:
    the spliced series must show the underlying walk's returns, not the gap."""
    idx = _minutes("2025-06-12 04:00", n)
    underlying = 5000 * np.exp(np.cumsum(rng.normal(0, 2e-4, n)))
    old = _make_segment(idx, underlying)
    new = _make_segment(idx, underlying * gap_ratio)
    ts = idx[roll_at]
    sched = pd.DataFrame([{"timestamp": ts, "from_contract": "MESM25",
                           "to_contract": "MESU25"}])
    return {"MESM25": old, "MESU25": new}, sched, idx, underlying, ts


def test_build_continuous_absorbs_gap_and_keeps_last_segment_executable(rng):
    segments, sched, idx, underlying, ts = _two_contract_world(1.0100, rng)
    cont, table = build_continuous(segments, sched)

    # factor recovered
    assert table["factor"].iloc[0] == pytest.approx(1.0100, abs=2e-4)
    assert table["method"].iloc[0] == "median_ratio"

    # the LAST segment is raw/executable: prices equal the new contract's
    after = cont.loc[cont.index >= ts, "close"]
    pd.testing.assert_series_equal(
        after, segments["MESU25"].loc[segments["MESU25"].index >= ts, "close"],
        check_names=False)

    # the splice return matches the underlying's true move, not the 1% gap
    i = list(idx).index(ts)
    true_move = underlying[i] / underlying[i - 1] - 1.0
    assert table["splice_ret_pct"].iloc[0] == pytest.approx(
        true_move * 100, abs=0.03)

    # mapped_contract column present and correct
    events = detect_mapping_changes(cont["mapped_contract"])
    assert len(events) == 1 and events["to_contract"].iloc[0] == "MESU25"

    # audit passes clean
    audit = splice_audit(cont["close"], sched, window_bars=200)
    assert not audit["artifact_flag"].any()


def test_build_continuous_three_segments_cumulative_and_return_preserving(rng):
    n = 900
    idx = _minutes("2025-03-01 04:00", n)
    underlying = 120 * np.exp(np.cumsum(rng.normal(0, 1e-4, n)))
    f1, f2 = 0.9950, 1.0080   # two calendar gaps
    segs = {
        "ZNM25": _make_segment(idx, underlying),
        "ZNU25": _make_segment(idx, underlying * f1),
        "ZNZ25": _make_segment(idx, underlying * f1 * f2),
    }
    t1, t2 = idx[300], idx[600]
    sched = pd.DataFrame([
        {"timestamp": t1, "from_contract": "ZNM25", "to_contract": "ZNU25"},
        {"timestamp": t2, "from_contract": "ZNU25", "to_contract": "ZNZ25"},
    ])
    cont, table = build_continuous(segs, sched)
    assert table["factor"].iloc[0] == pytest.approx(f1, abs=2e-4)
    assert table["factor"].iloc[1] == pytest.approx(f2, abs=2e-4)

    # earliest segment scaled by f1*f2, middle by f2, last by 1 —
    # equivalently the whole constructed series tracks underlying * f1*f2
    expected = underlying * f1 * f2
    np.testing.assert_allclose(cont["close"].values, expected, rtol=5e-4)

    # within-segment log returns preserved EXACTLY vs raw segments
    for code, lo, hi in (("ZNM25", None, t1), ("ZNU25", t1, t2), ("ZNZ25", t2, None)):
        seg = segs[code]["close"]
        piece = cont["close"]
        if lo is not None:
            seg, piece = seg[seg.index >= lo], piece[piece.index >= lo]
        if hi is not None:
            seg, piece = seg[seg.index < hi], piece[piece.index < hi]
        np.testing.assert_allclose(np.diff(np.log(piece.values)),
                                   np.diff(np.log(seg.values)), atol=1e-12)

    assert not splice_audit(cont["close"], sched, window_bars=200)[
        "artifact_flag"].any()


def test_build_continuous_provided_factors_override(rng):
    segments, sched, _, _, _ = _two_contract_world(1.0100, rng)
    cont, table = build_continuous(
        segments, sched, factors={("MESM25", "MESU25"): 1.0100})
    assert table["method"].iloc[0] == "provided"
    assert not splice_audit(cont["close"], sched, window_bars=200)[
        "artifact_flag"].any()


def test_splice_audit_flags_planted_bad_factor(rng):
    """Negative control — the QC-data failure mode reproduced: splicing with
    a WRONG factor (1.0 when the true gap is 1%) must be flagged."""
    segments, sched, _, _, _ = _two_contract_world(1.0100, rng)
    cont, table = build_continuous(
        segments, sched, factors={("MESM25", "MESU25"): 1.0})
    assert table["splice_ret_pct"].iloc[0] == pytest.approx(1.0, abs=0.1)
    audit = splice_audit(cont["close"], sched, window_bars=200)
    assert audit["artifact_flag"].all()


def test_build_continuous_validation_errors(rng):
    segments, sched, _, _, _ = _two_contract_world(1.01, rng)
    with pytest.raises(ValueError, match="missing per-contract segments"):
        build_continuous({"MESM25": segments["MESM25"]}, sched)
    bad = sched.copy()
    bad.loc[0, "from_contract"] = "MESH25"
    with pytest.raises(ValueError, match="not chained"):
        build_continuous(segments, pd.concat([sched, bad]).reset_index(drop=True))
    with pytest.raises(ValueError, match="empty roll schedule"):
        build_continuous(segments, sched.iloc[:0])


def test_constructed_series_round_trips_through_data_loader(tmp_path, rng):
    from spread_research import data_loader
    from spread_research.preview_data import save_canonical

    segments, sched, _, _, _ = _two_contract_world(1.005, rng)
    cont, _ = build_continuous(segments, sched)
    save_canonical(cont, "MES", "minute_own", data_dir=tmp_path)
    loaded = data_loader.load_local("MES", "minute_own", data_dir=tmp_path)
    assert "mapped_contract" in loaded.columns
    np.testing.assert_allclose(loaded["close"].values, cont["close"].values)
