"""What every live collector shares: the HTTP client, the clock, and raw storage."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from gel.collect.http import Throttle, get_with_backoff, write_raw
from gel.schema import TIMESTAMP_FORMAT


@dataclass
class Context:
    client: httpx.Client
    throttle: Throttle
    root: Path
    now: datetime
    config: dict

    @property
    def day(self) -> str:
        return self.now.strftime("%Y-%m-%d")

    @property
    def retrieved_at(self) -> str:
        return self.now.strftime(TIMESTAMP_FORMAT)

    def get(self, url: str, params: dict | None = None) -> httpx.Response:
        self.throttle.wait(urlparse(url).netloc)
        response = get_with_backoff(self.client, url, params=params)
        response.raise_for_status()
        return response

    def save(self, source: str, name: str, content: bytes, *, url: str, status: int) -> Path:
        """Store a raw response under data/raw/live/<source>/<day>/, stamped to survive reruns."""
        stamp = self.now.strftime("%H%M%SZ")
        path = self.root / "data/raw/live" / source / self.day / f"{stamp}-{name}"
        write_raw(path, content, url=url, status=status)
        return path

    def relative(self, path: Path) -> str:
        return str(path.relative_to(self.root))
