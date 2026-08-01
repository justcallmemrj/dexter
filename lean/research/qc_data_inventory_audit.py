"""QC cloud DATA-AUDIT TOOL — verifies A-001/A-002 (minute-data coverage).

This is NOT the trading algorithm (CLAUDE.md hard gate 1: that remains
prohibited until `PROCEED TO LEAN BUILD`). It places no orders, holds no
positions, and only counts bars: per-symbol minute-bar coverage, first/last
bar timestamps, per-year bar counts, and continuous-mapping roll counts for
the locked 8-instrument universe. Output = one compact JSON log line per
symbol at end of algorithm (marker DEXTER_ROW2), ingested by
scripts/ingest_qc_inventory.py.

This file mirrors the code of the CANONICAL run ("inventory-audit-2", QC
project dexter-rv-research 34720894, 2026-08-01; results in
reports/validation/00_qc_data_inventory.md).

Platform facts this code encodes (L-009):
- MYM data lives under Market.CBOT (Market.CME serves nothing);
- a continuous subscription starting before the 2019-05-06 micro launch never
  initializes for MYM (zero bars) -> start at the research window (2019-06-01).
Mapping/normalization mirror config/research_config.yaml (OpenInterest /
BackwardsRatio) so the audited series is the same series the research uses.
"""

from AlgorithmImports import *
import json


class DexterDataInventoryAudit(QCAlgorithm):

    UNIVERSE = [
        ("MES", Market.CME),
        ("MNQ", Market.CME),
        ("M2K", Market.CME),
        ("MYM", Market.CBOT),  # data-bearing market per diagnostic (L-009)
        ("ZT", Market.CBOT),
        ("ZF", Market.CBOT),
        ("ZN", Market.CBOT),
        ("ZB", Market.CBOT),
    ]

    def initialize(self):
        # Research window start (config research_start). Do NOT start before
        # 2019-05-06 while MYM is subscribed (L-009).
        self.set_start_date(2019, 6, 1)
        self.set_end_date(2026, 7, 31)   # free tier clips ~3mo before today — the
        self.set_cash(100_000)           # audit reports the ACTUAL last bar seen.
        self.set_benchmark(lambda dt: 0)  # no benchmark data subscription

        self.stats = {}
        self.futs = []
        for ticker, market in self.UNIVERSE:
            fut = self.add_future(
                ticker,
                Resolution.MINUTE,
                market=market,
                fill_forward=False,
                extended_market_hours=True,
                data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
                contract_depth_offset=0,
            )
            fut.set_filter(0, 0)  # continuous series only; no chain subscriptions
            self.futs.append(fut)
            self.stats[ticker] = {
                "sym": ticker, "first": None, "last": None, "total": 0,
                "per_year": {}, "rolls_per_year": {}, "last_mapped": None,
                "mapped_first": None, "mapped_last": None,
            }

    def on_data(self, slice: Slice):
        for fut in self.futs:
            ticker = fut.symbol.id.symbol
            st = self.stats[ticker]
            bar = slice.bars.get(fut.symbol)
            if bar is not None:
                t = str(bar.end_time)
                if st["first"] is None:
                    st["first"] = t
                st["last"] = t
                st["total"] += 1
                y = str(bar.end_time.year)
                st["per_year"][y] = st["per_year"].get(y, 0) + 1
            mapped = str(fut.mapped) if fut.mapped is not None else None
            if mapped is not None and mapped != st["last_mapped"]:
                if st["last_mapped"] is not None:
                    y = str(self.time.year)
                    st["rolls_per_year"][y] = st["rolls_per_year"].get(y, 0) + 1
                else:
                    st["mapped_first"] = mapped
                st["last_mapped"] = mapped
                st["mapped_last"] = mapped

    def on_end_of_algorithm(self):
        self.log("DEXTER_INVENTORY2_BEGIN")
        for ticker, _ in self.UNIVERSE:
            st = dict(self.stats[ticker])
            st.pop("last_mapped", None)
            self.log("DEXTER_ROW2 " + json.dumps(st, separators=(",", ":")))
        self.log("DEXTER_INVENTORY2_END")
