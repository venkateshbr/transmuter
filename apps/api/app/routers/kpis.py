"""KPI router — thin parse + respond layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.kpis import (
    KPICreate,
    KPIEntryItem,
    KPIEntryUpsert,
    KPIItem,
    KPIListResponse,
    KPIPulseSummary,
    KPIUpdate,
)
from app.services.kpi import KPIService

router = APIRouter(tags=["kpis"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> KPIService:
    return KPIService(
        get_supabase_admin(), current_user.tenant_id,
    )


# ── Pulse ────────────────────────────────────────────────────────────

@router.get(
    "/portfolio/kpi-pulse",
    response_model=KPIPulseSummary,
)
async def get_kpi_pulse(
    svc: Annotated[KPIService, Depends(_svc)],
) -> KPIPulseSummary:
    return svc.get_pulse_summary()


@router.get(
    "/portfolio/kpis",
    response_model=KPIListResponse,
)
async def list_all_kpis(
    svc: Annotated[KPIService, Depends(_svc)],
) -> KPIListResponse:
    return svc.list_all_kpis()


# ── KPI CRUD ─────────────────────────────────────────────────────────

@router.get(
    "/initiatives/{initiative_id}/kpis",
    response_model=KPIListResponse,
)
async def list_kpis(
    initiative_id: str,
    svc: Annotated[KPIService, Depends(_svc)],
) -> KPIListResponse:
    return svc.list_kpis(initiative_id)


@router.post(
    "/initiatives/{initiative_id}/kpis",
    response_model=KPIItem,
    status_code=201,
)
async def create_kpi(
    initiative_id: str,
    body: KPICreate,
    svc: Annotated[KPIService, Depends(_svc)],
) -> KPIItem:
    return svc.create_kpi(initiative_id, body)


@router.put(
    "/initiatives/{initiative_id}/kpis/{kpi_id}",
    response_model=KPIItem,
)
async def update_kpi(
    initiative_id: str,
    kpi_id: str,
    body: KPIUpdate,
    svc: Annotated[KPIService, Depends(_svc)],
) -> KPIItem:
    return svc.update_kpi(initiative_id, kpi_id, body)


@router.delete(
    "/initiatives/{initiative_id}/kpis/{kpi_id}",
    status_code=204,
)
async def delete_kpi(
    initiative_id: str,
    kpi_id: str,
    svc: Annotated[KPIService, Depends(_svc)],
) -> None:
    svc.delete_kpi(initiative_id, kpi_id)


# ── Entries ──────────────────────────────────────────────────────────

@router.put(
    "/initiatives/{initiative_id}/kpis/{kpi_id}/entries",
    response_model=list[KPIEntryItem],
)
async def upsert_entries(
    initiative_id: str,
    kpi_id: str,
    body: list[KPIEntryUpsert],
    svc: Annotated[KPIService, Depends(_svc)],
) -> list[KPIEntryItem]:
    return svc.upsert_entries(initiative_id, kpi_id, body)
