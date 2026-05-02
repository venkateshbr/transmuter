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
        meetings = result.data or []
        for meeting in meetings:
            meeting["stats"] = self.get_stats(meeting["id"])
        return meetings

    def get(self, meeting_id: str) -> dict | None:
        result = (
            self._c.table("meetings")
            .select("*, users!meetings_owner_id_fkey(display_name), workstreams(name)")
            .eq("tenant_id", self._tid)
            .eq("id", meeting_id)
            .maybe_single()
            .execute()
        )
        meeting = result.data if result else None
        if meeting:
            meeting["stats"] = self.get_stats(meeting_id)
            meeting["initiatives"] = self.get_initiatives(meeting_id)
        return meeting

    def create(self, data: dict) -> dict:
        result = (
            self._c.table("meetings")
            .insert({"tenant_id": self._tid, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    def update(self, meeting_id: str, data: dict) -> dict:
        result = (
            self._c.table("meetings")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", meeting_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, meeting_id: str) -> None:
        (
            self._c.table("meetings")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", meeting_id)
            .execute()
        )

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

    def create_agenda_item(self, meeting_id: str, data: dict) -> dict:
        result = (
            self._c.table("agenda_items")
            .insert({"tenant_id": self._tid, "meeting_id": meeting_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_agenda_item(self, meeting_id: str, item_id: str, data: dict) -> dict:
        result = (
            self._c.table("agenda_items")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("id", item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_agenda_item(self, meeting_id: str, item_id: str) -> None:
        (
            self._c.table("agenda_items")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("id", item_id)
            .execute()
        )

    def get_attendees(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_attendees")
            .select("*, users(display_name, email, role)")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        return result.data or []

    def add_attendee(self, meeting_id: str, user_id: str) -> dict:
        existing = (
            self._c.table("meeting_attendees")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            return existing.data
        result = (
            self._c.table("meeting_attendees")
            .insert({"tenant_id": self._tid, "meeting_id": meeting_id, "user_id": user_id})
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_attendee(self, meeting_id: str, attendee_id: str) -> None:
        (
            self._c.table("meeting_attendees")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("id", attendee_id)
            .execute()
        )

    def get_initiatives(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_initiatives")
            .select("*, initiatives(id, initiative_code, name, stage, rag_status)")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        return result.data or []

    def add_initiative(self, meeting_id: str, initiative_id: str) -> dict:
        existing = (
            self._c.table("meeting_initiatives")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("initiative_id", initiative_id)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            return existing.data
        result = (
            self._c.table("meeting_initiatives")
            .insert({
                "tenant_id": self._tid,
                "meeting_id": meeting_id,
                "initiative_id": initiative_id,
            })
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_initiative(self, meeting_id: str, link_id: str) -> None:
        (
            self._c.table("meeting_initiatives")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("id", link_id)
            .execute()
        )

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

    def list_action_items(self) -> list[dict]:
        result = (
            self._c.table("action_items")
            .select(
                "*, users!action_items_assignee_id_fkey(display_name), "
                "initiatives(name, initiative_code), "
                "meeting_sessions(session_date, meeting_id, meetings(name))"
            )
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []

    def update_action_item(self, action_item_id: str, data: dict) -> dict:
        result = (
            self._c.table("action_items")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", action_item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_action_item(self, action_item_id: str) -> None:
        (
            self._c.table("action_items")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", action_item_id)
            .execute()
        )

    def get_stats(self, meeting_id: str) -> dict:
        initiatives = (
            self._c.table("meeting_initiatives")
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        attendees = (
            self._c.table("meeting_attendees")
            .select("id", count="exact")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        sessions = self.get_sessions(meeting_id)
        open_actions = 0
        for session in sessions:
            actions = (
                self._c.table("action_items")
                .select("id", count="exact")
                .eq("tenant_id", self._tid)
                .eq("session_id", session["id"])
                .neq("status", "completed")
                .execute()
            )
            open_actions += actions.count or 0
        return {
            "initiatives": initiatives.count or 0,
            "attendees": attendees.count or 0,
            "sessions": len(sessions),
            "open_actions": open_actions,
            "last_session_date": sessions[0]["session_date"] if sessions else None,
        }
