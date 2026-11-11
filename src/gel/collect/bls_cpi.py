"""Download BLS CPI-U flat files into data/raw/indices/bls_cpi/ (append-only, with sidecars).

Source: https://download.bls.gov/pub/time.series/cu/ (layout documented in cu.txt, checked
2026-11-11). The BLS Public Data API is not used: https://api.bls.gov/robots.txt is
"User-agent: * / Disallow: /". download.bls.gov serves no robots.txt (404), and BLS asks robots
to carry contact information, so the request uses the project User-Agent with the contact email
from .env (GEL_CONTACT_EMAIL). BLS material is public domain; cite the Bureau of Labor Statistics.

Files: cu.data.1.AllItems (all-items series, item codes AA0 and SA0), cu.series (series
metadata, used to confirm what each series id means) and cu.footnote (footnote codes).

Usage: uv run python -m gel.collect.bls_cpi
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from gel.collect.http import TIMEOUT, Throttle, get_with_backoff, user_agent, write_raw
from gel.collect.live import load_env

BASE = "https://download.bls.gov/pub/time.series/cu/"
FILES = ["cu.data.1.AllItems", "cu.series", "cu.footnote"]
RAW_DIR = Path("data/raw/indices/bls_cpi")


def fetch(root: Path = Path("."), files: list[str] | None = None) -> list[Path]:
    load_env(root / ".env")
    if not os.environ.get("GEL_CONTACT_EMAIL", "").strip():
        raise SystemExit("GEL_CONTACT_EMAIL is not set in .env; BLS asks robots for contact info")
    now = datetime.now(UTC)
    out_dir = root / RAW_DIR / now.strftime("%Y-%m-%d")
    stamp = now.strftime("%H%M%SZ")
    throttle = Throttle()
    written = []
    with httpx.Client(
        headers={"User-Agent": user_agent()}, timeout=TIMEOUT, follow_redirects=True
    ) as client:
        for name in files or FILES:
            url = BASE + name
            throttle.wait(urlparse(url).netloc)
            r = get_with_backoff(client, url)
            if r.status_code != 200:
                raise SystemExit(f"{url}: HTTP {r.status_code}")
            path = out_dir / f"{stamp}-{name}.txt"
            write_raw(path, r.content, url=url, status=r.status_code)
            written.append(path)
    return written


def main(argv: list[str] | None = None) -> int:
    names = (argv if argv is not None else sys.argv[1:]) or None
    for p in fetch(files=names):
        print(f"wrote {p} ({p.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
