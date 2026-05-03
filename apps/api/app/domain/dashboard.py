from pydantic import BaseModel
from typing import Any

class DashboardSummary(BaseModel):
    total_initiatives: int
    at_risk: int
    pending_approvals: int

class PressureInfo(BaseModel):
    score: float
    label: str

class DashboardResponse(BaseModel):
    summary: DashboardSummary
    pipeline_by_stage: dict[str, int]
    rag_breakdown: dict[str, int]
    my_milestones: list[dict[str, Any]]
    portfolio_pressure: PressureInfo
    risk_heatmap: dict[str, int]
    my_actions: list[dict[str, Any]] = []
    kpi_pulse: dict[str, Any] = {}
    value_bridge: dict[str, str] = {}
    recent_activity: list[dict[str, Any]] = []
    available_filters: dict[str, list[dict[str, Any]]] = {}
