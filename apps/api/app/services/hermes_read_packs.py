"""PII-safe, tenant-scoped read packs exposed to Hermes."""

from __future__ import annotations

from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from supabase import Client

from app.core.auth import CurrentUser
from app.services.ai import CopilotSnapshot, CopilotToolRegistry


class HermesReadPackService:
    """Build compact business context without names, contacts, user IDs, or raw rows."""

    def __init__(self, client: Client, current_user: CurrentUser) -> None:
        self.registry = CopilotToolRegistry(client, current_user)

    def portfolio_overview(self) -> dict[str, Any]:
        snapshot = self.registry.build_snapshot()
        open_actions = [
            row for row in snapshot.action_items if row.get("status") in {"open", "in_progress"}
        ]
        overdue_actions = [
            row
            for row in open_actions
            if _as_date(row.get("due_date")) and _as_date(row.get("due_date")) < date.today()
        ]
        return {
            "initiative_count": len(snapshot.initiatives),
            "initiatives_by_rag": _counts(snapshot.initiatives, "rag_status"),
            "initiatives_by_stage": _counts(snapshot.initiatives, "stage"),
            "open_risk_count": sum(
                1 for row in snapshot.risks if row.get("status") not in {"closed", "resolved"}
            ),
            "risks_by_rating": _counts(snapshot.risks, "rating"),
            "milestones_by_status": _counts(snapshot.milestones, "status"),
            "open_action_count": len(open_actions),
            "overdue_action_count": len(overdue_actions),
            "kpi_count": len(snapshot.kpis),
            "response_contract": [
                "Use these tenant-scoped metrics as the source of truth.",
                "Do not infer people, owners, contact details, or records not present here.",
            ],
        }

    def initiatives_read_pack(
        self,
        *,
        search: str | None = None,
        rag_status: str | None = None,
        stage: str | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        snapshot = self.registry.build_snapshot()
        rows = snapshot.initiatives
        if search:
            needle = search.casefold()
            rows = [
                row
                for row in rows
                if needle in str(row.get("initiative_code") or "").casefold()
                or needle in str(row.get("name") or "").casefold()
            ]
        if rag_status:
            rows = [row for row in rows if row.get("rag_status") == rag_status]
        if stage:
            rows = [row for row in rows if row.get("stage") == stage]
        return {
            "count": len(rows),
            "items": [self._safe_initiative(row, snapshot) for row in rows[:limit]],
            "truncated": len(rows) > limit,
        }

    def governance_read_pack(self) -> dict[str, Any]:
        snapshot = self.registry.build_snapshot()
        today = date.today()
        open_milestones = [row for row in snapshot.milestones if row.get("status") != "complete"]
        overdue_milestones = [
            row
            for row in open_milestones
            if _as_date(row.get("planned_end")) and _as_date(row.get("planned_end")) < today
        ]
        open_risks = [
            row for row in snapshot.risks if row.get("status") not in {"closed", "resolved"}
        ]
        return {
            "milestone_count": len(snapshot.milestones),
            "open_milestone_count": len(open_milestones),
            "overdue_milestone_count": len(overdue_milestones),
            "milestones_by_status": _counts(snapshot.milestones, "status"),
            "milestones_by_priority": _counts(snapshot.milestones, "priority"),
            "open_risk_count": len(open_risks),
            "risks_by_rating": _counts(open_risks, "rating"),
            "risks_by_type": _counts(open_risks, "type"),
            "escalated_risk_count": sum(1 for row in open_risks if row.get("escalated")),
        }

    def financials_read_pack(self, *, year: int | None = None) -> dict[str, Any]:
        snapshot = self.registry.build_snapshot()
        entries = snapshot.financial_entries
        costs = snapshot.cost_lines
        if year is not None:
            entries = [row for row in entries if row.get("year") == year]
            costs = [row for row in costs if row.get("year") == year]
        gm_base = sum((_decimal(row.get("gm_uplift_base")) for row in entries), Decimal("0"))
        gm_actual = sum((_decimal(row.get("gm_uplift_actual")) for row in entries), Decimal("0"))
        recurring = sum(
            (_decimal(row.get("amount_plan")) for row in costs if row.get("is_recurring")),
            Decimal("0"),
        )
        one_off = sum(
            (_decimal(row.get("amount_plan")) for row in costs if not row.get("is_recurring")),
            Decimal("0"),
        )
        return {
            "year": year,
            "currency_note": "Values use the tenant reporting currency configured in Transmuter.",
            "planned_gm_uplift": _money(gm_base),
            "actual_gm_uplift": _money(gm_actual),
            "planned_recurring_cost": _money(recurring),
            "planned_one_off_cost": _money(one_off),
            "planned_net_value": _money(gm_base - recurring),
        }

    def tool_catalog(self) -> dict[str, Any]:
        return {
            "items": [
                {
                    "name": tool["name"],
                    "domain": tool["domain"],
                    "description": tool["description"],
                    "operation": tool["operation"],
                }
                for tool in self.registry.catalog()
                if tool["operation"] == "read"
            ],
            "write_policy": "Writes are unavailable to Hermes and remain in Transmuter confirmation.",
        }

    @staticmethod
    def _safe_initiative(row: dict[str, Any], snapshot: CopilotSnapshot) -> dict[str, Any]:
        initiative_id = row.get("id")
        return {
            "initiative_code": row.get("initiative_code"),
            "name": row.get("name"),
            "type": row.get("type"),
            "impact_type": row.get("impact_type"),
            "country": row.get("country"),
            "tag": row.get("tag"),
            "priority": row.get("priority"),
            "rag_status": row.get("rag_status"),
            "stage": row.get("stage"),
            "planned_start": row.get("planned_start"),
            "planned_end": row.get("planned_end"),
            "pressure_score": row.get("pressure_score"),
            "benefit_confidence": row.get("benefit_confidence"),
            "open_risk_count": sum(
                1
                for risk in snapshot.risks
                if risk.get("initiative_id") == initiative_id
                and risk.get("status") not in {"closed", "resolved"}
            ),
            "open_milestone_count": sum(
                1
                for milestone in snapshot.milestones
                if milestone.get("initiative_id") == initiative_id
                and milestone.get("status") != "complete"
            ),
        }


def _counts(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(row.get(key) or "unspecified") for row in rows))


def _as_date(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")
