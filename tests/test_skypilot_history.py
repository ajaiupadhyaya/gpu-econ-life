import gzip

import httpx
import pytest

from gel.collect.http import Throttle
from gel.collect.skypilot_history import (
    CATALOGS,
    choose_commit,
    fetch_selection,
    lookup_from_history,
    month_windows,
    parse_log,
    parse_stored,
    select_commits,
)
from gel.parse.skypilot import parse_azure, parse_lambda

COMMON = dict(
    retrieved_at="2024-01-05T00:00:00Z", source_url="u", raw_file="r", source_version="abc"
)


def test_no_blocked_provider_is_ever_fetched():
    assert set(CATALOGS) == {"aws", "azure", "gcp", "lambda"}
    for paths in CATALOGS.values():
        for path in paths:
            assert "vast" not in path and "runpod" not in path and "oci" not in path


def test_month_windows_look_at_the_start_of_the_month_then_the_whole_month():
    assert month_windows("2024-02") == [
        ("2024-02-01T00:00:00Z", "2024-02-08T00:00:00Z"),
        ("2024-02-01T00:00:00Z", "2024-02-29T23:59:59Z"),
    ]


def test_choose_commit_prefers_newer_catalogs_and_earlier_windows():
    calls = []

    def lookup(path, since, until):
        calls.append((path, until[:10]))
        if path == "new" and until.startswith("2024-02-29"):
            return {"sha": "aaa", "date": "2024-02-20T00:00:00Z"}
        if path == "old":
            return {"sha": "bbb", "date": "2024-02-02T00:00:00Z"}
        return None

    chosen = choose_commit("2024-02", ["new", "old"], lookup)
    assert chosen == {"sha": "aaa", "date": "2024-02-20T00:00:00Z", "path": "new"}
    assert calls[0] == ("new", "2024-02-08")


def test_a_month_with_no_commit_is_a_gap_not_a_carried_forward_price():
    assert choose_commit("2024-02", ["new"], lambda *a: None) is None


def test_lookup_takes_the_earliest_commit_in_the_window():
    history = {
        "p": [("2024-02-20T00:00:00Z", "late"), ("2024-02-02T00:00:00Z", "early")],
    }
    lookup = lookup_from_history(history)
    assert lookup("p", "2024-02-01T00:00:00Z", "2024-02-08T00:00:00Z")["sha"] == "early"
    assert lookup("p", "2024-03-01T00:00:00Z", "2024-03-08T00:00:00Z") is None
    assert lookup("missing", "2024-02-01T00:00:00Z", "2024-02-08T00:00:00Z") is None


def test_parse_log_converts_commit_times_to_utc():
    output = "abc 2024-01-02T20:00:00-05:00\ndef 2024-02-02T00:00:00+00:00\n"
    assert parse_log(output) == [
        ("2024-01-03T01:00:00Z", "abc"),
        ("2024-02-02T00:00:00Z", "def"),
    ]
    assert parse_log("") == []


def test_select_commits_covers_every_cloud_and_month():
    def lookup(path, since, until):
        return {"sha": "s" + since[:7], "date": since}

    rows = select_commits(["2024-01", "2024-02"], lookup, catalogs={"aws": ["a"], "gcp": ["g"]})
    assert len(rows) == 4
    assert {r["cloud"] for r in rows} == {"aws", "gcp"}
    assert rows[0]["month"] == "2024-01"


def test_fetch_stores_gzipped_raw_with_sidecars_and_resumes(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, text="a,b\n1,2\n")

    rows = [
        {
            "cloud": "aws",
            "month": "2024-01",
            "sha": "abcdef1234",
            "path": "catalogs/v5/aws/vms.csv",
            "date": "2024-01-02T00:00:00Z",
        }
    ]
    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_selection(rows, tmp_path, client, Throttle(min_interval=0)) == 1
    assert fetch_selection(rows, tmp_path, client, Throttle(min_interval=0)) == 0
    assert len(seen) == 1
    assert "/abcdef1234/catalogs/v5/aws/vms.csv" in seen[0]
    stored = next(tmp_path.rglob("*.csv.gz"))
    assert gzip.decompress(stored.read_bytes()) == b"a,b\n1,2\n"
    assert stored.with_name(stored.name + ".json").exists()


def test_azure_uses_configured_gpu_counts_never_the_catalog():
    skus = {"Standard_T": {"chip": "h100_sxm", "gpus": 8, "memory_gb": 80}}
    text = (
        "InstanceType,AcceleratorName,AcceleratorCount,Price,SpotPrice,Region\n"
        "Standard_T,H100,12,80.0,16.0,eastus\n"
        "Standard_Other,H100,8,80.0,16.0,eastus\n"
    )
    rows = {r.contract_type: r for r in parse_azure(text, skus=skus, **COMMON)}
    assert rows["on_demand"].gpu_count == 8
    assert rows["on_demand"].price_usd_per_gpu_hour == 10.0
    assert rows["spot"].price_usd_per_gpu_hour == 2.0
    assert rows["on_demand"].provider == "azure"


def test_azure_duplicate_generation_rows_are_collapsed():
    skus = {"Standard_T": {"chip": "h100_sxm", "gpus": 8}}
    text = (
        "InstanceType,Price,SpotPrice,Region,Generation\n"
        "Standard_T,80.0,,eastus,V1\nStandard_T,80.0,,eastus,V2\n"
    )
    assert len(parse_azure(text, skus=skus, **COMMON)) == 1


def test_azure_conflicting_duplicates_fail_loudly():
    from gel.parse.errors import LayoutError

    skus = {"Standard_T": {"chip": "h100_sxm", "gpus": 8}}
    text = (
        "InstanceType,Price,SpotPrice,Region,Generation\n"
        "Standard_T,80.0,,eastus,V1\nStandard_T,90.0,,eastus,V2\n"
    )
    with pytest.raises(LayoutError, match="conflicting"):
        parse_azure(text, skus=skus, **COMMON)


def test_lambda_takes_gpu_count_from_the_instance_name():
    plans = {"h100_sxm5": {"chip": "h100_sxm", "memory_gb": 80}}
    text = (
        "InstanceType,AcceleratorName,AcceleratorCount,Price,Region\n"
        "gpu_8x_h100_sxm5,H100,8.0,31.92,us-east-1\n"
        "gpu_8x_h100_sxm5,H100,8.0,31.92,us-west-2\n"
        "gpu_1x_rtx6000,RTX6000,1.0,0.5,us-east-1\n"
        "cpu_4x_general,,,0.2,us-east-1\n"
    )
    rows = parse_lambda(text, instances=plans, **COMMON)
    assert len(rows) == 1
    assert rows[0].gpu_count == 8
    assert rows[0].price_usd_per_gpu_hour == pytest.approx(3.99)
    assert rows[0].region == "unspecified"


def test_lambda_regions_disagreeing_on_price_fail_loudly():
    from gel.parse.errors import LayoutError

    plans = {"h100_sxm5": {"chip": "h100_sxm"}}
    text = (
        "InstanceType,AcceleratorName,AcceleratorCount,Price,Region\n"
        "gpu_8x_h100_sxm5,H100,8.0,31.92,us-east-1\n"
        "gpu_8x_h100_sxm5,H100,8.0,40.0,us-west-2\n"
    )
    with pytest.raises(LayoutError, match="conflicting"):
        parse_lambda(text, instances=plans, **COMMON)


def test_parse_stored_routes_each_cloud_and_stamps_the_commit():
    config = {
        "aws": {"instances": {"p5.48xlarge": {"chip": "h100_sxm", "gpus": 8}}},
        "azure": {"skus": {}},
        "lambda": {"catalog_instances": {}},
        "skypilot": {"gcp": {"accelerators": {}}},
    }
    row = {"cloud": "aws", "sha": "abc", "date": "2024-01-02T03:04:05Z", "path": "p"}
    text = "InstanceType,SpotPrice,Region,AvailabilityZone\np5.48xlarge,24.0,us-east-1,a\n"
    parsed = parse_stored(text, row, config, source_url="u", raw_file="r")
    assert parsed[0].retrieved_at == "2024-01-02T03:04:05Z"
    assert parsed[0].source_version == "abc"
    assert parsed[0].collector == "skypilot_history"
