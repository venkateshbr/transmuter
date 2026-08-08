"""Milestone domain models — Pydantic v2 contracts."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

MilestoneDependencyType = Literal[
    "finish_to_start",
    "start_to_start",
    "finish_to_finish",
    "start_to_finish",
]


class MilestoneCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    owner_id: str | None = None
    priority: str = "medium"
    planned_start: str | None = None
    planned_end: str | None = None

    @model_validator(mode="after")
    def validate_date_order(self) -> MilestoneCreate:
        if self.planned_start and self.planned_end and self.planned_start > self.planned_end:
            raise ValueError("planned_start must be on or before planned_end")
        return self


class MilestoneUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    owner_id: str | None = None
    priority: str | None = None
    status: str | None = None
    sort_order: int | None = None
    planned_start: str | None = None
    actual_start: str | None = None
    planned_end: str | None = None
    actual_end: str | None = None


class MilestoneItem(BaseModel):
    id: str
    initiative_id: str
    initiative_name: str | None = None
    name: str
    description: str | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    priority: str
    status: str
    sort_order: int
    planned_start: str | None = None
    actual_start: str | None = None
    planned_end: str | None = None
    actual_end: str | None = None
    pressure_score: str | None = None
    pressure_level: str | None = None
    checklist_total: int = 0
    checklist_done: int = 0
    dependency_count: int = 0


class MilestoneListResponse(BaseModel):
    items: list[MilestoneItem]
    total: int


class PortfolioMilestoneStats(BaseModel):
    total: int
    not_started: int
    on_track: int
    at_risk: int
    complete: int
    overdue: int


class PortfolioMilestoneResponse(BaseModel):
    stats: PortfolioMilestoneStats
    items: list[MilestoneItem]
    total: int


class MilestoneDetail(MilestoneItem):
    pressure_blast_radius: str | None = None
    pressure_dep_urgency: str | None = None
    pressure_cluster: str | None = None
    pressure_slack: str | None = None
    pressure_checklist: str | None = None
    pressure_self_status: str | None = None
    checklist: list[ChecklistItem] = []
    dependencies: list[DependencyItem] = []
    created_at: str | None = None
    updated_at: str | None = None


class ChecklistItemCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    sort_order: int = 0


class ChecklistItem(BaseModel):
    id: str
    milestone_id: str
    text: str
    completed: bool = False
    sort_order: int = 0


class ChecklistToggle(BaseModel):
    completed: bool


class DependencyCreate(BaseModel):
    upstream_milestone_id: str
    dependency_type: MilestoneDependencyType = "finish_to_start"
    lag_days: int = Field(0, ge=-3650, le=3650)


class DependencyItem(BaseModel):
    id: str
    upstream_milestone_id: str
    upstream_name: str | None = None
    downstream_milestone_id: str
    downstream_name: str | None = None
    dependency_type: MilestoneDependencyType = "finish_to_start"
    lag_days: int = 0


class MilestoneSummary(BaseModel):
    id: str
    name: str
    initiative_code: str | None = None


class DependencyResponse(BaseModel):
    id: str
    upstream: MilestoneSummary
    downstream: MilestoneSummary
    status: Literal["blocking", "at_risk", "resolved", "on_track"] = "on_track"
    upstream_status: str | None = None
    upstream_planned_end: str | None = None
    upstream_pressure_score: str | None = None
    downstream_status: str | None = None
    dependency_type: MilestoneDependencyType = "finish_to_start"
    lag_days: int = 0


class DependencyStats(BaseModel):
    total: int = 0
    blocking: int = 0
    at_risk: int = 0
    resolved: int = 0
    on_track: int = 0


class DependencyGraphNode(BaseModel):
    id: str
    name: str
    initiative_code: str | None = None
    status: str | None = None


class DependencyGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    status: Literal["blocking", "at_risk", "resolved", "on_track"] = "on_track"
    dependency_type: MilestoneDependencyType = "finish_to_start"
    lag_days: int = 0


class DependencyListResponse(BaseModel):
    items: list[DependencyResponse]
    total: int
    stats: DependencyStats = Field(default_factory=DependencyStats)
    nodes: list[DependencyGraphNode] = []
    edges: list[DependencyGraphEdge] = []


class RoadmapRange(BaseModel):
    earliest_start: str | None = None
    latest_end: str | None = None


class RoadmapInitiative(BaseModel):
    id: str
    name: str
    initiative_code: str | None = None
    workstream_id: str | None = None
    workstream_name: str | None = None


class RoadmapMilestone(MilestoneItem):
    initiative_code: str | None = None
    workstream_id: str | None = None
    workstream_name: str | None = None


class RoadmapStats(BaseModel):
    milestones: int = 0
    initiatives: int = 0
    dependencies: int = 0
    blocking_links: int = 0
    missing_dates: int = 0


class PortfolioRoadmapResponse(BaseModel):
    range: RoadmapRange
    initiatives: list[RoadmapInitiative]
    milestones: list[RoadmapMilestone]
    dependencies: list[DependencyGraphEdge]
    stats: RoadmapStats
