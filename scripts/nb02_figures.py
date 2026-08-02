"""Figures for the notebook-02 minute-level pair reports.

Reads the ingested CSVs written by `ingest_qc_pair_minute.py` — no QC access
needed, and no numbers are recomputed here, so a figure can never disagree with
the report's table.

    python scripts/nb02_figures.py --pair MES_MNQ

Outputs are namespaced by pair so one pair's figures can never silently
overwrite another's.
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


def variance_ratio_figure(pair: str) -> None:
    """The heart of the negative result: the residual's VR curve looks like
    reversion at 1-minute bars and like a random walk at 5-minute bars."""
    vr = pd.read_csv(MR / f"nb02_{pair}_variance_ratio.csv")
    leg_a, leg_b = pair.split("_")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)

    ax = axes[0]
    p = vr[vr.base_step_min == 1].pivot(index="q", columns="series", values="vr")
    styles = {"RES1": ("o-", "#b2182b", "residual S1 (beta=1)"),
              "RES2": ("s-", "#ef8a62", "residual S2 (rolling OLS)"),
              "LEGA": ("^--", "#2166ac", f"{leg_a} alone"),
              "LEGB": ("v--", "#67a9cf", f"{leg_b} alone")}
    for col, (st, c, lab) in styles.items():
        if col in p:
            ax.plot(p.index, p[col], st, color=c, label=lab, ms=5)
    ax.axhline(1.0, color="0.3", lw=1, ls=":")
    ax.set_xscale("log")
    ax.set_xticks(list(p.index))
    ax.set_xticklabels([str(q) for q in p.index])
    ax.set_xlabel("q (minutes)")
    ax.set_ylabel("variance ratio")
    ax.set_title("1-minute base sampling\nresidual looks mean-reverting", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower left")
    ax.grid(alpha=0.25)

    ax = axes[1]
    # Plot against ELAPSED MINUTES (q * base interval) so the three base
    # frequencies are compared at the same real horizon. Points whose block
    # would span more than ~150 minutes are dropped: with 390-bar sessions a
    # 15-min bar at q=15 covers 225 minutes, i.e. over half the session, and
    # the estimate is dominated by session-edge effects rather than by q.
    for step, st, c in ((1, "o-", "#b2182b"), (5, "s-", "#7f3b08"),
                        (15, "^-", "#404040")):
        d = vr[(vr.series == "RES1") & (vr.base_step_min == step)].dropna(subset=["vr"]).copy()
        d["elapsed"] = d["q"] * step
        d = d[d["elapsed"] <= 150].sort_values("elapsed")
        if len(d):
            ax.plot(d["elapsed"], d["vr"], st, color=c, ms=5,
                    label=f"{step}-min base bars")
    ax.axhline(1.0, color="0.3", lw=1, ls=":")
    ax.set_xscale("log")
    ax.set_xticks([2, 5, 15, 30, 60, 120])
    ax.set_xticklabels(["2", "5", "15", "30", "60", "120"])
    ax.set_xlabel("elapsed time spanned (minutes)")
    ax.set_title("residual S1 at matched elapsed horizons\ncoarser bars -> VR "
                 "returns to 1 -> microstructure", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower left")
    ax.grid(alpha=0.25)

    fig.suptitle(f"{pair.replace('_', '-')} variance ratios: is VR < 1 reversion or bid-ask bounce?",
                 fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / f"nb02_{pair}_variance_ratio.png", dpi=150)
    plt.close(fig)


def conditional_reversion_figure(pair: str) -> None:
    """Session-mean P&L of fading a dislocation. Positive = reversion pays."""
    cr = pd.read_csv(MR / f"nb02_{pair}_conditional_reversion.csv")
    specs = [("S1", "beta = 1 (estimation-free)"),
             ("S2", "trailing OLS residual"),
             ("S3", "static beta (LOOK-AHEAD, diagnostic only)")]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 4.0), sharey=True)
    colors = {1.5: "#2166ac", 2.0: "#4393c3", 2.5: "#f4a582", 3.0: "#b2182b"}
    for ax, (spec, title) in zip(axes, specs):
        d = cr[cr.spec == spec]
        for ez, g in d.groupby("entry_z"):
            g = g.sort_values("horizon_bars")
            ax.plot(g.horizon_bars, g.mean_session_bps, "o-", ms=4,
                    color=colors.get(ez, "0.4"), label=f"entry |z| = {ez}")
            sig = g[g.t_clustered.abs() >= 3]
            ax.plot(sig.horizon_bars, sig.mean_session_bps, "o", ms=9, mfc="none",
                    mec=colors.get(ez, "0.4"), mew=1.6)
        ax.axhline(0, color="0.2", lw=1)
        ax.axhspan(0, 3, color="0.85", zorder=0)
        ax.set_xscale("log")
        ax.set_xticks([5, 15, 30, 60, 120])
        ax.set_xticklabels(["5", "15", "30", "60", "120"])
        ax.set_xlabel("holding horizon (minutes)")
        ax.set_title(f"{spec} — {title}", fontsize=9.5)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("session-mean P&L of fading (bps)")
    axes[0].legend(fontsize=7.5, loc="lower left")
    axes[2].text(0.98, 0.04, "grey band = round-trip cost scale (~2-3 bps)\n"
                             "ringed markers: |t| >= 3 (session-clustered)",
                 transform=axes[2].transAxes, ha="right", fontsize=7, color="0.3")
    fig.suptitle(f"Fading a {pair.replace('_', '-')} dislocation "
                 f"(positive = fading pays)", fontsize=11)
    fig.tight_layout()
    fig.savefig(FIG / f"nb02_{pair}_conditional_reversion.png", dpi=150)
    plt.close(fig)


def roll_window_figure(pair: str) -> None:
    """Preflight: dispersion around OUR splice, and the shock a held position
    absorbs at every roll."""
    rb = pd.read_csv(MR / f"nb02_{pair}_roll_buckets.csv")
    hs = pd.read_csv(MR / f"nb02_{pair}_held_shock.csv")
    order = ["[-1170,-780)", "[-780,-390)", "[-390,0)", "[0,390)",
             "[390,780)", "[780,1170)"]
    rb = rb.set_index("bucket")
    base = rb.loc["baseline", "sd_dres_bps"]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.0))
    ax = axes[0]
    vals = [rb.loc[b, "sd_dres_bps"] for b in order]
    cols = ["#4393c3" if v < 1.2 * base else "#b2182b" for v in vals]
    ax.bar(range(len(order)), vals, color=cols)
    ax.axhline(base, color="0.2", ls="--", lw=1.2, label=f"baseline {base:.2f} bps")
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels(order, rotation=30, ha="right", fontsize=7.5)
    ax.set_ylabel("sd of 1-bar residual change (bps)")
    ax.set_title("Dispersion around the D-009 splice\n(bars relative to roll; "
                 "390 = one RTH day)", fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    ax = axes[1]
    hs["roll"] = pd.to_datetime(hs["roll"])
    ax.bar(hs["roll"], hs["shock_bps"].abs(), width=45, color="#b2182b")
    med = hs["shock_bps"].abs().median()
    ax.axhline(med, color="0.2", ls="--", lw=1.2, label=f"median {med:.1f} bps")
    ax.set_ylabel("|level shift| absorbed (bps)")
    ax.set_title("What a HELD position eats at each roll\n"
                 "(constructed series is continuous; a real trade is not)",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25, axis="y")

    fig.tight_layout()
    fig.savefig(FIG / f"nb02_{pair}_roll_preflight.png", dpi=150)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="MES_MYM")
    pair = ap.parse_args().pair
    FIG.mkdir(parents=True, exist_ok=True)
    variance_ratio_figure(pair)
    conditional_reversion_figure(pair)
    roll_window_figure(pair)
    for kind in ("variance_ratio", "conditional_reversion", "roll_preflight"):
        print(f"  wrote reports/figures/nb02_{pair}_{kind}.png")


if __name__ == "__main__":
    main()
