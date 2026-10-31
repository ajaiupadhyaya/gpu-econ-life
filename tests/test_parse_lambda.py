import pytest

from gel.parse.errors import LayoutError
from gel.parse.lambda_pricing import parse_pricing

PLANS = {
    "NVIDIA H100 SXM": {"chip": "h100_sxm"},
    "NVIDIA H100": {"chip": "h100_sxm"},
    "NVIDIA A100 SXM": {"by_vram": {40: "a100_40gb", 80: "a100_80gb"}},
    "NVIDIA Tesla V100": {"chip": "v100"},
}
COMMON = dict(
    plans=PLANS,
    ignore=["NVIDIA A6000"],
    retrieved_at="2026-11-01T06:00:00Z",
    source_url="u",
    raw_file="r",
)


def instance_row(plan, vram, price, vcpus="208", ram="1800 GiB"):
    return (
        f'<tr data-plan="{plan}"><th data-label="Plan">{plan}</th>'
        f'<td data-label="VRAM/GPU">{vram} GB</td><td data-label="vCPUs">{vcpus}</td>'
        f'<td data-label="RAM">{ram}</td><td data-label="STORAGE">22 TiB SSD</td>'
        f'<td data-label="PRICE/GPU/HR*">${price}</td></tr>'
    )


def cluster_row(plan, duration, count, price):
    return (
        f'<tr data-plan="{plan}"><th data-label="Plan">{plan}</th>'
        f'<td data-label="DURATION">{duration}</td><td data-label="GPU COUNT">{count}</td>'
        f'<td data-label="PRICE/GPU/HR*">${price}</td><td data-label="Action">Talk</td></tr>'
    )


def page(*panels):
    buttons = "".join(
        f'<button role="tab" id="tab-a-{i}" class="tab-button">{label}</button>'
        for i, (label, _) in enumerate(panels)
    )
    bodies = "".join(
        f'<div role="tabpanel" aria-labelledby="tab-a-{i}"><table><tbody>{rows}</tbody></table>'
        "</div>"
        for i, (_, rows) in enumerate(panels)
    )
    return f"<html><body>{buttons}{bodies}</body></html>"


def test_instance_rows_take_gpu_count_from_their_tab():
    html = page(
        ("8x", instance_row("NVIDIA H100 SXM", 80, "3.99")),
        ("1x", instance_row("NVIDIA H100 SXM", 80, "4.29", vcpus="26", ram="225 GiB")),
    )
    rows = sorted(parse_pricing(html, **COMMON), key=lambda r: r.gpu_count)
    assert [(r.gpu_count, r.price_usd_per_gpu_hour) for r in rows] == [(1, 4.29), (8, 3.99)]
    assert rows[1].price_usd_per_hour_instance == pytest.approx(31.92)
    assert (rows[0].vcpus, rows[0].ram_gb) == (26, 225.0)
    assert rows[0].contract_type == "on_demand"


def test_ambiguous_plan_names_resolve_through_vram():
    html = page(
        (
            "8x",
            instance_row("NVIDIA A100 SXM", 80, "2.79")
            + instance_row("NVIDIA A100 SXM", 40, "1.99"),
        )
    )
    assert {r.chip for r in parse_pricing(html, **COMMON)} == {"a100_40gb", "a100_80gb"}


def test_cluster_rows_become_other_contracts_with_their_count():
    html = page(
        ("NVIDIA H100", cluster_row("NVIDIA H100", "2 weeks – 1 year", "256+", "5.54")),
        ("8x", instance_row("NVIDIA H100 SXM", 80, "3.99")),
    )
    row = next(r for r in parse_pricing(html, **COMMON) if r.contract_type == "other")
    assert row.gpu_count == 256
    assert row.term_months is None
    assert row.sku == "1cc|2 weeks – 1 year|256+"


def test_ignored_plans_are_skipped():
    html = page(("8x", instance_row("NVIDIA A6000", 48, "1.09")))
    with pytest.raises(LayoutError, match="no rows"):
        parse_pricing(html, **COMMON)


def test_unknown_plan_fails_loudly():
    html = page(("8x", instance_row("NVIDIA Z900", 80, "9.99")))
    with pytest.raises(LayoutError, match="Z900"):
        parse_pricing(html, **COMMON)


def test_page_without_price_rows_fails_loudly():
    with pytest.raises(LayoutError, match="no rows"):
        parse_pricing("<html><body>Maintenance</body></html>", **COMMON)


def test_a_dash_means_not_offered_in_that_tab_and_is_skipped():
    html = page(
        (
            "8x",
            instance_row("NVIDIA H100 SXM", 80, "3.99")
            + instance_row("NVIDIA Tesla V100", 16, "X").replace("$X", "—"),
        )
    )
    assert [r.chip for r in parse_pricing(html, **COMMON)] == ["h100_sxm"]


def test_older_cluster_tables_label_the_price_differently():
    html = page(
        (
            "NVIDIA H100",
            cluster_row("NVIDIA H100", "2 weeks", "16", "5.54")
            .replace("PRICE/GPU/HR*", "Price per hour")
            .replace("DURATION", "Duration")
            .replace("GPU COUNT", "GPU count"),
        ),
        ("8x", instance_row("NVIDIA H100 SXM", 80, "3.99")),
    )
    row = next(r for r in parse_pricing(html, **COMMON) if r.contract_type == "other")
    assert (row.gpu_count, row.price_usd_per_gpu_hour) == (16, 5.54)


def test_unparseable_price_fails_loudly():
    html = page(("8x", instance_row("NVIDIA H100 SXM", 80, "contact us")))
    with pytest.raises(LayoutError, match="price"):
        parse_pricing(html, **COMMON)
