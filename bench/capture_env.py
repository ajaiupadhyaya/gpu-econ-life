#!/usr/bin/env python3
"""Record the software and hardware environment of a benchmark pod into env.json.

Identifiers that could tie a run to a specific machine (GPU UUID, hostname) are stored only as
truncated SHA-256 hashes. Standard library only.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

GPU_FIELDS = [
    "name",
    "uuid",
    "driver_version",
    "memory.total",
    "power.limit",
    "power.max_limit",
    "clocks.max.sm",
    "pcie.link.gen.max",
    "pcie.link.width.max",
    "compute_cap",
]


def run(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout.strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return f"<error: {exc}>"


def short_hash(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:12]


def gpus() -> list[dict]:
    out = run(["nvidia-smi", f"--query-gpu={','.join(GPU_FIELDS)}", "--format=csv,noheader"])
    rows = []
    for line in out.splitlines():
        vals = [v.strip() for v in line.split(",")]
        if len(vals) != len(GPU_FIELDS):
            rows.append({"unparsed": line})
            continue
        row = dict(zip(GPU_FIELDS, vals, strict=True))
        row["uuid_hash"] = short_hash(row.pop("uuid"))
        rows.append(row)
    return rows


def cpu_model() -> str:
    p = Path("/proc/cpuinfo")
    if p.exists():
        m = re.search(r"^model name\s*:\s*(.+)$", p.read_text(), re.M)
        if m:
            return m.group(1).strip()
    if sys.platform == "darwin":
        return run(["sysctl", "-n", "machdep.cpu.brand_string"])
    return platform.processor()


def ram_gb() -> float | None:
    p = Path("/proc/meminfo")
    if p.exists():
        m = re.search(r"^MemTotal:\s*(\d+) kB", p.read_text(), re.M)
        if m:
            return round(int(m.group(1)) / 1024**2, 1)
    if sys.platform == "darwin":
        try:
            return round(int(run(["sysctl", "-n", "hw.memsize"])) / 1024**3, 1)
        except ValueError:
            return None
    return None


def python_pkg_version(mod: str) -> str | None:
    out = run([sys.executable, "-c", f"import {mod}; print({mod}.__version__)"])
    return out if out and not out.startswith("<error") and "Error" not in out else None


def main() -> int:
    out_path = Path(sys.argv[1])
    smi_q = run(["nvidia-smi", "-q"])
    cuda = re.search(r"CUDA Version\s*:\s*(\S+)", smi_q)
    torch_cuda = run([sys.executable, "-c", "import torch; print(torch.version.cuda)"])
    env = {
        "captured_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gpus": gpus(),
        "driver_cuda_version": cuda.group(1) if cuda else None,
        "torch_cuda_version": torch_cuda if re.fullmatch(r"[\d.]+", torch_cuda or "") else None,
        "torch_version": python_pkg_version("torch"),
        "vllm_version": python_pkg_version("vllm") or (run(["vllm", "--version"]) or None),
        "vllm_cli": shutil.which("vllm"),
        "python": sys.version.split()[0],
        "cpu_model": cpu_model(),
        "cpu_count": __import__("os").cpu_count(),
        "ram_gb": ram_gb(),
        "kernel": platform.release(),
        "hostname_hash": short_hash(platform.node()),
        "nvidia_smi_q": smi_q,
    }
    out_path.write_text(json.dumps(env, indent=2, sort_keys=True) + "\n")
    print(f"[env] wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
