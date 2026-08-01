# Validation Report 01 — Data and Roll Validation

**Status: NOT STARTED — BLOCKED ON DATA (L-001).**

This report is the required output of the notebook-01 roll audit (mandate §8.4). It
will contain, per instrument:

- Roll-event inventory (all mapping changes in the research window).
- Raw vs adjusted price behavior around each roll, with figures in
  `reports/figures/`.
- Artificial-return-jump findings (`roll_adjustment.roll_gap_report` artifact flags).
- Z-score behavior across rolls and the excess extreme-z rate attributable to rolls.
- Adopted values for pre-roll entry exclusion, post-roll warm-up, and the
  flat-before-roll rule — each logged as a decision in
  `logs/research_decisions.md`.
- The verdict on assumption A-004 (continuous-for-indicators / mapped-for-execution).

No content may be added to this report except from executed analysis on real data.
