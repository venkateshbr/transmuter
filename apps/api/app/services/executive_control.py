"""Executive Control Tower service layer."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from supabase import Client

from app.core.auth import CurrentUser
from app.core.rbac import (
    ROLE_INITIATIVE_OWNER,
    ROLE_TRANSFORMATION_OFFICE,
    can_view_all_initiatives,
)
from app.domain.executive_control import (
    AllocationRuleCreate,
    AllocationRuleItem,
    AllocationRuleUpdate,
    AllocationRunCreate,
    AllocationRunItem,
    InitiativeDependencyCreate,
    InitiativeDependencyItem,
    InitiativeDependencyListResponse,
    InitiativeDependencyRollups,
    InitiativeDependencyUpdate,
    InitiativeRef,
    ReportFilterParams,
    ReportResponse,
    SharedCostAllocationItem,
    SharedCostPoolCreate,
    SharedCostPoolItem,
    SharedCostPoolListResponse,
    SharedCostPoolUpdate,
    ValueRealizationNoteCreate,
    ValueRealizationNoteItem,
)
from app.repositories.executive_control import ExecutiveControlRepository


def _dec(value: object) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _money(value: object) -> str:
    return format(_dec(value).quantize(Decimal("0.0001")), "f")


class ExecutiveControlService:
    def __init__(self, client: Client, tenant_id: UUID) -> None:
        self._repo = ExecutiveControlRepository(client, tenant_id)

    def list_dependencies(
        self,
        current_user: CurrentUser,
        initiative_id: str | None = None,
        filters: ReportFilterParams | None = None,
    ) -> InitiativeDependencyListResponse:
        items = [
            item
            for item in self._dependency_items()
            if self._can_view_dependency(current_user, item)
            and (not initiative_id or self._touches_initiative(item, initiative_id))
        ]
        if filters:
            initiatives = self._filtered_initiative_ids(filters, current_user)
            items = [
                item
                for item in items
                if item.upstream.id in initiatives or item.downstream.id in initiatives
            ]
        return InitiativeDependencyListResponse(
            items=items,
            total=len(items),
            rollups=self._dependency_rollups(items),
        )

    def create_dependency(self, data: InitiativeDependencyCreate) -> InitiativeDependencyItem:
        if data.upstream_initiative_id == data.downstream_initiative_id:
            raise HTTPException(status_code=400, detail="Dependency cannot point to itself")
        self._require_initiatives_exist(
            data.upstream_initiative_id,
            data.downstream_initiative_id,
        )
        if self._would_create_cycle(data.upstream_initiative_id, data.downstream_initiative_id):
            raise HTTPException(status_code=400, detail="Dependency would create a cycle")
        row = self._repo.create_dependency(self._dependency_payload(data.model_dump()))
        return self._dependency_item(self._hydrate_dependency(row))

    def update_dependency(
        self,
        dependency_id: str,
        data: InitiativeDependencyUpdate,
        current_user: CurrentUser,
    ) -> InitiativeDependencyItem:
        existing = self._repo.get_dependency(dependency_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Dependency not found")
        existing_item = self._dependency_item(self._hydrate_dependency(existing))
        patch = self._dependency_payload(data.model_dump(exclude_unset=True))
        if current_user.role == ROLE_TRANSFORMATION_OFFICE:
            pass
        elif current_user.role == ROLE_INITIATIVE_OWNER:
            if not self._can_view_dependency(current_user, existing_item):
                raise HTTPException(status_code=404, detail="Dependency not found")
            allowed = {"status", "resolution_notes"}
            if any(key not in allowed for key in patch):
                raise HTTPException(
                    status_code=403, detail="Owners can update status and notes only"
                )
        else:
            raise HTTPException(status_code=403, detail="Insufficient role")
        row = self._repo.update_dependency(dependency_id, patch)
        return self._dependency_item(self._hydrate_dependency(row))

    def delete_dependency(self, dependency_id: str) -> None:
        self._repo.delete_dependency(dependency_id)

    def list_pools(self, current_user: CurrentUser) -> SharedCostPoolListResponse:
        pools = [self._pool_item(row) for row in self._repo.list_pools()]
        if current_user.role == ROLE_INITIATIVE_OWNER:
            visible_ids = self._owned_initiative_ids(current_user)
            allocated_pool_ids = {
                row["pool_id"]
                for row in self._repo.list_allocations()
                if row.get("initiative_id") in visible_ids
            }
            pools = [pool for pool in pools if pool.id in allocated_pool_ids]
        return SharedCostPoolListResponse(items=pools, total=len(pools))

    def create_pool(self, data: SharedCostPoolCreate) -> SharedCostPoolItem:
        row = self._repo.create_pool(self._pool_payload(data.model_dump()))
        return self._pool_item(row)

    def update_pool(self, pool_id: str, data: SharedCostPoolUpdate) -> SharedCostPoolItem:
        row = self._repo.update_pool(
            pool_id, self._pool_payload(data.model_dump(exclude_unset=True))
        )
        return self._pool_item(row)

    def list_rules(self, pool_id: str) -> list[AllocationRuleItem]:
        return [self._rule_item(row) for row in self._repo.list_rules(pool_id)]

    def create_rule(self, pool_id: str, data: AllocationRuleCreate) -> AllocationRuleItem:
        if not self._repo.get_pool(pool_id):
            raise HTTPException(status_code=404, detail="Shared cost pool not found")
        row = self._repo.create_rule(pool_id, data.model_dump())
        return self._rule_item(row)

    def update_rule(
        self, pool_id: str, rule_id: str, data: AllocationRuleUpdate
    ) -> AllocationRuleItem:
        rule = self._repo.get_rule(rule_id)
        if not rule or rule.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Allocation rule not found")
        row = self._repo.update_rule(rule_id, data.model_dump(exclude_unset=True))
        return self._rule_item(row)

    def create_allocation_run(
        self,
        pool_id: str,
        data: AllocationRunCreate,
        current_user: CurrentUser,
    ) -> AllocationRunItem:
        pool = self._repo.get_pool(pool_id)
        rule = self._repo.get_rule(data.rule_id)
        if not pool or not rule or rule.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Pool or allocation rule not found")
        amount_plan = _dec(pool.get("amount_plan"))
        amount_actual = _dec(pool.get("amount_actual"))
        allocations = self._build_allocations(pool, rule, data.scenario)
        run = self._repo.create_run(
            {
                "pool_id": pool_id,
                "rule_id": data.rule_id,
                "scenario": data.scenario,
                "status": "completed",
                "total_amount_plan": _money(amount_plan),
                "total_amount_actual": _money(amount_actual)
                if pool.get("amount_actual") is not None
                else None,
                "created_by": str(current_user.id),
            },
            allocations,
        )
        return self._run_item({**run, "shared_cost_allocations": allocations})

    def list_runs(self, pool_id: str) -> list[AllocationRunItem]:
        return [self._run_item(row) for row in self._repo.list_runs(pool_id)]

    def create_value_note(
        self,
        initiative_id: str,
        data: ValueRealizationNoteCreate,
        current_user: CurrentUser,
    ) -> ValueRealizationNoteItem:
        if current_user.role == ROLE_INITIATIVE_OWNER:
            if initiative_id not in self._owned_initiative_ids(current_user):
                raise HTTPException(status_code=404, detail="Initiative not found")
        elif current_user.role != ROLE_TRANSFORMATION_OFFICE:
            raise HTTPException(status_code=403, detail="Insufficient role")
        row = self._repo.create_value_note(
            initiative_id,
            str(current_user.id),
            self._value_note_payload(data.model_dump()),
        )
        return self._note_item(row)

    def list_value_notes(
        self,
        initiative_id: str,
        current_user: CurrentUser,
    ) -> list[ValueRealizationNoteItem]:
        if (
            current_user.role == ROLE_INITIATIVE_OWNER
            and initiative_id not in self._owned_initiative_ids(current_user)
        ):
            raise HTTPException(status_code=404, detail="Initiative not found")
        return [self._note_item(row) for row in self._repo.list_value_notes(initiative_id)]

    def owner_cockpit(
        self, current_user: CurrentUser, filters: ReportFilterParams
    ) -> ReportResponse:
        filters.owner_id = str(current_user.id)
        return self._report("owner", current_user, filters)

    def management_report(
        self,
        current_user: CurrentUser,
        filters: ReportFilterParams,
    ) -> ReportResponse:
        return self._report("management", current_user, filters)

    def investor_report(
        self,
        current_user: CurrentUser,
        filters: ReportFilterParams,
    ) -> ReportResponse:
        return self._report("investor", current_user, filters)

    def _report(
        self,
        persona: str,
        current_user: CurrentUser,
        filters: ReportFilterParams,
    ) -> ReportResponse:
        initiative_ids = self._filtered_initiative_ids(filters, current_user)
        initiatives = [row for row in self._repo.list_initiatives() if row["id"] in initiative_ids]
        entries = [
            row
            for row in self._repo.list_financial_entries()
            if row.get("initiative_id") in initiative_ids
        ]
        costs = [
            row
            for row in self._repo.list_direct_cost_lines()
            if row.get("initiative_id") in initiative_ids
        ]
        allocations = [
            row
            for row in self._repo.list_allocations()
            if row.get("initiative_id") in initiative_ids
        ]
        if filters.target_year:
            entries = [row for row in entries if row.get("year") == filters.target_year]
            costs = [row for row in costs if row.get("year") == filters.target_year]
            allocations = [
                row
                for row in allocations
                if (row.get("shared_cost_pools") or {}).get("year") == filters.target_year
            ]
        dependencies = self.list_dependencies(current_user, filters=filters).rollups
        value_bridge = self._value_bridge(entries, costs, allocations)
        attention = self._needs_attention(initiatives, entries, allocations, dependencies)
        rows = self._initiative_report_rows(initiatives, entries, costs, allocations)
        summary = {
            "initiative_count": len(initiatives),
            "red": sum(1 for row in initiatives if row.get("rag_status") == "red"),
            "amber": sum(1 for row in initiatives if row.get("rag_status") == "amber"),
            "realized": sum(
                1 for row in initiatives if row.get("realization_status") == "realized"
            ),
            "needs_attention": len(attention),
        }
        return ReportResponse(
            persona=persona,  # type: ignore[arg-type]
            summary=summary,
            value_bridge=value_bridge,
            cost_allocation={
                "allocated_plan": _money(
                    sum((_dec(row.get("allocated_plan")) for row in allocations), Decimal("0"))
                ),
                "allocated_actual": _money(
                    sum((_dec(row.get("allocated_actual")) for row in allocations), Decimal("0"))
                ),
            },
            dependency_risk=dependencies,
            needs_attention=attention[:20],
            initiatives=rows,
        )

    def _build_allocations(self, pool: dict, rule: dict, scenario: str) -> list[dict]:
        candidates = self._allocation_candidates(rule.get("filters") or {})
        if not candidates:
            return []
        entries = self._repo.list_financial_entries()
        amount_plan = _dec(pool.get("amount_plan"))
        amount_actual = _dec(pool.get("amount_actual"))
        basis = self._basis_values(candidates, entries, rule)
        total_basis = sum(basis.values(), Decimal("0"))
        rows = []
        remaining_plan = amount_plan
        remaining_actual = amount_actual
        for index, initiative in enumerate(candidates):
            initiative_id = initiative["id"]
            if total_basis == 0:
                share = Decimal("1") / Decimal(len(candidates))
            else:
                share = basis[initiative_id] / total_basis
            if index == len(candidates) - 1:
                allocated_plan = remaining_plan
                allocated_actual = remaining_actual
            else:
                allocated_plan = (amount_plan * share).quantize(Decimal("0.0001"))
                allocated_actual = (amount_actual * share).quantize(Decimal("0.0001"))
                remaining_plan -= allocated_plan
                remaining_actual -= allocated_actual
            rows.append(
                {
                    "initiative_id": initiative_id,
                    "allocation_basis": rule["allocation_method"],
                    "basis_value": _money(basis[initiative_id]),
                    "allocated_plan": _money(allocated_plan),
                    "allocated_actual": _money(allocated_actual)
                    if scenario == "actual" and pool.get("amount_actual") is not None
                    else None,
                }
            )
        return rows

    def _allocation_candidates(self, filters: dict[str, Any]) -> list[dict]:
        initiatives = self._repo.list_initiatives()
        return [row for row in initiatives if self._matches_filters(row, filters)]

    def _basis_values(
        self, candidates: list[dict], entries: list[dict], rule: dict
    ) -> dict[str, Decimal]:
        method = rule["allocation_method"]
        weights = rule.get("weights") or {}
        values: dict[str, Decimal] = {}
        for row in candidates:
            initiative_id = row["id"]
            if method == "fixed_percentage" or method == "manual_amount":
                values[initiative_id] = _dec(weights.get(initiative_id))
            elif method == "benefit_weighted":
                values[initiative_id] = sum(
                    (
                        _dec(entry.get("gm_uplift_base"))
                        for entry in entries
                        if entry.get("initiative_id") == initiative_id
                    ),
                    Decimal("0"),
                )
            elif method == "revenue_weighted":
                values[initiative_id] = sum(
                    (
                        _dec(entry.get("revenue_uplift_base"))
                        for entry in entries
                        if entry.get("initiative_id") == initiative_id
                    ),
                    Decimal("0"),
                )
            elif method == "headcount_weighted":
                values[initiative_id] = _dec(weights.get(initiative_id, 1))
            else:
                values[initiative_id] = Decimal("1")
        return values

    def _dependency_items(self) -> list[InitiativeDependencyItem]:
        return [self._dependency_item(row) for row in self._repo.list_dependencies()]

    def _require_initiatives_exist(self, *initiative_ids: str) -> None:
        existing = {row["id"] for row in self._repo.list_initiatives()}
        if any(initiative_id not in existing for initiative_id in initiative_ids):
            raise HTTPException(status_code=404, detail="Initiative not found")

    def _dependency_item(self, row: dict) -> InitiativeDependencyItem:
        upstream = self._initiative_ref(row.get("upstream") or {})
        downstream = self._initiative_ref(row.get("downstream") or {})
        due = self._date(row.get("due_date"))
        status_value = row.get("status", "proposed")
        return InitiativeDependencyItem(
            id=row["id"],
            upstream=upstream,
            downstream=downstream,
            dependency_type=row.get("dependency_type", "blocks"),
            status=status_value,
            severity=row.get("severity", "medium"),
            owner_id=row.get("owner_id"),
            owner_name=(row.get("owner") or {}).get("display_name"),
            due_date=row.get("due_date"),
            resolution_notes=row.get("resolution_notes"),
            linked_milestone_id=row.get("linked_milestone_id"),
            linked_action_item_id=row.get("linked_action_item_id"),
            is_overdue=bool(
                due and due < date.today() and status_value not in {"resolved", "cancelled"}
            ),
            blast_radius=self._blast_radius(row.get("upstream_initiative_id") or upstream.id),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def _hydrate_dependency(self, row: dict) -> dict:
        for candidate in self._repo.list_dependencies():
            if candidate["id"] == row["id"]:
                return candidate
        return row

    def _dependency_rollups(
        self, items: list[InitiativeDependencyItem]
    ) -> InitiativeDependencyRollups:
        active = [item for item in items if item.status not in {"resolved", "cancelled"}]
        blocked = [
            item.downstream
            for item in active
            if item.status == "blocking" or item.dependency_type == "blocks"
        ]
        blocker_counts: dict[str, dict[str, Any]] = {}
        for item in active:
            slot = blocker_counts.setdefault(
                item.upstream.id,
                {"initiative": item.upstream.model_dump(), "blocking_count": 0, "blast_radius": 0},
            )
            slot["blocking_count"] += 1
            slot["blast_radius"] = max(slot["blast_radius"], item.blast_radius)
        top = sorted(
            blocker_counts.values(),
            key=lambda row: (row["blocking_count"], row["blast_radius"]),
            reverse=True,
        )
        return InitiativeDependencyRollups(
            total=len(items),
            blocking=sum(1 for item in items if item.status == "blocking"),
            at_risk=sum(1 for item in items if item.status == "at_risk"),
            overdue=sum(1 for item in items if item.is_overdue),
            resolved=sum(1 for item in items if item.status == "resolved"),
            critical_path_risk=sum(
                1
                for item in active
                if item.severity == "high" and item.status in {"blocking", "at_risk", "active"}
            ),
            blocked_initiatives=list({item.id: item for item in blocked}.values()),
            top_blockers=top[:5],
        )

    def _blast_radius(self, initiative_id: str) -> int:
        graph: dict[str, list[str]] = defaultdict(list)
        for row in self._repo.list_dependencies():
            if row.get("status") in {"resolved", "cancelled"}:
                continue
            graph[row["upstream_initiative_id"]].append(row["downstream_initiative_id"])
        visited: set[str] = set()
        queue = list(graph.get(initiative_id, []))
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            queue.extend(graph.get(current, []))
        return len(visited)

    def _would_create_cycle(self, upstream_id: str, downstream_id: str) -> bool:
        graph: dict[str, list[str]] = defaultdict(list)
        for row in self._repo.list_dependencies():
            graph[row["upstream_initiative_id"]].append(row["downstream_initiative_id"])
        graph[upstream_id].append(downstream_id)
        queue = list(graph.get(downstream_id, []))
        visited: set[str] = set()
        while queue:
            current = queue.pop(0)
            if current == upstream_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(graph.get(current, []))
        return False

    def _filtered_initiative_ids(
        self, filters: ReportFilterParams, current_user: CurrentUser
    ) -> set[str]:
        rows = self._repo.list_initiatives()
        filtered = [
            row for row in rows if self._matches_filters(row, filters.model_dump(exclude_none=True))
        ]
        if current_user.role == ROLE_INITIATIVE_OWNER:
            owned = self._owned_initiative_ids(current_user)
            filtered = [row for row in filtered if row["id"] in owned]
        return {row["id"] for row in filtered}

    def _owned_initiative_ids(self, current_user: CurrentUser) -> set[str]:
        uid = str(current_user.id)
        return {
            row["id"]
            for row in self._repo.list_initiatives()
            if row.get("owner_id") == uid or row.get("group_owner_id") == uid
        }

    def _matches_filters(self, row: dict, filters: dict[str, Any]) -> bool:
        if filters.get("business_unit_id") and filters["business_unit_id"] not in {
            link.get("business_unit_id")
            for link in row.get("initiative_business_units") or []
            if link.get("business_unit_id")
        }:
            return False
        for key in ("workstream_id", "tag", "country", "rag_status", "stage", "owner_id"):
            if filters.get(key) and row.get(key) != filters[key]:
                return False
        return True

    def _can_view_dependency(
        self, current_user: CurrentUser, item: InitiativeDependencyItem
    ) -> bool:
        if can_view_all_initiatives(current_user.role):
            return True
        uid = str(current_user.id)
        return (
            item.upstream.owner_id == uid or item.downstream.owner_id == uid or item.owner_id == uid
        )

    @staticmethod
    def _touches_initiative(item: InitiativeDependencyItem, initiative_id: str) -> bool:
        return item.upstream.id == initiative_id or item.downstream.id == initiative_id

    @staticmethod
    def _initiative_ref(row: dict) -> InitiativeRef:
        ws = row.get("workstreams") or {}
        return InitiativeRef(
            id=row["id"],
            initiative_code=row.get("initiative_code"),
            name=row.get("name") or "Untitled initiative",
            owner_id=row.get("owner_id"),
            workstream_id=row.get("workstream_id"),
            workstream_name=ws.get("name") if isinstance(ws, dict) else None,
            rag_status=row.get("rag_status"),
            stage=row.get("stage"),
        )

    def _pool_item(self, row: dict) -> SharedCostPoolItem:
        allocations = [a for a in self._repo.list_allocations() if a.get("pool_id") == row["id"]]
        return SharedCostPoolItem(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            category_key=row.get("category_key", "other"),
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            amount_plan=_money(row.get("amount_plan")),
            amount_actual=_money(row.get("amount_actual"))
            if row.get("amount_actual") is not None
            else None,
            is_recurring=bool(row.get("is_recurring")),
            status=row.get("status", "draft"),
            allocated_plan=_money(
                sum((_dec(a.get("allocated_plan")) for a in allocations), Decimal("0"))
            ),
            allocated_actual=_money(
                sum((_dec(a.get("allocated_actual")) for a in allocations), Decimal("0"))
            ),
            created_at=row.get("created_at"),
        )

    @staticmethod
    def _rule_item(row: dict) -> AllocationRuleItem:
        return AllocationRuleItem(
            id=row["id"],
            pool_id=row["pool_id"],
            name=row["name"],
            allocation_method=row["allocation_method"],
            filters=row.get("filters") or {},
            weights=row.get("weights") or {},
            is_active=bool(row.get("is_active", True)),
        )

    @staticmethod
    def _run_item(row: dict) -> AllocationRunItem:
        allocation_rows = row.get("shared_cost_allocations") or []
        return AllocationRunItem(
            id=row["id"],
            pool_id=row["pool_id"],
            rule_id=row["rule_id"],
            scenario=row.get("scenario", "plan"),
            status=row.get("status", "completed"),
            total_amount_plan=_money(row.get("total_amount_plan")),
            total_amount_actual=_money(row.get("total_amount_actual"))
            if row.get("total_amount_actual") is not None
            else None,
            created_by=row.get("created_by"),
            created_at=row["created_at"],
            allocations=[
                SharedCostAllocationItem(
                    id=allocation.get("id", ""),
                    initiative_id=allocation["initiative_id"],
                    initiative_name=(allocation.get("initiatives") or {}).get("name"),
                    allocation_basis=allocation["allocation_basis"],
                    basis_value=_money(allocation.get("basis_value")),
                    allocated_plan=_money(allocation.get("allocated_plan")),
                    allocated_actual=_money(allocation.get("allocated_actual"))
                    if allocation.get("allocated_actual") is not None
                    else None,
                )
                for allocation in allocation_rows
            ],
        )

    @staticmethod
    def _dependency_payload(data: dict) -> dict:
        return {key: value for key, value in data.items() if value is not None}

    @staticmethod
    def _pool_payload(data: dict) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        for key in ("amount_plan", "amount_actual"):
            if key in payload:
                payload[key] = _money(payload[key])
        return payload

    @staticmethod
    def _value_note_payload(data: dict) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        for key in ("planned_value", "actual_value"):
            if key in payload:
                payload[key] = _money(payload[key])
        return payload

    @staticmethod
    def _note_item(row: dict) -> ValueRealizationNoteItem:
        return ValueRealizationNoteItem(
            id=row["id"],
            initiative_id=row["initiative_id"],
            author_id=row.get("author_id"),
            note_type=row["note_type"],
            period_label=row.get("period_label"),
            planned_value=_money(row.get("planned_value"))
            if row.get("planned_value") is not None
            else None,
            actual_value=_money(row.get("actual_value"))
            if row.get("actual_value") is not None
            else None,
            explanation=row["explanation"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _date(value: object) -> date | None:
        if not value:
            return None
        if isinstance(value, date):
            return value
        return date.fromisoformat(str(value)[:10])

    def _value_bridge(
        self,
        entries: list[dict],
        costs: list[dict],
        allocations: list[dict],
    ) -> dict[str, str]:
        benefits_plan = sum((_dec(row.get("gm_uplift_base")) for row in entries), Decimal("0"))
        benefits_actual = sum((_dec(row.get("gm_uplift_actual")) for row in entries), Decimal("0"))
        direct_plan = sum((_dec(row.get("amount_plan")) for row in costs), Decimal("0"))
        direct_actual = sum((_dec(row.get("amount_actual")) for row in costs), Decimal("0"))
        allocated_plan = sum((_dec(row.get("allocated_plan")) for row in allocations), Decimal("0"))
        allocated_actual = sum(
            (_dec(row.get("allocated_actual")) for row in allocations), Decimal("0")
        )
        return {
            "benefits_plan": _money(benefits_plan),
            "benefits_actual": _money(benefits_actual),
            "direct_costs_plan": _money(direct_plan),
            "direct_costs_actual": _money(direct_actual),
            "allocated_costs_plan": _money(allocated_plan),
            "allocated_costs_actual": _money(allocated_actual),
            "total_burdened_costs_plan": _money(direct_plan + allocated_plan),
            "total_burdened_costs_actual": _money(direct_actual + allocated_actual),
            "net_before_allocation_plan": _money(benefits_plan - direct_plan),
            "net_after_allocation_plan": _money(benefits_plan - direct_plan - allocated_plan),
            "net_after_allocation_actual": _money(
                benefits_actual - direct_actual - allocated_actual
            ),
        }

    def _needs_attention(
        self,
        initiatives: list[dict],
        entries: list[dict],
        allocations: list[dict],
        dependencies: InitiativeDependencyRollups,
    ) -> list[dict[str, Any]]:
        attention: list[dict[str, Any]] = []
        actual_ids = {
            row["initiative_id"]
            for row in entries
            if row.get("gm_uplift_actual") is not None
            or row.get("revenue_uplift_actual") is not None
        }
        by_init_alloc = defaultdict(Decimal)
        for row in allocations:
            by_init_alloc[row["initiative_id"]] += _dec(row.get("allocated_plan"))
        for row in initiatives:
            iid = row["id"]
            if iid not in actual_ids and row.get("stage") == "in_progress":
                attention.append({"initiative_id": iid, "reason": "Missing actuals"})
            if row.get("realization_status") == "at_risk":
                attention.append({"initiative_id": iid, "reason": "Value realization at risk"})
            if (
                by_init_alloc[iid] > Decimal("0")
                and row.get("benefit_confidence")
                and _dec(row["benefit_confidence"]) < Decimal("50")
            ):
                attention.append(
                    {"initiative_id": iid, "reason": "Low confidence with allocated shared cost"}
                )
        for item in dependencies.blocked_initiatives:
            attention.append({"initiative_id": item.id, "reason": "Blocked by active dependency"})
        return attention

    def _initiative_report_rows(
        self,
        initiatives: list[dict],
        entries: list[dict],
        costs: list[dict],
        allocations: list[dict],
    ) -> list[dict[str, Any]]:
        rows = []
        for initiative in initiatives:
            iid = initiative["id"]
            i_entries = [row for row in entries if row.get("initiative_id") == iid]
            i_costs = [row for row in costs if row.get("initiative_id") == iid]
            i_alloc = [row for row in allocations if row.get("initiative_id") == iid]
            bridge = self._value_bridge(i_entries, i_costs, i_alloc)
            rows.append(
                {
                    "id": iid,
                    "initiative_code": initiative.get("initiative_code"),
                    "name": initiative.get("name"),
                    "owner_id": initiative.get("owner_id"),
                    "rag_status": initiative.get("rag_status"),
                    "stage": initiative.get("stage"),
                    "realization_status": initiative.get("realization_status"),
                    "benefit_confidence": str(initiative.get("benefit_confidence") or "0"),
                    **bridge,
                }
            )
        return rows
