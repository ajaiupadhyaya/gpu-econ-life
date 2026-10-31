"""Parse archived Paperspace pricing pages.

www.paperspace.com/pricing has no tables. Its machine prices are cards, and only the Hourly tab of
the CORE product is read: Gradient, Workstream, the Monthly tab and "effective hourly" figures are
other products or monthly plans. Blocks with the class `hide` are not on the page as a reader sees
it. That matters most on the H100 card, which keeps a hidden copy of the A100 card's price and specs
from December 2022 on. The 2020 page toggles hourly and monthly prices with the class `hidden`, so
there the hourly span is the one to read, and its Gradient instance types are left out.

A starred price is a commitment, with the term stated in a footnote. A star with no matching
footnote raises rather than passing for on-demand. The H100 on-demand price exists only in that
footnote, and is marked in `sku` as a promo where the page says so.

docs.digitalocean.com's pricing page has tables. Multi-GPU rows are whole-machine prices. From
November 2024 those tables drop their GPU count, so those rows are left out, not divided.

Chip identity comes from the row's own name, and a page that does not settle it gets no row: A100
needs a stated memory and H100 needs a stated form factor. "HGX" is read as SXM, because HGX boards
carry SXM modules. Specs naming a different chip from the card raise.
"""

import re

from selectolax.lexbor import LexborHTMLParser

from gel.parse.errors import LayoutError
from gel.parse.tables import Table, clean, page_text, read_tables
from gel.schema import Listing

UNREAD = 'script,style,noscript,s,del,strike,[style*="line-through"]'
CHIP_NAME = re.compile(r"V100|A100|H100|H200|B200|MI300|L40S")
OUT_OF_SCOPE = re.compile(
    r"^(?:GPU\+|M4000|[PA][456]000|RTX[45]000|C\d+$|Air\+?$|Standard$|Advanced$|Pro$)"
)
NAMED_MEMORY = {"V100-32G": 32, "A100-80G": 80}
A100_CHIPS = {40: "a100_40gb", 80: "a100_80gb"}
ANY_PRICE = re.compile(r"\$\s?\d")
CARD_PRICE = re.compile(r"^\$ ?(\d+(?:\.\d+)?)(\*{0,2}) ?/ ?hour$")
LEGACY_PRICE = re.compile(r"^(\d+(?:\.\d+)?) ?/ ?hour$")
TABLE_PRICE = re.compile(r"^\$(\d+(?:\.\d+)?)/(?:hr|hour)$")
COMMITMENT = re.compile(
    r"(\*+)\$(\d+(?:\.\d+)?)/ ?hour pricing is for a (\d+)-(year|month) commitment"
)
ON_DEMAND = re.compile(
    r"On-demand pricing for H100 is \$(\d+(?:\.\d+)?)(?:/| per )hour"
    r"( under our special promo price)?"
)
VCPUS = re.compile(r"(\d+) (?:x )?v?CPU")
RAM = re.compile(r"(\d+) ?GB RAM")
GPU_MEMORY = re.compile(r"(\d+) ?GB GPU")


def _chip(name: str, memory: int | None, hgx: bool) -> str | None:
    """Return the chip id, or None where the page does not settle it."""
    if name in ("V100", "V100-32G"):
        return "v100"
    if name in ("A100", "A100-80G"):
        if memory is None:
            return None
        if memory not in A100_CHIPS:
            raise LayoutError(f"A100 with unreadable memory: {name} {memory}")
        return A100_CHIPS[memory]
    if name == "H100":
        return "h100_sxm" if hgx else None
    raise LayoutError(f"unknown GPU name: {name!r}")


def _listing(
    meta: dict,
    name: str,
    price: float,
    *,
    gpus: int = 1,
    memory: int | None = None,
    hgx: bool = False,
    contract: str = "on_demand",
    months: int | None = None,
    vcpus: int | None = None,
    ram: int | None = None,
    region: str = "unspecified",
    promo: bool = False,
) -> Listing | None:
    memory = NAMED_MEMORY.get(name, memory)
    chip = _chip(name, memory, hgx)
    if chip is None:
        return None
    label = f"{gpus}x {name} HGX" if hgx else f"{gpus}x {name}"
    parts = [label, f"{memory}GB" if memory else "", "promo" if promo else ""]
    return Listing.from_instance_price(
        price=price,
        gpu_count=gpus,
        retrieved_at=meta["retrieved_at"],
        provider="paperspace",
        provider_type="neocloud",
        collector="wayback",
        sku="|".join(part for part in parts if part),
        chip=chip,
        gpu_memory_gb=memory,
        interconnect=None,
        region=region,
        contract_type=contract,
        term_months=months,
        vcpus=vcpus,
        ram_gb=ram,
        source_url=meta["source_url"],
        raw_file=meta["raw_file"],
    )


def _spec(pattern: re.Pattern, text: str) -> int | None:
    match = pattern.search(text)
    return int(match.group(1)) if match else None


def _from_specs(specs: list[str]) -> dict:
    text = " ".join(specs)
    return {
        "memory": _spec(GPU_MEMORY, text),
        "vcpus": _spec(VCPUS, text),
        "ram": _spec(RAM, text),
    }


def _term(count: str, unit: str) -> tuple[str, int]:
    months = int(count) * (12 if unit == "year" else 1)
    return {12: "reserved_1y", 36: "reserved_3y"}.get(months, "other"), months


def _commitments(text: str) -> dict[tuple[str, str], tuple[str, int]]:
    """Map each footnote's stars and price to the term it states."""
    return {
        (stars, price): _term(count, unit) for stars, price, count, unit in COMMITMENT.findall(text)
    }


def _card(card, name: str, footnotes: str, meta: dict) -> list[Listing]:
    prices = card.css('h1[class^="instance-price"]')
    if not prices:
        return []
    if len(prices) > 1:
        raise LayoutError(f"{name} card shows {len(prices)} prices")
    specs = [clean(spec.text(separator=" ")) for spec in card.css('p[class^="instance-specs"]')]
    other_chips = set(CHIP_NAME.findall(" ".join(specs))) - {name.split("-")[0]}
    if other_chips:
        raise LayoutError(f"{name} card lists {sorted(other_chips)} in its specs")
    shown = clean(prices[0].parent.text(separator=" "))
    match = CARD_PRICE.match(shown)
    if not match:
        raise LayoutError(f"unreadable price: {shown!r}")
    amount, stars = match.groups()
    contract, months = "on_demand", None
    if stars:
        terms = _commitments(footnotes)
        if (stars, amount) not in terms:
            raise LayoutError(f"{name} ${amount}{stars} has no matching footnote")
        contract, months = terms[(stars, amount)]
    fields = {**_from_specs(specs), "hgx": "HGX" in " ".join(specs)}
    rows = [_listing(meta, name, float(amount), contract=contract, months=months, **fields)]
    note = ON_DEMAND.search(footnotes)
    if name == "H100" and note:
        rows.append(_listing(meta, name, float(note[1]), promo=note[2] is not None, **fields))
    return [row for row in rows if row]


def _cards(pane, titles: list, meta: dict) -> list[Listing]:
    footnotes = clean(pane.text(separator=" "))
    if "on-demand pricing" in footnotes.lower() and not ON_DEMAND.search(footnotes):
        raise LayoutError("unreadable On-demand footnote")
    rows = []
    for title in titles:
        name = clean(title.text())
        if not OUT_OF_SCOPE.match(name):
            rows += _card(title.parent, name, footnotes, meta)
    return rows


def _hourly_pane(tree: LexborHTMLParser):
    for pane in tree.css("div.w-tab-pane"):
        if any(clean(h.text()) == "CORE" for h in pane.css("h1.product-featured-core-text")):
            return pane.css_first('div.w-tab-pane[data-w-tab="Hourly"]')
    return None


def _legacy(tree: LexborHTMLParser, meta: dict) -> list[Listing]:
    """The boxes with class vmTypeBox2 are the Gradient instance types, a different product."""
    rows = []
    for block in tree.css("div.pricingBlock:not(.vmTypeBox2)"):
        spans = block.css("span.bigPrice.hourlyOnly")
        if not spans:
            continue
        name = clean(block.css_first("h3.title").text())
        if OUT_OF_SCOPE.match(name):
            continue
        shown = clean(spans[0].text(separator=" "))
        match = LEGACY_PRICE.match(shown)
        if len(spans) > 1 or not match:
            raise LayoutError(f"unreadable price: {shown!r}")
        specs = [clean(item.text(separator=" ")) for item in block.css("div.specs li")]
        rows.append(_listing(meta, name, float(match.group(1)), **_from_specs(specs)))
    return [row for row in rows if row]


def _is_gpu_table(table: Table) -> bool:
    priced = "price" in " ".join(table.headers).lower()
    return any(
        CHIP_NAME.search(row[0])
        and not row[0].startswith("Free")
        and (priced or "$" in " ".join(row))
        for row in table.rows
    )


def _columns(table: Table) -> dict[str, int]:
    return {clean(header).lower(): i for i, header in enumerate(table.headers)}


def _table_price(text: str) -> float:
    match = TABLE_PRICE.match(text)
    if not match:
        raise LayoutError(f"unreadable price: {text!r}")
    return float(match.group(1))


def _one_gpu_rows(table: Table, columns: dict[str, int], meta: dict) -> list[Listing]:
    named = {"memory": "gpu (gb)", "vcpus": "vcpus", "ram": "cpu ram (gb)"}
    named = {field: columns[column] for field, column in named.items() if column in columns}
    rows = []
    for row in table.rows:
        if OUT_OF_SCOPE.match(row[0]):
            continue
        fields = {field: int(row[i]) for field, i in named.items()}
        if "regions" in columns:
            fields["region"] = row[columns["regions"]]
        rows.append(_listing(meta, row[0], _table_price(row[columns["price (hourly)"]]), **fields))
    return [row for row in rows if row]


def _counted_rows(
    table: Table, columns: dict[str, int], memory: dict[str, int], meta: dict
) -> list[Listing]:
    rows = []
    for row in table.rows:
        if OUT_OF_SCOPE.match(row[0]):
            continue
        price = _table_price(row[columns["price (hourly)"]])
        gpus = int(row[columns["gpus"]])
        rows.append(_listing(meta, row[0], price, gpus=gpus, memory=memory.get(row[0])))
    return [row for row in rows if row]


def _stated_memory(tables: list[Table]) -> dict[str, int]:
    """The multi-GPU table names its machines, and the table before it gives their memory."""
    memory = {}
    for table in tables:
        column = _columns(table).get("gpu (gb)")
        if column is not None:
            memory |= {row[0]: int(row[column]) for row in table.rows}
    return memory


def _docs(tables: list[Table], meta: dict) -> list[Listing]:
    memory = _stated_memory(tables)
    rows = []
    for table in tables:
        columns = _columns(table)
        if "name" in columns and "price (hourly)" in columns:
            rows += _one_gpu_rows(table, columns, meta)
        elif "gpus" in columns:
            rows += _counted_rows(table, columns, memory, meta)
        elif "machine" not in columns:
            raise LayoutError(f"unknown table: {table.headers}")
    return rows


def parse(html: str, meta: dict) -> list[Listing]:
    tree = LexborHTMLParser(html)
    for node in tree.css(UNREAD):
        node.decompose()
    tables = [table for table in read_tables(tree.html) if _is_gpu_table(table)]
    if tables:
        return _docs(tables, meta)
    if tree.css_first("span.bigPrice.hourlyOnly") is not None:
        return _legacy(tree, meta)
    pane = _hourly_pane(tree)
    if pane is not None:
        for node in pane.css(".hide"):
            node.decompose()
        titles = pane.css('h1[class^="instance-names"]')
        if titles:
            return _cards(pane, titles, meta)
    text = page_text(tree.html)
    if CHIP_NAME.search(text) and ANY_PRICE.search(text):
        raise LayoutError("unknown layout holding chip prices")
    return []
