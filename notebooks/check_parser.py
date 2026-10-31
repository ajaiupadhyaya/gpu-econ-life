"""Exploration only: run one provider's parser over every snapshot, writing nothing.

uv run python notebooks/check_parser.py coreweave
"""

import csv
import sys
from collections import Counter
from pathlib import Path

import polars as pl
import yaml

from gel.collect.wayback_snapshots import SELECTION_PATH
from gel.parse.wayback import PARSERS, _parse_one
from gel.schema import to_frame

provider = sys.argv[1]
root = Path(".")
config = yaml.safe_load((root / "config/skus.yaml").read_text())
with (root / SELECTION_PATH).open() as f:
    rows = [r for r in csv.DictReader(f) if r["provider"] == provider]
statuses, details, listings, empties = Counter(), Counter(), [], []
for row in rows:
    found, status, detail = _parse_one(row, root, PARSERS, config)
    statuses[status] += 1
    listings += found
    if detail:
        details[detail[:100]] += 1
    if status == "empty":
        empties.append((row["month"], row["url"]))
print(dict(statuses), len(listings), "rows")
for detail, count in details.most_common(15):
    print(count, detail)
print("empty:", empties)
if listings:
    frame = to_frame(listings).with_columns(pl.col("retrieved_at").str.slice(0, 7).alias("month"))
    pl.Config.set_tbl_rows(80)
    pl.Config.set_tbl_width_chars(120)
    print(frame.group_by("contract_type", "price_basis").len().sort("contract_type"))
    print(
        frame.group_by("month", "chip", "contract_type")
        .agg(pl.col("price_usd_per_gpu_hour").min().round(3).alias("low"))
        .sort("chip", "contract_type", "month")
        .group_by("chip", "contract_type", "low", maintain_order=True)
        .agg(
            pl.col("month").min().alias("from"),
            pl.col("month").max().alias("to"),
            pl.len().alias("n"),
        )
    )
