"""Governance repository — Stage gates & submissions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from supabase import Client


class GovernanceRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── Criteria ─────────────────────────────────────────────────────

    def list_criteria(self, gate_number: int | None = None) -> list[dict[str, Any]]:
        query = self._c.table("gate_criteria").select("*").eq("tenant_id", self._tid)
        if gate_number:
            query = query.eq("gate_number", gate_number)
        result = query.order("gate_number").order("sort_order").execute()
        return result.data or []

    def upsert_criterion(self, data: dict[str, Any]) -> dict[str, Any]:
        payload = {**data, "tenant_id": self._tid}
        if not payload.get("id"):
            payload["id"] = str(uuid4())
        result = self._c.table("gate_criteria").upsert(payload).execute()
        return result.data[0] if result.data else {}

    def update_criterion(self, criterion_id: str, data: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("gate_criteria")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", criterion_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_criterion(self, criterion_id: str) -> None:
        (
            self._c.table("gate_criteria")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", criterion_id)
            .execute()
        )

    # ── Gates ────────────────────────────────────────────────────────

    def list_gate_definitions(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = self._c.table("stage_gate_definitions").select("*").eq("tenant_id", self._tid)
        if active_only:
            query = query.eq("is_active", True)
        result = query.order("sort_order").order("gate_number").execute()
        return result.data or []

    def get_gate_definition(self, gate_number: int) -> dict[str, Any] | None:
        result = (
            self._c.table("stage_gate_definitions")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("gate_number", gate_number)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def get_initiative_access(self, initiative_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("initiatives")
            .select("id, owner_id, group_owner_id")
            .eq("tenant_id", self._tid)
            .eq("id", initiative_id)
            .maybe_single()
            .execute()
        )
        return result.data if result and result.data else None

    def create_gate_definition(self, data: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        payload = {
            **data,
            "id": data.get("id") or str(uuid4()),
            "tenant_id": self._tid,
            "created_at": data.get("created_at") or now,
            "updated_at": data.get("updated_at") or now,
        }
        result = self._c.table("stage_gate_definitions").insert(payload).execute()
        return result.data[0]

    def update_gate_definition(
        self,
        definition_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {**data, "updated_at": datetime.now(UTC).isoformat()}
        result = (
            self._c.table("stage_gate_definitions")
            .update(payload)
            .eq("tenant_id", self._tid)
            .eq("id", definition_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_gate_definition(self, definition_id: str) -> None:
        (
            self._c.table("stage_gate_definitions")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", definition_id)
            .execute()
        )

    def list_initiative_gates(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("stage_gates")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("gate_number")
            .execute()
        )
        return result.data or []

    def get_gate(self, initiative_id: str, gate_number: int) -> dict[str, Any] | None:
        result = (
            self._c.table("stage_gates")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .eq("gate_number", gate_number)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    # ── Submissions ──────────────────────────────────────────────────

    def list_submissions(self, initiative_id: str) -> list[dict[str, Any]]:
        result = (
            self._c.table("gate_submissions")
            .select(
                "*, initiatives(name, initiative_code), "
                "submitter:users!gate_submissions_submitted_by_id_fkey(display_name), "
                "decider:users!gate_submissions_decided_by_id_fkey(display_name)"
            )
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("submitted_at", desc=True)
            .execute()
        )
        return result.data or []

    def list_all_submissions(self) -> list[dict[str, Any]]:
        result = (
            self._c.table("gate_submissions")
            .select(
                "*, initiatives(name, initiative_code), "
                "submitter:users!gate_submissions_submitted_by_id_fkey(display_name), "
                "decider:users!gate_submissions_decided_by_id_fkey(display_name)"
            )
            .eq("tenant_id", self._tid)
            .order("submitted_at", desc=True)
            .execute()
        )
        return result.data or []

    def get_submission(self, submission_id: str) -> dict[str, Any] | None:
        result = (
            self._c.table("gate_submissions")
            .select(
                "*, initiatives(name, initiative_code), "
                "submitter:users!gate_submissions_submitted_by_id_fkey(display_name), "
                "decider:users!gate_submissions_decided_by_id_fkey(display_name)"
            )
            .eq("tenant_id", self._tid)
            .eq("id", submission_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create_submission(self, data: dict[str, Any]) -> dict[str, Any]:
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        result = self._c.table("gate_submissions").insert(data).execute()
        if result.data:
            return self.get_submission(result.data[0]["id"]) or result.data[0]
        return {}

    def update_submission(self, submission_id: str, data: dict[str, Any]) -> dict[str, Any]:
        result = (
            self._c.table("gate_submissions")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", submission_id)
            .execute()
        )
        if result.data:
            return self.get_submission(result.data[0]["id"]) or result.data[0]
        return {}

    # ── Initiative Updates ───────────────────────────────────────────

    def update_initiative_stage(self, initiative_id: str, stage: str) -> None:
        self._c.table("initiatives").update({"stage": stage}).eq("id", initiative_id).execute()
