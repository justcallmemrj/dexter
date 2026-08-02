# Validation Report 02 — Minute-Level Index Pair Relationships (A-006)

**Date:** 2026-08-01 · **Environment:** QC cloud project `dexter-rv-research`
(34720894), free tier · **Pre-registration:** D-010 (+ amendments A1, A2), all
written before the corresponding results existed
**Code:** `src/spread_research/{intraday_reversion,pair_minute_report,calendars,
roll_adjustment}.py`, driven by `lean/research/qc_pair_minute_analysis.py`
**Pairs:** MES–MYM (§1-§10, pre-registered D-010) · MES–MNQ (§11,
pre-registered D-012)
**Runs:** MES–MYM: gate "Emotional Fluorescent Orange Goat" → "Geeky Brown
Flamingo" → final **"Alert Magenta Rabbit"**. MES–MNQ: **"Virtual Asparagus
Pelican"** (single run; the pipeline was already validated).
**Machine-readable:** `reports/machine_readable/nb02_<PAIR>_*.csv`,
`qc_pair_minute_<PAIR>.json`
**Figures:** `nb02_<PAIR>_{conditional_reversion,variance_ratio,roll_preflight}.png`
(regenerate: `python scripts/nb02_figures.py --pair MES_MNQ`)

---

## 1. Verdict

**A-006 is FALSIFIED for BOTH index pairs tested so far — MES–MYM and MES–MNQ —
at intraday horizon.** Both returned the same answer under the same frozen
protocol, and in both the only statistically significant cells point at
*continuation*, not reversion. §1-§10 report MES–MYM; §11 reports MES–MNQ.

### MES–MYM

**A-006 is FALSIFIED for MES–MYM at intraday horizon.** The hedged residual
does not mean-revert over 5–120 minute holding periods on the own-splice
constructed minute series. Where the pre-registered statistic is significant it
has the **opposite** sign — the dislocation continues rather than reverts — and
even that effect is smaller than a round-trip cost.

This closes MES–MYM as an intraday reversion candidate. It does not close the
pair at longer horizons (see §7), and it says nothing yet about the other six
pairs.

## 2. Data and acceptance gate

Own-splice constructed series (D-009) for **MES** (`Market.CME`) and **MYM**
(`Market.CBOT`, per L-009), index roll rule expiry−8d at 10:30 ET, CME holiday
list passed to the schedule generator.

| | MES | MYM |
|---|---|---|
| Rolls built | 28 | 28 |
| `splice_audit` flags | **0** | **1** |
| Factors by median ratio at full 390-bar overlap | 28/28 | 28/28 |

Aligned RTH panel: **676,560 minute bars, 1,744 sessions**, median 390 bars per
session, 2019-06-03 → 2026-04-24 (free-tier end clip ~2026-05-04 applies to
every result in this report). 7,740 MES bars (1.1%) had no simultaneous MYM
print and were dropped, never filled — MYM is the thinner leg.

The single flag, **MYMZ19→MYMH20 on 2019-12-12**, was adjudicated NOT an
artifact and the reasoning is a bound, not a judgement call: a wrong splice
factor can inject at most the calendar gap it was removing, that gap is
**1.08 bp**, and the observed boundary return is **8.15 bp** — 7.5× larger than
the mechanism can produce. See D-010 amendment A1. Retained as a watch item in
`logs/issues_and_limitations.md` (L-012) because a single bad print at the
boundary minute would look identical.

**[ESTABLISHED] The constructor holds up on a second and third symbol.** MES is
clean at every roll and MYM at 27 of 28, against QC's own MYM series carrying
bad factors at 14 of the same 28 (validation report 01 §3). The measured factor
gaps reproduce the carry-regime sign flip on both legs (negative through 2021,
positive from 2022) — the same independent sanity check as the M2K/ZN acceptance.

## 3. Primary statistic — conditional forward reversion (D-010, amended A2)

Event = first crossing of |z| ≥ entry_z, z from `rolling_zscore(residual, 390)`
shifted. Entry at the close of bar t+1, exit at t+1+k, both inside the signal's
own session. Outcome is the **position's P&L** with the hedge ratio frozen at
the signal bar. Inference is session-clustered across 1,744 sessions.

Session-mean outcome in bps (positive = fading the dislocation pays), with
session-clustered t, at entry_z = 2.0:

| Horizon | S1 (β=1) | S2 (rolling OLS) | S3 (static β, look-ahead) |
|---|---|---|---|
| 5 | −0.48 (t −4.08) | −0.37 (t −2.88) | −0.79 (t −5.34) |
| 15 | −0.98 (t −5.13) | −0.85 (t −4.00) | −1.24 (t −5.04) |
| 30 | −1.25 (t −4.79) | −1.22 (t −4.36) | −1.04 (t −3.09) |
| 60 | −1.11 (t −3.30) | −0.90 (t −2.39) | −0.57 (t −1.30) |
| 120 | −0.74 (t −1.81) | −0.32 (t −0.67) | +0.97 (t +1.79) |

Across the full 60-cell grid (3 specs × 4 entry thresholds × 5 horizons):

- **Zero cells** in S1 or S2 are positive with |t| ≥ 3. D-010 criterion (a)
  fails outright, so REVERSION PRESENT is unreachable.
- 26 of 60 cells reach |t| ≥ 3; **24 of those 26 are negative**. The
  significant, reproducible finding is **continuation**, concentrated at
  entry_z 1.5–2.0 where the sample is largest.
- S1 and S2 agree in sign, so the "sign disagreement" branch of the NO
  REVERSION rule is not what decides this — the direct failure of (a) is.
- The only two positive cells with |t| ≥ 3 are in **S3**, the full-sample
  static-β spec that is look-ahead contaminated by construction and was
  pre-declared a diagnostic upper bound, never evidence.

**[ESTABLISHED] Fading a 1.5–2.0 sigma MES–MYM dislocation lost money over
2019-2026, at every horizon from 5 to 120 minutes, in both look-ahead-safe
specifications.** Figure: `reports/figures/nb02_MES_MYM_conditional_reversion.png` —
every significant marker in S1 and S2 sits below zero, and the only positive
significant markers are in the look-ahead spec, inside the cost band.

## 4. Supporting statistic — variance ratios, and why VR < 1 is not evidence here

VR(q) at 1-minute base sampling (VR < 1 = mean reversion, VR = 1 = random walk):

| q | Residual S1 | Residual S2 | MES alone | MYM alone |
|---|---|---|---|---|
| 2 | 0.887 | 0.906 | 0.989 | 0.990 |
| 15 | 0.795 | 0.847 | 0.942 | 0.935 |
| 30 | 0.756 | 0.817 | 0.865 | 0.866 |
| 60 | 0.747 | 0.846 | 0.857 | 0.848 |
| 120 | 0.749 | 0.830 | 0.828 | 0.816 |

Taken alone, "residual VR ≈ 0.75, bootstrap p < 0.001" reads like strong
reversion. Both pre-registered guards say otherwise:

1. **Shape.** The residual curve stops declining after q = 30:
   VR(120)/VR(30) = **0.991**. That is the flat-floor signature of additive
   microstructure noise, not the ~1/q decay of a mean-reverting process. (The
   module's test suite pins this discriminator against a planted AR(1), which
   decays to a ratio of 0.66, and a planted bid-ask bounce, which flattens
   above 0.85.)
2. **Base sampling.** Bounce variance does not scale with the sampling
   interval, so coarsening the bars must walk a bounce-driven VR back toward 1
   — and it does. Residual VR(q=2) rises 0.887 → 0.964 → 0.950 going from 1- to
   5- to 15-minute bars, and at 5-minute base sampling **VR(30) = 0.993 and
   VR(60) = 0.982** — indistinguishable from a random walk.

Note also that both legs individually sit at VR ≈ 0.83–0.87 by q = 120, so the
residual's 0.75 is not a large step beyond the bounce baseline its own legs set.
Figure: `reports/figures/nb02_MES_MYM_variance_ratio.png` — the right panel compares
base frequencies at MATCHED elapsed horizons, which is the honest comparison
(a 15-minute bar at q = 15 spans 225 minutes, not 15).

**[ESTABLISHED] The MES–MYM residual's sub-unit variance ratio at minute
resolution is a microstructure artifact, not a tradable relationship.** This is
precisely the false positive the battery was built to catch, and it would have
been reported as an edge by any test that stopped at "VR < 1, p < 0.001".

## 5. Economic scale — significance is not an edge

At SPX ≈ 5,000 an MES contract carries ≈ $25,000 notional and one tick ($1.25)
is 0.50 bps; at DJIA ≈ 40,000 an MYM contract carries ≈ $20,000 and one tick
($0.50) is 0.25 bps. Crossing the spread on both legs both ways, plus the
A-007 commission placeholder, is roughly **2–3 bps of notional per round trip**.

The largest session-mean anywhere in the two look-ahead-safe specs is
**+1.41 bps** (S2, entry_z 3.0, h = 120, t = 1.93). Every honest positive cell
in the grid is at or below the round-trip cost.

**[ESTABLISHED] Even if the sign had gone the other way, the effect sizes
measured here are ECONOMICALLY IMMATERIAL** at the cost scale this project
targets. With n ≈ 676k bars, statistical significance was never going to be the
binding constraint; D-010 anticipated this and required effect sizes in bps for
exactly this reason. (A-007/A-008 remain unverified placeholders — the cost
comparison is order-of-magnitude, and notebook 07 owns the real number.)

## 6. Notebook-02 preflight (the item report 01 §5 deferred)

### 6.1 z-score behaviour across rolls

Bar-offset buckets around OUR splice timestamps, in bars of the RTH series
(390 = one RTH day; both legs roll on the same dates):

| Bucket | n bars | sd of 1-bar residual change (bps) | vs baseline | mean \|z\| | P(\|z\|>2) |
|---|---|---|---|---|---|
| [−1170,−780) | 10,920 | 1.83 | 1.03× | 1.17 | 0.166 |
| [−780,−390) | 10,920 | 1.80 | 1.02× | 1.14 | 0.125 |
| [−390,0) | 10,920 | **2.81** | **1.59×** | 1.32 | 0.165 |
| [0,390) | 10,920 | **4.68** | **2.64×** | 1.21 | 0.157 |
| [390,780) | 10,920 | **3.09** | **1.74×** | 1.19 | 0.138 |
| [780,1170) | 10,920 | 1.95 | 1.10× | 1.26 | 0.168 |
| baseline | 611,040 | 1.77 | 1.00× | 1.25 | 0.164 |

Figure: `reports/figures/nb02_MES_MYM_roll_preflight.png`.

**[ESTABLISHED] Residual dispersion is elevated from one RTH day before the
splice to two RTH days after it**, peaking at 2.6× baseline on the first
post-roll day and back to ~1.1× by the third. **The z-score itself does not
misbehave** — mean |z| and the P(|z|>2) tail rate are flat across every bucket,
because the rolling z-score normalises by the same elevated volatility. So the
roll window is a *volatility* event in the constructed series, not an artifact
event: exactly what an own-spliced series should look like, and the reason an
exclusion window cannot be justified from these buckets alone.

### 6.2 What a held position actually absorbs

The constructed series is continuous at the splice by construction. A real
position is not: it must close the expiring pair and reopen the new one at
genuinely different prices. That shift is `log(f_MES) − β·log(f_MYM)`:

| | bps of residual |
|---|---|
| median across 28 rolls | **11.8** |
| 90th percentile | 13.9 |
| max | 15.5 |
| min | 6.3 |

**[ESTABLISHED] Every roll in the window imposes a 6–16 bps level shift on a
held MES–MYM position** — roughly **8× the largest effect measured anywhere in
§3**. This, not the bucket diagnostics, is the argument for a pre-roll
exclusion window.

### 6.3 Adopted windows

Re-anchored to the **D-009 splice timestamp** (index: expiry−8d at 10:30 ET).
The `roll_exclusion_days: 2` previously in config was anchored to QC's
OpenInterest flip, which happens at expiry-day open — about 8 days *after* our
splice, i.e. the wrong event entirely (validation report 01 §2).

- **Pre-roll exclusion: 780 bars (2 RTH days) before the splice.** Measured
  dispersion is only elevated in the last RTH day, but `max_holding_bars` is
  780, so a position opened two days out could still be open at the splice and
  eat the §6.2 shock. The binding constraint is the holding period, not the
  dispersion.
- **Post-roll warm-up: 780 bars (2 RTH days), raised from the 390 default.**
  Dispersion is still 1.74× baseline through the second post-roll day and only
  returns to baseline in the third. 780 also guarantees the 390-bar z-score
  lookback contains no pre-splice bars.

Both are recorded in `config/research_config.yaml` as ADOPTED with this report
as the citation, replacing the previous candidate values.

### 6.4 Signals cluster at the open

24.3% of |z| ≥ 2 crossings occur in the first 30 minutes of the session and
~37% in the first hour, decaying to ~3% per 30-minute bucket by the afternoon.
The 390-bar z-score lookback reaches back across the overnight break, so early
bars are scored against yesterday's mean and an overnight repricing registers
as a dislocation. **[PLAUSIBLE] A large minority of "signals" under the current
config are overnight-gap artifacts rather than intraday dislocations.** Logged
as L-013 for notebook 06; it does not change this report's verdict, which is
negative with or without them.

## 7. Reconciliation with the daily screen, and what is NOT concluded

The daily screen (D-008) found MES–MYM to be the *only* pair with daily-horizon
cointegration (EG p = 0.004, half-life ≈ 40 trading days). Nothing here
contradicts that. A 40-day half-life is ≈ 15,600 RTH minute bars — two orders of
magnitude beyond the ≤120-bar horizons tested and well beyond the 780-bar
maximum holding period this project's design allows. Consistently, the AR(1)
half-life of the raw minute residual is ≈ 84,000 bars (≈ 216 RTH days): at
minute resolution there is effectively no level anchor to trade.

**The structure is real and simply lives at the wrong horizon for an intraday
book.** Harvesting it would mean multi-week holds, which D-008 already ruled out
on regime-break grounds and which the Version 1 design does not contemplate.

Not concluded by this report: anything about MES–MNQ, MES–M2K or the four
Treasury pairs (A-009 untouched); anything about longer holding periods; and
anything about MES–MYM as a hedge or overlay rather than a reversion trade.

## 8. Hedge-ratio instability, quantified

Full-sample static β on log prices = 1.326. Trailing 1950-bar β has median
0.976 but a 5th–95th percentile range of **0.316 – 1.468**. L-007 is not a
theoretical worry for this pair; the hedge ratio genuinely wanders by a factor
of four and half of that range is economically absurd for two large-cap equity
indices.

This is also why S2's residual must be taken around the full trailing OLS fit
(intercept included). The no-intercept form multiplies β noise by log-price
level ≈ 10.5 and manufactured **−1,689 bps** of fictitious "reversion" during
the local dry run — see L-011 and D-010 amendment A2.

## 9. Method corrections made during this work (both logged before results)

Two defects were found and fixed while running this notebook. Both are recorded
in full because both changed a headline number:

1. **A1 — splice adjudication.** The mechanised rule `|sr| ≥ 0.6·|gap|` was
   satisfied by any small gap and falsely failed the gate. Replaced by a bound
   (gap must be material, same-signed, and large enough to explain the move).
   Replayed against all five known cases; only the triggering case changes.
2. **A2 — the primary statistic measures P&L, not residual change.** For S2 the
   residual contains its own trailing mean, so differencing it credited the
   *reference window sliding* as reversion. On two independent random walks that
   error reports +5.4 bps at t = 20.3 where the truth is nothing. After the fix
   S2's headline (entry 2.0, h = 120) moved from **+2.14 bps at t = +8.91** to
   **−0.32 bps at t = −0.67**, while S1 and S3 reproduced their previous numbers
   exactly — the self-check that this was a correction, not a new model.

Had A2 not been caught, this report would have claimed a significant intraday
reversion edge in MES–MYM that does not exist.

## 10. Status changes

- **A-006 → FALSIFIED for MES–MYM at intraday horizon** (assumptions register).
  Remains UNVERIFIED for MES–MNQ and MES–M2K.
- `roll_exclusion_days` → replaced by `roll_exclusion_bars: 780`, ADOPTED.
- `post_roll_warmup_bars` 390 → **780**, ADOPTED.
- New limitations: L-012 (MYM 2019-12-12 boundary print), L-013 (open-clustered
  signals under a 390-bar overnight-spanning z-lookback).
- D-009 constructor: third and fourth symbols validated (MES, MYM).

---

## 11. MES–MNQ (pre-registered D-012, run "Virtual Asparagus Pelican")

Second pair in the D-008 priority order, run under the **identical frozen
protocol** — same data path, gate, three specifications, 4×5 grid, variance-ratio
curves, verdict rule and seed. The only permitted differences were the second
leg symbol and its market (MNQ is `Market.CME`; the MYM/CBOT case was L-009).
D-012 also froze the signal configuration deliberately, so L-013 is **not**
fixed here — fixing it mid-sweep would make the two pairs non-comparable.

### 11.1 Gate — the cleanest build in the program so far

| | MES | MNQ |
|---|---|---|
| Rolls built | 28 | 28 |
| `splice_audit` flags | **0** | **0** |
| Factors by median ratio at full 390-bar overlap | 28/28 | 28/28 |

Aligned RTH panel: **684,300 bars, 1,780 sessions**, 2019-06-03 → 2026-04-24.
**Zero bars dropped on either leg** — MNQ prints every minute MES does, unlike
MYM which was missing 1.1%. Against QC's own MNQ series, which carried bad
factors at 4 of these same 28 rolls (validation report 01 §3), the constructed
series is clean at all 28. This is now the **fourth and fifth** symbol on which
the D-009 constructor has been validated (M2K, ZN, MES, MYM, MNQ).

### 11.2 Primary statistic — same answer, same direction

Session-mean P&L of fading, bps, with session-clustered t, at entry_z = 2.0:

| Horizon | S1 (β=1) | S2 (rolling OLS) | S3 (static β, look-ahead) |
|---|---|---|---|
| 5 | −0.48 (t −3.46) | −0.42 (t −4.09) | −0.22 (t −1.97) |
| 15 | −0.96 (t −3.95) | −0.65 (t −3.56) | −0.22 (t −1.18) |
| 30 | −1.17 (t −3.49) | −0.84 (t −3.11) | −0.34 (t −1.40) |
| 60 | −0.07 (t −0.15) | −0.54 (t −1.49) | +0.14 (t +0.43) |
| 120 | +0.70 (t +1.29) | +0.23 (t +0.50) | +1.12 (t +2.74) |

- **Zero cells** in S1 or S2 are positive with |t| ≥ 3. Criterion (a) fails
  outright; REVERSION PRESENT is unreachable.
- 22 of 60 cells reach |t| ≥ 3; **19 are negative**, again concentrated at
  entry_z 1.5–2.0. The three positive significant cells are all in **S3**, the
  look-ahead-contaminated diagnostic.
- Largest session-mean in either honest spec: **+1.78 bps** (S1, entry_z 3.0,
  h = 60) at t = 2.84 — below the significance bar *and* inside the ~2–3 bps
  round-trip cost band.

**[ESTABLISHED] Fading a 1.5–2.0 sigma MES–MNQ dislocation lost money over
2019-2026, at horizons from 5 to 30 minutes, in both look-ahead-safe specs.**

### 11.3 Variance ratios — weaker than MES–MYM, and weaker than its own legs

| q | Residual S1 | Residual S2 | MES alone | MNQ alone |
|---|---|---|---|---|
| 2 | 0.946 | 0.899 | 0.988 | **1.017** |
| 30 | 0.928 | 0.829 | 0.865 | 0.954 |
| 120 | 0.922 | 0.852 | 0.831 | 0.930 |

Two things stand out. First, the shape test fails exactly as before:
VR(120)/VR(30) = **0.994** for the residual — flat, the bounce floor, not the
~1/q decay of reversion. Second, and more damning, **the residual's VR at
q = 120 (0.922) is ABOVE MES's own leg VR (0.831)**: the hedged spread shows
*less* apparent reversion than one of its own legs traded outright. There is no
pair relationship here to be found even before the microstructure correction.
MNQ itself prints VR slightly **above** 1 at q = 2 (1.017), consistent with it
being the tighter book of the two second legs.

### 11.4 Preflight — and a structural roll cost that MES–MYM did not have

Dispersion around the D-009 splice (baseline 2.29 bps): pre-roll day 1.18×,
first post-roll day **1.71×**, second post-roll day **1.70×**, back to 1.11× by
the third. The **780-bar post-roll warm-up adopted in §6.3 is exactly right for
this pair too** — the elevation spans two RTH days and stops.

The held-position shock is where MES–MNQ differs materially:

| | MES–MYM | MES–MNQ |
|---|---|---|
| median \|shift\| | 11.8 bps | **17.4 bps** |
| max | 15.5 bps | **29.0 bps** |
| sign | mixed | **negative at all 28 rolls** |

**[ESTABLISHED] The MES–MNQ roll shock is one-signed at every roll in the
window.** Nasdaq's lower dividend yield gives NQ a higher net cost of carry than
SPX, so the MNQ calendar spread is systematically wider and the factor
differential never changes sign. A long-MES / short-MNQ spread carried across a
roll therefore pays ≈17 bps *every quarter in the same direction* — on the order
of **70 bps a year of structural drag**, not a symmetric risk that averages out.
Any future index-pair design must treat this as a carry cost to be modelled, not
as roll noise to be excluded. (The mirror position earns it, which is a
financing spread, not an edge.)

### 11.5 Other diagnostics

- Hedge instability again: static β = 0.746, trailing β median 0.704 with
  p5–p95 of **0.327–1.039**. L-011/L-007 apply identically.
- Raw minute residual AR(1) half-life ≈ 107,000 bars (~275 RTH days) — no level
  anchor at minute resolution, same as MES–MYM.
- Event clock: **24.7%** of |z| ≥ 2 crossings in the first 30 minutes, against
  24.3% for MES–MYM. Two independent pairs producing the same figure confirms
  **L-013 is a property of the 390-bar overnight-spanning z-score
  configuration, not of any pair.** Notebook 06 owns the fix.

### 11.6 Verdict

**A-006 is FALSIFIED for MES–MNQ at intraday horizon** (D-013). The pair with
the highest daily co-movement (0.93) and the deepest second leg gives the same
answer as the pair with the only daily-horizon cointegration. Two of the three
index pairs are now closed at intraday horizon, both with significant
continuation rather than reversion at the thresholds where the sample is
largest.

**Not concluded:** MES–M2K is untested and is the pair most dependent on the
own-splice constructor (QC's M2K series had bad factors at 19 of 28 rolls). The
index book is not closed until it runs.
