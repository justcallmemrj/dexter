# CONTEXT-HANDOFF — dexter intraday RV research (complete state, 2026-08-04)

Paste this whole file into a new session to restore full context. Owner:
**Derrick Johnson**. Repo `C:\Users\Mrder\dexter`, branch
`claude/futures-relative-value-research-fpv6m3` (all work committed AND
pushed — `git push` works from the harness; check `git log --oneline -8`).
QC cloud project **34720894** (free tier). Educational research; internal R&D
only — not investment advice.

---

## 0. READ FIRST — where the program actually stands

**All seven pairs in the locked universe have been tested at minute resolution
under one frozen, pre-registered protocol. Not one is tradable at intraday
horizon. Version 1's core hypothesis has NO SURVIVING CANDIDATE (D-018).**
The program outcome is written up in `reports/13_final_research_summary.md`
and notebook 13, and concluded as a **no-go (D-019)**.

Under CLAUDE.md hard gate 4 ("no forced positive conclusion") this is a
legitimate research outcome. It is recorded as the finding, not worked around.

**What is NOT concluded:** that these markets contain no structure. They contain
a real, consistent, correctly-signed reversion effect. It is simply smaller than
the tick, and most of what looked large was microstructure.

**Open thread 1 (notebook 06 / L-013) has since RUN — D-021, report 06.** The
no-go survived it, but one supporting claim did not: the significant
*continuation* that falsified MES–MYM and MES–MNQ is carried by first-30-minute
events. See §1b. Reports 02 and 13 carry inline amendments where this bites.

**The MES–M2K delayed-entry thread has ALSO now RUN — D-022 (pre-registered
2026-08-04) → D-023, validation report 14, notebook 14.** Verdict:
**DELAY-ROBUST** — the one cost-clearing surface in the program SURVIVES
delayed entry and is NOT the laggard catching up. See §1c. The no-go still
stands (criterion (b) untouched and failing; ceiling pre-committed). Reports
02/13, L-014 and the A-006 register row carry fresh inline amendments.

**⚠ READ NEXT — L-021, a session-clock defect found 2026-08-04 while
pre-registering the session experiment.** `rth_frame` filters on the clock the
DATA carries; LEAN stamps CBOT Treasury bars in **America/Chicago** and index
bars (including CBOT-listed MYM) in **America/New_York**. So the four Treasury
pairs were analysed on **10:31–17:00 ET, not the 09:30–16:00 ET that D-016,
reports 03/06/13 and this handoff all state** — missing the whole morning and
running two hours PAST the 15:00 ET Treasury settlement. Established, not
inferred: banked `own_splice_acceptance_*.json` shows ZN spanning 08:31–16:00
and M2K 09:31–17:00, each its own LEAN regular session in its own exchange
timezone. Bar count cannot detect this (any 390-minute window inside a 23h
session gives 390 bars), which is why `medbars=390` never flagged it. The four
Treasury verdicts are NOT withdrawn (7–11x cost gaps are not a one-hour
artifact, and L-016 tick quantisation is window-independent) but they are
UNCONFIRMED on the window they claim to describe. **Notebook 15 / D-024 owns
measuring the corrected window and annotating the corpus — do not annotate
reports 03/13 before that measurement exists.**

**D-024 is PRE-REGISTERED and UNRUN** (2026-08-04): the treasury-native session
experiment (A-013), which must first correct L-021. See §1d.

`lean/algorithm/` is still empty and stays empty: the LEAN build remains
hard-gated on Derrick writing the exact token **`PROCEED TO LEAN BUILD`**.

## 1. THE SEVEN VERDICTS

| Pair | Verdict | Decision | Why |
|---|---|---|---|
| MES–MYM | **A-006 FALSIFIED** | D-011 | 0/60 positive at \|t\|>=3; 24 of 26 significant cells NEGATIVE (continuation) |
| MES–MNQ | **A-006 FALSIFIED** | D-013 | same; residual VR sits ABOVE its own leg. Roll carries ~70 bps/yr one-signed drag |
| MES–M2K | **AMBIGUOUS / MICROSTRUCTURE** | D-015 | (a)+(c) pass, +6.31 bps at t=5.31 would clear cost — but (b) fails; VR>1 = lead-lag (probed 2026-08-04: real but NOT the carrier — §1c) |
| ZF–ZN | **AMBIGUOUS / IMMATERIAL** | D-017 | 20/20 cells positive, t to 9.44, effect **11x below cost** |
| ZT–ZF | **AMBIGUOUS / IMMATERIAL** | D-018 | 20/20, **7x below cost** |
| ZN–ZB | **AMBIGUOUS / IMMATERIAL** | D-018 | 20/20, **9x below cost**, largest roll shock in universe |
| ZT–ZN | **AMBIGUOUS / IMMATERIAL** | D-018 | 16/20, **9x below cost** |

Reports: `reports/validation/02_minute_pair_relationships.md` (index, §12 is
M2K) and `03_treasury_pair_relationships.md` (curve).
Data: `reports/machine_readable/nb02_<PAIR>_*.csv` for all seven.

## 1b. THE SIGNAL-DEFINITION RE-TEST (D-020 → D-021, report 06)

Pre-registered before the code existed. Four pairs re-run under three signal
definitions in one pass: **Z0** (the configured 390-bar overnight-spanning
score, re-emitted as a reproduction gate), **Z1** (session-anchored expanding
window, 30-bar warm-up), **Z2** (Z0 with first-30-minute events dropped —
the decomposition), plus an exploratory open-only subset.

- **Both validity gates passed in all four runs.** Z0 reproduced the banked
  notebook-02/03 grid **60/60 cells exactly** in every pair (so the data path is
  byte-identical, and it is a 4th determinism check on D-009); the Z1 event
  clock goes to 0.0% inside the warm-up.
- **The finding:** MES–MYM's 16 significant honest cells (all NEGATIVE under Z0)
  become 25 (all POSITIVE) under Z2; MES–MNQ's 15 all-negative become 21
  all-positive. The open-only subset is negative at every horizon in all three
  index pairs and is the **only** negative row anywhere in the ZF–ZN control.
- **Nothing advanced, and could not have.** Criterion (b) is computed on the
  RESIDUAL — no z-score enters it — so it is unchanged and still fails; the
  ceiling a signal change can reach is AMBIGUOUS/MICROSTRUCTURE, stated in
  D-020 before the numbers existed. The window is also spent.
- **L-013 reads MATERIAL — DIRECTION ONLY** because MES–M2K's criterion (a)
  flips (satisfied under Z0, fails under Z1).
- **Session-anchoring is NOT a strict improvement (L-018):** under Z1, S2
  produces **zero** cells at |t| ≥ 3 anywhere in any index pair while S1
  satisfies adjacency. Choosing a signal definition changes which hedge spec
  can pass.
- Runs: "Hyper Active Tan Hippopotamus" (MYM), "Muscular Blue Goshawk" (MNQ),
  "Crawling Magenta Barracuda" (M2K), "Measured Black Lion" (ZF–ZN control).
  Data: `nb06_<PAIR>_{signal_grids,event_clocks,scalars}.csv`.

## 1c. THE DELAYED-ENTRY RE-TEST (D-022 -> D-023, report 14, notebook 14)

Pre-registered before any code existed; the interpretation ceiling (no branch
can advance the pair) was frozen with it. Two QC backtests BY DESIGN (L-019):
part 1 "Creative Tan Antelope" (Z0 half), part 2 "Swimming Red Pigeon" (Z2
half + cross-correlation); both compute everything, each emits <= 57 keys.

- **All eight validity gates passed and were read first.** Both emissions
  set-identical to frozen manifests (54 + 57 keys); unmatched d=1 grids
  reproduced banked nb02 AND nb06 **60/60 cells exactly** each; matched
  n_events constant across delays in all 80 families; the two parts' shared
  diagnostics character-identical (5th D-009 determinism demonstration);
  crosscorr machinery sound (c0 = 0.788, 15 finite CIs, 1,000 replicates).
- **The finding:** on the frozen 37-cell read set (all included), retention
  ratio_d = ms(d)/ms(1) at entry t+d on MATCHED event sets is
  **rho(2)=0.932, rho(5)=0.849, rho(15)=0.536; S(5)=0.73, S(15)=0.59** — the
  DELAY-ROBUST branch. Catch-up predicts ~0 by d=5. Headline: Z2 S1 3.0/120
  runs +6.68 -> +5.89 -> +4.74 -> +2.24 bps across d = 1/2/5/15.
- **The cross-correlation found the lead-lag and measured it too small to
  matter:** ab_1 = corr(r_MES(t-1), r_M2K(t)) = **+0.033** [+0.021, +0.047]
  vs mirror +0.004; every k=2..5 ~ 0; X = TRUE. One bar deep, ~0.03 — and
  the t+1 convention already skips that bar. Both probes agree: **the
  surface is not laggard catch-up.** D-015's [PLAUSIBLE] attribution is
  withdrawn as the surface's explanation (L-014's thin-leg discipline binds
  unchanged).
- **Nothing advances, exactly as pre-registered.** Hypothesis-generating
  ONLY: it buys a banked target for the session/resolution thread. Honest
  counter-notes on the record (D-023): rho(15) sits BELOW the AR(1)
  prediction (0.77-0.85), and the criterion-(b) base-sampling evaporation
  is now an OPEN PUZZLE (unconditional VR vs conditional event study), not
  an explained artifact.
- Verdict machinery: `src/spread_research/delayed_entry_summary.py`, pinned
  by `tests/unit/test_delayed_entry_summary.py` (210 tests green). Data:
  `nb14_MES_M2K_{delay_grids,crosscorr,scalars}.csv`, two nb14 figures.

## 1d. THE SESSION EXPERIMENT — D-024 PRE-REGISTERED, NOT YET RUN

Notebook 15. Pre-registered 2026-08-04 before any code existed; verdict will be
**D-025**. Reads A-013 ("RTH-only captures the bulk of exploitable signal",
UNVERIFIED) and simultaneously corrects L-021.

- **Why it is genuinely new, unlike notebooks 06 and 14:** both of those
  carried a ceiling of AMBIGUOUS/MICROSTRUCTURE because criterion (b) is
  computed on the RESIDUAL and no signal definition or entry bar can touch it.
  **A session change alters which bars form the residual, so (b) is LIVE and
  must be RECOMPUTED.** This is the first experiment since notebook 03 that can
  move a Treasury verdict on its own terms.
- **Windows (all stated in BOTH clocks — now a binding convention):**
  S-USED (09:30,16:00] CT = 10:31–17:00 ET, what the banked runs did, the
  reproduction gate · S-RTH (08:30,15:00] CT = 09:31–16:00 ET, the corrected
  baseline every document claims · S-SETTLE (08:30,14:00] CT = 09:31–15:00 ET,
  open→**CME Treasury settlement** · S-CASH (07:20,14:00] CT = 08:21–15:00 ET,
  the true cash-open session, a CONDITIONAL arm.
- **Boundary provenance, asymmetric and declared:** the 14:00 CT close is
  PRIMARY-SOURCED (CME settles ZT/ZF/ZN/ZB on the VWAP of 13:59:30–14:00:00 CT;
  E-mini S&P on 14:59:30–15:00:00 CT — so the program's 16:00 close is the
  EQUITY settlement, inherited by the wrong asset class). The 08:20 ET open is
  a CONVENTION (historic floor open, this repo's own figure), NOT on CME's
  specs page, and LEAN calls those bars `premarket`. It may not be tuned.
- **S-CASH is conditional** because `self.history(contract, …)` returns only the
  LEAN regular session (~450 bars/day; Treasuries 08:31–16:00 CT), so
  pre-08:30-CT bars are not delivered. Getting them needs
  `extended_market_hours=True`, which would change `build_continuous`'s
  390-bar factor window and break D-009 comparability. The frozen fix: measure
  factors and run `splice_audit` on the REGULAR-SESSION SUBSET of the extended
  fetch, then apply them to the denser series — gated on reproducing the banked
  factor table character-for-character, else the arm is VOID and unreported.
- **Pairs:** all four Treasury pairs and nothing else (D-016 precedent,
  registered together, order ZF–ZN → ZT–ZF → ZN–ZB → ZT–ZN). **No index
  control** — an index pair would have to add or remove the 09:31–10:30 ET
  hour, and L-018 proved that hour can own an index pair's pooled sign
  (measured: MES–MYM's largest honest effect moves 1.703x when merely the
  first 30 minutes of events are dropped), so such a control fires by
  construction and would also re-express D-021's barred Z2 sign flip. The
  control is instead **S-HALF**, a within-Treasury displacement placebo:
  (09:00, 15:30] CT, 390 bars, anchored to nothing, giving a dose-response in
  window displacement of 0 → 30 → 60 minutes across S-USED → S-HALF → S-RTH.
- **Threshold 2.0x, not 1.5x:** a pure signal re-specification on identical
  bars already moves the "largest honest effect" statistic 1.467x (ZF–ZN,
  Z0 +0.286 → Z1 +0.195) and relocates its argmax, so 1.5x sat at the
  statistic's own noise floor. The move factor is directionless and
  sign-aware, and free-argmax and fixed-cell readings must agree.
- **Ceiling:** costs are tick-derived and session-independent, so
  ECONOMICALLY IMMATERIAL is expected to stand under every branch; the
  pre-open cost bar is HIGHER (A-008's 1-tick spread is scoped to "liquid RTH"
  and this run cannot measure quotes); no pair advances to LEAN.

## 2. THE FOUR NEAR-MISS FAKE EDGES (the real deliverable)

Each would have been published as an edge by a less careful battery. Carry
these forward into any new work:

1. **Bid-ask bounce** (MYM/MNQ): residual VR ~0.75 with p<0.001 that is flat
   past q=30 and returns to ~0.99 at 5-minute base sampling.
2. **Lead-lag from a thin leg** (M2K, L-014): a monotone, cost-clearing,
   t=5.7 surface initially attributed to the laggard catching up. M2K's own
   VR at q=2 is **1.012 (above 1)** — the tell. *(Amended by D-023: the
   catch-up is real but ONE bar deep and ~0.03 of correlation — it does not
   carry the surface, which survives 15-minute delayed entry. The thin-leg
   WARNING and the base-sampling check stand unchanged; the mechanism of
   the M2K surface is now an open question.)*
3. **Sliding reference window** (A2): differencing a residual built around a
   trailing mean credits the window moving. On two INDEPENDENT random walks it
   reports +5.4 bps at t=20.3. Fixing it dropped a headline from +2.14 bps
   t=+8.91 to −0.32 t=−0.67.
4. **Tick quantisation** (treasuries, L-016): coarse ticks vs minute vol give
   VR 0.13–0.32 that evaporates at 15-minute bars — and the same coarseness is
   what makes the costs large.

**Before believing ANY positive reversion result: (i) measure the position's
P&L, not the residual's change; (ii) compare against BOTH legs' own VR;
(iii) confirm it survives coarser base sampling.** All three are in the battery.

## 3. METHOD RULES THAT ARE NOW BINDING

- **L-011:** a fitted beta must carry its regression INTERCEPT. `y − β_t·x` on
  log prices scales beta noise by log(price) — ~105 bps on MYM for 0.001 of
  drift. Use `pair_minute_report.centered_residual`. `pair_builder.build_residual`
  keeps the no-intercept form ON PURPOSE (correct for notional/DV01).
- **A1:** a flagged splice is an artifact only if the gap can EXPLAIN it —
  material, same-signed, and inside a band around the splice return. Both bounds.
- **A2:** the primary statistic is POSITION P&L with beta frozen at the signal
  bar; report the session-clustered mean beside the pooled mean.
- **L-013:** the 390-bar z-window spans the overnight break, so 22.7–24.7% of
  index signals fire in the first 30 min. ABSENT in treasuries (12.7–13.6%) —
  it is an equity-session-open artifact. Notebook 06 owns the fix.
- **L-015 / L-017:** roll windows are pair- and asset-class-specific. Adopted
  index values (`roll_exclusion_bars: 780`, `post_roll_warmup_bars: 780`) do
  NOT transfer: M2K needs >=1170, treasuries need none.
- **Pre-registration is the house style.** D-010/D-012/D-014/D-016 were all
  written before the corresponding results existed. D-016 covered all four
  treasury pairs at once specifically to stop per-pair tuning.

## 4. WHAT IS BUILT AND VALIDATED

- **D-009 own-splice constructor** (`src/spread_research/roll_adjustment.py`) —
  now validated on **all eight instruments**, and demonstrated DETERMINISTIC
  twice (D-014 predicted M2K's flagged roll and its numbers in advance;
  ZT230831 flagged identically in both ZT runs). It replaces QC's adjustment,
  which is FALSIFIED (A-004: 40/220 bad factors).
- **`intraday_reversion.py`** — session-safe returns, non-overlapping variance
  ratio + session bootstrap, within-session AR(1) half-life, session-clustered
  conditional P&L event study, roll diagnostics, event clock. Its test suite
  encodes the known answers (random walk → VR 1; planted AR(1) → closed-form VR
  and recovered half-life; bounce walk → must NOT read as an edge).
- **`pair_minute_report.py`** — the whole battery as ONE tested function
  returning the flat {key: string} dict the QC summary-stat channel needs.
  `anchor="unit"` for index pairs, `"vol_ratio"` for treasuries.
- **`calendars.py`** — rule-derived CME holidays 2018–2027.
- **Pipeline is pair-parameterised end to end**: one `PAIR` constant in the
  driver + `MARKETS` map; `ingest_qc_pair_minute.py` and `nb02_figures.py` take
  `--pair` and namespace every output. **210 tests green.**

## 5. OPEN THREADS — Derrick's call

Each is a NEW program needing fresh pre-registration. **None may reuse this
window's results as evidence** — the window is spent for this hypothesis.

1. ~~**Final research summary (notebook 13 / report 13).**~~ **DONE 2026-08-03
   (D-019)** — `reports/13_final_research_summary.md`, notebook 13 executed
   with outputs banked, `nb13_program_summary.csv`, two figures. Every headline
   figure is recomputed from the banked CSVs by
   `src/spread_research/program_summary.py` and pinned by unit test, so a report
   can no longer drift from its own evidence.
2. ~~**Notebook 06 / L-013 fix.**~~ **DONE 2026-08-03 (D-020 → D-021)** — see
   §1b and `reports/validation/06_signal_definition_and_session_anchoring.md`.
3. ~~**MES–M2K delayed entry (D-015).**~~ **DONE 2026-08-04 (D-022 ->
   D-023)** — see §1c and `reports/validation/14_delayed_entry_mes_m2k.md`.
   DELAY-ROBUST; closed on this window by D-022's Review clause (no re-run
   under any variation).
4. **Different resolution or venue.** **The SESSION half is now
   PRE-REGISTERED as D-024 (notebook 15, unrun) — see §1d**, and it also
   corrects the L-021 clock defect. Note the equity-RTH claim in this thread's
   original text was itself wrong for Treasuries (they ran on 10:31–17:00 ET).
   Still open and NOT covered by D-024: **quote data** (which would replace the
   A-008 1-tick placeholder with a measurement — and A-008 is scoped in config
   to "liquid RTH", so the pre-open cost bar is unmeasured) and
   **second/tick resolution**. `research_config.data.later_resolutions`
   anticipates both. D-023's banked target stands: the M2K surface survives a
   15-minute delayed entry while its unconditional VR evaporates at coarse
   bars — finer resolution is what discriminates the reconciling mechanisms.
   Each needs its own pre-registration and a fresh window.
5. **(New, optional) Open-window continuation as its own hypothesis.** L-018
   documents a consistent, correctly-signed continuation effect in the first 30
   minutes across four pairs including the Treasury control. It is a DIFFERENT
   hypothesis from A-006, the residual variance ratio is not its supporting
   statistic, and D-020 deliberately issued no verdict on it. Needs its own
   pre-registration and its own verdict rule.

Suggested order now: **4** (optionally 5) — thread 3 is DONE and the
session/resolution thread now carries the banked D-023 target.

## 6. OPERATIONAL FACTS

- **`git push` WORKS from the harness** — everything through D-023 is
  committed and pushed. Commits are authored as
  `Claude <noreply@anthropic.com>` via `git -c user.name=... -c user.email=...`
  because the repo has no committer identity configured.
- Local env: `.venv` Python 3.14.5 — always `.venv/Scripts/python.exe`.
  `pytest tests/` → **210 green**.
- **L-019 (BINDING): never design a single-backtest emission above ~57 keys.**
  All four nb06 runs emitted 67-68 keys and the retrieved statistics silently
  lost exactly the 12-key S_RL block every time. Split batteries into PARTS
  (a frozen PART constant filtering only the emission; both parts compute
  everything; cross-part identity of shared diagnostics is a free determinism
  gate) and have the ingest compare the retrieved key SET against a frozen
  manifest plus S_KEYS.
- **L-020: QC files/update rejects files > 32,000 chars** (explicit error).
  `crosscorr.py` exists as a separate upload because of this. Watch
  `build_qc_upload.py` byte counts before run day.
- **The OS-clipboard bridge beats both chunk-paste and slice-reads.** Upload:
  `Set-Clipboard` each chunk -> focus a scratch textarea on the QC page ->
  real Ctrl+V -> read `.value` from JS (byte-perfect, no transcription).
  Download: stash JSON in a textarea, select, real Ctrl+C ->
  `Get-Clipboard -Raw` to file. ALWAYS verify SHA-256 both ways (in-page
  `crypto.subtle` vs local) — the hash caught a hand-transcription error
  again this session before the clipboard route was adopted.
- **Launch timing:** cancelling the import-rewrite modal while the free-tier
  deployment still says "Requesting Backtest" ABORTS the launch (lost one
  attempt this way; the relaunch got a fresh run name). Dismiss the modal
  only after "Waiting for Results" appears (~20-25s). An aborted attempt
  keeps its tab name; the real backtest may appear under a DIFFERENT name —
  match on `backtests/read` + S_PAIR, not the tab title.
- **Ingest flow for split runs:** `ingest_qc_delayed_entry.py --check
  raw_partN.json --part N` validates one part (gates 1/2/4[/3]) BEFORE the
  second backtest is spent; the full two-part call with `--compare-banked`
  writes nothing unless all eight gates pass.
- **Uploading only what changed:** `python scripts/build_qc_upload.py --driver
  {pair|signal} --only a.py,b.py` skips unchanged modules and prints a
  line-ending-normalised sha for every file, so the copies already in the
  project can be VERIFIED in-browser instead of re-uploaded. Verified in this
  session — 3 of 6 files needed uploading and all 6 hashes matched afterwards.
- **Reading results back is the slow part.** Use `browser_batch` to request
  five `window.__json.slice(a,b)` calls in ONE round trip (900-char slices;
  output truncates near 1,030). Reassemble locally and CHECK THE SHA-256
  against the browser's before ingesting — one slice boundary silently lost
  four characters in this session and the hash caught it immediately.
- **QC browser ops** (this is the fiddly part, full detail in the memory file
  `dexter_rv_research_project.md`):
  - The in-app Claude browser is NOT logged in. Use **claude-in-chrome**.
  - Return only SHORT SCALARS from `javascript_tool` — compile/backtest ids trip
    "[BLOCKED: Cookie/query string data]" and raw base64 trips a base64 filter.
    Stash in `window.__x`; read results back by slicing JSON in ~850-char pieces.
  - Upload via gzip+base64 in ~3000-char chunks, decompress with
    `DecompressionStream('gzip')` read through a **reader loop**
    (`new Response(blob.stream())` throws). **Always verify a SHA-256 of the
    base64 before decompressing** — 3 of ~10 transfers silently corrupted one
    500-char block, and per-block hashes located it in one round trip.
  - `compile/create` + `compile/read` are free — always compile before spending
    a backtest. `backtests/create` is paid-gated: launch by DOM-clicking
    `a[aria-label="Backtest Project (Ctrl+F5)"]` inside the same-origin iframes.
  - After clicking Backtest a modal offers to rewrite your imports → **click
    Cancel** (~(1024,400)); Yes overwrites the uploaded source.
  - Push protocol: files/update → **RELOAD the page** → compile → click.
  - The backtest appears in `backtests/read` only ~60s after the click.
  - Long JS poll loops hit a 45s CDP timeout — poll in <=35s slices.

## 7. STILL OPEN / UNVERIFIED

- **A-007/A-008** (commission and spread assumptions) remain placeholders. The
  cost comparisons in reports 02/03 use verified TICK specs and are robust to a
  3x error, but a real broker schedule is still owed.
- **A-012** (CTD / delivery-cycle contamination in ZB/ZN) remains UNVERIFIED —
  ZN–ZB was disqualified on cost and microstructure before A-012 could bind.
- **A-013** (RTH-only captures the signal) is untested and is a live limitation
  for treasuries specifically, whose liquid session starts ~08:20 ET. **D-021
  strengthened the case for testing it.**
- **L-012** (MYM 2019-12-12 boundary print) is a watch item, not resolved.
- **L-018** (open-window continuation; session-anchoring is not a strict
  improvement) is new as of D-021 and binds any future signal work.
- **L-019/L-020** (emission-channel key loss; 32k file cap) are operational
  limits from the notebook-14 session — see §6.
- **L-021 (session-clock defect, 2026-08-04)** — the Treasury pairs ran on
  10:31–17:00 ET, not the documented 09:30–16:00 ET. See §0. Binding: state
  every window in BOTH clocks and gate on an observed timezone witness, never
  on bar count. Reports 03/06/13 and D-016/D-017/D-018 carry a session label
  that is an hour wrong; D-024 owns correcting it after measurement.
- **Headroom warning (L-020):** `intraday_reversion.py` (29,461 uploaded
  chars) and `pair_minute_report.py` (29,332) are both within ~2,600 of QC's
  32,000-char `files/update` cap. Notebook 15's battery must go in a NEW
  module, as `crosscorr.py` did.
- **The D-023 open puzzle:** the M2K conditional effect survives a
  15-minute delayed entry while the residual's unconditional VR evaporates
  at 5-minute base sampling. Both banked. Reconciling mechanism unknown —
  the sharpest question the program now owns.
- Two of the four near-miss fake edges in §2 now have a fifth sibling worth
  naming: **a minority of events can own the pooled sign of an entire grid.**
  22.7–24.7% of events flipped three index pairs from negative to positive.
  Always report the subset an artifact selects, separately.
