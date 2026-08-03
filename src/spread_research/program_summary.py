"""Notebook-13 body: aggregate the seven pair results into the program verdict.

This module deliberately owns NO new statistics. Every number it produces is
recomputed from artifacts already banked in `reports/machine_readable/` by the
notebook-02/03 runs, so the final summary is a CROSS-CHECK of validation
reports 02 and 03 rather than a re-typing of them. The unit tests pin the
published figures; if a report and its own CSV ever disagree, the test fails.

Cost accounting follows the same rule the reports used: one tick crossed on
each leg on entry and on exit, the second leg weighted by the pair's own median
hedge ratio, expressed in bps of leg-A notional. Treasury costs are derived here
from the VERIFIED tick specifications (A-003). Index-pair costs are carried as
the documented band from validation report 02 §5 because two of the three index
second legs (MNQ, M2K) have no representative notional established in-repo —
inventing one to make a table symmetric would be fabricating an input.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

MR_DIR = Path("reports/machine_readable")

#: The locked universe's seven pairs, in the order they were tested.
PAIRS = ("MES_MYM", "MES_MNQ", "MES_M2K", "ZF_ZN", "ZT_ZF", "ZN_ZB", "ZT_ZN")

#: Specifications that are look-ahead safe. S3 is the full-sample static-beta
#: diagnostic and is never evidence (D-010).
HONEST_SPECS = ("S1", "S2")

#: |t| bar from the D-010 verdict rule, criterion (a).
T_BAR = 3.0

#: One tick as bps of contract notional, from the VERIFIED tick specifications
#: (A-003, `data/metadata/contract_specifications.csv`) divided by the
#: representative notional documented in validation report 02 §5 / 03 §2.
#: MNQ and M2K are absent on purpose: no representative notional for them is
#: established anywhere in this repo.
TICK_BPS = {
    "MES": 1.25 / 25_000 * 1e4,      # SPX ~5,000 x $5
    "MYM": 0.50 / 20_000 * 1e4,      # DJIA ~40,000 x $0.50
    "ZT": 7.8125 / 204_000 * 1e4,
    "ZF": 7.8125 / 108_000 * 1e4,
    "ZN": 15.625 / 110_000 * 1e4,
    "ZB": 31.25 / 115_000 * 1e4,
}

#: Round-trip cost band for the index pairs, validation report 02 §5: crossing
#: both legs both ways plus the A-007 commission placeholder. A-007/A-008 are
#: UNVERIFIED, so this is an order-of-magnitude figure and is used as such.
INDEX_COST_BAND_BPS = (2.0, 3.0)


@dataclass(frozen=True)
class PairFacts:
    """Provenance for one pair. Verdicts are quoted from the decision log, not
    re-derived here — the verdict rule was applied once, under pre-registration."""

    pair: str
    asset_class: str
    segment: str
    anchor: str
    verdict: str
    decision: str
    experiment: str
    report: str
    run_name: str


REGISTRY: dict[str, PairFacts] = {
    "MES_MYM": PairFacts("MES_MYM", "index", "S&P-vs-Dow", "unit",
                         "A-006 FALSIFIED", "D-011", "EXP-008", "02 §1-§10",
                         "Alert Magenta Rabbit"),
    "MES_MNQ": PairFacts("MES_MNQ", "index", "S&P-vs-Nasdaq", "unit",
                         "A-006 FALSIFIED", "D-013", "EXP-009", "02 §11",
                         "Virtual Asparagus Pelican"),
    "MES_M2K": PairFacts("MES_M2K", "index", "S&P-vs-Russell", "unit",
                         "AMBIGUOUS / MICROSTRUCTURE", "D-015", "EXP-010",
                         "02 §12", "Well Dressed Green Tapir"),
    "ZF_ZN": PairFacts("ZF_ZN", "treasury", "5s10s", "vol_ratio",
                       "AMBIGUOUS / IMMATERIAL", "D-017", "EXP-011", "03",
                       "Calculating Tan Cormorant"),
    "ZT_ZF": PairFacts("ZT_ZF", "treasury", "2s5s", "vol_ratio",
                       "AMBIGUOUS / IMMATERIAL", "D-018", "EXP-012", "03",
                       "Swimming Yellow Green Guanaco"),
    "ZN_ZB": PairFacts("ZN_ZB", "treasury", "10s30s", "vol_ratio",
                       "AMBIGUOUS / IMMATERIAL", "D-018", "EXP-013", "03",
                       "Measured Magenta Goat"),
    "ZT_ZN": PairFacts("ZT_ZN", "treasury", "2s10s", "vol_ratio",
                       "AMBIGUOUS / IMMATERIAL", "D-018", "EXP-014", "03",
                       "Logical Magenta Termite"),
}


# --------------------------------------------------------------------------
# readers
# --------------------------------------------------------------------------

def _csv(pair: str, kind: str, root: Path | str = MR_DIR) -> pd.DataFrame:
    return pd.read_csv(Path(root) / f"nb02_{pair}_{kind}.csv")


def read_scalars(pair: str, root: Path | str = MR_DIR) -> dict[str, str]:
    """The QC summary-stat channel, parsed back to {key: raw string}."""
    df = _csv(pair, "scalars", root)
    return dict(zip(df["key"].astype(str), df["value"].astype(str)))


def parse_fields(value: str) -> dict[str, str]:
    """Split one pipe-delimited scalar into its named sub-fields. Positional
    fragments (no '=') are returned under their own index, e.g. 'PASS'."""
    out: dict[str, str] = {}
    for i, chunk in enumerate(str(value).split("|")):
        if "=" in chunk:
            k, v = chunk.split("=", 1)
            out[k] = v
        else:
            out[str(i)] = chunk
    return out


def read_conditional(pair: str, root: Path | str = MR_DIR) -> pd.DataFrame:
    return _csv(pair, "conditional_reversion", root)


def read_variance_ratio(pair: str, root: Path | str = MR_DIR) -> pd.DataFrame:
    return _csv(pair, "variance_ratio", root)


# --------------------------------------------------------------------------
# statistics recomputed from the banked grids
# --------------------------------------------------------------------------

def grid_counts(cond: pd.DataFrame, specs=HONEST_SPECS,
                t_bar: float = T_BAR) -> dict[str, int]:
    """Significant-cell accounting over the look-ahead-safe specs.

    Sign is taken from `mean_session_bps` — the quantity the session-clustered
    t-statistic actually refers to (D-010 amendment A2, defect 2)."""
    honest = cond[cond["spec"].isin(specs)]
    sig = honest[honest["t_clustered"].abs() >= t_bar]
    return {
        "cells": int(len(honest)),
        "significant": int(len(sig)),
        "significant_positive": int((sig["mean_session_bps"] > 0).sum()),
        "significant_negative": int((sig["mean_session_bps"] < 0).sum()),
    }


def s1_positive_cells(cond: pd.DataFrame, t_bar: float = T_BAR) -> tuple[int, int]:
    """(cells positive at t >= t_bar, cells in the S1 grid) — the headline
    criterion-(a) count quoted per pair in validation report 03 §1."""
    s1 = cond[cond["spec"] == "S1"]
    hit = s1[(s1["t_clustered"] >= t_bar) & (s1["mean_session_bps"] > 0)]
    return int(len(hit)), int(len(s1))


def largest_honest_effect(cond: pd.DataFrame, specs=HONEST_SPECS) -> pd.Series:
    """The best cell either look-ahead-safe spec produced anywhere in the grid.

    This is deliberately the MAXIMUM, not a significant maximum: the point of
    the number is that even the most flattering honest cell is immaterial."""
    honest = cond[cond["spec"].isin(specs)]
    return honest.loc[honest["mean_session_bps"].idxmax()]


def matched_elapsed_vr(vr: pd.DataFrame, series: str = "RES1",
                       target_minutes: int = 30,
                       base_steps=(1, 5, 15)) -> dict[int, float]:
    """Residual variance ratio at MATCHED elapsed time as the base bar coarsens.

    The honest comparison is elapsed minutes, not q: a 15-minute bar at q=15
    spans 225 minutes, not 15. For each base step the q closest to
    `target_minutes` of elapsed time is chosen. This is the pre-committed
    base-sampling check (D-010 criterion (b), made decisive by D-014/D-016)."""
    out: dict[int, float] = {}
    for base in base_steps:
        sel = vr[(vr["series"] == series)
                 & (vr["base_step_min"] == base)
                 & vr["vr"].notna()].copy()
        if sel.empty:
            continue
        sel["elapsed_err"] = (sel["base_step_min"] * sel["q"] - target_minutes).abs()
        out[base] = float(sel.loc[sel["elapsed_err"].idxmin(), "vr"])
    return out


def leg_vr(vr: pd.DataFrame, q: int = 2, base: int = 1) -> dict[str, float]:
    """Each leg's own variance ratio — the bounce/lead-lag baseline the residual
    must be compared against (near-miss #2: a leg VR above 1 is lagged
    adjustment, and a spread against it 'reverts' for free)."""
    out = {}
    for leg in ("LEGA", "LEGB"):
        sel = vr[(vr["series"] == leg) & (vr["base_step_min"] == base)
                 & (vr["q"] == q)]
        if not sel.empty:
            out[leg] = float(sel["vr"].iloc[0])
    return out


def open_clustering(scalars: dict[str, str]) -> float:
    """Share of |z| >= 2 crossings landing in the first 30 minutes of the
    session — the L-013 diagnostic."""
    clock = parse_fields(scalars["S_CLOCK"])
    return float(clock["0"].split(":")[1])


# --------------------------------------------------------------------------
# cost accounting
# --------------------------------------------------------------------------

def round_trip_spread_bps(leg_a: str, leg_b: str, beta: float) -> float:
    """Spread-crossing cost of one round trip, in bps of leg-A notional.

    One tick on each leg on the way in and on the way out, leg B weighted by the
    hedge ratio actually used. Commission (A-007) is NOT included: it is an
    unverified placeholder and is stated separately wherever it is used."""
    return 2.0 * (TICK_BPS[leg_a] + beta * TICK_BPS[leg_b])


def pair_cost_bps(pair: str, scalars: dict[str, str]) -> tuple[float, str]:
    """(round-trip cost in bps, basis) for one pair.

    Treasuries: derived from verified ticks and the pair's own median vol-ratio
    beta. Index pairs: the documented report-02 §5 band, whose LOW end is used
    so the cost comparison is as generous to the effect as the evidence allows.
    """
    facts = REGISTRY[pair]
    if facts.asset_class == "treasury":
        leg_a, leg_b = pair.split("_")
        beta = float(parse_fields(scalars["S_SPECS"])["S1_beta_med"])
        return (round_trip_spread_bps(leg_a, leg_b, beta),
                f"spec-derived (A-003 ticks, beta={beta:.3f}); spread only")
    return (INDEX_COST_BAND_BPS[0],
            f"report 02 §5 band {INDEX_COST_BAND_BPS[0]:.0f}-"
            f"{INDEX_COST_BAND_BPS[1]:.0f} bps incl. A-007 placeholder; "
            "low end used")


# --------------------------------------------------------------------------
# the program table
# --------------------------------------------------------------------------

def pair_row(pair: str, root: Path | str = MR_DIR) -> dict:
    """One row of the program verdict table, entirely recomputed from CSVs."""
    facts = REGISTRY[pair]
    scalars = read_scalars(pair, root)
    cond = read_conditional(pair, root)
    vr = read_variance_ratio(pair, root)

    align = parse_fields(scalars["S_ALIGN"])
    shock = parse_fields(scalars["S_PF_SHOCK"])
    counts = grid_counts(cond)
    n_pos, n_s1 = s1_positive_cells(cond)
    best = largest_honest_effect(cond)
    walk = matched_elapsed_vr(vr)
    legs = leg_vr(vr)
    cost, basis = pair_cost_bps(pair, scalars)
    effect = float(best["mean_session_bps"])

    return {
        "pair": pair,
        "asset_class": facts.asset_class,
        "segment": facts.segment,
        "anchor": facts.anchor,
        "bars": int(align["bars"]),
        "sessions": int(align["sessions"]),
        "gate": parse_fields(scalars["S_GATE"])["0"],
        "s1_positive_cells": n_pos,
        "s1_cells": n_s1,
        "sig_cells_honest": counts["significant"],
        "sig_positive": counts["significant_positive"],
        "sig_negative": counts["significant_negative"],
        "best_effect_bps": round(effect, 3),
        "best_spec": str(best["spec"]),
        "best_entry_z": float(best["entry_z"]),
        "best_horizon": int(best["horizon_bars"]),
        "best_t": float(best["t_clustered"]),
        "round_trip_cost_bps": round(cost, 3),
        "cost_basis": basis,
        "effect_over_cost": round(effect / cost, 3),
        "vr_res_1min": round(walk.get(1, float("nan")), 3),
        "vr_res_5min": round(walk.get(5, float("nan")), 3),
        "vr_res_15min": round(walk.get(15, float("nan")), 3),
        "vr_walk_x": round(walk[15] / walk[1], 2) if walk.get(1) else float("nan"),
        "leg_a_vr_q2": round(legs.get("LEGA", float("nan")), 3),
        "leg_b_vr_q2": round(legs.get("LEGB", float("nan")), 3),
        "open_30min_share": open_clustering(scalars),
        "roll_shock_med_bps": float(shock["med"]),
        "roll_shock_max_bps": float(shock["max"]),
        "verdict": facts.verdict,
        "decision": facts.decision,
        "experiment": facts.experiment,
        "report": facts.report,
        "run": facts.run_name,
    }


def program_table(pairs=PAIRS, root: Path | str = MR_DIR) -> pd.DataFrame:
    """The seven-pair verdict table behind report 13."""
    return pd.DataFrame([pair_row(p, root) for p in pairs])


def program_totals(table: pd.DataFrame, cells_per_pair: int = 60) -> dict:
    """Program-wide accounting, including the total-trials disclosure the
    notebook-13 mandate requires."""
    return {
        "pairs_tested": int(len(table)),
        "pairs_reversion_present": int((table["verdict"] == "REVERSION PRESENT").sum()),
        "pairs_effect_clears_cost": int((table["effect_over_cost"] >= 1.0).sum()),
        "cells_examined": int(len(table) * cells_per_pair),
        "cells_honest": int(table["sig_cells_honest"].sum()),
        "bars_min": int(table["bars"].min()),
        "bars_max": int(table["bars"].max()),
        "sessions_min": int(table["sessions"].min()),
        "sessions_max": int(table["sessions"].max()),
        "gates_passed": int((table["gate"] == "PASS").sum()),
        "largest_effect_bps": float(table["best_effect_bps"].max()),
        "pairs_effect_below_cost": int((table["effect_over_cost"] < 1.0).sum()),
    }
