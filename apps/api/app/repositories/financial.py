"""Financial repository — typed Supabase data access."""

from __future__ import annotations

from datetime import UTC, datetime
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

    def create_cost_line(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("financial_cost_lines").insert(data).execute()
        return result.data[0]

    def update_cost_line(self, cost_line_id: str, data: dict) -> dict:  # type: ignore[type-arg]
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
    def upsert_cost_lines_batch(self, initiative_id: str, rows: list[dict]) -> list[dict]:
        """Upsert multiple cost lines at once."""
        saved = []
        for row in rows:
            row["tenant_id"] = self._tid
            row["initiative_id"] = initiative_id
            existing_rows = self._find_cost_lines(initiative_id, row)
            if existing_rows:
                row["updated_at"] = datetime.now(UTC).isoformat()
                result = None
                for existing in existing_rows:
                    result = (
                        self._c.table("financial_cost_lines")
                        .update(row)
                        .eq("tenant_id", self._tid)
                        .eq("id", existing["id"])
                        .execute()
                    )
            else:
                row["id"] = str(uuid4())
                result = self._c.table("financial_cost_lines").insert(row).execute()
            if result.data:
                saved.append(result.data[0])
        return saved

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
        assumption_id: str,
        comment: str,
        user_id: str,
    ) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("financial_cell_assumptions")
            .update({
                "comment": comment,
                "updated_by": user_id,
                "updated_at": datetime.now(UTC).isoformat(),
            })
            .eq("tenant_id", self._tid)
            .eq("id", assumption_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_cell_assumption(self, assumption_id: str) -> None:
        (
            self._c.table("financial_cell_assumptions")
            .delete()
            .eq("tenant_id", self._tid)
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
                key: value
                for key, value in row.items()
                if key not in _OPTIONAL_ENTRY_COLUMNS
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
            .eq("name", row["name"])
            .eq("year", row["year"])
            .eq("is_recurring", row["is_recurring"])
        )
        query = self._match_period(query, row)
        result = query.execute()
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
