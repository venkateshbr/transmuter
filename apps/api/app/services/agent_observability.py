"""Agent observability rollups."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from supabase import Client

from app.repositories.agent_observability import AgentObservabilityRepository


class AgentObservabilityService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = AgentObservabilityRepository(client, tenant_id)

    def rollup_daily_metrics(self, metric_date: date | None = None) -> list[dict[str, Any]]:
        target_date = metric_date or (datetime.now(UTC).date() - timedelta(days=1))
        audits = self._repo.list_audit_logs_for_day(target_date)
        corrections = self._repo.list_corrections_for_day(target_date)
        corrections_by_agent: dict[str, int] = defaultdict(int)
        for correction in corrections:
            corrections_by_agent[correction["agent_id"]] += 1

        rows: list[dict[str, Any]] = []
        for agent_id in sorted({row["agent_id"] for row in audits} | set(corrections_by_agent)):
            agent_audits = [row for row in audits if row["agent_id"] == agent_id]
            total_runs = len(agent_audits)
            latencies = [
                int(row["latency_ms"])
                for row in agent_audits
                if row.get("latency_ms") is not None
            ]
            confidences = [
                Decimal(str(row["confidence"]))
                for row in agent_audits
                if row.get("confidence") is not None
            ]
            payload = {
                "metric_date": target_date.isoformat(),
                "agent_id": agent_id,
                "total_runs": total_runs,
                "auto_approved": sum(
                    1 for row in agent_audits if row.get("human_action") == "approved"
                ),
                "hitl_required": sum(1 for row in agent_audits if row.get("requires_review")),
                "correction_count": corrections_by_agent[agent_id],
                "avg_latency_ms": _avg_int(latencies),
                "avg_confidence": _avg_decimal(confidences),
            }
            saved = self._repo.upsert_metric(payload)
            rows.append(saved or payload)
        return rows

    def weekly_quality_rows(self, start_date: date) -> list[dict[str, Any]]:
        metrics = self._repo.list_metrics_since(start_date)
        by_agent: dict[str, dict[str, Any]] = {}
        for metric in metrics:
            row = by_agent.setdefault(
                metric["agent_id"],
                {
                    "agent_id": metric["agent_id"],
                    "total_runs": 0,
                    "correction_count": 0,
                },
            )
            row["total_runs"] += int(metric.get("total_runs") or 0)
            row["correction_count"] += int(metric.get("correction_count") or 0)
        rows = []
        for row in by_agent.values():
            total_runs = row["total_runs"]
            correction_count = row["correction_count"]
            correction_rate_pct = (
                round((correction_count / total_runs) * 100, 1) if total_runs else 0.0
            )
            rows.append({**row, "correction_rate_pct": correction_rate_pct})
        return sorted(rows, key=lambda item: item["correction_rate_pct"], reverse=True)


def _avg_int(values: list[int]) -> str | None:
    if not values:
        return None
    return f"{sum(values) / len(values):.2f}"


def _avg_decimal(values: list[Decimal]) -> str | None:
    if not values:
        return None
    return f"{sum(values) / Decimal(len(values)):.4f}"
