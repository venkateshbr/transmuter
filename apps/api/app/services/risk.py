"""Risk service — business logic layer."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.risks import (
    RiskCreate,
    RiskHeatmapCell,
    RiskHeatmapResponse,
    RiskItem,
    RiskListResponse,
    RiskUpdate,
)
from app.repositories.audit import AuditRepository
from app.repositories.risk import RiskRepository


class RiskService:
    def __init__(self, client: Client, tenant_id: UUID, user_id: UUID | None = None) -> None:
        self._repo = RiskRepository(client, tenant_id)
        self._audit = AuditRepository(client, tenant_id)
        self._tenant_id = tenant_id
        self._user_id = str(user_id) if user_id else None

    # ── List / Detail ────────────────────────────────────────────────

    def list_risks(self, initiative_id: str) -> RiskListResponse:
        rows = self._repo.list(initiative_id)
        items = [self._to_item(r) for r in rows]
        return RiskListResponse(items=items, total=len(items))

    def list_portfolio_risks(
        self,
        status: str | None = None,
        type: str | None = None,
        rating: str | None = None,
    ) -> RiskListResponse:
        rows = self._repo.list_portfolio(status, type, rating)
        items = [self._to_item(r) for r in rows]
        return RiskListResponse(items=items, total=len(items))

    def get_risk(self, risk_id: str) -> RiskItem:
        row = self._assert_exists(risk_id)
        return self._to_item(row)

    # ── CRUD ─────────────────────────────────────────────────────────

    def create_risk(self, initiative_id: str, data: RiskCreate) -> RiskItem:
        payload = data.model_dump(exclude_none=True)
        self._calc_rating(payload)
        row = self._repo.create(initiative_id, payload)
        item = self._to_item(row)
        self._audit_change("create", "risk", row["id"], after_data=item.model_dump(mode="json"))
        return item

    def update_risk(
        self,
        initiative_id: str,
        risk_id: str,
        data: RiskUpdate,
    ) -> RiskItem:
        existing = self._assert_belongs_to_initiative(risk_id, initiative_id)
        patch = data.model_dump(exclude_unset=True)

        # Determine new impact/likelihood combining patch + existing
        impact = patch.get("impact", existing.get("impact"))
        likelihood = patch.get("likelihood", existing.get("likelihood"))

        if impact or likelihood:
            # We recalculate rating if impact or likelihood is known
            calc_payload = {"impact": impact, "likelihood": likelihood}
            self._calc_rating(calc_payload)
            patch["rating"] = calc_payload.get("rating")

        row = self._repo.update(risk_id, patch)
        item = self._to_item(row)
        self._audit_change(
            "update",
            "risk",
            risk_id,
            before_data=existing,
            after_data=item.model_dump(mode="json"),
        )
        return item

    def delete_risk(self, initiative_id: str, risk_id: str) -> None:
        existing = self._assert_belongs_to_initiative(risk_id, initiative_id)
        self._repo.delete(risk_id)
        self._audit_change("delete", "risk", risk_id, before_data=existing)

    # ── Heatmap ──────────────────────────────────────────────────────

    def get_heatmap(self) -> RiskHeatmapResponse:
        data = self._repo.get_heatmap_data()

        levels = ["high", "medium", "low"]
        counts: dict[tuple[str, str], int] = {}
        for row in data:
            imp = row.get("impact")
            lik = row.get("likelihood")
            if imp and lik:
                counts[(imp, lik)] = counts.get((imp, lik), 0) + 1

        cells = []
        for imp in levels:
            for lik in levels:
                cells.append(
                    RiskHeatmapCell(
                        impact=imp,
                        likelihood=lik,
                        count=counts.get((imp, lik), 0),
                    )
                )

        return RiskHeatmapResponse(
            cells=cells,
            total_open_risks=sum(counts.values()),
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _assert_exists(self, risk_id: str) -> dict[str, Any]:
        row = self._repo.get(risk_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk not found",
            )
        return row

    def _assert_belongs_to_initiative(
        self,
        risk_id: str,
        initiative_id: str,
    ) -> dict[str, Any]:
        row = self._assert_exists(risk_id)
        if row.get("initiative_id") != initiative_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Risk not found",
            )
        return row

    def _audit_change(
        self,
        action: str,
        entity_type: str,
        entity_id: str,
        *,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> None:
        if not self._user_id:
            return
        self._audit.log_change(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_id=self._user_id,
            before_data=before_data,
            after_data=after_data,
        )

    def _calc_rating(self, payload: dict[str, Any]) -> None:
        imp = payload.get("impact")
        lik = payload.get("likelihood")

        if not imp or not lik:
            payload["rating"] = None
            return

        matrix = {
            ("high", "high"): "high",
            ("high", "medium"): "high",
            ("high", "low"): "medium",
            ("medium", "high"): "high",
            ("medium", "medium"): "medium",
            ("medium", "low"): "low",
            ("low", "high"): "medium",
            ("low", "medium"): "low",
            ("low", "low"): "low",
        }

        payload["rating"] = matrix.get((imp, lik))

    def _to_item(self, row: dict[str, Any]) -> RiskItem:
        owner = row.get("users") or {}
        return RiskItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            description=row["description"],
            type=row.get("type"),
            impact=row.get("impact"),
            likelihood=row.get("likelihood"),
            rating=row.get("rating"),
            status=row["status"],
            owner_id=row.get("owner_id"),
            owner_name=(owner.get("display_name") if isinstance(owner, dict) else None),
            mitigation=row.get("mitigation"),
            escalated=row.get("escalated", False),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
