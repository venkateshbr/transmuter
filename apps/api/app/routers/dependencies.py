"""Dependencies router — global dependency management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.milestones import DependencyListResponse
from app.services.milestone import MilestoneService

router = APIRouter(tags=["dependencies"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> MilestoneService:
    return MilestoneService(
        get_supabase_admin(), current_user.tenant_id,
    )


@router.get(
    "/dependencies",
    response_model=DependencyListResponse,
)
async def list_all_dependencies(
    svc: Annotated[MilestoneService, Depends(_svc)],
) -> DependencyListResponse:
    """List all milestone dependencies across the portfolio."""
    return svc.list_all_dependencies()
