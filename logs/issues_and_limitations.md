# Known Issues and Limitations

## Open

- **L-001 (blocker):** No futures market data reachable from this research container.
  QuantConnect data requires QC Research / LEAN CLI + subscription; the container's
  network policy returns 403 for market-data hosts (Yahoo Finance) and for
  cmegroup.com / quantconnect.com docs. All empirical notebooks (02–13) are
  structured but unexecuted. **Resolution path:** run notebooks inside QuantConnect
  Research, or configure LEAN CLI with data locally.
- **L-002:** Contract specifications verified only against secondary sources
  (assumption A-003). Re-verify on CME before execution use.
- **L-003:** Commission and spread assumptions are placeholders (A-007, A-008).
- **L-004:** Minute-bar execution simulation cannot model queue position, intrabar
  adverse selection, or partial fills. Mitigated (not solved) by the 'stressed'
  cost acceptance rule; second/tick-level evaluation is a later phase.
- **L-005:** Micro contracts launched 2019-05-06 → at most ~7 years of history, all
  within one broad monetary era plus COVID. Regime coverage is structurally thin;
  parent E-mini proxy studies (clearly labeled) partially mitigate for the
  relationship analysis but never for execution realism.
- **L-006:** Treasury futures are delivery-settled with CTD dynamics; price-based
  hedge ratios only approximate DV01 neutrality (A-012).
- **L-007 (research caution, found during framework testing):** hedge-ratio
  estimation error contaminates the constructed residual with a slow random-walk
  component of magnitude ≈ (beta_hat − beta) × price_level, inflating measured
  half-life; the contamination ratio is INDEPENDENT of the residual's own
  volatility (it is price_level / (σ_x,window · √n_eff), with n_eff shrunk by
  residual autocorrelation). Demonstrated on synthetic data in
  `tests/unit/test_stationarity_mean_reversion.py::test_residual_pipeline_end_to_end`.
  Consequence: notebooks 04/05 must quantify this on real data — half-life
  estimates from noisy hedges are biased UP, and pair viability must be judged
  net of it.

## Closed

(none yet)
