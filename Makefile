.PHONY: install test lint coverage-preview collect health data models paper all

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

coverage-preview:
	uv run python -m gel.collect.wayback_cdx

collect:
	uv run python -m gel.collect.live --all

health:
	uv run python -m gel.collect.health

data:
	@echo "placeholder: built in Phases 2 to 4"

models:
	@echo "placeholder: built in Phases 5 to 7"

paper:
	@echo "placeholder: built in Phase 8"

all: data models paper
