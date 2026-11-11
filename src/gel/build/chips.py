"""Phase 3 chip reference table (Decisions 18 and 19).

Every value carries its source. Order of sources:

1. Epoch AI, 'Data on machine learning hardware' (CC BY 4.0), the archived CSV in
   data/raw/indices/epoch/. Field definitions checked 2026-11-10 against
   https://epoch.ai/data/machine-learning-hardware-documentation/records. "Release date" is
   "The date when the hardware could first be rented, used for machine learning workloads, or
   purchased (excluding pre-orders)".
2. data/raw/manual/chip_specs_manual.csv, if present: values AJ copied by hand from a
   manufacturer datasheet, one row per (chip_id, field) with its URL. These fill gaps only;
   they never overwrite an Epoch value.
3. data/raw/manual/chip_dates.csv: hand-recorded announcement dates (a separate field, never
   used as the release date).

A value Epoch leaves blank stays missing with a reason. Where an Epoch note says a format is
not supported natively (for example "FP8 and FP4: native compute not supported."), the field
is marked not_supported with that note as its source.

Outputs:
  data/processed/chip_specs_long.parquet  one row per chip x field, with status and source
  data/processed/chips.parquet            wide table, one row per chip
  paper/tables/chip_specs.csv             the wide table for the paper

Usage: uv run python -m gel.build.chips
"""

from __future__ import annotations

import argparse
import glob
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import polars as pl
import yaml

EPOCH_GLOB = "data/raw/indices/epoch/*/*-ml_hardware.csv"
EPOCH_URL = "https://epoch.ai/data/machine-learning-hardware"
MANUAL_SPECS = Path("data/raw/manual/chip_specs_manual.csv")
MANUAL_DATES = Path("data/raw/manual/chip_dates.csv")
OUT_LONG = Path("data/processed/chip_specs_long.parquet")
OUT_WIDE = Path("data/processed/chips.parquet")
OUT_TABLE = Path("paper/tables/chip_specs.csv")


@dataclass(frozen=True)
class Field:
    name: str
    epoch_column: str | None
    unit: str
    scale: float = 1.0  # divide Epoch's value by this
    fmt_token: str | None = None  # token searched for in Epoch "not supported" notes


FIELDS = [
    Field("release_date", "Release date", "date"),
    Field("tensor_fp16_bf16_tflops", "Tensor-FP16/BF16 performance (FLOP/s)", "TFLOP/s", 1e12),
    Field("fp8_tflops", "FP8 performance (FLOP/s)", "TFLOP/s", 1e12, "FP8"),
    Field("memory_gb", "Memory (bytes)", "GB", 1e9),
    Field("memory_bw_tbs", "Memory bandwidth (byte/s)", "TB/s", 1e12),
    Field("tdp_w", "TDP (W)", "W"),
    Field("release_price_usd", "Release price (USD)", "USD nominal"),
    Field("announcement_date", None, "date"),
]
FIELD_NAMES = [f.name for f in FIELDS]
STATUSES = ("ok", "not_supported", "missing")
NOT_SUPPORTED_RE = re.compile(r"([A-Z0-9 and,]+):\s*native compute not supported", re.I)


def load_chips(path: Path = Path("config/chips.yaml")) -> list[dict]:
    return yaml.safe_load(path.read_text())["chips"]


def latest_epoch() -> Path:
    files = sorted(glob.glob(EPOCH_GLOB))
    if not files:
        raise FileNotFoundError(f"no Epoch CSV matches {EPOCH_GLOB}")
    return Path(files[-1])


def _blank(v) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def unsupported_formats(note: str | None) -> set[str]:
    """Formats an Epoch note declares not natively supported, e.g. {'FP8', 'FP4'}."""
    out: set[str] = set()
    for m in NOT_SUPPORTED_RE.finditer(note or ""):
        out |= {t for t in re.split(r"[\s,]+|\bAND\b", m.group(1).upper()) if t.strip()}
    return out


def _record(chip_id, field, value, status, source_kind, source_ref, note=""):
    return {
        "chip_id": chip_id,
        "field": field.name,
        "unit": field.unit,
        "value": None if value is None else str(value),
        "status": status,
        "source_kind": source_kind,
        "source_ref": source_ref,
        "note": note,
    }


def _format_value(field: Field, raw: str) -> str:
    if field.unit == "date":
        return raw.strip()[:10]
    v = float(raw) / field.scale
    return f"{v:.6g}"


def epoch_records(chip: dict, epoch: pl.DataFrame, epoch_file: Path) -> list[dict]:
    chip_id, name = chip["id"], chip.get("epoch_name")
    row = None
    if name:
        hit = epoch.filter(pl.col("Hardware name") == name)
        if hit.is_empty():
            raise ValueError(f"{chip_id}: Epoch row {name!r} not found in {epoch_file}")
        row = hit.row(0, named=True)
    ref = f"Epoch AI ({EPOCH_URL}), row '{name}', file {epoch_file}"
    datasheet = (row or {}).get("Link to datasheet") or ""
    unsupported = unsupported_formats((row or {}).get("Notes"))
    out = []
    for f in FIELDS:
        if f.epoch_column is None:
            continue
        if row is None:
            out.append(_record(chip_id, f, None, "missing", "", "", "no Epoch row for this chip"))
            continue
        raw = row.get(f.epoch_column)
        if not _blank(raw):
            note = "Epoch datasheet links: " + " ".join(datasheet.split()) if datasheet else ""
            out.append(_record(chip_id, f, _format_value(f, raw), "ok", "epoch", ref, note))
        elif f.fmt_token and f.fmt_token in unsupported:
            out.append(
                _record(
                    chip_id,
                    f,
                    None,
                    "not_supported",
                    "epoch",
                    ref,
                    "Epoch note: " + " ".join((row.get("Notes") or "").split()),
                )
            )
        else:
            out.append(_record(chip_id, f, None, "missing", "", "", "blank in Epoch"))
    return out


def _manual_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return pl.read_csv(path, infer_schema_length=0).to_dicts()


def apply_manual_specs(records: list[dict], manual: list[dict]) -> list[dict]:
    """Fill missing values from hand-entered datasheet rows. Never overwrites a value."""
    by_key = {(r["chip_id"], r["field"]): r for r in records}
    fields = {f.name: f for f in FIELDS}
    for m in manual:
        key = (m["chip_id"], m["field"])
        if key not in by_key or m["field"] not in fields:
            raise ValueError(f"manual chip spec for unknown chip or field: {key}")
        if _blank(m.get("source_url")):
            raise ValueError(f"manual chip spec {key} has no source_url")
        cur = by_key[key]
        if cur["status"] != "missing":
            continue
        cur.update(
            value=str(m["value"]).strip(),
            status="ok",
            source_kind="datasheet",
            source_ref=m["source_url"].strip(),
            note=(m.get("notes") or "").strip(),
        )
    return records


def announcement_records(chips: list[dict], dates: list[dict]) -> list[dict]:
    field = next(f for f in FIELDS if f.name == "announcement_date")
    found = {
        d["chip_id"]: d
        for d in dates
        if (d.get("date_kind") or "").strip() == "announcement" and not _blank(d.get("source_url"))
    }
    out = []
    for c in chips:
        d = found.get(c["id"])
        if d:
            out.append(
                _record(
                    c["id"],
                    field,
                    d["release_date"].strip(),
                    "ok",
                    "manual",
                    d["source_url"].strip(),
                    (d.get("notes") or "").strip(),
                )
            )
        else:
            out.append(_record(c["id"], field, None, "missing", "", "", "not hand-recorded yet"))
    return out


def build_long(
    chips: list[dict],
    epoch_file: Path,
    manual_specs: list[dict] | None = None,
    manual_dates: list[dict] | None = None,
) -> pl.DataFrame:
    epoch = pl.read_csv(epoch_file, infer_schema_length=0)
    records: list[dict] = []
    for c in chips:
        records += epoch_records(c, epoch, epoch_file)
    records += announcement_records(chips, manual_dates or [])
    records = apply_manual_specs(records, manual_specs or [])
    vendor = {c["id"]: c["vendor"] for c in chips}
    df = pl.DataFrame(records).with_columns(
        pl.col("chip_id").replace_strict(vendor).alias("vendor")
    )
    order = {c["id"]: i for i, c in enumerate(chips)}
    return df.sort(
        pl.col("chip_id").replace_strict(order),
        pl.col("field").replace_strict({n: i for i, n in enumerate(FIELD_NAMES)}),
    ).select(
        "chip_id", "vendor", "field", "unit", "value", "status", "source_kind", "source_ref", "note"
    )


def check_sources(long: pl.DataFrame) -> list[str]:
    """Problems that make the table unusable. Empty list means every value is sourced."""
    problems = []
    for r in long.iter_rows(named=True):
        key = f"{r['chip_id']}.{r['field']}"
        if r["status"] not in STATUSES:
            problems.append(f"{key}: unknown status {r['status']!r}")
        if r["status"] == "ok" and (_blank(r["value"]) or _blank(r["source_ref"])):
            problems.append(f"{key}: value without a source")
        if r["status"] == "not_supported" and _blank(r["source_ref"]):
            problems.append(f"{key}: not_supported without a source")
        if r["status"] != "ok" and not _blank(r["value"]):
            problems.append(f"{key}: {r['status']} but has a value")
        if r["status"] == "missing" and _blank(r["note"]):
            problems.append(f"{key}: missing without a reason")
    return problems


def to_wide(long: pl.DataFrame) -> pl.DataFrame:
    wide = long.pivot(
        on="field", index=["chip_id", "vendor"], values="value", aggregate_function="first"
    )
    for f in FIELDS:
        if f.name not in wide.columns:
            wide = wide.with_columns(pl.lit(None, dtype=pl.String).alias(f.name))
        elif f.unit == "date":
            wide = wide.with_columns(pl.col(f.name).str.to_date(strict=True))
        else:
            wide = wide.with_columns(pl.col(f.name).cast(pl.Float64))
    return wide.select("chip_id", "vendor", *FIELD_NAMES)


def run(epoch_file: Path | None = None) -> pl.DataFrame:
    chips = load_chips()
    long = build_long(
        chips, epoch_file or latest_epoch(), _manual_rows(MANUAL_SPECS), _manual_rows(MANUAL_DATES)
    )
    problems = check_sources(long)
    if problems:
        raise ValueError("chip table has unsourced values:\n" + "\n".join(problems))
    for p in (OUT_LONG, OUT_WIDE, OUT_TABLE):
        p.parent.mkdir(parents=True, exist_ok=True)
    long.write_parquet(OUT_LONG)
    wide = to_wide(long)
    wide.write_parquet(OUT_WIDE)
    wide.write_csv(OUT_TABLE)
    return long


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the Phase 3 chip reference table.")
    ap.add_argument("--epoch-csv", type=Path, default=None)
    args = ap.parse_args(argv)
    long = run(args.epoch_csv)
    counts = long.group_by("status").len().sort("status")
    print(f"wrote {OUT_LONG}, {OUT_WIDE}, {OUT_TABLE}")
    for r in counts.iter_rows(named=True):
        print(f"  {r['status']:>13}: {r['len']}")
    missing = long.filter(pl.col("status") == "missing")
    for r in missing.iter_rows(named=True):
        print(f"  missing {r['chip_id']}.{r['field']} ({r['note']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
