import gzip
import json
from datetime import UTC, datetime

import httpx
import pytest

from gel.collect import aws_offers, azure_retail, lambda_page, skypilot
from gel.collect.context import Context
from gel.collect.http import Throttle
from gel.parse.errors import LayoutError
from tests.test_parse_aws import good, offer

NOW = datetime(2026, 11, 1, 6, 0, 0, tzinfo=UTC)
CONFIG = {
    "azure": {"skus": {"Standard_T": {"chip": "h100_sxm", "gpus": 8}}},
    "aws": {
        "regions": ["us-east-1"],
        "instances": {"p5.48xlarge": {"chip": "h100_sxm", "gpus": 8}},
    },
    "skypilot": {
        "catalog_version": "v8",
        "repo": "o/r",
        "branch": "master",
        "gcp": {"accelerators": {"H100": {"chip": "h100_sxm"}}},
    },
    "lambda": {"url": "https://l.example/pricing", "plans": {}, "ignore": []},
}


def context(tmp_path, handler):
    return Context(
        client=httpx.Client(transport=httpx.MockTransport(handler)),
        throttle=Throttle(min_interval=0),
        root=tmp_path,
        now=NOW,
        config=CONFIG,
    )


def azure_item(**overrides):
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


def test_azure_follows_pagination_and_saves_each_page(tmp_path):
    def handler(request):
        if "page2" in str(request.url):
            return httpx.Response(200, json={"Items": [azure_item(armRegionName="westus")]})
        return httpx.Response(
            200, json={"Items": [azure_item()], "NextPageLink": "https://prices.azure.com/page2"}
        )

    rows = azure_retail.collect(context(tmp_path, handler))
    assert {r.region for r in rows} == {"eastus", "westus"}
    raw = [
        p for p in (tmp_path / "data/raw/live/azure/2026-11-01").iterdir() if p.suffix == ".json"
    ]
    assert len([p for p in raw if not p.name.endswith(".json.json")]) == 2


def _aws_handler(tmp_path, counter):
    offer_bytes = gzip.decompress(offer(tmp_path, [good()]).read_bytes())

    def handler(request):
        if request.url.path.endswith("region_index.json"):
            body = {
                "regions": {
                    "us-east-1": {
                        "currentVersionUrl": "/offers/v1.0/aws/AmazonEC2/20261029175634/us-east-1/index.json"
                    }
                }
            }
            return httpx.Response(200, json=body)
        counter.append(str(request.url))
        return httpx.Response(200, content=offer_bytes)

    return handler


def test_aws_downloads_a_version_once_but_still_emits_rows_every_day(tmp_path):
    downloads = []
    handler = _aws_handler(tmp_path, downloads)
    first = aws_offers.collect(context(tmp_path, handler))
    next_day = context(tmp_path, handler)
    next_day.now = NOW.replace(day=2)
    second = aws_offers.collect(next_day)
    assert len(downloads) == 1
    assert downloads[0].endswith("/20261029175634/us-east-1/index.csv")
    assert len(first) == len(second) == 1
    assert second[0].retrieved_at.startswith("2026-11-02")
    assert "2026-11-01" in second[0].raw_file


def test_skypilot_pins_prices_to_a_commit(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.host == "api.github.com":
            return httpx.Response(200, json={"sha": "abc123"})
        if "aws" in request.url.path:
            return httpx.Response(
                200,
                text="InstanceType,SpotPrice,Region,AvailabilityZone\np5.48xlarge,24.0,us-east-1,a\n",
            )
        return httpx.Response(
            200,
            text="InstanceType,AcceleratorName,AcceleratorCount,Region,AvailabilityZone,Price,SpotPrice\n"
            ",H100,8,us-central1,us-central1-a,80.0,40.0\n",
        )

    rows = skypilot.collect(context(tmp_path, handler))
    assert {r.provider for r in rows} == {"aws", "google_cloud"}
    assert {r.source_version for r in rows} == {"abc123"}
    assert any("/abc123/catalogs/v8/gcp/vms.csv" in url for url in seen)


def test_lambda_saves_the_page_before_parsing(tmp_path):
    def handler(request):
        return httpx.Response(200, text="<html>changed</html>")

    with pytest.raises(LayoutError):
        lambda_page.collect(context(tmp_path, handler))
    saved = list((tmp_path / "data/raw/live/lambda/2026-11-01").glob("*pricing.html"))
    assert len(saved) == 1
    sidecar = json.loads(saved[0].with_name(saved[0].name + ".json").read_text())
    assert sidecar["source_url"] == "https://l.example/pricing"
