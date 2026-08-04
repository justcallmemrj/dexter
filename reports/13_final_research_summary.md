# Report 13 — Final Research Summary: Version 1 has no surviving intraday candidate

**Date:** 2026-08-03 · **Owner:** Derrick Johnson · Internal R&D, educational
research. Not investment advice, and nothing here is a validated or profitable
strategy.
**Decision recorded:** D-019 (no-go for Version 1 at intraday horizon)
**Notebook:** `notebooks/13_final_research_summary.ipynb` (runs locally; reads
only banked artifacts)
**Code:** `src/spread_research/program_summary.py`, tests in
`tests/unit/test_program_summary.py`
**Evidence:** validation reports
[01](validation/01_data_and_roll_validation.md),
[02](validation/02_minute_pair_relationships.md),
[03](validation/03_treasury_pair_relationships.md); EXP-005 … EXP-014;
`reports/machine_readable/nb02_<PAIR>_*.csv` (seven pairs),
`nb13_program_summary.csv`, `nb13_funnel.csv`
**Figures:** `reports/figures/nb13_effect_vs_cost.png`,
`nb13_base_sampling.png`
**Reproduce:** `python scripts/nb13_figures.py`; `pytest tests/` (168 green)

---

## 1. Verdict

**Version 1's core hypothesis — that hedged index or Treasury-curve residuals
mean-revert at intraday horizon by enough to trade — has NO SURVIVING CANDIDATE.**

All seven pairs in the locked universe (D-002) were tested at minute resolution
under one frozen, pre-registered protocol. Two index pairs are falsified, one is
unresolved with a microstructure signature, and all four Treasury pairs are
statistically overwhelming and economically immaterial.

Under CLAUDE.md hard gate 4 ("no forced positive conclusion") this is a
legitimate research outcome. It is recorded as the finding, not worked around.
`lean/algorithm/` remains empty and stays empty: the LEAN build is hard-gated on
the token `PROCEED TO LEAN BUILD`, and this report does not recommend issuing it.

| Pair | Segment | Anchor | Criterion (a) | Largest honest effect | Round trip | vs cost | Verdict | Decision |
|---|---|---|---|---|---|---|---|---|
| MES–MYM | S&P–Dow | β = 1 | **0/20** | +1.410 bps (t 1.93) | ~2–3 bps | 1.4× below | **A-006 FALSIFIED** | D-011 |
| MES–MNQ | S&P–Nasdaq | β = 1 | **0/20** | +1.781 bps (t 2.84) | ~2–3 bps | 1.1× below | **A-006 FALSIFIED** | D-013 |
| MES–M2K | S&P–Russell | β = 1 | 8/20 | +6.305 bps (t 5.31) | ~2–3 bps | 3.2× **above** | **AMBIGUOUS / MICROSTRUCTURE** | D-015 |
| ZF–ZN | 5s10s | vol ratio | **20/20** | +0.286 bps (t 6.59) | 3.10 bps | 10.9× below | **AMBIGUOUS / IMMATERIAL** | D-017 |
| ZT–ZF | 2s5s | vol ratio | **20/20** | +0.202 bps (t 6.88) | 1.41 bps | 7.0× below | **AMBIGUOUS / IMMATERIAL** | D-018 |
| ZN–ZB | 10s30s | vol ratio | **20/20** | +0.664 bps (t 6.49) | 5.85 bps | 8.8× below | **AMBIGUOUS / IMMATERIAL** | D-018 |
| ZT–ZN | 2s10s | vol ratio | 16/20 | +0.166 bps (t 4.07) | 1.50 bps | 9.1× below | **AMBIGUOUS / IMMATERIAL** | D-018 |

Criterion (a) counts cells of the 4 × 5 entry/horizon grid that are positive with
session-clustered t ≥ 3 in the estimation-free specification. "Largest honest
effect" is the best cell either look-ahead-safe specification produced anywhere
in its grid — deliberately the maximum, not a significant maximum, because the
point of the number is that even the most flattering honest cell does not pay.
Every figure in this table is recomputed from the banked run outputs by
`program_summary.py`; the reconciliation is enforced by unit test, so if a
validation report and its own CSV ever disagree, the test fails rather than this
summary quietly agreeing with the prose.

Figure: `reports/figures/nb13_effect_vs_cost.png`.

## 2. What was tested, and how the answer was allowed to be no

- **Universe (locked, D-002):** MES, MNQ, M2K, MYM index micros; ZT, ZF, ZN, ZB
  Treasuries. Seven pairs: three index (D-008 priority order), four curve
  segments. No cross-asset spreads, no big/micro spreads.
- **Data:** own-splice constructed minute series (D-009) for all eight
  instruments, 2019-06-03 → 2026-04-24 (QC free-tier end clip, disclosed with
  every result). RTH `(09:30, 16:00]` ET, 390 bars per session. Panels of
  675,840–684,300 aligned bars over 1,744–1,780 sessions per pair.
- **Primary statistic:** conditional forward reversion, measured as the
  **position's P&L** with the hedge ratio frozen at the signal bar, entered at
  the close of t+1 and exited at t+1+k, inference session-clustered.
- **Grid:** 3 specifications × 4 entry thresholds × 5 horizons = 60 cells per
  pair; S3 (full-sample static β) is look-ahead contaminated by construction and
  was pre-declared a diagnostic upper bound, never evidence.
- **Verdict rule, frozen before any result existed:** REVERSION PRESENT requires
  (a) positive with |t| ≥ 3 at ≥ 2 adjacent horizons in both honest specs, (b) a
  variance-ratio curve still declining past q = 30 and materially below both
  legs' own curves *and* surviving coarser base sampling, and (c) an effect that
  strengthens with entry threshold rather than living in one cell.

Four pre-registrations (D-010 with amendments A1/A2, D-012, D-014, D-016) were
written and committed **before** the corresponding results existed. D-016
registered all four Treasury pairs together, deliberately, so the protocol could
not be adjusted between pairs and the multiple-comparison structure was fixed in
advance rather than reconstructed afterwards. The one deliberate protocol change
across the program — S1's anchor moving from β = 1 to the volatility ratio for
Treasuries — was argued economically in D-016 before any Treasury statistic
existed, because a 1:1 log spread across the curve is the long leg plus noise
rather than a spread.

## 3. Significance was never the binding constraint

**[ESTABLISHED] At n ≈ 680,000 bars, statistical significance is free.** D-010
anticipated this and required effect sizes in bps beside every t-statistic; that
requirement is what decides most of this report.

The Treasury pairs make the point most sharply. Criterion (a) is satisfied about
as strongly as it can be — 20/20 cells positive at session-clustered t ≥ 3 in
three of four pairs, with t reaching 9.44 in ZF–ZN — the sign is correct
everywhere, and the result is internally consistent across four different curve
segments. And the largest effect any of them produces is **0.66 bps**, against a
round-trip cost of 1.4–5.9 bps computed from **verified** tick specifications
(A-003): one tick crossed on each leg on entry and on exit, the second leg
weighted by the pair's own median hedge ratio.

Treasury futures are quoted in ticks that are coarse relative to their
minute-level volatility — one tick is 0.38 bps of notional for ZT, 0.72 for ZF,
1.42 for ZN, 2.72 for ZB. That single fact drives both halves of the Treasury
result: it makes the cost large in bps, and (§5) it fills the hedged residual
with quantisation noise.

**The gap does not close under any plausible cost improvement.** A-007/A-008
remain unverified placeholders, but the shortfall is 7–11×; a threefold
reduction in transaction cost still leaves every Treasury pair uneconomic. This
conclusion is robust to the cost assumptions being wrong by a wide margin.

For the two falsified index pairs, cost is not even the objection — the sign is.
Where MES–MYM and MES–MNQ are significant, they are significant in the direction
of **continuation**: fading a 1.5–2.0 sigma dislocation lost money at every
horizon from 5 to 120 minutes, in both look-ahead-safe specifications, across
2019–2026.

> **AMENDED 2026-08-03 by validation report 06 (D-021), after this report was
> written.** That continuation is carried by the first 30 minutes of the
> session — 22.7–24.7% of index events under the configured z-score. Removing
> those events and changing nothing else flips every significant honest cell in
> both pairs from negative to positive (largest +2.40 bps for MES–MYM, +3.12
> for MES–MNQ). **The no-go recorded in §1 and §12 stands**, because criterion
> (b) is computed on the residual, is untouched by any signal definition, and
> still fails in all seven pairs — but the sentence above describes an
> equity-open effect rather than intraday behaviour away from the open. §11's
> funnel row "satisfied criterion (a)" counts the three index pairs as 1 of 3;
> on the open-excluded signal all three satisfy it. Only four pairs were re-run
> (D-020 fixed that scope in advance), so the funnel is left as measured rather
> than extrapolated to the three Treasury pairs that were not. See report 06
> and L-018.

## 4. The one pair that cleared its cost, and why it does not count

MES–M2K produced the only cost-clearing surface in the program: +6.31 bps at
session-clustered t = 5.31, monotone in entry threshold (−1.97 → +0.70 → +3.87 →
+5.57 bps across z = 1.5 → 3.0 at h = 60), positive with |t| ≥ 3 in both honest
specifications. Criteria (a) and (c) are satisfied.

Criterion (b) fails, and the mechanism is identifiable. **M2K's own variance
ratio at q = 2 is 1.012 — above 1** (bootstrap p_lt_1 = 0.935), the signature of
*lagged price adjustment*, opposite in sign to the bid-ask bounce that depresses
MES to 0.988. M2K is the thinnest book in the universe. A spread against a
lagging leg mechanically converges as the laggard catches up, most strongly when
the dislocation is largest — which is exactly the monotone-in-entry_z surface
observed — and the convergence disappears once bars are coarse enough to contain
the catch-up, which is exactly what the base-sampling check found (0.813 →
0.897 → 0.956 as bars coarsen 1 → 5 → 15 min, and insignificant at 5-minute base
sampling with p = 0.13/0.15).

**[PLAUSIBLE] The MES–M2K effect is lead-lag, not reversion.** It is stated as
PLAUSIBLE rather than ESTABLISHED on purpose: the pre-registered test that would
settle it (delayed entry at t+2/t+5/t+15, plus leg-return cross-correlation at
lags ±1..5) has not been run. Until it does, **no MES–M2K result may be quoted
as an edge**, and A-006 is neither confirmed nor falsified for that pair.

> **AMENDED 2026-08-04 by validation report 14 (D-022 → D-023).** The test
> ran, under a pre-registration that fixed the ceiling first. Outcome:
> **DELAY-ROBUST** — the surface survives delayed entry (retention 0.932 /
> 0.849 / 0.536 at d = 2 / 5 / 15 on matched event sets, all 37 read-set
> cells included), while the leg-level lead-lag, though real and one-sided,
> is one bar deep and worth ~0.03 of correlation — too small to carry the
> surface, and already excluded by the t+1 entry convention. The lead-lag
> attribution above is therefore withdrawn as the surface's explanation;
> the base-sampling evaporation becomes an open puzzle (unconditional VR vs
> conditional event study). **Nothing else changes:** (b) still fails, the
> pair does not advance, no MES–M2K result may be quoted as an edge, and
> this report's conclusion stands. The finding is hypothesis-generating for
> open thread 3 (different session/resolution) only.

Stating the multiple-testing position plainly: this was the third pair × 60
cells = 180 cells examined under one protocol at the time. A coherent monotone
surface with t up to 5.7 across two specifications is not what 180 independent
draws produce, so multiple testing does not by itself dismiss the finding. The
base-sampling result does.

## 5. The check that failed in every pair

Criterion (b)'s base-sampling test asks a simple question: does the effect care
how the clock is sliced? A genuine reversion process does not — its variance
ratio at 30 minutes of elapsed time is the same whether you reach 30 minutes
with thirty 1-minute bars or two 15-minute bars. Microstructure noise does not
scale with the sampling interval, so coarsening the bars must walk a
microstructure-driven variance ratio back toward 1.

Residual variance ratio at matched ~30 minutes elapsed:

| Pair | 1-min bars | 5-min | 15-min | walk | leg A VR(q=2) | leg B VR(q=2) |
|---|---|---|---|---|---|---|
| MES–MYM | 0.756 | 0.852 | 0.950 | 1.26× | 0.989 | 0.990 |
| MES–MNQ | 0.928 | 0.941 | 0.983 | 1.06× | 0.988 | **1.017** |
| MES–M2K | 0.813 | 0.897 | 0.956 | 1.18× | 0.988 | **1.012** |
| ZF–ZN | 0.134 | 0.467 | 0.827 | **6.17×** | 0.889 | 0.818 |
| ZT–ZF | 0.241 | 0.623 | 0.904 | 3.76× | 0.873 | 0.889 |
| ZN–ZB | 0.208 | 0.594 | 0.893 | 4.28× | 0.818 | 0.868 |
| ZT–ZN | 0.322 | 0.712 | 0.963 | 2.99× | 0.873 | 0.818 |

**[ESTABLISHED] Every hedged residual in the universe walks toward a random walk
as its base bar coarsens.** Not one pair's variance ratio is a property of the
relationship rather than of the sampling. Figure:
`reports/figures/nb13_base_sampling.png`.

The leg columns matter as much as the residual ones. A residual VR of 0.75 is
not impressive when both of its legs sit at 0.83–0.87 on their own; and a leg VR
*above* 1 (MNQ, M2K) is a warning that a spread against it will appear to revert
for free.

## 6. The four near-miss fake edges — the transferable deliverable

Each of these produced a publishable-looking result. Each was caught by a check
that was in the battery before the number existed. This section, not the seven
verdicts, is what carries forward into any successor program.

**1. Bid-ask bounce (MES–MYM, MES–MNQ).** Residual VR ≈ 0.75 with bootstrap
p < 0.001 reads like strong reversion. Two tells: the curve stops declining past
q = 30 (VR(120)/VR(30) = 0.991 — a flat floor, not the ~1/q decay of a
mean-reverting process, against the module's own calibration of 0.66 for a
planted AR(1) and >0.85 for a planted bounce), and it returns to ~0.99 at
5-minute base sampling.

**2. Lead-lag from a thin leg (MES–M2K, L-014).** A monotone, cost-clearing,
t = 5.31 surface initially attributed to the laggard catching up. The tell is
the leg's own variance ratio: M2K at q = 2 is 1.012, *above* 1. *(Amended
2026-08-04, report 14: the delayed-entry probe showed the catch-up is real
but one bar deep and tiny — it does NOT carry this surface, which survives
delay. The thin-leg WARNING stands — a leg VR above 1 still demands the
delayed-entry/base-sampling checks before any reversion claim — but for
MES–M2K the surface's mechanism is now an open question, not an explained
artifact.)*

**3. Sliding reference window (D-010 amendment A2).** Differencing a residual
built around a trailing mean credits the reference window moving toward the
price as if it were the price coming back. On two **independent random walks**
— no relationship whatsoever — that error reports +5.4 bps at t = 20.3, where
pricing the actual position on the same events reports +0.8 bps at t = 1.9.
Fixing it moved MES–MYM's S2 headline from **+2.14 bps at t = +8.91** to
**−0.32 bps at t = −0.67**, while S1 and S3 reproduced their previous numbers
exactly — the self-check that this was a correction and not a new model. Had
this not been caught, report 02 would have claimed an intraday reversion edge
that does not exist.

**4. Tick quantisation (all four Treasury pairs, L-016).** Coarse ticks against
minute-level volatility give residual variance ratios of 0.13–0.32 that look
like violent mean reversion and evaporate toward 1 at 15-minute bars. The same
coarseness is what makes the cost large, so the artifact and the disqualification
have a common cause.

**The rule that follows, and it is now binding.** Before believing ANY positive
reversion result: **(i)** measure the position's P&L, not the residual's change;
**(ii)** compare against BOTH legs' own variance ratios; **(iii)** confirm it
survives coarser base sampling. All three are implemented in the battery and
pinned by tests.

## 7. Method corrections that changed headline numbers

Three defects were found and fixed mid-program. All three are recorded in full
because all three moved a published figure, and because a research record that
hides its corrections is not evidence.

**L-011 — a fitted beta must carry its regression intercept.** Computing
`y − β_t·x` on log prices with no intercept scales every beta wobble by the log
price level. MYM near 38,000 has log(x) ≈ 10.5, so a beta moving 0.001 between
refits injects ~105 bps of residual movement — orders of magnitude larger than
the effect under study. Caught on synthetic data during the notebook-02 dry run,
where the no-intercept specification manufactured **−1,689 bps** of fictitious
"reversion" that vanished once the intercept was restored. Fix:
`pair_minute_report.rolling_ols_residual` measures deviation from the full
trailing fitted line, and a regression test asserts the no-intercept form stays
>20× noisier. `pair_builder.build_residual` keeps the no-intercept form **on
purpose** — it is correct for hedge ratios that are not fitted (notional, DV01).
(The register entry itself was corrected on 2026-08-02: it originally said
~10 bps, understating the effect tenfold.)

**A1 — adjudicating a flagged splice is a bound, not a one-sided ratio.** The
mechanised rule `|sr| ≥ 0.6·|gap|` is satisfied by any sufficiently small gap,
so it labelled a quiet-market news move a defect and suppressed a whole
analysis. The correct discriminator is arithmetic: a wrong splice factor can
inject **at most** the calendar gap it was removing. MYM's 2019-12-12 boundary
return of 8.15 bp against a 1.08 bp gap is 7.5× larger than the mechanism can
produce, so the factor cannot be the cause. Amended rule: a flag is a genuine
artifact only if the gap is material, same-signed, and `0.6·|gap| ≤ |sr| ≤
1.6·|gap|` — both bounds. Replayed against every known case in both directions;
only the triggering case changes, and the residual watch item (a single bad
print would look identical) is retained as L-012 rather than declared settled.

**A2 — the primary statistic measures position P&L, not residual change.**
Described in §6 as fake edge #3. It also fixed a second defect: `mean_bps`
pooled every event equally while `t_clustered` came from per-session means, and
the two can disagree in sign. Both are now reported, with `mean_session_bps` —
the quantity the t-statistic actually refers to — printed beside the pooled mean.
No verdict may quote a pooled mean next to a clustered t as if they described
the same average.

Amendments A1 and A2 were both recorded **before** the results they affected
were read, and both make the test harder to pass rather than easier. That
ordering is what keeps them corrections rather than goalpost-moving.

## 8. What the D-009 constructor established

**[ESTABLISHED] QuantConnect's continuous-adjusted futures series carry bad
adjustment factors and must not be relied on across rolls for this universe
(A-004 FALSIFIED).** The roll audit found 40 of 220 splices in the research
window jumping by the full calendar gap in the refetched series (M2K 19/28,
MYM 14/28, MNQ 4, MES 3, Treasuries 0), plus 24 more that leak in streamed mode
only, with the streamed and refetched paths disagreeing in both directions. Any
future streaming or live use requires its own splice audit (L-010).

The replacement — own-splice construction with factors taken by median ratio at
full 390-bar overlap, anchored to a documented roll rule (index: expiry−8d at
10:30 ET; Treasury: last business day of the month before delivery) with a
rule-derived CME holiday calendar — is now:

- **validated on all eight instruments** in the locked universe, and
- **demonstrated deterministic twice**: D-014 predicted in writing, before the
  run, which M2K roll would flag (M2KM19 2019-06-13), with what numbers (−6 bp
  splice return against a +26 bp gap) and what classification (`sign_mismatch`);
  all three reproduced exactly, on the symbol whose QC-provided series was worst.
  ZT230831 then flagged identically in both runs that include ZT.

Every one of the seven verdicts rests on a passed data-acceptance gate, applied
**before** any analysis was computed. That ordering is why the negative result is
about the market rather than about the data.

Two structural findings came out of the same work and outlive the hypothesis:

- **[ESTABLISHED] The MES–MNQ roll shock is one-signed at every roll in the
  window** — median 17.4 bps, max 29.0, negative at all 28. Nasdaq's lower
  dividend yield gives NQ a higher net cost of carry, so the MNQ calendar spread
  is systematically wider and the factor differential never changes sign. A
  long-MES/short-MNQ spread carried across rolls pays on the order of **70 bps a
  year of structural drag**. Any future index-pair design must model this as a
  carry cost, not exclude it as roll noise.
- **[ESTABLISHED] Roll-window behaviour is asset-class specific (L-015, L-017).**
  Index micros show 1.6–2.6× baseline residual dispersion around the splice and
  M2K is still elevated at 1.58× in the third RTH day; all four Treasury pairs
  show 0.89–1.03×, i.e. no elevation at all, because month-end rolls sit far from
  expiry with continuous liquidity. The adopted 780-bar index warm-up does not
  transfer: M2K needs ≥ 1,170 bars, Treasuries need none.

## 9. What is NOT concluded

- **Not concluded: that these markets contain no structure.** They contain a
  real, consistent, correctly-signed reversion effect — the Treasury pairs agree
  on it across four curve segments with t up to 9.4. It is simply smaller than
  the tick. What is concluded is that it is not harvestable at the cost scale and
  resolution this project targets.
- **Not concluded: anything about longer horizons.** MES–MYM is genuinely
  cointegrated at daily horizon (EG p = 0.004, half-life ≈ 40 trading days), and
  nothing here contradicts that. A 40-day half-life is ≈ 15,600 RTH minute bars,
  two orders of magnitude beyond the ≤120-bar horizons tested and well beyond the
  780-bar maximum hold the Version 1 design allows. **The structure is real and
  lives at the wrong horizon for an intraday book.**
- **Not concluded: that MES–M2K has no effect.** It is UNRESOLVED. The
  delayed-entry test would settle it. *(Amended 2026-08-04: the test ran —
  report 14, DELAY-ROBUST. It attributed the mechanism — NOT laggard
  catch-up — but by pre-registered design issued no verdict on A-006, which
  stays UNRESOLVED; settling it now requires a fresh window/resolution.)*
- **Not concluded: anything about quote data, tick/second resolution, a
  Treasury-native session, overnight hours, or DV01-hedged Treasury spreads.**
  Every negative here is minute resolution, trade bars, equity RTH.
- **Not concluded: that the signal definition was right.** L-013 is a live
  specification question (§10), deliberately left unfixed so all seven pairs
  stayed comparable.

## 10. Limitations and unverified assumptions

| ID | Status | Bearing on this conclusion |
|---|---|---|
| A-007 / A-008 (commission, spread) | UNVERIFIED placeholders | Treasury shortfall is 7–11×, robust to a 3× error; index verdicts do not rest on cost at all |
| A-012 (CTD / delivery-cycle in ZB, ZN) | UNVERIFIED | ZN–ZB was disqualified on cost and microstructure before A-012 could bind; ZB carries the universe's largest roll shock (median 39.5 bps, max 118) |
| A-013 (RTH-only captures the signal) | UNTESTED | Live limitation for Treasuries specifically, whose liquid session starts ~08:20 ET |
| A-005, A-010, A-011 | UNVERIFIED | Never reached — they belong to notebooks 04/07 that no candidate qualified for |
| L-012 (MYM 2019-12-12 boundary print) | Open watch item | One minute of ~1.36M, inside an exclusion window; not independently confirmed |
| L-013 (390-bar z-window spans the overnight break) | Open, owned by notebook 06 | 22.7–24.7% of index signals fire in the first 30 minutes vs 12.7–13.6% in Treasuries — an equity-session-open artifact of the SIGNAL definition |
| L-005 (micro history ≈ 7 years) | Structural | One broad monetary era plus COVID; regime coverage is thin |
| L-004 (minute bars cannot model queue position) | Structural | Would only matter if something had qualified |

**The window is spent for this hypothesis.** Re-running the same grid on the
same data after seeing these results would be a multiple-testing violation. Any
new work needs a new mechanism and a fresh pre-registration.

## 11. Funnel and total-trials disclosure

| Gate | Pairs |
|---|---|
| In the locked universe (D-002) | 7 |
| Passed the data-acceptance gate | 7 |
| Satisfied criterion (a) in a look-ahead-safe spec | 5 |
| … and survived the base-sampling check (b) | **0** |
| … and cleared round-trip cost | **0** |
| Advancing to notebooks 04–12 | **0** |

**420 cells were examined under one protocol** (7 pairs × 3 specifications × 4
entry thresholds × 5 horizons). Verdict rule (c) — the effect must strengthen
with entry threshold rather than live in one cell — is what guards that count,
and it is worth stating that (c) is not what decided any pair: the cost ratio
and the base-sampling check did.

## 12. Recommendation, and the three open threads

**Recommendation: no-go for Version 1 in its current form.** Do not proceed to a
LEAN build. Notebooks 04–12 as originally scoped are moot: there is no candidate
to select a hedge for, size, cost-model, walk-forward, stress-test or allocate.

Three threads remain genuinely open. Each is a **new program** requiring fresh
pre-registration, and **none may reuse this window's results as evidence**.

1. **Notebook 06 / L-013 — session-anchor the z-score.** Changes the SIGNAL
   definition, not the hypothesis. It is the cheapest remaining test of whether
   the whole grid was mis-specified, and it is the only thread that could change
   the reading of results already in hand. *Recommended first.*
2. **MES–M2K delayed entry (D-015).** Entry at t+2/t+5/t+15 instead of t+1, plus
   leg-return cross-correlation at lags ±1..5. If the effect is M2K catching up
   it decays sharply with delay; if it is genuine reversion it survives. Settles
   the one non-negative index result either way — and a confirmed lead-lag effect
   in the thinnest micro is itself a documented finding.
   *(DONE 2026-08-04 — validation report 14, D-022 → D-023: **DELAY-ROBUST**.
   The surface survives delay; the real lead-lag is one bar and ~0.03 of
   correlation — not the carrier. Hypothesis-generating only; feeds thread 3
   with a banked target: +6.68 bps decaying to +2.24 across a 15-minute
   entry delay.)*
3. **Different resolution or venue.** Quote data (which would replace the
   A-008 placeholder with a measurement), a Treasury-native session anchored at
   the 08:20 ET cash open, or second/tick resolution. These are **different
   experiments, not re-runs**; `research_config.data.later_resolutions`
   anticipates them.

A fourth legitimate option is to stop. The program has produced a clean negative
on a well-specified hypothesis, a validated data constructor, a tested battery,
and four documented ways to fool yourself. That is a real result, and spending
more on the same hypothesis is not obviously the best use of the next session.
