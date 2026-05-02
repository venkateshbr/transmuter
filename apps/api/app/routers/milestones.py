"""Milestone router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.milestones import (
    ChecklistItem,
    ChecklistItemCreate,
    ChecklistToggle,
    DependencyCreate,
    DependencyItem,
    MilestoneCreate,
    MilestoneDetail,
    MilestoneListResponse,
    MilestoneUpdate,
)
from app.domain.pressure import MilestonePressureResult
from app.services.milestone import MilestoneService

router = APIRouter(tags=["milestones"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MilestoneService:
    return MilestoneService(
        get_supabase_admin(), current_user.tenant_id,
    )


# ── Milestone CRUD ───────────────────────────────────────────────────

@router.get(
    "/milestones",
    response_model=MilestoneListResponse,
)
async def list_all_milestones(
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneListResponse:
    """List all milestones across the portfolio."""
    return svc.list_all_milestones()


@router.get(
    "/initiatives/{initiative_id}/milestones",
    response_model=MilestoneListResponse,
)
async def list_milestones(
    initiative_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneListResponse:
    return svc.list_milestones(initiative_id)


@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneDetail,
)
async def get_milestone(
    milestone_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    return svc.get_milestone(milestone_id)


@router.post(
    "/initiatives/{initiative_id}/milestones",
    response_model=MilestoneDetail,
    status_code=201,
)
async def create_milestone(
    initiative_id: str,
    body: MilestoneCreate,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    return svc.create_milestone(initiative_id, body)


@router.put(
    "/milestones/{milestone_id}",
    response_model=MilestoneDetail,
)
async def update_milestone(
    milestone_id: str,
    body: MilestoneUpdate,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    return svc.update_milestone(milestone_id, body)


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    milestone_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    svc.delete_milestone(milestone_id)


# ── Checklist ────────────────────────────────────────────────────────

@router.post(
    "/milestones/{milestone_id}/checklist",
    response_model=ChecklistItem,
    status_code=201,
)
async def add_checklist_item(
    milestone_id: str,
    body: ChecklistItemCreate,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> ChecklistItem:
    return svc.add_checklist_item(milestone_id, body)


@router.put(
    "/milestones/{milestone_id}/checklist/{item_id}",
    response_model=ChecklistItem,
)
async def toggle_checklist(
    milestone_id: str,
    item_id: str,
    body: ChecklistToggle,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> ChecklistItem:
    return svc.toggle_checklist(
        milestone_id, item_id, body.completed,
    )


@router.delete(
    "/milestones/{milestone_id}/checklist/{item_id}",
    status_code=204,
)
async def delete_checklist_item(
    milestone_id: str,
    item_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    svc.delete_checklist_item(milestone_id, item_id)


# ── Dependencies ─────────────────────────────────────────────────────

@router.post(
    "/milestones/{milestone_id}/dependencies",
    response_model=DependencyItem,
    status_code=201,
)
async def add_dependency(
    milestone_id: str,
    body: DependencyCreate,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> DependencyItem:
    return svc.add_dependency(milestone_id, body)


@router.delete(
    "/milestones/{milestone_id}/dependencies/{dependency_id}",
    status_code=204,
)
async def delete_dependency(
    milestone_id: str,
    dependency_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    svc.delete_dependency(milestone_id, dependency_id)


# ── Pressure ─────────────────────────────────────────────────────────

@router.get(
    "/milestones/{milestone_id}/pressure",
    response_model=MilestonePressureResult,
)
async def get_pressure(
    milestone_id: str,
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestonePressureResult:
    return svc.get_pressure(milestone_id)
