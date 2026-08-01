"""Daily-resolution pair relationship SCREEN (D-007 preview tier).

Run from the repo root:  .venv/Scripts/python.exe scripts/daily_preview_screen.py

Screens the 7 locked pairs (config/pair_definitions.yaml) on yfinance daily
preview data, plus clearly-labeled parent-proxy variants of the index pairs for
long-history context. Produces:
- reports/machine_readable/daily_pair_screen.csv
- reports/preview/daily_pair_screen.md
- experiment-log rows (one per screen window)

A screen deprioritizes or flags pairs; it can NEVER validate one (A-015, D-007).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
import yaml

from spread_research.data_loader import load_local
from spread_research.preview_screen import screen_pair, screen_tier
from spread_research.reporting import log_experiment

RESEARCH_START = "2019-06-01"   # config/research_config.yaml data.research_start
EXTENDED_START = "2010-01-01"
OLS_WINDOW = 126                # ~6 trading months of daily bars
# Parent-proxy versions of the index pairs (labeled; never merged with micros)
PROXY_PAIRS = {"ES_NQ": ("ES", "NQ"), "ES_RTY": ("ES", "RTY"), "ES_YM": ("ES", "YM")}


def _close(symbol: str) -> pd.Series:
    return load_local(symbol, "daily")["close"].rename(symbol)


def run_window(pairs: list[dict], start: str, label: str) -> pd.DataFrame:
    rows = []
    for p in pairs:
        a = _close(p["a"]).loc[start:]
        b = _close(p["b"]).loc[start:]
        row = screen_pair(a, b, pair_name=p["name"], use_log=p["use_log"],
                          ols_window_bars=OLS_WINDOW)
        row["window"] = label
        row["kind"] = p["kind"]
        row["tier"] = screen_tier(row)
        rows.append(row)
    return pd.DataFrame(rows)


def main() -> int:
    cfg = yaml.safe_load(Path("config/pair_definitions.yaml").read_text())
    pairs = []
    for name, d in cfg["index_pairs"].items():
        pairs.append({"name": name, "a": d["long_ref"], "b": d["short_ref"],
                      "use_log": True, "kind": "index_micro"})
    for name, d in cfg["treasury_pairs"].items():
        pairs.append({"name": name, "a": d["long_ref"], "b": d["short_ref"],
                      "use_log": False, "kind": "treasury"})
    proxy = [{"name": f"{n} (proxy)", "a": a, "b": b, "use_log": True,
              "kind": "index_parent_proxy"} for n, (a, b) in PROXY_PAIRS.items()]

    research = run_window(pairs, RESEARCH_START, "research_2019-06->present")
    extended = run_window(
        [p for p in pairs if p["kind"] == "treasury"] + proxy,
        EXTENDED_START, "extended_2010->present")
    table = pd.concat([research, extended], ignore_index=True)

    out_mr = Path("reports/machine_readable")
    out_mr.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_mr / "daily_pair_screen.csv", index=False)

    for _, window_df in table.groupby("window"):
        label = window_df["window"].iloc[0]
        exp_id = log_experiment(
            data_period=label,
            pairs=";".join(window_df["pair"]),
            model_type="daily_preview_screen(EG+ADF/KPSS+OLS126+half_life)",
            parameters={"ols_window_bars": OLS_WINDOW, "source": "yfinance_daily",
                        "assumption": "A-015", "decision": "D-007"},
            cost_scenario="none (no trading simulated at daily resolution)",
            result_summary="; ".join(
                f"{r.pair}:{r.tier}" for r in window_df.itertuples()),
            notes="Screening tier only — cannot validate pairs or measure "
                  "intraday reversion. See reports/preview/daily_pair_screen.md",
        )
        print(f"logged {exp_id}: {label}")

    cols = ["pair", "kind", "window", "n_obs", "daily_ret_corr", "eg_pvalue",
            "static_resid_verdict", "static_resid_half_life_days",
            "rolling_resid_half_life_days", "beta_roll_median",
            "beta_recent_vs_full_shift_pct", "tier"]
    print(table[cols].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
