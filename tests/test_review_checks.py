"""Supplementary review checks (docs/review_01.md): hand-checkable pieces."""

from datetime import date

import polars as pl
import pytest

from gel.models import review_checks as rc


def _listing(price_path: list[float], provider: str, contract: str) -> list[dict]:
    return [
        {
            "provider": provider,
            "sku": "x",
            "chip": "h100_sxm",
            "gpu_count": 8,
            "interconnect": "",
            "region": "r1",
            "contract_type": contract,
            "term_months": 0,
            "price_basis": "accelerator_only",
            "price_kind": "list",
            "form_factor": "sxm",
            "month": date(2024, k + 1, 1),
            "price_usd_per_gpu_hour": p,
        }
        for k, p in enumerate(price_path)
    ]


def test_unchanged_share_counts_month_to_month_transitions():
    rows = _listing([3.0, 3.0, 3.0, 2.5], "aws", "on_demand")  # 3 transitions, 2 unchanged
    rows += _listing([1.0, 1.1, 1.2], "aws", "spot")  # 2 transitions, 0 unchanged
    df = pl.DataFrame(rows)
    s = rc.transitions(df)
    got = dict(s.group_by("contract_type").agg(pl.col("_same").mean()).rows())
    assert got["on_demand"] == pytest.approx(2 / 3)
    assert got["spot"] == pytest.approx(0.0)
