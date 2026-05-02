"""Risk router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.risks import (
    RiskCreate,
    RiskHeatmapResponse,
    RiskItem,
    RiskListResponse,
    RiskUpdate,
)
from app.services.risk import RiskService

router = APIRouter(tags=["risks"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> RiskService:
    return RiskService(
        get_supabase_admin(), current_user.tenant_id,
    )


# ── Portfolio Risks ──────────────────────────────────────────────────

@router.get(
    "/portfolio/risks",
    response_model=RiskListResponse,
)
async def list_portfolio_risks(
    svc: Annotated[RiskService, Depends(_svc)],
    status: str | None = Query(None),
    type: str | None = Query(None),
    rating: str | None = Query(None),
) -> RiskListResponse:
    return svc.list_portfolio_risks(status=status, type=type, rating=rating)


@router.get(
    "/portfolio/risks/heatmap",
    response_model=RiskHeatmapResponse,
)
async def get_risk_heatmap(
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskHeatmapResponse:
    return svc.get_heatmap()


# ── Initiative Risks ─────────────────────────────────────────────────

@router.get(
    "/initiatives/{initiative_id}/risks",
    response_model=RiskListResponse,
)
async def list_initiative_risks(
    initiative_id: str,
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskListResponse:
    return svc.list_risks(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/risks",
    response_model=RiskItem,
    status_code=201,
)
async def create_risk(
    initiative_id: str,
    body: RiskCreate,
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskItem:
    return svc.create_risk(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/risks/{risk_id}",
    response_model=RiskItem,
)
async def update_risk(
    risk_id: str,
    body: RiskUpdate,
    svc: Annotated[RiskService, Depends(_svc)],
) -> RiskItem:
    return svc.update_risk(risk_id, body)


@router.delete(
    "/initiatives/{initiative_id}/risks/{risk_id}",
    status_code=204,
)
async def delete_risk(
    risk_id: str,
    svc: Annotated[RiskService, Depends(_svc)],
) -> None:
    svc.delete_risk(risk_id)
