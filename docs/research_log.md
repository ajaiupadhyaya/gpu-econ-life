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
