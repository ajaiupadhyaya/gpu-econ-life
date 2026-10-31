"""Polite HTTP and append-only raw storage, shared by every collector (CLAUDE.md rules 2 and 5)."""

import json
import os
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx

RETRY_STATUSES = {429} | set(range(500, 600))
MIN_INTERVAL_SECONDS = 1.0
# A stalled transfer fails after a minute with no bytes, rather than hanging a job for hours.
TIMEOUT = httpx.Timeout(connect=30, read=60, write=30, pool=30)


def user_agent() -> str:
    """Project User-Agent. The contact email comes from the environment, never from the repo."""
    base = "gpu-econ-life/0.1 (academic research)"
    email = os.environ.get("GEL_CONTACT_EMAIL", "").strip()
    return f"{base} contact: {email}" if email else base


class Throttle:
    """Keep at least `min_interval` seconds between requests to the same host."""

    def __init__(
        self,
        min_interval: float = MIN_INTERVAL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.min_interval = min_interval
        self.clock = clock
        self.sleep = sleep
        self.last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        if host in self.last:
            remaining = self.last[host] + self.min_interval - self.clock()
            if remaining > 0:
                self.sleep(remaining)
        self.last[host] = self.clock()


def get_with_backoff(
    client: httpx.Client,
    url: str,
    *,
    params: dict | None = None,
    max_attempts: int = 5,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    """GET with exponential backoff on 429, 5xx and network errors.

    Returns the last response if retries run out, or raises the last network error.
    """
    for attempt in range(max_attempts):
        last_attempt = attempt == max_attempts - 1
        try:
            response = client.get(url, params=params)
        except httpx.TransportError:
            if last_attempt:
                raise
        else:
            if response.status_code not in RETRY_STATUSES or last_attempt:
                return response
        sleep(base_delay * 2**attempt)
    raise AssertionError("unreachable")


def write_raw(path: Path, content: bytes, *, url: str, status: int) -> None:
    """Write a raw file and its .json sidecar. Refuses to overwrite: data/raw/ is append-only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "xb") as f:
        f.write(content)
    sidecar = {
        "source_url": url,
        "retrieved_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "http_status": status,
    }
    path.with_name(path.name + ".json").write_text(json.dumps(sidecar, indent=2) + "\n")
