"""Calibrate P3's hardware inputs from the P1 benchmark (handoff 5.2, Decisions 8 and 9).

Reads data/interim/bench/bench_windows.parquet and writes data/processed/p3_calibration.json:
per GPU at the operating concurrency, throughput q (output tokens/s), loaded board power w_load,
idle board power w_idle and efficiency eta (tokens/J); plus the per-generation efficiency step
G and power step used to project future generations.

Decision 9: the operating point is concurrency 32 with each GPU's best available precision
(the handoff's "economically realistic" comparison); BF16-only figures are written alongside as
the like-for-like alternative. The primary generation step is A100 -> H100 (Ampere -> Hopper,
the only true architecture step in the sample). H100 -> H200 is a same-architecture refresh and
is reported as a lower-bound sensitivity, not used for mu_G.

Usage: uv run python -m gel.models.p3_calibration
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

WINDOWS = Path("data/interim/bench/bench_windows.parquet")
OUT = Path("data/processed/p3_calibration.json")
OPERATING_CONCURRENCY = 32


def gpu_points(windows: pl.DataFrame, concurrency: int, best: bool) -> dict[str, dict]:
    w = windows.filter(~pl.col("dry_run") & (pl.col("concurrency") == concurrency))
    idle = (
        windows.filter(~pl.col("dry_run"))
        .group_by("gpu_label")
        .agg(pl.col("idle_watts_after_mode").mean().alias("w_idle"))
    )
    agg = (
        w.group_by(["gpu_label", "chip_id", "precision_mode", "run_id"])
        .agg(
            pl.col("output_tok_per_s").mean().alias("q"),
            pl.col("mean_watts_active").mean().alias("w_load"),
            pl.col("tokens_per_joule").mean().alias("eta"),
            pl.len().alias("n_repeats"),
        )
        .join(idle, on="gpu_label")
    )
    if best:
        agg = agg.sort("q", descending=True).group_by("gpu_label", maintain_order=True).first()
    else:
        agg = agg.filter(pl.col("precision_mode") == "bf16")
    return {r["gpu_label"]: r for r in agg.iter_rows(named=True)}


def step(points: dict, a: str, b: str) -> dict | None:
    if a not in points or b not in points:
        return None
    pa, pb = points[a], points[b]
    return {
        "from": a,
        "to": b,
        "eta_ratio": pb["eta"] / pa["eta"],
        "log_eta_ratio": math.log(pb["eta"] / pa["eta"]),
        "power_ratio": pb["w_load"] / pa["w_load"],
    }


def calibrate(windows: pl.DataFrame) -> dict:
    out = {
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": str(WINDOWS),
        "operating_concurrency": OPERATING_CONCURRENCY,
        "run_ids": sorted(windows.filter(~pl.col("dry_run"))["run_id"].unique().to_list()),
    }
    for name, best in (("best_available", True), ("bf16", False)):
        pts = gpu_points(windows, OPERATING_CONCURRENCY, best)
        primary = step(pts, "A100_SXM", "H100_SXM")
        refresh = step(pts, "H100_SXM", "H200_SXM")
        out[name] = {
            "gpus": {
                k: {
                    f: v[f]
                    for f in (
                        "chip_id",
                        "precision_mode",
                        "q",
                        "w_load",
                        "w_idle",
                        "eta",
                        "n_repeats",
                    )
                }
                | {"idle_share": v["w_idle"] / v["w_load"]}
                for k, v in pts.items()
            },
            "generation_step_primary": primary,
            "generation_step_refresh": refresh,
            "mu_G": primary["log_eta_ratio"] if primary else None,
            "power_step": primary["power_ratio"] if primary else None,
        }
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Calibrate P3 hardware inputs from P1.")
    ap.add_argument("--windows", type=Path, default=WINDOWS)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)
    cal = calibrate(pl.read_parquet(args.windows))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(cal, indent=2) + "\n")
    print(f"wrote {args.out}")
    for name in ("best_available", "bf16"):
        c = cal[name]
        print(
            f"[{name}] mu_G={c['mu_G']:.4f} (eta x{math.exp(c['mu_G']):.3f} per generation), "
            f"power step x{c['power_step']:.3f}"
        )
        if c["generation_step_refresh"]:
            print(f"  refresh H100->H200 eta x{c['generation_step_refresh']['eta_ratio']:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
