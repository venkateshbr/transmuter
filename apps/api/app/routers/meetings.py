from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import (
    assert_can_manage_initiatives,
    assert_can_view_meeting,
    assert_can_view_portfolio,
    assert_can_view_session,
)
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
) -> dict:
    """Get detail for a specific session."""
    assert_can_view_session(get_supabase_admin(), current_user, session_id)
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

@router.get("/{meeting_id}")
async def get_meeting(
    meeting_id: str,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    """Get full detail for a specific meeting series."""
    assert_can_view_meeting(get_supabase_admin(), current_user, meeting_id)
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
) -> dict:
    """Start a new live session or resume an active one."""
    assert_can_manage_initiatives(current_user)
    return svc.start_session(meeting_id)

@router.post("/{meeting_id}/agenda", status_code=201)
async def create_agenda_item(
    meeting_id: str,
    body: AgendaItemCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    svc: Annotated[MeetingService, Depends(_svc)],
) -> dict:
    assert_can_manage_initiatives(current_user)
    return svc.create_agenda_item(meeting_id, body)

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
