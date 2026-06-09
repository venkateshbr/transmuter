from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

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
            self._attach_workstreams(meeting)
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
            self._attach_workstreams(meeting)
            meeting["stats"] = self.get_stats(meeting_id)
            meeting["initiatives"] = self.get_initiatives(meeting_id)
        return meeting

    def create(self, data: dict) -> dict:
        result = self._c.table("meetings").insert({"tenant_id": self._tid, **data}).execute()
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

    def set_workstreams(self, meeting_id: str, workstream_ids: list[str]) -> None:
        (
            self._c.table("meeting_workstreams")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        unique_ids = list(dict.fromkeys([ws_id for ws_id in workstream_ids if ws_id]))
        if not unique_ids:
            return
        self._c.table("meeting_workstreams").insert(
            [
                {
                    "tenant_id": self._tid,
                    "meeting_id": meeting_id,
                    "workstream_id": workstream_id,
                }
                for workstream_id in unique_ids
            ]
        ).execute()

    def get_workstreams(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_workstreams")
            .select("id, workstream_id, workstreams(id, name)")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .order("created_at")
            .execute()
        )
        rows = result.data or []
        workstreams: list[dict] = []
        for row in rows:
            embedded = row.get("workstreams") if isinstance(row.get("workstreams"), dict) else {}
            workstreams.append(
                {
                    "id": embedded.get("id") or row.get("workstream_id"),
                    "name": embedded.get("name") or row.get("workstream_id"),
                }
            )
        return workstreams

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
            .insert(
                {
                    "tenant_id": self._tid,
                    "meeting_id": meeting_id,
                    "initiative_id": initiative_id,
                }
            )
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
            .insert(
                {
                    "tenant_id": self._tid,
                    "meeting_id": meeting_id,
                    "session_date": session_date,
                    "status": "in_progress",
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_session_by_date(self, meeting_id: str, session_date: str) -> dict | None:
        result = (
            self._c.table("meeting_sessions")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .eq("session_date", session_date)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

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
            .insert({"tenant_id": self._tid, "session_id": session_id, **data})
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_session_action_items(self, session_id: str) -> list[dict]:
        result = (
            self._c.table("action_items")
            .select(
                "*, users!action_items_assignee_id_fkey(display_name), initiatives(name, initiative_code)"
            )
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .execute()
        )
        return result.data or []

    def get_carry_forward_action_items(
        self,
        meeting_id: str,
        current_session_id: str,
    ) -> list[dict]:
        sessions = [s for s in self.get_sessions(meeting_id) if s["id"] != current_session_id]
        session_ids = [s["id"] for s in sessions]
        if not session_ids:
            return []
        result = (
            self._c.table("action_items")
            .select(
                "*, users!action_items_assignee_id_fkey(display_name), "
                "initiatives(name, initiative_code), "
                "meeting_sessions(session_date, meeting_id, meetings(name))"
            )
            .eq("tenant_id", self._tid)
            .in_("session_id", session_ids)
            .order("due_date")
            .order("created_at", desc=True)
            .execute()
        )
        return [
            item
            for item in (result.data or [])
            if item.get("status") not in {"completed", "cancelled"}
        ]

    def list_session_artifacts(self, session_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_artifacts")
            .select(
                "*, "
                "agenda_items(text, sort_order), "
                "initiatives(name, initiative_code, rag_status, stage), "
                "users!meeting_artifacts_assignee_id_fkey(display_name)"
            )
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_artifact(self, artifact_id: str) -> dict | None:
        result = (
            self._c.table("meeting_artifacts")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", artifact_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create_artifact(self, data: dict) -> dict:
        result = (
            self._c.table("meeting_artifacts").insert({"tenant_id": self._tid, **data}).execute()
        )
        row = result.data[0] if result.data else {}
        return self.get_artifact(row["id"]) if row else {}

    def update_artifact(self, artifact_id: str, data: dict) -> dict:
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("meeting_artifacts")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", artifact_id)
            .execute()
        )
        row = result.data[0] if result.data else {}
        return self.get_artifact(row["id"]) if row else {}

    def delete_artifact(self, artifact_id: str) -> None:
        (
            self._c.table("meeting_artifacts")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", artifact_id)
            .execute()
        )

    def upsert_external_event(self, meeting_id: str, provider: str, data: dict) -> dict:
        payload = {
            "tenant_id": self._tid,
            "meeting_id": meeting_id,
            "provider": provider,
            **data,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = (
            self._c.table("meeting_external_events")
            .upsert(payload, on_conflict="meeting_id,provider")
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_external_events(self, meeting_id: str) -> list[dict]:
        result = (
            self._c.table("meeting_external_events")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
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
            .order("due_date")
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    def list_open_actions_for_meeting(self, meeting_id: str) -> list[dict]:
        session_ids = [session["id"] for session in self.get_sessions(meeting_id)]
        if not session_ids:
            return []
        result = (
            self._c.table("action_items")
            .select(
                "id, description, initiative_id, status, due_date, priority, "
                "initiatives(id, name, initiative_code)"
            )
            .eq("tenant_id", self._tid)
            .in_("session_id", session_ids)
            .order("due_date")
            .order("created_at", desc=True)
            .execute()
        )
        return [
            item
            for item in (result.data or [])
            if item.get("status") not in {"completed", "cancelled"}
        ]

    def list_initiatives_for_workstreams(self, workstream_ids: list[str]) -> list[dict]:
        unique_ids = list(dict.fromkeys([ws_id for ws_id in workstream_ids if ws_id]))
        if not unique_ids:
            return []
        result = (
            self._c.table("initiatives")
            .select(
                "id, initiative_code, name, priority, rag_status, stage, tag, workstream_id, "
                "workstreams(id, name)"
            )
            .eq("tenant_id", self._tid)
            .in_("workstream_id", unique_ids)
            .is_("archived_at", "null")
            .order("rag_status", desc=True)
            .order("planned_end")
            .limit(30)
            .execute()
        )
        return result.data or []

    def list_recent_risks_for_initiatives(self, initiative_ids: list[str]) -> list[dict]:
        unique_ids = list(dict.fromkeys([initiative_id for initiative_id in initiative_ids if initiative_id]))
        if not unique_ids:
            return []
        result = (
            self._c.table("risks")
            .select("id, description, initiative_id, rating, status, initiatives(id, name, initiative_code)")
            .eq("tenant_id", self._tid)
            .in_("initiative_id", unique_ids)
            .eq("status", "open")
            .order("created_at", desc=True)
            .limit(12)
            .execute()
        )
        return result.data or []

    def list_recent_milestones_for_initiatives(self, initiative_ids: list[str]) -> list[dict]:
        unique_ids = list(dict.fromkeys([initiative_id for initiative_id in initiative_ids if initiative_id]))
        if not unique_ids:
            return []
        result = (
            self._c.table("milestones")
            .select(
                "id, name, initiative_id, status, planned_end, priority, "
                "initiatives(id, name, initiative_code)"
            )
            .eq("tenant_id", self._tid)
            .in_("initiative_id", unique_ids)
            .neq("status", "complete")
            .order("planned_end")
            .limit(12)
            .execute()
        )
        return result.data or []

    def get_action_item(self, action_item_id: str) -> dict:
        result = (
            self._c.table("action_items")
            .select(
                "*, users!action_items_assignee_id_fkey(display_name), "
                "initiatives(name, initiative_code), "
                "meeting_sessions(session_date, meeting_id, meetings(name))"
            )
            .eq("tenant_id", self._tid)
            .eq("id", action_item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_action_item(self, action_item_id: str, data: dict) -> dict:
        data["updated_at"] = datetime.now(UTC).isoformat()
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

    def _attach_workstreams(self, meeting: dict) -> None:
        legacy = meeting.get("workstreams") if isinstance(meeting.get("workstreams"), dict) else None
        meeting["legacy_workstream"] = legacy
        workstreams = self.get_workstreams(meeting["id"])
        if not workstreams and meeting.get("workstream_id"):
            workstreams = [
                {
                    "id": meeting["workstream_id"],
                    "name": (legacy or {}).get("name") or meeting["workstream_id"],
                }
            ]
        meeting["workstreams"] = workstreams
