"""Workflow repository — Supabase data access."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from supabase import Client


class WorkflowRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    def create_initiative_intake_run(self, submitter_user_id: UUID, raw_text: str) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "tenant_id": self._tid,
            "submitter_user_id": str(submitter_user_id),
            "raw_text": raw_text,
            "status": "extracting",
            "expires_at": (datetime.now(UTC) + timedelta(hours=48)).isoformat(),
        }
        result = self._c.table("initiative_intake_workflow_runs").insert(payload).execute()
        return result.data[0]

    def get_run(self, run_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self._c.table("initiative_intake_workflow_runs")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", str(run_id))
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create_meeting_notes_run(
        self,
        *,
        meeting_id: str,
        session_id: str,
        submitter_user_id: UUID,
        transcript_text: str,
    ) -> dict[str, Any]:
        payload = {
            "id": str(uuid4()),
            "tenant_id": self._tid,
            "meeting_id": meeting_id,
            "session_id": session_id,
            "submitter_user_id": str(submitter_user_id),
            "transcript_text": transcript_text,
            "status": "chunking",
            "expires_at": (datetime.now(UTC) + timedelta(hours=24)).isoformat(),
        }
        result = self._c.table("meeting_notes_workflow_runs").insert(payload).execute()
        return result.data[0]

    def get_meeting_notes_run(self, run_id: UUID | str) -> dict[str, Any] | None:
        result = (
            self._c.table("meeting_notes_workflow_runs")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", str(run_id))
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def update_meeting_notes_run(self, run_id: UUID | str, patch: dict[str, Any]) -> dict[str, Any]:
        patch["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("meeting_notes_workflow_runs")
            .update(patch)
            .eq("tenant_id", self._tid)
            .eq("id", str(run_id))
            .execute()
        )
        return result.data[0] if result.data else {}

    def update_run(self, run_id: UUID | str, patch: dict[str, Any]) -> dict[str, Any]:
        patch["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("initiative_intake_workflow_runs")
            .update(patch)
            .eq("tenant_id", self._tid)
            .eq("id", str(run_id))
            .execute()
        )
        return result.data[0] if result.data else {}

    def insert_audit_log(
        self,
        *,
        workflow_run_id: UUID | str,
        agent_id: str,
        skill_name: str,
        action: str,
        input_summary: str,
        output_summary: str,
        confidence: float | None = None,
        latency_ms: int | None = None,
        requires_review: bool = False,
        human_action: str | None = None,
    ) -> str | None:
        payload = {
            "tenant_id": self._tid,
            "agent_id": agent_id,
            "skill_name": skill_name,
            "workflow_run_id": str(workflow_run_id),
            "action": action,
            "confidence": confidence,
            "latency_ms": latency_ms,
            "input_summary": input_summary,
            "output_summary": output_summary,
            "requires_review": requires_review,
            "human_action": human_action,
        }
        result = self._c.table("agent_audit_log").insert(payload).execute()
        if result.data:
            return result.data[0].get("id")
        return None

    def insert_correction(
        self,
        *,
        agent_id: str,
        agent_prediction: dict[str, Any] | list[Any],
        human_correction: dict[str, Any] | list[Any],
        correction_type: str,
        corrected_by: UUID,
        audit_log_id: UUID | str | None = None,
    ) -> str | None:
        payload = {
            "tenant_id": self._tid,
            "agent_id": agent_id,
            "audit_log_id": str(audit_log_id) if audit_log_id else None,
            "agent_prediction": agent_prediction,
            "human_correction": human_correction,
            "correction_type": correction_type,
            "corrected_by": str(corrected_by),
        }
        result = self._c.table("agent_corrections").insert(payload).execute()
        if result.data:
            return result.data[0].get("id")
        return None
