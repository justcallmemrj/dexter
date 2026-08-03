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
  **~105 bps** of residual movement, orders of magnitude larger than the
  intraday effect under study. (Corrected 2026-08-02: this entry originally
  said ~10 bps, understating it 10x — 0.001 x 10.545 = 0.0105 log units = 105
  bps. The conclusion and the empirical -1,689 bps observation are unchanged.)
  The same arithmetic applies to Treasuries at a smaller log level:
  log(110) = 4.7, so 0.001 of beta drift is ~5 bps there.
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

- **L-012:** MYM 2019-12-12 (MYMZ19->MYMH20 splice) shows an 8.15 bp boundary
  return against a 1.08 bp calendar gap and an unusually quiet 0.358 bp local
  MAD. Adjudicated NOT a splice artifact by a bound — a wrong factor can inject
  at most the gap, and the move is 7.5x larger (D-010 amendment A1). But a
  single bad print in one contract's close at the boundary minute would look
  identical, and this was not independently confirmed against a second data
  source. MES moved only +2.3 bp at the same timestamp, so it was not an
  index-wide move. One minute of ~1.36M, at a roll boundary the adopted
  exclusion window keeps positions out of; revisit if a second symbol shows the
  same signature at the same timestamp.
- **L-013:** Under the current config (`zscore_lookback_bars: 390`, one RTH day)
  the z-score window reaches back across the overnight break, so the first bars
  of a session are scored against the previous session's mean. Consequence
  measured in validation report 02 §6.4: **24.3% of |z| >= 2 crossings occur in
  the first 30 minutes and ~37% in the first hour**, decaying to ~3% per 30-min
  bucket by the afternoon. A large minority of "intraday dislocations" under
  this configuration are overnight repricings. Notebook 06 must either
  session-anchor the z-score (reset at the open), add a warm-up after the open,
  or explicitly test the open-gap subset as its own hypothesis. Does not affect
  the report-02 verdict, which is negative with or without those events.

- **L-014:** M2K shows **lagged price adjustment**, not bid-ask bounce: its own
  variance ratio at q=2 is 1.012 with bootstrap p_lt_1 = 0.935, i.e. ABOVE 1
  (positive autocorrelation), where MES sits at 0.988 and MNQ at 1.017-with-a
  -declining-curve. Consequence (validation report 02 section 12): any spread
  against M2K mechanically "reverts" as the lagging leg catches up, producing a
  monotone, cost-clearing, statistically strong surface that is NOT a pair
  relationship and that vanishes once bars are coarse enough to contain the
  catch-up. This is the reason MES–M2K returned AMBIGUOUS rather than positive.
  **Any future work on a thin leg (M2K, and by extension any low-volume
  contract) must run the base-sampling check before believing a reversion
  result.** Unresolved test: delayed entry (t+2/t+5/t+15) — pre-register
  separately.
- **L-015:** The adopted 780-bar post-roll warm-up (report 02 section 6.3) is
  calibrated on MES–MYM and confirmed on MES–MNQ, but is **insufficient for
  M2K**, whose residual dispersion is still 1.58x baseline in the THIRD RTH day
  after the splice (1.93x first day, 1.66x second) where the other two pairs
  had returned to ~1.1x. M2K work needs >= 1,170 bars and a re-measurement.
  Roll-window parameters are pair-specific, not universal.

- **L-016:** Treasury futures are quoted in ticks that are COARSE relative to
  their minute-level volatility (1 tick = 0.38 bps of notional for ZT, 0.72 ZF,
  1.42 ZN, 2.72 ZB). Two consequences, both established in validation report 03:
  (i) a hedged Treasury residual at 1-minute sampling is dominated by tick
  quantisation, producing variance ratios of 0.13-0.32 that look like violent
  mean reversion and evaporate toward 1.0 at 15-minute sampling in all four
  pairs; (ii) the same coarseness makes round-trip costs large in bps (1.4-5.9
  bps per pair), which is why effects with t up to 9.4 are still 7-11x too
  small to trade. **Any future minute-resolution work on Treasury futures must
  run the base-sampling check before interpreting a low variance ratio**, and
  must quote effect sizes against tick-derived costs rather than against zero.
- **L-017:** Roll-window behaviour is ASSET-CLASS specific, not universal.
  Index micros show 1.6-2.6x baseline residual dispersion around the D-009
  splice (M2K still elevated in the third RTH day, L-015); all four Treasury
  pairs show 0.89-1.03x, i.e. no elevation at all, because month-end rolls sit
  far from expiry with continuous liquidity. The 780-bar post-roll warm-up
  adopted in report 02 section 6.3 applies to the index pairs and must NOT be
  assumed for Treasuries or for any new asset class without re-measuring.

## Closed

- **L-002 (closed 2026-08-01):** Contract specifications were verified only
  against secondary sources. Resolved: all 8 instruments primary-source
  verified live on cmegroup.com (browser session; A-003 → VERIFIED). New
  details captured in config: calendar-spread ticks, listing counts (MYM 4
  quarters vs 5 for other micros; treasuries 3), exact termination times
  (index micros 9:30 a.m. ET 3rd Friday; ZT/ZF 12:01 p.m. CT last business
  day; ZN/ZB 12:01 p.m. CT 7 business days prior to last business day).
