import numpy as np
import pandas as pd

from spread_research import data_validation as dv
from spread_research.contract_mapping import (bars_since_mapping_change,
                                              detect_mapping_changes,
                                              roll_exclusion_mask)
from spread_research.sensitivity import plateau_score, run_grid
from spread_research.structural_breaks import correlation_break_flags, cusum_mean_shift
from spread_research.walk_forward import acceptance_check, make_windows


def _ohlcv(n, seed=0, start="2024-01-02 14:31"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="1min", tz="UTC")
    close = 100 + np.cumsum(rng.normal(0, 0.05, n))
    return pd.DataFrame({"open": close, "high": close + 0.1, "low": close - 0.1,
                         "close": close, "volume": rng.integers(1, 100, n)}, index=idx)


def test_validation_catches_planted_defects():
    df = _ohlcv(2000)
    df.iloc[500, df.columns.get_loc("close")] = -5.0           # nonpositive
    df.loc[df.index[900]:df.index[980], "close"] = 42.0        # stale run
    df = pd.concat([df, df.iloc[[100]]]).sort_index()          # duplicate ts
    issues = dv.run_all_checks(df, "TEST")
    checks = set(issues["check"])
    assert "nonpositive_price" in checks
    assert "duplicate_timestamp" in checks
    assert "stale_price" in checks


def test_validation_flags_gaps_and_jumps():
    df = _ohlcv(2000)
    df = df.drop(df.index[300:315])                            # 15-minute hole
    df.iloc[1000, df.columns.get_loc("close")] *= 1.10         # 10% jump
    issues = dv.run_all_checks(df, "TEST")
    assert (issues["check"] == "gap").any()
    assert (issues["check"] == "abnormal_jump").any()


def test_pair_alignment_flagging():
    a, b = _ohlcv(500), _ohlcv(500).drop(_ohlcv(500).index[100:110])
    issues = dv.check_pair_alignment(a, b, "A", "B")
    assert len(issues) == 10


def test_mapping_change_detection_and_exclusion():
    idx = pd.date_range("2024-01-02", periods=1000, freq="1min", tz="UTC")
    mapped = pd.Series(["MESH24"] * 600 + ["MESM24"] * 400, idx)
    ev = detect_mapping_changes(mapped)
    assert len(ev) == 1
    assert ev.iloc[0]["from_contract"] == "MESH24"
    since = bars_since_mapping_change(mapped)
    assert since.iloc[600] == 0 and since.iloc[650] == 50
    mask = roll_exclusion_mask(idx, ev, days_before=0, warmup_bars=100,
                               mapped_contract=mapped)
    assert mask.iloc[605] and not mask.iloc[750]


def test_walk_forward_windows_no_overlap_with_embargo():
    idx = pd.date_range("2020-01-01", "2024-01-01", freq="1D")
    ws = make_windows(idx, train_months=12, test_months=3, step_months=3,
                      embargo_days=5)
    assert len(ws) > 5
    for w in ws:
        assert w.train_end + pd.Timedelta(days=5) <= w.test_start
        assert w.test_start < w.test_end


def test_acceptance_check_rules():
    good = pd.DataFrame({"pnl": [10, 8, 12, 9, -2, 11, 7, 10]})
    res = acceptance_check(good, "pnl", 0.55, 0.40)
    assert res["passes"]
    concentrated = pd.DataFrame({"pnl": [100, -5, 2, -4, 3, -2, 1, -3]})
    assert not acceptance_check(concentrated, "pnl", 0.55, 0.40)["passes"]


def test_grid_and_plateau():
    def ev(a, b):
        return {"score": -((a - 3) ** 2 + (b - 3) ** 2)}   # peak at (3,3)
    res = run_grid({"a": [1, 2, 3, 4, 5], "b": [1, 2, 3, 4, 5]}, ev)
    assert len(res) == 25 and (res["n_configs_evaluated"] == 25).all()
    ps = plateau_score(res, "score", ["a", "b"])
    assert "plateau_gap" in ps.columns


def test_structural_break_detectors():
    rng = np.random.default_rng(5)
    idx = pd.date_range("2024-01-02", periods=4000, freq="1min", tz="UTC")
    common = rng.normal(0, 1, 4000)
    ra = pd.Series(common + rng.normal(0, 0.3, 4000), idx)
    rb_corr = common + rng.normal(0, 0.3, 4000)
    rb_break = rng.normal(0, 1, 4000)                       # decorrelated
    rb = pd.Series(np.where(np.arange(4000) < 2000, rb_corr, rb_break), idx)
    flags = correlation_break_flags(ra, rb, window=300, floor=0.5)
    assert not flags.iloc[1500]
    assert flags.iloc[-1]
    # CUSUM: shift the residual mean halfway (fresh generator — reusing `rng`
    # here couples this check's noise path to the sections above)
    rng2 = np.random.default_rng(55)
    res = pd.Series(np.concatenate([rng2.normal(0, 1, 2000),
                                    rng2.normal(3, 1, 2000)]), idx)
    cs = cusum_mean_shift(res, lookback=390, threshold=10.0)
    assert not cs["alarm"].iloc[500:2000].any()   # quiet before the break
    assert cs["alarm"].iloc[2000:2200].any()      # alarms soon after it
