"""Program-level figures for the final research summary (notebook 13).

Two pictures, both of which have to be read before the negative conclusion is
believable:

  1. effect size against the cost of harvesting it, all seven pairs at once —
     the reason significance was never the binding constraint;
  2. the residual variance ratio walking back toward 1 as the base bar coarsens
     — the pre-committed check that failed in every pair.

No statistics are computed here. Everything comes from
`spread_research.program_summary`, which reads the banked notebook-02/03 CSVs,
so a figure cannot disagree with the report's table.

    python scripts/nb13_figures.py
"""

from __future__ import annotations

import pathlib
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import pandas as pd               # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from spread_research.program_summary import (  # noqa: E402
    PAIRS, matched_elapsed_vr, program_table, read_variance_ratio,
)

MR = REPO / "reports" / "machine_readable"
FIG = REPO / "reports" / "figures"

INDEX_COLOR = "#b2182b"
TREASURY_COLOR = "#2166ac"


def effect_vs_cost_figure(table: pd.DataFrame) -> None:
    """Best honest cell per pair against its own round-trip cost.

    Index costs are the report-02 §5 band (2-3 bps, A-007 placeholder included);
    treasury costs are derived from verified tick specs. Bars above their marker
    are untradable regardless of t-statistic."""
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    x = range(len(table))
    colors = [INDEX_COLOR if a == "index" else TREASURY_COLOR
              for a in table["asset_class"]]

    ax.bar(x, table["best_effect_bps"], color=colors, width=0.55,
           label="largest effect in a look-ahead-safe spec")
    ax.plot(x, table["round_trip_cost_bps"], "_", color="0.15", ms=26, mew=2.5,
            label="round-trip cost of harvesting it")

    for i, r in table.reset_index(drop=True).iterrows():
        ratio = r["round_trip_cost_bps"] / r["best_effect_bps"]
        txt = (f"{ratio:.1f}x below cost" if ratio >= 1
               else f"{1 / ratio:.1f}x above cost")
        ax.text(i, max(r["best_effect_bps"], r["round_trip_cost_bps"]) + 0.25,
                f"t = {r['best_t']:.2f}\n{txt}", ha="center", fontsize=7.2,
                color="0.25")

    ax.set_xticks(list(x))
    ax.set_xticklabels([p.replace("_", "-") for p in table["pair"]], fontsize=9)
    ax.set_ylabel("bps of notional")
    ax.set_ylim(0, max(table["best_effect_bps"].max(),
                       table["round_trip_cost_bps"].max()) + 1.6)
    ax.set_title("Every pair in the locked universe: measured effect vs the cost "
                 "of trading it\n(the one bar that clears its cost — MES-M2K — "
                 "failed the base-sampling check)", fontsize=10.5)
    ax.legend(fontsize=8, loc="upper right")
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(FIG / "nb13_effect_vs_cost.png", dpi=150)
    plt.close(fig)


def base_sampling_figure() -> None:
    """Criterion (b) across all seven pairs on one axis. A real reversion
    process does not care how you slice the clock; microstructure does."""
    fig, ax = plt.subplots(figsize=(8.2, 4.6))
    for pair in PAIRS:
        walk = matched_elapsed_vr(read_variance_ratio(pair, MR))
        steps = sorted(walk)
        is_index = pair.startswith("M")
        ax.plot(steps, [walk[s] for s in steps],
                "o-" if is_index else "s--",
                color=INDEX_COLOR if is_index else TREASURY_COLOR,
                ms=5, alpha=0.85, label=pair.replace("_", "-"))
    ax.axhline(1.0, color="0.2", lw=1.2, ls=":")
    ax.text(15, 1.005, "random walk", fontsize=7.5, color="0.35", ha="right")
    ax.set_xscale("log")
    ax.set_xticks([1, 5, 15])
    ax.set_xticklabels(["1-min bars", "5-min", "15-min"])
    ax.set_xlabel("base sampling interval (residual VR at matched ~30 min elapsed)")
    ax.set_ylabel("variance ratio")
    ax.set_ylim(0, 1.1)
    ax.set_title("The pre-committed base-sampling check, all seven pairs\n"
                 "every residual walks toward 1 as the bar coarsens", fontsize=10.5)
    ax.legend(fontsize=7.5, ncol=2, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "nb13_base_sampling.png", dpi=150)
    plt.close(fig)


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    table = program_table(root=MR)
    effect_vs_cost_figure(table)
    base_sampling_figure()
    for name in ("effect_vs_cost", "base_sampling"):
        print(f"  wrote reports/figures/nb13_{name}.png")


if __name__ == "__main__":
    main()
