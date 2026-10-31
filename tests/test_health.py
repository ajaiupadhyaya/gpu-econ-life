import json

from gel.collect.health import check, main


def write_run(root, day, collectors):
    path = root / "data/interim/live/runs" / f"{day}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"day": day, "collectors": collectors}))


def ok(**providers):
    return {"status": "ok", "providers": providers}


def history(root, days=7, rows=100):
    for i in range(1, days + 1):
        write_run(root, f"2026-11-{i:02d}", {"azure": ok(azure=rows)})


def test_healthy_day_has_no_problems(tmp_path):
    history(tmp_path)
    write_run(tmp_path, "2026-11-08", {"azure": ok(azure=98)})
    assert check(tmp_path, "2026-11-08") == []


def test_row_count_collapse_is_flagged(tmp_path):
    history(tmp_path)
    write_run(tmp_path, "2026-11-08", {"azure": ok(azure=40)})
    problems = check(tmp_path, "2026-11-08")
    assert len(problems) == 1
    assert "azure" in problems[0] and "40" in problems[0]


def test_provider_disappearing_is_flagged(tmp_path):
    history(tmp_path)
    write_run(tmp_path, "2026-11-08", {"other": ok(other=5)})
    assert any("azure" in p for p in check(tmp_path, "2026-11-08"))


def test_failed_collector_is_flagged(tmp_path):
    write_run(tmp_path, "2026-11-08", {"azure": {"status": "failed", "error": "boom"}})
    assert any("boom" in p for p in check(tmp_path, "2026-11-08"))


def test_missing_run_is_flagged(tmp_path):
    assert any("no run" in p for p in check(tmp_path, "2026-11-08"))


def test_first_day_without_history_is_not_a_problem(tmp_path):
    write_run(tmp_path, "2026-11-08", {"azure": ok(azure=10)})
    assert check(tmp_path, "2026-11-08") == []


def test_baseline_uses_only_the_seven_days_before(tmp_path):
    write_run(tmp_path, "2026-10-01", {"azure": ok(azure=1000)})
    history(tmp_path)
    write_run(tmp_path, "2026-11-08", {"azure": ok(azure=98)})
    assert check(tmp_path, "2026-11-08") == []


def test_main_exit_codes(tmp_path):
    write_run(tmp_path, "2026-11-08", {"azure": ok(azure=10)})
    assert main(["--day", "2026-11-08"], root=tmp_path) == 0
    assert main(["--day", "2026-11-09"], root=tmp_path) == 1
