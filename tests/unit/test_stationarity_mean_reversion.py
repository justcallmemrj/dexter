import numpy as np
import pandas as pd

from spread_research import mean_reversion as mr
from spread_research import stationarity as st
from spread_research.hedge_ratios import rolling_ols_beta
from spread_research.pair_builder import build_residual


def _ou(rng, n, hl, sigma=0.03):
    phi = np.exp(-np.log(2) / hl)
    res = np.zeros(n)
    eps = rng.normal(0, sigma, n)
    for t in range(1, n):
        res[t] = phi * res[t - 1] + eps[t]
    idx = pd.date_range("2024-01-02", periods=n, freq="1min", tz="UTC")
    return pd.Series(res, idx)


def test_ou_series_is_stationary(rng):
    s = _ou(rng, 10000, hl=50)
    v = st.stationarity_verdict(s)
    # KPSS can be marginal on strongly autocorrelated stationary series; both
    # labels count as evidence of stationarity, 'ambiguous' does not
    assert v["verdict"] in ("stationary", "stationary_marginal")


def test_random_walk_is_not_stationary(rng):
    rw = pd.Series(np.cumsum(rng.normal(0, 1, 10000)),
                   pd.date_range("2024-01-02", periods=10000, freq="1min", tz="UTC"))
    v = st.stationarity_verdict(rw)
    assert not v["verdict"].startswith("stationary")   # negative control


def test_engle_granger_positive_and_negative(cointegrated_pair, random_walk_pair):
    y, x, _, _ = cointegrated_pair
    assert st.engle_granger(y, x)["cointegrated_5pct"]
    a, b = random_walk_pair
    assert not st.engle_granger(a, b)["cointegrated_5pct"]


def test_half_life_recovers_known_value(rng):
    hl_true = 50.0
    s = _ou(rng, 30000, hl=hl_true)
    est = mr.half_life_ar1(s)["half_life_bars"]
    assert abs(est - hl_true) / hl_true < 0.25   # 25% tolerance at n=30k


def test_half_life_nan_on_random_walk(rng):
    rw = pd.Series(np.cumsum(rng.normal(0, 1, 20000)),
                   pd.date_range("2024-01-02", periods=20000, freq="1min", tz="UTC"))
    est = mr.half_life_ar1(rw)
    # b should be ~0; half-life either NaN or absurdly large — must not look tradable
    assert not (0 < est["half_life_bars"] < 1000)


def test_ou_fit(rng):
    s = _ou(rng, 30000, hl=100)
    fit = mr.fit_ou(s)
    assert abs(fit["half_life_bars"] - 100) / 100 < 0.3
    assert abs(fit["mu"]) < 0.05


def test_convergence_study_on_ou(rng):
    s = _ou(rng, 30000, hl=50)
    z = (s - s.mean()) / s.std()
    ev = mr.convergence_study(z, entry_z=2.0, horizon_bars=500, exit_z=0.25)
    assert len(ev) > 10
    # OU with hl=50 should overwhelmingly converge within 10 half-lives
    assert ev["converged"].mean() > 0.9


def test_residual_pipeline_end_to_end(rng):
    """Wiring test: with a KNOWN (slowly drifting) hedge ratio, build_residual +
    half_life_ar1 recover the true half-life, and a wrong hedge does not.

    NOTE (research caution, logged as L-007): when beta must be ESTIMATED, the
    error (beta_hat - beta) * price_level contaminates the residual with a slow
    random walk and inflates measured half-life. That contamination ratio is
    independent of the residual's own volatility — it must be quantified on real
    data (notebooks 04/05), which is why this test injects the true beta instead
    of pretending estimation noise away with a lucky seed.
    """
    n = 20000
    hl_true = 50.0
    idx = pd.date_range("2024-01-02", periods=n, freq="1min", tz="UTC")
    x = pd.Series(100 + np.cumsum(rng.normal(0, 0.2, n)), idx)
    beta_true = pd.Series(2.0 + 0.3 * np.sin(np.arange(n) / 3000.0), idx)
    phi = np.exp(-np.log(2) / hl_true)
    ou = np.zeros(n)
    eps = rng.normal(0, 0.5, n)
    for t in range(1, n):
        ou[t] = phi * ou[t - 1] + eps[t]
    y = beta_true * x + ou

    res = build_residual(y, x, beta_true.shift(1), use_log=False)
    est = mr.half_life_ar1(res.iloc[100:])
    assert 0.5 * hl_true < est["half_life_bars"] < 2.0 * hl_true

    # wrong constant hedge leaves a random-walk component → no usable reversion
    res_bad = build_residual(y, x, pd.Series(1.0, idx), use_log=False)
    est_bad = mr.half_life_ar1(res_bad.iloc[100:])
    hl_bad = est_bad["half_life_bars"]
    assert (hl_bad != hl_bad) or hl_bad > 10 * hl_true
