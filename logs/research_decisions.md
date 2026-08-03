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
