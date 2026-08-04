"""D-024 verdict arithmetic: read the notebook-15 CSVs, apply the frozen rule.

Every threshold, comparison and branch name here was fixed in D-024 BEFORE the
runs existed. Nothing in this module chooses anything; it only evaluates. It
lives in `src/` (not the notebook) so the report cannot drift from its own
evidence and so the numbers are pinned by unit tests — the same discipline
`program_summary.py` enforces for report 13.

The one subtlety worth stating in code. The comparison statistic is the
FREE signed argmax of `mean_session_bps` over the look-ahead-safe specs, reused
unchanged from `program_summary.largest_honest_effect`. Because the argmax is
free it can RELOCATE between windows, so D-024 requires the free-argmax ratio
and the ratio at the reference window's argmax cell to AGREE; if they disagree
the pair reads MOVE-IS-RELOCATION and is INCONCLUSIVE.
"""

from __future__ import annotations

import pandas as pd

from .program_summary import (
    HONEST_SPECS, T_BAR, largest_honest_effect, round_trip_spread_bps,
)

#: D-024 §6, calibrated on banked nuisance movement (a pure signal
#: re-specification already moves this statistic 1.467x) and fixed in advance.
MOVE_BAR = 2.0

#: Window tags, in the order D-024 §2 tabulates them.
WINDOWS = ("U", "H", "R", "S", "C")
WINDOW_NAMES = {"U": "S-USED", "H": "S-HALF", "R": "S-RTH",
                "S": "S-SETTLE", "C": "S-CASH"}


def window_grid(grids: pd.DataFrame, window: str) -> pd.DataFrame:
    return grids[grids["window"] == window]


def move_factor(ref: float, new: float) -> tuple[float, str]:
    """D-024 §6's directionless, sign-aware move factor.

    Returns (factor, note). A halving must count exactly as much as a doubling,
    and the ratio is undefined once either side is <= 0 — banked open subsets
    already produce negative largest honest effects, so this is a live case and
    a SIGN CHANGE is automatically a move.
    """
    if ref <= 0 or new <= 0:
        if (ref > 0) != (new > 0):
            return float("inf"), "SIGN_CHANGE"
        return float("nan"), "UNDEFINED_non_positive"
    return max(new / ref, ref / new), "ok"


def fixed_cell_effect(grids: pd.DataFrame, window: str,
                      cell: pd.Series) -> float:
    """The same grid cell the reference window's argmax picked, read on another
    window — the check that a 'move' is not just the argmax relocating."""
    g = window_grid(grids, window)
    m = g[(g["spec"] == cell["spec"])
          & (g["entry_z"] == cell["entry_z"])
          & (g["horizon_bars"] == cell["horizon_bars"])]
    return float(m["mean_session_bps"].iloc[0]) if len(m) else float("nan")


def criteria(grids: pd.DataFrame, vr: pd.DataFrame, window: str) -> dict:
    """D-010 (a) and (c) on one window. (b) is reported from the recomputed
    variance ratios by `vr_shape`, which is what makes this run able to move a
    verdict at all."""
    g = window_grid(grids, window)
    honest = g[g["spec"].isin(HONEST_SPECS)]
    sig = honest[honest["t_clustered"].abs() >= T_BAR]

    # (a) >= 2 adjacent horizons positive at |t| >= T_BAR in S1 AND S2
    def adjacent(spec: str) -> bool:
        s = honest[honest["spec"] == spec]
        for ez, block in s.groupby("entry_z"):
            b = block.sort_values("horizon_bars")
            ok = ((b["t_clustered"] >= T_BAR) & (b["mean_session_bps"] > 0)).values
            if any(ok[i] and ok[i + 1] for i in range(len(ok) - 1)):
                return True
        return False

    a = adjacent("S1") and adjacent("S2")

    # (c) the effect strengthens with entry threshold (S1, longest horizon)
    s1 = honest[honest["spec"] == "S1"]
    h = s1["horizon_bars"].max()
    ladder = s1[s1["horizon_bars"] == h].sort_values("entry_z")["mean_session_bps"]
    c = bool(len(ladder) > 1 and ladder.is_monotonic_increasing)

    return {"window": window, "window_name": WINDOW_NAMES[window],
            "criterion_a": bool(a), "criterion_c": c,
            "n_significant": int(len(sig)),
            "n_sig_positive": int((sig["mean_session_bps"] > 0).sum()),
            "n_sig_negative": int((sig["mean_session_bps"] < 0).sum())}


def vr_shape(vr: pd.DataFrame, window: str) -> dict:
    """Criterion (b)'s inputs, RECOMPUTED per window (D-024 §1).

    Reports the residual curve's tail ratio and the base-sampling walk toward
    1, plus both legs' own q=2 baselines — a residual VR below 1 means nothing
    until it is compared against the bounce baseline its legs set.
    """
    w = vr[vr["window"] == window]

    def cell(series, step, q):
        m = w[(w["series"] == series) & (w["base_step"] == step) & (w["q"] == q)]
        return float(m["vr"].iloc[0]) if len(m) else float("nan")

    res30, res120 = cell("RES1", 1, 30), cell("RES1", 1, 120)
    return {"window": window, "window_name": WINDOW_NAMES[window],
            "res_vr_q2": cell("RES1", 1, 2), "res_vr_q30": res30,
            "res_vr_q120": res120,
            "tail_ratio_120_over_30": (res120 / res30) if res30 else float("nan"),
            "base1_q30": res30, "base5_q5": cell("RES1", 5, 5),
            "base15_q2": cell("RES1", 15, 2),
            "lega_vr_q2": cell("LEGA", 1, 2), "legb_vr_q2": cell("LEGB", 1, 2)}


def pair_summary(grids: pd.DataFrame, vr: pd.DataFrame, scalars: pd.Series,
                 leg_a: str, leg_b: str) -> pd.DataFrame:
    """One row per window: the largest honest effect, its cell, the move
    against the D-024 reference, and the D-010 criteria."""
    beta = float(str(scalars.get("S_SPECS", "")).split("S1_beta_med=")[1]
                 .split("|")[0]) if "S1_beta_med=" in str(scalars.get("S_SPECS", "")) else float("nan")
    cost = round_trip_spread_bps(leg_a, leg_b, beta)

    ref_cell = largest_honest_effect(window_grid(grids, "U"))
    rows = []
    for w in WINDOWS:
        g = window_grid(grids, w)
        if g.empty:
            continue
        best = largest_honest_effect(g)
        # Q1 compares against S-USED; Q2 compares against S-RTH.
        ref_w = "U" if w in ("H", "R") else ("R" if w in ("S", "C") else None)
        row = {"window": w, "window_name": WINDOW_NAMES[w],
               "best_bps": float(best["mean_session_bps"]),
               "best_t": float(best["t_clustered"]),
               "best_cell": f"{best['spec']}/z{best['entry_z']}/h{int(best['horizon_bars'])}",
               "round_trip_bps": cost,
               "cost_ratio": cost / float(best["mean_session_bps"])
                             if best["mean_session_bps"] > 0 else float("nan"),
               "reference": ref_w}
        if ref_w is not None:
            ref_best = largest_honest_effect(window_grid(grids, ref_w))
            f, note = move_factor(float(ref_best["mean_session_bps"]),
                                  float(best["mean_session_bps"]))
            ref_arg = largest_honest_effect(window_grid(grids, ref_w))
            fixed_new = fixed_cell_effect(grids, w, ref_arg)
            f_fix, note_fix = move_factor(float(ref_arg["mean_session_bps"]),
                                          fixed_new)
            row.update({"move_free": f, "move_free_note": note,
                        "move_fixed": f_fix, "move_fixed_note": note_fix,
                        "moved": bool(f >= MOVE_BAR),
                        "agree": bool((f >= MOVE_BAR) == (f_fix >= MOVE_BAR))})
        crit = criteria(grids, vr, w)
        row.update({k: v for k, v in crit.items()
                    if k.startswith(("criterion", "n_"))})
        vrow = vr_shape(vr, w)
        b_ok, b_why = criterion_b(vrow)
        row["criterion_b"] = b_ok
        row["criterion_b_why"] = b_why
        row["base15_q2"] = vrow["base15_q2"]
        row["tail_ratio"] = vrow["tail_ratio_120_over_30"]
        row["d010_branch"] = d010_branch(crit["criterion_a"],
                                         crit["criterion_c"], b_ok,
                                         row["cost_ratio"])
        rows.append(row)
    return pd.DataFrame(rows)


#: Criterion (b) is judged by the same two facts reports 02/03 judged it by:
#: the curve must keep DECLINING past q=30 rather than sitting on a floor, and
#: it must SURVIVE coarser base sampling rather than marching back toward 1.
#: The thresholds below are not new science — they are calibrated so the rule
#: reproduces the banked (b) verdict on the banked window (S-USED), which is
#: asserted in the unit tests. Module calibration for reference: a planted
#: AR(1) decays to 0.66, a planted bid-ask bounce flattens above 0.85.
B_TAIL_BAR = 0.90        # VR(120)/VR(30) below this = still declining
B_BASE15_BAR = 0.70      # VR at 15-min base still materially below 1


def criterion_b(vrow: dict) -> tuple[bool, str]:
    """D-010 (b), RECOMPUTED per window — the criterion a session change can
    actually move, and the reason D-024 exists."""
    tail, base15 = vrow["tail_ratio_120_over_30"], vrow["base15_q2"]
    declining = bool(tail < B_TAIL_BAR)
    survives = bool(base15 < B_BASE15_BAR)
    why = (f"tail={tail:.3f}{'<' if declining else '>='}{B_TAIL_BAR} "
           f"base15={base15:.3f}{'<' if survives else '>='}{B_BASE15_BAR}")
    return (declining and survives), why


def d010_branch(a: bool, c: bool, b: bool, cost_ratio: float) -> str:
    """The frozen D-010 branch set, plus D-024's added (b)-ONLY branch and the
    D-017/D-018 economic label."""
    if b and a and c:
        base = "REVERSION PRESENT"
    elif a and not b:
        base = "AMBIGUOUS / MICROSTRUCTURE"
    elif b and not a:
        base = "(b)-ONLY"
    else:
        base = "AMBIGUOUS / MICROSTRUCTURE"
    if cost_ratio == cost_ratio and cost_ratio > 1.0:
        base += " + ECONOMICALLY IMMATERIAL"
    return base


def verdict(summary: pd.DataFrame) -> dict:
    """Apply the frozen D-024 §6 branch table to one pair."""
    by = summary.set_index("window")

    def moved(w):
        return bool(by.loc[w, "moved"]) if w in by.index else False

    def agree(w):
        return bool(by.loc[w, "agree"]) if w in by.index else True

    def branch(w):
        """The D-010 VERDICT BRANCH — not the raw (a,c) tuple. D-024 §6 asks
        whether the branch changes, and with (b) failing and the effect an
        order of magnitude below cost, (a)/(c) wobbles do not move it."""
        if w not in by.index:
            return None
        return str(by.loc[w, "d010_branch"])

    q1_move, q1_branch = moved("R"), branch("R") != branch("U")
    q1 = "L-021 MATERIAL" if (q1_move or q1_branch) else "L-021 IMMATERIAL"
    if not agree("R"):
        q1 = "MOVE-IS-RELOCATION (inconclusive)"

    q2_targets = [w for w in ("S", "C") if w in by.index]
    q2_move = any(moved(w) for w in q2_targets)
    q2_branch = any(branch(w) != branch("R") for w in q2_targets)
    q2 = "A-013 MATERIAL" if (q2_move or q2_branch) else "A-013 IMMATERIAL"
    if any(not agree(w) for w in q2_targets):
        q2 = "MOVE-IS-RELOCATION (inconclusive)"

    # The placebo: a 30-minute unanchored displacement moving the statistic at
    # least as much as the 60-minute anchored one means the statistic is simply
    # window-sensitive and Q1 cannot be read.
    mh = float(by.loc["H", "move_free"]) if "H" in by.index else float("nan")
    mr = float(by.loc["R", "move_free"]) if "R" in by.index else float("nan")
    confounded = bool(mh >= mr) if (mh == mh and mr == mr) else False
    if confounded:
        q1 = "DISPLACEMENT-CONFOUNDED (inconclusive)"

    return {"Q1_L021": q1, "Q2_A013": q2,
            "placebo_move": mh, "rth_move": mr,
            "displacement_confounded": confounded}
