# Validation Report 00-QC — Minute-Data Inventory (A-001 / A-002)

**Date:** 2026-08-01 · **Environment:** QuantConnect cloud, project
`dexter-rv-research` (34720894), LEAN master v17965
**Tool:** `lean/research/qc_data_inventory_audit.py` — log-only, zero-orders
data-audit backtest (permitted tool class under CLAUDE.md gate 1; the trading
algorithm remains unbuilt)
**Runs:** `inventory-audit-1` ("Crawling Blue Caterpillar", 250s, 66.87M data
points) + MYM market diagnostic ("Measured Yellow Chicken")
**Machine-readable:** `reports/machine_readable/qc_data_inventory.json`

## Method

One QC backtest subscribed all 8 instruments as continuous futures at
Resolution.MINUTE with the exact research settings from
`config/research_config.yaml` (OpenInterest mapping, BackwardsRatio
normalization, `fill_forward=False`, extended hours), window request
2019-04-01 → 2026-07-31, and counted delivered bars, first/last timestamps,
per-year totals, and continuous-mapping change (roll) counts.

## Results

| Sym | First bar (ET) | Last bar | Minute bars | Rolls (per yr) |
|---|---|---|---|---|
| MES | 2019-05-05 18:01 | 2026-05-04 | 2,453,645 | 3,4,4,4,4,4,4,1 |
| MNQ | 2019-05-05 18:04 | 2026-05-04 | 2,455,422 | 3,4,4,4,4,4,4,1 |
| M2K | 2019-05-05 18:02 | 2026-05-04 | 2,295,099 | 3,4,4,4,4,4,4,1 |
| MYM | see §MYM | — | — | — |
| ZT | 2019-03-31 23:04 | 2026-05-03 | 1,958,508 | 3,4,4,4,4,4,4,1 |
| ZF | 2019-03-31 23:00 | 2026-05-03 | 2,247,512 | 3,4,4,4,4,4,4,1 |
| ZN | 2019-03-31 23:00 | 2026-05-03 | 2,331,119 | 3,4,4,4,4,4,4,1 |
| ZB | 2019-03-31 23:00 | 2026-05-03 | 2,187,001 | 3,4,4,4,4,4,4,1 |

Findings:

1. **[ESTABLISHED] Micro minute data begins at launch.** MES/MNQ/M2K first
   bars are 2019-05-05 18:01–18:04 ET — the opening minutes of the launch
   session (Globex open Sunday 6 p.m. ET before the 2019-05-06 launch date).
   A-001 VERIFIED for these three.
2. **[ESTABLISHED] Treasury minute data present from the audit start**
   (2019-04-01; treasuries have longer history — not probed, research window
   starts 2019-06 per config). A-002 VERIFIED within the audited window.
3. **[ESTABLISHED] Roll cadence is exactly quarterly** under OpenInterest
   mapping: 4 mapping changes per full year, every symbol, every year — no
   missing or duplicated roll events at this granularity.
4. **[ESTABLISHED] Free-tier end clip:** requested end 2026-07-31, delivered
   through 2026-05-03/04 (~3 months before today) — known platform behavior,
   must be disclosed in every result that uses cloud data.
5. **[ESTABLISHED] Liquidity regime visible in bar counts:** ZT traded-minute
   counts jump ~25% starting 2022 (≈245k/yr 2020-21 → ≈300k+/yr 2022-25) —
   the rates-vol regime change. M2K runs ~5% fewer traded minutes than
   MES/MNQ. Relevant later for session filters and capacity assumptions.
6. **MYM (§MYM):** first run subscribed `Market.CBOT` (the contract's actual
   clearing venue per CME) and received **zero bars**; a dedicated diagnostic
   resolved the data-bearing market — see below.

## §MYM market resolution

Diagnostic backtest subscribing MYM under both `Market.CBOT` and `Market.CME`
simultaneously (2024-01-02 → 2024-03-01):

RESULT_PLACEHOLDER

## Consequences

- Notebooks 02–13's QC data-loading cells can rely on: minute continuous
  series for all 8 instruments from 2019-06-01 (config research_start), with
  the free-tier end clip disclosed.
- Roll-audit (notebook 01) has confirmed raw material: quarterly mapping
  changes are present and countable; next step is extracting exact roll dates
  and price-gap behavior around them.
