"""Mean-reversion characterization: half-life, OU parameters, convergence stats
(mandate notebooks 05/06)."""

from __future__ import annotations

import numpy as np
import pandas as pd


def half_life_ar1(residual: pd.Series) -> dict:
    """Half-life from the AR(1)/discrete-OU regression
    d_res_t = a + b * res_{t-1} + e_t  →  half_life = -ln(2)/ln(1+b).

    Returns NaN half-life when b >= 0 (no mean reversion). Units = bars of the
    input series; caller is responsible for stating bar size.
    """
    r = residual.dropna()
    lag = r.shift(1).dropna()
    d = r.diff().dropna()
    lag, d = lag.align(d, join="inner")
    if len(d) < 30:
        return {"b": np.nan, "half_life_bars": np.nan, "n": len(d)}
    x = np.vstack([np.ones(len(lag)), lag.values]).T
    coef, *_ = np.linalg.lstsq(x, d.values, rcond=None)
    b = coef[1]
    if b >= 0 or (1 + b) <= 0:
        hl = np.nan
    else:
        hl = -np.log(2.0) / np.log(1.0 + b)
    return {"b": float(b), "half_life_bars": float(hl) if hl == hl else np.nan,
            "n": len(d)}


def fit_ou(residual: pd.Series, dt: float = 1.0) -> dict:
    """Continuous-time OU parameters (theta = reversion speed, mu, sigma) from the
    exact discretization res_t = res_{t-1} e^{-theta dt} + ..."""
    r = residual.dropna()
    x = r.shift(1).dropna()
    y = r.iloc[1:]
    x, y = x.align(y, join="inner")
    if len(y) < 30:
        return {"theta": np.nan, "mu": np.nan, "sigma": np.nan, "half_life_bars": np.nan}
    X = np.vstack([np.ones(len(x)), x.values]).T
    coef, *_ = np.linalg.lstsq(X, y.values, rcond=None)
    a, phi = coef
    if not (0 < phi < 1):
        return {"theta": np.nan, "mu": np.nan, "sigma": np.nan, "half_life_bars": np.nan}
    theta = -np.log(phi) / dt
    mu = a / (1 - phi)
    resid = y.values - (a + phi * x.values)
    sigma_eq = np.std(resid) * np.sqrt(2 * theta / (1 - phi ** 2))
    return {"theta": float(theta), "mu": float(mu), "sigma": float(sigma_eq),
            "half_life_bars": float(np.log(2) / theta)}


def convergence_study(z: pd.Series, entry_z: float, horizon_bars: int,
                      exit_z: float = 0.0) -> pd.DataFrame:
    """Event study: at each bar where |z| first crosses entry_z (from below),
    record whether |z| touched exit_z within `horizon_bars`, time-to-convergence,
    and max further adverse excursion of |z|.

    Uses only forward outcomes for MEASUREMENT (this is an evaluation tool, not a
    signal — the forward window here is the thing being studied).
    """
    zz = z.dropna()
    abs_z = zz.abs()
    crossed = (abs_z >= entry_z) & (abs_z.shift(1) < entry_z)
    events = []
    idx = zz.index
    positions = np.flatnonzero(crossed.values)
    for p in positions:
        end = min(p + horizon_bars, len(zz) - 1)
        window = abs_z.iloc[p:end + 1]
        hit = window[window <= exit_z]
        events.append({
            "timestamp": idx[p],
            "entry_abs_z": abs_z.iloc[p],
            "converged": len(hit) > 0,
            "bars_to_converge": (window.index.get_loc(hit.index[0]) if len(hit) else np.nan),
            "max_adverse_abs_z": window.max(),
        })
    return pd.DataFrame(events)
