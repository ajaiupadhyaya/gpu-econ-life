"""AWS EC2 offer files: on-demand and reserved list prices.

A regional CSV is about 150 MB and changes roughly monthly, so each version is downloaded once.
The daily job still confirms which version is current and emits that day's rows from it. AWS's
offer files exclude spot prices, which come from the SkyPilot collector.
"""

import gzip
import re
from pathlib import Path

from gel.collect.context import Context
from gel.parse.aws import parse_offer_csv
from gel.parse.errors import LayoutError
from gel.schema import Listing

BASE = "https://pricing.us-east-1.amazonaws.com"
REGION_INDEX = f"{BASE}/offers/v1.0/aws/AmazonEC2/current/region_index.json"
VERSION = re.compile(r"/AmazonEC2/(\d{14})/")


def _stored(ctx: Context, version: str, region: str) -> Path | None:
    matches = sorted((ctx.root / "data/raw/live/aws").glob(f"*/*-{version}-{region}.csv.gz"))
    return matches[0] if matches else None


def collect(ctx: Context) -> list[Listing]:
    cfg = ctx.config["aws"]
    index = ctx.get(REGION_INDEX)
    ctx.save(
        "aws", "region_index.json", index.content, url=str(index.url), status=index.status_code
    )
    regions = index.json()["regions"]
    rows: list[Listing] = []
    for region in cfg["regions"]:
        path = regions[region]["currentVersionUrl"].replace("index.json", "index.csv")
        match = VERSION.search(path)
        if not match:
            raise LayoutError(f"no version in offer path: {path}")
        version = match.group(1)
        url = BASE + path
        raw = _stored(ctx, version, region)
        if raw is None:
            response = ctx.get(url)
            raw = ctx.save(
                "aws",
                f"{version}-{region}.csv.gz",
                gzip.compress(response.content),
                url=url,
                status=response.status_code,
            )
        rows += parse_offer_csv(
            raw,
            instances=cfg["instances"],
            retrieved_at=ctx.retrieved_at,
            source_url=url,
            raw_file=ctx.relative(raw),
        )
    return rows
