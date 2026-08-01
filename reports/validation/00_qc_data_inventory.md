# Validation Report 00-QC — Minute-Data Inventory (A-001 / A-002)

**Date:** 2026-08-01 · **Environment:** QuantConnect cloud, project
`dexter-rv-research` (34720894), LEAN master v17965
**Tool:** `lean/research/qc_data_inventory_audit.py` — log-only, zero-orders
data-audit backtest (permitted tool class under CLAUDE.md gate 1; the trading
algorithm remains unbuilt)
**Runs:** inventory-audit-1 (2019-04 start, 250s), MYM market diagnostic, MYM
start probe, **inventory-audit-2 (research window, 282s — canonical)**
**Machine-readable:** `reports/machine_readable/qc_data_inventory.json`

## Method

A QC backtest subscribed all 8 instruments as continuous futures at
Resolution.MINUTE with the exact research settings from
`config/research_config.yaml` (OpenInterest mapping, BackwardsRatio
normalization, `fill_forward=False`, extended hours) over the research window
(start 2019-06-01), counting delivered bars, first/last timestamps, per-year
totals, and continuous-mapping change (roll) counts.

## Results (canonical run: research window 2019-06-01 → clip)

| Sym | First bar (ET) | Last bar | Minute bars | Rolls/yr |
|---|---|---|---|---|
| MES | 2019-06-02 18:01 | 2026-05-04 | 2,427,063 | 3,4,4,4,4,4,4,1 |
| MNQ | 2019-06-02 18:01 | 2026-05-04 | 2,429,777 | 3,4,4,4,4,4,4,1 |
| M2K | 2019-06-02 18:01 | 2026-05-04 | 2,279,362 | 3,4,4,4,4,4,4,1 |
| MYM | 2019-06-02 18:01 | 2026-05-04 | 2,310,079 | 3,4,4,4,4,4,4,1 |
| ZT | 2019-06-02 17:01 | 2026-05-03 | 1,916,812 | 2,4,4,4,4,4,4,1 |
| ZF | 2019-06-02 17:01 | 2026-05-03 | 2,194,770 | 2,4,4,4,4,4,4,1 |
| ZN | 2019-06-02 17:01 | 2026-05-03 | 2,277,601 | 2,4,4,4,4,4,4,1 |
| ZB | 2019-06-02 17:01 | 2026-05-03 | 2,138,043 | 2,4,4,4,4,4,4,1 |

## Findings

1. **[ESTABLISHED] A-001 VERIFIED:** all four index micros have continuous
   minute data across the full research window — every instrument emits from
   the first session of the window (Sunday 2019-06-02 evening open) through
   the free-tier clip. A supplemental run from 2019-04-01 confirms
   MES/MNQ/M2K data begins at the 2019-05-06 launch itself (first bars
   2019-05-05 18:01–18:04 ET).
2. **[ESTABLISHED] A-002 VERIFIED (within window):** all four Treasury futures
   have continuous minute data across the research window. Pre-2019 depth was
   not probed (research starts 2019-06-01; QC is known to serve futures minute
   data much deeper — e.g. ES to 1997 — if regime-extension studies ever need it).
3. **[ESTABLISHED] Roll cadence is exactly quarterly** under OpenInterest
   mapping: 4 mapping changes per full calendar year for every symbol, no
   gaps, no extras (partial years at window edges count 2–3 as expected).
4. **[ESTABLISHED] Free-tier end clip:** requested end 2026-07-31, delivered
   through 2026-05-03/04 (~3 months before today). Must be disclosed in every
   result that uses cloud data.
5. **[ESTABLISHED] Liquidity regime visible in traded-minute counts:** ZT
   ~236–245k bars/yr in 2020–21 vs ~281–307k from 2022 on (rates-vol regime).
   M2K and MYM run ~4–6% fewer traded minutes than MES/MNQ. Relevant to
   session filters and capacity assumptions (A-011, A-013).
6. **[ESTABLISHED] MYM platform quirk (L-009):** QC serves MYM minute data
   under `Market.CBOT` only (`Market.CME` returns nothing), the data is
   complete from launch (History probes: 20,521 bars in the 21 days from
   2019-05-06), but a **continuous-contract subscription whose start date
   precedes the 2019-05-06 launch never initializes** — zero bars for the
   entire run (observed twice). The other three micros tolerate pre-launch
   starts. Consequence: any QC run touching MYM must start 2019-05-06 or
   later; the research window (2019-06-01) satisfies this automatically.

## Consequences

- Notebooks 02–13's QC data-loading cells can rely on minute continuous series
  for all 8 instruments from 2019-06-01, with the clip disclosed.
- Notebook 01 roll audit has confirmed raw material: quarterly mapping changes
  are present and countable; next step extracts exact roll dates and price-gap
  behavior (including the ~0.05% adjusted-series step risk around rolls).
- MES–MYM (top screening priority) is fully data-supported at minute
  resolution — the daily-preview structure finding can now be tested intraday.
