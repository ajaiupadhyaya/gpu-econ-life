"""One-off snapshot of getdeploying's CC BY dataset files. Run by hand, never on a schedule.

The license covers these files but grants no automated access, and the site's terms bar
systematically copying content. Each weekly file holds 53 trailing weeks, so a manual download
every six months keeps the whole series.

    uv run python -m gel.collect.getdeploying
"""

from datetime import UTC, datetime
from pathlib import Path

import httpx

from gel.collect.http import user_agent, write_raw

ROOT = Path(__file__).resolve().parents[3]
FILES = {
    "weekly.csv": "https://getdeploying.com/dataset/gpu-prices/weekly.csv",
    "gpu-models.csv": "https://getdeploying.com/dataset/gpu-models/gpu-models.csv",
}


def main() -> None:
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    with httpx.Client(headers={"User-Agent": user_agent()}, timeout=60) as client:
        for name, url in FILES.items():
            response = client.get(url)
            response.raise_for_status()
            path = ROOT / "data/raw/indices/getdeploying" / day / name
            write_raw(path, response.content, url=url, status=response.status_code)
            print(path.relative_to(ROOT), len(response.content))


if __name__ == "__main__":
    main()
