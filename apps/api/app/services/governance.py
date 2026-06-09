"""Governance service — stage gate logic."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import yaml
from fastapi import HTTPException, status
from supabase import Client

from app.domain.governance import (
    GateCriteriaState,
    GateDecisionPatch,
    GateItem,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
    PortfolioGovernanceResponse,
)
from app.repositories.audit import AuditRepository
from app.repositories.governance import GovernanceRepository
from app.services.financial import FinancialService


def _find_gates_path() -> Path:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "domain_packs/transmuter/gates.yaml"
        if candidate.exists():
            return candidate
    return Path("/app/domain_packs/transmuter/gates.yaml")


GATES_PATH = _find_gates_path()


class GovernanceService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID) -> None:
        self._client = client
        self._repo = GovernanceRepository(client, tenant_id)
        self._audit = AuditRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id)

    def get_status(self, initiative_id: str) -> GovernanceStatusResponse:
        gates = self._get_gates(initiative_id)
        submissions = [self._to_submission(s) for s in self._repo.list_submissions(initiative_id)]

        active = next((s for s in submissions if s.decision == "pending"), None)

        return GovernanceStatusResponse(gates=gates, active_submission=active, history=submissions)

    def list_submissions(self) -> list[GateSubmissionItem]:
        rows = self._repo.list_all_submissions()
        return [self._to_submission(r) for r in rows]

    def get_portfolio_governance(self) -> PortfolioGovernanceResponse:
        submissions = self.list_submissions()
        approved = len([s for s in submissions if s.decision == "approved"])
        pending = len([s for s in submissions if s.decision == "pending"])
        rejected = len([s for s in submissions if s.decision == "rejected"])
        conditional = len([s for s in submissions if s.decision == "conditional"])
        total = len(submissions)
        return PortfolioGovernanceResponse(
            health_score=f"{approved}/{total}",
            approved=approved,
            pending=pending,
            rejected=rejected,
            conditional=conditional,
            total_submissions=total,
            submissions=submissions,
        )

    def list_criteria(
        self,
        gate_number: int,
        initiative_id: str | None = None,
    ) -> list[GateCriteriaState]:
        active_submission: dict[str, Any] | None = None
        if initiative_id:
            active_submission = next(
                (
                    row
                    for row in self._repo.list_submissions(initiative_id)
                    if row["gate_number"] == gate_number and row["decision"] == "pending"
                ),
                None,
            )
        if active_submission and active_submission.get("criteria_snapshot"):
            return [
                GateCriteriaState(
                    id=row.get("id") or row.get("criterion_id"),
                    criterion_id=row.get("criterion_id") or row.get("id"),
                    label=row["label"],
                    guidance=row.get("guidance"),
                    sort_order=row.get("sort_order", index),
                    ticked=bool(row.get("ticked")),
                    ticked_by=row.get("ticked_by"),
                    ticked_at=row.get("ticked_at"),
                )
                for index, row in enumerate(active_submission["criteria_snapshot"])
            ]

        rows = self._repo.list_criteria(gate_number)
        if not rows:
            rows = self._pack_criteria(gate_number)
        return [
            GateCriteriaState(
                id=row["id"],
                criterion_id=row["criterion_id"],
                label=row["label"],
                guidance=row.get("guidance"),
                sort_order=row.get("sort_order", index),
            )
            for index, row in enumerate(rows)
        ]

    def submit_gate(
        self,
        initiative_id: str,
        gate_number: int,
        data: GateSubmissionCreate,
    ) -> GateSubmissionItem:
        # Business Logic: Cannot submit if another submission is pending
        history = self._repo.list_submissions(initiative_id)
        if any(s["gate_number"] == gate_number and s["decision"] == "pending" for s in history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gate {gate_number} already has a pending submission.",
            )

        if not any(item.get("ticked") for item in data.criteria_snapshot):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one gate criterion must be ticked before submission.",
            )

        payload = data.model_dump()
        payload["criteria_snapshot"] = self._normalize_snapshot(data.criteria_snapshot)
        payload["initiative_id"] = initiative_id
        payload["gate_number"] = gate_number
        payload["submitted_by_id"] = self._user_id
        payload["submitted_at"] = datetime.now(UTC).isoformat()
        payload["decision"] = "pending"

        row = self._repo.create_submission(payload)
        submission = self._to_submission(row)
        self._audit_change(
            "submit",
            "gate_submission",
            row["id"],
            after_data=submission.model_dump(mode="json"),
        )
        return submission

    def record_decision(self, submission_id: str, data: GateDecisionPatch) -> GateSubmissionItem:
        sub = self._repo.get_submission(submission_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )

        payload = data.model_dump(exclude_none=True)
        payload["decided_by_id"] = self._user_id
        payload["decided_at"] = datetime.now(UTC).isoformat()

        updated = self._repo.update_submission(submission_id, payload)

        # Trigger stage transition
        if data.decision == "approved":
            gate = self._get_gate(sub["initiative_id"], sub["gate_number"])
            if gate:
                self._repo.update_initiative_stage(sub["initiative_id"], gate.to_stage)
            financial_service = FinancialService(
                self._client,
                self._tenant_id,
            )
            governance_settings = (
                financial_service.get_governance_settings()
                if hasattr(financial_service, "get_governance_settings")
                else None
            )
            if governance_settings is None or (
                governance_settings.plan_lock_on_approval
                and sub["gate_number"] == governance_settings.initiative_plan_lock_gate_number
            ):
                financial_service.lock_bankable_plan_from_approval(
                    sub["initiative_id"],
                    submission_id,
                    self._user_id,
                    locked_reason=data.commentary,
                )

        submission = self._to_submission(updated)
        self._audit_change(
            self._decision_action(data.decision),
            "gate_submission",
            submission_id,
            before_data=sub,
            after_data=submission.model_dump(mode="json"),
        )
        return submission

    # ── Helpers ──────────────────────────────────────────────────────

    def _get_gates(self, initiative_id: str) -> list[GateItem]:
        rows = self._repo.list_initiative_gates(initiative_id)
        if rows:
            return [self._to_gate(g) for g in rows]
        return self._pack_gates(initiative_id)

    def _get_gate(self, initiative_id: str, gate_number: int) -> GateItem | None:
        row = self._repo.get_gate(initiative_id, gate_number)
        if row:
            return self._to_gate(row)
        return next(
            (gate for gate in self._pack_gates(initiative_id) if gate.gate_number == gate_number),
            None,
        )

    def _to_gate(self, row: dict[str, Any]) -> GateItem:
        return GateItem(**row)

    def _pack_gates(self, initiative_id: str) -> list[GateItem]:
        config = self._load_gate_pack()
        gates: list[GateItem] = []
        for gate_key, gate in config["gates"].items():
            gates.append(
                GateItem(
                    id=None,
                    initiative_id=initiative_id,
                    gate_number=int(gate_key[1:]),
                    label=gate["label"],
                    from_stage=gate["from_stage"],
                    to_stage=gate["to_stage"],
                )
            )
        return gates

    def _pack_criteria(self, gate_number: int) -> list[dict[str, Any]]:
        gate = self._load_gate_pack()["gates"].get(f"G{gate_number}", {})
        return [
            {
                "id": criterion["id"],
                "criterion_id": criterion["id"],
                "label": criterion["label"],
                "guidance": criterion.get("guidance"),
                "sort_order": index,
            }
            for index, criterion in enumerate(gate.get("criteria", []))
            if criterion.get("default", True)
        ]

    def _normalize_snapshot(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        now = datetime.now(UTC).isoformat()
        snapshot: list[dict[str, Any]] = []
        for index, row in enumerate(rows):
            ticked = bool(row.get("ticked"))
            snapshot.append(
                {
                    "id": row.get("id") or row.get("criterion_id"),
                    "criterion_id": row.get("criterion_id") or row.get("id"),
                    "label": row["label"],
                    "guidance": row.get("guidance"),
                    "sort_order": row.get("sort_order", index),
                    "ticked": ticked,
                    "ticked_by": self._user_id if ticked else row.get("ticked_by"),
                    "ticked_at": now if ticked else row.get("ticked_at"),
                }
            )
        return snapshot

    def _audit_change(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        *,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> None:
        self._audit.log_change(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=self._user_id,
            before_data=before_data,
            after_data=after_data,
        )

    @staticmethod
    def _decision_action(decision: str) -> str:
        if decision == "approved":
            return "approve"
        if decision == "rejected":
            return "reject"
        return "update"

    @staticmethod
    def _load_gate_pack() -> dict[str, Any]:
        with GATES_PATH.open() as handle:
            return yaml.safe_load(handle)

    def _to_submission(self, row: dict[str, Any]) -> GateSubmissionItem:
        submitter = row.get("submitter") or {}
        decider = row.get("decider") or {}

        return GateSubmissionItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            gate_number=row["gate_number"],
            submitted_by_id=row["submitted_by_id"],
            submitted_by_name=(
                submitter.get("display_name") if isinstance(submitter, dict) else None
            ),
            submitted_at=row["submitted_at"],
            decision=row["decision"],
            decided_by_id=row.get("decided_by_id"),
            decided_by_name=decider.get("display_name") if isinstance(decider, dict) else None,
            decided_at=row.get("decided_at"),
            commentary=row.get("commentary"),
            criteria_snapshot=row.get("criteria_snapshot"),
        )
