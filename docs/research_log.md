# Research log

A short note of what Claude Code did in each phase. This becomes the AI-assistance disclosure.

## Phase 0, 2026-10-31

Claude Code (Opus 5.5) built the repository scaffold, the HTTP and raw-storage helpers, the Wayback
CDX coverage tool and its tests, and logged H1–H4 as Decision 1. Subagents drafted the source audit,
the literature check and the fact-check of the proposal's claims. Claude reviewed the proposal and
ran an exploratory probe of unlisted price histories. Two Phase 0 stop conditions were met (a close
prior paper; terms of use on the live layer), so work stopped for the owner's decision. All research
decisions remain the owner's.

## Phase 1, 2026-10-31

The owner approved the revised plan. Claude Code built the canonical schema, four collectors, parsers,
a runner, a health check and a deployment kit, with tests, and ran the first real collection: 2,370
valid rows from Azure, AWS, Google Cloud and Lambda. It verified SKU mappings against vendor
documentation and updated the Claude Doc to match the plan. Deployment to a host awaits the owner.

## Deployment, 2026-10-31

The owner chose the OhCamel droplet. Claude Code installed the collector under a dedicated `gel`
user with resource limits and a sandbox, copied existing raw data across (156 files, checksums
matched), ran a collection on the host (2,370 rows, four providers, healthy) and enabled the daily
timer. OhCamel's containers were unchanged. Backups and alerts await the owner's accounts.

## Phase 2, 2026-10-31

Claude Code built the snapshot selection and downloader, the AWS and SkyPilot history pullers, the
Lambda parser, the coverage report and the validation sample. Two subagents wrote the CoreWeave and
Paperspace parsers, which Claude Code spot-checked against raw pages. All 285 snapshots have a status
(253 parsed, 32 verified empty, 0 failed), giving 35,733 historical rows. Lambda's archive prices
matched SkyPilot in 270 of 278 overlapping chip-months, and the other 8 fall in months when Lambda
changed prices. The owner hand-checked the 40-row sample and found no errors, which completes Phase 2.
