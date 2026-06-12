"""Tenant bootstrap shell defaults for blank organizations."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from supabase import Client

DEFAULT_ORG_SETTINGS: dict[str, Any] = {
    "nudge_overdue_days": 7,
    "nudge_nuclear_days": 14,
    "strategic_parameters": {
        "markets": [],
        "themes": [],
        "tags": [],
    },
}


class TenantBootstrapService:
    """Create the minimal tenant shell without business-specific configuration."""

    def __init__(self, client: Client) -> None:
        self._client = client

    def bootstrap_tenant(self, tenant_id: UUID | str) -> dict[str, int]:
        tid = str(tenant_id)
        return {
            "settings": self._bootstrap_settings(tid),
            "financial_groups": 0,
            "financial_items": 0,
            "gate_criteria": 0,
            "stage_gate_definitions": 0,
        }

    def _bootstrap_settings(self, tenant_id: str) -> int:
        row = (
            self._client.table("organizations")
            .select("id,settings")
            .eq("id", tenant_id)
            .maybe_single()
            .execute()
        )
        if not row or not row.data:
            return 0
        current = row.data.get("settings") or {}
        settings = self._merge_defaults(current, DEFAULT_ORG_SETTINGS)
        if settings == current:
            return 0
        self._client.table("organizations").update(
            {"settings": settings, "updated_at": datetime.now(UTC).isoformat()}
        ).eq("id", tenant_id).execute()
        return 1

    def _merge_defaults(self, current: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
        merged = {**current}
        for key, value in defaults.items():
            if key not in merged:
                merged[key] = value
            elif isinstance(value, dict) and isinstance(merged[key], dict):
                merged[key] = self._merge_defaults(merged[key], value)
        return merged
