# GPU Economic Life: project memory

## Goal
Estimate the market-implied economic life of AI accelerators (V100, A100, H100, H200, B200)
from rental prices and compare it to hyperscaler book depreciation. Output: an SSRN working
paper and a public replication package. Author: AJ (solo). Full proposal: docs/proposal.md.

## Non-negotiable rules
1. Never fabricate data, prices, dates, specs or citations. If a value is unknown or a source
   is unreachable, leave it missing, log it in docs/open_questions.md, and tell me.
2. data/raw/ is append-only. Never edit or delete raw files. Every raw file gets a sidecar
   .json with source URL, UTC retrieval timestamp and HTTP status.
3. Every number in the paper must trace to a script in src/ and a file in data/.
   No hand-typed results. Notebooks are for exploration only.
4. Verify every API endpoint and page structure against live documentation before coding
   against it. Do not rely on memory of endpoints.
5. Respect robots.txt and terms of service. Send a User-Agent with my contact email
   (<YOUR EMAIL>). At least 1 second between requests per host; exponential backoff on
   429 and 5xx.
6. Log every methodological choice in docs/decisions.md (date, choice, alternatives,
   reason) and every assumption with its value and source in docs/assumptions.md.
7. Ask me before: adding a data source, changing the unit of observation, changing a
   logged estimation spec, or deleting anything.
8. Small commits with clear messages after each working step. Run tests and ruff first.

## Stack
- Python 3.12, uv for environment and dependencies
- httpx for requests; selectolax or BeautifulSoup for parsing; Playwright only when a
  page needs JavaScript
- polars and duckdb for data; parquet for interim and processed files
- pyfixest or linearmodels for fixed-effects regressions; statsmodels otherwise
- matplotlib with one shared style file
- pytest and ruff
- Makefile targets: data, models, paper, all

## Layout
gpu-econ-life/
  CLAUDE.md, README.md, Makefile, pyproject.toml
  config/        providers.yaml, chips.yaml, assumptions.yaml
  data/raw/      append-only: wayback/, live/, indices/, specs/, eia/, edgar/
  data/interim/  parsed per-source parquet
  data/processed/ analysis panels
  src/gel/       collect/, parse/, build/, models/, accounting/, viz/
  tests/
  notebooks/     exploration only
  paper/         main.tex, references.bib, figures/, tables/
  deploy/        VPS setup and scheduler files
  docs/          proposal.md, data_sources.md, decisions.md, assumptions.md,
                 open_questions.md, research_log.md

## Conventions
- Prices: USD per GPU-hour, nominal, plus a CPI-deflated real column.
- Dates: UTC, ISO 8601. Monthly data keyed to the first day of the month.
- Chip ids: v100, a100_40gb, a100_80gb, h100_sxm, h100_pcie, h200, b200, mi300x, l40s.
- Provider types: hyperscaler, neocloud, marketplace.
- Contract types: on_demand, spot, reserved_1y, reserved_3y, other.
