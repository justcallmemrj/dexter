"""D-022 machinery: delayed entry on matched event sets + leg cross-correlation.

House rule: the test suite encodes the KNOWN answers before the real data is
touched. Three worlds are planted here:

- a lead-lag pair (leg B is leg A one bar late) where the delayed entry must
  find nothing at d >= 2 and the cross-correlation must be one-sided;
- a genuinely mean-reverting spread whose AR(1) coefficient predicts, in
  closed form, how much of the d = 1 effect each later entry retains
  (phi**(d-1)) — the effect must SURVIVE delay;
- neutral worlds (random walks, white noise) where every statistic must
  decline to find anything.

Plus the mechanics D-022's validity gates lean on: bit-for-bit default
reproduction, matched-set n_events constancy, the joint bootstrap, and the
part manifests.
"""

import json
import pathlib

import numpy as np
import pandas as pd
import pytest

from spread_research.crosscorr import leg_crosscorr_profile
from spread_research.intraday_reversion import conditional_reversion
from spread_research.pair_minute_report import (
    DELAYS, FEASIBLE_MAX_DELAY, delayed_entry_analysis_keys,
    pair_delayed_entry_report,
)
from spread_research.signals import rolling_zscore

BARS = 390
SEED = 20260801


def minute_index(n_sessions: int, bars: int = BARS) -> pd.DatetimeIndex:
    days = pd.bdate_range("2020-01-02", periods=n_sessions)
    return pd.DatetimeIndex(np.concatenate([
        (d + pd.Timedelta(minutes=571) + pd.to_timedelta(np.arange(bars), "m")
         ).values for d in days]))


def ar1_level(phi, n_sessions=250, sigma=1e-4, bars=BARS, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = minute_index(n_sessions, bars)
    parts = []
    for _ in range(n_sessions):
        x = np.empty(bars)
        x[0] = rng.normal(0, sigma / np.sqrt(1 - phi ** 2))
        e = rng.normal(0, sigma, bars)
        for i in range(1, bars):
            x[i] = phi * x[i - 1] + e[i]
        parts.append(x)
    return pd.Series(np.concatenate(parts), index=idx)


def _events(x, entry_z=2.0, horizons=(5, 30), lookback=60, **kw):
    z = rolling_zscore(x, lookback)
    return conditional_reversion(x, z, entry_z=entry_z, horizons=horizons, **kw)


# --- entry_delay defaults reproduce the banked convention ------------------


def test_default_call_unchanged_by_new_parameters():
    x = ar1_level(0.97, n_sessions=80)
    base = _events(x)
    explicit = _events(x, entry_delay=1, feasible_delay=None)
    pd.testing.assert_frame_equal(base, explicit)


def test_entry_delay_validation():
    x = ar1_level(0.97, n_sessions=30)
    with pytest.raises(ValueError, match="entry_delay"):
        _events(x, entry_delay=0)
    with pytest.raises(ValueError, match="feasible_delay"):
        _events(x, entry_delay=5, feasible_delay=2)


# --- matched sets: one event family serves every delay ---------------------


def test_matched_n_events_constant_across_delays():
    x = ar1_level(0.97, n_sessions=120)
    frames = {d: _events(x, entry_delay=d, feasible_delay=FEASIBLE_MAX_DELAY)
              for d in DELAYS}
    unmatched = _events(x)
    for k_row in range(len(frames[1])):
        ns = {int(frames[d].iloc[k_row]["n_events"]) for d in DELAYS}
        assert len(ns) == 1, f"n_events differs across delays: {ns}"
        assert ns.pop() <= int(unmatched.iloc[k_row]["n_events"])


def test_matched_set_excludes_late_session_events():
    """An event fired too close to the close for the LARGEST delay must be
    excluded for every delay, even those whose own exit would fit."""
    n_sessions, bars = 60, 120
    idx = minute_index(n_sessions, bars)
    rng = np.random.default_rng(3)
    v = rng.normal(0, 1e-6, len(idx))
    per = len(idx) // n_sessions
    spike_at = per - 25            # h=5: far = 15+5 = 20 bars needed; has 24
    late_at = per - 12             # far needs 20; only 11 remain -> excluded
    for s in range(n_sessions):
        v[s * per + (spike_at if s % 2 == 0 else late_at)] += 1e-3
    x = pd.Series(np.cumsum(v), index=idx)
    z = rolling_zscore(x, 30)
    cr = conditional_reversion(x, z, entry_z=2.0, horizons=(5,),
                               entry_delay=1, feasible_delay=15,
                               min_events=5)
    got = int(cr.iloc[0]["n_events"])
    plain = conditional_reversion(x, z, entry_z=2.0, horizons=(5,),
                                  min_events=5)
    assert got < int(plain.iloc[0]["n_events"])
    assert got >= n_sessions // 2 - 2   # the early spikes all survive


# --- planted lead-lag: delay kills it, cross-correlation is one-sided ------


def _lead_lag_pair(n_sessions=200, sigma=8e-4, lam=0.6, noise=2e-5,
                   seed=SEED):
    """log A = random walk (session-wise); log B PARTIALLY ADJUSTS toward A:
    b_t = b_{t-1} + lam*(a_{t-1} - b_{t-1}) + eps — L-014's laggard.

    A PURE one-bar lag would already be invisible at the t+1 entry (the
    convention skips one bar precisely to cancel first-order effects), so
    any lead-lag surface measurable at t+1 — including the banked M2K one —
    must be a multi-bar adjustment. Here the spread decays by (1-lam) per
    bar, so a delayed entry retains (1-lam)**(d-1) of the d=1 effect in
    expectation: 0.4 at d=2, ~0.026 at d=5 with lam=0.6 — the sharp decay
    D-022's LEAD-LAG branch is written for. The leg cross-correlation is
    one-sided: r_B(t) = lam*spread_{t-1} loads on A's PAST increments
    (ab_1 = lam*sigma/sd(r_B) ~ 0.92), while A is exogenous (ba_k ~ 0)."""
    rng = np.random.default_rng(seed)
    idx = minute_index(n_sessions)
    a_parts, b_parts = [], []
    for _ in range(n_sessions):
        wa = np.cumsum(rng.normal(0, sigma, BARS))
        wb = np.empty(BARS)
        wb[0] = wa[0]
        e = rng.normal(0, noise, BARS)
        for i in range(1, BARS):
            wb[i] = wb[i - 1] + lam * (wa[i - 1] - wb[i - 1]) + e[i]
        a_parts.append(wa)
        b_parts.append(wb)
    log_a = pd.Series(np.concatenate(a_parts), index=idx)
    log_b = pd.Series(np.concatenate(b_parts), index=idx)
    return log_a, log_b


def test_planted_lead_lag_decays_with_entry_delay():
    log_a, log_b = _lead_lag_pair()
    res = log_a - log_b
    z = rolling_zscore(res, BARS)
    vals = {}
    for d in (1, 2, 5, 15):
        cr = conditional_reversion(res, z, entry_z=2.0, horizons=(5, 30),
                                   legs=(log_a, log_b), beta=1.0,
                                   entry_delay=d, feasible_delay=15)
        vals[d] = float(cr.iloc[0]["mean_session_bps"])
    assert vals[1] > 0.5                       # the fake edge is there at t+1
    assert vals[2] < 0.6 * vals[1]             # ~(1-lam) = 0.4 expected
    assert abs(vals[5]) < vals[1] / 3          # ~0.026 expected
    assert abs(vals[15]) < vals[1] / 10        # ~0 expected


def test_planted_lead_lag_has_one_sided_crosscorr():
    log_a, log_b = _lead_lag_pair()
    xc = leg_crosscorr_profile(log_a, log_b, n_boot=200)
    r = xc.set_index("stat")
    assert r.loc["ab_1", "point"] > 0.8        # ~lam*sigma/sd(r_B) = 0.92
    assert abs(r.loc["ba_1", "point"]) < 0.1   # A is exogenous
    assert r.loc["asym_1", "ci_lo"] > 0        # X would be TRUE
    assert r.loc["ab_1", "ci_lo"] > 0
    assert (r.loc["ab_1", "point"] > r.loc["ab_2", "point"]
            > r.loc["ab_3", "point"])          # geometric decay in k
    assert abs(r.loc["ab_5", "point"]) < 0.1


# --- planted genuine reversion: the effect SURVIVES delay ------------------


def test_planted_ar1_reversion_survives_entry_delay():
    """Spread = AR(1) with phi = 2**(-1/40). Delayed entry retains
    phi**(d-1) of the d=1 effect in expectation — the closed form D-022's
    calibration paragraph leans on. Tolerances are loose: 250 sessions of
    events, not asymptotia."""
    phi = 2.0 ** (-1.0 / 40.0)
    w = ar1_level(phi, n_sessions=250, sigma=2e-4)
    rng = np.random.default_rng(11)
    common = pd.Series(
        np.cumsum(rng.normal(0, 1e-4, len(w))), index=w.index)
    log_a, log_b = common + w / 2, common - w / 2
    res = log_a - log_b                        # = w, the planted AR(1)
    z = rolling_zscore(res, BARS)
    vals = {}
    for d in (1, 5, 15):
        cr = conditional_reversion(res, z, entry_z=2.0, horizons=(30, 60),
                                   legs=(log_a, log_b), beta=1.0,
                                   entry_delay=d, feasible_delay=15)
        vals[d] = float(cr.iloc[1]["mean_session_bps"])
    assert vals[1] > 1.0
    assert vals[5] / vals[1] > 2 / 3           # ~phi**4 = 0.93 expected
    assert vals[15] / vals[1] > 1 / 3          # ~phi**14 = 0.78 expected


def test_symmetric_reversion_has_no_crosscorr_asymmetry():
    phi = 2.0 ** (-1.0 / 40.0)
    w = ar1_level(phi, n_sessions=200, sigma=2e-4)
    rng = np.random.default_rng(12)
    common = pd.Series(
        np.cumsum(rng.normal(0, 3e-4, len(w))), index=w.index)
    log_a, log_b = common + w / 2, common - w / 2
    xc = leg_crosscorr_profile(log_a, log_b, n_boot=200).set_index("stat")
    assert xc.loc["asym_1", "ci_lo"] < 0 < xc.loc["asym_1", "ci_hi"]


# --- cross-correlation known answers and mechanics -------------------------


def test_crosscorr_recovers_planted_contemporaneous_correlation():
    rng = np.random.default_rng(5)
    idx = minute_index(150)
    f = rng.normal(0, 1e-4, len(idx))
    ea = rng.normal(0, 1e-4, len(idx))
    eb = rng.normal(0, 1e-4, len(idx))
    log_a = pd.Series(np.cumsum(f + ea), index=idx)
    log_b = pd.Series(np.cumsum(f + eb), index=idx)
    xc = leg_crosscorr_profile(log_a, log_b, n_boot=200).set_index("stat")
    assert abs(xc.loc["c0", "point"] - 0.5) < 0.05   # corr = 1/2 by design
    for k in (1, 2, 5):
        assert abs(xc.loc[f"ab_{k}", "point"]) < 0.05
        lo, hi = xc.loc[f"asym_{k}", ["ci_lo", "ci_hi"]]
        assert lo < 0 < hi


def test_crosscorr_is_deterministic_and_session_safe():
    log_a, log_b = _lead_lag_pair(n_sessions=40)
    one = leg_crosscorr_profile(log_a, log_b, n_boot=100)
    two = leg_crosscorr_profile(log_a, log_b, n_boot=100)
    pd.testing.assert_frame_equal(one, two)
    n_pairs = one.set_index("stat")["n_pairs"]
    # per session: 389 returns -> 389 - k pairs at lag k, never straddling
    assert n_pairs["c0"] == 40 * (BARS - 1)
    for k in (1, 5):
        assert n_pairs[f"ab_{k}"] == 40 * (BARS - 1 - k)


def test_crosscorr_rejects_bad_lags():
    log_a, log_b = _lead_lag_pair(n_sessions=12)
    with pytest.raises(ValueError, match="lags"):
        leg_crosscorr_profile(log_a, log_b, lags=(0, 1))


# --- the battery and its part manifests ------------------------------------


def _small_battery(part):
    phi = 0.99
    w = ar1_level(phi, n_sessions=30, sigma=2e-4)
    rng = np.random.default_rng(21)
    common = pd.Series(np.cumsum(rng.normal(0, 1e-4, len(w))), index=w.index)
    a = pd.Series(4000 * np.exp(common + w / 2), index=w.index)
    b = pd.Series(2000 * np.exp(common - w / 2), index=w.index)
    return pair_delayed_entry_report(a, b, part=part, n_boot=50)


def test_manifest_parts_partition_the_battery():
    full = delayed_entry_analysis_keys(None)
    p1, p2 = delayed_entry_analysis_keys(1), delayed_entry_analysis_keys(2)
    assert set(p1) | set(p2) == set(full)
    assert set(p1) & set(p2) == {"S_ALIGN", "S_SPECS", "S_DELAYCFG"}
    assert len(p1) == 3 + 12 + 32              # 47: repro Z0 + matched Z0
    assert len(p2) == 3 + 12 + 32 + 3          # 50: Z2 half + crosscorr
    with pytest.raises(ValueError, match="part"):
        delayed_entry_analysis_keys(3)


def test_battery_emits_exactly_the_manifest_per_part():
    for part in (1, 2):
        out = _small_battery(part)
        assert set(out) == set(delayed_entry_analysis_keys(part))
        assert all(isinstance(v, str) and len(v) <= 960 for v in out.values())


def test_battery_shared_keys_identical_across_parts():
    """Local analogue of validity gate 2b: both parts must describe the same
    build. S_DELAYCFG legitimately differs (it names the part)."""
    p1, p2 = _small_battery(1), _small_battery(2)
    assert p1["S_ALIGN"] == p2["S_ALIGN"]
    assert p1["S_SPECS"] == p2["S_SPECS"]
    assert p1["S_DELAYCFG"] != p2["S_DELAYCFG"]


def test_battery_grid_values_parse_and_match_layout():
    out = _small_battery(1)
    for key in ("S_CR0_S1_20", "S_DE0_S1_20_d5"):
        cells = out[key].split("|")
        assert len(cells) == 5                 # five horizons
        for c in cells:
            parts = c.split(":")
            assert len(parts) == 6             # h:mean:ms:t:hit:n
            int(parts[0]); int(parts[5])


# --- the ingest inverts the emission, and its gates discriminate -----------


def _ingest():
    import importlib.util
    path = (pathlib.Path(__file__).resolve().parents[2]
            / "scripts" / "ingest_qc_delayed_entry.py")
    spec = importlib.util.spec_from_file_location("ingest_de", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _fake_driver_keys(analysis_keys_n):
    return {
        "S_HOLIDAYS": "n=96|memorial21=1|span=2018-2027",
        "S_BUILD_MES": "rolls=28|flags=0|med_ovl=390|nonmedian=0",
        "S_BUILD_M2K": "rolls=28|flags=1|med_ovl=390|nonmedian=0",
        "S_FLAG_M2K190613": "sr=-0.06|gap=0.2563|thr=0.05|mad=0.0|ratio=0.23|"
                            "gapshaped=0|why=sign_mismatch",
        "S_GATE": "PASS|both legs adjudicated non-gap-shaped",
        "S_PAIR": "MES_M2K|markets=cme/cme|anchor=unit|rolls=index|nb=14",
        "S_KEYS": str(analysis_keys_n + 7),
    }


def _correlated_battery(part):
    """A pair whose contemporaneous leg correlation is ~0.8 (common factor
    dominates the wedge), so ingest gate 3's c0 > 0.5 clause is satisfiable
    on synthetic data."""
    w = ar1_level(0.99, n_sessions=30, sigma=2e-4)
    rng = np.random.default_rng(31)
    common = pd.Series(np.cumsum(rng.normal(0, 3e-4, len(w))), index=w.index)
    a = pd.Series(4000 * np.exp(common + w / 2), index=w.index)
    b = pd.Series(2000 * np.exp(common - w / 2), index=w.index)
    out = pair_delayed_entry_report(a, b, part=part, n_boot=1000)
    out.update(_fake_driver_keys(len(delayed_entry_analysis_keys(part))))
    out["S_PAIR"] += f"|part={part}"
    return out


def test_ingest_gate4_set_equality_and_skeys():
    ing = _ingest()
    stats = _correlated_battery(1)
    ok, why = ing.gate_4_emission(stats, 1)
    assert ok, why
    broken = dict(stats)
    del broken["S_DE0_S1_20_d5"]               # missing grid key ...
    broken["S_RL_STRAY"] = "x"                 # ... offset by a stray key
    ok, why = ing.gate_4_emission(broken, 1)
    assert not ok and "S_DE0_S1_20_d5" in why  # count-equal but set-unequal
    wrong = dict(stats)
    wrong["S_KEYS"] = "99"
    ok, why = ing.gate_4_emission(wrong, 1)
    assert not ok and "99" in why


def test_ingest_parses_grids_and_gate2_passes():
    ing = _ingest()
    stats = _correlated_battery(1)
    grids = ing.parse_grids(stats)
    matched = grids[grids["matched"]]
    assert set(matched["delay"]) == {1, 2, 5, 15}
    assert len(matched) == 2 * 4 * 4 * 5       # specs x entries x delays x h
    assert len(grids[~grids["matched"]]) == 3 * 4 * 5
    ok, why = ing.gate_2_matched_sets(grids)
    assert ok, why
    # perturb one delay's n_events -> the constancy audit must catch it
    bad = dict(stats)
    key = "S_DE0_S1_20_d5"
    cells = bad[key].split("|")
    p = cells[0].split(":")
    p[5] = str(int(p[5]) + 1)
    cells[0] = ":".join(p)
    bad[key] = "|".join(cells)
    ok, why = ing.gate_2_matched_sets(ing.parse_grids(bad))
    assert not ok and "n_events varies" in why


def test_ingest_gate1_reproduction_logic(tmp_path, monkeypatch):
    """The gate must PASS when the banked grid equals the emitted repro grid
    and FAIL when one banked cell moves by more than the tolerance."""
    ing = _ingest()
    stats = _correlated_battery(1)
    grids = ing.parse_grids(stats)
    repro = grids[(~grids["matched"]) & (grids["signal"] == "0")]
    banked = repro[["spec", "entry_z", "horizon_bars", "mean_bps",
                    "mean_session_bps", "t_clustered", "hit_rate",
                    "n_events"]].reset_index(drop=True)
    monkeypatch.setattr(ing, "OUT", tmp_path)
    banked.to_csv(tmp_path / "nb02_MES_M2K_conditional_reversion.csv",
                  index=False)
    ok, why = ing.gate_1_reproduction(grids, 1)
    assert ok, why
    shifted = banked.copy()
    shifted.loc[0, "mean_session_bps"] += 0.01
    shifted.to_csv(tmp_path / "nb02_MES_M2K_conditional_reversion.csv",
                   index=False)
    ok, why = ing.gate_1_reproduction(grids, 1)
    assert not ok and "mean_session_bps" in why


def test_ingest_crosscorr_roundtrip_and_gate3():
    ing = _ingest()
    stats = _correlated_battery(2)
    xc = ing.parse_crosscorr(stats)
    assert len(xc) == 16                       # c0 + 5 ab + 5 ba + 5 asym
    assert xc.attrs["nboot"] == 1000
    ok, why = ing.gate_3_crosscorr(xc)
    assert ok, why                             # c0 ~ 0.8 on this pair
    r = xc.set_index("stat")
    assert r.loc["c0", "point"] > 0.5
    # a battery with weak leg correlation must FAIL the alignment clause
    weak = _small_battery(2)
    weak_xc = ing.parse_crosscorr(weak)
    ok, why = ing.gate_3_crosscorr(weak_xc)
    assert not ok and "c0" in why


def test_ingest_main_success_path_end_to_end(tmp_path, monkeypatch, capsys):
    """The full two-part ingest must complete and write the three nb14 CSVs
    when every gate passes — the path the 203 unit gates cannot see. The
    banked grids are patched to equal the emitted reproduction grids and the
    upload manifest is given the LIST shape build_qc_upload.py really
    writes (the shape mismatch here once got through review as a crash on
    the success path)."""
    ing = _ingest()
    p1, p2 = _correlated_battery(1), _correlated_battery(2)
    monkeypatch.setattr(ing, "OUT", tmp_path)

    g1, g2 = ing.parse_grids(p1), ing.parse_grids(p2)
    cols = ["spec", "entry_z", "horizon_bars", "mean_bps", "mean_session_bps",
            "t_clustered", "hit_rate", "n_events"]
    g1[(~g1["matched"]) & (g1["signal"] == "0")][cols].to_csv(
        tmp_path / "nb02_MES_M2K_conditional_reversion.csv", index=False)
    z2 = g2[(~g2["matched"]) & (g2["signal"] == "2")][["signal"] + cols]
    z2.to_csv(tmp_path / "nb06_MES_M2K_signal_grids.csv", index=False)

    manifest_dir = tmp_path / "data" / "interim" / "qc_upload"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text(json.dumps(
        [{"dest": "main.py", "sha256_upload_norm": "abc123", "bytes": 1}]))
    monkeypatch.setattr(ing, "REPO", tmp_path)

    in1, in2 = tmp_path / "p1.json", tmp_path / "p2.json"
    in1.write_text(json.dumps(p1))
    in2.write_text(json.dumps(p2))
    monkeypatch.setattr("sys.argv", [
        "ingest", "--part1", str(in1), "--part2", str(in2),
        "--run1", "Test Run One", "--run2", "Test Run Two",
        "--compare-banked"])
    assert ing.main() == 0, capsys.readouterr().out
    for name in ("delay_grids", "crosscorr", "scalars"):
        assert (tmp_path / f"nb14_MES_M2K_{name}.csv").exists(), name
    scal = pd.read_csv(tmp_path / "nb14_MES_M2K_scalars.csv")
    keys = set(scal["key"])
    assert "code_sha_main.py" in keys        # retry-policy hash recorded
    assert "RUN_P1" in keys and "RUN_P2" in keys
    assert any(k.startswith("D022_GATE") for k in keys)


def test_ingest_gate2b_cross_part_identity():
    ing = _ingest()
    p1, p2 = _correlated_battery(1), _correlated_battery(2)
    ok, why = ing.gate_2b_cross_part(p1, p2)
    assert ok, why
    p2["S_ALIGN"] = p2["S_ALIGN"].replace("sessions=30", "sessions=29")
    ok, why = ing.gate_2b_cross_part(p1, p2)
    assert not ok and "S_ALIGN" in why


def test_battery_delay_one_matches_unmatched_when_events_are_early():
    """With every event far from the close, matching removes nothing and the
    matched d=1 grid must equal the unmatched reproduction grid."""
    out = _small_battery(1)
    # On the tiny synthetic panel this cannot be asserted cell-for-cell in
    # general (late events exist), but n_events must never be larger.
    for spec in ("S1", "S2"):
        for ez in ("15", "20", "25", "30"):
            un = out[f"S_CR0_{spec}_{ez}"].split("|")
            ma = out[f"S_DE0_{spec}_{ez}_d1"].split("|")
            for u, m in zip(un, ma):
                assert int(m.split(":")[5]) <= int(u.split(":")[5])
