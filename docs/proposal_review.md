# Proposal review

Reviewed 2026-10-31 against proposal rev 18. Figures come from
[probe_unlisted_sources.md](probe_unlisted_sources.md), which
`notebooks/probe_unlisted_sources.py` regenerates. Nothing here has changed the proposal, and
Decision 1 (H1–H4) stands.

The project is worth doing. The hypotheses, stop conditions and range-based restatement are all
stronger than this kind of proposal usually has. The largest problem is one the risk table
understates: most posted GPU prices barely move, so a "market-implied" estimate built on them would
mostly measure pricing habits. That can be fixed now, cheaply, by changing which prices the
estimate rests on.

## Most posted prices do not move

On-demand prices changed at 6 of 44 sampled intervals across eight series. AWS spot prices for the
same chips changed at 20 of 21.

| Series | Chip | First sample | Last sample | What happened |
| --- | --- | --- | --- | --- |
| Azure on-demand | A100 | $3.40, Jul 2022 | $3.40, today | No change; the API dates this price to Mar 2021 |
| Azure on-demand | H100 | $12.29, Dec 2023 | $12.29, today | No change since the date the API gives |
| AWS on-demand | V100 | $3.06, Dec 2022 | $3.06, Mar 2026 | No change on a chip launched in 2017 |
| AWS on-demand | H100 | $12.29, Dec 2023 | $6.88, Oct 2026 | One 44% step between May and Oct 2025 |
| AWS on-demand | A100 | $4.10, Dec 2022 | $2.75, Oct 2026 | One 33% step in the same window |
| AWS spot | H100 | $9.40, Dec 2023 | $4.05, Oct 2026 | Low of $2.34 in Mar 2026, then up |
| AWS spot | V100 | $1.14, Dec 2022 | $0.37, Mar 2026 | Moves at every sample |
| Lambda on-demand | A100 | $1.10, Jun 2023 | $1.99, Aug 2026 | Rose 81% as the chip aged |
| Lambda on-demand | H100 | $3.49, May 2024 | $3.99, Aug 2026 | Fell to $2.99, then rose |

Three consequences follow.

- **Pooling biases the result toward "chips hold value".** Rows that cannot fall pull g(a) flat, and
  that reads as a bull finding for purely mechanical reasons. Estimating by provider type, which
  the plan already does, helps but does not cure it.
- **The real sample is repricing events, not rows.** A hyperscaler series with one price change in
  four years is one observation, however many monthly rows it produces.
- **Age effects are not monotone in this window.** Lambda's rent on A100 rose while the chip went
  from about 3 to 6 years old. The panel will end inside a 2026 price rise, so the last year will
  carry heavy weight in any fit.

**Recommended change.** Define the estimation sample as prices that clear, within what the terms
of use allow: hyperscaler spot, neocloud list prices and reserved prices, plus marketplace prices
only if written permission arrives (see the next section). Report hyperscaler on-demand separately
as a series of repricing events. Treat the paywalled indices as potentially core rather than
validation only, which makes confirming VCU's Bloomberg access the most valuable non-code task this
month.

## Terms of use: a Phase 0 stop condition was met

Phase 0 says to stop if a core source forbids automated access, and for the live layer one does.
[data_sources.md](data_sources.md) has the clauses. This is a reading of the terms, not legal advice.

| Source | Live collection | Wayback copy | Publishing the data |
| --- | --- | --- | --- |
| Vast.ai | Forbidden without a written agreement | Unresolved: the terms reach data "made available through the Website" | Forbidden, including any "index, benchmark, pricing-comparison service" |
| Oracle | Forbidden on oracle.com | Not addressed | Forbidden for site materials |
| RunPod | Forbidden for the site; unclear for the keyed API | Not addressed | Forbidden as a compiled database from the site |

Three things follow.

- **The proposal's two named live examples are both affected.** Vast.ai and RunPod are the sources
  the Data table names for live collection. The proposal's own mitigation, dropping sources that
  prohibit collection, removes its only true marketplace.
- **"Publish derived aggregates" may not rescue Vast data.** Its index clause covers use of the
  data, not only redistribution of it, so an aggregate could still be caught. This is unresolved.
- **Hyperscaler spot becomes the main moving series.** It is still set by the provider, but it does
  respond to capacity. The Azure API needs no key, Lambda permits rate-limited crawling, and
  getdeploying.com offers a CC BY 4.0 weekly file. That file covers only about 53 trailing weeks.

**Recommended path.** Ask Vast.ai and RunPod for written research permission now, since both sets
of terms allow for it. Build the live collector on the clear sources meanwhile, and add a blocked
source only with permission in hand. `config/providers.yaml` now marks those three as blocked.

One disclosure: during the audit, one unauthenticated request reached Vast's offers endpoint to
confirm its fields. My brief allowed one sample call per public API. No Vast data was kept, and the
endpoint is undocumented, so it must not be used.

## Identification and inference

**1. Provider clustering is the wrong level.** Age has one value per chip-month across all
providers, so the variation that identifies g(a) sits at chip × month. A chip-specific shock such
as the 2023 H100 shortage hits every provider at once, and provider clustering does not see it.
Two-way provider × month clustering does not either, because month effects absorb only what is
common across chips. There are at most nine chip ids, so conventional cluster-robust errors at
that level are unreliable. Use a wild cluster bootstrap or randomization inference at the chip
level, and expect wider bands than provider clustering would give. Nine providers is also too few
for standard provider clustering.

**2. Strategy 4 cannot answer "how fast".** In log prices, a constant geometric rate is exactly the
linear term of g, which is the part Hall (1968) says is unidentified. Shape-only estimation can
show departures from geometric decline, which speaks to H1's shape. It cannot supply RQ1's annual
rate, so every rate in the paper rests on strategies 1 to 3 or on the assumed linear term.

**3. The strategies are less independent than "agreement is the evidence" implies.** Strategy 1
fits three specs across five core chips, leaving almost no degrees of freedom; use a single quality
index such as MLPerf throughput. Strategies 2 and 3 both draw on the same few frontier changes:
V100→A100, A100→H100 and H100→B200. The first of those falls in the thinnest data. Agreement among
methods sharing the same three events is weak evidence, so say so in the paper. For H2 also use
announcement dates, because markets knew about successors long before GA.

**4. Add a fifth strategy: the term structure.** On a given date, a reserved price against an
on-demand or spot price for the same chip is the market's own forecast of the rent path, and that
comparison does not depend on Hall's age–time collinearity. Azure today lists H100 at $12.29
on-demand and $7.87, $5.40 and $4.92 per GPU-hour on 1, 3 and 5 year terms. The catch is that a
long term also buys guaranteed utilization, so the discount is not pure expected decline. This
reframes H3 from a wedge to a term structure, so it changes a logged hypothesis and is your call.

**5. H4's claim about time effects is too strong.** Month effects absorb only shocks common to all
chips. A shortage concentrated in one generation loads on that chip's age profile. Between late
2025 and August 2026 Lambda raised A100 by 54% and H100 by 33%, which is common in direction but
not in size.

## Valuation and restatement

**6. Chip age is not asset age.** Age here counts from a chip's GA date, but firms kept buying H100s
for years after GA. An H100 bought in 2025 is around year 2 on the proposal's curve and brand new
on the books. Step 4 needs each purchase cohort to enter the curve at its purchase date.

**7. Check that V(0) matches cost.** The proposal compares V(a) with straight-line book value
without testing whether the present value of net rents at purchase equals what the hardware cost.
If it far exceeds cost, the rents contain scarcity profits, and their decline is not depreciation.
If it falls short, the comparison needs normalizing. Compare V(a)/V(0) with the straight-line path,
and report V(0)/cost as a result in its own right.

**8. Lead with value lost by age, not T\*.** T\* is a tail statistic, observed for essentially one
chip and very sensitive to how opex is defined. As illustration only, using assumed inputs, power
for an H100 system at about 10 kW per 8 GPUs, PUE 1.3 and 8¢/kWh is about $0.13/GPU-hour. Adding an
assumed $150/kW-month colocation fee takes it to about $0.40. A hyperscaler with a sunk building
and a neocloud in rented space therefore get very different T\*. Headline the share of value lost
by years 1 to 6 and a straight-line-equivalent life, the book life that best matches the curve.
Keep T\* as a secondary result. If power is the binding constraint, also test retirement against
the rent per kW of the newest chip, since that is the mechanism in the bear case.

**9. Smaller fixes to Step 3.**

- `TDP × PUE` undercounts power, because a GPU's TDP excludes CPUs, memory, networking and fans. Use
  system power per GPU, as the example above does.
- One `u` across contract types is inconsistent. A reserved price is paid whether or not the GPU is
  busy, so u is close to 1 there. An on-demand list price only earns when sold.
- Utilization should fall with age, or V(a) will be overstated in the tail.
- Floor each year's net rent at zero, because an operator can switch off. As written, the sum also
  includes year T, a flow that is at or below zero by the definition of T\*.
- The opportunity-cost argument for hyperscalers holds against long-term contract rents, not
  posted on-demand.

## Data plan

**10. Three free histories are not in the proposal.** Each cuts the Wayback risk for hyperscalers,
and adding any of them needs your approval under rule 7.

| Source | Coverage found | What it adds | Caveat |
| --- | --- | --- | --- |
| [AWS Price List offer files](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json) | 123 versions, Dec 2015 to Oct 2026, about monthly | Official AWS on-demand and reserved history, reaching V100's early life | About 154 MB per region per version, so filter while streaming. Terms for this host were not found |
| [Azure Retail Prices API](https://prices.azure.com/api/retail/prices) | Current prices only | Free daily live feed for on-demand, spot and reserved | Not a history, and its date field is unreliable (see item 12) |
| [SkyPilot catalog repo](https://github.com/skypilot-org/skypilot-catalog) | Jul 2022 to today, about 13,900 commits | Dated AWS, Azure, GCP and Lambda prices, including AWS spot, which [AWS's own history tool](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances-history.html) keeps for only 90 days | The repo shows no license, so use it for research and do not republish it. Its Vast and RunPod files stay out unless those providers agree. Update frequency varies, and there are gaps to map (around Jun–Sep 2025 for AWS) |

With these, the AWS and Azure Wayback parsers can be dropped, and Phase 2 can concentrate on Lambda,
CoreWeave and Paperspace. That also removes the likeliest schedule overrun.

The irony matters, though. These sources mostly fill in the series that barely move. The prices
that do move before 2023 remain the hard part, and the terms above make it harder.

**11. The Phase 0 gate counts captures, not prices.** 6 of 9 providers passed, but the test cannot
see a JavaScript shell with no prices in it. AWS's on-demand page is a likely example. Phase 0 says
not to download page contents, so I did not. One snapshot per provider per year, about 50 pages,
would settle whether Phase 2 is viable before you commit four weeks to it.

**12. Fix these before Phase 1 writes its schema.**

- Add an availability field. The proposal plans to collect availability, but the Phase 1 schema has
  nowhere to put it, and a price with nothing in stock is not a real price.
- Add a source kind (list, spot, marketplace offer) so the sample in the recommended change can be
  defined from the data.
- Decide weighting early. Any marketplace feed returns one row per machine offer, so thousands of
  rows could swamp a single AWS price. Aggregate to chip × provider × contract × month before
  regressing.
- Azure's reservation rows hold the whole-term price with the unit "1 Hour". Read literally, a
  3-year H100 reservation would be about $1.1M per hour.
- Azure's `effectiveStartDate` is not a last-change date. V100 shows 2026-01-01 although SkyPilot
  has the same $3.06 back to 2022.
- `reserved_5y` is missing from the contract types, and Azure sells 5-year H100 terms.

**13. You may not need to buy a VPS.** Your DigitalOcean droplet and the M4 Mac mini already run
around the clock. A daily job this small could sit on either, which removes the $30–70 VPS line.
The cost is coupling a 22-week dataset to a host that does other work.

## Claims to soften

"Any outcome is publishable" holds for a working paper, but less so for journals. A paper whose
main result is "the strategies disagree" needs informative bounds to land. Likewise "market-implied"
should stay in the title only if the recommended sample change is made; otherwise "posted-price
implied" is the accurate term.

## Leave as is

- The dated hypotheses, stop conditions and refusal to give a point estimate for the restatement.
- Treating identification as the paper's central problem, and showing strategies side by side.
- The rule that you make every research decision and write the argument.
- The adversarial review after Phase 5. Run it on the data choices too, not only the code.

## Fact check

Of 18 claims checked, 10 match a primary source, 2 are wrong and 6 have no primary support yet. The
eight-row table mostly holds, and the full evidence is in
[proposal_fact_check.md](proposal_fact_check.md). These need changing before the proposal circulates.

| Claim | Problem | Fix |
| --- | --- | --- |
| All four hyperscalers reached 5–6 years | **Wrong for Meta**, which moved from a 4–5 range to 5.5 in 2025 and never reached 6 | "Microsoft, Alphabet and Amazon reached 6 by 2024; Meta reached 5.5 in 2025" |
| "Nvidia points to A100s rented through 2029" | **Wrong attribution.** The contract is CoreWeave's, one contract, and Nvidia's CEO only amplified it | "CoreWeave said in Aug 2026 it signed an A100 contract into 2029" |
| CoreWeave rebooked H100s at about 95% | Not in any transcript opened; press attributes it to a CNBC interview not yet found | Find the interview or drop it |
| Burry's 2–3 year cycle | One source says this figure is not his; the original post could not be read | Keep the $176B as reported and drop "2–3 years" until read |
| Nebius ~$167.6M | The years match, but this figure is not in the 20-F or Q1 6-K | Cite the 6-K for the change and drop the dollar figure |
| H100 forward $1.90→$2.64, and the $2 index gap | Both come from an article by Compute Desk's founder; the forward is Compute Desk's own series and the gap is about B200 | Attribute them, and say four indices, the article's own count |
| "Roughly 17 useful-life changes" | This is a vendor's row count, and it includes small firms and omits Microsoft's July 2020 change | Replace it with the count from `docs/useful_lives.md` in Phase 7 |

The bull case now has no primary support for its 95% figure and rests on one A100 contract, while
the bear case's cycle length may not be Burry's. That helps the paper's framing: the public debate
is thinner than it looks.

One finding also affects Step 4. Most firms disclose lives for a pool ("servers and network
equipment"), and Amazon's 2025 cut covers a subset. The restatement therefore compares a GPU curve
with a life set for a mixed pool, so the GPU share assumption also needs to cover the
non-GPU servers in that pool.

## Literature

PENDING: filled in from [related_work.md](related_work.md).

## Prior work in this account

`~/Documents/gpus-substack` contains an older GPU depreciation model, but its "real market
parameters" are `np.random.uniform` draws. Nothing from it should enter this project (rule 1).
