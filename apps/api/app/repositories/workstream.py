"""Workstream repository — tenant-scoped Supabase data access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class WorkstreamRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list(self) -> list[dict[str, Any]]:
        result = (
            self._c.table("workstreams")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("name")
            .execute()
        )
        return result.data or []

    def get(self, ws_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("workstreams")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", ws_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        data["tenant_id"] = self._tid
        result = self._c.table("workstreams").insert(data).execute()
        return result.data[0] if result.data else {}

    def update(self, ws_id: str, data: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("workstreams")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", ws_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, ws_id: str) -> None:
        (
            self._c.table("initiatives")
            .update({"workstream_id": None})
            .eq("tenant_id", self._tid)
            .eq("workstream_id", ws_id)
            .execute()
        )
        self._c.table("workstreams").delete().eq("tenant_id", self._tid).eq("id", ws_id).execute()
