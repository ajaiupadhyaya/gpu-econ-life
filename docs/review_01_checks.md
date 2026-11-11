# Review 01: results of the requested checks (points 1, 2, 4, 7)

Run by Claude Code on 2026-11-11 for AJ, to inform the responses in `docs/review_01.md`. Every
number comes from `paper/tables/p5_review_*.csv`, built by `gel.models.review_checks`
(`make p5-review`). The other review points (3, 5, 6, 8-15) are not addressed here.

## Point 1: what identifies the strategy 4 shape

**Chip-specific trends** (`p5_review_chip_trends.csv`). Adding a linear time trend for each chip
makes the a² coefficient unidentified (a² = t² − 2vt + v², and −2vt is a chip trend), so the
shape is no longer one number. It equals −0.39 − 4·c2 for an assumed a² coefficient c2:

| Assumed c2 | early − late rate |
| --- | --- |
| 0 (the reviewer's normalization) | −0.39 |
| half the no-trend estimate (−0.151) | +0.21 |
| the no-trend estimate (−0.302) | +0.81 |

So the reviewer's −0.39 is reproduced exactly, but it is itself a normalization. The accurate
statement is stronger: once chip-specific trends are allowed, **the sign of the shape is not
identified**. The no-trend estimate (+0.47) holds only under the assumption of no
vintage-specific calendar trends.

**Chip time slopes** (`p5_review_chip_slopes.csv`, log points per year relative to the V100, with
chip and month effects and no age terms): A100 40GB +0.02, A100 80GB −0.05, H100 PCIe −0.09, H100
SXM −0.19, H200 +0.33, B200 −0.19. These seven points are what the curvature is fitted through.
The H200's +0.33 (its 2025–26 shortage) is the outlier.

**Randomization inference over release dates** (`p5_review_permutation_summary.csv`). Of the
1,260 distinct ways to assign the seven release months to the seven chips, the actual assignment
gives the largest shape (+0.47; permuted mean 0.00, s.d. 0.10): p = 0.0008. The curvature is tied
to the true release order and is not a labelling accident. This test cannot tell age effects apart
from demand trends that are themselves ordered by vintage, which is the concern above.

## Point 2: sign convention

The measure is renamed `early_minus_late_rate` (rate over years 0–2 minus the rate over years 2–4).
Every table states that H1 predicts a negative value. `memo_02_hedonic.md` already read the
positive estimates as back-loaded, against H1, so no reported sentence had the sign wrong. The
review's other suggestion, making contract type the primary split, is a design change for AJ.

## Point 4: the pooled bins

`p5_review_bin_shift.csv` shifts the 6-month bin edges by k = 0 to 5 months. The bin covering 12 months
ranges from **0.24 to 1.22** across shifts, and still 0.23 to 1.18 after detrending. The pooled-bin
profile is set by the bin edges and is not an age profile. `p5_baseline_bins.csv` now carries a
"diagnostic only" note. The bins were never used in a figure or memo claim.

## Point 7: inference with seven chips

**Restricted bootstrap (WCR)** (`p5_review_wcr.csv`, 9,999 draws; null: measure = 0). No measure
in the headline table is significant under WCR:

| Measure | WCU p (reported) | WCR p |
| --- | --- | --- |
| Strategy 4, early − late rate | < 0.0001 | 0.29 |
| Strategy 2, early − late rate | 0.006 | 0.30 |
| Strategy 1a, rate years 0–2 | 0.30 | 0.65 |
| Strategy 2, rate years 2–4 | 0.21 | 0.23 |

Inverting the WCR test gives a 95% interval for the strategy 4 shape of **[−0.44, 1.03]**
(`p5_review_wcr_interval.csv`, 1,999 draws per step). The reported WCU interval is [0.36, 0.57].

**Coverage Monte Carlo** (`p5_review_monte_carlo.csv`; 200 replications on this panel's rows and
fixed effects, true curvature zero; errors with chip × month and provider × month components sized
to the actual residuals). Nominal 95% intervals cover:

| Method | i.i.d. chip × month shocks | random-walk chip shocks |
| --- | --- | --- |
| WCU (the reported intervals) | 72.5% | 66.0% |
| WCR | 98.5% | 97.5% |
| CR1 by chip | 76.0% | 74.0% |
| CR1 by provider | 69.5% | 72.5% |

The reported wild-bootstrap intervals are too narrow on this design. WCR is close to nominal,
slightly conservative.

**Other changes made:**
- Subsamples with fewer than 6 chips get no chip-level bootstrap (this drops the up-to-2022
  period, 3 chips).
- p-values carry their floor, 1/(B+1).
- CR2 (Bell–McCaffrey) was not computed: its adjustment needs the inverse square root of
  cluster blocks up to 5,510 × 5,510, including the absorbed fixed effects. The WCR test and the
  Monte Carlo answer the same question.

## What this means for the Phase 5 claims

- The shape result (prices falling later rather than earlier) is **not established**. Under
  WCR it is not significant (p = 0.29). Once vintage-specific trends are allowed, its sign is not
  identified. It is tied to the actual release order, but so is the 2023–26 demand rotation toward
  newer chips. H1 is neither supported nor rejected by these data.
- The other conclusions stand, more weakly: no strategy that identifies a rate finds a significant
  decline over years 0–4, and the observed cohort paths remain the main evidence on the rate.
- Switching the headline inference from WCU to WCR changes the estimation spec logged in
  Decision 23, so it is AJ's decision (CLAUDE.md rule 7).
