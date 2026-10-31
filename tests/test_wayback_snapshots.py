import csv

import httpx
import pytest

from gel.collect.http import Throttle
from gel.collect.wayback_snapshots import (
    SELECTION_FIELDS,
    archive_url,
    download,
    pages_with_history,
    select_snapshots,
    write_selection,
)

HEADER = ["timestamp", "original", "statuscode", "digest", "length", "mimetype"]


def capture(ts, status="200", url="https://x.example/p", mime="text/html"):
    return [ts, url, status, "D", "10", mime]


def cdx(*rows):
    return [HEADER, *rows]


def page(provider="lambda", url="https://x.example/p"):
    return {"provider": provider, "url": url}


def test_keeps_the_first_good_capture_of_each_month():
    rows = select_snapshots(
        page(),
        cdx(
            capture("20210102000000", status="301"),
            capture("20210105000000"),
            capture("20210120000000"),
            capture("20210203000000"),
        ),
    )
    assert [r["timestamp"] for r in rows] == ["20210105000000", "20210203000000"]


def test_order_of_the_index_does_not_change_the_choice():
    rows = select_snapshots(page(), cdx(capture("20210120000000"), capture("20210105000000")))
    assert [r["timestamp"] for r in rows] == ["20210105000000"]


def test_captures_before_the_panel_and_non_html_are_ignored():
    rows = select_snapshots(
        page(),
        cdx(
            capture("20191231000000"),
            capture("20200105000000", mime="warc/revisit", status="-"),
            capture("20200205000000", mime="application/pdf"),
        ),
    )
    assert rows == []


def test_selection_rows_carry_what_the_downloader_needs():
    row = select_snapshots(page("coreweave"), cdx(capture("20210105000000")))[0]
    assert set(SELECTION_FIELDS) <= set(row)
    assert row["provider"] == "coreweave"
    assert row["month"] == "2021-01"


def test_pages_with_history_excludes_skipped_pages_and_other_providers():
    config = {
        "providers": {
            "lambda": {
                "history": "wayback",
                "pages": [
                    {"url": "https://l.example/a"},
                    {"url": "https://l.example/b", "skip": True},
                ],
            },
            "vast": {"pages": [{"url": "https://v.example/a"}]},
        }
    }
    assert pages_with_history(config) == [{"provider": "lambda", "url": "https://l.example/a"}]


def test_archive_url_requests_the_original_bytes():
    assert (
        archive_url({"timestamp": "20210105000000", "original": "https://x.example/p"})
        == "https://web.archive.org/web/20210105000000id_/https://x.example/p"
    )


def test_selection_file_is_never_silently_replaced(tmp_path):
    path = tmp_path / "selection.csv"
    rows = select_snapshots(page(), cdx(capture("20210105000000")))
    write_selection(path, rows)
    write_selection(path, rows)
    other = select_snapshots(page(), cdx(capture("20210205000000")))
    with pytest.raises(FileExistsError):
        write_selection(path, other)
    assert next(csv.DictReader(path.open()))["timestamp"] == "20210105000000"


def client_for(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def rows_for(*months):
    return [
        {
            "provider": "lambda",
            "timestamp": f"2021{m}05000000",
            "original": "https://x.example/p",
            "month": f"2021-{m}",
        }
        for m in months
    ]


def test_download_stores_raw_bytes_with_sidecars_and_resumes(tmp_path):
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, content=b"<html>price</html>")

    throttle = Throttle(min_interval=0)
    first = download(rows_for("01", "02"), tmp_path, client_for(handler), throttle)
    assert first == {"fetched": 2, "skipped": 0, "failed": 0}
    files = sorted(p for p in tmp_path.rglob("*.html"))
    assert files[0].read_bytes() == b"<html>price</html>"
    assert files[0].with_name(files[0].name + ".json").exists()
    assert "/lambda/" in str(files[0])
    second = download(rows_for("01", "02", "03"), tmp_path, client_for(handler), throttle)
    assert second == {"fetched": 1, "skipped": 2, "failed": 0}
    assert len(seen) == 3


def test_one_missing_snapshot_does_not_stop_the_rest(tmp_path):
    def handler(request):
        return httpx.Response(404 if "202101" in str(request.url) else 200, content=b"x")

    result = download(rows_for("01", "02"), tmp_path, client_for(handler), Throttle(min_interval=0))
    assert result == {"fetched": 1, "skipped": 0, "failed": 1}


def test_stops_after_repeated_failures_rather_than_hammering_the_archive(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(403)

    months = [f"{m:02d}" for m in range(1, 13)]
    with pytest.raises(RuntimeError, match="consecutive"):
        download(
            rows_for(*months),
            tmp_path,
            client_for(handler),
            Throttle(min_interval=0),
            max_consecutive_failures=3,
        )
    assert len(calls) == 3
