# Assumptions Register

Status values: UNVERIFIED (default) / VERIFIED (evidence in repo) / PARTIAL /
FALSIFIED (must not be relied upon).

| ID | Assumption | Category | Status | Evidence / verification path | Risk if wrong |
|----|-----------|----------|--------|------------------------------|---------------|
| A-001 | Micro index futures (MES/MNQ/M2K/MYM) have usable minute-level history from ~2019-06 in QuantConnect | data | UNVERIFIED | Notebook 00 in QC Research | Research window shrinks; parent-proxy protocol needed |
| A-002 | Treasury futures (ZT/ZF/ZN/ZB) have long minute-level history in QuantConnect | data | UNVERIFIED | Notebook 00 in QC Research | Same as A-001 |
| A-003 | Contract specs in config/instruments.yaml are correct | specs | PARTIAL | Cross-checked 3+ secondary sources 2026-08-01; CME primary source unreachable (HTTP 403). ZF face-value contradiction in one source resolved by targeted search | Wrong tick values corrupt every cost and PnL number |
| A-004 | Continuous (OpenInterest-mapped, ratio-adjusted) series are artifact-free enough for indicator estimation | methodology | UNVERIFIED | Notebook 01 roll audit | Roll gaps create fake mean-reversion signals |
| A-005 | Mapped raw contract prices are executable at bar close +/- slippage model | execution | UNVERIFIED | Notebook 07; ultimately quote data | Overstated fill quality → fake edge |
| A-006 | Index pair residuals (MES-MNQ etc.) exhibit intraday mean reversion after hedging | signal | UNVERIFIED | Notebooks 02, 05 | Core hypothesis fails → no-go for index book |
| A-007 | Commission placeholders in cost_assumptions.yaml (~$0.62 micro, ~$0.85 treasury per side) are realistic retail all-in | costs | UNVERIFIED | Broker fee schedule confirmation | Understated costs inflate edge |
| A-008 | 1-tick top-of-book spread during RTH for all 8 instruments | costs | UNVERIFIED | Quote-data audit, notebook 07 | Wider real spreads kill marginal edges |
| A-009 | Treasury pair residuals mean-revert at intraday horizon in DV01/vol-hedged space | signal | UNVERIFIED | Notebooks 03, 05 | No-go for treasury book |
| A-010 | Hedge ratios drift slowly enough that a 1-week lookback refit daily is adequate | methodology | UNVERIFIED | Notebook 04 stability analysis | Stale hedges accumulate directional exposure |
| A-011 | Micro contract liquidity is sufficient for 1–10 contract clips without moving the book | capacity | UNVERIFIED | Volume/depth audit, notebook 07 | Slippage model too optimistic |
| A-012 | CTD switches / delivery-cycle effects in ZB/ZN do not dominate the residual at intraday horizon | methodology | UNVERIFIED | Notebook 03; roll-window behavior in notebook 01 | Structural jumps mistaken for tradable dislocations |
| A-013 | RTH-only trading (08:30–15:00 CT) captures the bulk of exploitable signal | scope | UNVERIFIED | Intraday seasonality sections, notebooks 02/03 | Missed edge or wrong session model |
| A-014 | No look-ahead: all signals computable from data available at decision bar | methodology | VERIFIED (by construction) | Enforced in src/spread_research/signals.py (shifted windows) + unit tests | Silent leakage → inflated results |
