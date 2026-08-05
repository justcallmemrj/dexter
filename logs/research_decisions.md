# Research Decision Log

Format per entry: Date | Decision | Alternatives considered | Evidence | Reason |
Expected effect | Review required?

---

## D-001 — 2026-08-01 — Adopt research-first framework before any algorithm

- **Decision:** Build reusable research library + configs + tests + notebooks before
  any `QCAlgorithm`. LEAN build gated on explicit `PROCEED TO LEAN BUILD` token.
- **Alternatives:** Prototype algorithm first and iterate.
- **Evidence:** Project mandate; standard practice against overfitting-by-iteration.
- **Reason:** Prevents assumptions being baked into production code untested.
- **Expected effect:** Slower start, higher-integrity conclusions.
- **Review:** No.

## D-002 — 2026-08-01 — Universe locked to index micros + Treasury futures

- **Decision:** MES/MNQ/M2K/MYM index pairs; ZT/ZF/ZN/ZB Treasury pairs. No
  big-vs-micro same-index pairs; no cross-asset pairs; UB deferred.
- **Alternatives:** Include ES–MES-type basis trades; include MES–ZN cross-asset.
- **Evidence:** Big/micro discrepancies are speed-arbitrage [ESTABLISHED as
  latency-dominated]; stock-bond correlation is regime-dependent [ESTABLISHED —
  sign flips across inflation regimes, e.g. pre/post-2000, 2022].
- **Reason:** Both excluded classes need capabilities (latency; regime model) out of
  V1 scope.
- **Expected effect:** Smaller but analyzable universe.
- **Review:** UB and cross-asset revisit after V1 validation completes.

## D-003 — 2026-08-01 — Contract specs sourced via web-search cross-checks

- **Decision:** Record specs in `config/instruments.yaml` +
  `data/metadata/contract_specifications.csv` from multiple secondary sources;
  flag primary-source (CME) verification as outstanding.
- **Alternatives:** Rely on model memory (rejected by mandate); block until CME
  reachable (rejected — CME returns HTTP 403 to this container).
- **Evidence:** Three independent secondary sources agree on all tick sizes/values;
  one search summary self-contradicted on ZF face value and was resolved by a
  targeted follow-up (ZF = $100,000 face, tick 1/4 of 1/32 = $7.8125).
- **Reason:** Best available verification under network policy.
- **Expected effect:** Correct cost/DV01 arithmetic; residual risk flagged (A-003).
- **Review:** Yes — re-verify on CME before any execution-related use.

## D-004 — 2026-08-01 — Continuous-adjusted for indicators, mapped-raw for execution

- **Decision:** Working hypothesis only: continuous adjusted series (OpenInterest
  mapping, BackwardsRatio candidate normalization) for relationship estimation;
  mapped raw contracts for executable prices.
- **Alternatives:** Raw-only (roll gaps corrupt indicators); adjusted-only
  (adjusted prices are not executable — [ESTABLISHED] source of fake backtest PnL).
- **Evidence:** None yet in-repo. Must be tested in notebook 01 roll audit.
- **Reason:** Standard separation; prevents roll gaps from generating fake signals
  and fake fills.
- **Expected effect:** Clean indicator series; honest execution prices.
- **Review:** Yes — notebook 01 must confirm no artifacts before this is final.

## D-005 — 2026-08-01 — Conservative cost acceptance rule

- **Decision:** A configuration is only research-viable if net edge survives the
  'stressed' scenario (full spread both legs + 2 ticks slippage per leg + commissions).
- **Alternatives:** Base-case acceptance (1 tick).
- **Evidence:** Minute-bar backtests cannot observe queue/adverse selection;
  underestimating costs is the dominant failure mode of retail spread backtests
  [ESTABLISHED in backtesting literature].
- **Reason:** Bias acceptance against false positives.
- **Expected effect:** Some genuinely marginal edges will be rejected — accepted cost.
- **Review:** Revisit only if quote-level data later shows tighter realized costs.

## D-007 — 2026-08-01 — Environment migrated local; daily yfinance screening tier added

- **Decision:** Continue the research on the user's local Windows machine
  (report 00 Addendum A). Add a clearly-labeled **daily-resolution screening
  tier** using yfinance front-month series (assumption A-015) to triage the 7
  pairs BEFORE the minute-resolution program runs in QC Research. Screening
  outputs are preview evidence only and can never validate a pair — only
  deprioritize or flag one.
- **Alternatives:** Wait for QC Research access for all empirical work (slower,
  wastes an available data tier); treat yfinance daily as research-grade
  (rejected — undocumented roll methodology, not executable prices).
- **Evidence:** Local probes 2026-08-01: yfinance daily OK for ES=F/ZN=F/MES=F;
  38/38 tests pass locally.
- **Reason:** Cheap, honest triage that concentrates expensive minute-level
  effort on pairs whose daily-resolution relationship structure is not already
  disqualifying.
- **Expected effect:** Pair prioritization with explicit caveats; possible early
  flags (e.g. structurally broken relationships).
- **Review:** Yes — screening conclusions must be re-checked against QC
  continuous series (A-015 verification) once minute data is available.

## D-009 — 2026-08-01 — Own-splice continuous construction replaces QC-provided adjusted series

- **Decision:** Indicator series for notebooks 02+ are constructed by US from
  QC per-contract raw minute bars, spliced with measured pn/po factors at OUR
  calendar roll dates (index ~8 days pre-expiry; treasuries month-end prior
  to delivery month), via src/spread_research/roll_adjustment.py. QC-provided
  continuous adjusted series are NOT used across roll boundaries for M2K/MYM
  (A-004 FALSIFIED); for MES/MNQ/treasuries they may serve only as stopgap
  with the 40 bad splice dates excluded. Constructor must pass unit tests +
  a splice-return re-audit before notebook 02 relies on it.
- **Alternatives:** Trust QC continuous series (rejected — validation report
  01: 40 data-side gap leaks up to 1.08%, concentrated in M2K/MYM); exclude
  roll windows only (rejected as primary — hedges/z-scores would still span
  contaminated history; kept as stopgap); switch normalization mode
  (BackwardsPanamaCanal — moot: the defect is in factor data, not the mode;
  ratio-vs-subtraction choice for OUR splicing resolved analytically in
  favor of ratio for returns-based indicators).
- **Evidence:** reports/validation/01_data_and_roll_validation.md; 220-splice
  streamed audit + 220-splice History-refetch sweep; figures
  rollaudit_refetch_verdict.png (40 points on the ar=gap diagonal).
- **Expected effect:** Trustworthy indicator series; roll timing aligned with
  executable liquidity; notebook 02 preflight gains a splice re-audit step.
- **Review:** Yes — after the constructor passes its splice re-audit; and
  L-010 re-audit required before any future streaming/live use.

## D-008 — 2026-08-01 — Screening outcome: minute-program priority order + treasury adaptive-hedge mandate

- **Decision:** Based on the daily preview screen (EXP-003/EXP-004,
  `reports/preview/daily_pair_screen.md`): (1) minute-resolution program runs
  for ALL 7 pairs (screen cannot test the intraday hypothesis) in priority
  order MES_MYM → MES_MNQ → treasuries → MES_M2K; (2) for Treasury pairs,
  long-lookback static hedges are demoted from candidate to control in
  notebook 04 (hedge ratios shown regime-driven: ZT_ZN rolling beta 0.0→0.4
  across 2010-26, recent-vs-full shifts +70-111%); (3) short z-lookback /
  short-hold design is hardened by evidence (all pairs except MES_MYM lack any
  long-run daily anchor 2019-26).
- **Alternatives:** Drop non-cointegrating pairs now (rejected — daily
  non-cointegration does not falsify intraday reversion); keep static treasury
  hedges as candidates (rejected — regime evidence).
- **Evidence:** EXP-003/EXP-004; figures preview_MES_MYM_residual.png,
  preview_MES_MNQ_residual.png, preview_ZT_ZN_rolling_beta.png; L-007
  empirically confirmed on real daily data (rolling-hedge half-life inflation
  1-2 orders of magnitude).
- **Reason:** Concentrate expensive minute-level effort; encode design
  constraints the daily evidence already settles.
- **Expected effect:** Faster path through notebooks 02-05; fewer wasted grids.
- **Review:** Yes — priority order may change once minute-level co-movement and
  microstructure (spreads, depth) are measured in notebooks 02/03/07.

## D-006 — 2026-08-01 — Empirical notebooks structured but blocked on data

- **Decision:** Notebooks 02–13 are created with full methodology and module wiring,
  but marked BLOCKED-ON-DATA; no synthetic results presented as market findings.
- **Alternatives:** Fabricate/simulate market data to "complete" notebooks (rejected
  — violates no-fabrication mandate); leave notebooks uncreated (rejected — the
  framework is the deliverable of this phase).
- **Evidence:** Environment audit (report 00): no QC data, network policy blocks
  market-data downloads (yfinance 403, CME 403).
- **Reason:** Integrity of the research record.
- **Expected effect:** Next session inside QuantConnect Research can execute
  notebooks without redesign.
- **Review:** Yes — unblock via QC Research environment or LEAN CLI + data
  subscription.

## D-010 — 2026-08-01 — PRE-REGISTRATION of the notebook-02 A-006 test (MES–MYM intraday)

Written and committed **before any minute-level result was examined**, so that
"no" is a reachable answer. Nothing below may be revised in response to an
outcome; a revision voids the test and forces a fresh pre-registration.

- **Decision — frozen data path.** Own-splice constructed MES (`Market.CME`)
  and MYM (`Market.CBOT`, per L-009) minute series via D-009
  (`index_roll_schedule`, `days_before=8`, splice 10:30 ET, CME holiday list
  from `src/spread_research/calendars.py`). Window 2019-06-01 → free-tier clip
  (~2026-05-04, disclosed with every result). RTH only, `(09:30, 16:00]` ET,
  390 bars/session. No return, variance-ratio block, z-score window, or
  holding period may cross a session close.
- **Decision — acceptance gate, applied BEFORE analysis.** `splice_audit` runs
  on each constructed close series. Analysis executes only if every roll is
  unflagged, or each flag is individually adjudicated non-gap-shaped (splice
  return far below the measured factor gap) and recorded with its numbers. A
  series that fails the gate is not analysed; the run reports the failure.
- **Decision — residual specifications.** All three are reported side by side;
  none is privileged after the fact. S1: log ratio, β = 1 (estimation-free
  anchor). S2: trailing 1950-bar OLS β on log prices, shifted (look-ahead
  safe). S3: full-sample static β — look-ahead contaminated, a diagnostic
  upper bound only, never evidence.
- **Decision — primary statistic.** Conditional forward reversion: z from
  `rolling_zscore(residual, 390)` (shifted); event = first crossing of
  |z| ≥ entry_z; entry at the close of bar t+1, exit at the close of t+1+k;
  k ∈ {5, 15, 30, 60, 120}; entry_z ∈ {1.5, 2.0, 2.5, 3.0}; inference
  session-clustered. Chosen as primary because the t+1 fill makes it
  structurally immune to first-order bid-ask bounce, which the variance ratio
  is not.
- **Decision — supporting statistics.** Variance-ratio curves over
  q ∈ {2, 5, 15, 30, 60, 120} at base sampling 1/5/15 min, computed on the
  residual AND on each leg alone (bounce baseline); within-session AR(1)
  half-life of the z-score.
- **Decision — verdict rule, declared now.**
  - **REVERSION PRESENT** requires all of: (a) positive mean conditional
    reversion with session-clustered |t| ≥ 3 at ≥ 2 adjacent horizons, in S1
    *and* S2; (b) the residual VR curve still declining past q = 30 (not a
    flat bounce floor) *and* materially below both legs' own VR curves;
    (c) the effect strengthens with entry_z rather than living in one cell.
  - **NO REVERSION** if session-clustered |t| < 2 across the grid, or the sign
    disagrees between S1 and S2.
  - **AMBIGUOUS / MICROSTRUCTURE** if (a) holds but (b) fails — detectable but
    carrying the signature of bid-ask bounce rather than a pair relationship.
    This does not advance the pair.
  - Effect sizes are reported in bps in every branch. With n ≈ 690k bars,
    statistical significance is not an edge claim: any result smaller than one
    MES+MYM round-trip tick is labelled **ECONOMICALLY IMMATERIAL** regardless
    of its t-statistic.
- **Decision — preflight adoption rule (the item report 01 §5 deferred).**
  Default adopted windows are pre-roll exclusion = `ceil(max_holding_bars/390)`
  = 2 RTH days before OUR splice, and post-roll warm-up =
  `zscore_lookback_bars` = 390 bars, both **re-anchored to the D-009 splice
  timestamp**. Measured bucket diagnostics may tighten or loosen these, and the
  direction must be justified from the numbers.
- **Alternatives:** judge on the variance ratio alone (rejected — bounce
  confound); on half-life alone (rejected — L-007 hedge-estimation inflation);
  run a mini-backtest now (rejected — CLAUDE.md gate 1, and A-007/A-008 cost
  assumptions are still unverified placeholders).
- **Evidence:** grid is 4 entry_z × 5 horizons × 3 specs = 60 cells per pair;
  rule (c) exists so no single cell can carry a conclusion
  (`research_config.yaml` validation.multiple_testing_note).
- **Expected effect:** an A-006 verdict for MES–MYM at intraday horizon that is
  binding in either direction, plus adopted roll windows for notebooks 04+.
- **Review:** Yes — a negative verdict closes MES–MYM at intraday horizon and
  re-prioritizes the minute program per D-008.

### D-010 Amendment A1 — 2026-08-01 — adjudication of a flagged splice is a BOUND, not a one-sided ratio

Recorded **after** seeing the first notebook-02 gate result and **before** any
analysis output existed. It converts one FAIL into a PASS, so the reasoning is
set out in full rather than buried in a code diff.

- **What happened.** The gate run (QC "Emotional Fluorescent Orange Goat")
  built both legs: MES 28/28 rolls clean, MYM 27/28 clean with one flag —
  MYMZ19→MYMH20 on 2019-12-12. Splice return **8.15 bp** against a measured
  calendar gap of **1.08 bp**, local MAD 0.358 bp, audit threshold 5.31 bp.
  The mechanised rule `|sr| >= 0.6*|gap|` called it gap-shaped, so the driver
  suppressed all analysis — exactly as D-010 instructs when a flag looks like
  a defect.
- **Why the rule was wrong.** `|sr| >= 0.6*|gap|` is satisfied by *any*
  sufficiently small gap, so it labels every quiet-market news move a defect.
  D-010's wording ("splice return far below the measured factor gap")
  anticipated only the case where the splice return undershoots the gap; it
  had no branch for a splice return that *overshoots* it, which is what
  occurred.
- **The correct discriminator is a bound.** The error a wrong splice factor can
  inject into the boundary return is at most the calendar gap that factor was
  removing. Here the entire gap is 1.08 bp, so even a maximally wrong factor
  (applying 1.0, i.e. no adjustment at all) could move the boundary by 1.08 bp.
  The observed move is 8.15 bp — **7.5x larger than the largest artifact the
  mechanism can produce**. The factor therefore cannot be the cause,
  arithmetically, independent of any judgement about the market that day.
- **Amended rule.** A flag counts as a genuine artifact only if the gap can
  explain it: the gap is material (|gap| > audit threshold) AND sign(sr) ==
  sign(gap) AND `0.6*|gap| <= |sr| <= 1.6*|gap|`. Both bounds, not one.
- **Verified against every known case, in both directions.** QC's own M2K/MYM
  data-side leaks (gaps 13-108 bp with splice returns tracking them, validation
  report 01 section 3) still classify as artifacts. The two D-009 acceptance
  flags still classify as non-artifacts: M2KM19 2019-06-13 (-6 bp vs +26 bp —
  sign mismatch and below band) and ZNM21 2021-05-31 (-8.3 bp vs -69 bp —
  below band). No case changes except the one that motivated the amendment.
- **Residual watch item (not dismissed).** A single bad print in one contract's
  close at the boundary minute would look the same. It is one minute of ~1.36M,
  in one leg, at a roll boundary that the adopted pre-roll exclusion will keep
  positions out of anyway. MES moved +2.3 bp at the same timestamp, so this was
  not a common index-wide move; MYM is price-weighted across 30 names and
  thinner than MES, and the local MAD (0.358 bp) was unusually quiet, which is
  what made an ordinary move breach a 10x-MAD threshold. Flagged in
  `logs/issues_and_limitations.md` rather than treated as settled.
- **Standing constraint:** this amendment changes only how a flag is CLASSIFIED.
  It does not touch the A-006 verdict rule, the grid, or the primary statistic,
  all of which remain frozen as written in D-010.

### D-010 Amendment A2 — 2026-08-01 — the primary statistic measures POSITION P&L, not residual change

Recorded after the first full analysis run (QC "Geeky Brown Flamingo") and
before any verdict was written. It corrects HOW the pre-registered statistic is
computed; the statistic, the grid and the verdict rule are unchanged.

- **Defect 1 — a moving reference point was being counted as reversion.**
  D-010 defined the outcome as `-sign(z)*(residual_{t+1+k} - residual_{t+1})`.
  For S1 (beta = 1) and S3 (constant beta) the residual is a tradable spread,
  so that difference IS the position's P&L. For **S2 it is not**: the trailing
  OLS residual contains its own trailing mean, so differencing it mixes the
  price coming back with the REFERENCE WINDOW SLIDING toward the price. Only
  the first is tradable. A control on two INDEPENDENT random walks (no
  relationship whatsoever) makes the size of the error plain: differencing a
  trailing-mean residual reports +5.4 bps at t = 20.3, while pricing the actual
  position on the same events reports +0.8 bps at t = 1.9. The entire effect
  was the window moving.
- **Amended measurement.** The outcome is now the position's P&L with the hedge
  ratio FROZEN AT THE SIGNAL BAR:
  `-sign(z_t) * [ (a_{t+1+k} - a_{t+1}) - beta_t * (b_{t+1+k} - b_{t+1}) ]`.
  This is identical to the old form when beta is constant, so S1 and S3 are
  expected to reproduce their previous numbers — that equality is the
  self-check that the change is a correction and not a new model.
- **Defect 2 — effect size and t-statistic were weighted differently.**
  `mean_bps` pooled every event equally while `t_clustered` came from
  per-session means. The two can disagree in sign when heavily-populated
  sessions behave unlike the typical one, and the first run produced exactly
  that (S1, entry 1.5, h=5: pooled +0.066 bps against t = -4.86). Both are now
  reported, with `mean_session_bps` — the quantity the t-statistic actually
  refers to — printed alongside the pooled mean. No verdict may quote a pooled
  mean next to a clustered t as if they described the same average.
- **Why this is a correction and not goalpost-moving.** It was derived from a
  synthetic control with a known answer of "nothing", not from the MES-MYM
  numbers; it makes the S2 specification harder to pass, not easier; and it
  leaves the frozen verdict rule, entry grid, horizon grid and specifications
  exactly as pre-registered. Regression tests
  (`test_moving_reference_point_is_not_counted_as_reversion`,
  `test_pnl_and_residual_agree_when_beta_is_constant`) pin both properties.
- **Consequence for reading run 1.** The S2 column of "Geeky Brown Flamingo"
  (positive, t up to 10.6) is measurement artifact and is superseded; it is
  retained in the record only as the evidence that motivated this amendment.

## D-011 — 2026-08-01 — A-006 FALSIFIED for MES–MYM at intraday horizon; roll windows adopted

- **Decision:** Close MES–MYM as an intraday reversion candidate. The
  pre-registered D-010 verdict rule returns **NO REVERSION**: zero cells of the
  60-cell grid are positive with session-clustered |t| >= 3 in either
  look-ahead-safe specification, so criterion (a) fails outright. Of the 26
  cells that do reach |t| >= 3, **24 are negative** — fading a 1.5-2.0 sigma
  dislocation lost money at every horizon from 5 to 120 minutes over 2019-2026.
  Adopt the roll windows in §6.3 of validation report 02.
- **Alternatives:** (i) read the sub-unit variance ratio (residual VR ~ 0.75,
  bootstrap p < 0.001) as reversion — rejected, both pre-registered guards
  identify it as microstructure: the curve stops declining after q = 30
  (VR(120)/VR(30) = 0.991) and it walks back to ~0.99 at 5-minute base
  sampling; (ii) read S2's pre-amendment result (+2.14 bps, t = +8.91) as an
  edge — rejected, that was the sliding-reference-window artifact fixed in
  amendment A2, and the corrected number is -0.32 bps at t = -0.67; (iii) read
  S3's two positive significant cells as evidence — rejected, S3 is the
  full-sample static-beta spec, look-ahead contaminated and pre-declared a
  diagnostic upper bound; (iv) extend the holding period to reach the daily
  structure — rejected here, a 40-day half-life is ~15,600 RTH bars, two orders
  of magnitude past the design's 780-bar maximum hold, and D-008 already ruled
  out long holds on regime-break grounds.
- **Evidence:** validation report 02; runs "Emotional Fluorescent Orange Goat",
  "Geeky Brown Flamingo", "Alert Magenta Rabbit" (QC 34720894); EXP-008;
  `reports/machine_readable/nb02_*.csv`. Gate passed first: MES 28/28 rolls
  clean, MYM 27/28 with one flag adjudicated non-artifact by the A1 bound.
- **Reason:** The hypothesis was tested as written and the answer is no. It is
  additionally immaterial: the largest session-mean in either honest spec is
  +1.41 bps against a ~2-3 bps round-trip cost, so the sign is not even the
  binding objection.
- **Expected effect:** Notebook 02 continues to MES–MNQ (next in the D-008
  priority order), then MES–M2K; notebook 03 runs the Treasury pairs against
  A-009 with the same battery and the same pre-registered rule. Notebooks 04/05
  inherit the adopted roll windows and must route every FITTED beta through the
  intercept-aware residual (L-011). If MES–MNQ and MES–M2K also come back
  negative, the index book as an intraday reversion strategy is closed and the
  program's remaining hypothesis is the Treasury curve.
- **Review:** No re-test of MES–MYM at intraday horizon without a NEW
  mechanism, pre-registered afresh. Re-running the same grid on the same window
  after seeing this result would be a multiple-testing violation.

## D-012 — 2026-08-02 — PRE-REGISTRATION of the notebook-02 A-006 test (MES–MNQ)

Written before the MES–MNQ series were built and before any MES–MNQ statistic
existed. Second pair in the D-008 priority order.

- **Decision:** Test A-006 for MES–MNQ under the **identical frozen protocol
  used for MES–MYM** — D-010 as amended by A1 (splice adjudication is a bound)
  and A2 (the primary statistic is position P&L with beta frozen at the signal
  bar, reported with a session-clustered mean alongside the pooled mean). Data
  path, acceptance gate, the three residual specifications, the 4x5 entry/horizon
  grid, the variance-ratio curves with their leg baselines and base-sampling
  check, and the verdict rule (REVERSION PRESENT / NO REVERSION / AMBIGUOUS-
  MICROSTRUCTURE) all carry over verbatim. Nothing is re-tuned for this pair.
- **Deliberately held constant: the signal configuration.** L-013 (24.3% of
  MES–MYM crossings fire in the first 30 minutes because the 390-bar z-window
  spans the overnight break) is a real defect and is NOT fixed here. Fixing it
  mid-sweep would make MES–MNQ non-comparable to MES–MYM and would amount to
  searching over signal definitions between pairs. It is fixed once, in
  notebook 06, after which BOTH pairs are re-run on the corrected definition.
- **Only permitted differences from the MES–MYM run:** the second leg symbol
  and its market (MNQ is `Market.CME`; the MYM/CBOT special case was L-009).
  Same contract chain M19..M26, same expiry−8d 10:30 ET roll rule, same CME
  holiday list, same RTH window, same seed (20260801).
- **Prior, stated in advance so it cannot be adjusted afterwards:** MES–MYM was
  the only pair with daily-horizon cointegration (D-008) and it returned NO
  REVERSION with the significant cells pointing at continuation. That is
  evidence against the index book generally, so a negative MES–MNQ result is the
  expected outcome rather than a surprise. MES–MNQ is still worth testing
  because it is a genuinely different microstructure — highest co-movement of
  the index pairs (0.93 daily) and the deeper book of the two second legs,
  where MYM was the thinner leg (1.1% of MES bars had no simultaneous MYM
  print). A POSITIVE result here would therefore be a strong claim and must
  clear the same bar, not a lower one.
- **Alternatives:** skip MES–MNQ and close the index book on the MES–MYM result
  alone (rejected — one pair is not the book, and D-008 committed to testing all
  seven at minute resolution); loosen the verdict rule because the first pair
  failed (rejected outright — that is the definition of moving goalposts).
- **Expected effect:** an A-006 verdict for MES–MNQ. If negative, MES–M2K is the
  last index pair and the index book is close to closed; the Treasury curve
  (A-009, notebook 03) becomes the program's remaining live hypothesis.
- **Review:** No re-test of MES–MNQ at intraday horizon without a NEW mechanism,
  pre-registered afresh.

## D-013 — 2026-08-02 — A-006 FALSIFIED for MES–MNQ; two of three index pairs closed

- **Decision:** Close MES–MNQ as an intraday reversion candidate. The D-012
  pre-registered rule (= D-010 as amended) returns **NO REVERSION**: zero of 60
  cells are positive at session-clustered |t| >= 3 in either look-ahead-safe
  spec, and 19 of the 22 significant cells are negative — continuation again, at
  the same entry_z 1.5-2.0 where the sample is largest. Largest honest
  session-mean +1.78 bps at t = 2.84, inside the ~2-3 bps round-trip band.
- **Additional decision — treat the MES–MNQ roll shock as a modelled carry cost,
  not roll noise.** The held-position shift is negative at all 28 rolls (median
  17.4 bps, max 29.0), because NQ's lower dividend yield gives it a
  systematically higher net cost of carry than SPX. That is ~70 bps/year of
  one-directional drag on a long-MES/short-MNQ spread. Any future index-pair
  design must model it; excluding roll windows does not remove it, it only
  avoids taking it as a single hit.
- **Alternatives:** (i) read the residual VR of 0.92-0.95 as weak reversion —
  rejected on two counts: the curve is flat past q=30 (VR120/VR30 = 0.994) and
  the residual sits ABOVE MES's own leg VR at q=120 (0.922 vs 0.831), i.e. the
  hedged spread shows LESS apparent reversion than a single leg outright;
  (ii) read S3's three positive significant cells as evidence — rejected, S3 is
  look-ahead contaminated and pre-declared a diagnostic upper bound; (iii)
  declare the index book closed now — rejected, MES–M2K is untested and D-008
  committed to all seven pairs.
- **Evidence:** validation report 02 §11; run "Virtual Asparagus Pelican"
  (QC 34720894); EXP-009; `reports/machine_readable/nb02_MES_MNQ_*.csv`. Gate
  passed with ZERO flags on both legs — the cleanest build in the program, and
  the fourth/fifth symbol validating the D-009 constructor.
- **Reason:** The pair with the highest daily co-movement and the deepest second
  leg gives the same answer as the pair with the only daily cointegration. Two
  independent pairs, same protocol, same direction.
- **Expected effect:** MES–M2K is the last index pair; it is also the one most
  dependent on the own-splice constructor (QC's M2K series had bad factors at 19
  of 28 rolls), so it is a useful constructor test regardless of its verdict. If
  it too returns negative, the index book is closed at intraday horizon and
  notebook 03 / the Treasury curve (A-009) becomes the program's remaining live
  hypothesis. That is a legitimate outcome under CLAUDE.md gate 4, not a failure
  to be worked around.
- **Review:** No re-test of MES–MNQ at intraday horizon without a NEW mechanism,
  pre-registered afresh. The two negative results also raise the prior against
  MES–M2K; if M2K comes back positive it must be scrutinised harder, not less.

## D-014 — 2026-08-02 — PRE-REGISTRATION of the notebook-02 A-006 test (MES–M2K)

Written before the MES–M2K series were built and before any MES–M2K statistic
existed. Last index pair in the D-008 priority order.

- **Decision:** Test A-006 for MES–M2K under the **identical frozen protocol**
  used for MES–MYM and MES–MNQ (D-010 + A1 + A2). Data path, gate, three
  specifications, 4x5 grid, variance-ratio curves with leg baselines and the
  base-sampling check, verdict rule, and seed all carry over verbatim. Signal
  configuration is again held constant: L-013 stays unfixed until notebook 06,
  so all three index pairs remain mutually comparable.
- **Only permitted differences:** the second leg symbol (M2K, `Market.CME`).
- **This run has a SECOND purpose that is independent of the verdict.** M2K is
  the symbol whose QC-provided continuous series was worst — bad factors at
  **19 of 28** rolls (validation report 01 §3), against 14 for MYM and 4 for
  MNQ. It is therefore the strongest live test of the D-009 own-splice
  constructor. The EXP-007 acceptance run already built M2K standalone and
  produced exactly one conservative flag (M2KM19 2019-06-13: −6 bp splice
  return against a +26 bp factor gap). **Prediction, recorded in advance:** that
  same roll should flag again, and the A1 bound should classify it
  `sign_mismatch` (the splice return and the gap have opposite signs), leaving
  the gate PASSED. If instead the gate fails, or a different set of rolls flags,
  the constructor is not deterministic and that finding outranks the A-006
  question.
- **Prior, stated in advance.** MES–MYM (the only daily-cointegrating pair) and
  MES–MNQ (the highest co-mover, deepest book) both returned NO REVERSION with
  significant continuation at entry_z 1.5-2.0. M2K is the weakest co-mover of
  the three (0.87 daily) and the thinnest book, so a negative result is strongly
  expected. **A POSITIVE result here must be scrutinised HARDER, not accepted
  more readily** — on this pair a spurious VR < 1 from bid-ask bounce is more
  likely, not less. Before any positive verdict is written: check the residual
  VR against BOTH leg baselines, and confirm the effect survives 5-minute base
  sampling. Those checks are already in the battery; this clause fixes in
  advance that they are decisive rather than advisory.
- **Alternatives:** skip M2K and declare the index book closed on two negatives
  (rejected — D-008 committed to testing the pairs, and skipping the one that
  best exercises the constructor would waste the run's second purpose); loosen
  the rule because two pairs already failed (rejected outright).
- **Expected effect:** an A-006 verdict for MES–M2K plus a determinism check on
  the D-009 constructor. If negative, the index book is closed at intraday
  horizon and notebook 03 / the Treasury curve (A-009) becomes the program's
  remaining live hypothesis — a legitimate outcome under CLAUDE.md gate 4.
- **Review:** No re-test without a NEW mechanism, pre-registered afresh.

## D-015 — 2026-08-02 — MES–M2K returns AMBIGUOUS / MICROSTRUCTURE; index book closed as an intraday reversion book

- **Decision:** MES–M2K returns the **AMBIGUOUS / MICROSTRUCTURE** branch of the
  frozen D-010 rule. Criteria (a) and (c) are SATISFIED — positive with
  session-clustered |t| >= 3 across adjacent horizons in S1 AND S2, monotone in
  entry threshold, and at +6.31 bps the largest cell would clear the ~2-3 bps
  round-trip. Criterion (b) FAILS. **The pair does not advance, and A-006 for
  MES–M2K is UNRESOLVED — neither confirmed nor falsified.**
- **What decided it, exactly as D-014 fixed in advance.** The base-sampling
  check: at matched ~30 minutes elapsed the residual VR runs 0.813 (1-min bars)
  -> 0.897 (5-min) -> 0.956 (15-min), and at 5-minute base sampling with q=30/60
  the VR is 0.942/0.940 at bootstrap p = 0.13/0.15 — not significantly below 1.
  The shape check agrees: VR(120)/VR(30) = 0.947, a floor rather than the ~1/q
  decay of mean reversion (module calibration: planted AR(1) 0.66, planted
  bounce >0.85).
- **Mechanism [PLAUSIBLE]:** lead-lag, not reversion. M2K's own VR at q=2 is
  **1.012 (p_lt_1 = 0.935), ABOVE 1** — lagged price adjustment, opposite in
  sign to the bounce depressing MES (0.988). A spread against a lagging leg
  mechanically converges as the laggard catches up, most strongly when the
  dislocation is largest — which is the monotone-in-entry_z surface observed —
  and the effect disappears once bars are coarse enough to contain the catch-up.
  *AMENDED 2026-08-04 by D-023 (report 14): the pre-registered test ran. The
  lead-lag is REAL but one bar deep and ~0.03 of correlation — withdrawn as
  the explanation of the conditional surface, which survives delayed entry
  (DELAY-ROBUST). The base-sampling evaporation this bullet tried to explain
  is now an open puzzle. Verdict branch unchanged.*
- **Alternatives:** (i) call it REVERSION PRESENT on the strength of (a)+(c)
  and the cost-clearing effect size (rejected — (b) is not optional, and D-014
  pre-committed the base-sampling check as decisive precisely so this decision
  could not be made after seeing the number); (ii) dismiss it as multiple
  testing across 180 cells (rejected as the primary argument — a monotone
  surface with t up to 5.7 in two specs is not what 180 independent draws
  produce; the base-sampling result is the honest reason, not the cell count);
  (iii) run the delayed-entry test opportunistically right now and report
  whichever answer it gives (rejected — that test must be pre-registered on its
  own terms, not bolted onto a run whose result is already known).
- **Consequence for the program.** All three index pairs are done: two FALSIFIED,
  one UNRESOLVED-with-a-microstructure-signature. **No index pair has produced a
  tradable intraday reversion result.** The index book is closed as an intraday
  reversion book. The Treasury curve (A-009, notebook 03) is now the program's
  primary live hypothesis — a legitimate outcome under CLAUDE.md gate 4.
- **The one open thread, and its price.** The MES–M2K delayed-entry test
  (entry at t+2 / t+5 / t+15 instead of t+1, plus leg-return cross-correlation
  at lags ±1..5) would settle lead-lag versus reversion in a single run. It is
  worth doing because a confirmed lead-lag effect in the thinnest micro is
  itself a documented finding, and because leaving A-006 unresolved for one pair
  is untidy. It is NOT worth doing before notebook 03: a lead-lag effect in the
  least liquid contract of the universe is the least likely of the remaining
  candidates to survive execution modelling (notebook 07). Sequence: notebook 03
  first, then this.
- **Evidence:** validation report 02 §12; run "Well Dressed Green Tapir"
  (QC 34720894); EXP-010; `reports/machine_readable/nb02_MES_M2K_*.csv`.
- **Also established by this run:** the D-009 constructor is **deterministic**.
  D-014 predicted in writing which roll would flag (M2KM19 2019-06-13), with
  what numbers (-6 bp splice vs +26 bp gap) and what classification
  (`sign_mismatch`); all three reproduced exactly, on the symbol whose
  QC-provided series was worst (19/28 bad factors).
- **Review:** No re-test of MES–M2K under this protocol. The delayed-entry test
  is a NEW mechanism and gets its own pre-registration.

## D-016 — 2026-08-02 — PRE-REGISTRATION of notebook 03: A-009 for ALL FOUR Treasury pairs

Written before any Treasury series was built and before any Treasury statistic
existed. **All four pairs are registered together, deliberately**, so that the
protocol cannot be adjusted between pairs and the multiple-comparison structure
is fixed in advance rather than reconstructed afterwards.

- **Hypothesis under test:** A-009 — "Treasury pair residuals mean-revert at
  intraday horizon in DV01/vol-hedged space."
- **Pairs and ORDER, fixed now:** ZF–ZN (5s10s, the most liquid RV segment) →
  ZT–ZF (2s5s) → ZN–ZB (10s30s) → ZT–ZN (2s10s, widest maturity gap and largest
  structural component). Liquidity-first, because L-014 showed a thin leg
  manufactures a lead-lag surface that mimics reversion.
- **Protocol:** identical to notebook 02 — D-010 as amended by A1 (splice
  adjudication is a bound) and A2 (primary statistic is position P&L with beta
  frozen at the signal bar; session-clustered mean reported beside the pooled
  mean). Same gate-before-analysis ordering, same 4x5 entry/horizon grid, same
  variance-ratio curves with leg baselines and base-sampling checks, same
  verdict rule (REVERSION PRESENT / NO REVERSION / AMBIGUOUS-MICROSTRUCTURE),
  same seed 20260801, same signal configuration (L-013 stays unfixed until
  notebook 06 so every pair in the program remains comparable).

### The one deliberate change from notebook 02, and why

**S1's anchor becomes the volatility-ratio hedge, beta = sigma_a/sigma_b,
instead of beta = 1.** This is an economic correction, not a free parameter:

- A unit beta is defensible for the index micros, whose legs are large-cap
  index futures of similar duration and volatility. It is **wrong** across the
  curve: ZT carries roughly a fifth of ZN's duration, so a 1:1 log spread is
  the long leg plus noise, not a spread. Testing A-009 with beta = 1 would test
  a position no one would hold.
- **D-008 already mandates this**, on evidence: Treasury hedge ratios are
  regime-driven (ZT–ZN 126-day beta ranged 0.0-0.4 across 2010-26), so adaptive
  hedging is required and long-lookback static hedges are demoted to control.
  The vol ratio is the estimation-LIGHT adaptive hedge — one robust moment per
  leg rather than a regression, so it carries far less estimation noise than
  OLS (L-007).
- **DV01 was the first choice and is unavailable.** A true DV01 hedge needs the
  cheapest-to-deliver bond's duration, which is not derivable from QC minute
  bars and is not in `data/metadata/contract_specifications.csv`. Inventing
  plausible DV01s would be fabricating an input. The vol ratio is the honest
  substitute and is documented as such.
- Derivation (in `vol_ratio_beta`): dollar-vol neutrality gives
  n_b = (mult_a*P_a*sigma_a)/(mult_b*P_b*sigma_b); normalising the spread by
  leg A's notional makes the log-space coefficient **sigma_a/sigma_b**, with
  multipliers and price levels cancelling.
- S1 is formed through `centered_residual` because a time-varying beta times a
  log price level manufactures the L-011 artifact regardless of asset class
  (log(110) = 4.7, so 0.001 of beta drift injects ~5 bps).
- S2 (trailing OLS residual) and S3 (full-sample static OLS) are unchanged. Per
  D-008, S3 is explicitly a **control** for Treasuries, not a candidate.

### Roll construction (differs from the index pairs)

`treasury_roll_schedule` — last business day of the month BEFORE the delivery
month, splice 10:30 ET, CME holidays passed. Chain opens at U19 (the June-2019
contract has already rolled off by the 2019-06-01 window start), giving 28
codes and **27 rolls**, which reproduces the EXP-007 ZN acceptance exactly.
QC's own OpenInterest flip is not used: report 01 §2 measured it at 18-36 days
pre-expiry with only 15-52% volume share, i.e. the wrong event, mirroring the
index case.

### Declared in advance, so they cannot become excuses afterwards

1. **The base-sampling check and the leg-VR baselines are DECISIVE, not
   advisory** — the same clause D-014 carried, now standing for all four pairs.
   L-014 is the reason: M2K produced a monotone, cost-clearing, t=5.7 surface
   that was pure lead-lag. Any positive Treasury result must survive coarsening
   to 5-minute base bars and must sit materially below BOTH legs' own VR.
2. **Roll windows are pair-specific (L-015).** The 780-bar post-roll warm-up
   adopted for the index pairs is NOT assumed here; each pair's buckets are
   measured and its own windows adopted.
3. **A-012 is live for ZN–ZB.** CTD switches and delivery-cycle effects are a
   documented hazard at the long end; a structural jump must not be read as a
   tradable dislocation. If ZN–ZB produces a positive result, the CTD-switch
   dates are checked before anything else.
4. **Session window.** RTH stays 09:30-16:00 ET per `research_config`
   session_filter, the same window used for every index pair. This is NOT the
   most liquid Treasury window — the cash open around 08:20 ET is excluded —
   and that is a known limitation of holding A-013 constant for comparability,
   to be revisited in the intraday-seasonality work, not silently varied here.
   *AMENDED 2026-08-04 by D-024 (L-021): this clause is FACTUALLY WRONG about
   what ran. `rth_frame` filters on the clock the data carries, and LEAN stamps
   CBOT Treasury bars in America/Chicago, so the four Treasury pairs were
   analysed on 09:30-16:00 CT = **10:31-17:00 ET** — missing 09:30-10:30 ET
   entirely and running two hours PAST the 15:00 ET Treasury settlement. The
   exclusion of the 08:20 ET cash open is therefore understated by an hour, and
   the splice documented here as "10:30 ET" is 10:30 CT = 11:30 ET for
   Treasuries. The reservation in this clause — revisit the session in separate,
   pre-registered work — is what D-024 discharges; the verdicts of D-017/D-018
   are not withdrawn but are UNCONFIRMED on the window they claim to describe.*
5. **Multiple testing.** Notebook 02 examined 180 cells. These four pairs add
   240 more, for 420 under one protocol. Verdict rule (c) — the effect must
   strengthen with entry threshold rather than live in one cell — is what
   guards against that, and it is unchanged.

- **Prior, stated in advance:** the index book produced no tradable intraday
  reversion (two falsified, one lead-lag artifact). The daily screen found every
  Treasury pair trending secularly with no long-run anchor, but it explicitly
  could not test the intraday hypothesis. Treasury curve trades have a genuine
  structural story that the index pairs lack, so this is a real test rather than
  a formality — but the same bar applies, and no result is accepted that fails
  the base-sampling check.
- **Alternatives:** run one pair, and only continue if it looks promising
  (rejected — that is selection on the outcome); use beta = 1 for comparability
  with notebook 02 (rejected — comparability is not worth testing an
  economically meaningless position); wait for real DV01 data (rejected as a
  blocker — the vol ratio is a documented, defensible substitute, and the
  DV01 comparison is notebook 04's job).
- **Expected effect:** an A-009 verdict per pair. If all four are negative or
  microstructural, Version 1's core hypothesis has no surviving candidate at
  intraday horizon and the program's honest conclusion is to report that —
  a legitimate outcome under CLAUDE.md gate 4.
- **Review:** No re-test of any Treasury pair under this protocol without a NEW
  mechanism, pre-registered afresh.

## D-017 — 2026-08-02 — ZF–ZN: statistically overwhelming, economically 11x too small; AMBIGUOUS / IMMATERIAL

First Treasury pair under D-016. Run "Calculating Tan Cormorant".

> **ANNOTATED 2026-08-05 (L-021, measured by D-025).** This decision was
> reached on **(09:30, 16:00] CT = 10:31–17:00 ET**, not the 09:30–16:00 ET it
> and D-016 state — LEAN stamps CBOT Treasury bars in America/Chicago. D-025
> re-ran the corrected window: ZF–ZN's largest honest effect moves **1.10x**
> against a pre-registered 2.0x materiality bar and the verdict branch is
> unchanged. **The decision stands on its own numbers; only its window label
> was wrong.** Per L-024, edge-relative subsets (this pair's open-window cut)
> are a separate matter and were NOT unaffected — see L-024.

- **Decision:** ZF–ZN returns **AMBIGUOUS / MICROSTRUCTURE**, and is
  additionally labelled **ECONOMICALLY IMMATERIAL** under the D-010 clause.
  The pair does not advance. A-009 is UNRESOLVED for ZF–ZN.
- **Criterion (a) is satisfied more strongly than anywhere in the program.**
  20/20 cells in S1 and 20/20 in S3 are positive at session-clustered |t| >= 3
  (18/20 in S2), with t reaching **9.44**. Every entry threshold, every horizon,
  all three specifications, same sign.
- **And it is untradeable by an order of magnitude.** The largest honest
  session-mean is **+0.286 bps**. One round trip costs ~**3.1 bps** of residual
  (ZF tick = 0.72 bps of its notional; ZN tick = 1.42 bps, contributing
  beta*1.42 = 0.83 bps at beta = 0.583; crossing both legs in and out), before
  the A-007 commission placeholder. **The effect is ~11x smaller than the cost
  of harvesting it.** This is the case D-010 anticipated when it required effect
  sizes in bps beside every t-statistic: at n = 675,840 bars, significance is
  free and meaningless on its own.
- **Criterion (b) fails decisively on the D-016 base-sampling check.** At
  matched ~30 minutes elapsed the residual VR runs **0.134 (1-min bars) ->
  0.467 (5-min) -> 0.827 (15-min)**. A VR of 0.10-0.13 at 1-minute sampling is
  not a relationship; it is tick quantisation. Both legs are themselves
  bounce-dominated (ZF 0.72, ZN 0.58 at q=120) because Treasury tick sizes are
  coarse relative to minute-level volatility, and the vol-ratio hedge cancels
  the common duration risk, leaving the quantisation noise as most of what
  remains.
- **Alternatives:** (i) call this REVERSION PRESENT on the strength of t = 9.44
  (rejected — (b) fails and the effect is 11x below cost; either alone is
  disqualifying); (ii) argue costs could fall enough to matter (rejected — an
  11x gap is not a fee-schedule question, and A-007/A-008 are placeholders that
  if anything understate cost); (iii) read the raw AR(1) half-life of 152 bars
  as evidence of a real level anchor (rejected — see the caveat below).
- **Interpretation caveat, important for the remaining pairs.** `S_HL`'s
  `raw_hl` is NOT comparable between notebook 02 and notebook 03. For the index
  pairs S1 was a raw log spread, so `raw_hl` measured a genuine level anchor
  (70k-107k bars). For the Treasury pairs S1 is the CENTERED residual around a
  trailing 1950-bar fit, so its half-life (152 bars here) is partly mechanical —
  the reference point itself moves. The conditional statistic is unaffected,
  because A2 made it price the position from the legs with beta frozen at entry.
  Do not quote treasury `raw_hl` as a reversion speed.
- **Two clean structural findings, both new:**
  1. **Treasury roll windows are flat.** Residual dispersion around the splice
     is 0.89x / 1.01x / 1.01x / 1.00x of baseline — no elevation at all, unlike
     every index pair (which ran 1.6x-2.6x). Month-end rolls sit far from
     expiry with continuous liquidity. **No post-roll warm-up extension is
     needed for ZF–ZN**, in contrast to L-015 for M2K.
  2. **L-013's open-clustering is absent.** Only 12.7% of crossings land in the
     first 30 minutes here, against 22.7-24.7% for all three index pairs, and
     the profile is nearly flat across the session. This confirms the mechanism:
     the clustering was an equity-session-open artifact of scoring the first
     bars against the previous session's mean. Treasuries have been trading
     through the night, so 09:30 ET is not an open for them.
- **The vol-ratio anchor was the right call.** Its beta is far more stable than
  the OLS beta on the same pair (p5-p95 of 0.495-0.693 versus 0.395-0.805) and
  its median of 0.583 is economically sensible for 5y-vs-10y. D-016's economic
  argument is supported by the data rather than merely asserted.
- **Evidence:** run "Calculating Tan Cormorant" (QC 34720894); EXP-011;
  `reports/machine_readable/nb02_ZF_ZN_*.csv`. Gate: 27 rolls per leg, ZERO
  flags on both, zero dropped bars.
- **Review:** No re-test of ZF–ZN under this protocol. Continue to ZT–ZF, ZN–ZB,
  ZT–ZN in the D-016 order; the remaining three are NOT cancelled by this
  result, since D-016 fixed the order and skipping would be selection on outcome.

## D-018 — 2026-08-03 — A-009 closed on all four Treasury pairs; Version 1 has no surviving intraday candidate

> **ANNOTATED 2026-08-05 (L-021, measured by D-025).** All four verdicts below
> were reached on **(09:30, 16:00] CT = 10:31–17:00 ET**, not the 09:30–16:00
> ET stated here and in D-016 — LEAN stamps CBOT Treasury bars in
> America/Chicago. D-025 re-ran every pair on the corrected window: largest
> honest effects move **1.01x (ZT–ZF), 1.10x (ZF–ZN), 1.14x (ZT–ZN), 1.26x
> (ZN–ZB)** against a pre-registered 2.0x bar, and **no branch changes**. The
> cost shortfalls are not a one-hour artifact and L-016's tick quantisation is
> window-independent. **These decisions stand; the label was wrong, the
> conclusions were not.** Per L-024 this does NOT extend to edge-relative
> subsets.

- **Decision:** All four Treasury pairs return **AMBIGUOUS / MICROSTRUCTURE and
  ECONOMICALLY IMMATERIAL** under the D-016 pre-registration. None advances.
  A-009 is unresolved-but-immaterial for ZF-ZN, ZT-ZF, ZN-ZB and ZT-ZN.
- **Consistency of the result.** Criterion (a) is satisfied in every pair
  (16-20 of 20 S1 cells positive at session-clustered |t| >= 3, t up to 9.4),
  the sign is right everywhere, and the effect is 7-11x below the round-trip
  cost computed from VERIFIED tick specifications in every pair. The
  base-sampling check fails in every pair, with the residual VR walking 3-6x
  back toward 1 as bars coarsen from 1 to 15 minutes.
- **The program-level consequence, stated plainly.** All seven pairs in the
  locked universe have now been tested at minute resolution under one frozen
  protocol: three index pairs (D-011, D-013, D-015) and four Treasury pairs
  (this decision). **Not one has produced a tradable intraday reversion
  result.** Version 1's core hypothesis — that hedged index or curve residuals
  mean-revert at intraday horizon by enough to trade — has **no surviving
  candidate**. Under CLAUDE.md gate 4 this is a legitimate research outcome and
  is recorded as the finding, not worked around.
- **What is NOT concluded.** That these markets contain no structure. They
  contain a real, consistent, correctly-signed effect that is simply smaller
  than the tick. What is concluded is that it is not harvestable at the cost
  scale and resolution this project targets.
- **Alternatives considered:** (i) declare a Treasury pair viable on the
  strength of t = 9.4 (rejected — 7-11x below cost, and the base-sampling check
  D-016 pre-committed as decisive fails); (ii) assume better execution closes
  the gap (rejected — a threefold cost improvement still leaves every pair
  uneconomic, so the conclusion is robust to the A-007/A-008 placeholders being
  badly wrong); (iii) try more hedge methods on the same data until something
  passes (rejected outright — that is a specification search, and D-008 already
  fixed the hedge question for this asset class).
- **The three genuinely open threads, in priority order.** Each is a NEW
  program requiring fresh pre-registration; none may reuse this window's
  results as evidence.
  1. **Notebook 06 / L-013:** session-anchor the z-score and re-run the closed
     pairs. This changes the SIGNAL definition, not the hypothesis, and is the
     cheapest remaining test of whether the whole grid was mis-specified.
  2. **MES-M2K delayed entry (D-015):** t+2 / t+5 / t+15 to separate lead-lag
     from reversion. Confirms or kills the one non-negative index result.
  3. **Resolution and venue:** every negative here is at MINUTE resolution on
     TRADE bars during equity RTH. Quote data, a Treasury-native session
     (08:20 ET), or second/tick resolution are different experiments, not
     re-runs. `research_config.data.later_resolutions` already anticipates this.
- **Expected effect:** notebooks 04-13 as originally scoped are moot for
  Version 1 in their current form: there is no candidate to select a hedge for,
  size, cost-model or walk-forward. The honest next deliverable is the
  final research summary (notebook 13 / report 13) recording a negative
  program outcome with its evidence, plus whichever open thread the user
  chooses to fund.
- **Review:** No re-test of any of the seven pairs under this protocol on this
  window. The window is spent for this hypothesis.

## D-019 — 2026-08-03 — Version 1 concluded NO-GO at intraday horizon; the negative outcome is banked as the deliverable

- **Decision:** Record the program's outcome as a **no-go for Version 1 as an
  intraday relative-value reversion program**, in notebook 13 and
  `reports/13_final_research_summary.md`. No LEAN build is recommended and the
  `PROCEED TO LEAN BUILD` token is not sought. Notebooks 04-12 as originally
  scoped are moot for Version 1: with zero candidates there is nothing to select
  a hedge for, size, cost-model, walk-forward, stress-test or allocate.
- **What this decision adds to D-018.** D-018 closed the last hypothesis; this
  one closes the PROGRAM and states what survives it. Nothing new was measured:
  the summary recomputes every headline figure from the banked run outputs
  rather than re-typing reports 02 and 03. No new experiment ID is issued
  precisely because no new statistic was computed — inventing an EXP row for a
  reconciliation would overstate what was done.
- **The reconciliation is enforced, not asserted.**
  `src/spread_research/program_summary.py` reads only
  `reports/machine_readable/nb02_<PAIR>_*.csv`, and
  `tests/unit/test_program_summary.py` pins every published effect size,
  t-statistic, variance-ratio walk, treasury cost and open-clustering share
  against those same CSVs. If a validation report and its own evidence ever
  drift apart, the test fails rather than the summary quietly agreeing with the
  prose. All seven pairs reconciled on the first run; 168 tests green.
- **Cost accounting, stated so it cannot be quietly widened later.** Treasury
  round-trip costs are derived in code from the VERIFIED tick specs (A-003) and
  each pair's own median vol-ratio beta, reproducing report 03's table to two
  decimals. Index-pair costs are carried as report 02 §5's 2-3 bps band, whose
  LOW end is used so the comparison is as generous to the effect as the evidence
  allows. MNQ and M2K are deliberately absent from `TICK_BPS`: no representative
  notional for them is established anywhere in this repo, and inventing one to
  make a table symmetric would be fabricating an input (a test pins their
  absence).
- **What is recorded as surviving the conclusion:** the D-009 own-splice
  constructor (validated on all eight instruments, deterministic twice, against
  a FALSIFIED A-004); the tested battery; the one-signed MES-MNQ roll carry
  (~70 bps/yr); asset-class-specific roll windows (L-015/L-017); and above all
  the four near-miss fake edges with the three-part rule they imply — measure the
  position's P&L, compare against BOTH legs' own variance ratios, and confirm the
  result survives coarser base sampling.
- **Alternatives:** (i) leave the program undocumented and move straight to the
  open threads (rejected — the negative outcome IS the deliverable, and an
  unbanked negative gets silently re-litigated); (ii) present the Treasury
  t-statistics as a "promising" result pending better execution (rejected —
  CLAUDE.md gate 3, and a 7-11x shortfall is not a fee-schedule question);
  (iii) soften MES-M2K to "unresolved, leaning positive" (rejected — it is
  UNRESOLVED, and the delayed-entry test is what decides it, not prose).
- **Evidence:** `reports/13_final_research_summary.md`; notebook 13 executed
  locally with outputs banked; `reports/machine_readable/nb13_program_summary.csv`
  and `nb13_funnel.csv`; `reports/figures/nb13_{effect_vs_cost,base_sampling}.png`;
  validation reports 01/02/03; EXP-005 - EXP-014.
- **Expected effect:** the program's record is closed and self-contained. The
  three open threads (notebook 06 / L-013, MES-M2K delayed entry, different
  resolution or venue) each require fresh pre-registration and may not reuse this
  window's results as evidence.
- **Review:** Revisit only if one of the open threads returns a result, or if
  the user funds a Version 2 with a different mechanism.
- **AMENDED 2026-08-03 by D-021 (open thread 1 was funded and ran the same
  day).** The no-go stands and no pair advanced. One supporting claim in
  report 13 §3 is corrected: the significant CONTINUATION in MES-MYM and
  MES-MNQ is carried by first-30-minute events, not by intraday behaviour away
  from the open. Report 13 carries the amendment inline; the conclusion,
  the funnel and the recommendation are unchanged.

## D-020 — 2026-08-03 — PRE-REGISTRATION of notebook 06: session-anchored z-score (L-013)

Written before the session-anchored z-score existed in code and before any
number under it existed. Open thread 1 of D-018/D-019. Nothing below may be
revised in response to an outcome; a revision voids the test and forces a fresh
pre-registration.

### What is actually being tested, stated honestly first

L-013: the configured z-window is 390 bars = one RTH day, so it reaches back
ACROSS the overnight break and the first bars of a session are scored against
yesterday's mean. Measured consequence: **22.7-24.7% of |z| >= 2 crossings in
the three index pairs land in the first 30 minutes** (MYM 24.3, MNQ 24.7, M2K
22.7), against **12.7-13.6% in the four Treasury pairs**, whose profile is
nearly flat. Treasuries trade through the night, so 09:30 ET is not an open for
them — which is why the same configuration produces clustering in one asset
class and not the other, and why this is a property of the SIGNAL DEFINITION.

**This is a robustness test of a negative conclusion, not a second attempt at a
positive one, and the reason is structural rather than a matter of taste.**
Criterion (b) of the D-010 verdict rule — the variance-ratio shape and
base-sampling checks — is computed on the RESIDUAL and does not involve the
z-score at all. Changing the signal definition therefore cannot change (b), and
(b) already failed in all seven pairs. Under the frozen rule a pair can move
from NO REVERSION to AMBIGUOUS / MICROSTRUCTURE under a new signal; **it cannot
reach REVERSION PRESENT.** That is stated here, in advance, so that a positive
(a) result under the new signal cannot later be presented as more than it is.

What the test can genuinely settle: whether the program's measured effects — in
particular the significant CONTINUATION at entry_z 1.5-2.0 that falsified
MES-MYM and MES-MNQ — were an artifact of scoring overnight repricings as
intraday dislocations, or survive their removal.

### Decision — the three signal definitions, fixed now

All three are computed in the same run on the same bars, and all three are
reported side by side. None is privileged after the fact.

- **Z0 — the current definition (baseline, already spent).**
  `rolling_zscore(residual, 390)`, shifted; window spans the overnight break.
  Re-emitted in this run for one purpose only: it must REPRODUCE the banked
  notebook-02 numbers for the same pair. See the validity gate below.
- **Z1 — session-anchored (the fix under test).** At bar t of session s, mean
  and standard deviation are taken over the bars of session s strictly before
  t, i.e. an expanding within-session window, with no bar from any prior
  session entering. Note this is the SAME object as "trailing 390 bars
  truncated at the session open", because an RTH session is exactly 390 bars —
  so the fix introduces no new window-length parameter.
  **Warm-up: z is undefined (NaN, no event) for the first 30 bars of each
  session.** Fixed at 30 now, and justified before the fact: a standard
  deviation from fewer than ~30 observations has over 13% relative standard
  error, so a shorter warm-up would replace an overnight-gap artifact with an
  estimation artifact; 30 minutes is also the bucket width the event clock
  already uses, so the diagnostic and the signal agree on the same grid.
- **Z2 — Z0 with first-30-minute events excluded (the decomposition).** The
  unchanged 390-bar overnight-spanning score, with events whose signal bar is
  in the first 30 minutes of the session dropped. Z2 exists because Z1 changes
  two things at once — how the open is SCORED and whether the open TRADES — and
  without Z2 a change in the grid could not be attributed to either. Z2 removes
  the open without re-scoring; Z1 does both.

Everything else is frozen exactly as in D-010 as amended by A1 and A2: the same
own-splice constructed data path and acceptance gate, the same three residual
specifications (S1/S2/S3 with S3 look-ahead and never evidence), the same 4x5
entry/horizon grid, the same position-P&L primary statistic with beta frozen at
the signal bar, the same session-clustered inference, the same seed 20260801,
and the same anchor per asset class (`unit` for index, `vol_ratio` for
Treasuries).

### Decision — pairs, and why not all seven

Four runs: **MES-MYM, MES-MNQ, MES-M2K** — the three pairs in which L-013 is
present — plus **ZF-ZN as a negative control**, the pair in which it is absent
(12.7% at the open, flat profile). The control is the point of including a
Treasury pair at all: the session anchor should move the index pairs and should
NOT materially move ZF-ZN, and if it moves ZF-ZN just as much then the fix is
doing something other than what it claims.

The other three Treasury pairs are NOT run. Their disqualification is a cost
ratio of 7-9x, and no re-definition of the entry signal can raise a 0.166-0.664
bps effect through a 1.4-5.9 bps cost. Running them would burn free-tier
backtests to re-confirm a conclusion the signal cannot reach. This scope is
fixed now so it cannot be widened after seeing the four results.

### Decision — VR blocks are NOT recomputed, and why that is not a shortcut

The variance-ratio curves, the leg baselines and the base-sampling checks are
functions of the residual and the sampling interval only. No z-score enters
them. They are therefore carried forward unchanged from EXP-008/009/010/011 and
criterion (b) keeps its existing value for each pair. Recomputing them would
consume most of the run's output budget to reproduce identical numbers.

### Decision — validity gates, applied BEFORE the grid is read

Both are pass/fail on mechanics, not on outcome, and either failure voids the
run rather than producing a result to interpret.

1. **Reproduction gate.** The Z0 grid emitted by this run must reproduce the
   banked notebook-02/03 grid for the same pair (`nb02_<PAIR>_conditional_
   reversion.csv`) cell for cell, to the emitted precision. If it does not, the
   pipeline changed and no comparison between Z0 and Z1 is meaningful.
2. **Implementation gate.** Under Z1 the share of |z| >= 2 crossings in the
   first 30 minutes must be **zero by construction** (the warm-up forbids them),
   and the share in the 30-60 minute bucket must fall below the Z0 share for the
   same bucket in the same pair. If the profile does not flatten, the anchor is
   not doing what L-013 says it does and the implementation is wrong.

### Decision — verdict rule, declared now

Per pair, the D-010 rule is re-applied to the Z1 grid unchanged: (a) positive
with session-clustered |t| >= 3 at >= 2 adjacent horizons in S1 AND S2;
(b) inherited from the pair's existing variance-ratio evidence; (c) the effect
strengthens with entry threshold. Effect sizes in bps beside every t-statistic.

Program-level readings, fixed in advance:

- **L-013 IMMATERIAL** if every pair's Z1 verdict equals its Z0 verdict. The
  D-019 no-go stands, strengthened: the negative outcome is not an artifact of
  the signal definition, and L-013 closes.
- **L-013 MATERIAL — DIRECTION ONLY** if a Z1 verdict differs from its Z0
  verdict. The pair does NOT advance on this evidence: (b) is unchanged and the
  window is the same one already spent, so a flip is HYPOTHESIS-GENERATING and
  requires a fresh window, venue or resolution to confirm. What it would change
  is the priority of open thread 3, not the program's conclusion.
- **IMPLEMENTATION DEFECT** if either validity gate fails: no verdict is read
  and the run is repeated after the defect is fixed.

Multiple testing, stated rather than reconstructed: this adds 4 pairs x 3 specs
x 4 entries x 5 horizons x 2 new signal definitions = **480 cells** to the 420
already examined. That is precisely why a flip cannot advance a pair here, and
why the interpretation bar above is set on direction rather than on any single
cell.

### Prior, stated in advance

The index pairs' significant cells are CONTINUATION concentrated at entry_z
1.5-2.0, which is where the event count is largest and therefore where
open-clustered events are most heavily represented. If those events are
overnight repricings that keep repricing, removing them should move the index
grids TOWARD zero rather than toward positive. The expected outcome is
therefore weaker continuation, unchanged verdicts, and L-013 closing as
immaterial. ZF-ZN is expected to be almost unchanged.

### Secondary, and explicitly EXPLORATORY

The open subset itself — events whose signal bar is in the first 30 minutes
under Z0 — is reported as its own conditional statistic, because L-013 listed
"test the open-gap subset as its own hypothesis" as one of the three legitimate
fixes. It is labelled EXPLORATORY and no verdict is issued on it: overnight-gap
reversion is a DIFFERENT hypothesis from A-006, the residual variance ratio is
not the right supporting statistic for it, and inventing a verdict rule for it
after seeing this run's numbers is exactly what pre-registration exists to
prevent. A positive here buys a fresh pre-registration and nothing else.

- **Alternatives:** (i) fix L-013 by lengthening the z-window to 1,950 bars so
  the overnight break is a smaller fraction of it (rejected — it dilutes the
  break rather than removing it, and it changes the horizon the signal is
  normalised against, which is a second confound); (ii) drop the first 30
  minutes from the DATA rather than from the events (rejected — that also
  removes those bars from every residual, variance-ratio and half-life estimate
  and would make this run non-comparable to notebook 02); (iii) run all seven
  pairs (rejected — see scope above); (iv) tune the warm-up length after seeing
  the event clock (rejected outright — that is the specification search this
  project's whole method exists to avoid).
- **Evidence to be produced:** report
  `reports/validation/06_signal_definition_and_session_anchoring.md`, machine-
  readable `nb06_<PAIR>_*.csv`, EXP-015 onward, one QC run per pair.
- **Expected effect:** L-013 resolved in one direction or the other, and the
  D-019 conclusion either strengthened or given a documented caveat.
- **Review:** No re-run of any pair under this protocol on this window. If a
  verdict flips, the follow-up is a different window/venue, pre-registered
  afresh — not another pass over these bars.

## D-021 — 2026-08-03 — L-013 is MATERIAL (direction only); the index "continuation" was an open-window effect; D-019 stands

Four runs under D-020: MES–MYM "Hyper Active Tan Hippopotamus", MES–MNQ
"Muscular Blue Goshawk", MES–M2K "Crawling Magenta Barracuda", ZF–ZN "Measured
Black Lion". EXP-015 - EXP-018, validation report 06.

- **Decision:** Read L-013 as **MATERIAL — DIRECTION ONLY**, the branch D-020
  fixed in advance for the case where a Z1 verdict differs from its Z0 verdict.
  MES–M2K's does: criterion (a) is satisfied under Z0 (D-015, AMBIGUOUS) and
  fails under Z1. **No pair advances**, and the D-019 no-go stands.
- **Both validity gates passed in all four runs, and were read first.** Gate 1:
  the Z0 grid reproduced the banked notebook-02/03 grid **60/60 cells exactly**
  in every pair, so the data path is byte-identical and the Z0-vs-Z1 comparison
  is a measurement rather than a comparison of two pipelines (also a fourth
  determinism check on the D-009 constructor). Gate 2: the Z1 event clock goes
  to 0.0% inside the warm-up in every pair, against 22.7-24.7% (index) and
  12.7% (Treasury control) under Z0. Enforced in code by
  `ingest_qc_signal_definition.py --compare-nb02`, which writes nothing on a
  failure.
- **The finding, and it corrects how an earlier result must be read.** The
  significant CONTINUATION that falsified MES–MYM (D-011) and MES–MNQ (D-013)
  was carried by events in the first 30 minutes of the session. Removing those
  events and nothing else (Z2 — same score, same grid, same specs, same
  inference) flips every significant honest cell from negative to positive:
  MES–MYM 16 significant cells all negative becomes 25 all positive; MES–MNQ 15
  all negative becomes 21 all positive. The open subset alone (ZO) is negative
  at every horizon in all three index pairs AND is the only negative row
  anywhere in the Treasury control's grid (-0.15 bps at t = -3.87). An
  overnight repricing scored against yesterday's mean is a level change that
  persists, not a dislocation that reverts.
- **Why this does not advance anything, exactly as pre-registered.**
  (i) Criterion (b) is computed on the RESIDUAL — no z-score enters it — so it
  is unchanged and still fails in all four pairs; the best branch reachable is
  AMBIGUOUS / MICROSTRUCTURE, and D-020 said so before these numbers existed.
  (ii) This is the same window already spent, so a sign flip is
  hypothesis-generating, not evidence. (iii) The effect sizes that now sit at
  or above the index cost band (Z2: MYM +2.40, MNQ +3.12, M2K +6.77 bps against
  ~2-3 bps) rest on A-007/A-008 placeholders, which is precisely the regime
  where a real fee schedule would decide it.
- **Z1 and Z2 disagree, and the decomposition is what says why.** Z1 removes the
  continuation but does NOT reach criterion (a) in any index pair, and the
  failure is uniform: **S2 produces zero cells at |t| >= 3 anywhere** in all
  three, while S1 does satisfy the adjacency requirement. [PLAUSIBLE]
  estimation-noise stacking — S2 is already a deviation from a trailing
  1,950-bar fit, and normalising it again against a short early-session
  dispersion divides a noisy numerator by a noisy denominator (L-007/L-011).
  **Session-anchoring is therefore not a strict improvement**; it removes a
  documented artifact and adds a documented cost that falls on the fitted-hedge
  spec. Logged as L-018.
- **The negative control did its job.** ZF–ZN, where L-013 is absent (12.7%,
  flat profile), keeps criterion (a) under all three definitions and moves from
  10.9x to 8.7x below its round-trip cost. No signal definition closes an
  order-of-magnitude gap, and the fact that the same change does NOT flip the
  control is what makes the index flip attributable to the open window.
- **Alternatives:** (i) present the Z2 flip as a recovered edge (rejected — (b)
  is unchanged and failing, the window is spent, and D-020 pre-committed the
  ceiling); (ii) adopt Z1 as the project's signal definition on the strength of
  its cleaner event clock (rejected — it fails (a) through S2 in every index
  pair, so adopting it would be choosing a definition by its diagnostic rather
  than by its result); (iii) tune the 30-bar warm-up now that the numbers are
  visible (rejected outright — that is the specification search the method
  exists to prevent); (iv) extend to the three untested Treasury pairs
  (rejected — D-020 fixed the scope before the results, and their 7-9x cost
  gaps are untouchable by a signal change).
- **Evidence:** validation report 06; `nb06_<PAIR>_{signal_grids,event_clocks,
  scalars}.csv`; `nb06_<PAIR>_signal_definitions.png`, `nb06_event_clocks.png`;
  EXP-015 - EXP-018.
- **Expected effect:** validation report 02's mechanism sentence ("the
  dislocation continues rather than reverts") is annotated as an open-window
  effect rather than intraday pair behaviour; report 13 and D-019 carry the
  same caveat. The program conclusion is unchanged. Open thread 3 (resolution
  and venue) gains priority: a signal artifact this large at the session
  boundary is an argument for testing a different session, not a different
  threshold.
- **Review:** No further pass over this window under any signal definition.
  Confirming the Z2 sign flip requires a fresh window, venue or resolution,
  pre-registered afresh.
  *AMENDED 2026-08-04 by D-022: this clause bars further SIGNAL-DEFINITION
  passes on this window and any confirmation of the Z2 sign flip; it does not
  bar the delayed-entry mechanism probe that D-015's Review clause reserved
  before this decision existed ("the delayed-entry test is a NEW mechanism and
  gets its own pre-registration") and that this decision's own EXP-017 notes
  kept open ("Delayed entry (D-015) remains the test that would settle it").
  That probe proceeds under D-022, issues no verdict on A-006, and cannot
  advance the pair.*

## D-022 — 2026-08-04 — PRE-REGISTRATION of notebook 14: MES–M2K delayed entry and leg-level cross-correlation (the D-015 open thread)

Written before any delayed-entry code existed and before any number under it
existed. This is D-019's open thread 2 (item 3 in CONTEXT-HANDOFF §5's
renumbered list — the numbering schemes differ, and thread NAMES are used
below to avoid the collision), pre-committed by D-015 ("the delayed-entry
test is a NEW mechanism and gets its own pre-registration") and left standing
by D-021 ("Delayed entry (D-015) remains the test that would settle it",
EXP-017). The OTHER open thread — different session/resolution/venue — is
D-019's thread 3, handoff §5 item 4, and is what D-021's text calls "open
thread 3"; it is referred to here as the **session/resolution thread**.
Nothing below may be revised in response to an outcome; a revision voids the
test and forces a fresh pre-registration.

### Standing with respect to D-021's review clause, stated first

D-021's Review clause, read literally ("no further pass over this window
under any signal definition"), covers any event study on these bars — so this
decision does not proceed by reinterpreting it: D-021 now carries an inline
amendment, made together with this pre-registration, scoping the clause to
what it was written to end (the signal-definition line and any confirmation
of the Z2 sign flip) and recording the carve-out's basis — D-015's Review
clause reserved the delayed-entry probe BEFORE D-021 existed, and D-021's own
EXP-017 notes kept it open. This test is not a signal re-definition and
issues **no verdict on A-006**: the z-scores are the two already-banked
definitions (Z0 and Z2), unchanged; what varies is the ENTRY BAR of the event
study, plus one new leg-level diagnostic. It is a **mechanism-attribution
probe** of results that already exist: does the positive conditional surface
in MES–M2K reflect the laggard leg catching up (lead-lag, L-014), or
convergence that is still there to harvest after the catch-up window has
passed? The window remains spent for hypothesis testing — which is why, under
every branch below, **the pair cannot advance and the D-019 no-go cannot
change.** What this run can change is only how D-015's [PLAUSIBLE] mechanism
sentence is labelled, and whether the session/resolution thread keeps its
M2K-specific motivation.

### Why this is worth running, stated honestly

Under the open-excluded signal, M2K's best honest cell is **+6.767 bps at
t = 5.14** (S1, entry 3.0, h = 120, n = 2,061 — nb06, EXP-017), the largest
effect in the program, sitting ~2.3–3.4x above the ~2–3 bps A-007/A-008
placeholder cost band. It is the only result in seven pairs sitting a clear
multiple above that band (MYM's +2.40 and MNQ's +3.12 sit at ~1.0–1.6x, inside
a placeholder's error). Leaving its mechanism unattributed leaves the
program's conclusion resting on criterion (b) alone for the one pair where
criteria (a) and (c) pass. A confirmed lead-lag mechanism in the thinnest
micro is also a documented finding in its own right (L-014's "any future work
on a thin leg" clause becomes [ESTABLISHED] rather than [PLAUSIBLE]).

### Decision — the delayed-entry battery, fixed now

The conditional event study is re-run with the entry bar moved. Everything
about event DETECTION is byte-identical to the banked runs: signal read at
bar t (first crossing of the entry threshold by |z|), same crossing
definition, same min_events = 20, same session-clustered inference, same
seed 20260801, same anchor "unit", same 4x5 entry/horizon grid, same
own-splice data path, gate and window (2019-06-01 → 2026-04-27 request
window; observed panel 2019-06-03 → 2026-04-24, 684,300 bars, 1,780
sessions).

- **Delays, fixed now: d ∈ {1, 2, 5, 15}.** Entry at the close of bar t+d,
  exit at the close of bar t+d+k for horizon k — the holding period is
  UNCHANGED at k bars for every delay; only the start moves. P&L is the
  position's P&L with beta frozen at the SIGNAL bar (A2, unchanged):
  pnl_bps = −sign(z_t) · [(a_{t+d+k} − a_{t+d}) − β_t (b_{t+d+k} − b_{t+d})] · 1e4.
  d = 1 is the banked convention and serves as the in-run baseline.
- **Signal definitions, fixed now: Z0 and Z2 only.** Z0 =
  rolling_zscore(residual, 390); Z2 = Z0 with events whose signal bar is in
  the first 30 minutes dropped — the identical objects banked in nb02/nb06.
  Z1 is NOT run: L-018 established that session-anchoring kills S2
  (zero cells at |t| >= 3 anywhere), so a two-spec read under Z1 is
  impossible and running it would spend budget to re-learn L-018.
- **Specifications, fixed now: S1 and S2** for the delayed grids — the two
  specs the D-010 verdict rule reads. S3 is look-ahead-contaminated, never
  evidence, and is emitted only inside the reproduction grids below.
- **Matched event sets — the design choice that makes delays comparable.**
  For the delayed grids, an event enters the grid at horizon k only if bar
  t + 15 + k (the LARGEST delay plus that horizon) still lies inside the
  signal bar's session and the sample. The same event set therefore serves
  all four delays at fixed (signal, spec, entry, horizon): **n_events is
  constant across d by construction**, and a decay profile cannot be
  manufactured by late-session events entering at d = 1 and dropping out at
  d = 15 (a composition shift of up to ~14/390 ≈ 3.6% of events, not random
  in session time). Feasibility depends only on the signal bar's position in
  the session — known at signal time, no look-ahead.
- **Reproduction grids.** The UNMATCHED d = 1 grids for Z0 and Z2, specs
  S1/S2/S3, are emitted alongside — solely to prove the pipeline unchanged
  against the banked CSVs (validity gate 1). They are re-emissions of banked
  numbers, not new tests.
- **Roll treatment unchanged.** As in nb02/nb06, no roll-window exclusion is
  applied to the event study (the banked grids the reproduction gate must
  match contain roll-adjacent events). The M2K >= 1,170-bar warm-up finding
  (L-015/L-017, report 02 §12.5) remains a limitation of any FUTURE M2K
  strategy, not of this comparison: the delay contrast reads the SAME events
  at different entry bars, so roll effects are common-mode across d.

### Decision — emission in TWO backtest parts, designed now (L-019)

Auditing the banked archives for this pre-registration exposed an
operational fact that was silent until now, logged as **L-019**: all four
nb06 runs EMITTED 67–68 summary-statistic keys (S_KEYS) but the retrieved
statistics contain only 55–56 — the 12-key S_RL per-roll block is missing in
every one, and no gate needed those keys, so nothing caught it. The channel
has never returned more than 57 keys intact in this project. This battery
(~100 keys in one run) is therefore NOT designed as a single emission with a
truncation contingency; it is designed as **two backtest parts from the
start**, each inside the known-good envelope:

- The driver carries a frozen constant **PART ∈ {1, 2}** that filters ONLY
  the emission dict. **Both parts compute the ENTIRE battery identically**
  (same code, same numbers); each reports its half. There is no
  analysis-code difference between parts, and the shared diagnostics both
  parts emit (S_ALIGN, S_GATE, S_BUILD_*, S_FLAG_*, S_SPECS) must be
  IDENTICAL across parts — a fifth determinism check, enforced as validity
  gate 2b below.
- **Part 1 (~54 keys):** matched delay grids under Z0 (4 delays x 2 specs x
  4 entries = 32) + unmatched d = 1 reproduction grids under Z0 (S1/S2/S3 x
  4 = 12) + diagnostics.
- **Part 2 (~57 keys):** matched delay grids under Z2 (32) + unmatched
  d = 1 reproduction grids under Z2 (12) + the cross-correlation block
  (3 keys) + diagnostics.
- The S_RL per-roll block is NOT emitted by this driver (the audit gate
  itself still runs; S_GATE and S_FLAG_* carry its result). One EXP row
  (EXP-019) covers both parts, recording both QC run names.
- **Retry policy, fixed now:** if a part fails the emission-completeness
  gate, exactly ONE re-run of that part is permitted, changing the emission
  layer only — the analysis-code hash must be unchanged and is recorded in
  the ingest output. Values retrieved from a gate-failing part are not read
  into any report. A second failure is IMPLEMENTATION DEFECT for the run as
  a whole.

### Decision — the cross-correlation block, fixed now

Lead-lag must be visible in the LEG RETURNS if it is the mechanism; the
event study alone cannot distinguish "the effect decayed" from "the effect
was fast reversion" (a genuinely fast-reverting spread and a catching-up
laggard both decay with delay — stated here so the identification limit is
on the record before the numbers are). The discriminator is asymmetry:
catch-up is directional (MES moves first, M2K follows); symmetric spread
reversion is not.

- Within-session 1-minute log returns of each leg on the aligned panel
  (first bar of each session dropped; pairs (t−k, t) kept only inside one
  session).
- **c_ab(k) = corr(r_MES(t−k), r_M2K(t))** for k = 1..5 ("MES leads M2K"),
  **c_ba(k) = corr(r_M2K(t−k), r_MES(t))** (the mirror), the contemporaneous
  c(0), and the asymmetry **asym(k) = c_ab(k) − c_ba(k)**.
- Inference: session bootstrap — sessions resampled with replacement from
  per-session sufficient statistics, 1,000 replicates, seed 20260801,
  percentile 95% CIs on c_ab(k), c_ba(k) and asym(k), all k = 1..5 (15 CIs;
  16 point estimates including c(0)). **One session-index draw is made per
  replicate and SHARED across every statistic**, so each asym(k) replicate is
  the paired difference c_ab(k) − c_ba(k) on the same resampled sessions —
  independent draws would lose the covariance term, widen the asym CI, and
  bias X toward FALSE. (Implementation note: the per-session sufficient
  statistics for all 11 correlations stack into one array and one index
  matrix gathers them, the `_vr_session_sums` chunking pattern.)
- Prediction under lead-lag: c_ab(1) materially positive, decaying by k = 5,
  and asym(1) > 0; under symmetric reversion of the spread, no asymmetry.

### Decision — validity gates, applied BEFORE anything is read

All are pass/fail on mechanics; any failure voids the run (no verdict is
read) and the run is repeated after the defect is fixed.

1. **Reproduction gate.** The unmatched d = 1 Z0 grid must reproduce
   `nb02_MES_M2K_conditional_reversion.csv` and the unmatched d = 1 Z2 grid
   must reproduce the signal-2 rows of `nb06_MES_M2K_signal_grids.csv`,
   cell for cell at the ingest tolerance already in force (0.0005; 0.5 on
   n_events), across all three specs — 60 + 60 cells. Enforced by the ingest
   script, which writes nothing on failure (the D-020 gate-1 pattern).
2. **Matched-set gate.** For every (signal, spec, entry, horizon), n_events
   must be IDENTICAL across d ∈ {1, 2, 5, 15}, and no larger than the
   unmatched d = 1 count. This is the matched design's own audit; a mismatch
   means the feasibility mask is wrong. (min_events = 20 applies to the
   matched set, so a cell is NaN for all four delays or none.)
   **2b. Cross-part identity.** The shared diagnostics emitted by both parts
   (S_ALIGN, S_GATE, S_BUILD_*, S_FLAG_*, S_SPECS) must be identical across
   part 1 and part 2, character for character.
3. **Cross-correlation gate.** (i) c(0) > 0.5 — two US equity-index futures
   at minute resolution (large-cap MES against small-cap M2K); anything less
   is an alignment defect, not a finding — with the number of within-session
   pairs reported per lag and positive for every lag; (ii) the bootstrap
   machinery itself: exactly 1,000 replicates, and all 15 CIs finite with
   strictly positive width. **X never takes a value from degenerate
   machinery**: any failure here is IMPLEMENTATION DEFECT, never X = FALSE
   (and never X = TRUE).
4. **Emission-completeness gate.** Per part, the RETRIEVED key set must
   equal the frozen per-part manifest as a SET (not a count — a missing grid
   key offset by a stray extra key must fail), and the retrieved S_KEYS
   value must equal the manifest's size. L-019 is the reason this gate reads
   sets: the nb06 truncation passed unnoticed precisely because nothing
   compared retrieved keys against emitted keys. On failure, the retry
   policy fixed above applies (one emission-layer-only retry per part).

### Decision — the read set, frozen from the banked grids

The decay statistics are computed over the cells that were significant
BEFORE this run existed — fixed here so no cell can be selected after the
results are visible. **R = the 37 banked cells with session-clustered
t >= +3 in S1/S2** (machine-readable sources of record:
`nb02_MES_M2K_conditional_reversion.csv`, `nb06_MES_M2K_signal_grids.csv`
signal 2):

- **R_Z0 (12):** S1 — 2.0/120, 2.5/30, 2.5/60, 2.5/120, 3.0/15, 3.0/30,
  3.0/60, 3.0/120; S2 — 2.5/120, 3.0/15, 3.0/30, 3.0/120.
- **R_Z2 (25):** S1 — 1.5/60, 1.5/120, 2.0/{5,15,30,60,120},
  2.5/{5,15,30,60,120}, 3.0/{5,15,30,60,120}; S2 — 2.0/30, 2.0/60, 2.0/120,
  2.5/15, 2.5/30, 3.0/5, 3.0/15, 3.0/30.

Per cell, the decay ratio at delay d is
**ratio_d = mean_session_bps(matched, d) / mean_session_bps(matched, 1)** —
session-mean over session-mean, the A2 primary statistic in both places. A
cell enters the ratio aggregation only if its matched d = 1 value has
t_clustered >= 2 AND mean_session_bps >= +0.5 (a denominator floor; ratios
on near-zero bases are noise). Excluded cells are counted and reported. If
fewer than 12 of the 37 qualify, the matched baseline no longer represents
the banked surface and the read is **INCONCLUSIVE — MATCHING DEGENERATE**
(a documented outcome, not a licence to relax the floor).

Summary numbers, defined now: **ρ(d)** = median ratio_d over included cells
(pooled; the R_Z0 and R_Z2 subset medians are reported beside it);
**S(d)** = share of included cells with t_clustered >= 3 at delay d;
**X** = TRUE iff the c_ab(1) 95% CI lower bound > 0 AND the asym(1) 95% CI
lower bound > 0. Effect sizes in bps accompany every t-statistic wherever
any of these appear. **The subset medians are descriptive only: no branch
label, no evidence-tag change and no open-thread consequence may be derived
from any subset. The verdict and every consequence attached to it read the
pooled statistics alone.**

### Decision — verdict rule, declared now

- **LEAD-LAG CONFIRMED** iff ρ(5) <= 1/3 AND S(5) <= 0.20 AND ρ(15) <= 1/3
  AND S(15) <= 0.20 AND X. The d = 15 terms are deliberately symmetric with
  DELAY-ROBUST's ρ(15) gate: a decay that does not PERSIST to d = 15 is not
  the catch-up story, and the branch this pre-registration expects must not
  be the easiest one to reach. The decay must also be corroborated by the
  leg-level signature: decay WITHOUT X reads MIXED, because if catch-up is
  the mechanism it must be visible in the returns themselves.
- **DELAY-ROBUST** iff ρ(5) >= 2/3 AND S(5) >= 0.50 AND ρ(15) >= 1/3.
  X is reported but does not gate this branch (a lead-lag component in the
  returns can coexist with convergence that survives it).
- **MIXED / UNRESOLVED** otherwise — including probes that disagree and the
  matching-degenerate case. A partial decay landing between the branches is
  recorded as exactly that.
- **IMPLEMENTATION DEFECT** if any validity gate fails: no verdict, fix,
  re-run.

Calibration of the thresholds, stated in advance rather than fitted after:
a pure catch-up mechanism completing within ~1–4 bars (M2K's own VR(2) =
1.012 places the positive autocorrelation at the shortest lag) leaves ~0 of
the effect at d = 5 — far below the 1/3 bar; genuine AR(1)-like convergence
at the measured within-session z half-life of 37–58 bars (nb02 z_hl 58.3,
nb06 z1_hl 37.1 — [PLAUSIBLE] as a timescale proxy) retains ~0.93–0.95 at
d = 5 and ~0.77–0.85 at d = 15 — comfortably above the 2/3 and 1/3 bars.
The generous indifference zone between the branches is deliberate: it makes
LEAD-LAG CONFIRMED hard to reach by noise and DELAY-ROBUST hard to reach by
wishful reading, at the price of a wider MIXED region.

### What each outcome may and may not conclude, fixed in advance

Under EVERY branch: criterion (b) is a property of the residual that no
entry timing can touch — it failed in nb02 and is inherited unchanged — so
**MES–M2K cannot advance, nothing can reach REVERSION PRESENT, the D-015
verdict branch (AMBIGUOUS / MICROSTRUCTURE) is the ceiling, and D-019
stands.** No result of this run is quotable as an edge (A-007/A-008 remain
placeholders; the window is spent).

- **LEAD-LAG CONFIRMED:** D-015's mechanism paragraph and L-014 upgrade
  from [PLAUSIBLE] to [ESTABLISHED — this window]. A-006 for MES–M2K stays
  formally UNRESOLVED (attributing the observed surface is not proof that
  no reversion exists), but the program's last non-negative index result is
  attributed to microstructure and the index book is closed WITHOUT an
  asterisk. The session/resolution thread loses its M2K-specific motivation
  and stands on its own merits only.
- **DELAY-ROBUST:** hypothesis-generating ONLY. It buys exactly one thing:
  a concrete, sharpened target for the session/resolution thread (the same
  statistic on a fresh window, venue or resolution, pre-registered afresh,
  per its own Review clause). It does not
  reopen this window, does not soften report 13, and is not evidence of
  tradability.
- **MIXED / UNRESOLVED:** the mechanism question is recorded as unresolved
  on this window and CLOSED here — the follow-up, if any, is the
  session/resolution thread on fresh data, not another pass over these bars.

### Multiple testing, stated rather than reconstructed

The matched grids add 4 delays x 2 signals x 2 specs x 4 entries x 5
horizons = **320 cells** (of which the 80 at d = 1 are baseline
re-measurements on matched sets), plus 16 cross-correlation point estimates
carrying 15 bootstrap CIs, on top of the 900 protocol cells and 80
exploratory open-subset cells already examined (report 06 §6's running
total). That is why the verdict reads pre-registered MEDIANS over a frozen
37-cell read set and two aggregate shares — no single cell, and no cell
chosen after the fact, can decide anything.

### Prior, stated in advance

The expected outcome is LEAD-LAG CONFIRMED: M2K's own VR(2) = 1.012 with
p_lt_1 = 0.935 — above 1 where MES sits at 0.988; MNQ's 1.017 is also above
1 but declines with q where M2K's does not, which is why L-014 ties M2K, the
thinnest book in the universe, to lagged price adjustment — the base-sampling
evaporation (0.813 → 0.897 → 0.956), and the monotone-in-entry surface are
all the fingerprint L-014 describes, and the effect should be mostly gone
by d = 2 and dead by d = 5, with c_ab(1) > 0, asym(1) > 0. The honest
alternative is real: nb06's Z2 surface strengthens monotonically to
h = 120, which a 1–2-bar catch-up alone does not obviously produce, and the
measured z half-lives (37–58 bars) would, if they describe the residual,
put the outcome deep in DELAY-ROBUST territory. Either answer is a
legitimate finding; if the effect survives delay, it is recorded as
DELAY-ROBUST and nothing more is claimed for it.

- **Alternatives considered:** (i) include Z1 (rejected — L-018: S2 is dead
  under Z1, a two-spec read is impossible); (ii) unmatched event sets only
  (rejected — the composition confound above); (iii) exit fixed at t+1+k
  with entry at t+d (rejected — conflates delay with a shortened holding
  period; the question is WHEN you can enter, not how long you hold);
  (iv) a control pair (rejected — the design is within-pair, d = 1 is its
  own baseline, and building a second pair's series spends free-tier budget
  to decorate a contrast the delays already carry); (v) second/tick resolution to see the
  catch-up directly (rejected here — that is the session/resolution
  thread, a different experiment on different data, and gluing it on would
  widen this scope after the fact); (vi) tuning delays, the denominator floor, or any
  threshold after seeing results (rejected outright — that is the
  specification search the method exists to prevent).
- **Evidence to be produced:** validation report
  `reports/validation/14_delayed_entry_mes_m2k.md`; notebook 14;
  machine-readable `nb14_MES_M2K_{delay_grids,crosscorr,scalars}.csv`;
  figures `nb14_MES_M2K_delay_decay.png`, `nb14_MES_M2K_crosscorr.png`;
  EXP-019 (one row covering both parts, both QC run names); two QC backtest
  parts (driver `lean/research/qc_delayed_entry_analysis.py` uploaded as
  main.py with PART = 1 then PART = 2, `build_qc_upload.py --driver delay`);
  ingest `scripts/ingest_qc_delayed_entry.py --part {1,2}` holding the frozen
  per-part key manifests and enforcing gates 1, 2, 2b and 4, writing nothing
  on any failure (gate 3 is applied at the same stage from the retrieved
  cross-correlation keys). L-019 logged in logs/issues_and_limitations.md.
  Verdict to be logged as D-023.
- **Expected effect:** the last unattributed index result gains a
  mechanism label in one direction or the other, and the session/resolution
  thread's priority is set by evidence instead of by an open question.
- **Review:** Once a verdict is read, no re-run of any part of this
  protocol on this window (gate-triggered repairs BEFORE a verdict — the
  IMPLEMENTATION DEFECT branch and the gate-4 retry policy — are part of the
  protocol, not re-runs). If the verdict is DELAY-ROBUST, the follow-up is a
  fresh-window/venue/resolution pre-registration (the session/resolution
  thread); if LEAD-LAG CONFIRMED or MIXED, the MES–M2K thread is closed on
  this window entirely.

## D-023 — 2026-08-04 — MES–M2K survives delayed entry: DELAY-ROBUST; the surface is NOT the laggard catching up; D-019 stands

Two runs under D-022: part 1 (Z0 half) "Creative Tan Antelope", part 2
(Z2 half + cross-correlation) "Swimming Red Pigeon". EXP-019, validation
report 14. Verdict computed by `delayed_entry_summary.py` from the banked
CSVs and pinned by unit test (210 green).

- **Decision:** Read the delayed-entry test as **DELAY-ROBUST**, the branch
  D-022 fixed for ρ(5) ≥ 2/3 AND S(5) ≥ 0.50 AND ρ(15) ≥ 1/3. Observed, on
  the frozen 37-cell read set with all 37 included (zero exclusions):
  **ρ(2) = 0.932, ρ(5) = 0.849, ρ(15) = 0.536; S(5) = 0.73, S(15) = 0.59.**
  A catch-up mechanism predicts ~0 by d = 5; the observed profile is
  nowhere near that, landing close to — though uniformly below — the AR(1)
  prediction at the measured 37–58-bar half-lives (0.93–0.95 predicted at
  d = 5 vs 0.849 observed; the shortfall grows with delay, see the
  counter-note below). **No pair advances, and the D-019 no-go stands** — criterion
  (b) is inherited unchanged and failing, the window is spent, and D-022
  pre-committed this ceiling before any number existed.
- **All eight validity gates passed, read first.** Both emissions
  set-identical to their frozen manifests (54 + 57 keys — the L-019
  two-part design closed the silent-loss hole); the unmatched d = 1 grids
  reproduced the banked nb02 AND nb06 grids **60/60 cells exactly** each
  (proving the L-020 module split changed nothing); matched n_events
  constant across delays in all 80 cell families; the two parts' shared
  diagnostics character-identical (a fifth determinism demonstration of the
  D-009 constructor); cross-correlation machinery sound (c0 = 0.788, 15
  finite CIs, exactly 1,000 replicates).
- **The cross-correlation found the lead-lag — and measured it too small to
  matter.** ab_1 = corr(r_MES(t−1), r_M2K(t)) = **+0.033** [+0.021, +0.047]
  against a mirror of +0.004 [−0.010, +0.016]; asym_1 = +0.029 with CI
  excluding zero ⇒ X = TRUE. Every k = 2..5 correlation is ≈ 0. So M2K
  genuinely lags MES — by ONE bar, worth ~0.03 of correlation — and the t+1
  entry convention already excludes that bar from every banked number. Both
  probes agree: **the conditional surface is not carried by laggard
  catch-up.** X does not gate the DELAY-ROBUST branch, exactly as
  pre-registered ("a lead-lag component in the returns can coexist with
  convergence that survives it").
- **Honest counter-note, on the record:** retention sits BELOW the AR(1)
  band at EVERY delay, and the shortfall grows: 0.932 vs 0.981–0.988 at
  d = 2, 0.849 vs 0.93–0.95 at d = 5, 0.536 (Z2 subset 0.453, descriptive)
  vs 0.77–0.85 at d = 15 — the observed d ≤ 5 decay alone implies a
  ~10–17-bar half-life. The profile discriminates cleanly AGAINST catch-up
  without being a clean AR(1) fit, though it stays far above the 1/3
  LEAD-LAG ceiling. And the
  criterion-(b) base-sampling evaporation (report 02 §12.3) is now an OPEN
  PUZZLE rather than an explained artifact: the unconditional VR washes out
  at 5-minute bars while the conditional effect survives a 15-minute
  delayed entry. These measure different things (every bar vs |z| ≥ 2
  events); discriminating between the reconciling mechanisms is precisely a
  fresh-resolution/session question.
- **Consequences, exactly as D-022 fixed them:** (i) hypothesis-generating
  ONLY — the result buys a sharpened, banked target for the
  session/resolution thread (+6.68 bps decaying to +2.24 as entry slips 15
  minutes, in the thinnest micro) and nothing else; (ii) report 13 is not
  softened; (iii) nothing here is quotable as an edge (A-007/A-008
  placeholders; 1,300 cells now examined on this window); (iv) D-015's
  mechanism sentence and L-014 are amended inline — the [PLAUSIBLE]
  lead-lag attribution correctly identified a real feature of M2K that
  turns out not to explain the surface; L-014's base-sampling discipline
  for thin legs binds unchanged.
- **Alternatives:** (i) read the strong retention as evidence of a tradable
  edge (rejected — the D-022 ceiling was fixed in advance, (b) still fails,
  and costs are placeholders); (ii) read the d = 15 shortfall vs AR(1) as
  MIXED (rejected — the frozen rule reads the frozen thresholds, and the
  shortfall is recorded in the decision instead of moving the goalposts);
  (iii) run a confirming pass on this window (rejected — barred by D-022's
  Review clause).
- **Evidence:** validation report 14; `nb14_MES_M2K_{delay_grids,crosscorr,
  scalars}.csv`; `nb14_MES_M2K_delay_decay.png`, `nb14_MES_M2K_crosscorr.png`;
  EXP-019; `delayed_entry_summary.py` pins.
- **Operational facts logged:** L-019 (the summary-statistic channel
  silently dropped the 12-key S_RL block in every nb06 run; ≤ ~57 keys per
  backtest and set-equality manifests are now binding), L-020 (files/update
  rejects files > 32,000 chars → `crosscorr.py` split), and the launch
  lesson: cancelling the import-rewrite modal during the free-tier
  "Requesting Backtest" phase aborts the deployment — dismiss it only after
  "Waiting for Results" appears.
- **Review:** Per D-022: no re-run of any part of this protocol on this
  window. The follow-up is a fresh-window/venue/resolution
  pre-registration (the session/resolution thread), on Derrick's call.

## D-024 — 2026-08-04 — PRE-REGISTRATION of notebook 15: the treasury-native session (A-013), and the session-clock defect it must correct first

Written before any notebook-15 code existed and before any number under it
existed. **D-019's open thread 3** (the session/resolution thread; it is item 4 in
CONTEXT-HANDOFF §5's renumbered list — the two schemes differ and D-022 kept
them straight), promoted by D-021. Authorised by Derrick 2026-08-04.

> **REVISED 2026-08-04, after adversarial review and BEFORE any notebook-15
> code, run or number existed.** The first version was committed at `f565348`;
> this revision is the binding text and the diff is in git. What changed, and
> why — each defect was demonstrated against banked numbers, not argued:
> (1) the index-pair control **S-SHIFT(ix)** is REMOVED and replaced by a
> within-treasury displacement placebo. It stripped the 09:31–10:30 ET hour
> from MES–MYM — a superset of the window L-018 proved owns that pair's sign —
> so it would have fired CONTROL-CONFOUNDED by construction (measured on the
> banked grids: MES–MYM's largest honest effect moves **+1.410 → +2.401 =
> 1.703x** when merely the first 30 minutes of EVENTS are dropped), forcing
> Q2 to read INCONCLUSIVE regardless of the Treasury numbers. It would also
> have re-expressed D-021's Z2 sign flip on spent bars, which D-021's amended
> Review clause bars. (2) The move threshold rises **1.5x → 2.0x**: a pure
> nuisance re-specification on identical bars already moves this statistic
> **1.467x** (ZF–ZN, Z0 +0.286 → Z1 +0.195), so 1.5x sat at its noise floor,
> and the original justification (t-stats of 4.07–9.44) wrongly bounded the
> variability of a maximum over 40 cells by the t of a single cell.
> (3) The move factor is now **directionless and sign-aware** — a halving read
> as "< 1.5" i.e. IMMATERIAL, and the ratio was undefined at ≤ 0 although
> banked open subsets already produce negative largest honest effects
> (MES–MYM −0.371, MES–MNQ −0.075). (4) The argmax **relocates** between
> specifications (verified: ZF–ZN S1/z2.0/h120 → S2/z2.5/h60), so a fixed-cell
> reading is now required to agree with the free-argmax one.
> (5) Added: an IMPLEMENTATION DEFECT branch, a **(b)-ONLY** branch, per-gate
> failure consequences, D-022's retry bound, a standing section for the Review
> clauses this run touches, D-022's descriptive-only clause, and the L-018(i)
> open-window-subset obligation. (6) Corrected §7's overlap arithmetic (the
> spent window is S-USED, so the new windows share **270** bars, not 330).
> Nothing below may now be revised in response to an outcome; a revision voids
> the test and forces a fresh pre-registration.

**This is not a LEAN authorisation.** `lean/algorithm/` stays empty; the gate
still requires the exact token `PROCEED TO LEAN BUILD`, which has not been
given.

### 0. The defect this experiment inherited, stated before anything else

Pre-registration research established **L-021**: `rth_frame` filters on the
clock the DATA carries, Treasury bars are Chicago-stamped and index bars are
New-York-stamped, so **every Treasury result in this program was computed on
10:31–17:00 ET, not the 09:30–16:00 ET that D-016, reports 03/06/13 and the
handoff all state.** Four independent links, the decisive one banked
(`own_splice_acceptance_*.json`: ZN spans 08:31→16:00, M2K spans 09:31→17:00 —
each its own LEAN regular session in its own exchange timezone). Bar count
cannot detect this; any 390-minute window inside a 23h session yields 390 bars.

This changes what the experiment is. **The A-013 question cannot be asked
against a baseline that was never measured.** Notebook 15 must therefore do two
things in one pass: measure the corrected baseline, and test the
treasury-native session against it. Both are pre-registered here together so
neither can be reported selectively.

**Every window below is stated in BOTH clocks.** That convention is now binding
on all future session work.

### 0b. Standing with respect to the Review clauses this run touches

- **D-016's Review clause** ("No re-test of any Treasury pair under this
  protocol without a NEW mechanism, pre-registered afresh") is SATISFIED, not
  circumvented: the session window is a new mechanism, pre-registered here
  before any code. D-016 clause 4 reserved exactly this work in advance — "to
  be revisited in the intraday-seasonality work, not silently varied here" —
  the same structure as the D-015 reservation D-022 relied on. D-016 clause 4
  additionally carries a factual error exposed by L-021 (it asserts "RTH stays
  09:30-16:00 ET", which for Treasuries was never what ran) and receives an
  inline amendment recording that.
- **D-021's Review clause**, as amended by D-022, bars further
  signal-definition passes on this window **and any confirmation of the Z2 sign
  flip**. This run touches neither: no index pair is run at all (§4), and no
  window here removes the equity-open hour from an index pair. That constraint
  is a stated reason for the §4 scope, not an incidental outcome.
- **D-018's and D-023's Review clauses** concern their own protocols (Treasury
  verdicts under D-016; delayed entry on the MES–M2K window) and are untouched.
  **This run does NOT discharge D-023's follow-up**: MES–M2K is out of scope
  here, and its fresh-window/venue/resolution test remains open.

### 1. Why this is a genuinely different experiment — criterion (b) is LIVE

D-020 (signal definition) and D-022 (entry timing) both carried a hard ceiling
of AMBIGUOUS / MICROSTRUCTURE for one structural reason: criterion (b) — the
variance-ratio shape, the leg baselines and the base-sampling checks — is
computed on the RESIDUAL, and no z-score and no entry bar enters it.

**A session change is not like that.** It changes which bars form the panel,
hence the residual, hence the variance ratios, the leg baselines, the block
counts (`nblk = (len(seg)-1)//q`) and the bootstrap's session partition.
Verified in code: `variance_ratio` → `_vr_session_sums` → `_session_slices` →
`session_ids`, and `subsample_within_session` on the same path.

**Criterion (b) must be RECOMPUTED, not inherited. All three D-010 criteria are
live and REVERSION PRESENT is reachable in principle.** Notebook 15 is the
first experiment since notebook 03 that can move a Treasury verdict on its own
terms. That is the argument for spending the runs, and it is why the ceiling in
§7 is set on economics rather than on (b).

### 2. The windows, fixed now (Treasury pairs; Chicago-stamped data)

| tag | data stamps (CT) | true ET | bars | displacement from S-USED | role |
|---|---|---|---|---|---|
| **S-USED** | (09:30, 16:00] | 10:31–17:00 | 390 | 0 | what the banked runs did — REPRODUCTION GATE |
| **S-HALF** | (09:00, 15:30] | 10:01–16:30 | 390 | −30 min | **PLACEBO** — no economic anchor at either end |
| **S-RTH** | (08:30, 15:00] | 09:31–16:00 | 390 | −60 min | the corrected equity-RTH baseline every document claims |
| **S-SETTLE** | (08:30, 14:00] | 09:31–15:00 | 330 | — | regular open → **CME Treasury settlement** |
| **S-CASH** | (07:20, 14:00] | 08:21–15:00 | 400 | — | the true cash-open session — **CONDITIONAL ARM, §3** |

**The placebo is the control, and it replaces the index pair.** S-USED, S-HALF
and S-RTH are all 390 bars on the same pairs, differing only in how far the
window is displaced: 0, 30 and 60 minutes. S-HALF is anchored to nothing —
09:00 CT and 15:30 CT are neither an open, a close, nor a settlement. It
therefore measures how much this statistic moves *per unit of displacement
alone*. Only S-RTH's boundary is economically motivated. A cross-asset index
control was rejected for the reasons in §4.

**Boundary provenance, with its asymmetry declared:**

- The **close at 14:00 CT / 15:00 ET is PRIMARY-SOURCED and asset-class
  specific**: CME settles ZT/ZF/ZN/ZB on the VWAP of Globex trades between
  **13:59:30 and 14:00:00 CT**, and settles E-mini S&P on **14:59:30–15:00:00
  CT**. The program's 16:00 close is exactly the *equity* settlement. This is
  the economic core: each asset class's session should end at its own daily
  reference price, and the Treasury one was inherited from the wrong class.
- The **open at 07:20 CT / 08:20 ET is a CONVENTION, not a sourced boundary.**
  It is the historic CBOT floor open and this repo's own recorded figure
  (D-016 clause 4; handoff §7), restated by Derrick. It is NOT on CME's current
  specs page, and LEAN labels those bars `premarket`. Its economic motivation
  is that scheduled US macro releases land at **08:30 ET** and are the largest
  scheduled information events for the Treasury market, falling entirely
  outside any 09:30-anchored window.
- **The open may not be tuned on this window.** No alternative open will be
  tried. A descriptive per-bucket activity profile (bar counts only) is emitted
  so a FUTURE experiment can define it empirically; it is fenced by §7.

### 3. The S-CASH arm is CONDITIONAL, and the condition is fixed now

S-CASH needs bars before 08:30 CT, which the current history call does not
return: `self.history(contract, …)` delivers the LEAN **regular session only**
(Treasuries 08:31–16:00 CT, ≈450 bars/day; measured 452.3 for ZN). The bars
exist — the streamed inventory path sees **1,107–1,403 bars/day** across the
eight instruments — but the history call does not return them. Obtaining them
means passing `extended_market_hours=True`, and that is **not a free change**:
`build_continuous` measures each splice factor over `factor_window_bars=390` of
overlap, so on a denser series 390 bars covers ~0.28–0.35 of a day (density
varies by symbol) instead of 0.867,
producing different factors, a different constructed series, and a broken
comparison to every banked result.

**The design that preserves D-009, fixed now:** fetch extended hours, but
measure the splice factors and run `splice_audit` on the **regular-session
subset** of that fetch — the identical bar set the banked runs used — then
apply those factors to the full extended series. The construction is unchanged
by definition; only the sampling of the adjusted series is denser.

**Gate S-CASH-ENABLE (pass/fail on mechanics, before any S-CASH grid is
read):** the splice factor table and the acceptance-gate outputs (`S_GATE`,
`S_BUILD_*`, `S_FLAG_*`) computed on the regular-session subset of the extended
fetch must reproduce the banked Treasury values **character for character**. On
failure: **the S-CASH arm is VOID.** The ingest drops every S-CASH key and
writes nothing for that arm; no S-CASH number is read, quoted, plotted or
alluded to in report 15, D-025 or any figure. Exactly ONE mechanics-only retry
is permitted, with the analysis-code hash recorded and unchanged; a second
failure ends the arm. The other four windows stand on their own and the true
cash-open session is deferred to its own pre-registration. Declared now so a
failed S-CASH arm cannot become a reason to relax the D-009 construction.

### 4. Pairs, and the order they run in

**All four Treasury pairs and nothing else**, registered together and in a fixed
order so the protocol cannot be adjusted between them (D-016 precedent,
liquidity-first): **ZF–ZN → ZT–ZF → ZN–ZB → ZT–ZN**.

**No index pair is run, and the reason is evidential rather than budgetary.**
An index window control would have to remove or add the 09:31–10:30 ET hour,
and L-018 established that the equity-open window can own an index pair's
pooled sign. Measured on the banked grids, dropping merely the first 30 minutes
of EVENTS moves MES–MYM's largest honest effect from +1.410 to +2.401
(**1.703x**) — so such a control would trip any confounding threshold by
construction, telling us nothing about Treasuries, and it would re-express
D-021's Z2 sign flip on spent bars, which D-021's amended Review clause bars.
The within-Treasury displacement placebo (S-HALF) is the sound control instead:
same pairs, same microstructure, same bar count, no known special structure at
its boundaries.

For the record, so no later reader mistakes the scope for a verdict: of the
three index pairs, MES–MYM and MES–MNQ are FALSIFIED (D-011, D-013) while
**MES–M2K is NOT — it is UNRESOLVED / AMBIGUOUS-MICROSTRUCTURE (D-015,
reaffirmed by D-023) with a POSITIVE grid whose largest honest effect is
+6.305 bps at t = 5.31.** It is excluded here because this run is a Treasury
session test, not because its question is settled, and per §0b this run does
not discharge D-023's follow-up. Scope is fixed now so it cannot widen after
the results.

### 5. Validity gates, applied BEFORE any grid is read

Failure consequences are stated per gate. Any gate whose consequence is "voids
the run" produces **no verdict at all** — the survivors of a partial failure may
not be reported as a protocol result.

1. **TIMEZONE-WITNESS gate.** Each leg emits the observed min/max time-of-day
   and median bars per calendar day of the constructed series *before* any
   session filter. Treasury legs must read 08:31/16:00 at ≈450 bars/day — the
   L-021 signature. **Bar count may never be used as a timezone witness.**
   Failure **voids the run**.
2. **Reproduction gate.** The S-USED grid AND its variance-ratio blocks must
   reproduce banked `nb02_<PAIR>_conditional_reversion.csv` and
   `nb02_<PAIR>_variance_ratio.csv` cell for cell **at the ingest tolerance
   already in force (0.0005; 0.5 on `n_events`)**, for all four pairs. Failure
   **voids the affected pair entirely**, and that pair is reported as
   IMPLEMENTATION DEFECT rather than dropped silently.
3. **Build-determinism gate.** `build_continuous` and `splice_audit` run on the
   unfiltered series and are session-agnostic (verified: no `session_ids`, no
   `rth_frame`, no time-of-day arithmetic in `roll_adjustment.py`). `S_GATE` /
   `S_BUILD_*` / `S_FLAG_*` must reproduce the banked Treasury values exactly —
   a **6th determinism demonstration** of D-009. Failure **voids the run**.
4. **Session-geometry gate.** Median bars/session must be exactly 390
   (S-USED, S-HALF, S-RTH) and 330 (S-SETTLE) — these windows lie wholly
   inside the dense regular session. No session may span a calendar date, and
   the splice timestamp must fall inside every window (verified in advance:
   10:30 CT is inside all five, and no window excludes it on the half-open left
   boundary). Failure **voids the affected window**.
   **S-CASH is gated differently, because its sparsity is itself evidence.**
   Outside the regular session `fill_forward=False` leaves minutes genuinely
   unpopulated — measured on the banked inventory, ZT fills only **70.7%** of
   available extended-hours minutes (ZB 84.4%, ZF 87.9%, ZN 93.1%) — so 400 is
   an upper bound, not an expectation, and a hard 400-bar requirement would
   fail on liquidity rather than on mechanics. S-CASH therefore requires only
   that the observed min/max time-of-day fall inside its bounds; the per-leg
   fill density of the 07:21–08:30 CT block is emitted and **reported as a
   finding**. If either leg fills below **80%** of that block, the pair's
   S-CASH arm reads **INCONCLUSIVE-COVERAGE** — which is a substantive answer
   to A-013 in its own right (a pre-open that does not print cannot be traded),
   not a defect to be worked around.
   **Additionally a minimum-blocks witness**: the median non-overlapping VR
   blocks per session at q = 120 is emitted per window, so a degenerate
   variance-ratio tail cannot be mistaken for criterion (b) moving.
5. **Emission-completeness gate (L-019).** Retrieved key SET == the frozen
   per-part manifest and `S_KEYS` == its size. The battery ships in parts of
   ≤ 57 keys with the manifests frozen in the ingest script before the first
   run; the banked Treasury runs already sat at 55–57 keys. The `S_RL` block is
   not emitted (D-022 precedent). Shared diagnostics must be character-identical
   across parts. **Retry policy, imported from D-022:** exactly ONE re-run of a
   failing part is permitted, changing the emission layer only, with the
   analysis-code hash recorded and unchanged; values retrieved from a
   gate-failing part are not read into any report; a second failure is
   IMPLEMENTATION DEFECT. **At most three gate-triggered repairs total across
   the whole run**, each logged with its cause before the next is attempted.

### 6. Verdict rule, declared now

Per pair and per window the full D-010 rule is applied unchanged — (a) positive
with session-clustered |t| ≥ 3 at ≥ 2 adjacent horizons in S1 AND S2;
(b) variance-ratio curve still declining past q = 30, materially below BOTH
legs' own curves, AND surviving coarser base sampling, **recomputed on that
window's residual**; (c) the effect strengthens with entry threshold — with
effect sizes in bps beside every t-statistic, plus the D-017/D-018 economic
materiality clause against the tick-derived round-trip cost.

**Branch set, extended.** D-010's branches are not exhaustive for a run that can
move (b), so one is added now: **(b)-ONLY** — the residual carries the reversion
signature but no conditional surface reaches (a). It does NOT advance the pair
and does NOT reopen D-019; it is a fresh-data hypothesis requiring its own
pre-registration on unspent bars. **IMPLEMENTATION DEFECT** is also a branch:
any gate failure per §5, no verdict read, defect fixed, re-run.

**The move statistic, fully specified.** The comparison quantity is the
**largest honest effect**: the free signed argmax of `mean_session_bps` over
S1 and S2 anywhere in the pair's 4×5 grid, no significance filter — the
definition already implemented and unit-pinned in `program_summary.py`, reused
unchanged, per pair. Because that argmax is free it can RELOCATE between
windows (verified on banked grids: ZF–ZN's moves from S1/z2.0/h120 under Z0 to
S2/z2.5/h60 under Z1), so:

- **move factor** = `max(e_new/e_ref, e_ref/e_new)` — directionless, so a
  halving counts exactly as much as a doubling;
- if **either** window's largest honest effect is **≤ 0** the ratio is not
  computed, and a **sign change is automatically a MOVE**;
- both the **free-argmax** ratio and the ratio at **S-USED's argmax cell held
  fixed** are reported, together with the argmax coordinates per window. A
  MATERIAL reading requires the two to AGREE; if they disagree the result is
  recorded as **MOVE-IS-RELOCATION** and reads INCONCLUSIVE for that pair.

Two questions, both answered from the same run, with separate branch names so
neither can borrow the other's consequences:

- **Q1 — did the L-021 defect matter?** Compare **S-RTH vs S-USED** (both 390
  bars, so the score means the same thing in both — this comparison is clean).
  Branches: **L-021 IMMATERIAL** iff every pair's verdict branch is identical
  and every pair's move factor < 2.0; **L-021 MATERIAL** otherwise.
- **Q2 — A-013 proper.** Compare **S-SETTLE (and S-CASH if enabled) vs S-RTH**.
  Branches: **A-013 IMMATERIAL** iff every pair's verdict branch is identical
  and every pair's move factor < 2.0; **A-013 MATERIAL** otherwise;
  **A-013 MATERIAL AND FAVOURABLE** — the only branch that could revive a pair
  — requires a branch reaching **REVERSION PRESENT** *and* the effect clearing
  that pair's round-trip cost. Prior: implausible at a 7–11x gap.
- **DISPLACEMENT-CONFOUNDED** iff the S-HALF move factor is **≥** the S-RTH
  move factor for the same pair — a smaller, economically meaningless
  displacement moving the statistic at least as much as the larger anchored
  one. Q1 then reads INCONCLUSIVE for that pair. The S-HALF/S-RTH move ratio is
  reported for every pair whether or not the branch fires.
- **Combined reading, fixed now:** D-025's headline reads **Q2**, with Q1
  reported beside it and never merged into it. All four combinations are
  legal and are reported as the pair (Q1, Q2); in particular "L-021 MATERIAL,
  A-013 IMMATERIAL" means the mislabelled hour moved the numbers while the
  treasury-native session did not, and that reading may not be restated as
  "the session mattered".

**Why 2.0x, justified before the fact and calibrated on banked numbers.** A
pure nuisance re-specification on identical bars already moves this statistic
**1.467x** (ZF–ZN largest honest effect: Z0 +0.286 → Z1 +0.195) and **1.248x**
(Z0 → Z2), with the argmax relocating in the process; and within a single
banked Treasury grid the honest cells span 8.4–12.3x, so 9–12 of 40 cells sit
within 1.5x of the maximum. A 1.5x threshold is therefore inside this
statistic's own specification noise. 2.0x clears the largest measured nuisance
movement with margin while remaining far below the ~10x that would matter
economically. Qualitative shifts are caught regardless by the
verdict-branch-change criterion, which does not depend on the threshold at all.

### 7. What no outcome may conclude

- **Costs do not move with the session.** The round trip is tick-derived from
  VERIFIED specs (A-003) — ZF–ZN 3.10, ZT–ZF **1.41**, ZN–ZB 5.85, ZT–ZN 1.50 bps,
  spread-only, commission (A-007) excluded as an unverified placeholder. The
  banked effects are 0.166–0.664 bps. **ECONOMICALLY IMMATERIAL is expected to
  stand under every branch**; no session change is a plausible 10x mechanism.
  Report 06 already showed the best available signal change moved ZF–ZN only
  from 10.9x to 8.7x below cost.
- **The cost bar is HIGHER, not lower, in the pre-open.** A-008 assumes a
  1-tick top-of-book spread and `cost_assumptions.yaml` scopes that explicitly
  to "liquid RTH". No overnight or pre-open spread assumption exists in the
  repo, and this run **cannot measure one** — trade bars, no quotes. Any
  S-CASH effect must clear an unmeasured, probably worse bar. That is the
  quote-data thread, not this one.
- **Freshness, corrected.** The spent window is S-USED (10:31–17:00 ET). Each
  new window shares **270 bars** with it. S-RTH and S-SETTLE each add **60**
  never-examined bars (09:31–10:30 ET); S-CASH adds **130** (08:21–10:30 ET).
  A result on any of them is therefore **not independent confirmation**, and
  the shared 60-bar block is precisely the equity-open hour L-018 showed can
  own a grid's pooled sign.
- **Q2 does not hold the signal fully constant, and its MATERIAL reading is
  attributable accordingly.** Z0 `rolling_zscore(residual, 390)` is held fixed
  in bars, but 390 bars is exactly one session under S-USED/S-HALF/S-RTH,
  **1.18 sessions under S-SETTLE (330)** and 0.975 under S-CASH (400). Q1 is
  clean; a Q2 MATERIAL reading is attributable to "the window OR its
  interaction with the fixed 390-bar score", never to session structure alone.
- **Descriptive outputs are descriptive only.** The activity profile, the
  pre-open subset, the L-018(i) open-window subset and any per-bucket or
  per-subset statistic carry **no branch label, no evidence-tag change and no
  open-thread consequence**. In particular an activity peak near 07:20 CT may
  NOT promote the 08:20 open from a convention to a sourced boundary. The
  verdict and every consequence attached to it read the pooled, per-pair
  statistics alone.
- **L-018 clause (i) is discharged explicitly**: because every window here uses
  the overnight-spanning Z0 score, each window additionally emits its
  open-window event subset, labelled EXPLORATORY, reported separately, and
  fenced by the clause above.
- **A-013 is answered for TREASURIES, at MINUTE resolution, on TRADE bars, over
  this date range only.** Quote data and second/tick resolution remain separate
  experiments with their own pre-registrations.
- **No pair advances to a LEAN build under any outcome, and the D-019 no-go is
  not reopened by any outcome of this run** — including a criterion-(b) pass, a
  (b)-ONLY branch, or a REVERSION PRESENT branch. Reopening D-019 requires a
  result clearing the pair's round-trip cost on unspent data, pre-registered
  afresh.

### 8. Prior, stated in advance and falsifiable

On **Q1** I expect L-021 MATERIAL in the statistical sense and benign in the
economic one: a window shifted an hour later, ending two hours past settlement
rather than at it, should move effect sizes noticeably while leaving every cost
ratio in the same order of magnitude.

On the **placebo** I expect S-HALF to move each pair LESS than S-RTH does — a
30-minute unanchored displacement should not move the statistic as much as a
60-minute anchored one. If it moves as much or more, the statistic is simply
window-sensitive and Q1 reads INCONCLUSIVE; given the measured 1.467x nuisance
movement, that outcome is a live possibility rather than a formality.

On **Q2** the directional prediction comes from **L-018**. Scheduled
information releases should behave the way the equity open did — a level change
that PERSISTS, i.e. CONTINUATION, not reversion. L-018 found exactly that at
the equity open across four pairs including the ZF–ZN Treasury control, whose
open-only subset is negative in **18 of 20 cells** (3 at |t| ≥ 3; the headline
cell is −0.146 bps at t = −3.87) where every other row of that pair's grid is
positive. So I
predict the S-CASH pre-open subset shows CONTINUATION, and that adding those
bars moves S-CASH's grid *toward* continuation relative to S-SETTLE. If instead
it reverts, L-018's generalisation is wrong and that is the more interesting
result.

Most likely overall: L-021 MATERIAL, A-013 IMMATERIAL, all four Treasury
verdicts unchanged in branch, immateriality untouched, the no-go standing, and
the program's Treasury session label corrected. There is a real chance
criterion (b) moves, and that is the genuinely new thing this run can produce.

- **Alternatives considered:** (i) re-run notebook 03 on the corrected window
  only (rejected — answers Q1 while leaving A-013, the actual open thread,
  untested, for the same runs); (ii) test only S-CASH against the banked
  numbers (rejected — compares two windows differing in BOTH endpoints against
  a mislabelled baseline, so no change could be attributed); (iii) use an index
  pair as the control (rejected on evidence — see §4: it fires by construction
  and collides with D-021's Review clause); (iv) drop the placebo entirely
  (rejected — without it a Treasury movement cannot be distinguished from
  ordinary window sensitivity, which is measurably ~1.47x for a mere
  re-specification); (v) run all seven pairs (rejected — scope fixed in §4
  before results); (vi) introduce session-anchored z-scores here (rejected —
  L-018 showed session-anchoring is not a strict improvement and it would
  confound the session change with a signal change); (vii) tune the 08:20 open,
  the 2.0x threshold, the placebo boundaries or any window after seeing results
  (rejected outright — the specification search this method exists to prevent).
- **Evidence to be produced:** validation report
  `reports/validation/15_session_window_treasuries.md`; notebook 15;
  `nb15_<PAIR>_{window_grids,variance_ratios,scalars}.csv`; figures
  `nb15_effect_by_window.png`, `nb15_activity_profile.png`; EXP-020 – EXP-023
  (four pairs); driver `lean/research/qc_session_window_analysis.py`; a new
  module `src/spread_research/session_window_report.py` (L-020: `intraday_reversion.py` has 2,539 chars of headroom and
  `pair_minute_report.py` 2,668 against QC's 32,000-char `files/update` cap,
  so the battery cannot live in either); ingest `scripts/ingest_qc_session_window.py` with frozen per-part
  manifests. Verdict to be logged as **D-025**.
- **Expected effect:** A-013 answered for Treasuries at minute resolution, the
  L-021 session label corrected across the corpus, and the session/resolution
  thread either closed or narrowed to quote data and finer resolution.
- **Review:** Once a verdict is read, no re-run of any part of this protocol on
  this window. Gate-triggered repairs BEFORE a verdict are part of the protocol
  and are bounded by §5 (at most three, each logged with cause). If S-CASH is
  voided by its enabling gate, the true cash-open session returns as its own
  pre-registration with a re-validated D-009 construction — not as an amendment
  to this one.

## D-025 — 2026-08-04 — A-013 IMMATERIAL and L-021 IMMATERIAL: the treasury-native session does not change any verdict

Twelve runs under D-024 (4 pairs x 3 parts), EXP-020 – EXP-023, validation
report 15. Every branch below is the one D-024 fixed in advance; nothing was
chosen after the numbers existed.

- **Decision:** **Q2 reads A-013 IMMATERIAL** and **Q1 reads L-021
  IMMATERIAL**. No pair's verdict branch changes on any window, no move factor
  reaches the pre-registered 2.0x bar, and criterion (b) fails identically on
  all 16 pair-window combinations. **No pair advances; the D-019 no-go stands.**
- **All 60 validity gates passed**, and three of them are load-bearing:
  (i) the S-USED grid reproduced the banked notebook-03 grid **60/60 cells** and
  its variance ratios **48/48 cells** in all four pairs, so the session
  parameterisation disturbed nothing; (ii) `S_GATE`/`S_BUILD_*`/`S_HOLIDAYS`
  reproduced the banked values exactly — a **6th determinism demonstration** of
  the D-009 constructor, with ZT230831 and both ZB flags reproducing their
  `sr`/`gap`/`ratio`/`sign_mismatch` verdicts; (iii) **S-CASH-ENABLE passed in
  all four pairs with the factor table identical character-for-character** under
  the extended-hours fetch, so the two-fetch design preserved D-009 exactly as
  D-024 §3 required.
- **L-021 confirmed live, then measured and found harmless.** The timezone
  witness reported `08:31-16:00` at ~450 bars/day on every regular-fetch leg —
  Chicago stamps — against `00:00-23:59` at ~1,378 bars/day on the extended
  fetch. So the four Treasury pairs really were analysed on 10:31–17:00 ET. The
  corrected window (S-RTH) moves the largest honest effect by only 1.01–1.26x
  and changes no branch. **The label was wrong; the conclusions were not.**
- **The one criterion that could have moved did not, and this is the result.**
  Unlike D-020 and D-022 — both structurally incapable of touching criterion
  (b) — a session change alters the residual itself, so (b) was live for the
  first time since notebook 03. It fails everywhere: the base-sampling walk
  still evaporates to **0.82–0.93 at 15-minute bars** (from 0.13–0.34 at
  1-minute), and the tail ratio VR(120)/VR(30) sits at **0.78–1.00**, a floor
  rather than reversion's decay. That is L-016's tick-quantisation signature,
  untouched by any window.
- **The treasury-native session helps, consistently, and not nearly enough.**
  Every treasury-native window improves the cost ratio in every pair, and the
  cash-open session is the best window in three of four: ZN–ZB 8.81x → **5.61x**,
  ZT–ZN 9.06x → **5.57x**, ZT–ZF 7.00x → 5.44x, ZF–ZN 10.85x → 8.08x. The
  direction is exactly what the settlement argument predicted. But the largest
  single move is **1.43x against a 2.0x bar**, and the best cost ratio in the
  whole experiment is still **5.6x below the round trip**. Calling this
  IMMATERIAL rather than promising is what fixing 2.0x in advance was for: a
  pure signal re-specification on identical bars already moves this statistic
  1.467x, so 1.2–1.4x is inside the statistic's own specification noise.
- **The falsifiable prior FAILED, which D-024 said would be the more
  interesting outcome.** D-024 predicted, from L-018, that the treasury
  pre-open (containing the 08:30 ET macro releases) would show CONTINUATION.
  It does not: across all four pairs the S-CASH open subset holds **zero**
  significant negative cells. L-018's continuation still appears where it was
  found — ZF–ZN's S-USED open subset, negative in 18/20 cells, reproducing the
  banked cell at **t = −3.87 exactly**. Logged as **L-023**: [PLAUSIBLE]
  L-018 is an equity-session-open (liquidity-discontinuity) effect, not a
  general information-release effect. Not tested here, not claimed.

  > **AMENDED 2026-08-05 (L-024) — the equity-open attribution is WITHDRAWN;
  > the failed prior is NOT.** The prior failed exactly as recorded (zero
  > significant negative cells in any S-CASH open subset) and that half stands.
  > But the corroborating clause is wrong: under L-021, S-USED is (09:30,
  > 16:00] **CT**, so its open subset is **10:31–11:00 ET, an hour after the
  > equity open**. The subset that IS the equity open is **S-RTH**
  > (09:31–10:00 ET), which this run measured and this paragraph did not use —
  > and on ZF–ZN it disagrees in sign at comparable power: **7/20 negative,
  > mean t +0.58** against S-USED's 18/20 and mean t −1.76. So ZF–ZN does not
  > corroborate an equity-open mechanism; its continuation is specific to the
  > 10:31–11:00 ET block. **No verdict in this decision moves** — D-024 §7
  > fenced these subsets as descriptive and neither Q1 nor Q2 depends on them.
  > See L-024 and report 15 §7 as amended.
- **One procedural artifact, reported as the rule dictates.** ZT–ZF trips
  DISPLACEMENT-CONFOUNDED because its placebo move (1.015x) marginally exceeds
  its S-RTH move (1.010x). Both are ~1% — nothing moved — and the frozen rule
  compares them without requiring either to be material. Logged as **L-022**;
  it is an artifact of the placebo rule's degenerate case and is evidence of
  nothing. The remaining three pairs read L-021 IMMATERIAL cleanly.
- **Alternatives:** (i) read the consistent sub-threshold improvement as
  support for the treasury-native session (rejected — 2.0x was fixed in advance
  precisely so a 1.2–1.4x movement could not be promoted after the fact, and
  the banked nuisance movement is 1.467x); (ii) relax the move bar now that the
  direction is known (rejected outright — the specification search the method
  exists to prevent); (iii) treat ZT–ZF's DISPLACEMENT-CONFOUNDED as a real
  finding (rejected — both inputs are ~1.01; it is reported and fenced);
  (iv) read the S-CASH open subsets as evidence about the release window
  (rejected — D-024 §7 fences them as descriptive only).
- **Evidence:** validation report 15; `nb15_<PAIR>_{window_grids,
  variance_ratios,open_subsets,scalars}.csv` and `nb15_<PAIR>_p{1,2,3}.json`
  for four pairs; `qc_extended_fetch_smoke.json`; EXP-020 – EXP-023; verdict
  arithmetic in `src/spread_research/session_window_summary.py`, pinned by
  `tests/unit/test_session_window_summary.py` (247 tests green).
- **Expected effect:** A-013 moves from UNVERIFIED to ANSWERED for Treasuries
  at minute resolution on trade bars over this window; L-021's session label is
  corrected across the corpus and its impact recorded as immaterial; the
  session half of the session/resolution thread CLOSES. What remains open in
  that thread is **quote data** — now the binding uncertainty, because the
  pre-open cost bar is unmeasured and A-008's 1-tick assumption is scoped in
  config to "liquid RTH" — and **second/tick resolution**.
- **Review:** No re-run of any part of this protocol on this window. The
  treasury-native session question is settled at minute resolution on trade
  bars; revisiting it requires quote data or finer resolution, pre-registered
  afresh.
