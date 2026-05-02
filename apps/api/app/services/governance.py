"""Governance service — stage gate logic."""

from __future__ import annotations

from typing import Any
from uuid import UUID
from datetime import datetime, timezone

from fastapi import HTTPException, status
from supabase import Client

from app.domain.governance import (
    GateDecisionPatch,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
    GateItem,
)
from app.repositories.governance import GovernanceRepository


class GovernanceService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID) -> None:
        self._repo = GovernanceRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id)

    def get_status(self, initiative_id: str) -> GovernanceStatusResponse:
        gates = [self._to_gate(g) for g in self._repo.list_initiative_gates(initiative_id)]
        submissions = [self._to_submission(s) for s in self._repo.list_submissions(initiative_id)]
        
        active = next((s for s in submissions if s.decision == "pending"), None)
        
        return GovernanceStatusResponse(
            gates=gates,
            active_submission=active,
            history=submissions
        )

    def list_submissions(self) -> list[GateSubmissionItem]:
        rows = self._repo.list_all_submissions()
        return [self._to_submission(r) for r in rows]

    def list_criteria(self, gate_number: int) -> list[dict[str, Any]]:
        return self._repo.list_criteria(gate_number)

    def submit_gate(self, initiative_id: str, gate_number: int, data: GateSubmissionCreate) -> GateSubmissionItem:
        # Business Logic: Cannot submit if another submission is pending
        history = self._repo.list_submissions(initiative_id)
        if any(s["gate_number"] == gate_number and s["decision"] == "pending" for s in history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gate {gate_number} already has a pending submission."
            )

        payload = data.model_dump()
        payload["initiative_id"] = initiative_id
        payload["gate_number"] = gate_number
        payload["submitted_by_id"] = self._user_id
        payload["submitted_at"] = datetime.now(timezone.utc).isoformat()
        payload["decision"] = "pending"

        row = self._repo.create_submission(payload)
        return self._to_submission(row)

    def record_decision(self, submission_id: str, data: GateDecisionPatch) -> GateSubmissionItem:
        sub = self._repo.get_submission(submission_id)
        if not sub:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

        payload = data.model_dump(exclude_none=True)
        payload["decided_by_id"] = self._user_id
        payload["decided_at"] = datetime.now(timezone.utc).isoformat()

        updated = self._repo.update_submission(submission_id, payload)
        
        # Trigger stage transition
        if data.decision == "approved":
            gate = self._repo.get_gate(sub["initiative_id"], sub["gate_number"])
            if gate:
                self._repo.update_initiative_stage(sub["initiative_id"], gate["to_stage"])

        return self._to_submission(updated)

    # ── Helpers ──────────────────────────────────────────────────────

    def _to_gate(self, row: dict[str, Any]) -> GateItem:
        return GateItem(**row)

    def _to_submission(self, row: dict[str, Any]) -> GateSubmissionItem:
        submitter = row.get("submitter") or {}
        decider = row.get("decider") or {}
        
        return GateSubmissionItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            gate_number=row["gate_number"],
            submitted_by_id=row["submitted_by_id"],
            submitted_by_name=submitter.get("display_name") if isinstance(submitter, dict) else None,
            submitted_at=row["submitted_at"],
            decision=row["decision"],
            decided_by_id=row.get("decided_by_id"),
            decided_by_name=decider.get("display_name") if isinstance(decider, dict) else None,
            decided_at=row.get("decided_at"),
            commentary=row.get("commentary"),
            criteria_snapshot=row.get("criteria_snapshot")
        )
