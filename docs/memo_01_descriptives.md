# Memo 01: what the raw price panel shows

Draft by Claude Code, 2026-11-11, for AJ to review (Decision 17). No regressions yet. Every number
here comes from `docs/cleaning_report.md` or `paper/tables/p4_descriptive_facts.csv`, both rebuilt
by `make data`. Readings marked **[AJ to confirm]** are interpretations, not results.

## The panel

`data/processed/panel.parquet` holds **24,210 listing-months** from October 2017 to November 2026.
Each row is one posted price for a provider, SKU, chip, GPU count, region, contract type and term
in one month, in USD per GPU-hour. It is built from 61,873 raw rows. Spot prices recorded by zone
become one regional median per day, and daily observations become one monthly median (your
choices, Decision 22). Where two collectors saw the same offer in the same month, the more direct
source is kept. The 239 dropped rows matched the kept price with a median gap of 0.00%, and 98% were
within 5%.

- **By contract:** 9,859 on-demand, 11,865 spot, 1,108 one-year reserved, 1,197 three-year
  reserved and 181 other listing-months.
- **By provider type:** 22,672 hyperscaler and 1,538 neocloud listing-months. The panel is
  overwhelmingly hyperscaler list prices, because Google, AWS and Azure publish every region and
  SKU. Neocloud history comes from archived pages (Lambda, CoreWeave, Paperspace).
- **Flags, kept rather than dropped:** the L40S has no age (Epoch has no release date for it; 2,085
  listing-months); 169 listing-months are price outliers (over 4x or under a quarter of their
  chip-month-contract median); no listing predates its chip's release month.

## Figure 4a: price by chip over time

Hyperscaler on-demand list prices sit well above neocloud prices for the same chip. Across the
months where both types list a chip, the median hyperscaler-to-neocloud ratio is 1.61 for the
V100, 2.34 for the A100 40GB, 1.92 for the A100 80GB and 3.10 for the H100 SXM. The H200 is the
exception at 0.73, over 20 months in which CoreWeave is the only neocloud listing it.

Hyperscaler list prices are sticky: AWS's V100 price is flat from 2017 to 2023, then moves in
steps. Many of the jumps in the median are **composition**, not repricing. A provider enters or
leaves, or a collector starts recording new regions (the live Azure collector adds many regions
from October 2026). **[AJ to confirm]** This is the main reason the hedonic model needs provider
and contract controls before any age profile is read off the raw medians.

## Figure 4b: real price against age

In 2025 dollars, the LOWESS fit of on-demand listings falls with age for the older chips. The V100
goes from $4.22 at 3 months to $2.72 at 111 months, and the A100 40GB from $3.09 at 6 months to $2.73 at
77 months. The A100 80GB is roughly flat ($4.19 at 18 months, $4.12 at 71). The newer chips *rise*
with age in the raw data: the H100 SXM goes from $6.64 to $10.61 (4 to 49 months) and the H200 from $7.04 to
$11.47 (2 to 23 months).

**[AJ to confirm]** The rising profiles for new chips are what the identification problem looks like
in raw data. Age moves one-for-one with calendar time and with which providers list a chip:
hyperscalers list the H100 later and at higher prices than neoclouds, and 2026 is a tight market.
None of this is an age effect, which is why Phase 5 runs four identification strategies rather than
reading age off these curves.

## Figure 4c: dispersion across providers

In a typical month the most expensive provider's median on-demand price is 2 to 3.5 times the
cheapest's. The median ratio is 3.10 for the V100, 2.67 for the A100 40GB, 2.47 for the A100 80GB, 3.52
for the H100 SXM, 2.08 for the B200 and 1.73 for the H200. Price dispersion is large and persistent,
consistent with list prices that are not arbitraged. **[AJ to confirm]**

## Figure 4d: against the getdeploying.com index

Over the 13 months where both exist, our median on-demand price is above getdeploying's median.
The ratio is 1.20 for the V100, 1.71 for the A100, 3.47 for the H100, 1.56 for the H200 and 1.57 for the B200.
getdeploying covers many more neoclouds and marketplaces, so its median is lower; ours is weighted
towards hyperscaler list prices. getdeploying pools A100 40/80GB and H100 SXM/PCIe, so those
comparisons are approximate. The level gap is the posted-versus-market wedge the proposal flags.
It argues for estimating profiles by provider type. **[AJ to confirm]**

## Things to check before Phase 5

- **Google H100 in SkyPilot's July 2026 catalog.** The accelerator-only on-demand price falls to
  about $4.20 in 12 of 19 regions (7 in June, none in August), against $10-11 elsewhere. Our parse
  matches the raw file, so the value is SkyPilot's. The cause is unknown; Phase 5 should check that
  results survive dropping that snapshot.
- **The live window is short locally.** Live rows cover 31 October to 10 November 2026; the droplet
  has more. November 2026 is a partial month with no CPI yet (1,861 listing-months without a real
  price).
- **Neocloud coverage is thin** (1,538 listing-months), so any neocloud-only profile rests on
  Lambda, CoreWeave and Paperspace's archived pages.
- **L40S age** needs a release date; it is a robustness chip, so Phase 5 can proceed without it.
