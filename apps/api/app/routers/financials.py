"""Financial router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.financials import (
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialGridResponse,
    FinancialGridUpdate,
    ValueBridgeResponse,
)
from app.services.financial import FinancialService

router = APIRouter(tags=["financials"])


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> FinancialService:
    return FinancialService(get_supabase_admin(), current_user.tenant_id)


# ── Financial Grid ────────────────────────────────────────────────────────────

@router.get("/initiatives/{initiative_id}/financials", response_model=FinancialGridResponse)
async def get_financials(
    initiative_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialGridResponse:
    """Return full financial grid (2026–2030, quarterly) for an initiative."""
    return svc.get_financial_grid(initiative_id)


@router.put("/initiatives/{initiative_id}/financials", response_model=FinancialGridResponse)
async def update_financials(
    initiative_id: str,
    body: FinancialGridUpdate,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialGridResponse:
    """Upsert the full financial grid for an initiative."""
    return svc.update_financial_grid(initiative_id, body)


@router.get("/initiatives/{initiative_id}/financials/export.xlsx")
async def export_financials_workbook(
    initiative_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> Response:
    """Export financial entries and cost lines as an XLSX workbook."""
    workbook = svc.export_workbook(initiative_id)
    return Response(
        content=workbook,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": (
                f'attachment; filename="initiative-{initiative_id}-financials.xlsx"'
            )
        },
    )


@router.post(
    "/initiatives/{initiative_id}/financials/import.xlsx",
    response_model=FinancialGridResponse,
)
async def import_financials_workbook(
    initiative_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
    file: UploadFile = File(...),
) -> FinancialGridResponse:
    """Import financial entries and cost lines from an XLSX workbook."""
    return svc.import_workbook(initiative_id, await file.read())


# ── Cost Lines ────────────────────────────────────────────────────────────────

@router.get(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineListResponse,
)
async def list_cost_lines(
    initiative_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineListResponse:
    return svc.list_cost_lines(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineItem,
    status_code=201,
)
async def create_cost_line(
    initiative_id: str,
    body: CostLineCreate,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    return svc.create_cost_line(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    response_model=CostLineItem,
)
async def update_cost_line(
    initiative_id: str,
    cost_line_id: str,
    body: CostLineUpdate,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    return svc.update_cost_line(cost_line_id, body)


@router.delete(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    status_code=204,
)
async def delete_cost_line(
    initiative_id: str,
    cost_line_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    svc.delete_cost_line(cost_line_id)


# ── Value Bridge ──────────────────────────────────────────────────────────────

@router.get(
    "/initiatives/{initiative_id}/financials/value-bridge",
    response_model=ValueBridgeResponse,
)
async def get_value_bridge(
    initiative_id: str,
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ValueBridgeResponse:
    """Value Bridge for a single initiative."""
    return svc.get_value_bridge(initiative_id)


@router.get("/portfolio/value-bridge", response_model=ValueBridgeResponse)
async def get_portfolio_value_bridge(
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ValueBridgeResponse:
    """Portfolio-level Value Bridge across all initiatives."""
    return svc.get_portfolio_value_bridge()
