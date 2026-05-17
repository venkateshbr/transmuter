"""Workflow service for HITL agent runs."""

from __future__ import annotations

import json
import time
from contextlib import suppress
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.agents.initiative_intake_agent import (
    extract_initiative_fields,
    scan_risk_patterns,
    suggest_kpis,
)
from app.agents.meeting_notes_agent import (
    chunk_transcript,
    extract_action_items,
    extract_meeting_decisions,
)
from app.domain.initiative_intake import (
    InitiativeDraft,
    InitiativeIntakeCreate,
    InitiativeIntakeSuggestions,
    SuggestedKPI,
    SuggestedRisk,
)
from app.domain.meeting_notes import (
    InitiativeStatusSignal,
    LinkedInitiativeContext,
    MeetingActionItemSuggestion,
    MeetingAttendeeContext,
    MeetingDecision,
    MeetingNotesWorkflowReview,
    MeetingTranscriptUpload,
)
from app.domain.meetings import ActionItemCreate, SessionUpdate
from app.domain.status_updates import StatusUpdateCreate
from app.domain.workflows import (
    InitiativeIntakeWorkflowStart,
    WorkflowApproveRequest,
    WorkflowApproveResponse,
    WorkflowRejectRequest,
    WorkflowRejectResponse,
    WorkflowReview,
    WorkflowRunCreated,
    WorkflowStatus,
)
from app.repositories.workflow import WorkflowRepository
from app.services.initiative import InitiativeService
from app.services.meeting import MeetingService
from app.services.status_update import StatusUpdateService


class WorkflowService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._client = client
        self._tenant_id = tenant_id
        self._repo = WorkflowRepository(client, tenant_id)

    async def start_initiative_intake(
        self,
        body: InitiativeIntakeWorkflowStart,
        submitter_user_id: UUID,
    ) -> WorkflowRunCreated:
        run = self._repo.create_initiative_intake_run(submitter_user_id, body.raw_text)
        run_id = run["id"]
        try:
            started = time.perf_counter()
            extraction = await extract_initiative_fields(body.raw_text)
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="karya",
                skill_name="initiative_field_extraction",
                action="extract_fields",
                input_summary=_summarize(body.raw_text),
                output_summary=_summarize(extraction.draft.model_dump_json(exclude_none=True)),
                confidence=extraction.confidence,
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )

            draft = extraction.draft
            self._repo.update_run(
                run_id,
                {
                    "status": "suggesting",
                    "extracted_draft": draft.model_dump(mode="json", exclude_none=True),
                },
            )

            started = time.perf_counter()
            kpis = suggest_kpis(
                initiative_type=draft.type,
                initiative_name=draft.name,
                value_logic=draft.value_logic,
            )
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="karya",
                skill_name="kpi_suggestion",
                action="suggest_kpis",
                input_summary=_summarize(draft.model_dump_json(exclude_none=True)),
                output_summary=f"{len(kpis.suggestions)} KPI suggestions generated",
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )

            started = time.perf_counter()
            risks = scan_risk_patterns(draft)
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="karya",
                skill_name="risk_pattern_scan",
                action="scan_risk_patterns",
                input_summary=_summarize(draft.model_dump_json(exclude_none=True)),
                output_summary=f"{len(risks.risks)} risk suggestions generated",
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )

            run = self._repo.update_run(
                run_id,
                {
                    "status": "awaiting_review",
                    "kpi_suggestions": [
                        item.model_dump(mode="json", exclude_none=True) for item in kpis.suggestions
                    ],
                    "risk_suggestions": [
                        item.model_dump(mode="json", exclude_none=True) for item in risks.risks
                    ],
                },
            )
        except Exception as exc:
            run = self._repo.update_run(run_id, {"status": "failed", "error": str(exc)})
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="karya",
                skill_name="initiative_intake_workflow",
                action="workflow_failed",
                input_summary=_summarize(body.raw_text),
                output_summary=_summarize(str(exc)),
                requires_review=True,
            )

        return WorkflowRunCreated(
            workflow_run_id=run["id"],
            status=run["status"],
            expires_at=_parse_datetime(run["expires_at"]),
        )

    def start_meeting_notes_extraction(
        self,
        *,
        meeting_id: str,
        session_id: str,
        body: MeetingTranscriptUpload,
        submitter_user_id: UUID,
    ) -> WorkflowRunCreated:
        meeting_service = MeetingService(self._client, self._tenant_id)
        session = meeting_service.get_session_for_meeting(meeting_id, session_id)
        meeting_service.update_session(
            session_id,
            SessionUpdate(transcript_text=body.transcript_text, has_transcript=True),
        )
        run = self._repo.create_meeting_notes_run(
            meeting_id=meeting_id,
            session_id=session_id,
            submitter_user_id=submitter_user_id,
            transcript_text=body.transcript_text,
        )
        run_id = run["id"]
        try:
            started = time.perf_counter()
            chunks = chunk_transcript(body.transcript_text)
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="netra",
                skill_name="transcript_chunking",
                action="chunk_transcript",
                input_summary=_summarize(body.transcript_text),
                output_summary=f"{len(chunks.chunks)} transcript chunks generated",
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )
            self._repo.update_meeting_notes_run(
                run_id,
                {
                    "status": "extracting",
                    "chunks": [item.model_dump(mode="json") for item in chunks.chunks],
                },
            )

            attendees = _attendees_from_session(session)
            initiatives = _initiatives_from_session(session)

            started = time.perf_counter()
            action_items = extract_action_items(chunks.chunks, attendees)
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="netra",
                skill_name="action_item_extraction",
                action="extract_action_items",
                input_summary=f"{len(chunks.chunks)} chunks, {len(attendees)} attendees",
                output_summary=f"{len(action_items.action_items)} action item suggestions",
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )

            started = time.perf_counter()
            decisions = extract_meeting_decisions(chunks.chunks, initiatives)
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="netra",
                skill_name="meeting_decisions_extraction",
                action="extract_decisions",
                input_summary=f"{len(chunks.chunks)} chunks, {len(initiatives)} linked initiatives",
                output_summary=(
                    f"{len(decisions.decisions)} decisions, "
                    f"{len(decisions.initiative_updates)} initiative updates"
                ),
                latency_ms=_elapsed_ms(started),
                requires_review=True,
            )
            run = self._repo.update_meeting_notes_run(
                run_id,
                {
                    "status": "awaiting_review",
                    "action_items": [
                        item.model_dump(mode="json", exclude_none=True)
                        for item in action_items.action_items
                    ],
                    "decisions": [
                        item.model_dump(mode="json", exclude_none=True)
                        for item in decisions.decisions
                    ],
                    "initiative_updates": [
                        item.model_dump(mode="json", exclude_none=True)
                        for item in decisions.initiative_updates
                    ],
                },
            )
        except Exception as exc:
            run = self._repo.update_meeting_notes_run(run_id, {"status": "failed", "error": str(exc)})
            self._repo.insert_audit_log(
                workflow_run_id=run_id,
                agent_id="karya",
                skill_name="meeting_notes_extraction",
                action="workflow_failed",
                input_summary=f"Session {session_id}",
                output_summary=_summarize(str(exc)),
                requires_review=True,
            )
        return WorkflowRunCreated(
            workflow_run_id=run["id"],
            status=run["status"],
            expires_at=_parse_datetime(run["expires_at"]),
        )

    def get_status(self, run_id: UUID) -> WorkflowStatus:
        run = self._get_run_or_404(run_id)
        run = self._expire_if_needed(run)
        return WorkflowStatus(
            workflow_run_id=run["id"],
            status=run["status"],
            expires_at=_parse_datetime(run["expires_at"]),
            created_initiative_id=run.get("created_initiative_id"),
            error=run.get("error"),
        )

    def get_review(self, run_id: UUID) -> WorkflowReview | MeetingNotesWorkflowReview:
        run = self._expire_if_needed(self._get_run_or_404(run_id))
        if run["status"] != "awaiting_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow is {run['status']} and cannot be reviewed.",
            )
        if run.get("workflow_type") == "meeting_notes_extraction":
            return MeetingNotesWorkflowReview(
                workflow_run_id=str(run["id"]),
                status=run["status"],
                expires_at=str(run["expires_at"]),
                session_id=str(run["session_id"]),
                meeting_id=str(run["meeting_id"]),
                action_items=run.get("action_items") or [],
                decisions=run.get("decisions") or [],
                initiative_updates=run.get("initiative_updates") or [],
            )
        draft = InitiativeDraft.model_validate(run.get("extracted_draft") or {})
        return WorkflowReview(
            workflow_run_id=run["id"],
            status=run["status"],
            expires_at=_parse_datetime(run["expires_at"]),
            extracted_draft=draft,
            field_confidence=_field_confidence(draft),
            kpi_suggestions=run.get("kpi_suggestions") or [],
            risk_suggestions=run.get("risk_suggestions") or [],
        )

    def approve(self, run_id: UUID, body: WorkflowApproveRequest, approved_by: UUID) -> Any:
        run = self._expire_if_needed(self._get_run_or_404(run_id))
        if run["status"] != "awaiting_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow is {run['status']} and cannot be approved.",
            )

        if run.get("workflow_type") == "meeting_notes_extraction":
            return self._approve_meeting_notes(run, body, approved_by)

        if body.initiative is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Initiative payload is required for initiative workflow approval.",
            )
        suggestions = body.suggestions or self._suggestions_from_run(run)
        self._record_initiative_corrections(run, body, suggestions, approved_by)
        initiative = InitiativeService(self._client, self._tenant_id).create_from_intake(
            InitiativeIntakeCreate(initiative=body.initiative, suggestions=suggestions),
            approved_by,
        )
        self._repo.update_run(
            run_id,
            {
                "status": "approved",
                "created_initiative_id": str(initiative.id),
                "approved_at": datetime.now(UTC).isoformat(),
            },
        )
        self._repo.insert_audit_log(
            workflow_run_id=run_id,
            agent_id="vishwa",
            skill_name="initiative_intake_workflow",
            action="approve_workflow",
            input_summary=f"Approved workflow {run_id}",
            output_summary=f"Created initiative {initiative.id}",
            requires_review=False,
            human_action="approved",
        )
        return WorkflowApproveResponse(
            workflow_run_id=run_id,
            status="approved",
            initiative=initiative,
        )

    def reject(
        self,
        run_id: UUID,
        body: WorkflowRejectRequest,
        rejected_by: UUID,
    ) -> WorkflowRejectResponse:
        run = self._expire_if_needed(self._get_run_or_404(run_id))
        if run["status"] != "awaiting_review":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Workflow is {run['status']} and cannot be rejected.",
            )
        if run.get("workflow_type") == "meeting_notes_extraction":
            self._record_full_rejection(run, body.reason, rejected_by)
            self._repo.update_meeting_notes_run(
                run_id,
                {
                    "status": "rejected",
                    "rejected_at": datetime.now(UTC).isoformat(),
                    "error": body.reason,
                },
            )
        else:
            self._record_full_rejection(run, body.reason, rejected_by)
            self._repo.update_run(
                run_id,
                {
                    "status": "rejected",
                    "rejected_at": datetime.now(UTC).isoformat(),
                    "error": body.reason,
                },
            )
        self._repo.insert_audit_log(
            workflow_run_id=run_id,
            agent_id="vishwa",
            skill_name="initiative_intake_workflow",
            action="reject_workflow",
            input_summary=f"Rejected workflow {run_id}",
            output_summary=_summarize(body.reason or "Rejected without comment"),
            requires_review=False,
            human_action="rejected",
        )
        return WorkflowRejectResponse(workflow_run_id=run_id, status="rejected")

    def _get_run_or_404(self, run_id: UUID) -> dict[str, Any]:
        run = self._repo.get_run(run_id)
        if run:
            run["workflow_type"] = "initiative_intake"
            return run
        run = self._repo.get_meeting_notes_run(run_id)
        if run:
            run["workflow_type"] = "meeting_notes_extraction"
            return run
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")

    def _expire_if_needed(self, run: dict[str, Any]) -> dict[str, Any]:
        if run["status"] != "awaiting_review":
            return run
        if _parse_datetime(run["expires_at"]) > datetime.now(UTC):
            return run
        if run.get("workflow_type") == "meeting_notes_extraction":
            updated = self._repo.update_meeting_notes_run(run["id"], {"status": "expired"})
            updated["workflow_type"] = "meeting_notes_extraction"
        else:
            updated = self._repo.update_run(run["id"], {"status": "expired"})
            updated["workflow_type"] = "initiative_intake"
        self._repo.insert_audit_log(
            workflow_run_id=run["id"],
            agent_id="sthira",
            skill_name="initiative_intake_workflow",
            action="expire_workflow",
            input_summary=f"Workflow {run['id']} exceeded review SLA",
            output_summary="Workflow expired after 48 hours without approval",
            requires_review=False,
        )
        return updated

    def _approve_meeting_notes(
        self,
        run: dict[str, Any],
        body: WorkflowApproveRequest,
        approved_by: UUID,
    ) -> dict[str, Any]:
        meeting_service = MeetingService(self._client, self._tenant_id)
        session_id = str(run["session_id"])
        self._record_meeting_notes_corrections(run, body, approved_by)
        action_ids: list[str] = []
        for item in _approved_action_items(body.action_items or run.get("action_items") or []):
            created = meeting_service.create_action_item(
                session_id,
                ActionItemCreate(
                    description=item.description,
                    assignee_id=item.suggested_assignee_id,
                    priority=item.priority,
                    due_date=item.due_date if _is_iso_date(item.due_date) else None,
                ),
            )
            if created.get("id"):
                action_ids.append(created["id"])

        decisions = _approved_decisions(body.decisions or run.get("decisions") or [])
        updates = _approved_updates(body.initiative_updates or run.get("initiative_updates") or [])
        if decisions or updates:
            session = meeting_service.get_session_detail(session_id)
            meeting_service.update_session(
                session_id,
                SessionUpdate(
                    notes=_append_meeting_notes(
                        session.get("notes"),
                        decisions=decisions,
                        updates=updates,
                    )
                ),
            )
        status_service = StatusUpdateService(self._client, self._tenant_id, approved_by)
        for update in updates:
            if not update.initiative_id:
                continue
            with suppress(HTTPException):
                status_service.create_update(
                    update.initiative_id,
                    StatusUpdateCreate(
                        rag_status=update.rag_status,
                        summary=update.summary,
                        is_draft=True,
                    ),
                )

        meeting_service.update_session(
            session_id,
            SessionUpdate(has_transcript=True, ai_optimised=True),
        )
        self._repo.update_meeting_notes_run(
            run["id"],
            {
                "status": "approved",
                "approved_at": datetime.now(UTC).isoformat(),
                "action_items": [item.model_dump(mode="json", exclude_none=True) for item in body.action_items],
                "decisions": [item.model_dump(mode="json", exclude_none=True) for item in body.decisions],
                "initiative_updates": [
                    item.model_dump(mode="json", exclude_none=True) for item in body.initiative_updates
                ],
            },
        )
        self._repo.insert_audit_log(
            workflow_run_id=run["id"],
            agent_id="vishwa",
            skill_name="meeting_notes_extraction",
            action="approve_workflow",
            input_summary=f"Approved meeting notes workflow {run['id']}",
            output_summary=f"Created {len(action_ids)} action items and optimised session {session_id}",
            requires_review=False,
            human_action="approved",
        )
        return {
            "workflow_run_id": run["id"],
            "status": "approved",
            "session": meeting_service.get_session_detail(session_id),
            "action_item_ids": action_ids,
        }

    def _record_initiative_corrections(
        self,
        run: dict[str, Any],
        body: WorkflowApproveRequest,
        suggestions: InitiativeIntakeSuggestions,
        corrected_by: UUID,
    ) -> None:
        prediction = {
            "initiative": run.get("extracted_draft") or {},
            "kpi_suggestions": run.get("kpi_suggestions") or [],
            "risk_suggestions": run.get("risk_suggestions") or [],
        }
        correction = {
            "initiative": body.initiative.model_dump(mode="json", exclude_none=True)
            if body.initiative
            else {},
            "kpi_suggestions": [
                item.model_dump(mode="json", exclude_none=True) for item in suggestions.kpis
            ],
            "risk_suggestions": [
                item.model_dump(mode="json", exclude_none=True) for item in suggestions.risks
            ],
        }
        if _normalise_for_compare(prediction) == _normalise_for_compare(correction):
            return
        self._repo.insert_correction(
            agent_id="netra",
            agent_prediction=prediction,
            human_correction=correction,
            correction_type="field_edit",
            corrected_by=corrected_by,
        )

    def _record_meeting_notes_corrections(
        self,
        run: dict[str, Any],
        body: WorkflowApproveRequest,
        corrected_by: UUID,
    ) -> None:
        prediction = {
            "action_items": run.get("action_items") or [],
            "decisions": run.get("decisions") or [],
            "initiative_updates": run.get("initiative_updates") or [],
        }
        correction = {
            "action_items": [
                item.model_dump(mode="json", exclude_none=True) for item in body.action_items
            ],
            "decisions": [
                item.model_dump(mode="json", exclude_none=True) for item in body.decisions
            ],
            "initiative_updates": [
                item.model_dump(mode="json", exclude_none=True) for item in body.initiative_updates
            ],
        }
        if _normalise_for_compare(prediction) == _normalise_for_compare(correction):
            return
        self._repo.insert_correction(
            agent_id="netra",
            agent_prediction=prediction,
            human_correction=correction,
            correction_type="field_edit",
            corrected_by=corrected_by,
        )

    def _record_full_rejection(
        self,
        run: dict[str, Any],
        reason: str | None,
        corrected_by: UUID,
    ) -> None:
        prediction = {
            "workflow_run_id": str(run["id"]),
            "workflow_type": run.get("workflow_type"),
            "status": run.get("status"),
        }
        self._repo.insert_correction(
            agent_id="netra",
            agent_prediction=prediction,
            human_correction={"reason": reason or "Rejected without comment"},
            correction_type="full_reject",
            corrected_by=corrected_by,
        )

    @staticmethod
    def _suggestions_from_run(run: dict[str, Any]) -> InitiativeIntakeSuggestions:
        return InitiativeIntakeSuggestions(
            trace_id=f"workflow-{run['id']}",
            agent_status="deterministic_fallback",
            kpis=[
                SuggestedKPI.model_validate(item)
                for item in run.get("kpi_suggestions") or []
                if item.get("accepted", True)
            ],
            risks=[
                SuggestedRisk.model_validate(item)
                for item in run.get("risk_suggestions") or []
                if item.get("accepted", True)
            ],
        )


def _attendees_from_session(session: dict[str, Any]) -> list[MeetingAttendeeContext]:
    attendees: list[MeetingAttendeeContext] = []
    for attendee in session.get("attendees") or []:
        user = attendee.get("users") or {}
        attendees.append(
            MeetingAttendeeContext(
                user_id=attendee["user_id"],
                display_name=user.get("display_name"),
            )
        )
    return attendees


def _initiatives_from_session(session: dict[str, Any]) -> list[LinkedInitiativeContext]:
    initiatives: list[LinkedInitiativeContext] = []
    for link in session.get("initiatives") or []:
        initiative = link.get("initiatives") or {}
        if not initiative.get("id"):
            continue
        initiatives.append(
            LinkedInitiativeContext(
                id=initiative["id"],
                name=initiative.get("name") or "Linked initiative",
                initiative_code=initiative.get("initiative_code"),
            )
        )
    return initiatives


def _approved_action_items(values: list[Any]) -> list[MeetingActionItemSuggestion]:
    result: list[MeetingActionItemSuggestion] = []
    for value in values:
        item = (
            value
            if isinstance(value, MeetingActionItemSuggestion)
            else MeetingActionItemSuggestion.model_validate(value)
        )
        if item.accepted:
            result.append(item)
    return result


def _approved_decisions(values: list[Any]) -> list[MeetingDecision]:
    result: list[MeetingDecision] = []
    for value in values:
        item = value if isinstance(value, MeetingDecision) else MeetingDecision.model_validate(value)
        if item.accepted:
            result.append(item)
    return result


def _approved_updates(values: list[Any]) -> list[InitiativeStatusSignal]:
    result: list[InitiativeStatusSignal] = []
    for value in values:
        item = (
            value
            if isinstance(value, InitiativeStatusSignal)
            else InitiativeStatusSignal.model_validate(value)
        )
        if item.accepted:
            result.append(item)
    return result


def _append_meeting_notes(
    existing: str | None,
    *,
    decisions: list[MeetingDecision],
    updates: list[Any],
) -> str:
    lines = [existing.strip()] if existing else []
    if decisions:
        lines.append("AI extracted decisions:")
        lines.extend(f"- {item.text}" for item in decisions)
    if updates:
        lines.append("AI extracted initiative updates:")
        lines.extend(f"- {item.initiative_name or 'Initiative'}: {item.summary}" for item in updates)
    return "\n".join(line for line in lines if line)


def _is_iso_date(value: str | None) -> bool:
    if not value:
        return False
    try:
        datetime.fromisoformat(value)
    except ValueError:
        return False
    return True


def _normalise_for_compare(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _summarize(value: str, limit: int = 300) -> str:
    clean = " ".join(value.split())
    return clean[:limit]


def _field_confidence(draft: InitiativeDraft) -> dict[str, str]:
    result: dict[str, str] = {}
    for field, value in draft.model_dump().items():
        if value is None:
            result[field] = "low"
        elif field in {"name", "type", "priority", "planned_end"}:
            result[field] = "high"
        else:
            result[field] = "medium"
    return result
