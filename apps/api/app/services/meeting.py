import re
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.core.config import settings
from app.domain.meeting_notes import (
    LinkedInitiativeContext,
    MeetingAttendeeContext,
    MeetingNotesWorkflowReview,
)
from app.domain.meetings import (
    ActionItemCreate,
    ActionItemListResponse,
    ActionItemStats,
    ActionItemUpdate,
    AgendaItemCreate,
    AgendaItemUpdate,
    AttendeeCreate,
    MeetingArtifactCreate,
    MeetingArtifactUpdate,
    MeetingCreate,
    MeetingExternalEventCreate,
    MeetingInitiativeCreate,
    MeetingMinutesGenerateRequest,
    MeetingTranscriptImport,
    MeetingUpdate,
    SessionUpdate,
)
from app.domain.risks import RiskCreate, RiskUpdate
from app.repositories.meeting import MeetingRepository
from app.services.risk import RiskService


class MeetingService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
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
        external_events = self._repo.get_external_events(meeting_id)

        return {
            **meeting,
            "sessions": sessions,
            "agenda": agenda,
            "attendees": attendees,
            "external_events": external_events,
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
        artifacts = self._repo.list_session_artifacts(session_id)
        carry_forward = self._repo.get_carry_forward_action_items(meeting_id, session_id)
        external_events = self._repo.get_external_events(meeting_id)

        return {
            **session,
            "agenda": agenda,
            "action_items": action_items,
            "artifacts": artifacts,
            "carry_forward_action_items": carry_forward,
            "external_events": external_events,
        }

    def update_session(self, session_id: str, data: SessionUpdate) -> dict:
        return self._repo.update_session(session_id, data.model_dump(exclude_none=True))

    def end_session(self, session_id: str) -> dict:
        return self._repo.update_session(session_id, {"status": "completed"})

    def create_action_item(self, session_id: str, data: ActionItemCreate) -> dict:
        self.get_session_detail(session_id)
        return self._repo.create_action_item(session_id, data.model_dump(exclude_none=True))

    def list_session_artifacts(self, session_id: str) -> list[dict]:
        self.get_session_detail(session_id)
        return self._repo.list_session_artifacts(session_id)

    def create_artifact(self, session_id: str, data: MeetingArtifactCreate) -> dict:
        session = self._assert_session(session_id)
        payload = data.model_dump(exclude_none=True)
        payload["session_id"] = session_id
        payload["meeting_id"] = session["meeting_id"]

        linked = self._create_linked_record(session_id, payload)
        if linked:
            payload.update(linked)
        return self._repo.create_artifact(payload)

    def update_artifact(self, artifact_id: str, data: MeetingArtifactUpdate) -> dict:
        existing = self._assert_artifact(artifact_id)
        patch = data.model_dump(exclude_unset=True)
        if not patch:
            return existing
        updated = self._repo.update_artifact(artifact_id, patch)
        merged = {**existing, **patch}
        self._sync_linked_record(merged)
        return updated

    def delete_artifact(self, artifact_id: str) -> None:
        existing = self._assert_artifact(artifact_id)
        self._delete_linked_record(existing)
        self._repo.delete_artifact(artifact_id)

    def create_microsoft_event(
        self,
        meeting_id: str,
        data: MeetingExternalEventCreate,
    ) -> dict:
        meeting = self._assert_meeting(meeting_id)
        if not settings.microsoft_graph_access_token:
            return self._repo.upsert_external_event(
                meeting_id,
                "microsoft",
                {
                    "organizer_email": data.organizer_email,
                    "sync_status": "not_configured",
                    "sync_error": "Microsoft Graph access token is not configured.",
                },
            )

        return self._create_graph_calendar_event(meeting, data)

    def import_transcript(self, session_id: str, data: MeetingTranscriptImport) -> dict:
        session = self._assert_session(session_id)
        transcript = data.transcript_text
        if transcript is None:
            transcript = self._import_graph_transcript(session)
        return self._repo.update_session(
            session_id,
            {
                "transcript_text": transcript or "",
                "transcript_source": data.transcript_source,
                "has_transcript": bool(transcript),
            },
        )

    def extract_meeting_notes(self, session_id: str) -> MeetingNotesWorkflowReview:
        detail = self.get_session_detail(session_id)
        transcript = detail.get("transcript_text") or detail.get("notes") or ""
        if not transcript.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Import a transcript or add session notes before extraction.",
            )
        chunks = chunk_transcript(transcript).chunks
        meeting_id = detail["meeting_id"]
        attendees = [
            MeetingAttendeeContext(
                user_id=row["user_id"],
                display_name=(row.get("users") or {}).get("display_name"),
            )
            for row in self._repo.get_attendees(meeting_id)
        ]
        linked = [
            LinkedInitiativeContext(
                id=(row.get("initiatives") or {}).get("id") or row.get("initiative_id"),
                name=(row.get("initiatives") or {}).get("name") or "Initiative",
                initiative_code=(row.get("initiatives") or {}).get("initiative_code"),
            )
            for row in self._repo.get_initiatives(meeting_id)
            if row.get("initiative_id") or (row.get("initiatives") or {}).get("id")
        ]
        actions = extract_action_items(chunks, attendees).action_items
        decisions = extract_meeting_decisions(chunks, linked)
        return MeetingNotesWorkflowReview(
            workflow_run_id=f"deterministic-meeting-notes-{session_id}",
            status="pending_review",
            expires_at=(datetime.now(UTC) + timedelta(hours=24)).isoformat(),
            session_id=session_id,
            meeting_id=meeting_id,
            action_items=actions,
            decisions=decisions.decisions,
            initiative_updates=decisions.initiative_updates,
        )

    def generate_minutes(
        self,
        session_id: str,
        _data: MeetingMinutesGenerateRequest,
    ) -> dict:
        detail = self.get_session_detail(session_id)
        minutes = self._build_minutes(detail)
        return self._repo.update_session(
            session_id,
            {
                "minutes_markdown": minutes,
                "minutes_status": "draft",
                "minutes_generated_at": datetime.now(UTC).isoformat(),
                "ai_optimised": True,
            },
        )

    def send_minutes(self, session_id: str) -> dict:
        session = self._assert_session(session_id)
        minutes = session.get("minutes_markdown")
        if not minutes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Generate and review minutes before sending.",
            )
        return self._repo.update_session(
            session_id,
            {
                "minutes_status": "sent",
                "minutes_sent_at": datetime.now(UTC).isoformat(),
            },
        )

    def list_action_items(self) -> ActionItemListResponse:
        items = self._repo.list_action_items()
        return ActionItemListResponse(items=items, stats=self._action_item_stats(items))

    def update_action_item(self, action_item_id: str, data: ActionItemUpdate) -> dict:
        patch = data.model_dump(exclude_none=True)
        if not patch:
            existing = self._repo.get_action_item(action_item_id)
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
                )
            return existing
        updated = self._repo.update_action_item(action_item_id, patch)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Action item not found"
            )
        return updated

    def delete_action_item(self, action_item_id: str) -> None:
        self._repo.delete_action_item(action_item_id)

    def _create_linked_record(self, session_id: str, payload: dict) -> dict | None:
        artifact_type = payload.get("artifact_type")
        if artifact_type == "action":
            item = self._repo.create_action_item(
                session_id,
                {
                    "description": payload.get("description") or payload["title"],
                    "initiative_id": payload.get("initiative_id"),
                    "assignee_id": payload.get("assignee_id"),
                    "priority": payload.get("priority", "medium"),
                    "status": self._action_status(payload.get("status")),
                    "due_date": payload.get("due_date"),
                },
            )
            if item:
                return {"linked_record_type": "action_item", "linked_record_id": item["id"]}
        if artifact_type == "risk" and payload.get("initiative_id"):
            risk = RiskService(self._client, self._tenant_id).create_risk(
                payload["initiative_id"],
                RiskCreate(
                    description=payload.get("description") or payload["title"],
                    type="operational",
                    impact="medium",
                    likelihood="medium",
                    status="open",
                    owner_id=payload.get("owner_id") or payload.get("assignee_id"),
                    mitigation=payload.get("title"),
                ),
            )
            return {"linked_record_type": "risk", "linked_record_id": risk.id}
        return None

    def _sync_linked_record(self, payload: dict) -> None:
        linked_type = payload.get("linked_record_type")
        linked_id = payload.get("linked_record_id")
        if not linked_type or not linked_id:
            return
        if linked_type == "action_item":
            patch = {
                "description": payload.get("description") or payload.get("title"),
                "initiative_id": payload.get("initiative_id"),
                "assignee_id": payload.get("assignee_id"),
                "priority": payload.get("priority"),
                "status": self._action_status(payload.get("status")),
                "due_date": payload.get("due_date"),
            }
            self._repo.update_action_item(
                str(linked_id), {k: v for k, v in patch.items() if v is not None}
            )
        elif linked_type == "risk" and payload.get("initiative_id"):
            RiskService(self._client, self._tenant_id).update_risk(
                payload["initiative_id"],
                str(linked_id),
                RiskUpdate(
                    description=payload.get("description") or payload.get("title"),
                    status="closed"
                    if payload.get("status") in {"completed", "cancelled"}
                    else "open",
                    owner_id=payload.get("owner_id") or payload.get("assignee_id"),
                ),
            )

    def _delete_linked_record(self, payload: dict) -> None:
        linked_type = payload.get("linked_record_type")
        linked_id = payload.get("linked_record_id")
        if linked_type == "action_item" and linked_id:
            self._repo.delete_action_item(str(linked_id))
        elif linked_type == "risk" and linked_id and payload.get("initiative_id"):
            RiskService(self._client, self._tenant_id).delete_risk(
                payload["initiative_id"],
                str(linked_id),
            )

    @staticmethod
    def _action_status(status_value: str | None) -> str:
        return (
            status_value
            if status_value in {"open", "in_progress", "completed", "cancelled"}
            else "open"
        )

    def _build_minutes(self, detail: dict) -> str:
        meeting = detail.get("meetings") or {}
        agenda = detail.get("agenda") or []
        artifacts = detail.get("artifacts") or []
        notes = self._mask_pii(detail.get("notes") or "")
        transcript = self._mask_pii(detail.get("transcript_text") or "")

        def artifact_lines(kind: str) -> list[str]:
            rows = [a for a in artifacts if a.get("artifact_type") == kind]
            return [
                f"- {self._mask_pii(a.get('title') or '')}"
                + (f" ({a.get('status')})" if a.get("status") else "")
                for a in rows
            ] or ["- None captured."]

        agenda_lines = [
            f"- {item.get('text')}"
            + (
                f" [{(item.get('initiatives') or {}).get('initiative_code')}]"
                if item.get("initiatives")
                else ""
            )
            for item in agenda
        ] or ["- No agenda items recorded."]

        return "\n".join(
            [
                f"# Minutes: {self._mask_pii(meeting.get('name') or 'Meeting')}",
                "",
                f"Session date: {detail.get('session_date')}",
                "",
                "## Agenda",
                *agenda_lines,
                "",
                "## Discussion Notes",
                notes or "No notes captured.",
                "",
                "## Transcript Summary Source",
                transcript[:2500] if transcript else "No transcript imported.",
                "",
                "## Decisions",
                *artifact_lines("decision"),
                "",
                "## Actions",
                *artifact_lines("action"),
                "",
                "## Risks And Issues",
                *artifact_lines("risk"),
                *artifact_lines("issue"),
                "",
                "## Assumptions",
                *artifact_lines("assumption"),
            ]
        )

    @staticmethod
    def _mask_pii(text: str) -> str:
        text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
        text = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[phone]", text)
        return text

    def _create_graph_calendar_event(
        self,
        meeting: dict,
        data: MeetingExternalEventCreate,
    ) -> dict:
        try:
            import httpx

            user_id = settings.microsoft_graph_user_id or data.organizer_email or "me"
            start = data.start_date_time or datetime.now(UTC).isoformat()
            end = data.end_date_time or datetime.now(UTC).isoformat()
            response = httpx.post(
                f"https://graph.microsoft.com/v1.0/users/{user_id}/events",
                headers={
                    "Authorization": f"Bearer {settings.microsoft_graph_access_token}",
                    "Content-Type": "application/json",
                },
                json={
                    "subject": meeting["name"],
                    "body": {
                        "contentType": "HTML",
                        "content": meeting.get("description") or "Transmuter meeting",
                    },
                    "start": {"dateTime": start, "timeZone": data.time_zone},
                    "end": {"dateTime": end, "timeZone": data.time_zone},
                    "isOnlineMeeting": True,
                    "onlineMeetingProvider": "teamsForBusiness",
                },
                timeout=10,
            )
            response.raise_for_status()
            body = response.json()
            online = body.get("onlineMeeting") or {}
            return self._repo.upsert_external_event(
                meeting["id"],
                "microsoft",
                {
                    "external_event_id": body.get("id"),
                    "online_meeting_id": online.get("id"),
                    "join_url": online.get("joinUrl"),
                    "organizer_email": data.organizer_email,
                    "sync_status": "synced",
                    "sync_error": None,
                    "last_synced_at": datetime.now(UTC).isoformat(),
                },
            )
        except Exception as exc:  # noqa: BLE001 - integration must not block meetings.
            return self._repo.upsert_external_event(
                meeting["id"],
                "microsoft",
                {
                    "organizer_email": data.organizer_email,
                    "sync_status": "failed",
                    "sync_error": str(exc)[:500],
                },
            )

    def _import_graph_transcript(self, session: dict) -> str:
        # Graph transcript retrieval requires the provider event/meeting id and tenant permissions.
        # The endpoint remains non-blocking until those credentials are configured.
        return ""

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

    def _assert_session(self, session_id: str) -> dict:
        session = self._repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return session

    def _assert_artifact(self, artifact_id: str) -> dict:
        artifact = self._repo.get_artifact(artifact_id)
        if not artifact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Meeting artifact not found"
            )
        return artifact
