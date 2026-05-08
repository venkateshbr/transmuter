"""KPI repository — Supabase data access."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID, uuid4

from supabase import Client


class KPIRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── KPIs ─────────────────────────────────────────────────────────

    def list(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("kpis")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def list_all(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("kpis")
            .select("*, initiative:initiatives(name, initiative_code)")
            .eq("tenant_id", self._tid)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def get(self, kpi_id: str) -> dict | None:  # type: ignore[type-arg]
        result = (
            self._c.table("kpis")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", kpi_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("kpis").insert(data).execute()
        return result.data[0]

    def update(self, kpi_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        from datetime import datetime

        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("kpis").update(data).eq("tenant_id", self._tid).eq("id", kpi_id).execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, kpi_id: str) -> None:
        (self._c.table("kpis").delete().eq("tenant_id", self._tid).eq("id", kpi_id).execute())

    # ── KPI Entries ──────────────────────────────────────────────────

    def get_entries(self, kpi_ids: list[str]) -> list[dict]:  # type: ignore[type-arg]
        if not kpi_ids:
            return []
        result = (
            self._c.table("kpi_entries")
            .select("*")
            .eq("tenant_id", self._tid)
            .in_("kpi_id", kpi_ids)
            .order("year")
            .order("quarter", nullsfirst=True)
            .execute()
        )
        return result.data or []

    def upsert_entries(self, kpi_id: str, entries: list[dict]) -> None:  # type: ignore[type-arg]
        if not entries:
            return

        for e in entries:
            e["kpi_id"] = kpi_id
            e["tenant_id"] = self._tid

            # Since there is a UNIQUE constraint on (kpi_id, year, quarter),
            # we can use Supabase's upsert matching on those columns.
            # However, postgrest upsert handles constraint conflicts.
            # Unfortunately, `upsert` requires the primary key if we don't specify `on_conflict`.
            # Let's do a manual check/update to be safe.

            match_query = (
                self._c.table("kpi_entries")
                .select("id")
                .eq("tenant_id", self._tid)
                .eq("kpi_id", kpi_id)
                .eq("year", e["year"])
            )
            if e.get("quarter") is not None:
                match_query = match_query.eq("quarter", e["quarter"])
            else:
                match_query = match_query.is_("quarter", "null")

            existing = match_query.maybe_single().execute()

            if existing and existing.data:
                from datetime import datetime

                e["updated_at"] = datetime.now(UTC).isoformat()
                (self._c.table("kpi_entries").update(e).eq("id", existing.data["id"]).execute())
            else:
                e["id"] = str(uuid4())
                self._c.table("kpi_entries").insert(e).execute()

    # ── Pulse Summary ────────────────────────────────────────────────

    def get_all_kpis_and_latest_entries(self) -> tuple[list[dict], list[dict]]:  # type: ignore[type-arg]
        # Fetch all active KPIs for the tenant
        kpis_result = self._c.table("kpis").select("id").eq("tenant_id", self._tid).execute()
        kpis = kpis_result.data or []
        if not kpis:
            return [], []

        kpi_ids = [k["id"] for k in kpis]

        # We need the most recent entry for each KPI.
        # We fetch all entries and sort in Python to find the latest with actuals.
        entries_result = (
            self._c.table("kpi_entries")
            .select("kpi_id, year, quarter, value_base, value_actual")
            .eq("tenant_id", self._tid)
            .in_("kpi_id", kpi_ids)
            .execute()
        )
        return kpis, entries_result.data or []
