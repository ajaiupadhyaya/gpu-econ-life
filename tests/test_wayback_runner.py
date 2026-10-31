import csv

import polars as pl

from gel.parse.errors import LayoutError
from gel.parse.wayback import parse_all, snapshot_time
from gel.schema import Listing


def selection(tmp_path, stems):
    rows = []
    for i, stem in enumerate(stems):
        timestamp = f"2021{i + 1:02d}05000000"
        row = {
            "provider": "lambda",
            "url": "https://x.example/p",
            "month": f"2021-{i + 1:02d}",
            "timestamp": timestamp,
            "original": "https://x.example/p",
        }
        rows.append(row)
        if stem is not None:
            path = tmp_path / "data/raw/wayback/pages/lambda/x-example-p" / f"{timestamp}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(stem)
    return rows


def good(html, meta):
    if html == "bad":
        raise LayoutError("new layout")
    if html == "empty":
        return []
    return [
        Listing.from_instance_price(
            price=80.0,
            gpu_count=8,
            sku="X",
            chip="h100_sxm",
            provider="lambda",
            provider_type="neocloud",
            collector="wayback",
            gpu_memory_gb=None,
            interconnect=None,
            region="unspecified",
            contract_type="on_demand",
            term_months=None,
            vcpus=None,
            ram_gb=None,
            retrieved_at=meta["retrieved_at"],
            source_url=meta["source_url"],
            raw_file=meta["raw_file"],
        )
    ]


def test_snapshot_time_is_the_price_date():
    assert snapshot_time("20210105123045") == "2021-01-05T12:30:45Z"


def test_every_snapshot_gets_a_status_and_nothing_vanishes(tmp_path):
    rows = selection(tmp_path, ["ok", "empty", "bad", None])
    failed = parse_all(rows, tmp_path, {"lambda": good})
    with (tmp_path / "data/interim/wayback/report.csv").open() as f:
        report = list(csv.DictReader(f))
    assert [r["status"] for r in report] == ["ok", "empty", "failed", "missing"]
    assert "new layout" in report[2]["detail"]
    assert failed == 1


def test_listings_point_back_to_the_archive(tmp_path):
    parse_all(selection(tmp_path, ["ok"]), tmp_path, {"lambda": good})
    frame = pl.read_parquet(tmp_path / "data/interim/wayback/listings.parquet")
    assert frame["retrieved_at"][0] == "2021-01-05T00:00:00Z"
    assert frame["source_url"][0].startswith("https://web.archive.org/web/20210105000000id_/")
    assert frame["raw_file"][0].endswith("20210105000000.html")


def test_a_provider_without_a_parser_is_reported_not_skipped(tmp_path):
    parse_all(selection(tmp_path, ["ok"]), tmp_path, {})
    with (tmp_path / "data/interim/wayback/report.csv").open() as f:
        assert next(csv.DictReader(f))["status"] == "no_parser"
