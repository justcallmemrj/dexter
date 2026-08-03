"""Figures for the notebook-06 signal-definition report (L-013, D-020).

One picture per pair, three panels: the conditional surface under each signal
definition, at the estimation-free specification. The point of the layout is
that Z0 and Z2 differ ONLY in whether first-30-minute events are counted, so
any difference between those two panels is the open window and nothing else.

    python scripts/nb06_figures.py --pair MES_MYM

Reads only the ingested CSVs, so a figure cannot disagree with the report.
"""

from __future__ import annotations

import argparse
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt   # noqa: E402
import pandas as pd               # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[1]
MR = REPO / "reports" / "machine_readable"
FIG = REPO / "reports" / "figures"

PANELS = [("0", "Z0 — configured 390-bar score\n(spans the overnight break)"),
          ("1", "Z1 — session-anchored\n(the fix under test)"),
          ("2", "Z2 — Z0 minus first-30-min events\n(the decomposition)")]
COLORS = {1.5: "#2166ac", 2.0: "#4393c3", 2.5: "#f4a582", 3.0: "#b2182b"}


def signal_figure(pair: str, cost_band=(2.0, 3.0)) -> None:
    d = pd.read_csv(MR / f"nb06_{pair}_signal_grids.csv")
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.1), sharey=True)
    for ax, (sig, title) in zip(axes, PANELS):
        g = d[(d["signal"] == sig) & (d["spec"] == "S1")]
        for ez, r in g.groupby("entry_z"):
            r = r.sort_values("horizon_bars")
            ax.plot(r["horizon_bars"], r["mean_session_bps"], "o-", ms=4,
                    color=COLORS.get(ez, "0.4"), label=f"entry |z| = {ez}")
            s = r[r["t_clustered"].abs() >= 3]
            ax.plot(s["horizon_bars"], s["mean_session_bps"], "o", ms=9,
                    mfc="none", mec=COLORS.get(ez, "0.4"), mew=1.6)
        ax.axhline(0, color="0.2", lw=1)
        ax.axhspan(cost_band[0], cost_band[1], color="0.85", zorder=0)
        ax.set_xscale("log")
        ax.set_xticks([5, 15, 30, 60, 120])
        ax.set_xticklabels(["5", "15", "30", "60", "120"])
        ax.set_xlabel("holding horizon (minutes)")
        ax.set_title(title, fontsize=9.5)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("session-mean P&L of fading (bps)")
    axes[0].legend(fontsize=7.5, loc="best")
    axes[2].text(0.98, 0.04, "grey band = round-trip cost scale\n"
                             "ringed markers: |t| >= 3 (session-clustered)",
                 transform=axes[2].transAxes, ha="right", fontsize=7, color="0.3")
    fig.suptitle(f"{pair.replace('_', '-')}: the same events, three signal "
                 f"definitions (S1, look-ahead-safe)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / f"nb06_{pair}_signal_definitions.png", dpi=150)
    plt.close(fig)


def clock_figure(pairs) -> None:
    """Where crossings land, before and after the anchor."""
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for pair in pairs:
        c = pd.read_csv(MR / f"nb06_{pair}_event_clocks.csv")
        for sig, ls in (("0", "-"), ("1", "--")):
            r = c[c["signal"] == sig].sort_values("minutes_from_open")
            ax.plot(r["minutes_from_open"], r["share"], ls, marker="o", ms=3.5,
                    label=f"{pair.replace('_', '-')} {'Z0' if sig == '0' else 'Z1'}",
                    alpha=0.85)
    ax.axvspan(0, 30, color="#f4a582", alpha=0.3)
    ax.text(35, ax.get_ylim()[1] * 0.92, "first 30 minutes", fontsize=8, color="0.3")
    ax.set_xlabel("minutes from the 09:30 ET open")
    ax.set_ylabel("share of |z| >= 2 crossings")
    ax.set_title("L-013: the crossings pile up at the equity open under the "
                 "390-bar score,\nand the session anchor removes the pile",
                 fontsize=10.5)
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "nb06_event_clocks.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default=None, help="omit to draw every ingested pair")
    args = ap.parse_args()
    FIG.mkdir(parents=True, exist_ok=True)
    pairs = ([args.pair] if args.pair
             else sorted(p.name.split("_signal_grids")[0][len("nb06_"):]
                         for p in MR.glob("nb06_*_signal_grids.csv")))
    for pair in pairs:
        band = (1.0, 3.10) if pair.startswith("Z") else (2.0, 3.0)
        signal_figure(pair, cost_band=band)
        print(f"  wrote reports/figures/nb06_{pair}_signal_definitions.png")
    clock_figure(pairs)
    print("  wrote reports/figures/nb06_event_clocks.png")


if __name__ == "__main__":
    main()
