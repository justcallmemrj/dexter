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
