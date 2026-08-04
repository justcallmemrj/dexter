# Validation report 14 — MES–M2K delayed entry and leg-level cross-correlation

**Pre-registration:** D-022 (2026-08-04, written before any code existed) ·
**Verdict decision:** D-023 · **Experiment:** EXP-019 ·
**Runs:** part 1 (Z0 half) "Creative Tan Antelope" · part 2 (Z2 half +
cross-correlation) "Swimming Red Pigeon" — QC project 34720894.
**Machine-readable:** `nb14_MES_M2K_{delay_grids,crosscorr,scalars}.csv`;
verdict recomputed from those CSVs by
`src/spread_research/delayed_entry_summary.py` and pinned by unit test.
Educational research; internal R&D only — not investment advice.

---

## 1. What was tested, and what no outcome could change

D-015 left one thread open on the one index pair that did not cleanly fail:
does the MES–M2K conditional surface reflect the thin leg catching up
(lead-lag, L-014), or convergence still there to harvest after the catch-up
window has passed? D-021 raised the stakes — under the open-excluded signal,
M2K's best honest cell (+6.767 bps at t = 5.14) is the largest effect in the
program.

D-022 froze the design before any number existed: the entry bar moves
(d ∈ {1, 2, 5, 15}, exit at t+d+k, beta frozen at the signal bar) on event
sets **matched at the largest delay** so n_events is constant across d; the
two banked signal definitions Z0 and Z2 unchanged; a leg-level
cross-correlation with jointly-resampled session-bootstrap CIs as the
mechanism discriminator; a 37-cell read set enumerated from the banked
grids; and the verdict thresholds. **The ceiling was fixed in the same
breath:** criterion (b) is a property of the residual that no entry timing
can touch, the window is spent, so under every branch the pair cannot
advance, nothing reaches REVERSION PRESENT, and the D-019 no-go stands.

## 2. Validity gates — all eight PASS, read before anything else

| Gate | Result |
|---|---|
| 4 (emission, part 1) | PASS — 54 keys, set-identical to the manifest |
| 4 (emission, part 2) | PASS — 57 keys, set-identical to the manifest |
| 1 (Z0 reproduces nb02) | PASS — **60/60 cells exactly** |
| 1 (Z2 reproduces nb06) | PASS — **60/60 cells exactly** |
| 2 (matched sets, both parts) | PASS — n_events constant across {1,2,5,15} in all 80 cells |
| 2b (cross-part identity) | PASS — 7 shared diagnostics character-identical |
| 3 (cross-correlation machinery) | PASS — c0 = 0.788, 15 finite CIs, 1,000 replicates |

Notes. (i) The battery ran as **two backtests by design** (L-019: the
summary-statistic channel silently lost the 12-key S_RL block in all four
nb06 runs; no single emission above ~57 keys is trusted again). Both parts
computed the entire battery; each emitted its half; the shared diagnostics
came back identical — a **fifth determinism demonstration** of the D-009
constructor. (ii) The double reproduction gate matters more than usual this
time: `leg_crosscorr_profile` forced a module split (`crosscorr.py`,
L-020 — QC's files/update caps a file at 32,000 characters), and 60/60 twice
proves the split changed nothing.

## 3. The delayed-entry result: the surface survives

All 37 read-set cells qualified for the ratio aggregation (matched d = 1
baseline kept every banked cell at t ≥ 2 and ≥ 0.5 bps; zero excluded).
Retention ratio_d = ms(d)/ms(1) on identical event sets:

| statistic | d = 2 | d = 5 | d = 15 | frozen bars |
|---|---|---|---|---|
| **ρ(d)** pooled median | **0.932** | **0.849** | **0.536** | DELAY-ROBUST needs ρ(5) ≥ 2/3, ρ(15) ≥ 1/3 |
| ρ(d), Z0 subset (12 cells, descriptive) | 0.929 | 0.882 | 0.673 | — |
| ρ(d), Z2 subset (25 cells, descriptive) | 0.932 | 0.843 | 0.453 | — |
| **S(d)** share of cells at t ≥ 3 | 0.95 | **0.73** | 0.59 | DELAY-ROBUST needs S(5) ≥ 0.50 |

A pure catch-up mechanism leaves ~0 of the effect at d = 5. The observed
profile is nowhere near that: it lands close to — though uniformly BELOW —
the AR(1) prediction at the measured within-session half-lives (predicted
0.981–0.988 at d = 2 and 0.93–0.95 at d = 5 for half-life 37–58 bars;
observed 0.932 and 0.849). The decay is somewhat faster than the measured
half-lives predict at every delay, most visibly at d = 15 (below). Headline cells, session-mean bps of
fading with clustered t (matched sets, n constant per row):

| cell | d = 1 | d = 2 | d = 5 | d = 15 | n |
|---|---|---|---|---|---|
| Z2 S1 3.0/120 (largest honest cell) | +6.68 (t 5.1) | +5.89 (t 4.7) | +4.74 (t 3.9) | +2.24 (t 1.9) | 2,057 |
| Z0 S1 3.0/60 (highest honest t) | +5.62 (t 5.7) | +5.25 (t 5.5) | +4.75 (t 5.1) | +3.06 (t 3.6) | 3,728 |

An entry a full **five minutes late** still finds two-thirds to five-sixths
of the banked effect; a **fifteen-minute** delay still finds half, pooled.
Stated honestly in the other direction: the below-AR(1) shortfall grows
with delay — at d = 15 the pooled retention (0.536, and 0.453 in the Z2
subset) sits well **below** the 0.77–0.85 prediction; the observed d ≤ 5
decay alone would imply a ~10–17-bar half-life rather than the measured
37–58. The profile discriminates cleanly against catch-up, not perfectly
for AR(1) — though it stays far above the 1/3 LEAD-LAG ceiling. Figure:
`nb14_MES_M2K_delay_decay.png`.

## 4. The cross-correlation result: the lead-lag is real, one-sided — and tiny

| statistic | point | 95% CI | reading |
|---|---|---|---|
| c(0) | 0.788 | — | alignment sanity (gate 3) |
| ab_1 = corr(r_MES(t−1), r_M2K(t)) | **+0.033** | [+0.021, +0.047] | MES leads M2K by one bar |
| ba_1 (mirror) | +0.004 | [−0.010, +0.016] | M2K does not lead MES |
| asym_1 (paired difference) | **+0.029** | [+0.014, +0.047] | one-sided ⇒ **X = TRUE** |
| ab_k, ba_k, asym_k for k = 2..5 | ≈ 0 | all CIs cover 0 | no multi-bar adjustment |

Figure: `nb14_MES_M2K_crosscorr.png`. Two things follow. First, L-014's
lead-lag is *real*: M2K does lag MES, detectably and one-sidedly. Second,
it is **confined to lag 1 and worth ~0.03 of correlation** — and the t+1
entry convention already skips that bar in every banked number, so this
catch-up cannot be what the conditional surface was made of. A multi-bar
partial adjustment (the only lead-lag shape that could survive to t+1)
would show ab_k > 0 at k = 2..5; it does not.

## 5. Verdict under the frozen rule: **DELAY-ROBUST**

ρ(5) = 0.849 ≥ 2/3, S(5) = 0.73 ≥ 0.50, ρ(15) = 0.536 ≥ 1/3 — the
DELAY-ROBUST branch, exactly as D-022 wrote it. X = TRUE is reported beside
the verdict and does not gate this branch (pre-registered: "a lead-lag
component in the returns can coexist with convergence that survives it" —
which is precisely what was found).

**What this may conclude (fixed in advance, D-022):**

- **Hypothesis-generating ONLY.** It buys exactly one thing: a concrete,
  sharpened target for the session/resolution thread — the same statistic
  on a fresh window, venue or resolution, pre-registered afresh. It does
  not reopen this window, does not soften report 13, and is not evidence
  of tradability.
- **The pair does not advance.** Criterion (b) is inherited unchanged and
  still fails; the D-015 branch (AMBIGUOUS / MICROSTRUCTURE) remains the
  ceiling; **the D-019 program no-go stands.**
- **No result here is quotable as an edge.** A-007/A-008 are placeholders,
  and this window has now been examined by exactly 1,300 grid cells across
  the program's four analysis notebooks (420 + 480 + 80 + 320).

**What is now established on this window (mechanism attribution only):**
the conditional surface is NOT carried by the laggard catching up. Two
independent probes agree — the position-level effect survives entry delays
that catch-up cannot survive, and the leg-level catch-up that does exist is
one bar deep, tiny, and already excluded by the entry convention.
D-015's [PLAUSIBLE] mechanism sentence is amended accordingly (it
correctly identified a real feature of M2K; that feature just does not
explain the surface). L-014's operational rule — run the base-sampling
check before believing any thin-leg reversion — binds unchanged.

## 6. The honest open puzzle this leaves

Two banked facts now sit in tension, and neither is wrong: the conditional
effect **survives a 15-minute delayed entry** (this report), yet the
residual's variance-ratio signature **evaporates at 5-minute base sampling**
(0.813 → 0.897 → 0.956, p = 0.13/0.15 — report 02 §12.3, unchanged and
still failing criterion (b)). These measure different things — the VR is an
unconditional property of every bar; the event study conditions on |z| ≥ 2
dislocations — and a mechanism that reconciles them (large dislocations
revert while typical bars carry bounce/quantisation noise; or a
session-time structure the pooled VR averages away) is exactly what a
second/tick-resolution or different-session test would discriminate. That
is the session/resolution thread's brief, now with a specific, banked
target: **+6.68 bps that decays to +2.24 as entry slips 15 minutes,
in the thinnest micro in the universe.**

## 7. Multiple testing, deliverables, amendments

320 matched cells (80 of them d = 1 baselines) + 16 cross-correlation
point estimates with 15 CIs, on top of the 900 + 80 previously examined.
The verdict read pre-registered medians over a frozen 37-cell read set —
no cell was chosen after the fact.

Deliverables: this report; notebook 14; `nb14_MES_M2K_*.csv`;
`nb14_MES_M2K_delay_decay.png`, `nb14_MES_M2K_crosscorr.png`; D-022/D-023;
EXP-019; L-019 (emission-channel key loss), L-020 (32k files/update cap);
`delayed_entry_summary.py` + pinned tests (210 green). Amendments applied
inline: report 02 §1/§12.3/§12.4, report 06 §8, report 13 §4/§6/§9/§12
thread 2, D-015's mechanism bullet, L-014, A-006 register row.
