from uuid import UUID
from supabase import Client
from app.repositories.meeting import MeetingRepository
from fastapi import HTTPException, status

class MeetingService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = MeetingRepository(client, tenant_id)
        self._tenant_id = tenant_id

    def list_meetings(self) -> list[dict]:
        return self._repo.list()

    def get_meeting_detail(self, meeting_id: str) -> dict:
        meeting = self._repo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        
        sessions = self._repo.get_sessions(meeting_id)
        agenda = self._repo.get_agenda(meeting_id)
        attendees = self._repo.get_attendees(meeting_id)
        
        return {
            **meeting,
            "sessions": sessions,
            "agenda": agenda,
            "attendees": attendees
        }

    def start_session(self, meeting_id: str) -> dict:
        from datetime import date
        today = date.today().isoformat()
        
        # Check for existing in_progress session
        sessions = self._repo.get_sessions(meeting_id)
        active = [s for s in sessions if s["status"] == "in_progress"]
        if active:
            return active[0]
            
        return self._repo.create_session(meeting_id, today)

    def get_session_detail(self, session_id: str) -> dict:
        session = self._repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        
        meeting_id = session["meeting_id"]
        agenda = self._repo.get_agenda(meeting_id)
        action_items = self._repo.get_session_action_items(session_id)
        
        return {
            **session,
            "agenda": agenda,
            "action_items": action_items
        }

    def update_session(self, session_id: str, data: dict) -> dict:
        return self._repo.update_session(session_id, data)

    def end_session(self, session_id: str) -> dict:
        return self._repo.update_session(session_id, {"status": "completed"})

    def create_action_item(self, session_id: str, data: dict) -> dict:
        return self._repo.create_action_item(session_id, data)
