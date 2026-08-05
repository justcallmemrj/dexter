"""SMOKE TEST — does QC deliver minute QUOTE bars for our universe, and what
does the top-of-book spread actually measure? (A-008 / open-thread-4a precondition.)

NOT the trading algorithm and NOT part of any pre-registered protocol. Zero
orders, three legs, two-week windows: this exists only to answer mechanical
questions before a quote-data battery is designed, and it emits no reversion
statistic of any kind. Whatever it finds is hypothesis-generating and cannot
advance any pair.

The question, and why it is not obvious. D-025 made the pre-open cost bar the
program's binding uncertainty: A-008 assumes a 1-tick top-of-book spread for
all eight instruments, config scopes that to "liquid RTH", and every S-CASH
cost ratio in report 15 therefore rests on an assumption known not to apply
where it was applied. Measuring it needs quote data the repo has never once
requested — there is no `QuoteBar`, `TickType` or `Resolution.TICK` anywhere in
src/, scripts/ or notebooks/. Four things are unknown and none is settled by
the docs, which this program has caught being wrong before (ES minute data
documented from 2009, served from 1997):

  1. Whether this free-tier project is served QuoteBars for futures AT ALL.
     Nominal availability in the AlgoSeek US Futures dataset is not the same
     as delivery to this tier, and the tier already clips end dates.
  2. Whether quotes reach back to research_start (2019-06). The micros
     launched 2019-05-06; quote history may be shallower than trade history.
  3. Whether quotes exist in the 07:21-08:30 CT pre-open block at all — the
     one block the whole thread is about. The banked extended-fetch smoke
     established that a REGULAR history call returns zero pre-open bars, so
     this must ride `extended_market_hours=True, fill_forward=False` for the
     same reasons D-024 documented: LEAN defaults fill_forward TRUE, and a
     forward-filled quote block would report a perfectly stable spread that is
     an artifact of repeats.
  4. What the spread actually IS. A-008 says 1 tick. That is the number this
     run can falsify, in RTH and pre-open separately.

Reported per leg and fetch mode: delivered span, bars/day, whether bid/ask
columns arrived populated, and the spread distribution IN TICKS (median, mean,
p90, and the fraction sitting at exactly one tick) for RTH and for the pre-open
block. Also the stale fraction, because a fill-forward block is the failure
mode that would make a tight measured spread meaningless, and the crossed /
zero-width fraction, because those are data defects rather than free money.

A-008 is a COST assumption, so the direction that matters is wider-than-1-tick.
A measured spread BELOW one tick is not a discovery, it is a sign the
measurement is wrong (top-of-book cannot be inside the minimum increment) and
this run flags it as such rather than banking it.
"""

from AlgorithmImports import *
from datetime import datetime, time, timedelta

import pandas as pd

# tick_size in PRICE POINTS, from config/instruments.yaml (A-003 VERIFIED
# against CME contract specs in a browser session). Treasuries are quoted per
# $100 face, so their ticks are the 1/32-family fractions, not decimals.
LEGS = [
    # leg,  market,        tick_size,   recent (Y, M),  early (Y, M)
    ("ZN",  Market.CBOT,   0.015625,    (2024, 12),     (2019, 9)),
    ("M2K", Market.CME,    0.10,        (2024, 12),     (2019, 9)),
    ("MES", Market.CME,    0.25,        (2024, 12),     (2019, 9)),
]

RECENT_START, RECENT_END = datetime(2024, 11, 1), datetime(2024, 11, 15)
EARLY_START, EARLY_END = datetime(2019, 6, 3), datetime(2019, 6, 14)

# Chicago stamps throughout — L-021's binding convention. The pre-open block is
# S-CASH's (07:20, 08:30] CT = 08:21-09:30 ET; RTH here is the CORRECTED
# (08:30, 15:00] CT = 09:31-16:00 ET, not the mislabelled window.
PRE_LO, PRE_HI = time(7, 20), time(8, 30)
RTH_LO, RTH_HI = time(8, 30), time(15, 0)


class QuoteDataSmoke(QCAlgorithm):

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
        served = []
        for leg, market, tick, recent, early in LEGS:
            fut = self.add_future(
                leg, Resolution.MINUTE, market=market, fill_forward=False,
                extended_market_hours=True,
                data_mapping_mode=DataMappingMode.OPEN_INTEREST,
                data_normalization_mode=DataNormalizationMode.BACKWARDS_RATIO,
                contract_depth_offset=0)
            fut.set_filter(0, 0)

            sym = self._resolve(fut.symbol, *recent)
            if sym is None:
                self.results[f"S_{leg}_RESOLVE"] = "FAIL|no contract"
                continue

            # (a) regular fetch — establishes QuoteBar delivery at all, and the
            # RTH spread. This is the call a battery would issue by default.
            ok = self._measure(f"{leg}_REG", tick, lambda: self._quotes(
                sym, RECENT_START, RECENT_END))
            served.append(ok)

            # (b) extended + FF-off — the only call that can reach the pre-open
            # block. Kwarg rejection is reported, never silently absorbed.
            self._measure(f"{leg}_EXT", tick, lambda: self._quotes(
                sym, RECENT_START, RECENT_END, ext=True))

            # (c) depth probe at research_start. A battery cannot span the
            # program's window if quotes begin later than trades do.
            esym = self._resolve(fut.symbol, *early)
            if esym is None:
                self.results[f"S_{leg}_EARLY"] = "FAIL|no contract"
            else:
                self._measure(f"{leg}_EARLY", tick, lambda: self._quotes(
                    esym, EARLY_START, EARLY_END, ext=True))

        any_served = any(served)
        self.results["S_VERDICT"] = (
            f"quotes_served={int(any_served)}|"
            f"proceed={'YES' if any_served else 'NO_no_quote_data_on_this_tier'}")

    def _quotes(self, sym, start, end, ext=False):
        """Typed QuoteBar history. Tries the documented signature first and
        records which one worked — the two differ across LEAN versions and a
        silent fallback to TradeBars would look like a zero-width spread."""
        kw = dict(fill_forward=False, extended_market_hours=True) if ext else {}
        try:
            h = self.history(QuoteBar, sym, start, end, Resolution.MINUTE, **kw)
            self.results.setdefault("S_API", "history(QuoteBar,...)")
            return h
        except TypeError:
            h = self.history[QuoteBar](sym, start, end, Resolution.MINUTE, **kw)
            self.results.setdefault("S_API", "history[QuoteBar](...)")
            return h

    def _measure(self, tag, tick, fetch):
        key = "S_" + tag
        try:
            h = fetch()
        except TypeError as e:
            self.results[key] = f"KWARG_REJECTED|{str(e)[:80]}"
            return False
        except Exception as e:
            self.results[key] = f"ERROR|{type(e).__name__}|{str(e)[:70]}"
            return False
        if h is None or len(h) == 0:
            self.results[key] = "EMPTY|no quote bars returned"
            return False

        h = h.reset_index()
        cols = {c.lower(): c for c in h.columns}
        bid, ask = cols.get("bidclose"), cols.get("askclose")
        if bid is None or ask is None:
            self.results[key] = f"NO_BIDASK|cols={','.join(sorted(cols))[:70]}"
            return False

        tcol = cols.get("time") or h.columns[1]
        idx = pd.DatetimeIndex(h[tcol])
        b = pd.Series(h[bid].astype(float).values, index=idx).sort_index()
        a = pd.Series(h[ask].astype(float).values, index=idx).sort_index()
        b, a = b[~b.index.duplicated("first")], a[~a.index.duplicated("first")]
        both = b.notna() & a.notna()
        if not bool(both.any()):
            self.results[key] = f"ALL_NAN|rows={len(b)}"
            return False
        b, a = b[both], a[both]

        spread_ticks = (a - b) / tick
        t = b.index.time
        reg_dates = pd.DatetimeIndex(
            b.index[(t > RTH_LO) & (t <= RTH_HI)]).normalize()
        n_days = max(1, reg_dates.nunique())

        rth = spread_ticks[(t > RTH_LO) & (t <= RTH_HI)]
        pre = spread_ticks[(t > PRE_LO) & (t <= PRE_HI)]
        # Fill-forward signature on the quote side: a synthetic bar repeats the
        # previous bid. A tight spread measured on repeats means nothing.
        pre_b = b[(t > PRE_LO) & (t <= PRE_HI)]
        stale = float((pre_b.diff() == 0).mean()) if len(pre_b) > 1 else float("nan")
        # Defects, not opportunities: a crossed or zero-width top of book.
        bad = float((spread_ticks <= 0).mean())

        self.results[key] = (
            f"{min(t).strftime('%H:%M')}-{max(t).strftime('%H:%M')}|"
            f"bars={len(b)}|days={n_days}|per_day={len(b) / n_days:.1f}|"
            f"rth_n={len(rth)}|{self._dist('rth', rth)}|"
            f"pre_n={len(pre)}|pre_per_day={len(pre) / n_days:.1f}|"
            f"{self._dist('pre', pre)}|"
            f"pre_stale={stale:.3f}|nonpos={bad:.4f}")
        return True

    @staticmethod
    def _dist(name, s):
        if len(s) == 0:
            return f"{name}_med=NA|{name}_p90=NA|{name}_eq1=NA|{name}_sub1=NA"
        return (f"{name}_med={s.median():.3f}|{name}_mean={s.mean():.3f}|"
                f"{name}_p90={s.quantile(0.90):.3f}|"
                # A-008 says this should be ~1.0 in RTH. eq1 is how often the
                # book is exactly one tick wide; sub1 must be ~0 or the
                # measurement is wrong, not the market.
                f"{name}_eq1={float((s.round(3) == 1.0).mean()):.3f}|"
                f"{name}_sub1={float((s < 0.999).mean()):.4f}")

    def _resolve(self, canonical, year, month):
        anchor = datetime(year, month, 1)
        for back in (25, 55, 85, 5):
            probe = anchor - timedelta(days=back)
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
