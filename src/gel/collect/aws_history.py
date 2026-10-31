"""Phase 2: AWS's own monthly price history, from its archived EC2 offer files.

    uv run python -m gel.collect.aws_history --download
    uv run python -m gel.collect.aws_history --parse

History uses us-east-1 only, from October 2017 when the P3 instances launched. Files are stored
gzipped and skipped when present, so the job can restart at any time.
"""

import argparse
import gzip
import logging
import sys
from pathlib import Path

import httpx
import yaml

from gel.collect.http import Throttle, get_with_backoff, user_agent, write_raw
from gel.parse.aws import parse_offer_csv
from gel.schema import to_frame

ROOT = Path(__file__).resolve().parents[3]
BASE = "https://pricing.us-east-1.amazonaws.com"
VERSION_INDEX = f"{BASE}/offers/v1.0/aws/AmazonEC2/index.json"
RAW_DIR = Path("data/raw/aws_offers")
INTERIM_DIR = Path("data/interim/aws_history")
REGION = "us-east-1"
FIRST_MONTH = "201710"
log = logging.getLogger("gel.collect.aws_history")


def versions_since(index: dict, first_month: str) -> list[str]:
    return sorted(v for v in index["versions"] if v[:6] >= first_month)


def version_timestamp(version: str) -> str:
    v = version
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}T{v[8:10]}:{v[10:12]}:{v[12:14]}Z"


def version_url(version: str, region: str) -> str:
    return f"{BASE}/offers/v1.0/aws/AmazonEC2/{version}/{region}/index.csv"


def fetch_versions(
    versions: list[str], region: str, root: Path, client: httpx.Client, throttle: Throttle
) -> list[Path]:
    paths = []
    for version in versions:
        path = root / RAW_DIR / f"{version}-{region}.csv.gz"
        paths.append(path)
        if path.exists():
            continue
        url = version_url(version, region)
        throttle.wait("pricing.us-east-1.amazonaws.com")
        response = get_with_backoff(client, url)
        response.raise_for_status()
        write_raw(path, gzip.compress(response.content), url=url, status=response.status_code)
        log.info("%s %.0f MB", version, len(response.content) / 1e6)
    return paths


def parse_versions(paths: list[Path], root: Path, instances: dict) -> int:
    total = 0
    for path in paths:
        version, region = path.name.removesuffix(".csv.gz").split("-", 1)
        rows = parse_offer_csv(
            path,
            instances=instances,
            retrieved_at=version_timestamp(version),
            source_url=version_url(version, region),
            raw_file=str(path.relative_to(root)),
            collector="aws_history",
        )
        target = root / INTERIM_DIR / f"{version}.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        to_frame(rows).write_parquet(target)
        total += len(rows)
        log.info("%s %d rows", version, len(rows))
    return total


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--parse", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    headers = {"User-Agent": user_agent()}
    with httpx.Client(headers=headers, timeout=600, follow_redirects=True) as client:
        index = get_with_backoff(client, VERSION_INDEX).json()
        versions = versions_since(index, FIRST_MONTH)
        log.info("%d versions from %s", len(versions), FIRST_MONTH)
        if args.download:
            fetch_versions(versions, REGION, root, client, Throttle())
    if args.parse:
        config = yaml.safe_load((root / "config/skus.yaml").read_text())
        paths = [root / RAW_DIR / f"{v}-{REGION}.csv.gz" for v in versions]
        log.info("parsed %d rows", parse_versions(paths, root, config["aws"]["instances"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
