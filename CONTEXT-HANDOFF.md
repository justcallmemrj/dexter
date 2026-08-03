# CONTEXT-HANDOFF — dexter intraday RV research (complete state, 2026-08-03)

Paste this whole file into a new session to restore full context. Owner:
**Derrick Johnson**. Repo `C:\Users\Mrder\dexter`, branch
`claude/futures-relative-value-research-fpv6m3`, HEAD **`295ff28`**.
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

`lean/algorithm/` is still empty and stays empty: the LEAN build remains
hard-gated on Derrick writing the exact token **`PROCEED TO LEAN BUILD`**.

## 1. THE SEVEN VERDICTS

| Pair | Verdict | Decision | Why |
|---|---|---|---|
| MES–MYM | **A-006 FALSIFIED** | D-011 | 0/60 positive at \|t\|>=3; 24 of 26 significant cells NEGATIVE (continuation) |
| MES–MNQ | **A-006 FALSIFIED** | D-013 | same; residual VR sits ABOVE its own leg. Roll carries ~70 bps/yr one-signed drag |
| MES–M2K | **AMBIGUOUS / MICROSTRUCTURE** | D-015 | (a)+(c) pass, +6.31 bps at t=5.31 would clear cost — but (b) fails; M2K's own VR>1 = lead-lag |
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

## 2. THE FOUR NEAR-MISS FAKE EDGES (the real deliverable)

Each would have been published as an edge by a less careful battery. Carry
these forward into any new work:

1. **Bid-ask bounce** (MYM/MNQ): residual VR ~0.75 with p<0.001 that is flat
   past q=30 and returns to ~0.99 at 5-minute base sampling.
2. **Lead-lag from a thin leg** (M2K, L-014): a monotone, cost-clearing,
   t=5.7 surface produced entirely by the laggard catching up. M2K's own VR at
   q=2 is **1.012 (above 1)** — the tell.
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
  `--pair` and namespace every output. **128 tests green.**

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
3. **MES–M2K delayed entry (D-015).** Entry at t+2/t+5/t+15 instead of t+1,
   plus leg-return cross-correlation at lags ±1..5. If lead-lag, the effect
   decays sharply with delay; if genuine reversion, it survives. Settles the
   one non-negative index result. **Note D-021 raised its stakes**: under the
   open-excluded signal M2K's best honest cell is +6.77 bps at t = 5.14, still
   the largest in the program.
4. **Different resolution or venue.** Every negative here is MINUTE resolution,
   TRADE bars, equity RTH (09:30–16:00 ET). Quote data, a treasury-native
   session (08:20 ET cash open), or second/tick resolution are DIFFERENT
   EXPERIMENTS, not re-runs. `research_config.data.later_resolutions` anticipates it.
   **D-021 promoted this**: a signal artifact this large at the session boundary
   is an argument for testing a different SESSION, not a different threshold.
5. **(New, optional) Open-window continuation as its own hypothesis.** L-018
   documents a consistent, correctly-signed continuation effect in the first 30
   minutes across four pairs including the Treasury control. It is a DIFFERENT
   hypothesis from A-006, the residual variance ratio is not its supporting
   statistic, and D-020 deliberately issued no verdict on it. Needs its own
   pre-registration and its own verdict rule.

Suggested order now: **3 then 4** — settle the one non-negative index result,
then decide whether to spend a new window on a different session or resolution.

## 6. OPERATIONAL FACTS

- **12 commits are LOCAL and UNPUSHED.** `git push` is blocked by the harness
  permission classifier; Derrick must run it. Commits are authored as
  `Claude <noreply@anthropic.com>` via `git -c user.name=... -c user.email=...`
  because the repo has no committer identity configured.
- Local env: `.venv` Python 3.14.5 — always `.venv/Scripts/python.exe`.
  `pytest tests/` → 182 green.
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
- Two of the four near-miss fake edges in §2 now have a fifth sibling worth
  naming: **a minority of events can own the pooled sign of an entire grid.**
  22.7–24.7% of events flipped three index pairs from negative to positive.
  Always report the subset an artifact selects, separately.
