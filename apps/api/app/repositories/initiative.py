"""Initiative repository — typed Supabase data access."""

from __future__ import annotations

import csv
import io
from datetime import UTC
from uuid import UUID, uuid4

from supabase import Client


class InitiativeRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── Code generation ────────────────────────────────────────────────────────

    def next_code(self) -> str:
        """Generate next sequential TRN-XXX code for this tenant."""
        result = (
            self._c.table("initiatives")
            .select("initiative_code")
            .eq("tenant_id", self._tid)
            .order("initiative_code", desc=True)
            .limit(1)
            .execute()
        )
        if not result.data:
            return "TRN-001"
        last_code = result.data[0]["initiative_code"]
        # Parse "TRN-042" → 42
        try:
            n = int(last_code.split("-")[-1])
        except (ValueError, IndexError):
            n = 0
        return f"TRN-{n + 1:03d}"

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def list(
        self,
        *,
        workstream_ids: list[str] | None = None,
        business_unit_ids: list[str] | None = None,
        rag_statuses: list[str] | None = None,
        stages: list[str] | None = None,
        priorities: list[str] | None = None,
        tags: list[str] | None = None,
        search: str | None = None,
        sort_by: str = "initiative_code",
        sort_desc: bool = False,
        page: int = 1,
        page_size: int = 50,
        include_archived: bool = False,
        owner_user_id: str | None = None,
    ) -> tuple[list[dict], int]:  # type: ignore[type-arg]
        q = (
            self._c.table("initiatives")
            .select(
                "id, initiative_code, name, priority, rag_status, stage, "
                "country, tag, planned_start, planned_end, pressure_score, archived_at, "
                "workstream_id, workstreams(name), "
                "initiative_business_units(business_unit_id, business_units(id, name)), "
                "owner_id, users!initiatives_owner_id_fkey(display_name)",
                count="exact",
            )
            .eq("tenant_id", self._tid)
        )

        if not include_archived:
            q = q.is_("archived_at", "null")
        if business_unit_ids:
            initiative_ids = set()
            linked_result = (
                self._c.table("initiative_business_units")
                .select("initiative_id")
                .eq("tenant_id", self._tid)
                .in_("business_unit_id", business_unit_ids)
                .execute()
            )
            initiative_ids.update(row["initiative_id"] for row in linked_result.data or [])
            if not initiative_ids:
                return [], 0
            q = q.in_("id", sorted(initiative_ids))
        if workstream_ids:
            q = q.in_("workstream_id", workstream_ids)
        if rag_statuses:
            q = q.in_("rag_status", rag_statuses)
        if stages:
            q = q.in_("stage", stages)
        if priorities:
            q = q.in_("priority", priorities)
        if tags:
            q = q.in_("tag", tags)
        if search:
            q = q.ilike("name", f"%{search}%")
        if owner_user_id:
            q = q.or_(f"owner_id.eq.{owner_user_id},group_owner_id.eq.{owner_user_id}")

        q = q.order(sort_by, desc=sort_desc)
        q = q.range((page - 1) * page_size, page * page_size - 1)

        result = q.execute()
        return result.data or [], result.count or 0

    def get(self, initiative_id: str) -> dict | None:  # type: ignore[type-arg]
        # PostgREST can't join the same table twice; fetch user names separately.
        result = (
            self._c.table("initiatives")
            .select(
                "*, workstreams(id, name), "
                "initiative_business_units(business_unit_id, business_units(id, name))"
            )
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .maybe_single()
            .execute()
        )
        if result is None or not result.data:
            return None
        row = result.data

        # Resolve owner display_name (maybe_single returns None directly on 0 rows)
        if row.get("owner_id"):
            u = (
                self._c.table("users")
                .select("display_name")
                .eq("id", row["owner_id"])
                .maybe_single()
                .execute()
            )
            row["_owner_name"] = u.data["display_name"] if (u and u.data) else None

        # Resolve group_owner display_name
        if row.get("group_owner_id"):
            g = (
                self._c.table("users")
                .select("display_name")
                .eq("id", row["group_owner_id"])
                .maybe_single()
                .execute()
            )
            row["_group_owner_name"] = g.data["display_name"] if (g and g.data) else None

        return row

    def get_team_members(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("initiative_team")
            .select("*, users(display_name, email)")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def get_kpi_indicator_rows(self, initiative_id: str) -> tuple[list[dict], list[dict]]:  # type: ignore[type-arg]
        kpis_result = (
            self._c.table("kpis")
            .select("id, name, unit")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("created_at")
            .execute()
        )
        kpis = kpis_result.data or []
        if not kpis:
            return [], []
        kpi_ids = [row["id"] for row in kpis]
        entries_result = (
            self._c.table("kpi_entries")
            .select("kpi_id, year, quarter, value_base, value_high, value_actual")
            .eq("tenant_id", self._tid)
            .in_("kpi_id", kpi_ids)
            .order("year")
            .order("quarter", nullsfirst=True)
            .execute()
        )
        return kpis, entries_result.data or []

    def get_counts(self, initiative_id: str) -> dict:  # type: ignore[type-arg]
        """Fetch aggregate counts for the detail page header."""
        ms = (
            self._c.table("milestones")
            .select("id, status", count="exact")
            .eq("initiative_id", initiative_id)
            .execute()
        )
        milestones = ms.data or []
        risks = (
            self._c.table("risks")
            .select("id, rating", count="exact")
            .eq("initiative_id", initiative_id)
            .eq("status", "open")
            .execute()
        )
        kpis = (
            self._c.table("kpis")
            .select("id", count="exact")
            .eq("initiative_id", initiative_id)
            .execute()
        )
        sus = (
            self._c.table("status_updates")
            .select("id", count="exact")
            .eq("initiative_id", initiative_id)
            .eq("is_draft", False)
            .execute()
        )
        risk_rows = risks.data or []
        return {
            "milestones_total": ms.count or 0,
            "milestones_complete": sum(1 for m in milestones if m["status"] == "complete"),
            "milestones_overdue": sum(1 for m in milestones if m["status"] == "overdue"),
            "kpis_total": kpis.count or 0,
            "risks_open": risks.count or 0,
            "risks_high": sum(1 for r in risk_rows if r["rating"] == "high"),
            "status_updates_total": sus.count or 0,
        }

    def create(self, data: dict) -> dict:  # type: ignore[type-arg]
        result = self._c.table("initiatives").insert(data).execute()
        return result.data[0]

    def update(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("initiatives")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .execute()
        )
        return result.data[0]

    def replace_business_units(self, initiative_id: str, business_unit_ids: list[str]) -> list[dict]:
        (
            self._c.table("initiative_business_units")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        unique_ids = list(dict.fromkeys([bu_id for bu_id in business_unit_ids if bu_id]))
        if not unique_ids:
            return []
        result = (
            self._c.table("initiative_business_units")
            .insert(
                [
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tid,
                        "initiative_id": initiative_id,
                        "business_unit_id": bu_id,
                    }
                    for bu_id in unique_ids
                ]
            )
            .execute()
        )
        return result.data or []

    def has_approved_gate_submission(self, initiative_id: str, gate_number: int) -> bool:
        result = (
            self._c.table("gate_submissions")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("gate_number", gate_number)
            .eq("decision", "approved")
            .limit(1)
            .execute()
        )
        return bool(result.data)

    def archive(self, initiative_id: str) -> dict:  # type: ignore[type-arg]
        from datetime import datetime

        return self.update(initiative_id, {"archived_at": datetime.now(UTC).isoformat()})

    def delete(self, initiative_id: str) -> None:
        for table in ("action_items", "agenda_items"):
            (
                self._c.table(table)
                .delete()
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )
        self._c.table("initiatives").delete().eq("tenant_id", self._tid).eq(
            "id", initiative_id
        ).execute()

    def export_csv(self, owner_user_id: str | None = None) -> str:
        """Return CSV string of all non-archived initiatives."""
        rows, _ = self.list(page_size=10000, include_archived=False, owner_user_id=owner_user_id)
        output = io.StringIO()
        fieldnames = [
            "initiative_code",
            "name",
            "stage",
            "rag_status",
            "priority",
            "workstream",
            "country",
            "type",
            "tag",
            "planned_start",
            "planned_end",
            "pressure_score",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            ws = row.get("workstreams") or {}
            writer.writerow(
                {
                    **row,
                    "workstream": ws.get("name", "") if isinstance(ws, dict) else "",
                }
            )
        return output.getvalue()
