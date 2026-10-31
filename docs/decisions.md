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
