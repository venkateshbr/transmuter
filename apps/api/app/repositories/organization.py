"""Organization repository — tenant data access."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class OrganizationRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def get_organization(self) -> dict[str, Any] | None:
        result = (
            self._c.table("organizations")
            .select("*")
            .eq("id", self._tid)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def update_organization(self, patch: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("organizations")
            .update(patch)
            .eq("id", self._tid)
            .execute()
        )
        return result.data[0] if result.data else {}
