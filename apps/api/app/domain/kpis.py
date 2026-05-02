"""KPI domain models — Pydantic v2 contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KPICreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    type: Literal["gross_margin", "operational", "custom"] = "custom"
    category: str | None = None
    frequency: Literal["quarterly", "monthly", "annual"] = "quarterly"
    unit: str | None = None


class KPIUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    type: Literal["gross_margin", "operational", "custom"] | None = None
    category: str | None = None
    frequency: Literal["quarterly", "monthly", "annual"] | None = None
    unit: str | None = None


class KPIEntryItem(BaseModel):
    id: str
    kpi_id: str
    year: int
    quarter: int | None = None
    value_base: str | None = None
    value_high: str | None = None
    value_actual: str | None = None


class KPIItem(BaseModel):
    id: str
    initiative_id: str
    initiative_name: str | None = None
    initiative_code: str | None = None
    health_status: Literal["on_track", "at_risk", "critical", "no_data"] = "no_data"
    name: str
    type: str
    category: str | None = None
    frequency: str
    unit: str | None = None
    entries: list[KPIEntryItem] = []


class KPIEntryUpsert(BaseModel):
    year: int
    quarter: int | None = None
    value_base: str | None = None
    value_high: str | None = None
    value_actual: str | None = None


class KPIListResponse(BaseModel):
    items: list[KPIItem]
    total: int


class KPIPulseSummary(BaseModel):
    total_kpis: int
    hitting_base: int
    missing_base: int
    no_actuals: int
    health_score: str  # percentage hitting base
