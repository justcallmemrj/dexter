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
- **L-018 (supersedes the OPEN part of L-013; validation report 06, D-021):**
  **The first 30 minutes of the equity session carry a CONTINUATION effect, and
  under the 390-bar score they are large enough to flip the sign of a whole
  grid.** Fading a dislocation that fires in that window lost money at every
  horizon in all three index pairs (t to -3.5) and produced the ONLY negative
  row anywhere in the ZF-ZN Treasury control (-0.15 bps at t = -3.87). Because
  those events are 22.7-24.7% of index samples, removing them and nothing else
  flips MES-MYM from 16 significant cells all NEGATIVE to 25 all POSITIVE, and
  MES-MNQ from 15 all negative to 21 all positive. They are 12.7% of the
  Treasury control's sample and there they flip nothing.
  Two consequences bind future work:
  (i) **any intraday result computed under an overnight-spanning z-score must
  report the open-window subset separately**, because a minority of events can
  own the pooled sign;
  (ii) **session-anchoring is not a strict improvement.** Under the
  session-anchored score, S2 (the trailing-OLS residual) produced ZERO cells at
  |t| >= 3 anywhere in any index pair, where S1 satisfied the adjacency
  requirement — [PLAUSIBLE] estimation-noise stacking, since S2 is already a
  deviation from a trailing fit and is then normalised again against a short
  early-session dispersion (L-007/L-011). Choosing a signal definition changes
  which hedge specification can pass; the two are not separable.
  Not resolved: whether the open-window continuation is tradable. That is a
  DIFFERENT hypothesis from A-006 and needs its own pre-registration.
- **L-013 (diagnosis RESOLVED 2026-08-03, consequences moved to L-018):** Under
  the current config (`zscore_lookback_bars: 390`, one RTH day)
  the z-score window reaches back across the overnight break, so the first bars
  of a session are scored against the previous session's mean. Consequence
  measured in validation report 02 §6.4: **24.3% of |z| >= 2 crossings occur in
  the first 30 minutes and ~37% in the first hour**, decaying to ~3% per 30-min
  bucket by the afternoon. A large minority of "intraday dislocations" under
  this configuration are overnight repricings. Notebook 06 must either
  session-anchor the z-score (reset at the open), add a warm-up after the open,
  or explicitly test the open-gap subset as its own hypothesis. Does not affect
  the report-02 verdict, which is negative with or without those events.
  **Notebook 06 ran all three (D-020/D-021, validation report 06). The
  diagnosis is confirmed and the verdict statement above is confirmed — report
  02's VERDICT is unchanged — but the last clause was too generous about its
  REASONING: report 02's significant continuation does not survive removing
  those events, it is produced by them. See L-018.**

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
  *AMENDED 2026-08-04 by D-023 (notebook 14): the delayed-entry test RAN.
  The lead-lag is REAL but one bar deep and tiny (ab_1 = +0.033, mirror
  +0.004, k >= 2 all ~0) — and the t+1 entry convention already skips that
  bar, so it does not carry the conditional surface: the effect survives
  delayed entry (rho(5) = 0.849, rho(15) = 0.536 on matched event sets;
  DELAY-ROBUST). The base-sampling discipline above binds unchanged — the
  VR evaporation at coarse bars is now an OPEN PUZZLE (unconditional
  property vs conditional-event property), not an explained artifact. No
  advance: criterion (b) unchanged, window spent, D-019 stands.*
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

- **L-019 (2026-08-04, discovered during the D-022 pre-registration audit):**
  **The QC summary-statistic channel silently lost keys in every notebook-06
  run, and no gate noticed.** All four nb06 runs recorded S_KEYS = 67–68
  (emitted) but the retrieved statistics dicts hold only 55–56 keys — exactly
  the 12-key S_RL per-roll block is missing in every run, while all seven
  nb02/nb03 runs (54–57 keys) came back complete with their S_RL blocks. The
  loss was harmless there (no gate or CSV consumed S_RL from nb06), which is
  precisely why it went unseen; where between `set_summary_statistic` and the
  browser read the keys vanish is UNATTRIBUTED. Consequences, binding until
  the mechanism is found: (i) no run may be designed to emit more than ~57
  summary-statistic keys in one backtest — split the battery into parts
  instead (D-022 is the first to do so); (ii) every future ingest must check
  the RETRIEVED key set against a frozen expected manifest AS A SET and
  against the emitted S_KEYS count — count-only or subset checks pass exactly
  the failure that happened here.
- **L-020 (2026-08-04, notebook-14 upload):** **QC `files/update` rejects any
  file above 32,000 characters.** `intraday_reversion.py` crossed the cap
  when the delayed-entry machinery was added and the upload failed with an
  explicit error (not silently). Resolution: `leg_crosscorr_profile` moved to
  its own module `crosscorr.py` (uploaded as a sixth flat file); the double
  60/60 reproduction gate in notebook 14 proves the split changed nothing.
  Consequence: any module approaching ~30k characters must be split BEFORE
  the run day, and `build_qc_upload.py`'s per-file byte counts are the early
  warning to watch.

- **L-021 (2026-08-04, found while pre-registering the A-013 session experiment;
  [ESTABLISHED] from banked pipeline data, not inference):** **`rth_frame`
  filters on the clock the DATA carries, and that clock is not the same for
  both asset classes — so every Treasury result in this program was computed on
  10:31–17:00 ET, not the "09:30–16:00 ET" that every document states.**

  Evidence chain, all four links independent:
  0. **In-repo and decisive on its own:** `config/research_config.yaml`
     specifies the session as `rth_start_ct: "08:30"` / `rth_end_ct: "15:00"`
     — i.e. in CENTRAL time — while `intraday_reversion.py` hardcodes
     `RTH_OPEN = time(9,30)` / `RTH_CLOSE = time(16,0)` under the comment
     "09:30-16:00 ET (config research_config.yaml session_filter, 08:30-15:00
     CT)". The code applies the ET numbers to whatever clock the data carries,
     so on CT-stamped bars it misses the config's own stated CT window by
     exactly one hour. (The config keys are themselves dead — nothing reads
     `session_filter` — so the divergence was never enforced.)
  1. CME (primary source, browser): E-mini S&P Globex opens Sunday **6:00 p.m.
     ET**; ZN Globex opens Sunday **5:00 p.m. CT** — the same instant.
  2. Banked `qc_data_inventory.json`: the index micros' first bar is
     `2019-06-02 18:01`, the Treasuries' is `2019-06-02 17:01`. Same reopen,
     stamps one hour apart.
  3. LEAN `market-hours-database.json`: `Future-cbot-ZT/ZF/ZN/ZB` carry
     `exchangeTimeZone America/Chicago`; `Future-cme-MES/MNQ/M2K` **and
     `Future-cbot-MYM`** carry `America/New_York`. MYM is CBOT-listed yet
     New-York-stamped, so the stamp follows the timezone field, not the venue.
  4. **Decisive**, banked `own_splice_acceptance_*.json`: the constructed ZN
     series spans `08:31 → 16:00`; M2K spans `09:31 → 17:00`. Each is exactly
     its own LEAN *regular session* expressed in its own exchange timezone
     (ZN 08:30–16:00 CT; M2K 09:30–17:00 ET).

  `rth_frame` keeps `(time(9,30), time(16,0)]` of `df.index.time` with no
  timezone awareness. A grep for `America/`, `tz=`, `timezone` across `src/`,
  `lean/` and `config/` returns no timezone HANDLING — the only hits are
  pass-throughs (`roll_adjustment.py` `tz=tz`, the four drivers' `tz=None`),
  a UTC localize in the preview path, and `datetime.timezone` in `reporting.py`.
  Nothing anywhere converts, asserts or even records the clock of an analysed
  index. Applied to Chicago-stamped Treasury bars `rth_frame` therefore
  selects
  **09:31–16:00 CT = 10:31–17:00 ET**, which still yields exactly 390 bars —
  which is why `medbars=390` never revealed it. Bar count cannot detect this:
  any 390-minute window inside a ~23h session gives 390 bars.

  **What the Treasury runs actually measured:** a window that EXCLUDES
  09:30–10:30 ET entirely and INCLUDES 15:00–17:00 ET — i.e. two hours *after*
  the CME Treasury settlement (VWAP of 13:59:30–14:00:00 CT = 15:00 ET),
  running to the Globex daily close. The intended window was the equity RTH.

  **Scope of the damage — and what is NOT damaged.** The analysis was
  internally consistent: a genuine, contiguous 390-bar session was analysed,
  session boundaries never straddled midnight, and every statistic is valid
  *for the window actually used*. Nothing is arithmetically wrong. What is
  wrong is the LABEL, and three inferences that lean on it:
  (i) report 03 §6 item 3 / D-020 / `session_anchored_zscore`'s docstring attribute
  the Treasuries' flat event clock to "09:30 ET is not an open for them" — the
  clock's leading bucket is actually 10:31–11:00 ET, so the conclusion may be
  right but the stated basis is not what was measured;
  (ii) the D-016 clause "RTH stays 09:30–16:00 ET … the cash open around
  08:20 ET is excluded" understates the exclusion by an hour;
  (iii) the splice, documented throughout as "10:30 ET", is **10:30 CT =
  11:30 ET** for Treasuries (`treasury_roll_schedule(splice_time=time(10,30),
  tz=None)` compared against a Chicago-stamped index). Harmless to the
  construction — it is a consistent choice and sits inside every candidate
  window — but mis-documented.

  **MEASURED AND CLOSED 2026-08-04 (D-025, report 15):** the corrected window
  (S-RTH) moves each pair's largest honest effect by only 1.01–1.26x and changes
  no verdict branch, so the mislabelled hour was real but **immaterial to every
  conclusion** — the label was wrong, the results were not. Reports 03/06/13 and
  D-016/D-017/D-018 may now be annotated with the corrected window and this
  measured impact. The timezone witness confirmed the mechanism live: every
  regular-fetch Treasury leg delivered 08:31-16:00 at ~450 bars/day.

  **Binding consequences.** (a) Any future session work must state windows in
  BOTH clocks and gate on an observed timezone witness, never on bar count.
  (b) Reports 03/06/13 and D-016/D-017/D-018 carry a session label that is an
  hour wrong and must be annotated once the corrected window is measured
  (notebook 15 / D-024 owns this). (c) The four Treasury verdicts are NOT
  withdrawn: cost ratios of 7–11x are not plausibly a one-hour-window artifact,
  and criterion (b) failed on tick quantisation (L-016), which is
  window-independent in mechanism. They are, however, now UNCONFIRMED on the
  window they claim to describe.

- **L-022 (2026-08-04, D-025):** **A placebo comparison that pits one move
  factor against another is DEGENERATE when neither moves.** D-024's rule reads
  DISPLACEMENT-CONFOUNDED iff the placebo's move factor is >= the treatment's,
  without requiring either to be material. On ZT-ZF both were ~1.01 — i.e.
  nothing moved at all — and the rule fired on a third-decimal difference,
  making Q1 read INCONCLUSIVE for that pair on no evidence. The verdict is
  reported as the frozen rule dictates, but the lesson binds future work:
  **any ratio-against-ratio control must be conditioned on the treatment
  having moved first** (e.g. "confounded only if the treatment moved AND the
  placebo moved at least as much"). The other three pairs read cleanly.
- **L-023 (2026-08-04, D-025; [PLAUSIBLE], not tested):** **L-018's
  open-window continuation did NOT generalise to the treasury cash open.**
  D-024 predicted from L-018 that the pre-open block containing the 08:30 ET
  macro releases would show CONTINUATION. Across all four Treasury pairs the
  S-CASH open subset holds ZERO significant negative cells, while L-018's
  effect still reproduces where it was found (ZF-ZN's S-USED open subset,
  negative in 18/20 cells, banked cell at t = -3.87 reproduced exactly).
  The candidate explanation is that the equity open is a LIQUIDITY
  DISCONTINUITY — a closed market reopening — whereas an 08:30 ET release
  lands in a market already trading continuously (the smoke test measured the
  07:21-08:30 CT block printing every single minute). Consequence for future
  work: **do not assume L-018 transfers to any "information event" window.**
  It was measured at a session boundary and is only established there.

## Closed

- **L-002 (closed 2026-08-01):** Contract specifications were verified only
  against secondary sources. Resolved: all 8 instruments primary-source
  verified live on cmegroup.com (browser session; A-003 → VERIFIED). New
  details captured in config: calendar-spread ticks, listing counts (MYM 4
  quarters vs 5 for other micros; treasuries 3), exact termination times
  (index micros 9:30 a.m. ET 3rd Friday; ZT/ZF 12:01 p.m. CT last business
  day; ZN/ZB 12:01 p.m. CT 7 business days prior to last business day).
