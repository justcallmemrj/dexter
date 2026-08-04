# Validation Report 06 — Signal Definition and Session Anchoring (L-013)

**Date:** 2026-08-03 · **Environment:** QC cloud project `dexter-rv-research`
(34720894), free tier · **Pre-registration:** D-020, written and committed
before the session-anchored z-score existed in code and before any number under
it existed
**Code:** `src/spread_research/{intraday_reversion,pair_minute_report}.py`,
driven by `lean/research/qc_signal_definition_analysis.py`
**Runs:** MES–MYM "Hyper Active Tan Hippopotamus" · MES–MNQ "Muscular Blue
Goshawk" · MES–M2K "Crawling Magenta Barracuda" · ZF–ZN "Measured Black Lion"
**Machine-readable:** `reports/machine_readable/nb06_<PAIR>_{signal_grids,
event_clocks,scalars}.csv`
**Figures:** `nb06_<PAIR>_signal_definitions.png`, `nb06_event_clocks.png`
(regenerate: `python scripts/nb06_figures.py`)
**Experiments:** EXP-015 … EXP-018 · **Decision:** D-021

---

## 1. Verdict

**L-013 is MATERIAL — DIRECTION ONLY, in the exact sense D-020 fixed in
advance.** One pair's verdict changes under the corrected signal, so the
finding is real; and because criterion (b) is a property of the residual that
no signal definition can touch, and because this is the same window already
spent, **no pair advances and the D-019 no-go stands.**

What does change is a *supporting claim* in the program's record, and it needs
stating plainly:

> **The significant CONTINUATION that falsified MES–MYM (D-011) and MES–MNQ
> (D-013) was carried by events in the first 30 minutes of the session.**
> Remove those events and nothing else — the score, the grid, the specifications
> and the inference all unchanged — and the sign of every significant honest
> cell flips from negative to positive.

That does not resurrect either pair. It does mean the phrase "the dislocation
continues rather than reverts", used in validation report 02, describes an
**equity-open effect** and not the intraday behaviour of the pair away from the
open. Report 02's verdict is unaffected; its mechanism sentence is not.

| Pair | Z0 criterion (a) | Z1 criterion (a) | Z2 criterion (a) | Verdict change? |
|---|---|---|---|---|
| MES–MYM | fails (16 sig cells, **all negative**) | fails (6 sig, 3+/3−) | **satisfied** (25 sig, all positive) | no (branch), yes (character) |
| MES–MNQ | fails (15 sig, **all negative**) | fails (7 sig, all positive) | **satisfied** (21 sig, all positive) | no (branch), yes (character) |
| MES–M2K | **satisfied** (AMBIGUOUS, D-015) | **fails** | **satisfied** (25 sig, all positive) | **YES** |
| ZF–ZN (control) | satisfied | satisfied | satisfied | no |

## 2. Both validity gates passed, in all four runs

D-020 made these pass/fail on mechanics and required them to be read **before**
any grid. They are enforced in code by
`scripts/ingest_qc_signal_definition.py --compare-nb02`, which refuses to write
anything on a failure.

| Pair | Gate 1 — Z0 reproduces notebook 02/03 | Gate 2 — Z1 event clock flattens | Aligned panel |
|---|---|---|---|
| MES–MYM | **PASS**, 60/60 cells exactly | **PASS**, 24.3% → 0.0% | 676,560 bars / 1,744 sessions |
| MES–MNQ | **PASS**, 60/60 | **PASS**, 24.7% → 0.0% | 684,300 / 1,780 |
| MES–M2K | **PASS**, 60/60 | **PASS**, 22.7% → 0.0% | 684,300 / 1,780 |
| ZF–ZN | **PASS**, 60/60 | **PASS**, 12.7% → 0.0% | 675,840 / 1,746 |

**[ESTABLISHED] The data path is byte-identical to the one that produced
validation reports 02 and 03.** Every Z0 cell — effect size, session-clustered
t, hit rate and event count — reproduces the banked grid exactly, on all four
pairs, and every acceptance gate returns the same PASS with the same flags
(MYM 2019-12-12 `gap_immaterial`; M2K 2019-06-13 `sign_mismatch`; ZF/ZN zero).
That is what makes the Z0-versus-Z1 comparison a measurement rather than a
comparison of two pipelines, and it is a fourth independent determinism check
on the D-009 constructor.

Figure: `reports/figures/nb06_event_clocks.png`.

## 3. What the three signal definitions actually did

Session-mean P&L of fading, bps (session-clustered t), spec S1, entry_z = 2.0:

| Pair | Signal | h=5 | h=15 | h=30 | h=60 | h=120 |
|---|---|---|---|---|---|---|
| MES–MYM | Z0 | −0.48 (−4.08) | −0.98 (−5.13) | −1.25 (−4.79) | −1.11 (−3.30) | −0.74 (−1.81) |
| | Z1 | +0.07 (0.99) | +0.23 (1.90) | +0.28 (1.69) | +0.63 (2.63) | +0.73 (2.36) |
| | Z2 | +0.23 (2.59) | +0.49 (**3.22**) | +0.69 (**3.49**) | +1.09 (**3.91**) | +1.03 (2.87) |
| | ZO | −0.73 (**−3.15**) | −1.23 (**−3.47**) | −1.32 (−2.87) | −1.53 (−2.78) | −1.91 (−2.97) |
| MES–MNQ | Z0 | −0.48 (−3.46) | −0.96 (−3.95) | −1.17 (−3.49) | −0.07 (−0.15) | +0.70 (1.29) |
| | Z1 | +0.10 (1.05) | +0.34 (2.14) | +0.85 (**3.59**) | +1.10 (**3.58**) | +1.51 (**3.52**) |
| | Z2 | +0.33 (**3.32**) | +0.71 (**3.70**) | +1.25 (**4.44**) | +2.21 (**5.58**) | +3.12 (**6.13**) |
| | ZO | −0.55 (−1.80) | −0.90 (−1.83) | −1.47 (−2.32) | −0.63 (−0.82) | −1.32 (−1.46) |
| MES–M2K | Z0 | −0.31 (−1.49) | −0.76 (−2.17) | −0.49 (−0.96) | +0.70 (1.01) | +2.65 (**3.08**) |
| | Z1 | +0.31 (2.03) | +0.89 (**3.00**) | +1.50 (**3.66**) | +2.40 (**4.00**) | +3.73 (**4.94**) |
| | Z2 | +0.61 (**3.75**) | +1.11 (**3.56**) | +2.16 (**4.82**) | +3.46 (**5.42**) | +4.67 (**5.87**) |
| | ZO | −0.51 (−1.09) | −1.01 (−1.40) | −0.31 (−0.33) | −0.68 (−0.58) | −0.97 (−0.72) |
| ZF–ZN | Z0 | +0.05 (6.71) | +0.08 (5.87) | +0.10 (5.40) | +0.19 (6.19) | +0.29 (6.59) |
| | Z1 | +0.05 (8.26) | +0.06 (5.57) | +0.08 (4.62) | +0.13 (5.40) | +0.16 (4.72) |
| | Z2 | +0.08 (9.45) | +0.13 (9.33) | +0.20 (9.56) | +0.29 (9.71) | +0.36 (8.10) |
| | ZO | −0.01 (−0.78) | −0.04 (−1.35) | −0.15 (**−3.87**) | −0.12 (−2.39) | −0.14 (−2.29) |

Figures: `nb06_<PAIR>_signal_definitions.png` — Z0 and Z2 differ in exactly one
thing, whether first-30-minute events are counted, so the difference between
those two panels IS the open window.

**[ESTABLISHED] Fading a dislocation that fires in the first 30 minutes of the
equity session loses money, in every pair tested, including the Treasury
control.** The ZO row is negative at every horizon in MES–MYM (t to −3.5),
MES–MNQ and MES–M2K, and in ZF–ZN it is the only negative row anywhere in that
pair's entire grid (−0.15 bps at t = −3.87, h = 30). This is a coherent
mechanism rather than four coincidences: an overnight repricing scored against
yesterday's mean is not a dislocation that reverts, it is a level change that
persists.

**[ESTABLISHED] When those events are 22.7–24.7% of the sample they flip the
pooled sign of the whole grid.** They are 12.7% of ZF–ZN's sample and there
they do not — which is exactly the discrimination the negative control was
included to provide.

## 4. Why Z1 and Z2 disagree, and why that matters

Z2 removes the open events. Z1 re-scores the entire session against
within-session statistics *and* declines to trade the first 30 minutes. The two
therefore answer different questions, and D-020 required both precisely so this
could be told apart.

Under Z1 the index pairs lose their significant continuation — that part
agrees with Z2 — but they do not reach criterion (a), and the reason is
specific and uniform:

| Pair | Z1, S1: entry levels with ≥2 adjacent positive cells at t ≥ 3 | Z1, S2 |
|---|---|---|
| MES–MYM | z = 2.5 only | **0 cells at t ≥ 3 anywhere** |
| MES–MNQ | z = 2.0 and 2.5 | **0 cells anywhere** |
| MES–M2K | z = 1.5, 2.0, 3.0 | **0 cells anywhere** |

**Criterion (a) requires S1 AND S2. In all three index pairs it is S2 that
fails, and it fails completely.** [PLAUSIBLE] The mechanism is estimation
noise stacking: S2 is already a deviation from a trailing 1,950-bar fitted
line, so normalising it a second time against a short, early-session dispersion
estimate divides a noisy numerator by a noisy denominator. Z1's within-session
sigma is smallest right after the warm-up, which is where the extra events
appear — MES–MYM's S2 grid gains ~4,000 events at entry 1.5 relative to Z0 while
its largest session-mean falls. This is consistent with L-007/L-011, and it is
a reason to treat "session-anchor the z-score" as an interaction with the hedge
specification rather than as a free improvement.

**[ESTABLISHED] Session-anchoring the z-score is not a strict improvement.** It
removes a documented artifact and introduces a documented cost, and on this
evidence the cost falls entirely on the fitted-hedge specification.

## 5. Materiality — the numbers that would matter if (b) had held

Largest cell in either look-ahead-safe spec, against the same round-trip cost
basis used in reports 02 and 03:

| Pair | Z0 best | Z1 best | Z2 best | Round trip | Z2 vs cost |
|---|---|---|---|---|---|
| MES–MYM | +1.410 (t 1.93) | +1.259 (t 2.74) | **+2.401** (t 6.01) | ~2–3 bps | at the low end |
| MES–MNQ | +1.781 (t 2.84) | +1.682 (t 3.25) | **+3.121** (t 6.13) | ~2–3 bps | ~1.0–1.6× above |
| MES–M2K | +6.305 (t 5.31) | +4.202 (t 3.37) | **+6.767** (t 5.14) | ~2–3 bps | ~2.3–3.4× above |
| ZF–ZN | +0.286 (t 6.59) | +0.195 (t 6.47) | **+0.357** (t 8.10) | 3.10 bps | **8.7× below** |

Two of the three index pairs now produce an honest cell at or above the cost
band where before they produced significant losses. **This is not an edge
claim and must not be read as one:** criterion (b) — the variance-ratio shape
and base-sampling checks — is computed on the residual, no z-score enters it,
and it failed for all four of these pairs in reports 02 and 03. It is unchanged
here by construction, so under the frozen D-010 rule the best branch any of
these pairs can reach is **AMBIGUOUS / MICROSTRUCTURE**. D-020 stated that
ceiling in advance, before these numbers existed, for exactly this reason.

The Treasury control confirms the cost logic is untouched: ZF–ZN's effect moves
from 10.9× below cost to 8.7× below cost. Nothing a signal definition does
closes an order-of-magnitude gap.

## 6. Multiple testing, stated rather than reconstructed

These four runs add 4 pairs × 3 specs × 4 entries × 5 horizons × 2 new signal
definitions = **480 cells** to the program's 420, plus 80 exploratory
open-subset cells. D-020 fixed the interpretation bar in advance at *direction*
rather than at any cell, precisely because a count this large will always
contain significant cells. The direction is what is reported: sign flip on
removal of open events, present in three index pairs, absent in the control.

## 7. Limitations specific to this report

- **The window is the same one already spent.** Nothing here is an out-of-sample
  confirmation, and the sign flip is HYPOTHESIS-GENERATING only.
- **The warm-up is 30 bars and was not tuned.** D-020 fixed it in advance from
  the precision of a dispersion estimate. No sensitivity sweep was run, and
  running one now would be the specification search the method exists to avoid.
- **Z1's warm-up is one bar wider than Z2's excluded bucket.** The warm-up
  covers the first 30 bars (through 10:00 ET); the event clock's leading bucket
  and Z2's exclusion cover minutes 0–29 (through 09:59). Z1 is therefore
  marginally stricter. Stated rather than hidden; it cannot account for a sign
  flip.
- **Variance ratios were not recomputed** — deliberately, see §5. Criterion (b)
  is inherited from EXP-008/009/010/011.
- **The open subset is EXPLORATORY.** Overnight-gap continuation is a different
  hypothesis from A-006, the residual variance ratio is not its right
  supporting statistic, and D-020 issues no verdict on it. A positive there
  buys a fresh pre-registration and nothing else.
- **A-007/A-008 remain unverified placeholders**, so the index cost band is
  order-of-magnitude. Two of the Z2 results sit inside it, which is exactly the
  regime where a real broker schedule would matter — and exactly why no claim
  is made on them.

## 8. Status changes

- **L-013 → RESOLVED as a diagnosis, and PROMOTED to a finding.** The 390-bar
  overnight-spanning z-score does put 22.7–24.7% of index signals in the first
  30 minutes, and those signals behave in the opposite direction to the rest of
  the session. New limitation **L-018** records the open-window continuation
  effect and the S2 interaction.
- **A-006 remains FALSIFIED for MES–MYM and MES–MNQ at intraday horizon** — the
  rule that falsified them fails (a) under both corrected signal definitions
  too, and (b) is unchanged. The *reason given* in report 02 (significant
  continuation) is now known to be an open-window effect and is annotated there.
- **A-006 remains UNRESOLVED for MES–M2K.** Its verdict is the one that changes
  branch under Z1, which is what makes L-013 material; the delayed-entry test
  (D-015) is still the test that would settle the pair.
  *(Amended 2026-08-04: it ran — D-022 → D-023, report 14, DELAY-ROBUST.
  Mechanism attributed — NOT laggard catch-up — but by pre-registered design
  it issued no verdict on A-006, which stays UNRESOLVED; the thread is closed
  on this window.)*
- **A-009 unchanged for ZF–ZN**: AMBIGUOUS / IMMATERIAL under every signal
  definition tested.
- **D-019's no-go stands.** No pair advanced; nothing here reaches REVERSION
  PRESENT, and nothing here can.
