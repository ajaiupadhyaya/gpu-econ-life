# Assumptions

Every assumption with its value and source. "Judgement" marks a value Claude Code chose with the
owner's leave; each has a sensitivity case. Decisions are in `docs/decisions.md`.

## Shared

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| Electricity price | $0.089/kWh, US industrial, last 12 months (Virginia $0.100 scenario) | EIA Form 861M, archived 2026-11-11 (Decision 12) | P1 energy cost (EIA column), P2 opex, P3 opex |
| Electricity price (run snapshots) | $0.08/kWh | Handoff default, kept in each run's config snapshot for provenance | P1 `energy_cost_per_mtok_mean` only |
| PUE | 1.3 | Handoff 3.5 / 5.2 default | P1 energy cost, P2 opex, P3 opex |
| Utilisation u | 0.70 | Handoff 5.2 default | P3 economics, P3 markup calibration |
| Discount rate | 8%/yr (P2 grid 5/8/12%) | Handoff 4.2 / 5.2 default | P2, P3 annuity and valuation |
| Board power only | nvidia-smi power.draw; host CPU, memory and network excluded | Handoff pitfalls; PUE applied explicitly | P1, P2, P3 |
| Release dates | Epoch AI hardware data; L40S 2023-08-08 (NVIDIA announcement, "available starting this fall") | Epoch CSV; `data/raw/manual/chip_dates.csv` (Decision 14) | P1-c, P2 ages, M8 |

## P1 benchmark

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| Model | Llama 3.1 8B Instruct, identical on every GPU | Decision 7 | All runs |
| Serving stack | vLLM 0.32.0 (image `ajaiupad/gel-bench:v0.32.0`), BF16, max length 4096, GPU memory 0.90, no prefix caching, seed 42 | Decision 6, `config/bench.yaml` | All runs |
| Workload | random dataset, 512 input / 256 output tokens (ignore_eos), concurrency 1/8/32/128 | Handoff 3.2 | All runs |
| Prompts per level | 20 / 160 / 160 / 640 | Decision 6 (trimmed from 20xC to fit GPU time) | All runs |
| Repeats, warmup | 3 repeats; one 32-prompt warmup per precision mode, discarded | Handoff 3.2 | All runs |
| FP8 | `--quantization fp8` (vLLM 0.32.0's deprecated alias for per-tensor online FP8): W8A8 on Ada/Hopper, Marlin W8A16 (`fp8_weight_only`) on Ampere | Decision 6; vLLM source; run logs | P1, P3 calibration |
| Energy window | vLLM's own benchmark duration ending at the window close (`energy_j_active`); full wrapper window kept too | `gel.bench.parse` docstring | Tokens per joule |
| Power coverage | a window passes if no gap between 1 Hz samples exceeds 2.5 s | `config/bench.yaml` | Acceptance check |
| Frontier GPU | H200 SXM (B200 refused for capacity five times) | Decision 7, amendment 3 | Discount D, P3 refresh step |
| Operating point | concurrency 32, best available precision (BF16 for like-for-like) | Handoff 5.2; Decisions 9, 14 | P1-b/c/d, P3 calibration |
| Rental price, primary | neocloud median on-demand price per chip (M4 panel) | Handoff 3.5 spec (b); Decision 13 | P1-c, P1-d, M8 |
| Rental price, robustness | the RunPod Secure Cloud on-demand price paid at launch | Handoff 3.5 spec (a) | `p1_obsolescence_discount.csv` |

## M4 price panel

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| Snapshot | collector 2026-11-10; manual reads 2026-11-11 | Decision 13 | All M4 outputs |
| One price per provider | median across that provider's regions and SKUs, per chip and billing type | `gel.build.spot_panel` | Medians |
| Per-GPU price | instance price / GPU count (CoreWeave 8-GPU instances / 8) | Provider pages | Panel |
| Nebius L40S | "from" price, Intel-CPU configuration ($1.55; AMD $1.82 noted) | Nebius pricing page | Panel |
| Hyperscalers | AWS, Azure, Google Cloud flagged; medians reported with and without them | Handoff 3.6 | Medians |
| Google Cloud basis | SkyPilot rows are accelerator-only (host VM excluded) | Decision 4 | Flagged in panel, excluded from cross-section check |
| Excluded providers | Vast.ai and RunPod listings (terms; Decision 3); Voltage Park and Crusoe (terms; Decision 13) | Provider terms | Panel |

## P2 term structure

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| R0 | on-demand price, same provider, chip and month | Handoff 4.2 | Observed F/R0 |
| Observations | reserved 1 y, 3 y and Azure 5 y vs on-demand; Phase 2 history plus November live files; median across providers and months, by provider type | Decision 14 | `p2_observed_ratios.csv` |
| Decay model | constant delta, least squares across tenors (Level 2/3); Level 4 only with three or more tenors | Handoff 4.2; Decision 14 | `p2_implied_decay.csv` |
| Term premium grid | pi in {0, 1, 2, 3}%/yr | Handoff 4.2 | P2-c |
| L_opex | age today + ln(R_now / opex) / delta, R_now = group's current median on-demand price | Decision 14 | P2-c, M8 |
| Opex per GPU-hour | P1 board power at c=32 x EIA price x PUE, plus maintenance at 4% of the Epoch release price where Epoch has one (H100, H200); power only otherwise (A100 80GB, L40S) | Decisions 11, 14 | L_opex |
| Age | years from release date to 2026-11-11 | Release-date row above | L_opex, M8 |

## P3 retirement model

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| Paths, horizon, tracking | 20,000 paths, 180 months, generations launched in months 0-60 | Handoff 5.3 | All scenarios |
| Generation 0 | H100 SXM (measured) | Decision 10 | Hardware path |
| Generation step mu_G | 0.459 (x1.58 tokens/J) | Measured, P1 A100->H100 at c=32, best precision (Decision 9) | Frontier progression |
| Generation step sigma_G | 0.086 | Epoch: sd of log FLOP/W steps V100->B200 (Decision 12) | Frontier progression |
| Power step per generation | x1.43 | Measured, P1 A100->H100 board power at c=32 | Hardware path |
| Idle share of loaded power | 0.21 (H100, gen 0) | Measured, P1 idle window vs c=32 load (A100 0.24) | Opex (Decision 8) |
| Capex per GPU (gen 0, H100) | $33,600 all-in (sensitivity $24,400) | Epoch AI hardware data (CC BY 4.0), citing SemiAnalysis DGX H100 $269k/8 (Decision 10) | Annuity, price anchor |
| Capex growth per generation | 1.63x (sensitivity 1.0x) | Epoch: H100 GPU+baseboard $24.4k / A100 40GB card $15,000 (Decision 10) | Annuity, price anchor |
| Maintenance | 4% of capex/yr (~$112/month for H100); sensitivity 12.5% | CloudRift blog 2026-01-21 (weak, vendor); GMI Cloud 10-15% (Decision 11) | Opex |
| Capex annuity term | 60 months (tornado 48/72) | Judgement: midpoint of 4-6 y book lives (Decision 12) | Frontier annuity |
| Retirement hold | 3 months | Handoff 5.2 | Rules |
| Physical failure | constant 2%/yr permanent loss; scenarios 0.5%, 11.1%, handoff's 8 y / shape 1.5 | Judgement on field data: Llama 3, Delta, Titan (Decision 12) | Failure channel |
| Release cadence | 18/24/30 months w.p. 0.25/0.50/0.25 (mean 24); empirical scenario 26/28/34 | Handoff base design; Epoch gaps (Decision 12) | Base scenario |
| Scarcity markup m(t) | log-OU, mean 0.90, kappa 0.98, sigma 1.09, floor -0.5, stationary start | Lambda H100 on-demand level; AWS spot H100 dynamics (Decision 12) | Token price |
| Scarcity boom | m mean 1.57 | Lambda H100 $4.14 in 2026 (Decision 12) | Scenario |
| No scarcity | m = 0 (price = frontier full cost) | Decision 15 | Attribution scenario |
| Electricity OU | kappa 0.43, sigma $0.0096, floor $0.02 | EIA-861M AR(1), deseasonalised (Decision 12) | Opex |
| Power regime | stay 0.979 constrained / 0.958 unconstrained; start constrained | LBNL Queued Up 2025 (>4 y queue) + judgement (Decision 12) | Base scenario |

## M8 triangulation

| Assumption | Value | Source | Used in |
| --- | --- | --- | --- |
| Generations | A100 80GB, H100 SXM, H200 SXM (SXM line with data in all three methods) | Decision 15 | `m8_triangulation.csv` |
| P1-implied decay | cross-sectional slope of log neocloud rent on age (0.23/yr at medians; 0.21-0.27 at max/min prices) | Decision 15 (vintage-price assumption) | P1 life to opex |
| Accounting lives | 4, 5, 5.5, 6 years (generic set; firm-specific lives await Phase 7) | Handoff section 6 | T-1 |
| Blended fleet | 1/(s/L_gpu + (1-s)/L_other), s in {0.3, 0.5, 0.7}, L_other in {6, 7} | Handoff section 6 | `m8_blended_fleet.csv` |
