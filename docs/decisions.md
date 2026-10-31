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
