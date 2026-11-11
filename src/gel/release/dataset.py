"""Public dataset for Zenodo (finish plan D4): derived monthly aggregates only.

Writes release/dataset/ with:
- gpu_rental_panel.csv: the listing-month panel (monthly median posted price per listing), minus
  rows that come only from the SkyPilot catalog history (no licence, finish plan "Do not
  republish"), with the source collector named on every row.
- chips.csv: the chip reference table (Epoch AI, CC BY 4.0; attribution in README).
- README.md: provenance, licences and column definitions.

Usage: uv run python -m gel.release.dataset
"""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

OUT = Path("release/dataset")
COLUMNS = [
    "month",
    "provider",
    "provider_type",
    "chip",
    "sku",
    "gpu_count",
    "form_factor",
    "region",
    "contract_type",
    "term_months",
    "price_basis",
    "price_usd_per_gpu_hour",
    "price_usd_per_gpu_hour_real2025",
    "age_months",
    "n_obs",
    "collector",
    "price_outlier",
]

README = """# GPU rental price panel (derived monthly aggregates)

Companion dataset to the working paper "Rental-Implied Depreciation of AI Accelerators: Why the
Estimates Disagree". Built by `gel.release.dataset` from the replication repository.

- `gpu_rental_panel.csv`: one row per listing-month: the median of a month's posted prices for
  one provider, SKU, chip, GPU count, form factor, region, contract type and term, in USD per
  GPU-hour (nominal, and in 2025 dollars using BLS CPI-U). `collector` names the source(s); rows
  available only from the SkyPilot catalog history are omitted because that catalog has no
  licence. They are re-created by the repository's collector.
- `chips.csv`: chip specifications and release dates from Epoch AI, "Data on machine learning
  hardware" (CC BY 4.0), as used in the paper.

Licence: the panel is released under CC BY 4.0 as a compilation of facts (posted prices),
except where a provider's terms say otherwise; see `docs/data_sources.md` in the repository.
Prices are posted list, spot and reserved prices, not transaction prices.
"""


def build() -> dict[str, int]:
    panel = pl.read_parquet("data/processed/panel.parquet")
    keep = panel.filter(
        ~pl.col("collector")
        .str.split("+")
        .list.eval(pl.element().str.starts_with("skypilot"))
        .list.all()
    )
    OUT.mkdir(parents=True, exist_ok=True)
    keep.select([c for c in COLUMNS if c in keep.columns]).sort(
        "chip", "provider", "month"
    ).write_csv(OUT / "gpu_rental_panel.csv")
    pl.read_parquet("data/processed/chips.parquet").write_csv(OUT / "chips.csv")
    (OUT / "README.md").write_text(README)
    return {"panel_rows": panel.height, "released_rows": keep.height}


def main(argv: list[str] | None = None) -> int:
    out = build()
    print(f"wrote {OUT}: {out['released_rows']:,} of {out['panel_rows']:,} listing-months")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
