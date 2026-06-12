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
            .neq("status", "cancelled")
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
        payload = {"tenant_id": self._tid, **data}
        try:
            result = self._c.table("meetings").insert(payload).execute()
        except Exception as exc:
            if not self._is_missing_meeting_schedule_columns(exc):
                raise
            legacy_payload = {
                key: value
                for key, value in payload.items()
                if key
                not in {
                    "day_of_week",
                    "start_time",
                    "timezone",
                    "duration_minutes",
                    "one_off_date",
                    "series_end_date",
                }
            }
            result = self._c.table("meetings").insert(legacy_payload).execute()
        return result.data[0] if result.data else {}

    def update(self, meeting_id: str, data: dict) -> dict:
        try:
            result = (
                self._c.table("meetings")
                .update(data)
                .eq("tenant_id", self._tid)
                .eq("id", meeting_id)
                .execute()
            )
        except Exception as exc:
            if not self._is_missing_meeting_schedule_columns(exc):
                raise
            legacy_data = {
                key: value
                for key, value in data.items()
                if key
                not in {
                    "day_of_week",
                    "start_time",
                    "timezone",
                    "duration_minutes",
                    "one_off_date",
                    "series_end_date",
                    "status",
                }
            }
            result = (
                self._c.table("meetings")
                .update(legacy_data)
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

    def set_attendees(self, meeting_id: str, user_ids: list[str]) -> None:
        (
            self._c.table("meeting_attendees")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .execute()
        )
        unique_ids = list(dict.fromkeys([user_id for user_id in user_ids if user_id]))
        if not unique_ids:
            return
        self._c.table("meeting_attendees").insert(
            [
                {
                    "tenant_id": self._tid,
                    "meeting_id": meeting_id,
                    "user_id": user_id,
                }
                for user_id in unique_ids
            ]
        ).execute()

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

    def create_session(self, meeting_id: str, session_date: str, data: dict | None = None) -> dict:
        payload = {
            "tenant_id": self._tid,
            "meeting_id": meeting_id,
            "session_date": session_date,
            "status": "scheduled",
            **(data or {}),
        }
        try:
            result = self._c.table("meeting_sessions").insert(payload).execute()
        except Exception as exc:
            if not self._is_missing_session_schedule_columns(exc):
                raise
            legacy_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"scheduled_start_at", "scheduled_end_at"}
            }
            result = self._c.table("meeting_sessions").insert(legacy_payload).execute()
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
        try:
            result = (
                self._c.table("meeting_sessions")
                .update(data)
                .eq("tenant_id", self._tid)
                .eq("id", session_id)
                .execute()
            )
        except Exception as exc:
            if not self._is_missing_session_schedule_columns(exc):
                raise
            legacy_data = {
                key: value
                for key, value in data.items()
                if key not in {"scheduled_start_at", "scheduled_end_at"}
            }
            result = (
                self._c.table("meeting_sessions")
                .update(legacy_data)
                .eq("tenant_id", self._tid)
                .eq("id", session_id)
                .execute()
            )
        return result.data[0] if result.data else {}

    def cancel_open_sessions(self, meeting_id: str) -> int:
        result = (
            self._c.table("meeting_sessions")
            .update(
                {
                    "status": "cancelled",
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
            .in_("status", ["scheduled", "in_progress"])
            .execute()
        )
        return len(result.data or [])

    def get_session_agenda(self, session_id: str) -> list[dict]:
        try:
            result = (
                self._c.table("meeting_session_agenda_items")
                .select("*, initiatives(name, initiative_code)")
                .eq("tenant_id", self._tid)
                .eq("session_id", session_id)
                .order("sort_order")
                .execute()
            )
        except Exception as exc:
            if self._is_missing_session_snapshot_tables(exc):
                return []
            raise
        return result.data or []

    def create_session_agenda_item(self, session_id: str, meeting_id: str, data: dict) -> dict:
        result = (
            self._c.table("meeting_session_agenda_items")
            .insert(
                {
                    "tenant_id": self._tid,
                    "session_id": session_id,
                    "meeting_id": meeting_id,
                    **data,
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_session_agenda_item(self, session_id: str, item_id: str, data: dict) -> dict:
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("meeting_session_agenda_items")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .eq("id", item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_session_agenda_item(self, session_id: str, item_id: str) -> None:
        (
            self._c.table("meeting_session_agenda_items")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .eq("id", item_id)
            .execute()
        )

    def snapshot_session_agenda(self, session: dict, agenda: list[dict]) -> None:
        if self.get_session_agenda(session["id"]):
            return
        rows = [
            {
                "tenant_id": self._tid,
                "meeting_id": session["meeting_id"],
                "session_id": session["id"],
                "source_agenda_item_id": item.get("id"),
                "initiative_id": item.get("initiative_id"),
                "text": item.get("text"),
                "sort_order": item.get("sort_order") or index,
            }
            for index, item in enumerate(agenda, start=1)
            if item.get("text")
        ]
        if not rows:
            return
        try:
            self._c.table("meeting_session_agenda_items").insert(rows).execute()
        except Exception as exc:
            if self._is_missing_session_snapshot_tables(exc):
                return
            raise

    def get_session_attendees(self, session_id: str) -> list[dict]:
        try:
            result = (
                self._c.table("meeting_session_attendees")
                .select("*, users(display_name, email, role)")
                .eq("tenant_id", self._tid)
                .eq("session_id", session_id)
                .execute()
            )
        except Exception as exc:
            if self._is_missing_session_snapshot_tables(exc):
                return []
            raise
        return result.data or []

    def add_session_attendee(self, session: dict, user_id: str) -> dict:
        existing = (
            self._c.table("meeting_session_attendees")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("session_id", session["id"])
            .eq("user_id", user_id)
            .maybe_single()
            .execute()
        )
        if existing and existing.data:
            return existing.data
        result = (
            self._c.table("meeting_session_attendees")
            .insert(
                {
                    "tenant_id": self._tid,
                    "meeting_id": session["meeting_id"],
                    "session_id": session["id"],
                    "user_id": user_id,
                }
            )
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_session_attendee(self, session_id: str, attendee_id: str) -> None:
        (
            self._c.table("meeting_session_attendees")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("session_id", session_id)
            .eq("id", attendee_id)
            .execute()
        )

    def snapshot_session_attendees(self, session: dict, attendees: list[dict]) -> None:
        if self.get_session_attendees(session["id"]):
            return
        rows = [
            {
                "tenant_id": self._tid,
                "meeting_id": session["meeting_id"],
                "session_id": session["id"],
                "source_meeting_attendee_id": attendee.get("id"),
                "user_id": attendee.get("user_id"),
            }
            for attendee in attendees
            if attendee.get("user_id")
        ]
        if not rows:
            return
        try:
            self._c.table("meeting_session_attendees").insert(rows).execute()
        except Exception as exc:
            if self._is_missing_session_snapshot_tables(exc):
                return
            raise

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

    def upsert_external_event(
        self,
        meeting_id: str,
        provider: str,
        data: dict,
        session_id: str | None = None,
    ) -> dict:
        payload = {
            "tenant_id": self._tid,
            "meeting_id": meeting_id,
            "session_id": session_id,
            "provider": provider,
            **data,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        try:
            existing_query = (
                self._c.table("meeting_external_events")
                .select("id")
                .eq("tenant_id", self._tid)
                .eq("meeting_id", meeting_id)
                .eq("provider", provider)
            )
            if session_id:
                existing_query = existing_query.eq("session_id", session_id)
            else:
                existing_query = existing_query.is_("session_id", "null")
            existing = existing_query.limit(1).execute()
            if existing.data:
                result = (
                    self._c.table("meeting_external_events")
                    .update(payload)
                    .eq("tenant_id", self._tid)
                    .eq("id", existing.data[0]["id"])
                    .execute()
                )
            else:
                result = self._c.table("meeting_external_events").insert(payload).execute()
        except Exception as exc:
            if not self._is_missing_external_event_columns(exc):
                raise
            legacy_payload = {
                key: value
                for key, value in payload.items()
                if key
                not in {
                    "integration_connection_id",
                    "scheduled_start_at",
                    "scheduled_end_at",
                    "time_zone",
                    "session_id",
                }
            }
            result = (
                self._c.table("meeting_external_events")
                .upsert(legacy_payload, on_conflict="meeting_id,provider")
                .execute()
            )
        return result.data[0] if result.data else {}

    def update_external_event(self, event_id: str, data: dict) -> dict:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("meeting_external_events")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", event_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def get_external_events(self, meeting_id: str, session_id: str | None = None) -> list[dict]:
        query = (
            self._c.table("meeting_external_events")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("meeting_id", meeting_id)
        )
        if session_id:
            query = query.or_(f"session_id.eq.{session_id},session_id.is.null")
        try:
            result = query.execute()
        except Exception as exc:
            if not session_id or not self._is_missing_external_event_columns(exc):
                raise
            result = (
                self._c.table("meeting_external_events")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("meeting_id", meeting_id)
                .execute()
            )
        return result.data or []

    def list_integration_connections(self) -> list[dict]:
        try:
            result = (
                self._c.table("integration_connections")
                .select(
                    "id, tenant_id, provider, organizer_email, external_account_id, "
                    "token_expires_at, scopes, sync_status, sync_error, last_synced_at, "
                    "created_at, updated_at"
                )
                .eq("tenant_id", self._tid)
                .order("provider")
                .execute()
            )
        except Exception as exc:
            if self._is_missing_integration_table(exc):
                return []
            raise
        return result.data or []

    def get_integration_connection(
        self,
        provider: str,
        organizer_email: str | None = None,
    ) -> dict | None:
        query = (
            self._c.table("integration_connections")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("provider", provider)
        )
        if organizer_email:
            query = query.eq("organizer_email", organizer_email)
        try:
            result = query.order("updated_at", desc=True).limit(1).execute()
        except Exception as exc:
            if self._is_missing_integration_table(exc):
                return None
            raise
        return result.data[0] if result.data else None

    def get_integration_connection_by_id(self, connection_id: str) -> dict | None:
        try:
            result = (
                self._c.table("integration_connections")
                .select("*")
                .eq("tenant_id", self._tid)
                .eq("id", connection_id)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            if self._is_missing_integration_table(exc):
                return None
            raise
        return result.data if result else None

    def upsert_integration_connection(self, provider: str, data: dict) -> dict:
        payload = {
            "tenant_id": self._tid,
            "provider": provider,
            **data,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        result = (
            self._c.table("integration_connections")
            .upsert(payload, on_conflict="tenant_id,provider,organizer_email")
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_integration_connection(self, connection_id: str, data: dict) -> dict:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("integration_connections")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", connection_id)
            .execute()
        )
        return result.data[0] if result.data else {}

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
        unique_ids = list(
            dict.fromkeys([initiative_id for initiative_id in initiative_ids if initiative_id])
        )
        if not unique_ids:
            return []
        result = (
            self._c.table("risks")
            .select(
                "id, description, initiative_id, rating, status, initiatives(id, name, initiative_code)"
            )
            .eq("tenant_id", self._tid)
            .in_("initiative_id", unique_ids)
            .eq("status", "open")
            .order("created_at", desc=True)
            .limit(12)
            .execute()
        )
        return result.data or []

    def list_recent_milestones_for_initiatives(self, initiative_ids: list[str]) -> list[dict]:
        unique_ids = list(
            dict.fromkeys([initiative_id for initiative_id in initiative_ids if initiative_id])
        )
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
        legacy = (
            meeting.get("workstreams") if isinstance(meeting.get("workstreams"), dict) else None
        )
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

    @staticmethod
    def _is_missing_integration_table(exc: Exception) -> bool:
        message = str(exc)
        return "integration_connections" in message and (
            "schema cache" in message or "PGRST205" in message
        )

    @staticmethod
    def _is_missing_external_event_columns(exc: Exception) -> bool:
        message = str(exc)
        return "meeting_external_events" in message and (
            "scheduled_start_at" in message
            or "scheduled_end_at" in message
            or "integration_connection_id" in message
            or "time_zone" in message
            or "session_id" in message
        )

    @staticmethod
    def _is_missing_meeting_schedule_columns(exc: Exception) -> bool:
        message = str(exc)
        return "meetings" in message and any(
            column in message
            for column in (
                "day_of_week",
                "start_time",
                "timezone",
                "duration_minutes",
                "one_off_date",
                "series_end_date",
                "status",
            )
        )

    @staticmethod
    def _is_missing_session_schedule_columns(exc: Exception) -> bool:
        message = str(exc)
        return "meeting_sessions" in message and (
            "scheduled_start_at" in message or "scheduled_end_at" in message
        )

    @staticmethod
    def _is_missing_session_snapshot_tables(exc: Exception) -> bool:
        message = str(exc)
        return (
            "meeting_session_agenda_items" in message or "meeting_session_attendees" in message
        ) and ("schema cache" in message or "PGRST205" in message or "does not exist" in message)
