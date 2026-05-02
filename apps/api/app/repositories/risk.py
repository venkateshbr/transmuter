"""Risk repository — Supabase data access."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID, uuid4

from supabase import Client


class RiskRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── Risks ────────────────────────────────────────────────────────

    def list(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("risks")
            .select("*, users!risks_owner_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def list_portfolio(
        self,
        status: str | None = None,
        type: str | None = None,
        rating: str | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self._c.table("risks")
            .select("*, users!risks_owner_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
        )
        if status:
            query = query.eq("status", status)
        if type:
            query = query.eq("type", type)
        if rating:
            query = query.eq("rating", rating)
            
        result = query.order("created_at", desc=True).execute()
        return result.data or []

    def get(self, risk_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("risks")
            .select("*, users!risks_owner_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("id", risk_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(self, initiative_id: str, data: dict[str, Any]) -> dict[str, Any]:
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("risks").insert(data).execute()
        # Fetch the complete item with joins
        if result.data:
            return self.get(result.data[0]["id"]) or result.data[0]
        return {}

    def update(self, risk_id: str, data: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("risks")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", risk_id)
            .execute()
        )
        if result.data:
            return self.get(result.data[0]["id"]) or result.data[0]
        return {}

    def delete(self, risk_id: str) -> None:
        (
            self._c.table("risks")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", risk_id)
            .execute()
        )

    # ── Heatmap ──────────────────────────────────────────────────────

    def get_heatmap_data(self) -> list[dict[str, Any]]:
        """Fetch all open risks and group them by impact and likelihood."""
        # Using a direct query because we can't do GROUP BY easily with Supabase client alone.
        # We'll fetch all open risks and group them in Python for simplicity.
        result = (
            self._c.table("risks")
            .select("impact, likelihood")
            .eq("tenant_id", self._tid)
            .eq("status", "open")
            .execute()
        )
        return result.data or []
