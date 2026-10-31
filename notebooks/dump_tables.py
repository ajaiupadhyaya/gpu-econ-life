"""Exploration only: print the tables in one snapshot.

uv run python notebooks/dump_tables.py path/to/snapshot.html
"""

import sys

from selectolax.lexbor import LexborHTMLParser

for path in sys.argv[1:]:
    with open(path, "rb") as f:
        tree = LexborHTMLParser(f.read().decode("utf-8", "ignore"))
    print("#####", path.split("pages/")[1])
    for i, table in enumerate(tree.css("table")):
        print(f"--- table {i}")
        for row in table.css("tr"):
            cells = [" ".join(c.text(separator=" ").split()) for c in row.css("th,td")]
            print(" | ".join(c[:34] for c in cells)[:150])
