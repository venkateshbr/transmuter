"""Minimal XLSX helpers for initiative template import/export."""

from __future__ import annotations

import re
from base64 import b64decode
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from html import unescape
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, status

from app.domain.financials import CostLineCreate, FinancialEntryUpdate
from app.domain.initiative_intake import (
    InitiativeWorkbookData,
    InitiativeWorkbookPreview,
    KPIWorkbookItem,
    WorkbookValidationError,
)
from app.domain.initiatives import InitiativeCreate
from app.domain.kpis import KPIEntryUpsert
from app.domain.milestones import MilestoneCreate
from app.domain.risks import RiskCreate

OVERVIEW_COLUMNS = [
    "name",
    "stage",
    "rag_status",
    "workstream_name",
    "owner_email",
    "group_owner_email",
    "type",
    "impact_type",
    "theme",
    "country",
    "tag",
    "priority",
    "summary",
    "context_problem",
    "value_logic",
    "dependencies_text",
    "planned_start",
    "planned_end",
]

SAMPLE_OVERVIEW = [
    "Imported Acceptance Initiative",
    "scoping",
    "green",
    "",
    "",
    "",
    "cost_reduction",
    "recurring",
    "Finance automation",
    "Singapore",
    "automation",
    "medium",
    "Imported from the Transmuter initiative template.",
    "Manual intake makes it hard to compare and govern initiatives consistently.",
    "Reduce manual effort and improve monthly close predictability.",
    "Finance, IT, and change management alignment.",
    "2026-06-01",
    "2026-12-31",
]

SHEET_DEFS = [
    ("Overview", OVERVIEW_COLUMNS, [SAMPLE_OVERVIEW]),
    (
        "Benefits",
        [
            "year",
            "quarter",
            "month",
            "revenue_uplift_base",
            "revenue_uplift_high",
            "revenue_uplift_actual",
            "gross_margin_base",
            "gross_margin_high",
            "gross_margin_actual",
            "gm_uplift_base",
            "gm_uplift_high",
            "gm_uplift_actual",
        ],
        [
            [
                "2030",
                "1",
                "",
                "100000.0000",
                "150000.0000",
                "",
                "45000.0000",
                "70000.0000",
                "",
                "45000.0000",
                "70000.0000",
                "",
            ]
        ],
    ),
    (
        "Costs",
        ["name", "year", "quarter", "month", "amount_plan", "amount_actual", "is_recurring"],
        [["Implementation support", "2030", "1", "", "12000.0000", "", "false"]],
    ),
    (
        "KPIs",
        [
            "name",
            "type",
            "category",
            "frequency",
            "unit",
            "year",
            "quarter",
            "value_base",
            "value_high",
            "value_actual",
        ],
        [
            [
                "Cycle time reduction",
                "operational",
                "delivery",
                "quarterly",
                "%",
                "2030",
                "1",
                "15.0000",
                "25.0000",
                "",
            ]
        ],
    ),
    (
        "Risks",
        ["description", "type", "impact", "likelihood", "mitigation"],
        [
            [
                "Adoption may lag without local champions",
                "people",
                "medium",
                "medium",
                "Assign market champions and weekly adoption review.",
            ]
        ],
    ),
    (
        "Milestones",
        ["name", "description", "priority", "planned_start", "planned_end"],
        [
            [
                "Pilot launch complete",
                "Complete pilot and validate benefits tracking.",
                "high",
                "2030-02-01",
                "2030-03-31",
            ]
        ],
    ),
]

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}
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
_PNG_1X1 = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADElEQVR42mP8z8BQDwAFgwJ/lYt9"
    "mAAAAABJRU5ErkJggg=="
)


def build_initiative_template() -> bytes:
    return _build_workbook(SHEET_DEFS)


def build_initiative_export(
    *,
    overview_rows: list[list[str]],
    benefit_rows: list[list[str]],
    cost_rows: list[list[str]],
    kpi_rows: list[list[str]],
    risk_rows: list[list[str]],
    milestone_rows: list[list[str]],
    status_update_rows: list[list[str]],
    meeting_note_rows: list[list[str]],
    reference_rows: list[list[str]],
) -> bytes:
    sheet_defs = _alchemist_export_sheet_defs(
        overview_rows=overview_rows,
        benefit_rows=benefit_rows,
        cost_rows=cost_rows,
        kpi_rows=kpi_rows,
        risk_rows=risk_rows,
        milestone_rows=milestone_rows,
        status_update_rows=status_update_rows,
        meeting_note_rows=meeting_note_rows,
        reference_rows=reference_rows,
    )
    return _build_workbook(sheet_defs)


def _alchemist_export_sheet_defs(
    *,
    overview_rows: list[list[str]],
    benefit_rows: list[list[str]],
    cost_rows: list[list[str]],
    kpi_rows: list[list[str]],
    risk_rows: list[list[str]],
    milestone_rows: list[list[str]],
    status_update_rows: list[list[str]],
    meeting_note_rows: list[list[str]],
    reference_rows: list[list[str]],
) -> list[tuple[str, list[str], list[list[str]]]]:
    overview = overview_rows[0] if overview_rows else []
    overview_map = dict(zip(OVERVIEW_COLUMNS, overview, strict=False))
    years = _export_years(benefit_rows, cost_rows, kpi_rows, overview_map)
    months = [
        month
        for _year in years
        for month in [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
    ]
    benefit_headers = [
        "Name",
        "Lane",
        "Benefit Type",
        "Denomination",
        "P&L Line",
        "Impact Type",
        "Timing",
        "Confidence",
        "Description",
        "_id",
        "_value_translation",
        "_sort_order",
        "_is_draft",
        "_metadata",
        "_created_at",
        "_updated_at",
        *[f"FY{str(year)[-2:]}" for year in years],
        *months,
    ]
    cost_headers = [
        "Name",
        "Lane",
        "Plan Mode",
        "Amount",
        "Start FY",
        "Start Month",
        "End FY",
        "End Month",
        "Lump Month",
        "Inflation %",
        "Cost Category",
        "P&L Line",
        "Service Line",
        "Timing",
        "Confidence",
        "Impact Type",
        "Description",
        "Notes",
        "_id",
        "_overrides",
        "_sort_order",
        "_is_draft",
        "_metadata",
        "_created_at",
        "_updated_at",
        *[f"FY{str(year)[-2:]}" for year in years],
        *months,
    ]
    kpi_headers = [
        "Name",
        "Lane",
        "Type",
        "Unit",
        "Cadence",
        "Indicator",
        "Impacted Metric",
        "RAG Green Min",
        "RAG Amber Min",
        "Custom Type Label",
        "Custom Unit Label",
        "Assessment Score",
        "Assessment Evidence",
        "Assessment Date",
        "Description",
        "_id",
        "_linked_kpi_id",
        "_library_template_id",
        "_category",
        "_kpi_category",
        "_value_translation",
        "_sort_order",
        "_is_draft",
        "_is_auto_generated",
        "_auto_generated_reason",
        "_metadata",
        "_created_at",
        "_updated_at",
        *[f"FY{str(year)[-2:]}" for year in years],
        *months,
    ]
    return [
        ("Overview", [], _alchemist_overview_rows(overview_map)),
        ("Summary", [], _alchemist_summary_rows(benefit_rows, cost_rows, years)),
        ("Benefits", benefit_headers, _alchemist_benefit_rows(benefit_rows, years)),
        ("Costs", cost_headers, _alchemist_cost_rows(cost_rows, years)),
        ("KPIs", kpi_headers, _alchemist_kpi_rows(kpi_rows, years)),
        (
            "Milestones",
            [
                "Name",
                "Type",
                "Priority",
                "Owner",
                "Planned Start",
                "Planned End",
                "Actual Start",
                "Actual End",
                "Status",
                "Evidence URL",
                "Depends On (names)",
                "Risk Reason",
                "Pressure Score",
                "Pressure Level",
                "Checklist Done",
                "Checklist Total",
                "_id",
                "_sort_order",
                "_created_at",
                "_updated_at",
            ],
            _alchemist_milestone_rows(milestone_rows),
        ),
        (
            "Action Items",
            [
                "Milestone",
                "Action",
                "Owner",
                "Due Date",
                "Status",
                "Notes",
                "_id",
                "_milestone_id",
                "_meeting_note_id",
            ],
            [["", "", "", "", "", "", "", "", ""]],
        ),
        (
            "Risks",
            [
                "Name",
                "Type",
                "Impact",
                "Likelihood",
                "Owner",
                "Status",
                "Mitigation",
                "Linked Milestone",
                "Escalation Reason",
                "SME Consultation",
                "Description",
                "_id",
                "_risk_milestone_id",
                "_sort_order",
                "_created_at",
                "_updated_at",
            ],
            _alchemist_risk_rows(risk_rows),
        ),
        (
            "Status Updates",
            [
                "Date (week of)",
                "Submitted At",
                "RAG",
                "Submitted By",
                "Summary",
                "Achievements",
                "Issues",
                "Next Steps",
                "Help Needed",
                "_id",
                "_is_draft",
                "_was_pre_populated",
                "_created_at",
                "_updated_at",
                "_author_id",
            ],
            _alchemist_status_update_rows(status_update_rows),
        ),
        ("Meeting Notes", ["Session Date", "Meeting", "Notes", "Status"], meeting_note_rows),
        (
            "_Reference",
            ["key", "value"],
            [
                *reference_rows,
                ["template_name", "alchemist-initiative-template"],
                ["version", "3"],
                ["fiscal_years (csv)", ",".join(str(year) for year in years)],
            ],
        ),
        ("_Validation", [], _alchemist_validation_rows()),
    ]


def _export_years(
    benefit_rows: list[list[str]],
    cost_rows: list[list[str]],
    kpi_rows: list[list[str]],
    overview: dict[str, str],
) -> list[int]:
    years: set[int] = set()
    for row in benefit_rows:
        if row and str(row[0]).isdigit():
            years.add(int(row[0]))
    for row in cost_rows:
        if len(row) > 1 and str(row[1]).isdigit():
            years.add(int(row[1]))
    for row in kpi_rows:
        if len(row) > 5 and str(row[5]).isdigit():
            years.add(int(row[5]))
    for key in ("planned_start", "planned_end"):
        value = overview.get(key) or ""
        if len(value) >= 4 and value[:4].isdigit():
            years.add(int(value[:4]))
    if not years:
        current = datetime.now().year
        return list(range(current, current + 5))
    start = min(years)
    end = max(max(years), start + 4)
    return list(range(start, end + 1))


def _alchemist_overview_rows(overview: dict[str, str]) -> list[list[str]]:
    return [
        ["Initiative Charter", ""],
        ["Edit values in column B. Cells with grey shading are calculated.", ""],
        ["", ""],
        ["INITIATIVE DETAILS", ""],
        ["Name", overview.get("name", "")],
        ["Reference", ""],
        ["Stage", overview.get("stage", "scoping")],
        ["RAG Status", overview.get("rag_status", "green")],
        ["Priority", overview.get("priority", "medium")],
        ["Initiative Type", overview.get("type", "")],
        ["Initiative Tag", overview.get("tag", "")],
        ["Theme", overview.get("theme", "")],
        ["Impact Type", overview.get("impact_type", "")],
        ["Value Step", ""],
        ["Service Line", ""],
        ["Country", overview.get("country", "")],
        ["Business Units", ""],
        ["Markets", ""],
        ["Workstream", overview.get("workstream_name", "")],
        ["Owner", overview.get("owner_email", "")],
        ["Group Owner", overview.get("group_owner_email", "")],
        ["Market Owner", ""],
        ["Workstream Lead", ""],
        ["Workstream Sponsor", ""],
        ["Planned Start Date", overview.get("planned_start", "")],
        ["Actual Start Date", ""],
        ["Planned Completion Date", overview.get("planned_end", "")],
        ["Actual Completion Date", ""],
        ["Quality Score", ""],
        ["Dependencies", overview.get("dependencies_text", "")],
        ["", ""],
        ["DESCRIPTION", ""],
        ["Description", overview.get("summary", "")],
        ["Context & Problem", overview.get("context_problem", "")],
        ["Value Logic / Assumptions", overview.get("value_logic", "")],
    ]


def _alchemist_summary_rows(
    benefit_rows: list[list[str]],
    cost_rows: list[list[str]],
    years: list[int],
) -> list[list[str]]:
    headers = ["Metric", *[f"FY{str(year)[-2:]}" for year in years], "All Years"]
    rows = [
        ["Financial Summary", *["" for _ in years], ""],
        ["All values are computed from Benefits / Costs.", *["" for _ in years], ""],
        ["", *["" for _ in years], ""],
        headers,
    ]
    for label, metric in [
        ("Revenue Plan - Base (USD m)", "revenue_uplift_base"),
        ("Revenue Plan - High (USD m)", "revenue_uplift_high"),
        ("Revenue Actual (USD m)", "revenue_uplift_actual"),
        ("Gross Margin Plan - Base (USD m)", "gross_margin_base"),
        ("Gross Margin Plan - High (USD m)", "gross_margin_high"),
        ("Gross Margin Actual (USD m)", "gross_margin_actual"),
    ]:
        values = [
            _million(sum(_period_value(row, metric, year) for row in benefit_rows))
            for year in years
        ]
        rows.append([label, *[str(value) for value in values], str(sum(values, Decimal("0")))])
    rows.append(["COSTS", *["" for _ in years], ""])
    values = [
        _million(sum(_period_value(row, "amount_plan", year) for row in cost_rows))
        for year in years
    ]
    rows.append(
        ["Cost Plan (USD m)", *[str(value) for value in values], str(sum(values, Decimal("0")))]
    )
    return rows


def _alchemist_benefit_rows(rows: list[list[str]], years: list[int]) -> list[list[str]]:
    metrics = [
        ("Revenue Uplift", "Plan Base", "Revenue", "USD", "revenue_uplift_base"),
        ("Revenue Uplift", "Plan High", "Revenue", "USD", "revenue_uplift_high"),
        ("Revenue Uplift", "Actual", "Revenue", "USD", "revenue_uplift_actual"),
        ("Gross Margin", "Plan Base", "Gross Margin", "USD", "gross_margin_base"),
        ("Gross Margin", "Plan High", "Gross Margin", "USD", "gross_margin_high"),
        ("Gross Margin", "Actual", "Gross Margin", "USD", "gross_margin_actual"),
    ]
    return [
        _alchemist_metric_row(label, lane, benefit_type, denom, metric, rows, years, 16)
        for label, lane, benefit_type, denom, metric in metrics
    ]


def _alchemist_cost_rows(rows: list[list[str]], years: list[int]) -> list[list[str]]:
    grouped: dict[tuple[str, bool], list[list[str]]] = {}
    for row in rows:
        if len(row) < 7:
            continue
        grouped.setdefault((row[0], row[6].strip().lower() in {"true", "1", "yes"}), []).append(row)
    output: list[list[str]] = []
    for (name, recurring), group in grouped.items():
        for lane, field in (("Plan", "amount_plan"), ("Actual", "amount_actual")):
            output.append(
                [
                    name,
                    lane,
                    "Manual",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "0",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "Recurring" if recurring else "One-off",
                    "",
                    "",
                    "",
                    "{}",
                    "0",
                    "false",
                    "{}",
                    "",
                    "",
                    *[
                        str(_million(sum(_cost_period_value(row, field, year) for row in group)))
                        for year in years
                    ],
                    *[
                        str(_million(_cost_month_value(group, field, year, month)))
                        for year in years
                        for month in range(1, 13)
                    ],
                ]
            )
    return output


def _alchemist_kpi_rows(rows: list[list[str]], years: list[int]) -> list[list[str]]:
    output = []
    for row in rows:
        if len(row) < 5:
            continue
        output.append(
            [
                row[0],
                "Base Case",
                row[1] or "Custom",
                row[4] or "",
                row[3] or "Quarterly",
                "Leading",
                row[2] or "",
                "90",
                "70",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                row[2] or "",
                '{"type":"none"}',
                "0",
                "false",
                "false",
                "",
                "{}",
                "",
                "",
                *["" for _ in years],
                *["" for _ in years for _month in range(12)],
            ]
        )
    return output


def _alchemist_milestone_rows(rows: list[list[str]]) -> list[list[str]]:
    return [
        [
            row[0],
            "",
            row[2],
            "",
            row[3],
            row[4],
            "",
            "",
            "Not Started",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        for row in rows
        if row
    ]


def _alchemist_risk_rows(rows: list[list[str]]) -> list[list[str]]:
    return [
        [
            row[0],
            row[1],
            row[2],
            row[3],
            "",
            row[5] if len(row) > 5 else "Open",
            row[4] if len(row) > 4 else "",
            "",
            "",
            "not_required",
            row[0],
            "",
            "",
            "",
            "",
            "",
        ]
        for row in rows
        if row
    ]


def _alchemist_status_update_rows(rows: list[list[str]]) -> list[list[str]]:
    return [
        [
            "",
            row[0],
            row[1],
            row[6],
            row[2],
            row[3],
            row[4],
            row[5],
            "",
            "",
            "false",
            "false",
            "",
            "",
            "",
        ]
        for row in rows
        if row
    ]


def _alchemist_validation_rows() -> list[list[str]]:
    return [
        ["Stages", "RAG", "Priority", "InitiativeType", "InitiativeTag", "ImpactType"],
        ["Scoping", "Red", "High", "Revenue", "Automation", "Recurring"],
        ["Execution", "Amber", "Medium", "Cost Reduction", "Offshoring", "One-off"],
        ["Executed", "Green", "Low", "Avoidance", "Commercial", ""],
    ]


def _alchemist_metric_row(
    name: str,
    lane: str,
    benefit_type: str,
    denomination: str,
    metric: str,
    rows: list[list[str]],
    years: list[int],
    prefix_len: int,
) -> list[str]:
    prefix = [
        name,
        lane,
        benefit_type,
        denomination,
        "",
        "",
        "",
        "",
        "",
        "",
        '{"mode":"none"}',
        "0",
        "false",
        '{"show_in_summary":true}',
        "",
        "",
    ]
    return [
        *prefix[:prefix_len],
        *[str(_million(sum(_period_value(row, metric, year) for row in rows))) for year in years],
        *[
            str(_million(_month_value(rows, metric, year, month)))
            for year in years
            for month in range(1, 13)
        ],
    ]


def _period_value(row: list[str], metric: str, year: int) -> Decimal:
    if len(row) < 3 or not str(row[0]).isdigit() or int(row[0]) != year:
        return Decimal("0")
    compact_metric_indexes = {
        "revenue_uplift_base": 3,
        "revenue_uplift_high": 4,
        "revenue_uplift_actual": 5,
        "gross_margin_base": 6,
        "gross_margin_high": 7,
        "gross_margin_actual": 8,
        "gm_uplift_base": 9,
        "gm_uplift_high": 10,
        "gm_uplift_actual": 11,
        "amount_plan": 4,
        "amount_actual": 5,
    }
    index = compact_metric_indexes.get(metric)
    if index is None or index >= len(row):
        return Decimal("0")
    return _decimal(row[index])


def _month_value(rows: list[list[str]], metric: str, year: int, month: int) -> Decimal:
    total = Decimal("0")
    quarter = ((month - 1) // 3) + 1
    for row in rows:
        if len(row) < 3 or not str(row[0]).isdigit() or int(row[0]) != year:
            continue
        row_quarter = int(row[1]) if len(row) > 1 and str(row[1]).isdigit() else None
        row_month = int(row[2]) if len(row) > 2 and str(row[2]).isdigit() else None
        value = _period_value(row, metric, year)
        if row_month == month:
            total += value
        elif row_quarter == quarter and row_month is None:
            total += value / Decimal("3")
        elif row_quarter is None and row_month is None:
            total += value / Decimal("12")
    return total


def _cost_period_value(row: list[str], metric: str, year: int) -> Decimal:
    if len(row) < 7 or not str(row[1]).isdigit() or int(row[1]) != year:
        return Decimal("0")
    index = 4 if metric == "amount_plan" else 5
    return _decimal(row[index])


def _cost_month_value(rows: list[list[str]], metric: str, year: int, month: int) -> Decimal:
    total = Decimal("0")
    quarter = ((month - 1) // 3) + 1
    for row in rows:
        if len(row) < 7 or not str(row[1]).isdigit() or int(row[1]) != year:
            continue
        row_quarter = int(row[2]) if str(row[2]).isdigit() else None
        row_month = int(row[3]) if str(row[3]).isdigit() else None
        value = _cost_period_value(row, metric, year)
        if row_month == month:
            total += value
        elif row_quarter == quarter and row_month is None:
            total += value / Decimal("3")
        elif row_quarter is None and row_month is None:
            total += value / Decimal("12")
    return total


def _million(value: Decimal) -> Decimal:
    return (value / Decimal("1000000")).quantize(Decimal("0.000001"))


def _build_workbook(sheet_defs: list[tuple[str, list[str], list[list[str]]]]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(len(sheet_defs)))
        zf.writestr("_rels/.rels", _root_rels())
        zf.writestr("xl/workbook.xml", _workbook(sheet_defs))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheet_defs)))
        zf.writestr("xl/styles.xml", _styles())
        zf.writestr("xl/media/transmuter-logo.png", _PNG_1X1)
        zf.writestr("xl/drawings/drawing1.xml", _drawing())
        zf.writestr("xl/drawings/_rels/drawing1.xml.rels", _drawing_rels())
        for index, (name, headers, rows) in enumerate(sheet_defs, start=1):
            prepared_headers, prepared_rows = _prepared_sheet_rows(name, headers, rows)
            sheet_rows = [prepared_headers, *prepared_rows] if prepared_headers else prepared_rows
            zf.writestr(
                f"xl/worksheets/sheet{index}.xml",
                _sheet(
                    sheet_rows,
                    data_validations=_data_validations(name, prepared_headers, len(prepared_rows)),
                    drawing=index == 1,
                ),
            )
            if index == 1:
                zf.writestr("xl/worksheets/_rels/sheet1.xml.rels", _sheet_drawing_rels())
    return output.getvalue()


def parse_initiative_template(data: bytes) -> InitiativeWorkbookData:
    try:
        with ZipFile(BytesIO(data)) as zf:
            sheets = _sheet_paths(zf)
            shared_strings = _shared_strings(zf)
            overview_rows = _read_sheet(zf, sheets["Overview"], shared_strings)
            if _is_alchemist_workbook(zf, sheets, overview_rows, shared_strings):
                return _parse_alchemist_workbook(zf, sheets, overview_rows, shared_strings)
            benefits_rows = (
                _read_sheet(zf, sheets["Benefits"], shared_strings) if "Benefits" in sheets else []
            )
            costs_rows = (
                _read_sheet(zf, sheets["Costs"], shared_strings) if "Costs" in sheets else []
            )
            kpi_rows = _read_sheet(zf, sheets["KPIs"], shared_strings) if "KPIs" in sheets else []
            risk_rows = (
                _read_sheet(zf, sheets["Risks"], shared_strings) if "Risks" in sheets else []
            )
            milestone_rows = (
                _read_sheet(zf, sheets["Milestones"], shared_strings)
                if "Milestones" in sheets
                else []
            )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workbook is missing required sheet: {exc.args[0]}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid initiative workbook",
        ) from exc

    errors: list[WorkbookValidationError] = []
    overview = next(_dict_rows(overview_rows, OVERVIEW_COLUMNS, "Overview", errors), None)
    if not overview:
        errors.append(
            WorkbookValidationError(
                sheet="Overview",
                row=2,
                column="name",
                message="Overview sheet must include one initiative row",
            )
        )
        overview_create = InitiativeCreate(name="Invalid workbook")
    else:
        overview_create = _parse_overview(overview, errors)

    return InitiativeWorkbookData(
        overview=overview_create,
        financial_entries=_parse_benefits(benefits_rows, errors),
        cost_lines=_parse_costs(costs_rows, errors),
        kpis=_parse_kpis(kpi_rows, errors),
        risks=_parse_risks(risk_rows, errors),
        milestones=_parse_milestones(milestone_rows, errors),
        validation_errors=errors,
    )


def parse_workbook_reference(data: bytes) -> dict[str, str]:
    try:
        with ZipFile(BytesIO(data)) as zf:
            sheets = _sheet_paths(zf)
            if "_Reference" not in sheets:
                return {}
            rows = _read_sheet(zf, sheets["_Reference"], _shared_strings(zf))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid initiative workbook reference",
        ) from exc
    reference: dict[str, str] = {}
    for row in _dict_rows(rows, ["key", "value"], "_Reference", []):
        if row["key"]:
            reference[row["key"]] = row["value"]
    return reference


def parse_workbook_overview_metadata(data: bytes) -> dict[str, str]:
    try:
        with ZipFile(BytesIO(data)) as zf:
            rows = _read_sheet(zf, _sheet_paths(zf)["Overview"], _shared_strings(zf))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid initiative workbook overview",
        ) from exc
    overview = next(_dict_rows(rows, OVERVIEW_COLUMNS, "Overview", []), None)
    if not overview:
        return {}
    return {
        "stage": overview.get("stage", ""),
        "rag_status": overview.get("rag_status", ""),
    }


def _is_alchemist_workbook(
    zf: ZipFile,
    sheets: dict[str, str],
    overview_rows: list[list[str]],
    shared_strings: list[str],
) -> bool:
    if (
        overview_rows
        and overview_rows[0]
        and overview_rows[0][0].strip().lower() == "initiative charter"
    ):
        return True
    if "_Reference" not in sheets:
        return False
    rows = _read_sheet(zf, sheets["_Reference"], shared_strings)
    reference = _key_value_rows(rows)
    return reference.get("template_name", "").lower().startswith("alchemist")


def _parse_alchemist_workbook(
    zf: ZipFile,
    sheets: dict[str, str],
    overview_rows: list[list[str]],
    shared_strings: list[str],
) -> InitiativeWorkbookData:
    errors: list[WorkbookValidationError] = []
    reference = _key_value_rows(
        _read_sheet(zf, sheets["_Reference"], shared_strings) if "_Reference" in sheets else []
    )
    overview_values = _key_value_rows(overview_rows)
    fiscal_years = _fiscal_years(reference, overview_values)
    metadata = {
        "format": "alchemist",
        "reference": overview_values.get("Reference") or reference.get("initiative_id"),
        "stage": _stage(overview_values.get("Stage")),
        "rag_status": _choice(overview_values.get("RAG Status"), {"green", "amber", "red"}),
        "workstream_name": _clean_text(overview_values.get("Workstream")),
        "business_unit_names": [
            item.strip()
            for item in re.split(r"[,;/]", _clean_text(overview_values.get("Business Units")) or "")
            if item.strip()
        ],
        "owner_name": _clean_text(
            overview_values.get("Owner") or overview_values.get("Market Owner")
        ),
        "group_owner_name": _clean_text(overview_values.get("Group Owner")),
    }
    overview = _parse_alchemist_overview(overview_values, errors)
    return InitiativeWorkbookData(
        overview=overview,
        financial_entries=_parse_alchemist_benefits(
            _read_sheet(zf, sheets["Benefits"], shared_strings) if "Benefits" in sheets else [],
            fiscal_years,
            errors,
        ),
        cost_lines=_parse_alchemist_costs(
            _read_sheet(zf, sheets["Costs"], shared_strings) if "Costs" in sheets else [],
            fiscal_years,
            errors,
        ),
        kpis=_parse_alchemist_kpis(
            _read_sheet(zf, sheets["KPIs"], shared_strings) if "KPIs" in sheets else [],
            fiscal_years,
            errors,
        ),
        risks=_parse_alchemist_risks(
            _read_sheet(zf, sheets["Risks"], shared_strings) if "Risks" in sheets else [],
            errors,
        ),
        milestones=_parse_alchemist_milestones(
            _read_sheet(zf, sheets["Milestones"], shared_strings) if "Milestones" in sheets else [],
            errors,
        ),
        status_updates=_parse_alchemist_status_updates(
            _read_sheet(zf, sheets["Status Updates"], shared_strings)
            if "Status Updates" in sheets
            else [],
        ),
        metadata=metadata,
        validation_errors=errors,
    )


def _parse_alchemist_overview(
    values: dict[str, str],
    errors: list[WorkbookValidationError],
) -> InitiativeCreate:
    name = _clean_text(values.get("Name")) or "Invalid workbook"
    if name == "Invalid workbook":
        errors.append(
            WorkbookValidationError(sheet="Overview", row=5, column="Name", message="Missing Name")
        )
    try:
        return InitiativeCreate(
            name=name,
            type=_initiative_type(values.get("Initiative Type")),
            impact_type=_impact_type(values.get("Impact Type")),
            theme=_blank_to_none(_clean_text(values.get("Theme"))),
            country=_blank_to_none(_clean_text(values.get("Country"))),
            tag=_initiative_tag(values.get("Initiative Tag")),
            priority=_choice(values.get("Priority"), {"high", "medium", "low"}) or "medium",
            summary=_blank_to_none(_clean_text(values.get("Description"))),
            context_problem=_blank_to_none(_clean_text(values.get("Context & Problem"))),
            value_logic=_blank_to_none(_clean_text(values.get("Value Logic / Assumptions"))),
            dependencies_text=_blank_to_none(_clean_text(values.get("Dependencies"))),
            planned_start=_blank_to_none(_date_text(values.get("Planned Start Date"))),
            planned_end=_blank_to_none(_date_text(values.get("Planned Completion Date"))),
        )
    except ValueError as exc:
        errors.append(
            WorkbookValidationError(sheet="Overview", row=None, column=None, message=str(exc))
        )
        return InitiativeCreate(name=name)


def _parse_alchemist_benefits(
    rows: list[list[str]],
    fiscal_years: list[int],
    errors: list[WorkbookValidationError],
) -> list[FinancialEntryUpdate]:
    headers, body = _headered_alchemist_rows(rows, "Name")
    if not headers:
        return []
    period_columns = _period_columns(headers, fiscal_years)
    by_period: dict[tuple[int, int], dict[str, Decimal | int | None]] = {}
    metric_map = {
        ("revenue uplift", "plan base"): "revenue_uplift_base",
        ("revenue uplift", "plan high"): "revenue_uplift_high",
        ("revenue uplift", "actual"): "revenue_uplift_actual",
        ("gross margin", "plan base"): "gross_margin_base",
        ("gross margin", "plan high"): "gross_margin_high",
        ("gross margin", "actual"): "gross_margin_actual",
    }
    for row in body:
        named = _row_dict(headers, row)
        name = _norm(named.get("Name"))
        lane = _norm(named.get("Lane"))
        if "gross margin uplift" in name:
            continue
        field = metric_map.get((name, lane))
        if not field:
            continue
        for index, year, month in period_columns:
            amount = _optional_decimal(_cell(named, headers, row, index))
            if amount is None:
                continue
            if amount == 0:
                continue
            monthly_amount = _scale_millions(amount)
            period = by_period.setdefault(
                (year, month),
                {"year": year, "month": month, "quarter": None},
            )
            period[field] = monthly_amount
            if field.startswith("gross_margin_"):
                period[field.replace("gross_margin_", "gm_uplift_")] = monthly_amount
    items: list[FinancialEntryUpdate] = []
    for row in by_period.values():
        try:
            items.append(FinancialEntryUpdate(**row))
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="Benefits", row=None, column=None, message=str(exc))
            )
    return items


def _parse_alchemist_costs(
    rows: list[list[str]],
    fiscal_years: list[int],
    errors: list[WorkbookValidationError],
) -> list[CostLineCreate]:
    headers, body = _headered_alchemist_rows(rows, "Name")
    if not headers:
        return []
    period_columns = _period_columns(headers, fiscal_years)
    by_line: dict[tuple[str, int, int, bool], dict[str, Any]] = {}
    for row in body:
        named = _row_dict(headers, row)
        name = _clean_text(named.get("Name"))
        if not name:
            continue
        lane = _norm(named.get("Lane"))
        is_recurring = "recurring" in _norm(named.get("Impact Type") or named.get("Plan Mode"))
        if "one-off" in _norm(named.get("Impact Type") or named.get("Plan Mode")):
            is_recurring = False
        for index, year, month in period_columns:
            amount = _optional_decimal(_cell(named, headers, row, index))
            if amount is None:
                continue
            key = (name, year, month, is_recurring)
            item = by_line.setdefault(
                key,
                {
                    "name": name,
                    "year": year,
                    "month": month,
                    "quarter": None,
                    "amount_plan": Decimal("0"),
                    "amount_actual": None,
                    "is_recurring": is_recurring,
                },
            )
            if lane == "actual":
                item["amount_actual"] = _scale_millions(amount)
            else:
                item["amount_plan"] = _scale_millions(amount)
    items: list[CostLineCreate] = []
    for row in by_line.values():
        if row["amount_plan"] == 0 and row["amount_actual"] in {None, Decimal("0")}:
            continue
        try:
            items.append(CostLineCreate(**row))
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="Costs", row=None, column=None, message=str(exc))
            )
    return items


def _parse_alchemist_kpis(
    rows: list[list[str]],
    fiscal_years: list[int],
    errors: list[WorkbookValidationError],
) -> list[KPIWorkbookItem]:
    headers, body = _headered_alchemist_rows(rows, "Name")
    if not headers:
        return []
    period_columns = _period_columns(headers, fiscal_years)
    by_name: dict[str, dict[str, Any]] = {}
    for row in body:
        named = _row_dict(headers, row)
        name = _clean_text(named.get("Name"))
        if not name:
            continue
        item = by_name.setdefault(
            name,
            {
                "name": name,
                "type": _kpi_type(named.get("Type")),
                "category": _blank_to_none(
                    _clean_text(named.get("_kpi_category") or named.get("Impacted Metric"))
                ),
                "frequency": _frequency(named.get("Cadence")),
                "unit": _blank_to_none(
                    _clean_text(named.get("Unit") or named.get("Custom Unit Label"))
                ),
                "entries": {},
            },
        )
        lane = _norm(named.get("Lane"))
        target = {
            "base case": "value_base",
            "high case": "value_high",
            "actual": "value_actual",
        }.get(lane)
        if not target:
            continue
        for index, year, month in period_columns:
            raw = _cell(named, headers, row, index)
            if raw == "":
                continue
            quarter = ((month - 1) // 3) + 1
            entry = item["entries"].setdefault((year, quarter), {"year": year, "quarter": quarter})
            entry[target] = raw
    result: list[KPIWorkbookItem] = []
    for item in by_name.values():
        item["entries"] = list(item["entries"].values())
        try:
            result.append(KPIWorkbookItem(**item))
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="KPIs", row=None, column=None, message=str(exc))
            )
    return result


def _parse_alchemist_risks(
    rows: list[list[str]],
    errors: list[WorkbookValidationError],
) -> list[RiskCreate]:
    headers, body = _headered_alchemist_rows(rows, "Name")
    items: list[RiskCreate] = []
    for index, row in enumerate(body, start=1):
        named = _row_dict(headers, row)
        description = _clean_text(named.get("Description") or named.get("Name"))
        if not description:
            continue
        try:
            items.append(
                RiskCreate(
                    description=description,
                    type=_risk_type(named.get("Type")),
                    impact=_choice(named.get("Impact"), {"high", "medium", "low"}),
                    likelihood=_choice(named.get("Likelihood"), {"high", "medium", "low"}),
                    status="closed" if _norm(named.get("Status")) == "closed" else "open",
                    mitigation=_blank_to_none(_clean_text(named.get("Mitigation"))),
                )
            )
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="Risks", row=index, column=None, message=str(exc))
            )
    return items


def _parse_alchemist_milestones(
    rows: list[list[str]],
    errors: list[WorkbookValidationError],
) -> list[MilestoneCreate]:
    headers, body = _headered_alchemist_rows(rows, "Name")
    items: list[MilestoneCreate] = []
    for index, row in enumerate(body, start=1):
        named = _row_dict(headers, row)
        name = _clean_text(named.get("Name"))
        if not name:
            continue
        description_parts = []
        for label, key in (
            ("Type", "Type"),
            ("Source owner", "Owner"),
            ("Source status", "Status"),
        ):
            value = _clean_text(named.get(key))
            if value:
                description_parts.append(f"{label}: {value}")
        try:
            items.append(
                MilestoneCreate(
                    name=name,
                    description="\n".join(description_parts) or None,
                    priority=_choice(named.get("Priority"), {"high", "medium", "low"}) or "medium",
                    planned_start=_blank_to_none(_date_text(named.get("Planned Start"))),
                    planned_end=_blank_to_none(_date_text(named.get("Planned End"))),
                )
            )
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(
                    sheet="Milestones", row=index, column=None, message=str(exc)
                )
            )
    return items


def _parse_alchemist_status_updates(rows: list[list[str]]) -> list[dict[str, Any]]:
    headers, body = _headered_alchemist_rows(rows, "Date (week of)")
    items: list[dict[str, Any]] = []
    for row in body:
        named = _row_dict(headers, row)
        summary = _clean_text(named.get("Summary"))
        if not summary:
            continue
        items.append(
            {
                "rag_status": _choice(named.get("RAG"), {"green", "amber", "red"}) or "green",
                "summary": summary,
                "achievements": _blank_to_none(_clean_text(named.get("Achievements"))),
                "issues": _blank_to_none(_clean_text(named.get("Issues"))),
                "next_steps": _blank_to_none(_clean_text(named.get("Next Steps"))),
                "is_draft": _norm(named.get("_is_draft")) == "true",
            }
        )
    return items


def build_preview(parsed: InitiativeWorkbookData) -> InitiativeWorkbookPreview:
    return InitiativeWorkbookPreview(
        name=parsed.overview.name,
        country=parsed.overview.country,
        priority=parsed.overview.priority,
        overview=parsed.overview,
        counts={
            "financials": len(parsed.financial_entries),
            "costs": len(parsed.cost_lines),
            "kpis": len(parsed.kpis),
            "risks": len(parsed.risks),
            "milestones": len(parsed.milestones),
        },
        validation_errors=parsed.validation_errors,
    )


def _dict_rows(
    rows: list[list[str]],
    expected_headers: list[str],
    sheet: str,
    errors: list[WorkbookValidationError],
) -> Iterable[dict[str, str]]:
    if not rows:
        return
    headers = [h.strip() for h in rows[0]]
    missing = [header for header in expected_headers if header not in headers]
    if missing:
        errors.append(
            WorkbookValidationError(
                sheet=sheet,
                row=1,
                column=None,
                message=f"Sheet is missing columns: {', '.join(missing)}",
            )
        )
        return
    for values in rows[1:]:
        row = {
            header: values[headers.index(header)].strip()
            if headers.index(header) < len(values)
            else ""
            for header in expected_headers
        }
        if any(row.values()):
            yield row


def _parse_overview(
    row: dict[str, str],
    errors: list[WorkbookValidationError],
) -> InitiativeCreate:
    name = _required(row, "name", "Overview", 2, errors)
    if not name:
        name = "Invalid workbook"
    try:
        return InitiativeCreate(
            name=name,
            type=_blank_to_none(row["type"]),
            impact_type=_blank_to_none(row["impact_type"]),
            theme=_blank_to_none(row["theme"]),
            country=_blank_to_none(row["country"]),
            tag=_blank_to_none(row["tag"]),
            priority=row["priority"] or "medium",
            summary=_blank_to_none(row["summary"]),
            context_problem=_blank_to_none(row["context_problem"]),
            value_logic=_blank_to_none(row["value_logic"]),
            dependencies_text=_blank_to_none(row["dependencies_text"]),
            planned_start=_blank_to_none(row["planned_start"]),
            planned_end=_blank_to_none(row["planned_end"]),
        )
    except ValueError as exc:
        errors.append(
            WorkbookValidationError(sheet="Overview", row=2, column=None, message=str(exc))
        )
        return InitiativeCreate(name=name)


def _parse_benefits(
    rows: list[list[str]],
    errors: list[WorkbookValidationError],
) -> list[FinancialEntryUpdate]:
    expected = SHEET_DEFS[1][1]
    items = []
    for index, row in enumerate(_dict_rows(rows, expected, "Benefits", errors), start=2):
        try:
            items.append(
                FinancialEntryUpdate(
                    year=_int(row["year"], "Benefits", index, "year", errors) or 2030,
                    quarter=_optional_int(row["quarter"], "Benefits", index, "quarter", errors),
                    month=_optional_int(row["month"], "Benefits", index, "month", errors),
                    revenue_uplift_base=_decimal(row["revenue_uplift_base"]),
                    revenue_uplift_high=_decimal(row["revenue_uplift_high"]),
                    revenue_uplift_actual=_optional_decimal(row["revenue_uplift_actual"]),
                    gross_margin_base=_decimal(row["gross_margin_base"]),
                    gross_margin_high=_decimal(row["gross_margin_high"]),
                    gross_margin_actual=_optional_decimal(row["gross_margin_actual"]),
                    gm_uplift_base=_decimal(row["gm_uplift_base"]),
                    gm_uplift_high=_decimal(row["gm_uplift_high"]),
                    gm_uplift_actual=_optional_decimal(row["gm_uplift_actual"]),
                )
            )
        except (InvalidOperation, ValueError) as exc:
            errors.append(
                WorkbookValidationError(sheet="Benefits", row=index, column=None, message=str(exc))
            )
    return items


def _parse_costs(
    rows: list[list[str]], errors: list[WorkbookValidationError]
) -> list[CostLineCreate]:
    expected = SHEET_DEFS[2][1]
    items = []
    for index, row in enumerate(_dict_rows(rows, expected, "Costs", errors), start=2):
        name = _required(row, "name", "Costs", index, errors)
        if not name:
            continue
        try:
            items.append(
                CostLineCreate(
                    name=name,
                    year=_int(row["year"], "Costs", index, "year", errors) or 2030,
                    quarter=_optional_int(row["quarter"], "Costs", index, "quarter", errors),
                    month=_optional_int(row["month"], "Costs", index, "month", errors),
                    amount_plan=_decimal(row["amount_plan"]),
                    amount_actual=_optional_decimal(row["amount_actual"]),
                    is_recurring=row["is_recurring"].strip().lower() in {"true", "1", "yes", "y"},
                )
            )
        except (InvalidOperation, ValueError) as exc:
            errors.append(
                WorkbookValidationError(sheet="Costs", row=index, column=None, message=str(exc))
            )
    return items


def _parse_kpis(
    rows: list[list[str]], errors: list[WorkbookValidationError]
) -> list[KPIWorkbookItem]:
    expected = SHEET_DEFS[3][1]
    items = []
    for index, row in enumerate(_dict_rows(rows, expected, "KPIs", errors), start=2):
        name = _required(row, "name", "KPIs", index, errors)
        if not name:
            continue
        entries = []
        if row.get("year"):
            entries.append(
                KPIEntryUpsert(
                    year=_int(row["year"], "KPIs", index, "year", errors) or 2030,
                    quarter=_optional_int(row["quarter"], "KPIs", index, "quarter", errors),
                    value_base=_blank_to_none(row["value_base"]),
                    value_high=_blank_to_none(row["value_high"]),
                    value_actual=_blank_to_none(row["value_actual"]),
                )
            )
        try:
            items.append(
                KPIWorkbookItem(
                    name=name,
                    type=row["type"] or "custom",
                    category=_blank_to_none(row["category"]),
                    frequency=row["frequency"] or "quarterly",
                    unit=_blank_to_none(row["unit"]),
                    entries=entries,
                )
            )
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="KPIs", row=index, column=None, message=str(exc))
            )
    return items


def _parse_risks(rows: list[list[str]], errors: list[WorkbookValidationError]) -> list[RiskCreate]:
    expected = SHEET_DEFS[4][1]
    items = []
    for index, row in enumerate(_dict_rows(rows, expected, "Risks", errors), start=2):
        description = _required(row, "description", "Risks", index, errors)
        if not description:
            continue
        try:
            items.append(
                RiskCreate(
                    description=description,
                    type=_blank_to_none(row["type"]),
                    impact=_blank_to_none(row["impact"]),
                    likelihood=_blank_to_none(row["likelihood"]),
                    mitigation=_blank_to_none(row["mitigation"]),
                )
            )
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(sheet="Risks", row=index, column=None, message=str(exc))
            )
    return items


def _parse_milestones(
    rows: list[list[str]],
    errors: list[WorkbookValidationError],
) -> list[MilestoneCreate]:
    expected = SHEET_DEFS[5][1]
    items = []
    for index, row in enumerate(_dict_rows(rows, expected, "Milestones", errors), start=2):
        name = _required(row, "name", "Milestones", index, errors)
        if not name:
            continue
        try:
            items.append(
                MilestoneCreate(
                    name=name,
                    description=_blank_to_none(row["description"]),
                    priority=row["priority"] or "medium",
                    planned_start=_blank_to_none(row["planned_start"]),
                    planned_end=_blank_to_none(row["planned_end"]),
                )
            )
        except ValueError as exc:
            errors.append(
                WorkbookValidationError(
                    sheet="Milestones", row=index, column=None, message=str(exc)
                )
            )
    return items


def _required(
    row: dict[str, str],
    key: str,
    sheet: str,
    row_number: int,
    errors: list[WorkbookValidationError],
) -> str:
    value = row[key].strip()
    if not value:
        errors.append(
            WorkbookValidationError(
                sheet=sheet,
                row=row_number,
                column=key,
                message=f"Missing {key}",
            )
        )
    return value


def _blank_to_none(value: str) -> str | None:
    value = value.strip()
    return value or None


def _decimal(value: str) -> Decimal:
    return Decimal(value.strip() or "0")


def _optional_decimal(value: str) -> Decimal | None:
    value = value.strip()
    return Decimal(value) if value else None


def _int(
    value: str,
    sheet: str,
    row_number: int,
    column: str,
    errors: list[WorkbookValidationError],
) -> int | None:
    value = value.strip()
    if not value:
        errors.append(
            WorkbookValidationError(
                sheet=sheet,
                row=row_number,
                column=column,
                message=f"Missing {column}",
            )
        )
        return None
    try:
        return int(value)
    except ValueError:
        errors.append(
            WorkbookValidationError(
                sheet=sheet,
                row=row_number,
                column=column,
                message=f"Invalid integer: {value}",
            )
        )
        return None


def _optional_int(
    value: str,
    sheet: str,
    row_number: int,
    column: str,
    errors: list[WorkbookValidationError],
) -> int | None:
    value = value.strip()
    if not value:
        return None
    return _int(value, sheet, row_number, column, errors)


def _key_value_rows(rows: list[list[str]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        if len(row) >= 2 and row[0].strip():
            result[row[0].strip()] = row[1].strip()
    return result


def _headered_alchemist_rows(
    rows: list[list[str]], first_header: str
) -> tuple[list[str], list[list[str]]]:
    for index, row in enumerate(rows):
        if row and row[0].strip() == first_header:
            return [value.strip() for value in row], rows[index + 1 :]
    return [], []


def _row_dict(headers: list[str], row: list[str]) -> dict[str, str]:
    return {
        header: row[index].strip() if index < len(row) else ""
        for index, header in enumerate(headers)
        if header
    }


def _cell(named: dict[str, str], headers: list[str], row: list[str], index: int) -> str:
    header = headers[index]
    if header and header not in named:
        return named.get(header, "")
    return row[index].strip() if index < len(row) else ""


def _fiscal_years(reference: dict[str, str], overview: dict[str, str]) -> list[int]:
    raw = reference.get("fiscal_years (csv)") or reference.get("fiscal_years") or ""
    years = [int(item) for item in re.findall(r"20\d{2}", raw)]
    if years:
        return years
    start = int(reference.get("base_fiscal_year") or datetime.now().year)
    count = int(reference.get("num_fiscal_years") or "5")
    return list(range(start, start + count))


def _period_columns(headers: list[str], fiscal_years: list[int]) -> list[tuple[int, int, int]]:
    fy_indexes = [
        index for index, value in enumerate(headers) if re.fullmatch(r"FY\d{2,4}", value.strip())
    ]
    start = (fy_indexes[-1] + 1) if fy_indexes else 0
    periods: list[tuple[int, int, int]] = []
    month_offset = 0
    for index in range(start, len(headers)):
        month = _MONTHS.get(headers[index].strip().lower())
        if not month:
            continue
        year = (
            fiscal_years[month_offset // 12]
            if month_offset // 12 < len(fiscal_years)
            else fiscal_years[-1]
        )
        periods.append((index, year, month))
        month_offset += 1
    return periods


def _scale_millions(value: Decimal) -> Decimal:
    return (value * Decimal("1000000")).quantize(Decimal("0.0001"))


def _norm(value: str | None) -> str:
    return _clean_text(value).strip().lower().replace("_", " ")


def _clean_text(value: str | None) -> str:
    value = str(value or "")
    value = re.sub(r"<\s*br\s*/?\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"</p\s*>", "\n", value, flags=re.IGNORECASE)
    value = re.sub(r"<[^>]+>", "", value)
    return unescape(value).strip()


def _choice(value: str | None, allowed: set[str]) -> str | None:
    cleaned = _norm(value).replace(" ", "_")
    return cleaned if cleaned in allowed else None


def _initiative_type(value: str | None) -> str | None:
    cleaned = _norm(value)
    mapping = {
        "revenue": "revenue_growth",
        "revenue growth": "revenue_growth",
        "cost reduction": "cost_reduction",
        "avoidance": "cost_avoidance",
        "cost avoidance": "cost_avoidance",
        "compliance": "compliance",
        "capability": "capability_building",
        "capability building": "capability_building",
    }
    return mapping.get(cleaned)


def _impact_type(value: str | None) -> str | None:
    cleaned = _norm(value)
    if cleaned in {"recurring", "one off", "one-off", "one_off"}:
        return "one_off" if cleaned != "recurring" else "recurring"
    return None


def _initiative_tag(value: str | None) -> str | None:
    return _choice(value, {"automation", "offshoring", "commercial", "other"})


def _stage(value: str | None) -> str | None:
    cleaned = _norm(value)
    return {
        "scoping": "scoping",
        "execution": "in_progress",
        "in progress": "in_progress",
        "in_progress": "in_progress",
        "executed": "complete",
        "complete": "complete",
    }.get(cleaned)


def _risk_type(value: str | None) -> str | None:
    cleaned = _norm(value)
    if cleaned in {"technology", "tech"}:
        return "technology"
    if cleaned in {"people", "adoption", "change"}:
        return "people"
    if cleaned == "financial":
        return "financial"
    return "operational" if cleaned else None


def _kpi_type(value: str | None) -> str:
    cleaned = _norm(value)
    if "gross" in cleaned:
        return "gross_margin"
    if "operational" in cleaned:
        return "operational"
    return "custom"


def _frequency(value: str | None) -> str:
    cleaned = _norm(value)
    if cleaned in {"monthly", "quarterly", "annual"}:
        return cleaned
    return "quarterly"


def _date_text(value: str | None) -> str:
    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        return cleaned
    try:
        serial = float(cleaned)
        if serial > 20000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(cleaned[:19], fmt).date().isoformat()
        except ValueError:
            continue
    return cleaned


def _sheet_paths(zf: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_by_id = {
        rel.attrib["Id"]: rel.attrib["Target"].lstrip("/")
        for rel in rels.findall("rel:Relationship", _REL_NS)
    }
    paths: dict[str, str] = {}
    rel_key = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in workbook.findall("main:sheets/main:sheet", _NS):
        target = rel_by_id[sheet.attrib[rel_key]]
        paths[sheet.attrib["name"]] = target if target.startswith("xl/") else f"xl/{target}"
    return paths


def _shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return [unescape("".join(item.itertext())) for item in root.findall("main:si", _NS)]


def _read_sheet(zf: ZipFile, path: str, shared_strings: list[str] | None = None) -> list[list[str]]:
    shared_strings = shared_strings or []
    root = ET.fromstring(zf.read(path))
    rows: list[list[str]] = []
    for row in root.findall("main:sheetData/main:row", _NS):
        values: list[str] = []
        current_col = 1
        for cell in row.findall("main:c", _NS):
            col = _column_number(cell.attrib.get("r", "A1"))
            while current_col < col:
                values.append("")
                current_col += 1
            inline = cell.find("main:is", _NS)
            if inline is not None:
                values.append(unescape("".join(inline.itertext())))
            else:
                raw = cell.findtext("main:v", default="", namespaces=_NS)
                if cell.attrib.get("t") == "s" and raw:
                    try:
                        values.append(shared_strings[int(raw)])
                    except (IndexError, ValueError):
                        values.append("")
                else:
                    values.append(raw)
            current_col += 1
        rows.append(values)
    return rows


def _prepared_sheet_rows(
    name: str,
    headers: list[str],
    rows: list[list[str]],
) -> tuple[list[str], list[list[str]]]:
    if name == "Benefits":
        formulas = ["fy_revenue_base_formula", "fy_gm_base_formula", "fy_gm_actual_formula"]
        return [*headers, *formulas], [row + ["", "", ""] for row in rows]
    if name == "Costs":
        return [*headers, "fy_cost_plan_formula"], [row + [""] for row in rows]
    return headers, rows


def _sheet(
    rows: list[list[str]],
    *,
    data_validations: str = "",
    drawing: bool = False,
) -> str:
    row_xml = []
    headers = rows[0] if rows else []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            formula = _formula(headers, col_index, row_index)
            if formula:
                cells.append(f'<c r="{ref}"><f>{_xml(formula)}</f></c>')
            else:
                cells.append(f'<c r="{ref}"{style} t="inlineStr"><is><t>{_xml(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    drawing_xml = '<drawing r:id="rId1"/>' if drawing else ""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheetData>{''.join(row_xml)}</sheetData>{data_validations}{drawing_xml}</worksheet>"
    )


def _formula(headers: list[str], col_index: int, row_index: int) -> str:
    if row_index == 1 or col_index > len(headers):
        return ""
    header = headers[col_index - 1]
    cell = lambda name: f"{_column_name(headers.index(name) + 1)}{row_index}"
    if header == "fy_revenue_base_formula" and "revenue_uplift_base" in headers:
        return f"SUM({cell('revenue_uplift_base')}:{cell('revenue_uplift_base')})"
    if header == "fy_gm_base_formula" and "gm_uplift_base" in headers:
        return f"SUM({cell('gm_uplift_base')}:{cell('gm_uplift_base')})"
    if header == "fy_gm_actual_formula" and "gm_uplift_actual" in headers:
        return f"SUM({cell('gm_uplift_actual')}:{cell('gm_uplift_actual')})"
    if header == "fy_cost_plan_formula" and "amount_plan" in headers:
        return f"SUM({cell('amount_plan')}:{cell('amount_plan')})"
    return ""


def _data_validations(name: str, headers: list[str], row_count: int) -> str:
    max_row = max(row_count + 1, 100)
    ranges: list[tuple[str, str]] = []
    if name == "Overview":
        ranges.extend(
            [
                ("stage", '"scoping,in_progress,complete"'),
                ("rag_status", '"green,amber,red"'),
                (
                    "type",
                    '"revenue_growth,cost_reduction,cost_avoidance,compliance,capability_building"',
                ),
                ("impact_type", '"recurring,one_off"'),
                ("tag", '"automation,offshoring,commercial,other"'),
                ("priority", '"high,medium,low"'),
            ]
        )
    elif name == "KPIs":
        ranges.append(("frequency", '"weekly,monthly,quarterly,annual"'))
    elif name in {"Risks", "Milestones"}:
        ranges.append(("priority" if name == "Milestones" else "impact", '"high,medium,low"'))
    validations = []
    for header, allowed in ranges:
        if header not in headers:
            continue
        col = _column_name(headers.index(header) + 1)
        validations.append(
            f'<dataValidation type="list" allowBlank="1" sqref="{col}2:{col}{max_row}">'
            f"<formula1>{_xml(allowed)}</formula1></dataValidation>"
        )
    if not validations:
        return ""
    return f'<dataValidations count="{len(validations)}">{"".join(validations)}</dataValidations>'


def _column_number(ref: str) -> int:
    result = 0
    for ch in "".join(c for c in ref if c.isalpha()):
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
    return result or 1


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(ord("A") + rem) + name
    return name


def _xml(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def _content_types(sheet_count: int) -> str:
    sheets = "\n".join(
        f'  <Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheets}
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/>
</Types>"""


def _root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook(sheet_defs: list[tuple[str, list[str], list[list[str]]]]) -> str:
    sheets = "\n".join(
        f'    <sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _, _) in enumerate(sheet_defs, start=1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
{sheets}
  </sheets>
</workbook>"""


def _workbook_rels(sheet_count: int) -> str:
    sheet_rels = "\n".join(
        f'  <Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{sheet_rels}
  <Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


def _sheet_drawing_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/drawing" Target="../drawings/drawing1.xml"/>
</Relationships>"""


def _drawing_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/transmuter-logo.png"/>
</Relationships>"""


def _drawing() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <xdr:twoCellAnchor editAs="oneCell">
    <xdr:from><xdr:col>0</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from>
    <xdr:to><xdr:col>1</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>1</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:to>
    <xdr:pic>
      <xdr:nvPicPr><xdr:cNvPr id="1" name="Transmuter logo"/><xdr:cNvPicPr/></xdr:nvPicPr>
      <xdr:blipFill><a:blip xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:embed="rId1"/><a:stretch><a:fillRect/></a:stretch></xdr:blipFill>
      <xdr:spPr><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></xdr:spPr>
    </xdr:pic>
    <xdr:clientData/>
  </xdr:twoCellAnchor>
</xdr:wsDr>"""


def _styles() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2">
    <font><sz val="11"/><name val="Aptos"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Aptos"/></font>
  </fonts>
  <fills count="2">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF7C3AED"/><bgColor indexed="64"/></patternFill></fill>
  </fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
    <xf numFmtId="0" fontId="1" fillId="1" borderId="0" xfId="0" applyFont="1" applyFill="1"/>
  </cellXfs>
</styleSheet>"""
