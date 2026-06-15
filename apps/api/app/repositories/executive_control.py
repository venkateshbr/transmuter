"""Executive Control Tower data access."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
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
                "variance_explanation,workstreams(id,name),initiative_business_units(business_unit_id)"
            )
            .eq("tenant_id", self._tid)
            .is_("archived_at", "null")
            .execute()
        )
        return result.data or []

    def list_financial_entries(self) -> list[dict]:
        try:
            result = (
                self._c.table("financial_entries").select("*").eq("tenant_id", self._tid).execute()
            )
            return result.data or []
        except Exception as exc:
            if not self._is_missing_table(exc, "financial_entries"):
                raise
        return self._list_clean_financial_entries()

    def list_direct_cost_lines(self) -> list[dict]:
        result = (
            self._c.table("financial_cost_lines").select("*").eq("tenant_id", self._tid).execute()
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

    def list_metric_definitions(self) -> list[dict]:
        result = (
            self._c.table("financial_metric_definitions")
            .select("id,key,rollup_type,benefit_class,is_benefit")
            .eq("tenant_id", self._tid)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []

    def list_financial_scenarios(self) -> list[dict]:
        result = (
            self._c.table("financial_scenarios")
            .select("id,key,kind,is_primary,is_active")
            .eq("tenant_id", self._tid)
            .eq("is_active", True)
            .execute()
        )
        return result.data or []

    def list_metric_values(self) -> list[dict]:
        result = (
            self._c.table("financial_metric_values")
            .select("initiative_id,metric_definition_id,scenario_id,year,month,value")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def _list_clean_financial_entries(self) -> list[dict]:
        definitions = {row["id"]: row for row in self.list_metric_definitions()}
        scenarios = {row["id"]: row for row in self.list_financial_scenarios()}
        plan_scenario_ids = [
            row["id"]
            for row in scenarios.values()
            if row.get("kind") == "plan" and row.get("is_primary")
        ]
        if not plan_scenario_ids:
            plan_scenario_ids = [
                row["id"] for row in scenarios.values() if row.get("kind") == "plan"
            ]
        actual_scenario_ids = {
            row["id"] for row in scenarios.values() if row.get("kind") == "actual"
        }
        entries: dict[tuple[str, int, int], dict] = {}
        for row in self.list_metric_values():
            scenario_id = row.get("scenario_id")
            if scenario_id not in set(plan_scenario_ids) | actual_scenario_ids:
                continue
            definition = definitions.get(row.get("metric_definition_id"))
            if not definition:
                continue
            year = int(row["year"])
            month = int(row["month"])
            key = (str(row["initiative_id"]), year, month)
            entry = entries.setdefault(
                key,
                {
                    "initiative_id": str(row["initiative_id"]),
                    "year": year,
                    "quarter": None,
                    "month": month,
                    "revenue_uplift_base": None,
                    "revenue_uplift_high": None,
                    "revenue_uplift_actual": None,
                    "gm_uplift_base": None,
                    "gm_uplift_high": None,
                    "gm_uplift_actual": None,
                },
            )
            amount = Decimal(str(row.get("value") or "0"))
            scenario_kind = scenarios.get(scenario_id, {}).get("kind")
            target = "actual" if scenario_kind == "actual" else "base"
            metric_key = definition.get("key")
            rollup_type = definition.get("rollup_type")
            benefit_class = definition.get("benefit_class")
            if metric_key == "revenue_uplift" or benefit_class == "revenue":
                slot = f"revenue_uplift_{target}"
            elif (
                rollup_type == "benefit"
                or definition.get("is_benefit")
                or metric_key
                in {
                    "gross_margin",
                    "gm_uplift",
                    "cost_savings",
                }
            ):
                slot = f"gm_uplift_{target}"
            else:
                continue
            current = entry.get(slot)
            entry[slot] = str((Decimal(str(current or "0")) + amount).quantize(Decimal("0.0001")))
        return list(entries.values())

    @staticmethod
    def _is_missing_table(exc: Exception, table_name: str) -> bool:
        text = str(exc)
        return table_name in text and (
            "Could not find the table" in text or "does not exist" in text or "schema cache" in text
        )
