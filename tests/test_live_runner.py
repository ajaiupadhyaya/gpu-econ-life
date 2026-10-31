import json
from datetime import UTC, datetime

import httpx
import polars as pl
import pytest

from gel.collect.context import Context
from gel.collect.http import Throttle
from gel.collect.live import load_env, main, run
from gel.schema import Listing

NOW = datetime(2026, 11, 1, 6, 0, 0, tzinfo=UTC)


def listing(provider="azure", collector="azure"):
    return Listing.from_instance_price(
        price=80.0,
        gpu_count=8,
        retrieved_at="2026-11-01T06:00:00Z",
        provider=provider,
        provider_type="hyperscaler",
        collector=collector,
        sku="X",
        chip="h100_sxm",
        gpu_memory_gb=None,
        interconnect=None,
        region="eastus",
        contract_type="on_demand",
        term_months=None,
        vcpus=None,
        ram_gb=None,
        source_url="u",
        raw_file="r",
    )


def make_context(tmp_path, handler=None):
    transport = httpx.MockTransport(handler or (lambda request: httpx.Response(200, text="ok")))
    return Context(
        client=httpx.Client(transport=transport),
        throttle=Throttle(min_interval=0),
        root=tmp_path,
        now=NOW,
        config={},
    )


def test_one_collector_failing_does_not_stop_the_others(tmp_path):
    def broken(ctx):
        raise RuntimeError("site changed")

    summary = run(
        ["broken", "good"],
        make_context(tmp_path),
        collectors={"broken": broken, "good": lambda ctx: [listing()]},
    )
    assert summary["collectors"]["broken"]["status"] == "failed"
    assert "site changed" in summary["collectors"]["broken"]["error"]
    assert summary["collectors"]["good"]["status"] == "ok"
    assert pl.read_parquet(tmp_path / "data/interim/live/good/2026-11-01.parquet").height == 1


def test_a_collector_returning_nothing_counts_as_failed(tmp_path):
    summary = run(["empty"], make_context(tmp_path), collectors={"empty": lambda ctx: []})
    assert summary["collectors"]["empty"]["status"] == "failed"


def test_summary_counts_rows_per_provider(tmp_path):
    rows = [listing("aws", "sky"), listing("aws", "sky"), listing("google_cloud", "sky")]
    run(["sky"], make_context(tmp_path), collectors={"sky": lambda ctx: rows})
    saved = json.loads((tmp_path / "data/interim/live/runs/2026-11-01.json").read_text())
    assert saved["collectors"]["sky"]["providers"] == {"aws": 2, "google_cloud": 1}


def test_rerunning_one_source_keeps_the_others_in_the_days_summary(tmp_path):
    collectors = {"a": lambda ctx: [listing()], "b": lambda ctx: [listing("aws", "b")]}
    run(["a", "b"], make_context(tmp_path), collectors=collectors)
    run(["b"], make_context(tmp_path), collectors=collectors)
    saved = json.loads((tmp_path / "data/interim/live/runs/2026-11-01.json").read_text())
    assert set(saved["collectors"]) == {"a", "b"}


def test_raw_files_are_stamped_so_a_same_day_rerun_cannot_collide(tmp_path):
    ctx = make_context(tmp_path)
    first = ctx.save("azure", "a.json", b"1", url="u", status=200)
    later = make_context(tmp_path)
    later.now = NOW.replace(minute=5)
    second = later.save("azure", "a.json", b"2", url="u", status=200)
    assert first != second
    assert first.parent == tmp_path / "data/raw/live/azure/2026-11-01"
    assert json.loads(first.with_name(first.name + ".json").read_text())["http_status"] == 200


def test_context_get_raises_on_http_errors(tmp_path):
    ctx = make_context(tmp_path, lambda request: httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        ctx.get("https://a.example/x")


def test_main_exits_nonzero_when_any_collector_fails(tmp_path):
    def broken(ctx):
        raise RuntimeError("nope")

    code = main(
        ["--all"], root=tmp_path, collectors={"a": broken, "b": lambda ctx: [listing()]}, config={}
    )
    assert code == 1


def test_main_exits_zero_when_everything_works(tmp_path):
    assert main(["--all"], root=tmp_path, collectors={"b": lambda ctx: [listing()]}, config={}) == 0


def test_main_requires_a_selection(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main([], root=tmp_path, collectors={}, config={})


def test_env_file_supplies_values_without_overriding_the_real_environment(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("# note\nGEL_CONTACT_EMAIL=a@example.org\nOTHER=x\n")
    monkeypatch.delenv("GEL_CONTACT_EMAIL", raising=False)
    monkeypatch.setenv("OTHER", "keep")
    load_env(tmp_path / ".env")
    import os

    assert os.environ["GEL_CONTACT_EMAIL"] == "a@example.org"
    assert os.environ["OTHER"] == "keep"
    monkeypatch.delenv("GEL_CONTACT_EMAIL")


def test_missing_env_file_is_fine(tmp_path):
    load_env(tmp_path / ".env")
