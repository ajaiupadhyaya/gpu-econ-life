# HANDOFF — Measuring the Economic Life of AI Accelerators
### Projects 1 + 3 + 2: Cross-generation benchmark → Power-constrained retirement model → Rental term-structure decay

**Owner:** AJ
**Purpose:** Extension of the solo paper on the market-implied economic life of AI accelerators (GPU rental prices vs hyperscaler depreciation schedules).
**Core contribution:** Pull apart the three things a GPU's rental price mixes together. Isolate **technological obsolescence** from **scarcity/demand shocks** and **physical wear**, then estimate economic life three independent ways and check them against each other.

---

## 0. Read this first — rules for Claude Code

1. **Never fabricate data.** Every price, benchmark number, or disclosure must trace to (a) a raw output file produced by our own harness, or (b) a row in a source-tracked CSV with `source_url` and `observed_date`. If a value is missing, leave it `NaN` and log it. Do not impute silently.
2. **Raw data is immutable.** `data/raw/` is append-only. All cleaning goes to `data/processed/` via scripts. Never hand-edit processed files.
3. **Reproducibility.** Pin all dependency versions (`uv.lock`). Set seeds for every stochastic component. Every figure must be regenerable from `make figures`.
4. **GPU time is the scarce resource (~3 hours total).** All benchmark code must be finished and dry-run tested on CPU (or the cheapest GPU) *before* any expensive pod is rented. No debugging on an H100/B200.
5. **Tests.** Every formula in `src/` gets a unit test with a hand-computed case (worked examples are given below).
6. **Ask AJ before** changing the research design, dropping a GPU type, or spending more than the planned GPU budget.

---

## 1. Research design in one page

| Project | Question | Method | Output |
|---|---|---|---|
| **P1 — Benchmark** | Is older hardware priced at what it produces? | Identical vLLM inference benchmark across 4–5 GPU generations; log power | tokens/s, tokens/J, $/M tokens, **obsolescence discount** per GPU |
| **P3 — Retirement model** | When is a GPU *economically* retired, given power is the binding constraint? | Structural model + Monte Carlo, calibrated on P1 | **Distribution** of retirement age; economic-depreciation schedule vs straight-line 4/5/5.5/6 yr |
| **P2 — Term structure** | What decay rate does the market price into multi-year rental contracts? | Invert contract-rate/spot-rate ratios; fit Nelson–Siegel-style decay curve | Implied decay rate δ(age) per generation; implied economic life |

**Triangulation:** P1 gives the cross-section (what the market pays for performance today), P2 gives market expectations (how fast that will change), and P3 gives the mechanism (why). The headline result is how closely the three agree. Where they disagree, that tells us something too: it shows where a scarcity premium is distorting prices.

**Build order:** P1 harness → (rent GPUs) → P2 data collection (runs in parallel; CPU only) → P3 model (calibrated on P1 + checked against P2) → triangulation + paper figures.

---

## 2. Repository structure

```
gpu-economic-life/
├── README.md
├── HANDOFF.md                  # this file
├── pyproject.toml / uv.lock
├── Makefile                    # make bench-parse, make p2, make p3, make figures, make test
├── config/
│   ├── gpus.yaml               # GPU specs: arch, launch date, memory, TDP, FP8/FP4 support, list price
│   ├── bench.yaml              # model, input/output lengths, concurrency sweep, repeats
│   └── p3_model.yaml           # all retirement-model parameters + distributions
├── bench/                      # runs ON the GPU pod
│   ├── Dockerfile              # FROM vllm/vllm-openai:<PINNED_VERSION>
│   ├── run_all.sh              # entry point: ./run_all.sh <GPU_LABEL> <PRICE_PER_HR> <PROVIDER> <CLOUD_TIER>
│   ├── run_vllm_sweep.sh       # serve + bench loop for one precision mode
│   ├── matmul_tflops.py        # optional raw-hardware microbenchmark
│   ├── capture_env.sh          # nvidia-smi -q, driver, CUDA, vLLM version, CPU, RAM → env.json
│   └── power_logger.sh         # nvidia-smi 1 Hz logger
├── data/
│   ├── raw/
│   │   ├── bench/<GPU_LABEL>/<RUN_ID>/   # vLLM JSONs, power CSVs, env.json, run_meta.json
│   │   ├── prices_spot_panel.csv         # cross-provider on-demand prices (P1 + P2)
│   │   ├── prices_term.csv               # reserved/term contract prices (P2)
│   │   └── external_reference.csv        # published index points (Silicon Data, Ornn, etc.)
│   └── processed/
├── src/gpuecon/
│   ├── bench_parse.py          # raw → tidy parquet
│   ├── energy.py               # power integration over benchmark windows
│   ├── metrics.py              # tokens/J, $/M tokens, obsolescence discount
│   ├── term_structure.py       # P2 inversion + curve fit
│   ├── retirement_model.py     # P3 structural model
│   ├── monte_carlo.py          # P3 simulation driver
│   ├── triangulate.py          # compare P1/P2/P3 implied lives
│   └── plotting.py
├── notebooks/                  # exploration only; nothing the paper depends on
├── tests/
└── outputs/
    ├── figures/
    └── tables/
```

---

## 3. PROJECT 1 — Cross-generation inference benchmark

### 3.1 Hardware plan (Runpod, ~3 h budget)

| Order | GPU | Minutes | Notes |
|---|---|---|---|
| 1 | RTX 4090 24GB | 15 | **Smoke test** the full pipeline end to end; cheapest |
| 2 | A100 80GB SXM | 25 | BF16 + FP8 (weight-only on Ampere — see 3.4) |
| 3 | H100 80GB SXM | 25 | BF16 + FP8 (native) |
| 4 | L40S 48GB | 20 | Inference-class Ada card; BF16 + FP8 |
| 5 | H200 or B200 | 20 | Frontier point; whichever is available |
| 6 | A100 | — | Reserved for P5 (SEC filing extraction), not this handoff |
| — | Buffer | 30 | Reruns / interruptions |

Use **Secure Cloud, on-demand** (not spot/community) for all benchmark GPUs. That keeps the price tier consistent and avoids interruptions. Record the exact $/hr shown at launch.

### 3.2 Benchmark specification (`config/bench.yaml`)

```yaml
model_primary: meta-llama/Llama-3.1-8B-Instruct   # gated: needs HF_TOKEN with access granted
model_fallback: Qwen/Qwen2.5-7B-Instruct          # ungated; use if Llama access isn't approved in time
dtype: bfloat16
max_model_len: 4096          # must fit a 24GB 4090 with KV cache
gpu_memory_utilization: 0.90
dataset: random
input_len: 512
output_len: 256
concurrency: [1, 8, 32, 128]
prompts_per_level: "20 x concurrency"
repeats: 3
warmup_prompts: 32           # discard
prefix_caching: false        # --no-enable-prefix-caching
seed: 42
precision_modes: [bf16, fp8] # fp8 skipped on hardware/versions that cannot run it; log the skip
```

**Pin one vLLM version for all GPUs.** It has to be recent enough to support Blackwell if a B200 is used. Record the version in `env.json`. If the frontier GPU forces a different version or CUDA build, flag it in `run_meta.json` as a confound and report it in the paper.

### 3.3 `run_all.sh` — behavior spec

```
Usage: ./run_all.sh <GPU_LABEL> <PRICE_PER_HR_USD> <PROVIDER> <CLOUD_TIER>
Example: ./run_all.sh H100_SXM 2.99 runpod secure
```
Steps:
1. `capture_env.sh` → `env.json` (GPU name, UUID-hash, driver, CUDA, vLLM version, `nvidia-smi -q` dump, CPU model, RAM, hostname-hash).
2. Write `run_meta.json`: GPU_LABEL, price, provider, tier, UTC start time, model used, git commit hash of this repo.
3. Download model weights **before** timing anything (`huggingface-cli download`).
4. For each precision mode:
   a. Start `vllm serve` in background with the config above (`--quantization fp8` for FP8 mode). Wait on `/health`.
   b. Warmup run (discarded).
   c. For each concurrency level × repeat:
      - Write `start_epoch_ms` to `windows.csv`
      - `vllm bench serve --dataset-name random --random-input-len 512 --random-output-len 256 --max-concurrency $C --num-prompts $((C*20)) --seed 42 --save-result --result-filename ${MODE}_c${C}_r${R}.json`
      - Write `end_epoch_ms` to `windows.csv`
   d. Kill server; sleep 10 s (lets power return to idle; that idle window is logged too).
5. `power_logger.sh` runs for the **entire** script:
   `nvidia-smi --query-gpu=timestamp,power.draw,utilization.gpu,temperature.gpu,clocks.sm,memory.used --format=csv,nounits -lms 1000`
6. Optional: `matmul_tflops.py` (torch matmul, 8192², BF16 and FP8 where supported, 50 iters after 10 warmup).
7. Tar everything into `results_<GPU_LABEL>_<UTC>.tar.gz` and print the path. **Results must be copied off the pod before it's terminated** (pod storage is ephemeral).

**Smoke-test acceptance (on the 4090):** every JSON parses, the power CSV covers every window, and `bench_parse.py` produces a non-empty parquet. Don't rent the next GPU until this passes.

### 3.4 Precision-mode caveat (important for the paper)

- **Ampere (A100)** has no FP8 tensor cores. vLLM's FP8 path on Ampere is **weight-only (W8A16)**. Label it `fp8_weight_only`, not `fp8`.
- **Hopper/Ada (H100, H200, L40S)** run native FP8 (W8A8).
- **Blackwell** also supports FP4. Optional extra mode if time allows.
- This is a measured channel of **format obsolescence**: older chips lose economic value because new number formats skip them. Report BF16-only comparisons as the "like-for-like" baseline and best-available-precision as the "economically realistic" comparison.

### 3.5 Metrics (`src/gpuecon/metrics.py`, `energy.py`)

For each GPU g, precision mode m, concurrency c (mean ± sd over repeats):

- **Throughput** `q` = output tokens/s (also keep total tokens/s, request/s, mean/p99 TTFT, mean/p99 TPOT). Verify JSON field names against the pinned vLLM version.
- **Energy per window** `E` = ∫ power dt over [start, end], trapezoidal rule on the 1 Hz log (joules).
- **Efficiency** `η` = output tokens / E  (tokens/J)
- **Cost per million tokens** `C$` = price_per_hr / (q × 3600) × 10⁶
- **Energy cost per million tokens** = (E / tokens) × 10⁶ / 3.6×10⁶ × electricity_price × PUE
  (defaults: $0.08/kWh, PUE 1.3. Both are config params; report sensitivity.)

**Obsolescence discount** (headline P1 number). Relative to a frontier GPU f, at matched concurrency:

```
D_g = (P_g / P_f) / (q_g / q_f) − 1
```
- `D_g < 0`: the market charges *less* per unit of output for the old chip than its performance alone would justify. The discount is obsolescence beyond raw speed (power, memory, format, software support).
- `D_g > 0`: the old chip carries a premium (scarcity, availability, contract flexibility).
- Compute D with (a) the price we actually paid and (b) the **median cross-provider spot price** from `prices_spot_panel.csv`. (b) is the primary spec, because one provider's price is noisy.
- Also compute an **energy-adjusted** version using cost per token including electricity, which matters to an owner more than a renter.

**Do not run a hedonic regression on 5 GPUs.** With n=5 it's underidentified. Report the ratios. For a robustness section, add published MLPerf Inference results to widen the cross-section (with source rows).

### 3.6 Cross-provider spot price panel (`data/raw/prices_spot_panel.csv`)

Collected once, same week as the benchmark:
```
observed_date, provider, gpu_label, interconnect(SXM/PCIe), memory_gb, price_per_gpu_hr, billing(on_demand/spot), region, min_commitment, source_url, notes
```
Target ≥8 providers per GPU where listed (e.g., Runpod, Lambda, CoreWeave, Nebius, Crusoe, Together, Vast.ai, Voltage Park, AWS/GCP/Azure list prices). Keep hyperscaler list prices in the panel but **flag them**, since they're structurally higher, and report medians both with and without them.

### 3.7 P1 outputs
- `outputs/tables/p1_benchmark_summary.csv`
- Fig P1-a: throughput vs concurrency, one line per GPU (BF16)
- Fig P1-b: tokens/J by GPU, ordered by launch date, BF16 vs best precision
- Fig P1-c: $/M tokens (rental) and $/M tokens (energy only) by launch date. Log scale on y.
- Fig P1-d: obsolescence discount D_g with provider-dispersion error bars

---

## 4. PROJECT 2 — Implied decay from rental term structure (CPU only)

### 4.1 Data (`data/raw/prices_term.csv`)

```
observed_date, provider, gpu_label, tenor_months, price_per_gpu_hr, prepay(bool), commitment_type, cluster_min_gpus, source_url, notes
```
- Tenors of interest: 1 (or on-demand), 6, 12, 24, 36, 60 months.
- Sources: public reserved/committed pricing pages, published index data, and any rate cards AJ obtains. Many long-tenor prices are "contact sales". **Record them as missing, don't guess.**
- `data/raw/external_reference.csv` holds published points used as calibration targets, each with URL. Seed rows (verify before using):
  - Ornn (via Data Gravity, 2026): 5-yr A100 rental ≈ 80% of 1-month rate; 5-yr B200 ≈ 54% of 1-month. https://www.datagravity.dev/p/the-gpu-depreciation-curve-is-broken
  - Silicon Data H100 neo-cloud index: $2.00 (2025-12-09) → $2.88 (2026-10-24). https://fourweekmba.com/ai-nvidia-h100-rent-up-44-as-anthropic-token-prices-halve/

### 4.2 Model (`src/gpuecon/term_structure.py`)

**Level 1: constant decay, no discounting.** A flat T-year contract at rate F equals the average expected spot rent, which decays exponentially at δ:
```
F/R0 = (1 − e^(−δT)) / (δT)
```
Solve for δ by root-finding (`scipy.optimize.brentq`, bracket [1e-6, 5]).

**Level 2: with discounting at rate r.** The lessor is indifferent between the flat rate F and the expected spot path:
```
F/R0 = [ (1 − e^(−(r+δ)T)) / (r+δ) ] / [ (1 − e^(−rT)) / r ]
```
Default r = 8% (cost of capital for a neocloud). Sweep r ∈ {5%, 8%, 12%}.

**Level 3: term premium π.** Long contracts price in credit risk, utilization certainty, and prepayment. Model the observed ratio as `(F/R0)_obs = (F/R0)_model(δ, r) × (1 − π·T)`. π isn't identified from one tenor, so **report δ over a grid π ∈ {0, 1%, 2%, 3%}/yr**. A positive π biases naive δ upward. State the direction explicitly in the paper.

**Level 4: age-varying decay (multiple tenors).** Let expected spot rent follow
```
R(t) = R0 · exp( −∫₀ᵗ δ(s) ds ),   δ(s) = β0 + β1 · exp(−s/τ)
```
β1 > 0 means fast early decay (the launch premium erodes) that settles to a long-run rate β0. Fit (β0, β1, τ) per generation by least squares on all available tenors. Constraints: β0 ≥ 0, β0+β1 ≥ 0, τ ∈ [0.25, 5] years. If fewer than 3 tenors exist for a GPU, fit Level 2 only and say so.

**Implied economic life (define two versions; report both):**
- `L_50`: age at which expected rent falls to 50% of launch rent
- `L_opex`: age at which expected rent falls below operating cost per GPU-hour (power × PUE × electricity + maintenance). Opex comes from P1 measured power. This is the one that ties to P3.

### 4.3 Unit tests (hand-checked)
- Level 1: F/R0 = 0.80, T = 5 → δ ≈ 0.092 (±0.002)
- Level 1: F/R0 = 0.54, T = 5 → δ ≈ 0.278 (±0.003)
- Level 2 with r → 0 converges to Level 1 (tolerance 1e-6)
- Level 4 with β1 = 0 reproduces Level 1/2

### 4.4 P2 outputs
- `outputs/tables/p2_implied_decay.csv` (gpu, tenor set, δ under each r/π, L_50, L_opex)
- Fig P2-a: observed F/R0 vs tenor, one series per GPU, with fitted curves
- Fig P2-b: implied δ(age) curves by generation
- Fig P2-c: heatmap of implied L_opex over (r, π)

---

## 5. PROJECT 3 — Power-constrained retirement model

### 5.1 Intuition (put this in the paper)

A data-center GPU rarely physically dies before it's retired. It's **evicted** when the power and rack slot it occupies would earn more running a newer chip. In a power-constrained market the scarce input is the **megawatt**, not the silicon, so economic life is set by **tokens per joule relative to the frontier**, not by wear. In a power-*unconstrained* market, an old chip survives as long as it covers its own operating cost. That's why the same chip can have very different economic lives in different regimes. Neither "6 years is fine" nor "it's 2–3 years" is right in general. It depends on the regime.

### 5.2 Model (`src/gpuecon/retirement_model.py`)

Time in months; generations g = 0, 1, 2, … launched at t_g.

**Hardware (calibrated from P1 + `gpus.yaml`):**
- `η_g` tokens/J, `q_g` tokens/s at operating concurrency (default c = 32), `w_g` kW board power under load (P1 measured), `K_g` capex per GPU (incl. share of server/network; config)
- Frontier progression: `η_{g+1} = η_g · G`, `G ~ LogNormal(μ_G, σ_G)`. Calibrate μ_G from the measured H100/A100 and B200-or-H200/H100 efficiency ratios. Report the calibration.
- Release cadence: `Δt ~` discrete {18, 24, 30, 36} months with config probabilities.

**Market:**
- Token price p(t), $/token. Competitive anchor: the frontier's all-in cost per token × (1 + markup m(t)).
  - `m(t)` = scarcity markup, OU process: `dm = κ(m̄ − m)dt + σ_m dW`, floored at −0.5. **This is the scarcity channel.** Spikes in m lift every generation's rent at once, which is exactly the confound from P1/P2.
- Electricity price e(t) $/kWh: OU around $0.08 (config), floored at $0.02.
- Power regime S(t) ∈ {constrained, unconstrained}: 2-state Markov chain, monthly transition matrix in config.

**Per-GPU monthly economics** (utilization u, default 0.70; PUE default 1.3; maintenance M_g $/GPU-month):
```
Revenue_g(t) = p(t) · q_g · 3600 · 730 · u
Opex_g(t)    = e(t) · w_g · PUE · 730 · u_power + M_g
Margin_g(t)  = Revenue_g(t) − Opex_g(t)
```

**Retirement rules:**
- *Unconstrained:* retire g at the first t where `Margin_g(t) < 0` for 3 consecutive months (avoid retiring on noise).
- *Constrained:* compare margin **per kW**. Retire g when
  `Margin_g/w_g  <  Margin_frontier/w_frontier − A_frontier/w_frontier`
  where `A_frontier` = annuitized frontier capex (K × r/(1−(1+r)^−n), monthly), held 3 months.
- Retirement is absorbing. Record retirement age `a_g = t_retire − t_g`. Also apply a physical-failure hazard (Weibull, config; default characteristic life 8 yr, shape 1.5) so a chip can drop out from wear first. Record *which* channel ended its life (obsolescence vs negative margin vs failure).

**Economic value and depreciation schedule:**
```
V_g(a) = E[ Σ_{s≥a} Margin_g(t_g+s) · (1+r_m)^−(s−a)  |  still alive ]
```
Economic depreciation in year k = V(k−1) − V(k). Compare against straight-line at 4, 5, 5.5 and 6 years on the same K_g. Also report the **cumulative gap** (accounting book value − economic value) by age.

### 5.3 Monte Carlo (`src/gpuecon/monte_carlo.py`)
- N = 20,000 paths (vectorized NumPy; must run in < 10 min on a laptop CPU), 180-month horizon, seed in config.
- Track generations launched in months 0–60 so each has a full observable life.
- Outputs per scenario: distribution of retirement age (mean, median, P10/P90), share of each retirement channel, mean economic-depreciation schedule, implied rent path (to compare with P2).

**Scenarios (all in `p3_model.yaml`):**
| Scenario | Cadence | Power regime | Scarcity markup |
|---|---|---|---|
| Base | 24 mo | Markov, calibrated | OU, moderate |
| Fast frontier | 18 mo | — | — |
| Slow frontier | 36 mo | — | — |
| Permanently power-constrained | — | always constrained | — |
| Power abundant | — | always unconstrained | — |
| Scarcity boom | — | — | high m̄ (2026-like) |

### 5.4 Validation (this is what makes it a paper, not a toy)
1. **Cross-sectional check vs P1:** model-implied rent ratios between generations at today's state vs observed P1 spot-price ratios.
2. **Term-structure check vs P2:** run the model forward from today's state, compute the flat-rate equivalent for 12/36/60-month tenors, and compare with P2 observed F/R0.
3. **Scarcity sanity check:** feed the scarcity-boom scenario and confirm it reproduces "old GPU rents rising while efficiency lag widens" (the 2026 H100 pattern). If it can't, the model is missing something. Say so.
4. **Sensitivity:** tornado chart of retirement-age sensitivity to G, cadence, electricity price, PUE, utilization, r.

### 5.5 P3 outputs
- Fig P3-a: retirement-age distribution, base vs power-constrained vs power-abundant
- Fig P3-b: economic value vs straight-line book value by age (4/5/5.5/6 yr)
- Fig P3-c: share of retirements by channel, by scenario
- Fig P3-d: tornado sensitivity
- Table P3: retirement age P10/P50/P90 per scenario

---

## 6. Triangulation (`src/gpuecon/triangulate.py`)

One table and one figure that sum up the paper:

| Generation | P1 obsolescence discount D | P2 implied L_opex (range over r, π) | P3 median retirement age (base; P10–P90) | Hyperscaler book life |
|---|---|---|---|---|

Fig T-1: per generation, three intervals (P1-implied, P2, P3) plotted next to the accounting lives (4, 5, 5.5, 6). Where the intervals overlap, that's evidence. Where they diverge, attribute the gap: use the scarcity markup state in P3 to explain how much of the P1/P2 rent level is scarcity rather than obsolescence.

**State this caveat in the paper:** hyperscaler useful lives cover blended fleets (CPU servers, storage, networking). Include a bounding exercise: if GPUs are share s of the server asset pool, the blended implied life is 1 / (s/L_gpu + (1−s)/L_other), for s ∈ {0.3, 0.5, 0.7} and L_other ∈ {6, 7}.

---

## 7. Runpod runbook (do this in order)

1. **Locally:** build and test `bench/Dockerfile`. Run `run_all.sh` in CPU-mode dry run (mock `vllm` and `nvidia-smi` with stub scripts that emit valid output) so the parsing pipeline is proven.
2. Accept the Llama 3.1 license on Hugging Face; create a read token. If access hasn't been granted in time, switch `model_primary` to the Qwen fallback **for all GPUs** (never mix models).
3. Runpod: create a template from the pinned image, env `HF_TOKEN`, 60 GB container disk, expose SSH.
4. Launch the **4090 first**. `git clone` the repo → `./bench/run_all.sh RTX4090 <price> runpod secure`. Copy the tarball off (scp over the pod's SSH port, or `runpodctl send`). Run `make bench-parse` locally. **Only proceed if it passes.**
5. Run each remaining GPU, one pod at a time. **Terminate each pod as soon as its tarball is copied off.** Stopped pods with volumes still bill.
6. Log actual minutes and $ spent per pod in `data/raw/gpu_spend_log.csv`.

---

## 8. Known pitfalls

- **Board power ≠ wall power.** `nvidia-smi power.draw` excludes host CPU, memory, fans, PUE. Apply PUE explicitly and say so.
- **Same-model rule.** Identical weights, prompts, seed, lengths and vLLM version on every GPU. Any deviation is a recorded confound.
- **Memory-bound vs compute-bound.** Low concurrency measures memory bandwidth; high concurrency measures compute. Report both. Obsolescence looks different in each regime, and that's a finding in itself.
- **SXM vs PCIe.** Match interconnect/variant in the price panel to the benchmarked variant.
- **Provider price dispersion is huge** (multi-x for the same chip). Always use medians plus dispersion bands, never one quote.
- **Survivorship in rental listings.** Listed prices only cover chips still deployed. Mention this as a bias toward longer implied lives.
- **The 2026 scarcity regime.** Rents for older chips rose in 2026. Don't read P1/P2 levels as pure obsolescence signals. P3's markup state is how we separate the two.

---

## 9. Milestones and acceptance criteria

| # | Milestone | Done when |
|---|---|---|
| M1 | Repo scaffold, configs, tests passing | `make test` green; P2 unit tests match hand values |
| M2 | Bench harness proven | 4090 smoke test → parquet with all windows + energy |
| M3 | All GPUs benchmarked | 4–5 GPUs × 2 modes × 4 concurrencies × 3 repeats; spend log ≤ 3 h |
| M4 | Price panels collected | spot panel ≥8 providers/GPU where available; term panel populated (missing = NaN) |
| M5 | P1 results | Summary table + Figs P1-a…d |
| M6 | P2 results | Implied δ table + Figs P2-a…c |
| M7 | P3 model | MC runs < 10 min; validation checks 1–4 reported (pass or documented fail) |
| M8 | Triangulation | Table + Fig T-1 + blended-fleet bounding table |
| M9 | Paper-ready | `make figures` regenerates everything from raw; README documents every assumption |

---

## 10. Open questions for AJ (answer before M3)
1. Llama 3.1 8B (gated) or Qwen 2.5 7B (ungated) as the single benchmark model?
2. H200 or B200 as the frontier point if both are available? (B200 adds the FP4 format channel but may force a newer vLLM build.)
3. Default electricity price and PUE for the base case. Use a specific region (e.g., Virginia data-center alley) or a national average?
4. Any rate cards from industry contacts that can go into `prices_term.csv`? Record the source as "private communication" with date.
