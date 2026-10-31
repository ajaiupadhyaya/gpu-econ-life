from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_layout_matches_claude_md():
    for rel in [
        "CLAUDE.md",
        "README.md",
        "Makefile",
        "pyproject.toml",
        "config/providers.yaml",
        "config/chips.yaml",
        "config/assumptions.yaml",
        "data/raw/wayback",
        "data/raw/live",
        "data/raw/indices",
        "data/raw/specs",
        "data/raw/eia",
        "data/raw/edgar",
        "data/interim",
        "data/processed",
        "src/gel/collect",
        "src/gel/parse",
        "src/gel/build",
        "src/gel/models",
        "src/gel/accounting",
        "src/gel/viz",
        "notebooks",
        "paper/figures",
        "paper/tables",
        "deploy",
        "docs/proposal.md",
        "docs/decisions.md",
        "docs/assumptions.md",
        "docs/open_questions.md",
        "docs/research_log.md",
    ]:
        assert (ROOT / rel).exists(), rel


def test_chip_ids_match_conventions():
    chips = yaml.safe_load((ROOT / "config/chips.yaml").read_text())["chips"]
    assert [c["id"] for c in chips] == [
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


def test_providers_cover_every_phase0_provider_and_type():
    data = yaml.safe_load((ROOT / "config/providers.yaml").read_text())
    providers = data["providers"]
    assert set(providers) >= {
        "aws",
        "google_cloud",
        "azure",
        "oracle",
        "lambda",
        "coreweave",
        "runpod",
        "vast",
        "paperspace",
    }
    for name, p in providers.items():
        assert p["provider_type"] in {"hyperscaler", "neocloud", "marketplace"}, name
        assert p["pages"], name
        for page in p["pages"]:
            assert page["url"].startswith("https://"), page


def test_raw_data_is_not_tracked():
    ignore = (ROOT / ".gitignore").read_text()
    assert "data/raw/**" in ignore
    assert ".env" in ignore
