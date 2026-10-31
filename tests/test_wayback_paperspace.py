import pytest

from gel.parse.errors import LayoutError
from gel.parse.wayback_paperspace import parse

META = dict(retrieved_at="2024-03-02T23:09:38Z", source_url="u", raw_file="r")
GPU_SPECS = ("16 GB GPU", "30 GB RAM", "8 vCPU")
HGX_SPECS = ("NVIDIA HGX H100 GPU", "111 GB RAM", "11 vCPU")
A100_SPECS = ("NVIDIA A100 GPU", "222 GB RAM", "22 vCPU")
THREE_YEAR = "<p>*$7.77/hour pricing is for a 3-year commitment.</p>"


def page(*parts):
    return "<html><body>" + "".join(parts) + "</body></html>"


def card(
    name, price="11.11", specs=GPU_SPECS, *, unit="/ hour", hide_price=False, hide_specs=False
):
    """A machine card as the flex layout writes it, from December 2021 on."""
    wrap = "instance-price-wrap hide" if hide_price else "instance-price-wrap"
    money = (
        f'<div class="{wrap}"><div class="text-block-13">$</div>'
        f'<h1 class="instance-price-2">{price}</h1><div class="text-block-22">{unit}</div></div>'
    )
    items = "".join(f'<li><p class="instance-specs-2">{s}</p></li>' for s in specs)
    listed = "instance-specs-list-2 hide" if hide_specs else "instance-specs-list-2"
    return (
        '<div class="instance-blocks-flex"><div class="instance-type-holder-flex">'
        f'<h1 class="instance-names">{name}</h1>{money if price else ""}'
        f'<ul class="{listed}">{items}</ul></div><a class="w-button">Create</a></div>'
    )


def hidden_card(name, price, specs):
    """Copies of retired cards sit in hidden containers, with the visible-looking markup."""
    return f'<div class="instance-container hide w-row">{card(name, price, specs)}</div>'


def core(hourly, monthly=""):
    return (
        '<div data-w-tab="Core" class="w-tab-pane">'
        '<div class="product-featured-logo hide">'
        '<h1 class="product-featured-core-text light">CORE</h1></div>'
        '<div class="tabs-menu hide w-tab-menu">Hourly Monthly</div>'
        f'<div data-w-tab="Hourly" class="w-tab-pane">{hourly}</div>'
        f'<div data-w-tab="Monthly" class="w-tab-pane">{monthly}</div></div>'
    )


def rows_of(hourly, monthly=""):
    return parse(page(core(hourly, monthly)), META)


def table(headers, rows, before=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<p>{before}</p><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


LONG = [
    "Name",
    "GPU (GB)",
    "vCPUs",
    "CPU RAM (GB)",
    "Price (hourly)",
    "Linux",
    "Windows",
    "Regions",
]
COUNTED = ["Machine Type", "GPUs", "Price (hourly)"]
SHORT = ["Name", "Price (hourly)", "Gradient Subscription Plan"]
UNCOUNTED = ["Machine", "Price (hourly)", "Gradient Subscription Plan"]


def long_row(name, memory, price, regions="NY2"):
    return [name, memory, "9", "99", price, "y", "", regions]


# The layouts


def test_flex_card_is_an_hourly_machine_with_one_gpu():
    row = rows_of(card("V100"))[0]
    assert (row.chip, row.gpu_count, row.contract_type) == ("v100", 1, "on_demand")
    assert row.term_months is None
    assert row.price_usd_per_gpu_hour == 11.11
    assert row.price_usd_per_hour_instance == 11.11
    assert (row.gpu_memory_gb, row.ram_gb, row.vcpus) == (16, 30, 8)
    assert row.provider == "paperspace" and row.provider_type == "neocloud"
    assert row.collector == "wayback" and row.region == "unspecified"
    assert row.price_basis == "instance"
    assert (row.source_url, row.raw_file) == ("u", "r")


def test_late_2021_cards_use_other_class_names():
    html = (
        '<div class="instance-blocks-flex"><div class="instance-type-holder-flex">'
        '<h1 class="instance-names-2">V100</h1><div class="div-block-30">'
        '<div class="text-block-13">$</div><h1 class="instance-price-2">11.11</h1>'
        '<div class="text-block-22">/ hour</div></div><ul class="instance-specs-list-2">'
        '<li><p class="instance-specs-2">16 GB GPU</p></li></ul></div></div>'
    )
    assert [r.price_usd_per_gpu_hour for r in rows_of(html)] == [11.11]


def test_2020_webflow_cards_sit_in_a_core_pane_beside_workstream():
    block = (
        '<div class="instance-blocks dedicated w-col"><div class="instance-type-holder">'
        '<h1 class="instance-names">V100</h1><div class="instance-description">Fast</div>'
        '<div class="instance-price-holder"><div class="sign-pricing">$</div>'
        '<h1 class="instance-price">{}</h1><div class="text-block-14">/ hour</div></div>'
        '<ul class="instance-specs-list"><li><p class="instance-specs">8 vCPU</p></li>'
        '<li><p class="instance-specs">16 GB GPU <span class="dedicated-gpu">DEDICATED</span></p>'
        '<p class="instance-specs">Starts at 50GB SSD</p></li></ul></div></div>'
    )
    workstream = (
        '<div data-w-tab="Tab 3" class="w-tab-pane">'
        '<h1 class="product-featured-core-text">Workstream</h1>'
        f'<div data-w-tab="Hourly" class="w-tab-pane">{block.format("99.99")}</div></div>'
    )
    rows = parse(page(workstream, core(block.format("11.11"))), META)
    assert [(r.price_usd_per_gpu_hour, r.gpu_memory_gb, r.vcpus) for r in rows] == [(11.11, 16, 8)]


def legacy_block(name, hourly, monthly):
    return (
        f'<div class="pricingContainer"><div class="pricingBlock"><h3 class="title"><span>{name}'
        '</span></h3><div class="shownPrice"><span class="dollarSign">$</span>'
        f'<span class="bigPrice white hourlyOnly hidden">{hourly}<span>/ hour</span></span>'
        f'<span class="bigPrice white monthlyOnly">{monthly}<span>/ month</span></span>'
        '<div class="hourlyOnly hidden">+ $5 monthly storage fee</div>'
        '<div class="monthlyOnly hidden"><span class="bold">$8.88</span> effective hourly price'
        '</div></div><div class="specs"><ul><li>30GB RAM</li><li>8 x CPU</li><li>16 GB GPU<span>'
        " DEDICATED</span></li></ul></div></div></div>"
    )


def test_the_2020_page_reads_the_hourly_price_behind_the_toggle():
    row = parse(page(legacy_block("V100", "11.11", "9999")), META)[0]
    assert (row.chip, row.price_usd_per_gpu_hour) == ("v100", 11.11)
    assert (row.gpu_memory_gb, row.ram_gb, row.vcpus) == (16, 30, 8)


def test_the_2020_page_leaves_out_gradient_instance_types():
    gradient = (
        '<div class="vmTypeBox2 pricingBlock"><h3 class="title"><span>V100 x8</span></h3>'
        '<div class="shownPrice"><span class="bigPrice white regularVMOnly">99.99<span>/ hour'
        '</span></span><span class="bigPrice white preemptibleOnly hidden">77.77<span>/ hour'
        "</span></span></div></div>"
        '<div class="vmTypeBox2 pricingBlock"><h3 class="title"><span>TPUv2</span></h3>'
        '<div class="shownPrice"><span class="bigPrice white hourlyOnly">66.66<span>/ hour'
        "</span></span></div></div>"
    )
    rows = parse(page(legacy_block("V100", "11.11", "9999"), gradient), META)
    assert [r.price_usd_per_gpu_hour for r in rows] == [11.11]


def test_the_2020_page_skips_other_gpus():
    assert parse(page(legacy_block("P5000", "11.11", "9999")), META) == []


def test_docs_table_with_memory_and_regions():
    rows = parse(
        page(table(LONG, [long_row("V100", "16", "$11.11/hr", "NY2 CA1")])),
        META,
    )
    row = rows[0]
    assert (row.chip, row.gpu_memory_gb, row.vcpus, row.ram_gb) == ("v100", 16, 9, 99)
    assert (row.region, row.gpu_count, row.price_usd_per_gpu_hour) == ("NY2 CA1", 1, 11.11)


def test_docs_short_table_states_no_memory_or_region():
    row = parse(page(table(SHORT, [["V100", "$11.11/hr", "Growth"]])), META)[0]
    assert (row.chip, row.gpu_memory_gb, row.region) == ("v100", None, "unspecified")
    assert (row.vcpus, row.ram_gb) == (None, None)


def test_docs_pages_with_no_content_are_empty():
    stub = "<a href='/h100'>NVIDIA H100 Reference</a><p>Paperspace Pricing</p>"
    assert parse(page(stub), META) == []


# Trap 1: the name decides, and hidden blocks are not on the page


def test_a_hidden_price_and_hidden_specs_are_not_read():
    html = (
        card("H100", "99.99", A100_SPECS, hide_price=True, hide_specs=True).replace(
            "</ul></div>",
            '</ul><div class="instance-price-wrap"><div class="text-block-13">$</div>'
            '<h1 class="instance-price-2">7.77*</h1><div class="text-block-22">/ hour</div></div>'
            '<ul class="instance-specs-list-2"><li><p class="instance-specs-2">'
            "NVIDIA HGX H100 GPU</p></li><li><p>111 GB RAM</p></li></ul></div>",
        )
        + THREE_YEAR
    )
    rows = rows_of(html)
    assert [(r.chip, r.price_usd_per_gpu_hour) for r in rows] == [("h100_sxm", 7.77)]


def test_an_h100_card_whose_only_price_is_hidden_gives_no_row():
    html = card("H100", "99.99", A100_SPECS, hide_price=True, hide_specs=True)
    assert rows_of(html) == []


def test_a_retired_card_in_a_hidden_container_is_not_read():
    rows = rows_of(card("V100", "11.11") + hidden_card("V100", "99.99", GPU_SPECS))
    assert [r.price_usd_per_gpu_hour for r in rows] == [11.11]


def test_visible_specs_naming_another_chip_fail_loudly():
    with pytest.raises(LayoutError, match="V100"):
        rows_of(card("V100", "11.11", A100_SPECS))


# Trap 2: only hourly machine prices become rows


def test_the_monthly_tab_never_becomes_rows():
    monthly = card("V100", "1234", GPU_SPECS, unit="/ month")
    rows = rows_of(card("V100", "11.11"), monthly)
    assert [r.price_usd_per_gpu_hour for r in rows] == [11.11]


def test_a_monthly_price_inside_the_hourly_tab_fails_loudly():
    with pytest.raises(LayoutError, match="month"):
        rows_of(card("V100", "1234", GPU_SPECS, unit="/ month"))


def test_gradient_plans_are_ignored():
    gradient = (
        '<div data-w-tab="Gradient" class="w-tab-pane"><h5>V100 included</h5>'
        '<div data-w-tab="Tab 1" class="w-tab-pane">$ 8 per month</div></div>'
    )
    rows = parse(page(gradient, core(card("V100", "11.11"))), META)
    assert [r.price_usd_per_gpu_hour for r in rows] == [11.11]


def test_docs_storage_network_and_subscription_tables_are_ignored():
    html = page(
        table(
            ["Size", "Price (hourly)", "Max Price (monthly)"], [["50 GB", "$1.11/hr", "$5.00/mo"]]
        ),
        table(
            ["Name", "Price (hourly)", "Max Price (monthly)"],
            [["Public IP Address", "$1.11/hr", "$3.00/mo"]],
        ),
        table(
            ["Subscription", "Price (hourly)", "Max Price (monthly)"],
            [["Growth", "$1.11/hr", "$39.00/mo"]],
        ),
        table(SHORT, [["V100", "$11.11/hr", "Growth"]]),
    )
    assert [r.price_usd_per_gpu_hour for r in parse(html, META)] == [11.11]


def test_docs_free_machines_are_not_prices():
    html = page(
        table(["Machine Name (slug)", "Hourly Rate"], [["Free-A100-80G", "$0.00"]]),
        table(["Name", "Gradient Subscription Plan"], [["Free A100-80G", "Growth"]]),
        table(SHORT, [["V100", "$11.11/hr", "Growth"]]),
    )
    assert [r.chip for r in parse(html, META)] == ["v100"]


@pytest.mark.parametrize(
    "name", ["P5000", "RTX4000", "A4000", "A6000", "M4000", "GPU+", "C4", "Air"]
)
def test_out_of_scope_cards_are_skipped(name):
    assert rows_of(card(name)) == []


@pytest.mark.parametrize("name", ["GPU+ (M4000)", "P4000", "A5000", "RTX5000"])
def test_out_of_scope_docs_rows_are_skipped(name):
    html = page(table(SHORT, [[name, "$1.11/hr", ""], ["V100", "$11.11/hr", ""]]))
    assert [r.chip for r in parse(html, META)] == ["v100"]


# Trap 3: per machine or per GPU


def test_multi_gpu_rows_with_a_stated_count_are_whole_machine_prices():
    html = page(
        table(LONG, [long_row("V100-32G", "32", "$11.00/hr")]),
        table(COUNTED, [["V100-32G", "2", "$22.00/hr"], ["V100-32G", "4", "$44.00/hr"]]),
    )
    rows = {r.gpu_count: r for r in parse(html, META)}
    assert set(rows) == {1, 2, 4}
    assert rows[4].price_usd_per_hour_instance == 44.0
    assert rows[4].price_usd_per_gpu_hour == 11.0
    assert rows[4].gpu_memory_gb == 32
    assert rows[4].region == "unspecified"
    assert len({r.sku for r in rows.values()}) == 3


def test_multi_gpu_rows_without_a_count_are_left_out_rather_than_divided():
    html = page(
        table(SHORT, [["V100-32G", "$11.00/hr", "Growth"]]),
        table(UNCOUNTED, [["V100-32G", "$22.00/hr", "Growth"], ["V100-32G", "$44.00/hr", ""]]),
    )
    assert [r.gpu_count for r in parse(html, META)] == [1]


def test_no_multi_gpu_rows_are_invented_from_a_card():
    assert [r.gpu_count for r in rows_of(card("V100"))] == [1]


# Trap 4: commitments stay apart from on-demand prices


def test_a_starred_price_takes_its_term_from_the_footnote():
    html = card("H100", "7.77*", HGX_SPECS) + THREE_YEAR
    row = rows_of(html)[0]
    assert (row.contract_type, row.term_months) == ("reserved_3y", 36)
    assert row.price_usd_per_gpu_hour == 7.77


def test_two_footnotes_are_kept_apart_by_their_stars():
    html = (
        card("H100", "7.77*", HGX_SPECS)
        + card("A100-80G", "6.66**", A100_SPECS)
        + "<p>*$7.77/hour pricing is for a 3-year commitment.**$6.66/hour pricing is for a"
        " 1-year commitment.</p><p>**$6.66/hour pricing is for a 1-year commitment.</p>"
    )
    rows = {r.chip: r for r in rows_of(html)}
    assert (rows["h100_sxm"].contract_type, rows["h100_sxm"].term_months) == ("reserved_3y", 36)
    assert (rows["a100_80gb"].contract_type, rows["a100_80gb"].term_months) == ("reserved_1y", 12)


def test_a_stated_term_that_fits_no_contract_type_is_other():
    html = (
        card("H100", "7.77*", HGX_SPECS) + "<p>*$7.77/hour pricing is for a 2-year commitment.</p>"
    )
    row = rows_of(html)[0]
    assert (row.contract_type, row.term_months) == ("other", 24)


def test_the_on_demand_footnote_is_a_separate_row():
    html = (
        card("H100", "7.77*", HGX_SPECS)
        + "<p>*$7.77/ hour pricing is for a 3-year commitment. On-demand pricing for H100 is"
        " $9.99 per hour.\xa0</p>"
    )
    rows = {r.contract_type: r for r in rows_of(html)}
    assert set(rows) == {"reserved_3y", "on_demand"}
    assert rows["on_demand"].price_usd_per_gpu_hour == 9.99
    assert rows["reserved_3y"].price_usd_per_gpu_hour == 7.77
    assert rows["on_demand"].chip == "h100_sxm"
    assert rows["on_demand"].term_months is None
    assert (rows["on_demand"].vcpus, rows["on_demand"].ram_gb) == (11, 111)


def test_a_starred_price_with_no_footnote_fails_loudly():
    with pytest.raises(LayoutError, match="footnote"):
        rows_of(card("H100", "7.77*", HGX_SPECS))


def test_a_footnote_for_another_price_fails_loudly():
    with pytest.raises(LayoutError, match="footnote"):
        rows_of(
            card("H100", "7.77*", HGX_SPECS) + "<p>*$1.23/hour pricing is for a 3-year term</p>"
        )


def test_an_on_demand_footnote_that_cannot_be_read_fails_loudly():
    html = (
        card("H100", "7.77*", HGX_SPECS) + THREE_YEAR + "<p>On-demand pricing for H100 varies</p>"
    )
    with pytest.raises(LayoutError, match="On-demand"):
        rows_of(html)


# Trap 5: variants and memory


def test_v100_variants_are_one_chip_with_memory_and_sku_kept():
    html = page(
        table(LONG, [long_row("V100", "16", "$11.00/hr"), long_row("V100-32G", "32", "$12.00/hr")])
    )
    rows = {r.gpu_memory_gb: r for r in parse(html, META)}
    assert {r.chip for r in rows.values()} == {"v100"}
    assert "V100-32G" in rows[32].sku and "V100-32G" not in rows[16].sku


def test_the_name_gives_v100_memory_when_the_table_does_not():
    row = parse(page(table(SHORT, [["V100-32G", "$11.00/hr", "Growth"]])), META)[0]
    assert (row.chip, row.gpu_memory_gb) == ("v100", 32)


def test_a100_memory_column_decides_the_chip():
    html = page(
        table(
            LONG,
            [long_row("A100", "40", "$11.00/hr"), long_row("A100-80G", "80", "$12.00/hr")],
        )
    )
    assert {r.chip: r.gpu_memory_gb for r in parse(html, META)} == {
        "a100_40gb": 40,
        "a100_80gb": 80,
    }


def test_a100_multi_gpu_rows_take_memory_from_the_same_page():
    html = page(
        table(LONG, [long_row("A100", "40", "$11.00/hr")]),
        table(COUNTED, [["A100", "8", "$88.00/hr"]]),
    )
    rows = {r.gpu_count: r for r in parse(html, META)}
    assert rows[8].chip == "a100_40gb"
    assert rows[8].price_usd_per_gpu_hour == 11.0


def test_a100_memory_outside_the_two_known_sizes_fails_loudly():
    with pytest.raises(LayoutError, match="A100"):
        parse(page(table(LONG, [long_row("A100", "20", "$11.00/hr")])), META)


def test_a100_with_no_memory_anywhere_on_the_page_is_left_out():
    assert rows_of(card("A100", "11.11", A100_SPECS)) == []
    assert parse(page(table(SHORT, [["A100", "$11.00/hr", "Growth"]])), META) == []


def test_a100_80g_card_takes_memory_from_its_name():
    row = rows_of(card("A100-80G", "11.11", A100_SPECS))[0]
    assert (row.chip, row.gpu_memory_gb, row.ram_gb) == ("a100_80gb", 80, 222)


def test_hgx_in_the_visible_specs_marks_h100_as_sxm():
    row = rows_of(card("H100", "11.11", HGX_SPECS))[0]
    assert row.chip == "h100_sxm"
    assert "HGX" in row.sku
    assert row.gpu_memory_gb is None


def test_h100_with_no_form_factor_is_left_out():
    html = page(
        table(LONG, [long_row("H100", "80", "$11.00/hr"), long_row("V100", "16", "$12.00/hr")]),
        table(COUNTED, [["H100", "8", "$88.00/hr"]]),
    )
    assert [r.chip for r in parse(html, META)] == ["v100"]
    assert rows_of(card("H100", "11.11", ("80 GB GPU",))) == []


# Trap 6: crossed-out, promotional and "starting at" prices


def test_a_struck_through_card_price_is_not_read():
    html = card("V100", "<s>99.99</s>11.11")
    assert [r.price_usd_per_gpu_hour for r in rows_of(html)] == [11.11]


def test_a_price_crossed_out_with_a_style_is_not_read():
    html = card("V100", '<span style="text-decoration: line-through">99.99</span>11.11')
    assert [r.price_usd_per_gpu_hour for r in rows_of(html)] == [11.11]


def test_a_struck_through_docs_row_price_is_not_read():
    html = page(table(SHORT, [["V100", "<del>$99.99/hr</del>$11.11/hr", "Growth"]]))
    assert [r.price_usd_per_gpu_hour for r in parse(html, META)] == [11.11]


def test_a_labelled_promo_price_is_kept_and_marked_in_sku():
    html = (
        card("H100", "7.77*", HGX_SPECS)
        + "<p>*$7.77/hour pricing is for a 3-year commitment. On-demand pricing for H100 is"
        " $9.99/hour under our special promo price.</p>"
    )
    rows = {r.contract_type: r for r in rows_of(html)}
    assert "promo" in rows["on_demand"].sku
    assert "promo" not in rows["reserved_3y"].sku


def test_a_starting_at_label_on_a_price_fails_loudly():
    html = card("V100").replace('<div class="text-block-13">$</div>', "Starting at $")
    with pytest.raises(LayoutError, match="price"):
        rows_of(html)


def test_a_marketing_banner_price_is_not_a_row():
    banner = "<p>Access NVIDIA H100 GPUs for as low as $1.23/hour!</p>"
    rows = rows_of(banner + card("V100"))
    assert [r.chip for r in rows] == ["v100"]


# Trap 7: unknown layouts fail loudly


def test_an_unknown_layout_holding_chip_prices_fails_loudly():
    html = page("<div class='new-pricing'><b>V100</b> <i>$11.11 / hr</i></div>")
    with pytest.raises(LayoutError, match="layout"):
        parse(html, META)


def test_a_core_pane_with_no_hourly_tab_fails_loudly():
    html = page(
        '<div class="w-tab-pane"><h1 class="product-featured-core-text">CORE</h1>'
        '<div data-w-tab="Pay as you go" class="w-tab-pane">V100 $11.11</div></div>'
    )
    with pytest.raises(LayoutError, match="layout"):
        parse(html, META)


def test_renamed_card_classes_fail_loudly():
    html = '<div class="gpu-card"><h1 class="gpu-name">V100</h1><p>$ 11.11 / hour</p></div>'
    with pytest.raises(LayoutError, match="layout"):
        rows_of(html)


def test_an_unknown_gpu_card_fails_loudly():
    with pytest.raises(LayoutError, match="Z900"):
        rows_of(card("Z900"))


def test_a_new_in_scope_chip_fails_loudly_rather_than_being_skipped():
    with pytest.raises(LayoutError, match="H200"):
        rows_of(card("H200"))


def test_an_unknown_name_in_a_docs_gpu_table_fails_loudly():
    html = page(table(SHORT, [["V100", "$11.11/hr", ""], ["Z900", "$22.22/hr", ""]]))
    with pytest.raises(LayoutError, match="Z900"):
        parse(html, META)


def test_an_unknown_docs_table_holding_chip_prices_fails_loudly():
    with pytest.raises(LayoutError, match="unknown table"):
        parse(page(table(["GPU type", "Cost"], [["V100", "$11.11"]])), META)


def test_a_docs_page_with_tables_but_no_gpu_table_fails_loudly_if_chip_prices_remain():
    html = page(table(["Size", "Price"], [["50 GB", "$1.11/hr"]]), "<p>V100 is $11.11/hr</p>")
    with pytest.raises(LayoutError, match="layout"):
        parse(html, META)


def test_an_unreadable_card_price_fails_loudly():
    with pytest.raises(LayoutError, match="price"):
        rows_of(card("V100", "four"))


def test_an_unreadable_docs_price_fails_loudly():
    with pytest.raises(LayoutError, match="price"):
        parse(page(table(SHORT, [["V100", "ask us", "Growth"]])), META)


def test_two_visible_prices_on_one_card_fail_loudly():
    html = card("V100").replace("</ul></div>", '</ul><h1 class="instance-price-2">9.99</h1></div>')
    with pytest.raises(LayoutError, match="price"):
        rows_of(html)
