"""Executive Control Tower data access."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from supabase import Client


class ExecutiveControlRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list_initiatives(self) -> list[dict]:
        result = (
            self._c.table("initiatives")
            .select(
                "id,initiative_code,name,owner_id,group_owner_id,workstream_id,rag_status,"
                "stage,country,tag,planned_end,benefit_confidence,realization_status,"
                "variance_explanation,workstreams(id,name,business_unit_id,business_units(id,name))"
            )
            .eq("tenant_id", self._tid)
            .is_("archived_at", "null")
            .execute()
        )
        return result.data or []

    def list_financial_entries(self) -> list[dict]:
        result = (
            self._c.table("financial_entries")
            .select("*")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def list_direct_cost_lines(self) -> list[dict]:
        result = (
            self._c.table("financial_cost_lines")
            .select("*")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def list_actions(self) -> list[dict]:
        result = (
            self._c.table("action_items")
            .select("id,initiative_id,description,status,due_date,priority,assignee_id")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def list_status_updates(self) -> list[dict]:
        result = (
            self._c.table("status_updates")
            .select("id,initiative_id,submitted_at,is_draft,rag_status")
            .eq("tenant_id", self._tid)
            .eq("is_draft", False)
            .execute()
        )
        return result.data or []

    def list_kpi_entries(self) -> list[dict]:
        result = (
            self._c.table("kpis")
            .select("id,initiative_id,name,kpi_entries(year,quarter,value_base,value_actual)")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def list_dependencies(self) -> list[dict]:
        result = (
            self._c.table("initiative_dependencies")
            .select(
                "*,"
                "upstream:initiatives!initiative_dependencies_upstream_initiative_id_fkey("
                "id,initiative_code,name,owner_id,workstream_id,rag_status,stage,"
                "workstreams(id,name)"
                "),"
                "downstream:initiatives!initiative_dependencies_downstream_initiative_id_fkey("
                "id,initiative_code,name,owner_id,workstream_id,rag_status,stage,"
                "workstreams(id,name)"
                "),"
                "owner:users!initiative_dependencies_owner_id_fkey(display_name)"
            )
            .eq("tenant_id", self._tid)
            .order("due_date")
            .execute()
        )
        return result.data or []

    def get_dependency(self, dependency_id: str) -> dict | None:
        result = (
            self._c.table("initiative_dependencies")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", dependency_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def create_dependency(self, data: dict) -> dict:
        payload = {**data, "id": str(uuid4()), "tenant_id": self._tid}
        result = self._c.table("initiative_dependencies").insert(payload).execute()
        return result.data[0]

    def update_dependency(self, dependency_id: str, data: dict) -> dict:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("initiative_dependencies")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", dependency_id)
            .execute()
        )
        return result.data[0]

    def delete_dependency(self, dependency_id: str) -> None:
        (
            self._c.table("initiative_dependencies")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", dependency_id)
            .execute()
        )

    def list_pools(self) -> list[dict]:
        result = (
            self._c.table("shared_cost_pools")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("year")
            .order("month")
            .execute()
        )
        return result.data or []

    def create_pool(self, data: dict) -> dict:
        payload = {**data, "id": str(uuid4()), "tenant_id": self._tid}
        result = self._c.table("shared_cost_pools").insert(payload).execute()
        return result.data[0]

    def update_pool(self, pool_id: str, data: dict) -> dict:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("shared_cost_pools")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", pool_id)
            .execute()
        )
        return result.data[0]

    def get_pool(self, pool_id: str) -> dict | None:
        result = (
            self._c.table("shared_cost_pools")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", pool_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def create_rule(self, pool_id: str, data: dict) -> dict:
        payload = {**data, "id": str(uuid4()), "tenant_id": self._tid, "pool_id": pool_id}
        result = self._c.table("shared_cost_allocation_rules").insert(payload).execute()
        return result.data[0]

    def update_rule(self, rule_id: str, data: dict) -> dict:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("shared_cost_allocation_rules")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", rule_id)
            .execute()
        )
        return result.data[0]

    def list_rules(self, pool_id: str) -> list[dict]:
        result = (
            self._c.table("shared_cost_allocation_rules")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("pool_id", pool_id)
            .order("created_at")
            .execute()
        )
        return result.data or []

    def get_rule(self, rule_id: str) -> dict | None:
        result = (
            self._c.table("shared_cost_allocation_rules")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", rule_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def create_run(self, data: dict, allocations: list[dict]) -> dict:
        run_payload = {**data, "id": str(uuid4()), "tenant_id": self._tid}
        run = self._c.table("shared_cost_allocation_runs").insert(run_payload).execute().data[0]
        if allocations:
            rows = [
                {
                    **row,
                    "id": str(uuid4()),
                    "tenant_id": self._tid,
                    "run_id": run["id"],
                    "pool_id": run["pool_id"],
                    "rule_id": run["rule_id"],
                }
                for row in allocations
            ]
            self._c.table("shared_cost_allocations").insert(rows).execute()
        return run

    def list_runs(self, pool_id: str) -> list[dict]:
        result = (
            self._c.table("shared_cost_allocation_runs")
            .select("*,shared_cost_allocations(*,initiatives(name))")
            .eq("tenant_id", self._tid)
            .eq("pool_id", pool_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def list_allocations(self) -> list[dict]:
        result = (
            self._c.table("shared_cost_allocations")
            .select("*,shared_cost_pools(year,quarter,month,is_recurring,category_key)")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def create_value_note(self, initiative_id: str, author_id: str, data: dict) -> dict:
        payload = {
            **data,
            "id": str(uuid4()),
            "tenant_id": self._tid,
            "initiative_id": initiative_id,
            "author_id": author_id,
        }
        result = self._c.table("initiative_value_realization_notes").insert(payload).execute()
        return result.data[0]

    def list_value_notes(self, initiative_id: str) -> list[dict]:
        result = (
            self._c.table("initiative_value_realization_notes")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
