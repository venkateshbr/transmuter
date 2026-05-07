from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.database import get_supabase_admin
from app.services.admin import AdminService

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_role("transformation_office"))],
)


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> AdminService:
    return AdminService(get_supabase_admin(), current_user.tenant_id, current_user.id)


class PortfolioCleanupRequest(BaseModel):
    confirm_slug: str = Field(..., min_length=2, max_length=80)


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


@router.get("/portfolio-cleanup-preview")
async def get_portfolio_cleanup_preview(
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Preview tenant-scoped portfolio rows that a tenant admin can delete."""
    return svc.get_portfolio_cleanup_preview()


@router.delete("/portfolio-cleanup")
async def delete_portfolio_data(
    body: PortfolioCleanupRequest,
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Delete current-tenant portfolio data while preserving tenant account records."""
    return svc.delete_portfolio_data(body.confirm_slug)


@router.put("/settings")
async def update_settings(
    body: dict[str, object],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Update organization settings."""
    return svc.update_settings(body)


@router.get("/gate-criteria")
async def list_gate_criteria(
    svc: Annotated[AdminService, Depends(_svc)],
    gate_number: int | None = None,
) -> dict[str, object]:
    """List gate criteria."""
    return svc.list_gate_criteria(gate_number)


@router.post("/gate-criteria")
async def upsert_gate_criterion(
    body: dict[str, object],
    svc: Annotated[AdminService, Depends(_svc)],
) -> dict[str, object]:
    """Add or update a gate criterion."""
    return svc.upsert_gate_criterion(body)


@router.delete("/gate-criteria/{criterion_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_gate_criterion(
    criterion_id: str,
    svc: Annotated[AdminService, Depends(_svc)],
) -> None:
    """Delete a gate criterion."""
    svc.delete_gate_criterion(criterion_id)
    return None


@router.get("/audit-logs")
async def list_audit_logs(
    svc: Annotated[AdminService, Depends(_svc)],
    limit: int = 100,
) -> dict[str, object]:
    """List audit logs."""
    return svc.list_audit_logs(limit)
