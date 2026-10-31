import subprocess
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


def _ignored(path: str) -> bool:
    return subprocess.run(["git", "check-ignore", "-q", path], cwd=ROOT).returncode == 0


def test_data_is_ignored_but_layout_survives_a_clone():
    for path in [
        "data/raw/wayback/cdx/x.json",
        "data/interim/a.parquet",
        "data/processed/b.parquet",
    ]:
        assert _ignored(path), path
    for path in ["data/raw/wayback/.gitkeep", "data/raw/live/.gitkeep", "data/interim/.gitkeep"]:
        assert not _ignored(path), path


def test_contact_email_file_is_ignored():
    assert _ignored(".env")
