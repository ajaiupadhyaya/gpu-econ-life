"""Parse archived Lambda pricing pages.

Columns are found by name, because the headers changed many times. An unknown table holding chip
prices raises, and so does an unknown GPU label. Reservation terms are recorded only where the page
states them. Tables comparing Lambda with other clouds are ignored, so a competitor's price can
never become a Lambda row.
"""

import re
from datetime import date

from selectolax.lexbor import LexborHTMLParser

from gel.parse.errors import LayoutError
from gel.parse.lambda_pricing import parse_pricing
from gel.parse.tables import Table, clean, page_text, read_tables
from gel.schema import Listing

LABEL = re.compile(r"^(?:(On-demand|Reserved)\s+)?(\d+)x\s+(.+)$", re.I)
TAGS = re.compile(r"\s+(New Price|New|Coming soon)\b.*$|\s+\(min\..*$", re.I)
PRICE = re.compile(r"^\$\s?(\d+(?:\.\d+)?)\s*(.*)$")
PER_GPU_UNIT = re.compile(r"^/\s*(GPU|H100|H200|A100|B200|GH200)\s*/\s*(hr|hour)\b", re.I)
PER_INSTANCE_UNIT = re.compile(r"^/\s*(hr|hour)\b", re.I)
NOTE = re.compile(r"^(—|-)?\s*(contact us)?$", re.I)
NO_PRICE = re.compile(
    r"^(coming soon|contact sales|contact us|talk to our team|sold out|-|—|)$", re.I
)
OUT_OF_SCOPE = re.compile(
    r"A6000|RTX 6000|RTX 600\b|\bA10\b|GH200|K80|RTX 8000|RTX 5000|A5000", re.I
)
CHIP_NAME = re.compile(r"V100|A100|H100|H200|B200")
EFFECTIVE = re.compile(r"effective (\d+)/(\d+)/(\d{4})", re.I)
TERM_COLUMNS = {
    "6 months": ("other", 6),
    "1 year": ("reserved_1y", 12),
    "3 year": ("reserved_3y", 36),
}
TERMS = {
    "3-months": ("other", 3),
    "1 year": ("reserved_1y", 12),
    "1-year": ("reserved_1y", 12),
    "2 years": ("other", 24),
    "3 years": ("reserved_3y", 36),
    "3-years": ("reserved_3y", 36),
}
EARLY_PRICE = re.compile(
    r"(\d+)x NVIDIA[^$]*?(V100|A100)[^$]*?"
    r"Dedicated \1-GPU instance pricing \$(\d+(?:\.\d+)?)\s*/\s*hr"
)


def _normal(header: str) -> str:
    return re.sub(r"\s*/\s*", "/", clean(header)).strip("*").lower()


def _chip(name: str, vram: int | None) -> str | None:
    upper = name.upper()
    if OUT_OF_SCOPE.search(name):
        return None
    if "V100" in upper:
        return "v100"
    if "H100" in upper:
        return "h100_pcie" if "PCIE" in upper else "h100_sxm"
    if "H200" in upper:
        return "h200"
    if "B200" in upper:
        return "b200"
    if "A100" in upper:
        chips = {40: "a100_40gb", 80: "a100_80gb"}
        if vram not in chips:
            raise LayoutError(f"A100 with unreadable memory: {name} {vram}")
        return chips[vram]
    raise LayoutError(f"unknown GPU label: {name}")


def _number(text: str) -> float | None:
    match = re.match(r"[\d,.]*\d", text)
    return float(match.group(0).replace(",", "")) if match else None


def _ram_gb(text: str) -> float | None:
    value = _number(text)
    if value is None:
        return None
    return value * 1000 if " TB" in f" {text}" else value


def _price(text: str, per_gpu_column: bool = False) -> tuple[float, bool] | None:
    """Return (price, is_per_gpu), or None where the page gives no price."""
    text = re.sub(r"^as low as\s+", "", text, flags=re.I)
    if NO_PRICE.match(text):
        return None
    match = PRICE.match(text)
    if not match:
        raise LayoutError(f"unreadable price: {text!r}")
    amount, rest = float(match.group(1)), match.group(2).strip()
    if PER_GPU_UNIT.match(rest):
        return amount, True
    if PER_INSTANCE_UNIT.match(rest):
        return amount, per_gpu_column
    if per_gpu_column and NOTE.match(rest):
        return amount, True
    raise LayoutError(f"unreadable price: {text!r}")


def _listing(
    meta: dict,
    *,
    label: str,
    gpus: int,
    vram: int | None,
    price: tuple[float, bool],
    contract: str,
    months: int | None,
    vcpus: str = "",
    ram: str = "",
    sku: str | None = None,
) -> Listing | None:
    chip = _chip(label, vram)
    if chip is None:
        return None
    build = Listing.from_gpu_price if price[1] else Listing.from_instance_price
    return build(
        price=price[0],
        gpu_count=gpus,
        retrieved_at=meta["retrieved_at"],
        provider="lambda",
        provider_type="neocloud",
        collector="wayback",
        sku=sku or f"{gpus}x {label}|{vram}GB",
        chip=chip,
        gpu_memory_gb=vram,
        interconnect=None,
        region="unspecified",
        contract_type=contract,
        term_months=months,
        vcpus=int(_number(vcpus)) if _number(vcpus) else None,
        ram_gb=_ram_gb(ram),
        source_url=meta["source_url"],
        raw_file=meta["raw_file"],
    )


def _split_label(cell: str) -> tuple[str | None, int, str]:
    match = LABEL.match(TAGS.sub("", clean(cell)))
    if not match:
        raise LayoutError(f"unreadable GPU cell: {cell!r}")
    return match.group(1), int(match.group(2)), match.group(3)


def _price_column(columns: dict[str, int], headers: list[str], snapshot: str) -> int:
    """With dated price columns, take the newest one in force at the snapshot."""
    dated = [(i, EFFECTIVE.search(h)) for i, h in enumerate(headers)]
    dated = [(i, m) for i, m in dated if m]
    if dated:
        i, match = dated[-1]
        month, day, year = (int(g) for g in match.groups())
        return i if date.fromisoformat(snapshot[:10]) >= date(year, month, day) else i - 1
    return next(i for name, i in columns.items() if name.startswith(("price", "on-demand price")))


def _instance_table(table: Table, meta: dict) -> list[Listing]:
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    vram_column = columns.get("vram per gpu", columns.get("vram/gpu"))
    label_column = columns.get("gpus", columns.get("plan", 0))
    kind_column = 0 if label_column != 0 else None
    price_column = _price_column(columns, table.headers, meta["retrieved_at"])
    per_gpu = "gpu" in _normal(table.headers[price_column])
    reserved = "Reserved pricing" in table.before or meta.get("reserved_page", False)
    term = re.search(r"minimum (\d+)-month commitment", table.before)
    default = ("other", int(term.group(1)) if term else None) if reserved else ("on_demand", None)
    rows = []
    for row in table.rows:
        kind, gpus, label = _split_label(row[label_column])
        kind = row[kind_column] if kind_column is not None else kind
        price = _price(row[price_column], per_gpu)
        if price is None:
            continue
        contract, months = default
        if kind and kind.lower() == "reserved":
            contract, months = "other", None
        vram = int(_number(row[vram_column])) if vram_column is not None else None
        listing = _listing(
            meta,
            label=label,
            gpus=gpus,
            vram=vram,
            price=price,
            contract=contract,
            months=months,
            vcpus=row[columns["vcpus"]],
            ram=row[columns["ram"]],
        )
        if listing:
            rows.append(listing)
    return rows


def _term_table(table: Table, meta: dict) -> list[Listing]:
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    rows = []
    for row in table.rows:
        _, gpus, label = _split_label(re.sub(r"\s*\(\d+ GB\)", "", row[0]))
        vram = int(_number(row[1]))
        for name, (contract, months) in TERM_COLUMNS.items():
            price = _price(row[columns[name]].replace("/hour", " / hr"))
            if price is None:
                continue
            listing = _listing(
                meta,
                label=label,
                gpus=gpus,
                vram=vram,
                price=price,
                contract=contract,
                months=months,
                vcpus=row[columns["vcpus"]],
            )
            if listing:
                rows.append(listing)
    return rows


def _cluster_table(table: Table, meta: dict) -> list[Listing]:
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    rows = []
    for row in table.rows:
        name = row[columns["gpu"]]
        if OUT_OF_SCOPE.search(name):
            continue
        _, gpus, _ = _split_label(row[columns["instance type"]])
        term = clean(row[columns["term"]]).lower()
        if term not in TERMS:
            raise LayoutError(f"unreadable term: {term!r}")
        contract, months = TERMS[term]
        price = _price(row[columns["per hour price"]])
        if price is None:
            continue
        listing = _listing(
            meta,
            label=name,
            gpus=gpus,
            vram=int(_number(row[columns["gpu memory"]])),
            price=price,
            contract=contract,
            months=months,
            vcpus=row[columns["vcpus"]],
            sku=f"cluster|{name}|{term}",
        )
        if listing:
            rows.append(listing)
    return rows


def _ladder_table(table: Table, meta: dict) -> list[Listing]:
    """A commitment ladder quotes one chip per GPU-hour. Its name sits in the text above it."""
    names = re.findall(r"H100|H200|B200", " ".join([*table.headers, table.before]))
    if not names:
        raise LayoutError("commitment ladder with no chip named near it")
    name = names[-1]
    rows = []
    for row in table.rows:
        if len(row) < 3 or _normal(row[1]) == "commitment":
            continue
        commitment = clean(row[1]).lower()
        contract, months = TERMS.get(commitment, ("other", None))
        price = _price(row[2], per_gpu_column=True)
        if price is None:
            continue
        listing = _listing(
            meta,
            label=name,
            gpus=1,
            vram=None,
            price=price,
            contract=contract,
            months=months,
            sku=f"ladder|{name}|{row[0].lower()}|{commitment}",
        )
        if listing:
            rows.append(listing)
    return rows


def _has_prices_for_chips(table: Table) -> bool:
    text = " ".join(cell for row in table.rows for cell in row)
    return "$" in text and CHIP_NAME.search(text) is not None


def _route(table: Table, meta: dict) -> list[Listing]:
    header = {_normal(h) for h in table.headers}
    flat = " ".join(cell.lower() for row in table.rows[:2] for cell in row)
    if "savings on gpu" in header:
        return []
    if {"6 months", "1 year", "3 year"} <= header:
        return _term_table(table, meta)
    if "per hour price" in header and "term" in header:
        return _cluster_table(table, meta)
    if "commitment" in header or "commitment" in flat:
        return _ladder_table(table, meta)
    has_vram = header & {"vram per gpu", "vram/gpu"}
    if (has_vram and any(h.startswith(("price", "20")) for h in header)) or (
        "on-demand price" in header
    ):
        return _instance_table(table, meta)
    if _has_prices_for_chips(table):
        raise LayoutError(f"unknown table: {table.headers}")
    return []


def _early_prices(html: str, meta: dict) -> list[Listing]:
    rows = []
    for gpus, name, price in EARLY_PRICE.findall(page_text(html)):
        listing = _listing(
            meta,
            label=f"NVIDIA {name}",
            gpus=int(gpus),
            vram=16 if name == "V100" else None,
            price=(float(price), False),
            contract="on_demand",
            months=None,
        )
        if listing:
            rows.append(listing)
    return rows


def parse(html: str, meta: dict) -> list[Listing]:
    if LexborHTMLParser(html).css_first("tr[data-plan]") is not None:
        config = meta["lambda_config"]
        rows = parse_pricing(
            html,
            plans=config["plans"],
            ignore=config["ignore"],
            retrieved_at=meta["retrieved_at"],
            source_url=meta["source_url"],
            raw_file=meta["raw_file"],
            collector="wayback",
            skip_commitments=True,
        )
        for table in read_tables(html):
            if "commitment" in {_normal(h) for h in table.headers}:
                rows += _ladder_table(table, meta)
        return rows
    tables = read_tables(html)
    rows = [row for table in tables for row in _route(table, meta)]
    return rows or (_early_prices(html, meta) if not tables else [])
