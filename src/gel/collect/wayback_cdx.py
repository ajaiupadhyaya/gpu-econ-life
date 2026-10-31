"""Wayback CDX coverage preview for candidate pricing pages.

Index only: this reads capture metadata and downloads no page contents. Counts say a URL was
captured, not that the capture holds a readable price.
"""

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
import yaml

from gel.collect.http import Throttle, get_with_backoff, user_agent, write_raw

ROOT = Path(__file__).resolve().parents[3]
CDX_URL = "https://web.archive.org/cdx/search/cdx"
CDX_FIELDS = "timestamp,original,statuscode,digest,length,mimetype"
FROM_YEAR = 2019
TO_YEAR = 2026
GATE_YEARS = (2020, 2021, 2022)
GATE_MIN_SNAPSHOTS = 6


def build_params(url: str, *, from_year: int = FROM_YEAR, to_year: int = TO_YEAR) -> dict:
    return {
        "url": url,
        "output": "json",
        "fl": CDX_FIELDS,
        "from": str(from_year),
        "to": str(to_year),
    }


def parse_rows(payload: list) -> list[dict]:
    """The CDX JSON format is a header row followed by data rows; an empty index is []."""
    if len(payload) < 2:
        return []
    header, *rows = payload
    return [dict(zip(header, row, strict=True)) for row in rows]


def is_usable(row: dict) -> bool:
    """A 200 capture, or a revisit record (byte-identical to an earlier capture)."""
    return row["statuscode"] == "200" or row["mimetype"] == "warc/revisit"


def summarize_by_year(rows: list[dict]) -> dict[int, dict]:
    summary: dict[int, dict] = {}
    for row in rows:
        year = int(row["timestamp"][:4])
        s = summary.setdefault(year, {"captures": 0, "usable": 0, "_m": set(), "_v": set()})
        s["captures"] += 1
        if is_usable(row):
            s["usable"] += 1
            s["_m"].add(row["timestamp"][:6])
            s["_v"].add(row["digest"])
    return {
        year: {
            "captures": s["captures"],
            "usable": s["usable"],
            "months": len(s["_m"]),
            "versions": len(s["_v"]),
        }
        for year, s in sorted(summary.items())
    }


def provider_gate(pages: list[dict[int, dict]]) -> dict:
    """Phase 0 stop test: at least six usable snapshots a year in every year before 2023."""
    by_year = {
        year: sum(page.get(year, {}).get("usable", 0) for page in pages) for year in GATE_YEARS
    }
    return {"by_year": by_year, "passes": all(n >= GATE_MIN_SNAPSHOTS for n in by_year.values())}


def _cell(stats: dict | None) -> str:
    if not stats or not stats["usable"]:
        return "·"
    return f"{stats['usable']} / {stats['months']}m / {stats['versions']}v"


def render_preview(results: dict, generated_at: str) -> str:
    years = list(range(FROM_YEAR, TO_YEAR + 1))
    gates = {
        name: provider_gate([page["by_year"] for page in r["pages"]]) for name, r in results.items()
    }
    passing = sum(g["passes"] for g in gates.values())
    lines = [
        "# Wayback coverage preview",
        "",
        f"Generated {generated_at} by `make coverage-preview` from the CDX index. No page contents "
        "were downloaded.",
        "",
        f"**Stop test:** {passing} of {len(results)} providers have at least "
        f"{GATE_MIN_SNAPSHOTS} usable snapshots in each of {GATE_YEARS[0]}–{GATE_YEARS[-1]}.",
        "",
        "Do not read these counts as price coverage. A capture can be an empty JavaScript shell, "
        "so a page can pass this test and still hold no readable prices.",
        "",
        "## Provider gate",
        "",
        "Usable snapshots summed across each provider's candidate pages.",
        "",
        "| Provider | Type | " + " | ".join(str(y) for y in GATE_YEARS) + " | Passes |",
        "| --- | --- | " + " | ".join("---" for _ in GATE_YEARS) + " | --- |",
    ]
    for name, r in results.items():
        gate = gates[name]
        counts = " | ".join(str(gate["by_year"][y]) for y in GATE_YEARS)
        lines.append(
            f"| {name} | {r['provider_type']} | {counts} | {'yes' if gate['passes'] else 'no'} |"
        )
    lines += [
        "",
        "## Per page",
        "",
        "Each cell: usable snapshots / distinct months / distinct content versions (by digest). "
        "`·` means none. A version count of 1 across a year means the page bytes never changed.",
        "",
        "| Provider | URL | " + " | ".join(str(y) for y in years) + " |",
        "| --- | --- | " + " | ".join("---" for _ in years) + " |",
    ]
    for name, r in results.items():
        for page in r["pages"]:
            cells = " | ".join(_cell(page["by_year"].get(y)) for y in years)
            lines.append(f"| {name} | {page['url']} | {cells} |")
    return "\n".join(lines) + "\n"


def _slug(url: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", url.split("://", 1)[1].lower()).strip("-")


def fetch_index(client: httpx.Client, throttle: Throttle, url: str, stamp: str) -> dict:
    throttle.wait(urlparse(CDX_URL).netloc)
    response = get_with_backoff(client, CDX_URL, params=build_params(url))
    response.raise_for_status()
    raw_path = ROOT / "data/raw/wayback/cdx" / stamp / f"{_slug(url)}.json"
    write_raw(raw_path, response.content, url=str(response.url), status=response.status_code)
    return summarize_by_year(parse_rows(json.loads(response.content)))


def main() -> None:
    config = yaml.safe_load((ROOT / "config/providers.yaml").read_text())
    now = datetime.now(UTC)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    throttle = Throttle(min_interval=2.0)
    results: dict = {}
    failures = []
    with httpx.Client(headers={"User-Agent": user_agent()}, timeout=180) as client:
        for name, provider in config["providers"].items():
            pages = []
            for page in provider["pages"]:
                try:
                    by_year = fetch_index(client, throttle, page["url"], stamp)
                except (httpx.HTTPError, json.JSONDecodeError) as exc:
                    failures.append(f"{name} {page['url']}: {exc}")
                    continue
                print(f"{name:14} {sum(s['usable'] for s in by_year.values()):6} {page['url']}")
                pages.append({"url": page["url"], "by_year": by_year})
            results[name] = {"provider_type": provider["provider_type"], "pages": pages}
    preview = render_preview(results, now.strftime("%Y-%m-%dT%H:%M:%SZ"))
    if failures:
        preview += "\n## Queries that failed\n\n" + "\n".join(f"- {f}" for f in failures) + "\n"
    (ROOT / "docs/coverage_preview.md").write_text(preview)
    print(f"failed queries: {len(failures)}")


if __name__ == "__main__":
    main()
