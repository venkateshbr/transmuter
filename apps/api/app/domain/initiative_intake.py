"""Initiative intake contracts for AI-guided creation and workbook import."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.financials import CostLineCreate, FinancialEntryUpdate
from app.domain.initiatives import InitiativeCreate
from app.domain.kpis import KPICreate, KPIEntryUpsert
from app.domain.milestones import MilestoneCreate
from app.domain.risks import RiskCreate


class WorkbookValidationError(BaseModel):
    sheet: str
    row: int | None = None
    column: str | None = None
    message: str


class KPIWorkbookItem(KPICreate):
    entries: list[KPIEntryUpsert] = Field(default_factory=list)


class InitiativeWorkbookData(BaseModel):
    overview: InitiativeCreate
    financial_entries: list[FinancialEntryUpdate] = Field(default_factory=list)
    cost_lines: list[CostLineCreate] = Field(default_factory=list)
    kpis: list[KPIWorkbookItem] = Field(default_factory=list)
    risks: list[RiskCreate] = Field(default_factory=list)
    milestones: list[MilestoneCreate] = Field(default_factory=list)
    validation_errors: list[WorkbookValidationError] = Field(default_factory=list)


class InitiativeWorkbookPreview(BaseModel):
    name: str
    country: str | None = None
    priority: str = "medium"
    overview: InitiativeCreate
    counts: dict[str, int]
    validation_errors: list[WorkbookValidationError] = Field(default_factory=list)


class IntakeSuggestionState(BaseModel):
    accepted: bool = True
    note: str | None = None


class SuggestedFinancialEntry(FinancialEntryUpdate, IntakeSuggestionState):
    pass


class SuggestedCostLine(CostLineCreate, IntakeSuggestionState):
    pass


class SuggestedKPI(KPICreate, IntakeSuggestionState):
    entries: list[KPIEntryUpsert] = Field(default_factory=list)


class SuggestedRisk(RiskCreate, IntakeSuggestionState):
    pass


class SuggestedMilestone(MilestoneCreate, IntakeSuggestionState):
    pass


class InitiativeIntakeRequest(BaseModel):
    initiative: InitiativeCreate
    conversation: list[str] = Field(default_factory=list)


class InitiativeIntakeSuggestions(BaseModel):
    trace_id: str
    trace_url: str | None = None
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    financial_entries: list[SuggestedFinancialEntry] = Field(default_factory=list)
    cost_lines: list[SuggestedCostLine] = Field(default_factory=list)
    kpis: list[SuggestedKPI] = Field(default_factory=list)
    risks: list[SuggestedRisk] = Field(default_factory=list)
    milestones: list[SuggestedMilestone] = Field(default_factory=list)


class InitiativeIntakeCreate(BaseModel):
    initiative: InitiativeCreate
    suggestions: InitiativeIntakeSuggestions | None = None
