from typing import Annotated, Literal

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_governance,
    assert_can_manage_tenant_setup,
    assert_can_view_audit_log,
    assert_can_view_portfolio,
)
from app.domain.dashboard_config import DashboardConfigResponse, DashboardConfigUpdate
from app.services.admin import AdminService
from app.services.dashboard_config import DashboardConfigService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
)


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> AdminService:
    return AdminService(get_supabase_admin(), current_user.tenant_id, current_user.id)


def _dashboard_svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> DashboardConfigService:
    return DashboardConfigService(get_supabase_admin(), str(current_user.tenant_id))


class PortfolioCleanupRequest(BaseModel):
    confirm_slug: str = Field(..., min_length=2, max_length=80)


class MeetingBulkCleanupRequest(BaseModel):
    meeting_ids: list[str] = Field(..., min_length=1, max_length=100)
    confirm_phrase: str = Field(..., min_length=1, max_length=80)


class StrategicParameterReferenceResetRequest(BaseModel):
    parameter_type: Literal["market", "theme", "tag"]
    value: str = Field(..., min_length=1, max_length=300)


@router.get("/settings")
async def get_settings(svc: Annotated[AdminService, Depends(_svc)]) -> dict[str, object]:
    """Get organization settings."""
    return svc.get_settings()


@router.get("/billing")
async def get_billing_status(svc: Annotated[AdminService, Depends(_svc)]) -> dict[str, object]:
    """Get tenant subscription and seat status."""
    return svc.get_billing_status()


@router.get("/launch-readiness")
async def get_launch_readiness(svc: Annotated[AdminService, Depends(_svc)]) -> dict[str, object]:
    """Get launch readiness checks for the tenant and runtime."""
    return svc.get_launch_readiness()


@router.get("/setup-status")
async def get_setup_status(svc: Annotated[AdminService, Depends(_svc)]) -> dict[str, object]:
    """Get first-run tenant setup checklist status."""
    return svc.get_setup_status()


@router.get("/dashboard-configuration", response_model=DashboardConfigResponse)
async def get_dashboard_configuration(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardConfigService, Depends(_dashboard_svc)],
) -> DashboardConfigResponse:
    """Get tenant dashboard menu configuration."""
    assert_can_view_portfolio(current_user)
    return svc.get_configuration()


@router.put("/dashboard-configuration", response_model=DashboardConfigResponse)
async def update_dashboard_configuration(
    body: DashboardConfigUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[DashboardConfigService, Depends(_dashboard_svc)],
) -> DashboardConfigResponse:
    """Update tenant dashboard menu configuration."""
    assert_can_manage_tenant_setup(current_user)
    return svc.update_configuration(body)


@router.get("/portfolio-cleanup-preview")
async def get_portfolio_cleanup_preview(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Preview tenant-scoped portfolio rows that a tenant admin can delete."""
    assert_can_manage_tenant_setup(current_user)
    return svc.get_portfolio_cleanup_preview()


@router.delete("/portfolio-cleanup")
async def delete_portfolio_data(
    body: PortfolioCleanupRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Delete current-tenant portfolio data while preserving tenant account records."""
    assert_can_manage_tenant_setup(current_user)
    return svc.delete_portfolio_data(body.confirm_slug)


@router.post("/portfolio-cleanup/delete")
async def delete_portfolio_data_action(
    body: PortfolioCleanupRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Delete current-tenant portfolio data via an action endpoint for browser clients."""
    assert_can_manage_tenant_setup(current_user)
    return svc.delete_portfolio_data(body.confirm_slug)


@router.get("/meeting-cleanup-candidates")
async def list_meeting_cleanup_candidates(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """List current-tenant meeting series available for selective cleanup."""
    assert_can_manage_tenant_setup(current_user)
    return svc.list_meeting_cleanup_candidates()


@router.post("/meeting-cleanup/delete")
async def delete_selected_meetings(
    body: MeetingBulkCleanupRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Delete selected current-tenant meeting series and dependent meeting data."""
    assert_can_manage_tenant_setup(current_user)
    return svc.delete_selected_meetings(body.meeting_ids, body.confirm_phrase)


@router.put("/settings")
async def update_settings(
    body: dict[str, object],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Update organization settings."""
    assert_can_manage_tenant_setup(current_user)
    return svc.update_settings(body)


@router.post("/strategic-parameters/reset-references")
async def reset_strategic_parameter_references(
    body: StrategicParameterReferenceResetRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Clear initiative references before deleting a configured strategic parameter."""
    assert_can_manage_tenant_setup(current_user)
    return svc.reset_strategic_parameter_references(body.parameter_type, body.value)


@router.get("/gate-criteria")
async def list_gate_criteria(
    svc: Annotated[AdminService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    gate_number: int | None = None,
) -> dict[str, object]:
    """List gate criteria."""
    assert_can_view_portfolio(current_user)
    return svc.list_gate_criteria(gate_number)


@router.post("/gate-criteria")
async def upsert_gate_criterion(
    body: dict[str, object],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Add or update a gate criterion."""
    assert_can_manage_governance(current_user)
    return svc.upsert_gate_criterion(body)


@router.delete("/gate-criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gate_criterion(
    criterion_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[AdminService, Depends(_svc)],
) -> None:
    """Delete a gate criterion."""
    assert_can_manage_governance(current_user)
    svc.delete_gate_criterion(criterion_id)
    return None


@router.get("/audit-logs")
async def list_audit_logs(
    svc: Annotated[AdminService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    limit: int = 100,
) -> dict[str, object]:
    """List audit logs."""
    assert_can_view_audit_log(current_user)
    return svc.list_audit_logs(limit)
