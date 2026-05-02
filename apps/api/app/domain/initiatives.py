"""Initiative domain models — Pydantic v2 contracts (Vastu #33)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.financials import FinancialSummary


# ── Enums ─────────────────────────────────────────────────────────────────────

InitiativeType = Literal[
    "revenue_growth", "cost_reduction", "cost_avoidance", "compliance", "capability_building"
]
ImpactType = Literal["recurring", "one_off"]
Priority = Literal["high", "medium", "low"]
RAGStatus = Literal["red", "amber", "green"]
Stage = Literal["scoping", "in_progress", "complete"]
InitiativeTag = Literal["automation", "offshoring", "commercial", "other"]


# ── Write models (request bodies) ─────────────────────────────────────────────

class InitiativeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    workstream_id: UUID | None = None
    owner_id: UUID | None = None
    group_owner_id: UUID | None = None
    type: InitiativeType | None = None
    impact_type: ImpactType | None = None
    theme: str | None = None
    country: str | None = None
    tag: InitiativeTag | None = None
    priority: Priority = "medium"
    summary: str | None = None
    value_logic: str | None = None
    dependencies_text: str | None = None
    planned_start: date | None = None
    planned_end: date | None = None


class InitiativeUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=300)
    workstream_id: UUID | None = None
    owner_id: UUID | None = None
    group_owner_id: UUID | None = None
    type: InitiativeType | None = None
    impact_type: ImpactType | None = None
    theme: str | None = None
    country: str | None = None
    tag: InitiativeTag | None = None
    priority: Priority | None = None
    rag_status: RAGStatus | None = None
    stage: Stage | None = None
    summary: str | None = None
    lessons_learned: str | None = None
    value_logic: str | None = None
    dependencies_text: str | None = None
    planned_start: date | None = None
    actual_start: date | None = None
    planned_end: date | None = None
    actual_end: date | None = None


# ── Read models (response bodies) ─────────────────────────────────────────────

class PressureBreakdown(BaseModel):
    schedule: Decimal | None = None
    milestone_health: Decimal | None = None
    risk_exposure: Decimal | None = None
    kpi_performance: Decimal | None = None
    financial: Decimal | None = None
    self_reported: Decimal | None = None


class InitiativeListItem(BaseModel):
    """Compact row for the pipeline list view."""
    id: UUID
    initiative_code: str
    name: str
    workstream_id: UUID | None
    workstream_name: str | None
    owner_id: UUID | None
    owner_name: str | None
    type: str | None
    priority: str
    rag_status: str
    stage: str
    country: str | None
    tag: str | None
    planned_value_base: str | None    # Decimal as string
    planned_value_high: str | None
    actual_value: str | None
    pressure_score: str | None
    archived_at: str | None


class InitiativeCounts(BaseModel):
    milestones_total: int = 0
    milestones_complete: int = 0
    milestones_overdue: int = 0
    kpis_total: int = 0
    risks_open: int = 0
    risks_high: int = 0
    status_updates_total: int = 0


class InitiativeTeamMember(BaseModel):
    id: UUID
    user_id: UUID
    role: str
    display_name: str | None = None
    email: str | None = None


class InitiativeKPIIndicator(BaseModel):
    id: UUID
    name: str
    unit: str | None = None
    health_status: str = "no_data"
    this_quarter_actual: str | None = None
    this_year_actual: str | None = None
    all_time_actual: str | None = None


class InitiativeDetail(BaseModel):
    """Full detail — used on the 8-tab initiative page."""
    id: UUID
    initiative_code: str
    name: str
    workstream_id: UUID | None
    workstream_name: str | None
    business_unit_id: UUID | None = None
    business_unit_name: str | None = None
    owner_id: UUID | None
    owner_name: str | None
    group_owner_id: UUID | None
    group_owner_name: str | None
    type: str | None
    impact_type: str | None
    theme: str | None
    country: str | None
    tag: str | None
    priority: str
    rag_status: str
    stage: str
    summary: str | None
    lessons_learned: str | None = None
    value_logic: str | None
    dependencies_text: str | None
    planned_start: date | None
    actual_start: date | None
    planned_end: date | None
    actual_end: date | None
    pressure_score: str | None
    pressure_breakdown: PressureBreakdown | None
    counts: InitiativeCounts
    team_members: list[InitiativeTeamMember] = []
    kpi_indicators: list[InitiativeKPIIndicator] = []
    financial_summary: FinancialSummary | None = None
    archived_at: str | None
    created_at: str
    updated_at: str


class InitiativeListResponse(BaseModel):
    items: list[InitiativeListItem]
    total: int
    page: int
    page_size: int
