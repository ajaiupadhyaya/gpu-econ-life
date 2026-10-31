import json

import httpx
import pytest

from gel.collect.http import Throttle, get_with_backoff, user_agent, write_raw


def test_user_agent_uses_contact_email_only_when_set(monkeypatch):
    monkeypatch.delenv("GEL_CONTACT_EMAIL", raising=False)
    assert "@" not in user_agent()
    monkeypatch.setenv("GEL_CONTACT_EMAIL", "someone@example.org")
    assert "someone@example.org" in user_agent()


def test_write_raw_creates_sidecar_with_required_fields(tmp_path):
    path = tmp_path / "x" / "page.json"
    write_raw(path, b"{}", url="https://example.org/a", status=200)
    assert path.read_bytes() == b"{}"
    sidecar = json.loads(path.with_name("page.json.json").read_text())
    assert sidecar["source_url"] == "https://example.org/a"
    assert sidecar["http_status"] == 200
    assert sidecar["retrieved_at"].endswith("Z")


def test_write_raw_is_append_only(tmp_path):
    path = tmp_path / "page.json"
    write_raw(path, b"first", url="https://example.org/a", status=200)
    with pytest.raises(FileExistsError):
        write_raw(path, b"second", url="https://example.org/a", status=200)
    assert path.read_bytes() == b"first"


def test_throttle_spaces_requests_per_host():
    now = {"t": 100.0}
    slept = []

    def fake_sleep(s):
        slept.append(s)
        now["t"] += s

    throttle = Throttle(min_interval=1.5, clock=lambda: now["t"], sleep=fake_sleep)
    throttle.wait("a.example")
    throttle.wait("a.example")
    throttle.wait("b.example")
    assert slept == [pytest.approx(1.5)]


def _client(statuses):
    calls = iter(statuses)

    def handler(request):
        return httpx.Response(next(calls), text="body")

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_backoff_retries_429_and_5xx_then_succeeds():
    slept = []
    with _client([429, 503, 200]) as client:
        resp = get_with_backoff(client, "https://a.example/x", sleep=slept.append, base_delay=2.0)
    assert resp.status_code == 200
    assert slept == [2.0, 4.0]


def test_backoff_does_not_retry_other_client_errors():
    slept = []
    with _client([404]) as client:
        resp = get_with_backoff(client, "https://a.example/x", sleep=slept.append)
    assert resp.status_code == 404
    assert slept == []


def test_backoff_gives_up_after_max_attempts():
    with _client([500, 500, 500]) as client:
        resp = get_with_backoff(client, "https://a.example/x", sleep=lambda s: None, max_attempts=3)
    assert resp.status_code == 500


def test_network_errors_are_retried_then_succeed():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) == 1:
            raise httpx.ReadTimeout("stalled", request=request)
        return httpx.Response(200, text="ok")

    slept = []
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        response = get_with_backoff(client, "https://a.example/x", sleep=slept.append)
    assert response.status_code == 200
    assert slept == [2.0]


def test_network_errors_are_raised_once_attempts_run_out():
    def handler(request):
        raise httpx.ConnectError("down", request=request)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(httpx.ConnectError),
    ):
        get_with_backoff(client, "https://a.example/x", sleep=lambda s: None, max_attempts=3)
