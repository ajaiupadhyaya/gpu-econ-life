.PHONY: interim edgar-fetch edgar restate release-manifest verify-raw dataset paper-numbers asset-values review-checks hedonic p5-figures panel p4-figures cpi-fetch cpi chips eia-states reference m8 figures p1-figures p2 p3-validate spot-panel install test test-fast lint coverage-preview collect health bench-dryrun bench-parse bench-report p3-calibrate p3-capex p3-market p3 data models paper all

install:
	uv sync

test:
	uv run pytest

test-fast:
	uv run pytest -m "not slow"

lint:
	uv run ruff check .
	uv run ruff format --check .

coverage-preview:
	uv run python -m gel.collect.wayback_cdx

collect:
	uv run python -m gel.collect.live --all

health:
	uv run python -m gel.collect.health

# P1 benchmark (docs/bench_runbook.md). The dry run uses stub binaries and a temp directory.
bench-dryrun:
	bench/dryrun.sh

spot-panel: bench-parse
	uv run python -m gel.build.spot_panel --day 2026-11-10

bench-report: spot-panel p3-market
	uv run python -m gel.bench.report --frontier H200_SXM

p3-calibrate: bench-parse
	uv run python -m gel.models.p3_calibration

p3-capex:
	uv run python -m gel.models.p3_capex

p3-market: p3-calibrate p3-capex
	uv run python -m gel.models.p3_market_calibration

p3: p3-calibrate p3-capex p3-market
	uv run python -m gel.models.monte_carlo

bench-parse:
	uv run python -m gel.bench.parse --root data/raw/bench --out data/interim/bench/bench_windows.parquet

# Phase 3 reference tables (Decisions 18-21). cpi-fetch downloads a new BLS snapshot to
# data/raw (needs GEL_CONTACT_EMAIL in .env); cpi builds from the latest archived snapshot.
cpi-fetch:
	uv run python -m gel.collect.bls_cpi

cpi:
	uv run python -m gel.build.cpi

chips:
	uv run python -m gel.build.chips

eia-states:
	uv run python -m gel.build.eia_states

reference: chips eia-states cpi

# Parsed per-source files from data/raw (Phase 2 history). Live rows are parsed at collection time
# into data/interim/live/ and are an input here (their raw copies are on the collection host).
interim:
	uv run python -m gel.parse.wayback
	uv run python -m gel.collect.aws_history --parse
	uv run python -m gel.collect.skypilot_history --parse

# Phase 4 panel, cleaning report and descriptive figures (Decision 22).
panel: reference
	uv run python -m gel.build.panel

p4-figures: panel
	uv run python -m gel.viz.panel_figures

data: reference panel p4-figures

# Phase 5 hedonic models (Decision 23): about 20 minutes with 9,999 bootstrap draws.
hedonic: panel
	uv run python -W ignore -m gel.models.hedonic

p5-figures: hedonic
	uv run python -W ignore -m gel.viz.hedonic_figures

models: hedonic p5-figures asset-values restate

# Phase 7 accounting restatement (Decision 26). edgar-fetch needs the network and the contact
# email; edgar and restate run from archived raw files.
edgar-fetch:
	uv run python -m gel.collect.edgar api
	uv run python -m gel.collect.edgar filings NBIS:0001104659-26-064092 CRWV:0001193125-25-067651

edgar:
	uv run python -m gel.parse.edgar
	uv run python -m gel.parse.edgar verify docs/useful_lives.md

restate: edgar asset-values
	uv run python -m gel.accounting.restate

# Phase 6 asset values and economic life (Decision 25); seconds.
asset-values: hedonic
	uv run python -m gel.models.asset_value

# Checks requested by the Phase 5 review (docs/review_01.md points 1, 4, 7); about 15 minutes.
p5-review: panel
	uv run python -W ignore -m gel.models.review_checks all

# Checks requested by the adversarial review (docs/review_01.md, Decision 24). Slow: the
# permutation test and the coverage Monte Carlo take over an hour; `extra` alone takes ~2 minutes.
review-checks: hedonic
	uv run python -W ignore -m gel.models.review_checks all

# Paper (Stage C): numbers and small tables from result files, then the PDF.
paper-numbers: models
	uv run python -m gel.viz.paper_numbers

paper: paper-numbers
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error summary.tex

all: interim data figures models paper

# Release (finish plan D2/D4): raw-data manifest with checksums, verification, public dataset.
release-manifest:
	uv run python -m gel.release.manifest build

verify-raw:
	uv run python -m gel.release.manifest verify

dataset: panel
	uv run python -m gel.release.dataset

# Every table and figure from raw data (handoff M9): P1 parse -> M4 panel -> P1 tables/figures,
# P3 calibration + Monte Carlo + validation, P2 term structure.
p1-figures: bench-report p3-market
	uv run python -m gel.viz.p1_figures

p2: p3-market spot-panel
	uv run python -m gel.models.p2_term

p3-validate: p3
	uv run python -m gel.models.p3_validation

m8: p2 p3-validate
	uv run python -m gel.models.triangulate

figures: bench-parse p1-figures p3-validate p2 m8
