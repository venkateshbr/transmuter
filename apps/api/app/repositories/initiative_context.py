"""Initiative context repository for AI skill inputs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class InitiativeContextRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def get_initiative(self, initiative_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("initiatives")
            .select("id, name, stage, rag_status, priority, summary")
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def list_milestones(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("milestones")
            .select("id, name, status, priority, planned_end, actual_end")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        return result.data or []

    def list_kpis(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("kpis")
            .select("id, name")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        return result.data or []

    def list_kpi_entries(self, kpi_ids: list[str]) -> list[dict[str, Any]]:
        if not kpi_ids:
            return []
        result = (
            self._c.table("kpi_entries")
            .select("kpi_id, year, quarter, value_base, value_actual")
            .eq("tenant_id", self._tid)
            .in_("kpi_id", kpi_ids)
            .execute()
        )
        return result.data or []

    def list_risks(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("risks")
            .select("id, description, status, impact, rating, created_at")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        return result.data or []

    def list_financial_entries(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("financial_entries")
            .select("year, quarter, revenue_uplift_base, revenue_uplift_actual")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        return result.data or []

    def list_cost_lines(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("financial_cost_lines")
            .select("year, quarter, amount_plan, amount_actual")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        return result.data or []

    def get_last_status_update(self, initiative_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("status_updates")
            .select("rag_status, submitted_at, summary")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("is_draft", False)
            .order("submitted_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
