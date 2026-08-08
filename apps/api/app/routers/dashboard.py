from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials
from supabase import Client

from app.core.auth import CurrentUser, bearer, get_current_user
from app.core.database import get_supabase_admin, get_supabase_request_client, get_supabase_user
from app.domain.dashboard import DashboardResponse
from app.domain.dashboard_config import DashboardConfigResponse
from app.domain.dashboard_layout import (
    DashboardBreakpoint,
    DashboardKey,
    DashboardLayoutResponse,
    DashboardLayoutUpdate,
)
from app.repositories.dashboard import DashboardRepository
from app.services.dashboard import DashboardService
from app.services.dashboard_config import DashboardConfigService
from app.services.dashboard_layout import DashboardLayoutService

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
    if current_user.role == "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context is required",
        )
    return DashboardConfigService(get_supabase_admin(), str(current_user.tenant_id))


def _layout_svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> DashboardLayoutService:
    if current_user.role == "platform_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context is required",
        )
    return DashboardLayoutService(
        get_supabase_user(credentials.credentials),
        str(current_user.tenant_id),
        str(current_user.id),
        current_user.role,
    )


@router.get("/configuration", response_model=DashboardConfigResponse)
async def get_dashboard_configuration(
    svc: Annotated[DashboardConfigService, Depends(_config_svc)],
) -> DashboardConfigResponse:
    """Get enabled dashboard registry for current tenant navigation."""
    return svc.get_configuration()


@router.get("/{dashboard_key}/layout", response_model=DashboardLayoutResponse)
async def get_dashboard_layout(
    dashboard_key: DashboardKey,
    svc: Annotated[DashboardLayoutService, Depends(_layout_svc)],
    breakpoint: DashboardBreakpoint = "desktop",
) -> DashboardLayoutResponse:
    return svc.get_layout(dashboard_key, breakpoint)


@router.put("/{dashboard_key}/layout", response_model=DashboardLayoutResponse)
async def save_dashboard_layout(
    dashboard_key: DashboardKey,
    data: DashboardLayoutUpdate,
    svc: Annotated[DashboardLayoutService, Depends(_layout_svc)],
) -> DashboardLayoutResponse:
    return svc.save_layout(dashboard_key, data)


@router.delete("/{dashboard_key}/layout", response_model=DashboardLayoutResponse)
async def reset_dashboard_layout(
    dashboard_key: DashboardKey,
    svc: Annotated[DashboardLayoutService, Depends(_layout_svc)],
    breakpoint: DashboardBreakpoint = "desktop",
) -> DashboardLayoutResponse:
    return svc.reset_personal_layout(dashboard_key, breakpoint)


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
