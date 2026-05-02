"""Governance router — Stage gates & submissions."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.governance import (
    GateDecisionPatch,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
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
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GovernanceStatusResponse:
    return svc.get_status(id)


@router.get(
    "/governance/criteria/{gate_number}",
    response_model=list[dict[str, Any]],
)
async def list_gate_criteria(
    gate_number: int,
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[dict[str, Any]]:
    return svc.list_criteria(gate_number)


@router.post(
    "/initiatives/{id}/gates/{gate_number}/submit",
    response_model=GateSubmissionItem,
    status_code=201,
)
async def submit_gate(
    id: str,
    gate_number: int,
    body: GateSubmissionCreate,
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> GateSubmissionItem:
    return svc.submit_gate(id, gate_number, body)


@router.get(
    "/governance/submissions",
    response_model=list[GateSubmissionItem],
)
async def list_submissions(
    svc: Annotated[GovernanceService, Depends(_svc)],
) -> list[GateSubmissionItem]:
    return svc.list_submissions()


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
    # RBAC: Only Transformation Office can decide on gates
    # We check user metadata or role assigned in Supabase.
    # In this app, we assume 'transformation_office' role is needed.
    if current_user.role != "transformation_office":
         raise HTTPException(
             status_code=status.HTTP_403_FORBIDDEN,
             detail="Only Transformation Office members can record gate decisions."
         )
    
    return svc.record_decision(submission_id, body)
