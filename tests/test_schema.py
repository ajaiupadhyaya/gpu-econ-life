import polars as pl
import pytest

from gel.schema import CHIPS, CONTRACT_TYPES, Listing, to_frame


def row(**overrides):
    base = dict(
        retrieved_at="2026-11-01T06:00:00Z",
        provider="azure",
        provider_type="hyperscaler",
        collector="azure",
        sku="Standard_X",
        chip="h100_sxm",
        gpu_count=8,
        gpu_memory_gb=80,
        interconnect=None,
        region="eastus",
        contract_type="on_demand",
        term_months=None,
        price_usd_per_hour_instance=80.0,
        price_usd_per_gpu_hour=10.0,
        vcpus=96,
        ram_gb=1900.0,
        source_url="https://example.org/x",
        raw_file="data/raw/live/azure/x.json",
    )
    return base | overrides


def test_conventions_match_claude_md():
    assert CHIPS == (
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
    assert CONTRACT_TYPES == ("on_demand", "spot", "reserved_1y", "reserved_3y", "other")


def test_valid_listing_is_accepted():
    assert Listing(**row()).price_usd_per_gpu_hour == 10.0


@pytest.mark.parametrize(
    "overrides",
    [
        {"price_usd_per_hour_instance": 0.0, "price_usd_per_gpu_hour": 0.0},
        {"price_usd_per_hour_instance": -1.0, "price_usd_per_gpu_hour": -0.125},
        {"gpu_count": 0},
        {"chip": "rtx4090"},
        {"provider_type": "reseller"},
        {"contract_type": "weekly"},
        {"region": ""},
        {"retrieved_at": "2026-11-01 06:00"},
        {"price_kind": "guess"},
        {"price_basis": "guess"},
    ],
)
def test_invalid_listings_are_rejected(overrides):
    with pytest.raises(ValueError):
        Listing(**row(**overrides))


def test_per_gpu_price_must_equal_instance_price_over_gpu_count():
    with pytest.raises(ValueError, match="per-GPU"):
        Listing(**row(price_usd_per_gpu_hour=12.0))


@pytest.mark.parametrize(
    ("contract", "term", "ok"),
    [
        ("on_demand", None, True),
        ("on_demand", 12, False),
        ("spot", None, True),
        ("reserved_1y", 12, True),
        ("reserved_1y", 36, False),
        ("reserved_3y", 36, True),
        ("reserved_3y", None, False),
        ("other", 60, True),
        ("other", None, True),
    ],
)
def test_term_must_fit_the_contract(contract, term, ok):
    args = row(contract_type=contract, term_months=term)
    if ok:
        Listing(**args)
    else:
        with pytest.raises(ValueError, match="term"):
            Listing(**args)


def test_from_instance_price_divides_by_gpu_count():
    args = row()
    del args["price_usd_per_gpu_hour"], args["price_usd_per_hour_instance"]
    assert Listing.from_instance_price(price=80.0, **args).price_usd_per_gpu_hour == 10.0


def test_from_gpu_price_multiplies_by_gpu_count():
    args = row()
    del args["price_usd_per_gpu_hour"], args["price_usd_per_hour_instance"]
    assert Listing.from_gpu_price(price=10.0, **args).price_usd_per_hour_instance == 80.0


def test_to_frame_has_stable_types_even_when_optional_columns_are_empty():
    frame = to_frame([Listing(**row())])
    assert frame.schema["term_months"] == pl.Int64
    assert frame.schema["available"] == pl.Boolean
    assert frame.schema["gpu_count"] == pl.Int64
    assert frame.height == 1
    assert to_frame([]).columns == frame.columns
