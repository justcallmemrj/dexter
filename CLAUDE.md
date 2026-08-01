# CLAUDE.md — Project rules for AI-assisted work on this repository

## Project identity

Research-first intraday relative-value futures system (equity-index micros and U.S.
Treasury futures) targeting QuantConnect LEAN. Correct project description:
"An intraday futures relative-value and spread-reversion research system inspired by
professional quantitative trading principles." It is NOT institutional HFT and must
never be described as such.

## Hard gates — do not violate

1. **The complete integrated QuantConnect trading algorithm must NOT be built until a
   human explicitly writes the exact authorization token: `PROCEED TO LEAN BUILD`.**
   Until then: research utilities, statistical modules, test harnesses, notebooks,
   data-audit tools, and reporting infrastructure only. `lean/algorithm/` stays empty.
2. **No live trading.** Never create brokerage credentials, live-order configuration,
   or live deployment. Research, backtesting, simulation, paper-trading prep only.
3. **No fabricated profitability.** Never represent the strategy as validated or
   profitable. A single profitable backtest, one lucky parameter set, ignored costs,
   perfect fills, or continuous-contract artifacts do not constitute evidence.
4. **No forced positive conclusion.** Legitimate outcomes include: proceed, revise,
   collect better data, drop pairs, change holding period, change hedge method, reject.
5. **Universe is locked**: MES, MNQ, M2K, MYM index micros; ZT, ZF, ZN, ZB Treasuries
   (UB only after independent validation). No cross-asset (index-vs-Treasury) spreads
   in Version 1. No big/micro same-index spreads (ES–MES etc.). No other asset classes
   without explicit user approval.
6. **No machine learning in Version 1** unless a specific research finding justifies it
   and the justification is logged.
7. **Parent E-mini data used as proxy for short Micro history must be clearly labeled,
   never silently merged, and never treated as executable Micro prices.**

## Working conventions

- Material assumptions go in `config/*.yaml`; do not scatter constants in notebooks.
- Notebooks call functions in `src/spread_research/`; keep logic out of notebooks.
- Log decisions in `logs/research_decisions.md`, assumptions in
  `logs/assumptions_register.md`, experiments in `logs/experiment_log.csv`.
- Data that fails validation is flagged, never silently filled.
- Continuous adjusted series → indicators/relationships only. Mapped raw contracts →
  executable prices and order simulation. This split is a working hypothesis until
  roll-artifact testing (notebook 01) confirms it.
- Random seeds are set and recorded in config whenever randomness is used.
- Run `pytest tests/` before committing changes to `src/`.
- Evidence discipline: tag non-trivial market-behavior claims as [ESTABLISHED],
  [PLAUSIBLE], or [SPECULATIVE] in research documents.

## Environment notes

- This container has no QuantConnect data and no LEAN CLI credentials; the network
  policy blocks market-data downloads (see `reports/00_repository_audit.md`).
  Empirical notebooks are therefore structured-but-blocked until run inside
  QuantConnect Research (or LEAN CLI with data) — do not fake their results.
