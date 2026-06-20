"""Executive Control Tower router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.executive_control import (
    AllocationPreviewRequest,
    AllocationPreviewResponse,
    AllocationRuleCreate,
    AllocationRuleItem,
    AllocationRuleUpdate,
    AllocationRunCreate,
    AllocationRunItem,
    AllocationTargetItem,
    AllocationTargetUpsert,
    AllocationWeightItem,
    AllocationWeightUpsert,
    InitiativeDependencyCreate,
    InitiativeDependencyItem,
    InitiativeDependencyListResponse,
    InitiativeDependencyUpdate,
    ReportFilterParams,
    ReportResponse,
    SharedCostAllocationItem,
    SharedCostConfigResponse,
    SharedCostPoolCreate,
    SharedCostPoolItem,
    SharedCostPoolListResponse,
    SharedCostPoolPeriodItem,
    SharedCostPoolPeriodUpsert,
    SharedCostPoolUpdate,
    SharedCostReportingSettings,
    ValueRealizationNoteCreate,
    ValueRealizationNoteItem,
)
from app.services.executive_control import ExecutiveControlService

router = APIRouter(tags=["executive-control"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> ExecutiveControlService:
    return ExecutiveControlService(client, current_user.tenant_id)


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
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> InitiativeDependencyListResponse:
    assert_can_view_initiative(client, current_user, initiative_id)
    return svc.list_dependencies(current_user, initiative_id=initiative_id)


@router.get("/shared-costs/config", response_model=SharedCostConfigResponse)
async def shared_cost_config(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostConfigResponse:
    assert_can_view_portfolio(current_user)
    return svc.shared_cost_config()


@router.get("/shared-costs/reporting-settings", response_model=SharedCostReportingSettings)
async def get_shared_cost_reporting_settings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostReportingSettings:
    assert_can_view_portfolio(current_user)
    return svc.get_reporting_settings()


@router.put("/shared-costs/reporting-settings", response_model=SharedCostReportingSettings)
async def update_shared_cost_reporting_settings(
    body: SharedCostReportingSettings,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> SharedCostReportingSettings:
    assert_can_manage_initiatives(current_user)
    return svc.update_reporting_settings(body)


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


@router.get("/shared-cost-pools/{pool_id}/periods", response_model=list[SharedCostPoolPeriodItem])
async def list_shared_cost_pool_periods(
    pool_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[SharedCostPoolPeriodItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_pool_periods(pool_id)


@router.put("/shared-cost-pools/{pool_id}/periods", response_model=list[SharedCostPoolPeriodItem])
async def replace_shared_cost_pool_periods(
    pool_id: str,
    body: list[SharedCostPoolPeriodUpsert],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[SharedCostPoolPeriodItem]:
    assert_can_manage_initiatives(current_user)
    return svc.replace_pool_periods(pool_id, body)


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


@router.put(
    "/shared-cost-pools/{pool_id}/allocation-rules/{rule_id}/targets",
    response_model=list[AllocationTargetItem],
)
async def replace_allocation_rule_targets(
    pool_id: str,
    rule_id: str,
    body: list[AllocationTargetUpsert],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[AllocationTargetItem]:
    assert_can_manage_initiatives(current_user)
    return svc.replace_rule_targets(pool_id, rule_id, body)


@router.put(
    "/shared-cost-pools/{pool_id}/allocation-rules/{rule_id}/weights",
    response_model=list[AllocationWeightItem],
)
async def replace_allocation_rule_weights(
    pool_id: str,
    rule_id: str,
    body: list[AllocationWeightUpsert],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[AllocationWeightItem]:
    assert_can_manage_initiatives(current_user)
    return svc.replace_rule_weights(pool_id, rule_id, body)


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


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-runs/preview",
    response_model=AllocationPreviewResponse,
)
async def preview_allocation_run(
    pool_id: str,
    body: AllocationPreviewRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationPreviewResponse:
    assert_can_view_portfolio(current_user)
    return svc.preview_allocation_run(pool_id, body)


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-runs/{run_id}/approve",
    response_model=AllocationRunItem,
)
async def approve_allocation_run(
    pool_id: str,
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRunItem:
    assert_can_manage_initiatives(current_user)
    return svc.approve_run(pool_id, run_id, current_user)


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-runs/{run_id}/lock",
    response_model=AllocationRunItem,
)
async def lock_allocation_run(
    pool_id: str,
    run_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRunItem:
    assert_can_manage_initiatives(current_user)
    return svc.approve_run(pool_id, run_id, current_user, lock=True)


@router.post(
    "/shared-cost-pools/{pool_id}/allocation-runs/{run_id}/void",
    response_model=AllocationRunItem,
)
async def void_allocation_run(
    pool_id: str,
    run_id: str,
    body: dict[str, str],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> AllocationRunItem:
    assert_can_manage_initiatives(current_user)
    return svc.void_run(pool_id, run_id, body.get("reason", ""), current_user)


@router.get("/shared-cost-allocations", response_model=list[SharedCostAllocationItem])
async def list_shared_cost_allocations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
) -> list[SharedCostAllocationItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_shared_cost_allocations()


@router.get(
    "/initiatives/{initiative_id}/value-realization-notes",
    response_model=list[ValueRealizationNoteItem],
)
async def list_value_realization_notes(
    initiative_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[ExecutiveControlService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> list[ValueRealizationNoteItem]:
    assert_can_view_initiative(client, current_user, initiative_id)
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
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> ValueRealizationNoteItem:
    assert_can_view_initiative(client, current_user, initiative_id)
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
