import pytest

from gel.parse.azure import parse_items
from gel.parse.errors import LayoutError

SKUS = {
    "Standard_T": {"chip": "h100_sxm", "gpus": 8, "memory_gb": 80, "source": "https://d.example"}
}
COMMON = dict(skus=SKUS, retrieved_at="2026-11-01T06:00:00Z", source_url="u", raw_file="r")


def item(**overrides):
    base = {
        "currencyCode": "USD",
        "retailPrice": 80.0,
        "unitOfMeasure": "1 Hour",
        "armRegionName": "eastus",
        "armSkuName": "Standard_T",
        "skuName": "T",
        "productName": "Virtual Machines T Series",
        "type": "Consumption",
        "effectiveStartDate": "2023-12-01T00:00:00Z",
    }
    return base | overrides


def test_on_demand_row():
    row = parse_items([item()], **COMMON)[0]
    assert row.contract_type == "on_demand"
    assert row.price_kind == "list"
    assert row.price_usd_per_gpu_hour == 10.0
    assert row.gpu_memory_gb == 80
    assert row.effective_from == "2023-12-01"


def test_spot_row_is_labelled_from_the_sku_name():
    row = parse_items([item(skuName="T Spot", retailPrice=16.0)], **COMMON)[0]
    assert (row.contract_type, row.price_kind) == ("spot", "spot")


def test_reservation_price_is_a_term_total_not_an_hourly_rate():
    rows = parse_items(
        [
            item(),
            item(type="Reservation", reservationTerm="1 Year", retailPrice=8760 * 40.0),
            item(type="Reservation", reservationTerm="3 Years", retailPrice=26280 * 32.0),
            item(type="Reservation", reservationTerm="5 Years", retailPrice=43800 * 24.0),
        ],
        **COMMON,
    )
    by_contract = {(r.contract_type, r.term_months): r for r in rows}
    assert by_contract[("reserved_1y", 12)].price_usd_per_hour_instance == pytest.approx(40.0)
    assert by_contract[("reserved_3y", 36)].price_usd_per_hour_instance == pytest.approx(32.0)
    assert by_contract[("other", 60)].price_usd_per_hour_instance == pytest.approx(24.0)


def test_reservation_dearer_than_on_demand_means_the_term_total_assumption_broke():
    items = [item(), item(type="Reservation", reservationTerm="1 Year", retailPrice=8760 * 200.0)]
    with pytest.raises(LayoutError, match="term total"):
        parse_items(items, **COMMON)


@pytest.mark.parametrize(
    "overrides",
    [
        {"productName": "Virtual Machines T Series Windows"},
        {"skuName": "T Low Priority"},
        {"type": "DevTestConsumption"},
        {"retailPrice": 0.0},
    ],
)
def test_rows_out_of_scope_are_skipped(overrides):
    assert parse_items([item(**overrides)], **COMMON) == []


def test_unknown_sku_is_skipped_because_counts_must_be_documented():
    assert parse_items([item(armSkuName="Standard_Other")], **COMMON) == []


@pytest.mark.parametrize(
    "overrides",
    [{"currencyCode": "EUR"}, {"type": "Mystery"}, {"unitOfMeasure": "1 GB/Month"}],
)
def test_unfamiliar_shapes_fail_loudly(overrides):
    with pytest.raises(LayoutError):
        parse_items([item(**overrides)], **COMMON)
