import polars as pl
import pytest

from gel.build.historical import coverage_table, render_report, validation_sample
from gel.schema import Listing, to_frame


def listing(
    provider="lambda", chip="v100", date="2021-03-05T00:00:00Z", collector="wayback", price=8.0
):
    return Listing.from_instance_price(
        price=price,
        gpu_count=8,
        retrieved_at=date,
        provider=provider,
        provider_type="neocloud",
        collector=collector,
        sku="X",
        chip=chip,
        gpu_memory_gb=None,
        interconnect=None,
        region="unspecified",
        contract_type="on_demand",
        term_months=None,
        vcpus=None,
        ram_gb=None,
        source_url=f"https://web.archive.org/web/{date[:4]}0105000000id_/https://x.example/p",
        raw_file="r",
    )


def frame(rows):
    return to_frame(rows)


def test_coverage_table_counts_distinct_months_per_provider_and_chip():
    table = coverage_table(
        frame(
            [
                listing(date="2021-03-05T00:00:00Z"),
                listing(date="2021-03-09T00:00:00Z"),
                listing(date="2021-05-05T00:00:00Z"),
                listing(chip="a100_40gb", date="2022-01-05T00:00:00Z"),
            ]
        )
    )
    row = table.filter(pl.col("chip") == "v100").to_dicts()[0]
    assert row["first"] == "2021-03"
    assert row["last"] == "2021-05"
    assert row["months"] == 2
    assert row["rows"] == 3


def test_report_states_totals_and_links_the_heatmap():
    report = render_report(frame([listing(), listing(provider="aws", collector="aws_history")]))
    assert "2 rows" in report
    assert "figures/coverage_heatmap.png" in report
    assert "| aws |" in report


def many():
    rows = []
    for provider in ("lambda", "coreweave"):
        for year in (2021, 2022):
            for month in range(1, 11):
                rows.append(
                    listing(provider, date=f"{year}-{month:02d}-05T00:00:00Z", price=8.0 + month)
                )
    return frame(rows)


def test_sample_has_the_requested_size_and_touches_every_stratum():
    sample = validation_sample(many(), n=8, seed=7)
    assert sample.height == 8
    strata = sample.select("provider", pl.col("retrieved_at").str.slice(0, 4)).unique()
    assert strata.height == 4


def test_sample_is_reproducible_from_its_seed():
    assert validation_sample(many(), n=8, seed=7).equals(validation_sample(many(), n=8, seed=7))


def test_sample_only_draws_rows_parsed_from_archived_pages():
    rows = many().vstack(frame([listing(provider="aws", collector="aws_history")]))
    assert set(validation_sample(rows, n=8, seed=7)["provider"]) == {"lambda", "coreweave"}


def test_sample_links_a_page_a_person_can_open():
    url = validation_sample(many(), n=4, seed=7)["check_url"][0]
    assert "id_/" not in url
    assert url.startswith("https://web.archive.org/web/")


def test_sample_refuses_to_be_smaller_than_asked():
    with pytest.raises(ValueError):
        validation_sample(frame([listing()]), n=40, seed=7)
