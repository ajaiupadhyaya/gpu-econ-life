"""Benchmark parser: hand-built run directories, plus the full CPU dry run on stub binaries.

Everything here is test fixture or stub output. None of it is data.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from gel.bench import parse

ROOT = Path(__file__).resolve().parents[1]
CFG = yaml.safe_load((ROOT / "config" / "bench.yaml").read_text())


def make_run(tmp_path: Path, *, dry_run=False, drop_result=False, power_until_ms=12_000):
    """One bf16 mode, one window [1000, 11000] ms, constant 200 W at 1 Hz, vLLM duration 5 s."""
    cfg = json.loads(json.dumps(CFG))
    cfg["workload"]["concurrency"] = [8]
    cfg["workload"]["repeats"] = 1
    run = tmp_path / "H100_SXM" / "RUN1"
    (run / "results").mkdir(parents=True)
    (run / "logs").mkdir()
    meta = {
        "run_id": "RUN1",
        "gpu_label": "H100_SXM",
        "chip_id": "h100_sxm",
        "arch": "hopper",
        "price_per_hr_usd": 2.0,
        "provider": "test",
        "cloud_tier": "secure",
        "model": cfg["model"],
        "vllm_version_expected": "0.32.0",
        "precision_modes": ["bf16"],
        "completed_modes": ["bf16"],
        "skipped_modes": [],
        "confounds": [],
        "dry_run": dry_run,
        "config_snapshot": cfg,
    }
    (run / "run_meta.json").write_text(json.dumps(meta))
    (run / "env.json").write_text(json.dumps({"vllm_version": "0.32.0"}))
    lines = ["epoch_ms, timestamp, index, power.draw [W], utilization.gpu [%]"]
    lines += [f"{t}, x, 0, 200.00, 99" for t in range(0, power_until_ms + 1, 1000)]
    (run / "power.csv").write_text("\n".join(lines) + "\n")
    (run / "windows.csv").write_text(
        "mode,phase,concurrency,repeat,num_prompts,start_epoch_ms,end_epoch_ms,result_file,"
        "exit_code\nbf16,measure,8,1,160,1000,11000,results/bf16_c8_r1.json,0\n"
    )
    if not drop_result:
        (run / "results" / "bf16_c8_r1.json").write_text(
            json.dumps(
                {
                    "completed": 160,
                    "failed": 0,
                    "duration": 5.0,
                    "total_input_tokens": 81920,
                    "total_output_tokens": 40960,
                    "request_throughput": 32.0,
                    "output_throughput": 8192.0,
                    "total_token_throughput": 24576.0,
                    "mean_ttft_ms": 30.0,
                    "p99_ttft_ms": 60.0,
                    "mean_tpot_ms": 6.0,
                    "p99_tpot_ms": 9.0,
                }
            )
        )
    return run


def test_hand_built_run_energy_and_metrics(tmp_path):
    df, rep = parse.parse_run(make_run(tmp_path))
    assert rep.ok, rep.problems
    row = df.row(0, named=True)
    assert row["energy_j_window"] == pytest.approx(2000.0)  # 200 W * 10 s
    assert row["energy_j_active"] == pytest.approx(1000.0)  # 200 W * 5 s (vLLM duration)
    assert row["tokens_per_joule"] == pytest.approx(40960 / 1000.0)
    assert row["cost_per_mtok_paid"] == pytest.approx(2.0 / (8192 * 3600) * 1e6)
    # 1000 J / 40960 tok * 1e6 / 3.6e6 * 0.08 * 1.3
    assert row["energy_cost_per_mtok"] == pytest.approx(1000 / 40960 * 1e6 / 3.6e6 * 0.104)
    assert row["confounds"] == ""


def test_dry_run_is_refused_by_default(tmp_path):
    run = make_run(tmp_path, dry_run=True)
    with pytest.raises(parse.DryRunRefused):
        parse.parse_run(run)
    df, _ = parse.parse_run(run, allow_dry_run=True)
    assert df["dry_run"].to_list() == [True]


def test_missing_result_json_is_a_problem(tmp_path):
    _, rep = parse.parse_run(make_run(tmp_path, drop_result=True))
    assert any("unreadable" in p for p in rep.problems)


def test_power_log_that_stops_early_is_a_problem(tmp_path):
    _, rep = parse.parse_run(make_run(tmp_path, power_until_ms=9000))
    assert any("does not cover" in p for p in rep.problems)


def test_vllm_version_mismatch_is_recorded_as_confound(tmp_path):
    run = make_run(tmp_path)
    (run / "env.json").write_text(json.dumps({"vllm_version": "0.33.0"}))
    df, _ = parse.parse_run(run)
    assert "0.33.0" in df["confounds"][0]


def test_consistency_flags_mixed_models(tmp_path):
    a, _ = parse.parse_run(make_run(tmp_path / "a"))
    b, _ = parse.parse_run(make_run(tmp_path / "b"))
    b = b.with_columns(b["model"].str.replace("Llama", "Qwen"))
    import polars as pl

    assert parse.check_consistency(pl.concat([a, b]))


# ---- full CPU dry run of the pod harness ------------------------------------------------------


def run_dryrun(out: Path, **env_extra) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "STUB_BENCH_SLEEP_S": "0.3",
        "BENCH_POWER_MS": "50",
        "BENCH_IDLE_S": "0.5",
        **env_extra,
    }
    return subprocess.run(
        [str(ROOT / "bench" / "dryrun.sh"), str(out)],
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )


needs_bash = pytest.mark.skipif(
    shutil.which("bash") is None or shutil.which("uv") is None, reason="dry run needs bash and uv"
)


@pytest.mark.slow
@needs_bash
def test_full_dry_run_meets_smoke_test_acceptance(tmp_path):
    proc = run_dryrun(tmp_path)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert list(tmp_path.glob("results_CPU_STUB_*.tar.gz"))
    runs = parse.find_runs(tmp_path)
    assert len(runs) == 1
    df, rep = parse.parse_run(runs[0], allow_dry_run=True)
    # Handoff 3.3 acceptance: every JSON parses, power covers every window, table non-empty.
    assert rep.ok, rep.problems
    assert len(df) == 2 * 4 * 3
    assert df["power_covered"].all()
    assert df.filter(df["precision_mode"] == "fp8")["fp8_marlin_detected"].all()
    assert not df.filter(df["precision_mode"] == "bf16")["fp8_marlin_detected"].any()
    assert sorted(set(df["num_prompts"])) == [20, 160, 640]
    meta = json.loads((runs[0] / "run_meta.json").read_text())
    assert meta["dry_run"] is True and meta["utc_end"]


@pytest.mark.slow
@needs_bash
def test_dry_run_records_a_failed_mode_as_skipped(tmp_path):
    proc = run_dryrun(tmp_path, STUB_FAIL_MODE_FLAG="fp8")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    df, rep = parse.parse_run(parse.find_runs(tmp_path)[0], allow_dry_run=True)
    assert len(df) == 4 * 3
    assert set(df["precision_mode"]) == {"bf16"}
    assert any("mode fp8 skipped" in p for p in rep.problems)
