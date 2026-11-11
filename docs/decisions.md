# Decision log

Every methodological choice: date, choice, alternatives, reason.

## Decision 1: Hypotheses (2026-10-31)

- **Date:** 2026-10-31, before any regression has been run and before any price data was collected.
- **Choice:** the hypotheses below, copied verbatim from docs/proposal.md.
- **Alternatives:** leave hypotheses informal until the descriptive work in Phase 4.
- **Reason:** a dated record stops the results from quietly reshaping them.

- **H1: Front-loaded decline.** Value falls fastest in years 1–2, closer to geometric than straight-line. If so, straight-line book values overstate asset value early in life even when the total life is right.
- **H2: Obsolescence shocks.** A successor reaching general availability (H100 for A100, B200 for H100) causes a discrete drop in the predecessor's rent beyond the smooth age trend.
- **H3: Contract-type wedge.** Spot and on-demand prices fall faster with age than 1-year reserved prices, so the implied life depends on which market you read.
- **H4: Demand regimes.** Shortages temporarily mask age effects. H100 1-year forward prices rose from $1.90 to $2.64/hour in early 2026 ([Compute Desk analysis](https://www.kucoin.com/news/flash/gpu-pricing-disarray-four-indices-diverge-market-lacks-consensus)). Time fixed effects should absorb this, leaving age profiles stable across sub-periods.

## Decision 2: Reposition the paper (2026-10-31)

- **Date:** 2026-10-31, approved by the owner after Phase 0 hit two stop conditions. No price data
  had entered any estimate.
- **Choice:** adopt the revised plan in docs/proposal_review.md. The working title becomes *Rental-Implied
  Depreciation of AI Accelerators: Why the Estimates Disagree*. Its three parts are to reconcile the
  published rates, estimate age slopes by contract and provider type, and restate earnings firm by
  firm by purchase cohort. A short reconciliation note is added as an early output.
- **Alternatives:** abandon the project; keep the original "first use" framing; wait for written
  permission from Vast.ai and RunPod.
- **Reason:** close prior work ends the "first use" claim, while these three parts remain open
  after reading the two closest packages. Marketplace collection is dropped because terms restrict
  it and Huang's CC BY tables already provide that comparison.
- **Hypotheses:** H1–H4 in Decision 1 are unchanged. New hypotheses get their own dated entry before
  any regression.

## Decision 3: Sources approved under rule 7 (2026-10-31)

- **Date:** 2026-10-31, approved by the owner with Decision 2.
- **Choice:** add AWS offer files, the Azure Retail Prices API, SkyPilot catalog history (AWS, Azure,
  GCP and Lambda files only), Huang's CC BY tables and Chincholikar & Chawla's CC BY artifact.
- **Alternatives:** rely on Wayback alone.
- **Reason:** official or structured history removes the need for most hyperscaler page parsers.
- **Excluded:** Vast.ai, RunPod and Oracle, and SkyPilot's files for those providers. CCIR's series
  stay out until its terms are known. Huang's Vast.ai rebuild script must not be run.

## Decision 4: Phase 1 implementation choices (2026-10-31)

Made while building the collector, within the approved plan. The owner can reverse any of them.

- **getdeploying is manual, not scheduled.** The approved plan listed its weekly file, but the
  license grants no automated access and the terms bar systematically copying content. Each file
  holds trailing history, so a hand download every six months loses nothing. Alternative: a
  scheduled fetch, rejected under rule 5.
- **GPU counts come from vendor documentation, never SkyPilot.** SkyPilot lists
  Standard_ND96isr_H100_v5 with 12 GPUs where Microsoft documents eight, which would understate its
  per-GPU price by a third. AWS counts are also checked against the offer file's GPU column.
- **AWS spot and Google Cloud come through SkyPilot.** AWS's offer files exclude spot and its history
  tool needs credentials. Google's catalog needs an API key. SkyPilot needs neither. The catalog's
  Google rows have no instance type and are treated as accelerator-only prices, excluding the host
  VM. That reading is not yet confirmed against Google's pricing page.
- **Additive schema columns:** `collector`, `price_kind`, `price_basis`, `zone`, `available`,
  `source_version` and `effective_from`. The Phase 1 fields are all present. No current source
  reports availability, so `available` is empty for now.
- **The unit of observation is unchanged.** Spot rows are stored by zone for fidelity. Phase 4 decides
  how to aggregate them to region, and that choice comes to the owner under rule 7.
- **Azure's 5-year reservations** use contract type `other` with `term_months` 60, because the
  contract types in CLAUDE.md stop at three years.
- **Out of scope:** Azure's GB200 is a different product from B200. Azure SKU variants missing from
  Microsoft's size documentation are left out rather than assumed.
- **Lambda's page has no region,** so `region` is `unspecified`. Its 1-Click Cluster rows use
  contract type `other`, with the page's duration range kept in `sku`.

## Decision 5: Phase 2 choices (2026-10-31)

Made while building the historical panel, within the approved plan. The owner can reverse any of them.

- **The price date is the snapshot time** for archive pages, the version time for AWS files and the
  commit time for SkyPilot, as the Phase 2 prompt says. A price may have changed earlier.
- **No price is carried forward.** A month with no observation stays a gap.
- **AWS history is us-east-1 only,** from October 2017 when P3 launched. Alternative: more regions,
  rejected because each file is large and the panel needs the price path rather than regional spread.
- **`price_basis` must separate CoreWeave's series.** Its prices are `accelerator_only` through 2024
  and `instance` from 2025. H100 goes from $4.76 to $6.155 at that break, which is a change of basis,
  not a price rise. Never compare across the break without adjusting.
- **Term prices are recorded only where the page states the term.** Lambda's commitment ladders are
  per-GPU quotes with no machine size, so they use `gpu_count` 1 and keep the commitment in `sku`.
  Ranges such as "3-6 months" keep `term_months` empty.
- **Where a table has dated price columns,** the one in force at the snapshot is used.
- **HGX is read as SXM** (`h100_sxm`), because HGX boards carry SXM modules. This affects 54
  Paperspace rows and CoreWeave's HGX H100 rows. No page states SXM directly.
- **CoreWeave's "$4.76 Reserve Now" is kept as on-demand,** with the label kept in `sku`.
- **Rows that do not settle chip identity are left out,** not assumed. See open_questions.md.
- **The validation sample** is 40 archive rows, spread across provider and year, with seed 20261031.

## Decision 6: Extension adopted: benchmark, term structure, retirement model (2026-11-10)

- **Date:** 2026-11-10. The owner supplied `docs/handoff_extension.md` (written in Claude Chat) and
  said to start. Three conflicts with earlier decisions went to the owner, who answered as below.
- **Choice:** add three projects to this paper: P1, a cross-generation vLLM inference benchmark
  on rented GPUs; P2, decay rates implied by the rental term structure; P3, a power-constrained
  retirement model. They live in this repo (`gel.bench`, `gel.models.term_structure`, later
  `gel.models.retirement`), not in the separate `gpuecon` repo the handoff sketches, so P2 can
  reuse the Azure 1/3/5-year, AWS reserved and Lambda commitment prices already collected.
- **Alternatives:** a separate repo (rejected by the owner); defer the extension until after
  Phase 3.
- **Spot price panel (rule 7):** recorded by hand, once, in benchmark week, from public pricing
  pages. Each quote is a row with `source_url` and `observed_date`, plus a saved page copy.
  **Vast.ai and RunPod listings stay out** (Decision 3 stands). The only RunPod price recorded is
  the one actually paid at pod launch, which is our own invoice, not collected data. On this
  basis the owner approved CoreWeave, Nebius, Crusoe, Together and Voltage Park as manual sources.
  Each provider's terms still get read before its first row, and any that bars even manual
  recording is dropped and logged in open_questions.md.
- **Benchmark prompt counts trimmed (owner's choice).** The handoff's 20×C prompts at every level
  would take roughly 45–50 GPU-minutes per GPU on an RTX 4090, against a 15–25 minute budget.
  The counts are now 20, 160, 160 and 640 prompts at concurrency 1, 8, 32 and 128 (20×C at
  low concurrency, 5×C from 32 up, never fewer than 160 requests above C=1). Concurrencies,
  three repeats and both precision modes are unchanged. The 4090 smoke test will give a real
  timing, and the counts can be revisited then.
- **vLLM pinned to v0.32.0** (PyPI and Docker Hub, 2026-10-18), not v0.33.0 (2026-11-02), which
  was eight days old. Benchmark flags and result-JSON keys were checked against the v0.32.0 source.
  In that version the random dataset sets `ignore_eos` automatically, so each request generates
  exactly 256 tokens, and FP8 on GPUs without FP8 hardware uses the Marlin weight-only kernel.
  Ampere's FP8 mode is therefore labelled `fp8_weight_only`.
- **Benchmark raw files** go to `data/raw/bench/<GPU_LABEL>/<RUN_ID>/`. In place of rule 2's
  per-file sidecar, `run_meta.json` and `env.json` describe every file in the run directory,
  since these are our own measurements, not downloads. Dry runs on stub binaries are tagged
  `dry_run: true` and the parser refuses them unless told otherwise, so stub numbers can't reach
  `data/`.
- **P2 root bracket.** δ is solved on [1e-6, 5] as the handoff specifies. An observed ratio at or
  above 1 implies non-positive decay, outside that bracket. It is reported as missing with the
  reason recorded, never clipped. In 2026 that can be a real outcome (rents rising), and the
  paper should report how often it happens.

## Decision 7: Benchmark model, frontier GPU and smoke-test card (2026-11-10)

- **Date:** 2026-11-10, chosen by the owner after a live read of Runpod's Secure Cloud catalog
  (`list-gpu-types`, one GPU, pods) and a check of Hugging Face access.
- **Model: Llama 3.1 8B Instruct** on every GPU. The owner also weighed Meta's newer Muse models:
  Glimmer (~30B dense, about 60 GB in BF16) does not fit the 24 and 48 GB cards, and Spark Open
  (816B MoE) needs a multi-GPU node. Alternative: Qwen 2.5 7B, which is ungated and
  readable with the owner's token today. Reason: it's the handoff's primary choice and the more
  standard benchmark model, which helps the MLPerf robustness rows. Blocker: the owner's current
  token gets HTTP 403 on the Llama repo, so the licence must be accepted (and the token given
  gated-repo read access) before any pod is rented.
- **Frontier GPU: B200**, with H200 as the fallback if no B200 is in stock on the day. The owner
  approved it on 2026-11-10 against the estimate in docs/bench_runbook.md (about $2.66 for ~20
  minutes; about $6.50 for all five GPUs). Catalog read 2026-11-10: B200 $7.99/hr, LOW
  stock, EU-RO-1 only; H200 SXM $5.29/hr, LOW stock in five data centres. Reason: B200 is a new
  architecture (Blackwell), so the H100-to-frontier efficiency ratio that calibrates P3's G
  reflects a real generation step, not just Hopper with more memory.
- **Smoke test on an RTX 3090**, not the handoff's RTX 4090, which had no Secure Cloud stock in
  that read ($0.89/hr when listed). RTX 3090: $0.50/hr, LOW stock, EUR-IS-2. Being Ampere, it also
  exercises the Marlin `fp8_weight_only` path the A100 will use. Label `RTX3090` added to
  `config/bench.yaml`. Like the 4090, it sits outside the paper's sample.
- **Amendment (2026-11-10, same day):** when the image was ready, `get-capacity` showed the
  RTX 3090 and RTX 4090 out of stock in Secure Cloud at CUDA 13.0 and 13.2. The smoke test moved to
  an **RTX A6000** (Ampere, 48 GB, $0.59/hr, Low stock). It keeps the Ampere `fp8_weight_only`
  check and, with 48 GB, does not run short of KV cache at concurrency 128. Label `RTX_A6000` added.
  Owner's standing instruction for this step: "whatever you recommend".
- **Amendment 2 (2026-11-10):** the RTX A6000 and RTX 4090 were refused for capacity five more
  times, though the catalog listed both as Low. The smoke test ran on an **A40** (Ampere, 48 GB,
  $0.59/hr, CA-MTL-1, pod `3fr96bavm534zl`). It passed the handoff's acceptance check: 24 of 24
  windows, every JSON parsed, power covered every window (largest gap 1.38 s), Marlin detected
  for `fp8_weight_only`, no confounds. Runpod's support notes report high demand for exactly the
  consumer and workstation cards tried (RTX 3090, 4090, 5090, A40, A6000), so later runs should
  expect stock to vanish between the catalog read and the create.
- **Amendment 3 (2026-11-10): frontier run on the H200 (owner's choice).** The B200 was refused for
  capacity five times between ~22:23 and ~23:21 UTC, while Runpod's catalog kept listing it as Low
  stock. Claude Code recommended waiting; the owner chose to run the approved H200 fallback now
  (pod `og4awvzz5s9dz8`, EUR-IS-4, $5.29/hr). Consequence for the paper: the frontier point is
  Hopper, the same architecture as the H100. The H100-to-frontier efficiency ratio that calibrates
  P3's G therefore reflects a memory-bandwidth refresh (HBM3e, 141 GB), not a new generation, and
  the FP4 format channel is not measured. A B200 run remains possible later as an addition.

## Decision 8: P3 power cost counts idle draw (2026-11-10)

- **Date:** 2026-11-10, chosen by the owner.
- **Choice:** the handoff's undefined `u_power` is replaced by an explicit idle term. Monthly power
  cost = e(t) × PUE × 730 h × [w_load × u + w_idle × (1 − u)] / 1000, plus maintenance. `w_load`
  and `w_idle` come from P1: mean board power during measured windows at the operating concurrency,
  and mean power in the idle window after each precision mode.
- **Alternatives:** `u_power = u`, which charges no power while the GPU waits for work.
- **Reason:** a GPU awaiting work still draws power: measured idle was 82–118 W against 276–678 W
  under load (A40, A100, H100, H200; 2026-11-10). Ignoring it makes old chips look cheaper to keep
  and pushes retirement ages later.

## Decision 9: P3 calibration choices (2026-11-10)

Made while building P3, within the handoff's design. The owner can reverse any of them.

- **Operating point:** concurrency 32 (handoff default) with each GPU's best available precision
  (handoff 3.4's "economically realistic" comparison). BF16-only values are written alongside
  in `data/processed/p3_calibration.json` as the like-for-like alternative.
- **Generation step (mu_G):** log(eta_H100 / eta_A100) = 0.459 (1.58x tokens/J per generation,
  best precision; 1.25x BF16-only). A100 to H100 is the only true architecture step in the sample.
  The H100 to H200 refresh (1.14x) is a same-architecture step and is reported as a lower-bound
  sensitivity, not used for mu_G. The handoff suggested both ratios; with the B200 missing, using
  the refresh would understate the frontier's pace. sigma_G cannot be identified from one step and
  is a placeholder (0.15).
- **Power path:** board power grows by the measured A100 to H100 ratio (1.43x) per generation, and
  throughput follows as q = eta x w. Idle draw is a constant share of loaded power, taken from
  generation 0 (A100: 0.24).
- **Rules:** the negative-margin rule applies in both regimes; the obsolescence rule applies only in
  the power-constrained regime and excludes the current frontier chip. The retirement month is the
  third consecutive month the condition holds. Margins count up to, not including, that month.
- **Valuation:** V(a) follows the handoff's sum, which leaves the current month undiscounted
  (annuity-due). Values are pooled across tracked generations as a share of each generation's own
  capex. The sum stops at the 180-month horizon, so V at old ages is slightly understated for
  long-lived chips (at most 120 observable months per generation).

## Decision 10: Epoch AI hardware data as P3's capex source; generation 0 re-anchored (2026-11-10)

- **Date:** 2026-11-10, approved by the owner under rule 7 after Claude Code read Epoch's pages,
  licence and data.
- **Source added:** Epoch AI, "Data on machine learning hardware" (CC BY 4.0; no terms-of-use
  page exists, `/terms` returns 404; the documentation offers programmatic CSV access). Archived
  at `data/raw/indices/epoch/2026-11-10/235424Z-ml_hardware.csv` with sidecar. Epoch's AI Chip
  Sales hub and its chip-price analysis were read but not added.
- **Capex anchor:** generation 0 is now the measured **H100 SXM** (not the A100), with
  **K0 = $33,600** all-in. Epoch's note derives this from an 8xH100 DGX server sold for $269k
  (SemiAnalysis, May 2023), so it includes the server share the handoff's capex definition asks
  for. The network fabric is excluded, which is a limitation. Epoch has no A100 80GB price, and
  its A100 40GB figure ($15,000) is a card price without a server share.
- **Capex growth per generation: 1.63x** = H100 GPU + baseboard bill of materials ($24.4k per GPU,
  same Epoch note) / A100 SXM4 40GB card price ($15,000), the closest like-for-like pair.
  Sensitivity scenarios: `capex_low` (K0 = $24,400, GPU + baseboard only) and `capex_flat`
  (growth 1.0x, the rough implication of Epoch's 49%/yr performance-per-dollar trend against our
  measured ~2.3x throughput step).
- **Empirical cadence scenario:** release gaps between NVIDIA data-centre architectures from the
  same file (V100 to A100 34.4 months, A100 to H100 28.2, H100 to B200 25.9) give an
  `empirical_cadence` scenario. The base scenario keeps the handoff's 24-month mean.
- **Rule 3:** the numbers come from `gel.models.p3_capex` reading the raw CSV, not hand-typed.
- **Alternatives:** keep the A100 as generation 0 with the $15,000 card price (rejected by the
  owner); wait for another source.
- **Still missing:** maintenance per GPU-month (Epoch has none). Claude Code is searching for a
  citable source to bring to the owner.

## Decision 11: P3 maintenance = 4% of capex per year (2026-11-10)

- **Date:** 2026-11-10, chosen by the owner after Claude Code searched for a source.
- **Choice:** M_g = 0.04 x K_g / 12 per GPU-month (about $112 for the H100 generation). Source:
  CloudRift, "The True Cost of GPU Ownership" (Natalia Trifonova, 2026-01-21): "Spares" line,
  spare parts and support contracts at 4% of capex annually, based on the author's conversations
  with data-centre operators. Sensitivity scenario `maintenance_high` at 12.5% (midpoint of GMI
  Cloud's "10-15% of hardware cost annually", 2026-04-14, uncited).
- **Quality:** weak. Both sources are blogs by GPU-rental vendors, and neither cites its figure.
  No peer-reviewed or primary source was found; SemiAnalysis's TCO model is paywalled. A search
  summary claimed GMI quoted "$20k-50k per 8-GPU system per year", but the page does not say
  that, so the claim was discarded. The paper must flag maintenance as weakly sourced.
- **Alternatives:** 12.5% base; $0 base with sensitivity; owner-supplied figure.
- **Form:** proportional to each generation's capex, following CloudRift's reasoning that spares
  and support "scale with system value".

## Decision 12: P3 placeholders replaced by calibrations; model fixes (2026-11-11)

- **Date:** 2026-11-11. The owner asked Claude Code to resolve the placeholders "with intelligent
  judgement" and approved researching field failure data. All values are written by
  `gel.models.p3_market_calibration` to `data/processed/p3_market.json` and referenced from
  `config/p3_model.yaml` as `from_market:...`, so nothing is hand-typed (rule 3).
- **Electricity:** EIA Form 861M (public domain; EIA is in the original source list), US
  industrial revenue / sales, 2016-09 to 2026-08. Mean = last 12 months, $0.089/kWh (Virginia
  $0.100, in a `virginia_power` scenario; this settles open question 3: national base, Virginia as
  sensitivity). OU kappa 0.43 and sigma $0.0096 from an AR(1) on the deseasonalised log price.
- **Scarcity markup:** m = rent / H100 all-in cost per sold GPU-hour - 1, using the model's own
  cost structure ($1.61/h). Level 0.90 = mean of Lambda's H100 on-demand markup while the H100
  was the frontier (2023-08 to 2025-05; B200 listings start 2025-06). Dynamics from AWS spot H100
  (2023-08 to 2026-10), the only market-like series: kappa 0.98, sigma 1.09 in markup units. Boom
  = Lambda's 2026 price ($4.14, from $3.14), markup 1.57: the handoff's "2026-like" level. The
  markup absorbs normal provider overhead (colocation, network, staff, sales) as well as
  scarcity, because the model's cost has no separate facility line. This is stated in the paper.
- **Markup process changed (model fix):** OU on log(1 + m), with a convexity-corrected long-run
  mean and m(0) drawn from the stationary law. The handoff's OU on m with a -0.5 floor drifted
  upward at the calibrated volatility (the floor clips the downside). The original process stays
  as the `markup_level_process` scenario: median 3.83 years against 4.08.
- **OU fitting is consistent with the simulator:** both use the same Euler step
  (phi = 1 - kappa dt), so calibrated parameters reproduce the observed AR(1).
- **Rent path (model fix):** E[rent(a)] / E[rent(0)] over the same paths, a ratio of means. The
  earlier mean of per-path ratios was biased upward by Jensen's inequality (12-month F/R0 above 1).
- **sigma_G = 0.086:** standard deviation of log BF16 FLOP/s-per-TDP-watt steps,
  V100 -> A100 -> H100 -> B200 (1.87x, 1.81x, 1.59x; Epoch). The spec-based mean step (1.75x)
  is a tornado case; the measured 1.58x stays the base.
- **Power regime:** p_stay_constrained = 1 - 1/48. A constrained spell lasts about as long as a
  grid-interconnection wait, which LBNL "Queued Up: 2025 Edition" (Rand et al., Dec 2025) puts at
  a median "over 4 years for those built in 2018-2024" (read on emp.lbl.gov). p_stay_unconstrained
  = 1 - 1/24 is a judgement: new capacity is absorbed faster than it is built. The long-run share
  constrained is 2/3. The chain starts constrained, given queue lengths and 2026's rising H100
  rents.
- **Physical failure:** constant hazard (Weibull shape 1), 2%/yr of permanent loss, a judgement
  based on field data in `data/raw/manual/gpu_failure_evidence.csv`. Incident rates on modern GPUs
  are 8-11% per GPU-year (Llama 3, 16,384 H100s: 268 GPU-category interruptions in 54 days =
  11.1%; Delta H100 uncorrectable-memory MTBE 88,768 h = 9.9%). These are upper bounds, because
  most incidents end in a reset, remap or warranty swap, not the asset's loss. Titan (Ostrouchov
  et al., SC20) found neither infant mortality nor wear-out over five years, which supports shape
  1. Its GitHub data has no licence and is not used. Scenarios: `failure_low` 0.5%,
  `failure_high` 11.1%, `failure_handoff` (8 years, shape 1.5). Llama 3's Table 5 is internally
  inconsistent (148 faulty-GPU events vs 30.1% of 419 = 126); the higher count is used.
- **Cadence:** the base keeps the handoff's 24-month mean (a design choice, not a placeholder);
  `empirical_cadence` uses Epoch's architecture gaps (26/28/34 months). NVIDIA's reported
  annual cadence could not be verified from NVIDIA's own pages and is not used.
- **Annuity term:** 60 months, the midpoint of the 4-6 year book lives being compared; the tornado
  varies it (48/72) with a swing of 0.17 years.
- **Validation (handoff 5.4)**, `gel.models.p3_validation`:
  1. Cross-section: model A100/H100 rent ratio 0.44 agrees within 25% with Lambda (0.57),
     CoreWeave (0.46) and AWS (0.42). Google Cloud disagrees, a basis mismatch (Decision 4).
  2. Term structure: model F/R0 1.00 at 12 months, 0.91 at 36. Neocloud observed medians are 0.91
     and 0.60; hyperscalers 0.62 and 0.38. Lambda's A100 commitments (0.88-0.92) match. The rest
     implies a term premium of about 10-12%/yr (neocloud) and 19-38%/yr (hyperscaler), consistent
     with sticky, inflated on-demand list prices (Phase 0 review). Reported as a documented
     failure of the rent-decay channel alone to explain hyperscaler term discounts.
  3. Scarcity: passes. The markup jump at month 36 lifts the oldest generation's rent from $2.20
     to $2.92/h while its efficiency gap widens (1.59x -> 1.65x).
  4. Tornado: the generation step dominates (median 8.7 years if steps are refresh-sized, 3.5 at
     spec size), then cadence, markup, maintenance and failure. Electricity, PUE, utilisation and
     the discount rate each move the median by 0.2 years or less.

## Decision 13: M4 price panel; sources, exclusions and the primary discount spec (2026-11-11)

- **Date:** 2026-11-11. The owner said to start M4 under Decision 6's rules (one manual pass,
  public pages, read each provider's terms first).
- **Manual sources recorded** in `data/raw/manual/prices_spot_panel.csv` and `prices_term.csv`,
  each price read by Claude Code in a browser from the provider's own page on 2026-11-11:
  - **Nebius**: no restriction in its terms (docs.nebius.com/legal/terms-of-use, 2025-03-31).
    Page copy saved.
  - **Together**: no scraping clause; §4.3(c) bars competitive analysis using its Services, which
    are not used here. Page copy saved.
  - **CoreWeave**: unclear. Its acceptable-use policy (aimed at customers) bars "harvesting or
    scraping of any content". Prices were read and cited; no page copy kept. Instance prices are
    per 8-GPU instance and are divided by 8.
- **Excluded:** Voltage Park, whose ToS §5.2(h) bars robots and also "any manual process" to
  extract content without written permission. Crusoe, whose Website Terms of Use v1.0
  (2024-08-12) give a "personal, non-commercial" licence and bar copying or publishing content
  without written permission. Vast.ai and RunPod listings stay out (Decision 3); only the RunPod
  price we paid is used.
- **Collector sources** for the same week (2026-11-10): AWS, Azure, Google Cloud (SkyPilot,
  accelerator-only basis, flagged), Lambda. Each provider contributes one price per chip and
  billing type, the median across its regions and SKUs.
- **Lambda parser fix:** Lambda added "NVIDIA HGX H100" and "NVIDIA HGX A100" cluster plans on
  2026-11-03 and the daily parse has failed since (no alerts are configured). HGX H100 now maps
  to `h100_sxm` (Decision 5's HGX = SXM rule); HGX A100 states no VRAM and is ignored. Days
  2026-11-03 to 11-10 were re-parsed locally from the raw pages (`gel.collect.lambda_backfill`).
  The droplet still runs the old config until redeployed (owner's call).
- **Coverage (on-demand providers):** H100 8 (the handoff's target), H200 7, B200 6, A100 80GB 5,
  L40S 4, A40 1 (only the RunPod price paid). Term prices: only Together's short reservations
  (3-30 and 31-90 days, kept as ranges); CoreWeave ("up to 60%") and Nebius commitments are
  "contact sales" and recorded as unpriced.
- **Primary discount spec:** D on the **neocloud median** on-demand price (handoff spec (b);
  hyperscalers flagged and shown alongside as the all-provider median), written to
  `paper/tables/p1_obsolescence_discount_median.csv` with provider counts. The paid-price spec
  (a) stays as a robustness column. Reason: hyperscaler list prices are structurally higher and
  sticky (Phase 0 review), and one provider's price is noisy. The two specs disagree: paid
  prices make every old chip look discounted, medians put most near parity.

## Decision 14: P1 and P2 results choices (2026-11-11)

- **Operating point for P1 figures:** concurrency 32 (handoff P3 default), best available precision
  for cost figures, BF16 for the like-for-like discount figure. P1-a shows all concurrencies.
- **Rental cost per token** uses the M4 neocloud median on-demand price (Decision 13); energy cost
  uses EIA's $0.089/kWh and PUE 1.3 (Decision 12), not the $0.08 default stored in the run snapshots.
- **L40S release date:** 2023-08-08, the NVIDIA announcement ("available starting this fall"),
  `data/raw/manual/chip_dates.csv`. Epoch has no L40S row, and its L40 (a different SKU) is not
  used as a proxy. Age error is at most about a quarter of a year.
- **P2 observations:** reserved/on-demand ratios for the same provider, chip and month from the
  Phase 2 history and the November live files, including Azure's 5-year reservations. Medians
  are taken across providers and months, separately for neoclouds and hyperscalers.
- **P2 estimation:** one constant delta per chip x provider type, least squares across tenors,
  on r {5, 8, 12}% x pi {0, 1, 2, 3}%/yr. Level 4 only where three tenors exist (H100,
  hyperscalers: 12/36/60). With three parameters on three points that fit is exact, so it is
  illustrative only.
- **L_opex** = age today + ln(R_now / opex) / delta, with R_now the group's current median on-demand
  price. opex = power (P1 c=32 board power x EIA price x PUE) + maintenance at 4% of the Epoch
  release price where Epoch has one (H100, H200); power only otherwise (A100 80GB, L40S), flagged.
- **`make figures`** regenerates every table and figure from raw data (bench parse -> M4 panel ->
  P1 tables and figures; P3 calibration, Monte Carlo and validation; P2) in about 40 seconds.
