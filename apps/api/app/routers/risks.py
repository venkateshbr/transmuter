"""Risk router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.risks import (
    RiskCreate,
    RiskHeatmapResponse,
    RiskItem,
    RiskListResponse,
    RiskUpdate,
)
from app.jobs.portfolio_rag import enqueue_portfolio_rag_rebuild
from app.services.risk import RiskService

router = APIRouter(tags=["risks"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RiskService:
    return RiskService(
        get_supabase_admin(),
        current_user.tenant_id,
    )


# ── Portfolio Risks ──────────────────────────────────────────────────


@router.get(
    "/portfolio/risks",
    response_model=RiskListResponse,
)
async def list_portfolio_risks(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
    status: str | None = Query(None),
    type: str | None = Query(None),
    rating: str | None = Query(None),
) -> RiskListResponse:
    assert_can_view_portfolio(current_user)
    return svc.list_portfolio_risks(status=status, type=type, rating=rating)


@router.get(
    "/portfolio/risks/heatmap",
    response_model=RiskHeatmapResponse,
)
async def get_risk_heatmap(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskHeatmapResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_heatmap()


# ── Initiative Risks ─────────────────────────────────────────────────


@router.get(
    "/initiatives/{initiative_id}/risks",
    response_model=RiskListResponse,
)
async def list_initiative_risks(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskListResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_risks(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/risks",
    response_model=RiskItem,
    status_code=201,
)
async def create_risk(
    initiative_id: str,
    body: RiskCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskItem:
    assert_can_manage_initiatives(current_user)
    result = svc.create_risk(initiative_id, body)
    enqueue_portfolio_rag_rebuild(current_user.tenant_id)
    return result


@router.put(
    "/initiatives/{initiative_id}/risks/{risk_id}",
    response_model=RiskItem,
)
async def update_risk(
    initiative_id: str,
    risk_id: str,
    body: RiskUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskItem:
    assert_can_manage_initiatives(current_user)
    result = svc.update_risk(initiative_id, risk_id, body)
    enqueue_portfolio_rag_rebuild(current_user.tenant_id)
    return result


@router.delete(
    "/initiatives/{initiative_id}/risks/{risk_id}",
    status_code=204,
)
async def delete_risk(
    initiative_id: str,
    risk_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[RiskService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_risk(initiative_id, risk_id)
    enqueue_portfolio_rag_rebuild(current_user.tenant_id)
