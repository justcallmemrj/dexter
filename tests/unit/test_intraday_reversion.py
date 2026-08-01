"""Controls for the intraday-reversion battery.

The point of these tests is that the tools must be able to return NO. Each
statistic is exercised against a process whose answer is known analytically:
a within-session random walk (VR == 1, no reversion), a planted AR(1) (known
half-life, VR falling in q), and a random walk contaminated by bid-ask bounce
(VR below 1 but RISING in q — the false positive this battery must not
mistake for an edge).
"""

from datetime import time

import numpy as np
import pandas as pd
import pytest

from spread_research.intraday_reversion import (
    conditional_reversion, half_life_within_session, held_position_roll_shock,
    roll_window_diagnostics, rth_frame, session_ids, subsample_within_session,
    variance_ratio, variance_ratio_curve, within_session_returns,
)
from spread_research.signals import rolling_zscore

BARS = 390
SEED = 20260801


def minute_index(n_sessions: int, bars: int = BARS) -> pd.DatetimeIndex:
    """Sessions of `bars` minute bars stamped (09:30, 16:00], weekdays only."""
    days = pd.bdate_range("2020-01-02", periods=n_sessions)
    return pd.DatetimeIndex(np.concatenate([
        (d + pd.Timedelta(minutes=571) + pd.to_timedelta(np.arange(bars), "m")
         ).values for d in days]))


def _sessionwise(n_sessions, step_fn, bars=BARS, seed=SEED):
    rng = np.random.default_rng(seed)
    idx = minute_index(n_sessions, bars)
    parts = [step_fn(rng, bars) for _ in range(n_sessions)]
    return pd.Series(np.concatenate(parts), index=idx)


def random_walk(n_sessions=250, sigma=1e-4, bars=BARS, seed=SEED):
    return _sessionwise(n_sessions,
                        lambda rng, b: np.cumsum(rng.normal(0, sigma, b)),
                        bars, seed)


def ar1_level(phi, n_sessions=250, sigma=1e-4, bars=BARS, seed=SEED):
    """Stationary AR(1) restarted each session from its stationary law."""
    def step(rng, b):
        x = np.empty(b)
        x[0] = rng.normal(0, sigma / np.sqrt(1 - phi ** 2))
        e = rng.normal(0, sigma, b)
        for i in range(1, b):
            x[i] = phi * x[i - 1] + e[i]
        return x
    return _sessionwise(n_sessions, step, bars, seed)


def bounce_walk(n_sessions=250, sigma=1e-4, half_spread=1e-4, bars=BARS, seed=SEED):
    """Random walk observed through a bid-ask bounce: efficient price plus an
    i.i.d. +/- half-spread. Negative lag-1 autocorrelation, no tradable edge."""
    def step(rng, b):
        return (np.cumsum(rng.normal(0, sigma, b))
                + half_spread * rng.choice([-1.0, 1.0], b))
    return _sessionwise(n_sessions, step, bars, seed)


# --- session plumbing ------------------------------------------------------


def test_rth_frame_keeps_390_bars_and_drops_overnight():
    idx = pd.date_range("2020-01-02 00:00", "2020-01-03 23:59", freq="min")
    s = pd.Series(1.0, index=idx)
    kept = rth_frame(s)
    per_day = kept.groupby(kept.index.normalize()).size()
    assert set(per_day) == {390}
    assert kept.index.time.min() > time(9, 30)
    assert kept.index.time.max() == time(16, 0)


def test_within_session_returns_drops_session_boundaries():
    x = random_walk(n_sessions=5)
    r = within_session_returns(x)
    assert len(r) == 5 * (BARS - 1)
    firsts = pd.Series(session_ids(x.index)).drop_duplicates().index
    assert not set(x.index[firsts]) & set(r.index)


# --- variance ratio: the three known answers -------------------------------


def test_vr_random_walk_is_one():
    curve = variance_ratio_curve(random_walk(n_sessions=400), qs=(2, 15, 60),
                                 n_boot=300)
    for _, row in curve.iterrows():
        assert row["ci_lo"] < 1.0 < row["ci_hi"], row.to_dict()
        assert abs(row["vr"] - 1.0) < 0.12, row.to_dict()


def test_vr_ar1_matches_closed_form_and_falls_with_q():
    phi = 0.99
    x = ar1_level(phi, n_sessions=400)
    curve = variance_ratio_curve(x, qs=(2, 15, 60, 120), n_boot=200)
    for _, row in curve.iterrows():
        q = int(row["q"])
        expected = (1 - phi ** q) / (q * (1 - phi))
        assert abs(row["vr"] - expected) < 0.1, (q, row["vr"], expected)
    assert curve["vr"].is_monotonic_decreasing
    assert curve["vr"].iloc[-1] < 0.75
    assert curve["p_lt_1"].iloc[-1] < 0.01


def test_vr_under_pure_bounce_is_below_one_but_FLATTENS():
    """The false positive this battery exists to catch. Bounce alone drives VR
    well below 1, so a rule that stopped at 'VR < 1' would call it an edge.
    The signature is that bounce spends its whole effect by q ~ 10 and then
    sits on a floor, whereas real reversion keeps decaying (next test)."""
    curve = variance_ratio_curve(bounce_walk(n_sessions=600),
                                 qs=(2, 30, 120), n_boot=200).set_index("q")
    assert curve.loc[2, "vr"] < 0.8
    assert curve.loc[120, "vr"] / curve.loc[30, "vr"] > 0.85   # flat tail
    assert curve.loc[120, "vr"] > 0.25                         # positive floor


def test_ar1_keeps_decaying_where_bounce_flattens():
    """The discriminator, stated as the comparison the report will make: past
    q ~ 30 the bounce curve has spent itself and the AR(1) curve has not."""
    ou = variance_ratio_curve(ar1_level(0.99, n_sessions=600), qs=(30, 120),
                              n_boot=100).set_index("q")
    bounce = variance_ratio_curve(bounce_walk(n_sessions=600), qs=(30, 120),
                                  n_boot=100).set_index("q")
    assert ou.loc[120, "vr"] / ou.loc[30, "vr"] < 0.75
    assert bounce.loc[120, "vr"] / bounce.loc[30, "vr"] > 0.85


def test_coarser_base_sampling_kills_bounce_but_not_reversion():
    """Second discriminator: bounce variance does not scale with the sampling
    interval, so subsampling walks a bounce-driven VR back toward 1."""
    b = bounce_walk(n_sessions=400)
    fine = variance_ratio(b, q=2, n_boot=200)["vr"]
    coarse = variance_ratio(subsample_within_session(b, 15), q=2, n_boot=200)["vr"]
    assert fine < 0.75
    assert coarse > fine + 0.15

    ou = ar1_level(0.99, n_sessions=400)
    ou_coarse = variance_ratio(subsample_within_session(ou, 15), q=8,
                               n_boot=200)["vr"]
    assert ou_coarse < 0.85       # survives coarsening


def test_subsample_is_session_anchored():
    x = random_walk(n_sessions=6)
    sub = subsample_within_session(x, 15)
    per = pd.Series(1, index=sub.index.normalize()).groupby(level=0).sum()
    assert set(per) == {int(np.ceil(BARS / 15))}
    with pytest.raises(ValueError):
        subsample_within_session(x, 0)


def test_vr_rejects_degenerate_q():
    with pytest.raises(ValueError):
        variance_ratio(random_walk(n_sessions=5), q=1)


def test_vr_blocks_never_straddle_a_session():
    """A q-block that spanned an overnight gap would import the gap's variance
    into the numerator and bias VR upward. Session count must bound blocks."""
    x = random_walk(n_sessions=20)
    out = variance_ratio(x, q=100, n_boot=50)
    assert out["n_blocks"] == 20 * ((BARS - 1) // 100)
    assert out["n_returns"] == 20 * (BARS - 1)


# --- half-life -------------------------------------------------------------


def test_half_life_recovers_planted_ar1():
    phi = 0.99
    got = half_life_within_session(ar1_level(phi, n_sessions=300))
    expected = -np.log(2) / np.log(phi)
    assert abs(got["half_life_bars"] - expected) / expected < 0.15


def test_half_life_is_nan_for_random_walk():
    got = half_life_within_session(random_walk(n_sessions=300))
    assert not (0 < got["half_life_bars"] < 1000)


def test_half_life_excludes_cross_session_pairs():
    x = random_walk(n_sessions=10)
    assert half_life_within_session(x)["n"] == 10 * (BARS - 1)


# --- conditional reversion -------------------------------------------------


def _events(x, entry_z=2.0, horizons=(5, 30), lookback=60):
    return conditional_reversion(x, rolling_zscore(x, lookback),
                                 entry_z=entry_z, horizons=horizons)


def test_conditional_reversion_positive_on_planted_ar1():
    out = _events(ar1_level(0.99, n_sessions=400))
    assert (out["mean_bps"] > 0).all()
    assert (out["t_clustered"] > 3).all()
    assert (out["hit_rate"] > 0.5).all()


def test_conditional_reversion_flat_on_random_walk():
    out = _events(random_walk(n_sessions=400))
    assert (out["t_clustered"].abs() < 3).all(), out.to_dict("records")


def test_conditional_reversion_never_crosses_a_session():
    """Every event must have entry and exit inside the signal's own session,
    and long horizons must drop more events than short ones."""
    x = ar1_level(0.99, n_sessions=200)
    out = conditional_reversion(x, rolling_zscore(x, 60), entry_z=2.0,
                                horizons=(5, 200, 380))
    assert out["n_dropped"].is_monotonic_increasing
    assert out.loc[out["horizon_bars"] == 380, "n_dropped"].iloc[0] > 0


def test_conditional_reversion_measures_from_the_bar_after_the_signal():
    """Known-answer check of the fill convention: the outcome must be exactly
    -sign(z_t) * (res_{t+1+k} - res_{t+1}), i.e. the signal bar's own close is
    never the entry price (no same-bar fill, no look-ahead)."""
    idx = minute_index(1)
    res = pd.Series(np.arange(len(idx), dtype=float) * 1e-4, index=idx)
    z = pd.Series(0.0, index=idx)
    t = 100
    z.iloc[t] = 3.0                       # single first-crossing at bar t
    out = conditional_reversion(res, z, entry_z=2.0, horizons=(30,),
                                min_events=1)
    assert out["n_events"].iloc[0] == 1
    expected = -1.0 * (res.iloc[t + 31] - res.iloc[t + 1]) * 1e4
    assert out["mean_bps"].iloc[0] == pytest.approx(expected)
    assert expected == pytest.approx(-30.0)   # 30 bars of +1e-4 drift, faded

    # Perturbing ONLY the signal bar must leave the outcome untouched.
    bumped = res.copy()
    bumped.iloc[t] += 5e-3
    after = conditional_reversion(bumped, z, entry_z=2.0, horizons=(30,),
                                  min_events=1)
    assert after["mean_bps"].iloc[0] == pytest.approx(expected)


def test_conditional_reversion_handles_empty_input():
    empty = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    assert conditional_reversion(empty, empty, entry_z=2.0).empty


# --- roll-window diagnostics ----------------------------------------------


def test_roll_window_diagnostics_buckets_partition_the_series():
    x = random_walk(n_sessions=60)
    z = rolling_zscore(x, 60)
    rolls = [x.index[BARS * 20], x.index[BARS * 40]]
    out = roll_window_diagnostics(x, z, rolls)
    assert out["n_bars"].sum() == len(x)
    assert "baseline" in set(out["bucket"])
    assert (out.loc[out["bucket"] != "baseline", "n_bars"] > 0).all()


def test_roll_window_diagnostics_flags_a_planted_boundary_jump():
    """Negative control for the preflight: plant a gap at the roll bar and the
    adjacent bucket's residual dispersion must exceed baseline."""
    x = random_walk(n_sessions=60)
    p = BARS * 30 + 60          # mid-session, as OUR splices are (10:30 ET)
    x.iloc[p:] += 0.02
    z = rolling_zscore(x, 60)
    out = roll_window_diagnostics(x, z, [x.index[p]]).set_index("bucket")
    assert out.loc["[0,390)", "sd_dres_bps"] > 3 * out.loc["baseline", "sd_dres_bps"]


def test_held_position_roll_shock_known_answer():
    # beta=1, legs' factors differ by 50 bp -> the held spread absorbs ~50 bp.
    got = held_position_roll_shock(1.0050, 1.0000, beta=1.0)
    assert got == pytest.approx(np.log(1.005) * 1e4, rel=1e-9)
    assert held_position_roll_shock(1.01, 1.01, beta=1.0) == pytest.approx(0.0)
