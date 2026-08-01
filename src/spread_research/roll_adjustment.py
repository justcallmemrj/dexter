"""Roll adjustment: OWN-SPLICE continuous construction + splice audits (D-009).

History: this module originally only VERIFIED QC-provided continuous series
('roll_gap_report'), on the premise that QC's adjustment could be trusted.
The notebook-01 roll audit falsified that premise (A-004 FALSIFIED,
validation report 01): QC's adjusted series carry bad factors at 40/220
rolls (M2K 19, MYM 14, MNQ 4, MES 3). Per D-009 the research therefore
builds its own continuous series from per-contract raw segments:

- quarterly index expiries (3rd Friday — CME-verified termination rule) and
  treasury delivery months are derived from contract codes;
- roll dates are OURS: index rolls 'days_before' calendar days pre-expiry
  (default 8 — the Thursday before expiry week, where liquidity actually
  migrates), treasuries roll on the last business day of the month before
  the delivery month. QC's OpenInterest flip (expiry-day open for index
  micros; see validation report 01 §2) is NOT used;
- splice factors are measured from overlapping simultaneous bars (median
  ratio — robust to single bad prints) with an explicit last-close fallback,
  never a silent 1.0;
- BackwardsRatio semantics: the LATEST segment keeps executable raw prices;
  earlier segments are multiplied by the cumulative downstream factors, so
  within-segment returns are preserved exactly;
- every constructed series ships with a splice table and must pass
  'splice_audit()' — the same artifact test the QC audit used — before any
  notebook consumes it.

Schedule frames share one shape everywhere (identical to
'contract_mapping.detect_mapping_changes' output): columns
'[timestamp, from_contract, to_contract]'.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

import numpy as np
import pandas as pd

MONTH_CODES = {"H": 3, "M": 6, "U": 9, "Z": 12}

# ---------------------------------------------------------------------------
# Contract-code arithmetic (quarterly cycle only — the locked universe)
# ---------------------------------------------------------------------------


def parse_contract(code: str) -> tuple[str, int, int]:
    """'M2KZ25' -> ('M2K', 12, 2025). Last 3 chars = month letter + 2-digit
    year (pivot 20xx — fine for this project's 2019+ range)."""
    if len(code) < 4:
        raise ValueError(f"contract code too short: {code!r}")
    root, letter, yy = code[:-3], code[-3], code[-2:]
    if letter not in MONTH_CODES or not yy.isdigit() or not root:
        raise ValueError(f"unparseable quarterly contract code: {code!r}")
    return root, MONTH_CODES[letter], 2000 + int(yy)


def third_friday(year: int, month: int) -> date:
    """Index expiry day: the 3rd Friday of the contract month (CME-verified
    termination: 9:30 a.m. ET that day)."""
    d = date(year, month, 1)
    first_friday = d + timedelta(days=(4 - d.weekday()) % 7)
    return first_friday + timedelta(days=14)


def index_expiry(code: str) -> date:
    _, month, year = parse_contract(code)
    return third_friday(year, month)


def prior_business_day(d: date, holidays: frozenset[date] | set[date] = frozenset()) -> date:
    """Step back to a Mon-Fri that is not in 'holidays'. Without a holiday
    list, exchange holidays are still survivable — the factor window uses
    actually-available bars — but a splice ON a holiday spans a longer quiet
    boundary and can trip the conservative audit floor (observed: ZNM21 roll
    scheduled 2021-05-31 Memorial Day, -8bp boundary return flagged at the
    5bp floor). Pass CME holidays to keep splices on trading days."""
    while d.weekday() >= 5 or d in holidays:
        d -= timedelta(days=1)
    return d


def last_business_day_of_month(year: int, month: int,
                               holidays: frozenset[date] | set[date] = frozenset()) -> date:
    nxt = date(year + (month == 12), (month % 12) + 1, 1)
    return prior_business_day(nxt - timedelta(days=1), holidays)


def index_roll_schedule(codes: list[str], *, days_before: int = 8,
                        splice_time: time = time(14, 30),
                        tz: str = "UTC",
                        holidays: frozenset[date] | set[date] = frozenset()) -> pd.DataFrame:
    """OUR index roll calendar: roll 'days_before' calendar days before each
    contract's 3rd-Friday expiry (weekend-snapped back), at 'splice_time'.
    'codes' = consecutive quarterly contracts, e.g. ['MESH24','MESM24',...]."""
    ordered = sorted(codes, key=index_expiry)
    rows = []
    for old, new in zip(ordered[:-1], ordered[1:]):
        roll_d = prior_business_day(index_expiry(old) - timedelta(days=days_before), holidays)
        rows.append({
            "timestamp": pd.Timestamp(datetime.combine(roll_d, splice_time), tz=tz),
            "from_contract": old, "to_contract": new,
        })
    return pd.DataFrame(rows, columns=["timestamp", "from_contract", "to_contract"])


def treasury_roll_schedule(codes: list[str], *, splice_time: time = time(14, 30),
                           tz: str = "UTC",
                           holidays: frozenset[date] | set[date] = frozenset()) -> pd.DataFrame:
    """OUR treasury roll calendar: roll on the last business day of the month
    BEFORE the delivery month (precedes first-notice; liquidity migrates in
    that window per validation report 01 §2)."""
    def delivery(code: str) -> tuple[int, int]:
        _, month, year = parse_contract(code)
        return year, month

    ordered = sorted(codes, key=lambda c: delivery(c))
    rows = []
    for old, new in zip(ordered[:-1], ordered[1:]):
        y, m = delivery(old)
        prev_y, prev_m = (y - 1, 12) if m == 1 else (y, m - 1)
        roll_d = last_business_day_of_month(prev_y, prev_m, holidays)
        rows.append({
            "timestamp": pd.Timestamp(datetime.combine(roll_d, splice_time), tz=tz),
            "from_contract": old, "to_contract": new,
        })
    return pd.DataFrame(rows, columns=["timestamp", "from_contract", "to_contract"])


# ---------------------------------------------------------------------------
# Splice factors and continuous construction
# ---------------------------------------------------------------------------


def measure_splice_factor(old_close: pd.Series, new_close: pd.Series,
                          ts: pd.Timestamp, *, window_bars: int = 390,
                          min_overlap: int = 30) -> tuple[float, int, str]:
    """Ratio factor new/old at splice time 'ts'.

    Primary: median of bar-by-bar ratios over overlapping timestamps within
    the trailing 'window_bars' bars strictly before 'ts' (robust to a bad
    print on either leg). Fallback (overlap < min_overlap): ratio of the two
    last closes before 'ts', flagged via method='last_close_ratio'.
    Raises when either leg has no data — a splice factor is never silent.
    """
    old_w = old_close.dropna().loc[old_close.index < ts].tail(window_bars)
    new_w = new_close.dropna().loc[new_close.index < ts].tail(window_bars)
    overlap = old_w.index.intersection(new_w.index)
    if len(overlap) >= min_overlap:
        ratio = new_w.loc[overlap] / old_w.loc[overlap]
        return float(ratio.median()), int(len(overlap)), "median_ratio"
    if len(old_w) and len(new_w):
        return (float(new_w.iloc[-1] / old_w.iloc[-1]),
                int(min(len(old_w), len(new_w))), "last_close_ratio")
    raise ValueError(
        f"no data to measure splice factor at {ts} "
        f"(old bars={len(old_w)}, new bars={len(new_w)})")


def _validate_schedule(segments: dict[str, pd.DataFrame],
                       schedule: pd.DataFrame) -> list[str]:
    if schedule.empty:
        raise ValueError("empty roll schedule")
    ts = pd.to_datetime(schedule["timestamp"])
    if not ts.is_monotonic_increasing:
        raise ValueError("roll schedule timestamps must be ascending")
    chain = [schedule.iloc[0]["from_contract"]]
    for _, row in schedule.iterrows():
        if row["from_contract"] != chain[-1]:
            raise ValueError(
                f"schedule not chained at {row['timestamp']}: expected "
                f"from_contract={chain[-1]!r}, got {row['from_contract']!r}")
        chain.append(row["to_contract"])
    missing = [c for c in chain if c not in segments]
    if missing:
        raise ValueError(f"missing per-contract segments for {missing}")
    return chain


def build_continuous(segments: dict[str, pd.DataFrame], schedule: pd.DataFrame,
                     *, price_cols: tuple[str, ...] = ("open", "high", "low", "close"),
                     factor_window_bars: int = 390, min_overlap: int = 30,
                     factors: dict[tuple[str, str], float] | None = None,
                     ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the own-splice continuous series (BackwardsRatio semantics).

    segments : {contract_code: canonical OHLCV frame (tz-aware, sorted)}
    schedule : [timestamp, from_contract, to_contract] — OUR roll calendar.
               Bars strictly before a roll timestamp belong to from_contract;
               bars at/after it to to_contract.
    factors  : optional {(from, to): factor} overrides (e.g. QC-audit-measured
               pn/po); anything absent is measured from the segments.

    Returns (continuous frame incl. mapped_contract, splice table). The
    LATEST segment keeps raw executable prices; each earlier segment is
    multiplied by the cumulative product of all downstream factors. The
    splice table records factor, provenance, and the realized splice return
    of the constructed close series; run 'splice_audit' for the formal check.
    """
    chain = _validate_schedule(segments, schedule)
    times = list(pd.to_datetime(schedule["timestamp"]))
    bounds = [None] + times + [None]

    per_roll: list[dict] = []
    for k, (_, row) in enumerate(schedule.iterrows()):
        key = (row["from_contract"], row["to_contract"])
        ts = times[k]
        if factors is not None and key in factors:
            f, n, method = float(factors[key]), 0, "provided"
        else:
            f, n, method = measure_splice_factor(
                segments[key[0]]["close"], segments[key[1]]["close"], ts,
                window_bars=factor_window_bars, min_overlap=min_overlap)
        if not np.isfinite(f) or f <= 0:
            raise ValueError(f"invalid splice factor {f} at {ts} for {key}")
        per_roll.append({"timestamp": ts, "from_contract": key[0],
                         "to_contract": key[1], "factor": f,
                         "n_overlap": n, "method": method})

    # cumulative multiplier for segment i = product of factors of rolls i..end
    mults = np.cumprod([r["factor"] for r in per_roll][::-1])[::-1]
    pieces = []
    for i, contract in enumerate(chain):
        seg = segments[contract]
        lo, hi = bounds[i], bounds[i + 1]
        piece = seg if lo is None else seg.loc[seg.index >= lo]
        if hi is not None:
            piece = piece.loc[piece.index < hi]
        if piece.empty:
            raise ValueError(f"segment {contract} has no bars in its window "
                             f"[{lo}, {hi})")
        piece = piece.copy()
        mult = float(mults[i]) if i < len(mults) else 1.0
        for col in price_cols:
            if col in piece.columns:
                piece[col] = piece[col].astype(float) * mult
        piece["mapped_contract"] = contract
        pieces.append(piece)

    out = pd.concat(pieces).sort_index()
    if out.index.duplicated().any():
        raise ValueError("constructed series has duplicate timestamps")

    close = out["close"]
    for r in per_roll:
        ts = r["timestamp"]
        before = close.loc[close.index < ts]
        after = close.loc[close.index >= ts]
        r["factor_gap_pct"] = round((r["factor"] - 1.0) * 100.0, 4)
        r["splice_ret_pct"] = (
            round((float(after.iloc[0]) / float(before.iloc[-1]) - 1.0) * 100.0, 4)
            if len(before) and len(after) else np.nan)
    return out, pd.DataFrame(per_roll)


def splice_audit(close: pd.Series, schedule: pd.DataFrame, *,
                 window_bars: int = 390, mad_mult: float = 10.0,
                 min_flag_threshold: float = 5e-4) -> pd.DataFrame:
    """Formal artifact test of a continuous close series at scheduled rolls —
    the same test that exposed the QC data defects (validation report 01 §3).

    For each roll timestamp: the boundary-crossing log return vs the local
    MAD of log returns (±window_bars, splice bar excluded). Flag when
    |splice| > max(mad_mult * 1.4826 * MAD, min_flag_threshold) — the
    absolute floor (default 5 bp) keeps quiet-market splices honest where
    local MAD ~ 0 (e.g. ZT/ZF midnights).
    """
    logc = np.log(close.dropna().astype(float))
    rets = logc.diff()
    rows = []
    for _, ev in schedule.iterrows():
        ts = ev["timestamp"]
        before = logc.loc[logc.index < ts]
        after = logc.loc[logc.index >= ts]
        if not len(before) or not len(after):
            rows.append({"timestamp": ts, "splice_log_ret": np.nan,
                         "local_mad": np.nan, "threshold": np.nan,
                         "artifact_flag": True, "note": "no data at boundary"})
            continue
        r = float(after.iloc[0] - before.iloc[-1])
        i = rets.index.get_indexer([after.index[0]])[0]
        local = pd.concat([rets.iloc[max(0, i - window_bars):i],
                           rets.iloc[i + 1:i + 1 + window_bars]]).dropna()
        mad = float((local - local.median()).abs().median()) if len(local) else np.nan
        thr = max(mad_mult * 1.4826 * mad, min_flag_threshold) if mad == mad \
            else min_flag_threshold
        rows.append({"timestamp": ts, "splice_log_ret": r, "local_mad": mad,
                     "threshold": thr, "artifact_flag": bool(abs(r) > thr),
                     "note": ""})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Verification of EXTERNALLY-provided continuous series (kept from v0)
# ---------------------------------------------------------------------------


def roll_gap_report(raw_close: pd.Series, adjusted_close: pd.Series,
                    roll_events: pd.DataFrame, window_bars: int = 30) -> pd.DataFrame:
    """For each roll event: raw price gap, adjusted-series return at the event,
    and whether the adjusted return looks like an artifact (exceeds 10x the
    local MAD of adjusted returns). Used to audit provider series; the
    constructed-series check is 'splice_audit'."""
    adj_ret = np.log(adjusted_close).diff()
    rows = []
    for _, ev in roll_events.iterrows():
        ts = ev["timestamp"]
        if ts not in raw_close.index:
            continue
        i = raw_close.index.get_loc(ts)
        if isinstance(i, slice) or i == 0:
            continue
        raw_gap = float(raw_close.iloc[i] - raw_close.iloc[i - 1])
        local = adj_ret.iloc[max(0, i - window_bars):i + window_bars].dropna()
        mad = float((local - local.median()).abs().median()) or np.nan
        ev_ret = float(adj_ret.iloc[i]) if not np.isnan(adj_ret.iloc[i]) else np.nan
        rows.append({
            "timestamp": ts,
            "from_contract": ev.get("from_contract"),
            "to_contract": ev.get("to_contract"),
            "raw_price_gap": raw_gap,
            "adjusted_log_return_at_roll": ev_ret,
            "local_mad": mad,
            "artifact_flag": bool(mad == mad and ev_ret == ev_ret
                                  and abs(ev_ret) > 10 * mad * 1.4826),
        })
    return pd.DataFrame(rows)
