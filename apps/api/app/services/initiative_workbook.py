"""Minimal XLSX helpers for initiative template import/export."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from html import unescape
from io import BytesIO
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
    "value_logic",
    "dependencies_text",
    "planned_start",
    "planned_end",
]

SAMPLE_OVERVIEW = [
    "Imported Acceptance Initiative",
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
            "year", "quarter", "month",
            "revenue_uplift_base", "revenue_uplift_high", "revenue_uplift_actual",
            "gross_margin_base", "gross_margin_high", "gross_margin_actual",
            "gm_uplift_base", "gm_uplift_high", "gm_uplift_actual",
        ],
        [["2030", "1", "", "100000.0000", "150000.0000", "", "45000.0000", "70000.0000", "", "45000.0000", "70000.0000", ""]],
    ),
    (
        "Costs",
        ["name", "year", "quarter", "month", "amount_plan", "amount_actual", "is_recurring"],
        [["Implementation support", "2030", "1", "", "12000.0000", "", "false"]],
    ),
    (
        "KPIs",
        ["name", "type", "category", "frequency", "unit", "year", "quarter", "value_base", "value_high", "value_actual"],
        [["Cycle time reduction", "operational", "delivery", "quarterly", "%", "2030", "1", "15.0000", "25.0000", ""]],
    ),
    (
        "Risks",
        ["description", "type", "impact", "likelihood", "mitigation"],
        [["Adoption may lag without local champions", "people", "medium", "medium", "Assign market champions and weekly adoption review."]],
    ),
    (
        "Milestones",
        ["name", "description", "priority", "planned_start", "planned_end"],
        [["Pilot launch complete", "Complete pilot and validate benefits tracking.", "high", "2030-02-01", "2030-03-31"]],
    ),
]

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


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
    sheet_defs = [
        ("Overview", OVERVIEW_COLUMNS, overview_rows),
        (SHEET_DEFS[1][0], SHEET_DEFS[1][1], benefit_rows),
        (SHEET_DEFS[2][0], SHEET_DEFS[2][1], cost_rows),
        (SHEET_DEFS[3][0], SHEET_DEFS[3][1], kpi_rows),
        (SHEET_DEFS[4][0], SHEET_DEFS[4][1], risk_rows),
        (SHEET_DEFS[5][0], SHEET_DEFS[5][1], milestone_rows),
        (
            "Status Updates",
            ["submitted_at", "rag_status", "summary", "achievements", "issues", "next_steps", "submitted_by"],
            status_update_rows,
        ),
        ("Meeting Notes", ["session_date", "meeting_name", "notes", "status"], meeting_note_rows),
        ("_Reference", ["key", "value"], reference_rows),
    ]
    return _build_workbook(sheet_defs)


def _build_workbook(sheet_defs: list[tuple[str, list[str], list[list[str]]]]) -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(len(sheet_defs)))
        zf.writestr("_rels/.rels", _root_rels())
        zf.writestr("xl/workbook.xml", _workbook(sheet_defs))
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheet_defs)))
        zf.writestr("xl/styles.xml", _styles())
        for index, (_, headers, rows) in enumerate(sheet_defs, start=1):
            zf.writestr(f"xl/worksheets/sheet{index}.xml", _sheet([headers, *rows]))
    return output.getvalue()


def parse_initiative_template(data: bytes) -> InitiativeWorkbookData:
    try:
        with ZipFile(BytesIO(data)) as zf:
            sheets = _sheet_paths(zf)
            overview_rows = _read_sheet(zf, sheets["Overview"])
            benefits_rows = _read_sheet(zf, sheets["Benefits"]) if "Benefits" in sheets else []
            costs_rows = _read_sheet(zf, sheets["Costs"]) if "Costs" in sheets else []
            kpi_rows = _read_sheet(zf, sheets["KPIs"]) if "KPIs" in sheets else []
            risk_rows = _read_sheet(zf, sheets["Risks"]) if "Risks" in sheets else []
            milestone_rows = _read_sheet(zf, sheets["Milestones"]) if "Milestones" in sheets else []
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
        row = {header: values[headers.index(header)].strip() if headers.index(header) < len(values) else "" for header in expected_headers}
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
            value_logic=_blank_to_none(row["value_logic"]),
            dependencies_text=_blank_to_none(row["dependencies_text"]),
            planned_start=_blank_to_none(row["planned_start"]),
            planned_end=_blank_to_none(row["planned_end"]),
        )
    except ValueError as exc:
        errors.append(WorkbookValidationError(sheet="Overview", row=2, column=None, message=str(exc)))
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
            errors.append(WorkbookValidationError(sheet="Benefits", row=index, column=None, message=str(exc)))
    return items


def _parse_costs(rows: list[list[str]], errors: list[WorkbookValidationError]) -> list[CostLineCreate]:
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
            errors.append(WorkbookValidationError(sheet="Costs", row=index, column=None, message=str(exc)))
    return items


def _parse_kpis(rows: list[list[str]], errors: list[WorkbookValidationError]) -> list[KPIWorkbookItem]:
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
            errors.append(WorkbookValidationError(sheet="KPIs", row=index, column=None, message=str(exc)))
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
            errors.append(WorkbookValidationError(sheet="Risks", row=index, column=None, message=str(exc)))
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
            errors.append(WorkbookValidationError(sheet="Milestones", row=index, column=None, message=str(exc)))
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


def _read_sheet(zf: ZipFile, path: str) -> list[list[str]]:
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
            values.append("" if inline is None else unescape("".join(inline.itertext())))
            current_col += 1
        rows.append(values)
    return rows


def _sheet(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            style = ' s="1"' if row_index == 1 else ""
            cells.append(f'<c r="{ref}"{style} t="inlineStr"><is><t>{_xml(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData></worksheet>'
    )


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
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _content_types(sheet_count: int) -> str:
    sheets = "\n".join(
        f'  <Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, sheet_count + 1)
    )
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
{sheets}
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
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
