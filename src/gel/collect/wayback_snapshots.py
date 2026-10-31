"""Phase 2: choose monthly Wayback snapshots from the CDX index and download them.

    uv run python -m gel.collect.wayback_snapshots --select
    uv run python -m gel.collect.wayback_snapshots --download

Each provider's pages come from config/providers.yaml. Downloads are resumable: a snapshot already
on disk is skipped, so the job can stop and restart at any time.
"""

import argparse
import csv
import io
import json
import logging
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

from gel.collect.http import TIMEOUT, Throttle, get_with_backoff, user_agent, write_raw
from gel.collect.wayback_cdx import parse_rows

ROOT = Path(__file__).resolve().parents[3]
SELECTION_PATH = Path("data/raw/wayback/selection.csv")
PAGES_DIR = Path("data/raw/wayback/pages")
SELECTION_FIELDS = ["provider", "url", "month", "timestamp", "original", "digest"]
FIRST_MONTH = "202001"
MIN_INTERVAL_SECONDS = 4.0
log = logging.getLogger("gel.collect.wayback_snapshots")


def pages_with_history(config: dict) -> list[dict]:
    return [
        {"provider": name, "url": page["url"]}
        for name, provider in config["providers"].items()
        if provider.get("history") == "wayback"
        for page in provider["pages"]
        if not page.get("skip")
    ]


def select_snapshots(page: dict, payload: list) -> list[dict]:
    """The first HTTP 200 HTML capture per month, for one URL."""
    months: dict[str, dict] = {}
    for row in sorted(parse_rows(payload), key=lambda r: r["timestamp"]):
        month = row["timestamp"][:6]
        usable = row["statuscode"] == "200" and row["mimetype"].startswith("text/html")
        if usable and month >= FIRST_MONTH and month not in months:
            months[month] = row
    return [
        {
            "provider": page["provider"],
            "url": page["url"],
            "month": f"{month[:4]}-{month[4:]}",
            "timestamp": row["timestamp"],
            "original": row["original"],
            "digest": row["digest"],
        }
        for month, row in sorted(months.items())
    ]


def write_selection(path: Path, rows: list[dict]) -> None:
    """data/raw/ is append-only, so a different selection must not replace this file."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=SELECTION_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    content = buffer.getvalue().encode()
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError(f"{path} exists with different content")
        return
    write_raw(path, content, url="derived from data/raw/wayback/cdx", status=200)


def archive_url(row: dict) -> str:
    """The id_ modifier returns the page as captured, without the archive's rewriting."""
    return f"https://web.archive.org/web/{row['timestamp']}id_/{row['original']}"


def snapshot_path(root: Path, row: dict) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "-", row["original"].split("://", 1)[1].lower()).strip("-")
    return root / PAGES_DIR / row["provider"] / slug / f"{row['timestamp']}.html"


def download(
    rows: list[dict],
    root: Path,
    client: httpx.Client,
    throttle: Throttle,
    *,
    max_consecutive_failures: int = 10,
) -> dict:
    result = {"fetched": 0, "skipped": 0, "failed": 0}
    consecutive = 0
    for row in rows:
        path = snapshot_path(root, row)
        if path.exists():
            result["skipped"] += 1
            continue
        url = archive_url(row)
        throttle.wait("web.archive.org")
        try:
            response = get_with_backoff(client, url)
        except httpx.HTTPError as exc:
            log.warning("error on %s: %s", url, exc)
            response = None
        if response is None or response.status_code != 200:
            status = None if response is None else response.status_code
            log.warning("no snapshot at %s (status %s)", url, status)
            result["failed"] += 1
            consecutive += 1
            if consecutive >= max_consecutive_failures:
                raise RuntimeError(f"{consecutive} consecutive failures, stopping politely")
            continue
        consecutive = 0
        write_raw(path, response.content, url=url, status=response.status_code)
        result["fetched"] += 1
        if result["fetched"] % 25 == 0:
            log.info("%s", result)
    return result


def _latest_cdx_dir(root: Path) -> Path:
    return sorted((root / "data/raw/wayback/cdx").iterdir())[-1]


def _select(root: Path) -> list[dict]:
    config = yaml.safe_load((root / "config/providers.yaml").read_text())
    cdx_dir = _latest_cdx_dir(root)
    rows: list[dict] = []
    for page in pages_with_history(config):
        slug = re.sub(r"[^a-z0-9]+", "-", page["url"].split("://", 1)[1].lower()).strip("-")
        rows += select_snapshots(page, json.loads((cdx_dir / f"{slug}.json").read_text()))
    write_selection(root / SELECTION_PATH, rows)
    return rows


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if args.select:
        rows = _select(root)
        log.info("selected %d snapshots across %d URLs", len(rows), len({r["url"] for r in rows}))
    if args.download:
        with (root / SELECTION_PATH).open() as f:
            rows = list(csv.DictReader(f))
        headers = {"User-Agent": user_agent()}
        with httpx.Client(headers=headers, timeout=TIMEOUT, follow_redirects=True) as client:
            started = time.monotonic()
            result = download(rows, root, client, Throttle(min_interval=MIN_INTERVAL_SECONDS))
            log.info("done in %.0fs: %s", time.monotonic() - started, result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
