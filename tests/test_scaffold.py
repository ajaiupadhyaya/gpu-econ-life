import subprocess
from pathlib import Path

import yaml

from gel.collect.live import COLLECTORS
from gel.schema import CHIPS

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


def test_providers_with_restrictive_terms_stay_blocked():
    providers = yaml.safe_load((ROOT / "config/providers.yaml").read_text())["providers"]
    blocked = {name for name, p in providers.items() if p.get("live_collection") == "blocked"}
    assert blocked == {"oracle", "runpod", "vast"}


def test_every_sku_mapping_is_allowed_and_cites_a_source():
    config = yaml.safe_load((ROOT / "config/skus.yaml").read_text())
    for name, spec in config["azure"]["skus"].items():
        assert spec["source"].startswith("https://"), name
        assert spec["chip"] in CHIPS and spec["gpus"] >= 1, name
    assert config["aws"]["source"].startswith("https://")
    for name, spec in config["aws"]["instances"].items():
        assert spec["chip"] in CHIPS and spec["gpus"] >= 1, name
    for name, spec in config["skypilot"]["gcp"]["accelerators"].items():
        assert spec["chip"] in CHIPS, name


def test_collectors_cover_only_cleared_sources():
    assert set(COLLECTORS) == {"azure", "aws", "lambda", "skypilot"}
    catalog_code = (ROOT / "src/gel/collect/skypilot.py").read_text()
    assert '"aws"' in catalog_code and '"gcp"' in catalog_code


def test_deployment_units_run_the_real_entry_points():
    service = (ROOT / "deploy/gel-collect.service").read_text()
    assert "python -m gel.collect.live --all" in service
    assert "python -m gel.collect.health" in service
    assert "OnFailure=gel-alert@" in service
    assert "Persistent=true" in (ROOT / "deploy/gel-collect.timer").read_text()


def test_backup_can_never_delete_or_rewrite_raw_data():
    script = (ROOT / "deploy/backup.sh").read_text()
    assert "rclone copy" in script and "--immutable" in script
    assert "rclone sync" not in script


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
