"""P3 capex extraction from Epoch AI's hardware CSV (Decision 10). Fixture rows mimic the real
file's columns and wording; they are test data, not data."""

import pytest

from gel.models import p3_capex

HEADER = "Hardware name,Release date,Release price (USD),Source for the price\n"
ROWS = (
    'NVIDIA H100 SXM5 80GB,2022-09-20,33600.0,"No official MSRP. DGX servers with 8xH100 were '
    "sold for $269k, or $33,600 per GPU. In bill of materials, 8 GPUs + baseboard are $195k, "
    'or $24.4k per GPU."\n'
    "NVIDIA A100 SXM4 40 GB,2020-05-14,15000.0,https://example.org/a100\n"
    "NVIDIA Tesla V100 SXM2,2017-07-01,11500.0,\n"
    "NVIDIA B200,2024-11-15,,\n"
)


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "ml_hardware.csv"
    p.write_text(HEADER + ROWS)
    return p


def test_extracts_anchor_and_bom(csv_path):
    c = p3_capex.extract(csv_path)
    assert c["K0_usd"] == 33_600.0
    assert c["h100_gpu_baseboard_usd"] == 24_400.0
    assert c["a100_40gb_card_usd"] == 15_000.0


def test_growth_is_card_level_ratio(csv_path):
    c = p3_capex.extract(csv_path)
    # 24,400 / 15,000 = 1.62667
    assert c["growth_per_generation"] == pytest.approx(24_400 / 15_000)


def test_architecture_release_gaps(csv_path):
    c = p3_capex.extract(csv_path)
    # V100 SXM2 2017-07-01 -> A100 2020-05-14 -> H100 2022-09-20 -> B200 2024-11-15
    gaps = {g["to"]: g["months"] for g in c["architecture_gaps"]}
    assert gaps["NVIDIA A100 SXM4 40 GB"] == pytest.approx(34.4, abs=0.1)
    assert gaps["NVIDIA H100 SXM5 80GB"] == pytest.approx(28.2, abs=0.1)
    assert gaps["NVIDIA B200"] == pytest.approx(25.9, abs=0.1)


def test_missing_bom_note_raises(tmp_path):
    p = tmp_path / "x.csv"
    p.write_text(
        HEADER + "NVIDIA H100 SXM5 80GB,2022-09-20,33600.0,no note\n"
        "NVIDIA A100 SXM4 40 GB,2020-05-14,15000.0,\n"
    )
    with pytest.raises(ValueError, match="baseboard"):
        p3_capex.extract(p)
