"""P3 capex inputs from Epoch AI's machine-learning hardware dataset (Decision 10).

Reads the archived CSV in data/raw/indices/epoch/ and writes data/processed/p3_capex.json:

- K0_usd: H100 SXM5 80GB "Release price (USD)" = $33,600. Epoch's note derives it from a DGX
  server with 8 H100s sold for $269k (SemiAnalysis, May 2023), so it includes the server share,
  matching the handoff's capex definition. The network fabric is not included.
- growth_per_generation: H100 GPU + baseboard bill of materials ($24.4k per GPU, parsed from the
  same note) / A100 SXM4 40GB card price ($15,000), the closest like-for-like pair: 1.63x.
- Sensitivity values: $24,400 (GPU + baseboard only) for K0; ~1.0x for growth (Decision 10).
- architecture_gaps: months between release dates of successive NVIDIA data-centre
  architectures (V100 -> A100 -> H100 -> B200), recorded for an empirical-cadence scenario.

Data: Epoch AI, 'Data on machine learning hardware', CC BY 4.0.
Usage: uv run python -m gel.models.p3_capex
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, date, datetime
from pathlib import Path

import polars as pl

RAW_GLOB = "data/raw/indices/epoch/*/*-ml_hardware.csv"
OUT = Path("data/processed/p3_capex.json")
H100 = "NVIDIA H100 SXM5 80GB"
A100_40 = "NVIDIA A100 SXM4 40 GB"
ARCHITECTURES = ["NVIDIA Tesla V100 SXM2", A100_40, H100, "NVIDIA B200"]
BOM_RE = re.compile(r"baseboard are \$[\d.,]+k, or \$([\d.]+)k per GPU", re.I)


def _row(df: pl.DataFrame, name: str) -> dict:
    hit = df.filter(pl.col("Hardware name") == name)
    if hit.is_empty():
        raise ValueError(f"{name} not found in Epoch CSV")
    return hit.row(0, named=True)


def _months(a: str, b: str) -> float:
    da, db = date.fromisoformat(a), date.fromisoformat(b)
    return (db - da).days / 30.4375


def extract(csv_path: Path) -> dict:
    df = pl.read_csv(csv_path, infer_schema_length=0)
    h100, a100 = _row(df, H100), _row(df, A100_40)
    note = h100.get("Source for the price") or ""
    m = BOM_RE.search(note)
    if not m:
        raise ValueError("H100 GPU + baseboard bill-of-materials figure not found in Epoch note")
    bom = float(m.group(1)) * 1000.0
    k0 = float(h100["Release price (USD)"])
    a100_card = float(a100["Release price (USD)"])
    gaps = []
    for prev, nxt in zip(ARCHITECTURES, ARCHITECTURES[1:], strict=False):
        try:
            a, b = _row(df, prev)["Release date"], _row(df, nxt)["Release date"]
        except ValueError:
            continue
        gaps.append({"from": prev, "to": nxt, "months": round(_months(a, b), 2)})
    return {
        "K0_usd": k0,
        "K0_basis": "H100 SXM5 80GB: DGX 8xH100 $269k / 8 (server share in, network out)",
        "h100_gpu_baseboard_usd": bom,
        "a100_40gb_card_usd": a100_card,
        "growth_per_generation": bom / a100_card,
        "growth_basis": "H100 GPU+baseboard BOM / A100 SXM4 40GB card price",
        "sensitivity": {"K0_usd": [bom, k0], "growth_per_generation": [1.0, bom / a100_card]},
        "architecture_gaps": gaps,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Extract P3 capex inputs from Epoch AI data.")
    ap.add_argument("--csv", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    csv_path = args.csv or max(Path(".").glob(RAW_GLOB))
    out = extract(csv_path) | {
        "source_file": str(csv_path),
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "citation": "Epoch AI, 'Data on machine learning hardware', CC BY 4.0",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"wrote {args.out}: K0 ${out['K0_usd']:,.0f}, growth x{out['growth_per_generation']:.3f}, "
        f"gaps {[g['months'] for g in out['architecture_gaps']]} months"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
