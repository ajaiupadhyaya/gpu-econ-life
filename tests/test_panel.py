"""Phase 4 panel steps on hand-built rows (Decision 22)."""

from datetime import date

import polars as pl
import pytest

from gel.build import panel as P


def _row(**kw):
    base = {
        "retrieved_at": "2026-03-05T06:00:00Z",
        "provider": "aws",
        "provider_type": "hyperscaler",
        "sku": "p4d.24xlarge",
        "chip": "a100_40gb",
        "gpu_count": 8,
        "gpu_memory_gb": 40.0,
        "interconnect": "sxm",
        "region": "us-east-1",
        "contract_type": "on_demand",
        "term_months": None,
        "price_usd_per_hour_instance": 32.0,
        "price_usd_per_gpu_hour": 4.0,
        "vcpus": 96,
        "ram_gb": 1152.0,
        "price_basis": "instance",
        "price_kind": "list",
        "zone": None,
        "collector": "aws",
        "origin": "live",
    }
    base.update(kw)
    return base


def _frame(rows):
    return pl.DataFrame(rows, infer_schema_length=None)


def test_clean_drops_bad_rows_and_counts_them():
    log = []
    df = _frame(
        [
            _row(),
            _row(),  # exact duplicate
            _row(price_usd_per_gpu_hour=0.0),
            _row(chip="tpu_v5"),
        ]
    )
    out = P.clean(df, ["a100_40gb"], log)
    assert out.height == 1
    assert [e["dropped"] for e in log] == [1, 1, 1]


def test_spot_zones_collapse_to_median_per_region_day():
    log = []
    rows = [
        _row(contract_type="spot", price_kind="spot", zone=z, price_usd_per_gpu_hour=p)
        for z, p in [("us-east-1a", 1.0), ("us-east-1b", 2.0), ("us-east-1c", 6.0)]
    ]
    df = P.clean(_frame(rows), ["a100_40gb"], [])
    out = P.collapse_zones(df, log)
    assert out.height == 1
    assert out["price_usd_per_gpu_hour"].item() == pytest.approx(2.0)
    assert out["n_zones"].item() == 3


def test_month_collapse_uses_median_and_counts_observations():
    days = ["2026-03-01", "2026-03-02", "2026-03-20"]
    prices = [4.0, 4.0, 10.0]
    rows = [
        _row(retrieved_at=f"{d}T06:00:00Z", price_usd_per_gpu_hour=p)
        for d, p in zip(days, prices, strict=True)
    ]
    df = P.collapse_zones(P.clean(_frame(rows), ["a100_40gb"], []), [])
    out = P.collapse_months(df, [])
    r = out.row(0, named=True)
    assert (r["month"], r["price_usd_per_gpu_hour"], r["n_obs"]) == (date(2026, 3, 1), 4.0, 3)
    assert (r["first_day"], r["last_day"]) == (date(2026, 3, 1), date(2026, 3, 20))


def _pipeline(rows):
    df = P.clean(_frame(rows), ["a100_40gb", "h100_sxm"], [])
    return P.collapse_months(P.collapse_zones(df, []), [])


def test_more_direct_collector_wins_even_with_different_sku_text():
    rows = [
        _row(
            provider="lambda",
            provider_type="neocloud",
            sku="8x NVIDIA A100|40GB",
            interconnect="",
            region="unspecified",
            collector="wayback",
            origin="history",
            price_usd_per_gpu_hour=1.10,
        ),
        _row(
            provider="lambda",
            provider_type="neocloud",
            sku="gpu_8x_a100",
            interconnect="",
            region="unspecified",
            collector="skypilot_history",
            origin="history",
            price_usd_per_gpu_hour=1.10,
        ),
    ]
    kept, agreement = P.pick_collector(_pipeline(rows), [])
    assert kept.height == 1
    assert kept["collector"].item() == "wayback"
    assert agreement["pairs"] == 1
    assert agreement["median_abs_pct_gap"] == pytest.approx(0.0)


def test_form_factor_keeps_pcie_and_sxm_apart():
    rows = [
        _row(
            provider="lambda",
            sku="gpu_1x_a100_sxm4",
            interconnect="",
            gpu_count=1,
            collector="skypilot_history",
            origin="history",
        ),
        _row(
            provider="lambda",
            sku="1x|NVIDIA A100 PCIe|40GB",
            interconnect="",
            gpu_count=1,
            collector="lambda",
        ),
    ]
    kept, _ = P.pick_collector(_pipeline(rows), [])
    assert sorted(kept["form_factor"].to_list()) == ["pcie", "sxm"]


def test_equally_direct_collectors_are_merged():
    rows = [
        _row(collector="aws", origin="live", price_usd_per_gpu_hour=4.0),
        _row(collector="aws_history", origin="history", price_usd_per_gpu_hour=4.2),
    ]
    log = []
    kept, _ = P.pick_collector(_pipeline(rows), log)
    assert kept.height == 1
    assert kept["collector"].item() == "aws+aws_history"
    assert kept["price_usd_per_gpu_hour"].item() == pytest.approx(4.1)
    assert kept["n_obs"].item() == 2
    assert log[-1]["dropped"] == 1


def test_form_factor_reader():
    df = pl.DataFrame(
        {
            "sku": ["gpu_8x_h100_sxm5", "NVIDIA A100 PCIe", "p4d.24xlarge", "x"],
            "ic": ["", "", "nvlink", None],
        }
    )
    got = df.select(P.form_factor(pl.col("sku"), pl.col("ic")).alias("ff"))["ff"].to_list()
    assert got == ["sxm", "pcie", "sxm", ""]


@pytest.fixture
def reference():
    chips = pl.DataFrame(
        {
            "chip_id": ["a100_40gb", "h100_sxm"],
            "release_date": [date(2020, 5, 14), None],
            "tensor_fp16_bf16_tflops": [312.0, 989.5],
            "memory_gb": [40.0, 80.0],
            "memory_bw_tbs": [1.555, 3.35],
        }
    )
    cpi = pl.DataFrame({"month": [date(2026, 3, 1)], "to_2025_usd": [0.98], "cpi_imputed": [False]})
    return chips, cpi


def test_age_real_price_and_flags(reference):
    chips, cpi = reference
    rows = [
        _row(price_usd_per_gpu_hour=4.0),
        _row(sku="other", price_usd_per_gpu_hour=4.0),
        _row(sku="odd", price_usd_per_gpu_hour=40.0),  # 10x the cell median -> outlier
        _row(chip="h100_sxm", sku="h", retrieved_at="2026-04-02T00:00:00Z"),
    ]
    kept, _ = P.pick_collector(_pipeline(rows), [])
    out = P.join_reference(kept, chips, cpi)
    a = out.filter((pl.col("chip") == "a100_40gb") & (pl.col("sku") == "p4d.24xlarge")).row(
        0, named=True
    )
    assert a["age_months"] == (2026 - 2020) * 12 + (3 - 5)  # 70
    assert a["price_usd_per_gpu_hour_real2025"] == pytest.approx(4.0 * 0.98)
    assert not a["pre_release"]
    assert out.filter(pl.col("sku") == "odd")["price_outlier"].item()
    h = out.filter(pl.col("chip") == "h100_sxm").row(0, named=True)
    assert h["age_months"] is None  # no release date -> age unknown, not guessed
    assert h["price_usd_per_gpu_hour_real2025"] is None  # no CPI for April


def test_pre_release_listing_is_flagged(reference):
    chips, cpi = reference
    rows = [_row(retrieved_at="2020-03-01T00:00:00Z")]
    kept, _ = P.pick_collector(_pipeline(rows), [])
    out = P.join_reference(kept, chips, cpi)
    assert out["age_months"].item() == -2
    assert out["pre_release"].item()
