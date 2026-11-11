# gpu-econ-life

How fast do AI accelerators lose value, and how does that compare with the 4-6 year useful lives
in hyperscaler accounts? This repository is the replication package for the working paper
**"Rental-Implied Depreciation of AI Accelerators: Why the Estimates Disagree"** (`paper/main.tex`).
It builds an open panel of posted GPU rental prices (NVIDIA V100 to B200, October 2017 to November
2026), estimates age-price profiles under four identification strategies, turns rents into asset
values, triangulates with a benchmark, a term-structure model and a retirement model, and restates
seven firms' earnings under rental-implied schedules.

**Paper:** SSRN preprint, abstract ID 7692700:
<https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7692700>.

**DOIs:**
- Code, results and paper (this repository, release v1.0.2):
  <https://doi.org/10.5281/zenodo.24146261> (all versions: <https://doi.org/10.5281/zenodo.24143073>).
- Public panel and redistributable raw data: <https://doi.org/10.5281/zenodo.24143180>
  (all versions: <https://doi.org/10.5281/zenodo.24143179>), built by `make deposit`.

The research design is in [docs/proposal.md](docs/proposal.md); the plan to finish and publish is
[docs/finish_plan.md](docs/finish_plan.md). Project rules are in [CLAUDE.md](CLAUDE.md).

## Status (2026-11-11)

| Step | State |
| --- | --- |
| Phases 0-2: collector (runs daily on a server), historical panel | Done |
| Extension M1-M9: benchmark (P1), term structure (P2), retirement model (P3), triangulation (M8) | Done |
| B1 Phase 3 reference tables (chips, EIA electricity, CPI-U) | Done (Decisions 19-21) |
| B2 Phase 4 panel and descriptives | Done (Decision 22); memo 01 awaits AJ |
| B3 Phase 5 hedonic age profiles, four strategies | Done (Decision 23); memo 02 awaits AJ |
| B4 Adversarial review and its checks | Done (Decision 24); review_01 has Claude's draft responses; AJ's responses pending |
| B5 Phase 6 asset values and economic life | Done (Decision 25) |
| B6 Phase 7 EDGAR XBRL facts, useful lives, earnings restatement | Done (Decision 26) |
| C1-C3 Paper scaffold, verified references (65), first-draft prose | Done; prose is a draft for AJ to rewrite (Decision 17) |
| C4 Faculty review | AJ |
| C5 Two-page summary | Done (`paper/summary.tex`) |
| D1 Pre-public audit | Done ([docs/release_audit.md](docs/release_audit.md)); six items for AJ |
| D2 Replication package | Done: `make all`, raw-data manifest with checksums, public dataset builder, licence drafts |
| D3-D7 Public repo, Zenodo DOI, SSRN/arXiv, site, journal | AJ's accounts and approvals |

## Reproduce

```bash
uv sync
make test        # full test suite
make all         # interim -> data -> figures -> models -> paper (PDF), from data/raw
make review-checks   # the adversarial review's checks (slow: permutation test and Monte Carlo)
```

`make all` runs, in order: parse the archived history (`interim`), build the reference tables and
the panel (`data`), the benchmark, term-structure, retirement and triangulation outputs
(`figures`), the hedonic models, asset values and earnings restatement (`models`), then the
number macros and the PDFs (`paper`). Every number in the paper is a macro written by
`gel.viz.paper_numbers` from a generated table, so no result is typed by hand.

Inputs `make all` needs: `data/raw/` (archived source files, each with a `.json` sidecar of source
URL, UTC retrieval time and HTTP status) and `data/interim/live/` (the live collector's daily
parsed files; their raw copies are on the collection host). `make verify-raw` checks a local
`data/raw/` against `release/raw_manifest.csv` (SHA-256 per file). Files that may not be
redistributed list the collector command that re-fetches them.

Network steps are separate and never run by `make all`: `make collect` (live prices),
`make cpi-fetch`, `make edgar-fetch`. They need `GEL_CONTACT_EMAIL` in the git-ignored `.env`.

## Data and licences

| Path | What | Terms |
| --- | --- | --- |
| `data/raw/aws_offers/`, `live/` | AWS offer files; live Azure, AWS, Lambda, SkyPilot prices | derived aggregates only |
| `data/raw/skypilot_history/`, `wayback/` | SkyPilot catalog history; archived Lambda, CoreWeave, Paperspace pages | not redistributed; re-fetched |
| `data/raw/indices/epoch/` | Epoch AI hardware data | CC BY 4.0 |
| `data/raw/eia/`, `indices/bls_cpi/` | EIA Form 861M; BLS CPI-U | public domain |
| `data/raw/edgar/` | SEC EDGAR companyfacts, submissions and filings | public (cite the SEC) |
| `data/raw/bench/`, `manual/` | own benchmark runs; hand-recorded prices and transcriptions | own |

`make dataset` writes `release/dataset/`, the public panel of monthly median posted prices for
Zenodo (rows available only from the SkyPilot catalog are left out). Code is MIT-licensed
(`LICENSE`, a draft for AJ to confirm). Vast.ai, RunPod listings, Oracle, Voltage Park and Crusoe
are excluded by their terms.

## Outputs

- `paper/main.pdf` (built, not tracked) from `paper/main.tex` and `paper/sections/`;
  `paper/summary.pdf`, the two-page summary.
- `paper/tables/`: every table as CSV, plus the LaTeX tables the paper inputs (`p4_*` panel,
  `p5_*` hedonic and review checks, `p6_*` asset values and schedules, `p7_*` restatement,
  `p1`-`p3`, `m4`, `m8` extension).
- `paper/figures/`: every figure, one shared style (`gel.viz.style`).

## Documentation

- [docs/decisions.md](docs/decisions.md): every methodological choice with date, alternatives and
  reason (Decisions 1-26).
- [docs/assumptions.md](docs/assumptions.md): every assumption with its value and source.
- [docs/open_questions.md](docs/open_questions.md): what is unresolved, including owner decisions.
- [docs/review_01.md](docs/review_01.md), [docs/review_01_checks.md](docs/review_01_checks.md):
  the adversarial review and its checks.
- [docs/useful_lives.md](docs/useful_lives.md): every server useful-life policy with the exact
  filing quote and accession number.
- [docs/memo_01_descriptives.md](docs/memo_01_descriptives.md),
  [docs/memo_02_hedonic.md](docs/memo_02_hedonic.md): plain-English memos.
- [docs/venues.md](docs/venues.md): journal and preprint rules; [docs/release_audit.md](docs/release_audit.md).

## Main limitations

- Posted prices, overwhelmingly hyperscaler list prices; 96% of on-demand and reserved
  month-to-month transitions show no change. No marketplace or negotiated prices.
- Seven chip generations, so seven clusters: inference uses the restricted wild bootstrap and a
  design-based Monte Carlo; no strategy pins down the rate or shape of the age profile.
- Asset values exclude hosting, network and staff costs (no sourced figure), so values are upper
  bounds and economic life is set by the horizon or by obsolescence, not by rents reaching cost.
- The restatement's server and GPU shares of capital expenditure are assumptions shown as grids;
  capex excludes finance-lease additions.

## Layout

```
config/       assumptions (Phase 6), accounting (Phase 7), chips, providers, skus, bench, p3_model
src/gel/      collect/, parse/, build/, models/ (hedonic, review_checks, asset_value, P2, P3, M8),
              accounting/ (restate), release/ (manifest, dataset), viz/ (figures, paper_numbers)
paper/        main.tex, sections/, numbers.tex (generated), references.bib, tables/, figures/
release/      raw_manifest.csv, dataset/ (Zenodo)
deploy/       collector deployment (systemd units, push.sh)
docs/         proposal, plan, decisions, assumptions, sources, memos, reviews, logs
tests/        pytest suite
```
