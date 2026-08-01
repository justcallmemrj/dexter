"""Notebook-01 analysis: roll calendar + adjusted-series splice artifacts.

Reads reports/machine_readable/qc_roll_audit.json (chart-channel export of the
QC roll audit) and produces:
- reports/machine_readable/qc_roll_audit.csv          tidy per-roll rows
- reports/machine_readable/qc_roll_audit_summary.csv  per-symbol summary
- reports/figures/rollaudit_ar_vs_gp.png              splice-vs-gap scatter
- reports/figures/rollaudit_leak_timeline.png         leak ratio over time
- printed tables for reports/validation/01_data_and_roll_validation.md

Splice classification (thresholds are explicit, not tuned):
  leak_ratio = ar/gp (only where |gp| >= 0.10%)
  leaked  : leak_ratio >= 0.7  (adjusted series carries >=70% of the raw gap)
  partial : 0.3 <= leak_ratio < 0.7
  clean   : otherwise
A splice is additionally 'elevated' when |ar| > max(0.05%, 10x overnight
median) — movement far beyond a typical midnight bar regardless of gap match.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SRC = Path("reports/machine_readable/qc_roll_audit.json")
FIG = Path("reports/figures")
MONTHS = {3: "H", 6: "M", 9: "U", 12: "Z"}


def quarter_code(d: datetime) -> str:
    """Contract month letter+2-digit-year for the quarterly expiry at/after d."""
    for m in (3, 6, 9, 12):
        if d.month <= m:
            return f"{MONTHS[m]}{str(d.year)[2:]}"
    return f"H{str(d.year + 1)[2:]}"


def tidy(doc: dict) -> pd.DataFrame:
    rows = []
    for sym, s in doc["series"].items():
        for i in range(len(s["t"])):
            t = datetime.fromtimestamp(s["t"][i], tz=timezone.utc)
            dte = s["dte"][i]
            old_exp = t + timedelta(days=dte)
            old_code = quarter_code(old_exp)
            nxt = old_exp + timedelta(days=80)
            rows.append({
                "sym": sym, "date": t.date().isoformat(),
                "old": f"{sym}{old_code}", "new": f"{sym}{quarter_code(nxt)}",
                "dte": dte, "gp": s["gp"][i], "ar": s["ar"][i], "vs": s["vs"][i],
            })
    df = pd.DataFrame(rows)
    on_med = {k: v["on_med_pct"] for k, v in doc["baselines"].items()}
    df["on_med"] = df["sym"].map(on_med)
    big = df["gp"].abs() >= 0.10
    df["leak_ratio"] = pd.NA
    df.loc[big, "leak_ratio"] = (df.loc[big, "ar"] / df.loc[big, "gp"]).round(3)
    lr = pd.to_numeric(df["leak_ratio"], errors="coerce")
    df["splice"] = "clean"
    df.loc[lr.ge(0.3) & lr.lt(0.7), "splice"] = "partial"
    df.loc[lr.ge(0.7), "splice"] = "leaked"
    df["elevated"] = df["ar"].abs() > (df["on_med"] * 10).clip(lower=0.05)
    return df.sort_values(["sym", "date"]).reset_index(drop=True)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    out = []
    for sym, g in df.groupby("sym"):
        counts = g["splice"].value_counts()
        out.append({
            "sym": sym, "n_rolls": len(g),
            "dte_min": g["dte"].min(), "dte_med": g["dte"].median(),
            "dte_max": g["dte"].max(),
            "abs_gap_med_pct": g["gp"].abs().median(),
            "abs_gap_max_pct": g["gp"].abs().max(),
            "clean": int(counts.get("clean", 0)),
            "partial": int(counts.get("partial", 0)),
            "leaked": int(counts.get("leaked", 0)),
            "elevated": int(g["elevated"].sum()),
            "vs_med": g["vs"].median(),
            "last_leaked": (g.loc[g["splice"] == "leaked", "date"].max()
                            if counts.get("leaked", 0) else None),
        })
    return pd.DataFrame(out).sort_values("sym")


def figures(df: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharex=False, sharey=False)
    for ax, (label, syms) in zip(axes, [
            ("Index micros", ["MES", "MNQ", "M2K", "MYM"]),
            ("Treasuries", ["ZT", "ZF", "ZN", "ZB"])]):
        sub = df[df["sym"].isin(syms)]
        colors = {"clean": "tab:green", "partial": "tab:orange",
                  "leaked": "tab:red"}
        for cls, c in colors.items():
            s = sub[sub["splice"] == cls]
            ax.scatter(s["gp"], s["ar"], s=22, c=c, label=cls, alpha=0.8)
        lim = max(sub["gp"].abs().max(), sub["ar"].abs().max()) * 1.1
        ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.7, label="ar = gap (full leak)")
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("raw calendar gap at roll, %")
        ax.set_ylabel("adjusted-series splice return, %")
        ax.set_title(label)
        ax.legend(fontsize=8)
    fig.suptitle("QC continuous (OpenInterest/BackwardsRatio) splice returns vs raw roll gaps, 2019-06 -> 2026-05")
    fig.tight_layout()
    fig.savefig(FIG / "rollaudit_ar_vs_gp.png", dpi=130)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4.5))
    lr = pd.to_numeric(df["leak_ratio"], errors="coerce")
    d = pd.to_datetime(df["date"])
    for sym, marker in zip(df["sym"].unique(), "osv^DPX*"):
        m = df["sym"] == sym
        ax.scatter(d[m], lr[m].fillna(0), s=20, marker=marker, label=sym, alpha=0.8)
    ax.axhline(0.7, color="r", lw=0.7, ls="--")
    ax.axhline(0.3, color="orange", lw=0.7, ls="--")
    ax.set_ylabel("leak ratio (splice return / raw gap)")
    ax.set_title("Roll-gap leak ratio per splice (>=0.7 red line = full leak; |gap|>=0.1% only)")
    ax.legend(fontsize=8, ncol=4)
    fig.tight_layout()
    fig.savefig(FIG / "rollaudit_leak_timeline.png", dpi=130)
    plt.close(fig)

    if "final" in df.columns and df["final"].ne("unprobed").any():
        fig, ax = plt.subplots(figsize=(8, 6))
        colors = {"clean": "tab:green", "streaming_only_artifact": "tab:blue",
                  "elevated_ambiguous": "tab:orange", "data_side_leak": "tab:red"}
        for cls, c in colors.items():
            s = df[df["final"] == cls]
            ax.scatter(s["gp"], s["refetch_ar"], s=24, c=c, label=f"{cls} ({len(s)})",
                       alpha=0.8)
        lim = 1.5
        ax.plot([-lim, lim], [-lim, lim], "k--", lw=0.7)
        ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("raw calendar gap at roll, %")
        ax.set_ylabel("HISTORY-REFETCHED splice return, %")
        ax.set_title("Final verdict: refetched (research-path) splice returns vs raw gaps\n"
                     "points on the diagonal = bad adjustment factors in QC data")
        ax.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(FIG / "rollaudit_refetch_verdict.png", dpi=130)
        plt.close(fig)


def merge_refetch(df: pd.DataFrame) -> pd.DataFrame:
    """Join the 220-splice History-refetch sweep and issue the FINAL verdict.

    'splice' classifies the STREAMED series; 'final' classifies the REFETCHED
    series — the data path notebooks/QuantBook actually consume:
      data_side_leak          refetch carries >=60% of the raw gap (bad factor
                              in QC data itself; must be repaired/excluded)
      streaming_only_artifact streamed leaked but refetch is clean
      elevated_ambiguous      refetch elevated but not gap-shaped
      clean                   refetch consistent with a normal midnight bar
    """
    ref_path = Path("reports/machine_readable/qc_splice_refetch.json")
    if not ref_path.exists():
        df["refetch_ar"] = pd.NA
        df["final"] = "unprobed"
        return df
    ref = json.loads(ref_path.read_text())["refetch_pct"]
    key = df["sym"] + "_" + df["date"].str.replace("-", "")
    df["refetch_ar"] = key.map({k: float(v) for k, v in ref.items()})

    def verdict(row):
        ra, gp = row["refetch_ar"], row["gp"]
        if pd.isna(ra):
            return "unprobed"
        if abs(gp) >= 0.10 and gp != 0 and abs(ra / gp) >= 0.6:
            return "data_side_leak"
        if abs(ra) > 0.05:
            return "elevated_ambiguous"
        if row["splice"] in ("leaked", "partial"):
            return "streaming_only_artifact"
        return "clean"

    df["final"] = df.apply(verdict, axis=1)
    return df


def main() -> int:
    doc = json.loads(SRC.read_text())
    df = tidy(doc)
    df = merge_refetch(df)
    out = Path("reports/machine_readable")
    df.to_csv(out / "qc_roll_audit.csv", index=False)
    summary = summarize(df)
    summary.to_csv(out / "qc_roll_audit_summary.csv", index=False)
    figures(df)
    pd.set_option("display.width", 220)
    print(summary.to_string(index=False))
    print("\nLeaked splices (adjusted series carried >=70% of the raw gap):")
    leaked = df[df["splice"] == "leaked"]
    print(leaked[["sym", "date", "old", "new", "gp", "ar", "leak_ratio"]]
          .to_string(index=False))
    print(f"\ntotals: {len(df)} rolls | clean {sum(df['splice']=='clean')} | "
          f"partial {sum(df['splice']=='partial')} | leaked {len(leaked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
