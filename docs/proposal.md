# Rental-Implied Depreciation of AI Accelerators: Why the Estimates Disagree

Research proposal · working draft · 2026-10-31 · @AJ

## Summary

This project explains why published estimates of AI accelerator depreciation disagree, from about 11% to about 40% a year, using what people pay to rent NVIDIA V100, A100, H100, H200 and B200 chips. It then compares the rental-implied path to the 5 to 6 year straight-line lives the largest cloud companies use in their financial statements.

**Method in one line:** put the published rates on one basis, build a 2020–2027 panel of GPU rental prices by contract and provider type, report each chip's observed price path, estimate age–price profiles to project newer chips, convert rents into asset values net of power and operating cost, and restate earnings firm by firm by purchase cohort.

**Outputs:** a short reconciliation note around mid-January, a 25–35 page working paper posted to SSRN and arXiv (q-fin), a public replication repository, and an open GPU rental-price dataset.

**Status:** independent pre-advisor draft. All work through a complete first draft is done solo; a VCU finance or accounting faculty member reviews it before anything is posted.

## Motivation

Reported earnings at the largest AI spenders now hinge on one management estimate: how many years a server lasts. From 2020 to 2024, Microsoft, Alphabet and Amazon stretched server lives to 6 years. Meta reached 5.5 in 2025. In January 2025 Amazon partly reversed, cutting a subset of servers from 6 to 5 years and citing "an increased pace of technology development, particularly in the area of artificial intelligence and machine learning" ([The Register](https://www.theregister.com/2025/02/07/amazon_q4_fy_2024/)).

**Selected server useful-life changes, newest first** ([American Compute compilation of 10-K/20-F filings](https://www.amcompute.com/gpu-depreciation-schedules), updated Oct 10, 2026):

| Effective | Company | Change | Reported effect |
| --- | --- | --- | --- |
| Jan 2026 | Nebius | 4 → 5 years | Not quantified in the 20-F or Q1 2026 6-K |
| Jan 2025 | Amazon (subset) | 6 → 5 years | $1.4B more 2025 depreciation |
| Jan 2025 | Meta | 5 → 5.5 years | $2.92B less 2025 depreciation |
| Jan 2024 | Amazon | 5 → 6 years | $3.2B less 2024 depreciation |
| Jun 2024 (FY2025) | Oracle | 5 → 6 years | $733M lower FY2025 operating expenses |
| Jan 2023 | Alphabet | 4 → 6 years | $3.9B less 2023 depreciation |
| Jan 2023 | CoreWeave | 5 → 6 years | $20M lower 2023 expenses |
| Jul 2022 (FY2023) | Microsoft | 4 → 6 years | $3.7B higher FY2023 operating income |

**The bear case.** Michael Burry estimates about $176B of understated depreciation from 2026 to 2028, as reported in the press; the original post has not been read ([Value the Markets, Sept 2026](https://www.valuethemarkets.com/analysis/gpu-depreciation-debate-behind-this-weeks-ai-dip)).

**The bull case.** CoreWeave said in August 2026 that it signed an A100 contract running into 2029, and Nvidia's CEO amplified the claim ([CoreWeave Q2 2026 call](https://www.webull.com/news/15426275319522304)). This is one contract, not a fleet.

**Why it is still open.** The first estimates have now appeared, and they disagree: about 39.9% a year ([Amissah-Ocran & Ayumu 2026](https://doi.org/10.54660/.ijmrge.2026.7.5.49-62)), 24–27% ([Chincholikar & Chawla 2026](https://zenodo.org/records/21894454)), 17–32% ([Huang 2026](https://zenodo.org/records/22053861)), −15% to flat ([CCIR 2026](https://ccir.io/research/rental-rates-by-generation)) and 11% ([Watkins 2026](https://www.jaredwatkins.com/posts/2026/08/ai-depreciation-curve/)). They measure different things: resale value, net cash flow or posted rent, at one date or along a path. No study yet puts them on one basis.

**Why now.** The data finally exist. Compute Desk's founder counts four index providers, three of them on the Bloomberg Terminal (Silicon Data, Ornn AI, Compute Desk), whose B200 quotes started more than $2/hour apart, which shows contract type and supplier matter ([Compute Desk analysis](https://www.kucoin.com/news/flash/gpu-pricing-disarray-four-indices-diverge-market-lacks-consensus)).

**Most posted prices barely move.** Across eight on-demand series sampled from 2022 to 2026, the price changed at 6 of 44 intervals, while AWS spot prices for the same chips changed at 20 of 21. Azure's A100 has stayed at $3.40 per GPU-hour since at least July 2022, and Lambda's A100 rose 81% as the chip aged. Estimates built on posted on-demand prices may therefore mostly measure pricing habits.

## Research questions and hypotheses

The core paper answers RQ1–RQ3. RQ4 is an optional extension, included only if time allows.

1. **RQ1: Age–price profile.** Holding chip quality, contract type and market conditions fixed, how fast does a GPU generation's rental price fall as it ages?
2. **RQ2: Economic life.** What useful life and depreciation pattern do those rents imply once power, hosting and utilization are netted out?
3. **RQ3: Accounting gap.** How far is market-implied depreciation from reported straight-line depreciation, and what does the gap do to each firm's operating income and EPS?
4. **RQ4 (extension): Market response.** Do stock prices or analyst forecasts react when firms change useful-life estimates?

**Hypotheses.** Write these into the decision log with a date before running any regression, so the results cannot quietly reshape them.

- **H1: Front-loaded decline.** Value falls fastest in years 1–2, closer to geometric than straight-line. If so, straight-line book values overstate asset value early in life even when the total life is right.
- **H2: Obsolescence shocks.** A successor reaching general availability (H100 for A100, B200 for H100) causes a discrete drop in the predecessor's rent beyond the smooth age trend.
- **H3: Contract-type wedge.** Spot and on-demand prices fall faster with age than 1-year reserved prices, so the implied life depends on which market you read.
- **H4: Demand regimes.** Shortages temporarily mask age effects. H100 1-year forward prices rose from $1.90 to $2.64/hour in early 2026 ([Compute Desk analysis](https://www.kucoin.com/news/flash/gpu-pricing-disarray-four-indices-diverge-market-lacks-consensus)). Time fixed effects should absorb this, leaving age profiles stable across sub-periods.

## Contribution and related literature

The paper makes three contributions:

1. **A reconciliation.** Published rates go on one basis, showing how much of the spread comes from the price series, the identification assumption and the step from rent to value.
2. **Age slopes by contract and provider type,** from an open multi-contract panel that separates prices that clear from prices that sit.
3. **A firm-by-firm earnings restatement** under a rental-implied schedule, entering each purchase cohort at its purchase date, reported as a range across assumptions rather than one headline number.

**Where it sits in the literature:**

- **Depreciation from vintage prices.** Hulten & Wykoff (1981) estimate depreciation from used-asset prices by age. Hall (1968) shows that age, vintage and time effects cannot all be identified at once, which is this paper's central econometric problem. Oliner (1993), Doms et al. (2004) and Geske, Ramey & Shapiro (2007) apply the method to mainframes and PCs. Geske et al. split value loss into aging, obsolescence and revaluation, the decomposition this paper adapts.
- **Hedonic price measurement.** Berndt & Griliches (1993) and Triplett (2006) on quality-adjusted computer prices.
- **Rental markets for durable capital.** Gavazza (2011) on aircraft leasing is the closest analog: an expensive asset, an active rental market and fast technological change.
- **Accounting estimates.** Keating & Zimmerman (1999) on why firms change depreciation policy and what it signals.
- **Practitioner work.** The GPU indices (Silicon Data, Ornn AI, Compute Desk, SemiAnalysis) and sell-side and blog analyses of the debate. The paper's pitch to this audience: a transparent, reproducible version of what they argue about.

**Direct predecessors.** This paper is not the first to apply these methods to AI accelerators. [Amissah-Ocran & Ayumu (2026)](https://doi.org/10.54660/.ijmrge.2026.7.5.49-62) fit a rent–age profile at one date. [Chincholikar & Chawla (2026)](https://zenodo.org/records/21894454) run a Hulten-Wykoff profile on resale prices and say their work is not an audit of any firm. [Huang (2026)](https://zenodo.org/records/22053861) measures cash-flow decay on one spot marketplace. [CCIR (2026)](https://ccir.io/research/rental-rates-by-generation) rebuilt on-demand rates from web archives. [Dutta & Patatoukas (2026)](https://doi.org/10.2139/ssrn.7420380) already use "market-implied life" for a figure drawn from equity values, which is one reason this paper says "rental-implied".

## Data

The core dataset is a panel of GPU rental prices built from official price files, catalog history and archived pages, extended forward with live collection. Everything else either controls for quality, supplies costs, or feeds the accounting step.

| Source | What it gives | Access | Role |
| --- | --- | --- | --- |
| [AWS Price List offer files](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/index.json) | On-demand and reserved list prices, about monthly since December 2015 | Free | Core history, hyperscaler list prices |
| [SkyPilot catalog history](https://github.com/skypilot-org/skypilot-catalog) (AWS, Azure, GCP and Lambda files only) | Dated list and spot prices since July 2022, including AWS spot | Free; no license stated, so not republished | Core history, spot prices |
| Archived pricing pages via the Internet Archive Wayback Machine (CDX API) | Posted $/GPU-hour for Lambda, CoreWeave and Paperspace | Free, rate-limited | Neocloud history |
| Live collection: Azure Retail Prices API, AWS offer files, Lambda's pricing page, and SkyPilot for AWS spot and Google Cloud | Daily list, spot and reserved prices | Free | Recent high-frequency panel |
| Published tables: [Huang (2026)](https://zenodo.org/records/22053861) and [Chincholikar & Chawla (2026)](https://zenodo.org/records/21894454) | Marketplace cash-flow rates, utilization and executed resale prices | Free, CC BY | Comparison series, cited rather than rebuilt |
| Published indices: [getdeploying.com datasets](https://getdeploying.com/dataset) (CC BY, downloaded by hand); Silicon Data, Ornn AI and Compute Desk on Bloomberg (if VCU has a terminal); SemiAnalysis 1-year H100 contract index | Aggregate price levels, some by contract term | Free, Bloomberg or paywall | Validation, possibly core |
| NVIDIA datasheets and MLCommons MLPerf results | Launch and GA dates, memory, bandwidth, BF16 TFLOPS, TDP, benchmark throughput | Free | Quality controls |
| U.S. EIA electricity data (API) | Monthly commercial and industrial $/kWh by state | Free API key | Operating cost |
| SEC EDGAR XBRL (companyfacts API) and 10-K text | PP&E, depreciation, capex, useful-life disclosures | Free | Accounting restatement |
| CRSP via WRDS (if VCU has access), else a free price source | Daily stock returns | WRDS or free | RQ4 only |

**Excluded by terms of use:** Vast.ai, RunPod and Oracle restrict automated collection, so nothing is collected from them. Huang's published tables supply the marketplace comparison instead.

**Unit of observation:** one posted price for a (provider, SKU, chip, GPUs per instance, interconnect, region, contract type, date) combination, in $/GPU-hour. Multi-GPU instance prices are divided by GPU count.

**Chips in scope:** V100, A100, H100, H200 and B200 as the core; AMD MI300X and NVIDIA L40S as robustness checks.

**Known weaknesses and how each is handled:**

- **Posted vs. transaction prices.** List prices, especially hyperscaler on-demand, are not what large customers pay under negotiated contracts. Estimate profiles separately by provider type, and check levels against transaction- and survey-based indices.
- **Archive gaps and layout changes.** Snapshots are irregular and JavaScript-rendered pages may not archive cleanly. Sample monthly, publish a coverage heatmap, write per-provider parsers, and spot-check by hand.
- **Composition and survivorship.** Providers enter and exit, and cheap ones may be the ones that vanish. Use provider fixed effects and a balanced-panel robustness check.
- **Bundling.** Instance prices include CPU, RAM, storage and networking. Control for host specs or adjust to a GPU-only share.
- **Short history for new chips.** B200 has under two years of prices, so its long-run path must be borrowed from V100 and A100. State this assumption explicitly and show how results move without it.
- **Terms of service.** Some sites restrict scraping or redistribution. Where raw data cannot be shared, publish derived aggregates.

## Methodology

The method has four steps: estimate age–price profiles, deal with the identification problem, turn rents into asset values, and restate earnings. A fifth step (event study) is optional.

### Step 1: Hedonic rental-price model

```latex
\ln p_{i,c,t} = \alpha_c + g(a_{c,t}) + \delta_t + X_i'\beta + \varepsilon_{i,c,t}
```

- p = posted price in $/GPU-hour for listing i of chip c in month t.
- a = months since chip c reached general availability. g(a) is the age profile, the object of interest.
- α = chip (vintage) fixed effect; δ = month fixed effect.
- X = provider type (hyperscaler, neocloud, marketplace), contract type and term, interconnect, GPUs per instance, region, host specs.
- Inference at the chip level, because age has one value per chip-month: a wild cluster bootstrap or CR2, with provider clustering shown for comparison.

### Step 2: Identification

Age equals calendar time minus vintage, so with chip and month fixed effects the linear part of g cannot be identified (Hall 1968). This is the hardest part of the paper. Start from each chip's observed price path, which needs no such assumption. Then run all four strategies to project newer chips from older ones and report them side by side; disagreement gets reported, not hidden. Strategies 2 and 3 draw on the same few frontier changes, so their agreement is weak evidence. The leading published estimates assign the whole secular decline to age, so sweeping that linear term in strategy 4 is new.

1. **Quality-adjusted vintage.** Replace the chip fixed effect with observed specs (BF16 TFLOPS, memory bandwidth, memory). The vintage effect becomes a function of specs, which frees up the age effect.
2. **Frontier-relative obsolescence.** Add each chip's performance relative to the best chip available that month, measuring obsolescence directly (after Geske, Ramey & Shapiro 2007).
3. **Successor event study.** Track a chip's price around its successor's GA date against a comparison series such as reserved prices or non-NVIDIA chips. This tests H2.
4. **Shape only.** Keep full fixed effects, identify only the curvature of g, and pin the linear term with a stated assumption shown across a range.

### Step 3: From rents to asset values and economic life

```latex
V_c(a) = \sum_{k=0}^{T-a} \frac{8760 \left[ u \, p_c(a+k) - o_c(a+k) \right]}{(1+r)^{k+1}}
```

- V = value of a chip at age a (years), the present value of its remaining net rent. 8760 = hours per year.
- u = utilization. o = operating cost per hour: TDP (kW) × PUE × electricity $/kWh, plus hosting and maintenance. r = discount rate.
- Economic life T* = the first age at which u × p falls to o or below.
- Market-implied depreciation in year a = V(a) − V(a+1), compared with straight-line book depreciation over 5, 5.5 and 6 years.
- For a hyperscaler using its own GPUs, the market rent is the opportunity cost, so the same valuation applies.

**Changes after review.** Multiply net rent by a survival curve S(a), stated as a range, because failed units earn nothing. Use system power per GPU rather than chip TDP. Set utilization by contract type and age. Floor each year's net rent at zero. Report V(0)/cost, because rents above cost contain scarcity profits rather than depreciation. Headline the share of value lost by years 1 to 6 and a straight-line-equivalent life, and keep T* as a secondary result.

**Sensitivity grid:** r ∈ {8%, 10%, 12%}, u ∈ {50%, 70%, 90%}, PUE ∈ {1.2, 1.4}. Rents beyond the observed ages of new chips are borrowed from older generations' estimated profiles. **Optional cross-check:** used-hardware resale prices give direct asset values.

### Step 4: Earnings restatement

Firms: Microsoft, Alphabet, Amazon, Meta, Oracle, CoreWeave, Nebius. None reports GPU assets separately, so estimate a GPU asset base from server capex and PP&E disclosures, with the GPU share of server capex as a varied assumption. Enter each purchase cohort at its purchase date, apply rental-implied depreciation and report the change in depreciation, operating income and EPS against reported figures.

### Step 5 (optional): Event study

Abnormal returns around the useful-life changes documented from filings since 2020. Nearly all were disclosed with earnings, so effects are confounded: treat this as descriptive only.

## Expected results

Any outcome supports a working paper, while journal placement will depend on how informative the bounds are.

- **Rents imply 5+ years with a front-loaded shape.** Book lives are defensible in length, but straight-line timing overstates early-life asset values. That is a narrower, sharper claim than either side of the debate makes.
- **Rents imply 2–4 years.** The paper quantifies the overstatement firm by firm, as ranges.
- **The identification strategies disagree.** Showing how much the answer depends on assumptions nobody in the debate states is itself the contribution.

**Planned headline exhibits:**

1. Price paths by chip generation, 2020–2027.
2. Estimated age profiles with confidence bands, by contract type.
3. Market-implied value curve against 5, 5.5 and 6 year straight-line schedules.
4. Firm-level change in depreciation and EPS across the sensitivity grid.

## Timeline

The plan runs 22 weeks from November 2, 2026: a reconciliation note around mid-January, a complete draft by March 21 and a posted working paper by April 5, ahead of spring 2027 graduation.

[embedded content: project timeline · 9 phases, 22 weeks]

The live collector is built in week 1 because current prices can't be collected after the fact; it then runs daily until April. Faculty review comes only after a complete draft exists.

## Budget and infrastructure

Expect roughly $60–150 out of pocket for the whole project. Compute is not the bottleneck: the historical pull is slow because of archive rate limits, not processing, so it runs for days on a cheap server.

| Item | Approx. cost | Notes |
| --- | --- | --- |
| Small VPS (1–2 vCPU, 2–4 GB RAM) | $5–12/month for ~6 months | Hetzner, DigitalOcean or similar; runs the daily collector and the Wayback pull |
| Off-server backups | $0–5/month | S3-compatible object storage; raw snapshots should stay well under 50 GB |
| Dataset release | $0 | GitHub for code; Zenodo for a citable DOI on the data |
| Bloomberg and WRDS | $0 | Through VCU if available; ask the business school library |
| Analysis | $0 | Regressions and valuation run on a laptop |

Check current VPS prices before signing up; the figures above are approximate.

## Risks and mitigations

The two risks most likely to hurt the paper are thin archive coverage before 2023 and gaps between posted and transaction prices. Both have workable fallbacks.

| Risk | Likelihood | Impact | Mitigation or fallback |
| --- | --- | --- | --- |
| Wayback coverage too thin before 2023 | Medium | High | Narrow to well-archived providers (AWS, Google Cloud, Lambda); lean harder on 2023+ and the live panel |
| Posted prices diverge from transaction prices | High | Medium | Split by provider type; validate against transaction and survey indices; frame claims as about the posted-price market |
| Identification strategies disagree sharply | Medium | Medium | Report the range as a finding (see Expected results) |
| GPU share of server capex is not disclosed | High | Medium | Present the restatement as a sensitivity table, never a point estimate |
| A similar paper appears first | Occurred | High | Repositioned around reconciling the estimates; watch SSRN, arXiv and Zenodo; post the reconciliation note early |
| Scraping blocked or terms conflict | Occurred | Medium | Prefer official APIs, respect robots.txt, keep request rates low; Vast.ai, RunPod and Oracle dropped |
| Scope creep | Medium | Medium | RQ4, extra chips and resale prices only after the core draft exists |
| Solo blind spots in the econometrics | Medium | High | Adversarial review at the end of Phase 5: a fresh Claude session critiques the identification from code and results alone |

## Deliverables and publication plan

The end product is a posted working paper with a public replication package, then a journal submission.

**Deliverables:**

- Working paper, 25–35 pages, in LaTeX.
- Public GitHub repository that rebuilds every figure and table from raw data with one command.
- Dataset on Zenodo with a DOI (derived aggregates where terms of service restrict raw data).
- Two-page plain-English summary for interviews and recruiting conversations.

**Publication sequence:**

1. Faculty review of the complete draft (VCU finance or accounting).
2. Post to SSRN and arXiv (q-fin.GN, cross-listed to econ.GN). First-time arXiv submitters may need an endorsement, which a faculty member can provide.
3. Submit to one journal at a time. Candidates to check for fit in Phase 8: Financial Analysts Journal or Journal of Financial Data Science (practitioner reach), Accounting Horizons (policy-relevant accounting), Economics Letters (a short version of the depreciation estimate), or an undergraduate research journal.
4. Present at a student research conference or a finance or accounting conference with a student session.

## Claude Code kickoff brief

Claude Code builds the pipeline and does the checks; you make every research decision and write the argument. Set up the repo once, then run one phase prompt at a time and review its output before moving on.

**Status, October 31, 2026:** Phases 0 and 2 are done, and Phase 1's collector runs daily, with backups and alerts still to set up. The prompts below predate the review, so where they conflict with this revised proposal, the proposal wins. The repository's `docs/proposal_review.md` has the reasoning.

### Setup (about 20 minutes)

1. Create an empty folder named `gpu-econ-life`, run `git init`, and link it to a private GitHub repo.
2. Export this doc as Markdown and save it as `docs/proposal.md`. Claude Code can't open this doc, but it can read that file.
3. Save the block below as `CLAUDE.md` in the repo root. Claude Code reads it automatically at the start of every session, so the rules stick.
4. Open Claude Code in the folder. For each phase, switch to plan mode, paste the phase prompt, read the plan, then approve. Review diffs before accepting them.
5. Start Phase 1 (the live collector) in week 1. Every day it isn't running is data you can never get back.
6. Keep a short note of what Claude Code did in each phase. Most journals and SSRN ask authors to disclose AI assistance, and this becomes your disclosure statement.

### CLAUDE.md

```markdown
# GPU Economic Life: project memory

## Goal
Estimate the market-implied economic life of AI accelerators (V100, A100, H100, H200, B200)
from rental prices and compare it to hyperscaler book depreciation. Output: an SSRN working
paper and a public replication package. Author: AJ (solo). Full proposal: docs/proposal.md.

## Non-negotiable rules
1. Never fabricate data, prices, dates, specs or citations. If a value is unknown or a source
   is unreachable, leave it missing, log it in docs/open_questions.md, and tell me.
2. data/raw/ is append-only. Never edit or delete raw files. Every raw file gets a sidecar
   .json with source URL, UTC retrieval timestamp and HTTP status.
3. Every number in the paper must trace to a script in src/ and a file in data/.
   No hand-typed results. Notebooks are for exploration only.
4. Verify every API endpoint and page structure against live documentation before coding
   against it. Do not rely on memory of endpoints.
5. Respect robots.txt and terms of service. Send a User-Agent with my contact email
   (<YOUR EMAIL>). At least 1 second between requests per host; exponential backoff on
   429 and 5xx.
6. Log every methodological choice in docs/decisions.md (date, choice, alternatives,
   reason) and every assumption with its value and source in docs/assumptions.md.
7. Ask me before: adding a data source, changing the unit of observation, changing a
   logged estimation spec, or deleting anything.
8. Small commits with clear messages after each working step. Run tests and ruff first.

## Stack
- Python 3.12, uv for environment and dependencies
- httpx for requests; selectolax or BeautifulSoup for parsing; Playwright only when a
  page needs JavaScript
- polars and duckdb for data; parquet for interim and processed files
- pyfixest or linearmodels for fixed-effects regressions; statsmodels otherwise
- matplotlib with one shared style file
- pytest and ruff
- Makefile targets: data, models, paper, all

## Layout
gpu-econ-life/
  CLAUDE.md, README.md, Makefile, pyproject.toml
  config/        providers.yaml, chips.yaml, assumptions.yaml
  data/raw/      append-only: wayback/, live/, indices/, specs/, eia/, edgar/
  data/interim/  parsed per-source parquet
  data/processed/ analysis panels
  src/gel/       collect/, parse/, build/, models/, accounting/, viz/
  tests/
  notebooks/     exploration only
  paper/         main.tex, references.bib, figures/, tables/
  deploy/        VPS setup and scheduler files
  docs/          proposal.md, data_sources.md, decisions.md, assumptions.md,
                 open_questions.md, research_log.md

## Conventions
- Prices: USD per GPU-hour, nominal, plus a CPI-deflated real column.
- Dates: UTC, ISO 8601. Monthly data keyed to the first day of the month.
- Chip ids: v100, a100_40gb, a100_80gb, h100_sxm, h100_pcie, h200, b200, mi300x, l40s.
- Provider types: hyperscaler, neocloud, marketplace.
- Contract types: on_demand, spot, reserved_1y, reserved_3y, other.
```

### Phase 0: Setup and source audit (week 1)

```text
Read CLAUDE.md and docs/proposal.md. Then:

1. Scaffold the repo exactly as CLAUDE.md describes: pyproject.toml (uv), ruff and pytest
   config, a Makefile with placeholder targets, the docs/ files with headers, and stub
   YAML files in config/.
2. Build docs/data_sources.md. For every source in the proposal's Data section, check the
   live documentation and record: access method, URL or endpoint pattern, auth, rate
   limits, robots.txt and terms-of-service notes on automated access and redistribution,
   earliest available date, and fields. Mark anything you could not confirm UNVERIFIED.
3. Put candidate pricing-page URLs in config/providers.yaml (AWS EC2 GPU instances,
   Google Cloud GPU pricing, Azure ND/NC pricing, Oracle GPU pricing, Lambda, CoreWeave,
   RunPod, Vast.ai, Paperspace). Query the Wayback Machine CDX API for each and report
   snapshot counts by year in docs/coverage_preview.md. Do not download page contents yet.
4. Literature check: search SSRN, arXiv, NBER and Google Scholar for work estimating
   depreciation, economic life or rental age-price profiles for GPUs or AI accelerators.
   List anything close in docs/related_work.md with links and a one-line summary.
5. Add decision #1 to docs/decisions.md: hypotheses H1 to H4 copied verbatim from the
   proposal, dated today.

Done when: the repo installs, `make test` passes, and data_sources.md,
coverage_preview.md and related_work.md are complete.
Stop and ask me if: a paper already does this; a core source forbids automated access;
or most providers have fewer than 6 snapshots a year before 2023.
```

### Phase 1: Live collector (weeks 1–2)

```text
Build the daily live price collector.

1. Define the canonical listing schema in src/gel/schema.py: retrieved_at, provider,
   provider_type, sku, chip, gpu_count, gpu_memory_gb, interconnect, region,
   contract_type, term_months, price_usd_per_hour_instance, price_usd_per_gpu_hour,
   vcpus, ram_gb, source_url, raw_file. Add validation tests (price > 0, gpu_count >= 1,
   chip in the allowed list).
2. Implement collectors for the sources marked live in docs/data_sources.md, starting
   with official APIs. Save raw responses to data/raw/live/<provider>/<YYYY-MM-DD>/ with
   sidecars, then parse to data/interim/live/.
3. One entry point, `uv run python -m gel.collect.live --all`, with logging. One
   provider failing must not stop the others.
4. Write deploy/README.md: provision a small Ubuntu VPS, install uv, clone the repo, run
   the collector daily at a fixed UTC time with a systemd timer, back up data/raw/ to
   S3-compatible storage, and alert me on failure.
5. Add a health check that compares today's rows per provider with the 7-day average.

Done when: one local run produces valid rows for at least 4 providers, tests pass, and
I have confirmed the VPS deployment works.
Stop and ask me if: a provider needs a login or payment, or forbids automated access.
```

### Phase 2: Historical panel from the archive (weeks 3–6)

```text
Build the historical panel from the Wayback Machine.

1. From the CDX results, pick at most one snapshot per URL per month (the first capture
   with HTTP 200). Save the list to data/raw/wayback/selection.csv.
2. Download the selected snapshots with polite rate limiting and resumable state (skip
   files already downloaded). Store raw content unchanged, with sidecars.
3. Write parsers per provider and per page layout. Detect the layout version and fail
   loudly on unknown layouts instead of guessing. Output rows in the canonical schema,
   using the snapshot timestamp as the price date.
4. Write docs/coverage.md with a heatmap (chip x provider x month) and row counts.
5. Draw a random sample of 40 parsed rows, stratified by provider and year, and write
   data/interim/validation_sample.csv with each row's archive URL so I can check them
   by hand.

Done when: every provider with usable coverage has a parser, the coverage report exists,
and I have checked the validation sample with under 2% errors.
Stop and ask me if: archived pages are empty because they need JavaScript, or a price
can only be read by guessing.
```

### Phase 3: Reference tables (week 6, alongside Phase 2)

```text
Build the reference tables.

1. config/chips.yaml: chip id, vendor, architecture, announcement date, general
   availability date (first public cloud availability), memory GB, memory bandwidth TB/s,
   BF16 dense TFLOPS, TDP W. Every value needs a source URL from an official NVIDIA or
   AMD datasheet or announcement. Leave a value missing rather than estimating it.
2. MLPerf: download MLCommons training and inference results for the chips in scope and
   build a per-chip throughput index from one or two common benchmarks. Log the choice
   in decisions.md.
3. EIA: pull monthly commercial and industrial electricity prices for the main
   data-center states (start with VA, TX, OR, GA, AZ, OH) and the U.S. average.
4. CPI-U from BLS or FRED for deflation.

Done when: all tables exist and a test fails if any value lacks a source.
```

### Phase 4: Panel and descriptives (weeks 7–8)

```text
1. Merge live and historical rows into data/processed/panel.parquet: deduplicate,
   compute price per GPU-hour, join chip specs, compute age in months since general
   availability, and add a real-dollar column.
2. Write a cleaning report listing rows dropped at each step and why.
3. Figures: (a) median price per GPU-hour by chip over time, by provider type;
   (b) price against age by chip with a LOWESS fit; (c) price dispersion across providers
   per chip-month; (d) our series against the getdeploying.com index and any index
   exports I put in data/raw/indices/.
4. Write docs/memo_01_descriptives.md: 1 to 2 pages in plain English on what the raw
   data shows, with the figures. No regressions yet.

Done when: `make data` rebuilds the panel from raw, figures are in paper/figures/, and
the memo is written.
```

### Phase 5: Hedonic models and identification (weeks 9–12)

```text
Implement Steps 1 and 2 of the proposal's methodology in src/gel/models/.

1. Baseline: chip and month fixed effects plus controls, with the age profile as
   (i) 6-month bins and (ii) a cubic spline. Cluster by provider; add two-way
   provider x month clustering as a robustness check.
2. Implement identification strategies 1 to 4 exactly as the proposal describes. For
   strategy 4, expose the linear-term assumption as a parameter and plot results across
   a range of values.
3. Estimate separately by contract type (H3) and by sub-period (H4).
4. Successor event study (H2) using GA dates from config/chips.yaml.
5. Write LaTeX tables and figures. Record every specification in decisions.md.
6. Write docs/memo_02_hedonic.md: in plain English, what each strategy assumes, what it
   finds, and where they disagree.

Done when: `make models` reproduces every table and the memo is written.
```

After Phase 5, open a fresh Claude Code session with no history. Give it only `src/gel/models/`, the result tables and Step 2 of the proposal, and ask for the weakest assumption and the most likely referee objection. Save the answer to `docs/review_01.md` and respond to each point before moving on.

### Phase 6: Asset values and economic life (weeks 13–15)

```text
Implement Step 3 of the methodology.

1. A function value(chip, age, params) that computes the present value of net rent.
   Read r, utilization, PUE, electricity price, hosting cost per kW-month and
   maintenance from config/assumptions.yaml. Each default value needs a cited source in
   docs/assumptions.md.
2. Rent beyond a chip's observed ages: borrow the estimated age profile from older
   generations. Make the borrowing rule explicit and switchable.
3. Compute economic life T* and annual market-implied depreciation per chip across the
   grid r in {8%, 10%, 12%}, u in {50%, 70%, 90%}, PUE in {1.2, 1.4}.
4. Figure: market-implied value curve against 5, 5.5 and 6 year straight-line schedules
   for each chip, with bands across the grid.

Done when: tables and figures rebuild with `make models`.
```

### Phase 7: Accounting restatement (weeks 16–17)

```text
Implement Step 4 of the methodology.

1. Pull XBRL companyfacts from SEC EDGAR for MSFT, GOOGL, AMZN, META, ORCL, CRWV and
   NBIS (20-F filer). Use a User-Agent with my email and stay under SEC's fair-access
   limit of 10 requests per second. Extract PP&E, depreciation and capex.
2. docs/useful_lives.md: every useful-life policy and change, with the exact filing
   quote, accession number and URL. Cross-check against the table in the proposal and
   flag any mismatch.
3. Restate depreciation under the market-implied schedules, with the GPU share of server
   capex as a parameter set in assumptions.yaml (start with a 30% to 80% grid). Report
   the change in depreciation, operating income and EPS by firm-year.
4. Write a LaTeX sensitivity table and a figure.

Done when: every firm-year number traces to an XBRL fact or a logged assumption.
```

### Phase 8: Paper scaffold and replication (weeks 18–20)

```text
1. Create paper/main.tex with sections: Introduction, Institutional background, Data,
   Methodology, Results, Accounting implications, Robustness, Conclusion. Pull tables and
   figures in only from generated files. Leave section text for me to write; add bullet
   notes of the key results under each heading.
2. Build paper/references.bib. For every entry, find the DOI or a stable URL and confirm
   title, authors, year and venue. Add a field verified = {yes} or {no}, and list every
   unverified entry in docs/open_questions.md. Never invent a reference.
3. Make `make all` rebuild everything from data/raw to paper/main.pdf on a clean clone,
   and test it in a fresh directory.
4. Write README.md: replication steps, data sources, licenses, expected runtime.
5. Check scope and submission rules for the candidate journals in the proposal and
   summarize them in docs/venues.md.

Done when: a clean clone rebuilds the PDF and no unverified references remain.
```

## References

The academic references below were compiled for this draft and have not yet been checked against the original publications. Phase 8 confirms each one against its DOI before anything is posted.

- Berndt, E. R., & Griliches, Z. (1993). Price indexes for microcomputers: An exploratory study. In *Price Measurements and Their Uses*. NBER / University of Chicago Press.
- Doms, M. E., Dunn, W. E., Oliner, S. D., & Sichel, D. E. (2004). How fast do personal computers depreciate? Concepts and new estimates. *Tax Policy and the Economy*, 18.
- Gavazza, A. (2011). Leasing and secondary markets: Theory and evidence from commercial aircraft. *Journal of Political Economy*, 119(2).
- Geske, M. J., Ramey, V. A., & Shapiro, M. D. (2007). Why do computers depreciate? In *Hard-to-Measure Goods and Services: Essays in Honor of Zvi Griliches*. NBER / University of Chicago Press.
- Hall, R. E. (1968). Technical change and capital from the point of view of the dual. *Review of Economic Studies*, 35(1).
- Hulten, C. R., & Wykoff, F. C. (1981). The estimation of economic depreciation using vintage asset prices. *Journal of Econometrics*, 15(3).
- Keating, A. S., & Zimmerman, J. L. (1999). Depreciation-policy changes: Tax, earnings management, and investment opportunity incentives. *Journal of Accounting and Economics*, 28(3).
- Oliner, S. D. (1993). Constant-quality price change, depreciation, and retirement of mainframe computers. In *Price Measurements and Their Uses*. NBER / University of Chicago Press.
- Triplett, J. (2006). *Handbook on Hedonic Indexes and Quality Adjustments in Price Indexes*. OECD Publishing.

**Web sources cited in this proposal** (accessed Oct 31, 2026):

- [American Compute, "GPU Depreciation Schedules"](https://www.amcompute.com/gpu-depreciation-schedules), compilation of 10-K and 20-F useful-life disclosures, updated Oct 10, 2026.
- [The Register, Amazon Q4 FY2024 coverage](https://www.theregister.com/2025/02/07/amazon_q4_fy_2024/), Feb 7, 2025.
- [Value the Markets, "The GPU Depreciation Debate Behind This Week's AI Dip"](https://www.valuethemarkets.com/analysis/gpu-depreciation-debate-behind-this-weeks-ai-dip), Sept 16, 2026.
- [Compute Desk analysis of diverging GPU indices (KuCoin repost)](https://www.kucoin.com/news/flash/gpu-pricing-disarray-four-indices-diverge-market-lacks-consensus).
- [getdeploying.com GPU Rental Price Index](https://getdeploying.com/gpu-price-index): on-demand only, provider-median method, weekly data since July 2024.

**Added after the Phase 0 literature check:**

- Amissah-Ocran, B., & Ayumu, M. T. (2026). [Collateral Without a Curve: A Residual-Value Methodology for Compute-Backed Credit](https://doi.org/10.54660/.ijmrge.2026.7.5.49-62). *International Journal of Multidisciplinary Research and Growth Evaluation*, 7(5), 49–62.
- Chincholikar, S., & Chawla, R. (2026). [Economic depreciation of AI accelerators: Evidence from secondary-market transactions](https://zenodo.org/records/21894454). Reproducibility artifact, submitted to *Journal of Economics and Finance*.
- CCIR (2026). [GPU Rental Rates by Generation: Nine Years of Posted Prices](https://ccir.io/research/rental-rates-by-generation). Research note.
- Dutta, S., & Patatoukas, P. N. (2026). [Priced to Last, but Built to Last? The Asset Life Question in the AI Buildout](https://doi.org/10.2139/ssrn.7420380). SSRN working paper; abstract read only.
- Huang, J. (2026). [GPU Rental Value Curves: replication data for "Underwriting GPU Depreciation"](https://zenodo.org/records/22053861). Zenodo dataset; working paper not yet read.
- Watkins, J. (2026). [Deriving the AI Depreciation Curve](https://www.jaredwatkins.com/posts/2026/08/ai-depreciation-curve/). Blog post.
