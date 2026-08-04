"""Figures for the notebook-14 delayed-entry report (D-022 -> D-023).

Two pictures. The decay figure is the verdict made visible: every read-set
cell's retention ratio against entry delay, with the frozen 2/3 and 1/3 bars
and the two mechanism predictions (catch-up dies by d=5; AR(1) at the
measured half-life barely notices). The cross-correlation figure shows the
leg-level discriminator: a real but TINY MES->M2K asymmetry.

    python scripts/nb14_figures.py

Reads only the ingested CSVs, so a figure cannot disagree with the report.
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
from spread_research.delayed_entry_summary import delayed_entry_summary  # noqa: E402

MR = REPO / "reports" / "machine_readable"
FIG = REPO / "reports" / "figures"
PAIR = "MES_M2K"


def decay_figure(s) -> None:
    cells = s["per_cell"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))

    ax = axes[0]
    delays = [1, 2, 5, 15]
    for _, r in cells.iterrows():
        ax.plot(delays, [r[f"ratio_d{d}"] for d in delays], "-", lw=0.7,
                alpha=0.35, color="#4393c3" if r["signal"] == "0" else "#b2182b")
    ax.plot(delays, [s[f"rho_{d}"] for d in delays], "ko-", lw=2.5, ms=6,
            label=f"pooled median (rho(5)={s['rho_5']:.2f}, rho(15)={s['rho_15']:.2f})")
    phi58, phi37 = 2 ** (-1 / 58), 2 ** (-1 / 37)
    ax.plot(delays, [phi58 ** (d - 1) for d in delays], ":", color="gray",
            label="AR(1), half-life 58 bars (nb02 z_hl)")
    ax.plot(delays, [phi37 ** (d - 1) for d in delays], "--", color="gray",
            label="AR(1), half-life 37 bars (nb06 z1_hl)")
    ax.axhline(2 / 3, color="#2166ac", lw=1, alpha=0.6)
    ax.axhline(1 / 3, color="#b2182b", lw=1, alpha=0.6)
    ax.text(15.2, 2 / 3, "DELAY-ROBUST floor at d=5", fontsize=7,
            va="center", color="#2166ac")
    ax.text(15.2, 1 / 3, "LEAD-LAG ceiling", fontsize=7, va="center",
            color="#b2182b")
    ax.set_xlabel("entry delay d (bars after signal)")
    ax.set_ylabel("retention ratio_d = ms(d) / ms(1)")
    ax.set_title(f"Retention across the 37-cell read set - verdict {s['verdict']}\n"
                 "(blue = Z0 cells, red = Z2 cells; matched event sets)")
    ax.set_ylim(-0.35, 1.5)
    ax.set_xticks(delays)
    ax.legend(fontsize=7, loc="lower left")

    ax = axes[1]
    grids = pd.read_csv(MR / f"nb14_{PAIR}_delay_grids.csv")
    grids["signal"] = grids["signal"].astype(str)
    m = grids[grids["matched"].astype(bool)]
    for sig, spec, ez, h, lab, color in (
            ("2", "S1", 3.0, 120, "Z2 S1 3.0/120 (largest honest cell)", "#b2182b"),
            ("0", "S1", 3.0, 60, "Z0 S1 3.0/60 (highest honest t)", "#4393c3")):
        g = m[(m.signal == sig) & (m.spec == spec) & (m.entry_z == ez)
              & (m.horizon_bars == h)].sort_values("delay")
        ax.plot(g["delay"], g["mean_session_bps"], "o-", color=color, label=lab)
        for _, r in g.iterrows():
            ax.annotate(f"t={r['t_clustered']:.1f}",
                        (r["delay"], r["mean_session_bps"]),
                        textcoords="offset points", xytext=(4, 5), fontsize=7)
    ax.axhspan(2.0, 3.0, color="gray", alpha=0.15,
               label="~2-3 bps round trip (A-007/A-008 placeholders)")
    ax.set_xlabel("entry delay d (bars after signal)")
    ax.set_ylabel("mean session P&L of fading (bps)")
    ax.set_title("Headline cells: the effect an entry d bars late still finds\n"
                 "(no costs applied; not an edge claim - D-022 ceiling)")
    ax.set_xticks([1, 2, 5, 15])
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / f"nb14_{PAIR}_delay_decay.png", dpi=150)
    plt.close(fig)


def crosscorr_figure(s) -> None:
    xc = pd.read_csv(MR / f"nb14_{PAIR}_crosscorr.csv").set_index("stat")
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ks = [1, 2, 3, 4, 5]
    for pre, color, lab in (("ab", "#b2182b", "corr(r_MES(t-k), r_M2K(t)) - MES leads"),
                            ("ba", "#4393c3", "corr(r_M2K(t-k), r_MES(t)) - mirror"),
                            ("asym", "#333333", "asymmetry (paired difference)")):
        pts = [xc.loc[f"{pre}_{k}", "point"] for k in ks]
        lo = [xc.loc[f"{pre}_{k}", "ci_lo"] for k in ks]
        hi = [xc.loc[f"{pre}_{k}", "ci_hi"] for k in ks]
        off = {"ab": -0.15, "ba": 0.0, "asym": 0.15}[pre]
        ax.errorbar([k + off for k in ks], pts,
                    yerr=[[p - l for p, l in zip(pts, lo)],
                          [h - p for p, h in zip(pts, hi)]],
                    fmt="o", ms=5, color=color, capsize=3, label=lab)
    ax.axhline(0, color="gray", lw=0.8)
    ax.set_xlabel("lag k (minutes)")
    ax.set_ylabel("within-session correlation")
    ax.set_title(f"Leg-level lead-lag, session bootstrap 95% CIs (c0 = {s['c0']:.3f})\n"
                 f"ab_1 = {s['ab_1']:.3f} vs ba_1 = {s['ba_1']:.3f}: real, one-sided, and TINY - "
                 f"X = {s['X']}")
    ax.set_xticks(ks)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIG / f"nb14_{PAIR}_crosscorr.png", dpi=150)
    plt.close(fig)


def main() -> int:
    grids = pd.read_csv(MR / f"nb14_{PAIR}_delay_grids.csv")
    xc = pd.read_csv(MR / f"nb14_{PAIR}_crosscorr.csv")
    s = delayed_entry_summary(grids, xc)
    decay_figure(s)
    crosscorr_figure(s)
    for f in (f"nb14_{PAIR}_delay_decay.png", f"nb14_{PAIR}_crosscorr.png"):
        print(f"  {FIG / f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
