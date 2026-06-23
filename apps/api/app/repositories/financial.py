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
        self._page_size = 1000

    def _select_tenant_pages(self, table_name: str, columns: str = "*") -> list[dict]:  # type: ignore[type-arg]
        rows: list[dict] = []  # type: ignore[type-arg]
        start = 0
        while True:
            result = (
                self._c.table(table_name)
                .select(columns)
                .eq("tenant_id", self._tid)
                .range(start, start + self._page_size - 1)
                .execute()
            )
            page = result.data or []
            rows.extend(page)
            if len(page) < self._page_size:
                return rows
            start += self._page_size

    # ── Financial Entries ─────────────────────────────────────────────────────

    def get_entries(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        """Return all financial_entries rows for an initiative, ordered by year/quarter."""
        try:
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
        except Exception as exc:
            if self._is_missing_table(exc, "financial_entries"):
                return []
            raise

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
        try:
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
        except Exception as exc:
            if self._is_missing_table(exc, "financial_entries"):
                return []
            raise

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
            text = str(exc)
            if self._is_missing_table(exc, "financial_metric_values") or "metric_key" in text:
                return []
            raise

    def list_benefit_lines(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_benefit_lines")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("display_order")
            .order("name")
            .execute()
        )
        return result.data or []

    def list_all_benefit_lines(self) -> list[dict]:  # type: ignore[type-arg]
        return self._select_tenant_pages("financial_benefit_lines")

    def get_benefit_line(self, initiative_id: str, benefit_line_id: str) -> dict | None:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_benefit_lines")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", benefit_line_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def update_benefit_line(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: dict,  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "updated_by": user_id,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = (
            self._c.table("financial_benefit_lines")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("id", benefit_line_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def tenant_user_exists(self, user_id: str) -> bool:
        result = (
            self._c.table("users")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("id", user_id)
            .maybe_single()
            .execute()
        )
        return bool(result and result.data)

    def create_benefit_line_validation_event(
        self,
        initiative_id: str,
        benefit_line_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "initiative_id": initiative_id,
            "benefit_line_id": benefit_line_id,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("financial_benefit_line_validation_events").insert(payload).execute()
        return result.data[0]

    def list_benefit_line_validation_events(
        self,
        initiative_id: str,
        benefit_line_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_benefit_line_validation_events")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .eq("benefit_line_id", benefit_line_id)
                .order("created_at")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "financial_benefit_line_validation_events"):
                return []
            raise

    def list_configurable_metric_values(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_metric_values")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("year")
            .order("month")
            .execute()
        )
        return result.data or []

    def create_benefit_lines_batch(
        self,
        initiative_id: str,
        rows: list[dict],  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        if not rows:
            return []
        now = datetime.now(UTC).isoformat()
        payload = []
        for row in rows:
            payload.append(
                {
                    **row,
                    "id": row.get("id") or str(uuid4()),
                    "tenant_id": self._tid,
                    "initiative_id": initiative_id,
                    "created_by": row.get("created_by") or user_id,
                    "updated_by": row.get("updated_by") or user_id,
                    "created_at": row.get("created_at") or now,
                    "updated_at": row.get("updated_at") or now,
                }
            )
        result = self._c.table("financial_benefit_lines").insert(payload).execute()
        return result.data or []

    def upsert_configurable_metric_values_batch(
        self,
        initiative_id: str,
        rows: list[dict],  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        saved = []
        now = datetime.now(UTC).isoformat()
        for row in rows:
            payload = {
                **row,
                "tenant_id": self._tid,
                "initiative_id": initiative_id,
                "updated_by": row.get("updated_by") or user_id,
                "updated_at": row.get("updated_at") or now,
            }
            existing = self._find_configurable_metric_value(initiative_id, payload)
            if existing:
                result = (
                    self._c.table("financial_metric_values")
                    .update(payload)
                    .eq("tenant_id", self._tid)
                    .eq("id", existing["id"])
                    .execute()
                )
            else:
                payload["id"] = payload.get("id") or str(uuid4())
                payload["created_by"] = payload.get("created_by") or user_id
                payload["created_at"] = payload.get("created_at") or now
                result = self._c.table("financial_metric_values").insert(payload).execute()
            if result.data:
                saved.append(result.data[0])
        return saved

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

    def list_financial_scope(self, initiative_id: str) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("initiative_financial_scope")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "initiative_financial_scope"):
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

    def initiatives_by_code(self) -> dict[str, dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("initiatives")
            .select("id,initiative_code,name,stage,workstream_id")
            .eq("tenant_id", self._tid)
            .is_("archived_at", "null")
            .execute()
        )
        return {
            str(row.get("initiative_code") or "").strip().upper(): row
            for row in result.data or []
            if row.get("initiative_code")
        }

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
            .select("id,name")
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

    def upsert_benefit_ledger_entry(self, initiative_id: str, data: dict) -> tuple[dict, bool]:  # type: ignore[type-arg]
        existing = (
            self._c.table("benefit_realization_ledger")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("period_granularity", data["period_granularity"])
            .eq("period_start", data["period_start"])
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            row = self.update_benefit_ledger_entry(
                initiative_id,
                existing.data["id"],
                data,
            )
            return row, False
        return self.create_benefit_ledger_entry(initiative_id, data), True

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

    def replace_financial_scope(
        self,
        initiative_id: str,
        metric_definition_ids: list[str],
        cost_category_ids: list[str],
        all_metric_definition_ids: list[str] | None = None,
        all_cost_category_ids: list[str] | None = None,
    ) -> None:
        try:
            (
                self._c.table("initiative_financial_scope")
                .delete()
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )
            active_metric_ids = set(metric_definition_ids)
            active_category_ids = set(cost_category_ids)
            metric_rows = sorted(set(all_metric_definition_ids or metric_definition_ids))
            category_rows = sorted(set(all_cost_category_ids or cost_category_ids))
            rows = [
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tid,
                    "initiative_id": initiative_id,
                    "scope_type": "metric_definition",
                    "metric_definition_id": metric_id,
                    "is_active": metric_id in active_metric_ids,
                }
                for metric_id in metric_rows
            ] + [
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tid,
                    "initiative_id": initiative_id,
                    "scope_type": "cost_category",
                    "cost_category_id": category_id,
                    "is_active": category_id in active_category_ids,
                }
                for category_id in category_rows
            ]
            if rows:
                self._c.table("initiative_financial_scope").insert(rows).execute()
        except Exception as exc:
            if self._is_missing_table(exc, "initiative_financial_scope"):
                return
            raise

    def create_cost_line(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        data = self._cost_line_with_engine_category(data)
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
        data = self._cost_line_with_engine_category(data)
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

    def list_metric_definitions(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_metric_definitions")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("display_order")
            .order("label")
            .execute()
        )
        return result.data or []

    def list_cost_categories(self) -> list[dict]:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_cost_categories")
                .select("*")
                .eq("tenant_id", self._tid)
                .order("display_order")
                .order("label")
                .execute()
            )
            return result.data or []
        except Exception as exc:
            if self._is_missing_table(exc, "financial_cost_categories"):
                return []
            raise

    def get_cost_category_by_key(self, category_key: str) -> dict | None:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_cost_categories")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("key", category_key)
                .maybe_single()
                .execute()
            )
            return result.data if result and result.data else None
        except Exception as exc:
            if self._is_missing_table(exc, "financial_cost_categories"):
                return None
            raise

    def get_cost_category_by_id(self, category_id: str) -> dict | None:  # type: ignore[type-arg]
        try:
            result = (
                self._c.table("financial_cost_categories")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("id", category_id)
                .maybe_single()
                .execute()
            )
            return result.data if result and result.data else None
        except Exception as exc:
            if self._is_missing_table(exc, "financial_cost_categories"):
                return None
            raise

    def create_cost_category(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
            "updated_at": data.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("financial_cost_categories").insert(payload).execute()
        return result.data[0]

    def update_cost_category(
        self,
        cost_category_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict | None:  # type: ignore[type-arg]
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("financial_cost_categories")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", cost_category_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def list_tenant_annual_baselines(
        self,
        baseline_year: int | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_tenant_annual_baselines")
            .select("*")
            .eq("tenant_id", self._tid)
        )
        if baseline_year is not None:
            query = query.eq("baseline_year", baseline_year)
        result = query.order("baseline_year").execute()
        return result.data or []

    def list_initiative_annual_baselines(
        self,
        initiative_id: str,
        baseline_year: int | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_initiative_annual_baselines")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
        )
        if baseline_year is not None:
            query = query.eq("baseline_year", baseline_year)
        result = query.order("baseline_year").execute()
        return result.data or []

    def list_all_initiative_annual_baselines(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_initiative_annual_baselines")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("initiative_id")
            .order("baseline_year")
            .execute()
        )
        return result.data or []

    def upsert_tenant_annual_baselines(
        self,
        rows: list[dict],  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        saved = []
        now = datetime.now(UTC).isoformat()
        for row in rows:
            payload = {
                **row,
                "tenant_id": self._tid,
                "updated_by": row.get("updated_by") or user_id,
                "updated_at": row.get("updated_at") or now,
            }
            existing = (
                self._c.table("financial_tenant_annual_baselines")
                .select("id")
                .eq("tenant_id", self._tid)
                .eq("metric_definition_id", payload["metric_definition_id"])
                .eq("baseline_year", payload["baseline_year"])
                .maybe_single()
                .execute()
            )
            if existing and existing.data:
                result = (
                    self._c.table("financial_tenant_annual_baselines")
                    .update(payload)
                    .eq("tenant_id", self._tid)
                    .eq("id", existing.data["id"])
                    .execute()
                )
            else:
                payload["id"] = payload.get("id") or str(uuid4())
                payload["created_by"] = payload.get("created_by") or user_id
                payload["created_at"] = payload.get("created_at") or now
                result = (
                    self._c.table("financial_tenant_annual_baselines").insert(payload).execute()
                )
            if result.data:
                saved.append(result.data[0])
        return saved

    def upsert_initiative_annual_baselines(
        self,
        initiative_id: str,
        rows: list[dict],  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> list[dict]:  # type: ignore[type-arg]
        saved = []
        now = datetime.now(UTC).isoformat()
        for row in rows:
            payload = {
                **row,
                "tenant_id": self._tid,
                "initiative_id": initiative_id,
                "updated_by": row.get("updated_by") or user_id,
                "updated_at": row.get("updated_at") or now,
            }
            existing = (
                self._c.table("financial_initiative_annual_baselines")
                .select("id")
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .eq("metric_definition_id", payload["metric_definition_id"])
                .eq("baseline_year", payload["baseline_year"])
                .maybe_single()
                .execute()
            )
            if existing and existing.data:
                result = (
                    self._c.table("financial_initiative_annual_baselines")
                    .update(payload)
                    .eq("tenant_id", self._tid)
                    .eq("id", existing.data["id"])
                    .execute()
                )
            else:
                payload["id"] = payload.get("id") or str(uuid4())
                payload["created_by"] = payload.get("created_by") or user_id
                payload["created_at"] = payload.get("created_at") or now
                result = (
                    self._c.table("financial_initiative_annual_baselines").insert(payload).execute()
                )
            if result.data:
                saved.append(result.data[0])
        return saved

    def list_financial_scenarios(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_scenarios")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("display_order")
            .order("label")
            .execute()
        )
        return result.data or []

    def list_financial_bridge_rows(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_bridge_rows")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("display_order")
            .order("label")
            .execute()
        )
        return result.data or []

    def list_financial_attribute_definitions(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_attribute_definitions")
            .select("*")
            .eq("tenant_id", self._tid)
            .order("entity_type")
            .order("display_order")
            .order("label")
            .execute()
        )
        return result.data or []

    def create_financial_bridge_row(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {**data, "tenant_id": self._tid}
        result = self._c.table("financial_bridge_rows").insert(payload).execute()
        return result.data[0]

    def update_financial_bridge_row(
        self,
        bridge_row_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict | None:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_bridge_rows")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", bridge_row_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def create_financial_attribute_definition(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {**data, "tenant_id": self._tid}
        result = self._c.table("financial_attribute_definitions").insert(payload).execute()
        return result.data[0]

    def update_financial_attribute_definition(
        self,
        attribute_definition_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict | None:  # type: ignore[type-arg]
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("financial_attribute_definitions")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", attribute_definition_id)
            .execute()
        )
        return result.data[0] if result.data else None

    def get_reporting_settings(self) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("organizations")
            .select("fiscal_year_start_month,reporting_currency")
            .eq("id", self._tid)
            .maybe_single()
            .execute()
        )
        return result.data or {}

    def update_reporting_settings(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = self._c.table("organizations").update(payload).eq("id", self._tid).execute()
        return result.data[0] if result.data else payload

    def create_metric_definition(
        self,
        data: dict,  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        now = datetime.now(UTC).isoformat()
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_by": data.get("created_by") or user_id,
            "updated_by": data.get("updated_by") or user_id,
            "created_at": data.get("created_at") or now,
            "updated_at": data.get("updated_at") or now,
        }
        result = self._c.table("financial_metric_definitions").insert(payload).execute()
        return result.data[0]

    def update_metric_definition(
        self,
        metric_definition_id: str,
        data: dict,  # type: ignore[type-arg]
        user_id: str | None = None,
    ) -> dict:  # type: ignore[type-arg]
        payload = {**data, "updated_by": user_id, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("financial_metric_definitions")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", metric_definition_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def create_financial_scenario(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_at": data.get("created_at") or datetime.now(UTC).isoformat(),
            "updated_at": data.get("updated_at") or datetime.now(UTC).isoformat(),
        }
        result = self._c.table("financial_scenarios").insert(payload).execute()
        return result.data[0]

    def update_financial_scenario(
        self,
        scenario_id: str,
        data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("financial_scenarios")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", scenario_id)
            .execute()
        )
        return result.data[0] if result.data else {}

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
        replacement = self.get_cost_category_by_key(replacement_key)
        result = (
            self._c.table("financial_cost_lines")
            .update(
                {
                    "category_key": replacement_key,
                    "category_id": replacement.get("id") if replacement else None,
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("tenant_id", self._tid)
            .eq("category_key", category_key)
            .execute()
        )
        (
            self._c.table("financial_cost_categories")
            .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
            .eq("tenant_id", self._tid)
            .eq("key", category_key)
            .execute()
        )
        try:
            (
                self._c.table("financial_config_items")
                .update({"is_active": False, "updated_at": datetime.now(UTC).isoformat()})
                .eq("tenant_id", self._tid)
                .eq("key", category_key)
                .eq("item_type", "cost_category")
                .execute()
            )
        except Exception as exc:
            if not self._is_missing_table(exc, "financial_config_items"):
                raise
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
            .select(
                "id,initiative_code,name,stage,workstream_id,tag,"
                "workstreams(name),initiative_business_units(business_unit_id, business_units(id, name))"
            )
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
        for table_name in ("financial_metric_values", "financial_benefit_lines"):
            (
                self._c.table(table_name)
                .delete()
                .eq("tenant_id", self._tid)
                .eq("initiative_id", initiative_id)
                .execute()
            )

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
            row = self._cost_line_with_engine_category(row)
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

    def upsert_locked_actual_cost_lines_batch(
        self,
        initiative_id: str,
        rows: list[dict],  # type: ignore[type-arg]
    ) -> list[dict]:  # type: ignore[type-arg]
        """Update only actual amounts when the approved plan is locked."""
        saved = []
        now = datetime.now(UTC).isoformat()
        for row in rows:
            row = self._cost_line_with_engine_category(row)
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            actual_amount = Decimal(str(row.get("amount_actual") or "0"))
            existing_rows = self._find_cost_lines(initiative_id, row)
            if existing_rows:
                for existing in existing_rows:
                    result = (
                        self._c.table("financial_cost_lines")
                        .update(
                            {
                                "amount_actual": row.get("amount_actual"),
                                "updated_at": now,
                            }
                        )
                        .eq("tenant_id", self._tid)
                        .eq("id", existing["id"])
                        .execute()
                    )
                    if result.data:
                        saved.append(result.data[0])
                continue
            if actual_amount == 0:
                continue
            payload = {
                **row,
                "amount_plan": "0.0000",
                "id": str(uuid4()),
                "created_at": row.get("created_at") or now,
                "updated_at": row.get("updated_at") or now,
            }
            result = self._c.table("financial_cost_lines").insert(payload).execute()
            if result.data:
                saved.append(result.data[0])
        return saved

    def _cost_line_with_engine_category(self, data: dict) -> dict:  # type: ignore[type-arg]
        payload = dict(data)
        category = None
        raw_category_id = payload.get("category_id")
        if raw_category_id:
            category = self.get_cost_category_by_id(str(raw_category_id))
        if not category:
            category_key = str(payload.get("category_key") or "other")
            category = self.get_cost_category_by_key(category_key)
        if category:
            payload["category_id"] = category["id"]
            payload["category_key"] = category["key"]
        else:
            payload["category_key"] = str(payload.get("category_key") or "other")
            payload.pop("category_id", None)
        return payload

    # ── Portfolio aggregation ─────────────────────────────────────────────────

    def get_all_entries(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all financial_entries for the tenant (portfolio-level)."""
        try:
            return self._select_tenant_pages("financial_entries")
        except Exception as exc:
            if self._is_missing_table(exc, "financial_entries"):
                return []
            raise

    def get_all_cost_lines(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all cost lines for the tenant (portfolio-level)."""
        return self._select_tenant_pages("financial_cost_lines")

    def get_all_metric_values(self) -> list[dict]:  # type: ignore[type-arg]
        """Return all custom financial metric values for the tenant."""
        try:
            return self._select_tenant_pages("financial_metric_values")
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
            .select("*")
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

    def _find_configurable_metric_value(
        self,
        initiative_id: str,
        row: dict,  # type: ignore[type-arg]
    ) -> dict | None:  # type: ignore[type-arg]
        query = (
            self._c.table("financial_metric_values")
            .select("id")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("metric_definition_id", row["metric_definition_id"])
            .eq("scenario_id", row["scenario_id"])
            .eq("year", row["year"])
            .eq("month", row["month"])
        )
        benefit_line_id = row.get("benefit_line_id")
        if benefit_line_id:
            query = query.eq("benefit_line_id", benefit_line_id)
        else:
            query = query.is_("benefit_line_id", "null")
        result = query.maybe_single().execute()
        return result.data if result and result.data else None

    def _upsert_metric_values_from_legacy_entries(
        self,
        initiative_id: str,
        rows: list[dict],
    ) -> list[dict]:  # type: ignore[type-arg]
        definitions = {row["key"]: row["id"] for row in self.list_metric_definitions()}
        scenarios = {row["key"]: row["id"] for row in self.list_financial_scenarios()}
        metric_field_map = {
            "revenue_uplift": (
                "revenue_uplift_base",
                "revenue_uplift_high",
                "revenue_uplift_actual",
            ),
            "gross_margin": ("gross_margin_base", "gross_margin_high", "gross_margin_actual"),
            "gm_uplift": ("gm_uplift_base", "gm_uplift_high", "gm_uplift_actual"),
            "cogs": ("cogs_base", "cogs_high", "cogs_actual"),
        }
        scenario_keys = ("plan_base", "plan_high", "actual")
        payload: list[dict] = []
        for row in rows:
            year = int(row["year"])
            month = int(row.get("month") or ((int(row.get("quarter") or 1) - 1) * 3 + 1))
            for scenario_key in scenario_keys:
                scenario_id = scenarios.get(scenario_key)
                if not scenario_id:
                    continue
                for metric_key, field_names in metric_field_map.items():
                    field_name = field_names[scenario_keys.index(scenario_key)]
                    value = row.get(field_name)
                    if value is None:
                        continue
                    metric_definition_id = definitions.get(metric_key)
                    if not metric_definition_id:
                        continue
                    payload.append(
                        {
                            "metric_definition_id": metric_definition_id,
                            "scenario_id": scenario_id,
                            "benefit_line_id": None,
                            "year": year,
                            "month": month,
                            "value": value,
                            "status": "draft",
                            "note": None,
                        }
                    )
        if not payload:
            return []
        return self.upsert_configurable_metric_values_batch(initiative_id, payload)

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
