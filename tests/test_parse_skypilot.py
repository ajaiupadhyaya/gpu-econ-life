import pytest

from gel.parse.errors import LayoutError
from gel.parse.skypilot import parse_aws_spot, parse_gcp

COMMON = dict(
    retrieved_at="2026-11-01T06:00:00Z", source_url="u", raw_file="r", source_version="abc"
)
AWS = {"p5.48xlarge": {"chip": "h100_sxm", "gpus": 8, "memory_gb": 80}}
AWS_HEADER = (
    "InstanceType,AcceleratorName,AcceleratorCount,Price,SpotPrice,Region,AvailabilityZone\n"
)
GCP = {"H100": {"chip": "h100_sxm", "memory_gb": 80}, "V100": {"chip": "v100"}}
GCP_HEADER = (
    "InstanceType,AcceleratorName,AcceleratorCount,Region,AvailabilityZone,Price,SpotPrice\n"
)


def test_aws_spot_uses_configured_gpu_count_not_the_catalog():
    text = AWS_HEADER + "p5.48xlarge,H100,12.0,68.8,24.0,us-east-1,use1-az1\n"
    row = parse_aws_spot(text, instances=AWS, **COMMON)[0]
    assert row.gpu_count == 8
    assert row.price_usd_per_gpu_hour == 3.0
    assert (row.provider, row.collector) == ("aws", "skypilot")
    assert (row.contract_type, row.price_kind) == ("spot", "spot")
    assert (row.region, row.zone) == ("us-east-1", "use1-az1")
    assert row.source_version == "abc"


def test_aws_rows_without_spot_or_outside_scope_are_skipped():
    text = (
        AWS_HEADER
        + "p5.48xlarge,H100,8.0,68.8,,us-east-1,use1-az1\nm5.large,,,0.1,0.03,us-east-1,a\n"
    )
    assert parse_aws_spot(text, instances=AWS, **COMMON) == []


def test_gcp_gives_on_demand_and_spot_rows_marked_accelerator_only():
    text = GCP_HEADER + ",H100,8,us-central1,us-central1-a,80.0,40.0\n"
    rows = {r.contract_type: r for r in parse_gcp(text, accelerators=GCP, **COMMON)}
    assert rows["on_demand"].price_usd_per_gpu_hour == 10.0
    assert rows["spot"].price_usd_per_gpu_hour == 5.0
    assert rows["spot"].price_basis == "accelerator_only"
    assert rows["on_demand"].provider == "google_cloud"
    assert rows["on_demand"].provider_type == "hyperscaler"
    assert rows["on_demand"].zone == "us-central1-a"


def test_gcp_host_vm_rows_are_skipped():
    text = GCP_HEADER + "n2-standard-8,,,us-central1,us-central1-a,0.4,0.1\n"
    assert parse_gcp(text, accelerators=GCP, **COMMON) == []


@pytest.mark.parametrize("parser", ["aws", "gcp"])
def test_missing_columns_fail_loudly(parser):
    text = "Only,These\n1,2\n"
    with pytest.raises(LayoutError):
        if parser == "aws":
            parse_aws_spot(text, instances=AWS, **COMMON)
        else:
            parse_gcp(text, accelerators=GCP, **COMMON)
