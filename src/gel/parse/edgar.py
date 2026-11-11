"""Parse SEC EDGAR companyfacts into annual facts, and filing HTML into searchable text.

Facts: reads the latest raw companyfacts JSON per firm in data/raw/edgar/ and writes
data/interim/edgar/facts.parquet, one row per (firm, concept, unit, period) with the value from
the ORIGINAL annual filing for that period (earliest `filed`, then lowest accession), plus the
latest filing's value so restatements stay visible. Only annual forms (10-K, 10-K/A, 20-F,
20-F/A) are used; duration facts must span 330-400 days; instant facts must fall on a fiscal
year-end date seen in that firm's annual duration facts.

Every candidate concept for a variable is kept; `selected` marks, for each firm-variable-fiscal
year, the highest-priority concept that has a value (so Depreciation is used where present and
DepreciationDepletionAndAmortization or DepreciationAndAmortization only where it is missing).

Fiscal year = calendar year of the period end date. That matches each firm's own label here:
MSFT (June year-end), ORCL (May), the rest (December).

The companyfacts `fy` field is the fiscal year of the FILING, not of the fact (a FY2024 10-K
carries FY2022 comparatives with fy=2024), so it is recorded but never used as the period key.

Nebius (NBIS, formerly Yandex N.V.) files a 20-F with us-gaap concepts (no ifrs-full). Its
filings before the FY2024 20-F report the whole Yandex group in RUB with USD "convenience
translation" facts; config/accounting.yaml (xbrl.min_filing_fy) excludes those filings.

Usage: uv run python -m gel.parse.edgar
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path

import polars as pl
import yaml
from selectolax.lexbor import LexborHTMLParser as HTMLParser

RAW_DIR = Path("data/raw/edgar")
OUT = Path("data/interim/edgar/facts.parquet")
CONFIG = Path("config/accounting.yaml")
ANNUAL_FORMS = {"10-K", "10-K/A", "20-F", "20-F/A"}
MIN_DAYS, MAX_DAYS = 330, 400

# variable -> (unit, [concepts in priority order]). All in the us-gaap taxonomy.
VARIABLES: dict[str, tuple[str, list[str]]] = {
    "ppe_gross": (
        "USD",
        [
            "PropertyPlantAndEquipmentGross",
            "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetBeforeAccumulatedDepreciationAndAmortization",
        ],
    ),
    "ppe_net": (
        "USD",
        [
            "PropertyPlantAndEquipmentNet",
            "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization",
        ],
    ),
    "accumulated_depreciation": (
        "USD",
        [
            "AccumulatedDepreciationDepletionAndAmortizationPropertyPlantAndEquipment",
            "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAccumulatedDepreciationAndAmortization",
        ],
    ),
    "depreciation": (
        "USD",
        ["Depreciation", "DepreciationDepletionAndAmortization", "DepreciationAndAmortization"],
    ),
    "capex": (
        "USD",
        ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"],
    ),
    "operating_income": ("USD", ["OperatingIncomeLoss"]),
    "pretax_income": (
        "USD",
        [
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
            "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
        ],
    ),
    "income_tax": ("USD", ["IncomeTaxExpenseBenefit"]),
    "net_income": ("USD", ["NetIncomeLoss"]),
    "eps_diluted": ("USD/shares", ["EarningsPerShareDiluted"]),
    "shares_diluted": ("shares", ["WeightedAverageNumberOfDilutedSharesOutstanding"]),
}
INSTANT_VARIABLES = {"ppe_gross", "ppe_net", "accumulated_depreciation"}

SCHEMA = {
    "ticker": pl.Utf8,
    "cik": pl.Int64,
    "entity": pl.Utf8,
    "taxonomy": pl.Utf8,
    "concept": pl.Utf8,
    "variable": pl.Utf8,
    "priority": pl.Int64,
    "unit": pl.Utf8,
    "fiscal_year": pl.Int64,
    "start": pl.Date,
    "end": pl.Date,
    "value": pl.Float64,
    "accn": pl.Utf8,
    "form": pl.Utf8,
    "fy": pl.Int64,
    "fp": pl.Utf8,
    "filed": pl.Date,
    "frame": pl.Utf8,
    "n_filings": pl.Int64,
    "value_latest": pl.Float64,
    "accn_latest": pl.Utf8,
    "form_latest": pl.Utf8,
    "filed_latest": pl.Date,
    "restated": pl.Boolean,
}


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def annual_facts(companyfacts: dict, ticker: str, min_filing_fy: int | None = None) -> pl.DataFrame:
    """Deduplicated annual facts for every candidate concept in VARIABLES."""
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    rows: list[dict] = []
    for variable, (unit, concepts) in VARIABLES.items():
        for priority, concept in enumerate(concepts):
            for f in gaap.get(concept, {}).get("units", {}).get(unit, []):
                if f.get("form") not in ANNUAL_FORMS:
                    continue
                if min_filing_fy is not None and (f.get("fy") or 0) < min_filing_fy:
                    continue
                start, end = _d(f.get("start")), _d(f["end"])
                if variable in INSTANT_VARIABLES:
                    if start is not None:
                        continue
                elif start is None or not MIN_DAYS <= (end - start).days <= MAX_DAYS:
                    continue
                rows.append(
                    {
                        "ticker": ticker,
                        "cik": int(companyfacts.get("cik", 0)),
                        "entity": companyfacts.get("entityName", ""),
                        "taxonomy": "us-gaap",
                        "concept": concept,
                        "variable": variable,
                        "priority": priority,
                        "unit": unit,
                        "fiscal_year": end.year,
                        "start": start,
                        "end": end,
                        "value": float(f["val"]),
                        "accn": f["accn"],
                        "form": f["form"],
                        "fy": f.get("fy"),
                        "fp": f.get("fp"),
                        "filed": _d(f["filed"]),
                        "frame": f.get("frame"),
                    }
                )
    if not rows:
        return pl.DataFrame(schema=SCHEMA)
    df = pl.DataFrame(rows, schema={k: v for k, v in SCHEMA.items() if k in rows[0]})
    # Instants only on fiscal year-ends (dates where an annual duration fact ends).
    fy_ends = set(df.filter(pl.col("start").is_not_null())["end"].to_list())
    df = df.filter(pl.col("start").is_not_null() | pl.col("end").is_in(list(fy_ends)))
    return dedupe(df)


def dedupe(df: pl.DataFrame) -> pl.DataFrame:
    """One row per (ticker, concept, unit, start, end): the original filing's value."""
    keys = ["ticker", "concept", "unit", "start", "end"]
    df = df.sort([*keys, "filed", "accn"], nulls_last=False)
    g = df.group_by(keys, maintain_order=True)
    first = g.first()
    last = g.agg(
        pl.col("value").last().alias("value_latest"),
        pl.col("accn").last().alias("accn_latest"),
        pl.col("form").last().alias("form_latest"),
        pl.col("filed").last().alias("filed_latest"),
        pl.len().cast(pl.Int64).alias("n_filings"),
        (pl.col("value").n_unique() > 1).alias("restated"),
    )
    out = first.join(last, on=keys, how="left", nulls_equal=True)
    return out.select(list(SCHEMA))


def mark_selected(df: pl.DataFrame) -> pl.DataFrame:
    """selected = highest-priority concept per (ticker, variable, fiscal_year)."""
    best = df.group_by(["ticker", "variable", "fiscal_year"]).agg(
        pl.col("priority").min().alias("_best")
    )
    df = df.join(best, on=["ticker", "variable", "fiscal_year"], how="left")
    # If one concept has two periods ending in the same calendar year (rare), keep the later end.
    df = df.with_columns((pl.col("priority") == pl.col("_best")).alias("selected")).drop("_best")
    latest_end = (
        df.filter(pl.col("selected"))
        .group_by(["ticker", "variable", "fiscal_year"])
        .agg(pl.col("end").max().alias("_end"))
    )
    df = df.join(latest_end, on=["ticker", "variable", "fiscal_year"], how="left")
    df = df.with_columns(pl.col("selected") & (pl.col("end") == pl.col("_end"))).drop("_end")
    return df.sort(["ticker", "variable", "fiscal_year", "priority"])


def latest_companyfacts(root: Path = Path(".")) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in sorted((root / RAW_DIR).glob("*/*-companyfacts-*.json")):
        if not p.name.endswith(".json.json"):
            out[p.name.split("-companyfacts-")[1].split("-")[0]] = p  # sorted: last wins
    return out


def load_config(root: Path = Path(".")) -> dict:
    path = root / CONFIG
    return yaml.safe_load(path.read_text()) if path.exists() else {}


def build(root: Path = Path(".")) -> pl.DataFrame:
    cfg = load_config(root).get("xbrl", {})
    min_fy = cfg.get("min_filing_fy", {}) or {}
    frames = []
    for ticker, path in latest_companyfacts(root).items():
        frames.append(annual_facts(json.loads(path.read_text()), ticker, min_fy.get(ticker)))
    df = mark_selected(pl.concat(frames))
    out = root / OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(out)
    return df


# ---------------------------------------------------------------- filing text and quotes


_IX_HEADER = re.compile(rb"<ix:header>.*?</ix:header>", re.S | re.I)
# A space after block-level boundaries only, so inline tags (inline XBRL wraps numbers and
# words in <ix:nonNumeric>/<span>) do not split "four years." into "four years .".
_BLOCK_END = re.compile(rb"(</(?:p|div|td|th|tr|li|h[1-6]|table|title)\s*>|<br\s*/?>)", re.I)


def html_to_text(raw: bytes) -> str:
    """Visible text of a filing document, whitespace collapsed to single spaces."""
    tree = HTMLParser(_BLOCK_END.sub(rb"\1 ", _IX_HEADER.sub(b"", raw)))
    for node in tree.css("script, style"):
        node.decompose()
    body = tree.body or tree.root
    text = body.text(separator="") if body is not None else ""
    return normalize_ws(text)


def normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\xa0", " ").replace("​", "")).strip()


_SENT = re.compile(r"(?<=[.;])\s+(?=[A-Z(])")


def sentences_with(text: str, *keywords: str) -> list[str]:
    """Sentences containing every keyword (case-insensitive)."""
    kws = [k.lower() for k in keywords]
    return [s for s in _SENT.split(text) if all(k in s.lower() for k in kws)]


_QUOTE_LINE = re.compile(r'^- Quote: "(.*)"\s*$')
_RAW_LINE = re.compile(r"^- Raw file: `([^`]+)`")


def verify_quotes(md_path: Path, root: Path = Path(".")) -> list[str]:
    """Check every '- Quote: "..."' line in useful_lives.md appears verbatim (modulo whitespace)
    in the raw file named on the nearest preceding '- Raw file: `...`' line. Returns problems."""
    problems: list[str] = []
    raw_file: str | None = None
    cache: dict[str, str] = {}
    for n, line in enumerate(md_path.read_text().splitlines(), 1):
        if line.startswith("### "):
            raw_file = None
        m = _RAW_LINE.match(line)
        if m:
            raw_file = m.group(1)
            continue
        q = _QUOTE_LINE.match(line)
        if not q:
            continue
        if raw_file is None:
            problems.append(f"line {n}: quote without a raw file")
            continue
        if raw_file not in cache:
            cache[raw_file] = html_to_text((root / raw_file).read_bytes())
        if normalize_ws(q.group(1)) not in cache[raw_file]:
            problems.append(f"line {n}: quote not found in {raw_file}")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] == "verify":
        problems = verify_quotes(Path(args[1] if len(args) > 1 else "docs/useful_lives.md"))
        for p in problems:
            print(p)
        print(f"{len(problems)} problems")
        return 1 if problems else 0
    df = build()
    sel = df.filter(pl.col("selected"))
    print(f"wrote {OUT}: {df.height} facts ({sel.height} selected)")
    print(
        sel.group_by(["ticker", "variable"])
        .agg(pl.col("fiscal_year").min().alias("from"), pl.col("fiscal_year").max().alias("to"))
        .sort(["ticker", "variable"])
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
