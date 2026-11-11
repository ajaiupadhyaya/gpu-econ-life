.PHONY: panel p4-figures cpi-fetch cpi chips eia-states reference m8 figures p1-figures p2 p3-validate spot-panel install test test-fast lint coverage-preview collect health bench-dryrun bench-parse bench-report p3-calibrate p3-capex p3-market p3 data models paper all

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

# Phase 4 panel, cleaning report and descriptive figures (Decision 22).
panel: reference
	uv run python -m gel.build.panel

p4-figures: panel
	uv run python -m gel.viz.panel_figures

data: reference panel p4-figures

models:
	@echo "placeholder: built in Phases 5 to 7"

paper:
	@echo "placeholder: built in Phase 8"

all: data models paper

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
