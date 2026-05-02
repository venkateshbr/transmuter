from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.domain.meetings import (
    ActionItemCreate,
    AgendaItemCreate,
    AgendaItemUpdate,
    AttendeeCreate,
    MeetingCreate,
    MeetingInitiativeCreate,
    MeetingListResponse,
    MeetingUpdate,
    SessionUpdate,
)
from app.services.meeting import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])

def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> MeetingService:
    return MeetingService(get_supabase_admin(), current_user.tenant_id)

@router.get("")
async def list_meetings(svc: Annotated[MeetingService, Depends(_svc)]) -> MeetingListResponse:
    """List all meetings in the portfolio."""
    return {"items": svc.list_meetings()}

@router.post("", status_code=201)
async def create_meeting(
    body: MeetingCreate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.create_meeting(body)


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, svc: Annotated[MeetingService, Depends(_svc)]) -> dict:
    """Get detail for a specific session."""
    return svc.get_session_detail(session_id)

@router.patch("/sessions/{session_id}")
async def update_session(
    session_id: str,
    data: SessionUpdate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Update session data (notes, transcript)."""
    return svc.update_session(session_id, data)

@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, svc: Annotated[MeetingService, Depends(_svc)]) -> dict:
    """Mark a session as completed."""
    return svc.end_session(session_id)

@router.post("/sessions/{session_id}/action-items")
async def create_action_item(
    session_id: str,
    data: ActionItemCreate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Create a new action item in the session."""
    return svc.create_action_item(session_id, data)

@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, svc: Annotated[MeetingService, Depends(_svc)]) -> dict:
    """Get full detail for a specific meeting series."""
    return svc.get_meeting_detail(meeting_id)

@router.put("/{meeting_id}")
async def update_meeting(
    meeting_id: str,
    body: MeetingUpdate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.update_meeting(meeting_id, body)

@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(
    meeting_id: str,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    svc.delete_meeting(meeting_id)

@router.post("/{meeting_id}/sessions/start")
async def start_session(meeting_id: str, svc: Annotated[MeetingService, Depends(_svc)]) -> dict:
    """Start a new live session or resume an active one."""
    return svc.start_session(meeting_id)

@router.post("/{meeting_id}/agenda", status_code=201)
async def create_agenda_item(
    meeting_id: str,
    body: AgendaItemCreate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.create_agenda_item(meeting_id, body)

@router.put("/{meeting_id}/agenda/{item_id}")
async def update_agenda_item(
    meeting_id: str,
    item_id: str,
    body: AgendaItemUpdate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.update_agenda_item(meeting_id, item_id, body)

@router.delete("/{meeting_id}/agenda/{item_id}", status_code=204)
async def delete_agenda_item(
    meeting_id: str,
    item_id: str,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    svc.delete_agenda_item(meeting_id, item_id)

@router.post("/{meeting_id}/attendees", status_code=201)
async def add_attendee(
    meeting_id: str,
    body: AttendeeCreate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.add_attendee(meeting_id, body)

@router.delete("/{meeting_id}/attendees/{attendee_id}", status_code=204)
async def delete_attendee(
    meeting_id: str,
    attendee_id: str,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    svc.delete_attendee(meeting_id, attendee_id)

@router.post("/{meeting_id}/initiatives", status_code=201)
async def add_initiative(
    meeting_id: str,
    body: MeetingInitiativeCreate,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    return svc.add_initiative(meeting_id, body)

@router.delete("/{meeting_id}/initiatives/{link_id}", status_code=204)
async def delete_initiative(
    meeting_id: str,
    link_id: str,
    svc: Annotated[MeetingService, Depends(_svc)],
) -> None:
    svc.delete_initiative(meeting_id, link_id)
