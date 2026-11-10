#!/usr/bin/env bash
# CPU dry run of the whole pod pipeline on stub vllm / nvidia-smi binaries (handoff section 7,
# step 1). Writes to a temporary directory, never to data/raw. Every value produced is fake and
# the run is tagged dry_run: true, which the parser refuses by default.
#
# Usage: bench/dryrun.sh [out_root]     (default: a fresh mktemp directory)
# Env:   STUB_FAIL_MODE_FLAG=fp8 makes the stub server fail the FP8 mode (tests the skip path).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
OUT_ROOT="${1:-$(mktemp -d -t gel-bench-dryrun)}"

export PATH="$HERE/stubs:$PATH"
export BENCH_OUT_ROOT="$OUT_ROOT"
export BENCH_DRY_RUN=1 BENCH_SKIP_DOWNLOAD=1
export BENCH_PYTHON="${BENCH_PYTHON:-uv run --project $ROOT --quiet python}"
export BENCH_STAMP_PYTHON=python3
export BENCH_POWER_MS="${BENCH_POWER_MS:-100}"   # 10 Hz so short stub windows have samples
export BENCH_IDLE_S="${BENCH_IDLE_S:-1}"
export STUB_BENCH_SLEEP_S="${STUB_BENCH_SLEEP_S:-0.6}"

# BENCH_PYTHON holds a multi-word command, so run_all.sh must not quote it as one word.
# Wrap it in a tiny shim on PATH instead.
SHIM_DIR="$(mktemp -d -t gel-pyshim)"
printf '#!/usr/bin/env bash\nexec %s "$@"\n' "$BENCH_PYTHON" > "$SHIM_DIR/benchpy"
chmod +x "$SHIM_DIR/benchpy"
export BENCH_PYTHON="$SHIM_DIR/benchpy"

"$HERE/run_all.sh" CPU_STUB 0.00 dryrun none
rm -rf "$SHIM_DIR"
echo "[dryrun] output root: $OUT_ROOT"
