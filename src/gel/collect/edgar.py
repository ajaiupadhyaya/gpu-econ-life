"""Download SEC EDGAR data for the Phase 7 restatement into data/raw/edgar/ (append-only, sidecars).

Endpoints, checked live on 2026-11-11 (UTC) against
https://www.sec.gov/search-filings/edgar-application-programming-interfaces (last updated
April 8, 2025) and https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data:

- Ticker -> CIK map: https://www.sec.gov/files/company_tickers.json ("data file for ticker, CIK,
  EDGAR conformed company name associations"). CIKs are resolved from this file, never typed in.
- Filing history: https://data.sec.gov/submissions/CIK##########.json (10-digit, zero-padded).
  Older filings beyond the most recent 1,000 sit in extra files listed under "filings.files";
  they are fetched too so the index reaches back to 2020.
- XBRL facts: https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json.
- Filing documents: https://www.sec.gov/Archives/edgar/data/{cik}/{accession without dashes}/
  {document}. robots.txt allows /Archives/edgar/data.

Fair access: the SEC caps automated clients at 10 requests per second and asks for a declared
User-Agent with contact details. This collector sends the project User-Agent with the contact
email from .env (GEL_CONTACT_EMAIL) and keeps at least 1 s between requests per host (CLAUDE.md
rule 5), with exponential backoff on 429 and 5xx. No authentication is needed.

Usage:
  uv run python -m gel.collect.edgar api        # tickers, submissions and companyfacts
  uv run python -m gel.collect.edgar filings    # 10-K/20-F (and selected 10-Q/6-K) documents
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from gel.collect.http import TIMEOUT, Throttle, get_with_backoff, user_agent, write_raw
from gel.collect.live import load_env

TICKERS = ["MSFT", "GOOGL", "AMZN", "META", "ORCL", "CRWV", "NBIS"]
TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SUBMISSIONS_PAGE_URL = "https://data.sec.gov/submissions/{name}"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{doc}"
INDEX_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/index.json"
RAW_DIR = Path("data/raw/edgar")
FILINGS_DIR = RAW_DIR / "filings"
ANNUAL_FORMS = {"10-K", "20-F"}
FILINGS_SINCE = "2020-01-01"


class EdgarClient:
    """One polite client: contact User-Agent, 1 s per host, backoff, every response archived."""

    def __init__(self, root: Path = Path(".")):
        load_env(root / ".env")
        if not os.environ.get("GEL_CONTACT_EMAIL", "").strip():
            raise SystemExit("GEL_CONTACT_EMAIL is not set in .env; SEC requires a declared UA")
        self.root = root
        self.throttle = Throttle()
        self.client = httpx.Client(
            headers={"User-Agent": user_agent(), "Accept-Encoding": "gzip, deflate"},
            timeout=TIMEOUT,
            follow_redirects=True,
        )

    def get(self, url: str) -> httpx.Response:
        self.throttle.wait(urlparse(url).netloc)
        return get_with_backoff(self.client, url)

    def close(self) -> None:
        self.client.close()


def resolve_ciks(tickers_json: dict, tickers: list[str]) -> dict[str, int]:
    """Ticker -> CIK from SEC's company_tickers.json ({"0": {"cik_str", "ticker", "title"}})."""
    by_ticker = {row["ticker"].upper(): int(row["cik_str"]) for row in tickers_json.values()}
    missing = [t for t in tickers if t.upper() not in by_ticker]
    if missing:
        raise SystemExit(f"tickers not in SEC company_tickers.json: {missing}")
    return {t: by_ticker[t.upper()] for t in tickers}


def _save(client: EdgarClient, url: str, path: Path) -> httpx.Response:
    r = client.get(url)
    if r.status_code != 200:
        raise SystemExit(f"{url}: HTTP {r.status_code}")
    write_raw(client.root / path, r.content, url=url, status=r.status_code)
    return r


def fetch_api(root: Path = Path("."), tickers: list[str] | None = None) -> list[Path]:
    """Tickers file, submissions (with extra pages) and companyfacts for each firm."""
    tickers = tickers or TICKERS
    now = datetime.now(UTC)
    out = RAW_DIR / now.strftime("%Y-%m-%d")
    stamp = now.strftime("%H%M%SZ")
    client = EdgarClient(root)
    written: list[Path] = []
    try:
        path = out / f"{stamp}-company_tickers.json"
        ciks = resolve_ciks(_save(client, TICKER_URL, path).json(), tickers)
        written.append(path)
        for t in tickers:
            cik = ciks[t]
            path = out / f"{stamp}-submissions-{t}-CIK{cik:010d}.json"
            sub = _save(client, SUBMISSIONS_URL.format(cik=cik), path).json()
            written.append(path)
            for page in sub.get("filings", {}).get("files", []):
                path = out / f"{stamp}-submissions-{t}-{page['name']}"
                _save(client, SUBMISSIONS_PAGE_URL.format(name=page["name"]), path)
                written.append(path)
            path = out / f"{stamp}-companyfacts-{t}-CIK{cik:010d}.json"
            _save(client, FACTS_URL.format(cik=cik), path)
            written.append(path)
    finally:
        client.close()
    return written


@dataclass(frozen=True)
class Filing:
    ticker: str
    cik: int
    accession: str
    form: str
    filing_date: str
    report_date: str
    primary_document: str

    @property
    def url(self) -> str:
        return ARCHIVE_URL.format(
            cik=self.cik, acc=self.accession.replace("-", ""), doc=self.primary_document
        )


def filing_rows(sub: dict) -> list[dict]:
    """Columnar 'recent' block (or an extra page, which has the same columns) -> rows."""
    block = sub["filings"]["recent"] if "filings" in sub else sub
    keys = ["accessionNumber", "form", "filingDate", "reportDate", "primaryDocument"]
    return [
        dict(zip(keys, vals, strict=True)) for vals in zip(*(block[k] for k in keys), strict=True)
    ]


def select_filings(
    ticker: str, cik: int, rows: list[dict], since: str = FILINGS_SINCE
) -> list[Filing]:
    """Every 10-K / 20-F (originals, not amendments) filed on or after `since`, plus each
    fiscal year's first 10-Q, where useful-life changes are usually first described."""
    rows = sorted(rows, key=lambda r: r["filingDate"])
    picked = [r for r in rows if r["form"] in ANNUAL_FORMS and r["filingDate"] >= since]
    annual_dates = [r["filingDate"] for r in rows if r["form"] in ANNUAL_FORMS]
    quarterlies = [r for r in rows if r["form"] == "10-Q" and r["filingDate"] >= since]
    for q in quarterlies:
        # First 10-Q after each 10-K: no other 10-Q between the last annual filing and it.
        prior_annual = max((d for d in annual_dates if d < q["filingDate"]), default=None)
        earlier_q = [
            x
            for x in quarterlies
            if x["filingDate"] < q["filingDate"]
            and (prior_annual is None or x["filingDate"] > prior_annual)
        ]
        if not earlier_q:
            picked.append(q)
    return [
        Filing(
            ticker,
            cik,
            r["accessionNumber"],
            r["form"],
            r["filingDate"],
            r["reportDate"],
            r["primaryDocument"],
        )
        for r in sorted(picked, key=lambda r: r["filingDate"])
    ]


def latest_api_files(root: Path, kind: str) -> dict[str, list[Path]]:
    """Ticker -> the most recent raw files of one kind ('submissions' or 'companyfacts')."""
    out: dict[str, list[Path]] = {}
    for p in sorted((root / RAW_DIR).glob(f"*/*-{kind}-*.json")):
        if p.name.endswith(".json.json"):
            continue
        ticker = p.name.split(f"-{kind}-")[1].split("-")[0]
        run = p.parent.name + p.name.split("-")[0]
        prev = out.get(ticker)
        prev_run = prev[0].parent.name + prev[0].name.split("-")[0] if prev else ""
        if run > prev_run:
            out[ticker] = [p]
        elif run == prev_run:
            out[ticker].append(p)
    return out


def filing_path(f: Filing, doc: str | None = None) -> Path:
    return FILINGS_DIR / f.ticker / f.accession / (doc or f.primary_document)


def fetch_filings(root: Path = Path("."), extra: list[tuple[str, str]] | None = None) -> list[Path]:
    """Primary documents of the selected filings. Already-archived documents are skipped (the
    raw store is append-only and a filing document never changes after dissemination).

    `extra` is a list of (ticker, accession) pairs fetched in full through the filing's
    index.json (every .htm document), for 6-K exhibits and other filings outside the rule above.
    """
    client = EdgarClient(root)
    written: list[Path] = []
    try:
        subs = latest_api_files(root, "submissions")
        index: dict[tuple[str, str], tuple[int, dict]] = {}
        for ticker, paths in subs.items():
            rows: list[dict] = []
            cik = 0
            for p in paths:
                data = json.loads(p.read_text())
                if "cik" in data:
                    cik = int(data["cik"])
                rows += filing_rows(data)
            for r in rows:
                index[(ticker, r["accessionNumber"])] = (cik, r)
            for f in select_filings(ticker, cik, rows):
                path = filing_path(f)
                if (root / path).exists() or not f.primary_document:
                    continue
                _save(client, f.url, path)
                written.append(path)
        for ticker, acc in extra or []:
            cik, r = index[(ticker, acc)]
            f = Filing(ticker, cik, acc, r["form"], r["filingDate"], r["reportDate"], "")
            idx_path = filing_path(f, "index.json")
            url = INDEX_URL.format(cik=cik, acc=acc.replace("-", ""))
            if not (root / idx_path).exists():
                _save(client, url, idx_path)
                written.append(idx_path)
            items = json.loads((root / idx_path).read_text())["directory"]["item"]
            for item in items:
                name = item["name"]
                if not name.lower().endswith((".htm", ".html")) or "index" in name.lower():
                    continue
                path = filing_path(f, name)
                if (root / path).exists():
                    continue
                _save(client, ARCHIVE_URL.format(cik=cik, acc=acc.replace("-", ""), doc=name), path)
                written.append(path)
    finally:
        client.close()
    return written


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    cmd = args[0] if args else "api"
    if cmd == "api":
        paths = fetch_api()
    elif cmd == "filings":
        extra = [tuple(a.split(":", 1)) for a in args[1:]]
        paths = fetch_filings(extra=extra)  # type: ignore[arg-type]
    else:
        raise SystemExit(
            "usage: python -m gel.collect.edgar [api | filings [TICKER:ACCESSION ...]]"
        )
    for p in paths:
        print(f"wrote {p} ({p.stat().st_size:,} bytes)")
    print(f"{len(paths)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
