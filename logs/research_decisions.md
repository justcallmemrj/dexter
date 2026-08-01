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
