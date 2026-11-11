"""One shared matplotlib style for every figure (CLAUDE.md stack rule).

Palette: the dataviz skill's reference categorical slots, validated with its script for these
five slots in light mode (2026-11-11): all hard checks pass; three slots are below 3:1 contrast
on the surface, so figures carry direct labels and every figure has a CSV table beside it.
Colour follows the entity (GPU), assigned in fixed launch order, never by rank.
"""

from __future__ import annotations

import glob
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import polars as pl  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e2dd"
SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

# GPU label -> (chip id, display name), in launch order. Colours are fixed per GPU.
GPUS = {
    "A40": ("a40", "A40"),
    "A100_SXM": ("a100_80gb", "A100 80GB"),
    "H100_SXM": ("h100_sxm", "H100 SXM"),
    "L40S": ("l40s", "L40S"),
    "H200_SXM": ("h200", "H200 SXM"),
}
COLOR = {label: SLOTS[i] for i, label in enumerate(GPUS)}
EPOCH_NAMES = {
    "a40": "NVIDIA A40 PCIe",
    "a100_80gb": "NVIDIA A100 SXM4 80 GB",
    "h100_sxm": "NVIDIA H100 SXM5 80GB",
    "h200": "NVIDIA H200 SXM",
    "b200": "NVIDIA B200",
}


def release_dates() -> dict[str, str]:
    """chip_id -> release date: Epoch AI hardware data, plus hand-sourced dates for chips Epoch
    lacks (data/raw/manual/chip_dates.csv)."""
    epoch = pl.read_csv(
        max(glob.glob("data/raw/indices/epoch/*/*-ml_hardware.csv")), infer_schema_length=0
    )
    out = {}
    for chip, name in EPOCH_NAMES.items():
        hit = epoch.filter(pl.col("Hardware name") == name)
        if not hit.is_empty():
            out[chip] = hit["Release date"][0]
    manual = Path("data/raw/manual/chip_dates.csv")
    if manual.exists():
        for r in pl.read_csv(manual).iter_rows(named=True):
            out.setdefault(r["chip_id"], r["release_date"])
    return out


def apply() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": SURFACE,
            "axes.facecolor": SURFACE,
            "savefig.facecolor": SURFACE,
            "axes.edgecolor": INK_2,
            "axes.labelcolor": INK,
            "text.color": INK,
            "xtick.color": INK_2,
            "ytick.color": INK_2,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "lines.linewidth": 2.0,
            "lines.markersize": 6,
            "font.size": 9,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "legend.frameon": False,
            "savefig.dpi": 200,
            "figure.dpi": 100,
        }
    )
