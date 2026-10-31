import gzip

import httpx
import pytest

from gel.collect.aws_history import fetch_versions, version_timestamp, versions_since
from gel.collect.http import Throttle


def test_versions_since_filters_and_sorts():
    index = {"versions": {"20261029175634": {}, "20171101000000": {}, "20170210223144": {}}}
    assert versions_since(index, "201710") == ["20171101000000", "20261029175634"]


def test_version_timestamp_is_the_canonical_format():
    assert version_timestamp("20171101123045") == "2017-11-01T12:30:45Z"


def test_fetch_stores_gzipped_raw_and_skips_what_exists(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, content=b"csv")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    throttle = Throttle(min_interval=0)
    first = fetch_versions(["20171101000000"], "us-east-1", tmp_path, client, throttle)
    second = fetch_versions(["20171101000000"], "us-east-1", tmp_path, client, throttle)
    assert len(seen) == 1
    assert seen[0].endswith("/20171101000000/us-east-1/index.csv")
    assert first == second
    assert gzip.decompress(first[0].read_bytes()) == b"csv"
    assert first[0].with_name(first[0].name + ".json").exists()


def test_a_failed_version_raises_rather_than_leaving_a_silent_gap(tmp_path):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    with pytest.raises(httpx.HTTPStatusError):
        fetch_versions(["20171101000000"], "us-east-1", tmp_path, client, Throttle(min_interval=0))
