# Review 01: Phase 5 hedonic age profiles and identification

Independent adversarial review, written 2026-11-10 by a session with no project history.

**What I read:** `src/gel/models/hedonic.py` and `hedonic_core.py` (the other files in `src/gel/models/` only skimmed for names), `src/gel/build/panel.py`, `docs/cleaning_report.md`, `paper/tables/p5_*.csv` and `p5_*.tex`, and `docs/proposal.md` (hypotheses, Step 1, Step 2, the Phase 5 brief).
**What I deliberately did not read:** `docs/memo_02_hedonic.md`, `docs/decisions.md`, `docs/memo_01_descriptives.md`, `docs/open_questions.md`. So some of the points below may already be dealt with there. If so, say where.

**Checks I ran:** read-only Python against `data/processed/panel.parquet` using `gel.models.hedonic.load_sample()` and `hedonic_core.fit_ols()`, point estimates only (no bootstrap). The scripts are in this session's scratchpad and are not part of the repo. Numbers I label "my check" come from those runs. They are not in any table, so treat them as leads to reproduce, not as results.

Severity scale: **Critical** means the headline claim may not survive. **Major** means a referee will require it fixed. **Moderate** means it must be addressed or disclosed. **Minor** means cleanup.

---

## The two questions

**(1) Weakest identifying assumption.** The one tight shape result, strategy 4's `front_loading` = 0.47 [0.36, 0.57], is identified only by *differences in calendar-time trends across seven vintages*. It assumes there are no chip-specific (vintage × period) trends other than those that age itself produces. When I add chip-specific linear time trends, the estimate flips sign (+0.47 to −0.39). See point 1. For the two strategies that identify the linear term, the runner-up is strategy 2's assumption that a five-step frontier series is the *only* common time effect (point 5).

**(2) Most likely referee objection.** "These are administered hyperscaler list prices, not market rents." 93% of the estimation sample is Google, AWS or Azure. On-demand and reserved list prices are unchanged in 96.3% of month-to-month transitions. AWS's V100 on-demand price is $3.06 in every year from 2017 to 2026. The age profile is therefore identified from a handful of repricing decisions and from spot prices (point 3). A close second: the pooled shape result is entirely a spot-market result, and its sign is the *opposite* of H1 (point 2).

---

## Critical

### 1. The strategy 4 shape result is identified only from cross-vintage differences in time trends

**Evidence.**
- Spec `s4_shape`, `hedonic.py:249-255`: chip FE, month FE, and the curvature terms `age2, age3, knot0..2`. Write age as a = t − v (calendar month minus vintage). Then a² = t² − 2vt + v². The t² part is absorbed by the month FE and the v² part by the chip FE. What is left, −2vt, is a chip-specific linear time trend whose slope is proportional to vintage. The cubic and knot terms work the same way at higher order. So the curvature estimate amounts to: "do older vintages have systematically different calendar-time trends than newer ones?" It is answered with seven chips. Two pairs (h100_sxm/h100_pcie, h200/b200) share a release month, so there are only five distinct vintages.
- My check: refitting s4 with a linear trend for each chip (age2 removed, since it becomes unidentified, and one trend dropped as the normalization) moves `front_loading` from **+0.47 to −0.39**.
- Leave-one-chip-out (my check) is reassuring but does not test this assumption: s4 `front_loading` stays between 0.30 (drop h200) and 0.51 (drop a100_40gb).
- Chip-specific trends unrelated to age are plausible in this sample. Example: Google's H100 spot price rises from a median of $2.08 (2026-01) to $5.53 (2026-10) across 79–91 listings, a demand-regime move that hits one vintage hardest.

**Why it matters.** The paper's main shape claim, and anything Phase 6 builds on it, rests on the absence of vintage-specific demand trends. That is exactly what the 2023–2026 AI boom violates: demand moved toward Hopper and away from Volta. This is the APC "no interaction" assumption, and Step 2 of the proposal does not state it.

**What would resolve it.** (a) State the assumption explicitly in the paper. (b) Plot the identifying variation: the seven chip-specific time slopes (from a chip × trend model with month FE) against release date, which is the scatter the quadratic is fitted through. (c) Report s4 with chip-specific linear trends, keeping only the terms still identified (cubic and knots), as a bound. (d) Run a placebo that permutes release dates across chips and re-estimates the shape (randomization inference over the 7! = 5,040 assignments, or over the distinct ones).

Draft response (Claude, for AJ to confirm or rewrite): Accepted. The assumption is now stated, and the checks are in `p5_review_chip_trends.csv`, `p5_review_chip_slopes.csv` and `p5_review_permutation_summary.csv`. With chip-specific trends the a^2 term is unidentified, and the shape becomes a linear function of whatever a^2 coefficient is assumed (−0.39 at zero, +0.81 at the no-trend value). The chip time slopes behind the curvature are not monotone in release date (H200 +0.33/yr against V100; H100 SXM and B200 −0.19). The paper will present the strategy 4 shape as conditional on no vintage-specific trends, not as a finding.

Response (AJ):

### 2. The pooled shape result comes from spot prices, and its sign is the opposite of H1

**Evidence.**
- `MEASURES["front_loading"]` (`hedonic.py:178-180`) = rate(0–2) − rate(2–4). H1 (`proposal.md:53`) predicts a faster decline early: rate(0–2) < rate(2–4) < 0, so `front_loading` < 0. Every significant estimate is **positive**: s4 0.47 [0.36, 0.57], s2 0.26 [0.05, 0.47], s4 spot 0.87 [0.34, 1.41]. A positive value means prices rise, or fall more slowly, in years 0–2 than in years 2–4. That is a concave, back-loaded profile. Strategies 1a and 1b put rate(0–2) at +0.27 and +0.28 a year: rents *rising* with age (`p5_strategies.tex`).
- `p5_h3_h4.tex`: on-demand shape is −0.17 (1a), −0.12 (2) and −0.13 (4), all insignificant but with H1's sign. Spot is +0.65, +0.76 and +0.87, all significant.
- My check (s4 shape by subsample): no spot listings −0.02; spot, non-Google 0.70; Google only 0.17; AWS only 0.53; neoclouds only 0.10.
- The measure's name, `front_loading`, reads naturally as "positive = front-loaded", which inverts what it measures.

**Why it matters.** If the memo or paper reads 0.47 as support for H1, the sign is wrong. Even read correctly, the pooled number is a weighted average of a spot profile (prices rise while capacity is scarce, then fall) and an on-demand profile that is flat or front-loaded. Spot is 48% of rows (9,693 of 20,185). A spot price is a capacity-utilization price, not a rental value of the asset, so pooling it with list prices has no clear interpretation for economic life.

**What would resolve it.** Rename the measure (for example `early_minus_late_rate`) and state H1's predicted sign next to every table. Make contract type the primary split, not a robustness check. Report the asset-value calculation (Phase 6) separately for spot and list prices. Pre-specify which market is the "rental value", for example on-demand or reserved, the market a depreciation comparison should use.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. Renamed `early_minus_late_rate`, with H1's predicted sign (< 0) printed in every table header (Decision 24). Contract type becomes the primary split. Spot is +0.87 and on-demand −0.13. Among non-spot listings whose price changes at least once, the shape is −0.52 (`p5_review_repricing_shape.csv`), in H1's direction. Phase 6 values the asset on list (on-demand) prices, with spot reported separately.

Response (AJ):

### 3. Administered list prices: most of the identifying variation is a few repricing decisions

**Evidence.**
- Estimation sample by provider (my check, n = 20,185): google_cloud 62.3%, aws 18.9%, azure 11.8%, lambda 4.0%, coreweave 2.0%, paperspace 1.0%. No marketplace rows. The proposal excludes marketplaces for terms-of-use reasons (`proposal.md:93`), but the X vector still lists the provider type (`proposal.md:121`).
- Share of month-to-month transitions with an unchanged nominal price (my check, same listing key as `panel.py:49-61` plus form factor): aws on-demand 0.992, reserved_1y 0.995, reserved_3y 0.985; azure on-demand 1.000; coreweave on-demand 1.000; google on-demand 0.956; lambda on-demand 0.910. Over all on-demand and reserved transitions, only **3.7%** (of 9,186) show any change. Spot moves more: aws 0.172 unchanged, google 0.652.
- AWS V100 on-demand: median nominal price $3.06 in every year 2017–2026. In real 2025 dollars it falls from $3.99 to $2.96 purely through the CPI deflator. Before 2020-04 the only V100 rows are AWS on-demand and reserved, so V100's young-age observations are this flat price.
- The changes cluster by provider and month, across chips. Google on-demand and reserved listings repriced in 2025-03: h100_sxm −0.755 log (28 listings) and a100_40gb −0.598 (20 listings).

**Why it matters.** A referee will say the paper measures menu-cost stickiness and the pricing policies of three firms. With month FE, a never-changed list price for an old chip shows up as the old chip's price *rising* relative to repriced new chips. That fits the positive bins (point 4) and the positive 1a/1b rates. "Market-implied life" needs prices that clear a market.

**What would resolve it.** (a) Show the share of identifying variation from repricing events: re-estimate on listings that change price at least once, or treat each provider repricing as an event. (b) Validate the profiles against a market price series that is permitted under the project's rules. The proposal names Huang's published marketplace tables (`proposal.md:93`): compare levels and age gradients at matching chip-months. Any new source needs your approval (CLAUDE.md rule 7). (c) Frame the result explicitly as "posted cloud list and spot prices" and move the economic-life claim to the spot and neocloud subsample if that is where prices move.

Draft response (Claude, for AJ to confirm or rewrite): Accepted as the main framing risk. 96% of on-demand and reserved transitions are unchanged (`p5_review_repricing.csv`). The paper will describe the data as posted cloud prices and show results on listings that move. Validation against marketplace evidence uses only the published tables the proposal already names (Huang 2026), compared at matching chip-months; no new collection.

Response (AJ):

---

## Major

### 4. The pooled 6-month-bin baseline is "identified" only by the binning restriction (coding/identification error)

**Evidence.**
- `baseline_bins` (`hedonic.py:346-354`) puts pooled bin dummies alongside chip and month FE. `fit_ols` drops only columns that are *exactly* collinear (`hedonic_core.py:98-105`). floor(age/6) is not exactly linear in age, so nothing is dropped (`p5_baseline_bins.csv`, `dropped` empty, condition 43.8). With monthly age dummies the solver does drop columns (`bin109, bin110, bin111`, my check), which confirms the Hall dependency exists and that the bins break it only by assumption.
- Shifting the bin boundaries by k months (age_bin = (age_months + k) // 6, my check) gives: bin01 = +0.40 (k=0), +0.43 (1), +0.52 (2), +0.59 (3), **+1.00 (4)**, **−0.11 (5)**. The whole profile moves by about 0.6 log points with k. With 12-month bins: +0.18 at 1y, −0.01 at 3y. With 3-month bins: +0.44 at 0.25y, +0.87 at 2.25y.
- `p5_baseline_bins.csv` reports bin01–bin06 with `wcb_p` = 0.0 and CIs excluding zero (bin01 0.40 [0.27, 0.53]). That precision is spurious: the level of the profile is set by where the bin edges fall.

**Why it matters.** Phase 5 item 1 asks for this table as the baseline. Any figure or sentence that reads it as an age profile ("rents are 40–90% higher after 6 months") reports an artifact.

**What would resolve it.** Do not report pooled bins as levels. Either impose the strategy 4 normalization explicitly (bins plus an assumed linear term, swept) or report only detrended bins or second differences. Add a test: for any spec with chip and month FE, refit with bin edges shifted and assert that the identified quantities do not change.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. The pooled bins are now labelled diagnostic only, and `p5_review_bin_shift.csv` shows levels moving by up to 0.9 log points with the bin edges. The paper will not report them as an age profile.

Response (AJ):

### 5. Strategy 2 is a time-series step variable; its frontier includes a chip that is not in the sample or rentable

**Evidence.**
- `s2_frontier` (`hedonic.py:242-248`) has chip FE and no month FE. rel_frontier = ln TFLOPs_c − ln F_t, so with chip FE its coefficient is the coefficient on −ln F_t, a pure time series. The linear age term is then identified from within-chip time variation, under the assumption that the *only* common time effect is F_t.
- The frontier steps in the sample (my check, from `load_sample`, `hedonic.py:72-77`): 125 (2017-10), 312 (2020-05), 989.5 (2022-09), **1307.4 (2023-12)**, 2250 (2024-11). The 2023-12 step is **mi300x** (1307.4 TFLOP/s, release month 2023-12 in the panel's joined chip columns, my check). mi300x is not in `SAMPLE_CHIPS` (`hedonic.py:27`), and its only panel rows are Azure 2026-10/11 (`cleaning_report.md`). So obsolescence of NVIDIA chips is dated to a chip nobody in the panel could rent.
- With an NVIDIA-only frontier (my check), rate(0–2) is 0.099 vs 0.111, rate(2–4) −0.148 vs −0.150, and the coefficient 0.089 vs 0.079. The coding issue barely moves the estimates, but it should be fixed.
- In `period:from_2026` the frontier is constant, `rel_frontier` is dropped (`p5_summary.csv`, `dropped=rel_frontier`), and s2 has **no time control at all**. The table still reports rate(0–2) = −6.60 [−47.7, 35.8].
- Partial reassurance (my check): adding calendar-year FE to s2 leaves rate(0–2) 0.145, rate(2–4) −0.135 and front-loading 0.28. So within-year time effects are not driving it, though they could still sit at the monthly level.
- Real prices with no month FE: the CPI deflator enters as age (point 3, V100). Nominal vs real (my check): rate(0–2) 0.140 vs 0.111, rate(2–4) −0.118 vs −0.150.

**Why it matters.** Strategy 2 has to attribute the 2023 ChatGPT demand shock and the 2026 spot surge to age or to the frontier. With five steps, the frontier coefficient is identified from five dates, each of which coincides with other market events.

**What would resolve it.** Build F_t from in-sample chips and date each step by first cloud availability, not release. Report s2 with year or quarter FE as the main version. Suppress s2 in any subsample where the frontier is constant. Show event-time plots around each of the frontier steps.

Draft response (Claude, for AJ to confirm or rewrite): Partly accepted. An in-sample frontier changes almost nothing: rate(0–2) is 0.099 vs 0.111, and the shape 0.25 vs 0.26 (`p5_review_frontier.csv`). Year effects leave the estimates similar (shape 0.28). Switching the logged frontier to in-sample chips is proposed to AJ (Decision 24 (b)). Strategy 2 is not reported in sub-periods where the frontier is constant.

Response (AJ):

### 6. Event study: wrong event dates (release, not GA), no comparison series, and the linear term is omitted

**Evidence.**
- Event dates are Epoch `release_date` (`hedonic.py:389-393`). The proposal specifies the successor's *GA* date (`proposal.md:54, 130, 428`) and defines age from GA (`proposal.md:119`). Release vs first listing in the panel (my check): a100_40gb 2020-05 vs 2020-11; h100_sxm 2022-09 vs 2023-01 (AWS's first is 2023-08, Google's 2024-04, `cleaning_report.md`); b200 2024-11 vs 2025-06.
- The only sizeable coefficient, `ev_+6_+11` = −0.18 [−0.60, 0.26] (`p5_event_study.csv`), falls in the window where cloud GA actually happened. Re-dating events to the successor's first panel listing (my check, point estimates) gives ev_+0_+5 = −0.18, ev_+6_+11 = −0.05, and pre-period bins of about +0.10. The pattern depends on the dating.
- The proposal says the comparison is "against a comparison series such as reserved prices or non-NVIDIA chips" (`proposal.md:130`). The code has none: the controls are whichever chips have `tau` null, which are h200 and b200 (my check). b200 is itself the successor event for h100, and h200 shares b200's release month (2024-11 in the data), so the "never-treated" units are the treatment and its sibling.
- The model includes only `CURVATURE` (`hedonic.py:395`), so the event bins absorb any linear age trend in tau (tau = age − constant within chip). That is the same Hall problem as point 4: the bins carry the unidentified linear term, and the pre-period bins are the only check.
- There are really three events (successor dates 2020-05, 2022-09, 2024-11) spread across five chip series. The chip-cluster bootstrap treats these as seven independent clusters.
- `s3_implied_annual_rate` = h2 / mean architecture gap (2.46 years, `hedonic.py:399-400`) assumes all obsolescence arrives as one step per generation. That is an assumption, not an estimate, and it should not be listed as a strategy 3 *result*.

**What would resolve it.** Take GA dates from a documented source (first general-availability listing per provider, logged in `docs/assumptions.md`). Use a stacked event design with clean controls (for each event, chips not treated within ±18 months), plus reserved prices as the comparison series the proposal promised. Report each event separately (three rows). Do inference by permutation over placebo event dates. Drop `s3_implied_annual_rate`, or present it as a calibration.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. Re-dating events to the successor's first panel listing moves the one negative bin from +6..+11 to +0..+5 (−0.18 in both cases; `p5_review_event_dating.csv`), and the pre-period rises to about +0.10. The paper will report H2 as not detected under either dating and drop `s3_implied_annual_rate` from the results. A stacked design with reserved prices as the comparison series is left as a stated limitation.

Response (AJ):

### 7. Inference with 7 unbalanced clusters: the wild cluster bootstrap is too narrow and degenerates in subsamples

**Evidence.**
- Cluster sizes run from 355 (h100_pcie) to 5,510 (a100_40gb) (`p5_sample.csv`). The bootstrap is the unrestricted (WCU) percentile-t version (`hedonic_core.py:151-206`). The few-cluster literature (MacKinnon and Webb, and later papers) finds WCU tests over-reject with few, unbalanced clusters and recommends the restricted version (WCR) for p-values. Verify the citations before using them.
- s4 full sample: the WCB CI [0.36, 0.57] is *narrower* than CR1 by chip ±1.96 × 0.081 = [0.31, 0.63]. It is much narrower than provider clustering (SE 0.169) or two-way provider × month (SE 0.160) (`p5_summary.csv`). A few-cluster bootstrap that is tighter than the naive CR1 interval is a warning sign.
- Subsamples are allowed with as few as 3 chips (`hedonic.py:448, 453`). With G = 3 there are 6³ = 216 weight vectors. The results: `period:to_2022`, s2 rate(2–4) = −0.031 **[−0.03, −0.03]**, p = 0.000; `coef_rel_frontier` [−0.00, 0.00]; s1a `coef_ln_tflops` = **−1.54** [−1.72, −1.35], p = 0.000, a "significant" *negative* compute elasticity from three chips, two of which share the same TFLOPs.
- Residuals are correlated across chips within a provider-month (point 3: Google repriced H100 and A100 in the same month), and chip clustering ignores that dependence. Provider clustering (6 clusters) is also few.
- p-values print as 0.000. With B = 9,999 the floor is 1/(B+1) = 0.0001, so they should be reported as p < 0.0001.

**What would resolve it.** (a) Use WCR p-values, and get CIs by test inversion. (b) Add CR2/CR3 (Bell-McCaffrey) with Imbens-Kolesár degrees of freedom. (c) Run a Monte Carlo on this panel's design: simulate chip-level and provider-month shocks under a known flat profile and report the coverage of each method. (d) Set a minimum G (≥ 6) below which the bootstrap is not reported, and suppress the `to_2022` rows. (e) Add randomization inference over vintages (point 1d).

Draft response (Claude, for AJ to confirm or rewrite): Accepted. On this panel's design, WCR p-values, the test-inversion interval and the Monte Carlo (`p5_review_wcr*.csv`, `p5_review_monte_carlo.csv`) show the unrestricted bootstrap covering 66–73%. Sub-samples below 6 chips are no longer reported. Proposed to AJ: WCR becomes the headline inference (Decision 24 (a)).

Response (AJ):

### 8. Unit of observation and weighting: Google's region and shape count sets the weights

**Evidence.**
- Rows per provider-chip-month (my check): median 4, mean 18.0, max 422, over 1,120 cells. Google lists the same per-GPU price for 1, 2, 4 and 8-GPU shapes. For example, Google H100 on-demand in 2026-08 to 2026-10 has 19–20 listings each at gpu_count 1, 2 and 4 with identical min, median and max ($9.80, $11.17–11.26, $14.20). Duplicate price points add N without adding information.
- Google is 81–82% of a100_40gb and h100_sxm rows and 0% of h100_pcie.
- The provider-chip-month weighted run (`w_pcm`, `hedonic.py:97-98`) cuts s4 shape from 0.47 to 0.29 and s1a rate(0–2) from 0.27 to 0.21 (`p5_summary.csv`). Google only gives 0.17 and non-Google 0.44 (my check).

**What would resolve it.** Collapse to unique price points per provider × chip × contract × month (or region × month) before estimation, or weight providers equally. Report the headline under that weighting as well, plus provider-specific profiles for at least AWS, Google and the neoclouds pooled.

Draft response (Claude, for AJ to confirm or rewrite): Accepted as a robustness check. Unique price points raise the strategy 4 shape to 0.54, provider-equal weights cut it to 0.19, and dropping Google gives 0.44 (`p5_review_weighting.csv`). The weighting is reported next to the headline.

Response (AJ):

### 9. Strategy 1 is a seven-point cross-section, and one chip flips it

**Evidence.**
- In `s1a_tflops` (`hedonic.py:228-234`) the linear age term, with month FE and no chip FE, is identified from the cross-chip relation between residual price and release date. That is a regression on seven chips. a100_40gb/a100_80gb share 312 TFLOPs, and h100_sxm/h200 share 989.5 (my check), so s1a forces each pair to have the same vintage effect.
- Leave-one-chip-out (my check): dropping h200 moves s1a rate(0–2) from +0.27 to **−0.11** and front-loading from +0.31 to **−0.18**. Dropping b200 moves rate(0–2) to +0.46.
- The TFLOP elasticity is 0.88 [0.15, 1.59]. An elasticity below 1 means newer chips are cheaper per TFLOP, and the spline reads that as older chips' prices "rising" with age.
- `period:from_2026` s1a: CI ±53, condition number 288,069, yet no † because the `extrapolated` flag only checks specs whose first FE is `chip` (`hedonic.py:276`).

**What would resolve it.** Present strategy 1 honestly as a seven-point cross-section: plot the chip effects from the chip + month FE model against ln TFLOPs and release date, and report the leave-one-out table. State the residual degrees of freedom (7 chips, 2–4 vintage parameters). Fix the extrapolation flag so it covers specs with no chip FE whose age support within the subperiod is short.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. The leave-one-chip-out table is `p5_review_leave_one_out.csv`. Strategy 1's sign depends on the H200 (dropping it gives −0.18), and the paper says so.

Response (AJ):

---

## Moderate

### 10. Age is measured from release, not cloud availability, and the lag differs by chip

**Evidence.** Age comes from Epoch's release month (`panel.py:271-287`), while the proposal says GA (`proposal.md:119`). Age at first listing (`p5_sample.csv`): h200 1 month, v100 3, h100_sxm/pcie 4, a100_40gb 6, b200 7, a100_80gb 18. Age year 0 has 383 rows (1.9% of the sample, my check), so g(0), the normalization point of every profile, is anchored on a thin, chip-dependent window. h200 and b200 share the release month 2024-11, so they have the same age in every month. Please check that against the chips table's source.
**What would resolve it.** Re-run with age measured from the first cloud listing (market-wide or provider-specific) as a robustness check, and report profiles from age 0.5 rather than 0.

Draft response (Claude, for AJ to confirm or rewrite): Partly accepted. Age from first cloud listing is used for the event-dating check. A full re-run with age measured from availability is a logged-spec change and is listed for AJ.

Response (AJ):

### 11. Age support beyond 4 years rests on two or three chips and an unrestricted cubic

**Evidence.** By age year (my check): year 5 has only a100_40gb, a100_80gb and v100; year 6 only a100_40gb and v100; years 7–9 only v100. The spline is a truncated-power cubic with knots at 1.5, 3 and 5 (`hedonic.py:29, 53-58`), so it stays cubic beyond 5 years. `profile_curve` reports up to age 6 and the strategy 4 detrending runs over ages 0–6 (`hedonic.py:288, 306-318`). The definition of the swept linear term (the "average slope over 0–6") therefore depends on the V100/A100 tail. `extrapolated` uses the maximum span across chips (V100's 9 years), so it can never trigger on the full sample (`hedonic.py:272-277`).
**What would resolve it.** Use a natural spline (linear beyond the last knot), detrend over 0–4, add a per-chip age-support figure, and compute the flag per chip.

Draft response (Claude, for AJ to confirm or rewrite): Noted. The detrending grid and natural spline are logged specs (Decision 23 amendment). The paper states that ages beyond 5 years rest on the V100 and A100.

Response (AJ):

### 12. H3 and H4 splits cannot carry the hypotheses as specified

**Evidence.** H4: `from_2026` is unusable (s1a CI ±53, s2 ±40, s4 ±11) and `to_2022` has G = 3 (point 7), so the "stable across sub-periods" test reduces to one usable period (2023–2025). H3: the contract subsamples change the provider and chip mix. Reserved rows number 644 and 734 with condition numbers of 13,000–17,000, and they come mostly from AWS, Lambda and Paperspace. So the spot vs reserved comparison is partly a Google vs AWS comparison.
**What would resolve it.** Estimate one pooled model with contract × curvature and period × curvature interactions, holding provider-region FE fixed. For H3, use within-provider contrasts: AWS posts on-demand, spot, 1y and 3y prices for the same instance. Use rolling windows for H4 instead of three fixed bins.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. H4 cannot be tested as specified, and the paper says so. H3 is reported as the spot vs list-price split from point 2.

Response (AJ):

### 13. Cohort paths and s2 report CPI deflation as price decline

**Evidence.** `cohort_paths` (`hedonic.py:357-383`) and s2 have no month FE, so an unchanged nominal list price shows a real decline of about 26% over 2017–2026 (AWS V100, point 3). Calling these paths "observed" is accurate, but a reader will take the decline as market depreciation.
**What would resolve it.** Show cohort paths in nominal terms next to the real ones, or net out a common time index estimated from the other chips, and say in the caption how much of the decline is the deflator.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. Nominal and real cohort paths are side by side in `p5_review_cohort_nominal.csv`.

Response (AJ):

### 14. Data spot-checks to resolve before the paper

**Evidence.** (a) Google H100 on-demand: the median is $10.79 in 2026-06, $4.20 in 2026-07, and $11.17 in 2026-08, across 19–38 listings per GPU count (my check). That is the known July 2026 anomaly, and the robustness run drops 398 rows (`hedonic.py:436-444`). But the $4.20 minimum already appears in 2026-06, so the anomaly may start earlier than the filter assumes. The filter also depends on the `collector` string containing "skypilot". (b) The panel runs to 2026-11-01, a partial month. Its 1,861 rows have no CPI and drop out of estimation silently through the null real price (`cleaning_report.md`; `hedonic.py:70`). That is fine, but the sample definition should say so. (c) The outlier flag compares each price with the chip-month-contract median *across providers and regions* (`panel.py:295-303`). In cells with two or three providers it can flag a legitimate provider-level price. Report which providers the 169 flagged rows come from.
**What would resolve it.** Inspect the raw 2026-06/07 Google rows, document the filter in `decisions.md`, and add a provider breakdown of the outlier flags to the cleaning report.

Draft response (Claude, for AJ to confirm or rewrite): Accepted. (a) The June 2026 $4.20 rows are already in open_questions; the robustness run drops July only. (b) The partial November 2026 month is stated in the sample definition (Decision 23). (c) A provider breakdown of the outlier flags is left for the cleaning report.

Response (AJ):

---

## Minor (code)

### 15. Small coding issues

- `cr1_se` and `wild_cluster_bootstrap_many` set k = the number of non-absorbed regressors (`hedonic_core.py:123-124, 168-169`). Month and provider-region FE are not nested in chip clusters, and the usual convention (Stata, pyfixest) counts non-nested FE in k. With n = 20,185 the effect is small, but say which convention is used.
- `twoway_se` silently falls back to V_a when V_a + V_b − V_ab < 0 (`hedonic_core.py:136-137`). Log how often this happens.
- `EVENTS` (`hedonic.py:34-40`) leaves h200 out, so h200 silently becomes a never-treated control (point 6). If that is intended, make it explicit.
- p-values of exactly 0 should print as < 1/(B+1) (point 7).
- `cohort_paths` uses normal-approximation CIs with CR1 by provider-region (`hedonic.py:362-378`), a different inference method from every other table. Label it in the figure or table note.
- Bin labels assume nonnegative ages (`hedonic.py:111`, `measure.str.slice(3)` in `baseline_bins`). That is fine today (0 pre-release rows), but add an assertion.

Draft response (Claude, for AJ to confirm or rewrite): Noted. Minor. The k convention is documented here: non-absorbed regressors only, a small difference at n = 20,185.

Response (AJ):

---

## Suggested order of work

1. Points 2 and 4 first. They are interpretation and reporting errors, can be fixed without new estimation, and could otherwise reach the memo or paper wrong.
2. Point 1 (chip-trend robustness, vintage permutation) and point 7 (WCR, CR2, design Monte Carlo). Together these decide whether the shape result is a finding.
3. Point 3 (repricing-event decomposition and validation against permitted marketplace evidence) and point 6 (GA dates, stacked design). These decide what the paper can claim about economic life and about H2.
4. Everything else.
