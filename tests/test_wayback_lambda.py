import pytest

from gel.parse.errors import LayoutError
from gel.parse.tables import read_tables
from gel.parse.wayback_lambda import parse

META = dict(retrieved_at="2022-06-13T01:48:40Z", source_url="u", raw_file="r")


def table(headers, rows, before=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<p>{before}</p><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def page(*tables):
    return "<html><body>" + "".join(tables) + "</body></html>"


B = ["GPUs", "VRAM per GPU", "vCPUs", "RAM", "Storage", "Price"]
ON_DEMAND = "On-demand pricing"


def test_read_tables_returns_headers_rows_and_the_text_before():
    html = page(table(["A", "B"], [["1", "2"]], before="Reserved pricing here"))
    found = read_tables(html)[0]
    assert found.headers == ["A", "B"]
    assert found.rows == [["1", "2"]]
    assert "Reserved pricing" in found.before


def test_on_demand_table_with_instance_prices():
    html = page(
        table(
            B,
            [["8x NVIDIA Tesla V100", "16 GB", "92", "448 GiB", "5.9 TiB", "$4.40 / hr"]],
            ON_DEMAND,
        )
    )
    row = parse(html, META)[0]
    assert (row.chip, row.gpu_count, row.contract_type) == ("v100", 8, "on_demand")
    assert row.price_usd_per_gpu_hour == pytest.approx(0.55)
    assert (row.vcpus, row.ram_gb, row.gpu_memory_gb) == (92, 448.0, 16)
    assert row.provider == "lambda" and row.collector == "wayback"


def test_a100_memory_decides_the_chip():
    rows = [
        ["1x NVIDIA A100", "40 GB", "30", "200 GiB", "512 GiB", "$1.10 / hr"],
        ["8x NVIDIA A100", "80 GB", "240", "1800 GiB", "20 TiB", "$12.00 / hr"],
    ]
    assert {r.chip for r in parse(page(table(B, rows, ON_DEMAND)), META)} == {
        "a100_40gb",
        "a100_80gb",
    }


def test_a_table_announced_as_reserved_keeps_its_stated_minimum_term():
    html = page(
        table(
            B,
            [["8x NVIDIA A100", "40 GB", "224", "800 GiB", "13.96 TiB", "$8.00 / hr"]],
            "Reserved pricing Reserved instances require a minimum 3-month commitment.",
        )
    )
    row = parse(html, META)[0]
    assert (row.contract_type, row.term_months) == ("other", 3)


def test_a_reserved_table_with_no_stated_term_claims_no_term():
    html = page(
        table(
            B,
            [["8x NVIDIA A100", "40 GB", "224", "800 GiB", "13.96 TiB", "$8.00 / hr"]],
            "Compare GPU costs Pricing",
        )
    )
    row = parse(html, {**META, "reserved_page": True})[0]
    assert (row.contract_type, row.term_months) == ("other", None)


def test_term_columns_become_one_row_per_term():
    headers = B[:5] + ["Network Bandwidth (Gbps)", "6 months", "1 year", "3 year"]
    rows = [
        [
            "8x NVIDIA A100",
            "40 GB",
            "128",
            "2048 GB",
            "27 TB",
            "1600",
            "$8.80/hour",
            "$8.36/hour",
            "$8.10/hour",
        ]
    ]
    parsed = {(r.contract_type, r.term_months): r for r in parse(page(table(headers, rows)), META)}
    assert set(parsed) == {("other", 6), ("reserved_1y", 12), ("reserved_3y", 36)}
    assert parsed[("reserved_1y", 12)].price_usd_per_gpu_hour == pytest.approx(1.045)


def test_cluster_table_quotes_per_gpu_with_a_stated_term():
    headers = [
        "",
        "Instance type",
        "GPU",
        "GPU Memory",
        "vCPUs",
        "Storage",
        "Network Bandwidth (Gbps)",
        "Per Hour Price",
        "Term",
        "# of GPUs",
    ]
    rows = [
        [
            "Reserved",
            "8x NVIDIA H100",
            "H100 SXM",
            "80 GB",
            "200",
            "20 TB",
            "3200",
            "$1.89/H100/hour",
            "3-years",
            "64 - 60,000",
        ],
        [
            "Sprint",
            "8x NVIDIA H100",
            "H100 SXM",
            "80 GB",
            "224",
            "27 TB",
            "3200",
            "$4.85/H100/hour",
            "3-months",
            "248",
        ],
    ]
    parsed = {r.term_months: r for r in parse(page(table(headers, rows)), META)}
    assert parsed[36].contract_type == "reserved_3y"
    assert parsed[36].price_usd_per_gpu_hour == 1.89
    assert parsed[3].contract_type == "other"
    assert parsed[3].chip == "h100_sxm"


def test_per_gpu_table_labels_contract_inside_the_first_cell():
    headers = ["GPUs", "VRAM/GPU", "vCPUs", "RAM", "STORAGE", "PRICE/GPU/HR*"]
    rows = [
        [
            "On-demand 8x NVIDIA H100 SXM",
            "80 GB",
            "208",
            "1800 GiB",
            "26 TiB SSD",
            "$2.99 / GPU / hr",
        ],
        ["Reserved 8x NVIDIA H100 SXM", "80 GB", "208", "1800 GiB", "22 TiB SSD", "CONTACT SALES"],
    ]
    parsed = parse(page(table(headers, rows)), META)
    assert len(parsed) == 1
    assert parsed[0].price_usd_per_gpu_hour == 2.99
    assert parsed[0].price_usd_per_hour_instance == pytest.approx(23.92)


def test_competitor_comparison_rows_are_never_recorded_as_lambda_prices():
    headers = [
        "",
        "GPU",
        "GPU Memory",
        "Network Bandwidth (Gbps)",
        "1-Year Price",
        "Savings on GPU",
    ]
    rows = [
        ["AWS p4d.24xlarge", "NVIDIA 8x A100", "40 GB", "400", "$19.22/hour", ""],
        ["Lambda Reserved Cloud Cluster", "NVIDIA 8x A100", "40 GB", "1600", "$8.36/hour", "57%"],
    ]
    assert parse(page(table(headers, rows)), META) == []


@pytest.mark.parametrize("label", ["NVIDIA RTX A6000", "NVIDIA Quadro RTX 6000", "NVIDIA A10"])
def test_out_of_scope_gpus_are_skipped(label):
    row = [f"1x {label}", "24 GB", "6", "46 GiB", "685 GiB", "$0.75 / hr"]
    assert parse(page(table(B, [row], ON_DEMAND)), META) == []


def test_coming_soon_prices_are_skipped_and_tags_ignored():
    rows = [
        ["1x NVIDIA H100 PCIe New", "80 GB", "26", "200 GiB", "1 TiB", "$1.99 / hr"],
        ["8x NVIDIA A100", "40 GB", "128", "2048 GB", "27 TB", "Coming Soon"],
    ]
    parsed = parse(page(table(B, rows, ON_DEMAND)), META)
    assert [r.chip for r in parsed] == ["h100_pcie"]


def test_unknown_gpu_label_fails_loudly():
    row = ["8x NVIDIA Z900", "80 GB", "26", "200 GiB", "1 TiB", "$1.99 / hr"]
    with pytest.raises(LayoutError, match="Z900"):
        parse(page(table(B, [row], ON_DEMAND)), META)


def test_unknown_table_with_prices_fails_loudly():
    with pytest.raises(LayoutError, match="unknown table"):
        parse(page(table(["GPU type", "Cost"], [["H100", "$2.00"]])), META)


def test_unknown_table_without_prices_is_ignored():
    assert parse(page(table(["Feature", "Included"], [["Support", "Yes"]])), META) == []


def test_unreadable_price_fails_loudly():
    row = ["8x NVIDIA Tesla V100", "16 GB", "92", "448 GiB", "5.9 TiB", "$four"]
    with pytest.raises(LayoutError, match="price"):
        parse(page(table(B, [row], ON_DEMAND)), META)


PER_GPU = ["GPUs", "VRAM/GPU", "vCPUs", "RAM", "STORAGE", "PRICE/GPU/HR*"]


def test_header_spacing_and_instance_price_variants_are_the_same_layout():
    headers = ["GPUs", "VRAM / GPU", "vCPUs", "RAM", "STORAGE", "PRICE*"]
    rows = [["8x NVIDIA H100 SXM New", "80 GB", "208", "1800 GiB", "26 TiB SSD", "$27.92 / hr"]]
    row = parse(page(table(headers, rows, ON_DEMAND)), META)[0]
    assert row.price_usd_per_gpu_hour == pytest.approx(3.49)


def test_a_separate_column_can_hold_the_contract_kind():
    headers = ["", "GPUs", "VRAM / GPU", "vCPUs", "RAM", "STORAGE", "PRICE / GPU / HR*"]
    rows = [
        [
            "On-demand",
            "8x NVIDIA H100 SXM New Price",
            "80 GB",
            "208",
            "1800 GiB",
            "26 TiB",
            "$2.99 / GPU / hr",
        ],
        [
            "Reserved",
            "8x NVIDIA H100 SXM New",
            "80 GB",
            "208",
            "1800 GiB",
            "26 TiB",
            "CONTACT SALES",
        ],
    ]
    parsed = parse(page(table(headers, rows)), META)
    assert [r.contract_type for r in parsed] == ["on_demand"]
    assert parsed[0].price_usd_per_gpu_hour == 2.99


def test_a_blank_first_header_can_hold_the_label_with_a_bare_per_gpu_price():
    headers = ["", "VRAM/GPU", "vCPUs", "RAM", "STORAGE", "PRICE/GPU/HR*"]
    rows = [["On-demand 8x NVIDIA B200 SXM6", "180 GB", "208", "2900 GiB", "22 TiB SSD", "$4.99"]]
    row = parse(page(table(headers, rows)), META)[0]
    assert (row.chip, row.gpu_count, row.price_usd_per_gpu_hour) == ("b200", 8, 4.99)


def test_reserved_row_with_a_trailing_note_and_no_price_is_skipped():
    rows = [
        [
            "Reserved 8x NVIDIA H100 SXM (min. 64 GPUs)",
            "80 GB",
            "208",
            "1800 GiB",
            "22 TiB",
            "CONTACT SALES",
        ]
    ]
    assert parse(page(table(PER_GPU, rows)), META) == []


def test_two_dated_price_columns_use_the_one_in_force_at_the_snapshot():
    headers = B[:5] + ["2023 Price", "2024 Price (effective 1/1/2024)"]
    rows = [["1x NVIDIA A100 SXM", "40 GB", "30", "200 GiB", "512 GiB", "$1.10 / hr", "$1.29 / hr"]]
    before = {**META, "retrieved_at": "2023-12-20T00:00:00Z"}
    after = {**META, "retrieved_at": "2024-01-01T07:34:33Z"}
    assert parse(page(table(headers, rows, ON_DEMAND)), before)[0].price_usd_per_gpu_hour == 1.10
    assert parse(page(table(headers, rows, ON_DEMAND)), after)[0].price_usd_per_gpu_hour == 1.29


def test_ladder_takes_its_chip_from_the_heading_and_keeps_each_commitment():
    headers = ["", "Commitment", "As low as (per GPU-hour)"]
    rows = [
        ["On-demand", "1 week-3 months", "$2.69— contact us"],
        ["Reserved", "3-6 months", "$2.29— contact us"],
        ["Reserved", "1 year", "$1.85— contact us"],
        ["Reserved", "2 years", "$1.70"],
        ["Reserved", "3 years", "Talk to our team"],
    ]
    parsed = parse(page(table(headers, rows, "1-Click Clusters NVIDIA H100 GPUs")), META)
    by_term = {r.sku.split("|")[-1]: r for r in parsed}
    assert set(by_term) == {"1 week-3 months", "3-6 months", "1 year", "2 years"}
    assert {r.chip for r in parsed} == {"h100_sxm"}
    assert (by_term["1 year"].contract_type, by_term["1 year"].term_months) == ("reserved_1y", 12)
    assert (by_term["2 years"].contract_type, by_term["2 years"].term_months) == ("other", 24)
    assert (by_term["3-6 months"].contract_type, by_term["3-6 months"].term_months) == (
        "other",
        None,
    )
    assert by_term["1 year"].gpu_count == 1
    assert by_term["1 year"].price_usd_per_gpu_hour == 1.85


def test_ladder_with_no_chip_in_sight_fails_rather_than_guessing():
    headers = ["", "Commitment", "As low as (per GPU-hour)"]
    with pytest.raises(LayoutError, match="no chip"):
        parse(page(table(headers, [["Reserved", "1 year", "$1.85"]], "Great prices")), META)


def test_gh200_cluster_row_with_an_odd_term_is_skipped_as_out_of_scope():
    headers = [
        "",
        "Instance type",
        "GPU",
        "GPU Memory",
        "vCPUs",
        "Storage",
        "Network Bandwidth",
        "Per Hour Price",
        "Term",
        "# of GPUs",
    ]
    rows = [
        [
            "NVIDIA GH200",
            "1x NVIDIA GH200",
            "GH200 Superchip",
            "96 GB",
            "72",
            "30 TB",
            "400 Gbps",
            "$5.99 /GH200/hour",
            "3-12 months",
            "10 or 2",
        ],
        [
            "NVIDIA H100",
            "8x NVIDIA H100",
            "H100 SXM",
            "80 GB",
            "224",
            "30 TB",
            "3200 Gbps",
            "$1.89/H100/hour",
            "3 years",
            "64 - 32,000",
        ],
    ]
    parsed = parse(page(table(headers, rows)), META)
    assert [(r.chip, r.contract_type) for r in parsed] == [("h100_sxm", "reserved_3y")]


def test_tabbed_pages_use_the_live_parser_and_are_labelled_as_archive_rows():
    html = (
        '<html><body><button role="tab" id="t-0">8x</button>'
        '<div aria-labelledby="t-0"><table><tbody><tr data-plan="NVIDIA H100 SXM">'
        '<th data-label="Plan">NVIDIA H100 SXM</th><td data-label="VRAM/GPU">80 GB</td>'
        '<td data-label="vCPUs">208</td><td data-label="RAM">1800 GiB</td>'
        '<td data-label="STORAGE">22 TiB</td><td data-label="PRICE/GPU/HR*">$3.99</td>'
        "</tr></tbody></table></div></body></html>"
    )
    plans = {"NVIDIA H100 SXM": {"chip": "h100_sxm"}}
    row = parse(html, {**META, "lambda_config": {"plans": plans, "ignore": []}})[0]
    assert (row.collector, row.gpu_count, row.price_usd_per_gpu_hour) == ("wayback", 8, 3.99)


def test_the_2021_table_has_no_memory_column():
    headers = ["GPUs", "NVLink™", "vCPUs", "RAM", "Temporary Storage", "On-demand Price"]
    rows = [
        ["8x V100s", "Yes", "92", "448 GiB", "5.9 TiB", "$12.00 / hr"],
        ["1x A6000", "No", "14", "100 GiB", "1 TiB", "Coming Soon"],
    ]
    parsed = parse(page(table(headers, rows, ON_DEMAND)), META)
    assert [(r.chip, r.price_usd_per_gpu_hour) for r in parsed] == [("v100", 1.5)]


def test_contact_us_is_no_price():
    headers = ["", "Commitment", "As low as (per GPU-hour)"]
    rows = [
        ["Reserved", "1 year", "Contact us"],
        ["On-demand", "1 week+", "$3.79"],
        ["Reserved", "3-6 months", "As low as $2.29— Contact us"],
    ]
    parsed = parse(page(table(headers, rows, "NVIDIA HGX B200 GPUs")), META)
    assert [r.price_usd_per_gpu_hour for r in parsed] == [3.79, 2.29]


def test_tabbed_pages_can_also_carry_a_commitment_ladder():
    html = (
        "<html><body><p>NVIDIA H100 GPUs</p><table><thead><tr><th>Plan</th><th>Commitment</th>"
        "<th>As low as (per GPU-hour)</th><th>Action</th></tr></thead><tbody>"
        '<tr data-plan="Reserved">'
        '<th data-label="Plan">Reserved</th><td data-label="Commitment">1 year</td>'
        '<td data-label="As low as (per GPU-hour)">$1.85</td><td data-label="Action">Talk</td>'
        "</tr></tbody></table>"
        '<button role="tab" id="t-0">8x</button>'
        '<div aria-labelledby="t-0"><table><tbody><tr data-plan="NVIDIA H100 SXM">'
        '<th data-label="Plan">NVIDIA H100 SXM</th><td data-label="VRAM/GPU">80 GB</td>'
        '<td data-label="vCPUs">208</td><td data-label="RAM">1800 GiB</td>'
        '<td data-label="STORAGE">22 TiB</td><td data-label="PRICE/GPU/HR*">$3.99</td>'
        "</tr></tbody></table></div></body></html>"
    )
    plans = {"NVIDIA H100 SXM": {"chip": "h100_sxm"}}
    rows = parse(html, {**META, "lambda_config": {"plans": plans, "ignore": []}})
    assert sorted(r.price_usd_per_gpu_hour for r in rows) == [1.85, 3.99]


def test_early_pages_without_tables_read_the_stated_instance_price():
    text = (
        "<html><body><h2>8-GPU Instance NEW</h2><p>GPUS 8x NVIDIA Tesla V100 Tensor Core (16 GB) "
        "+ NVLink VCPUS 92 SYSTEM RAM 448 GB</p><p>Dedicated 8-GPU instance pricing $12.00 / hr</p>"
        "</body></html>"
    )
    row = parse(text, META)[0]
    assert (row.chip, row.gpu_count) == ("v100", 8)
    assert row.price_usd_per_gpu_hour == 1.5
