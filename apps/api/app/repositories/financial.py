"""Financial repository — typed Supabase data access."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID

from supabase import Client


class FinancialRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── Financial Entries ─────────────────────────────────────────────────────

    def get_entries(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        """Return all financial_entries rows for an initiative, ordered by year/quarter."""
        result = (
            self._c.table("financial_entries")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("year")
            .order("quarter")
            .execute()
        )
        return result.data or []

    def upsert_entry(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        """Insert or update a single financial entry (unique on initiative_id + year + quarter)."""
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = (
            self._c.table("financial_entries")
            .upsert(data, on_conflict="initiative_id,year,quarter,month")
            .execute()
        )
        return result.data[0]

    def upsert_entries_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Upsert multiple financial entries at once."""
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
        result = (
            self._c.table("financial_entries")
            .upsert(rows, on_conflict="initiative_id,year,quarter,month")
            .execute()
        )
        return result.data or []

    # ── Cost Lines ────────────────────────────────────────────────────────────

    def list_cost_lines(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_cost_lines")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("year")
            .order("quarter")
            .order("name")
            .execute()
        )
        return result.data or []

    def create_cost_line(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        from uuid import uuid4

        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("financial_cost_lines").insert(data).execute()
        return result.data[0]

    def update_cost_line(self, cost_line_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        from datetime import datetime

        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("financial_cost_lines")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", cost_line_id)
            .execute()
        )
        if not result.data:
            return {}
        return result.data[0]

    def delete_cost_line(self, cost_line_id: str) -> None:
        (
            self._c.table("financial_cost_lines")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", cost_line_id)
            .execute()
        )

    # ── Portfolio aggregation ─────────────────────────────────────────────────

    def get_all_entries(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all financial_entries for the tenant (portfolio-level)."""
        result = (
            self._c.table("financial_entries")
            .select("*")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def get_all_cost_lines(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all cost lines for the tenant (portfolio-level)."""
        result = (
            self._c.table("financial_cost_lines")
            .select("*")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []
