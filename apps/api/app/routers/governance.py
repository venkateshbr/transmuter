"""Governance router — Stage gates & submissions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.governance import (
    GateCriteriaCreate,
    GateCriteriaItem,
    GateCriteriaState,
    GateCriteriaUpdate,
    GateDecisionPatch,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
    PortfolioGovernanceResponse,
    StageGateDefinition,
    StageGateDefinitionCreate,
    StageGateDefinitionUpdate,
)
from app.services.governance import GovernanceService

router = APIRouter(tags=["governance"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> GovernanceService:
    return GovernanceService(client, current_user.tenant_id, current_user.id, current_user.role)


@router.get(
    "/initiatives/{id}/governance",
    response_model=GovernanceStatusResponse,
)
async def get_governance_status(
    id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> GovernanceStatusResponse:
    assert_can_view_initiative(client, current_user, id)
    return svc.get_status(id)


@router.get(
    "/initiatives/{id}/gates",
    response_model=GovernanceStatusResponse,
)
async def get_initiative_gates(
    id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> GovernanceStatusResponse:
    assert_can_view_initiative(client, current_user, id)
    return svc.get_status(id)


@router.get(
    "/governance/criteria/{gate_number}",
    response_model=list[GateCriteriaState],
)
async def list_gate_criteria(
    gate_number: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[GateCriteriaState]:
    assert_can_view_portfolio(current_user)
    return svc.list_criteria(gate_number)


@router.get(
    "/governance/stage-gates",
    response_model=list[StageGateDefinition],
)
async def list_tenant_stage_gate_definitions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[StageGateDefinition]:
    assert_can_view_portfolio(current_user)
    return svc.list_gate_definitions()


@router.get(
    "/admin/governance/stage-gates",
    response_model=list[StageGateDefinition],
)
async def list_stage_gate_definitions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[StageGateDefinition]:
    assert_can_view_portfolio(current_user)
    return svc.list_gate_definitions()


@router.post(
    "/admin/governance/stage-gates",
    response_model=StageGateDefinition,
    status_code=201,
)
async def create_stage_gate_definition(
    body: StageGateDefinitionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> StageGateDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.create_gate_definition(body)


@router.patch(
    "/admin/governance/stage-gates/{definition_id}",
    response_model=StageGateDefinition,
)
async def update_stage_gate_definition(
    definition_id: str,
    body: StageGateDefinitionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> StageGateDefinition:
    assert_can_manage_initiatives(current_user)
    return svc.update_gate_definition(definition_id, body)


@router.delete(
    "/admin/governance/stage-gates/{definition_id}",
    status_code=204,
)
async def delete_stage_gate_definition(
    definition_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_gate_definition(definition_id)


@router.get(
    "/admin/governance/gate-criteria",
    response_model=list[GateCriteriaItem],
)
async def list_gate_criteria_config(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
    gate_number: int | None = None,
) -> list[GateCriteriaItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_gate_criteria_config(gate_number)


@router.post(
    "/admin/governance/gate-criteria",
    response_model=GateCriteriaItem,
    status_code=201,
)
async def create_gate_criterion_config(
    body: GateCriteriaCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GateCriteriaItem:
    assert_can_manage_initiatives(current_user)
    return svc.create_gate_criterion(body)


@router.patch(
    "/admin/governance/gate-criteria/{criterion_id}",
    response_model=GateCriteriaItem,
)
async def update_gate_criterion_config(
    criterion_id: str,
    body: GateCriteriaUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GateCriteriaItem:
    assert_can_manage_initiatives(current_user)
    return svc.update_gate_criterion(criterion_id, body)


@router.delete(
    "/admin/governance/gate-criteria/{criterion_id}",
    status_code=204,
)
async def delete_gate_criterion_config(
    criterion_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_gate_criterion(criterion_id)


@router.get(
    "/initiatives/{id}/gates/{gate_number}/criteria",
    response_model=list[GateCriteriaState],
)
async def list_initiative_gate_criteria(
    id: str,
    gate_number: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> list[GateCriteriaState]:
    assert_can_view_initiative(client, current_user, id)
    return svc.list_criteria(gate_number, id)


@router.post(
    "/initiatives/{id}/gates/{gate_number}/submit",
    response_model=GateSubmissionItem,
    status_code=201,
)
async def submit_gate(
    id: str,
    gate_number: int,
    body: GateSubmissionCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GateSubmissionItem:
    return svc.submit_gate(id, gate_number, body)


@router.get(
    "/governance/submissions",
    response_model=list[GateSubmissionItem],
)
async def list_submissions(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[GateSubmissionItem]:
    assert_can_view_portfolio(current_user)
    return svc.list_submissions()


@router.get(
    "/portfolio/governance",
    response_model=PortfolioGovernanceResponse,
)
async def get_portfolio_governance(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> PortfolioGovernanceResponse:
    assert_can_view_portfolio(current_user)
    return svc.get_portfolio_governance()


@router.patch(
    "/governance/submissions/{submission_id}/decide",
    response_model=GateSubmissionItem,
)
async def record_gate_decision(
    submission_id: str,
    body: GateDecisionPatch,
    svc: Annotated[GovernanceService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> GateSubmissionItem:
    return svc.record_decision(submission_id, body)


@router.post(
    "/gates/submissions/{submission_id}/decide",
    response_model=GateSubmissionItem,
)
async def post_gate_decision(
    submission_id: str,
    body: GateDecisionPatch,
    svc: Annotated[GovernanceService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> GateSubmissionItem:
    return svc.record_decision(submission_id, body)
