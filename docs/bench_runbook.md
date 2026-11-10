# P1 benchmark runbook

How to run the cross-generation benchmark (docs/handoff_extension.md section 7, as amended by
Decision 6). GPU time is the scarce resource, so nothing here gets debugged on an expensive pod.

## Before any pod is rented (all free)

1. `make test`. This includes the CPU dry run on stub binaries.
2. `make bench-dryrun` and read its output. It writes to a temp directory, never `data/raw`.
3. **Model access (Decision 7: Llama 3.1 8B).** Accept the licence on the Hugging Face model page
   and use a token that can read gated repos (`HF_TOKEN`). On 2026-11-10 the local token got 403.
4. **Image.** Build and push from the repo root (owner step: it needs a registry account):

   ```bash
   docker buildx build --platform linux/amd64 -f bench/Dockerfile --build-arg BENCH_GIT_COMMIT=$(git rev-parse HEAD) -t <namespace>/gel-bench:v0.32.0 --push .
   ```

   Commit first, so the commit baked into the image matches the code.
5. **Runpod template.** Image `<namespace>/gel-bench:v0.32.0`, env `HF_TOKEN`, 60 GB container
   disk, expose **22/tcp**, and an SSH key on the account (Runpod injects it as `PUBLIC_KEY`).
   Secure Cloud, on-demand, for every GPU.

## Per GPU (one pod at a time)

| Order | GPU_LABEL | Modes | $/hr (catalog 2026-11-10) | Est. min | Est. cost |
| --- | --- | --- | --- | --- | --- |
| 1 | `RTX3090` (smoke test) | bf16, fp8_weight_only | 0.50 | ~50 | ~$0.42 |
| 2 | `A100_SXM` | bf16, fp8_weight_only | 1.79 | ~30 | ~$0.90 |
| 3 | `L40S` | bf16, fp8 | 1.09 | ~45 | ~$0.82 |
| 4 | `H100_SXM` | bf16, fp8 | 3.99 | ~25 | ~$1.66 |
| 5 | `B200` (else `H200_SXM`, $5.29) | bf16, fp8 | 7.99 | ~20 | ~$2.66 |
| | **Total** | | | **~2.8 h** | **~$6.50** |

Prices are Runpod Secure Cloud on-demand, one GPU, from `list-gpu-types` on 2026-11-10. Stock
changes; record the price actually shown at launch. Pods are billed per second, so a short run on
an expensive card stays cheap. Deploying a pod needs a balance of at least one hour at that rate
(about $8 for a B200), but that is a minimum balance, not a charge.

The minutes are my estimates, not measurements. Each pod gets roughly 15 minutes of fixed overhead
(image pull, a 16 GB weight download, two server starts with CUDA graph capture), plus the sweep:
753k output tokens per precision mode at the Decision 6 prompt counts. Low-bandwidth 24–48 GB cards
are the slow ones: at concurrency 1 an 8B BF16 model decodes at roughly memory bandwidth / 16 GB,
about 50 tok/s on a 3090 or L40S, and the 3090's KV cache cannot hold 128 sequences. The B200 is
mostly overhead. Budget about $10 to allow one rerun. The 3090 run replaces these guesses with
real timings.

1. Launch the pod. **Write down the exact $/hr shown at launch.**
2. Get a direct SSH command (`runpodctl ssh info <pod-id>`), connect, and start tmux:
   `tmux new -s bench`.
3. `cd /opt/gel && ./bench/run_all.sh <GPU_LABEL> <PRICE> runpod secure`
4. When it prints the tarball path, copy it off from your Mac:
   `scp -P <port> root@<ip>:/workspace/bench_out/results_<...>.tar.gz .`
5. Unpack into `data/raw/bench/<GPU_LABEL>/` and run `make bench-parse`.
6. **Terminate the pod** once the tarball is safely on the Mac. Stopped pods with volumes still bill.
7. Add a row to `data/raw/manual/gpu_spend_log.csv`.

**After the smoke test (RTX 3090): stop.** Continue only if `make bench-parse` prints `OK` for the run (every
JSON parses, power covers every window, parquet non-empty). Then compare the real minutes with
the table above before renting anything else.

## What the harness records

`data/raw/bench/<GPU_LABEL>/<RUN_ID>/`: `run_meta.json` (label, chip, price, provider, tier,
model, git commit, skipped modes, confounds, full config snapshot), `env.json` (driver, CUDA,
torch, vLLM, CPU, RAM, hashed GPU UUID and hostname, `nvidia-smi -q`), `power.csv` (nvidia-smi
every second for the whole run, each line stamped with host epoch ms), `windows.csv` (every
warmup, measured and idle window in epoch ms), `results/*.json` (vLLM's own result files) and
`logs/` (server, bench client, download).

If FP8 cannot load on a GPU, the mode is recorded under `skipped_modes` with the reason, and the
parser reports it. On Ampere the parser also checks the server log for vLLM's Marlin weight-only
warning (`fp8_marlin_detected`).

## Hand-recorded CSVs (`data/raw/manual/`, git-ignored like all raw data)

Decision 6: one manual pass in benchmark week, public pricing pages only, no Vast.ai or RunPod
listings. Read each provider's terms before its first row. Save a copy of each page next to the
CSV and name it in `page_copy`.

`gpu_spend_log.csv`

```
pod_id,gpu_label,provider,cloud_tier,price_per_hr_usd,launched_utc,terminated_utc,minutes,cost_usd,notes
```

`prices_spot_panel.csv`

```
observed_date,provider,provider_type,gpu_label,chip_id,interconnect,memory_gb,price_per_gpu_hr,billing,region,min_commitment,source_url,page_copy,notes
```

`prices_term.csv`

```
observed_date,provider,gpu_label,chip_id,tenor_months,price_per_gpu_hr,prepay,commitment_type,cluster_min_gpus,source_url,page_copy,notes
```

"Contact sales" is recorded as a row with an empty price and `notes=contact sales`, never a guess.

`external_reference.csv`

```
point_id,series,chip_id,date,value,unit,source_url,retrieved_utc,verified_by,notes
```

The handoff's two seed points (Ornn via Data Gravity, Silicon Data via fourweekmba) are **not
entered yet**. Both are secondary reports and must be checked against a primary source first.
See docs/open_questions.md.
