"""Phase 2: dated prices from the git history of the SkyPilot catalog, one commit per month.

    uv run python -m gel.collect.skypilot_history --select --download --parse

A month without a commit stays a gap: no price is carried forward. Only the AWS, Azure, GCP and
Lambda files are read. The repository's Vast.ai, RunPod and OCI files are out of bounds under those
providers' terms. Commit dates come from a local blobless clone, because GitHub's path-filtered
commit API times out on a repository this size. The clone holds commits and trees, no file contents.
"""

import argparse
import calendar
import csv
import gzip
import io
import logging
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from gel.collect.http import TIMEOUT, Throttle, get_with_backoff, user_agent, write_raw
from gel.parse.skypilot import parse_aws_spot, parse_azure, parse_gcp, parse_lambda
from gel.schema import TIMESTAMP_FORMAT, Listing, to_frame

ROOT = Path(__file__).resolve().parents[3]
REPO = "skypilot-org/skypilot-catalog"
RAW_DIR = Path("data/raw/skypilot_history")
INTERIM_DIR = Path("data/interim/skypilot_history")
CLONE_DIR = Path("data/interim/skypilot_repo.git")
SELECTION_FIELDS = ["cloud", "month", "sha", "path", "date"]
FIRST_MONTH = "2022-07"
VERSIONS = ("v8", "v7", "v6", "v5", "v4")
CATALOGS = {
    cloud: [f"catalogs/{v}/{cloud}/vms.csv" for v in VERSIONS] + extra
    for cloud, extra in {
        "aws": ["catalogs/v3/aws.csv"],
        "azure": ["catalogs/v3/azure.csv", "catalogs/v1/azure.csv"],
        "gcp": ["catalogs/v3/gcp.csv", "catalogs/v1/gcp.csv"],
        "lambda": [],
    }.items()
}
log = logging.getLogger("gel.collect.skypilot_history")
Lookup = Callable[[str, str, str], dict | None]


def month_windows(month: str) -> list[tuple[str, str]]:
    year, number = int(month[:4]), int(month[5:7])
    last = calendar.monthrange(year, number)[1]
    start = f"{month}-01T00:00:00Z"
    return [(start, f"{month}-08T00:00:00Z"), (start, f"{month}-{last:02d}T23:59:59Z")]


def choose_commit(month: str, paths: list[str], lookup: Lookup) -> dict | None:
    """Prefer the newest catalog format with a commit in the month, nearest the month's start."""
    for path in paths:
        for since, until in month_windows(month):
            found = lookup(path, since, until)
            if found:
                return found | {"path": path}
    return None


def select_commits(months: list[str], lookup: Lookup, catalogs: dict = CATALOGS) -> list[dict]:
    rows = []
    for month in months:
        for cloud, paths in catalogs.items():
            chosen = choose_commit(month, paths, lookup)
            if chosen:
                rows.append({"cloud": cloud, "month": month} | chosen)
    return rows


def months_until(last: str) -> list[str]:
    months, year, number = [], int(FIRST_MONTH[:4]), int(FIRST_MONTH[5:])
    while f"{year}-{number:02d}" <= last:
        months.append(f"{year}-{number:02d}")
        year, number = (year + 1, 1) if number == 12 else (year, number + 1)
    return months


def lookup_from_history(history: dict[str, list[tuple[str, str]]]) -> Lookup:
    """Answer month queries from commit lists: the earliest commit inside the window."""

    def lookup(path: str, since: str, until: str) -> dict | None:
        window = sorted((d, sha) for d, sha in history.get(path, []) if since <= d <= until)
        return {"sha": window[0][1], "date": window[0][0]} if window else None

    return lookup


def parse_log(output: str) -> list[tuple[str, str]]:
    """Turn `git log --format="%H %cI"` output into (UTC timestamp, sha) pairs."""
    commits = []
    for line in output.splitlines():
        sha, stamp = line.split()
        moment = datetime.fromisoformat(stamp).astimezone(UTC)
        commits.append((moment.strftime(TIMESTAMP_FORMAT), sha))
    return commits


def read_history(repo: Path, paths: list[str]) -> dict[str, list[tuple[str, str]]]:
    command = ["git", "-C", str(repo), "log", "--format=%H %cI", "HEAD", "--"]
    return {
        path: parse_log(
            subprocess.run([*command, path], check=True, capture_output=True, text=True).stdout
        )
        for path in paths
    }


def ensure_clone(root: Path) -> Path:
    repo = root / CLONE_DIR
    if repo.exists():
        subprocess.run(["git", "-C", str(repo), "fetch", "-q", "origin"], check=True)
    else:
        repo.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/{REPO}.git"
        subprocess.run(
            ["git", "clone", "-q", "--bare", "--filter=blob:none", url, str(repo)], check=True
        )
    return repo


def stored_path(root: Path, row: dict) -> Path:
    return root / RAW_DIR / row["cloud"] / f"{row['month']}-{row['sha'][:10]}.csv.gz"


def raw_url(row: dict) -> str:
    return f"https://raw.githubusercontent.com/{REPO}/{row['sha']}/{row['path']}"


def fetch_selection(rows: list[dict], root: Path, client: httpx.Client, throttle: Throttle) -> int:
    fetched = 0
    for row in rows:
        path = stored_path(root, row)
        if path.exists():
            continue
        url = raw_url(row)
        throttle.wait("raw.githubusercontent.com")
        response = get_with_backoff(client, url)
        response.raise_for_status()
        write_raw(path, gzip.compress(response.content), url=url, status=response.status_code)
        fetched += 1
    return fetched


def parse_stored(
    text: str, row: dict, config: dict, *, source_url: str, raw_file: str
) -> list[Listing]:
    common = dict(
        retrieved_at=row["date"],
        source_url=source_url,
        raw_file=raw_file,
        source_version=row["sha"],
        collector="skypilot_history",
    )
    if row["cloud"] == "aws":
        return parse_aws_spot(text, instances=config["aws"]["instances"], **common)
    if row["cloud"] == "gcp":
        return parse_gcp(text, accelerators=config["skypilot"]["gcp"]["accelerators"], **common)
    if row["cloud"] == "azure":
        return parse_azure(text, skus=config["azure"]["skus"], **common)
    return parse_lambda(text, instances=config["lambda"]["catalog_instances"], **common)


def parse_all(rows: list[dict], root: Path, config: dict) -> int:
    total = 0
    for row in rows:
        path = stored_path(root, row)
        text = gzip.decompress(path.read_bytes()).decode()
        listings = parse_stored(
            text, row, config, source_url=raw_url(row), raw_file=str(path.relative_to(root))
        )
        target = root / INTERIM_DIR / row["cloud"] / f"{row['month']}.parquet"
        target.parent.mkdir(parents=True, exist_ok=True)
        to_frame(listings).write_parquet(target)
        total += len(listings)
        log.info("%s %s %d rows", row["cloud"], row["month"], len(listings))
    return total


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--parse", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    selection = root / RAW_DIR / "selection.csv"
    with httpx.Client(
        headers={"User-Agent": user_agent()}, timeout=TIMEOUT, follow_redirects=True
    ) as client:
        if args.select:
            last = datetime.now(UTC).strftime("%Y-%m")
            paths = [path for group in CATALOGS.values() for path in group]
            history = read_history(ensure_clone(root), paths)
            rows = select_commits(months_until(last), lookup_from_history(history))
            buffer = io.StringIO()
            writer = csv.DictWriter(buffer, fieldnames=SELECTION_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerows({k: r[k] for k in SELECTION_FIELDS} for r in rows)
            write_raw(selection, buffer.getvalue().encode(), url=f"github:{REPO}", status=200)
            log.info("selected %d commits", len(rows))
        with selection.open() as f:
            rows = list(csv.DictReader(f))
        if args.download:
            log.info("fetched %d files", fetch_selection(rows, root, client, Throttle()))
    if args.parse:
        config = yaml.safe_load((root / "config/skus.yaml").read_text())
        log.info("parsed %d rows", parse_all(rows, root, config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
