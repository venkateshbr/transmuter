"""Executive Control Tower router."""

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
from app.domain.executive_control import (
    AllocationRuleCreate,
    AllocationRuleItem,
    AllocationRuleUpdate,
    AllocationRunCreate,
    AllocationRunItem,
    InitiativeDependencyCreate,
    InitiativeDependencyItem,
    InitiativeDependencyListResponse,
    InitiativeDependencyUpdate,
    ReportFilterParams,
    ReportResponse,
    SharedCostPoolCreate,
    SharedCostPoolItem,
    SharedCostPoolListResponse,
    SharedCostPoolUpdate,
    ValueRealizationNoteCreate,
    ValueRealizationNoteItem,
)
from app.services.executive_control import ExecutiveControlService

router = APIRouter(tags=["executive-control"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> ExecutiveControlService:
    return ExecutiveControlService(get_supabase_admin(), current_user.tenant_id)


def _filters(
    business_unit_id: str | None = Query(None),
    workstream_id: str | None = Query(None),
    tag: str | None = Query(None),
    country: str | None = Query(None),
    owner_id: str | None = Query(None),
    rag_status: str | None = Query(None),
    stage: str | None = Query(None),
    target_year: int | None = Query(None),
) -> ReportFilterParams:
    return ReportFilterParams(
        business_unit_id=business_unit_id,
        workstream_id=workstream_id,
        tag=tag,
        country=country,
        owner_id=owner_id,
        rag_status=rag_status,
        stage=stage,
        target_year=target_year,
    )


@router.get("/initiative-dependencies", response_model=InitiativeDependencyListResponse)
async def list_initiative_dependencies(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
    filters: Annotated[ReportFilterParams, Depends(_filters)],
) -> InitiativeDependencyListResponse:
    return svc.list_dependencies(current_user, filters=filters)


@router.post("/initiative-dependencies", response_model=InitiativeDependencyItem, status_code=201)
async def create_initiative_dependency(
    body: InitiativeDependencyCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> InitiativeDependencyItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_dependency(body)


@router.patch("/initiative-dependencies/{dependency_id}", response_model=InitiativeDependencyItem)
async def update_initiative_dependency(
    dependency_id: str,
    body: InitiativeDependencyUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> InitiativeDependencyItem:
    return svc.update_dependency(dependency_id, body, current_user)


@router.delete("/initiative-dependencies/{dependency_id}", status_code=204)
async def delete_initiative_dependency(
    dependency_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_dependency(dependency_id)


@router.get(
    "/initiatives/{initiative_id}/dependencies",
    response_model=InitiativeDependencyListResponse,
)
async def list_dependencies_for_initiative(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> InitiativeDependencyListResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_dependencies(current_user, initiative_id=initiative_id)


@router.get("/shared-cost-pools", response_model=SharedCostPoolListResponse)
async def list_shared_cost_pools(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostPoolListResponse:
    return svc.list_pools(current_user)


@router.post("/shared-cost-pools", response_model=SharedCostPoolItem, status_code=201)
async def create_shared_cost_pool(
    body: SharedCostPoolCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostPoolItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_pool(body)


@router.patch("/shared-cost-pools/{pool_id}", response_model=SharedCostPoolItem)
async def update_shared_cost_pool(
    pool_id: str,
    body: SharedCostPoolUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostPoolItem:
    assert_can_manage_initiatives(current_user)
    return svc.update_pool(pool_id, body)


@router.get(
    "/shared-cost-pools/{pool_id}/allocation-rules", response_model=list[AllocationRuleItem]
)
async def list_allocation_rules(
    pool_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[AllocationRuleItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_rules(pool_id)


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-rules",
    response_model=AllocationRuleItem,
    status_code=201,
)
async def create_allocation_rule(
    pool_id: str,
    body: AllocationRuleCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRuleItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_rule(pool_id, body)


@router.patch(
    "/shared-cost-pools/{pool_id}/allocation-rules/{rule_id}", response_model=AllocationRuleItem
)
async def update_allocation_rule(
    pool_id: str,
    rule_id: str,
    body: AllocationRuleUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRuleItem:
    assert_can_manage_initiatives(current_user)
    return svc.update_rule(pool_id, rule_id, body)


@router.get("/shared-cost-pools/{pool_id}/allocation-runs", response_model=list[AllocationRunItem])
async def list_allocation_runs(
    pool_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[AllocationRunItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_runs(pool_id)


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-runs",
    response_model=AllocationRunItem,
    status_code=201,
)
async def create_allocation_run(
    pool_id: str,
    body: AllocationRunCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRunItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_allocation_run(pool_id, body, current_user)


@router.get(
    "/initiatives/{initiative_id}/value-realization-notes",
    response_model=list[ValueRealizationNoteItem],
)
async def list_value_realization_notes(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[ValueRealizationNoteItem]:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.list_value_notes(initiative_id, current_user)


@router.post(
    "/initiatives/{initiative_id}/value-realization-notes",
    response_model=ValueRealizationNoteItem,
    status_code=201,
)
async def create_value_realization_note(
    initiative_id: str,
    body: ValueRealizationNoteCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> ValueRealizationNoteItem:
    assert_can_view_initiative(get_supabase_admin(), current_user, initiative_id)
    return svc.create_value_note(initiative_id, body, current_user)


@router.get("/reports/owner-cockpit", response_model=ReportResponse)
async def owner_cockpit(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
    filters: Annotated[ReportFilterParams, Depends(_filters)],
) -> ReportResponse:
    return svc.owner_cockpit(current_user, filters)


@router.get("/reports/executive-control-tower", response_model=ReportResponse)
async def executive_control_tower(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
    filters: Annotated[ReportFilterParams, Depends(_filters)],
) -> ReportResponse:
    assert_can_view_portfolio(current_user)
    return svc.management_report(current_user, filters)


@router.get("/reports/investor-summary", response_model=ReportResponse)
async def investor_summary(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
    filters: Annotated[ReportFilterParams, Depends(_filters)],
) -> ReportResponse:
    assert_can_view_portfolio(current_user)
    return svc.investor_report(current_user, filters)
