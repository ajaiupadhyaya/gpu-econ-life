#!/usr/bin/env python3
"""Prefix each stdin line with epoch milliseconds (header line gets 'epoch_ms')."""

import sys
import time

first = True
for line in sys.stdin:
    line = line.rstrip("\n")
    if not line:
        continue
    if first:
        sys.stdout.write(f"epoch_ms, {line}\n")
        first = False
    else:
        sys.stdout.write(f"{time.time_ns() // 1_000_000}, {line}\n")
    sys.stdout.flush()
