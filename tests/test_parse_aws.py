import gzip

import pytest

from gel.parse.aws import COLUMNS, parse_offer_csv
from gel.parse.errors import LayoutError

INSTANCES = {
    "p5.48xlarge": {"chip": "h100_sxm", "gpus": 8, "memory_gb": 80},
    "p4d.24xlarge": {"chip": "a100_40gb", "gpus": 8, "memory_gb": 40},
}
COMMON = dict(
    instances=INSTANCES, retrieved_at="2026-11-01T06:00:00Z", source_url="u", raw_file="r"
)


def good(**overrides):
    base = {c: "" for c in COLUMNS} | {
        "TermType": "OnDemand",
        "Unit": "Hrs",
        "PricePerUnit": "80.0",
        "Currency": "USD",
        "Product Family": "Compute Instance",
        "Region Code": "us-east-1",
        "Instance Type": "p5.48xlarge",
        "vCPU": "192",
        "Memory": "2048 GiB",
        "Network Performance": "3200 Gigabit",
        "Tenancy": "Shared",
        "Operating System": "Linux",
        "CapacityStatus": "Used",
        "Pre Installed S/W": "NA",
        "GPU": "8",
    }
    return base | overrides


def offer(tmp_path, rows, header=None, version="20261029175634"):
    header = header or COLUMNS
    lines = [
        '"FormatVersion","v1.0"',
        '"Disclaimer","x"',
        '"Publication Date","2026-10-29T17:56:34Z"',
        f'"Version","{version}"',
        '"OfferCode","AmazonEC2"',
        ",".join(f'"{h}"' for h in header),
    ]
    lines += [",".join(f'"{r[h]}"' for h in header) for r in rows]
    path = tmp_path / "offer.csv.gz"
    path.write_bytes(gzip.compress("\n".join(lines).encode()))
    return path


def test_on_demand_row(tmp_path):
    row = parse_offer_csv(offer(tmp_path, [good()]), **COMMON)[0]
    assert row.contract_type == "on_demand"
    assert row.price_usd_per_gpu_hour == 10.0
    assert (row.vcpus, row.ram_gb) == (192, 2048.0)
    assert row.interconnect == "3200 Gigabit"
    assert row.source_version == "20261029175634"
    assert row.region == "us-east-1"


def test_no_upfront_standard_reservations_are_kept(tmp_path):
    rows = [
        good(
            TermType="Reserved",
            LeaseContractLength="1yr",
            PurchaseOption="No Upfront",
            OfferingClass="standard",
            PricePerUnit="60.0",
        ),
        good(
            TermType="Reserved",
            LeaseContractLength="3yr",
            PurchaseOption="No Upfront",
            OfferingClass="standard",
            PricePerUnit="40.0",
        ),
    ]
    parsed = parse_offer_csv(offer(tmp_path, rows), **COMMON)
    assert {(r.contract_type, r.term_months) for r in parsed} == {
        ("reserved_1y", 12),
        ("reserved_3y", 36),
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"Operating System": "Windows"},
        {"Tenancy": "Dedicated"},
        {"CapacityStatus": "UnusedCapacityReservation"},
        {"Pre Installed S/W": "SQL Std"},
        {"Instance Type": "m5.large"},
        {"PricePerUnit": "0.0"},
        {"Unit": "Quantity"},
        {"TermType": "Reserved", "PurchaseOption": "All Upfront", "LeaseContractLength": "1yr"},
        {
            "TermType": "Reserved",
            "PurchaseOption": "No Upfront",
            "LeaseContractLength": "1yr",
            "OfferingClass": "convertible",
        },
    ],
)
def test_rows_out_of_scope_are_skipped(tmp_path, overrides):
    assert parse_offer_csv(offer(tmp_path, [good(**overrides)]), **COMMON) == []


def test_missing_column_fails_loudly(tmp_path):
    header = [c for c in COLUMNS if c != "PricePerUnit"]
    with pytest.raises(LayoutError, match="PricePerUnit"):
        parse_offer_csv(offer(tmp_path, [good()], header=header), **COMMON)


def test_gpu_count_disagreeing_with_config_fails_loudly(tmp_path):
    with pytest.raises(LayoutError, match="GPU count"):
        parse_offer_csv(offer(tmp_path, [good(GPU="4")]), **COMMON)
