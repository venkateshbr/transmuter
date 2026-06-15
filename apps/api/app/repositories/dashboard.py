from typing import Any
from uuid import UUID


class DashboardRepository:
    def __init__(self, client: Any, tenant_id: UUID) -> None:
        self.client = client
        self.tenant_id = str(tenant_id)

    def get_initiatives_for_dashboard(
        self, owner_user_id: str | None = None
    ) -> list[dict[str, Any]]:
        select = (
            "id, name, initiative_code, stage, rag_status, priority, pressure_score, workstream_id, tag, "
            "workstreams(name), initiative_business_units(business_unit_id, business_units(id, name))"
        )
        res = (
            self.client.table("initiatives")
            .select(select)
            .eq("tenant_id", self.tenant_id)
            .is_("archived_at", "null")
        )
        if owner_user_id:
            res = res.or_(f"owner_id.eq.{owner_user_id},group_owner_id.eq.{owner_user_id}")
        res = res.execute()
        return res.data or []

    def get_stage_gate_definitions(self) -> list[dict[str, Any]]:
        res = (
            self.client.table("stage_gate_definitions")
            .select("gate_number,label,from_stage,to_stage,is_active")
            .eq("tenant_id", self.tenant_id)
            .eq("is_active", True)
            .order("gate_number")
            .execute()
        )
        return res.data or []

    def get_my_milestones(self, user_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        res = (
            self.client.table("milestones")
            .select("*, initiative:initiatives(name)")
            .eq("tenant_id", self.tenant_id)
            .eq("owner_id", str(user_id))
            .neq("status", "complete")
            .order("planned_end")
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_risks_for_heatmap(self) -> list[dict[str, Any]]:
        res = (
            self.client.table("risks")
            .select("id, initiative_id, impact, likelihood")
            .eq("tenant_id", self.tenant_id)
            .eq("status", "open")
            .execute()
        )
        return res.data or []

    def get_pending_approvals_count(self) -> int:
        res = (
            self.client.table("gate_submissions")
            .select("id", count="exact")
            .eq("tenant_id", self.tenant_id)
            .eq("decision", "pending")
            .execute()
        )
        return res.count if res.count is not None else 0

    def get_my_actions(self, user_id: UUID, limit: int = 5) -> list[dict[str, Any]]:
        select = (
            "id, description, status, due_date, initiative_id, initiatives(name, initiative_code), "
            "meeting_sessions(session_date, meetings(name))"
        )
        res = (
            self.client.table("action_items")
            .select(select)
            .eq("tenant_id", self.tenant_id)
            .eq("assignee_id", str(user_id))
            .order("due_date")
            .limit(25)
            .execute()
        )
        return res.data or []

    def get_kpi_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        kpis = (
            self.client.table("kpis")
            .select("id, name, unit, initiative_id, initiatives(name, initiative_code)")
            .eq("tenant_id", self.tenant_id)
            .execute()
        ).data or []

        kpi_ids = [k["id"] for k in kpis]
        entries = []
        if kpi_ids:
            entries = (
                self.client.table("kpi_entries")
                .select("kpi_id, year, quarter, value_base, value_high, value_actual")
                .eq("tenant_id", self.tenant_id)
                .in_("kpi_id", kpi_ids)
                .execute()
            ).data or []

        return kpis, entries

    def get_financial_summary_data(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        try:
            entry_select = (
                "initiative_id, year, quarter, revenue_uplift_base, revenue_uplift_high, revenue_uplift_actual, "
                "gm_uplift_base, gm_uplift_high, gm_uplift_actual"
            )
            entries = (
                self.client.table("financial_entries")
                .select(entry_select)
                .eq("tenant_id", self.tenant_id)
                .execute()
            ).data or []
        except Exception as exc:
            text = str(exc)
            if "financial_entries" in text and (
                "Could not find the table" in text
                or "does not exist" in text
                or "schema cache" in text
            ):
                entries = []
            else:
                raise

        costs = (
            self.client.table("financial_cost_lines")
            .select("initiative_id, year, quarter, amount_plan, amount_actual, is_recurring")
            .eq("tenant_id", self.tenant_id)
            .execute()
        ).data or []

        return entries, costs

    def get_recent_activity(self) -> list[dict[str, Any]]:
        select = (
            "id, initiative_id, rag_status, summary, submitted_at, "
            "initiatives(name, initiative_code), "
            "users!status_updates_author_id_fkey(display_name)"
        )
        res = (
            self.client.table("status_updates")
            .select(select)
            .eq("tenant_id", self.tenant_id)
            .eq("is_draft", False)
            .order("submitted_at", desc=True)
            .limit(25)
            .execute()
        )
        return res.data or []

    def get_filter_options(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        bus = (
            self.client.table("business_units")
            .select("id, name")
            .eq("tenant_id", self.tenant_id)
            .order("name")
            .execute()
        ).data or []

        wss = (
            self.client.table("workstreams")
            .select("id, name")
            .eq("tenant_id", self.tenant_id)
            .order("name")
            .execute()
        ).data or []

        return bus, wss

    def get_workstream_target_locks(self) -> list[dict[str, Any]]:
        try:
            res = (
                self.client.table("workstream_target_locks")
                .select(
                    "id, workstream_id, version, lock_date, locked_at, "
                    "locked_run_rate_value, actual_total, variance"
                )
                .eq("tenant_id", self.tenant_id)
                .order("workstream_id")
                .order("version")
                .execute()
            )
            return res.data or []
        except Exception as exc:
            text = str(exc)
            if "workstream_target_locks" in text and (
                "Could not find the table" in text
                or "does not exist" in text
                or "schema cache" in text
            ):
                return []
            raise
