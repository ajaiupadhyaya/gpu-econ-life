"""Compare one day's rows per provider with the average of the seven days before it."""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WINDOW_DAYS = 7
MIN_RATIO = 0.5


def _load(root: Path, day: str) -> dict | None:
    path = root / "data/interim/live/runs" / f"{day}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _counts(run: dict) -> dict[tuple[str, str], int]:
    return {
        (collector, provider): rows
        for collector, result in run["collectors"].items()
        for provider, rows in result.get("providers", {}).items()
    }


def check(root: Path, day: str) -> list[str]:
    today = _load(root, day)
    if today is None:
        return [f"no run recorded for {day}"]
    problems = [
        f"{name} failed: {result.get('error')}"
        for name, result in today["collectors"].items()
        if result["status"] != "ok"
    ]
    current = date.fromisoformat(day)
    past = (_load(root, str(current - timedelta(days=i))) for i in range(1, WINDOW_DAYS + 1))
    baseline: dict[tuple[str, str], list[int]] = {}
    for run in filter(None, past):
        for key, rows in _counts(run).items():
            baseline.setdefault(key, []).append(rows)
    counts = _counts(today)
    for key, history in sorted(baseline.items()):
        average = sum(history) / len(history)
        rows = counts.get(key, 0)
        if rows < MIN_RATIO * average:
            problems.append(f"{key[1]} via {key[0]}: {rows} rows against a {average:.0f} average")
    return problems


def main(argv: list[str] | None = None, *, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--day", default=datetime.now(UTC).strftime("%Y-%m-%d"))
    args = parser.parse_args(argv)
    problems = check(root, args.day)
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(f"{args.day}: {'healthy' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
