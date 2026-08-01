# Preview Report — Daily-Resolution Pair Relationship Screen

**Date:** 2026-08-01 · **Tier:** screening/preview (D-007) · **Experiments:** EXP-003 (extended window), EXP-004 (research window); EXP-001/002 are the identical first run before tier labels were renamed — metrics unchanged, superseded for reference purposes.
**Data:** yfinance front-month daily series (assumption A-015 — roll methodology undocumented; screening evidence only)
**Code:** `scripts/daily_preview_screen.py` → `src/spread_research/preview_screen.py` (unit-tested incl. planted-structure and random-walk negative controls)

---

## 1. What this screen can and cannot say

**Can:** characterize daily-horizon relationship structure of the 7 locked pairs —
cointegration over multi-year windows, static-residual stationarity, hedge-ratio
stability/regime breaks — and order the minute-resolution research effort.

**Cannot:** test the actual strategy hypotheses A-006/A-009 (INTRADAY mean
reversion of hedged residuals with z-score lookbacks of ~1 RTH day). Intraday
reversion is invisible in daily bars. **No pair is validated or rejected by this
screen.** No trading was simulated and no cost model was applied.

## 2. Data used

12 symbols (4 micros from 2019-05, 4 treasuries + 4 parent proxies from 2010;
RTY from its 2017-07 launch), canonical schema in `data/processed/`, validation
battery run (`reports/machine_readable/preview_data_quality.csv`). Notable flags,
all retained-never-filled:

- Real events correctly flagged: COVID crash days (2020-03-12/16/24), SVB
  2-year repricing (2023-03-13), Hurricane Sandy closure gap (2012-10-29/30).
- **Suspected provider artifact:** ZB 2015-03-23 log-return +0.099 (a ~10% one-day
  move in the 30-year future did not happen) — consistent with a Yahoo bad print
  or roll splice (logged L-008). One more reason this tier is screening-only.

## 3. Results

Full table: `reports/machine_readable/daily_pair_screen.csv`. Research window =
2019-06 → 2026-07 (n≈1,804 daily bars); extended = 2010 → 2026-07.

| Pair | Window | Ret corr | EG p | Static resid verdict | Static HL (d) | Tier |
|---|---|---|---|---|---|---|
| **MES_MYM** | research | 0.94 | **0.004** | **stationary** | **40** | **daily_structure_present** |
| MES_MNQ | research | 0.93 | 0.28 | non_stationary | — | no_daily_structure |
| MES_M2K | research | 0.87 | 0.44 | non_stationary | — | no_daily_structure |
| ZT_ZF | research | 0.91 | 0.69 | non_stationary | — | no_daily_structure |
| ZF_ZN | research | 0.94 | 0.63 | non_stationary | — | no_daily_structure |
| ZT_ZN | research | 0.81 | 0.68 | non_stationary | — | no_daily_structure |
| ZN_ZB | research | 0.91 | 0.64 | non_stationary | — | no_daily_structure |
| ZT_ZF | extended | 0.88 | 0.09 | stationary_marginal | 178 | no_daily_structure (beta shift +70%) |
| ZT_ZN | extended | 0.73 | 0.22 | non_stationary | — | no_daily_structure (beta shift +111%) |
| ES_NQ (proxy) | extended | 0.93 | 0.25 | non_stationary | — | no_daily_structure |
| ES_RTY (proxy) | extended | 0.87 | 0.32 | non_stationary | — | no_daily_structure |
| ES_YM (proxy) | extended | 0.96 | 0.29 | non_stationary | — | no_daily_structure |

Figures: `reports/figures/preview_MES_MYM_residual.png`,
`preview_MES_MNQ_residual.png`, `preview_ZT_ZN_rolling_beta.png`.

## 4. Findings

1. **[ESTABLISHED at daily horizon] Only MES–MYM shows daily-horizon
   cointegration structure** in the research window (EG p=0.004, stationary
   residual, half-life ≈ 40 trading days, ±5% oscillation band). S&P-vs-Dow is
   the only pair whose relative price had a stable long-run anchor over 2019-26.
2. **[ESTABLISHED at daily horizon] Every other pair's relative price trended
   secularly** across 2019-26 (tech supercycle for MNQ, small-cap underperformance
   for M2K, the 2022 rate-regime repricing for all Treasury pairs). Any strategy
   variant relying on a long-run level anchor (long z-lookbacks, static hedges,
   multi-week holds) is dead on arrival for these pairs. This **hardens the
   existing design choice** of short z-score lookbacks (~1 RTH day) and short
   max holding (≤2 days): the strategy must re-anchor its mean quickly.
3. **[ESTABLISHED at daily horizon] Treasury hedge ratios are regime-driven, not
   parameters.** ZT–ZN 126d rolling beta ranges ~0.0→0.4 over 2010-26 (figure),
   recent-vs-full shifts of +70–111%. For the minute program, adaptive hedging
   (short-lookback rolling / Kalman / DV01-refreshed) is **mandatory** for
   Treasury pairs; notebook 04 should treat static hedges as a control, not a
   candidate.
4. **[ESTABLISHED on this data] L-007 confirmed on real data:** rolling-hedge
   residual half-lives are inflated by hedge-estimation noise by 1–2 orders of
   magnitude vs static-hedge residuals (e.g. MES_MYM 40d static vs 932d rolling;
   MES_MNQ 106d vs 2,849d). At minute resolution notebooks 04/05 must quantify
   this contamination before interpreting any half-life.
5. **[SPECULATIVE] Prioritization hypothesis for the minute program:** MES–MYM
   first (structure at every tested horizon), then MES–MNQ (highest co-movement,
   cleanest microstructure), then Treasury pairs with adaptive hedges from the
   start. Small-cap M2K last among index pairs (weakest co-movement, 0.87).

## 5. What changes in the research plan

- Notebook 02/03 (minute-level relationships) proceed for **all 7 pairs** — the
  intraday hypothesis is untested by this screen — but in the priority order
  above, and notebook 04's hedge-method grid for Treasuries drops long-lookback
  static hedges from candidate to control.
- A-015 verification path unchanged: cross-check these daily conclusions against
  QC continuous series once minute data is available.

## 6. Blocking dependency unchanged

Minute-resolution history (the primary research resolution) still requires the
QuantConnect Research environment or a licensed data drop (L-001, partial).
