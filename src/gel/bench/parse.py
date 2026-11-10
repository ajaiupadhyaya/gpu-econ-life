"""Parse benchmark run directories (bench/run_all.sh output) into one tidy table.

One row per measured window: GPU x precision mode x concurrency x repeat. Raw files are only read.

Energy is integrated two ways:
  energy_j_window  over the whole wrapper window in windows.csv (includes the bench client's own
                   start-up: tokenizer load and prompt sampling, at near-idle power)
  energy_j_active  over [end - duration, end], where duration is vLLM's own benchmark timer.
                   This is the primary measure; its error is the client's post-processing tail
                   (computing metrics, writing the JSON), well under a second.

Usage:
  make bench-parse
  uv run python -m gel.bench.parse --root /tmp/dryrun --allow-dry-run --out /tmp/x.parquet
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import polars as pl

from gel.bench import energy, metrics

MARLIN_MARKER = "leveraging the Marlin kernel"

RESULT_FIELDS = {
    "completed": "completed",
    "failed": "failed",
    "duration": "duration_s",
    "total_input_tokens": "input_tokens",
    "total_output_tokens": "output_tokens",
    "request_throughput": "request_per_s",
    "output_throughput": "output_tok_per_s",
    "total_token_throughput": "total_tok_per_s",
    "mean_ttft_ms": "mean_ttft_ms",
    "p99_ttft_ms": "p99_ttft_ms",
    "mean_tpot_ms": "mean_tpot_ms",
    "p99_tpot_ms": "p99_tpot_ms",
    "mean_itl_ms": "mean_itl_ms",
    "p99_itl_ms": "p99_itl_ms",
}


class DryRunRefused(Exception):
    pass


@dataclass
class RunReport:
    run_dir: Path
    problems: list[str] = field(default_factory=list)
    n_windows: int = 0

    @property
    def ok(self) -> bool:
        return not self.problems


def _num(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return math.nan  # "[N/A]", "[Not Supported]", blank


def read_power(path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (epoch_ms, watts) from a stamped nvidia-smi CSV."""
    with path.open(newline="") as fh:
        rows = list(csv.reader(fh, skipinitialspace=True))
    if not rows:
        return np.array([]), np.array([])
    header = [h.strip() for h in rows[0]]
    i_t = header.index("epoch_ms")
    i_p = next(i for i, h in enumerate(header) if h.startswith("power.draw"))
    data = [r for r in rows[1:] if len(r) == len(header)]
    t = np.array([_num(r[i_t]) for r in data])
    p = np.array([_num(r[i_p]) for r in data])
    return t, p


def parse_run(run_dir: Path, allow_dry_run: bool = False) -> tuple[pl.DataFrame, RunReport]:
    run_dir = Path(run_dir)
    report = RunReport(run_dir)
    meta = json.loads((run_dir / "run_meta.json").read_text())
    if meta.get("dry_run") and not allow_dry_run:
        raise DryRunRefused(f"{run_dir} is a dry run (stub data); pass allow_dry_run=True")
    env = json.loads((run_dir / "env.json").read_text())
    cfg = meta["config_snapshot"]
    max_gap = float(cfg["power"]["max_gap_s"])
    t_ms, watts = read_power(run_dir / "power.csv")
    if len(t_ms) == 0:
        report.problems.append("power.csv is empty")

    marlin = {}
    for mode in meta["precision_modes"]:
        log = run_dir / "logs" / f"server_{mode}.log"
        marlin[mode] = log.exists() and MARLIN_MARKER in log.read_text(errors="replace")

    confounds = list(meta.get("confounds", []))
    got_vllm = str(env.get("vllm_version") or "")
    if got_vllm.split("+")[0] != meta["vllm_version_expected"] and not meta.get("dry_run"):
        confounds.append(f"vLLM {got_vllm} != expected {meta['vllm_version_expected']}")

    with (run_dir / "windows.csv").open(newline="") as fh:
        windows = list(csv.DictReader(fh))

    idle = {}
    for w in windows:
        if w["phase"] == "idle":
            e = energy.integrate_window(
                t_ms, watts, int(w["start_epoch_ms"]), int(w["end_epoch_ms"]), max_gap
            )
            idle[w["mode"]] = e.mean_watts

    rows = []
    for w in windows:
        if w["phase"] != "measure":
            continue
        report.n_windows += 1
        mode, c, r = w["mode"], int(w["concurrency"]), int(w["repeat"])
        label = f"{mode} c={c} r={r}"
        start, end = int(w["start_epoch_ms"]), int(w["end_epoch_ms"])
        row = {
            "run_id": meta["run_id"],
            "gpu_label": meta["gpu_label"],
            "chip_id": meta["chip_id"],
            "arch": meta["arch"],
            "provider": meta["provider"],
            "cloud_tier": meta["cloud_tier"],
            "price_paid_per_hr": float(meta["price_per_hr_usd"]),
            "model": meta["model"],
            "vllm_version": got_vllm,
            "precision_mode": mode,
            "concurrency": c,
            "repeat": r,
            "num_prompts": int(w["num_prompts"]),
            "exit_code": int(w["exit_code"] or -1),
            "window_start_ms": start,
            "window_end_ms": end,
            "fp8_marlin_detected": marlin.get(mode, False),
            "dry_run": bool(meta.get("dry_run")),
        }
        if row["exit_code"] != 0:
            report.problems.append(f"{label}: bench exited {row['exit_code']}")
        try:
            res = json.loads((run_dir / w["result_file"]).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            report.problems.append(f"{label}: result JSON unreadable ({exc})")
            res = {}
        for src, dst in RESULT_FIELDS.items():
            v = res.get(src)
            row[dst] = float(v) if isinstance(v, int | float) else math.nan
        if res and int(res.get("completed", 0)) != row["num_prompts"]:
            report.problems.append(
                f"{label}: completed {res.get('completed')} of {row['num_prompts']} requests"
            )

        ew = energy.integrate_window(t_ms, watts, start, end, max_gap)
        dur_ms = row["duration_s"] * 1000.0
        a_start = max(start, end - dur_ms) if math.isfinite(dur_ms) else math.nan
        ea = (
            energy.integrate_window(t_ms, watts, a_start, end, max_gap)
            if math.isfinite(a_start)
            else energy.WindowEnergy(math.nan, math.nan, 0, math.nan, False)
        )
        if not (ew.covered and ea.covered):
            report.problems.append(
                f"{label}: power log does not cover the window (max gap {ew.max_gap_s})"
            )
        row.update(
            {
                "energy_j_window": ew.joules,
                "mean_watts_window": ew.mean_watts,
                "energy_j_active": ea.joules,
                "mean_watts_active": ea.mean_watts,
                "power_max_gap_s": ew.max_gap_s,
                "power_covered": ew.covered and ea.covered,
                "idle_watts_after_mode": idle.get(mode, math.nan),
                "tokens_per_joule": metrics.tokens_per_joule(row["output_tokens"], ea.joules),
                "cost_per_mtok_paid": metrics.cost_per_mtok(
                    row["price_paid_per_hr"], row["output_tok_per_s"]
                ),
            }
        )
        ec = cfg["energy_cost"]
        row["energy_cost_per_mtok"] = metrics.energy_cost_per_mtok(
            ea.joules, row["output_tokens"], ec["electricity_usd_per_kwh"], ec["pue"]
        )
        row["confounds"] = "; ".join(confounds)
        rows.append(row)

    if report.n_windows == 0:
        report.problems.append("no measured windows")
    wl = cfg["workload"]
    expected = len(meta["completed_modes"]) * len(wl["concurrency"]) * wl["repeats"]
    if report.n_windows != expected:
        report.problems.append(f"{report.n_windows} measured windows, expected {expected}")
    for s in meta.get("skipped_modes", []):
        report.problems.append(f"mode {s['mode']} skipped: {s['reason']}")
    return pl.DataFrame(rows), report


def find_runs(root: Path) -> list[Path]:
    return sorted(p.parent for p in Path(root).glob("*/*/run_meta.json"))


def check_consistency(df: pl.DataFrame) -> list[str]:
    """Same-model rule: identical weights and vLLM version on every GPU."""
    issues = []
    for col in ("model", "vllm_version"):
        vals = df[col].unique().to_list()
        if len(vals) > 1:
            issues.append(f"runs disagree on {col}: {vals}")
    return issues


def summarize(df: pl.DataFrame) -> pl.DataFrame:
    """Mean and sd over repeats for each GPU x mode x concurrency."""
    keys = ["gpu_label", "chip_id", "precision_mode", "concurrency"]
    cols = [
        "output_tok_per_s",
        "total_tok_per_s",
        "request_per_s",
        "mean_ttft_ms",
        "p99_ttft_ms",
        "mean_tpot_ms",
        "p99_tpot_ms",
        "tokens_per_joule",
        "mean_watts_active",
        "cost_per_mtok_paid",
        "energy_cost_per_mtok",
    ]
    aggs = [pl.len().alias("n_repeats")]
    for c in cols:
        aggs += [pl.col(c).mean().alias(f"{c}_mean"), pl.col(c).std().alias(f"{c}_sd")]
    return df.group_by(keys).agg(aggs).sort(keys)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Parse benchmark run directories.")
    ap.add_argument("--root", type=Path, default=Path("data/raw/bench"))
    ap.add_argument("--out", type=Path, default=Path("data/interim/bench/bench_windows.parquet"))
    ap.add_argument("--allow-dry-run", action="store_true")
    args = ap.parse_args(argv)

    runs = find_runs(args.root)
    if not runs:
        print(f"no runs under {args.root}", file=sys.stderr)
        return 1
    frames, failed = [], False
    for run in runs:
        try:
            df, rep = parse_run(run, allow_dry_run=args.allow_dry_run)
        except DryRunRefused as exc:
            print(f"SKIP {exc}")
            continue
        status = "OK  " if rep.ok else "FAIL"
        print(f"{status} {run.name}: {rep.n_windows} windows, {len(df)} rows")
        for p in rep.problems:
            print(f"     - {p}")
        failed |= not rep.ok
        frames.append(df)
    if not frames:
        print("nothing parsed", file=sys.stderr)
        return 1
    df = pl.concat(frames, how="diagonal_relaxed")
    for issue in check_consistency(df):
        print(f"CONFOUND {issue}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(args.out)
    summarize(df).write_parquet(args.out.with_name(args.out.stem + "_summary.parquet"))
    print(f"wrote {args.out} ({len(df)} rows)")
    return 1 if failed or df.is_empty() else 0


if __name__ == "__main__":
    sys.exit(main())
