from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin, get_supabase_request_client
from app.domain.dashboard import DashboardResponse
from app.domain.dashboard_config import DashboardConfigResponse
from app.repositories.dashboard import DashboardRepository
from app.services.dashboard import DashboardService
from app.services.dashboard_config import DashboardConfigService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> DashboardService:
    repo = DashboardRepository(client, current_user.tenant_id)
    return DashboardService(repo)


def _config_svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DashboardConfigService:
    return DashboardConfigService(get_supabase_admin(), str(current_user.tenant_id))


@router.get("/configuration", response_model=DashboardConfigResponse)
async def get_dashboard_configuration(
    svc: Annotated[DashboardConfigService, Depends(_config_svc)],
) -> DashboardConfigResponse:
    """Get enabled dashboard registry for current tenant navigation."""
    return svc.get_configuration()


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = None,
    workstream_id: str | None = None,
    rag_status: str | None = None,
    priority: str | None = None,
    tag: str | None = None,
    target_year: int | None = None,
):
    """Get aggregated dashboard data for the current user."""
    return svc.get_dashboard_data(
        user_id=current_user.id,
        role=current_user.role,
        business_unit_id=business_unit_id,
        workstream_id=workstream_id,
        rag_status=rag_status,
        priority=priority,
        tag=tag,
        target_year=target_year,
    )


@router.get("/executive-summary.pdf")
async def get_executive_summary_pdf(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = None,
    workstream_id: str | None = None,
    rag_status: str | None = None,
    priority: str | None = None,
    tag: str | None = None,
    target_year: int | None = None,
) -> Response:
    content = svc.generate_executive_summary_pdf(
        user_id=current_user.id,
        role=current_user.role,
        business_unit_id=business_unit_id,
        workstream_id=workstream_id,
        rag_status=rag_status,
        priority=priority,
        tag=tag,
        target_year=target_year,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="transmuter-executive-summary.pdf"'},
    )
