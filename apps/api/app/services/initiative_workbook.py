"""Minimal XLSX helpers for initiative template import/export."""

from __future__ import annotations

from collections.abc import Iterable
from io import BytesIO
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, status

from app.domain.initiatives import InitiativeCreate


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
    ("Benefits", ["year", "quarter", "month", "revenue_uplift_base", "revenue_uplift_high", "gm_uplift_base", "gm_uplift_high"], []),
    ("Costs", ["name", "year", "quarter", "month", "amount_plan", "amount_actual", "is_recurring"], []),
    ("KPIs", ["name", "type", "category", "frequency", "unit"], []),
    ("Risks", ["description", "type", "impact", "likelihood", "mitigation"], []),
    ("Milestones", ["name", "description", "priority", "planned_start", "planned_end"], []),
]

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def build_initiative_template() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types(len(SHEET_DEFS)))
        zf.writestr("_rels/.rels", _root_rels())
        zf.writestr("xl/workbook.xml", _workbook())
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(SHEET_DEFS)))
        zf.writestr("xl/styles.xml", _styles())
        for index, (_, headers, rows) in enumerate(SHEET_DEFS, start=1):
            zf.writestr(f"xl/worksheets/sheet{index}.xml", _sheet([headers, *rows]))
    return output.getvalue()


def parse_initiative_template(data: bytes) -> InitiativeCreate:
    try:
        with ZipFile(BytesIO(data)) as zf:
            sheets = _sheet_paths(zf)
            rows = _read_sheet(zf, sheets["Overview"])
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

    overview = next(_dict_rows(rows, OVERVIEW_COLUMNS), None)
    if not overview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Overview sheet must include one initiative row",
        )
    return InitiativeCreate(
        name=_required(overview, "name"),
        type=_blank_to_none(overview["type"]),
        impact_type=_blank_to_none(overview["impact_type"]),
        theme=_blank_to_none(overview["theme"]),
        country=_blank_to_none(overview["country"]),
        tag=_blank_to_none(overview["tag"]),
        priority=overview["priority"] or "medium",
        summary=_blank_to_none(overview["summary"]),
        value_logic=_blank_to_none(overview["value_logic"]),
        dependencies_text=_blank_to_none(overview["dependencies_text"]),
        planned_start=_blank_to_none(overview["planned_start"]),
        planned_end=_blank_to_none(overview["planned_end"]),
    )


def _dict_rows(rows: list[list[str]], expected_headers: list[str]) -> Iterable[dict[str, str]]:
    if not rows:
        return
    headers = [h.strip() for h in rows[0]]
    missing = [header for header in expected_headers if header not in headers]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Overview sheet is missing columns: {', '.join(missing)}",
        )
    for values in rows[1:]:
        row = {header: values[headers.index(header)].strip() if headers.index(header) < len(values) else "" for header in expected_headers}
        if any(row.values()):
            yield row


def _required(row: dict[str, str], key: str) -> str:
    value = row[key].strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing {key}")
    return value


def _blank_to_none(value: str) -> str | None:
    value = value.strip()
    return value or None


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
            values.append("" if inline is None else "".join(inline.itertext()))
            current_col += 1
        rows.append(values)
    return rows


def _sheet(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{_xml(value)}</t></is></c>')
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


def _workbook() -> str:
    sheets = "\n".join(
        f'    <sheet name="{name}" sheetId="{index}" r:id="rId{index}"/>'
        for index, (name, _, _) in enumerate(SHEET_DEFS, start=1)
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
  <fonts count="1"><font><sz val="11"/><name val="Aptos"/></font></fonts>
  <fills count="1"><fill><patternFill patternType="none"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>
</styleSheet>"""
