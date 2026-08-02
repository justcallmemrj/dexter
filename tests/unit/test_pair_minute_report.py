"""End-to-end exercise of the notebook-02 report body on synthetic pairs.

This is the dry run that keeps typos out of QuantConnect: the same function the
QC driver calls is executed here against series whose answer is known. Two
worlds are tested — a pair whose hedged residual really does revert, and a pair
of independent random walks where the honest answer is "nothing here".
"""

import numpy as np
import pandas as pd
import pytest

from spread_research.pair_minute_report import (
    fmt, pair_minute_report, residual_specs, rolling_beta,
    rolling_ols_residual, vol_ratio_beta,
)

BARS = 390
SESSIONS = 120


def _index(n_sessions=SESSIONS):
    days = pd.bdate_range("2020-01-02", periods=n_sessions)
    return pd.DatetimeIndex(np.concatenate([
        (d + pd.Timedelta(minutes=571) + pd.to_timedelta(np.arange(BARS), "m")
         ).values for d in days]))


def _pair(reverting: bool, seed=7, phi=0.99):
    """Leg A = common factor. Leg B = same factor plus, optionally, a
    stationary AR(1) wedge so that log(A) - log(B) mean-reverts."""
    rng = np.random.default_rng(seed)
    idx = _index()
    n = len(idx)
    common = np.cumsum(rng.normal(0, 1e-4, n))
    if reverting:
        w = np.empty(n)
        w[0] = 0.0
        e = rng.normal(0, 1e-4, n)
        for i in range(1, n):
            w[i] = phi * w[i - 1] + e[i]
    else:
        w = np.cumsum(rng.normal(0, 1e-4, n))
    a = pd.Series(4000 * np.exp(common), index=idx)
    b = pd.Series(30000 * np.exp(common - w), index=idx)
    return a, b


def _rolls(idx, k=3):
    return [idx[len(idx) * (i + 1) // (k + 1)] for i in range(k)]


def _factors(rolls, vals):
    return pd.Series(vals, index=pd.DatetimeIndex(rolls))


def _report(reverting, **kw):
    a, b = _pair(reverting)
    rolls = _rolls(a.index)
    return pair_minute_report(
        a, b, roll_timestamps=rolls,
        factors_a=_factors(rolls, [1.001, 1.002, 1.0005]),
        factors_b=_factors(rolls, [1.0005, 1.0018, 1.0009]),
        n_boot=60, q_grid=(2, 15, 60), entry_grid=(2.0,),
        horizons=(5, 30), **kw)


# --- shape of the emitted payload -----------------------------------------


def test_report_emits_parseable_keys_within_the_qc_ceiling():
    out = _report(True)
    assert 10 < len(out) <= 110                      # summary-statistic ceiling
    assert all(k.startswith("S_") for k in out)
    assert all(isinstance(v, str) and len(v) <= 960 for v in out.values())
    for k in ("S_ALIGN", "S_BETA", "S_HL", "S_CLOCK", "S_PF_SHOCK",
              "S_PF_NROLLS", "S_CR_S1_20", "S_CR_S2_20", "S_CR_S3_20",
              "S_VR_RES1_s1", "S_VR_RES1_s15", "S_VR_LEGA_s1", "S_VR_LEGB_s1"):
        assert k in out, k


def test_align_key_reports_390_bar_sessions():
    kv = dict(p.split("=", 1) for p in _report(True)["S_ALIGN"].split("|"))
    assert kv["medbars"] == "390"
    assert int(kv["sessions"]) == SESSIONS
    assert kv["dropA"] == "0" and kv["dropB"] == "0"


def test_conditional_rows_carry_every_horizon():
    row = _report(True)["S_CR_S1_20"]
    horizons = [int(cell.split(":")[0]) for cell in row.split("|")]
    assert horizons == [5, 30]
    # layout: horizon:mean_bps:mean_session_bps:t_clustered:hit_rate:n_events
    assert all(len(cell.split(":")) == 6 for cell in row.split("|"))


def test_fmt_preserves_nan_instead_of_inventing_a_number():
    assert fmt(float("nan")) == "nan"
    assert fmt(None) == "nan"
    assert fmt("abc") == "nan"
    assert fmt(1.23456, 2) == "1.23"


# --- the battery must be able to say "nothing here" ------------------------


def test_independent_walks_produce_no_reversion_signal():
    """The negative control that matters: two unrelated random walks must not
    clear the D-010 bar. Their residual is itself a random walk, so the
    conditional statistic should be insignificant and VR should sit near 1."""
    out = _report(False)
    cells = [c.split(":") for c in out["S_CR_S1_20"].split("|")]
    tstats = [abs(float(c[3])) for c in cells if c[3] != "nan"]
    assert tstats and max(tstats) < 3.0, out["S_CR_S1_20"]

    vr = {int(c.split(":")[0]): float(c.split(":")[1])
          for c in out["S_VR_RES1_s1"].split("|")}
    assert all(0.85 < v < 1.15 for v in vr.values()), vr


def test_reverting_pair_is_detected_with_the_expected_signs():
    out = _report(True)
    for spec in ("S1", "S2", "S3"):
        cells = [c.split(":") for c in out[f"S_CR_{spec}_20"].split("|")]
        assert all(float(c[1]) > 0 for c in cells), spec   # fade pays, in bps
        assert all(float(c[2]) > 0 for c in cells), spec   # session-mean agrees
        # Reversion should build with horizon toward the planted half-life,
        # so the long horizon carries the evidence, not the 5-bar one.
        assert float(cells[-1][3]) > 4.0, (spec, cells)
        assert float(cells[-1][1]) > float(cells[0][1]), (spec, cells)

    vr = {int(c.split(":")[0]): float(c.split(":")[1])
          for c in out["S_VR_RES1_s1"].split("|")}
    assert vr[60] < vr[15] < 1.05                    # keeps decaying with q
    assert vr[60] < 0.9

    # Planted half-life is -ln2/ln(0.99) ~ 69 bars; the estimator must find it.
    hl = dict(p.split("=", 1) for p in out["S_HL"].split("|"))
    assert abs(float(hl["raw_hl"]) - 69.0) / 69.0 < 0.2


def test_leg_baseline_is_reported_and_looks_like_a_random_walk():
    """Legs share the common random-walk factor, so their own VR must sit near
    1 — that is what makes them a usable bounce baseline for the residual."""
    out = _report(True)
    for tag in ("LEGA", "LEGB"):
        vr = {int(c.split(":")[0]): float(c.split(":")[1])
              for c in out[f"S_VR_{tag}_s1"].split("|")}
        assert all(0.85 < v < 1.15 for v in vr.values()), (tag, vr)


# --- specs and preflight ---------------------------------------------------


def test_residual_specs_are_look_ahead_safe_where_they_claim_to_be():
    a, b = _pair(True)
    la, lb = np.log(a), np.log(b)
    specs, info = residual_specs(la, lb, beta_lookback=200)
    # S2's beta at t must not move when data at t (or later) changes.
    bumped = lb.copy()
    bumped.iloc[500:] += 0.05
    beta_ref = rolling_beta(la, lb, 200)
    beta_new = rolling_beta(la, bumped, 200)
    assert beta_ref.iloc[:500].equals(beta_new.iloc[:500])
    assert set(specs) == {"S1", "S2", "S3"}
    assert np.isfinite(info["beta_static"])


def test_preflight_shock_is_reported_in_bps_and_matches_the_factors():
    out = _report(True)
    kv = dict(p.split("=", 1) for p in out["S_PF_SHOCK"].split("|"))
    assert kv["units"] == "bps_of_S1_residual"
    assert int(kv["n"]) == 3
    # First roll: factors 1.001 vs 1.0005 -> ~5 bps of residual level shift.
    first = float(out["S_PF_SH0"].split("|")[0].split(":")[1])
    assert abs(abs(first) - (np.log(1.001) - np.log(1.0005)) * 1e4) < 0.15


def test_preflight_buckets_cover_the_series_and_include_baseline():
    out = _report(True)
    buckets = {k for k in out if k.startswith("S_PF_[")}
    assert len(buckets) == 6
    assert "S_PF_baseline" in out
    total = sum(int(dict(p.split("=", 1) for p in out[k].split("|"))["n"])
                for k in list(buckets) + ["S_PF_baseline"])
    kv = dict(p.split("=", 1) for p in out["S_ALIGN"].split("|"))
    assert total == int(kv["bars"])


def test_empty_overlap_is_reported_not_crashed():
    idx = _index(3)
    a = pd.Series(1.0, index=idx)
    b = pd.Series(1.0, index=idx + pd.Timedelta(days=400))
    out = pair_minute_report(a, b, roll_timestamps=[],
                             factors_a=pd.Series(dtype=float),
                             factors_b=pd.Series(dtype=float), n_boot=10)
    assert out["S_ALIGN"].startswith("EMPTY")


def test_omitting_the_ols_intercept_would_manufacture_hedge_noise():
    """Regression guard for the L-011 fix. On log PRICES the no-intercept form
    y - beta*x scales every beta wobble by log(x) ~ 10.5 for MYM, so it must be
    dramatically noisier than the residual around the full fitted line. If this
    ever inverts, the specification has silently regressed."""
    a, b = _pair(True)
    la, lb = np.log(a), np.log(b)
    proper = rolling_ols_residual(la, lb, 1950)
    naive = (la - rolling_beta(la, lb, 1950) * lb).dropna()
    assert naive.std() > 20 * proper.std()
    assert proper.std() < 0.05          # residual stays in a sane bps range


# --- treasury anchor: volatility-ratio hedge (notebook 03) ------------------


def test_vol_ratio_beta_recovers_a_planted_volatility_ratio():
    """beta must equal sigma_a/sigma_b, independent of price level or
    multiplier — that is the whole point of the log-space derivation."""
    rng = np.random.default_rng(3)
    idx = _index()
    n = len(idx)
    for ratio, pa, pb in ((0.4, 110.0, 130.0), (2.5, 4000.0, 110.0)):
        a = pd.Series(pa * np.exp(np.cumsum(rng.normal(0, ratio * 1e-4, n))), index=idx)
        b = pd.Series(pb * np.exp(np.cumsum(rng.normal(0, 1e-4, n))), index=idx)
        beta = vol_ratio_beta(np.log(a), np.log(b), 1950).dropna()
        assert abs(beta.median() - ratio) / ratio < 0.10, (ratio, beta.median())


def test_vol_ratio_beta_is_look_ahead_safe():
    a, b = _pair(True)
    la, lb = np.log(a), np.log(b)
    ref = vol_ratio_beta(la, lb, 500)
    bumped = lb.copy()
    bumped.iloc[3000:] *= 1.01
    assert ref.iloc[:3000].equals(vol_ratio_beta(la, bumped, 500).iloc[:3000])


def test_vol_ratio_beta_ignores_overnight_gaps():
    """An overnight jump must not inflate either leg's volatility estimate."""
    a, b = _pair(True)
    la, lb = np.log(a), np.log(b)
    clean = vol_ratio_beta(la, lb, 500)
    # A real overnight gap PERSISTS: step the level up at each session open and
    # keep it there, so only the boundary return changes and every
    # within-session return is untouched.
    starts = np.flatnonzero(np.r_[True, np.diff(la.index.normalize().values.astype("int64")) != 0])
    step = pd.Series(0.0, index=la.index)
    step.iloc[starts[5:]] = 0.02
    jumped = la + step.cumsum()
    assert vol_ratio_beta(jumped, lb, 500).iloc[-1] == pytest.approx(clean.iloc[-1], rel=1e-9)


def test_treasury_anchor_produces_a_centered_residual():
    """The vol-ratio spec must go through centered_residual, or a drifting beta
    times log(price) manufactures the L-011 artifact all over again."""
    a, b = _pair(True)
    la, lb = np.log(a), np.log(b)
    specs, info = residual_specs(la, lb, beta_lookback=500, anchor="vol_ratio")
    assert info["anchor"] == "vol_ratio"
    assert not (info["betas"]["S1"] == 1.0).all()
    naive = (la - info["betas"]["S1"] * lb).dropna()
    assert naive.std() > 20 * specs["S1"].std()
    assert abs(specs["S1"].mean()) < 5 * specs["S1"].std()


def test_unknown_anchor_is_rejected():
    a, b = _pair(True)
    with pytest.raises(ValueError):
        residual_specs(np.log(a), np.log(b), anchor="dv01")


def test_report_records_which_anchor_was_used():
    for anchor, tag in (("unit", "log_ratio_beta1"),
                        ("vol_ratio", "vol_ratio_sigma_a_over_sigma_b")):
        out = _report(True, anchor=anchor)
        assert out["S_SPECS"].startswith(f"anchor={anchor}|S1={tag}")
