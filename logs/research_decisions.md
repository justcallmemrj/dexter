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
