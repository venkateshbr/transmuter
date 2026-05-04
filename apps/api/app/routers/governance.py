"""Governance router — Stage gates & submissions."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_initiative,
    assert_can_view_portfolio,
)
from app.domain.governance import (
    GateCriteriaState,
    GateDecisionPatch,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
    PortfolioGovernanceResponse,
)
from app.services.governance import GovernanceService

router = APIRouter(tags=["governance"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> GovernanceService:
    return GovernanceService(
        get_supabase_admin(), current_user.tenant_id, current_user.id
    )


@router.get(
    "/initiatives/{id}/governance",
    response_model=GovernanceStatusResponse,
)
async def get_governance_status(
    id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GovernanceStatusResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, id)
    return svc.get_status(id)


@router.get(
    "/initiatives/{id}/gates",
    response_model=GovernanceStatusResponse,
)
async def get_initiative_gates(
    id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GovernanceStatusResponse:
    assert_can_view_initiative(get_supabase_admin(), current_user, id)
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
    "/initiatives/{id}/gates/{gate_number}/criteria",
    response_model=list[GateCriteriaState],
)
async def list_initiative_gate_criteria(
    id: str,
    gate_number: int,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[GateCriteriaState]:
    assert_can_view_initiative(get_supabase_admin(), current_user, id)
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
    assert_can_manage_initiatives(current_user)
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
    assert_can_manage_initiatives(current_user)
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
    assert_can_manage_initiatives(current_user)
    return svc.record_decision(submission_id, body)
