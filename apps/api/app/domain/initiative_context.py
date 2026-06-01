"""Initiative context pull contracts for AI skills."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CompletedMilestoneContext(BaseModel):
    name: str
    completed_at: str | None = None


class MilestonesContextSummary(BaseModel):
    total: int = 0
    complete: int = 0
    overdue: int = 0
    at_risk: int = 0
    completed_this_period: list[CompletedMilestoneContext] = Field(default_factory=list)


class KPIContextItem(BaseModel):
    name: str
    target_base: str | None = None
    latest_actual: str | None = None
    on_track: bool = False


class KPIsContextSummary(BaseModel):
    kpis: list[KPIContextItem] = Field(default_factory=list)


class NewRiskContext(BaseModel):
    description: str


class RisksContextSummary(BaseModel):
    open_high: int = 0
    open_medium: int = 0
    new_this_period: list[NewRiskContext] = Field(default_factory=list)


class FinancialsContextSummary(BaseModel):
    revenue_plan: str = "0.0000"
    revenue_actual: str = "0.0000"
    costs_plan: str = "0.0000"
    costs_actual: str = "0.0000"


class LastStatusUpdateContext(BaseModel):
    rag_status: str
    submitted_at: str | None = None
    summary: str


class InitiativeContextPullResult(BaseModel):
    initiative_id: str
    period_start: str
    period_end: str
    milestones_summary: MilestonesContextSummary
    kpis_summary: KPIsContextSummary
    risks_summary: RisksContextSummary
    financials_summary: FinancialsContextSummary
    last_update: LastStatusUpdateContext | None = None
    sources: list[str] = Field(default_factory=list)
