import pytest

from gel.parse.errors import LayoutError
from gel.parse.wayback_coreweave import parse

META = dict(retrieved_at="2023-06-13T01:48:40Z", source_url="u", raw_file="r")


def table(headers, rows, before=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<p>{before}</p><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def page(*parts):
    return "<html><body>" + "".join(parts) + "</body></html>"


def columns(cells):
    return "".join(f'<div class="w-col"><div>{c}</div></div>' for c in cells)


GRID_HEAD = [
    "GPU Model",
    "VRAM (GB)",
    "Max vCPUs per GPU<br/>(<strong>$0.01</strong>/hr)",
    "Max RAM (GB) per GPU<br/>($0.005/hr)",
    "GPU Component<br/>Cost Per Hour",
]


def grid(rows, head=None):
    """The 2022-24 price grid, with a desktop block of div rows."""
    body = "".join(f'<div class="table-body-row w-row">{columns(row)}</div>' for row in rows)
    return (
        f'<div class="desktop"><div class="table"><div class="table-header">'
        f'<div class="table-header-container w-row">{columns(head or GRID_HEAD)}</div></div>'
        f'<div class="table-body">{body}</div></div></div>'
    )


def card(label, price):
    """The same grid's mobile card."""
    return (
        f'<div class="pricing-card"><div><a href="#">{label}</a><div>{price}</div></div>'
        '<div class="pricing-card-right"><div><strong>80</strong> VRAM</div></div></div>'
    )


def v2_row(cells, row_class="kubernetes-gpu-pricing", row_type="table-row"):
    """A 2025-26 CMS row. The model cell repeats the name in a node the page hides."""
    name, rest = cells[0], cells[1:]
    model = f'<h3>{name}</h3><h3 class="w-condition-invisible">{name}</h3>'
    body = "".join(f'<div class="table-v2-cell"><div>{c}</div></div>' for c in rest)
    mobile = f'<div class="table-cell-column"><div class="table-meta-value">{name}</div></div>'
    return (
        f'<div role="listitem" class="{row_type} w-dyn-item {row_class}"><div class="table-grid">'
        f'<div class="table-v2-cell table-v2-cell--name">{model}</div>{body}{mobile}</div></div>'
    )


def v2_table(head, rows, classes="kubernetes-gpu-pricing", region=""):
    cells = "".join(f'<div class="table-v2-cell">{h}</div>' for h in head)
    label = f"<h5>{region}</h5>" if region else ""
    return (
        f'{label}<div class="table-v2 {classes}"><div class="table-v2-header">{cells}</div>'
        f'<div class="table-v2-body"><div role="list">{"".join(rows)}</div></div></div>'
    )


V2_2025 = [
    "GPU Model",
    "GPU Count",
    "VRAM (GB)",
    "vCPUs",
    "System RAM<br/>(GB)",
    "Local Storage<br/>(TB)",
    "Instance Price<br/>(Per Hour)",
]
V2_2026 = V2_2025[:-1] + ["On-Demand Price (Per Hour)", "Spot Price (Per Hour)"]
INFERENCE = "Inference Single GPU Price(Per Hour)²"
COMPONENT = ["Type", "Description", "Resource Label", "Cost per Hour", "VRAM"]
FLAT = ["Description", "Label", "Cost per hour", "VRAM"]
INSTANCE = ["GPU", "GPU Count", "Instance", "Cost per hour"]
BUNDLED = ["GPU Type", "VRAM", "vCPU", "RAM (GB)", "Storage", "Network", "$/GPU/Hour"]


def test_the_2020_table_quotes_a_bundle_of_one_gpu_with_its_cpu_and_ram():
    rows = [
        ["NVIDIA V100 for NVLINK", "16GB HBM2", "4", "32", "450", "10 Gbps", "$9.11"],
        ["NVIDIA V100 for PCIe", "16GB HBM2", "3", "20", "64", "1 Gbps", "$9.22"],
    ]
    parsed = parse(page(table(BUNDLED, rows)), META)
    assert [r.price_usd_per_gpu_hour for r in parsed] == [9.11, 9.22]
    assert {(r.chip, r.gpu_count, r.price_basis) for r in parsed} == {("v100", 1, "instance")}
    assert (parsed[0].vcpus, parsed[0].ram_gb, parsed[0].gpu_memory_gb) == (4, 32.0, 16)
    assert parsed[0].interconnect == "NVLINK" and parsed[1].interconnect == "PCIe"
    assert (parsed[0].provider, parsed[0].provider_type) == ("coreweave", "neocloud")
    assert (parsed[0].collector, parsed[0].region) == ("wayback", "unspecified")
    assert (parsed[0].contract_type, parsed[0].price_kind) == ("on_demand", "list")


@pytest.mark.parametrize("label", ["NVIDIA P100 for NVLINK", "NVIDIA Quadro RTX 6000"])
def test_out_of_scope_gpus_in_the_2020_table_are_skipped(label):
    row = [label, "16GB", "4", "32", "450", "10 Gbps", "$9.11"]
    assert parse(page(table(BUNDLED, [row])), META) == []


def test_tables_filled_by_script_hold_no_prices_and_are_truly_empty():
    html = page(
        table(["Qty", "GPU Type", "VRAM", "vCPU", "RAM", "Storage", "Network", "$/Hour"], []),
        table(["Offering", "Rate"], [["Block Storage (HDD)", "$9.99 per GB / month"]]),
    )
    assert parse(html, META) == []


def test_the_same_table_with_chip_prices_in_it_fails_loudly():
    headers = ["Qty", "GPU Type", "VRAM", "vCPU", "RAM", "Storage", "Network", "$/Hour"]
    row = ["8", "NVIDIA V100", "16GB", "8", "64", "1TB", "1 Gbps", "$9.11"]
    with pytest.raises(LayoutError, match="unknown table"):
        parse(page(table(headers, [row])), META)


def test_resource_table_prices_a_gpu_component_alone():
    rows = [
        ["GPU", "NVIDIA V100 for NVLINK", "Tesla_V100_NVLINK", "$9.33", "16GB HBM2"],
        ["CPU", "AMD Epyc vCPU", "epyc", "$9.44", "N/A"],
        ["RAM", "System RAM per GB", "memory", "$9.55", "N/A"],
    ]
    parsed = parse(page(table(COMPONENT, rows)), META)
    assert len(parsed) == 1
    row = parsed[0]
    assert (row.chip, row.gpu_count, row.price_basis) == ("v100", 1, "accelerator_only")
    assert row.price_usd_per_gpu_hour == row.price_usd_per_hour_instance == 9.33
    assert (row.vcpus, row.ram_gb, row.gpu_memory_gb) == (None, None, 16)
    assert row.contract_type == "on_demand"


def test_a100_memory_can_come_from_the_vram_cell_or_the_resource_label():
    rows = [
        ["GPU", "NVIDIA A100 for NVLINK", "A100_NVLINK", "$9.33", "40GB HBM2e"],
        ["GPU", "NVIDIA A100 for PCIE", "A100_PCIE_80GB", "$9.44", "​"],
        ["GPU", "NVIDIA A100 for NVLINK (80GB)", "A100_NVLINK _ 80GB", "$9.55", "​"],
    ]
    parsed = parse(page(table(COMPONENT, rows)), META)
    assert [(r.chip, r.gpu_memory_gb) for r in parsed] == [
        ("a100_40gb", 40),
        ("a100_80gb", 80),
        ("a100_80gb", 80),
    ]
    assert "A100_NVLINK_80GB" in parsed[2].sku


def test_a100_with_no_memory_on_the_row_fails_rather_than_assuming():
    row = ["GPU", "NVIDIA A100 for NVLINK", "A100_NVLINK", "$9.33", "N/A"]
    with pytest.raises(LayoutError, match="memory"):
        parse(page(table(COMPONENT, [row])), META)


def test_memory_stated_twice_with_different_values_fails():
    row = ["GPU", "NVIDIA A100 (40GB)", "A100_PCIE_80GB", "$9.33", "40GB"]
    with pytest.raises(LayoutError, match="memory"):
        parse(page(table(COMPONENT, [row])), META)


def test_the_2023_table_has_no_type_column_and_reads_h100_form_factors():
    rows = [
        ["H100 HGX (80GB)", "H100_NVLINK_80GB", "$9.33", "N/A"],
        ["H100 for PCIe (80GB)", "H100_PCIE", "$9.44", "N/A"],
        ["A100 HGX (40GB)", "A100_NVLINK", "$9.55", "40GB HBM2e"],
        ["RTX A6000", "RTX_A6000", "$9.66", "48GB GDDR6"],
        ["A40", "A40", "$9.77", "48GB GDDR6"],
    ]
    parsed = parse(page(table(FLAT, rows)), META)
    assert [(r.chip, r.gpu_memory_gb) for r in parsed] == [
        ("h100_sxm", 80),
        ("h100_pcie", 80),
        ("a100_40gb", 40),
    ]
    assert {r.price_basis for r in parsed} == {"accelerator_only"}


def test_the_billing_example_table_never_becomes_a_row():
    example = table(
        ["Instance type", "Instance count", "Unit cost per hour"],
        [["Tesla V100 NVLINK", "4", "$9.33"]],
    )
    real = table(FLAT, [["V100 for NVLINK", "Tesla_V100_NVLINK", "$9.33", "16GB HBM2"]])
    parsed = parse(page(real, example), META)
    assert [(r.gpu_count, r.price_usd_per_gpu_hour) for r in parsed] == [(1, 9.33)]


def gitbook(*cells, heading="GPU Instance Resource Pricing", end="An example, guaranteed request"):
    head = ["Type", "Description", "Label", "Cost per Hour", "VRAM"]
    spans = "".join(f"<div><span>{c}</span></div>" for c in [heading, *head, *cells, end])
    return page(f"<div>{spans}</div>")


def test_resource_rows_drawn_in_divs_are_read_from_the_page_text():
    html = gitbook(
        "GPU",
        "NVIDIA A100 for NVLINK (80GB)",
        "A100_NVLINK",
        "_",
        "80GB",
        "$9.33",
        "​",
        "GPU",
        "NVIDIA Quadro RTX 5000",
        "Quadro_RTX",
        "_",
        "5000",
        "$9.44",
        "16GB GDDR6",
        "GPU",
        "NVIDIA V100 for NVLINK",
        "Tesla_V100_NVLINK",
        "$9.55",
        "16GB HBM2",
        "CPU",
        "AMD Epyc Rome vCPU",
        "amd-epyc-rome",
        "$9.66",
        "N/A",
        "RAM",
        "System RAM per GB",
        "memory",
        "$9.77",
        "N/A",
    )
    parsed = parse(html, META)
    assert [(r.chip, r.price_usd_per_gpu_hour) for r in parsed] == [
        ("a100_80gb", 9.33),
        ("v100", 9.55),
    ]
    assert {r.price_basis for r in parsed} == {"accelerator_only"}
    assert "A100_NVLINK_80GB" in parsed[0].sku


def test_a_page_with_a_real_grid_but_only_unpriced_chips_is_not_silently_empty():
    row = ["NVIDIA HGX H100", "80", "48", "256", "Reserve Now"]
    with pytest.raises(LayoutError, match="unknown layout"):
        parse(page(grid([row])), META)


def test_a_div_row_with_no_price_fails_loudly():
    html = gitbook("GPU", "NVIDIA V100 for NVLINK", "Tesla_V100_NVLINK", "soon", "16GB")
    with pytest.raises(LayoutError, match="no price"):
        parse(html, META)


def test_the_price_grid_is_a_component_price_and_its_maximums_are_not_included_cpus():
    rows = [
        ["A100 80GB NVLINK", "80", "48", "256", "<strong>$9.33</strong>"],
        ["A100 40GB PCIe", "40", "48", "256", "<strong>$9.44</strong>"],
        ["NVIDIA H100 PCIe", "80", "48", "256", "<strong>$9.55</strong>"],
        ["Tesla V100 NVLINK", "16", "36", "128", "<strong>$9.66</strong>"],
        ["A40", "48", "48", "256", "<strong>$9.77</strong>"],
        ["RTX A6000", "48", "48", "256", "<strong>$9.88</strong>"],
    ]
    parsed = parse(page(grid(rows)), META)
    assert [r.chip for r in parsed] == ["a100_80gb", "a100_40gb", "h100_pcie", "v100"]
    assert {r.price_basis for r in parsed} == {"accelerator_only"}
    assert {(r.gpu_count, r.vcpus, r.ram_gb) for r in parsed} == {(1, None, None)}
    assert parsed[0].price_usd_per_gpu_hour == 9.33
    assert parsed[0].gpu_memory_gb == 80


def test_a_grid_with_another_price_column_is_not_a_component_price():
    head = GRID_HEAD[:4] + ["Instance Cost Per Hour"]
    row = ["Tesla V100 NVLINK", "16", "36", "128", "$9.66"]
    with pytest.raises(LayoutError, match="GPU Component"):
        parse(page(grid([row], head=head)), META)


def test_reserve_now_with_no_price_gives_no_row():
    reserve = '<a href="/r"><strong>Reserve Now</strong></a>'
    rows = [
        ["NVIDIA HGX H100", "80", "48", "256", reserve],
        ["A100 40GB PCIe", "40", "48", "256", "$9.33"],
    ]
    assert [r.chip for r in parse(page(grid(rows)), META)] == ["a100_40gb"]


def test_a_price_beside_reserve_now_is_kept_with_no_term_and_is_labelled():
    cell = '<strong>$9.33</strong><a href="/r"><strong><br/>Reserve Now</strong></a>'
    row = parse(page(grid([["NVIDIA HGX H100", "80", "48", "256", cell]])), META)[0]
    assert (row.chip, row.price_usd_per_gpu_hour) == ("h100_sxm", 9.33)
    assert (row.contract_type, row.term_months) == ("on_demand", None)
    assert "reserve now" in row.sku


def test_a_mobile_card_that_agrees_changes_nothing_and_gives_no_second_row():
    desktop = grid([["A100 40GB PCIe", "40", "48", "256", "$9.33"]])
    assert len(parse(page(desktop, card("A100 40GB PCIe", "$9.33 / Hour")), META)) == 1


def test_a_mobile_card_quoting_another_price_leaves_that_row_out():
    rows = [
        ["A100 40GB NVLINK", "40", "48", "256", "$9.33"],
        ["A100 40GB PCIe", "40", "48", "256", "$9.44"],
    ]
    cards = card("A100 40GB NVLINK", "<strong>$9.99</strong> / Hour")
    parsed = parse(page(grid(rows), card("A100 40GB PCIe", "$9.44 / Hour"), cards), META)
    assert [r.price_usd_per_gpu_hour for r in parsed] == [9.44]


def test_a_grid_price_with_no_card_is_kept():
    desktop = grid([["NVIDIA HGX H100", "80", "48", "256", "$9.33"]])
    html = page(desktop, card("NVIDIA HGX H100", '<a href="/r">Reserve Now</a>'))
    assert [r.price_usd_per_gpu_hour for r in parse(html, META)] == [9.33]


def test_starting_at_banner_is_not_a_price():
    banner = '<div class="banner__copy">NVIDIA HGX H100s are here, starting at $0.11/hr.</div>'
    row = ["A100 40GB PCIe", "40", "48", "256", "$9.33"]
    parsed = parse(page(banner, grid([row])), META)
    assert [r.price_usd_per_gpu_hour for r in parsed] == [9.33]


def test_up_to_percent_off_and_cpu_grids_are_not_prices():
    faq = "<p>Reserved Instances (up to 60% for 24/7 committed usage).</p>"
    cpu = (
        '<div class="desktop"><div class="table"><div class="table-header">'
        f'<div class="w-row">{columns(["CPU Model", "RAM per vCPU", "Cost Per vCPU"])}</div></div>'
        '<div class="table-body"><div class="table-body-row w-row">'
        f"{columns(['AMD EPYC Milan', '4', '$9.11'])}</div></div></div></div>"
    )
    row = ["A100 40GB PCIe", "40", "48", "256", "$9.33"]
    assert len(parse(page(faq, grid([row]), cpu), META)) == 1


def test_docs_instance_prices_cover_the_whole_instance_and_divide_by_the_stated_count():
    rows = [
        ["H100 HGX (InfiniBand)", "8", "gd-8xh100ib-i128", "$80.00"],
        ["H100 HGX", "8", "gd-8xh100-i128", "$80.00"],
        ["H200 (InfiniBand)", "8", "gd-8xh200ib-i128", "$88.00"],
        ["B200 (InfiniBand)", "8", "b200-8x", "$96.00"],
        ["L40S", "8", "gd-8xl40s-i128", "$40.00"],
    ]
    parsed = parse(page(table(INSTANCE, rows)), META)
    assert [r.chip for r in parsed] == ["h100_sxm", "h100_sxm", "h200", "b200", "l40s"]
    assert {r.price_basis for r in parsed} == {"instance"}
    assert parsed[0].gpu_count == 8
    assert parsed[0].price_usd_per_hour_instance == 80.0
    assert parsed[0].price_usd_per_gpu_hour == 10.0
    assert parsed[0].interconnect == "InfiniBand"
    assert parsed[0].sku != parsed[1].sku
    assert parsed[0].gpu_memory_gb is None


@pytest.mark.parametrize(
    "label",
    ["GB200 NVL72 1", "GB300 NVL72 *", "GH200", "L40", "RTX Pro 6000 Blackwell Server Edition"],
)
def test_out_of_scope_instances_are_skipped(label):
    assert parse(page(table(INSTANCE, [[label, "4", "x", "$99.00"]])), META) == []


def test_contact_us_for_pricing_is_no_price():
    row = ["B200 (InfiniBand)", "8", "b200-8x", "Contact us for pricing"]
    assert parse(page(table(INSTANCE, [row])), META) == []


def test_docs_a100_with_no_memory_is_left_out():
    rows = [["A100", "8", "gd-8xa100-i128", "$80.00"], ["L40S", "8", "x", "$40.00"]]
    assert [r.chip for r in parse(page(table(INSTANCE, rows)), META)] == ["l40s"]


def test_docs_h100_with_no_form_factor_is_left_out():
    rows = [["H100 (InfiniBand)", "8", "x", "$80.00"], ["L40S", "8", "x", "$40.00"]]
    assert [r.chip for r in parse(page(table(INSTANCE, rows)), META)] == ["l40s"]


def test_docs_gpu_count_must_be_a_number():
    with pytest.raises(LayoutError, match="count"):
        parse(page(table(INSTANCE, [["H100 HGX", "", "x", "$80.00"]])), META)


def test_2025_grid_reads_visible_rows_and_a_stated_a100_memory():
    rows = [
        v2_row(["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "$80.00"]),
        v2_row(["NVIDIA HGX H200", "8", "141", "128", "2,048", "61.44", "$88.00"]),
        v2_row(["NVIDIA B200", "8", "180", "128", "2,048", "61.44", "$96.00"]),
        v2_row(["NVIDIA A100", "8", "80", "128", "2,048", "7.68", "$24.00"]),
        v2_row(["NVIDIA L40S", "8", "48", "128", "1,024", "7.68", "$16"]),
    ]
    parsed = parse(page(v2_table(V2_2025, rows)), META)
    assert [r.chip for r in parsed] == ["h100_sxm", "h200", "b200", "a100_80gb", "l40s"]
    assert {r.price_basis for r in parsed} == {"instance"}
    first = parsed[0]
    assert (first.gpu_count, first.vcpus, first.ram_gb, first.gpu_memory_gb) == (8, 128, 2048.0, 80)
    assert first.price_usd_per_gpu_hour == 10.0
    assert first.sku == "8x NVIDIA HGX H100"
    assert (first.contract_type, first.region) == ("on_demand", "unspecified")


def test_2025_grid_skips_rows_the_cms_lists_with_no_instance_price():
    rows = [
        v2_row(["NVIDIA H100 PCIe", "", "80", "", "", "", ""], row_class="gpu-pricing"),
        v2_row(["Public IP Address", "", "", "", "", "", ""], row_class="networking-pricing"),
        v2_row(["AMD Genoa (9454)", "", "", "192", "1,536", "7.68", "$7.77"], "kubernetes-cpu"),
        v2_row(["NVIDIA L40S", "8", "48", "128", "1,024", "7.68", "$16"]),
    ]
    assert [r.chip for r in parse(page(v2_table(V2_2025, rows)), META)] == ["l40s"]


def test_hidden_cms_copies_in_other_tables_never_become_rows():
    gpu = [v2_row(["NVIDIA L40S", "8", "48", "128", "1,024", "7.68", "$16"])]
    cpu = [v2_row(["NVIDIA HGX H100", "", "128", "2,048", "61.44", "$80.00"], "gpu-pricing")]
    rate = [v2_row(["A100 80GB NVLINK", "$9.33"], row_class="gpu-pricing")]
    html = page(
        v2_table(V2_2025, gpu),
        v2_table(["CPU Model", "CPU Type", "vCPUs", "RAM", "Storage", "Price"], cpu, "cpu"),
        v2_table(["Offering", "Rate"], rate, "networking-pricing"),
        v2_table(["Product", "Price"], rate, "storage-pricing-new"),
    )
    assert [r.chip for r in parse(html, META)] == ["l40s"]


@pytest.mark.parametrize(
    "label",
    [
        "NVIDIA GB200 NVL72",
        "NVIDIA GB300 NVL72",
        "NVIDIA HGX B300",
        "NVIDIA GH200",
        "NVIDIA L40",
        "NVIDIA RTX PRO 6000 Blackwell Server Edition (High Memory)",
    ],
)
def test_out_of_scope_grid_rows_are_skipped_even_with_a_footnoted_count(label):
    row = v2_row([label, "4^1", "186", "144", "960", "30.72", "$42.00"])
    assert parse(page(v2_table(V2_2025, [row])), META) == []


def test_an_in_scope_grid_row_with_a_blank_count_fails_rather_than_guessing():
    row = v2_row(["NVIDIA HGX H100", "", "80", "128", "2,048", "61.44", "$80.00"])
    with pytest.raises(LayoutError, match="count"):
        parse(page(v2_table(V2_2025, [row])), META)


def test_grid_h100_with_no_form_factor_fails_rather_than_assuming():
    row = v2_row(["NVIDIA H100", "8", "80", "128", "2,048", "61.44", "$80.00"])
    with pytest.raises(LayoutError, match="form factor"):
        parse(page(v2_table(V2_2025, [row])), META)


def test_grid_a100_with_no_memory_fails_rather_than_assuming():
    row = v2_row(["NVIDIA A100", "8", "", "128", "2,048", "7.68", "$24.00"])
    with pytest.raises(LayoutError, match="memory"):
        parse(page(v2_table(V2_2025, [row])), META)


def test_the_late_2025_row_class_is_the_same_grid():
    row = v2_row(
        ["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "$80.00"],
        row_class="gpu-pricing-and-kubernetes-gpu-pricing",
        row_type="table-row-v2",
    )
    parsed = parse(page(v2_table(V2_2025, [row], classes="gpu-pricing")), META)
    assert [(r.chip, r.price_usd_per_gpu_hour) for r in parsed] == [("h100_sxm", 10.0)]


def test_spot_prices_are_their_own_rows_and_each_table_names_its_region():
    north = v2_table(
        [*V2_2026, INFERENCE],
        [v2_row(["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "$80", "$40", "$10.00"])],
        classes="gpu-pricing",
        region="REGION: NORTH AMERICA",
    )
    europe = v2_table(
        V2_2026,
        [v2_row(["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "$80", "$32"])],
        classes="gpu-pricing",
        region="REGION: EUROPE",
    )
    parsed = parse(page(north, europe), META)
    found = {(r.region, r.contract_type, r.price_kind): r for r in parsed}
    assert set(found) == {
        ("north_america", "on_demand", "list"),
        ("north_america", "spot", "spot"),
        ("europe", "on_demand", "list"),
        ("europe", "spot", "spot"),
    }
    spot = found[("europe", "spot", "spot")]
    assert (spot.price_usd_per_hour_instance, spot.price_usd_per_gpu_hour) == (32.0, 4.0)
    assert (spot.term_months, spot.price_basis, spot.gpu_count) == (None, "instance", 8)
    assert spot.sku != found[("europe", "on_demand", "list")].sku


def test_inference_only_single_gpu_price_is_not_recorded():
    table_ = v2_table(
        [*V2_2026, INFERENCE],
        [v2_row(["NVIDIA L40S", "8", "48", "128", "1,024", "7.68", "$16", "N/A", "$2.00"])],
        classes="gpu-pricing",
    )
    assert [r.price_usd_per_gpu_hour for r in parse(page(table_), META)] == [2.0]
    assert [r.contract_type for r in parse(page(table_), META)] == ["on_demand"]


def test_contact_sales_on_demand_keeps_the_spot_row():
    row = v2_row(["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "Contact sales", "$40"])
    parsed = parse(page(v2_table(V2_2026, [row], classes="gpu-pricing")), META)
    assert [r.contract_type for r in parsed] == ["spot"]


def test_an_unknown_grid_price_column_fails_rather_than_being_ignored():
    head = [*V2_2025, "1-Year Reserved Price"]
    row = v2_row(["NVIDIA HGX H100", "8", "80", "128", "2,048", "61.44", "$80", "$60"])
    with pytest.raises(LayoutError, match="unknown column"):
        parse(page(v2_table(head, [row])), META)


def test_a_grid_row_of_the_wrong_length_fails():
    row = v2_row(["NVIDIA HGX H100", "8", "$80.00"])
    with pytest.raises(LayoutError, match="cells"):
        parse(page(v2_table(V2_2025, [row])), META)


def test_an_unknown_grid_table_with_chip_prices_fails_loudly():
    row = v2_row(["NVIDIA HGX H100", "$80.00"])
    with pytest.raises(LayoutError, match="unknown table"):
        parse(page(v2_table(["Accelerator", "Rate"], [row])), META)


def test_competitor_comparison_tables_can_never_become_rows():
    headers = ["Cloud", "GPU", "Price per hour"]
    rows = [["AWS p5.48xlarge", "NVIDIA H100 SXM", "$9.33"], ["CoreWeave", "H100", "$9.44"]]
    with pytest.raises(LayoutError, match="unknown table"):
        parse(page(table(headers, rows)), META)


def test_a_competitor_row_inside_a_known_grid_fails_loudly():
    row = ["AWS p4d.24xlarge", "40", "48", "256", "$9.33"]
    with pytest.raises(LayoutError, match="unknown GPU label"):
        parse(page(grid([row])), META)


def test_a_competitor_row_inside_an_instance_grid_fails_loudly():
    row = v2_row(["Azure ND H100 v5", "8", "80", "128", "2,048", "61.44", "$80.00"])
    with pytest.raises(LayoutError, match="form factor|unknown GPU label"):
        parse(page(v2_table(V2_2025, [row])), META)


def test_a_gpu_table_row_with_an_unknown_label_fails_loudly():
    with pytest.raises(LayoutError, match="Z900"):
        parse(page(table(INSTANCE, [["Z900", "8", "x", "$80.00"]])), META)


def test_an_unreadable_price_fails_loudly():
    with pytest.raises(LayoutError, match="unreadable price"):
        parse(page(table(INSTANCE, [["L40S", "8", "x", "from $40.00"]])), META)


def test_prices_outside_any_known_layout_fail_rather_than_return_empty():
    html = page("<div><h3>NVIDIA H100</h3><p>$9.33 / hour</p></div>")
    with pytest.raises(LayoutError, match="unknown layout"):
        parse(html, META)


def test_a_grid_page_with_no_gpu_table_fails_rather_than_return_empty():
    html = page(
        '<div class="pricing-card"><a href="#">NVIDIA HGX H100</a>$9.33 / Hour</div>',
    )
    with pytest.raises(LayoutError, match="GPU table"):
        parse(html, META)


def test_a_page_with_no_chips_and_only_storage_prices_is_empty():
    html = page("<p>Block Storage $9.99 per GB / month</p>")
    assert parse(html, META) == []
