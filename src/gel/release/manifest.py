"""Replication manifest for the raw data (finish plan D2).

`build` walks data/raw, records every file's SHA-256, size and sidecar source, and classes each
file by what may be redistributed (docs/finish_plan.md "What can be published"). `verify` checks a
local data/raw against the manifest, so a replicator who re-fetched or received the files knows
they match what the paper used.

Classes: own (our measurements and transcriptions), open (licence permits redistribution: Epoch CC
BY 4.0, EIA and BLS public domain, SEC EDGAR), derived_only (provider price files; publish monthly
aggregates, not the files), refetch (no licence or third-party pages: SkyPilot history, Wayback
pages; re-run the collector).

Usage: uv run python -m gel.release.manifest [build|verify|deposit [OUT]]
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

RAW = Path("data/raw")
MANIFEST = Path("release/raw_manifest.csv")
CLASSES = {
    "bench": "own",
    "manual": "own",
    "indices/epoch": "open",
    "indices/bls_cpi": "open",
    "indices/getdeploying": "open",
    "eia": "open",
    "edgar": "open",
    "aws_offers": "derived_only",
    "live": "derived_only",
    "skypilot_history": "refetch",
    "wayback": "refetch",
}
REFETCH = {
    "skypilot_history": "uv run python -m gel.collect.skypilot_history",
    "wayback": (
        "uv run python -m gel.collect.wayback_cdx && uv run python -m gel.collect.wayback_snapshots"
    ),
    "aws_offers": "uv run python -m gel.collect.aws_history",
    "edgar": "uv run python -m gel.collect.edgar",
}


def file_class(rel: Path) -> str:
    parts = rel.parts
    for key in (f"{parts[0]}/{parts[1]}" if len(parts) > 1 else "", parts[0]):
        if key in CLASSES:
            return CLASSES[key]
    return "unclassified"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sidecar_source(path: Path) -> str:
    side = path.with_name(path.name + ".json")
    if not side.exists():
        return ""
    try:
        return str(json.loads(side.read_text()).get("source_url", ""))
    except (json.JSONDecodeError, AttributeError):
        return ""


def build() -> int:
    rows = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file() or path.name == ".gitkeep" or path.name == ".DS_Store":
            continue
        rel = path.relative_to(RAW)
        top = rel.parts[0]
        rows.append(
            {
                "path": str(rel),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "class": file_class(rel),
                "source_url": "" if path.suffix == ".json" else sidecar_source(path),
                "refetch": REFETCH.get(top, ""),
            }
        )
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    print(
        f"wrote {MANIFEST}: {len(rows)} files; " + ", ".join(f"{k} {v}" for k, v in counts.items())
    )
    return 0


def verify() -> int:
    bad = missing = ok = 0
    with MANIFEST.open() as fh:
        for r in csv.DictReader(fh):
            path = RAW / r["path"]
            if not path.exists():
                missing += 1
                continue
            if sha256(path) != r["sha256"]:
                bad += 1
                print(f"checksum mismatch: {r['path']}")
            else:
                ok += 1
    print(f"verified {ok} files; {missing} missing; {bad} mismatched")
    return 1 if bad else 0


def deposit(out: str = "release/deposit") -> int:
    """Zip for the Zenodo data record: every raw file classed own or open (with its sidecar),
    the manifest, and the public panel in release/dataset/."""
    import zipfile

    target = Path(out)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "gpu-econ-life-public-data.zip"
    n = 0
    with MANIFEST.open() as fh, zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in csv.DictReader(fh):
            if r["class"] in ("own", "open"):
                zf.write(RAW / r["path"], f"data/raw/{r['path']}")
                n += 1
        zf.write(MANIFEST, "release/raw_manifest.csv")
        for f in sorted(Path("release/dataset").glob("*")):
            zf.write(f, f"release/dataset/{f.name}")
    print(f"wrote {path}: {n} raw files, {path.stat().st_size / 1e6:.0f} MB")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv or ["build"]
    cmd = argv[0]
    if cmd == "deposit":
        return deposit(*argv[1:])
    return {"build": build, "verify": verify}[cmd]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
