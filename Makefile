.PHONY: install test test-fast lint coverage-preview collect health bench-dryrun bench-parse data models paper all

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

bench-parse:
	uv run python -m gel.bench.parse --root data/raw/bench --out data/interim/bench/bench_windows.parquet

data:
	@echo "placeholder: built in Phases 2 to 4"

models:
	@echo "placeholder: built in Phases 5 to 7"

paper:
	@echo "placeholder: built in Phase 8"

all: data models paper
