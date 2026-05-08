"""Dependencies router — global dependency management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import assert_can_view_portfolio
from app.domain.milestones import DependencyListResponse
from app.services.milestone import MilestoneService

router = APIRouter(tags=["dependencies"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MilestoneService:
    return MilestoneService(
        get_supabase_admin(),
        current_user.tenant_id,
    )


@router.get(
    "/dependencies",
    response_model=DependencyListResponse,
)
async def list_all_dependencies(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> DependencyListResponse:
    """List all milestone dependencies across the portfolio."""
    assert_can_view_portfolio(current_user)
    return svc.list_all_dependencies()


@router.get(
    "/portfolio/dependencies",
    response_model=DependencyListResponse,
)
async def list_portfolio_dependencies(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> DependencyListResponse:
    assert_can_view_portfolio(current_user)
    return svc.list_all_dependencies()
