from gel.collect.wayback_cdx import (
    build_params,
    parse_rows,
    provider_gate,
    render_preview,
    summarize_by_year,
)

HEADER = ["timestamp", "original", "statuscode", "digest", "length", "mimetype"]


def row(ts, status="200", digest="A", mimetype="text/html"):
    return [ts, "https://x.example/p", status, digest, "10", mimetype]


def test_build_params_requests_index_fields_only():
    params = build_params("https://x.example/p", from_year=2019, to_year=2026)
    assert params["url"] == "https://x.example/p"
    assert params["output"] == "json"
    assert params["from"] == "2019"
    assert params["to"] == "2026"
    assert "digest" in params["fl"]


def test_parse_rows_handles_empty_index():
    assert parse_rows([]) == []
    assert parse_rows([HEADER]) == []


def test_parse_rows_returns_named_fields():
    rows = parse_rows([HEADER, row("20210102030405")])
    assert rows[0]["timestamp"] == "20210102030405"
    assert rows[0]["statuscode"] == "200"


def test_summary_counts_only_usable_captures():
    rows = parse_rows(
        [
            HEADER,
            row("20210115000000", digest="A"),
            row("20210120000000", digest="A"),
            row("20210215000000", digest="B"),
            row("20210315000000", status="301", digest="C"),
            row("20210415000000", status="404", digest="D"),
            row("20220115000000", status="-", digest="B", mimetype="warc/revisit"),
        ]
    )
    summary = summarize_by_year(rows)
    assert summary[2021] == {"captures": 5, "usable": 3, "months": 2, "versions": 2}
    assert summary[2022] == {"captures": 1, "usable": 1, "months": 1, "versions": 1}


def _page(by_year):
    return {
        y: {"captures": n, "usable": n, "months": min(n, 12), "versions": 1}
        for y, n in by_year.items()
    }


def test_provider_gate_needs_six_usable_per_year_in_each_year_before_2023():
    ok = provider_gate([_page({2020: 6, 2021: 9, 2022: 12})])
    assert ok["passes"] is True
    thin = provider_gate([_page({2020: 5, 2021: 9, 2022: 12})])
    assert thin["passes"] is False
    assert thin["by_year"][2020] == 5


def test_provider_gate_sums_a_providers_pages():
    gate = provider_gate([_page({2020: 3, 2021: 3, 2022: 3}), _page({2020: 3, 2021: 3, 2022: 3})])
    assert gate["passes"] is True


def test_render_preview_states_stop_condition_result():
    results = {
        "good": {
            "provider_type": "hyperscaler",
            "pages": [
                {"url": "https://g.example/p", "by_year": _page({2020: 9, 2021: 9, 2022: 9})}
            ],
        },
        "bad": {
            "provider_type": "neocloud",
            "pages": [{"url": "https://b.example/p", "by_year": _page({2022: 1})}],
        },
    }
    md = render_preview(results, generated_at="2026-10-31T00:00:00Z")
    assert "1 of 2 providers" in md
    assert "https://g.example/p" in md
    assert "Do not read these counts as price coverage" in md
