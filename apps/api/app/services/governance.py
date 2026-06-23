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
    GateCriteriaCreate,
    GateCriteriaItem,
    GateCriteriaState,
    GateCriteriaUpdate,
    GateDecisionPatch,
    GateItem,
    GateSubmissionCreate,
    GateSubmissionItem,
    GovernanceStatusResponse,
    PortfolioGovernanceResponse,
    StageGateDefinition,
    StageGateDefinitionCreate,
    StageGateDefinitionUpdate,
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
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID, user_role: str) -> None:
        self._client = client
        self._repo = GovernanceRepository(client, tenant_id)
        self._audit = AuditRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id)
        self._user_role = user_role

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

    def list_gate_definitions(self) -> list[StageGateDefinition]:
        return [self._to_gate_definition(row) for row in self._repo.list_gate_definitions()]

    def create_gate_definition(self, data: StageGateDefinitionCreate) -> StageGateDefinition:
        row = self._repo.create_gate_definition(data.model_dump(mode="json"))
        return self._to_gate_definition(row)

    def update_gate_definition(
        self,
        definition_id: str,
        data: StageGateDefinitionUpdate,
    ) -> StageGateDefinition:
        row = self._repo.update_gate_definition(
            definition_id,
            data.model_dump(mode="json", exclude_none=True),
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stage gate definition not found",
            )
        return self._to_gate_definition(row)

    def delete_gate_definition(self, definition_id: str) -> None:
        self._repo.delete_gate_definition(definition_id)

    def list_gate_criteria_config(self, gate_number: int | None = None) -> list[GateCriteriaItem]:
        return [GateCriteriaItem(**row) for row in self._repo.list_criteria(gate_number)]

    def create_gate_criterion(self, data: GateCriteriaCreate) -> GateCriteriaItem:
        row = self._repo.upsert_criterion(data.model_dump(mode="json"))
        return GateCriteriaItem(**row)

    def update_gate_criterion(
        self,
        criterion_id: str,
        data: GateCriteriaUpdate,
    ) -> GateCriteriaItem:
        row = self._repo.update_criterion(
            criterion_id,
            data.model_dump(mode="json", exclude_none=True),
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gate criterion not found",
            )
        return GateCriteriaItem(**row)

    def delete_gate_criterion(self, criterion_id: str) -> None:
        self._repo.delete_criterion(criterion_id)

    def submit_gate(
        self,
        initiative_id: str,
        gate_number: int,
        data: GateSubmissionCreate,
    ) -> GateSubmissionItem:
        gate_definition = self._repo.get_gate_definition(gate_number)
        self._assert_gate_role_allowed(initiative_id, gate_definition)

        # Business Logic: Cannot submit if another submission is pending
        history = self._repo.list_submissions(initiative_id)
        if any(s["gate_number"] == gate_number and s["decision"] == "pending" for s in history):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Gate {gate_number} already has a pending submission.",
            )

        gate_definition = self._repo.get_gate_definition(gate_number)
        normalized_snapshot = self._normalize_snapshot(data.criteria_snapshot)
        ticked_count = len([item for item in normalized_snapshot if item.get("ticked")])
        if not ticked_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one gate criterion must be ticked before submission.",
            )
        if gate_definition and gate_definition.get("require_all_criteria"):
            required_count = len(
                [
                    item
                    for item in self._repo.list_criteria(gate_number)
                    if item.get("is_active", True)
                ]
            )
            if required_count and ticked_count < required_count:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="All active gate criteria must be ticked before submission.",
                )
        payload = data.model_dump()
        payload["criteria_snapshot"] = normalized_snapshot
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

    def submit_bankable_plan_rebaseline(
        self,
        initiative_id: str,
        reason: str,
    ) -> GateSubmissionItem:
        financial_service = FinancialService(self._client, self._tenant_id)
        settings = financial_service.get_governance_settings()
        if not settings.allow_rebaseline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bankable plan rebaseline is disabled for this tenant.",
            )
        if self._user_role not in settings.rebaseline_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role cannot request a bankable plan rebaseline.",
            )

        current = financial_service.get_current_bankable_plan(initiative_id)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No bankable plan exists for this initiative.",
            )

        history = self._repo.list_submissions(initiative_id)
        if any(
            row.get("submission_type") == "bankable_plan_rebaseline"
            and row.get("decision") == "pending"
            for row in history
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This initiative already has a pending rebaseline request.",
            )

        snapshot = financial_service.get_bankable_plan_snapshot(initiative_id)
        now = datetime.now(UTC).isoformat()
        criteria_snapshot = [
            {
                "id": "rebaseline-reason",
                "criterion_id": "rebaseline-reason",
                "label": "Rebaseline reason documented",
                "guidance": "Finance has documented why the approved baseline should change.",
                "sort_order": 1,
                "ticked": True,
                "ticked_by": self._user_id,
                "ticked_at": now,
            },
            {
                "id": "dashboard-impact-reviewed",
                "criterion_id": "dashboard-impact-reviewed",
                "label": "Dashboard and board-pack impact reviewed",
                "guidance": (
                    "Approver understands that approval changes the current bankable "
                    "baseline used by Benefit Tracking, Waterline, dashboards, and exports."
                ),
                "sort_order": 2,
                "ticked": True,
                "ticked_by": self._user_id,
                "ticked_at": now,
            },
        ]
        payload = {
            "initiative_id": initiative_id,
            "gate_number": settings.initiative_plan_lock_gate_number,
            "submission_type": "bankable_plan_rebaseline",
            "submitted_by_id": self._user_id,
            "submitted_at": now,
            "decision": "pending",
            "commentary": reason,
            "criteria_snapshot": criteria_snapshot,
            "requested_bankable_plan_version": current.version + 1,
            "requested_snapshot": snapshot.model_dump(mode="json"),
        }
        row = self._repo.create_submission(payload)
        submission = self._to_submission(row)
        self._audit_change(
            "submit",
            "bankable_plan_rebaseline",
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
        gate_definition = self._repo.get_gate_definition(sub["gate_number"])
        self._assert_gate_role_allowed(sub["initiative_id"], gate_definition)

        payload = data.model_dump(exclude_none=True)
        payload["decided_by_id"] = self._user_id
        payload["decided_at"] = datetime.now(UTC).isoformat()

        updated = self._repo.update_submission(submission_id, payload)

        # Trigger stage transition
        if data.decision == "approved":
            financial_service = FinancialService(
                self._client,
                self._tenant_id,
            )
            if sub.get("submission_type") == "bankable_plan_rebaseline":
                financial_service.rebaseline_bankable_plan(
                    sub["initiative_id"],
                    self._user_id,
                    reason=data.commentary or sub.get("commentary"),
                    trigger_submission_id=submission_id,
                )
            else:
                gate = self._get_gate(sub["initiative_id"], sub["gate_number"])
                if gate:
                    self._repo.update_initiative_stage(sub["initiative_id"], gate.to_stage)
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
        definitions = self._repo.list_gate_definitions(active_only=True)
        if definitions:
            return [self._definition_to_gate(row, initiative_id) for row in definitions]
        return self._pack_gates(initiative_id)

    def _get_gate(self, initiative_id: str, gate_number: int) -> GateItem | None:
        row = self._repo.get_gate(initiative_id, gate_number)
        if row:
            return self._to_gate(row)
        definition = self._repo.get_gate_definition(gate_number)
        if definition:
            return self._definition_to_gate(definition, initiative_id)
        return next(
            (gate for gate in self._pack_gates(initiative_id) if gate.gate_number == gate_number),
            None,
        )

    def _to_gate(self, row: dict[str, Any]) -> GateItem:
        return GateItem(**row)

    @staticmethod
    def _to_gate_definition(row: dict[str, Any]) -> StageGateDefinition:
        return StageGateDefinition(
            id=row["id"],
            gate_number=row["gate_number"],
            key=row["key"],
            label=row["label"],
            from_stage=row["from_stage"],
            to_stage=row["to_stage"],
            description=row.get("description"),
            approval_required=row.get("approval_required", True),
            approver_roles=row.get("approver_roles") or ["transformation_office"],
            require_all_criteria=row.get("require_all_criteria", True),
            sort_order=row.get("sort_order") or 0,
            is_system=row.get("is_system", False),
            is_active=row.get("is_active", True),
        )

    def _definition_to_gate(self, row: dict[str, Any], initiative_id: str) -> GateItem:
        definition = self._to_gate_definition(row)
        return GateItem(
            id=None,
            initiative_id=initiative_id,
            gate_number=definition.gate_number,
            label=definition.label,
            from_stage=definition.from_stage,
            to_stage=definition.to_stage,
            approval_required=definition.approval_required,
            approver_roles=definition.approver_roles,
            require_all_criteria=definition.require_all_criteria,
        )

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

    def _assert_gate_role_allowed(
        self,
        initiative_id: str,
        gate_definition: dict[str, Any] | None,
    ) -> None:
        if self._user_role == "transformation_office":
            return
        if not gate_definition:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Stage gate configuration not found",
            )
        approver_roles = gate_definition.get("approver_roles") or ["transformation_office"]
        if self._user_role not in approver_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This role cannot act on the configured stage gate",
            )
        if self._user_role == "initiative_owner":
            initiative = self._repo.get_initiative_access(initiative_id)
            user_id = self._user_id
            if not initiative or user_id not in {
                str(initiative.get("owner_id") or ""),
                str(initiative.get("group_owner_id") or ""),
            }:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Initiative owners can only act on their own initiatives",
                )

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
        initiative = row.get("initiatives") if isinstance(row.get("initiatives"), dict) else {}

        return GateSubmissionItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            initiative_code=initiative.get("initiative_code"),
            initiative_name=initiative.get("name"),
            initiatives=initiative or None,
            gate_number=row["gate_number"],
            submission_type=row.get("submission_type") or "stage_gate",
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
            requested_bankable_plan_version=row.get("requested_bankable_plan_version"),
            requested_snapshot=row.get("requested_snapshot"),
        )
