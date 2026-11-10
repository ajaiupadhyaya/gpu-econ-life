#!/usr/bin/env python3
"""Optional raw-hardware microbenchmark: 8192x8192 matmul, 10 warmup + 50 timed iterations.

BF16 everywhere; FP8 (torch._scaled_mm, e4m3) only on compute capability >= 8.9. Writes JSON.
"""

from __future__ import annotations

import json
import sys

import torch

N, WARMUP, ITERS = 8192, 10, 50


def time_op(fn) -> float:
    for _ in range(WARMUP):
        fn()
    torch.cuda.synchronize()
    start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
    start.record()
    for _ in range(ITERS):
        fn()
    end.record()
    torch.cuda.synchronize()
    return start.elapsed_time(end) / 1000.0 / ITERS  # seconds per matmul


def main() -> int:
    out = {"n": N, "warmup": WARMUP, "iters": ITERS, "device": torch.cuda.get_device_name(0)}
    cap = torch.cuda.get_device_capability(0)
    out["compute_capability"] = f"{cap[0]}.{cap[1]}"
    flops = 2 * N**3

    a = torch.randn(N, N, device="cuda", dtype=torch.bfloat16)
    b = torch.randn(N, N, device="cuda", dtype=torch.bfloat16)
    out["bf16_tflops"] = flops / time_op(lambda: a @ b) / 1e12

    if cap >= (8, 9) and hasattr(torch, "float8_e4m3fn"):
        a8 = a.to(torch.float8_e4m3fn)
        b8 = b.t().contiguous().t().to(torch.float8_e4m3fn)  # column-major second operand
        one = torch.ones((), device="cuda", dtype=torch.float32)
        try:
            sec = time_op(
                lambda: torch._scaled_mm(a8, b8, scale_a=one, scale_b=one, out_dtype=torch.bfloat16)
            )
            out["fp8_tflops"] = flops / sec / 1e12
        except RuntimeError as exc:
            out["fp8_tflops"] = None
            out["fp8_error"] = str(exc)[:500]
    else:
        out["fp8_tflops"] = None
        out["fp8_skip_reason"] = f"compute capability {cap} has no FP8 tensor cores"

    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=2)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
