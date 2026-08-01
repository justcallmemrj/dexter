import numpy as np
import pandas as pd

from spread_research.backtester import run_spread_backtest
from spread_research.costs import CostModel, LegCost
from spread_research.metrics import summarize, max_drawdown
from spread_research.signals import rolling_zscore, zscore_positions


def _idx(n):
    return pd.date_range("2024-01-02 14:31", periods=n, freq="1min", tz="UTC")


def test_zscore_no_lookahead(rng):
    s = pd.Series(rng.normal(0, 1, 5000), _idx(5000))
    z_full = rolling_zscore(s, lookback=100)
    s2 = s.copy()
    s2.iloc[3000:] += 100.0          # perturb the future
    z_pert = rolling_zscore(s2, lookback=100)
    # values strictly before the perturbation must be identical
    assert np.allclose(z_full.iloc[:3000].dropna().values,
                       z_pert.iloc[:3000].dropna().values)


def test_zscore_excludes_current_bar(rng):
    s = pd.Series(rng.normal(0, 1, 500), _idx(500))
    s.iloc[-1] = 1000.0              # single extreme bar
    z = rolling_zscore(s, lookback=100)
    # the extreme bar must produce an extreme z (its own value is not in the stats)
    assert z.iloc[-1] > 50


def test_position_state_machine():
    z = pd.Series([0.0, 0.5, 2.1, 2.5, 1.0, 0.4, 0.0, -2.2, -4.5, -1.0, 0.0, -2.5],
                  _idx(12))
    pos = zscore_positions(z, entry_z=2.0, exit_z=0.5, stop_z=4.0,
                           max_holding_bars=100)
    p = pos["position"].tolist()
    assert p[2] == -1               # entered short spread on z=2.1
    assert p[3] == -1               # held
    assert p[5] == 0                # exited on |z|<=0.5
    assert pos["exit_reason"].iloc[5] == "converged"
    assert p[7] == 1                # entered long on z=-2.2
    assert p[8] == 0                # stopped on |z|>=4
    assert pos["exit_reason"].iloc[8] == "stop"
    assert p[9] == 0                # blocked after stop until |z|<=exit_z
    assert p[11] == 1               # unblocked at index 10 (z=0), re-enters at -2.5


def test_time_exit():
    z = pd.Series([2.5] * 20, _idx(20))
    pos = zscore_positions(z, entry_z=2.0, exit_z=0.5, stop_z=4.0,
                           max_holding_bars=5)
    assert pos["position"].iloc[1] == -1
    assert (pos["exit_reason"] == "time").any()


def _cost_model(commission=0.62, spread_ticks=1.0, tick_value=1.25):
    legs = {"A": LegCost("A", commission, spread_ticks, tick_value),
            "B": LegCost("B", commission, spread_ticks, tick_value)}
    return CostModel(legs, {"zero": 0.0, "base": 1.0, "stressed": 2.0})


def test_backtester_profits_on_perfect_reverting_spread():
    """Constructed spread that reliably mean-reverts; with zero costs the
    strategy must be profitable, and execution must lag decisions by one bar."""
    n = 4000
    rng = np.random.default_rng(7)
    hl = 30
    phi = np.exp(-np.log(2) / hl)
    res = np.zeros(n)
    for t in range(1, n):
        res[t] = phi * res[t - 1] + rng.normal(0, 0.5)
    pb = pd.Series(100.0, _idx(n))                  # leg B constant
    pa = pd.Series(100.0 + res, _idx(n))            # all spread action in leg A
    z = rolling_zscore(pa - pb, lookback=200)
    pos = zscore_positions(z, 2.0, 0.25, 6.0, 500)["position"]
    # cost-free run isolates the signal-capture mechanics
    result = run_spread_backtest(pa, pb, pos, 1, 1, 1.0, 1.0, None, "A", "B")
    assert len(result.trades) > 5
    assert result.bar_pnl.sum() > 0


def test_backtester_costs_reduce_pnl_monotonically():
    n = 4000
    rng = np.random.default_rng(7)
    phi = np.exp(-np.log(2) / 30)
    res = np.zeros(n)
    for t in range(1, n):
        res[t] = phi * res[t - 1] + rng.normal(0, 0.5)
    pb = pd.Series(100.0, _idx(n))
    pa = pd.Series(100.0 + res, _idx(n))
    z = rolling_zscore(pa - pb, lookback=200)
    pos = zscore_positions(z, 2.0, 0.25, 6.0, 500)["position"]
    cm = _cost_model()
    pnls = [run_spread_backtest(pa, pb, pos, 1, 1, 1.0, 1.0, cm, "A", "B",
                                scenario=s).bar_pnl.sum()
            for s in ("zero", "base", "stressed")]
    assert pnls[0] > pnls[1] > pnls[2]


def test_backtester_no_lookahead_execution():
    """A signal that 'predicts' the very next bar perfectly must earn nothing,
    because execution happens one bar later (decide t, fill t+1, earn from t+1->t+2)."""
    n = 2000
    rng = np.random.default_rng(11)
    steps = rng.choice([-1.0, 1.0], size=n)
    pa = pd.Series(1000 + np.cumsum(steps), _idx(n))
    pb = pd.Series(1000.0, _idx(n))
    # cheat signal: position at t equals direction of the t -> t+1 move
    cheat = pd.Series(np.append(steps[1:], 0.0), _idx(n))
    result = run_spread_backtest(pa, pb, cheat, 1, 1, 1.0, 1.0, None, "A", "B")
    # with iid signs, profit from a one-bar-ahead cheat must vanish under 1-bar lag
    assert abs(result.bar_pnl.sum()) < 3 * np.sqrt(n)


def test_metrics_and_drawdown():
    eq = pd.Series([0.0, 10, 5, 20, 3, 30], _idx(6))
    assert max_drawdown(eq) == -17.0


def test_summarize_smoke():
    n = 500
    rng = np.random.default_rng(3)
    pa = pd.Series(100 + np.cumsum(rng.normal(0, 0.1, n)), _idx(n))
    pb = pd.Series(100.0, _idx(n))
    z = rolling_zscore(pa - pb, lookback=50)
    pos = zscore_positions(z, 1.5, 0.25, 5.0, 100)["position"]
    r = run_spread_backtest(pa, pb, pos, 1, 1, 1.0, 1.0, None, "A", "B")
    s = summarize(r, bars_per_year=98280.0)
    assert "sharpe" in s and "n_trades" in s
