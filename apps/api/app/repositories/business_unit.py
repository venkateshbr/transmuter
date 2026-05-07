"""Business Unit repository — tenant-scoped Supabase data access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class BusinessUnitRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list(self) -> list[dict[str, Any]]:
        result = (
            self._c.table("business_units")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("name")
            .execute()
        )
        return result.data or []

    def get(self, bu_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("business_units")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", bu_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        data["tenant_id"] = self._tid
        result = self._c.table("business_units").insert(data).execute()
        return result.data[0] if result.data else {}

    def update(self, bu_id: str, data: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("business_units")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", bu_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, bu_id: str) -> None:
        workstreams = (
            self._c.table("workstreams")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("business_unit_id", bu_id)
            .execute()
        )
        workstream_ids = [row["id"] for row in workstreams.data or []]
        if workstream_ids:
            (
                self._c.table("initiatives")
                .update({"workstream_id": None})
                .eq("tenant_id", self._tid)
                .in_("workstream_id", workstream_ids)
                .execute()
            )
        (
            self._c.table("workstreams")
            .update({"business_unit_id": None})
            .eq("tenant_id", self._tid)
            .eq("business_unit_id", bu_id)
            .execute()
        )
        (
            self._c.table("business_units")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", bu_id)
            .execute()
        )
