#!/usr/bin/env bash
# 1 Hz GPU power logger. Runs for the whole of run_all.sh.
# Each nvidia-smi line is prefixed with the host's epoch milliseconds, so power samples and
# benchmark windows share one clock (nvidia-smi's own timestamp is local time with no zone).
#
# Usage: power_logger.sh <out.csv> <pidfile>
set -euo pipefail
OUT="$1"
PIDFILE="$2"
MS="${BENCH_POWER_MS:-1000}"
PY="${BENCH_STAMP_PYTHON:-python3}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

nvidia-smi -i 0 \
  --query-gpu=timestamp,index,power.draw,utilization.gpu,temperature.gpu,clocks.sm,memory.used \
  --format=csv,nounits -lms "$MS" \
  > >("$PY" -u "$HERE/stamp_lines.py" > "$OUT") &
echo $! > "$PIDFILE"
exec 2>/dev/null   # the kill at shutdown is expected; drop the job-status notice
wait || true
