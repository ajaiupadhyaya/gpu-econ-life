#!/usr/bin/env bash
# P1 benchmark entry point. Runs ON the GPU pod.
#
# Usage:   ./bench/run_all.sh <GPU_LABEL> <PRICE_PER_HR_USD> <PROVIDER> <CLOUD_TIER>
# Example: ./bench/run_all.sh H100_SXM 2.99 runpod secure
#
# Environment:
#   HF_TOKEN             needed for gated models (Llama 3.1)
#   BENCH_OUT_ROOT       where run directories and the tarball go (default /workspace/bench_out,
#                        or <repo>/data/raw/bench when /workspace does not exist)
#   BENCH_GIT_COMMIT     commit the image was built from (set by the Dockerfile)
#   BENCH_MATMUL=1       also run the matmul microbenchmark
#   BENCH_SKIP_DOWNLOAD=1, BENCH_DRY_RUN=1, BENCH_PYTHON, BENCH_IDLE_S   used by bench/dryrun.sh
#
# Results MUST be copied off the pod before it is terminated: pod storage is ephemeral.
set -euo pipefail

if [[ $# -ne 4 ]]; then
  sed -n '2,6p' "$0"; exit 2
fi
GPU_LABEL="$1"; PRICE="$2"; PROVIDER="$3"; TIER="$4"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
PY="${BENCH_PYTHON:-python3}"
CONFIG="${BENCH_CONFIG:-$ROOT/config/bench.yaml}"
export TZ=UTC CUDA_VISIBLE_DEVICES=0

if [[ -z "${BENCH_OUT_ROOT:-}" ]]; then
  if [[ -d /workspace ]]; then BENCH_OUT_ROOT=/workspace/bench_out; else BENCH_OUT_ROOT="$ROOT/data/raw/bench"; fi
fi
if [[ "${BENCH_GIT_COMMIT:-}" == "" ]]; then
  BENCH_GIT_COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
  if [[ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ]]; then
    BENCH_GIT_COMMIT="${BENCH_GIT_COMMIT}-dirty"
  fi
fi
export BENCH_GIT_COMMIT

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
RUN_ID="${STAMP}_${GPU_LABEL}"
OUT="$BENCH_OUT_ROOT/$GPU_LABEL/$RUN_ID"
mkdir -p "$OUT/results" "$OUT/logs"
echo "[run_all] run directory: $OUT"

# 1. Power logger first, so the whole run (including model load) is on the record.
"$HERE/power_logger.sh" "$OUT/power.csv" "$OUT/logs/power_logger.pid" &
LOGGER_WRAPPER=$!
stop_logger() {
  sleep 2   # one more sample past the last window
  if [[ -f "$OUT/logs/power_logger.pid" ]]; then
    kill "$(cat "$OUT/logs/power_logger.pid")" 2>/dev/null || true
  fi
  wait "$LOGGER_WRAPPER" 2>/dev/null || true
  rm -f "$OUT/logs/power_logger.pid"
}
trap stop_logger EXIT

# 2. Environment.
"$PY" "$HERE/capture_env.py" "$OUT/env.json"

# 3. Weights before anything is timed.
MODEL="$("$PY" -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['model'])" "$CONFIG")"
if [[ "${BENCH_SKIP_DOWNLOAD:-0}" != "1" ]]; then
  echo "[run_all] downloading $MODEL"
  hf download "$MODEL" --exclude "original/*" > "$OUT/logs/download.log" 2>&1
fi

# 4. Sweep (writes run_meta.json and windows.csv).
"$PY" "$HERE/run_vllm_sweep.py" --config "$CONFIG" --out "$OUT" --gpu-label "$GPU_LABEL" \
  --price "$PRICE" --provider "$PROVIDER" --tier "$TIER"

# 6. Optional raw-hardware microbenchmark.
if [[ "${BENCH_MATMUL:-0}" == "1" ]]; then
  "$PY" "$HERE/matmul_tflops.py" "$OUT/matmul.json" > "$OUT/logs/matmul.log" 2>&1 || \
    echo "[run_all] matmul failed; see logs/matmul.log"
fi

stop_logger
trap - EXIT

# 7. Tarball.
TARBALL="$BENCH_OUT_ROOT/results_${GPU_LABEL}_${STAMP}.tar.gz"
tar -czf "$TARBALL" -C "$BENCH_OUT_ROOT/$GPU_LABEL" "$RUN_ID"
echo "[run_all] done. Copy this off the pod BEFORE terminating it:"
echo "$TARBALL"
