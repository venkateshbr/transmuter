from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import assert_can_manage_program_cadence
from app.domain.meetings import MeetingArtifactUpdate
from app.services.meeting import MeetingService

router = APIRouter(prefix="/meeting-artifacts", tags=["meetings"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> MeetingService:
    return MeetingService(client, current_user.tenant_id)


@router.put("/{artifact_id}")
async def update_meeting_artifact(
    artifact_id: str,
    body: MeetingArtifactUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_program_cadence(current_user)
    return svc.update_artifact(artifact_id, body)


@router.delete("/{artifact_id}", status_code=204)
async def delete_meeting_artifact(
    artifact_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_program_cadence(current_user)
    svc.delete_artifact(artifact_id)
