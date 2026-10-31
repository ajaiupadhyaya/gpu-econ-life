"""Parse every selected snapshot into the canonical schema.

    uv run python -m gel.parse.wayback

Every snapshot gets a status in data/interim/wayback/report.csv: ok, empty (a real page with no
in-scope prices), failed (a layout no parser knows), missing or no_parser. The exit code is 1 if any
snapshot failed, so an unknown layout cannot pass unnoticed.
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import yaml

from gel.collect.wayback_snapshots import SELECTION_PATH, archive_url, snapshot_path
from gel.parse import wayback_coreweave, wayback_lambda, wayback_paperspace
from gel.parse.errors import LayoutError
from gel.schema import Listing, to_frame

ROOT = Path(__file__).resolve().parents[3]
OUTPUT_DIR = Path("data/interim/wayback")
REPORT_FIELDS = ["provider", "url", "month", "timestamp", "status", "rows", "detail"]
PARSERS = {
    "lambda": wayback_lambda.parse,
    "coreweave": wayback_coreweave.parse,
    "paperspace": wayback_paperspace.parse,
}


def snapshot_time(timestamp: str) -> str:
    t = timestamp
    return f"{t[:4]}-{t[4:6]}-{t[6:8]}T{t[8:10]}:{t[10:12]}:{t[12:14]}Z"


def _parse_one(
    row: dict, root: Path, parsers: dict, config: dict
) -> tuple[list[Listing], str, str]:
    path = snapshot_path(root, row)
    if row["provider"] not in parsers:
        return [], "no_parser", ""
    if not path.exists():
        return [], "missing", ""
    meta = {
        "retrieved_at": snapshot_time(row["timestamp"]),
        "source_url": archive_url(row),
        "raw_file": str(path.relative_to(root)),
        "reserved_page": row["url"].rstrip("/").endswith("/reserved"),
        "lambda_config": config.get("lambda", {}),
    }
    try:
        listings = parsers[row["provider"]](path.read_bytes().decode("utf-8", "ignore"), meta)
    except (LayoutError, ValueError) as exc:
        return [], "failed", str(exc)
    return listings, "ok" if listings else "empty", ""


def parse_all(rows: list[dict], root: Path, parsers: dict = PARSERS) -> int:
    skus = root / "config/skus.yaml"
    config = yaml.safe_load(skus.read_text()) if skus.exists() else {}
    report = []
    listings: list[Listing] = []
    for row in rows:
        found, status, detail = _parse_one(row, root, parsers, config)
        listings += found
        report.append(
            {
                **{k: row[k] for k in ("provider", "url", "month", "timestamp")},
                "status": status,
                "rows": len(found),
                "detail": detail,
            }
        )
    output = root / OUTPUT_DIR
    output.mkdir(parents=True, exist_ok=True)
    to_frame(listings).write_parquet(output / "listings.parquet")
    with (output / "report.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REPORT_FIELDS)
        writer.writeheader()
        writer.writerows(report)
    return sum(1 for r in report if r["status"] == "failed")


def main(root: Path = ROOT) -> int:
    with (root / SELECTION_PATH).open() as f:
        rows = list(csv.DictReader(f))
    failed = parse_all(rows, root)
    with (root / OUTPUT_DIR / "report.csv").open() as f:
        print(dict(Counter((r["provider"], r["status"]) for r in csv.DictReader(f))))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
