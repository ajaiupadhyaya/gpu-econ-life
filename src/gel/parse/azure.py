"""Parse Azure Retail Prices API items.

Reservation rows carry the whole-term price under the unit "1 Hour", so they are converted to an
hourly rate. A converted rate above on-demand means that assumption no longer holds.
"""

from gel.parse.errors import LayoutError
from gel.schema import Listing

RESERVATION_TERMS = {
    "1 Year": ("reserved_1y", 12),
    "3 Years": ("reserved_3y", 36),
    "5 Years": ("other", 60),
}
HOURS_PER_MONTH = 730
KNOWN_TYPES = {"Consumption", "DevTestConsumption", "Reservation"}


def _in_scope(item: dict, skus: dict) -> bool:
    return (
        item["armSkuName"] in skus
        and "Windows" not in item["productName"]
        and "Low Priority" not in item["skuName"]
        and item["type"] != "DevTestConsumption"
        and item["retailPrice"] > 0
    )


def _classify(item: dict) -> tuple[str, int | None, str, float]:
    """Return contract type, term, price kind and hourly instance price."""
    if item["type"] == "Reservation":
        term = item.get("reservationTerm")
        if term not in RESERVATION_TERMS:
            raise LayoutError(f"unknown reservation term: {term}")
        contract, months = RESERVATION_TERMS[term]
        return contract, months, "list", item["retailPrice"] / (months * HOURS_PER_MONTH)
    if "Spot" in item["skuName"]:
        return "spot", None, "spot", item["retailPrice"]
    return "on_demand", None, "list", item["retailPrice"]


def parse_items(
    items: list[dict], *, skus: dict, retrieved_at: str, source_url: str, raw_file: str
) -> list[Listing]:
    rows = []
    for item in items:
        if not _in_scope(item, skus):
            continue
        if item["type"] not in KNOWN_TYPES:
            raise LayoutError(f"unknown price type: {item['type']}")
        if item["currencyCode"] != "USD":
            raise LayoutError(f"unexpected currency: {item['currencyCode']}")
        if item["unitOfMeasure"] != "1 Hour":
            raise LayoutError(f"unexpected unit: {item['unitOfMeasure']}")
        spec = skus[item["armSkuName"]]
        contract, months, kind, hourly = _classify(item)
        rows.append(
            Listing.from_instance_price(
                price=hourly,
                gpu_count=spec["gpus"],
                retrieved_at=retrieved_at,
                provider="azure",
                provider_type="hyperscaler",
                collector="azure",
                sku=item["armSkuName"],
                chip=spec["chip"],
                gpu_memory_gb=spec.get("memory_gb"),
                interconnect=None,
                region=item["armRegionName"],
                contract_type=contract,
                term_months=months,
                vcpus=None,
                ram_gb=None,
                source_url=source_url,
                raw_file=raw_file,
                price_kind=kind,
                effective_from=item["effectiveStartDate"][:10],
            )
        )
    _check_term_totals(rows)
    return rows


def _check_term_totals(rows: list[Listing]) -> None:
    on_demand = {
        (r.sku, r.region): r.price_usd_per_hour_instance
        for r in rows
        if r.contract_type == "on_demand"
    }
    for row in rows:
        base = on_demand.get((row.sku, row.region))
        reserved = row.term_months is not None
        if reserved and base and row.price_usd_per_hour_instance > base * 1.01:
            raise LayoutError(
                f"{row.sku} {row.region}: reserved rate exceeds on-demand, so the term total "
                "assumption no longer holds"
            )
