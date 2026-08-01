"""QC cloud ACCEPTANCE TEST for the own-splice constructor (D-009).

NOT the trading algorithm (CLAUDE.md gate 1). Zero orders. Runs the ACTUAL
shipped module (src/spread_research/roll_adjustment.py, uploaded as a second
project file) against real per-contract minute data:

1. Build OUR roll schedule for the symbol's quarterly chain
   (index: 8 days pre-expiry; treasuries: last business day of prior month).
2. Resolve each contract Symbol via future_chain_provider; fetch per-contract
   minute closes (close-only — memory guard on the free node).
3. build_continuous() with median-ratio splice factors.
4. splice_audit() — the same artifact test that exposed QC's 40 bad factors.

Acceptance criterion: ZERO artifact flags on the constructed series for the
symbol whose QC-provided series was WORST (M2K: 19/28 data-side leaks).
Output via summary statistics (S_* keys) in on_end_of_algorithm.

Set SYMBOL/MARKET/CODES/IS_INDEX for the symbol under test.
"""

from AlgorithmImports import *
from datetime import datetime, time, timedelta

from roll_adjustment import (
    index_roll_schedule, parse_contract, splice_audit, third_friday,
    treasury_roll_schedule, build_continuous, last_business_day_of_month,
)
import pandas as pd


class OwnSpliceAcceptance(QCAlgorithm):

    SYMBOL = "M2K"
    MARKET = Market.CME
    IS_INDEX = True
    CODES = ["M2KM19", "M2KU19", "M2KZ19", "M2KH20", "M2KM20", "M2KU20",
             "M2KZ20", "M2KH21", "M2KM21", "M2KU21", "M2KZ21", "M2KH22",
             "M2KM22", "M2KU22", "M2KZ22", "M2KH23", "M2KM23", "M2KU23",
             "M2KZ23", "M2KH24", "M2KM24", "M2KU24", "M2KZ24", "M2KH25",
             "M2KM25", "M2KU25", "M2KZ25", "M2KH26", "M2KM26"]
    WINDOW_START = datetime(2019, 6, 1)

    def initialize(self):
        self.set_start_date(2026, 4, 28)   # History-only pattern (inside clip)
        self.set_end_date(2026, 4, 29)
        self.set_cash(100_000)
        self.set_benchmark(lambda dt: 0)
        self.results = {}
        fut = self.add_future(
            self.SYMBOL, Resolution.MINUTE, market=self.MARKET,
            fill_forward=False, extended_market_hours=True,
            data_mapping_mode=DataMappingMode.OPEN_INTEREST,
            data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
            contract_depth_offset=0)
        fut.set_filter(0, 0)
        try:
            self._run(fut)
        except Exception as e:
            self.results["S_FATAL"] = str(e)[:120]

    def _run(self, fut):
        if self.IS_INDEX:
            sched = index_roll_schedule(self.CODES, days_before=8,
                                        splice_time=time(10, 30), tz=None)
        else:
            sched = treasury_roll_schedule(self.CODES,
                                           splice_time=time(10, 30), tz=None)
        times = list(pd.to_datetime(sched["timestamp"]))
        starts = [self.WINDOW_START] + times
        ends = times + [datetime(2026, 4, 27)]

        segments = {}
        for i, code in enumerate(self.CODES):
            sym = self._resolve(fut.symbol, code)
            if sym is None:
                self.results["S_RESOLVE_FAIL"] = code
                return
            h = self.history(sym, starts[i] - timedelta(days=6),
                             ends[i] + timedelta(days=1), Resolution.MINUTE)
            if h is None or h.empty or "close" not in h.columns:
                self.results["S_DATA_FAIL"] = code
                return
            h = h.reset_index()
            tcol = "time" if "time" in h.columns else h.columns[1]
            s = pd.Series(h["close"].astype(float).values,
                          index=pd.DatetimeIndex(h[tcol])).sort_index()
            s = s[~s.index.duplicated(keep="first")]
            segments[code] = pd.DataFrame({"close": s})

        cont, table = build_continuous(segments, sched,
                                       price_cols=("close",))
        audit = splice_audit(cont["close"], sched, window_bars=390)

        merged = table.merge(audit, on="timestamp")
        n_flag = int(merged["artifact_flag"].sum())
        for _, r in merged.iterrows():
            key = "S_" + r["from_contract"] + "_" + \
                pd.Timestamp(r["timestamp"]).strftime("%Y%m%d")
            self.results[key] = (
                f"{int(r['artifact_flag'])}|{r['splice_ret_pct']}|"
                f"{round(r['factor'], 6)}|{r['method']}|{r['n_overlap']}")
        self.results["S_TOTAL"] = (
            f"rolls={len(merged)}|flags={n_flag}|bars={len(cont)}|"
            f"first={cont.index[0]}|last={cont.index[-1]}")

    def _resolve(self, canonical, code):
        _, month, year = parse_contract(code)
        if self.IS_INDEX:
            anchor = third_friday(year, month)
        else:
            anchor = last_business_day_of_month(year, month)
        for back in (25, 55, 85, 5):
            probe = datetime(anchor.year, anchor.month, anchor.day) - \
                timedelta(days=back)
            try:
                for s in self.future_chain_provider.get_future_contract_list(
                        canonical, probe):
                    if s.id.date.year == year and s.id.date.month == month:
                        return s
            except Exception:
                continue
        return None

    def on_data(self, slice: Slice):
        pass

    def on_end_of_algorithm(self):
        for k, v in self.results.items():
            self.set_summary_statistic(k, str(v))
