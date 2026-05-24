from __future__ import annotations

from time import perf_counter

from app.core.config import settings
from app.core.observability import (
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
