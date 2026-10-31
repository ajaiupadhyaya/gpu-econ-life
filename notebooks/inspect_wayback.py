"""Exploration only: summarize what each downloaded snapshot holds, to plan the parsers.

uv run python notebooks/inspect_wayback.py lambda
"""

import re
import sys
from collections import Counter
from pathlib import Path

from selectolax.lexbor import LexborHTMLParser

provider = sys.argv[1]
root = Path("data/raw/wayback/pages") / provider
signatures = Counter()
for slug in sorted(p for p in root.iterdir() if p.is_dir()):
    print("==", slug.name)
    for path in sorted(slug.glob("*.html")):
        tree = LexborHTMLParser(path.read_bytes().decode("utf-8", "ignore"))
        for node in tree.css("script,style,noscript"):
            node.decompose()
        text = " ".join((tree.body.text(separator=" ") if tree.body else "").split())
        prices = re.findall(r"\$\s?\d[\d,]*(?:\.\d+)?", text)
        chips = sorted(set(re.findall(r"\b(V100|A100|H100|H200|B200)\b", text)))
        tables = len(tree.css("table"))
        rows = len(tree.css("tr"))
        print(f"{path.stem[:6]} tables={tables:2} tr={rows:3} prices={len(prices):3} chips={chips}")
