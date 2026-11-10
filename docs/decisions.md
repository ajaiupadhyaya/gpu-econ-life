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
