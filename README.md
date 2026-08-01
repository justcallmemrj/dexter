# Dexter — Intraday Futures Relative-Value Research

**An intraday futures relative-value and spread-reversion research system inspired by
professional quantitative trading principles.**

Status: **RESEARCH PHASE — no trading algorithm exists and none is authorized.**

## What this is

A research-first framework for investigating temporary pricing dislocations:

- between related **equity-index futures** (MES–MNQ, MES–M2K, MES–MYM), and
- between different maturities of **U.S. Treasury futures** (ZT–ZF, ZF–ZN, ZT–ZN, ZN–ZB),

with the eventual goal — *if and only if the research validates it* — of an intraday,
market-neutral spread-reversion algorithm on QuantConnect LEAN, operating initially on
minute data.

This is **not** an HFT system. No claim of validated profitability is made anywhere in
this repository. The research may legitimately conclude "do not build this."

## What this is not (yet)

- No `QCAlgorithm` implementation exists. Building the integrated LEAN algorithm is
  gated behind an explicit human authorization token (see `CLAUDE.md`).
- No live-trading configuration, credentials, or deployment tooling will be created.
- Nothing here is investment advice.

## Repository layout

```
config/       Version-controlled research assumptions (YAML)
data/         raw / interim / processed market data + verified contract metadata
notebooks/    Numbered research notebooks (00–13), each answering specific questions
src/spread_research/  Reusable, unit-tested research library — notebooks call this
tests/        pytest unit / integration / regression tests
reports/      Audit and validation reports, figures, tables, machine-readable outputs
lean/         Reserved for future LEAN research/algorithm code (empty until authorized)
logs/         Research decision log, assumptions register, experiment log, issues
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest tests/          # verify the statistical core
```

Python ≥ 3.11 required. See `reports/00_repository_audit.md` for the environment audit
and current blockers (notably: futures market data is not yet available in this
environment — empirical notebooks are structured but blocked on data access).

## Research workflow

1. Every material assumption lives in `config/*.yaml`, not hard-coded in notebooks.
2. Every meaningful decision is logged in `logs/research_decisions.md`.
3. Every assumption is registered in `logs/assumptions_register.md` with a status
   (unverified / verified / falsified).
4. Every experiment is appended to `logs/experiment_log.csv`.
5. Notebooks import from `src/spread_research/` — no duplicated logic in notebooks.
6. Validation reports in `reports/validation/` are the formal record; the final
   go / revise / no-go recommendation will live in
   `reports/validation/99_final_recommendation.md` once the research is complete.
