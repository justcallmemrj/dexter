# Known Issues and Limitations

## Open

- **L-001 (partial blocker — downgraded 2026-08-01):** Originally: no futures market
  data reachable from the research container at any resolution. After migration to
  the local Windows machine (report 00, Addendum A): yfinance daily data for all
  probed instruments works, so **daily-resolution screening is unblocked**;
  minute-resolution research history (the project's primary resolution) remains
  unavailable locally. **Remaining resolution path:** run notebooks inside
  QuantConnect Research (browser-driven workflow available on this machine), or a
  licensed data drop into `data/raw/`.
- **L-003:** Commission and spread assumptions are placeholders (A-007, A-008).
- **L-004:** Minute-bar execution simulation cannot model queue position, intrabar
  adverse selection, or partial fills. Mitigated (not solved) by the 'stressed'
  cost acceptance rule; second/tick-level evaluation is a later phase.
- **L-005:** Micro contracts launched 2019-05-06 → at most ~7 years of history, all
  within one broad monetary era plus COVID. Regime coverage is structurally thin;
  parent E-mini proxy studies (clearly labeled) partially mitigate for the
  relationship analysis but never for execution realism.
- **L-006:** Treasury futures are delivery-settled with CTD dynamics; price-based
  hedge ratios only approximate DV01 neutrality (A-012).
- **L-007 (research caution, found during framework testing):** hedge-ratio
  estimation error contaminates the constructed residual with a slow random-walk
  component of magnitude ≈ (beta_hat − beta) × price_level, inflating measured
  half-life; the contamination ratio is INDEPENDENT of the residual's own
  volatility (it is price_level / (σ_x,window · √n_eff), with n_eff shrunk by
  residual autocorrelation). Demonstrated on synthetic data in
  `tests/unit/test_stationarity_mean_reversion.py::test_residual_pipeline_end_to_end`.
  Consequence: notebooks 04/05 must quantify this on real data — half-life
  estimates from noisy hedges are biased UP, and pair viability must be judged
  net of it.

- **L-009 (platform quirk, must-respect):** In QC, MYM minute data exists only
  under `Market.CBOT` (`Market.CME` serves nothing), is complete from the
  2019-05-06 launch, **but a continuous-contract subscription starting before
  the launch date never initializes (zero bars for the whole run)** — the
  other micros tolerate pre-launch starts. All QC runs touching MYM must start
  2019-05-06 or later; the research window (2019-06-01) satisfies this.
  Evidence: validation report 00-QC §Findings-6 + qc_data_inventory.json
  diagnostics.
- **L-010 (data defect, mitigated by D-009):** QC continuous-futures adjusted
  series contain BAD ADJUSTMENT FACTORS at 40 of 220 rolls in the research
  window (M2K 19, MYM 14, MNQ 4, MES 3; treasuries clean) — the refetched
  (QuantBook/notebook) series jump by the full calendar gap (0.13-1.08%) at
  those splices. Additionally 24 splices leak in the STREAMED backtest feed
  only, and streamed/refetched paths disagree in both directions — any future
  streaming/live use requires its own splice audit. Dated list:
  reports/machine_readable/qc_roll_audit.csv (final == data_side_leak).
  Evidence: validation report 01. Free-tier operational caps discovered en
  route: logs 10KB/backtest AND 10KB/day; custom chart series unreliable
  above ~10/run (summary statistics reliable).
- **L-008:** yfinance preview series contain at least one suspected provider
  artifact: ZB 2015-03-23 daily log-return +0.099 (~10% one-day move in the
  30-year future that did not occur — bad print or roll splice). Flagged by the
  validation battery, retained-never-filled, documented in
  `reports/preview/daily_pair_screen.md` §2. Reinforces A-015: preview tier is
  screening-only and its data is never execution-grade.

- **L-011:** A fitted hedge ratio must be paired with its regression
  INTERCEPT. Computing `log(P_a) - beta_t * log(P_b)` with a rolling OLS beta
  but no intercept scales every beta wobble by the log price LEVEL — MYM near
  38,000 has log(x) ~ 10.5, so a beta moving 0.001 between refits injects
  ~10 bps of residual movement, larger than the intraday effect under study.
  Caught on synthetic data during the notebook-02 dry run, where the
  no-intercept spec produced -1,689 bps "reversion" that vanished (to +1.7 bps,
  matching the estimation-free spec) once the intercept was restored. Fix:
  `pair_minute_report.rolling_ols_residual` measures the deviation from the
  full trailing fitted line; a regression test asserts the no-intercept form
  stays >20x noisier. `pair_builder.build_residual` keeps the no-intercept form
  ON PURPOSE — it is correct for hedge ratios that are NOT fitted (notional,
  DV01). **Notebook 04 must route every FITTED beta through the
  intercept-aware path**, or its half-life and residual comparisons will be
  measuring hedge noise (this is L-007 with a concrete mechanism).

## Closed

- **L-002 (closed 2026-08-01):** Contract specifications were verified only
  against secondary sources. Resolved: all 8 instruments primary-source
  verified live on cmegroup.com (browser session; A-003 → VERIFIED). New
  details captured in config: calendar-spread ticks, listing counts (MYM 4
  quarters vs 5 for other micros; treasuries 3), exact termination times
  (index micros 9:30 a.m. ET 3rd Friday; ZT/ZF 12:01 p.m. CT last business
  day; ZN/ZB 12:01 p.m. CT 7 business days prior to last business day).
