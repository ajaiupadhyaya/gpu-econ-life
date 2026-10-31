"""Lambda's public pricing page. Its terms permit rate-limited crawling."""

from gel.collect.context import Context
from gel.parse.lambda_pricing import parse_pricing
from gel.schema import Listing


def collect(ctx: Context) -> list[Listing]:
    cfg = ctx.config["lambda"]
    response = ctx.get(cfg["url"])
    raw = ctx.save(
        "lambda", "pricing.html", response.content, url=cfg["url"], status=response.status_code
    )
    return parse_pricing(
        response.text,
        plans=cfg["plans"],
        ignore=cfg["ignore"],
        retrieved_at=ctx.retrieved_at,
        source_url=cfg["url"],
        raw_file=ctx.relative(raw),
    )
