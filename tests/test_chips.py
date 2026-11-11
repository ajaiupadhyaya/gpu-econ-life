"""Phase 3 chip reference table: every value has a source, gaps stay missing (Decision 18)."""

from pathlib import Path

import polars as pl
import pytest

from gel.build import chips as ch

CHIPS = [
    {"id": "a", "vendor": "NVIDIA", "epoch_name": "Chip A"},
    {"id": "b", "vendor": "NVIDIA", "epoch_name": "Chip B"},
    {"id": "c", "vendor": "AMD", "epoch_name": None},
]


@pytest.fixture
def epoch_csv(tmp_path: Path) -> Path:
    df = pl.DataFrame(
        {
            "Hardware name": ["Chip A", "Chip B", "Other"],
            "Release date": ["2022-09-20", "2020-05-14", "2019-01-01"],
            "Release price (USD)": ["33600.0", "", ""],
            "Tensor-FP16/BF16 performance (FLOP/s)": ["989500000000000.0", "3.12e14", ""],
            "FP8 performance (FLOP/s)": ["1979000000000000.0", "", ""],
            "Memory (bytes)": ["80000000000.0", "40000000000.0", ""],
            "Memory bandwidth (byte/s)": ["3350000000000.0", "1555000000000.0", ""],
            "TDP (W)": ["700.0", "400.0", ""],
            "Link to datasheet": ["https://example.org/a.pdf", "", ""],
            "Notes": [
                "FP4: native compute not supported.",
                "FP8 and FP4: native compute not supported.",
                "",
            ],
        }
    )
    path = tmp_path / "235424Z-ml_hardware.csv"
    df.write_csv(path)
    return path


def _get(long: pl.DataFrame, chip: str, field: str) -> dict:
    return long.filter((pl.col("chip_id") == chip) & (pl.col("field") == field)).row(0, named=True)


def test_units_are_converted(epoch_csv):
    long = ch.build_long(CHIPS, epoch_csv)
    assert _get(long, "a", "tensor_fp16_bf16_tflops")["value"] == "989.5"
    assert _get(long, "a", "memory_gb")["value"] == "80"
    assert _get(long, "a", "memory_bw_tbs")["value"] == "3.35"
    assert _get(long, "a", "release_date")["value"] == "2022-09-20"


def test_every_chip_has_every_field(epoch_csv):
    long = ch.build_long(CHIPS, epoch_csv)
    assert long.height == len(CHIPS) * len(ch.FIELDS)


def test_values_carry_epoch_source(epoch_csv):
    rec = _get(ch.build_long(CHIPS, epoch_csv), "a", "tdp_w")
    assert rec["status"] == "ok"
    assert rec["source_kind"] == "epoch"
    assert "Chip A" in rec["source_ref"] and str(epoch_csv) in rec["source_ref"]


def test_blank_epoch_value_is_missing_not_filled(epoch_csv):
    rec = _get(ch.build_long(CHIPS, epoch_csv), "b", "release_price_usd")
    assert rec["status"] == "missing" and rec["value"] is None
    assert rec["note"] == "blank in Epoch"


def test_epoch_not_supported_note(epoch_csv):
    rec = _get(ch.build_long(CHIPS, epoch_csv), "b", "fp8_tflops")
    assert rec["status"] == "not_supported"
    assert "FP8 and FP4" in rec["note"]


def test_unsupported_formats_parser():
    assert ch.unsupported_formats("FP8 and FP4: native compute not supported.") == {"FP8", "FP4"}
    assert ch.unsupported_formats(
        "Listed figures are without sparsity.\n\nFP4: native compute not supported."
    ) == {"FP4"}
    assert ch.unsupported_formats(None) == set()


def test_chip_without_epoch_row_is_all_missing(epoch_csv):
    long = ch.build_long(CHIPS, epoch_csv).filter(pl.col("chip_id") == "c")
    assert set(long["status"]) == {"missing"}


def test_unknown_epoch_name_raises(epoch_csv):
    with pytest.raises(ValueError, match="not found"):
        ch.build_long([{"id": "x", "vendor": "NVIDIA", "epoch_name": "Nope"}], epoch_csv)


def test_manual_datasheet_fills_gap_only(epoch_csv):
    manual = [
        {
            "chip_id": "c",
            "field": "tdp_w",
            "value": "350",
            "source_url": "https://example.org/c.pdf",
        },
        {"chip_id": "a", "field": "tdp_w", "value": "999", "source_url": "https://example.org/x"},
    ]
    long = ch.build_long(CHIPS, epoch_csv, manual_specs=manual)
    filled = _get(long, "c", "tdp_w")
    assert (filled["value"], filled["source_kind"]) == ("350", "datasheet")
    assert filled["source_ref"] == "https://example.org/c.pdf"
    assert _get(long, "a", "tdp_w")["value"] == "700"  # Epoch value is never overwritten


def test_manual_row_without_url_raises(epoch_csv):
    manual = [{"chip_id": "c", "field": "tdp_w", "value": "350", "source_url": ""}]
    with pytest.raises(ValueError, match="no source_url"):
        ch.build_long(CHIPS, epoch_csv, manual_specs=manual)


def test_announcement_date_from_hand_record_only(epoch_csv):
    dates = [
        {
            "chip_id": "c",
            "release_date": "2023-08-08",
            "date_kind": "announcement",
            "source_url": "https://example.org/pr",
            "notes": "",
        },
    ]
    long = ch.build_long(CHIPS, epoch_csv, manual_dates=dates)
    assert _get(long, "c", "announcement_date")["value"] == "2023-08-08"
    assert _get(long, "c", "release_date")["status"] == "missing"  # never reused as release date


def test_check_sources_passes_on_built_table(epoch_csv):
    assert ch.check_sources(ch.build_long(CHIPS, epoch_csv)) == []


def test_check_sources_fails_on_unsourced_value(epoch_csv):
    long = ch.build_long(CHIPS, epoch_csv).with_columns(
        pl.when((pl.col("chip_id") == "a") & (pl.col("field") == "tdp_w"))
        .then(pl.lit(""))
        .otherwise(pl.col("source_ref"))
        .alias("source_ref")
    )
    assert ch.check_sources(long) == ["a.tdp_w: value without a source"]


def test_wide_table_types(epoch_csv):
    wide = ch.to_wide(ch.build_long(CHIPS, epoch_csv))
    assert wide.schema["release_date"] == pl.Date
    assert wide.schema["tdp_w"] == pl.Float64
    assert wide.filter(pl.col("chip_id") == "a")["fp8_tflops"].item() == pytest.approx(1979.0)


def test_project_config_lists_all_chip_ids():
    ids = [c["id"] for c in ch.load_chips()]
    assert ids == [
        "v100",
        "a100_40gb",
        "a100_80gb",
        "h100_sxm",
        "h100_pcie",
        "h200",
        "b200",
        "mi300x",
        "l40s",
    ]


def test_built_project_table_has_no_unsourced_values():
    # Runs against the committed pipeline output when it exists (make chips).
    if not ch.OUT_LONG.exists():
        pytest.skip("run make chips first")
    assert ch.check_sources(pl.read_parquet(ch.OUT_LONG)) == []
