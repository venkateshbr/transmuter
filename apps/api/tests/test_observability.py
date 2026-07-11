from __future__ import annotations

from time import perf_counter

import pytest
from fastapi import FastAPI

from app.core import observability
from app.core.config import settings
from app.core.observability import (
    configure_observability,
    metrics_snapshot,
    notify_p1_p2_error,
    record_agent_run,
    record_request_metrics,
    record_worker_job,
    record_worker_queue_depth,
)


def test_metrics_snapshot_includes_slo_agent_and_worker_metrics() -> None:
    started_at = perf_counter()

    record_request_metrics("GET", "/initiatives/123", 200, started_at)
    record_agent_run("portfolio_chat", "tenant-1", "generated", started_at, corrected=True)
    record_worker_job("notifications", "status_nudges.nudge_non_compliant", "succeeded", started_at)
    record_worker_queue_depth("notifications", 3)

    snapshot = metrics_snapshot()

    assert snapshot["service"] == settings.app_name
    assert snapshot["routes"]
    assert snapshot["agents"]
    assert snapshot["workers"]["jobs"]
    assert snapshot["workers"]["queue_depths"]["notifications"] == 3
    assert snapshot["slo"]["api_p99_ms_target"] == settings.api_p99_slo_ms
    assert snapshot["slo"]["agent_correction_rate_target"] == settings.agent_correction_rate_slo


def test_alert_webhook_masks_pii(monkeypatch) -> None:
    calls: list[dict] = []

    def fake_post(url: str, json: dict, timeout: int) -> None:
        calls.append({"url": url, "json": json, "timeout": timeout})

    monkeypatch.setattr(settings, "alert_webhook_url", "https://alerts.example.invalid/hook")
    monkeypatch.setattr("app.core.observability.httpx.post", fake_post)

    notify_p1_p2_error(
        source="api",
        message="Failure for user@example.com",
        severity="P1",
        context={"email": "owner@example.com", "path": "/auth/login"},
    )

    assert calls[0]["url"] == "https://alerts.example.invalid/hook"
    assert calls[0]["json"]["message"] == "Failure for [redacted]"
    assert calls[0]["json"]["context"]["email"] == "[redacted]"


def test_sentry_disables_request_bodies_and_frame_locals(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}
    logfire_instrumentation: dict = {}

    monkeypatch.setattr(observability, "_configured", False)
    monkeypatch.setattr(settings, "sentry_dsn", "https://public@example.invalid/1")
    monkeypatch.setattr(observability.sentry_sdk, "init", lambda **kwargs: captured.update(kwargs))
    monkeypatch.setattr(observability.logfire, "configure", lambda **_kwargs: None)
    monkeypatch.setattr(
        observability.logfire,
        "instrument_fastapi",
        lambda *_args, **kwargs: logfire_instrumentation.update(kwargs),
    )

    configure_observability(FastAPI())

    assert captured["send_default_pii"] is False
    assert captured["include_local_variables"] is False
    assert captured["max_request_body_size"] == "never"
    assert captured["before_send"] is observability._sentry_before_send
    assert captured["before_send_transaction"] is observability._sentry_before_send
    assert (
        "meeting-integrations/microsoft/oauth/callback" in logfire_instrumentation["excluded_urls"]
    )


@pytest.mark.parametrize(
    "path",
    [
        "/api/meeting-integrations/microsoft/oauth/callback",
        "/meeting-integrations/microsoft/oauth/callback",
    ],
)
def test_sentry_scrubs_oauth_callback_request_target_and_data(path: str) -> None:
    event = {
        "request": {
            "url": f"https://app.example.com{path}?code=secret-code&state=secret-state",
            "query_string": "code=secret-code&state=secret-state",
            "data": {"code": "secret-code", "state": "secret-state"},
            "cookies": {"binding": "secret-binding"},
            "headers": {
                "Authorization": "Bearer secret-token",
                "Cookie": "binding=secret-binding",
                "User-Agent": "test",
            },
        }
    }

    scrubbed = observability._sentry_before_send(event, {})

    request = scrubbed["request"]
    assert request["url"] == f"https://app.example.com{path}"
    assert "query_string" not in request
    assert "data" not in request
    assert "cookies" not in request
    assert request["headers"] == {"User-Agent": "test"}
    assert "secret" not in str(scrubbed)
