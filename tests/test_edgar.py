"""Phase 7 EDGAR collector helpers and companyfacts parsing, on tiny hand-written fixtures."""

import json
from datetime import date
from pathlib import Path

import polars as pl
import pytest

from gel.collect import edgar as collect
from gel.parse import edgar as parse

FIX = Path(__file__).parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text())


# ------------------------------------------------------------------ collector


def test_resolve_ciks_from_sec_ticker_file():
    ciks = collect.resolve_ciks(load("edgar_tickers.json"), ["BBB", "aaa"])
    assert ciks == {"BBB": 2222, "aaa": 111}


def test_resolve_ciks_fails_loudly_on_unknown_ticker():
    with pytest.raises(SystemExit, match="ZZZ"):
        collect.resolve_ciks(load("edgar_tickers.json"), ["ZZZ"])


def test_select_filings_keeps_annuals_since_2020_and_first_10q_after_each():
    rows = collect.filing_rows(load("edgar_submissions.json"))
    picked = collect.select_filings("BBB", 2222, rows)
    accns = [f.accession for f in picked]
    # 2019 10-K is before 2020; 10-K/A is an amendment; only the first 10-Q after each 10-K.
    assert accns == ["0000002222-23-000009", "0000002222-24-000001", "0000002222-24-000002"]


def test_filing_url_uses_accession_without_dashes():
    f = collect.Filing("BBB", 2222, "0000002222-24-000001", "10-K", "", "", "b-20231231.htm")
    assert f.url == (
        "https://www.sec.gov/Archives/edgar/data/2222/000000222224000001/b-20231231.htm"
    )
    assert collect.filing_path(f) == Path(
        "data/raw/edgar/filings/BBB/0000002222-24-000001/b-20231231.htm"
    )


def test_latest_api_files_picks_most_recent_run(tmp_path):
    d1, d2 = tmp_path / collect.RAW_DIR / "2026-01-01", tmp_path / collect.RAW_DIR / "2026-02-01"
    for d in (d1, d2):
        d.mkdir(parents=True)
        (d / "010000Z-submissions-BBB-CIK0000002222.json").write_text("{}")
        (d / "010000Z-submissions-BBB-CIK0000002222.json.json").write_text("{}")
    (d2 / "010000Z-submissions-BBB-CIK0000002222-submissions-001.json").write_text("{}")
    got = collect.latest_api_files(tmp_path, "submissions")["BBB"]
    assert sorted(p.name for p in got) == [
        "010000Z-submissions-BBB-CIK0000002222-submissions-001.json",
        "010000Z-submissions-BBB-CIK0000002222.json",
    ]
    assert all(p.parent == d2 for p in got)


# ------------------------------------------------------------------ companyfacts parsing


@pytest.fixture
def facts() -> pl.DataFrame:
    return parse.mark_selected(parse.annual_facts(load("edgar_companyfacts.json"), "BBB"))


def row(df: pl.DataFrame, concept: str, fy: int) -> dict:
    hit = df.filter((pl.col("concept") == concept) & (pl.col("fiscal_year") == fy))
    assert hit.height == 1, hit
    return hit.row(0, named=True)


def test_duplicate_facts_keep_the_original_filing(facts):
    r = row(facts, "PaymentsToAcquirePropertyPlantAndEquipment", 2022)
    assert r["value"] == 100 and r["accn"] == "0000002222-23-000001"
    assert r["value_latest"] == 105 and r["accn_latest"] == "0000002222-24-000001"
    assert r["n_filings"] == 2 and r["restated"] is True


def test_only_annual_forms_full_year_durations_and_usd(facts):
    capex = facts.filter(pl.col("variable") == "capex")
    assert sorted(capex["fiscal_year"].to_list()) == [2022, 2023]
    assert capex.filter(pl.col("fiscal_year") == 2023)["value"].to_list() == [200]
    assert set(capex["unit"].to_list()) == {"USD"}


def test_instants_only_on_fiscal_year_ends(facts):
    ppe = facts.filter(pl.col("variable") == "ppe_gross")
    assert ppe["end"].to_list() == [date(2023, 12, 31)]
    assert ppe["value"].to_list() == [900]


def test_depreciation_falls_back_to_dda_only_where_missing(facts):
    sel = facts.filter((pl.col("variable") == "depreciation") & pl.col("selected"))
    by_year = dict(zip(sel["fiscal_year"].to_list(), sel["concept"].to_list(), strict=True))
    assert by_year == {2022: "DepreciationDepletionAndAmortization", 2023: "Depreciation"}


def test_split_adjusted_eps_is_kept_as_latest(facts):
    r = row(facts, "EarningsPerShareDiluted", 2022)
    assert r["value"] == 20.0 and r["value_latest"] == 1.0


def test_min_filing_fy_drops_earlier_filings():
    df = parse.annual_facts(load("edgar_companyfacts.json"), "BBB", min_filing_fy=2023)
    r = df.filter(
        (pl.col("concept") == "PaymentsToAcquirePropertyPlantAndEquipment")
        & (pl.col("fiscal_year") == 2022)
    ).row(0, named=True)
    assert r["value"] == 105 and r["n_filings"] == 1


# ------------------------------------------------------------------ filing text and quotes


def test_html_to_text_drops_hidden_xbrl_and_keeps_inline_words_together():
    text = parse.html_to_text((FIX / "edgar_filing.htm").read_bytes())
    assert "999" not in text and "color" not in text
    assert "from four to five years." in text
    assert "annually. We changed" in text and "Next block" in text


def test_verify_quotes_flags_paraphrase(tmp_path):
    raw = tmp_path / "f.htm"
    raw.write_bytes((FIX / "edgar_filing.htm").read_bytes())
    md = tmp_path / "lives.md"
    md.write_text(
        "### X\n"
        "- Raw file: `f.htm`\n"
        '- Quote: "We changed the useful life of our servers from four to five years."\n'
        '- Quote: "We changed server lives to five years."\n'
    )
    problems = parse.verify_quotes(md, tmp_path)
    assert len(problems) == 1 and "line 4" in problems[0]


def test_sentences_with_all_keywords():
    text = "Servers last six years. Buildings last 30 years; servers are reviewed."
    assert parse.sentences_with(text, "servers", "six") == ["Servers last six years."]
