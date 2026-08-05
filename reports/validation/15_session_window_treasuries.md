# Validation report 15 — the treasury-native session (A-013), and the session-clock defect it corrected (L-021)

**Pre-registration:** D-024 (written and revised before any run existed; the
revision is commit `8dc47ec`, the runs began after `1042225`).
**Verdict:** D-025. **Experiments:** EXP-020 – EXP-023.
**Runs (12 backtests, QC project 34720894, 4 pairs x 3 parts):**
ZF–ZN "Emotional Blue Cobra" / "Upgraded Magenta kitten" / "Dancing Red Orange Rat" ·
ZT–ZF "Hyper Active Tan Gaur" / "Hyper Active Fluorescent Pink Guanaco" / "Emotional Blue Caterpillar" ·
ZN–ZB "Square Yellow Green Gorilla" / "Swimming Red Scorpion" / "Dancing Apricot Hippopotamus" ·
ZT–ZN "Casual Fluorescent Yellow Eagle" / "Square Tan Pig" / "Swimming Black Elephant".
**Precondition:** extended-fetch smoke test, run "Virtual Sky Blue Bull".

Educational research; internal R&D only — not investment advice.

---

## 1. What this run answers, and the defect it had to correct first

Two questions, pre-registered together so neither could be reported selectively:

- **Q1 (L-021):** did it matter that the four Treasury pairs were actually
  analysed on **10:31–17:00 ET**, not the 09:30–16:00 ET every prior document
  claims? `rth_frame` filters on the clock the DATA carries, and LEAN stamps
  CBOT Treasury bars in America/Chicago while stamping index bars in
  America/New_York.
- **Q2 (A-013):** does a **treasury-native session** — one that ends at the
  CME Treasury settlement rather than the equity settlement — change the
  answer?

**Why this experiment could move a verdict where notebooks 06 and 14 could
not.** Both of those carried a hard ceiling because criterion (b) is computed
on the RESIDUAL and no signal definition or entry bar enters it. A session
change alters *which bars form the panel*, hence the residual, hence the
variance ratios, the leg baselines, the per-session block counts and the
bootstrap's resampling unit. **Criterion (b) was live for the first time since
notebook 03.**

## 2. The five windows (all stated in BOTH clocks — now binding)

| tag | data stamps (CT) | true ET | bars | role |
|---|---|---|---|---|
| **S-USED** | (09:30, 16:00] | 10:31–17:00 | 390 | what the banked runs did — reproduction gate |
| **S-HALF** | (09:00, 15:30] | 10:01–16:30 | 390 | PLACEBO, anchored to nothing, −30 min |
| **S-RTH** | (08:30, 15:00] | 09:31–16:00 | 390 | the corrected equity baseline, −60 min |
| **S-SETTLE** | (08:30, 14:00] | 09:31–15:00 | 330 | open → **CME Treasury settlement** |
| **S-CASH** | (07:20, 14:00] | 08:21–15:00 | 400 | the true cash-open session |

The close at 14:00 CT is primary-sourced: CME settles ZT/ZF/ZN/ZB on the VWAP
of Globex trades between **13:59:30 and 14:00:00 CT**, and settles E-mini S&P
on **14:59:30–15:00:00 CT**. The program's 16:00 close was therefore the
*equity* settlement, inherited by the wrong asset class. The 08:20 ET open
remains a **convention**, declared as such in D-024 and not tuned.

## 3. Validity gates — 60 of 60 passed

Every gate in D-024 §5 passed on every part of every pair. The three that carry
the most weight:

- **Reproduction (gate 2).** The S-USED conditional grid reproduced the banked
  `nb02_<PAIR>_conditional_reversion.csv` **60/60 cells exactly** in all four
  pairs, and the S-USED variance ratios reproduced the banked curves **48/48
  cells** in all four. The session parameterisation disturbed nothing.
- **Build determinism (gate 3).** `S_GATE` / `S_BUILD_*` / `S_HOLIDAYS`
  reproduced the banked Treasury values exactly — a **6th determinism
  demonstration** of the D-009 constructor. ZT's `ZT230831` and ZB's two flags
  reproduced with identical `sr`, `gap`, `ratio` and `sign_mismatch` verdicts.
- **S-CASH-ENABLE.** The full factor table survived the extended-hours fetch
  **character-for-character** in all four pairs, so the D-009 construction is
  provably unchanged under the two-fetch design.

**The timezone witness confirmed L-021 live**: every regular-fetch leg reported
a delivered span of `08:31-16:00` at ~450 bars/day — Chicago stamps — while the
extended fetch reported `00:00-23:59` at ~1,378 bars/day.

## 4. Q1 — did the L-021 defect matter? **L-021 IMMATERIAL**

| pair | S-USED best (bps) | S-RTH best | move | branch change |
|---|---|---|---|---|
| ZF–ZN | +0.286 | +0.314 | 1.10x | none |
| ZT–ZF | +0.202 | +0.200 | 1.01x | none |
| ZN–ZB | +0.664 | +0.837 | 1.26x | none |
| ZT–ZN | +0.166 | +0.189 | 1.14x | none |

No pair reaches the pre-registered **2.0x** move bar and no verdict branch
changes. **The mislabelled hour did not change any conclusion.** The banked
Treasury verdicts stand on their own numbers; what was wrong was the label.

**One exception is procedural, not substantive.** ZT–ZF trips
**DISPLACEMENT-CONFOUNDED** because its placebo move (1.015x) marginally
exceeds its S-RTH move (1.010x). Both are ~1%, i.e. nothing moved at all, and
the rule compares them without requiring either to be material. This is a
degenerate case of the placebo rule, logged as **L-022**; it is reported as the
frozen rule dictates and is not evidence of anything.

## 5. Q2 — does a treasury-native session change the answer? **A-013 IMMATERIAL**

The direction is consistent and the magnitude is not enough.

| pair | S-USED ratio | S-RTH | S-SETTLE | S-CASH | best move vs S-RTH |
|---|---|---|---|---|---|
| ZF–ZN | 10.85x | 9.88x | 8.08x | 8.21x | 1.22x |
| ZT–ZF | 7.00x | 7.07x | 5.99x | 5.44x | 1.30x |
| ZN–ZB | 8.81x | 6.99x | 6.33x | **5.61x** | 1.25x |
| ZT–ZN | 9.06x | 7.96x | 6.84x | **5.57x** | 1.43x |

*(cost ratio = round-trip spread cost ÷ largest honest effect; lower is better)*

**Every treasury-native window improves the cost ratio in every pair**, and the
cash-open session is the best window in three of four. That is a real,
consistent, correctly-signed effect and it is exactly what the economic
argument predicted. **It is also nowhere near enough.** The largest single move
is 1.43x against a 2.0x bar, and the best cost ratio in the entire experiment
is still **5.6x below the round trip**. No pair advances.

Reporting this as IMMATERIAL rather than "promising" is the whole point of
having fixed 2.0x in advance: a pure signal re-specification on identical bars
already moves this statistic **1.467x** (ZF–ZN, Z0→Z1), so a 1.2–1.4x movement
sits inside the statistic's own specification noise.

## 6. Criterion (b) — the one that could have moved, and did not

**[ESTABLISHED] The sub-unit variance ratio survives no session window.** In
every pair and every window the base-sampling walk still evaporates:

| pair | 1-min base | 5-min | 15-min |
|---|---|---|---|
| ZF–ZN (S-CASH) | 0.145 | 0.499 | **0.824** |
| ZT–ZF (S-CASH) | 0.263 | 0.658 | **0.900** |
| ZN–ZB (S-CASH) | 0.252 | 0.653 | **0.893** |
| ZT–ZN (S-CASH) | 0.338 | 0.717 | **0.928** |

The tail ratio VR(120)/VR(30) runs **0.78–1.00** — a floor, not the ~1/q decay
of genuine reversion (module calibration: planted AR(1) 0.66, planted bounce
flattens above 0.85). This is L-016's tick-quantisation signature, unchanged.
**Criterion (b) fails identically on all 16 pair-window combinations**, so no
window reaches REVERSION PRESENT and every window lands in the same D-010
branch as banked: **AMBIGUOUS / MICROSTRUCTURE + ECONOMICALLY IMMATERIAL.**

This is the load-bearing result. The one criterion a session change *could*
have moved is the one that most clearly did not.

## 7. The falsifiable prior failed, and that is the interesting part

D-024 predicted, from L-018, that the treasury pre-open — which contains the
08:30 ET macro releases — would show **CONTINUATION**, because an information
release is a level change that persists. **It does not.** Across all four
pairs the S-CASH open-window subset contains **zero** significant negative
cells; the subsets are mixed and insignificant.

Meanwhile L-018's continuation *does* still appear where it was found: ZF–ZN's
S-USED open subset is negative in 18 of 20 cells and reproduces the banked cell
at **t = −3.87 exactly**.

**[PLAUSIBLE] L-018 is an equity-session-open effect, not a general
information-release effect.** The equity open is a liquidity discontinuity —
a market that was closed reopens — whereas the 08:30 ET release lands in a
market already trading continuously (the smoke test measured the 07:21–08:30 CT
block printing every single minute). That distinction is a hypothesis this run
did not test and cannot settle; it is recorded, not claimed.

> **AMENDED 2026-08-05 (L-024), from this run's own banked data — the second
> paragraph and the conclusion above are WITHDRAWN as written.** The first
> paragraph is unaffected: the prior failed, and that finding stands.
>
> **The contrast used here is the wrong one.** Under L-021, S-USED is
> (09:30, 16:00] **CT**, so its "open window" subset is **10:31–11:00 ET — an
> hour after the equity open**. The window whose open IS the equity open is
> **S-RTH** ((08:30, 15:00] CT = 09:31–10:00 ET). This run measured that
> subset; §7 did not use it. On ZF–ZN — the pair the claim names — the two
> disagree in sign at comparable power (n = 3,232 vs 3,351 at z = 2.0, k = 30):
>
> | ZF–ZN open subset | window (ET) | neg cells | mean t | min t |
> |---|---|---|---|---|
> | S-USED | 10:31–11:00 | 18/20 | **−1.76** | −3.87 |
> | S-RTH (the equity open) | 09:31–10:00 | 7/20 | **+0.58** | −1.71 |
>
> So the continuation is **absent at the equity open in the very pair cited**,
> where the subset in fact leans positive. A weak, non-significant lean does
> appear at the true equity open in the short-end pairs (ZT–ZF, ZT–ZN: both
> 15/20 negative, mean t −0.95 / −1.13, one cell at t = −3.21), so the
> direction is not refuted everywhere — but it is not carried by ZF–ZN, and
> the liquidity-discontinuity explanation above has no support here.
>
> **Nothing in §4–§6 moves.** These subsets are fenced as descriptive by
> D-024 §7 (`label = EXPLORATORY_open_subset`); A-013 IMMATERIAL, L-021
> IMMATERIAL and the four Treasury verdicts do not depend on them. The
> Treasury control simply stops corroborating L-018, which then rests on its
> three index pairs — and those are index-stamped (America/New_York), so
> their open subsets are the equity open and L-021 never touched them.
> See L-024.

## 8. Limitations

- **Costs did not move and were never going to.** Round-trip cost is
  tick-derived from VERIFIED specs (A-003); A-007/A-008 remain placeholders,
  and A-008's 1-tick spread is scoped in config to "liquid RTH". The pre-open
  cost bar is **unmeasured and probably worse**, and this run cannot measure it
  — trade bars, no quotes.
- **Freshness.** Each new window shares 270 bars with the spent S-USED window;
  S-RTH and S-SETTLE add 60 never-examined bars (09:31–10:30 ET) and S-CASH
  adds 130 (08:21–10:30 ET). A result on any of them is not independent
  confirmation.
- **Q2 does not hold the score fully constant.** 390 bars is exactly one
  session under S-USED/S-HALF/S-RTH, 1.18 sessions under S-SETTLE and 0.975
  under S-CASH, so a Q2 movement is attributable to the window OR its
  interaction with the fixed 390-bar score.
- **The open-window subsets and the activity profile are DESCRIPTIVE ONLY**
  (D-024 §7). No branch label, evidence-tag change or open-thread consequence
  is derived from them.
- **The 08:20 ET open remains a convention.** The activity profile is banked so
  a future experiment can define it empirically; it may not promote the
  boundary retroactively.

## 9. What this changes

- **A-013 is ANSWERED for Treasuries** at minute resolution on trade bars over
  2019-06 → 2026-04: RTH-only did not cost the program a tradable result.
- **L-021's session label is corrected** and its impact measured: the defect
  was real but immaterial to every conclusion.
- **The D-019 no-go stands**, and no pair advances. `lean/algorithm/` remains
  empty.
- Still open and NOT covered here: **quote data** (which would replace the
  A-008 placeholder with a measurement — and is now the binding uncertainty,
  since the pre-open cost bar is unmeasured) and **second/tick resolution**.
