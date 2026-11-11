# Memo 02: age profiles and what each identification strategy assumes

Draft by Claude Code, 2026-11-11, for AJ to review (Decision 17). Every number comes from
`paper/tables/p5_*.csv`, rebuilt by `make models` (Decision 23 and its amendment). Brackets are 95%
intervals from a wild cluster bootstrap at the chip level (7 chips, Webb weights, 9,999 draws)
unless stated. Log points: −0.10 is about a 10% fall. Readings marked **[AJ to confirm]** are
interpretations.

Sample: 20,185 listing-months, seven NVIDIA chips (V100 to B200), October 2017 to October 2026.
Controls in every model: provider × region, contract × term, GPUs per instance, price basis, form
factor.

## 1. What actually happened to each chip (no identification assumption needed)

Each chip's own price path, controlling for who sells it and on what terms, but with no month
effects (Figure 5a). This is the lead result the review asked for, because a realized path needs
no age–time decomposition. Bands here are CR1 by provider-region.

- **V100:** almost flat for four years (−0.06 at 2 years, −0.13 at 4), then a fall to −0.34 at 6
  years and −0.38 at 9.
- **A100 40GB:** −0.28 by 2 years, flat to 4, −0.45 at 5, then back to −0.24 at 6 (2026).
- **A100 80GB:** a steady decline to −0.38 at 4.5 years, then −0.27 at 5.5 (2026).
- **H100 SXM:** prices *rose* in the first year (+0.24) and were still +0.13 at 2 years. They fell to
  −0.50 at 3 years, then recovered to −0.04 at 4 years in 2026.
- **H200:** +0.24 at 1 year and +0.65 at 1.5 years, all in the 2025–26 shortage.

Dropping 2026 deepens the A100 and H100 declines: the A100 40GB reaches −0.41 at 5.5 years, and the H100 SXM
−0.58 at 3. **[AJ to confirm]** The realized paths are not one smooth decay. They are long flat
stretches, sharp falls and demand-driven rebounds, and the 2026 shortage reverses part of the decline
for every chip still on sale.

## 2. Projection strategies: what each assumes and finds

| Strategy | Assumes | Rate, years 0–2 (log/yr) | Rate, years 2–4 | Shape* |
| --- | --- | --- | --- | --- |
| 1a quality index | Vintage differences are fully captured by BF16 TFLOP/s | +0.27 [−0.23, 0.77] | −0.03 [−0.24, 0.18] | +0.31 [−0.52, 1.11] |
| 1b three specs | ... by TFLOP/s, bandwidth and memory | +0.28 [−0.28, 0.84] | −0.00 [−0.50, 0.47] | +0.28 [−0.42, 0.97] |
| 2 frontier-relative | Market-wide time effects work only through the best chip available | +0.11 [−0.12, 0.35] | −0.15 [−0.41, 0.11] | +0.26 [0.05, 0.47] |
| 4 shape only | Nothing about the linear rate; it is swept | (assumed) | (assumed) | +0.47 [0.36, 0.57] |

\*Shape = annual rate over years 0–2 minus the rate over years 2–4. H1 (front-loaded decline) predicts
a negative number.

- **Strategy 1** prices each extra doubling of TFLOP/s at 0.88 log points [0.15, 1.59]. It finds no
  decline with age in the first two years and roughly zero after. The age profile is wide because
  the vintage effect rests on seven chips.
- **Strategy 2's** frontier term is small and imprecise (0.08 [−0.06, 0.22]). Its age profile rises
  slightly then falls; it is the only identified strategy whose shape interval excludes zero.
- **Strategy 3 (successor release, H2):** no detectable drop when a successor arrives. Prices in
  the first year after are −0.09 [−0.40, 0.23] relative to the 6 months before. Spread over the mean
  2.5-year architecture gap, that is −0.04 per year [−0.16, 0.09]. Announcement dates were not
  available, so a drop priced in at announcement would be missed.
- **Strategy 4** cannot give a rate (Figure 5c shows the curve for average rates from 0 to −0.40 per year).
  What it does give is the shape. Whatever the rate, prices sit above trend for the first 1.5 years
  (+0.70 [0.43, 0.98] relative to the detrended line at 1.5 years) and fall faster after.

## 3. Where they agree and disagree

- **Agreement on shape, against H1.** Every strategy's shape estimate is positive: prices fall
  *later*, not earlier. Strategies 2 and 4 exclude zero. This survives weighting each
  provider-chip-month equally (strategy 4: +0.29 [0.07, 0.50]) and dropping the anomalous Google
  July 2026 snapshot (+0.47). **[AJ to confirm]** The most likely reason is demand timing rather than
  physics: the H100 and H200 were young during the 2023–26 shortages, so scarcity loads onto early
  ages. This is the review's point that month effects absorb only shocks common to all chips.
- **Disagreement on rate.** No strategy that identifies a linear term finds a significant decline
  over years 0–4; strategy 1 even leans positive. The realized V100 and A100 paths fall 0.3–0.45 log
  points over 4–6 years. **[AJ to confirm]** The projection strategies are dominated by the newer
  chips' shortage-era prices, so in this sample the observed cohort paths are the more credible
  guide to the rate, and the identification range is itself a finding (proposal, Expected results).

## 4. H3 and H4

- **H3, contract type:** the shape flips by contract. Spot prices are strongly back-loaded in all
  three strategies (strategy 4: +0.87 [0.34, 1.41]). On-demand prices lean front-loaded but are
  not significant (strategy 4: −0.13 [−0.40, 0.13]). Reserved-price samples are small (644 and 734
  listing-months) and uninformative. This fits H3's idea that the market you read changes the answer, though
  the wedge is in shape rather than speed. **[AJ to confirm]**
- **H4, sub-periods:** 2023–25 repeats the full-sample shape (strategy 4: +0.48). The pre-2023 period has only
  three chips, so its bootstrap has three clusters and says little. 2026 alone is too short (each
  chip is seen for under a year), and those estimates are flagged as extrapolations. H4's
  stability claim cannot be tested well with these data.

## 5. Caveats for the review (B4)

- Seven chips means seven clusters. Across the full-sample measures, the chip-level bootstrap interval is a
  median 1.2 times as wide as a provider-clustered (6 clusters) normal interval, from 0.3 times
  (strategy 4's shape) to 16.6 times (strategy 1b's TFLOP/s coefficient). Neither is reliable with so few clusters; the bootstrap is the
  pre-registered headline (Decision 23).
- The baseline 6-month-bin model is identified only through the binning (Hall 1968), so its bins
  are reported in `p5_baseline_bins.csv` but not interpreted.
- Google is 62% of rows. Equal provider-chip-month weights move strategy 1's TFLOP/s coefficient from 0.88
  to 0.70 [−0.04, 1.45] but leave the shape sign unchanged.
- No announcement dates, no L40S or MI300X in the sample, and the live data stop on 10 November.
