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
