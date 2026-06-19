"""Deterministic loader for the anonymised initiative portfolio workbook."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4
from zipfile import ZipFile

from supabase import Client

from app.services.initiative_workbook import (
    _clean_text,
    _date_text,
    _read_sheet,
    _shared_strings,
    _sheet_paths,
)

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


@dataclass
class WorkbookInitiative:
    reference: str
    name: str
    summary: dict[str, str] = field(default_factory=dict)
    charter: dict[str, str] = field(default_factory=dict)
    benefits: list[dict[str, str]] = field(default_factory=list)
    costs: list[dict[str, str]] = field(default_factory=list)
    kpis: list[dict[str, str]] = field(default_factory=list)
    milestones: list[dict[str, str]] = field(default_factory=list)
    risks: list[dict[str, str]] = field(default_factory=list)
    status_updates: list[dict[str, str]] = field(default_factory=list)


class PortfolioWorkbookReloadService:
    """Reset and load a tenant portfolio from Initiative_Portfolio_Anonymised.xlsx."""

    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID | None = None) -> None:
        self._client = client
        self._tenant_id = str(tenant_id)
        self._user_id = str(user_id) if user_id else None

    def reload(self, data: bytes, *, reset: bool = True) -> dict[str, int]:
        parsed = self.parse(data)
        if reset:
            self.reset_portfolio_data()

        metric_defs = self._metric_definitions()
        scenarios = self._financial_scenarios()
        business_units = self._ensure_business_units(parsed)
        workstreams = self._ensure_workstreams(parsed, business_units, self._user_ids_by_name())
        stages = self._stage_by_gate_number()

        counts = {
            "initiatives": 0,
            "business_units": len(business_units),
            "workstreams": len(workstreams),
            "initiative_business_units": 0,
            "benefit_lines": 0,
            "metric_values": 0,
            "cost_lines": 0,
            "kpis": 0,
            "kpi_entries": 0,
            "milestones": 0,
            "risks": 0,
            "status_updates": 0,
        }
        for item in parsed.values():
            initiative_id = self._create_initiative(item, workstreams, stages)
            counts["initiatives"] += 1
            counts["initiative_business_units"] += self._link_business_units(
                initiative_id, item, business_units
            )
            benefit_line_ids = self._create_benefit_lines(initiative_id, item, metric_defs)
            counts["benefit_lines"] += len(benefit_line_ids)
            counts["metric_values"] += self._create_metric_values(
                initiative_id, item, metric_defs, scenarios, benefit_line_ids
            )
            counts["cost_lines"] += self._create_cost_lines(initiative_id, item)
            kpi_counts = self._create_kpis(initiative_id, item)
            counts["kpis"] += kpi_counts["kpis"]
            counts["kpi_entries"] += kpi_counts["kpi_entries"]
            counts["milestones"] += self._create_milestones(initiative_id, item)
            counts["risks"] += self._create_risks(initiative_id, item)
            counts["status_updates"] += self._create_status_updates(initiative_id, item)

        return counts

    def dry_run(self, data: bytes) -> dict[str, Any]:
        parsed = self.parse(data)
        summary = self.workbook_summary(parsed)
        metric_defs = self._metric_definitions()
        scenarios = self._financial_scenarios()
        stages = self._stage_by_gate_number()
        summary["missing_metric_keys"] = [
            key for key in summary["required_metric_keys"] if key not in metric_defs
        ]
        summary["missing_scenario_keys"] = [
            key for key in summary["required_scenario_keys"] if key not in scenarios
        ]
        summary["missing_stage_gate_numbers"] = [
            gate for gate in summary["required_stage_gate_numbers"] if gate not in stages
        ]
        summary["ready"] = not (
            summary["missing_metric_keys"]
            or summary["missing_scenario_keys"]
            or summary["missing_stage_gate_numbers"]
        )
        return summary

    def parse(self, data: bytes) -> dict[str, WorkbookInitiative]:
        with ZipFile(BytesIO(data)) as zf:
            sheets = _sheet_paths(zf)
            shared_strings = _shared_strings(zf)
            rows_by_sheet = {
                name: _read_sheet(zf, path, shared_strings) for name, path in sheets.items()
            }

        initiatives = self._parse_summary(rows_by_sheet.get("Initiative Summary", []))
        self._merge_charter(rows_by_sheet.get("Charter Details", []), initiatives)
        self._merge_rows(rows_by_sheet.get("Benefits", []), initiatives, "benefits")
        self._merge_rows(rows_by_sheet.get("Costs", []), initiatives, "costs")
        self._merge_rows(rows_by_sheet.get("KPIs", []), initiatives, "kpis")
        self._merge_rows(rows_by_sheet.get("Milestones", []), initiatives, "milestones")
        self._merge_rows(rows_by_sheet.get("Risks", []), initiatives, "risks")
        self._merge_rows(rows_by_sheet.get("Status Updates", []), initiatives, "status_updates")
        return initiatives

    @classmethod
    def workbook_summary(cls, parsed: dict[str, WorkbookInitiative]) -> dict[str, Any]:
        business_units = sorted(
            {name for item in parsed.values() for name in cls._business_unit_names(item)}
        )
        workstreams = sorted(
            {cls._workstream_name(item) for item in parsed.values() if cls._workstream_name(item)}
        )
        required_metric_keys = sorted(
            {_benefit_metric_key(row) for item in parsed.values() for row in item.benefits}
        )
        required_scenario_keys = sorted(
            {
                _scenario_key(row.get("Lane"))
                for item in parsed.values()
                for row in item.benefits
                if _scenario_key(row.get("Lane"))
            }
        )
        required_stage_gate_numbers = sorted(
            {
                gate
                for item in parsed.values()
                for gate in [_stage_gate_number(item)]
                if gate is not None
            }
        )
        benefit_line_keys = {
            (
                item.reference,
                _clean_text(row.get("_id")) or _clean_text(row.get("Name")),
                _benefit_metric_key(row),
                _clean_text(row.get("Name")),
            )
            for item in parsed.values()
            for row in item.benefits
            if _clean_text(row.get("Name"))
        }
        metric_values = sum(
            1
            for item in parsed.values()
            for row in item.benefits
            for _year, _month, value in _monthly_values(row)
            if _workbook_financial_value(value, row.get("Denomination")) is not None
        )
        cost_lines = sum(
            1
            for item in parsed.values()
            for row in item.costs
            for _year, _month, value in (_monthly_values(row) or _fallback_cost_periods(row))
            if _clean_text(row.get("Lane")).lower() in {"plan", "actual"}
            and _workbook_money(value) is not None
        )
        kpi_names = {
            (item.reference, _clean_text(row.get("Name")))
            for item in parsed.values()
            for row in item.kpis
            if _clean_text(row.get("Name"))
        }
        kpi_entries = {
            (item.reference, _clean_text(row.get("Name")), year, ((month - 1) // 3) + 1)
            for item in parsed.values()
            for row in item.kpis
            for year, month, value in _monthly_values(row)
            if _clean_text(row.get("Name")) and _decimal_or_none(value) is not None
        }
        return {
            "initiatives": len(parsed),
            "business_units": len(business_units),
            "workstreams": len(workstreams),
            "benefit_lines": len(benefit_line_keys),
            "metric_values": metric_values,
            "cost_lines": cost_lines,
            "kpis": len(kpi_names),
            "kpi_entries": len(kpi_entries),
            "milestones": sum(
                1
                for item in parsed.values()
                for row in item.milestones
                if _clean_text(row.get("Name"))
            ),
            "risks": sum(
                1
                for item in parsed.values()
                for row in item.risks
                if _clean_text(row.get("Description") or row.get("Name"))
            ),
            "status_updates": sum(
                1
                for item in parsed.values()
                for row in item.status_updates
                if _clean_text(row.get("Summary"))
            ),
            "business_unit_names": business_units,
            "workstream_names": workstreams,
            "required_metric_keys": required_metric_keys,
            "required_scenario_keys": required_scenario_keys,
            "required_stage_gate_numbers": required_stage_gate_numbers,
        }

    def reset_portfolio_data(self) -> None:
        for table in (
            "action_items",
            "agenda_items",
            "meeting_initiatives",
            "gate_submissions",
            "stage_gates",
            "status_updates",
            "risks",
            "kpi_entries",
            "kpis",
            "milestone_dependencies",
            "milestone_checklist",
            "milestones",
            "financial_metric_values",
            "financial_benefit_lines",
            "financial_cost_lines",
            "initiative_financial_scope",
            "initiative_financial_selections",
            "initiative_business_units",
            "initiative_team",
            "initiatives",
        ):
            self._delete_tenant_rows(table)

    def _parse_summary(self, rows: list[list[str]]) -> dict[str, WorkbookInitiative]:
        header_index = next(
            (index for index, row in enumerate(rows) if row and row[0] == "Reference"),
            None,
        )
        if header_index is None:
            return {}
        headers = rows[header_index]
        initiatives: dict[str, WorkbookInitiative] = {}
        for row in rows[header_index + 1 :]:
            named = _row_dict(headers, row)
            reference = _clean_text(named.get("Reference"))
            name = _clean_text(named.get("Initiative"))
            if not reference or not name:
                continue
            initiatives[reference] = WorkbookInitiative(
                reference=reference,
                name=name,
                summary=named,
            )
        return initiatives

    def _merge_charter(
        self,
        rows: list[list[str]],
        initiatives: dict[str, WorkbookInitiative],
    ) -> None:
        if len(rows) < 3:
            return
        reference_row = next(
            (row for row in rows if row and _clean_text(row[0]) == "Reference"), []
        )
        name_row = next((row for row in rows if row and _clean_text(row[0]) == "Name"), [])
        columns: dict[int, str] = {}
        for index, value in enumerate(reference_row[1:], start=1):
            reference = _clean_text(value)
            if reference:
                columns[index] = reference
                initiatives.setdefault(
                    reference,
                    WorkbookInitiative(
                        reference=reference,
                        name=_clean_text(name_row[index]) if index < len(name_row) else reference,
                    ),
                )
        for row in rows[2:]:
            if not row:
                continue
            field_name = _clean_text(row[0])
            if not field_name:
                continue
            for index, reference in columns.items():
                if index < len(row):
                    initiatives[reference].charter[field_name] = _clean_text(row[index])
                    if field_name == "Name" and row[index]:
                        initiatives[reference].name = _clean_text(row[index])

    def _merge_rows(
        self,
        rows: list[list[str]],
        initiatives: dict[str, WorkbookInitiative],
        target: str,
    ) -> None:
        headers, body = _headered_rows(rows, "Reference")
        if not headers:
            return
        for row in body:
            named = _row_dict(headers, row)
            reference = _clean_text(named.get("Reference"))
            if not reference:
                continue
            name = _clean_text(named.get("Initiative"))
            initiatives.setdefault(
                reference,
                WorkbookInitiative(reference=reference, name=name or reference),
            )
            getattr(initiatives[reference], target).append(named)

    def _create_initiative(
        self,
        item: WorkbookInitiative,
        workstreams: dict[str, str],
        stages: dict[int, str],
    ) -> str:
        now = datetime.now(UTC).isoformat()
        stage = self._stage_value(item, stages)
        row = {
            "id": str(uuid4()),
            "tenant_id": self._tenant_id,
            "initiative_code": item.reference,
            "name": item.name,
            "workstream_id": workstreams.get(self._workstream_name(item).lower()),
            "owner_id": self._user_id,
            "group_owner_id": self._user_id,
            "type": _initiative_type(
                item.charter.get("Initiative Type") or item.summary.get("Type")
            ),
            "impact_type": _impact_type(item.charter.get("Impact Type")),
            "theme": _blank(item.charter.get("Theme")),
            "country": _blank(item.charter.get("Country")),
            "tag": _blank(item.charter.get("Initiative Tag") or item.summary.get("Tag")),
            "priority": _priority(item.charter.get("Priority") or item.summary.get("Priority")),
            "summary": _blank(item.charter.get("Description")),
            "context_problem": _blank(item.charter.get("Context & Problem")),
            "value_logic": _blank(item.charter.get("Value Logic & Assumptions")),
            "dependencies_text": _blank(item.charter.get("Dependencies")),
            "planned_start": _date_or_none(item.charter.get("Planned Start Date")),
            "planned_end": _date_or_none(
                item.charter.get("Planned Completion Date")
                or item.summary.get("Planned Completion")
            ),
            "rag_status": _rag(item.charter.get("RAG Status") or item.summary.get("RAG")),
            "stage": stage,
            "benefit_confidence": "50.00",
            "realization_status": "not_started",
            "created_at": now,
            "updated_at": now,
        }
        result = self._client.table("initiatives").insert(row).execute()
        return result.data[0]["id"]

    def _link_business_units(
        self,
        initiative_id: str,
        item: WorkbookInitiative,
        business_units: dict[str, str],
    ) -> int:
        rows = []
        for name in self._business_unit_names(item):
            bu_id = business_units.get(name.lower())
            if bu_id:
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "initiative_id": initiative_id,
                        "business_unit_id": bu_id,
                    }
                )
        if not rows:
            return 0
        self._client.table("initiative_business_units").insert(rows).execute()
        return len(rows)

    def _create_benefit_lines(
        self,
        initiative_id: str,
        item: WorkbookInitiative,
        metric_defs: dict[str, str],
    ) -> dict[tuple[str, str, str], str]:
        unique: dict[tuple[str, str, str], dict[str, Any]] = {}
        for row in item.benefits:
            metric_key = _benefit_metric_key(row)
            metric_definition_id = metric_defs.get(metric_key)
            if not metric_definition_id:
                continue
            key = (
                _clean_text(row.get("_id")) or _clean_text(row.get("Name")),
                metric_key,
                _clean_text(row.get("Name")),
            )
            unique.setdefault(
                key,
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "initiative_id": initiative_id,
                    "metric_definition_id": metric_definition_id,
                    "name": _clean_text(row.get("Name")) or metric_key,
                    "description": _blank(row.get("Description")),
                    "impact_type": _line_impact_type(row.get("Impact Type")),
                    "timing": _blank(row.get("Timing")),
                    "confidence": _decimal_or_none(row.get("Confidence")),
                    "attributes": {
                        "p_l_line": _blank(row.get("P&L Line")),
                        "benefit_type": _blank(row.get("Benefit Type")),
                        "denomination": _blank(row.get("Denomination")),
                        "source_reference": item.reference,
                        "source_line_id": _blank(row.get("_id")),
                    },
                    "show_in_summary": '"show_in_summary":true' in (row.get("_metadata") or ""),
                    "display_order": _int_or_zero(row.get("_sort_order")),
                    "created_by": self._user_id,
                    "updated_by": self._user_id,
                },
            )
        if not unique:
            return {}
        created = (
            self._client.table("financial_benefit_lines").insert(list(unique.values())).execute()
        )
        ids_by_key: dict[tuple[str, str, str], str] = {}
        for row in created.data or []:
            for key, payload in unique.items():
                if payload["id"] == row["id"]:
                    ids_by_key[key] = row["id"]
                    break
        return ids_by_key

    def _create_metric_values(
        self,
        initiative_id: str,
        item: WorkbookInitiative,
        metric_defs: dict[str, str],
        scenarios: dict[str, str],
        benefit_line_ids: dict[tuple[str, str, str], str],
    ) -> int:
        rows: list[dict[str, Any]] = []
        for row in item.benefits:
            metric_key = _benefit_metric_key(row)
            metric_definition_id = metric_defs.get(metric_key)
            scenario_id = scenarios.get(_scenario_key(row.get("Lane")))
            if not metric_definition_id or not scenario_id:
                continue
            line_key = (
                _clean_text(row.get("_id")) or _clean_text(row.get("Name")),
                metric_key,
                _clean_text(row.get("Name")),
            )
            benefit_line_id = benefit_line_ids.get(line_key)
            for year, month, value in _monthly_values(row):
                amount = _workbook_financial_value(value, row.get("Denomination"))
                if amount is None:
                    continue
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "initiative_id": initiative_id,
                        "metric_definition_id": metric_definition_id,
                        "benefit_line_id": benefit_line_id,
                        "scenario_id": scenario_id,
                        "year": year,
                        "month": month,
                        "value": str(amount),
                        "status": "draft",
                        "created_by": self._user_id,
                        "updated_by": self._user_id,
                    }
                )
        if rows:
            self._client.table("financial_metric_values").insert(rows).execute()
        return len(rows)

    def _create_cost_lines(self, initiative_id: str, item: WorkbookInitiative) -> int:
        rows: list[dict[str, Any]] = []
        category_ids = self._cost_categories()
        for cost in item.costs:
            lane = _clean_text(cost.get("Lane")).lower()
            if lane not in {"plan", "actual"}:
                continue
            periods = _monthly_values(cost)
            if not periods:
                periods = _fallback_cost_periods(cost)
            for year, month, raw_value in periods:
                amount = _workbook_money(raw_value)
                if amount is None:
                    continue
                category_key = _category_key(cost.get("Cost Category"))
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "initiative_id": initiative_id,
                        "name": _clean_text(cost.get("Name")) or "Imported cost",
                        "category_key": category_key,
                        "category_id": category_ids.get(category_key),
                        "year": year,
                        "quarter": None,
                        "month": month,
                        "amount_plan": str(amount) if lane == "plan" else "0",
                        "amount_actual": str(amount) if lane == "actual" else None,
                        "is_recurring": _is_recurring(cost),
                        "phasing": {
                            "mode": _blank(cost.get("Plan Mode")),
                            "amount_m": _blank(cost.get("Amount")),
                            "start_fy": _blank(cost.get("Start FY")),
                            "start_month": _blank(cost.get("Start Month")),
                            "end_fy": _blank(cost.get("End FY")),
                            "end_month": _blank(cost.get("End Month")),
                            "lump_month": _blank(cost.get("Lump Month")),
                            "inflation_pct": _blank(cost.get("Inflation %")),
                            "source_line_id": _blank(cost.get("_id")),
                        },
                        "attributes": {
                            "p_l_line": _blank(cost.get("P&L Line")),
                            "service_line": _blank(cost.get("Service Line")),
                            "timing": _blank(cost.get("Timing")),
                            "confidence": _blank(cost.get("Confidence")),
                            "impact_type": _blank(cost.get("Impact Type")),
                            "notes": _blank(cost.get("Notes")),
                        },
                        "created_by": self._user_id,
                        "updated_by": self._user_id,
                    }
                )
        if rows:
            self._client.table("financial_cost_lines").insert(rows).execute()
        return len(rows)

    def _create_kpis(self, initiative_id: str, item: WorkbookInitiative) -> dict[str, int]:
        grouped: dict[str, dict[str, Any]] = {}
        for row in item.kpis:
            name = _clean_text(row.get("Name"))
            if not name:
                continue
            kpi = grouped.setdefault(
                name,
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "initiative_id": initiative_id,
                    "name": name,
                    "type": _kpi_type(row.get("Type")),
                    "category": _blank(row.get("_kpi_category") or row.get("Impacted Metric")),
                    "frequency": _frequency(row.get("Cadence")),
                    "unit": _blank(row.get("Unit") or row.get("Custom Unit Label")),
                    "entries": {},
                },
            )
            target = {
                "base case": "value_base",
                "high case": "value_high",
                "actual": "value_actual",
            }.get(_clean_text(row.get("Lane")).lower())
            if not target:
                continue
            for year, month, raw_value in _monthly_values(row):
                amount = _decimal_or_none(raw_value)
                if amount is None:
                    continue
                quarter = ((month - 1) // 3) + 1
                entry = kpi["entries"].setdefault(
                    (year, quarter),
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "kpi_id": kpi["id"],
                        "year": year,
                        "quarter": quarter,
                    },
                )
                entry[target] = str(amount)
        kpis = [{k: v for k, v in row.items() if k != "entries"} for row in grouped.values()]
        entries = [entry for row in grouped.values() for entry in row["entries"].values()]
        if kpis:
            self._client.table("kpis").insert(kpis).execute()
        if entries:
            self._client.table("kpi_entries").insert(entries).execute()
        return {"kpis": len(kpis), "kpi_entries": len(entries)}

    def _create_milestones(self, initiative_id: str, item: WorkbookInitiative) -> int:
        rows = []
        for row in item.milestones:
            name = _clean_text(row.get("Name"))
            if not name:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "initiative_id": initiative_id,
                    "name": name,
                    "description": _blank(row.get("Description")),
                    "owner_id": self._user_id,
                    "priority": _priority(row.get("Priority")),
                    "status": _milestone_status(row.get("Status")),
                    "sort_order": _int_or_zero(row.get("_sort_order")),
                    "planned_start": _date_or_none(row.get("Planned Start")),
                    "planned_end": _date_or_none(row.get("Planned End")),
                    "actual_start": _date_or_none(row.get("Actual Start")),
                    "actual_end": _date_or_none(row.get("Actual End")),
                }
            )
        if rows:
            self._client.table("milestones").insert(rows).execute()
        return len(rows)

    def _create_risks(self, initiative_id: str, item: WorkbookInitiative) -> int:
        rows = []
        for row in item.risks:
            description = _clean_text(row.get("Description") or row.get("Name"))
            if not description:
                continue
            impact = _risk_level(row.get("Impact"))
            likelihood = _risk_level(row.get("Likelihood"))
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "initiative_id": initiative_id,
                    "description": description,
                    "type": _risk_type(row.get("Type")),
                    "impact": impact,
                    "likelihood": likelihood,
                    "rating": _risk_rating(impact, likelihood),
                    "status": "closed"
                    if _clean_text(row.get("Status")).lower() == "closed"
                    else "open",
                    "owner_id": self._user_id,
                    "mitigation": _blank(row.get("Mitigation")),
                }
            )
        if rows:
            self._client.table("risks").insert(rows).execute()
        return len(rows)

    def _create_status_updates(self, initiative_id: str, item: WorkbookInitiative) -> int:
        if not self._user_id:
            return 0
        rows = []
        for row in item.status_updates:
            summary = _clean_text(row.get("Summary"))
            if not summary:
                continue
            submitted_at = _blank(row.get("Submitted At")) or _date_or_none(
                row.get("Date (week of)")
            )
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "initiative_id": initiative_id,
                    "author_id": self._user_id,
                    "rag_status": _rag(row.get("RAG")),
                    "summary": summary[:2000],
                    "achievements": _blank(row.get("Achievements")),
                    "issues": _blank(row.get("Issues")),
                    "next_steps": _blank(row.get("Next Steps")),
                    "is_draft": _clean_text(row.get("_is_draft")).lower() == "true",
                    "submitted_at": submitted_at,
                }
            )
        if rows:
            self._client.table("status_updates").insert(rows).execute()
        return len(rows)

    def _ensure_business_units(self, parsed: dict[str, WorkbookInitiative]) -> dict[str, str]:
        existing = {
            row["name"].lower(): row["id"]
            for row in self._client.table("business_units")
            .select("id,name")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        }
        names = sorted(
            {name for item in parsed.values() for name in self._business_unit_names(item)}
        )
        rows = []
        for name in names:
            if name.lower() not in existing:
                rows.append(
                    {
                        "id": str(uuid4()),
                        "tenant_id": self._tenant_id,
                        "name": name,
                        "code": _code(name),
                    }
                )
        if rows:
            for row in self._client.table("business_units").insert(rows).execute().data or []:
                existing[row["name"].lower()] = row["id"]
        return existing

    def _ensure_workstreams(
        self,
        parsed: dict[str, WorkbookInitiative],
        _business_units: dict[str, str],
        _user_ids_by_name: dict[str, str],
    ) -> dict[str, str]:
        existing = {
            row["name"].lower(): row
            for row in self._client.table("workstreams")
            .select("id,name")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        }
        rows = []
        for item in parsed.values():
            name = self._workstream_name(item)
            if not name:
                continue
            existing_row = existing.get(name.lower())
            if existing_row:
                continue
            rows.append(
                {
                    "id": str(uuid4()),
                    "tenant_id": self._tenant_id,
                    "name": name,
                }
            )
        if rows:
            for row in self._client.table("workstreams").insert(rows).execute().data or []:
                existing[row["name"].lower()] = row
        return {row["name"].lower(): row["id"] for row in existing.values()}

    def _user_ids_by_name(self) -> dict[str, str]:
        rows = (
            self._client.table("users")
            .select("id,email,display_name")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        )
        lookup: dict[str, str] = {}
        for row in rows:
            for key in (row.get("display_name"), row.get("email")):
                cleaned = _clean_text(key).lower()
                if cleaned:
                    lookup[cleaned] = row["id"]
        return lookup

    def _metric_definitions(self) -> dict[str, str]:
        rows = (
            self._client.table("financial_metric_definitions")
            .select("id,key")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        )
        return {row["key"]: row["id"] for row in rows}

    def _financial_scenarios(self) -> dict[str, str]:
        rows = (
            self._client.table("financial_scenarios")
            .select("id,key")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        )
        return {row["key"]: row["id"] for row in rows}

    def _cost_categories(self) -> dict[str, str]:
        rows = (
            self._client.table("financial_cost_categories")
            .select("id,key")
            .eq("tenant_id", self._tenant_id)
            .execute()
            .data
            or []
        )
        return {row["key"]: row["id"] for row in rows}

    def _stage_by_gate_number(self) -> dict[int, str]:
        rows = (
            self._client.table("stage_gate_definitions")
            .select("gate_number,to_stage")
            .eq("tenant_id", self._tenant_id)
            .eq("is_active", True)
            .execute()
            .data
            or []
        )
        return {int(row["gate_number"]): row["to_stage"] for row in rows}

    def _stage_value(self, item: WorkbookInitiative, stages: dict[int, str]) -> str:
        raw = item.charter.get("Stage gate") or item.summary.get("Stage") or ""
        match = re.search(r"\d+", raw)
        if match and int(match.group(0)) in stages:
            return stages[int(match.group(0))]
        return _clean_text(raw).lower().replace(" ", "_") or "identified"

    @staticmethod
    def _business_unit_names(item: WorkbookInitiative) -> list[str]:
        raw = item.charter.get("Business Units") or item.summary.get("Business Units") or ""
        return [part.strip() for part in re.split(r"[,;/]", raw) if part.strip()]

    @staticmethod
    def _workstream_name(item: WorkbookInitiative) -> str:
        return _clean_text(item.charter.get("Workstream") or item.summary.get("Workstream"))

    def _delete_tenant_rows(self, table: str) -> None:
        try:
            self._client.table(table).delete().eq("tenant_id", self._tenant_id).execute()
        except Exception as exc:
            if "does not exist" in str(exc) or "Could not find the table" in str(exc):
                return
            raise


def _headered_rows(rows: list[list[str]], first_header: str) -> tuple[list[str], list[list[str]]]:
    for index, row in enumerate(rows):
        if row and _clean_text(row[0]) == first_header:
            return [_clean_text(value) for value in row], rows[index + 1 :]
    return [], []


def _row_dict(headers: list[str], row: list[str]) -> dict[str, str]:
    return {
        header: _clean_text(row[index]) if index < len(row) else ""
        for index, header in enumerate(headers)
        if header
    }


def _monthly_values(row: dict[str, str]) -> list[tuple[int, int, str]]:
    values: list[tuple[int, int, str]] = []
    for key, value in row.items():
        match = re.fullmatch(r"FY(\d{2,4})-([A-Za-z]{3})", key.strip())
        if not match:
            continue
        year_token, month_token = match.groups()
        year = int(year_token)
        if year < 100:
            year += 2000
        month = _MONTHS.get(month_token.lower())
        if not month:
            continue
        if value.strip() in {"", "0", "0.0", "0.00"}:
            continue
        values.append((year, month, value))
    return values


def _fallback_cost_periods(row: dict[str, str]) -> list[tuple[int, int, str]]:
    amount = row.get("Amount") or ""
    if not amount.strip() or amount.strip() in {"0", "0.0", "0.00"}:
        return []
    year = _int_or_zero(row.get("Start FY"))
    month = _MONTHS.get(_clean_text(row.get("Start Month")).lower()[:3], 0)
    if not year or not month:
        return []
    return [(year, month, amount)]


def _workbook_money(value: str | None) -> Decimal | None:
    amount = _decimal_or_none(value)
    if amount is None or amount == 0:
        return None
    return (amount * Decimal("1000000")).quantize(Decimal("0.0001"))


def _workbook_financial_value(value: str | None, denomination: str | None) -> Decimal | None:
    amount = _decimal_or_none(value)
    if amount is None or amount == 0:
        return None
    if _clean_text(denomination).lower() == "%":
        return amount.quantize(Decimal("0.0001"))
    return (amount * Decimal("1000000")).quantize(Decimal("0.0001"))


def _decimal_or_none(value: str | None) -> Decimal | None:
    raw = _clean_text(value)
    if not raw:
        return None
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _int_or_zero(value: str | None) -> int:
    raw = _clean_text(value)
    try:
        return int(Decimal(raw))
    except (InvalidOperation, ValueError):
        return 0


def _blank(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def _date_or_none(value: str | None) -> str | None:
    parsed = _date_text(value)
    return parsed or None


def _code(name: str) -> str:
    code = "".join(ch for ch in name.upper() if ch.isalnum())
    return code[:8] or "BU"


def _initiative_type(value: str | None) -> str | None:
    cleaned = _clean_text(value).lower().replace(" ", "_")
    return {
        "revenue": "revenue_growth",
        "revenue_growth": "revenue_growth",
        "cost_reduction": "cost_reduction",
        "cost_avoidance": "cost_avoidance",
        "compliance": "compliance",
        "capability_building": "capability_building",
    }.get(cleaned)


def _impact_type(value: str | None) -> str | None:
    cleaned = _clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if cleaned in {"recurring", "one_off"}:
        return cleaned
    return None


def _priority(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in {"high", "medium", "low"} else "medium"


def _rag(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in {"red", "amber", "green"} else "green"


def _line_impact_type(value: str | None) -> str | None:
    cleaned = _clean_text(value).lower().replace("-", "_").replace(" ", "_")
    if cleaned == "one_off":
        return "one_time"
    if cleaned == "recurring":
        return "recurring"
    return None


def _benefit_metric_key(row: dict[str, str]) -> str:
    name = _clean_text(row.get("Name")).lower()
    denomination = _clean_text(row.get("Denomination")).lower()
    if "revenue" in name and denomination == "%":
        return "revenue_uplift_pct"
    if "revenue" in name:
        return "revenue_uplift"
    if "gross margin uplift" in name and denomination == "%":
        return "gm_uplift_pct"
    if "gross margin uplift" in name:
        return "gm_uplift"
    if "gross margin" in name and denomination == "%":
        return "gm_pct"
    if "gross margin" in name:
        return "gross_margin"
    return "cost_savings"


def _scenario_key(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    return {
        "plan base": "plan_base",
        "base case": "plan_base",
        "plan high": "plan_high",
        "high case": "plan_high",
        "actual": "actual",
        "baseline": "baseline",
    }.get(cleaned, cleaned.replace(" ", "_"))


def _stage_gate_number(item: WorkbookInitiative) -> int | None:
    raw = item.charter.get("Stage gate") or item.summary.get("Stage") or ""
    match = re.search(r"\d+", raw)
    return int(match.group(0)) if match else None


def _category_key(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    key = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
    return key or "other"


def _is_recurring(row: dict[str, str]) -> bool:
    raw = f"{row.get('Impact Type') or ''} {row.get('Plan Mode') or ''}".lower()
    return "recurring" in raw or "annual" in raw


def _kpi_type(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    if "gross" in cleaned:
        return "gross_margin"
    if "operational" in cleaned:
        return "operational"
    return "custom"


def _frequency(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in {"monthly", "quarterly", "annual"} else "quarterly"


def _milestone_status(value: str | None) -> str:
    cleaned = _clean_text(value).lower()
    if "complete" in cleaned:
        return "complete"
    if "progress" in cleaned:
        return "in_progress"
    if "overdue" in cleaned:
        return "overdue"
    return "not_started"


def _risk_level(value: str | None) -> str | None:
    cleaned = _clean_text(value).lower()
    return cleaned if cleaned in {"high", "medium", "low"} else None


def _risk_rating(impact: str | None, likelihood: str | None) -> str | None:
    if "high" in {impact, likelihood}:
        return "high"
    if "medium" in {impact, likelihood}:
        return "medium"
    if impact or likelihood:
        return "low"
    return None


def _risk_type(value: str | None) -> str | None:
    cleaned = _clean_text(value).lower()
    if cleaned in {"operational", "people", "financial", "technology"}:
        return cleaned
    return "operational" if cleaned else None
