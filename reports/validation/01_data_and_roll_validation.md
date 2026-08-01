# Validation Report 01 — Data & Roll Validation (A-004 / D-004)

**Date:** 2026-08-01 · **Environment:** QC cloud project `dexter-rv-research`
(34720894) · **Tools:** `lean/research/qc_roll_audit.py` (zero-order roll
audit, chart-channel output) + splice-refetch sweeps; analysis in
`scripts/analyze_qc_roll_audit.py`
**Runs:** roll audit "Casual Fluorescent Orange Jellyfish"; refetch sweeps
"Geeky Orange Salmon" (A) + "Geeky Fluorescent Yellow Guanaco" (B); earlier
diagnostics "Alert Green Giraffe", "Pensive Yellow Green Snake"
**Machine-readable:** `qc_roll_audit.json` (streamed audit),
`qc_splice_refetch.json` (research-path refetch), merged `qc_roll_audit.csv`
**Figures:** `rollaudit_ar_vs_gp.png`, `rollaudit_leak_timeline.png`,
`rollaudit_refetch_verdict.png`

## 1. What was measured

For every continuous-contract mapping change over the research window
(220 rolls: 28 per index micro, 27 per Treasury), with the exact research
settings (OpenInterest mapping, BackwardsRatio normalization): the roll date,
old→new contract, old-contract days-to-expiry (dte), the raw calendar-spread
gap (gp, %) from per-contract minute History, trailing 3-day volume share of
the new contract (vs), and the adjusted-series **splice return** — measured
twice: in the **streamed** series (bar-by-bar backtest feed) and in the
**History-refetched** series (the path QuantBook/notebooks consume). The
yardstick for splice returns is each symbol's median |first-bar-of-day
return| (0.5–2 bp; ZT/ZF literally 0).

## 2. Roll calendar and mapping-timing facts

1. **[ESTABLISHED] Cadence is exactly quarterly** for all 8 instruments
   (partial edge years aside): 4 mapping changes per full year, none missing,
   none duplicated.
2. **[ESTABLISHED] Index micros flip at expiry-day open (dte = 0)** (single
   exception: MES 2020-03-18, dte=2). By flip time the new contract already
   carries 71–95% of trailing 3-day volume — QC's OpenInterest flip happens
   ~a week AFTER real-market liquidity migrates. Consequence: mapped-raw
   "execution" prices during roll week belong to the dying contract; any
   execution-realism work (notebook 07+) must implement OUR OWN roll schedule
   (calendar-based, ~7–9 days pre-expiry) rather than trusting the QC flip.
   `roll_exclusion_days: 2` in config is anchored to the wrong event as-is.
3. **[ESTABLISHED] Treasuries flip 18–36 days before expiry** (ZT/ZF ~28–36,
   ZN/ZB ~18–25 — consistent with their different termination rules) at only
   ~15–52% new-contract volume share: OI crosses before volume in Treasury
   rolls. Same consequence as above, mirrored.
4. **[ESTABLISHED] Calendar-gap magnitudes and carry regime:** median |gap|
   0.21–0.74% by symbol, max 1.38% (MNQ). Index gaps flipped sign with the
   rate regime — negative 2020–22 (dividends > rates), strongly positive
   2022+ (rates > dividends) — a clean cost-of-carry sanity check on the data.

## 3. The splice-artifact finding

Streamed vs refetched classification of all 220 splices
(`qc_roll_audit.csv`, `final` column; figure `rollaudit_refetch_verdict.png`):

| Class | Count | Meaning |
|---|---|---|
| clean | 151 | splice indistinguishable from a normal midnight bar |
| streaming_only_artifact | 24 | streamed feed leaked the gap; refetched series clean |
| **data_side_leak** | **40** | **refetched series carries ≥60% of the raw gap — bad adjustment factor in QC's data itself** |
| elevated_ambiguous | 5 | elevated but not gap-shaped (4 = the 2022-08-28 post-Jackson-Hole Sunday reopen, plausibly genuine market movement) |

Data-side leaks by symbol: **M2K 19/28, MYM 14/28, MNQ 4/28 (all ≤2020-06),
MES 3/28, Treasuries 0/108.** Full dated list in `qc_roll_audit.csv`
(`final == data_side_leak`); gaps injected range 0.13–1.08%, i.e. 10–100×
a typical midnight bar move.

Findings:

5. **[ESTABLISHED] A-004 is FALSIFIED as stated** for QC-provided continuous
   adjusted series: they are NOT artifact-free for indicator estimation.
   M2K and MYM adjusted series carry fake gap-sized jumps at roughly half of
   all rolls — in both streamed AND refetched (research-path) data. MES/MNQ
   are nearly clean (2–4 defects each); Treasuries are fully clean on the
   research path.
6. **[ESTABLISHED] The streamed and refetched series disagree in BOTH
   directions** (24 streaming-only leaks; also cases where streaming looked
   clean but refetch leaks, e.g. MES 2019-06-21). The two code paths apply
   factors independently; neither can be validated by the other. Any future
   streaming/live use gets its own audit (L-010).
7. **[PLAUSIBLE] Mechanism:** missing/incorrect entries in QC's factor files
   for the affected symbol-dates. Not investigated further — the research
   does not need the platform fixed; it needs a trustworthy series.

## 4. Decision (D-009) — how the research proceeds

**Build our own adjusted series** from mapped-raw per-contract segments
spliced with measured factors (`src/spread_research/roll_adjustment.py` was
scaffolded for exactly this):

- Splice factor per roll = pn/po from per-contract minute closes at the flip
  (this audit already measured and stored them for every roll; the method is
  reproducible inside QC Research for any refresh).
- Roll dates: OUR calendar schedule (index: ~8 days pre-expiry; Treasuries:
  month-end prior to delivery month), not QC's flip — aligning indicator
  splices with executable-liquidity reality.
- QC per-contract raw bars remain the data source (verified internally
  consistent); only QC's factor APPLICATION is bypassed.
- Until the own-splice constructor is validated (unit tests + a re-run of
  this audit's splice test on the constructed series), notebooks 02+ must not
  compute indicators across roll boundaries on QC-provided continuous series
  for M2K/MYM; MES/MNQ/Treasury series may be used with the 40 bad dates
  excluded as a stopgap.

## 5. Chronicle / provenance

Run 1 of the roll audit hit QC's free-tier log cap (10KB/backtest AND 10KB/
day) at 56 of 220 rolls (`qc_roll_audit_run1_partial.log` retained — it also
carries per-roll po/pn raw closes for 2019-06→2021-02). Output was rerouted
through custom chart series + summary statistics (log-cap-free); the refetch
sweeps used History probes with summary-statistic output. Free-tier end clip
(~2026-05-04) applies to all runs. Platform quirks feeding L-009/L-010 are
logged in `logs/issues_and_limitations.md`.

Original stub requirements not yet executed (deferred, tracked): z-score
behavior across rolls and adopted exclusion/warm-up windows — these are only
meaningful on the OWN-SPLICE constructed series (D-009) and move to the
notebook-02 preflight.
