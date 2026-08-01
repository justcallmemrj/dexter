"""QC cloud ROLL-AUDIT TOOL — notebook 01 evidence (A-004 / D-004).

NOT the trading algorithm (CLAUDE.md hard gate 1; prohibited until
`PROCEED TO LEAN BUILD`). Zero orders, zero positions. For every continuous-
contract mapping change (OpenInterest mode) over the research window it logs:

  DEXTER_ROLL {s, d, o, n, dte, po, pn, vs, gap, gp, ar}
    s   canonical ticker              d   first bar at/after the mapping flip
    o/n old/new contract (.value)     dte old contract days-to-expiry at roll
    po  last raw close of OLD contract at flip (3d minute History)
    pn  last raw close of NEW contract at flip  -> gap = pn-po, gp = gap %
    vs  new-contract volume share of (old+new) over trailing 3d
    ar  adjusted continuous series splice return % (first bar after flip vs
        last bar before) — artifact test: must be typical-overnight sized,
        NOT gap-sized, if BackwardsRatio splicing is clean
  DEXTER_ROLLSTATS {s, on_med_pct, on_mad_pct, n}
    per-symbol baseline: median/MAD of |first-bar-of-day returns| of the
    adjusted series — the yardstick for `ar`.

Implementation note: rolls are detected by polling `fut.mapped` for changes
(Symbol objects retained for History); Slice.symbol_changed_events is NOT used
because its old_symbol/new_symbol surface as plain strings in the Python
wrapper (runtime-error found 2026-08-01).

Same subscription settings as the research (research_config.yaml) and the
inventory audit; start respects L-009 (never before 2019-05-06 with MYM).
"""

from AlgorithmImports import *
import json
import statistics


class DexterRollAudit(QCAlgorithm):

    UNIVERSE = [
        ("MES", Market.CME),
        ("MNQ", Market.CME),
        ("M2K", Market.CME),
        ("MYM", Market.CBOT),  # L-009: data-bearing market
        ("ZT", Market.CBOT),
        ("ZF", Market.CBOT),
        ("ZN", Market.CBOT),
        ("ZB", Market.CBOT),
    ]

    def initialize(self):
        self.set_start_date(2019, 6, 1)   # research window; L-009 safe
        self.set_end_date(2026, 7, 31)    # free tier clips ~3mo before today
        self.set_cash(100_000)
        self.set_benchmark(lambda dt: 0)

        self.futs = {}
        self.prev_close = {}
        self.prev_day = {}
        self.on_returns = {}
        self.pending_roll = {}
        self.last_mapped = {}
        self.roll_rows = []
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
            fut.set_filter(0, 0)
            self.futs[fut.symbol] = fut
            self.on_returns[ticker] = []

    def on_data(self, slice: Slice):
        for sym, fut in self.futs.items():
            ticker = sym.id.symbol
            mapped = fut.mapped
            prev_m = self.last_mapped.get(sym)
            if mapped is not None and prev_m is not None                     and str(mapped) != str(prev_m):
                row = {"s": ticker, "d": str(self.time)[:16],
                       "o": str(prev_m.value), "n": str(mapped.value)}
                try:
                    row["dte"] = (prev_m.id.date - self.time).days
                except Exception:
                    row["dte"] = None
                try:
                    h = self.history([prev_m, mapped], timedelta(days=3),
                                     Resolution.MINUTE)
                    if not h.empty and "close" in h.columns:
                        for s_, key in ((prev_m, "po"), (mapped, "pn")):
                            try:
                                row[key] = round(
                                    float(h.loc[s_]["close"].iloc[-1]), 6)
                            except Exception:
                                row[key] = None
                        try:
                            vo = float(h.loc[prev_m]["volume"].sum())
                            vn = float(h.loc[mapped]["volume"].sum())
                            row["vs"] = (round(vn / (vo + vn), 3)
                                         if (vo + vn) > 0 else None)
                        except Exception:
                            row["vs"] = None
                except Exception as e:
                    row["err"] = str(e)[:40]
                if row.get("po") is not None and row.get("pn") is not None:
                    row["gap"] = round(row["pn"] - row["po"], 6)
                    row["gp"] = round(
                        (row["pn"] / row["po"] - 1.0) * 100.0, 4)
                self.pending_roll[sym] = row
            if mapped is not None:
                self.last_mapped[sym] = mapped

            bar = slice.bars.get(sym)
            if bar is None:
                continue
            c = float(bar.close)
            pc = self.prev_close.get(sym)
            d = bar.end_time.date()
            prev_d = self.prev_day.get(sym)
            if prev_d is not None and d != prev_d and pc:
                self.on_returns[ticker].append(abs(c / pc - 1.0))
            self.prev_day[sym] = d
            row = self.pending_roll.pop(sym, None)
            if row is not None:
                if pc:
                    row["ar"] = round((c / pc - 1.0) * 100.0, 4)
                self.roll_rows.append(row)
            self.prev_close[sym] = c

    def on_end_of_algorithm(self):
        self.log("DEXTER_ROLLAUDIT_BEGIN")
        for row in self.roll_rows:
            self.log("DEXTER_ROLL " + json.dumps(row, separators=(",", ":")))
        for ticker, arr in self.on_returns.items():
            if arr:
                med = statistics.median(arr)
                mad = statistics.median([abs(x - med) for x in arr])
                self.log("DEXTER_ROLLSTATS " + json.dumps(
                    {"s": ticker, "on_med_pct": round(med * 100.0, 4),
                     "on_mad_pct": round(mad * 100.0, 4), "n": len(arr)},
                    separators=(",", ":")))
        self.log("DEXTER_ROLLAUDIT_END")
