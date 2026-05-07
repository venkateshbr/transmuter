"""Audit repository — system change logs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from supabase import Client


class AuditRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        result = (
            self._c.table("audit_log")
            .select("*, users(display_name, email)")
            .eq("tenant_id", self._tid)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = {
            "tenant_id": self._tid,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": actor_id,
            "after_data": metadata or {},
        }
        result = self._c.table("audit_log").insert(data).execute()
        return result.data[0] if result.data else {}
