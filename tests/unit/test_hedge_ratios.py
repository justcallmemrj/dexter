import numpy as np

from spread_research import hedge_ratios as hr


def test_rolling_ols_recovers_known_beta(cointegrated_pair):
    y, x, beta_true, _ = cointegrated_pair
    beta = hr.rolling_ols_beta(y, x, window=2000, shifted=False).dropna()
    # With an autocorrelated residual (hl=50), a 2000-bar window has effective
    # n≈14 → slope se≈0.15; the endpoint is noise-bound (~3 se), the average
    # across windows must be tight.
    assert abs(beta.mean() - beta_true) < 0.05
    assert abs(beta.iloc[-1] - beta_true) < 0.5


def test_ewls_recovers_known_beta(cointegrated_pair):
    y, x, beta_true, _ = cointegrated_pair
    beta = hr.ewls_beta(y, x, halflife=2000, shifted=False).dropna()
    assert abs(beta.iloc[-1] - beta_true) < 0.1


def test_kalman_converges_to_known_beta(cointegrated_pair):
    y, x, beta_true, _ = cointegrated_pair
    beta = hr.kalman_beta(y, x, delta=1e-5, shifted=False).dropna()
    assert abs(beta.iloc[-1] - beta_true) < 0.1
    # after convergence the path should be stable, not oscillating wildly
    tail = beta.iloc[-5000:]
    assert tail.std() < 0.1


def test_robust_beta_ignores_outliers(cointegrated_pair, rng):
    y, x, beta_true, _ = cointegrated_pair
    y_corrupt = y.copy()
    # plant gross outliers in 0.5% of bars
    pos = rng.choice(len(y), size=len(y) // 200, replace=False)
    y_corrupt.iloc[pos] += rng.normal(0, 20, len(pos))
    beta = hr.rolling_robust_beta(y_corrupt, x, window=2000, step=500,
                                  shifted=False).dropna()
    # same small-sample noise as OLS applies; judge by the average and require
    # the corruption not to blow the endpoint out beyond noise bounds
    assert abs(beta.mean() - beta_true) < 0.1
    assert abs(beta.iloc[-1] - beta_true) < 0.5


def test_shifted_series_have_no_lookahead(cointegrated_pair):
    """The value reported at t must not change when data at t..end changes."""
    y, x, _, _ = cointegrated_pair
    beta_full = hr.rolling_ols_beta(y, x, window=500, shifted=True)
    cut = 10000
    beta_trunc = hr.rolling_ols_beta(y.iloc[:cut], x.iloc[:cut], window=500,
                                     shifted=True)
    # identical wherever both defined (up to the cut)
    joined = beta_full.iloc[:cut].dropna()
    assert np.allclose(joined.values, beta_trunc.dropna().values)


def test_notional_ratio_arithmetic():
    import pandas as pd
    pa = pd.Series([5000.0]); pb = pd.Series([20000.0])
    # MES ($5) vs MNQ ($2): (5000*5)/(20000*2) = 0.625 contracts of B per A...
    # ratio = notional_a / notional_b
    r = hr.notional_ratio(pa, pb, 5.0, 2.0)
    assert abs(r.iloc[0] - 0.625) < 1e-12
