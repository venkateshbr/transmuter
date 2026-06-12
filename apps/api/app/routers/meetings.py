from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_meeting,
    assert_can_view_portfolio,
    assert_can_view_session,
)
from app.domain.meeting_notes import MeetingNotesWorkflowReview
from app.domain.meetings import (
    ActionItemCreate,
    AgendaItemCreate,
    AgendaItemUpdate,
    AgendaSuggestionsResponse,
    AttendeeCreate,
    MeetingArtifactCreate,
    MeetingArtifactUpdate,
    MeetingCreate,
    MeetingExternalEventCreate,
    MeetingInitiativeCreate,
    MeetingListResponse,
    MeetingMinutesGenerateRequest,
    MeetingSeriesCancelResponse,
    MeetingTranscriptImport,
    MeetingTranscriptSyncResponse,
    MeetingUpdate,
    SessionStartRequest,
    SessionUpdate,
)
from app.services.meeting import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> MeetingService:
    return MeetingService(client, current_user.tenant_id)


@router.get("")
async def list_meetings(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> MeetingListResponse:
    """List all meetings in the portfolio."""
    assert_can_view_portfolio(current_user)
    return {"items": svc.list_meetings()}


@router.post("", status_code=201)
async def create_meeting(
    body: MeetingCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_meeting(body)


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict:
    """Get detail for a specific session."""
    assert_can_view_session(client, current_user, session_id)
    return svc.get_session_detail(session_id)


@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    data: SessionUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Update session data (notes, transcript)."""
    assert_can_manage_initiatives(current_user)
    return svc.update_session(session_id, data)


@router.post("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Mark a session as completed."""
    assert_can_manage_initiatives(current_user)
    return svc.end_session(session_id)


@router.post("/sessions/{session_id}/action-items")
async def create_action_item(
    session_id: str,
    data: ActionItemCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Create a new action item in the session."""
    assert_can_manage_initiatives(current_user)
    return svc.create_action_item(session_id, data)


@router.post("/sessions/{session_id}/agenda", status_code=201)
async def create_session_agenda_item(
    session_id: str,
    body: AgendaItemCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_session_agenda_item(session_id, body)


@router.put("/sessions/{session_id}/agenda/{item_id}")
async def update_session_agenda_item(
    session_id: str,
    item_id: str,
    body: AgendaItemUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.update_session_agenda_item(session_id, item_id, body)


@router.post("/sessions/{session_id}/agenda/suggestions", response_model=AgendaSuggestionsResponse)
async def suggest_session_agenda_items(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> AgendaSuggestionsResponse:
    assert_can_manage_initiatives(current_user)
    return svc.suggest_session_agenda_items(session_id)


@router.delete("/sessions/{session_id}/agenda/{item_id}", status_code=204)
async def delete_session_agenda_item(
    session_id: str,
    item_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_session_agenda_item(session_id, item_id)


@router.post("/sessions/{session_id}/attendees", status_code=201)
async def add_session_attendee(
    session_id: str,
    body: AttendeeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.add_session_attendee(session_id, body)


@router.delete("/sessions/{session_id}/attendees/{attendee_id}", status_code=204)
async def delete_session_attendee(
    session_id: str,
    attendee_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_session_attendee(session_id, attendee_id)


@router.post("/sessions/{session_id}/external-events/microsoft")
async def create_session_microsoft_external_event(
    session_id: str,
    body: MeetingExternalEventCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    assert_can_view_session(client, current_user, session_id)
    session = svc.get_session_detail(session_id)
    return svc.create_microsoft_event(session["meeting_id"], body, session_id=session_id)


@router.get("/sessions/{session_id}/artifacts")
async def list_session_artifacts(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict:
    assert_can_view_session(client, current_user, session_id)
    return {"items": svc.list_session_artifacts(session_id)}


@router.post("/sessions/{session_id}/artifacts", status_code=201)
async def create_session_artifact(
    session_id: str,
    body: MeetingArtifactCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_artifact(session_id, body)


@router.post("/sessions/{session_id}/transcript/import")
async def import_session_transcript(
    session_id: str,
    body: MeetingTranscriptImport,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.import_transcript(session_id, body)


@router.post(
    "/sessions/{session_id}/transcript/sync/microsoft",
    response_model=MeetingTranscriptSyncResponse,
)
async def sync_microsoft_session_transcript(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> MeetingTranscriptSyncResponse:
    assert_can_manage_initiatives(current_user)
    return svc.sync_microsoft_transcript(session_id)


@router.post("/sessions/{session_id}/minutes/generate")
async def generate_session_minutes(
    session_id: str,
    body: MeetingMinutesGenerateRequest,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.generate_minutes(session_id, body)


@router.post("/sessions/{session_id}/ai/extract", response_model=MeetingNotesWorkflowReview)
async def extract_session_ai_notes(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> MeetingNotesWorkflowReview:
    assert_can_manage_initiatives(current_user)
    return svc.extract_meeting_notes(session_id)


@router.post("/sessions/{session_id}/minutes/send")
async def send_session_minutes(
    session_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.send_minutes(session_id)


@router.put("/artifacts/{artifact_id}")
async def update_meeting_artifact(
    artifact_id: str,
    body: MeetingArtifactUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.update_artifact(artifact_id, body)


@router.delete("/artifacts/{artifact_id}", status_code=204)
async def delete_meeting_artifact(
    artifact_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_artifact(artifact_id)


@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict:
    """Get full detail for a specific meeting series."""
    assert_can_view_meeting(client, current_user, meeting_id)
    return svc.get_meeting_detail(meeting_id)


@router.put("/{meeting_id}")
async def update_meeting(
    meeting_id: str,
    body: MeetingUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.update_meeting(meeting_id, body)


@router.post("/{meeting_id}/cancel", response_model=MeetingSeriesCancelResponse)
async def cancel_meeting_series(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> MeetingSeriesCancelResponse:
    assert_can_manage_initiatives(current_user)
    return svc.cancel_meeting_series(meeting_id)


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_meeting(meeting_id)


@router.post("/{meeting_id}/sessions/start")
async def start_session(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    body: SessionStartRequest | None = None,
) -> dict:
    """Start a date-specific live session or resume that date's session."""
    assert_can_manage_initiatives(current_user)
    return svc.start_session(meeting_id, body)


@router.get("/{meeting_id}/sessions")
async def list_meeting_sessions_window(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
    anchor_date: str | None = None,
    page_size: int = 3,
) -> dict:
    assert_can_view_meeting(client, current_user, meeting_id)
    return svc.get_sessions_window(meeting_id, anchor_date=anchor_date, page_size=page_size)


@router.post("/{meeting_id}/external-events/microsoft")
async def create_microsoft_external_event(
    meeting_id: str,
    body: MeetingExternalEventCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_microsoft_event(meeting_id, body)


@router.post("/{meeting_id}/agenda", status_code=201)
async def create_agenda_item(
    meeting_id: str,
    body: AgendaItemCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_agenda_item(meeting_id, body)


@router.post("/{meeting_id}/agenda/suggestions", response_model=AgendaSuggestionsResponse)
async def suggest_agenda_items(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> AgendaSuggestionsResponse:
    assert_can_manage_initiatives(current_user)
    return svc.suggest_agenda_items(meeting_id)


@router.put("/{meeting_id}/agenda/{item_id}")
async def update_agenda_item(
    meeting_id: str,
    item_id: str,
    body: AgendaItemUpdate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.update_agenda_item(meeting_id, item_id, body)


@router.delete("/{meeting_id}/agenda/{item_id}", status_code=204)
async def delete_agenda_item(
    meeting_id: str,
    item_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_agenda_item(meeting_id, item_id)


@router.post("/{meeting_id}/attendees", status_code=201)
async def add_attendee(
    meeting_id: str,
    body: AttendeeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.add_attendee(meeting_id, body)


@router.delete("/{meeting_id}/attendees/{attendee_id}", status_code=204)
async def delete_attendee(
    meeting_id: str,
    attendee_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_attendee(meeting_id, attendee_id)


@router.post("/{meeting_id}/initiatives", status_code=201)
async def add_initiative(
    meeting_id: str,
    body: MeetingInitiativeCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.add_initiative(meeting_id, body)


@router.delete("/{meeting_id}/initiatives/{link_id}", status_code=204)
async def delete_initiative(
    meeting_id: str,
    link_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    assert_can_manage_initiatives(current_user)
    svc.delete_initiative(meeting_id, link_id)
