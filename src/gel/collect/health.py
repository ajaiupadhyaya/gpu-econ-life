"""Compare the latest run's rows per provider with the average of the seven days before it.

A run is dated when it starts, so one crossing midnight still counts. If the newest run is too old,
the collector has stopped, which is a problem in itself.
"""

import argparse
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WINDOW_DAYS = 7
MIN_RATIO = 0.5
# Measured from the start of the run's UTC day, so a daily 06:10 run stays inside it.
MAX_AGE_HOURS = 54


def utc_now() -> datetime:
    return datetime.now(UTC)


def latest_day(names: list[str], now: datetime) -> str | None:
    """The newest run's day, or None if there is no run recent enough to trust."""
    days = sorted(name.removesuffix(".json") for name in names)
    if not days:
        return None
    start = datetime.fromisoformat(days[-1]).replace(tzinfo=UTC)
    return days[-1] if (now - start) <= timedelta(hours=MAX_AGE_HOURS) else None


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
    parser.add_argument("--day", help="default: the latest run")
    args = parser.parse_args(argv)
    runs = root / "data/interim/live/runs"
    names = [p.name for p in runs.glob("*.json")] if runs.exists() else []
    day = args.day or latest_day(names, utc_now())
    problems = check(root, day) if day else ["no recent run recorded"]
    for problem in problems:
        print(f"PROBLEM {problem}")
    print(f"{day}: {'healthy' if not problems else f'{len(problems)} problem(s)'}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
