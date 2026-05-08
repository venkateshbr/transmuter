"""Financial router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import Response

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.financials import (
    BreakEvenResponse,
    CostLineCreate,
    CostLineItem,
    CostLineListResponse,
    CostLineUpdate,
    FinancialCellAssumption,
    FinancialCellAssumptionCreate,
    FinancialCellAssumptionListResponse,
    FinancialCellAssumptionUpdate,
    FinancialGridResponse,
    FinancialGridUpdate,
    FinancialScenario,
    ScenarioFinancialSummary,
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialGridResponse:
    """Return full financial grid (2026–2030, quarterly) for an initiative."""
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.get_financial_grid(initiative_id)


@router.put("/initiatives/{initiative_id}/financials", response_model=FinancialGridResponse)
async def update_financials(
    initiative_id: str,
    body: FinancialGridUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialGridResponse:
    """Upsert the full financial grid for an initiative."""
    assert_can_manage_initiatives(current_user)
    return svc.update_financial_grid(initiative_id, body)


@router.get("/initiatives/{initiative_id}/financials/export.xlsx")
async def export_financials_workbook(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> Response:
    """Export financial entries and cost lines as an XLSX workbook."""
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
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
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    file: UploadFile = File(...),
) -> FinancialGridResponse:
    """Import financial entries and cost lines from an XLSX workbook."""
    assert_can_manage_initiatives(current_user)
    return svc.import_workbook(initiative_id, await file.read())


# ── Cost Lines ────────────────────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineListResponse,
)
async def list_cost_lines(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineListResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_cost_lines(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/financials/cost-lines",
    response_model=CostLineItem,
    status_code=201,
)
async def create_cost_line(
    initiative_id: str,
    body: CostLineCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_cost_line(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    response_model=CostLineItem,
)
async def update_cost_line(
    initiative_id: str,
    cost_line_id: str,
    body: CostLineUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> CostLineItem:
    assert_can_manage_initiatives(current_user)
    return svc.update_cost_line(cost_line_id, body)


@router.delete(
    "/initiatives/{initiative_id}/financials/cost-lines/{cost_line_id}",
    status_code=204,
)
async def delete_cost_line(
    initiative_id: str,
    cost_line_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_cost_line(cost_line_id)


# ── Value Bridge ──────────────────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/financials/value-bridge",
    response_model=ValueBridgeResponse,
)
async def get_value_bridge(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ValueBridgeResponse:
    """Value Bridge for a single initiative."""
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.get_value_bridge(initiative_id)


@router.get(
    "/initiatives/{initiative_id}/financials/scenario-summary",
    response_model=ScenarioFinancialSummary,
)
async def get_scenario_summary(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    scenario: FinancialScenario = Query("base"),
) -> ScenarioFinancialSummary:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.get_scenario_summary(initiative_id, scenario)


@router.get(
    "/initiatives/{initiative_id}/financials/break-even",
    response_model=BreakEvenResponse,
)
async def get_break_even(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
    scenario: FinancialScenario = Query("base"),
) -> BreakEvenResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.get_break_even(initiative_id, scenario)


@router.get(
    "/initiatives/{initiative_id}/financials/assumptions",
    response_model=FinancialCellAssumptionListResponse,
)
async def list_cell_assumptions(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCellAssumptionListResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_cell_assumptions(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/financials/assumptions",
    response_model=FinancialCellAssumption,
    status_code=201,
)
async def upsert_cell_assumption(
    initiative_id: str,
    body: FinancialCellAssumptionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCellAssumption:
    assert_can_manage_initiatives(current_user)
    return svc.upsert_cell_assumption(initiative_id, body, current_user.id)


@router.put(
    "/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
    response_model=FinancialCellAssumption,
)
async def update_cell_assumption(
    initiative_id: str,
    assumption_id: str,
    body: FinancialCellAssumptionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> FinancialCellAssumption:
    assert_can_manage_initiatives(current_user)
    return svc.update_cell_assumption(assumption_id, body, current_user.id)


@router.delete(
    "/initiatives/{initiative_id}/financials/assumptions/{assumption_id}",
    status_code=204,
)
async def delete_cell_assumption(
    initiative_id: str,
    assumption_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_cell_assumption(assumption_id)


@router.get("/portfolio/value-bridge", response_model=ValueBridgeResponse)
async def get_portfolio_value_bridge(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[FinancialService, Depends(_svc)],
) -> ValueBridgeResponse:
    """Portfolio-level Value Bridge across all initiatives."""
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_value_bridge()
