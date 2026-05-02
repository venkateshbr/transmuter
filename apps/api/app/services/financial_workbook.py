"""Minimal XLSX workbook helpers for financial import/export.

The workbook is intentionally simple and deterministic so acceptance tests can
round-trip seeded data without adding a heavy spreadsheet dependency.
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException, status

from app.domain.financials import CostLineCreate, FinancialEntryUpdate, FinancialGridUpdate


ENTRY_COLUMNS = [
    "year",
    "quarter",
    "month",
    "revenue_uplift_base",
    "revenue_uplift_high",
    "revenue_uplift_actual",
    "revenue_uplift_pct_base",
    "revenue_uplift_pct_high",
    "revenue_uplift_pct_actual",
    "gross_margin_base",
    "gross_margin_high",
    "gross_margin_actual",
    "gm_pct_base",
    "gm_pct_high",
    "gm_pct_actual",
    "gm_uplift_base",
    "gm_uplift_high",
    "gm_uplift_actual",
    "gm_uplift_pct_base",
    "gm_uplift_pct_high",
    "gm_uplift_pct_actual",
    "cogs_base",
    "cogs_high",
    "cogs_actual",
    "cogs_pct_base",
    "cogs_pct_high",
    "cogs_pct_actual",
]

COST_COLUMNS = [
    "name",
    "year",
    "quarter",
    "month",
    "amount_plan",
    "amount_actual",
    "is_recurring",
]

_NS = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REL_NS = {"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}


def build_financial_workbook(entries: list[dict[str, Any]], cost_lines: list[dict[str, Any]]) -> bytes:
    """Build a two-sheet XLSX workbook as bytes."""
    entry_rows = [ENTRY_COLUMNS] + [[_cell_value(row.get(col)) for col in ENTRY_COLUMNS] for row in entries]
    cost_rows = [COST_COLUMNS] + [[_cell_value(row.get(col)) for col in COST_COLUMNS] for row in cost_lines]

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", _content_types())
        zf.writestr("_rels/.rels", _root_rels())
        zf.writestr("xl/workbook.xml", _workbook())
        zf.writestr("xl/_rels/workbook.xml.rels", _workbook_rels())
        zf.writestr("xl/styles.xml", _styles())
        zf.writestr("xl/worksheets/sheet1.xml", _sheet(entry_rows))
        zf.writestr("xl/worksheets/sheet2.xml", _sheet(cost_rows))
    return output.getvalue()


def parse_financial_workbook(data: bytes) -> FinancialGridUpdate:
    """Parse financial workbook bytes into the existing grid update contract."""
    try:
        with ZipFile(BytesIO(data)) as zf:
            shared_strings = _read_shared_strings(zf)
            sheets = _sheet_paths(zf)
            entry_rows = _read_sheet(zf, sheets["financial_entries"], shared_strings)
            cost_rows = _read_sheet(zf, sheets["cost_lines"], shared_strings)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workbook is missing required sheet: {exc.args[0]}",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid financial workbook",
        ) from exc

    return FinancialGridUpdate(
        entries=[_entry_from_row(row) for row in _dict_rows(entry_rows, ENTRY_COLUMNS)],
        cost_lines=[_cost_from_row(row) for row in _dict_rows(cost_rows, COST_COLUMNS)],
    )


def _cell_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _entry_from_row(row: dict[str, str]) -> FinancialEntryUpdate:
    return FinancialEntryUpdate(
        year=_int(row, "year"),
        quarter=_int_or_none(row, "quarter"),
        month=_int_or_none(row, "month"),
        revenue_uplift_base=_decimal(row, "revenue_uplift_base", default="0"),
        revenue_uplift_high=_decimal(row, "revenue_uplift_high", default="0"),
        revenue_uplift_actual=_decimal_or_none(row, "revenue_uplift_actual"),
        revenue_uplift_pct_base=_decimal(row, "revenue_uplift_pct_base", default="0"),
        revenue_uplift_pct_high=_decimal(row, "revenue_uplift_pct_high", default="0"),
        revenue_uplift_pct_actual=_decimal_or_none(row, "revenue_uplift_pct_actual"),
        gross_margin_base=_decimal(row, "gross_margin_base", default="0"),
        gross_margin_high=_decimal(row, "gross_margin_high", default="0"),
        gross_margin_actual=_decimal_or_none(row, "gross_margin_actual"),
        gm_pct_base=_decimal(row, "gm_pct_base", default="0"),
        gm_pct_high=_decimal(row, "gm_pct_high", default="0"),
        gm_pct_actual=_decimal_or_none(row, "gm_pct_actual"),
        gm_uplift_base=_decimal(row, "gm_uplift_base", default="0"),
        gm_uplift_high=_decimal(row, "gm_uplift_high", default="0"),
        gm_uplift_actual=_decimal_or_none(row, "gm_uplift_actual"),
        gm_uplift_pct_base=_decimal(row, "gm_uplift_pct_base", default="0"),
        gm_uplift_pct_high=_decimal(row, "gm_uplift_pct_high", default="0"),
        gm_uplift_pct_actual=_decimal_or_none(row, "gm_uplift_pct_actual"),
        cogs_base=_decimal(row, "cogs_base", default="0"),
        cogs_high=_decimal(row, "cogs_high", default="0"),
        cogs_actual=_decimal_or_none(row, "cogs_actual"),
        cogs_pct_base=_decimal(row, "cogs_pct_base", default="0"),
        cogs_pct_high=_decimal(row, "cogs_pct_high", default="0"),
        cogs_pct_actual=_decimal_or_none(row, "cogs_pct_actual"),
    )


def _cost_from_row(row: dict[str, str]) -> CostLineCreate:
    return CostLineCreate(
        name=_required(row, "name"),
        year=_int(row, "year"),
        quarter=_int_or_none(row, "quarter"),
        month=_int_or_none(row, "month"),
        amount_plan=_decimal(row, "amount_plan", default="0"),
        amount_actual=_decimal_or_none(row, "amount_actual"),
        is_recurring=_bool(row.get("is_recurring", "")),
    )


def _dict_rows(rows: list[list[str]], expected_headers: list[str]) -> Iterable[dict[str, str]]:
    if not rows:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workbook sheet is empty")
    headers = [h.strip() for h in rows[0]]
    missing = [header for header in expected_headers if header not in headers]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workbook sheet is missing columns: {', '.join(missing)}",
        )
    for values in rows[1:]:
        row = {header: values[headers.index(header)].strip() if headers.index(header) < len(values) else "" for header in expected_headers}
        if any(row.values()):
            yield row


def _required(row: dict[str, str], key: str) -> str:
    value = row.get(key, "").strip()
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Missing {key}")
    return value


def _int(row: dict[str, str], key: str) -> int:
    try:
        return int(Decimal(_required(row, key)))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid integer: {key}") from exc


def _int_or_none(row: dict[str, str], key: str) -> int | None:
    value = row.get(key, "").strip()
    if not value:
        return None
    try:
        return int(Decimal(value))
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid integer: {key}") from exc


def _decimal(row: dict[str, str], key: str, default: str) -> Decimal:
    value = row.get(key, "").strip() or default
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid decimal: {key}") from exc


def _decimal_or_none(row: dict[str, str], key: str) -> Decimal | None:
    value = row.get(key, "").strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid decimal: {key}") from exc


def _bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "y"}


def _read_shared_strings(zf: ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return ["".join(item.itertext()) for item in root.findall("main:si", _NS)]


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
        name = sheet.attrib["name"]
        rel_id = sheet.attrib[rel_key]
        target = rel_by_id[rel_id]
        path = target if target.startswith("xl/") else f"xl/{target}"
        paths[name] = path
    return paths


def _read_sheet(zf: ZipFile, path: str, shared_strings: list[str]) -> list[list[str]]:
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
            values.append(_read_cell(cell, shared_strings))
            current_col += 1
        rows.append(values)
    return rows


def _read_cell(cell: ET.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        inline = cell.find("main:is", _NS)
        return "" if inline is None else "".join(inline.itertext())
    value = cell.find("main:v", _NS)
    if value is None or value.text is None:
        return ""
    if cell_type == "s":
        return shared_strings[int(value.text)]
    return value.text


def _column_number(ref: str) -> int:
    letters = "".join(ch for ch in ref if ch.isalpha())
    result = 0
    for ch in letters:
        result = result * 26 + (ord(ch.upper()) - ord("A") + 1)
    return result or 1


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


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(ord("A") + rem) + name
    return name


def _xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _content_types() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""


def _root_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""


def _workbook() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="financial_entries" sheetId="1" r:id="rId1"/>
    <sheet name="cost_lines" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""


def _workbook_rels() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
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
