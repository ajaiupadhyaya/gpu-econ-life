"""Parse an AWS EC2 regional offer file (CSV, gzipped as stored in data/raw)."""

import gzip
from pathlib import Path

import polars as pl

from gel.parse.errors import LayoutError
from gel.schema import Listing

METADATA_LINES = 5
COLUMNS = [
    "TermType",
    "Unit",
    "PricePerUnit",
    "Currency",
    "LeaseContractLength",
    "PurchaseOption",
    "OfferingClass",
    "Product Family",
    "Region Code",
    "Instance Type",
    "vCPU",
    "Memory",
    "Network Performance",
    "Tenancy",
    "Operating System",
    "CapacityStatus",
    "Pre Installed S/W",
    "GPU",
]
RESERVED = {"1yr": ("reserved_1y", 12), "3yr": ("reserved_3y", 36)}


def _read_preamble(path: Path) -> tuple[str, list[str]]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        lines = [next(f) for _ in range(METADATA_LINES + 1)]
    version = lines[3].split(",")[1].strip().strip('"')
    header = [h.strip().strip('"') for h in lines[METADATA_LINES].split('","')]
    return version, header


def _ram_gb(memory: str) -> float | None:
    number = memory.split()[0].replace(",", "") if memory else ""
    return float(number) if number else None


def parse_offer_csv(
    path: Path, *, instances: dict, retrieved_at: str, source_url: str, raw_file: str
) -> list[Listing]:
    version, header = _read_preamble(path)
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        raise LayoutError(f"offer file is missing columns: {missing}")
    frame = pl.read_csv(
        path, skip_rows=METADATA_LINES, columns=COLUMNS, infer_schema_length=0
    ).filter(
        pl.col("Instance Type").is_in(list(instances)),
        pl.col("Product Family").str.starts_with("Compute Instance"),
        pl.col("Tenancy") == "Shared",
        pl.col("Operating System") == "Linux",
        pl.col("CapacityStatus") == "Used",
        pl.col("Pre Installed S/W") == "NA",
        pl.col("Unit") == "Hrs",
        pl.col("Currency") == "USD",
    )
    rows = []
    for rec in frame.iter_rows(named=True):
        price = float(rec["PricePerUnit"])
        if price <= 0:
            continue
        if rec["TermType"] == "OnDemand":
            contract, months = "on_demand", None
        elif (
            rec["TermType"] == "Reserved"
            and rec["PurchaseOption"] == "No Upfront"
            and rec["OfferingClass"] == "standard"
            and rec["LeaseContractLength"] in RESERVED
        ):
            contract, months = RESERVED[rec["LeaseContractLength"]]
        else:
            continue
        spec = instances[rec["Instance Type"]]
        if rec["GPU"] and int(rec["GPU"]) != spec["gpus"]:
            raise LayoutError(
                f"{rec['Instance Type']}: GPU count {rec['GPU']} disagrees with config"
            )
        rows.append(
            Listing.from_instance_price(
                price=price,
                gpu_count=spec["gpus"],
                retrieved_at=retrieved_at,
                provider="aws",
                provider_type="hyperscaler",
                collector="aws",
                sku=rec["Instance Type"],
                chip=spec["chip"],
                gpu_memory_gb=spec.get("memory_gb"),
                interconnect=rec["Network Performance"] or None,
                region=rec["Region Code"],
                contract_type=contract,
                term_months=months,
                vcpus=int(rec["vCPU"]) if rec["vCPU"] else None,
                ram_gb=_ram_gb(rec["Memory"]),
                source_url=source_url,
                raw_file=raw_file,
                source_version=version,
            )
        )
    return rows
