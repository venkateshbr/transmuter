"""Milestone repository — Supabase data access."""

from __future__ import annotations

from datetime import UTC
from uuid import UUID, uuid4

from supabase import Client


class MilestoneRepository:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._c = client
        self._tid = str(tenant_id)

    # ── Milestones ───────────────────────────────────────────────────

    def list(
        self, initiative_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("milestones")
            .select(
                "*, initiatives(name), users!milestones_owner_id_fkey(display_name)",
            )
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .order("sort_order")
            .order("planned_end")
            .execute()
        )
        return result.data or []

    def list_all(self) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("milestones")
            .select(
                "*, initiatives(name), users!milestones_owner_id_fkey(display_name)",
            )
            .eq("tenant_id", self._tid)
            .order("planned_end")
            .execute()
        )
        return result.data or []

    def get(self, milestone_id: str) -> dict | None:  # type: ignore[type-arg]
        result = (
            self._c.table("milestones")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("id", milestone_id)
            .maybe_single()
            .execute()
        )
        return result.data if result else None

    def create(self, initiative_id: str, data: dict) -> dict:  # type: ignore[type-arg]
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["initiative_id"] = initiative_id
        result = self._c.table("milestones").insert(data).execute()
        return result.data[0]

    def update(
        self, milestone_id: str, data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        from datetime import datetime
        data["updated_at"] = datetime.now(UTC).isoformat()
        result = (
            self._c.table("milestones")
            .update(data)
            .eq("tenant_id", self._tid)
            .eq("id", milestone_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete(self, milestone_id: str) -> None:
        (
            self._c.table("milestones")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", milestone_id)
            .execute()
        )

    def get_siblings(
        self, initiative_id: str, exclude_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("milestones")
            .select("id, status, planned_end, pressure_score")
            .eq("tenant_id", self._tid)
            .eq("initiative_id", initiative_id)
            .neq("id", exclude_id)
            .execute()
        )
        return result.data or []

    # ── Checklist ────────────────────────────────────────────────────

    def get_checklist(
        self, milestone_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        result = (
            self._c.table("milestone_checklist")
            .select("*")
            .eq("tenant_id", self._tid)
            .eq("milestone_id", milestone_id)
            .order("sort_order")
            .execute()
        )
        return result.data or []

    def checklist_stats(
        self, milestone_id: str,
    ) -> tuple[int, int]:
        rows = self.get_checklist(milestone_id)
        total = len(rows)
        done = sum(1 for r in rows if r.get("completed"))
        return total, done

    def create_checklist_item(
        self, milestone_id: str, data: dict,  # type: ignore[type-arg]
    ) -> dict:  # type: ignore[type-arg]
        data["id"] = str(uuid4())
        data["tenant_id"] = self._tid
        data["milestone_id"] = milestone_id
        result = (
            self._c.table("milestone_checklist")
            .insert(data).execute()
        )
        return result.data[0]

    def toggle_checklist_item(
        self, item_id: str, completed: bool,
    ) -> dict:  # type: ignore[type-arg]
        result = (
            self._c.table("milestone_checklist")
            .update({"completed": completed})
            .eq("tenant_id", self._tid)
            .eq("id", item_id)
            .execute()
        )
        return result.data[0] if result.data else {}

    def delete_checklist_item(self, item_id: str) -> None:
        (
            self._c.table("milestone_checklist")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", item_id)
            .execute()
        )

    # ── Dependencies ─────────────────────────────────────────────────

    def get_dependencies(
        self, milestone_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        """Get dependencies where this milestone is downstream."""
        result = (
            self._c.table("milestone_dependencies")
            .select(
                "*, "
                "upstream:milestones!upstream_milestone_id(id, name), "
                "downstream:milestones!downstream_milestone_id(id, name)"
            )
            .eq("tenant_id", self._tid)
            .eq("downstream_milestone_id", milestone_id)
            .execute()
        )
        return result.data or []

    def get_downstream(
        self, milestone_id: str,
    ) -> list[dict]:  # type: ignore[type-arg]
        """Get milestones that depend on this one (direct)."""
        dep_result = (
            self._c.table("milestone_dependencies")
            .select("downstream_milestone_id")
            .eq("tenant_id", self._tid)
            .eq("upstream_milestone_id", milestone_id)
            .execute()
        )
        deps = dep_result.data or []
        if not deps:
            return []
        ids = [d["downstream_milestone_id"] for d in deps]
        ms_result = (
            self._c.table("milestones")
            .select("id, name, planned_end, status")
            .in_("id", ids)
            .execute()
        )
        return ms_result.data or []

    def get_transitive_downstream_count(
        self, milestone_id: str,
    ) -> int:
        """Count transitive downstream (depth > 1)."""
        visited: set[str] = set()
        direct_ids: set[str] = set()
        queue = [milestone_id]
        depth = 0
        while queue:
            next_queue: list[str] = []
            for mid in queue:
                if mid in visited:
                    continue
                visited.add(mid)
                ds = (
                    self._c.table("milestone_dependencies")
                    .select("downstream_milestone_id")
                    .eq("tenant_id", self._tid)
                    .eq("upstream_milestone_id", mid)
                    .execute()
                )
                for d in ds.data or []:
                    did = d["downstream_milestone_id"]
                    if did not in visited:
                        next_queue.append(did)
                        if depth == 0:
                            direct_ids.add(did)
            queue = next_queue
            depth += 1
        # Subtract root + direct to get indirect only
        total_reachable = len(visited) - 1  # exclude root
        return max(total_reachable - len(direct_ids), 0)

    def create_dependency(
        self, downstream_id: str, upstream_id: str,
    ) -> dict:  # type: ignore[type-arg]
        data = {
            "id": str(uuid4()),
            "tenant_id": self._tid,
            "upstream_milestone_id": upstream_id,
            "downstream_milestone_id": downstream_id,
        }
        result = (
            self._c.table("milestone_dependencies")
            .insert(data).execute()
        )
        return result.data[0]

    def would_create_cycle(
        self, downstream_id: str, upstream_id: str,
    ) -> bool:
        """Check if adding upstream→downstream creates a cycle."""
        # A cycle exists if downstream can already reach upstream
        visited: set[str] = set()
        queue = [upstream_id]
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            if current == downstream_id:
                return True
            ups = (
                self._c.table("milestone_dependencies")
                .select("upstream_milestone_id")
                .eq("tenant_id", self._tid)
                .eq("downstream_milestone_id", current)
                .execute()
            )
            for u in ups.data or []:
                uid = u["upstream_milestone_id"]
                if uid not in visited:
                    queue.append(uid)
        return False

    def delete_dependency(self, dependency_id: str) -> None:
        (
            self._c.table("milestone_dependencies")
            .delete()
            .eq("tenant_id", self._tid)
            .eq("id", dependency_id)
            .execute()
        )

    def list_all_dependencies(self) -> list[dict]:  # type: ignore[type-arg]
        """List all dependencies with expanded upstream/downstream and initiative info."""
        result = (
            self._c.table("milestone_dependencies")
            .select(
                "id, "
                "upstream:milestones!upstream_milestone_id("
                "id, name, status, planned_end, pressure_score, initiatives(initiative_code)"
                "), "
                "downstream:milestones!downstream_milestone_id("
                "id, name, status, initiatives(initiative_code)"
                ")"
            )
            .eq("tenant_id", self._tid)
            .execute()
        )
        return result.data or []
