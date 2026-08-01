# Report 00 — Repository and Environment Audit

**Date:** 2026-08-01
**Auditor:** Claude (research framework setup session)
**Scope:** Pre-research inspection required before any file creation (project
mandate §5). This report was drafted from live inspection, then committed together
with the initial framework scaffold.

---

## 1. Repository state at inspection

| Item | Finding |
|---|---|
| Repository | `justcallmemrj/dexter`, cloned at `/home/user/dexter` |
| Commits | **None** — empty repository, no history on local or remote |
| Branch | `claude/futures-relative-value-research-fpv6m3` (designated work branch, checked out) |
| Existing Python / LEAN / notebook / data / config / test / report files | **None** |
| Classification | **Empty greenfield repository** — not a QuantConnect project, no prior algorithm, nothing to preserve or migrate |

No files were deleted or overwritten; there were none to delete.

## 2. Environment

| Item | Finding |
|---|---|
| OS | Linux 6.18.5 (ephemeral managed research container) |
| Python | 3.11.15 |
| pip | 24.0 (functional; PyPI reachable through proxy) |
| Docker | Available (`/usr/bin/docker`) — LEAN Docker images *could* be pulled if the registry is reachable (untested) |
| LEAN CLI | **Not installed** |
| Jupyter | Not preinstalled; installed during setup |
| Local QuantConnect data | **None** (`~/.lean`, no data directory anywhere) |
| QuantConnect Research access | **None** — no QC credentials in environment |

### Packages installed during setup (recorded versions)

numpy 2.4.6 · pandas 3.0.5 · scipy 1.17.1 · statsmodels 0.14.6 ·
scikit-learn 1.9.0 · matplotlib 3.11.1 · PyYAML 6.0.1 · pytest 9.1.1 ·
nbformat / nbclient / ipykernel (latest) · yfinance 1.5.2 (installed, **unusable — see §3**)

`requirements.txt` and `pyproject.toml` pin these as floors.

## 3. Network / data access probes (all performed live)

| Probe | Result | Consequence |
|---|---|---|
| `pip install` (PyPI) | ✅ works | Tooling installable |
| Yahoo Finance via yfinance (`ES=F`, `ZN=F`, `MES=F` daily) | ❌ proxy `CONNECT` 403 | No free proxy market data; even coarse daily relationship checks impossible here |
| `cmegroup.com` contract-spec pages (direct fetch) | ❌ HTTP 403 | Primary-source spec verification blocked |
| `quantconnect.com` docs (direct fetch) | ❌ HTTP 403 | Continuous-futures mapping docs unreadable directly |
| Web search (summarized results) | ✅ works | Used for multi-source contract-spec cross-verification (see D-003) |
| GitHub (git push/pull via session proxy) | ✅ works | Version control functional |

## 4. Data availability conclusion

**There is no futures market data available in this environment, at any resolution.**
This is the single controlling blocker (logged as **L-001**). Everything empirical —
data inventory (§8.1 of the mandate), roll audits, pair relationship analysis,
hedge-ratio comparison, signal analysis, cost calibration, backtests, walk-forward,
stress testing — requires one of:

1. **QuantConnect Research environment** (recommended): open this repository's
   notebooks in QC Research, where `qb = QuantBook()` provides minute/second/tick
   futures history for all eight instruments. The notebooks are written so their
   data-loading cell is the only QC-specific piece.
2. **LEAN CLI + local data**: install `lean` CLI (Docker is present), log in, and
   download the required futures data (paid subscription).
3. **Alternative licensed data drop** into `data/raw/` matching the documented schema
   (`src/spread_research/data_loader.py`).

## 5. What was built in this session instead

Because assumptions must be testable the moment data is available, this session
delivered the full *non-empirical* layer:

- Directory structure per mandate §6 (research / reusable code / tests / reports /
  future-LEAN separation).
- `config/*.yaml` — all material assumptions externalized and version-controlled.
- `src/spread_research/` — unit-tested statistical core (hedge ratios incl. Kalman,
  stationarity, half-life, signals with look-ahead protection, conservative cost
  model, vectorized spread backtester, walk-forward splitter, metrics, validation).
- `tests/` — synthetic-data unit tests with known-answer checks and negative
  controls (random walks must *not* pass stationarity; uncointegrated pairs must
  *not* look tradable).
- Notebooks 00–13 — 00 executed here (environment audit); 01 populated with
  verified specs and roll-audit methodology; 02–13 fully structured with purpose,
  research questions, methodology and module wiring, explicitly marked
  **BLOCKED-ON-DATA** with no fabricated results.
- Logs: decision log (D-001…D-006), assumptions register (A-001…A-014), experiment
  log, issues/limitations.

## 6. Code quality of existing project

Not applicable — repository was empty. All code in this repo originates from this
session and is covered by the test suite (`pytest tests/`).

## 7. Risks and blockers

| # | Risk / blocker | Severity | Mitigation |
|---|---|---|---|
| 1 | No market data in container (L-001) | **Blocker** for empirical phases | Run notebooks in QC Research; framework designed for zero-redesign handoff |
| 2 | Contract specs from secondary sources only (A-003/L-002) | Medium | Multi-source agreement achieved; re-verify on CME before execution use |
| 3 | Micro history only from 2019-05 (L-005) | Medium | Parent E-mini proxy protocol (labeled, never merged, never executable) |
| 4 | Minute bars hide microstructure (L-004) | Medium | 'Stressed' cost acceptance rule; later second/tick evaluation |
| 5 | Multiple-testing risk: 7 pairs × parameter grids | High (statistical) | Trial counting mandated in `research_config.yaml`; plateau-over-peak selection; walk-forward acceptance rules |
| 6 | Treasury CTD/delivery dynamics (L-006) | Medium | DV01-approx hedging treated as candidate, not default; roll/delivery windows excluded pending notebook 01 |

## 8. Recommended next actions (ordered)

1. Open `notebooks/00_environment_and_data_audit.ipynb` inside **QuantConnect
   Research** and execute the data-inventory section (A-001/A-002 verification).
2. Execute notebook 01 roll audit → produce
   `reports/validation/01_data_and_roll_validation.md` with real roll evidence.
3. Proceed through notebooks 02–07 in order; log every experiment.
4. Confirm commissions/spreads with a real broker fee schedule (A-007/A-008).
5. Only after notebooks 08–13 and the validation reports: issue the formal
   go / revise / no-go recommendation. **The LEAN algorithm remains prohibited
   until the user writes `PROCEED TO LEAN BUILD`.**
