"""Shared synthetic fixtures. Seeds are fixed (config: meta.random_seed) so every
test run is deterministic."""

import numpy as np
import pandas as pd
import pytest

SEED = 20260801


def make_index(n: int) -> pd.DatetimeIndex:
    return pd.date_range("2024-01-02 14:31", periods=n, freq="1min", tz="UTC")


@pytest.fixture
def rng():
    return np.random.default_rng(SEED)


@pytest.fixture
def cointegrated_pair(rng):
    """y = 2.0 * x + OU(residual, half-life 50 bars). Known ground truth:
    beta=2.0, half_life≈50. The residual scale is chosen so hedge-estimation
    noise (beta error x price level) does not swamp the OU component — a
    signal-to-noise condition real pairs must also satisfy to be researchable."""
    n = 20000
    x = 100 + np.cumsum(rng.normal(0, 0.2, n))
    hl = 50.0
    phi = np.exp(-np.log(2) / hl)
    res = np.zeros(n)
    eps = rng.normal(0, 0.5, n)
    for t in range(1, n):
        res[t] = phi * res[t - 1] + eps[t]
    y = 2.0 * x + res
    idx = make_index(n)
    return pd.Series(y, idx, name="y"), pd.Series(x, idx, name="x"), 2.0, hl


@pytest.fixture
def random_walk_pair(rng):
    """Two INDEPENDENT random walks — the negative control. No cointegration,
    no mean reversion; the framework must not find any."""
    n = 20000
    a = 100 + np.cumsum(rng.normal(0, 0.05, n))
    b = 100 + np.cumsum(rng.normal(0, 0.05, n))
    idx = make_index(n)
    return pd.Series(a, idx, name="a"), pd.Series(b, idx, name="b")
