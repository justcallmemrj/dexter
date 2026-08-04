"""SMOKE TEST — does `history(..., extended_market_hours=True,
fill_forward=False)` deliver real pre-open bars? (D-024 part 3 precondition.)

NOT the trading algorithm and NOT part of the D-024 protocol. Zero orders, one
contract, a two-week window: this exists only to answer a mechanical question
before a full part-3 battery is spent, and it emits no reversion statistic of
any kind.

The question, and why it is not obvious. Notebook 15's S-CASH arm needs bars
before 08:30 CT. Two banked facts make that uncertain:

  1. `history()` on a CONTRACT symbol does NOT inherit the canonical
     subscription's config — every banked run passes
     `add_future(..., fill_forward=False, extended_market_hours=True)` and
     still gets a delivered span of 08:31-16:00 (LEAN's regular session).
  2. LEAN's own default is `fillForward=TRUE`. So an extended fetch that does
     not pin it would return the pre-open block as forward-filled REPEATS of
     the last regular-session print — which look like bars, count like bars,
     and would make both the coverage finding and the S-CASH grid meaningless.

So this run measures four things per fetch mode: the delivered time-of-day
span, bars per trading day, how many bars land in the 07:21-08:30 CT block, and
what fraction of that block's closes are IDENTICAL to the preceding close.
A high identical-close fraction is the fill-forward signature.
"""

from AlgorithmImports import *
from datetime import datetime, time, timedelta

import pandas as pd

LEG = "ZN"
CODE_YEAR, CODE_MONTH = 2024, 12          # ZNZ24, front through mid-Nov 2024
PROBE_START = datetime(2024, 11, 1)
PROBE_END = datetime(2024, 11, 15)

PRE_LO, PRE_HI = time(7, 20), time(8, 30)   # the S-CASH block, Chicago stamps


class ExtendedFetchSmoke(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2026, 4, 28)      # History-only, inside the clip
        self.set_end_date(2026, 4, 29)
        self.set_cash(100_000)
        self.set_benchmark(lambda dt: 0)
        self.results = {}
        try:
            self._run()
        except Exception as e:
            import traceback
            self.results["S_FATAL"] = str(e)[:110]
            self.results["S_FATAL_TB"] = traceback.format_exc()[-240:]

    def _run(self):
        fut = self.add_future(
            LEG, Resolution.MINUTE, market=Market.CBOT, fill_forward=False,
            extended_market_hours=True,
            data_mapping_mode=DataMappingMode.OPEN_INTEREST,
            data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
            contract_depth_offset=0)
        fut.set_filter(0, 0)

        sym = self._resolve(fut.symbol)
        if sym is None:
            self.results["S_RESOLVE"] = "FAIL|no contract"
            return
        self.results["S_RESOLVE"] = f"OK|{LEG}{CODE_MONTH:02d}{CODE_YEAR}"

        # (a) the banked call, exactly as parts 1-2 issue it
        self._measure("REG", lambda: self.history(
            sym, PROBE_START, PROBE_END, Resolution.MINUTE))

        # (b) the part-3 call. If the kwargs are rejected the run says so
        # loudly rather than silently falling back to (a).
        def ext():
            return self.history(sym, PROBE_START, PROBE_END, Resolution.MINUTE,
                                fill_forward=False, extended_market_hours=True)
        self._measure("EXT", ext)

        reg, ext_ = self.results.get("S_REG", ""), self.results.get("S_EXT", "")
        differs = reg.split("|")[0] != ext_.split("|")[0]
        self.results["S_VERDICT"] = (
            f"spans_differ={int(differs)}|"
            f"proceed={'YES' if differs else 'NO_extended_had_no_effect'}")

    def _measure(self, tag, fetch):
        try:
            h = fetch()
        except TypeError as e:
            self.results["S_" + tag] = f"KWARG_REJECTED|{str(e)[:80]}"
            return
        if h is None or h.empty or "close" not in h.columns:
            self.results["S_" + tag] = "EMPTY|no bars returned"
            return
        h = h.reset_index()
        tcol = "time" if "time" in h.columns else h.columns[1]
        s = pd.Series(h["close"].astype(float).values,
                      index=pd.DatetimeIndex(h[tcol])).sort_index()
        s = s[~s.index.duplicated("first")]

        t = s.index.time
        # Trading days = dates carrying a REGULAR-session bar, the same
        # denominator session_window_report uses. Counting every calendar date
        # would include Sunday evenings and deflate every rate.
        reg_dates = pd.DatetimeIndex(
            s.index[(t > time(8, 30)) & (t <= time(16, 0))]).normalize()
        n_days = max(1, reg_dates.nunique())

        blk = s[(t > PRE_LO) & (t <= PRE_HI)]
        span_min = (PRE_HI.hour * 60 + PRE_HI.minute
                    - PRE_LO.hour * 60 - PRE_LO.minute)
        # Fill-forward signature: a synthetic bar repeats the previous close.
        stale = float((blk.diff() == 0).mean()) if len(blk) > 1 else float("nan")

        self.results["S_" + tag] = (
            f"{min(t).strftime('%H:%M')}-{max(t).strftime('%H:%M')}|"
            f"bars={len(s)}|days={n_days}|per_day={len(s) / n_days:.1f}|"
            f"pre={len(blk)}|pre_per_day={len(blk) / n_days:.1f}|"
            f"pre_density={len(blk) / n_days / span_min:.3f}|"
            f"pre_stale={stale:.3f}")

    def _resolve(self, canonical):
        anchor = datetime(CODE_YEAR, CODE_MONTH, 1)
        for back in (25, 55, 85, 5):
            probe = anchor - timedelta(days=back)
            try:
                for s in self.future_chain_provider.get_future_contract_list(
                        canonical, probe):
                    if (s.id.date.year == CODE_YEAR
                            and s.id.date.month == CODE_MONTH):
                        return s
            except Exception:
                continue
        return None

    def on_data(self, slice):
        pass

    def on_end_of_algorithm(self):
        self.results["S_KEYS"] = str(len(self.results) + 1)
        for k, v in self.results.items():
            self.set_summary_statistic(k, str(v)[:960])
