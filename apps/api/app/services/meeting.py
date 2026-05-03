from datetime import date
from uuid import UUID
from supabase import Client
from app.repositories.meeting import MeetingRepository
from fastapi import HTTPException, status
from app.domain.meetings import (
    ActionItemCreate,
    ActionItemListResponse,
    ActionItemStats,
    ActionItemUpdate,
    AgendaItemCreate,
    AgendaItemUpdate,
    AttendeeCreate,
    MeetingCreate,
    MeetingInitiativeCreate,
    MeetingUpdate,
    SessionUpdate,
)

class MeetingService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = MeetingRepository(client, tenant_id)
        self._tenant_id = tenant_id

    def list_meetings(self) -> list[dict]:
        return self._repo.list()

    def create_meeting(self, data: MeetingCreate) -> dict:
        payload = data.model_dump(exclude_none=True)
        return self._repo.create(payload)

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

    def update_meeting(self, meeting_id: str, data: MeetingUpdate) -> dict:
        self._assert_meeting(meeting_id)
        payload = data.model_dump(exclude_none=True)
        if not payload:
            return self.get_meeting_detail(meeting_id)
        self._repo.update(meeting_id, payload)
        return self.get_meeting_detail(meeting_id)

    def delete_meeting(self, meeting_id: str) -> None:
        self._assert_meeting(meeting_id)
        self._repo.delete(meeting_id)

    def create_agenda_item(self, meeting_id: str, data: AgendaItemCreate) -> dict:
        self._assert_meeting(meeting_id)
        payload = data.model_dump(exclude_none=True)
        if "sort_order" not in payload:
            payload["sort_order"] = len(self._repo.get_agenda(meeting_id)) + 1
        return self._repo.create_agenda_item(meeting_id, payload)

    def update_agenda_item(
        self,
        meeting_id: str,
        item_id: str,
        data: AgendaItemUpdate,
    ) -> dict:
        self._assert_meeting(meeting_id)
        return self._repo.update_agenda_item(
            meeting_id,
            item_id,
            data.model_dump(exclude_none=True),
        )

    def delete_agenda_item(self, meeting_id: str, item_id: str) -> None:
        self._assert_meeting(meeting_id)
        self._repo.delete_agenda_item(meeting_id, item_id)

    def add_attendee(self, meeting_id: str, data: AttendeeCreate) -> dict:
        self._assert_meeting(meeting_id)
        return self._repo.add_attendee(meeting_id, data.user_id)

    def delete_attendee(self, meeting_id: str, attendee_id: str) -> None:
        self._assert_meeting(meeting_id)
        self._repo.delete_attendee(meeting_id, attendee_id)

    def add_initiative(self, meeting_id: str, data: MeetingInitiativeCreate) -> dict:
        self._assert_meeting(meeting_id)
        return self._repo.add_initiative(meeting_id, data.initiative_id)

    def delete_initiative(self, meeting_id: str, link_id: str) -> None:
        self._assert_meeting(meeting_id)
        self._repo.delete_initiative(meeting_id, link_id)

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

    def update_session(self, session_id: str, data: SessionUpdate) -> dict:
        return self._repo.update_session(session_id, data.model_dump(exclude_none=True))

    def end_session(self, session_id: str) -> dict:
        return self._repo.update_session(session_id, {"status": "completed"})

    def create_action_item(self, session_id: str, data: ActionItemCreate) -> dict:
        self.get_session_detail(session_id)
        return self._repo.create_action_item(session_id, data.model_dump(exclude_none=True))

    def list_action_items(self) -> ActionItemListResponse:
        items = self._repo.list_action_items()
        return ActionItemListResponse(items=items, stats=self._action_item_stats(items))

    def update_action_item(self, action_item_id: str, data: ActionItemUpdate) -> dict:
        patch = data.model_dump(exclude_none=True)
        if not patch:
            existing = self._repo.get_action_item(action_item_id)
            if not existing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")
            return existing
        updated = self._repo.update_action_item(action_item_id, patch)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found")
        return updated

    def delete_action_item(self, action_item_id: str) -> None:
        self._repo.delete_action_item(action_item_id)

    @staticmethod
    def _action_item_stats(items: list[dict]) -> ActionItemStats:  # type: ignore[type-arg]
        today = date.today()
        stats = ActionItemStats(total=len(items))
        for item in items:
            status_value = item.get("status") or "open"
            if status_value == "open":
                stats.open += 1
            elif status_value == "in_progress":
                stats.in_progress += 1
            elif status_value == "completed":
                stats.completed += 1
            elif status_value == "cancelled":
                stats.cancelled += 1
            due_date = item.get("due_date")
            if status_value not in {"completed", "cancelled"} and due_date:
                try:
                    if date.fromisoformat(str(due_date)) < today:
                        stats.overdue += 1
                except ValueError:
                    pass
        return stats

    def _assert_meeting(self, meeting_id: str) -> dict:
        meeting = self._repo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
        return meeting
