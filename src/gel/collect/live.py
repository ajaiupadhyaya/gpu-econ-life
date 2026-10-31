"""Daily live price collection. Run with: uv run python -m gel.collect.live --all"""

import argparse
import json
import logging
import os
import sys
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml

from gel.collect import aws_offers, azure_retail, lambda_page, skypilot
from gel.collect.context import Context
from gel.collect.http import Throttle, user_agent
from gel.schema import Listing, to_frame

ROOT = Path(__file__).resolve().parents[3]
COLLECTORS: dict[str, Callable[[Context], list[Listing]]] = {
    "azure": azure_retail.collect,
    "aws": aws_offers.collect,
    "lambda": lambda_page.collect,
    "skypilot": skypilot.collect,
}
log = logging.getLogger("gel.collect.live")


def load_env(path: Path) -> None:
    """Read KEY=VALUE lines from a git-ignored .env. Real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


def run(names: list[str], ctx: Context, collectors: dict = COLLECTORS) -> dict:
    """Run each collector in turn. A failure is recorded and never stops the next collector."""
    summary_path = ctx.root / "data/interim/live/runs" / f"{ctx.day}.json"
    summary: dict = {"day": ctx.day, "retrieved_at": ctx.retrieved_at, "collectors": {}}
    if summary_path.exists():
        summary["collectors"] = json.loads(summary_path.read_text())["collectors"]
    for name in names:
        try:
            rows = collectors[name](ctx)
            if not rows:
                raise RuntimeError("collector returned no rows")
            path = ctx.root / "data/interim/live" / name / f"{ctx.day}.parquet"
            path.parent.mkdir(parents=True, exist_ok=True)
            to_frame(rows).write_parquet(path)
        except Exception as exc:
            log.exception("%s failed", name)
            summary["collectors"][name] = {"status": "failed", "error": f"{exc!r}"}
            continue
        providers = Counter(row.provider for row in rows)
        log.info("%s ok: %d rows %s", name, len(rows), dict(providers))
        summary["collectors"][name] = {"status": "ok", "providers": dict(providers)}
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary


def main(
    argv: list[str] | None = None,
    *,
    root: Path = ROOT,
    collectors: dict = COLLECTORS,
    config: dict | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="run every collector")
    group.add_argument("--source", action="append", choices=sorted(collectors))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    load_env(root / ".env")
    if config is None:
        config = yaml.safe_load((root / "config/skus.yaml").read_text())
    names = list(collectors) if args.all else args.source
    headers = {"User-Agent": user_agent()}
    with httpx.Client(headers=headers, timeout=300, follow_redirects=True) as client:
        ctx = Context(
            client=client,
            throttle=Throttle(),
            root=root,
            now=datetime.now(UTC).replace(microsecond=0),
            config=config,
        )
        summary = run(names, ctx, collectors)
    failed = [n for n, r in summary["collectors"].items() if r["status"] != "ok"]
    if failed:
        log.error("failed collectors: %s", ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
