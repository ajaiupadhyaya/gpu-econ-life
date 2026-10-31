"""Parse SkyPilot catalog files for AWS spot and Google Cloud prices.

GPU counts for AWS come from config, not the catalog, whose counts are not reliable. Google rows
have no instance type: they price the accelerator alone, excluding the host VM.
"""

import csv
import io
import re

from gel.parse.errors import LayoutError
from gel.schema import Listing

AWS_COLUMNS = {"InstanceType", "SpotPrice", "Region", "AvailabilityZone"}
GCP_COLUMNS = {
    "InstanceType",
    "AcceleratorName",
    "AcceleratorCount",
    "Region",
    "Price",
    "SpotPrice",
}
GCP_COLUMNS |= {"AvailabilityZone"}
AZURE_COLUMNS = {"InstanceType", "Price", "SpotPrice", "Region"}
LAMBDA_COLUMNS = {"InstanceType", "Price"}
LAMBDA_NAME = re.compile(r"^gpu_(\d+)x_(.+)$")


def _records(text: str, required: set[str]) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    missing = required - set(reader.fieldnames or [])
    if missing:
        raise LayoutError(f"catalog is missing columns: {sorted(missing)}")
    return list(reader)


def _positive(value: str | None) -> float | None:
    price = float(value) if value else 0.0
    return price if price > 0 else None


def parse_aws_spot(
    text: str,
    *,
    instances: dict,
    retrieved_at: str,
    source_url: str,
    raw_file: str,
    source_version: str,
    collector: str = "skypilot",
) -> list[Listing]:
    rows = []
    for rec in _records(text, AWS_COLUMNS):
        spec = instances.get(rec["InstanceType"])
        price = _positive(rec["SpotPrice"])
        if spec is None or price is None:
            continue
        rows.append(
            Listing.from_instance_price(
                price=price,
                gpu_count=spec["gpus"],
                retrieved_at=retrieved_at,
                provider="aws",
                provider_type="hyperscaler",
                collector=collector,
                sku=rec["InstanceType"],
                chip=spec["chip"],
                gpu_memory_gb=spec.get("memory_gb"),
                interconnect=None,
                region=rec["Region"],
                zone=rec["AvailabilityZone"],
                contract_type="spot",
                term_months=None,
                vcpus=None,
                ram_gb=None,
                source_url=source_url,
                raw_file=raw_file,
                price_kind="spot",
                source_version=source_version,
            )
        )
    return rows


def parse_gcp(
    text: str,
    *,
    accelerators: dict,
    retrieved_at: str,
    source_url: str,
    raw_file: str,
    source_version: str,
    collector: str = "skypilot",
) -> list[Listing]:
    rows = []
    for rec in _records(text, GCP_COLUMNS):
        spec = accelerators.get(rec["AcceleratorName"])
        if spec is None or rec["InstanceType"] or not rec["AcceleratorCount"]:
            continue
        for column, contract, kind in (
            ("Price", "on_demand", "list"),
            ("SpotPrice", "spot", "spot"),
        ):
            price = _positive(rec[column])
            if price is None:
                continue
            rows.append(
                Listing.from_instance_price(
                    price=price,
                    gpu_count=int(float(rec["AcceleratorCount"])),
                    retrieved_at=retrieved_at,
                    provider="google_cloud",
                    provider_type="hyperscaler",
                    collector=collector,
                    sku=rec["AcceleratorName"],
                    chip=spec["chip"],
                    gpu_memory_gb=spec.get("memory_gb"),
                    interconnect=None,
                    region=rec["Region"],
                    zone=rec["AvailabilityZone"],
                    contract_type=contract,
                    term_months=None,
                    vcpus=None,
                    ram_gb=None,
                    source_url=source_url,
                    raw_file=raw_file,
                    price_kind=kind,
                    price_basis="accelerator_only",
                    source_version=source_version,
                )
            )
    return rows


def _unique(seen: dict, key: tuple, price: float) -> bool:
    """True the first time a key appears. The same key at another price cannot be resolved."""
    if key not in seen:
        seen[key] = price
        return True
    if seen[key] != price:
        raise LayoutError(f"conflicting prices for {key}: {seen[key]} and {price}")
    return False


def parse_azure(
    text: str,
    *,
    skus: dict,
    retrieved_at: str,
    source_url: str,
    raw_file: str,
    source_version: str,
    collector: str = "skypilot_history",
) -> list[Listing]:
    rows: list[Listing] = []
    seen: dict = {}
    for rec in _records(text, AZURE_COLUMNS):
        spec = skus.get(rec["InstanceType"])
        if spec is None or not rec["Region"]:
            continue
        for column, contract, kind in (
            ("Price", "on_demand", "list"),
            ("SpotPrice", "spot", "spot"),
        ):
            price = _positive(rec[column])
            key = (rec["InstanceType"], rec["Region"], contract)
            if price is None or not _unique(seen, key, price):
                continue
            rows.append(
                Listing.from_instance_price(
                    price=price,
                    gpu_count=spec["gpus"],
                    retrieved_at=retrieved_at,
                    provider="azure",
                    provider_type="hyperscaler",
                    collector=collector,
                    sku=rec["InstanceType"],
                    chip=spec["chip"],
                    gpu_memory_gb=spec.get("memory_gb"),
                    interconnect=None,
                    region=rec["Region"],
                    contract_type=contract,
                    term_months=None,
                    vcpus=None,
                    ram_gb=None,
                    source_url=source_url,
                    raw_file=raw_file,
                    price_kind=kind,
                    source_version=source_version,
                )
            )
    return rows


def parse_lambda(
    text: str,
    *,
    instances: dict,
    retrieved_at: str,
    source_url: str,
    raw_file: str,
    source_version: str,
    collector: str = "skypilot_history",
) -> list[Listing]:
    """Lambda prices one instance the same everywhere, so regional rows collapse to one."""
    rows: list[Listing] = []
    seen: dict = {}
    for rec in _records(text, LAMBDA_COLUMNS):
        match = LAMBDA_NAME.match(rec["InstanceType"])
        spec = instances.get(match.group(2)) if match else None
        price = _positive(rec["Price"])
        if spec is None or price is None or not _unique(seen, (rec["InstanceType"],), price):
            continue
        rows.append(
            Listing.from_instance_price(
                price=price,
                gpu_count=int(match.group(1)),
                retrieved_at=retrieved_at,
                provider="lambda",
                provider_type="neocloud",
                collector=collector,
                sku=rec["InstanceType"],
                chip=spec["chip"],
                gpu_memory_gb=spec.get("memory_gb"),
                interconnect=None,
                region="unspecified",
                contract_type="on_demand",
                term_months=None,
                vcpus=None,
                ram_gb=None,
                source_url=source_url,
                raw_file=raw_file,
                source_version=source_version,
            )
        )
    return rows
