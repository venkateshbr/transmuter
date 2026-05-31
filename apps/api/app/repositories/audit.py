"""Audit repository — system change logs."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from supabase import Client

PII_KEYS = {"email", "phone", "display_name", "admin_email", "organizer_email"}


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
        return self.log_change(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=actor_id,
            after_data=metadata or {},
        )

    def log_change(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_id: str,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> dict[str, Any]:
        data = {
            "tenant_id": self._tid,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "user_id": actor_id,
            "before_data": self._mask_pii(before_data) if before_data is not None else None,
            "after_data": self._mask_pii(after_data) if after_data is not None else None,
            "ip_address": ip_address,
        }
        result = self._c.table("audit_log").insert(data).execute()
        return result.data[0] if result.data else {}

    @classmethod
    def _mask_pii(cls, value: Any) -> Any:
        if isinstance(value, dict):
            masked: dict[str, Any] = {}
            for key, item in value.items():
                if key.lower() in PII_KEYS:
                    masked[key] = "[redacted]"
                else:
                    masked[key] = cls._mask_pii(item)
            return masked
        if isinstance(value, list):
            return [cls._mask_pii(item) for item in value]
        if isinstance(value, UUID | date | datetime | Decimal):
            return str(value)
        return value
