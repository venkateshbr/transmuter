"""Milestone router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_milestone,
    assert_can_view_portfolio,
)
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
    PortfolioMilestoneResponse,
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneListResponse:
    """List all milestones across the portfolio."""
    assert_can_view_portfolio(current_user)
    return svc.list_all_milestones()


@router.get(
    "/portfolio/milestones",
    response_model=PortfolioMilestoneResponse,
)
async def list_portfolio_milestones(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> PortfolioMilestoneResponse:
    assert_can_view_portfolio(current_user)
    return svc.list_portfolio_milestones()


@router.get(
    "/initiatives/{initiative_id}/milestones",
    response_model=MilestoneListResponse,
)
async def list_milestones(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneListResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_milestones(initiative_id)


@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneDetail,
)
async def get_milestone(
    milestone_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    assert_can_view_milestone(get_supabase_admin(), current_user, milestone_id)
    return svc.get_milestone(milestone_id)


@router.post(
    "/initiatives/{initiative_id}/milestones",
    response_model=MilestoneDetail,
    status_code=201,
)
async def create_milestone(
    initiative_id: str,
    body: MilestoneCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    assert_can_manage_initiatives(current_user)
    return svc.create_milestone(initiative_id, body)


@router.put(
    "/milestones/{milestone_id}",
    response_model=MilestoneDetail,
)
async def update_milestone(
    milestone_id: str,
    body: MilestoneUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestoneDetail:
    assert_can_manage_initiatives(current_user)
    return svc.update_milestone(milestone_id, body)


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_milestone(
    milestone_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> ChecklistItem:
    assert_can_manage_initiatives(current_user)
    return svc.add_checklist_item(milestone_id, body)


@router.put(
    "/milestones/{milestone_id}/checklist/{item_id}",
    response_model=ChecklistItem,
)
async def toggle_checklist(
    milestone_id: str,
    item_id: str,
    body: ChecklistToggle,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> ChecklistItem:
    assert_can_manage_initiatives(current_user)
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> DependencyItem:
    assert_can_manage_initiatives(current_user)
    return svc.add_dependency(milestone_id, body)


@router.delete(
    "/milestones/{milestone_id}/dependencies/{dependency_id}",
    status_code=204,
)
async def delete_dependency(
    milestone_id: str,
    dependency_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_dependency(milestone_id, dependency_id)


# ── Pressure ─────────────────────────────────────────────────────────

@router.get(
    "/milestones/{milestone_id}/pressure",
    response_model=MilestonePressureResult,
)
async def get_pressure(
    milestone_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> MilestonePressureResult:
    assert_can_view_milestone(get_supabase_admin(), current_user, milestone_id)
    return svc.get_pressure(milestone_id)
