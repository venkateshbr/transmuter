from uuid import UUID, uuid4
from supabase import Client

class MeetingRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def list(self) -> list[dict]:
        result = (
            self._c.table("meetings")
            .select("*, users!meetings_owner_id_fkey(display_name), workstreams(name)")
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def get(self, meeting_id: str) -> dict | None:
        result = (
            self._c.table("meetings")
            .select("*, users!meetings_owner_id_fkey(display_name), workstreams(name)")
            .eq("tenant_id", self._tid)
            .eq("id", meeting_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def get_sessions(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_sessions")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .order("session_date", desc=True)
            .execute()
        )
        return result.data or []

    def get_agenda(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("agenda_items")
            .select("*, initiatives(name, initiative_code)")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .order("sort_order")
            .execute()
        )
        return result.data or []

    def get_attendees(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_attendees")
            .select("*, users(display_name, email, role)")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        return result.data or []

    def create_session(self, meeting_id: str, session_date: str) -> dict:
        result = (
            self._c.table("meeting_sessions")
            .insert({
                "tenant_id": self._tid,
                "meeting_id": meeting_id,
                "session_date": session_date,
                "status": "in_progress"
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_session(self, session_id: str) -> dict | None:
        result = (
            self._c.table("meeting_sessions")
            .select("*, meetings(*)")
            .eq("tenant_id", self._tid)
            .eq("id", session_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def update_session(self, session_id: str, data: dict) -> dict:
        result = (
            self._c.table("meeting_sessions")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", session_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def create_action_item(self, session_id: str, data: dict) -> dict:
        result = (
            self._c.table("action_items")
            .insert({
                "tenant_id": self._tid,
                "session_id": session_id,
                **data
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_session_action_items(self, session_id: str) -> list[dict]:
        result = (
            self._c.table("action_items")
            .select("*, users!action_items_assignee_id_fkey(display_name), initiatives(name, initiative_code)")
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .execute()
        )
        return result.data or []
