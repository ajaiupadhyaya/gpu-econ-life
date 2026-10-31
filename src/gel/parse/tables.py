"""Read HTML tables, with the text just before each one, for the archived-page parsers."""

from dataclasses import dataclass

from selectolax.lexbor import LexborHTMLParser

BEFORE_CHARS = 300


@dataclass
class Table:
    headers: list[str]
    rows: list[list[str]]
    before: str


def clean(text: str | None) -> str:
    return " ".join((text or "").split())


def _text_before(node) -> str:
    """Walk backwards through earlier siblings and ancestors for nearby heading text."""
    words: list[str] = []
    length = 0
    while node is not None and length < BEFORE_CHARS:
        sibling = node.prev
        while sibling is not None and length < BEFORE_CHARS:
            text = clean(sibling.text(separator=" "))
            if text:
                words.insert(0, text)
                length += len(text)
            sibling = sibling.prev
        node = node.parent
    return " ".join(words)[-BEFORE_CHARS:]


def read_tables(html: str) -> list[Table]:
    tree = LexborHTMLParser(html)
    for node in tree.css("script,style,noscript"):
        node.decompose()
    tables = []
    for node in tree.css("table"):
        rows = [
            [clean(cell.text(separator=" ")) for cell in row.css("th,td")] for row in node.css("tr")
        ]
        rows = [row for row in rows if row]
        if rows:
            tables.append(Table(headers=rows[0], rows=rows[1:], before=_text_before(node)))
    return tables


def page_text(html: str) -> str:
    tree = LexborHTMLParser(html)
    for node in tree.css("script,style,noscript"):
        node.decompose()
    return clean(tree.body.text(separator=" ") if tree.body else "")
