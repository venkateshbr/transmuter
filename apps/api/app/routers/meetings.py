from typing import Annotated
from fastapi import APIRouter, Depends
from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.services.meeting import MeetingService

router = APIRouter(prefix="/meetings", tags=["meetings"])

def _svc(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> MeetingService:
    return MeetingService(get_supabase_admin(), current_user.tenant_id)

@router.get("")
async def list_meetings(svc: Annotated[MeetingService, Depends(_svc)]):
    """List all meetings in the portfolio."""
    return {"items": svc.list_meetings()}

@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, svc: Annotated[MeetingService, Depends(_svc)]):
    """Get full detail for a specific meeting series."""
    return svc.get_meeting_detail(meeting_id)

@router.post("/{meeting_id}/sessions/start")
async def start_session(meeting_id: str, svc: Annotated[MeetingService, Depends(_svc)]):
    """Start a new live session or resume an active one."""
    return svc.start_session(meeting_id)

@router.get("/sessions/{session_id}")
async def get_session(session_id: str, svc: Annotated[MeetingService, Depends(_svc)]):
    """Get detail for a specific session."""
    return svc.get_session_detail(session_id)

@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, data: dict, svc: Annotated[MeetingService, Depends(_svc)]):
    """Update session data (notes, transcript)."""
    return svc.update_session(session_id, data)

@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str, svc: Annotated[MeetingService, Depends(_svc)]):
    """Mark a session as completed."""
    return svc.end_session(session_id)

@router.post("/sessions/{session_id}/action-items")
async def create_action_item(session_id: str, data: dict, svc: Annotated[MeetingService, Depends(_svc)]):
    """Create a new action item in the session."""
    return svc.create_action_item(session_id, data)
