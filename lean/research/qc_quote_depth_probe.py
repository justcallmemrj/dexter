"""DEPTH RE-PROBE — is 2019 quote data usable, or was EXP-024's 2019 read an
artifact of probing the DEFERRED contract? (Corrects a design defect in
qc_quote_data_smoke.py; open thread 4a.)

NOT the trading algorithm and NOT part of any pre-registered protocol. Zero
orders, history only. Hypothesis-generating; advances no pair.

WHAT WENT WRONG. EXP-024 asked whether quotes reach back to research_start
(2019-06) by fetching the SEPTEMBER 2019 contract over a JUNE 2019 window. For
the equity micros September was still the deferred month then — the quarterly
roll is expiry-8d, i.e. 2019-06-13 — so the returned median spreads (MES 20
ticks, M2K 23 ticks, M2K delivering only 617 bars/day against 1,380) measure
back-month illiquidity, not quote-data quality. ZN's clean 1-tick read over the
same window is NOT affected, because Treasuries roll ahead of first notice, so
September was already ZN's active contract. That asymmetry is the tell, and it
is what this run tests instead of assuming.

THE DISCRIMINATOR. Three measurements per micro leg, and the comparison is
what carries the answer:

  1. M19 over the June window      — the FRONT contract, never before measured
  2. U19 over the SAME June window — the DEFERRED contract; must reproduce
                                     EXP-024's banked numbers exactly
  3. U19 over an August window     — the SAME contract once it HAS become
                                     front, which separates "this contract is
                                     illiquid" from "this contract was not yet
                                     front"

PRE-STATED READING, fixed before the numbers exist:

  * If M19 (June) is tight and U19 (June) is wide, and U19 tightens in August,
    the 2019 figures in EXP-024 were a back-month artifact, 2019 quote data is
    USABLE, and a battery may span research_start.
  * If M19 (June) is ALSO wide, the explanation is WRONG: either 2019 quote
    data is poor or the micros genuinely traded that wide a month after launch.
    Either way a battery must start later, and EXP-024's caveat becomes a
    finding rather than a defect.
  * "Tight" is fixed here at a median <= 3 ticks and "wide" at >= 10, chosen to
    leave a deliberate dead band so a marginal result reads INCONCLUSIVE rather
    than being argued either way after the fact.

ZN rides along on the ORIGINAL window as a pure reproduction gate: it must
return EXP-024's banked values (per_day 1377.9, rth_med 1.000, rth_eq1 1.000,
rth_n 3510). If it does not, the data path changed and nothing else in this run
is interpretable.

The June window intentionally keeps EXP-024's exact 2019-06-03 -> 2019-06-14
span so the U19 arms reproduce byte-for-byte. That span runs ~1 day past the
2019-06-13 splice, so the M19 arm carries about one post-roll day. That biases
M19 toward looking WORSE, i.e. against the explanation being tested, which is
the safe direction.
"""

from AlgorithmImports import *
from datetime import datetime, time, timedelta

import pandas as pd

JUN_START, JUN_END = datetime(2019, 6, 3), datetime(2019, 6, 14)   # EXP-024's span
AUG_START, AUG_END = datetime(2019, 8, 1), datetime(2019, 8, 12)

# leg, market, tick_size (price points; config/instruments.yaml, A-003 VERIFIED)
LEGS = {
    "MES": (Market.CME, 0.25),
    "M2K": (Market.CME, 0.10),
    "ZN": (Market.CBOT, 0.015625),
}

# tag -> (leg, contract year, contract month, window start, window end)
PROBES = [
    ("MES_M19_JUN", "MES", 2019, 6, JUN_START, JUN_END),   # front, new
    ("MES_U19_JUN", "MES", 2019, 9, JUN_START, JUN_END),   # deferred, reproduces
    ("MES_U19_AUG", "MES", 2019, 9, AUG_START, AUG_END),   # same contract, front
    ("M2K_M19_JUN", "M2K", 2019, 6, JUN_START, JUN_END),
    ("M2K_U19_JUN", "M2K", 2019, 9, JUN_START, JUN_END),
    ("M2K_U19_AUG", "M2K", 2019, 9, AUG_START, AUG_END),
    ("ZN_U19_JUN", "ZN", 2019, 9, JUN_START, JUN_END),     # reproduction gate
]

TIGHT_TICKS, WIDE_TICKS = 3.0, 10.0

# Chicago stamps; L-021's convention. Each filter is applied on the bar's OWN
# clock, so for ET-stamped index legs this selects 08:31-15:00 ET. That is
# stated rather than silently corrected: the comparison here is front vs
# deferred on IDENTICAL filters, which the offset does not disturb.
PRE_LO, PRE_HI = time(7, 20), time(8, 30)
RTH_LO, RTH_HI = time(8, 30), time(15, 0)


class QuoteDepthProbe(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2026, 4, 28)      # History-only, inside the clip
        self.set_end_date(2026, 4, 29)
        self.set_cash(100_000)
        self.set_benchmark(lambda dt: 0)
        self.results = {}
        self.med = {}
        try:
            self._run()
        except Exception as e:
            import traceback
            self.results["S_FATAL"] = str(e)[:110]
            self.results["S_FATAL_TB"] = traceback.format_exc()[-240:]

    def _run(self):
        canon = {}
        for leg, (market, _tick) in LEGS.items():
            fut = self.add_future(
                leg, Resolution.MINUTE, market=market, fill_forward=False,
                extended_market_hours=True,
                data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
                contract_depth_offset=0)
            fut.set_filter(0, 0)
            canon[leg] = fut.symbol

        for tag, leg, year, month, start, end in PROBES:
            sym = self._resolve(canon[leg], year, month, start)
            if sym is None:
                self.results["S_" + tag] = "FAIL|no contract"
                continue
            tick = LEGS[leg][1]
            self._measure(tag, tick, lambda: self.history(
                QuoteBar, sym, start, end, Resolution.MINUTE,
                fill_forward=False, extended_market_hours=True))

        self._verdict()

    def _verdict(self):
        def band(v):
            if v is None:
                return "NA"
            if v <= TIGHT_TICKS:
                return "TIGHT"
            return "WIDE" if v >= WIDE_TICKS else "MID"

        parts = []
        confirmed, contradicted = 0, 0
        for leg in ("MES", "M2K"):
            m = self.med.get(f"{leg}_M19_JUN")
            d = self.med.get(f"{leg}_U19_JUN")
            a = self.med.get(f"{leg}_U19_AUG")
            parts.append(f"{leg}:front={band(m)}/deferred={band(d)}/aug={band(a)}")
            if band(m) == "TIGHT" and band(d) == "WIDE":
                confirmed += 1
            elif band(m) == "WIDE":
                contradicted += 1

        if contradicted:
            call = "EXPLANATION_CONTRADICTED_2019_NOT_USABLE"
        elif confirmed == 2:
            call = "BACK_MONTH_ARTIFACT_CONFIRMED_2019_USABLE"
        else:
            call = "INCONCLUSIVE"
        self.results["S_VERDICT"] = f"{call}|" + "|".join(parts)

    def _measure(self, tag, tick, fetch):
        key = "S_" + tag
        try:
            h = fetch()
        except TypeError as e:
            self.results[key] = f"KWARG_REJECTED|{str(e)[:80]}"
            return
        except Exception as e:
            self.results[key] = f"ERROR|{type(e).__name__}|{str(e)[:70]}"
            return
        if h is None or len(h) == 0:
            self.results[key] = "EMPTY|no quote bars returned"
            return

        h = h.reset_index()
        cols = {c.lower(): c for c in h.columns}
        bid, ask = cols.get("bidclose"), cols.get("askclose")
        if bid is None or ask is None:
            self.results[key] = f"NO_BIDASK|cols={','.join(sorted(cols))[:70]}"
            return

        tcol = cols.get("time") or h.columns[1]
        idx = pd.DatetimeIndex(h[tcol])
        b = pd.Series(h[bid].astype(float).values, index=idx).sort_index()
        a = pd.Series(h[ask].astype(float).values, index=idx).sort_index()
        b, a = b[~b.index.duplicated("first")], a[~a.index.duplicated("first")]
        both = b.notna() & a.notna()
        if not bool(both.any()):
            self.results[key] = f"ALL_NAN|rows={len(b)}"
            return
        b, a = b[both], a[both]

        spread = (a - b) / tick
        t = b.index.time
        n_days = max(1, pd.DatetimeIndex(
            b.index[(t > RTH_LO) & (t <= RTH_HI)]).normalize().nunique())
        rth = spread[(t > RTH_LO) & (t <= RTH_HI)]
        pre = spread[(t > PRE_LO) & (t <= PRE_HI)]
        if len(rth):
            self.med[tag] = float(rth.median())

        self.results[key] = (
            f"{min(t).strftime('%H:%M')}-{max(t).strftime('%H:%M')}|"
            f"bars={len(b)}|days={n_days}|per_day={len(b) / n_days:.1f}|"
            f"rth_n={len(rth)}|{self._dist('rth', rth)}|"
            f"pre_n={len(pre)}|{self._dist('pre', pre)}|"
            f"nonpos={float((spread <= 0).mean()):.4f}")

    @staticmethod
    def _dist(name, s):
        if len(s) == 0:
            return f"{name}_med=NA|{name}_mean=NA|{name}_p90=NA|{name}_eq1=NA"
        return (f"{name}_med={s.median():.3f}|{name}_mean={s.mean():.3f}|"
                f"{name}_p90={s.quantile(0.90):.3f}|"
                f"{name}_eq1={float((s.round(3) == 1.0).mean()):.3f}|"
                f"{name}_sub1={float((s < 0.999).mean()):.4f}")

    def _resolve(self, canonical, year, month, window_start):
        """Probe from inside the fetch window first. The micros were listed
        2019-05-06, so an anchor-minus-85-days probe can predate their
        existence entirely and silently return nothing."""
        anchor = datetime(year, month, 1)
        probes = [window_start,
                  window_start - timedelta(days=7),
                  anchor - timedelta(days=5),
                  anchor - timedelta(days=25),
                  anchor - timedelta(days=55)]
        for probe in probes:
            if probe < datetime(2019, 5, 7):
                continue
            try:
                for s in self.future_chain_provider.get_future_contract_list(
                        canonical, probe):
                    if s.id.date.year == year and s.id.date.month == month:
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
