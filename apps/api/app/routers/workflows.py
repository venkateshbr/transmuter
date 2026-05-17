"""Workflow router — HITL orchestration endpoints."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import assert_can_manage_initiatives
from app.domain.workflows import (
    InitiativeIntakeWorkflowStart,
    WorkflowApproveRequest,
    WorkflowRejectRequest,
    WorkflowRejectResponse,
    WorkflowRunCreated,
    WorkflowStatus,
)
from app.services.workflow import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> WorkflowService:
    return WorkflowService(get_supabase_admin(), current_user.tenant_id)


@router.post("/initiative-intake", response_model=WorkflowRunCreated, status_code=202)
async def start_initiative_intake_workflow(
    body: InitiativeIntakeWorkflowStart,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[WorkflowService, Depends(_svc)],
) -> WorkflowRunCreated:
    assert_can_manage_initiatives(current_user)
    return await svc.start_initiative_intake(body, current_user.id)


@router.get("/{run_id}/status", response_model=WorkflowStatus)
async def get_workflow_status(
    run_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[WorkflowService, Depends(_svc)],
) -> WorkflowStatus:
    return svc.get_status(run_id)


@router.get("/{run_id}/review")
async def get_workflow_review(
    run_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[WorkflowService, Depends(_svc)],
) -> Any:
    assert_can_manage_initiatives(current_user)
    return svc.get_review(run_id)


@router.post("/{run_id}/approve", status_code=201)
async def approve_workflow(
    run_id: UUID,
    body: WorkflowApproveRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[WorkflowService, Depends(_svc)],
) -> Any:
    assert_can_manage_initiatives(current_user)
    return svc.approve(run_id, body, current_user.id)


@router.post("/{run_id}/reject", response_model=WorkflowRejectResponse)
async def reject_workflow(
    run_id: UUID,
    body: WorkflowRejectRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[WorkflowService, Depends(_svc)],
) -> WorkflowRejectResponse:
    assert_can_manage_initiatives(current_user)
    return svc.reject(run_id, body, current_user.id)
