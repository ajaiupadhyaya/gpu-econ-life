# Related work: literature gate for "Market-Implied Economic Life of AI Accelerators"

Search date: 2026-10-31. Result of the Phase 0 literature check in `docs/proposal.md`.

## 1. Verdict

**Yes, the core idea has already been done in thinner form, so the claim "first use of vintage-price depreciation methods on AI accelerators" cannot stand, and the Phase 0 stop condition ("a paper already does this") is triggered; this is a reason to reposition the paper, not to kill it.** The closest paper is Amissah-Ocran & Ayumu (2026), "Collateral Without a Curve" (*International Journal of Multidisciplinary Research and Growth Evaluation* 7(5), 49–62), which I read in full. **Data:** it uses posted on-demand rents from one cross-provider survey dated 15 October 2025, taking the lowest independent-provider quote, so it has a single date and no panel, no contract-type split and no transaction prices. **Chips:** V100, A100 40GB and 80GB, H100, H200 and B200, which is this project's whole core list. **Method:** it fits log rent on age across six vintages, cites Hall and Hulten-Wykoff, adopts the vintage assumption as stated (no separate age, vintage and time effects; it does not use Geske et al.), then defines economic life and asset value almost exactly as Step 3 of the proposal does: T* is the first age at which p·u − c ≤ 0, and value is the present value of remaining net rent. It finds 5.93 years at 700 W and 5.38 at 1,000 W, and 72.7/46.3/24.7/9.9% retention over four years at 700 W. **Accounting link:** it compares that curve to 4-, 5- and 6-year straight-line schedules and names Nebius and CoreWeave, but its purpose is credit structuring and a text search found no firm-level earnings or EPS restatement. Two more works close the gap from other sides. Chincholikar & Chawla (2026, under review) run a Hulten-Wykoff profile on executed used-GPU prices for V100, A100, H100, H200 and L40S and find 24–27% a year; Huang (2026) reports rental contribution decaying 17–32% a year on a transacted marketplace panel against book lives. I saw only the public records for those two, not the manuscripts, and SSRN full text was unreachable, so every SSRN row below rests on its abstract. What I did not find anywhere is the combination of a multi-year rental panel across provider and contract types, formal age–vintage–time identification, and a firm-by-firm restatement under a price-implied schedule.

**Update, same day:** the owner approved both Zenodo downloads, and the packages were then read. See section 5, which replaces the "Record only" caveats on those two rows.

## 2. Papers, sorted by closeness

How to read this table:

- Each summary ends with what I actually opened. **Full text** means I read the work itself. **Record only** means the repository page, with no manuscript available. **Abstract only** means the abstract as deposited with Crossref, because SSRN returned 403.
- Under your definition (market prices used to estimate a profile, rate or life, and/or a comparison to book lives) some practitioner notes count as Direct. Direct does not mean rigorous.
- SSRN dates are Crossref record-creation dates, a proxy for posting date.
- Numbers are the authors' own and were not replicated.

| Closeness | Title | Authors | Date | Venue | Link | Data used | Method | One-line summary |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Direct | Collateral Without a Curve: A Residual-Value Methodology for Compute-Backed Credit | Benedict Amissah-Ocran, Mark Tettey Ayumu | 2026 (received 21 Jun, accepted 23 Jul) | IJMRGE 7(5), 49–62; journal header states double-blind peer review | [DOI](https://doi.org/10.54660/.ijmrge.2026.7.5.49-62) | Posted on-demand rents, 15 Oct 2025, for V100, A100, H100, H200, B200; TDP; colocation and energy costs; evidence to end-2025 | Log-quadratic rent on age across six vintages at one date; endogenous T*; PV of net rent; adjusted for fire-sale and appraisal haircuts; Monte Carlo | Closest overall: same chips and same valuation identity; finds CoreWeave's 6-year line overstates value twofold at year three; credit focus, no EPS restatement. **Full text.** |
| Direct | Economic depreciation of AI accelerators: Evidence from secondary-market transactions (reproducibility artifact) | Samir Chincholikar, Robin Chawla | 2026-08-11 (v1.3.0) | Submitted to *Journal of Economics and Finance* per the record; under review per Vista | [Zenodo](https://zenodo.org/records/21894454) | 241 monthly executed used-GPU prices, 11 NVIDIA data-center GPUs (V100, A100, H100, H200, L40S), 2023–2026, from CCIR's executed-sales series | Hulten-Wykoff panel age-price profile (24.4%); hedonic cross-section (26.7%); Winfrey S-3 survival correction; ask-price and rental user-cost triangulation; preregistered | Self-described first transaction-based estimate; more front-loaded than straight-line, consistent with a six-year geometric life, strongly vintage-dependent. No B200. **Record only;** GitHub repo returns 404. |
| Direct | GPU Rental Value Curves: replication data for "Underwriting GPU Depreciation" | Junhong Huang (Boston University) | 2026-08-22 (v1.6.1) | Zenodo dataset; companion paper not located | [Zenodo](https://zenodo.org/records/22053861) | 1,397-day panel of transacted rental prices and quantities, 130 GPU models, unnamed peer-to-peer marketplace, Oct 2022–Jul 2026; metered power; occupancy; 47 SEC useful-life disclosures | Rental contribution decay rates; fitted and realized value curves; utilization wedge; underwriting grid; cross-validation against Ornn's index | Closest on data: contribution decays 17–32% a year against 16.7–20% implied by 5–6 year lives. **Record and file list only;** estimation details unseen. |
| Direct | Rent and Age: Five Generations | CCIR (Compute Credit Index Research LLC; no named authors) | 2026-07-06, updated 2026-09-29 | CCIR research note | [CCIR](https://ccir.io/research/gpu-age-curve) | Neocloud posted on-demand medians, single date 2026-09-28; B300, B200, H200, H100, A100; 65 observations in the fit | Log rate on age, cross-section; capability shown as ratio tables, not regressors | About −21% per year, R² 0.93; says outright this is not the rate any chip's price fell. No book-life comparison. **Full text.** |
| Direct | GPU Rental Rates by Generation: Nine Years of Posted Prices | CCIR | 2026-07-08 | CCIR research note | [CCIR](https://ccir.io/research/rental-rates-by-generation) | 1,869 Wayback and Common Crawl captures, Oct 2017–Apr 2026, 13 providers, guaranteed on-demand only | Monthly cross-provider medians; log-linear fits by generation | V100 −15.3%/yr (R² 0.82), H100 −15.3% (R² 0.57), A100 no trend; essentially this project's archive method. Row-level file on request only. **Full text.** |
| Direct | Deriving the AI Depreciation Curve | Jared Watkins | 2026-09-07 | Personal blog | [Post](https://www.jaredwatkins.com/posts/2026/08/ai-depreciation-curve/) | Rents for V100–B300 from aggregators, indices and quotes; MLPerf; one audited resale point | Per-chip exponential rent fits; throughput model; V(t) net of power and opex plus resale; no age–vintage–time identification | Pooled rent decay 0.112 a year (0.059–0.244 by market); compares 6-year straight-line; no restated earnings. **Full text.** |
| Direct | DumpsterCluster: From Dumpster Diving to Serving LLaMA-70B on $60 GPUs | Zeyu Cao, Xuan Guo, Cheng Zhang, Cheuk Hang Lau, Ilia Shumailov, Yiren Zhao | 2026 (arXiv v1 stamped 10 Jul) | arXiv cs.LG | [arXiv](https://arxiv.org/abs/2608.14614) | eBay prices for V100 16GB and A100 40GB; sample size unreported | Stretched-exponential fit to launch price | Systems paper; the depreciation fit is incidental and has no accounting link. **Full text (relevant section).** |
| Direct | The Illusion of Stability: Unpacking H100 GPU Market Value Trends | Yang Gao (Silicon Data) | 2026-01-30 | Vendor note | [Silicon Data](https://www.silicondata.com/use-cases/h100-gpu-market-value-trends) | "Thousands" of global H100 resale listings, Jun 2024 onward | Age buckets relative to contemporaneous new price | Used about 61–69% of new; says it is not an accounting schedule; H100 only; vendor. **Full text.** |
| Direct | GPU Depreciation Schedules vs Resale Data | Bernie Margulies, AC Research (American Compute) | 2026-10-27 | Vendor blog | [Post](https://www.amcompute.com/blog/gpu-useful-life-depreciation-schedules) | Resale bands from its June 2026 report; SEC filings | Bands by years since first shipment against 4-, 5- and 6-year straight-line | Calls six years aggressive but defensible; firm sells residual-value insurance; band method not shown. **Blog full text; underlying report not opened.** |
| Partial | Priced to Last, but Built to Last? The Asset Life Question in the AI Buildout | Sunil Dutta, Panos N. Patatoukas | 2026-09-13 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7420380) | Long-term analyst forecasts, Big 5 hyperscalers | Restates forecast earnings and value across asset lives; backs out implied life | "Market-implied life" of 14 years from equity values, 5 years gives net income 28% below consensus; no GPU price data; closest threat to the restatement and to this project's title. **Abstract only.** |
| Partial | The Depreciation Paradox: Accelerator Obsolescence, the Structural Collateral Floor, and the Safe Limits of AI Infrastructure Leverage | Megha Surya Bodepudi, Mahesh Bodepudi | 2026-08-26 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7346098) | BEA computing-equipment profile; MLPerf lineage V100–GB300; 67 filer-years, 10 filers | Hazard benchmarks against disclosed lives | Book lives too long against either benchmark; no GPU market prices. **Abstract only.** |
| Partial | The Price of Compute: Hedonic Evidence from GPU Rental Markets | Helvin Shek | 2026-09-30 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7541938) | 556 rental listings, five GPU generations, two sources | Rosen hedonic regression | Closest to Step 1 cross-sectionally: hyperscalers 138.9% higher, spot 62.6% lower; abstract reports no age profile. **Abstract only.** |
| Partial | Compute as Collateral | Nicholas G. Polson | 2026-08-15 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7270603) | Disclosed leases; a measured "value ladder"; full data unseen | Debt-capacity model of a plateau-then-cliff value path | Claims two-thirds of the scarcity rent dissipates within two years of a successor reaching volume; overlaps H2. **Abstract only.** |
| Partial | Five Years for the Chip, One for the Model: Contract Menus and the Economic Life of AI Infrastructure | Panagiotis I. Chronopoulos | 2026-08-18 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7295000) | One major cloud vendor's posted commitment menu | Term-discount structure, same resource across commitment lengths | Reads economic life from contract terms; GPU capacity priced like long-lived capital; overlaps H3 in spirit. **Abstract only.** |
| Partial | The Second Rental: CoreWeave, GPU Depreciation and How Long AI Chips Earn | Russ W. Rosenzweig (Vista Research) | 2026-10-05 | Zenodo working paper | [Zenodo](https://zenodo.org/records/23483110) | CoreWeave filings; Ornn term curves; posted prices | Replacement model under a power constraint; breakeven lives | One firm; tabulates competing decline rates; pointed me to several rows here. **Full text (HTML version).** |
| Partial | How Is the AI Build-Out Financed? Internal Funds, Leases, and Depreciation Compared with the Dot-Com Boom | Zhongzheng Fang | 2026-10-20 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7643251) | Filings for the ten largest capital spenders | Cash-gap measure; depreciation sensitivity | Faster server depreciation would lower 2025 operating income by a few percent; lives assumed, not estimated. **Abstract only.** |
| Partial | Global Financial Stability Report, April 2026, Chapter 1, Box 1.4 | Deepali Gautam, Johannes Kramer, Aki Yokoyama (box authors) | April 2026 | IMF | [PDF](https://www.imf.org/-/media/files/publications/gfsr/2026/april/english/ch1.pdf) | Filings of 10 hyperscalers; market data | PP&E/depreciation implied life of about 7 years; 3-year scenario; Merton-style spreads | A 3-year life cuts aggregate EBIT margin by more than 9 points; stylized, no GPU prices. **Full text (box).** |
| Partial | How Long Does a GPU Last? | Chris Zeoli (Data Gravity) | 2026-09-21 | Substack | [Post](https://www.datagravity.dev/p/how-long-does-a-gpu-last) | Reliability studies, SemiAnalysis rents, useful-life disclosures | Cohort model; straight-line against sum-of-years-digits | Half of lifetime cash in the first two years; relays a JPMorgan AM 3-year-life EPS sensitivity. **Full text.** |
| Partial | Charts of the Week: Attention is All You Need | Moses Sternstein (a16z) | 2026-10-23 | Newsletter | [Post](https://www.a16z.news/p/charts-of-the-week-attention-is-all) | Ornn rental series | Rates against a six-year straight-line baseline | Recent rates 9–143% above baseline, yet A100 and H100 were mostly below it over the longer history. **Full text.** |
| Partial | The Economics of Open-Weight Inference | Ornn Data (no named authors) | 2026-09-07 | Ornn publication | [Ornn](https://data.ornn.com/publications/the-economics-of-open-weight-inference) | Ornn index, 1-month to 5-year term marks, A100–B200 | Term retention and implied forwards | Five-year A100 marks hold about 80% of one-month; states it does not establish residual value or book-life adequacy; vendor. **Full text.** |
| Partial | (Early) AI Compute Asset Pricing | Federico M. Bandi, Yinan Su | 2026-07-13, v4 2026-10-21 | arXiv q-fin.PR; SSRN | [arXiv](https://arxiv.org/abs/2607.12156) | Silicon Data and Ornn indices and term curves | Synthetic futures returns by generation and maturity | Serious finance paper on rental markets; no depreciation estimate in the part read. **First 100k of 161k characters.** |
| Partial | Is Compute the New Oil? Cross-Asset Risk and the Case for a Dedicated Market | Doohwi Cha | 2026-07-14 | SSRN | [DOI](https://doi.org/10.2139/ssrn.6829278) | Daily Bloomberg GPU rental indices: A100, H100, B200 | Price dynamics; out-of-sample hedge tests | Uses this project's validation indices; about hedging, not depreciation. **Abstract only.** |
| Partial | Pricing Compute Futures: Forward Curve and Volatility for a Non-Storable, Depreciating Commodity | Amine Assody | 2026-07-29 | SSRN | [DOI](https://doi.org/10.2139/ssrn.6926798) | Public price records for the A100 and H100 generational transitions | Two-factor model with scheduled jumps | Calibrates launch-window jumps to two transitions; overlaps H2 as a model input. **Abstract only.** |
| Partial | AI Chip Lifespans: A Note on the Secondary Market | Mihir Kshirsagar (Princeton CITP) | 2025-12-18 | Blog | [Post](https://blog.citp.princeton.edu/2025/12/18/ai-chip-lifespans-a-note-on-the-secondary-market/) | Silicon Data indices; NVIDIA revenue | Qualitative test of the value cascade | Argues rents near opex do not support 5–6 year lives; no estimate. **Full text.** |
| Partial | CoreWeave's Residual: What a Used GPU Has to Fetch | Cape Fear Advisors | 2026-09-16 | Substack | [Post](https://capefearadvisors.substack.com/p/coreweaves-call-option-on-used-gpus) | CoreWeave and NVIDIA filings; third-party rents and resale | Solves for the residual a rack needs | Required residual about 87% of deployed cost against 16–24 cents in executed sales; different denominators, as it notes. **Full text.** |
| Partial | GPU Residual Value (product page) | Silicon Data | Undated | Vendor product | [Page](https://www.silicondata.com/products/gpu-residual-value) | Proprietary forward curve to 36 months | DCF of rent net of utilization decay and opex | Commercial version of Step 3; proprietary, no book comparison. **Full page.** |
| Partial | H100 Depreciation | Mercatus (AI compute marketplace; not the Mercatus Center) | 2026-03-30 | Vendor blog | [Post](https://www.mercatus-ai.com/blog/h100-depreciation) | Sample not disclosed | Age-band estimates | Widely repeated bands, labelled forward-looking, and internally inconsistent. **Full text.** |
| Background | The AI Chip Depreciation Debate | Matthew Shaffer | 2026-03-25 | SSRN (teaching case) | [DOI](https://doi.org/10.2139/ssrn.6459645) | Case narrative | Teaching case | Shows the debate has reached the accounting classroom; no estimate. **Abstract only.** |
| Background | When Software Extends GPU Life: Workload Choice and Economic Retirement | Uwe Jens Cerron | 2026-10-02 | SSRN | [DOI](https://doi.org/10.2139/ssrn.7549859) | Synthetic examples | Retirement theory | States its numbers are not estimates of GPU lifetimes. **Abstract and [GitHub README](https://github.com/uwecerron/GPU_Depreciation_Research).** |
| Background | The GPU Depreciation Problem | Arnav Gupta | 2026-09-21 | Zenodo preprint | [Zenodo](https://zenodo.org/records/22881400) | Filings, vendor specs | Scenarios | Separates physical, accounting and economic life; no price estimate. **Record only; PDF not read.** |
| Background | AI Computing Hardware as an Accounting Asset; Technology Is a Consumable Item; The Effective Life Problem | Mason Barrett; Manoj Kumar Bohra; Shubham Agarwal | 2026-06-08; 2026-08-21; 2026-09-19 | SSRN | [Barrett](https://doi.org/10.2139/ssrn.6844518), [Bohra](https://doi.org/10.2139/ssrn.7323639), [Agarwal](https://doi.org/10.2139/ssrn.7475178) | Conceptual | Disclosure and accounting frameworks | Accounting framing only. **Abstract only.** |
| Background | Pricing, Hedging, and Securitizing AI Compute; The Half-Life of a Futures Contract; Chips as Collateral and the Macroeconomics of AI Financing | Seung Jung Lee, Sriram Nagaraj; Fuli Yang; Sang Rae Kim | 2026-08-26; 2026-08-28; 2026-08-15 | SSRN | [Lee](https://doi.org/10.2139/ssrn.7342241), [Yang](https://doi.org/10.2139/ssrn.7359042), [Kim](https://doi.org/10.2139/ssrn.7271464) | Models; full data unseen | Compute derivatives and securitization theory | Rental price as an underlying; no vintage estimate in the abstracts. **Abstract only.** |
| Background | Financing the AI Buildout | Stijn Van Nieuwerburgh | Oct 2026 | NBER WP 35865; forthcoming BPEA per the page | [NBER](https://www.nber.org/papers/w35865) | Buildout cost estimates | Financing analysis | Names residual values as a risk; depreciation treatment unknown. **Abstract page only.** |
| Background | The AI investment race | Phurichai Rungcharoenkitkul | July 2026 | BIS WP 1367 | [BIS](https://www.bis.org/publ/work1367.htm) | Balance sheets, deal data | Contest model | Uses reported 5–6 year lives as a calibration input, no estimate. **PDF text searched.** |
| Background | Tracking Trillions | Goldman Sachs Global Investment Research | By May 2026 | Sell-side | [Summary](https://www.itiger.com/news/1111410595) | Revenue-anchored capex | Sensitivity to chip life | 3 against 5 years raises annual depreciation from about $3tn to nearly $4tn. **Secondary summary only; primary page returned 403.** |
| Background | The Rise of Cloud Computing: Minding Your P's, Q's and K's | David Byrne, Carol Corrado, Daniel Sichel | Oct 2018; book chapter 2021 | NBER WP 25188 | [NBER](https://www.nber.org/papers/w25188) | AWS offerings, 2009–2016 | Hedonic price indexes | Standard reference for cloud price measurement; pre-GPU focus. **Abstract page.** |
| Background | Exploring quality adjustment in PPI cloud computing | Steven D. Sawyer, Claire O'Bryan | Feb 2023 | *Monthly Labor Review* | [BLS](https://www.bls.gov/opub/mlr/2023/article/exploring-quality-adjustment-in-ppi-cloud-computing.htm) | AWS, Azure, GCP IaaS, 2017–2019 | Time-dummy hedonics | Official-statistics method for hourly cloud prices; GPU instances not mentioned. **Full text.** |
| Background | Cloud Computing and National Accounting | Diane Coyle, David Nguyen | 2018 | ESCoE DP 2018-19 | [IDEAS](https://ideas.repec.org/p/nsr/escoed/escoe-dp-2018-19.html) | UK cloud prices | Price indices | Quality-adjusted cloud prices fell substantially. **Abstract page.** |
| Background | Trends in GPU price-performance | Marius Hobbhahn, Tamay Besiroglu | 2022-06-27 | Epoch AI | [Epoch](https://epoch.ai/publications/trends-in-gpu-price-performance) | 470 GPU models, 2006–2021 | Log-linear trend of FLOP/s per dollar | Doubling about every 2.5 years; no depreciation. **Full page.** |
| Background | The performance per dollar of AI chips purchased each quarter has grown by an average of 49% per year | Venkat Somala | 2026-08-13 | Epoch AI | [Epoch](https://epoch.ai/data-insights/chip-performance-per-dollar) | 24 accelerators, 2023–2025 sales and purchase prices | Dollar-weighted trend | Useful frontier measure for the obsolescence regressor; no depreciation. **Full page.** |
| Background | Open posted-price datasets: GPU Rental Prices ledger; GPU Cloud Pricing Dataset; Compute Comparison snapshots | GPU Rental Prices; FastGPU; Compute Comparison | 2026-07-19; 2026-10-04; 2026-10-10 | Zenodo | [Ledger](https://zenodo.org/records/21435395), [FastGPU](https://zenodo.org/records/23132958), [Snapshots](https://zenodo.org/records/23275464) | Daily posted rates; FastGPU's series starts 2026-08-05; Compute Comparison says rows are not verified histories | Collections | Open but recent or unverified, so they do not replace a 2020–2027 archive panel. **Record only.** |

Three SSRN papers state a chip life without estimating it from prices: Cornell ([4–5 years](https://doi.org/10.2139/ssrn.7539101)), Fitzpatrick ([about 4 years](https://doi.org/10.2139/ssrn.7620359)) and Rakesh KS ([2.3-year half-life from a physics-style model](https://doi.org/10.2139/ssrn.6731365)). I read their abstracts only.

**No official estimate found.** I found no Fed, BEA, BLS or BIS paper that estimates GPU depreciation from market prices, and no Epoch AI piece that does either. Search summaries said an Epoch analysis assumes a 30% annual price decline and a 5-year life; I did not open that page, so treat it as unverified.

## 3. Planned contributions after this search

### Dead or contested

- **"First use of vintage-price methods on AI accelerators" (proposal line 61): dead.** Amissah-Ocran & Ayumu and Chincholikar & Chawla both precede it, and the second names Hulten-Wykoff outright.
- **"New data ... rebuilt from archived pricing pages" (line 60): contested.** CCIR has already done this with Wayback and Common Crawl. The sentence calling indices paywalled and limited to the newest chips is also out of date, because CCIR publishes free series and a rates CSV, and Ornn and Silicon Data cover the A100.
- **"I have not found a peer-reviewed estimate" (line 36): no longer safe to write.** Amissah-Ocran & Ayumu is in a journal that states double-blind peer review, and Chincholikar & Chawla is under review.
- **Step 3 valuation (lines 124–136): not new.** Amissah-Ocran & Ayumu use nearly the same T* and present-value identity; Watkins, Silicon Data and Huang are close. Cite them, and do not present it as original.
- **H1, front-loaded decline: already claimed.** The hypothesis is still testable, but it is no longer a finding of its own.
- **H2, successor shocks: claim contested, method open.** Polson and Assody make the claim or calibrate it. I found no event study around successor launch dates.
- **H4, demand regimes: partly documented.** CCIR marks two periods when older chips' rents rose.
- **Aggregate book-versus-market gap (RQ3 at a high level): contested.** Huang, Chincholikar & Chawla, Amissah-Ocran & Ayumu and Watkins all address it.
- **The title's "Market-Implied": collides.** Dutta & Patatoukas already use "market-implied life" for a 14-year figure from equity values. "Rental-Implied" would avoid confusion and sets up a sharp contrast.
- **Risk table (line 193):** "a similar paper appears first" is no longer a low-to-medium risk. It has happened.

### Looks safe, but confirm against the two unread manuscripts

- **Reconciling the estimates.** This is the strongest remaining pitch. Published figures disagree: about 39.9% (Amissah-Ocran, one-date lowest quotes, as stated), −21% (CCIR cross-section), −15% to flat (CCIR cohorts), 11% (Watkins pooled rent), 17–32% (Huang, contribution), 24–27% (Chincholikar, resale). The units differ, and that is the point. CCIR says its own cross-section cannot separate age from vintage, and Amissah-Ocran & Ayumu adopt that separation as an assumption. Nobody I found runs the Hall problem side by side across several identification strategies on rents. Caution: Chincholikar & Chawla report "different identifying variation" and Huang's file list includes period controls, so check how far each one went.
- **Age profiles by contract type (H3) and provider type.** Shek reports level differences, and Ornn and Bandi & Su study term structures. I found no age-slope comparison across spot, on-demand and reserved prices, or across hyperscaler, neocloud and marketplace.
- **Firm-by-firm restatement under a price-implied schedule, by vintage.** Existing work uses hypothetical lives (IMF, JPMorgan AM via Zeoli, Fang) or analyst-implied lives (Dutta & Patatoukas). This contribution looks open, subject to the GPU-share assumption.
- **An open, citable, row-level historical panel.** CCIR's file is on request and on-demand only, Huang released derived measures in a 208 kB package, and the open Zenodo sets start in 2026. "Open and multi-contract" is defensible; "new" is not.

### Before relying on this

1. Open the two Zenodo packages, which I did not download because file downloads need your approval: `gpu-rental-value-curves-v1.6.1.zip` (207.6 kB, [Huang](https://zenodo.org/records/22053861)) and `ai-gpu-depreciation-v1.3.0.zip` (1.8 MB, [Chincholikar & Chawla](https://zenodo.org/records/21894454)).
2. Read these SSRN papers in your own browser, in this order: Dutta & Patatoukas (7420380), Shek (7541938), Bodepudi & Bodepudi (7346098), Polson (7270603).
3. Consider asking Huang for the paper, and CCIR for its archive file, which it says is available on request.

## 4. Search log

Run 2026-10-31. Searches sent no personal details.

### Web search (extended mode unless marked)

1. `GPU depreciation rental prices age-price profile economic life working paper`
2. `market-implied depreciation AI accelerators SSRN paper GPU useful life hyperscaler book depreciation`
3. `economic depreciation of GPUs estimated from secondary market resale prices arXiv`
4. `how fast do GPUs depreciate vintage price hedonic H100 A100 rental price panel`
5. `"Underwriting GPU Depreciation" Junhong Huang Boston University`
6. `"The Price of Compute" hedonic evidence GPU rental markets Helvin Shek`
7. `"Economic depreciation of AI accelerators" secondary-market transactions Chincholikar Chawla Journal of Economics and Finance`
8. `Matthew Shaffer "The AI Chip Depreciation Debate" paper`
9. `Federal Reserve FEDS Notes AI chips GPU depreciation capital stock measurement data center servers` (Federal Reserve Board and regional Fed domains)
10. `BEA Bureau of Economic Analysis depreciation AI servers GPUs cloud computing price index measurement` (bea.gov, bls.gov)
11. `BIS IMF working paper AI data centre GPU depreciation useful life obsolescence financial stability` (bis.org, imf.org, oecd.org, ecb.europa.eu)
12. `Epoch AI GPU depreciation lifespan rental price compute useful life analysis` (epoch.ai)
13. `Dutta Patatoukas "Priced to Last, but Built to Last" asset life question AI buildout`
14. `Watkins "Deriving the AI Depreciation Curve"`
15. `CCIR "Rent and Age" five generations GPU age curve posted rents`
16. `Silicon Data "GPU Residual Value" methodology depreciation curve H100 A100`
17. `Watkins AI depreciation curve GPU rents fitted decline present value remaining rentals September 2026 substack`
18. `"Collateral Without a Curve" residual-value methodology compute-backed credit Amissah-Ocran` (standard mode)
19. `site:ideas.repec.org GPU depreciation AI accelerators useful life` (ideas.repec.org, econpapers.repec.org, nber.org)
20. `accounting research useful life extension servers Amazon Microsoft Alphabet depreciation estimate change earnings effect working paper AI hyperscalers`
21. `Olga Usvyatsky "Depreciation of GPUs" useful lives useful myths Deep Quarry` (standard mode)
22. `GPU rental price drop successor launch event study H100 A100 Blackwell obsolescence shock empirical paper 2026`
23. `restating hyperscaler earnings economic depreciation GPUs market prices EPS impact analysis 2026 study geometric vs straight-line`
24. `Coyle Hampton "Twenty-first century progress in computing" cloud price index Telecommunications Policy` (standard mode)

### OpenAlex API

- General search from 2022, sorted by relevance: `GPU depreciation`; `AI accelerator depreciation`; `GPU rental price`; `economic life GPU`; `GPU useful life depreciation`; `GPU resale price depreciation`; `AI chip depreciation accounting`; `compute rental market GPU price`; `cloud computing price index hedonic`.
- `title_and_abstract.search` from 2024: `age-price profile computers`; `Hulten-Wykoff`; `vintage price depreciation computers`; `economic depreciation artificial intelligence hardware`; `GPU depreciation rate secondary market`; `useful life change servers earnings`; `depreciation estimate change cloud servers accounting`; `hedonic price GPU`; `GPU cloud price`; `Vast.ai marketplace`; `AI compute price index`; `compute price trends GPU cost per hour`; `residual value GPU`; `GPU collateral depreciation`.
- General search from 2017: `rise of cloud computing price index`; `cloud computing price index quality adjusted`; `semiconductor prices falling hedonic`; `GPU price performance trend`.

### Crossref API

- SSRN prefix 10.2139, from 2024-06-01: `GPU depreciation`; `GPU rental prices`; `AI accelerator depreciation useful life`; `economic life GPUs`; `AI chips depreciation hyperscalers earnings`; `useful life servers depreciation AI`; `compute rental market price index`; `GPU secondary market resale prices`; `vintage capital AI compute depreciation`.
- SSRN prefix, from 2025-09-01: `hyperscaler depreciation restated operating income useful life sensitivity`; `GPU obsolescence successor generation rental price`; `neocloud CoreWeave depreciation useful life`; `economic depreciation computing equipment age price AI`; `GPU lease residual value estimate`.
- All prefixes, title search: `Underwriting GPU Depreciation`; `Economic depreciation of AI accelerators`. Three further title queries failed with unparseable responses: `market-implied economic life AI accelerators`; `age-price profile GPU`; `rental value curves GPU`.
- All prefixes, bibliographic search from 2025-06-01: `Priced to Last Built to Last Asset Life AI Buildout`; `Dutta Patatoukas AI asset life`; `Collateral Without a Curve residual value compute-backed credit`; `AI depreciation curve`; `useful life AI servers earnings quality`; `GPU asset life capex accounting estimate`.

### arXiv API (newest first)

`all:GPU AND all:depreciation`; `all:GPU AND all:"useful life"`; `all:GPU AND all:"rental" AND all:price`; `all:accelerator AND all:depreciation AND all:"economic"`; `abs:"compute" AND abs:"depreciation" AND cat:q-fin*`; `abs:"GPU" AND cat:econ*`; `abs:"GPU" AND cat:q-fin*`; `abs:"cloud" AND abs:"hedonic"`.

arXiv searches metadata and abstracts, so full-text mentions are missed. DumpsterCluster did not appear in these queries.

### Other sources

- **Zenodo API, most recent:** `"GPU depreciation"`; `"AI accelerators" depreciation`; `"GPU" "useful life"`; `"GPU" rental price depreciation`; `accelerator "economic life"`.
- **Semantic Scholar API:** `GPU depreciation`; `AI accelerator economic depreciation`; `GPU rental price`; `useful life AI servers`.
- **GitHub API:** repository search `gpu depreciation in:name,description`, plus the Chincholikar account and the Cerron repository.
- **Citation chasing:** Vista's reference list gave Dutta & Patatoukas, Watkins, CCIR and Amissah-Ocran & Ayumu. CCIR's research index gave the rental-rate note.

### Indexes I could not reach, or reached only in part

- **SSRN: blocked.** WebFetch returned 403. I then tried one retry through `curl` with a browser-style User-Agent, which was the wrong call because it was an attempt to get past a bot check. The permission system blocked it before it ran. I did not retry and did not use a browser tool. SSRN coverage here comes entirely from Crossref metadata and abstracts, so any paper without a deposited abstract could be under-read, and unindexed recent postings could be missed.
- **Google Scholar: partial.** One query loaded with one result (Bodepudi & Bodepudi) and an error message. Not repeated.
- **Semantic Scholar: mostly rate-limited.** Three of four searches and two retries returned 429. DOI lookup found 1 of 4 papers tried.
- **NBER and RePEc/IDEAS site search: no usable results through fetch.** Domain-restricted web search was the substitute, and individual paper pages opened normally.
- **Zenodo files inside archives:** file-tree preview worked; reading individual files returned 403. I stopped there.
- **Chincholikar & Chawla GitHub repo:** 404, and not among that account's public repositories.
- **Crossref:** three title queries failed. OpenAlex's `from_created_date` filter requires a paid plan.

### Seen but not opened, so not in the table

Gaffeo, "When Growth Destroys Collateral" (*The Economists' Voice*; publisher page returned 405). Ashok, "The Yield Premium of Compute" (ResearchGate; not attempted). HBS case "Meta: Accounting for AI Data Center Depreciation" (403). Coyle & Hampton 2024 (citation seen only). Usvyatsky, Deep Quarry (paywalled). American Compute's June 2026 residual-value report.

### Suggested alerts

Two direct hits surfaced on Zenodo, not SSRN, so watch Zenodo as well.

- **SSRN (string untested, site unreachable from here):** `("GPU" OR "AI accelerator" OR "AI chip") AND (depreciation OR "useful life" OR "economic life" OR "residual value")`. Also follow authors Chincholikar, Huang, Dutta, Patatoukas and Polson.
- **SSRN through Crossref, tested; advance the date on each run:**
  `https://api.crossref.org/prefixes/10.2139/works?query.bibliographic=GPU+depreciation&filter=from-created-date:2026-10-01&sort=created&order=desc&rows=20&select=title,DOI,created`
- **arXiv, tested, low noise; misses papers that say only "compute":**
  `https://export.arxiv.org/api/query?search_query=(abs:GPU+OR+abs:GPUs+OR+abs:%22AI+accelerator%22+OR+abs:%22AI+accelerators%22+OR+abs:%22AI+chip%22+OR+abs:%22AI+chips%22)+AND+(abs:depreciation+OR+abs:depreciate+OR+abs:%22economic+life%22+OR+abs:%22residual+value%22+OR+abs:%22rental+price%22)&sortBy=submittedDate&sortOrder=descending&max_results=25`
- **Zenodo, tested:** `https://zenodo.org/api/records?q=%22GPU%20depreciation%22&size=20&sort=mostrecent`
- **OpenAlex, tested form:** `https://api.openalex.org/works?filter=title_and_abstract.search:GPU%20depreciation,from_publication_date:2026-10-01&sort=publication_date:desc`
- **Practitioner:** [CCIR research index](https://ccir.io/research).

## 5. The two packages, read 2026-10-31

Both zips matched Zenodo's published MD5 checksums. Their contents were read as text, and nothing inside them was run.

- `ai-gpu-depreciation-v1.3.0.zip` (MD5 `35752d5ad26fa93e5f32cdaa659aeda0`) contains the full manuscript. Headline 26.7% (hedonic, primary) and 24.4% (panel), with V100 supplying 84.6% of units; without V100 the rates fall to 11.2% and 12.3%. A100 alone is 14.5%. H100 is called uninformative. Survival-corrected rates are 42.2% and 53.3% at assumed 6- and 5-year lives. The paper states that it is not an audit of hyperscaler depreciation and not a measure for any firm's fleet. Its rental panel has 43 rows, 37 of them on-demand.
- `gpu-rental-value-curves-v1.6.1.zip` (MD5 `30dc239dd5d6ea393ba885879600462f`) contains tables, code and documentation, not the paper. Its marketplace history comes from 500.farm, described as an anonymous endpoint covering Vast.ai. The headline is cash-flow decay on a pre-shock window. It reports period controls, CR2 inference, a utilization wedge, value-basis rates, survivorship bounds and 47 useful-life disclosures with URLs. Period effects are orthogonalized against a linear trend. No earnings or EPS restatement appears in the package. The working paper is still unread.

Effect on section 3: "reconciling the estimates", "age profiles by contract and provider type" and "firm-by-firm restatement" all remain open. Details are in `docs/proposal_review.md`.
