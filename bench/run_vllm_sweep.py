#!/usr/bin/env python3
"""Pod-side sweep driver: for each precision mode, serve the model, warm up, run every
concurrency x repeat, stop the server, idle. Called by run_all.sh; standard library + PyYAML only
(both ship in the vLLM image).

Writes into the run directory:
  run_meta.json            what was run, where, at what price; skips and confounds
  windows.csv              one row per timed window (warmup, measure, idle), epoch ms
  results/<mode>_c<C>_r<R>.json   vllm bench serve result files
  logs/server_<mode>.log, logs/bench_<mode>_c<C>_r<R>.log
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

import yaml

WINDOW_FIELDS = [
    "mode",
    "phase",
    "concurrency",
    "repeat",
    "num_prompts",
    "start_epoch_ms",
    "end_epoch_ms",
    "result_file",
    "exit_code",
]


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, obj: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


class Windows:
    def __init__(self, path: Path):
        self.path = path
        new = not path.exists()
        self.fh = path.open("a", newline="")
        self.w = csv.DictWriter(self.fh, fieldnames=WINDOW_FIELDS)
        if new:
            self.w.writeheader()
            self.fh.flush()

    def add(self, **row) -> None:
        self.w.writerow({k: row.get(k, "") for k in WINDOW_FIELDS})
        self.fh.flush()
        os.fsync(self.fh.fileno())


def wait_healthy(port: int, proc: subprocess.Popen, timeout_s: float) -> str:
    """Return '' when /health answers 200, else a reason string."""
    deadline = time.monotonic() + timeout_s
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return f"server exited with code {proc.returncode} before becoming healthy"
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return ""
        except OSError:
            pass
        time.sleep(1.0)
    return f"server not healthy after {timeout_s:.0f}s"


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=30)


def bench_cmd(
    cfg: dict, model: str, c: int, n: int, result_dir: Path, fname: str, meta: list[str]
) -> list[str]:
    wl, sv = cfg["workload"], cfg["serve"]
    return [
        "vllm",
        "bench",
        "serve",
        "--backend",
        "openai",
        "--model",
        model,
        "--host",
        "127.0.0.1",
        "--port",
        str(sv["port"]),
        "--dataset-name",
        wl["dataset"],
        "--random-input-len",
        str(wl["input_len"]),
        "--random-output-len",
        str(wl["output_len"]),
        "--max-concurrency",
        str(c),
        "--num-prompts",
        str(n),
        "--seed",
        str(wl["seed"]),
        "--percentile-metrics",
        "ttft,tpot,itl,e2el",
        "--metric-percentiles",
        "50,99",
        "--save-result",
        "--result-dir",
        str(result_dir),
        "--result-filename",
        fname,
        "--metadata",
        *meta,
    ]


def serve_cmd(cfg: dict, model: str, mode: str) -> list[str]:
    sv = cfg["serve"]
    cmd = [
        "vllm",
        "serve",
        model,
        "--dtype",
        sv["dtype"],
        "--max-model-len",
        str(sv["max_model_len"]),
        "--gpu-memory-utilization",
        str(sv["gpu_memory_utilization"]),
        "--seed",
        str(sv["seed"]),
        "--port",
        str(sv["port"]),
        "--host",
        "127.0.0.1",
    ]
    cmd.append("--enable-prefix-caching" if sv["prefix_caching"] else "--no-enable-prefix-caching")
    return cmd + list(cfg["modes"][mode])


def run_bench(cmd: list[str], log: Path) -> int:
    with log.open("w") as fh:
        return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT).returncode


def sweep(cfg: dict, out: Path, gpu_label: str, model: str, meta: dict) -> None:
    gpu = cfg["gpus"][gpu_label]
    wl = cfg["workload"]
    results, logs = out / "results", out / "logs"
    results.mkdir(parents=True, exist_ok=True)
    logs.mkdir(parents=True, exist_ok=True)
    win = Windows(out / "windows.csv")
    idle_s = float(os.environ.get("BENCH_IDLE_S") or wl["idle_after_mode_s"])
    meta_path = out / "run_meta.json"

    for mode in gpu["modes"]:
        print(f"[sweep] mode={mode}: starting server", flush=True)
        server_log = (logs / f"server_{mode}.log").open("w")
        proc = subprocess.Popen(
            serve_cmd(cfg, model, mode), stdout=server_log, stderr=subprocess.STDOUT
        )
        reason = wait_healthy(cfg["serve"]["port"], proc, cfg["serve"]["health_timeout_s"])
        if reason:
            print(f"[sweep] mode={mode}: SKIPPED ({reason})", flush=True)
            stop_server(proc)
            server_log.close()
            meta["skipped_modes"].append({"mode": mode, "reason": reason})
            write_json(meta_path, meta)
            continue

        tag = [f"gpu_label={gpu_label}", f"precision_mode={mode}"]
        fname = f"warmup_{mode}.json"
        t0 = now_ms()
        rc = run_bench(
            bench_cmd(
                cfg,
                model,
                wl["warmup_concurrency"],
                wl["warmup_prompts"],
                results,
                fname,
                [*tag, "phase=warmup"],
            ),
            logs / f"bench_warmup_{mode}.log",
        )
        win.add(
            mode=mode,
            phase="warmup",
            concurrency=wl["warmup_concurrency"],
            repeat=0,
            num_prompts=wl["warmup_prompts"],
            start_epoch_ms=t0,
            end_epoch_ms=now_ms(),
            result_file=f"results/{fname}",
            exit_code=rc,
        )

        for c in wl["concurrency"]:
            n = int(wl["prompts"][c])
            for r in range(1, wl["repeats"] + 1):
                fname = f"{mode}_c{c}_r{r}.json"
                print(f"[sweep] mode={mode} c={c} r={r} n={n}", flush=True)
                t0 = now_ms()
                rc = run_bench(
                    bench_cmd(
                        cfg, model, c, n, results, fname, [*tag, "phase=measure", f"repeat={r}"]
                    ),
                    logs / f"bench_{mode}_c{c}_r{r}.log",
                )
                win.add(
                    mode=mode,
                    phase="measure",
                    concurrency=c,
                    repeat=r,
                    num_prompts=n,
                    start_epoch_ms=t0,
                    end_epoch_ms=now_ms(),
                    result_file=f"results/{fname}",
                    exit_code=rc,
                )
                if rc != 0:
                    print(f"[sweep]   bench exited {rc}; see logs", flush=True)

        stop_server(proc)
        server_log.close()
        t0 = now_ms()
        time.sleep(idle_s)
        win.add(mode=mode, phase="idle", start_epoch_ms=t0, end_epoch_ms=now_ms())
        meta["completed_modes"].append(mode)
        write_json(meta_path, meta)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--gpu-label", required=True)
    ap.add_argument("--price", required=True, type=float)
    ap.add_argument("--provider", required=True)
    ap.add_argument("--tier", required=True)
    ap.add_argument("--model", default=None, help="override config model (records a confound)")
    args = ap.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    if args.gpu_label not in cfg["gpus"]:
        print(f"unknown GPU_LABEL {args.gpu_label}; known: {sorted(cfg['gpus'])}", file=sys.stderr)
        return 2
    model = args.model or cfg["model"]
    gpu = cfg["gpus"][args.gpu_label]
    dry_run = os.environ.get("BENCH_DRY_RUN") == "1"
    if args.gpu_label == "CPU_STUB" and not dry_run:
        print("CPU_STUB is for dry runs only (set BENCH_DRY_RUN=1)", file=sys.stderr)
        return 2

    meta = {
        "run_id": args.out.name,
        "gpu_label": args.gpu_label,
        "chip_id": gpu["chip_id"],
        "arch": gpu["arch"],
        "price_per_hr_usd": args.price,
        "provider": args.provider,
        "cloud_tier": args.tier,
        "model": model,
        "vllm_version_expected": cfg["vllm_version"],
        "precision_modes": list(gpu["modes"]),
        "completed_modes": [],
        "skipped_modes": [],
        "confounds": [],
        "git_commit": os.environ.get("BENCH_GIT_COMMIT", "unknown"),
        "utc_start": utc_now(),
        "utc_end": None,
        "dry_run": dry_run,
        "config_snapshot": cfg,
    }
    if model != cfg["model"]:
        meta["confounds"].append(f"model override: {model} instead of {cfg['model']}")
    write_json(args.out / "run_meta.json", meta)
    try:
        sweep(cfg, args.out, args.gpu_label, model, meta)
    finally:
        meta["utc_end"] = utc_now()
        write_json(args.out / "run_meta.json", meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
