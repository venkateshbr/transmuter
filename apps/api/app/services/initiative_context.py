"""Initiative context pull skill implementation."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.domain.initiative_context import (
    CompletedMilestoneContext,
    FinancialsContextSummary,
    InitiativeContextPullResult,
    KPIContextItem,
    KPIsContextSummary,
    LastStatusUpdateContext,
    MilestonesContextSummary,
    NewRiskContext,
    RisksContextSummary,
)
from app.repositories.initiative_context import InitiativeContextRepository


class InitiativeContextService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = InitiativeContextRepository(client, tenant_id)

    def pull_context(
        self,
        initiative_id: str,
        *,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> InitiativeContextPullResult:
        start = period_start or _quarter_start(date.today())
        end = period_end or date.today()
        if start > end:
            raise HTTPException(
                status_code=422,
                detail="period_start must be on or before period_end",
            )
        initiative = self._repo.get_initiative(initiative_id)
        if not initiative:
            raise HTTPException(status_code=404, detail="Initiative not found")

        milestones = self._repo.list_milestones(initiative_id)
        kpis = self._repo.list_kpis(initiative_id)
        kpi_entries = self._repo.list_kpi_entries([item["id"] for item in kpis])
        risks = self._repo.list_risks(initiative_id)
        financial_entries = self._repo.list_financial_entries(initiative_id)
        cost_lines = self._repo.list_cost_lines(initiative_id)
        last_update = self._repo.get_last_status_update(initiative_id)

        return InitiativeContextPullResult(
            initiative_id=str(initiative["id"]),
            period_start=start.isoformat(),
            period_end=end.isoformat(),
            milestones_summary=_milestones_summary(milestones, start, end),
            kpis_summary=_kpis_summary(kpis, kpi_entries),
            risks_summary=_risks_summary(risks, start, end),
            financials_summary=_financials_summary(financial_entries, cost_lines, start, end),
            last_update=_last_update(last_update),
            sources=[
                "initiatives",
                "milestones",
                "kpis",
                "kpi_entries",
                "risks",
                "financial_entries",
                "financial_cost_lines",
                "status_updates",
            ],
        )


def _milestones_summary(
    milestones: list[dict[str, Any]],
    period_start: date,
    period_end: date,
) -> MilestonesContextSummary:
    completed_this_period = []
    for milestone in milestones:
        actual_end = _parse_date(milestone.get("actual_end"))
        if actual_end and period_start <= actual_end <= period_end:
            completed_this_period.append(
                CompletedMilestoneContext(
                    name=milestone["name"],
                    completed_at=actual_end.isoformat(),
                )
            )
    return MilestonesContextSummary(
        total=len(milestones),
        complete=sum(1 for item in milestones if item.get("status") == "complete"),
        overdue=sum(1 for item in milestones if item.get("status") == "overdue"),
        at_risk=sum(1 for item in milestones if _milestone_at_risk(item, period_end)),
        completed_this_period=completed_this_period,
    )


def _kpis_summary(kpis: list[dict[str, Any]], entries: list[dict[str, Any]]) -> KPIsContextSummary:
    entries_by_kpi: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        entries_by_kpi.setdefault(entry["kpi_id"], []).append(entry)
    items = []
    for kpi in kpis:
        latest = _latest_kpi_entry(entries_by_kpi.get(kpi["id"], []))
        target = _dec(latest.get("value_base")) if latest else None
        actual = _dec(latest.get("value_actual")) if latest else None
        items.append(
            KPIContextItem(
                name=kpi["name"],
                target_base=_money(target) if target is not None else None,
                latest_actual=_money(actual) if actual is not None else None,
                on_track=bool(target is not None and actual is not None and actual >= target),
            )
        )
    return KPIsContextSummary(kpis=items)


def _risks_summary(
    risks: list[dict[str, Any]],
    period_start: date,
    period_end: date,
) -> RisksContextSummary:
    open_risks = [item for item in risks if item.get("status") != "closed"]
    return RisksContextSummary(
        open_high=sum(1 for item in open_risks if _risk_level(item) == "high"),
        open_medium=sum(1 for item in open_risks if _risk_level(item) == "medium"),
        new_this_period=[
            NewRiskContext(description=item["description"])
            for item in risks
            if _date_in_period(item.get("created_at"), period_start, period_end)
        ],
    )


def _financials_summary(
    entries: list[dict[str, Any]],
    cost_lines: list[dict[str, Any]],
    period_start: date,
    period_end: date,
) -> FinancialsContextSummary:
    period_entries = [item for item in entries if _financial_row_in_period(item, period_start, period_end)]
    period_costs = [item for item in cost_lines if _financial_row_in_period(item, period_start, period_end)]
    return FinancialsContextSummary(
        revenue_plan=_money(sum((_dec(item.get("revenue_uplift_base")) for item in period_entries), Decimal("0"))),
        revenue_actual=_money(
            sum((_dec(item.get("revenue_uplift_actual")) for item in period_entries), Decimal("0"))
        ),
        costs_plan=_money(sum((_dec(item.get("amount_plan")) for item in period_costs), Decimal("0"))),
        costs_actual=_money(sum((_dec(item.get("amount_actual")) for item in period_costs), Decimal("0"))),
    )


def _last_update(row: dict[str, Any] | None) -> LastStatusUpdateContext | None:
    if not row:
        return None
    return LastStatusUpdateContext(
        rag_status=row["rag_status"],
        submitted_at=row.get("submitted_at"),
        summary=row["summary"],
    )


def _milestone_at_risk(row: dict[str, Any], period_end: date) -> bool:
    if row.get("status") in {"overdue", "at_risk"}:
        return True
    planned_end = _parse_date(row.get("planned_end"))
    return bool(row.get("status") != "complete" and planned_end and planned_end < period_end)


def _latest_kpi_entry(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not entries:
        return None
    return sorted(
        entries,
        key=lambda item: (int(item.get("year") or 0), int(item.get("quarter") or 0)),
        reverse=True,
    )[0]


def _risk_level(row: dict[str, Any]) -> str | None:
    return row.get("rating") or row.get("impact")


def _financial_row_in_period(row: dict[str, Any], period_start: date, period_end: date) -> bool:
    year = int(row["year"])
    quarter = row.get("quarter")
    if quarter:
        start_month = (int(quarter) - 1) * 3 + 1
        row_start = date(year, start_month, 1)
        row_end = _quarter_end(year, int(quarter))
    else:
        row_start = date(year, 1, 1)
        row_end = date(year, 12, 31)
    return row_start <= period_end and row_end >= period_start


def _date_in_period(value: str | None, period_start: date, period_end: date) -> bool:
    parsed = _parse_date(value)
    return bool(parsed and period_start <= parsed <= period_end)


def _parse_date(value: str | date | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return date.fromisoformat(value)


def _quarter_start(value: date) -> date:
    start_month = ((value.month - 1) // 3) * 3 + 1
    return date(value.year, start_month, 1)


def _quarter_end(year: int, quarter: int) -> date:
    month = quarter * 3
    return date(year, month, monthrange(year, month)[1])


def _dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _money(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.0001'))}"
