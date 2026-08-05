# Validation Report 03 — Minute-Level Treasury Curve Relationships (A-009)

**Date:** 2026-08-03 · **Environment:** QC cloud project `dexter-rv-research`
(34720894), free tier · **Pre-registration:** D-016, covering all four pairs
together and written before any Treasury series was built
**Code:** `src/spread_research/{intraday_reversion,pair_minute_report}.py`,
driven by `lean/research/qc_pair_minute_analysis.py`
**Runs:** ZF–ZN "Calculating Tan Cormorant" · ZT–ZF "Swimming Yellow Green
Guanaco" · ZN–ZB "Measured Magenta Goat" · ZT–ZN "Logical Magenta Termite"
**Machine-readable:** `reports/machine_readable/nb02_<PAIR>_*.csv`
**Figures:** `nb02_<PAIR>_{conditional_reversion,variance_ratio,roll_preflight}.png`

---

## 1. Verdict — all four pairs, one answer

| Pair | Gate | (a) S1 cells positive at \|t\|>=3 | Largest honest effect | Round-trip cost | Ratio | Verdict |
|---|---|---|---|---|---|---|
| ZF–ZN (5s10s) | PASS | **20/20** | +0.286 bps | 3.10 bps | **11x** | AMBIGUOUS / IMMATERIAL |
| ZT–ZF (2s5s) | PASS | **20/20** | +0.202 bps | 1.41 bps | **7x** | AMBIGUOUS / IMMATERIAL |
| ZN–ZB (10s30s) | PASS | **20/20** | +0.664 bps | 5.85 bps | **9x** | AMBIGUOUS / IMMATERIAL |
| ZT–ZN (2s10s) | PASS | 16/20 | +0.166 bps | 1.50 bps | **9x** | AMBIGUOUS / IMMATERIAL |

**A-009 is UNRESOLVED-but-IMMATERIAL for every Treasury pair.** All four
produce a statistically overwhelming, internally consistent, correctly-signed
reversion effect — and in all four it is **7 to 11 times smaller than the cost
of harvesting it**, and it fails the pre-committed base-sampling check.

This is not four marginal calls. It is the same result four times, on four
different curve segments, with t-statistics as high as 9.4.

## 2. Why the significance is real and irrelevant

Effect sizes are computed against costs derived from the **verified** contract
specifications (`data/metadata/contract_specifications.csv`, A-003 VERIFIED),
not from guesses: tick value divided by contract notional, one tick crossed on
each leg on entry and on exit, with the second leg weighted by the pair's own
median hedge ratio.

| | ZT | ZF | ZN | ZB |
|---|---|---|---|---|
| tick value | $7.8125 | $7.8125 | $15.625 | $31.25 |
| ~notional | $204k | $108k | $110k | $115k |
| **1 tick in bps** | **0.38** | **0.72** | **1.42** | **2.72** |

Treasury futures are quoted in coarse ticks relative to their minute-level
volatility. That single fact drives both halves of this report: it makes the
round-trip cost large in bps, and it fills the hedged residual with
quantisation noise.

**The gap does not close under any plausible cost improvement.** A-007/A-008
are unverified placeholders, but the shortfall is 7–11x; even a threefold
reduction in transaction cost leaves every pair uneconomic. This conclusion is
robust to the cost assumptions being wrong by a wide margin.

## 3. Why criterion (b) fails — the same signature in all four

Residual variance ratio at matched ~30 minutes of elapsed time, as the base
sampling is coarsened:

| Pair | 1-min bars | 5-min bars | 15-min bars | movement toward 1 |
|---|---|---|---|---|
| ZF–ZN | 0.134 | 0.467 | 0.827 | **6.2x** |
| ZT–ZF | 0.241 | 0.623 | 0.904 | **3.8x** |
| ZN–ZB | 0.208 | 0.594 | 0.893 | **4.3x** |
| ZT–ZN | 0.322 | 0.712 | 0.963 | **3.0x** |

A variance ratio of 0.13–0.32 at one-minute sampling looks like violent mean
reversion. It is tick quantisation: coarsen the bars and it evaporates toward a
random walk in every case. The legs corroborate this — each Treasury leg is
itself bounce-dominated at 1-minute sampling (ZN 0.58, ZB 0.68, ZF 0.72, ZT
0.67 at q=120) and each returns to ~1.0 at 15-minute sampling.

**[ESTABLISHED] The sub-unit variance ratio of every hedged Treasury residual
at minute resolution is a tick-quantisation artifact, not a curve
relationship.** Logged as L-016.

## 4. The gate, and what it says about the constructor

| Pair | rolls/leg | flags | adjudication |
|---|---|---|---|
| ZF–ZN | 27 | 0 / 0 | — |
| ZT–ZF | 27 | 1 (ZT) / 0 | `sign_mismatch` |
| ZN–ZB | 27 | 0 / 2 (ZB) | both `sign_mismatch` |
| ZT–ZN | 27 | 1 (ZT) / 0 | `sign_mismatch` |

All 27 rolls per leg, zero dropped bars on any pair, every flag adjudicated a
non-artifact by the A1 bound. **ZT230831 flags identically in both runs that
include ZT** (ZT–ZF and ZT–ZN: sr = −0.0614, gap = +0.4312, ratio 0.14), which
is a second independent determinism check on the D-009 constructor after the
M2K one. The constructor has now been validated on **all eight instruments** in
the locked universe.

## 5. The vol-ratio anchor (D-016's one deliberate change) is supported

| Pair | vol-ratio β median | β p5–p95 | OLS β p5–p95 |
|---|---|---|---|
| ZF–ZN | 0.583 | 0.495–0.693 | 0.395–0.805 |
| ZT–ZF | 0.449 | 0.369–0.527 | 0.105–0.548 |
| ZN–ZB | 0.554 | 0.477–0.627 | 0.266–0.706 |
| ZT–ZN | 0.260 | 0.197–0.356 | 0.033–0.407 |

Every median is economically sensible for its curve segment (2y carries ~26% of
10y's volatility, 5y ~58% of 10y, 10y ~55% of 30y), and the vol-ratio band is
2–4x tighter than the OLS band on the same data. The ZT–ZN OLS 5th percentile
of **0.033** is the clearest illustration of why D-008 demoted fitted static
hedges to a control for this asset class.

## 6. Treasury-specific structural findings

1. **Roll windows are flat.** Residual dispersion around the splice sits at
   0.89–1.03x baseline for every pair, versus 1.6–2.6x for the index micros.
   Month-end rolls sit far from expiry with continuous liquidity. **No
   post-roll warm-up extension is needed for any Treasury pair** — the opposite
   of L-015's finding for M2K. Roll windows are asset-class-specific.
2. **Held-position roll shock is large and grows with maturity**: median 9.7
   bps (ZT–ZF), 13.0 (ZF–ZN), 21.8 (ZT–ZN), **39.5 bps (ZN–ZB, max 118)**. The
   long end is where a held position bleeds most at rolls, consistent with
   A-012's warning about ZB delivery-cycle effects.
3. **L-013's open-clustering is absent throughout.** 12.7–13.6% of crossings in
   the first 30 minutes, against 22.7–24.7% for the index pairs, with a nearly
   flat intraday profile. Treasuries trade through the night, so 09:30 ET is
   not an open for them. Three index pairs and four Treasury pairs now agree
   that L-013 is an equity-session-open artifact of the z-score configuration.

   > **AMENDED 2026-08-05 (L-021 + L-024).** "The first 30 minutes" here is
   > **10:31–11:00 ET**, not 09:31–10:00 ET — see the session-window correction
   > in §8. The *conclusion* survives and is arguably strengthened: the point
   > is that Treasury crossings do NOT cluster at the window edge, and that is
   > true at 10:31 ET and equally true at the corrected 09:31 ET edge (report
   > 15 measured both). But the sentence "09:30 ET is not an open for them"
   > was, on this report's own data, never a statement about 09:30 ET.
   > **The index comparison is unaffected** — index bars are stamped
   > America/New_York, so their first 30 minutes really is the equity open.

## 7. A-012 (CTD / delivery-cycle) — checked as D-016 required

D-016 pre-committed that a positive ZN–ZB result would trigger a CTD-switch
check before anything else. ZN–ZB is not positive in the tradable sense, so the
clause is moot, but the evidence was inspected anyway: ZB's two flagged splices
(2023-08-31, 2026-02-27) are both `sign_mismatch` non-artifacts, and ZB carries
the largest roll shock in the universe (median 39.5 bps, max 118 bps). **A-012
remains UNVERIFIED and untested as a signal contaminant** — this report
disqualifies ZN–ZB on cost and microstructure before CTD effects become the
binding question.

## 8. Limitations specific to this report

- **Session window.** RTH is held at 09:30–16:00 ET for comparability with
  notebook 02 (A-013), which excludes the 08:20 ET cash-Treasury open — a
  genuinely liquid window for these contracts. Stated in D-016 in advance;
  a Treasury-native session is a separate study.

  > **CORRECTED 2026-08-04 by L-021, measured 2026-08-04 by validation report
  > 15 (D-024 → D-025).** The window stated above is **not the window this
  > report ran on.** `rth_frame` filters on the clock the DATA carries, and
  > LEAN stamps CBOT Treasury bars in **America/Chicago**. So these four pairs
  > were analysed on **(09:30, 16:00] CT = 10:31–17:00 ET** — missing the
  > 09:31–10:30 ET morning entirely and running two hours past the 15:00 ET
  > CME Treasury settlement. Bar count could not detect it: any 390-minute
  > window inside a 23-hour session yields 390 bars, which is why the
  > `medbars = 390` check never flagged it.
  >
  > **The verdicts are unaffected, and this was measured rather than assumed.**
  > Report 15 re-ran all four pairs on the corrected window: the largest honest
  > effect moves **1.01x (ZT–ZF), 1.10x (ZF–ZN), 1.14x (ZT–ZN), 1.26x (ZN–ZB)**
  > against a pre-registered 2.0x materiality bar, and **no pair's verdict
  > branch changes**. The 7–11x cost shortfalls below are not a one-hour
  > artifact and L-016's tick quantisation is window-independent. What was
  > wrong was the label, not the conclusion.
  >
  > **Binding convention since D-024:** state every window in BOTH clocks and
  > gate on an observed timezone witness, never on bar count. **And see L-024:**
  > any statistic defined relative to the window's EDGE — an "open subset", a
  > first-30-minutes cut — is still mislocated by this defect even though the
  > headline numbers survived it.
- **`raw_hl` is not comparable to notebook 02.** S1 here is a centered residual
  around a trailing fit, so its half-life (152–369 bars across the four pairs)
  is partly mechanical. The conditional statistic is unaffected (A2).
- **DV01 hedging was not tested.** It requires CTD duration, which is not in
  QC minute bars or the metadata; inventing DV01s would have been fabricating
  an input. The vol ratio is the documented substitute and its stability
  (§5) supports it, but a true DV01 comparison remains notebook 04's job.
- **Multiple testing.** These four pairs add 240 cells to notebook 02's 180,
  for 420 program-wide. Verdict rule (c) is what guards the conclusion, and it
  is not what decided any of these four — the cost ratio and the base-sampling
  check did.
