# gpu-econ-life

How long does an AI accelerator stay economically useful, and how does that compare with the
4-6 year useful lives in hyperscaler accounts? This repository estimates it three independent
ways and checks them against each other:

- **P1 Cross-generation benchmark.** The same vLLM inference benchmark on five GPU generations
  (A40, A100 80GB, H100 SXM, L40S, H200 SXM), with measured power, priced at a hand-collected
  cross-provider rental panel. Is older hardware priced at what it produces?
- **P2 Term structure.** Decay rates implied by reserved/on-demand price ratios. What
  obsolescence does the contract market price in?
- **P3 Retirement model.** A Monte Carlo of when a GPU is evicted, by newer chips in a
  power-constrained market or by negative margins, calibrated on P1 and on market data.

The original paper (rental-implied depreciation; see [docs/proposal.md](docs/proposal.md) and
[docs/proposal_review.md](docs/proposal_review.md)) supplies the historical price panel. The
extension that added P1-P3 is specified in [docs/handoff_extension.md](docs/handoff_extension.md).
Project rules are in [CLAUDE.md](CLAUDE.md).

## Status (2026-11-11)

| Milestone | State |
| --- | --- |
| Phase 0-2: proposal review, live collector, historical panel (35,733 rows) | Done; collector runs daily on a server |
| M1 Scaffold, configs, tests | Done (432 tests) |
| M2 Benchmark harness (CPU dry run + GPU smoke test) | Done |
| M3 Five GPUs benchmarked (~3.2 GPU-hours, ~$5.86) | Done; frontier is the H200 (B200 unavailable) |
| M4 Cross-provider price panel | Done (8 providers for H100; A40 has one price) |
| M5 P1 results, figures P1-a to P1-d | Done |
| M6 P2 results, figures P2-a to P2-c | Done |
| M7 P3 model, calibration, validation checks 1-4 | Done (check 2 fails for hyperscalers, documented) |
| M8 Triangulation, Fig T-1, blended-fleet bounds | Done |
| M9 Reproducible from raw data; assumptions documented | Done (clean rebuild verified) |
| Phase 3+ of the original plan (reference tables, firm-level restatement) | Not started |

Results so far are summarised in [docs/results_p1_p2.md](docs/results_p1_p2.md).

## Reproduce

```bash
uv sync
make test       # 432 tests
make figures    # every table and figure from raw data, ~50 s on a laptop
```

`make figures` runs, in dependency order: parse the benchmark runs -> build the M4 price panel ->
P1 tables and figures -> P3 calibration (hardware from P1, capex from Epoch, market processes
from prices and EIA) -> Monte Carlo (17 scenarios) -> validation -> P2 -> triangulation. On
2026-11-11 a copy of the repository with every generated output deleted was rebuilt this way.
All 26 outputs matched the committed versions, apart from generation timestamps and runtimes.

Other targets: `make bench-dryrun` (benchmark harness on stub binaries), `make p3` (Monte Carlo
only, all scenarios), `make collect` / `make health` (live collector), `make lint`.

Running a GPU benchmark (Runpod) is described in [docs/bench_runbook.md](docs/bench_runbook.md).

## Data

Raw data lives in `data/raw/` (append-only, every file with a sidecar `.json` of source URL,
UTC retrieval time and HTTP status). It is **not in git**. It is kept on the owner's Mac and on
the collection server; automated backups are not yet configured. What `make figures` needs:

| Path | What | Licence / terms |
| --- | --- | --- |
| `data/raw/bench/<GPU>/<run>/` | benchmark runs: vLLM results, 1 Hz power log, windows, env, run metadata | own measurements |
| `data/raw/wayback/`, `aws_offers/`, `skypilot_history/`, `live/` | historical and daily rental prices (Phase 1-2) | see [docs/data_sources.md](docs/data_sources.md) |
| `data/raw/manual/prices_spot_panel.csv`, `prices_term.csv`, `pages/` | hand-recorded neocloud prices (Nebius, Together, CoreWeave) with page copies where terms allow | Decision 13 |
| `data/raw/indices/epoch/` | Epoch AI "Data on machine learning hardware" | CC BY 4.0 |
| `data/raw/eia/` | EIA Form 861M monthly sales and revenue | public domain |
| `data/raw/manual/gpu_failure_evidence.csv`, `chip_dates.csv` | figures transcribed from cited papers and NVIDIA's newsroom | citations in file |
| `data/raw/manual/gpu_spend_log.csv` | GPU spend per pod (Runpod billing) | own records |

Excluded by their terms: Vast.ai, RunPod listings (only the price we paid is used), Voltage
Park, Crusoe. Oracle is excluded from live collection.

## Outputs

- `paper/tables/`: P1 summary and discount tables (paid-price and median-price specs), M4
  medians, P2 observed ratios and implied decay, P3 scenarios, value-vs-book and validation,
  M8 triangulation, attribution and blended-fleet tables. Every figure has a CSV of its numbers.
- `paper/figures/`: P1-a..d, P2-a..c, P3 tornado, T-1. One shared style (`gel.viz.style`), using
  a palette validated for colour-vision deficiency.
- `data/processed/`: calibration files consumed by P3 and P2 (`p3_calibration.json`,
  `p3_capex.json`, `p3_market.json`) and the M4 panel.

## Assumptions and decisions

- [docs/assumptions.md](docs/assumptions.md): every assumption with its value and source, by
  project.
- [docs/decisions.md](docs/decisions.md): every methodological choice with alternatives and reasons
  (Decisions 1-15).
- [docs/open_questions.md](docs/open_questions.md): what is unresolved.
- [docs/research_log.md](docs/research_log.md): what was done, when, and what was found.

## Main limitations

- One price snapshot (2026-11-10/11); provider coverage is thin for the A40 (one price) and the
  A100 (two neocloud prices).
- The frontier is the H200, a Hopper refresh; no Blackwell point and no FP4 measurement.
- Board power only, with PUE applied as an assumption.
- P2's term ratios mix expected decay with on-demand list premiums and term premiums;
  hyperscaler ratios cannot be explained by decay alone (P3 validation check 2).
- P3's maintenance input is weakly sourced (two vendor blogs), and its physical-failure hazard is a
  judgement on incident data.
- P1's implied life rests on the vintage-price assumption (today's age gradient across chips
  describes one chip's path).
- Accounting lives are the handoff's generic 4/5/5.5/6 years; firm-specific lives need Phase 7.

## Layout

```
config/       bench.yaml (benchmark), p3_model.yaml (retirement model), providers/skus (collector)
bench/        pod-side harness: Dockerfile, run_all.sh, sweep driver, stubs for dry runs
src/gel/      collect/, parse/, build/ (historical, spot_panel), bench/ (parse, metrics, report),
              models/ (term_structure, p2_term, retirement_model, monte_carlo, calibrations,
              validation, triangulate), viz/ (style, figures)
deploy/       collector deployment (systemd units, push.sh)
docs/         proposal, decisions, assumptions, data sources, results, runbook, logs
tests/        pytest suite (hand-computed cases for every formula)
```
