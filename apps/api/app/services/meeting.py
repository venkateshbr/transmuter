import re
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

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
    MeetingUpdate,
    SessionStartRequest,
    SessionUpdate,
)
from app.domain.risks import RiskCreate, RiskUpdate
from app.repositories.meeting import MeetingRepository
from app.services.email_delivery import EmailDeliveryService
from app.services.risk import RiskService


class MeetingService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._repo = MeetingRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._email = EmailDeliveryService()

    def list_meetings(self) -> list[dict]:
        return self._repo.list()

    def create_meeting(self, data: MeetingCreate) -> dict:
        payload = data.model_dump(exclude_none=True)
        workstream_ids = self._normalized_workstream_ids(
            payload.pop("workstream_ids", []),
            payload.get("workstream_id"),
        )
        payload["workstream_id"] = workstream_ids[0] if workstream_ids else None
        meeting = self._repo.create(payload)
        if meeting:
            self._repo.set_workstreams(meeting["id"], workstream_ids)
            meeting = self._repo.get(meeting["id"]) or meeting
        return meeting

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
        workstream_ids_provided = (
            "workstream_ids" in data.model_fields_set or "workstream_id" in data.model_fields_set
        )
        workstream_ids = self._normalized_workstream_ids(
            payload.pop("workstream_ids", None),
            payload.get("workstream_id"),
        )
        if workstream_ids_provided:
            payload["workstream_id"] = workstream_ids[0] if workstream_ids else None
        if not payload:
            if workstream_ids_provided:
                self._repo.set_workstreams(meeting_id, workstream_ids)
            return self.get_meeting_detail(meeting_id)
        self._repo.update(meeting_id, payload)
        if workstream_ids_provided:
            self._repo.set_workstreams(meeting_id, workstream_ids)
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
        response = AgendaSuggestionsResponse(items=suggestions[:12], trace_id=self._agenda_trace_id())
        return self._trace_agenda_suggestions(meeting, response)

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

    def start_session(self, meeting_id: str, data: SessionStartRequest | None = None) -> dict:
        self._assert_meeting(meeting_id)
        session_date = (data.session_date if data else None) or date.today().isoformat()
        try:
            date.fromisoformat(session_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="session_date must use YYYY-MM-DD format.",
            ) from exc

        existing = self._repo.get_session_by_date(meeting_id, session_date)
        if existing:
            return existing
        return self._repo.create_session(meeting_id, session_date)

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
                        text=self._mask_pii(f"Confirm next milestone and owner for {code} - {name}"),
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
                    text=self._mask_pii(f"Mitigate open risk for {code}: {risk.get('description')}"),
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
