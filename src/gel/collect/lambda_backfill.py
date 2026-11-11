"""Re-parse saved Lambda pricing pages for days whose parse failed (e.g. a new plan name).

Reads data/raw/live/lambda/<day>/*-pricing.html with its sidecar and writes
data/interim/live/lambda/<day>.parquet. Raw files are only read. Days that already have a
parquet are skipped unless --force.

Usage: uv run python -m gel.collect.lambda_backfill [--force]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from gel.parse.lambda_pricing import parse_pricing
from gel.schema import to_frame


def backfill(root: Path, force: bool = False) -> list[tuple[str, int]]:
    cfg = yaml.safe_load((root / "config/skus.yaml").read_text())["lambda"]
    done = []
    for day_dir in sorted((root / "data/raw/live/lambda").glob("20*")):
        out = root / "data/interim/live/lambda" / f"{day_dir.name}.parquet"
        pages = sorted(day_dir.glob("*-pricing.html"))
        if not pages or (out.exists() and not force):
            continue
        html = pages[-1]
        side = json.loads(html.with_name(html.name + ".json").read_text())
        rows = parse_pricing(
            html.read_text(),
            plans=cfg["plans"],
            ignore=cfg["ignore"],
            retrieved_at=side["retrieved_at"],
            source_url=side["source_url"],
            raw_file=str(html.relative_to(root)),
        )
        out.parent.mkdir(parents=True, exist_ok=True)
        to_frame(rows).write_parquet(out)
        done.append((day_dir.name, len(rows)))
    return done


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Re-parse saved Lambda pricing pages.")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    for day, n in backfill(Path("."), args.force):
        print(f"{day}: {n} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
