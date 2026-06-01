"""Initiative intake contracts for AI-guided creation and workbook import."""

from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.core.agent_security import validate_agent_model_strings, validate_agent_text_list
from app.domain.financials import CostLineCreate, FinancialEntryUpdate
from app.domain.initiatives import InitiativeCreate, InitiativeType, Priority
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
    status_updates: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
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

    @field_validator("conversation")
    @classmethod
    def validate_conversation(cls, value: list[str]) -> list[str]:
        return validate_agent_text_list(value, "conversation")

    @model_validator(mode="after")
    def validate_agent_visible_fields(self) -> InitiativeIntakeRequest:
        validate_agent_model_strings(self.initiative.model_dump(mode="json"))
        return self


class InitiativeFieldExtractionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        validate_agent_model_strings({"text": value})
        return value


class InitiativeDraft(BaseModel):
    name: str | None = None
    type: InitiativeType | None = None
    priority: Priority | None = None
    workstream: str | None = None
    country: str | None = None
    summary: str | None = None
    value_logic: str | None = None
    planned_end: date | None = None
    dependencies: str | None = None


class InitiativeFieldExtractionResult(BaseModel):
    trace_id: str
    trace_url: str | None = None
    agent_status: Literal["generated", "deterministic_fallback"] = "deterministic_fallback"
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    input_tokens: int = 0
    output_tokens: int = 0
    draft: InitiativeDraft


class KPISuggestionRequest(BaseModel):
    initiative_type: InitiativeType | None = None
    initiative_name: str | None = Field(None, max_length=300)
    value_logic: str | None = Field(None, max_length=1000)


class KPISuggestion(KPICreate, IntakeSuggestionState):
    rationale: str


class KPISuggestionResult(BaseModel):
    suggestions: list[KPISuggestion] = Field(default_factory=list)


class RiskPatternScanRequest(BaseModel):
    initiative_draft: InitiativeDraft


class RiskPattern(RiskCreate, IntakeSuggestionState):
    rationale: str


class RiskPatternScanResult(BaseModel):
    risks: list[RiskPattern] = Field(default_factory=list)


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
