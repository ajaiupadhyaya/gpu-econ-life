.PHONY: install test lint coverage-preview data models paper all

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

coverage-preview:
	uv run python -m gel.collect.wayback_cdx

data:
	@echo "placeholder: built in Phases 1 to 4"

models:
	@echo "placeholder: built in Phases 5 to 7"

paper:
	@echo "placeholder: built in Phase 8"

all: data models paper
