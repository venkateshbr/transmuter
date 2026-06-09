"""Financial repository — typed Supabase data access."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from supabase import Client

_OPTIONAL_ENTRY_COLUMNS = {
    "cogs_base",
    "cogs_high",
    "cogs_actual",
    "cogs_pct_base",
    "cogs_pct_high",
    "cogs_pct_actual",
}


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
            .order("month")
            .execute()
        )
        return result.data or []

    def get_initiative_period(self, initiative_id: str) -> dict | None:  # type: ignore[type-arg]
        result = (
            self._c.table("initiatives")
            .select("id,stage,planned_start,planned_end")
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def upsert_entry(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        """Insert or update a single financial entry (unique on initiative_id + year + quarter)."""
        return self.upsert_entries_batch(initiative_id, [data])[0]

    def upsert_entries_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        """Upsert multiple financial entries at once."""
        saved = []
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            existing_rows = self._find_financial_entries(initiative_id, row)
            if existing_rows:
                row["updated_at"] = datetime.now(UTC).isoformat()
                result = None
                for existing in existing_rows:
                    result = self._write_financial_entry(row, existing["id"])
            else:
                row["id"] = str(uuid4())
                result = self._write_financial_entry(row)
            if result.data:
                saved.append(result.data[0])
        return saved

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

    def list_metric_values(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_metric_values")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .order("metric_key")
                .order("year")
                .order("quarter")
                .order("month")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "financial_metric_values"):
                return []
            raise

    def upsert_metric_values_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        saved = []
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            existing_rows = self._find_metric_values(initiative_id, row)
            if existing_rows:
                row["updated_at"] = datetime.now(UTC).isoformat()
                result = None
                for existing in existing_rows:
                    result = (
                        self._c.table("financial_metric_values")
                        .update(row)
                        .eq("tenant_id", self._tid)
                        .eq("id", existing["id"])
                        .execute()
                    )
            else:
                row["id"] = str(uuid4())
                result = self._c.table("financial_metric_values").insert(row).execute()
            if result and result.data:
                saved.append(result.data[0])
        return saved

    def list_financial_selections(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("initiative_financial_selections")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "initiative_financial_selections"):
                return []
            raise

    def list_bankable_plans(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("bankable_plans")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .order("version")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "bankable_plans"):
                return []
            raise

    def list_latest_bankable_plans_for_initiatives(
        self,
        initiative_ids: list[str],
    ) -> list[dict]:  # type: ignore[type-arg]
        if not initiative_ids:
            return []
        try:
            result = (
                self._c.table("bankable_plans")
                .select("*")
                .eq("tenant_id", self._tid)
                .in_("initiative_id", initiative_ids)
                .order("initiative_id")
                .order("version")
                .execute()
            )
            latest: dict[str, dict] = {}
            for row in result.data or []:
                latest[str(row["initiative_id"])] = row
            return list(latest.values())
        except Exception as exc:
            if self._is_missing_table(exc, "bankable_plans"):
                return []
            raise

    def create_bankable_plan(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
            "updated_at": data.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("bankable_plans").insert(payload).execute()
        return result.data[0]

    def get_latest_bankable_plan(self, initiative_id: str) -> dict | None:  # type: ignore[type-arg]
        plans = self.list_bankable_plans(initiative_id)
        return plans[-1] if plans else None

    def get_organization_settings(self) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("organizations")
            .select("settings")
            .eq("id", self._tid)
            .maybe_single()
            .execute()
        )
        return (result.data or {}).get("settings") or {}

    def update_organization_settings(self, settings: dict) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("organizations")
            .update({"settings": settings, "updated_at": datetime.now(UTC).isoformat()})
            .eq("id", self._tid)
            .execute()
        )
        return result.data[0] if result.data else {"settings": settings}

    def list_workstreams(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("workstreams")
            .select("id,name,business_unit_id")
            .eq("tenant_id", self._tid)
            .order("name")
            .execute()
        )
        return result.data or []

    def list_workstream_initiatives(self, workstream_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("initiatives")
            .select("id,initiative_code,name,stage,workstream_id")
            .eq("tenant_id", self._tid)
            .eq("workstream_id", workstream_id)
            .is_("archived_at", "null")
            .order("initiative_code")
            .execute()
        )
        return result.data or []

    def list_approved_gate_submissions(
        self,
        initiative_ids: list[str],
        gate_number: int,
        cutoff_date: date,
    ) -> list[dict]:  # type: ignore[type-arg]
        if not initiative_ids:
            return []
        result = (
            self._c.table("gate_submissions")
            .select("id,initiative_id,gate_number,decision,decided_at")
            .eq("tenant_id", self._tid)
            .eq("gate_number", gate_number)
            .eq("decision", "approved")
            .in_("initiative_id", initiative_ids)
            .lte("decided_at", f"{cutoff_date.isoformat()}T23:59:59+00:00")
            .order("decided_at")
            .execute()
        )
        return result.data or []

    def list_workstream_target_locks(self, workstream_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("workstream_target_locks")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("workstream_id", workstream_id)
                .order("version")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "workstream_target_locks"):
                return []
            raise

    def create_workstream_target_lock(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
            "updated_at": data.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("workstream_target_locks").insert(payload).execute()
        return result.data[0]

    def get_latest_workstream_target_lock(self, workstream_id: str) -> dict | None:  # type: ignore[type-arg]
        rows = self.list_workstream_target_locks(workstream_id)
        return rows[-1] if rows else None

    def list_forecasts(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_forecasts")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .order("year")
                .order("quarter")
                .order("month")
                .order("line_key")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "financial_forecasts"):
                return []
            raise

    def upsert_forecasts_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:  # type: ignore[type-arg]
        saved = []
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            existing_rows = self._find_forecasts(initiative_id, row)
            row["updated_at"] = datetime.now(UTC).isoformat()
            if existing_rows:
                result = (
                    self._c.table("financial_forecasts")
                    .update(row)
                    .eq("tenant_id", self._tid)
                    .eq("id", existing_rows[0]["id"])
                    .execute()
                )
            else:
                row["id"] = str(uuid4())
                result = self._c.table("financial_forecasts").insert(row).execute()
            if result.data:
                saved.append(result.data[0])
        return saved

    # ── Benefit Realization Ledger ────────────────────────────────────────────

    def list_benefit_ledger_entries(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("benefit_realization_ledger")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .order("period_start")
                .order("created_at")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "benefit_realization_ledger"):
                return []
            raise

    def list_benefit_ledger_entries_for_initiatives(
        self,
        initiative_ids: list[str],
    ) -> list[dict]:  # type: ignore[type-arg]
        if not initiative_ids:
            return []
        try:
            result = (
                self._c.table("benefit_realization_ledger")
                .select("*")
                .eq("tenant_id", self._tid)
                .in_("initiative_id", initiative_ids)
                .order("period_start")
                .order("created_at")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "benefit_realization_ledger"):
                return []
            raise

    def create_benefit_ledger_entry(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "initiative_id": initiative_id,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
            "updated_at": data.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("benefit_realization_ledger").insert(payload).execute()
        return result.data[0]

    def update_benefit_ledger_entry(
        self,
        initiative_id: str,
        entry_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("benefit_realization_ledger")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", entry_id)
            .execute()
        )
        if not result.data:
            return {}
        return result.data[0]

    def delete_benefit_ledger_entry(self, initiative_id: str, entry_id: str) -> None:
        (
            self._c.table("benefit_realization_ledger")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", entry_id)
            .execute()
        )

    def replace_financial_selections(
        self,
        initiative_id: str,
        metric_keys: list[str],
        cost_category_keys: list[str],
        all_metric_keys: list[str] | None = None,
        all_cost_category_keys: list[str] | None = None,
    ) -> None:
        (
            self._c.table("initiative_financial_selections")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        active_metric_keys = set(metric_keys)
        active_cost_keys = set(cost_category_keys)
        metric_rows = sorted(set(all_metric_keys or metric_keys))
        cost_rows = sorted(set(all_cost_category_keys or cost_category_keys))
        rows = [
            {
                "id": str(uuid4()),
                "tenant_id": self._tid,
                "initiative_id": initiative_id,
                "item_key": key,
                "item_type": "metric",
                "is_active": key in active_metric_keys,
            }
            for key in metric_rows
        ] + [
            {
                "id": str(uuid4()),
                "tenant_id": self._tid,
                "initiative_id": initiative_id,
                "item_key": key,
                "item_type": "cost_category",
                "is_active": key in active_cost_keys,
            }
            for key in cost_rows
        ]
        if rows:
            self._c.table("initiative_financial_selections").insert(rows).execute()

    def create_cost_line(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("financial_cost_lines").insert(data).execute()
        return result.data[0]

    def update_cost_line(
        self,
        initiative_id: str,
        cost_line_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("financial_cost_lines")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", cost_line_id)
            .execute()
        )
        if not result.data:
            return {}
        return result.data[0]

    def delete_cost_line(self, initiative_id: str, cost_line_id: str) -> None:
        (
            self._c.table("financial_cost_lines")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", cost_line_id)
            .execute()
        )

    # ── Tenant configuration ─────────────────────────────────────────────────

    def list_config_groups(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_config_groups")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("kind")
            .order("display_order")
            .execute()
        )
        return result.data or []

    def list_config_items(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_config_items")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("item_type")
            .order("display_order")
            .execute()
        )
        return result.data or []

    def upsert_config_group(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {**data, "tenant_id": self._tid, "updated_at": datetime.now(UTC).isoformat()}
        existing = (
            self._c.table("financial_config_groups")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("key", payload["key"])
            .execute()
        )
        if existing.data:
            result = (
                self._c.table("financial_config_groups")
                .update(payload)
                .eq("tenant_id", self._tid)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            payload["id"] = str(uuid4())
            result = self._c.table("financial_config_groups").insert(payload).execute()
        return result.data[0]

    def upsert_config_item(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {**data, "tenant_id": self._tid, "updated_at": datetime.now(UTC).isoformat()}
        existing = (
            self._c.table("financial_config_items")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("key", payload["key"])
            .execute()
        )
        if existing.data:
            result = (
                self._c.table("financial_config_items")
                .update(payload)
                .eq("tenant_id", self._tid)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            payload["id"] = str(uuid4())
            result = self._c.table("financial_config_items").insert(payload).execute()
        return result.data[0]

    def deactivate_config_groups_except(self, active_keys: set[str]) -> None:
        """Deactivate tenant config groups omitted from a full configuration save."""
        existing = (
            self._c.table("financial_config_groups")
            .select("id,key,is_active")
            .eq("tenant_id", self._tid)
            .execute()
        )
        for row in existing.data or []:
            if row["key"] in active_keys or row.get("is_active") is False:
                continue
            (
                self._c.table("financial_config_groups")
                .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
                .eq("tenant_id", self._tid)
                .eq("id", row["id"])
                .execute()
            )

    def deactivate_config_items_except(self, active_keys: set[str]) -> None:
        """Deactivate tenant config items omitted from a full configuration save."""
        existing = (
            self._c.table("financial_config_items")
            .select("id,key,is_active")
            .eq("tenant_id", self._tid)
            .execute()
        )
        for row in existing.data or []:
            if row["key"] in active_keys or row.get("is_active") is False:
                continue
            (
                self._c.table("financial_config_items")
                .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
                .eq("tenant_id", self._tid)
                .eq("id", row["id"])
                .execute()
            )

    def reassign_cost_category(self, category_key: str, replacement_key: str) -> int:
        result = (
            self._c.table("financial_cost_lines")
            .update(
                {
                    "category_key": replacement_key,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("tenant_id", self._tid)
            .eq("category_key", category_key)
            .execute()
        )
        (
            self._c.table("financial_config_items")
            .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
            .eq("tenant_id", self._tid)
            .eq("key", category_key)
            .eq("item_type", "cost_category")
            .execute()
        )
        return len(result.data or [])

    def deactivate_metric(self, metric_key: str) -> None:
        (
            self._c.table("financial_config_items")
            .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
            .eq("tenant_id", self._tid)
            .eq("key", metric_key)
            .eq("item_type", "metric")
            .execute()
        )

    def get_portfolio_initiatives(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("initiatives")
            .select("id,initiative_code,name,stage,workstream_id,tag,workstreams(name,business_unit_id)")
            .eq("tenant_id", self._tid)
            .is_("archived_at", "null")
            .execute()
        )
        return result.data or []

    def delete_grid(self, initiative_id: str) -> None:
        (
            self._c.table("financial_cost_lines")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        (
            self._c.table("financial_entries")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .execute()
        )
        try:
            (
                self._c.table("financial_metric_values")
                .delete()
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )
        except Exception as exc:
            if not self._is_missing_table(exc, "financial_metric_values"):
                raise

    def initiative_exists(self, initiative_id: str) -> bool:
        result = (
            self._c.table("initiatives")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .maybe_single()
            .execute()
        )
        return bool(result and result.data)

    def upsert_cost_lines_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:
        """Replace category-period cost values from the grid/import payload."""
        saved = []
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            existing_rows = self._find_cost_lines(initiative_id, row)
            for existing in existing_rows:
                (
                    self._c.table("financial_cost_lines")
                    .delete()
                    .eq("tenant_id", self._tid)
                    .eq("id", existing["id"])
                    .execute()
                )
            if self._cost_row_is_zero(row):
                continue
            row["id"] = str(uuid4())
            result = self._c.table("financial_cost_lines").insert(row).execute()
            if result.data:
                saved.append(result.data[0])
        return saved

    # ── Portfolio aggregation ─────────────────────────────────────────────────

    def get_all_entries(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all financial_entries for the tenant (portfolio-level)."""
        result = self._c.table("financial_entries").select("*").eq("tenant_id", self._tid).execute()
        return result.data or []

    def get_all_cost_lines(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all cost lines for the tenant (portfolio-level)."""
        result = (
            self._c.table("financial_cost_lines").select("*").eq("tenant_id", self._tid).execute()
        )
        return result.data or []

    def get_all_metric_values(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all custom financial metric values for the tenant."""
        try:
            result = (
                self._c.table("financial_metric_values")
                .select("*")
                .eq("tenant_id", self._tid)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "financial_metric_values"):
                return []
            raise

    # ── Cell Assumptions ──────────────────────────────────────────────────────

    def list_cell_assumptions(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_cell_assumptions")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("row_key")
            .order("column_key")
            .execute()
        )
        return result.data or []

    def upsert_cell_assumption(
        self,
        initiative_id: str,
        data: dict,  # type: ignore[type-arg]
        user_id: str,
    ) -> dict:  # type: ignore[type-arg]
        existing = (
            self._c.table("financial_cell_assumptions")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("row_key", data["row_key"])
            .eq("column_key", data["column_key"])
            .execute()
        )
        now = datetime.now(UTC).isoformat()
        payload = {
            "tenant_id": self._tid,
            "initiative_id": initiative_id,
            "row_key": data["row_key"],
            "column_key": data["column_key"],
            "comment": data["comment"],
            "updated_by": user_id,
            "updated_at": now,
        }
        if existing.data:
            result = (
                self._c.table("financial_cell_assumptions")
                .update(payload)
                .eq("tenant_id", self._tid)
                .eq("id", existing.data[0]["id"])
                .execute()
            )
        else:
            payload["id"] = str(uuid4())
            payload["created_by"] = user_id
            result = self._c.table("financial_cell_assumptions").insert(payload).execute()
        return result.data[0]

    def update_cell_assumption(
        self,
        initiative_id: str,
        assumption_id: str,
        comment: str,
        user_id: str,
    ) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_cell_assumptions")
            .update(
                {
                    "comment": comment,
                    "updated_by": user_id,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", assumption_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_cell_assumption(self, initiative_id: str, assumption_id: str) -> None:
        (
            self._c.table("financial_cell_assumptions")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", assumption_id)
            .execute()
        )

    def _find_financial_entries(self, initiative_id: str, row: dict) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_entries")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("year", row["year"])
        )
        query = self._match_period(query, row)
        result = query.execute()
        return result.data or []

    def _write_financial_entry(self, row: dict, row_id: str | None = None):  # type: ignore[no-untyped-def,type-arg]
        try:
            return self._execute_financial_entry_write(row, row_id)
        except Exception as exc:
            text = str(exc)
            if "Could not find the" not in text or "financial_entries" not in text:
                raise
            trimmed = {
                key: value for key, value in row.items() if key not in _OPTIONAL_ENTRY_COLUMNS
            }
            return self._execute_financial_entry_write(trimmed, row_id)

    def _execute_financial_entry_write(self, row: dict, row_id: str | None = None):  # type: ignore[no-untyped-def,type-arg]
        if row_id:
            return (
                self._c.table("financial_entries")
                .update(row)
                .eq("tenant_id", self._tid)
                .eq("id", row_id)
                .execute()
            )
        return self._c.table("financial_entries").insert(row).execute()

    def _find_cost_lines(self, initiative_id: str, row: dict) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_cost_lines")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("category_key", row.get("category_key", "other"))
            .eq("year", row["year"])
            .eq("is_recurring", row["is_recurring"])
        )
        query = self._match_period(query, row)
        result = query.execute()
        return result.data or []

    @staticmethod
    def _cost_row_is_zero(row: dict) -> bool:  # type: ignore[type-arg]
        return (
            Decimal(str(row.get("amount_plan") or "0")) == 0
            and Decimal(str(row.get("amount_actual") or "0")) == 0
        )

    def _find_metric_values(self, initiative_id: str, row: dict) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_metric_values")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("metric_key", row["metric_key"])
            .eq("year", row["year"])
        )
        query = self._match_period(query, row)
        try:
            result = query.execute()
        except Exception as exc:
            if self._is_missing_table(exc, "financial_metric_values"):
                return []
            raise
        return result.data or []

    def _find_forecasts(self, initiative_id: str, row: dict) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_forecasts")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("line_type", row["line_type"])
            .eq("line_key", row["line_key"])
            .eq("year", row["year"])
        )
        query = self._match_period(query, row)
        try:
            result = query.execute()
        except Exception as exc:
            if self._is_missing_table(exc, "financial_forecasts"):
                return []
            raise
        return result.data or []

    @staticmethod
    def _match_period(query, row: dict):  # type: ignore[no-untyped-def,type-arg]
        if row.get("quarter") is None:
            query = query.is_("quarter", "null")
        else:
            query = query.eq("quarter", row["quarter"])
        if row.get("month") is None:
            query = query.is_("month", "null")
        else:
            query = query.eq("month", row["month"])
        return query

    @staticmethod
    def _is_missing_table(exc: Exception, table_name: str) -> bool:
        text = str(exc)
        return table_name in text and (
            "Could not find the table" in text or "does not exist" in text or "schema cache" in text
        )
