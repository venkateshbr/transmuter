"""Milestone service — business logic layer."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.domain.milestones import (
    ChecklistItem,
    ChecklistItemCreate,
    DependencyCreate,
    DependencyItem,
    DependencyListResponse,
    DependencyResponse,
    MilestoneCreate,
    MilestoneDetail,
    MilestoneItem,
    MilestoneListResponse,
    MilestoneSummary,
    MilestoneUpdate,
)
from app.domain.pressure import (
    MilestonePressureEngine,
    MilestonePressureResult,
    pressure_level,
)
from app.repositories.milestone import MilestoneRepository


class MilestoneService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = MilestoneRepository(client, tenant_id)
        self._tenant_id = tenant_id

    # ── List / Detail ────────────────────────────────────────────────

    def list_milestones(
        self, initiative_id: str,
    ) -> MilestoneListResponse:
        rows = self._repo.list(initiative_id)
        items = [self._to_item(r) for r in rows]
        return MilestoneListResponse(
            items=items, total=len(items),
        )

    def list_all_milestones(self) -> MilestoneListResponse:
        """List all milestones across the portfolio (all initiatives)."""
        rows = self._repo.list_all()
        items = [self._to_item(r) for r in rows]
        return MilestoneListResponse(
            items=items, total=len(items),
        )

    def get_milestone(self, milestone_id: str) -> MilestoneDetail:
        row = self._repo.get(milestone_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Milestone not found",
            )
        checklist = self._repo.get_checklist(milestone_id)
        deps = self._repo.get_dependencies(milestone_id)
        return self._to_detail(row, checklist, deps)

    # ── CRUD ─────────────────────────────────────────────────────────

    def create_milestone(
        self, initiative_id: str, data: MilestoneCreate,
    ) -> MilestoneDetail:
        row = self._repo.create(initiative_id, {
            "name": data.name,
            "description": data.description,
            "owner_id": data.owner_id,
            "priority": data.priority,
            "planned_start": data.planned_start,
            "planned_end": data.planned_end,
        })
        self._recalc_pressure(row["id"], initiative_id)
        return self.get_milestone(row["id"])

    def update_milestone(self, milestone_id: str, data: MilestoneUpdate) -> MilestoneDetail:
        existing = self._assert_exists(milestone_id)
        patch = {
            k: v
            for k, v in data.model_dump(exclude_none=True).items()
        }
        self._repo.update(milestone_id, patch)
        self._recalc_pressure(
            milestone_id, existing["initiative_id"],
        )
        return self.get_milestone(milestone_id)

    def delete_milestone(self, milestone_id: str) -> None:
        self._assert_exists(milestone_id)
        self._repo.delete(milestone_id)

    # ── Checklist ────────────────────────────────────────────────────

    def add_checklist_item(
        self, milestone_id: str, data: ChecklistItemCreate,
    ) -> ChecklistItem:
        ms = self._assert_exists(milestone_id)
        row = self._repo.create_checklist_item(milestone_id, {
            "text": data.text,
            "sort_order": data.sort_order,
        })
        self._recalc_pressure(milestone_id, ms["initiative_id"])
        return ChecklistItem(
            id=row["id"],
            milestone_id=row["milestone_id"],
            text=row["text"],
            completed=row["completed"],
            sort_order=row.get("sort_order", 0),
        )

    def toggle_checklist(
        self, milestone_id: str, item_id: str, completed: bool,
    ) -> ChecklistItem:
        ms = self._assert_exists(milestone_id)
        row = self._repo.toggle_checklist_item(item_id, completed)
        self._recalc_pressure(milestone_id, ms["initiative_id"])
        return ChecklistItem(
            id=row["id"],
            milestone_id=row["milestone_id"],
            text=row["text"],
            completed=row["completed"],
            sort_order=row.get("sort_order", 0),
        )

    def delete_checklist_item(
        self, milestone_id: str, item_id: str,
    ) -> None:
        ms = self._assert_exists(milestone_id)
        self._repo.delete_checklist_item(item_id)
        self._recalc_pressure(milestone_id, ms["initiative_id"])

    # ── Dependencies ─────────────────────────────────────────────────

    def add_dependency(
        self, milestone_id: str, data: DependencyCreate,
    ) -> DependencyItem:
        ms = self._assert_exists(milestone_id)
        if self._repo.would_create_cycle(
            milestone_id, data.upstream_milestone_id,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Adding this dependency would create a cycle",
            )
        row = self._repo.create_dependency(
            milestone_id, data.upstream_milestone_id,
        )
        self._recalc_pressure(milestone_id, ms["initiative_id"])
        self._recalc_pressure(data.upstream_milestone_id, ms["initiative_id"])
        return DependencyItem(
            id=row["id"],
            upstream_milestone_id=row["upstream_milestone_id"],
            downstream_milestone_id=row["downstream_milestone_id"],
        )

    def delete_dependency(
        self, milestone_id: str, dependency_id: str,
    ) -> None:
        ms = self._assert_exists(milestone_id)
        deps = self._repo.get_dependencies(milestone_id)
        target_dep = next((d for d in deps if d["id"] == dependency_id), None)
        
        self._repo.delete_dependency(dependency_id)
        self._recalc_pressure(milestone_id, ms["initiative_id"])
        if target_dep:
            self._recalc_pressure(target_dep["upstream_milestone_id"], ms["initiative_id"])

    def list_all_dependencies(self) -> DependencyListResponse:
        """List all dependencies across the portfolio."""
        rows = self._repo.list_all_dependencies()
        items = []
        for r in rows:
            u = r.get("upstream") or {}
            d = r.get("downstream") or {}
            u_init = u.get("initiatives") or {}
            d_init = d.get("initiatives") or {}
            
            items.append(DependencyResponse(
                id=r["id"],
                upstream=MilestoneSummary(
                    id=u.get("id", ""),
                    name=u.get("name", ""),
                    initiative_code=u_init.get("initiative_code") if isinstance(u_init, dict) else None
                ),
                downstream=MilestoneSummary(
                    id=d.get("id", ""),
                    name=d.get("name", ""),
                    initiative_code=d_init.get("initiative_code") if isinstance(d_init, dict) else None
                )
            ))
        return DependencyListResponse(items=items, total=len(items))

    # ── Pressure ─────────────────────────────────────────────────────

    def get_pressure(
        self, milestone_id: str,
    ) -> MilestonePressureResult:
        ms = self._assert_exists(milestone_id)
        return self._calc_pressure(ms)

    # ── Helpers ──────────────────────────────────────────────────────

    def _assert_exists(self, milestone_id: str) -> dict:  # type: ignore[type-arg]
        row = self._repo.get(milestone_id)
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Milestone not found",
            )
        return row

    def _calc_pressure(
        self, milestone: dict,  # type: ignore[type-arg]
    ) -> MilestonePressureResult:
        mid = milestone["id"]
        iid = milestone["initiative_id"]
        downstream = self._repo.get_downstream(mid)
        transitive = self._repo.get_transitive_downstream_count(mid)
        siblings = self._repo.get_siblings(iid, mid)
        stats = self._repo.checklist_stats(mid)
        return MilestonePressureEngine.calculate(
            milestone, downstream, transitive, siblings, stats,
        )

    def _recalc_pressure(
        self, milestone_id: str, initiative_id: str,
    ) -> None:
        """Recalculate and persist pressure score."""
        ms = self._repo.get(milestone_id)
        if not ms:
            return
        result = self._calc_pressure(ms)
        self._repo.update(milestone_id, {
            "pressure_score": result.pressure_score,
            "pressure_blast_radius": result.blast_radius,
            "pressure_dep_urgency": result.dep_urgency,
            "pressure_cluster": result.cluster,
            "pressure_slack": result.slack,
            "pressure_checklist": result.checklist,
            "pressure_self_status": result.self_status,
        })

    def _to_item(self, row: dict) -> MilestoneItem:  # type: ignore[type-arg]
        owner = row.get("users") or {}
        initiative = row.get("initiatives") or {}
        chk_total, chk_done = self._repo.checklist_stats(row["id"])
        deps = self._repo.get_dependencies(row["id"])
        ps = row.get("pressure_score")
        return MilestoneItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            initiative_name=(
                initiative.get("name")
                if isinstance(initiative, dict) else None
            ),
            name=row["name"],
            description=row.get("description"),
            owner_id=row.get("owner_id"),
            owner_name=(
                owner.get("display_name")
                if isinstance(owner, dict) else None
            ),
            priority=row["priority"],
            status=row["status"],
            sort_order=row.get("sort_order", 0),
            planned_start=row.get("planned_start"),
            actual_start=row.get("actual_start"),
            planned_end=row.get("planned_end"),
            actual_end=row.get("actual_end"),
            pressure_score=str(ps) if ps is not None else None,
            pressure_level=(
                pressure_level(ps) if ps is not None else None
            ),
            checklist_total=chk_total,
            checklist_done=chk_done,
            dependency_count=len(deps),
        )

    def _to_detail(
        self,
        row: dict,  # type: ignore[type-arg]
        checklist_rows: list[dict],  # type: ignore[type-arg]
        dep_rows: list[dict],  # type: ignore[type-arg]
    ) -> MilestoneDetail:
        item = self._to_item(row)
        chk_items = [
            ChecklistItem(
                id=c["id"],
                milestone_id=c["milestone_id"],
                text=c["text"],
                completed=c.get("completed", False),
                sort_order=c.get("sort_order", 0),
            )
            for c in checklist_rows
        ]
        dep_items = [
            DependencyItem(
                id=d["id"],
                upstream_milestone_id=d["upstream_milestone_id"],
                downstream_milestone_id=d["downstream_milestone_id"],
            )
            for d in dep_rows
        ]
        def _str(v: object) -> str | None:
            return str(v) if v is not None else None

        return MilestoneDetail(
            **item.model_dump(),
            pressure_blast_radius=_str(row.get("pressure_blast_radius")),
            pressure_dep_urgency=_str(row.get("pressure_dep_urgency")),
            pressure_cluster=_str(row.get("pressure_cluster")),
            pressure_slack=_str(row.get("pressure_slack")),
            pressure_checklist=_str(row.get("pressure_checklist")),
            pressure_self_status=_str(row.get("pressure_self_status")),
            checklist=chk_items,
            dependencies=dep_items,
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )
