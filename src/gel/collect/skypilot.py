"""SkyPilot catalog: AWS spot and Google Cloud prices, pinned to one commit per run.

Only the AWS and GCP files are fetched. The repository also holds Vast.ai and RunPod files, which
are out of bounds under those providers' terms (docs/data_sources.md section 2).
"""

import gzip

from gel.collect.context import Context
from gel.parse.skypilot import parse_aws_spot, parse_gcp
from gel.schema import Listing


def _fetch(ctx: Context, sha: str, cloud: str) -> tuple[str, str, str]:
    cfg = ctx.config["skypilot"]
    path = f"catalogs/{cfg['catalog_version']}/{cloud}/vms.csv"
    url = f"https://raw.githubusercontent.com/{cfg['repo']}/{sha}/{path}"
    response = ctx.get(url)
    raw = ctx.save(
        "skypilot",
        f"{cloud}-vms.csv.gz",
        gzip.compress(response.content),
        url=url,
        status=response.status_code,
    )
    return response.text, url, ctx.relative(raw)


def collect(ctx: Context) -> list[Listing]:
    cfg = ctx.config["skypilot"]
    head = ctx.get(f"https://api.github.com/repos/{cfg['repo']}/commits/{cfg['branch']}")
    sha = head.json()["sha"]
    common = dict(retrieved_at=ctx.retrieved_at, source_version=sha)
    text, url, raw = _fetch(ctx, sha, "aws")
    rows = parse_aws_spot(
        text, instances=ctx.config["aws"]["instances"], source_url=url, raw_file=raw, **common
    )
    text, url, raw = _fetch(ctx, sha, "gcp")
    rows += parse_gcp(
        text, accelerators=cfg["gcp"]["accelerators"], source_url=url, raw_file=raw, **common
    )
    return rows
