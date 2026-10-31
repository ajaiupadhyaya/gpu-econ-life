"""Parse Lambda's public pricing page.

Instance tables sit in tabs labelled 8x, 4x, 2x and 1x, so GPU count comes from the tab. Cluster
tables state their own GPU count and a duration range. An unknown plan or layout raises.
"""

import re

from selectolax.lexbor import LexborHTMLParser

from gel.parse.errors import LayoutError
from gel.schema import Listing

PRICE = re.compile(r"^\$(\d+(?:\.\d+)?)$")
TAB_COUNT = re.compile(r"^(\d+)x$")
NOT_OFFERED = {"—", "–", "-"}


def _cells(row) -> dict[str, str]:
    return {c.attributes["data-label"]: c.text(strip=True) for c in row.css("[data-label]")}


def _price_cell(cells: dict[str, str]) -> str:
    labels = ("PRICE/GPU/HR", "PRICE PER HOUR")
    return next((v for k, v in cells.items() if k.upper().startswith(labels)), "")


def _not_offered(cells: dict[str, str]) -> bool:
    """The page shows a dash where a plan is not sold in that tab's size."""
    return _price_cell(cells) in NOT_OFFERED


def _price(cells: dict[str, str]) -> float:
    raw = _price_cell(cells)
    match = PRICE.match(raw)
    if not match:
        raise LayoutError(f"unreadable price: {raw!r}")
    return float(match.group(1))


def _chip(plan: str, vram: int | None, plans: dict) -> str:
    spec = plans.get(plan)
    if spec is None:
        raise LayoutError(f"unknown plan: {plan}")
    if "chip" in spec:
        return spec["chip"]
    if vram not in spec["by_vram"]:
        raise LayoutError(f"{plan}: no chip for {vram} GB")
    return spec["by_vram"][vram]


def _leading_number(text: str) -> float:
    match = re.match(r"[\d,.]+", text)
    if not match:
        raise LayoutError(f"expected a number: {text!r}")
    return float(match.group(0).replace(",", ""))


def parse_pricing(
    html: str,
    *,
    plans: dict,
    ignore: list,
    retrieved_at: str,
    source_url: str,
    raw_file: str,
    collector: str = "lambda",
    skip_commitments: bool = False,
) -> list[Listing]:
    tree = LexborHTMLParser(html)
    labels = {b.attributes.get("id"): b.text(strip=True) for b in tree.css('[role="tab"]')}
    common = dict(
        retrieved_at=retrieved_at,
        provider="lambda",
        provider_type="neocloud",
        collector=collector,
        interconnect=None,
        region="unspecified",
        source_url=source_url,
        raw_file=raw_file,
    )
    rows = []
    for panel in tree.css("[aria-labelledby]"):
        label = labels.get(panel.attributes["aria-labelledby"], "")
        for row in panel.css("tr[data-plan]"):
            plan = row.attributes["data-plan"]
            if plan in ignore:
                continue
            cells = _cells(row)
            if _not_offered(cells) or (skip_commitments and "Commitment" in cells):
                continue
            if "VRAM/GPU" in cells:
                count = TAB_COUNT.match(label)
                if not count:
                    raise LayoutError(f"instance table under unexpected tab: {label!r}")
                gpus = int(count.group(1))
                vram = int(_leading_number(cells["VRAM/GPU"]))
                rows.append(
                    Listing.from_gpu_price(
                        price=_price(cells),
                        gpu_count=gpus,
                        sku=f"{gpus}x|{plan}|{vram}GB",
                        chip=_chip(plan, vram, plans),
                        gpu_memory_gb=vram,
                        contract_type="on_demand",
                        term_months=None,
                        vcpus=int(_leading_number(cells["vCPUs"])),
                        ram_gb=_leading_number(cells["RAM"]),
                        **common,
                    )
                )
            elif "DURATION" in {k.upper() for k in cells}:
                cells = {k.upper(): v for k, v in cells.items()}
                raw_count = cells["GPU COUNT"]
                rows.append(
                    Listing.from_gpu_price(
                        price=_price(cells),
                        gpu_count=int(_leading_number(raw_count)),
                        sku=f"1cc|{cells['DURATION']}|{raw_count}",
                        chip=_chip(plan, None, plans),
                        gpu_memory_gb=None,
                        contract_type="other",
                        term_months=None,
                        vcpus=None,
                        ram_gb=None,
                        **common,
                    )
                )
            else:
                raise LayoutError(f"unrecognized table columns: {sorted(cells)}")
    if not rows:
        raise LayoutError("no rows found on the pricing page")
    return rows
