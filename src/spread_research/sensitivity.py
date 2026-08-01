"""Parameter-sensitivity machinery (mandate notebook 10).

Grid runner + plateau analysis. Selection discipline: prefer the CENTER OF A
STABLE PLATEAU over the single best cell; a peak whose neighbors are poor is
treated as overfitting evidence, not alpha. Every grid run also reports the
number of configurations evaluated (multiple-testing accounting).
"""

from __future__ import annotations

import itertools

import pandas as pd


def run_grid(param_grid: dict[str, list], eval_fn) -> pd.DataFrame:
    """eval_fn(**params) -> dict of metrics. Returns tidy results with one row per
    configuration and a `n_configs_evaluated` column on every row."""
    keys = list(param_grid)
    rows = []
    combos = list(itertools.product(*(param_grid[k] for k in keys)))
    for combo in combos:
        params = dict(zip(keys, combo))
        metrics = eval_fn(**params)
        rows.append({**params, **metrics})
    df = pd.DataFrame(rows)
    df["n_configs_evaluated"] = len(combos)
    return df


def plateau_score(results: pd.DataFrame, metric: str,
                  param_cols: list[str]) -> pd.DataFrame:
    """For each config, the mean metric over its grid neighbors (differing by one
    step in exactly one parameter). High own-metric with high neighbor-mean =
    plateau; high own-metric with low neighbor-mean = suspect peak."""
    res = results.copy()
    levels = {p: sorted(res[p].unique()) for p in param_cols}

    def neighbors(row):
        vals = []
        for p in param_cols:
            lv = levels[p]
            i = lv.index(row[p])
            for j in (i - 1, i + 1):
                if 0 <= j < len(lv):
                    m = res
                    for q in param_cols:
                        m = m[m[q] == (lv[j] if q == p else row[q])]
                    if len(m):
                        vals.append(m.iloc[0][metric])
        return sum(vals) / len(vals) if vals else float("nan")

    res["neighbor_mean_" + metric] = res.apply(neighbors, axis=1)
    res["plateau_gap"] = res[metric] - res["neighbor_mean_" + metric]
    return res
