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

## Extension handoff, 2026-11-10

The owner brought a handoff from Claude Chat adding a GPU benchmark (P1), a term-structure decay
inversion (P2) and a retirement model (P3). Claude Code checked it against the existing repo,
raised three conflicts (repo location, price-panel sources, benchmark minutes) and recorded the
answers as Decision 6. Work started on branch `feat/extension-bench-term-structure`.

## First GPU run (smoke test), 2026-11-10

Claude Code built and pushed the pod image (`ajaiupad/gel-bench:v0.32.0`), stored the owner's
Hugging Face token as a Runpod secret (the owner entered it), and after eight capacity refusals
across three card types ran the full sweep on an A40. Timeline (UTC): pod created 18:46:30;
image pulled and container up 18:53:43; benchmark started 18:55:44; weights downloaded and first
measured window 18:57:58; BF16 finished ~19:26; FP8 weight-only finished 19:48:10. The tarball was
copied off (checksums matched) and the pod terminated. `make bench-parse` passed.
Early observations, not yet results: Ampere's weight-only FP8 speeds decoding 1.78× at
concurrency 1 but is *slower* than BF16 at concurrency 128 (1,192 vs 1,370 tok/s), consistent
with the format-obsolescence channel. Idle board power after each mode was ~82 W against ~299 W
under load.
