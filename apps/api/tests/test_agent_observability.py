from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import UUID, uuid4

from app.jobs import agent_metrics
from app.services import agent_observability as observability_module
from app.services.agent_observability import AgentObservabilityService

TENANT_ID = uuid4()


class FakeAgentObservabilityRepository:
    def __init__(self, client: object, tenant_id: UUID) -> None:
        self.saved: list[dict] = []

    def list_audit_logs_for_day(self, metric_date: date) -> list[dict]:
        return [
            {
                "agent_id": "netra",
                "latency_ms": 100,
                "confidence": "0.8000",
                "requires_review": True,
                "human_action": None,
            },
            {
                "agent_id": "netra",
                "latency_ms": 200,
                "confidence": "0.9000",
                "requires_review": False,
                "human_action": "approved",
            },
            {
                "agent_id": "karya",
                "latency_ms": None,
                "confidence": None,
                "requires_review": True,
                "human_action": None,
            },
        ]

    def list_corrections_for_day(self, metric_date: date) -> list[dict]:
        return [
            {"agent_id": "netra"},
            {"agent_id": "netra"},
            {"agent_id": "prahari"},
        ]

    def upsert_metric(self, payload: dict) -> dict:
        self.saved.append(payload)
        return payload


def test_agent_metrics_rollup_counts_audits_and_corrections(monkeypatch) -> None:
    repo = FakeAgentObservabilityRepository(None, TENANT_ID)
    monkeypatch.setattr(
        observability_module,
        "AgentObservabilityRepository",
        lambda client, tenant_id: repo,
    )

    rows = AgentObservabilityService(SimpleNamespace(), TENANT_ID).rollup_daily_metrics(
        date(2026, 5, 16)
    )

    netra = next(row for row in rows if row["agent_id"] == "netra")
    karya = next(row for row in rows if row["agent_id"] == "karya")
    prahari = next(row for row in rows if row["agent_id"] == "prahari")
    assert netra["total_runs"] == 2
    assert netra["auto_approved"] == 1
    assert netra["hitl_required"] == 1
    assert netra["correction_count"] == 2
    assert netra["avg_latency_ms"] == "150.00"
    assert netra["avg_confidence"] == "0.8500"
    assert karya["total_runs"] == 1
    assert prahari["total_runs"] == 0
    assert prahari["correction_count"] == 1


def test_weekly_quality_report_flags_threshold_breach() -> None:
    rows = [
        {"agent_id": "netra", "total_runs": 20, "correction_count": 1, "correction_rate_pct": 5.0},
        {
            "agent_id": "karya",
            "total_runs": 10,
            "correction_count": 2,
            "correction_rate_pct": 20.0,
        },
    ]
    breached = [
        row
        for row in rows
        if row["correction_rate_pct"] > agent_metrics.CORRECTION_RATE_INCIDENT_THRESHOLD
    ]

    report = agent_metrics._render_quality_report(date(2026, 5, 11), rows, breached)

    assert "Weekly Agent Quality Report" in report
    assert "| karya | 10 | 2 | 20.0% |" in report
    assert "P3 threshold breached" in report


def test_weekly_quality_report_skips_github_without_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    result = agent_metrics._post_github_comment(17, "body")

    assert result == {"status": "skipped", "reason": "GITHUB_TOKEN not configured"}
