from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.dashboard import DashboardResponse
from app.repositories.dashboard import DashboardRepository
from app.services.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> DashboardService:
    repo = DashboardRepository(get_supabase_admin(), current_user.tenant_id)
    return DashboardService(repo)


def _filter_params(
    business_unit_id: str | None,
    workstream_id: str | None,
    rag_status: str | None,
) -> dict[str, str | None]:
    return {
        "business_unit_id": business_unit_id,
        "workstream_id": workstream_id,
        "rag_status": rag_status,
    }


@router.get("/summary")
async def get_dashboard_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get dashboard summary cards."""
    return svc.get_dashboard_slice(
        "summary",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/pressure-gauge")
async def get_dashboard_pressure_gauge(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get portfolio pressure score."""
    return svc.get_dashboard_slice(
        "portfolio_pressure",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/rag-breakdown")
async def get_dashboard_rag_breakdown(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get initiative counts by RAG status."""
    return svc.get_dashboard_slice(
        "rag_breakdown",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/pipeline-by-stage")
async def get_dashboard_pipeline_by_stage(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get initiative counts and value ranges by stage."""
    return svc.get_pipeline_by_stage_detail(
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/pipeline-value")
async def get_dashboard_pipeline_value(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get portfolio planned and actual value totals."""
    return svc.get_dashboard_slice(
        "value_bridge",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/risk-heatmap")
async def get_dashboard_risk_heatmap(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get open risk counts by impact and likelihood."""
    return svc.get_dashboard_slice(
        "risk_heatmap",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/kpi-pulse")
async def get_dashboard_kpi_pulse(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get KPI health across scoped initiatives."""
    return svc.get_dashboard_slice(
        "kpi_pulse",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/value-bridge")
async def get_dashboard_value_bridge(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get portfolio benefits, costs, and net value."""
    return svc.get_dashboard_slice(
        "value_bridge",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/recent-activity")
async def get_dashboard_recent_activity(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get recent submitted status-update activity."""
    return svc.get_dashboard_slice(
        "recent_activity",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/my-milestones")
async def get_dashboard_my_milestones(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get milestones assigned to the current user."""
    return svc.get_dashboard_slice(
        "my_milestones",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/my-actions")
async def get_dashboard_my_actions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
):
    """Get open action items assigned to the current user."""
    return svc.get_dashboard_slice(
        "my_actions",
        user_id=current_user.id,
        role=current_user.role,
        **_filter_params(business_unit_id, workstream_id, rag_status),
    )


@router.get("/executive-summary.pdf")
async def get_executive_summary_pdf(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardService, Depends(_svc)],
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    rag_status: str | None = Query(None),
    target_year: int | None = Query(None),
) -> Response:
    """Generate a tenant-scoped executive summary PDF for the current dashboard view."""
    content = svc.generate_executive_summary_pdf(
        user_id=current_user.id,
        role=current_user.role,
        business_unit_id=business_unit_id,
        workstream_id=workstream_id,
        rag_status=rag_status,
        target_year=target_year,
    )
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="transmuter-executive-summary.pdf"'},
    )


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
