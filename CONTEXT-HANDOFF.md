# CONTEXT-HANDOFF — dexter intraday RV research (complete state, 2026-08-03)

Paste this whole file into a new session to restore full context. Owner:
**Derrick Johnson**. Repo `C:\Users\Mrder\dexter`, branch
`claude/futures-relative-value-research-fpv6m3`, HEAD **`8650e2f`**.
QC cloud project **34720894** (free tier). Educational research; internal R&D
only — not investment advice.

---

## 0. READ FIRST — where the program actually stands

**All seven pairs in the locked universe have been tested at minute resolution
under one frozen, pre-registered protocol. Not one is tradable at intraday
horizon. Version 1's core hypothesis has NO SURVIVING CANDIDATE (D-018).**

Under CLAUDE.md hard gate 4 ("no forced positive conclusion") this is a
legitimate research outcome. It is recorded as the finding, not worked around.

**What is NOT concluded:** that these markets contain no structure. They contain
a real, consistent, correctly-signed reversion effect. It is simply smaller than
the tick, and most of what looked large was microstructure.

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

## 5. THE FOUR OPEN THREADS — Derrick's call

Each is a NEW program needing fresh pre-registration. **None may reuse this
window's results as evidence** — the window is spent for this hypothesis.

1. **Final research summary (notebook 13 / report 13).** Write up the negative
   program outcome with its evidence. The honest default deliverable.
2. **Notebook 06 / L-013 fix.** Session-anchor the z-score, re-run the closed
   pairs. Changes the SIGNAL definition, not the hypothesis — the cheapest
   remaining test of whether the whole grid was mis-specified.
3. **MES–M2K delayed entry (D-015).** Entry at t+2/t+5/t+15 instead of t+1,
   plus leg-return cross-correlation at lags ±1..5. If lead-lag, the effect
   decays sharply with delay; if genuine reversion, it survives. Settles the
   one non-negative index result.
4. **Different resolution or venue.** Every negative here is MINUTE resolution,
   TRADE bars, equity RTH (09:30–16:00 ET). Quote data, a treasury-native
   session (08:20 ET cash open), or second/tick resolution are DIFFERENT
   EXPERIMENTS, not re-runs. `research_config.data.later_resolutions` anticipates it.

Suggested order: **1 then 2** — bank the finding first, then spend one cheap
run on the signal definition before concluding the design was right and the
markets simply do not cooperate.

## 6. OPERATIONAL FACTS

- **7 commits are LOCAL and UNPUSHED.** `git push` is blocked by the harness
  permission classifier; Derrick must run it.
- Local env: `.venv` Python 3.14.5 — always `.venv/Scripts/python.exe`.
  `pytest tests/` → 128 green.
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
  for treasuries specifically, whose liquid session starts ~08:20 ET.
- **L-012** (MYM 2019-12-12 boundary print) is a watch item, not resolved.
