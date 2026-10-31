"""Azure Retail Prices API: unauthenticated, documented, one query per configured SKU."""

from gel.collect.context import Context
from gel.parse.azure import parse_items
from gel.schema import Listing

API = "https://prices.azure.com/api/retail/prices"


def collect(ctx: Context) -> list[Listing]:
    skus = ctx.config["azure"]["skus"]
    rows: list[Listing] = []
    for sku in skus:
        url: str | None = API
        params = {"$filter": f"armSkuName eq '{sku}' and serviceName eq 'Virtual Machines'"}
        items: list[dict] = []
        first_raw = None
        page = 0
        while url:
            response = ctx.get(url, params)
            raw = ctx.save(
                "azure",
                f"{sku}-{page}.json",
                response.content,
                url=str(response.url),
                status=response.status_code,
            )
            first_raw = first_raw or raw
            payload = response.json()
            items.extend(payload["Items"])
            url, params = payload.get("NextPageLink"), None
            page += 1
        rows += parse_items(
            items,
            skus=skus,
            retrieved_at=ctx.retrieved_at,
            source_url=API,
            raw_file=ctx.relative(first_raw),
        )
    return rows
