"""M4 spot panel: one price per provider, medians with and without hyperscalers (fixtures only)."""

import polars as pl
import pytest

from gel.build import spot_panel as sp


def panel():
    return pl.DataFrame(
        {
            "provider": [
                "aws",
                "azure",
                "lambda",
                "nebius",
                "together",
                "coreweave",
                "runpod_paid",
            ],
            "provider_type": [
                "hyperscaler",
                "hyperscaler",
                "neocloud",
                "neocloud",
                "neocloud",
                "neocloud",
                "neocloud",
            ],
            "chip_id": ["h100_sxm"] * 7,
            "billing": ["on_demand"] * 7,
            "price_per_gpu_hr": [6.88, 15.98, 4.59, 4.50, 3.99, 6.155, 3.99],
        }
    )


def test_medians_with_and_without_hyperscalers():
    m = sp.medians(panel()).row(0, named=True)
    assert m["n_providers"] == 7
    assert m["median_all"] == pytest.approx(4.59)  # sorted: 3.99 3.99 4.50 4.59 6.155 6.88 15.98
    assert m["n_neocloud"] == 5
    assert m["median_neocloud"] == pytest.approx(4.50)  # 3.99 3.99 4.50 4.59 6.155
    assert m["min"] == pytest.approx(3.99) and m["max"] == pytest.approx(15.98)


def test_collapse_to_one_price_per_provider():
    rows = pl.DataFrame(
        {
            "provider": ["azure", "azure", "azure"],
            "provider_type": ["hyperscaler"] * 3,
            "chip_id": ["h100_sxm"] * 3,
            "billing": ["on_demand"] * 3,
            "price_per_gpu_hr": [12.0, 16.0, 20.0],
        }
    )
    one = sp.one_per_provider(rows)
    assert one.height == 1
    assert one["price_per_gpu_hr"][0] == pytest.approx(16.0)
