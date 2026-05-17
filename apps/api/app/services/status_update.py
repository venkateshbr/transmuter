"""Status Update service — business logic layer."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.agents.status_update_agent import draft_status_update
from app.domain.status_updates import (
    NudgeCreate,
    NudgeResponse,
    StatusComplianceItem,
    StatusComplianceResponse,
    StatusComplianceSummary,
    StatusUpdateCreate,
    StatusUpdateDraftSuggestion,
    StatusUpdateItem,
    StatusUpdateListResponse,
    StatusUpdatePatch,
)
from app.repositories.status_update import StatusUpdateRepository
from app.services.initiative_context import InitiativeContextService
from app.services.nudge_delivery import NudgeDeliveryService


class StatusUpdateService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID | None) -> None:
        self._client = client
        self._repo = StatusUpdateRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id) if user_id else None
        self._delivery = NudgeDeliveryService()

    # ── List / Get ───────────────────────────────────────────────────

    def list_history(self, initiative_id: str) -> StatusUpdateListResponse:
        rows = self._repo.list_history(initiative_id)
        items = [self._to_item(r) for r in rows]
        return StatusUpdateListResponse(items=items, total=len(items))

    def get_draft(self, initiative_id: str) -> StatusUpdateItem | None:
        row = self._repo.get_draft(initiative_id)
        if not row:
            return None
        return self._to_item(row)

    def get_update(self, update_id: str) -> StatusUpdateItem:
        row = self._assert_exists(update_id)
        return self._to_item(row)

    # ── CRUD ─────────────────────────────────────────────────────────

    def create_update(self, initiative_id: str, data: StatusUpdateCreate) -> StatusUpdateItem:
        # Business logic: Cannot have more than one draft per initiative
        if data.is_draft:
            existing_draft = self._repo.get_draft(initiative_id)
            if existing_draft:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A draft status update already exists for this initiative.",
                )

        payload = data.model_dump(exclude_none=True)
        row = self._repo.create(initiative_id, self._user_id, payload)
        return self._to_item(row)

    def patch_update(self, update_id: str, data: StatusUpdatePatch) -> StatusUpdateItem:
        existing = self._assert_exists(update_id)
        patch = data.model_dump(exclude_unset=True)

        # Transitioning from draft to submitted
        if existing.get("is_draft") and patch.get("is_draft") is False:
            from datetime import datetime

            patch["submitted_at"] = datetime.now(UTC).isoformat()

        row = self._repo.update(update_id, patch)
        return self._to_item(row)

    def submit_update(self, update_id: str) -> StatusUpdateItem:
        existing = self._assert_exists(update_id)
        if not existing.get("is_draft"):
            return self._to_item(existing)
        return self.patch_update(update_id, StatusUpdatePatch(is_draft=False))

    def delete_update(self, update_id: str) -> None:
        self._assert_exists(update_id)
        self._repo.delete(update_id)

    # ── Helpers ──────────────────────────────────────────────────────

    def _assert_exists(self, update_id: str) -> dict[str, Any]:
        row = self._repo.get(update_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Status update not found",
            )
        return row

    def list_recent_updates(self) -> list[StatusUpdateItem]:
        rows = self._repo.list_recent_updates()
        return [self._to_item(r) for r in rows]

    def generate_draft(self, initiative_id: str) -> StatusUpdateDraftSuggestion:
        context = InitiativeContextService(self._client, self._tenant_id).pull_context(initiative_id)
        return draft_status_update(context)

    def get_compliance_stats(self) -> StatusComplianceResponse:
        rows = self._repo.list_compliance()
        from datetime import UTC, datetime

        now = datetime.now(UTC)
        nudge_counts = self._repo.list_nudge_counts()

        on_time = 0
        overdue = 0
        nuclear = 0

        compliance_list: list[StatusComplianceItem] = []

        for row in rows:
            updates = row.get("status_updates", [])
            # Sort by submitted_at
            submitted_updates = [u for u in updates if u.get("submitted_at")]
            submitted_updates.sort(key=lambda x: x["submitted_at"], reverse=True)

            last_update = submitted_updates[0] if submitted_updates else None
            last_date_str = last_update["submitted_at"] if last_update else None

            days_since = 999
            status = "nuclear"

            if last_date_str:
                last_date = datetime.fromisoformat(last_date_str.replace("Z", "+00:00"))
                days_since = (now - last_date).days

                if days_since <= 7:
                    status = "on_time"
                    on_time += 1
                elif days_since <= 14:
                    status = "overdue"
                    overdue += 1
                else:
                    status = "nuclear"
                    nuclear += 1
            else:
                status = "nuclear"
                nuclear += 1

            compliance_list.append(
                StatusComplianceItem(
                    initiative_id=row["id"],
                    initiative_name=row["name"],
                    owner_name=(row.get("users") or {}).get("display_name"),
                    last_update_at=last_date_str,
                    days_since=days_since,
                    status=status,
                    rag_status=last_update["rag_status"] if last_update else "red",
                    nudge_count=nudge_counts.get(row["id"], 0),
                )
            )

        return StatusComplianceResponse(
            summary=StatusComplianceSummary(
                total=len(rows),
                on_time=on_time,
                overdue=overdue,
                nuclear=nuclear,
            ),
            initiatives=compliance_list,
        )

    def nudge_owner(
        self,
        initiative_id: str,
        data: NudgeCreate | None = None,
    ) -> NudgeResponse:
        """Triggers a nudge for the initiative owner."""
        channel = (data or NudgeCreate()).channel
        target = self._repo.get_initiative_nudge_target(initiative_id)
        if not target:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Initiative not found",
            )
        nudge = self._repo.log_nudge(initiative_id, self._user_id, channel)
        owner = target.get("users") if isinstance(target.get("users"), dict) else {}
        delivery = self._delivery.deliver(
            channel=channel,
            owner_email=owner.get("email"),
            initiative_name=target["name"],
        )
        return NudgeResponse(
            success=True,
            nudge_id=nudge.get("id"),
            initiative_id=initiative_id,
            sent_at=nudge.get("sent_at"),
            channel=channel,
            delivery_status=delivery.status,
        )

    def list_nudges(self) -> list[dict[str, Any]]:
        return self._repo.list_nudges()

    def nudge_non_compliant_initiatives(self, channel: str = "both") -> list[NudgeResponse]:
        from datetime import timedelta

        rows = self.get_compliance_stats().initiatives
        recently_nudged = self._repo.list_nudged_ids_since(datetime.now(UTC) - timedelta(hours=24))
        responses: list[NudgeResponse] = []
        for row in rows:
            if row.status == "on_time" or row.initiative_id in recently_nudged:
                continue
            target = self._repo.get_initiative_nudge_target(row.initiative_id)
            if not target:
                continue
            nudge = self._repo.log_nudge(row.initiative_id, None, channel)
            owner = target.get("users") if isinstance(target.get("users"), dict) else {}
            delivery = self._delivery.deliver(
                channel=channel,
                owner_email=owner.get("email"),
                initiative_name=target["name"],
            )
            responses.append(
                NudgeResponse(
                    success=True,
                    nudge_id=nudge.get("id"),
                    initiative_id=row.initiative_id,
                    sent_at=nudge.get("sent_at"),
                    channel=channel,
                    delivery_status=delivery.status,
                )
            )
        return responses

    def _to_item(self, row: dict[str, Any]) -> StatusUpdateItem:
        author = row.get("users") or {}
        # Handle join from list_recent_updates
        initiative = row.get("initiatives") or {}
        initiative_name = initiative.get("name") if isinstance(initiative, dict) else None

        return StatusUpdateItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            initiative_name=initiative_name,
            author_id=row["author_id"],
            author_name=(author.get("display_name") if isinstance(author, dict) else None),
            rag_status=row["rag_status"],
            summary=row["summary"],
            achievements=row.get("achievements"),
            issues=row.get("issues"),
            next_steps=row.get("next_steps"),
            is_draft=row.get("is_draft", True),
            submitted_at=row.get("submitted_at"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
