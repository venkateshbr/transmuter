"""Agent observability repository."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from supabase import Client


class AgentObservabilityRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_audit_logs_for_day(self, metric_date: date) -> list[dict[str, Any]]:
        start = datetime.combine(metric_date, time.min).isoformat()
        end = datetime.combine(metric_date, time.max).isoformat()
        result = (
            self._c.table("agent_audit_log")
            .select("*")
            .eq("tenant_id", self._tid)
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        )
        return result.data or []

    def list_corrections_for_day(self, metric_date: date) -> list[dict[str, Any]]:
        start = datetime.combine(metric_date, time.min).isoformat()
        end = datetime.combine(metric_date, time.max).isoformat()
        result = (
            self._c.table("agent_corrections")
            .select("*")
            .eq("tenant_id", self._tid)
            .gte("created_at", start)
            .lte("created_at", end)
            .execute()
        )
        return result.data or []

    def upsert_metric(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        payload = {"tenant_id": self._tid, **payload}
        result = (
            self._c.table("agent_metrics")
            .upsert(payload, on_conflict="tenant_id,metric_date,agent_id")
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    def list_metrics_since(self, start_date: date) -> list[dict[str, Any]]:
        result = (
            self._c.table("agent_metrics")
            .select("*")
            .eq("tenant_id", self._tid)
            .gte("metric_date", start_date.isoformat())
            .execute()
        )
        return result.data or []
