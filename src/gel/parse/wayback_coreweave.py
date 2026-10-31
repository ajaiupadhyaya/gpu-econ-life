"""Parse archived CoreWeave pricing pages.

Which price a page quotes depends on its layout, so each reader sets price_basis from what that
layout says. The docs resource tables and the 2022-24 grid sell a GPU a la carte: "the total
instance cost is a combination of a GPU component, the number of vCPU, and the amount of RAM", so
those rows are accelerator_only, per GPU, and the grid's maximum vCPUs and RAM are limits rather
than included resources. The 2020 table lists the vCPUs and RAM that come with its $/GPU/Hour and
sells "additional" cores on top, and the 2025 pages and docs quote "Instance Price" with a GPU
count, so those rows are instance.

A label decides the chip. A100 needs its memory on the row, and H100 needs HGX, SXM or PCIe. A few
rows are known to state neither and are left out. An unknown table, label, column or price raises.
Nothing the page hides is read, and the hidden CMS copies of the old component rates in the 2025
tables are ignored. "Up to 60%" offers and the "starting at" banner are not prices, and the
inference-only per-GPU column is limited to one class of customer, so none of them become rows.
"""

import re

from selectolax.lexbor import LexborHTMLParser

from gel.parse.errors import LayoutError
from gel.parse.tables import Table, clean, read_tables
from gel.schema import Listing

CHIP_NAME = re.compile(r"V100|A100|H100|(?<!G)H200|(?<!G)B200|L40S|MI300X", re.I)
ANY_PRICE = re.compile(r"\$\s?\d")
PRICE = re.compile(r"^\$(\d[\d,]*(?:\.\d+)?)$")
NO_PRICE = re.compile(r"^(|n/a|contact sales|contact us|contact us for pricing)$", re.I)
OUT_OF_SCOPE = re.compile(r"RTX|QUADRO|\bA40\b|\bP100\b|\bL40\b|GH200|GB200|GB300|\bB300\b", re.I)
MEMORY = re.compile(r"(\d+)\s*GB", re.I)
INTERCONNECTS = {"NVLINK": "NVLINK", "PCIE": "PCIe", "INFINIBAND": "InfiniBand"}
# Docs instance rows that state no A100 memory or H100 form factor anywhere on the page.
UNSTATED = {"A100", "H100 (InfiniBand)"}
RESOURCE_HEADING = "GPU Instance Resource Pricing"
RESOURCE_KINDS = {"GPU", "CPU", "RAM"}
RESOURCE_END = "An example"
CARD_PRICE = re.compile(r"\$(\d[\d,]*(?:\.\d+)?)\s*/\s*Hour", re.I)
REGION = re.compile(r"^REGION:\s*(.+)$", re.I)
GRID_PRICES = {
    "instance price (per hour)": ("on_demand", "list"),
    "on-demand price (per hour)": ("on_demand", "list"),
    "spot price (per hour)": ("spot", "spot"),
}
# "Pricing based on GPUs is exclusively applicable to the CoreWeave inference platform customers."
GRID_IGNORED = {"inference single gpu price(per hour)²"}
GRID_SPECS = {
    "gpu model",
    "gpu count",
    "vram (gb)",
    "vcpus",
    "system ram (gb)",
    "local storage (tb)",
}
OTHER_GRIDS = {"cpu model", "product", "offering", "dx speed"}


def _normal(text: str) -> str:
    return clean(text).lower()


def _text(node) -> str:
    return clean(node.text(separator=" ")) if node is not None else ""


def _price(text: str) -> float | None:
    """Return a dollar amount, or None where the page gives no price."""
    text = clean(text)
    if NO_PRICE.match(text):
        return None
    match = PRICE.match(text)
    if not match:
        raise LayoutError(f"unreadable price: {text!r}")
    return float(match.group(1).replace(",", ""))


def _memory(*texts: str) -> int | None:
    stated = {int(value) for text in texts for value in MEMORY.findall(text)}
    if len(stated) > 1:
        raise LayoutError(f"conflicting memory: {texts}")
    return stated.pop() if stated else None


def _number(text: str) -> float | None:
    text = text.replace(",", "").strip()
    return float(text) if re.fullmatch(r"\d+(\.\d+)?", text) else None


def _chip(label: str, memory: int | None) -> str | None:
    """Return the chip a label states, None if out of scope. Assume nothing it does not state."""
    upper = label.upper()
    if OUT_OF_SCOPE.search(upper):
        return None
    if "V100" in upper:
        return "v100"
    if "A100" in upper:
        chips = {40: "a100_40gb", 80: "a100_80gb"}
        if memory not in chips:
            raise LayoutError(f"A100 with unreadable memory: {label} {memory}")
        return chips[memory]
    if "H100" in upper:
        if "PCIE" in upper:
            return "h100_pcie"
        if "HGX" in upper or "SXM" in upper:
            return "h100_sxm"
        raise LayoutError(f"H100 with no stated form factor: {label}")
    if "H200" in upper:
        return "h200"
    if "B200" in upper:
        return "b200"
    if "L40S" in upper:
        return "l40s"
    if "MI300X" in upper:
        return "mi300x"
    raise LayoutError(f"unknown GPU label: {label}")


def _interconnect(label: str) -> str | None:
    upper = label.upper()
    return next((name for key, name in INTERCONNECTS.items() if key in upper), None)


def _listing(
    meta: dict,
    *,
    label: str,
    chip: str,
    price: float,
    basis: str,
    sku: str,
    gpus: int = 1,
    memory: int | None = None,
    contract: str = "on_demand",
    kind: str = "list",
    vcpus: float | None = None,
    ram: float | None = None,
    region: str = "unspecified",
) -> Listing:
    build = Listing.from_gpu_price if basis == "accelerator_only" else Listing.from_instance_price
    return build(
        price=price,
        gpu_count=gpus,
        retrieved_at=meta["retrieved_at"],
        provider="coreweave",
        provider_type="neocloud",
        collector="wayback",
        sku=sku,
        chip=chip,
        gpu_memory_gb=memory,
        interconnect=_interconnect(label),
        region=region,
        contract_type=contract,
        term_months=None,
        vcpus=int(vcpus) if vcpus else None,
        ram_gb=ram,
        price_kind=kind,
        price_basis=basis,
        source_url=meta["source_url"],
        raw_file=meta["raw_file"],
    )


def _component(meta: dict, description: str, resource: str, cost: str, vram: str) -> Listing | None:
    """One row of a docs resource table, whichever way the page drew it."""
    resource = re.sub(r"\s*_\s*", "_", resource)
    memory = _memory(description, resource, vram)
    price = _price(cost)
    chip = _chip(f"{description} {resource}", memory)
    if price is None or chip is None:
        return None
    return _listing(
        meta,
        label=f"{description} {resource}",
        chip=chip,
        price=price,
        basis="accelerator_only",
        sku=f"component|{description}|{resource}",
        memory=memory,
    )


def _component_table(table: Table, meta: dict) -> list[Listing]:
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    label = columns.get("resource label", columns.get("label"))
    if label is None:
        raise LayoutError(f"unknown table: {table.headers}")
    rows = []
    for row in table.rows:
        if "type" in columns and row[columns["type"]] != "GPU":
            continue
        listing = _component(
            meta,
            row[columns["description"]],
            row[label],
            row[columns["cost per hour"]],
            row[columns["vram"]],
        )
        if listing:
            rows.append(listing)
    return rows


def _bundled_table(table: Table, meta: dict) -> list[Listing]:
    """The 2020 table: one GPU with the vCPUs and RAM its row lists."""
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    rows = []
    for row in table.rows:
        label, vram = row[columns["gpu type"]], row[columns["vram"]]
        memory = _memory(vram)
        chip = _chip(label, memory)
        price = _price(row[columns["$/gpu/hour"]])
        if chip is None or price is None:
            continue
        rows.append(
            _listing(
                meta,
                label=label,
                chip=chip,
                price=price,
                basis="instance",
                sku=f"bundle|{label}",
                memory=memory,
                vcpus=_number(row[columns["vcpu"]]),
                ram=_number(row[columns["ram (gb)"]]),
            )
        )
    return rows


def _instance_table(table: Table, meta: dict) -> list[Listing]:
    """The docs page from 2025: a whole instance, with its GPU count beside it."""
    columns = {_normal(h): i for i, h in enumerate(table.headers)}
    instance = columns.get("instance id", columns.get("instance"))
    if instance is None:
        raise LayoutError(f"unknown table: {table.headers}")
    rows = []
    for row in table.rows:
        label = row[columns["gpu"]]
        if label in UNSTATED:
            continue
        chip = _chip(label, _memory(label))
        price = _price(row[columns["cost per hour"]])
        if chip is None or price is None:
            continue
        count = row[columns["gpu count"]]
        if not count.isdigit():
            raise LayoutError(f"unreadable GPU count: {label} {count!r}")
        rows.append(
            _listing(
                meta,
                label=label,
                chip=chip,
                price=price,
                basis="instance",
                sku=f"{count}x {label}|{row[instance]}",
                gpus=int(count),
                memory=_memory(label),
            )
        )
    return rows


def _has_prices_for_chips(table: Table) -> bool:
    text = " ".join(cell for row in table.rows for cell in row)
    return ANY_PRICE.search(text) is not None and CHIP_NAME.search(text) is not None


def _route(table: Table, meta: dict) -> list[Listing]:
    header = {_normal(h) for h in table.headers}
    if "$/gpu/hour" in header and {"vcpu", "ram (gb)"} <= header:
        return _bundled_table(table, meta)
    if {"description", "cost per hour", "vram"} <= header:
        return _component_table(table, meta)
    if {"gpu", "gpu count", "cost per hour"} <= header:
        return _instance_table(table, meta)
    if "unit cost per hour" in header:
        return []  # A billing example that repeats the unit price from the table above it.
    if _has_prices_for_chips(table):
        raise LayoutError(f"unknown table: {table.headers}")
    return []


def _resource_divs(lines: list[str], meta: dict) -> list[Listing]:
    """GitBook drew the resource table in divs from late 2021 to late 2022, a flat run of text."""
    start = lines.index("VRAM", lines.index(RESOURCE_HEADING))
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if line.startswith(RESOURCE_END):
            break
        if line in RESOURCE_KINDS:
            rows.append([line])
        elif rows:
            rows[-1].append(line)
    listings = []
    for row in rows:
        if row[0] != "GPU":
            continue
        cost = next((i for i, cell in enumerate(row) if cell.startswith("$")), None)
        if cost is None or cost < 3:
            raise LayoutError(f"resource row with no price: {row}")
        listing = _component(
            meta, row[1], "".join(row[2:cost]), row[cost], " ".join(row[cost + 1 :])
        )
        if listing:
            listings.append(listing)
    return listings


def _card_prices(tree: LexborHTMLParser) -> dict[str, float]:
    prices = {}
    for card in tree.css(".pricing-card"):
        link = card.css_first("a")
        price = CARD_PRICE.search(_text(card))
        if link is not None and price:
            prices[_text(link)] = float(price.group(1).replace(",", ""))
    return prices


def _component_grid(tree: LexborHTMLParser, meta: dict) -> list[Listing]:
    """The 2022-24 grid. A row whose mobile card quotes another price cannot be read either way."""
    grids = [n for n in tree.css(".desktop") if "GPU Model" in _text(n.css_first(".table-header"))]
    if len(grids) != 1:
        raise LayoutError(f"price grid with {len(grids)} GPU tables")
    head = _text(grids[0].css_first(".table-header"))
    if "GPU Component" not in head:
        raise LayoutError(f"price grid with no GPU Component column: {head}")
    cards = _card_prices(tree)
    rows = []
    for row in grids[0].css(".table-body-row"):
        cells = [_text(cell) for cell in row.css(".w-col")]
        if len(cells) != 5:
            raise LayoutError(f"grid row with {len(cells)} cells: {cells}")
        label, vram, _, _, cost = cells
        reserve = cost.endswith("Reserve Now")
        price = _price(cost.removesuffix("Reserve Now"))
        memory = _memory(label, f"{vram} GB")
        chip = _chip(label, memory)
        if price is None or chip is None or cards.get(label, price) != price:
            continue
        rows.append(
            _listing(
                meta,
                label=label,
                chip=chip,
                price=price,
                basis="accelerator_only",
                sku=f"component|{label}" + ("|reserve now" if reserve else ""),
                memory=memory,
            )
        )
    return rows


def _region(table) -> str:
    """A 2026 table has a heading such as REGION: EUROPE directly above it."""
    node = table.prev
    while node is not None and not _text(node):
        node = node.prev
    match = REGION.match(_text(node))
    return re.sub(r"\W+", "_", match.group(1).strip().lower()) if match else "unspecified"


def _instance_grid(table, head: list[str], meta: dict) -> list[Listing]:
    unknown = set(head) - GRID_SPECS - set(GRID_PRICES) - GRID_IGNORED
    if unknown or not set(head) & set(GRID_PRICES):
        raise LayoutError(f"unknown column in GPU table: {unknown or head}")
    columns = {name: i for i, name in enumerate(head)}
    prices = [(columns[name], kind) for name, kind in GRID_PRICES.items() if name in columns]
    region = _region(table)
    rows = []
    for row in table.css('[role="listitem"]'):
        cells = [_text(cell) for cell in row.css(".table-v2-cell")]
        if len(cells) != len(head):
            raise LayoutError(f"grid row with {len(cells)} cells: {cells}")
        label, count = cells[columns["gpu model"]], cells[columns["gpu count"]]
        priced = [(_price(cells[i]), kind) for i, kind in prices]
        priced = [(price, kind) for price, kind in priced if price is not None]
        if not priced:
            continue
        if not count and not CHIP_NAME.search(label):
            continue  # The CMS lists CPUs here too, and the page hides them.
        vram = cells[columns["vram (gb)"]]
        memory = _memory(label, f"{vram} GB")
        chip = _chip(label, memory)
        if chip is None:
            continue
        if not count.isdigit():
            raise LayoutError(f"unreadable GPU count: {label} {count!r}")
        for price, (contract, kind) in priced:
            rows.append(
                _listing(
                    meta,
                    label=label,
                    chip=chip,
                    price=price,
                    basis="instance",
                    sku=f"{count}x {label}" + ("|spot" if kind == "spot" else ""),
                    gpus=int(count),
                    memory=memory,
                    contract=contract,
                    kind=kind,
                    vcpus=_number(cells[columns["vcpus"]]),
                    ram=_number(cells[columns["system ram (gb)"]]),
                    region=region,
                )
            )
    return rows


def _instance_grids(tree: LexborHTMLParser, meta: dict) -> list[Listing]:
    rows = []
    for table in tree.css(".table-v2"):
        head = [_normal(_text(cell)) for cell in table.css(".table-v2-header .table-v2-cell")]
        if head and head[0] == "gpu model":
            rows += _instance_grid(table, head, meta)
        elif head and head[0] in OTHER_GRIDS:
            continue
        else:
            text = _text(table)
            if ANY_PRICE.search(text) and CHIP_NAME.search(text):
                raise LayoutError(f"unknown table: {head}")
    return rows


def parse(html: str, meta: dict) -> list[Listing]:
    tree = LexborHTMLParser(html)
    for node in tree.css("script,style,noscript,.w-condition-invisible"):
        node.decompose()
    text = tree.body.text(separator="\n") if tree.body else ""
    lines = [clean(line) for line in text.split("\n")]
    lines = [line for line in lines if line]
    if tree.css_first(".table-v2") is not None:
        rows = _instance_grids(tree, meta)
    elif tree.css_first(".pricing-card, .table-body-row") is not None:
        rows = _component_grid(tree, meta)
    elif tree.css_first("table") is not None:
        rows = [row for table in read_tables(html) for row in _route(table, meta)]
    elif RESOURCE_HEADING in lines:
        rows = _resource_divs(lines, meta)
    else:
        rows = []
    flat = " ".join(lines)
    if not rows and ANY_PRICE.search(flat) and CHIP_NAME.search(flat):
        raise LayoutError("unknown layout: chip names and prices but no rows")
    return rows
