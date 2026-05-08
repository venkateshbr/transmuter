from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.dashboard import DashboardResponse
from app.repositories.dashboard import DashboardRepository
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> DashboardService:
    repo = DashboardRepository(get_supabase_admin(), current_user.tenant_id)
    return DashboardService(repo)


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = None,
    workstream_id: str | None = None,
    rag_status: str | None = None,
    target_year: int | None = None,
):
    """Get aggregated dashboard data for the current user."""
    return svc.get_dashboard_data(
        user_id=current_user.id,
        role=current_user.role,
        business_unit_id=business_unit_id,
        workstream_id=workstream_id,
        rag_status=rag_status,
        target_year=target_year,
    )
