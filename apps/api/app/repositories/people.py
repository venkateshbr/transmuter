"""People repository — tenant-scoped Supabase data access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class PeopleRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_users(
        self,
        *,
        role: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        query = self._c.table("users").select("*").eq("tenant_id", self._tid)
        if role:
            query = query.eq("role", role)
        if status:
            query = query.eq("status", status)
        result = query.order("display_name").execute()
        rows = result.data or []
        if not search:
            return rows
        needle = search.lower()
        return [
            row
            for row in rows
            if needle in str(row.get("display_name") or "").lower()
            or needle in str(row.get("email") or "").lower()
            or needle in str(row.get("title") or "").lower()
        ]

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("users")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        result = (
            self._c.table("users")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("email", email)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def upsert_user(self, row: dict[str, Any]) -> dict[str, Any]:
        result = self._c.table("users").upsert(row).execute()
        return result.data[0] if result.data else row

    def update_user(self, user_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("users")
            .update(patch)
            .eq("tenant_id", self._tid)
            .eq("id", user_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def list_owned_initiatives(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("initiatives")
            .select("id, initiative_code, name, stage, rag_status, planned_end, pressure_score")
            .eq("tenant_id", self._tid)
            .eq("owner_id", user_id)
            .is_("archived_at", "null")
            .execute()
        )
        return result.data or []

    def list_owned_milestones(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("milestones")
            .select(
                "id, name, status, planned_end, pressure_score, initiatives(name, initiative_code)"
            )
            .eq("tenant_id", self._tid)
            .eq("owner_id", user_id)
            .neq("status", "complete")
            .execute()
        )
        return result.data or []

    def list_assigned_actions(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("action_items")
            .select("*, initiatives(name, initiative_code), meeting_sessions(meetings(name))")
            .eq("tenant_id", self._tid)
            .eq("assignee_id", user_id)
            .neq("status", "completed")
            .execute()
        )
        return result.data or []

    def list_user_workstreams(self, user_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("user_workstreams")
            .select("id, workstream_id, workstreams(id, name)")
            .eq("tenant_id", self._tid)
            .eq("user_id", user_id)
            .execute()
        )
        return result.data or []

    def replace_user_workstreams(
        self,
        user_id: str,
        workstream_ids: list[str],
    ) -> list[dict[str, Any]]:
        (
            self._c.table("user_workstreams")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("user_id", user_id)
            .execute()
        )
        rows = [
            {"tenant_id": self._tid, "user_id": user_id, "workstream_id": workstream_id}
            for workstream_id in workstream_ids
        ]
        if rows:
            self._c.table("user_workstreams").insert(rows).execute()
        return self.list_user_workstreams(user_id)

    def list_invites(self) -> list[dict[str, Any]]:
        result = (
            self._c.table("user_invites")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_invite(self, invite_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("user_invites")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", invite_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def get_pending_invite_by_email(self, email: str) -> dict[str, Any] | None:
        result = (
            self._c.table("user_invites")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("email", email)
            .eq("status", "pending")
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def list_pending_invites_by_email(self, email: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("user_invites")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("email", email)
            .eq("status", "pending")
            .execute()
        )
        return result.data or []

    def insert_invite(self, row: dict[str, Any]) -> dict[str, Any]:
        result = self._c.table("user_invites").insert(row).execute()
        return result.data[0] if result.data else row

    def update_invite(self, invite_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("user_invites")
            .update(patch)
            .eq("tenant_id", self._tid)
            .eq("id", invite_id)
            .execute()
        )
        return result.data[0] if result.data else {}
