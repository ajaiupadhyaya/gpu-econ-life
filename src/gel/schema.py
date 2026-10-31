"""Canonical listing schema: one row per posted price, in the conventions of CLAUDE.md."""

import math
from dataclasses import asdict, dataclass
from datetime import datetime

import polars as pl

CHIPS = (
    "v100",
    "a100_40gb",
    "a100_80gb",
    "h100_sxm",
    "h100_pcie",
    "h200",
    "b200",
    "mi300x",
    "l40s",
)
PROVIDER_TYPES = ("hyperscaler", "neocloud", "marketplace")
CONTRACT_TYPES = ("on_demand", "spot", "reserved_1y", "reserved_3y", "other")
PRICE_KINDS = ("list", "spot")
PRICE_BASES = ("instance", "accelerator_only")
FIXED_TERMS = {"on_demand": None, "spot": None, "reserved_1y": 12, "reserved_3y": 36}
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

SCHEMA = {
    "retrieved_at": pl.String,
    "provider": pl.String,
    "provider_type": pl.String,
    "sku": pl.String,
    "chip": pl.String,
    "gpu_count": pl.Int64,
    "gpu_memory_gb": pl.Float64,
    "interconnect": pl.String,
    "region": pl.String,
    "contract_type": pl.String,
    "term_months": pl.Int64,
    "price_usd_per_hour_instance": pl.Float64,
    "price_usd_per_gpu_hour": pl.Float64,
    "vcpus": pl.Int64,
    "ram_gb": pl.Float64,
    "source_url": pl.String,
    "raw_file": pl.String,
    "collector": pl.String,
    "price_kind": pl.String,
    "price_basis": pl.String,
    "zone": pl.String,
    "available": pl.Boolean,
    "source_version": pl.String,
    "effective_from": pl.String,
}


@dataclass(frozen=True, slots=True, kw_only=True)
class Listing:
    retrieved_at: str
    provider: str
    provider_type: str
    sku: str
    chip: str
    gpu_count: int
    gpu_memory_gb: float | None
    interconnect: str | None
    region: str
    contract_type: str
    term_months: int | None
    price_usd_per_hour_instance: float
    price_usd_per_gpu_hour: float
    vcpus: int | None
    ram_gb: float | None
    source_url: str
    raw_file: str
    collector: str
    price_kind: str = "list"
    price_basis: str = "instance"
    zone: str | None = None
    available: bool | None = None
    source_version: str | None = None
    effective_from: str | None = None

    def __post_init__(self) -> None:
        if self.chip not in CHIPS:
            raise ValueError(f"chip not allowed: {self.chip}")
        if self.provider_type not in PROVIDER_TYPES:
            raise ValueError(f"provider type not allowed: {self.provider_type}")
        if self.contract_type not in CONTRACT_TYPES:
            raise ValueError(f"contract type not allowed: {self.contract_type}")
        if self.price_kind not in PRICE_KINDS:
            raise ValueError(f"price kind not allowed: {self.price_kind}")
        if self.price_basis not in PRICE_BASES:
            raise ValueError(f"price basis not allowed: {self.price_basis}")
        if self.gpu_count < 1:
            raise ValueError(f"gpu_count must be at least 1: {self.gpu_count}")
        if not self.price_usd_per_hour_instance > 0 or not self.price_usd_per_gpu_hour > 0:
            raise ValueError(f"price must be positive: {self.price_usd_per_hour_instance}")
        if not self.region:
            raise ValueError("region must not be empty")
        datetime.strptime(self.retrieved_at, TIMESTAMP_FORMAT)
        implied = self.price_usd_per_hour_instance / self.gpu_count
        if not math.isclose(implied, self.price_usd_per_gpu_hour, rel_tol=1e-9):
            raise ValueError(f"per-GPU price {self.price_usd_per_gpu_hour} != {implied}")
        if (
            self.contract_type in FIXED_TERMS
            and self.term_months != FIXED_TERMS[self.contract_type]
        ):
            raise ValueError(f"term {self.term_months} does not fit {self.contract_type}")

    @classmethod
    def from_instance_price(cls, *, price: float, gpu_count: int, **fields) -> "Listing":
        return cls(
            price_usd_per_hour_instance=price,
            price_usd_per_gpu_hour=price / gpu_count,
            gpu_count=gpu_count,
            **fields,
        )

    @classmethod
    def from_gpu_price(cls, *, price: float, gpu_count: int, **fields) -> "Listing":
        return cls(
            price_usd_per_hour_instance=price * gpu_count,
            price_usd_per_gpu_hour=price,
            gpu_count=gpu_count,
            **fields,
        )


def to_frame(listings: list[Listing]) -> pl.DataFrame:
    return pl.DataFrame([asdict(row) for row in listings], schema=SCHEMA)
