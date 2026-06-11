import re
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from langfuse.types import TraceContext
from supabase import Client

from app.agents.initiative_intake_agent import _get_langfuse
from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.core.config import settings
from app.core.database import get_supabase_admin
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
    AgendaSuggestion,
    AgendaSuggestionsResponse,
    AttendeeCreate,
    MeetingArtifactCreate,
    MeetingArtifactUpdate,
    MeetingCreate,
    MeetingExternalEventCreate,
    MeetingInitiativeCreate,
    MeetingMinutesGenerateRequest,
    MeetingTranscriptImport,
    MeetingTranscriptSyncResponse,
    MeetingUpdate,
    SessionStartRequest,
    SessionUpdate,
)
from app.domain.risks import RiskCreate, RiskUpdate
from app.repositories.meeting import MeetingRepository
from app.services.email_delivery import EmailDeliveryService
from app.services.meeting_providers import (
    MeetingInviteRequest,
    MeetingProviderConfigurationError,
    MicrosoftGraphMeetingProvider,
)
from app.services.risk import RiskService


class MeetingService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._repo = MeetingRepository(client, tenant_id)
        self._secret_repo = MeetingRepository(get_supabase_admin(), tenant_id)
        self._tenant_id = tenant_id
        self._email = EmailDeliveryService()

    def list_meetings(self) -> list[dict]:
        return self._repo.list()

    def create_meeting(self, data: MeetingCreate) -> dict:
        payload = data.model_dump(exclude_none=True)
        participant_user_ids = payload.pop("participant_user_ids", [])
        default_agenda_items = payload.pop("default_agenda_items", [])
        workstream_ids = self._normalized_workstream_ids(
            payload.pop("workstream_ids", []),
            payload.get("workstream_id"),
        )
        payload["workstream_id"] = workstream_ids[0] if workstream_ids else None
        self._normalize_schedule_payload(payload)
        meeting = self._repo.create(payload)
        if meeting:
            self._repo.set_workstreams(meeting["id"], workstream_ids)
            if participant_user_ids:
                self._repo.set_attendees(meeting["id"], self._normalized_ids(participant_user_ids))
            for index, item in enumerate(default_agenda_items, start=1):
                agenda_payload = {
                    key: value
                    for key, value in item.items()
                    if key in {"text", "initiative_id", "sort_order"} and value is not None
                }
                agenda_payload.setdefault("sort_order", index)
                self._repo.create_agenda_item(meeting["id"], agenda_payload)
            meeting = self._repo.get(meeting["id"]) or meeting
        return meeting

    def get_meeting_detail(self, meeting_id: str) -> dict:
        meeting = self._repo.get(meeting_id)
        if not meeting:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

        sessions_window = self.get_sessions_window(meeting_id)
        sessions = sessions_window["items"]
        agenda = self._repo.get_agenda(meeting_id)
        attendees = self._repo.get_attendees(meeting_id)
        external_events = self._repo.get_external_events(meeting_id)

        return {
            **meeting,
            "sessions": sessions,
            "sessions_window": sessions_window,
            "agenda": agenda,
            "attendees": attendees,
            "external_events": external_events,
        }

    def update_meeting(self, meeting_id: str, data: MeetingUpdate) -> dict:
        self._assert_meeting(meeting_id)
        payload = data.model_dump(exclude_none=True)
        participant_user_ids = payload.pop("participant_user_ids", None)
        workstream_ids_provided = (
            "workstream_ids" in data.model_fields_set or "workstream_id" in data.model_fields_set
        )
        workstream_ids = self._normalized_workstream_ids(
            payload.pop("workstream_ids", None),
            payload.get("workstream_id"),
        )
        if workstream_ids_provided:
            payload["workstream_id"] = workstream_ids[0] if workstream_ids else None
        self._normalize_schedule_payload(payload, partial=True)
        if not payload:
            if workstream_ids_provided:
                self._repo.set_workstreams(meeting_id, workstream_ids)
            if participant_user_ids is not None:
                self._repo.set_attendees(meeting_id, participant_user_ids)
            return self.get_meeting_detail(meeting_id)
        self._repo.update(meeting_id, payload)
        if workstream_ids_provided:
            self._repo.set_workstreams(meeting_id, workstream_ids)
        if participant_user_ids is not None:
            self._repo.set_attendees(meeting_id, self._normalized_ids(participant_user_ids))
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

    def suggest_agenda_items(self, meeting_id: str) -> AgendaSuggestionsResponse:
        meeting = self._assert_meeting(meeting_id)
        workstream_ids = [item["id"] for item in meeting.get("workstreams") or [] if item.get("id")]
        if not workstream_ids and meeting.get("workstream_id"):
            workstream_ids = [meeting["workstream_id"]]

        linked_rows = self._repo.get_initiatives(meeting_id)
        linked_initiatives = [
            row.get("initiatives") or {"id": row.get("initiative_id")}
            for row in linked_rows
            if row.get("initiative_id") or row.get("initiatives")
        ]
        workstream_initiatives = self._repo.list_initiatives_for_workstreams(workstream_ids)
        initiatives = self._dedupe_by_id([*linked_initiatives, *workstream_initiatives])
        initiative_ids = [item["id"] for item in initiatives if item.get("id")]

        suggestions = self._deterministic_agenda_suggestions(
            meeting=meeting,
            initiatives=initiatives,
            open_actions=self._repo.list_open_actions_for_meeting(meeting_id),
            risks=self._repo.list_recent_risks_for_initiatives(initiative_ids),
            milestones=self._repo.list_recent_milestones_for_initiatives(initiative_ids),
        )
        response = AgendaSuggestionsResponse(
            items=suggestions[:12], trace_id=self._agenda_trace_id()
        )
        return self._trace_agenda_suggestions(meeting, response)

    def suggest_session_agenda_items(self, session_id: str) -> AgendaSuggestionsResponse:
        session = self._assert_session(session_id)
        self._materialize_session(session)
        return self.suggest_agenda_items(session["meeting_id"])

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

    def get_sessions_window(
        self,
        meeting_id: str,
        anchor_date: str | None = None,
        page_size: int = 3,
    ) -> dict:
        meeting = self._assert_meeting(meeting_id)
        anchor = self._parse_date(anchor_date or date.today().isoformat(), "anchor_date")
        size = max(1, min(page_size, 12))
        session_dates = self._session_window_dates(meeting, anchor, size)
        sessions = [self._ensure_session(meeting, session_date) for session_date in session_dates]
        sessions.sort(key=lambda item: item["session_date"])
        return {
            "anchor_date": anchor.isoformat(),
            "page_size": size,
            "items": sessions,
            "previous_anchor_date": (anchor - timedelta(days=28)).isoformat(),
            "next_anchor_date": (anchor + timedelta(days=28)).isoformat(),
        }

    def add_initiative(self, meeting_id: str, data: MeetingInitiativeCreate) -> dict:
        self._assert_meeting(meeting_id)
        return self._repo.add_initiative(meeting_id, data.initiative_id)

    def delete_initiative(self, meeting_id: str, link_id: str) -> None:
        self._assert_meeting(meeting_id)
        self._repo.delete_initiative(meeting_id, link_id)

    def start_session(self, meeting_id: str, data: SessionStartRequest | None = None) -> dict:
        meeting = self._assert_meeting(meeting_id)
        session_date = (data.session_date if data else None) or date.today().isoformat()
        parsed = self._parse_date(session_date, "session_date")

        existing = self._repo.get_session_by_date(meeting_id, session_date)
        if existing:
            self._materialize_session(existing)
            if existing.get("status") != "in_progress":
                existing = self._repo.update_session(existing["id"], {"status": "in_progress"})
            return existing
        session = self._create_scheduled_session(meeting, parsed, "in_progress")
        self._materialize_session(session)
        return session

    def get_session_detail(self, session_id: str) -> dict:
        session = self._repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        meeting_id = session["meeting_id"]
        self._materialize_session(session)
        agenda = self._repo.get_session_agenda(session_id) or self._repo.get_agenda(meeting_id)
        attendees = self._repo.get_session_attendees(session_id) or self._repo.get_attendees(
            meeting_id
        )
        action_items = self._repo.get_session_action_items(session_id)
        artifacts = self._repo.list_session_artifacts(session_id)
        carry_forward = self._repo.get_carry_forward_action_items(meeting_id, session_id)
        external_events = self._repo.get_external_events(meeting_id, session_id)

        return {
            **session,
            "agenda": agenda,
            "attendees": attendees,
            "action_items": action_items,
            "artifacts": artifacts,
            "carry_forward_action_items": carry_forward,
            "external_events": external_events,
        }

    def create_session_agenda_item(self, session_id: str, data: AgendaItemCreate) -> dict:
        session = self._assert_session(session_id)
        self._materialize_session(session)
        payload = data.model_dump(exclude_none=True)
        if "sort_order" not in payload:
            payload["sort_order"] = len(self._repo.get_session_agenda(session_id)) + 1
        return self._repo.create_session_agenda_item(session_id, session["meeting_id"], payload)

    def update_session_agenda_item(
        self,
        session_id: str,
        item_id: str,
        data: AgendaItemUpdate,
    ) -> dict:
        self._assert_session(session_id)
        return self._repo.update_session_agenda_item(
            session_id,
            item_id,
            data.model_dump(exclude_none=True),
        )

    def delete_session_agenda_item(self, session_id: str, item_id: str) -> None:
        self._assert_session(session_id)
        self._repo.delete_session_agenda_item(session_id, item_id)

    def add_session_attendee(self, session_id: str, data: AttendeeCreate) -> dict:
        session = self._assert_session(session_id)
        self._materialize_session(session)
        return self._repo.add_session_attendee(session, data.user_id)

    def delete_session_attendee(self, session_id: str, attendee_id: str) -> None:
        self._assert_session(session_id)
        self._repo.delete_session_attendee(session_id, attendee_id)

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
        session_id: str | None = None,
    ) -> dict:
        meeting = self._assert_meeting(meeting_id)
        session = None
        attendees = self._repo.get_attendees(meeting_id)
        if session_id:
            session = self._assert_session(session_id)
            if session["meeting_id"] != meeting_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found for meeting",
                )
            self._materialize_session(session)
            attendees = self._repo.get_session_attendees(session_id) or attendees
        self._validate_external_event_schedule(data)
        connection = self._integration_secret_repo().get_integration_connection(
            "microsoft_graph",
            data.organizer_email,
        )
        if not connection:
            return self._repo.upsert_external_event(
                meeting_id,
                "microsoft",
                {
                    "organizer_email": data.organizer_email,
                    "scheduled_start_at": data.start_date_time,
                    "scheduled_end_at": data.end_date_time,
                    "time_zone": data.time_zone,
                    "sync_status": "not_configured",
                    "sync_error": (
                        "Microsoft Graph is not connected for this tenant. "
                        "Connect a Microsoft organizer account before syncing Teams invites."
                    ),
                },
                session_id=session_id,
            )

        try:
            result = MicrosoftGraphMeetingProvider(
                connection,
                self._integration_secret_repo(),
            ).create_invite(
                self._meeting_invite_subject(meeting, session),
                attendees,
                MeetingInviteRequest(
                    organizer_email=data.organizer_email,
                    start_date_time=data.start_date_time,
                    end_date_time=data.end_date_time,
                    time_zone=data.time_zone,
                    attendee_user_ids=data.attendee_user_ids,
                    recurrence=self._graph_recurrence(meeting, data, session_id),
                ),
            )
            return self._repo.upsert_external_event(
                meeting_id,
                "microsoft",
                {
                    "integration_connection_id": connection.get("id"),
                    "external_event_id": result.external_event_id,
                    "online_meeting_id": result.online_meeting_id,
                    "join_url": result.join_url,
                    "organizer_email": result.organizer_email,
                    "scheduled_start_at": data.start_date_time,
                    "scheduled_end_at": data.end_date_time,
                    "time_zone": data.time_zone,
                    "sync_status": "synced",
                    "sync_error": None,
                    "last_synced_at": datetime.now(UTC).isoformat(),
                },
                session_id=session_id,
            )
        except MeetingProviderConfigurationError as exc:
            sync_status = "not_configured"
            sync_error = str(exc)
        except Exception as exc:  # noqa: BLE001 - integration must not block meetings.
            sync_status = "failed"
            sync_error = str(exc)

        return self._repo.upsert_external_event(
            meeting_id,
            "microsoft",
            {
                "integration_connection_id": connection.get("id"),
                "organizer_email": data.organizer_email or connection.get("organizer_email"),
                "scheduled_start_at": data.start_date_time,
                "scheduled_end_at": data.end_date_time,
                "time_zone": data.time_zone,
                "sync_status": sync_status,
                "sync_error": sync_error[:500],
            },
            session_id=session_id,
        )

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

    def sync_microsoft_transcript(self, session_id: str) -> MeetingTranscriptSyncResponse:
        session = self._assert_session(session_id)
        event = self._microsoft_external_event(session["meeting_id"], session_id)
        if not event:
            return MeetingTranscriptSyncResponse(
                status="unavailable",
                detail="Create and sync a Teams invite before importing a Microsoft transcript.",
            )

        connection = self._microsoft_connection_for_event(event)
        if not connection:
            return MeetingTranscriptSyncResponse(
                status="unavailable",
                detail="Microsoft Graph is not connected for the event organizer.",
            )

        try:
            result = MicrosoftGraphMeetingProvider(
                connection,
                self._integration_secret_repo(),
            ).sync_transcript(event)
        except MeetingProviderConfigurationError as exc:
            return MeetingTranscriptSyncResponse(status="unavailable", detail=str(exc))
        except Exception as exc:  # noqa: BLE001 - transcript sync should report provider state.
            self._repo.upsert_external_event(
                session["meeting_id"],
                "microsoft",
                {
                    "integration_connection_id": connection.get("id"),
                    "organizer_email": event.get("organizer_email"),
                    "sync_status": "failed",
                    "sync_error": str(exc)[:500],
                },
                session_id=session_id,
            )
            return MeetingTranscriptSyncResponse(status="failed", detail=str(exc)[:500])

        if result.status != "synced":
            if result.status == "pending":
                self._repo.upsert_external_event(
                    session["meeting_id"],
                    "microsoft",
                    {
                        "integration_connection_id": connection.get("id"),
                        "organizer_email": event.get("organizer_email"),
                        "sync_status": "pending",
                        "sync_error": result.detail,
                    },
                    session_id=session_id,
                )
            return MeetingTranscriptSyncResponse(status=result.status, detail=result.detail)

        updated = self._repo.update_session(
            session_id,
            {
                "transcript_text": result.transcript_text,
                "transcript_source": "microsoft_graph",
                "has_transcript": True,
            },
        )
        self._repo.upsert_external_event(
            session["meeting_id"],
            "microsoft",
            {
                "integration_connection_id": connection.get("id"),
                "organizer_email": event.get("organizer_email"),
                "sync_status": "synced",
                "sync_error": None,
                "last_synced_at": datetime.now(UTC).isoformat(),
            },
            session_id=session_id,
        )
        return MeetingTranscriptSyncResponse(status="synced", session=updated)

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
        if not self._has_minutes_source(detail):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add notes, import a transcript, capture agenda items, or record artifacts before generating minutes.",
            )
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
        meeting_id = session["meeting_id"]
        attendees = self._repo.get_attendees(meeting_id)
        recipients = self._attendee_emails(attendees)
        if not recipients:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Add at least one attendee with an email address before sending minutes.",
            )

        meeting = session.get("meetings") or {}
        subject = f"Minutes: {self._mask_pii(meeting.get('name') or 'Meeting')}"
        delivery = self._email.deliver(
            to=recipients,
            subject=subject,
            text=self._minutes_email_text(session, minutes),
        )
        if delivery.status == "queued" and delivery.detail == "email_not_configured":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Email delivery is not configured.",
            )
        if delivery.status != "sent":
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Minutes email could not be sent.",
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

    @staticmethod
    def _normalized_workstream_ids(
        workstream_ids: list[str] | None,
        legacy_workstream_id: str | None,
    ) -> list[str]:
        values = workstream_ids if workstream_ids is not None else []
        if legacy_workstream_id and not values:
            values = [legacy_workstream_id]
        return list(dict.fromkeys([str(value) for value in values if value]))

    @staticmethod
    def _normalized_ids(values: list[str]) -> list[str]:
        return list(dict.fromkeys([str(value) for value in values if value]))

    def _normalize_schedule_payload(self, payload: dict, partial: bool = False) -> None:
        if "start_time" in payload:
            parsed_time = self._parse_time(str(payload["start_time"]))
            payload["start_time"] = parsed_time.strftime("%H:%M")
        elif not partial:
            payload["start_time"] = "09:00"

        if "timezone" in payload:
            payload["timezone"] = self._validate_timezone(str(payload["timezone"]))
        elif not partial:
            payload["timezone"] = "UTC"

        if "one_off_date" in payload and payload["one_off_date"]:
            one_off = self._parse_date(str(payload["one_off_date"]), "one_off_date")
            payload["one_off_date"] = one_off.isoformat()
            if payload.get("recurrence") == "ad_hoc" and payload.get("day_of_week") is None:
                payload["day_of_week"] = one_off.weekday()

        if "series_end_date" in payload and payload["series_end_date"]:
            series_end = self._parse_date(str(payload["series_end_date"]), "series_end_date")
            payload["series_end_date"] = series_end.isoformat()
        elif not partial and payload.get("recurrence") != "ad_hoc":
            payload["series_end_date"] = None

        if not partial and payload.get("day_of_week") is None:
            payload["day_of_week"] = date.today().weekday()

    def _ensure_session(self, meeting: dict, session_date: date) -> dict:
        existing = self._repo.get_session_by_date(meeting["id"], session_date.isoformat())
        if existing:
            self._materialize_session(existing)
            return existing
        session = self._create_scheduled_session(meeting, session_date, "scheduled")
        self._materialize_session(session)
        return session

    def _create_scheduled_session(
        self, meeting: dict, session_date: date, status_value: str
    ) -> dict:
        start_at, end_at = self._session_datetimes(meeting, session_date)
        return self._repo.create_session(
            meeting["id"],
            session_date.isoformat(),
            {
                "status": status_value,
                "scheduled_start_at": start_at.isoformat(),
                "scheduled_end_at": end_at.isoformat(),
            },
        )

    def _materialize_session(self, session: dict) -> None:
        self._repo.snapshot_session_agenda(session, self._repo.get_agenda(session["meeting_id"]))
        self._repo.snapshot_session_attendees(
            session, self._repo.get_attendees(session["meeting_id"])
        )

    def _session_window_dates(self, meeting: dict, anchor: date, page_size: int) -> list[date]:
        recurrence = meeting.get("recurrence") or "weekly"
        if recurrence == "ad_hoc":
            one_off = meeting.get("one_off_date") or meeting.get("created_at", "")[:10]
            return [self._parse_date(str(one_off or anchor.isoformat()), "one_off_date")]
        if recurrence == "monthly":
            return self._monthly_window_dates(meeting, anchor, page_size)

        interval_days = 14 if recurrence == "biweekly" else 7
        target_weekday = self._meeting_weekday(meeting, anchor)
        current = anchor + timedelta(days=(target_weekday - anchor.weekday()) % 7)
        while current >= anchor:
            current -= timedelta(days=interval_days)
        previous_dates = [
            current - timedelta(days=interval_days * index) for index in range(page_size)
        ]
        previous_dates.reverse()
        next_start = current + timedelta(days=interval_days)
        next_dates = [
            next_start + timedelta(days=interval_days * index) for index in range(page_size)
        ]
        return [*previous_dates, *next_dates]

    def _monthly_window_dates(self, meeting: dict, anchor: date, page_size: int) -> list[date]:
        target_weekday = self._meeting_weekday(meeting, anchor)
        months: list[date] = []
        for offset in range(-page_size - 1, page_size + 2):
            first = self._add_months(date(anchor.year, anchor.month, 1), offset)
            candidate = first + timedelta(days=(target_weekday - first.weekday()) % 7)
            months.append(candidate)
        previous_dates = [item for item in months if item < anchor][-page_size:]
        next_dates = [item for item in months if item >= anchor][:page_size]
        return [*previous_dates, *next_dates]

    @staticmethod
    def _add_months(value: date, months: int) -> date:
        month_index = value.month - 1 + months
        year = value.year + month_index // 12
        month = month_index % 12 + 1
        return date(year, month, 1)

    @staticmethod
    def _meeting_weekday(meeting: dict, anchor: date) -> int:
        value = meeting.get("day_of_week")
        if value is None:
            return anchor.weekday()
        return int(value)

    def _session_datetimes(self, meeting: dict, session_date: date) -> tuple[datetime, datetime]:
        start_time = self._parse_time(str(meeting.get("start_time") or "09:00"))
        tz = ZoneInfo(self._validate_timezone(str(meeting.get("timezone") or "UTC")))
        start_local = datetime.combine(session_date, start_time, tzinfo=tz)
        duration = int(meeting.get("duration_minutes") or 60)
        end_local = start_local + timedelta(minutes=duration)
        return start_local.astimezone(UTC), end_local.astimezone(UTC)

    @staticmethod
    def _parse_date(value: str, field_name: str) -> date:
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{field_name} must use YYYY-MM-DD format.",
            ) from exc

    @staticmethod
    def _parse_time(value: str) -> time:
        try:
            return time.fromisoformat(value[:5])
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_time must use HH:MM format.",
            ) from exc

    @staticmethod
    def _validate_timezone(value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="timezone must be a valid IANA timezone.",
            ) from exc
        return value

    @staticmethod
    def _dedupe_by_id(items: list[dict]) -> list[dict]:
        seen: set[str] = set()
        deduped: list[dict] = []
        for item in items:
            item_id = item.get("id")
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            deduped.append(item)
        return deduped

    def _deterministic_agenda_suggestions(
        self,
        *,
        meeting: dict,
        initiatives: list[dict],
        open_actions: list[dict],
        risks: list[dict],
        milestones: list[dict],
    ) -> list[AgendaSuggestion]:
        suggestions: list[AgendaSuggestion] = []
        for action in open_actions[:4]:
            initiative = action.get("initiatives") or {}
            suggestions.append(
                AgendaSuggestion(
                    text=self._mask_pii(f"Close carry-forward action: {action.get('description')}"),
                    initiative_id=action.get("initiative_id"),
                    rationale="Open action item carried forward from an earlier session.",
                    source_type="carry_forward_action",
                )
            )
            if initiative.get("initiative_code"):
                suggestions[-1].rationale += f" Linked to {initiative['initiative_code']}."

        for initiative in initiatives:
            rag = initiative.get("rag_status")
            stage = initiative.get("stage")
            code = initiative.get("initiative_code") or "Initiative"
            name = initiative.get("name") or "unnamed initiative"
            if rag in {"red", "amber"}:
                suggestions.append(
                    AgendaSuggestion(
                        text=self._mask_pii(f"Resolve {rag} status for {code} - {name}"),
                        initiative_id=initiative.get("id"),
                        rationale="Selected workstream or linked initiative is not green.",
                        source_type="workstream_initiative",
                    )
                )
            elif stage != "complete":
                suggestions.append(
                    AgendaSuggestion(
                        text=self._mask_pii(
                            f"Confirm next milestone and owner for {code} - {name}"
                        ),
                        initiative_id=initiative.get("id"),
                        rationale="Active initiative in a selected workstream needs forward-looking review.",
                        source_type="workstream_initiative",
                    )
                )

        for risk in risks[:3]:
            initiative = risk.get("initiatives") or {}
            code = initiative.get("initiative_code") or "initiative"
            suggestions.append(
                AgendaSuggestion(
                    text=self._mask_pii(
                        f"Mitigate open risk for {code}: {risk.get('description')}"
                    ),
                    initiative_id=risk.get("initiative_id"),
                    rationale="Recent open risk is tied to this meeting's initiatives.",
                    source_type="risk",
                )
            )

        for milestone in milestones[:3]:
            initiative = milestone.get("initiatives") or {}
            code = initiative.get("initiative_code") or "initiative"
            due = f" due {milestone.get('planned_end')}" if milestone.get("planned_end") else ""
            suggestions.append(
                AgendaSuggestion(
                    text=self._mask_pii(
                        f"Review upcoming milestone for {code}: {milestone.get('name')}{due}"
                    ),
                    initiative_id=milestone.get("initiative_id"),
                    rationale="Upcoming or incomplete milestone is relevant to this meeting.",
                    source_type="milestone",
                )
            )

        if not suggestions:
            workstream_names = ", ".join(
                [item.get("name") for item in meeting.get("workstreams") or [] if item.get("name")]
            )
            text = (
                f"Confirm priorities, blockers, and owners for {workstream_names}"
                if workstream_names
                else "Confirm decisions, blockers, and owners for the next review period"
            )
            suggestions.append(
                AgendaSuggestion(
                    text=self._mask_pii(text),
                    rationale="Fallback suggestion because no open actions, risks, milestones, or active initiatives were found.",
                    source_type="fallback",
                )
            )

        deduped: list[AgendaSuggestion] = []
        seen_text: set[str] = set()
        for suggestion in suggestions:
            key = suggestion.text.lower()
            if key in seen_text:
                continue
            seen_text.add(key)
            deduped.append(suggestion)
        return deduped

    @staticmethod
    def _agenda_trace_id() -> str:
        langfuse = _get_langfuse()
        if langfuse:
            return langfuse.create_trace_id(seed=f"meeting-agenda-suggestions-{uuid4()}")
        return f"deterministic-meeting-agenda-suggestions-{uuid4()}"

    def _trace_agenda_suggestions(
        self,
        meeting: dict,
        response: AgendaSuggestionsResponse,
    ) -> AgendaSuggestionsResponse:
        langfuse = _get_langfuse()
        if not langfuse or not response.trace_id:
            return response
        try:
            with langfuse.start_as_current_observation(
                name="meeting_agenda_suggestions",
                as_type="agent",
                trace_context=TraceContext(trace_id=response.trace_id),
                input={
                    "meeting_id": meeting.get("id"),
                    "workstream_count": len(meeting.get("workstreams") or []),
                },
                metadata={"source": "deterministic_agenda_suggestions"},
                model=settings.default_model,
            ):
                response.trace_url = langfuse.get_trace_url(trace_id=response.trace_id)
                langfuse.update_current_span(output=response.model_dump(mode="json"))
            langfuse.flush()
        except Exception:
            response.trace_url = None
        return response

    @staticmethod
    def _has_minutes_source(detail: dict) -> bool:
        return any(
            [
                str(detail.get("notes") or "").strip(),
                str(detail.get("transcript_text") or "").strip(),
                bool(detail.get("agenda")),
                bool(detail.get("artifacts")),
            ]
        )

    def _build_minutes(self, detail: dict) -> str:
        meeting = detail.get("meetings") or {}
        agenda = detail.get("agenda") or []
        artifacts = detail.get("artifacts") or []
        action_items = detail.get("action_items") or []
        notes = self._mask_pii(detail.get("notes") or "")
        transcript = self._mask_pii(detail.get("transcript_text") or "")

        def artifact_lines(kind: str) -> list[str]:
            rows = [a for a in artifacts if a.get("artifact_type") == kind]
            return [
                f"- {self._mask_pii(a.get('title') or '')}"
                + (f" ({a.get('status')})" if a.get("status") else "")
                for a in rows
            ] or ["- None captured."]

        def action_lines() -> list[str]:
            rows = artifacts_for_type("action") + [
                {
                    "title": item.get("description"),
                    "status": item.get("status"),
                    "priority": item.get("priority"),
                }
                for item in action_items
            ]
            return [
                f"- {self._mask_pii(item.get('title') or item.get('description') or '')}"
                + (f" ({item.get('status')})" if item.get("status") else "")
                + (f" [{item.get('priority')}]" if item.get("priority") else "")
                for item in rows
            ] or ["- None captured."]

        def artifacts_for_type(kind: str) -> list[dict]:
            return [item for item in artifacts if item.get("artifact_type") == kind]

        def artifacts_for_agenda(agenda_id: str | None, kind: str | None = None) -> list[str]:
            if not agenda_id:
                return []
            rows = [
                item
                for item in artifacts
                if item.get("agenda_item_id") == agenda_id
                and (kind is None or item.get("artifact_type") == kind)
            ]
            return [
                f"- {self._mask_pii(item.get('title') or '')}"
                + (f" ({item.get('status')})" if item.get("status") else "")
                for item in rows
            ]

        agenda_lines = [
            f"- {item.get('text')}"
            + (
                f" [{(item.get('initiatives') or {}).get('initiative_code')}]"
                if item.get("initiatives")
                else ""
            )
            for item in agenda
        ] or ["- No agenda items recorded."]

        summary_lines = self._minutes_summary_lines(notes, transcript)
        agenda_sections = self._agenda_minutes_sections(
            agenda,
            notes,
            transcript,
            artifacts_for_agenda,
        )

        return "\n".join(
            [
                f"# Minutes: {self._mask_pii(meeting.get('name') or 'Meeting')}",
                "",
                f"Session date: {detail.get('session_date')}",
                "",
                "## AI Summary",
                *summary_lines,
                "",
                "## Agenda",
                *agenda_lines,
                "",
                "## Agenda Discussion",
                *agenda_sections,
                "",
                "## Decisions",
                *artifact_lines("decision"),
                "",
                "## Actions",
                *action_lines(),
                "",
                "## Risks And Issues",
                *artifact_lines("risk"),
                *artifact_lines("issue"),
                "",
                "## Assumptions",
                *artifact_lines("assumption"),
                "",
                "## Source Coverage",
                f"- Captured notes: {'included' if notes else 'not captured'}.",
                f"- Imported transcript: {'summarized' if transcript else 'not imported'}.",
            ]
        )

    def _minutes_summary_lines(self, notes: str, transcript: str) -> list[str]:
        sentences = self._source_sentences(notes, transcript)
        if not sentences:
            return ["- No notes or transcript content available for summary."]
        return [f"- {self._synthesis_sentence(sentence)}" for sentence in sentences[:5]]

    def _agenda_minutes_sections(
        self,
        agenda: list[dict],
        notes: str,
        transcript: str,
        artifacts_for_agenda: object,
    ) -> list[str]:
        sentences = self._source_sentences(notes, transcript)
        if not agenda:
            bullets = [f"- {self._synthesis_sentence(sentence)}" for sentence in sentences[:6]]
            return [
                "### General Discussion",
                *(bullets or ["- No discussion captured."]),
            ]

        sections: list[str] = []
        used_indexes: set[int] = set()
        for item in agenda:
            title = self._mask_pii(str(item.get("text") or "Agenda item"))
            agenda_id = item.get("id") or item.get("source_agenda_item_id")
            matched = self._sentences_for_agenda(title, sentences)
            for index, _score, _sentence in matched:
                used_indexes.add(index)
            discussion_bullets = [
                f"- {self._synthesis_sentence(sentence)}"
                for _index, _score, sentence in matched[:4]
            ] or ["- No specific transcript or note content was captured for this agenda item."]
            sections.extend(
                [
                    f"### {title}",
                    *discussion_bullets,
                ]
            )
            agenda_artifacts = artifacts_for_agenda(agenda_id)
            if agenda_artifacts:
                sections.extend(["", "Captured items:", *agenda_artifacts])
            sections.append("")

        unassigned = [
            sentence for index, sentence in enumerate(sentences) if index not in used_indexes
        ][:4]
        if unassigned:
            sections.extend(
                [
                    "### Additional Discussion",
                    *[f"- {self._synthesis_sentence(sentence)}" for sentence in unassigned],
                ]
            )
        return sections

    def _sentences_for_agenda(
        self,
        agenda_title: str,
        sentences: list[str],
    ) -> list[tuple[int, int, str]]:
        agenda_terms = self._summary_terms(agenda_title)
        scored: list[tuple[int, int, str]] = []
        for index, sentence in enumerate(sentences):
            sentence_terms = self._summary_terms(sentence)
            score = len(agenda_terms & sentence_terms)
            if score:
                scored.append((index, score, sentence))
        return sorted(scored, key=lambda item: (-item[1], item[0]))

    def _source_sentences(self, notes: str, transcript: str) -> list[str]:
        chunks = []
        if notes.strip():
            chunks.append(notes)
        if transcript.strip():
            chunks.append(transcript)
        text = "\n".join(chunks)
        raw_sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
        sentences: list[str] = []
        for sentence in raw_sentences:
            cleaned = self._clean_minutes_sentence(sentence)
            if len(cleaned) >= 12 and cleaned not in sentences:
                sentences.append(cleaned)
        return sentences

    def _clean_minutes_sentence(self, sentence: str) -> str:
        cleaned = self._mask_pii(sentence)
        cleaned = re.sub(r"^\s*[\w .'-]{1,48}:\s*", "", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -\t")
        return cleaned

    def _synthesis_sentence(self, sentence: str) -> str:
        cleaned = self._clean_minutes_sentence(sentence)
        if len(cleaned) > 220:
            cleaned = cleaned[:220].rsplit(" ", 1)[0] + "..."
        if not cleaned:
            return "No substantive discussion captured."
        return f"Discussed {cleaned[0].lower()}{cleaned[1:]}"

    @staticmethod
    def _summary_terms(text: str) -> set[str]:
        stop_words = {
            "about",
            "after",
            "again",
            "agenda",
            "also",
            "and",
            "are",
            "for",
            "from",
            "have",
            "into",
            "item",
            "meeting",
            "next",
            "not",
            "our",
            "review",
            "session",
            "that",
            "the",
            "this",
            "with",
        }
        return {
            word for word in re.findall(r"[a-z0-9]{4,}", text.lower()) if word not in stop_words
        }

    @staticmethod
    def _mask_pii(text: str) -> str:
        text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.-]+", "[email]", text)
        text = re.sub(r"\+?\d[\d\s().-]{7,}\d", "[phone]", text)
        return text

    @staticmethod
    def _attendee_emails(attendees: list[dict]) -> list[str]:
        recipients: list[str] = []
        for attendee in attendees:
            user = attendee.get("users") if isinstance(attendee.get("users"), dict) else {}
            email = user.get("email") if isinstance(user, dict) else None
            if isinstance(email, str):
                recipients.append(email)
        return recipients

    def _minutes_email_text(self, session: dict, minutes: str) -> str:
        meeting = session.get("meetings") or {}
        meeting_name = self._mask_pii(meeting.get("name") or "Meeting")
        session_date = session.get("session_date") or "not recorded"
        return "\n".join(
            [
                f"Minutes for {meeting_name}",
                f"Session date: {session_date}",
                "",
                minutes,
                "",
                "Sent from Transmuter.",
            ]
        )

    def _import_graph_transcript(self, session: dict) -> str:
        # Graph transcript retrieval requires the provider event/meeting id and tenant permissions.
        # The endpoint remains non-blocking until those credentials are configured.
        return ""

    def _microsoft_external_event(
        self, meeting_id: str, session_id: str | None = None
    ) -> dict | None:
        events = self._repo.get_external_events(meeting_id, session_id)
        synced = [
            event
            for event in events
            if event.get("provider") == "microsoft"
            and (event.get("online_meeting_id") or event.get("join_url"))
        ]
        if session_id:
            session_events = [event for event in synced if event.get("session_id") == session_id]
            if session_events:
                return session_events[0]
        return synced[0] if synced else None

    @staticmethod
    def _meeting_invite_subject(meeting: dict, session: dict | None) -> dict:
        if not session:
            return meeting
        return {
            **meeting,
            "name": f"{meeting.get('name') or 'Meeting'} - {session.get('session_date')}",
        }

    def _microsoft_connection_for_event(self, event: dict) -> dict | None:
        connection_id = event.get("integration_connection_id")
        repo = self._integration_secret_repo()
        if connection_id:
            connection = repo.get_integration_connection_by_id(str(connection_id))
            if connection:
                return connection
        return repo.get_integration_connection("microsoft_graph", event.get("organizer_email"))

    def _integration_secret_repo(self) -> MeetingRepository:
        return getattr(self, "_secret_repo", self._repo)

    @staticmethod
    def _validate_external_event_schedule(data: MeetingExternalEventCreate) -> None:
        start = MeetingService._parse_event_datetime(data.start_date_time)
        end = MeetingService._parse_event_datetime(data.end_date_time)
        if end <= start:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="end_date_time must be after start_date_time.",
            )
        if data.series_end_date:
            series_end = MeetingService._parse_date(data.series_end_date, "series_end_date")
            if series_end < start.date():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="series_end_date must be on or after start_date_time.",
                )

    @staticmethod
    def _parse_event_datetime(value: str) -> datetime:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="start_date_time and end_date_time must be ISO datetime strings.",
            ) from exc
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)

    @staticmethod
    def _graph_recurrence(
        meeting: dict,
        data: MeetingExternalEventCreate,
        session_id: str | None,
    ) -> dict | None:
        if session_id or meeting.get("recurrence") == "ad_hoc":
            return None
        series_end_date = data.series_end_date or meeting.get("series_end_date")
        if not series_end_date:
            return None
        start = MeetingService._parse_event_datetime(data.start_date_time).date()
        end = MeetingService._parse_date(str(series_end_date), "series_end_date")
        day_name = MeetingService._graph_weekday(int(meeting.get("day_of_week") or start.weekday()))
        recurrence = meeting.get("recurrence") or "weekly"
        if recurrence == "monthly":
            pattern = {
                "type": "relativeMonthly",
                "interval": 1,
                "daysOfWeek": [day_name],
                "index": "first",
            }
        else:
            pattern = {
                "type": "weekly",
                "interval": 2 if recurrence == "biweekly" else 1,
                "daysOfWeek": [day_name],
            }
        return {
            "pattern": pattern,
            "range": {
                "type": "endDate",
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "recurrenceTimeZone": data.time_zone or meeting.get("timezone") or "UTC",
            },
        }

    @staticmethod
    def _graph_weekday(day_of_week: int) -> str:
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        return days[day_of_week % 7]

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
