from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class SearchRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)

    def list_initiative_search_rows(
        self,
        owner_user_id: str | None = None,
        workstream_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self._client.table("initiatives")
            .select(
                "id, name, initiative_code, summary, rag_status, stage, "
                "owner_id, group_owner_id, workstream_id, workstreams(name)"
            )
            .eq("tenant_id", self._tenant_id)
            .is_("archived_at", "null")
            .order("initiative_code")
            .limit(1000)
        )
        if owner_user_id:
            query = query.or_(f"owner_id.eq.{owner_user_id},group_owner_id.eq.{owner_user_id}")
        if workstream_ids:
            query = query.in_("workstream_id", workstream_ids)
        result = query.execute()
        return result.data or []

    def list_milestone_search_rows(
        self,
        owner_user_id: str | None = None,
        workstream_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self._client.table("milestones")
            .select(
                "id, name, description, status, priority, planned_end, initiative_id, owner_id, "
                "initiatives!inner(id, name, initiative_code, owner_id, group_owner_id, workstream_id)"
            )
            .eq("tenant_id", self._tenant_id)
            .order("planned_end")
            .limit(1000)
        )
        if workstream_ids:
            query = query.in_("initiatives.workstream_id", workstream_ids)
        result = query.execute()
        return result.data or []

    def list_risk_search_rows(
        self,
        owner_user_id: str | None = None,
        workstream_ids: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self._client.table("risks")
            .select(
                "id, description, type, impact, likelihood, rating, status, initiative_id, owner_id, "
                "initiatives!inner(id, name, initiative_code, owner_id, group_owner_id, workstream_id)"
            )
            .eq("tenant_id", self._tenant_id)
            .order("created_at", desc=True)
            .limit(1000)
        )
        if workstream_ids:
            query = query.in_("initiatives.workstream_id", workstream_ids)
        result = query.execute()
        return result.data or []

    def list_user_workstream_ids(self, user_id: str) -> list[str]:
        result = (
            self._client.table("user_workstreams")
            .select("workstream_id")
            .eq("tenant_id", self._tenant_id)
            .eq("user_id", user_id)
            .execute()
        )
        return [str(row["workstream_id"]) for row in result.data or [] if row.get("workstream_id")]

    def list_user_search_rows(self) -> list[dict[str, Any]]:
        result = (
            self._client.table("users")
            .select("id, display_name, title, department, market, role, status")
            .eq("tenant_id", self._tenant_id)
            .eq("status", "active")
            .order("display_name")
            .limit(1000)
            .execute()
        )
        return result.data or []
