"""Status Update repository — Supabase data access."""

from __future__ import annotations

from datetime import UTC
from typing import Any
from uuid import UUID, uuid4

from supabase import Client


class StatusUpdateRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_history(self, initiative_id: str) -> list[dict[str, Any]]:
        """Returns all submitted status updates for an initiative, most recent first."""
        result = (
            self._c.table("status_updates")
            .select("*, users!status_updates_author_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("is_draft", False)
            .order("submitted_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_draft(self, initiative_id: str) -> dict[str, Any] | None:
        """Returns the current draft for an initiative, if any."""
        result = (
            self._c.table("status_updates")
            .select("*, users!status_updates_author_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("is_draft", True)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    def get(self, update_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("status_updates")
            .select("*, users!status_updates_author_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("id", update_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(
        self, initiative_id: str, author_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        data["author_id"] = author_id

        # If created directly as submitted, set submitted_at
        if not data.get("is_draft", True):
            from datetime import datetime
            data["submitted_at"] = datetime.now(UTC).isoformat()

        result = self._c.table("status_updates").insert(data).execute()
        if result.data:
            return self.get(result.data[0]["id"]) or result.data[0]
        return {}

    def update(self, update_id: str, data: dict[str, Any]) -> dict[str, Any]:
        from datetime import datetime
        
        data["updated_at"] = datetime.now(UTC).isoformat()
        
        result = (
            self._c.table("status_updates")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", update_id)
            .execute()
        )
        if result.data:
            return self.get(result.data[0]["id"]) or result.data[0]
        return {}

    def delete(self, update_id: str) -> None:
        (
            self._c.table("status_updates")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", update_id)
            .execute()
        )

    def list_recent_updates(self, limit: int = 50) -> list[dict[str, Any]]:
        """Returns the most recent submitted status updates across all initiatives."""
        result = (
            self._c.table("status_updates")
            .select("*, initiatives(name), users!status_updates_author_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .eq("is_draft", False)
            .order("submitted_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    def list_compliance(self) -> list[dict[str, Any]]:
        """Returns a list of all initiatives with their latest status update info."""
        # Note: This is a complex join, we fetch initiatives and then we'll map the latest update in service
        # or use a RPC if available. For now, fetch all initiatives and their last status update submitted_at.
        result = (
            self._c.table("initiatives")
            .select("id, name, owner_id, users!initiatives_owner_id_fkey(display_name), status_updates(submitted_at, rag_status)")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def list_nudge_counts(self) -> dict[str, int]:
        result = (
            self._c.table("nudge_log")
            .select("initiative_id")
            .eq("tenant_id", self._tid)
            .execute()
        )
        counts: dict[str, int] = {}
        for row in result.data or []:
            initiative_id = row["initiative_id"]
            counts[initiative_id] = counts.get(initiative_id, 0) + 1
        return counts

    def log_nudge(
        self, initiative_id: str, sent_by_id: str, channel: str = "both",
    ) -> dict[str, Any]:
        """Logs a nudge in the nudge_log table."""
        data = {
            "id": str(uuid4()),
            "tenant_id": self._tid,
            "initiative_id": initiative_id,
            "sent_by_id": sent_by_id,
            "channel": channel,
        }
        result = self._c.table("nudge_log").insert(data).execute()
        return result.data[0] if result.data else {}

    def list_nudges(self) -> list[dict[str, Any]]:
        """Returns all nudges sent for the tenant."""
        result = (
            self._c.table("nudge_log")
            .select("*, initiatives(name), users!nudge_log_sent_by_id_fkey(display_name)")
            .eq("tenant_id", self._tid)
            .order("sent_at", desc=True)
            .execute()
        )
        return result.data or []
