"""Risk domain models — Pydantic v2 contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class RiskCreate(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)
    type: Literal["operational", "people", "financial", "technology"] | None = None
    impact: Literal["high", "medium", "low"] | None = None
    likelihood: Literal["high", "medium", "low"] | None = None
    status: Literal["open", "closed"] = "open"
    owner_id: str | None = None
    mitigation: str | None = None
    escalated: bool = False


class RiskUpdate(BaseModel):
    description: str | None = Field(None, min_length=1, max_length=1000)
    type: Literal["operational", "people", "financial", "technology"] | None = None
    impact: Literal["high", "medium", "low"] | None = None
    likelihood: Literal["high", "medium", "low"] | None = None
    status: Literal["open", "closed"] | None = None
    owner_id: str | None = None
    mitigation: str | None = None
    escalated: bool | None = None


class RiskItem(BaseModel):
    id: str
    initiative_id: str
    description: str
    type: str | None = None
    impact: str | None = None
    likelihood: str | None = None
    rating: str | None = None
    status: str
    owner_id: str | None = None
    owner_name: str | None = None
    mitigation: str | None = None
    escalated: bool
    created_at: str | None = None
    updated_at: str | None = None


class RiskListResponse(BaseModel):
    items: list[RiskItem]
    total: int


class RiskHeatmapCell(BaseModel):
    impact: str
    likelihood: str
    count: int


class RiskHeatmapResponse(BaseModel):
    cells: list[RiskHeatmapCell]
    total_open_risks: int
