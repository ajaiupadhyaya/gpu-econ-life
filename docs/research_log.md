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

## A100 SXM run, 2026-11-10

Pod `hqtiegsvysdv5h` (US-MD-1, $1.79/hr) placed on the second attempt at 20:00:17 UTC. Container up
within ~5 minutes; benchmark 20:06:43 to ~20:36:40; results copied off (checksums matched) and
the pod terminated at 20:37:40. `make bench-parse`: OK for both runs (48 rows), power covered
every window (largest gap 1.42 s), Marlin detected. Early observations, not yet results: the A100
is 2.3 to 2.7× the A40's throughput and 1.7 to 2.1× its tokens per joule, yet it costs more per
token at Runpod's list prices at every concurrency. A40 rental looks cheap relative to output.
Idle board power after each mode ~90 W.

Billing note: `list-pod-billing` (read 20:38 UTC) shows a pod `66klutbsdm6402`, not created by
Claude Code, with $0.059 in the 19:00 bucket. It no longer exists (`list-pods` empty). Every
create call in this session either returned 400 or produced the A40 or A100 pods. Flagged to the
owner.

## H100 SXM run, 2026-11-10

Pod `e73k3rnpzm336u` (CA-MTL-1, $3.99/hr) placed on the first attempt at 22:00:32 UTC. Container
up within ~4 minutes; benchmark 22:04:57 to 22:22:25; results copied off (checksums matched) and
the pod terminated at 22:22:45. `make bench-parse`: OK for all three runs (72 rows), power covered
every window (largest gap 1.08 s). FP8 ran natively (no Marlin warning in the server log).
Early observations: native FP8 adds 49% throughput at concurrency 1 and 29% at 128 over BF16,
and 37 to 57% more tokens per joule. On Ampere, by contrast, weight-only FP8 was slower than
BF16 at 128. Idle board power ~118 W.

vLLM 0.32.0 logs: "--quantization fp8 is deprecated for online quantization; use
--quantization fp8_per_tensor instead." Every GPU used the same flag, so this is not a confound
across runs. Keep `fp8` for the remaining GPUs for consistency, and note it in the paper.

B200: refused for capacity twice at ~22:23 UTC (any data centre, then EU-RO-1), despite Low stock
in the catalog. L40S: out of stock.

## H200 SXM run (frontier fallback), 2026-11-10

Pod `og4awvzz5s9dz8` (EUR-IS-4, $5.29/hr) placed on the second attempt at 23:21:42 UTC, after five
B200 refusals between ~22:23 and ~23:21 (the owner chose the fallback). Benchmark 23:26:06 to
~23:41; results copied off (checksums matched) and the pod terminated at 23:42:09. `make
bench-parse`: OK for all four runs (96 rows); one model, one vLLM version, no confounds; power
covered every window (largest gap 1.05 s); native FP8. `gel.bench.report --frontier H200_SXM`
wrote `paper/tables/p1_benchmark_summary.csv` and `p1_obsolescence_discount.csv` (paid-price spec).

Early observations, not yet results (paid Runpod prices, one provider, so noisy; the primary spec
needs the cross-provider spot panel): against the H200, every older GPU is priced *below* its
relative output in the like-for-like BF16 comparison (D from -0.02 to -0.36). The A40 is the
cheapest per unit of output (D about -0.30 to -0.36), and the discount grows with chip age. The
one positive D is the A100 at concurrency 128 under best-available precision (+0.18), because
Ampere's weight-only FP8 cannot help at high load: format obsolescence leaves it with BF16
throughput only. The H200 adds 16 to 30% throughput over the H100 at a 33% higher price.
Idle board power ~94 W.

## First full P3 run, 2026-11-11

`make p3` ran end to end: calibration from P1, capex from Epoch (Decision 10), maintenance at
4% of capex (Decision 11), 10 scenarios at N = 20,000 in about 9 seconds. Outputs:
`paper/tables/p3_retirement_by_scenario.csv`, `p3_value_vs_book.csv`, `p3_summary.json`.

Preliminary, with placeholders still in place (docs/assumptions.md):
- Base median retirement 5.25 years (P10 1.8, P90 8.9). Power-constrained 4.8, power-abundant
  6.3, fast frontier 4.7, slow frontier 6.2, scarcity boom 3.7, empirical cadence 5.7, flat
  capex 4.2, high maintenance 4.5.
- **Physical failure ends 59% of lives in the base case**, under the handoff's Weibull default
  (8-year scale, shape 1.5). The retirement distribution is largely set by that assumption,
  and P10 (~1.8 years) is pure failure. It needs field data before any result is reported.
- Economic value is front-loaded: V/K falls 0.92 -> 0.72 -> 0.53 -> 0.40 over years 0-3. That is
  below 6-year straight-line book value in years 1-3 and above 4-5-year book from year 3, with a
  long tail.
- V(0)/K = 0.92 in the base case: buying a new GPU at list capex is slightly NPV-negative at a
  20% average markup, mostly because failure truncates life. In the scarcity boom V(0)/K > 1.
- The model-implied 60-month flat-rate ratio F/R0 is 0.83 (36-month 0.93). That is close to the
  handoff's unverified Ornn A100 point (~0.80), but this is not yet a validation: check 2 needs
  P2's observed ratios.
- Regime does not move the rent path (price is set by the frontier's cost), and the boom scenario
  starts high, so validation check 3 (boom raises old-chip rents) needs a mid-path markup jump.

## P3 calibrated and validated, 2026-11-11

The owner asked Claude Code to resolve the P3 placeholders with its own judgement and approved
the failure-data research. Decision 12 records every value and its source. Two model artefacts
surfaced and were fixed: the floored OU markup drifted upward at the calibrated volatility (now a
stationary log-OU), and the rent path used a mean of ratios (now a ratio of means). Calibrated
base results (N = 20,000, 16 scenarios, ~17 s):

- Base median retirement 4.08 years (P10 2.17, P90 7.00); 90% of retirements are obsolescence,
  9% failure.
- Power regime decides it: always constrained 3.58 years; power abundant 11.0 years (44% still
  running at the horizon, 34% retired on negative margin).
- Fast frontier 3.17, slow 5.58, empirical cadence 4.67; scarcity boom 2.83; high maintenance
  3.25; flat capex 3.50; failure at the 11% incident upper bound 3.17; handoff's original failure
  curve 3.50.
- Economic value starts at 1.39x capex at a 0.90 markup and falls to 1.00 at year 1, 0.63 at year
  2 and 0.47 at year 3. That is above every straight-line book value (4-6 years) from year 2 on,
  with a long tail (0.27 at year 5).
- Implied flat-rate ratios: 1.00 (12 months), 0.91 (36), 0.81 (60).
- Validation: cross-section agrees for Lambda, CoreWeave and AWS. The term structure matches
  Lambda's A100 commitments but not hyperscaler reserved discounts (term premium 19-38%/yr
  needed). The scarcity jump passes. In the tornado the generation step dominates by far.

These are not yet paper results: P2's write-up, the spot panel (M4) and triangulation (M8) are
still to come.

## L40S run; P1 complete, 2026-11-11

Pod `uw5ykj7y5tbb3y` (OC-AU-1, $1.09/hr) placed on the first attempt at 00:15:59 UTC. Benchmark
00:21:32 to ~01:00; results copied off (checksums matched) and the pod terminated at 01:01:19.
`make bench-parse`: OK for all five GPUs (120 rows); one model, one vLLM version, no confounds;
native FP8 on Ada. Spend (Runpod billing, final): A40 $0.63, A100 $1.12, H100 $1.48, H200
$1.81; L40S about $0.82 pending. Total about $5.86 for ~3.2 GPU-hours.

Billing also lists pods Claude Code did not create: `nvb5w84zur9dfh` ($1.73) and
`wxm8ugeu3zsbqy` ($1.30), both 2026-11-10 01:00-04:00 UTC, before this session's first pod;
`66klutbsdm6402` ($0.06) and `2wu4kaqd5b58gn` ($0.08). Flagged to the owner.

P1 like-for-like discount vs H200 (paid prices): A40 -0.30 to -0.36; A100 -0.08 to -0.24;
L40S -0.09 to -0.17; H100 -0.02 to -0.12. Every older chip rents below its relative output.

## M4 price panel, 2026-11-11

Terms checked for five manual providers. Nebius, Together and CoreWeave were recorded; Voltage Park
and Crusoe were excluded by their terms. Prices were read from each provider's page in the
in-app browser; the fetcher's summaries were not trusted for price pairing. Found and fixed an
8-day silent failure in the droplet's Lambda parse (a new plan name). The panel has 51 provider
prices (H100 8 providers on-demand). On neocloud median prices the like-for-like discount against
the H200 is near parity for the H100 (-0.08 to +0.03) and A100 (-0.12 to +0.07). The L40S
carries a premium (+0.09 to +0.20). The A40 (-0.35 to -0.41) rests on one price. Paid-price
discounts were uniformly negative because RunPod is cheap: one provider's price misleads.

## Lambda parser fix deployed, 2026-11-11

With the owner's go-ahead, `deploy/push.sh` shipped commit 9273467 to the droplet (previously
3f51fbe). `gel.collect.lambda_backfill` ran on the host as user `gel`, re-parsing the saved raw
pages for 2026-11-03 to 11-10 (20 rows a day; no new requests to Lambda). The daily timer stays
active (next run 06:11 UTC). OhCamel, Tidewater and Strata containers were unaffected. The host's
`runs/<day>.json` summaries for those days still record the original failure, which is accurate
history.

## M5 and M6: P1 and P2 results, 2026-11-11

Built the shared plotting style (`gel.viz.style`, the dataviz skill's validated palette), the P1
figures P1-a to P1-d and the P2 module with figures P2-a to P2-c (`gel.models.p2_term`). Each
figure was rendered and inspected, and label collisions were fixed. `make figures` regenerates
everything from raw data in about 40 seconds. A single-scenario P3 sanity run briefly overwrote
the 16-scenario P3 tables; they were regenerated with `make p3`. Summary in
`docs/results_p1_p2.md`.

## M8 triangulation, 2026-11-11

Added a no-scarcity P3 scenario (median 10.7 years vs 4.1 base) and `gel.models.triangulate` with
Fig T-1, attribution and the blended-fleet table, wired into `make figures`. Main finding: the
market-based lives to operating cost (P1, P2) and P3 without power constraints agree on a long life
(roughly 10 years and up). P3 in a power-constrained market with a scarcity markup gives about 4
years, inside or just below the 4-6 year accounting band.

## M9: reproducible from raw data, 2026-11-11

Rebuilt every output from scratch in a scratch copy of the repository (the project's own outputs
were not deleted). A missing Makefile dependency surfaced and was fixed. After that, all 26
outputs reproduced exactly apart from timestamps and runtimes. Added the EIA-priced energy-cost
column, reorganised `docs/assumptions.md` and rewrote the README. All nine handoff milestones are
now met.

## Billing attribution resolved, 2026-11-11

The two larger pods flagged earlier as unattributed, `nvb5w84zur9dfh` ($1.73, 2026-11-10 01:00-03:00
UTC) and `wxm8ugeu3zsbqy` ($1.30, 02:00-04:00 UTC), belong to the owner's separate look-ahead probe
project, which rented a Runpod A100 that morning in a different session (its notes name
`nvb5w84zur9dfh`). They are not this project's spend and not a leak.
