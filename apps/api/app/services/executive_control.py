"""Executive Control Tower service layer."""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import UTC, date, datetime
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
    AllocationExceptionItem,
    AllocationPreviewRequest,
    AllocationPreviewResponse,
    AllocationReconciliation,
    AllocationRuleCreate,
    AllocationRuleItem,
    AllocationRuleUpdate,
    AllocationRunCreate,
    AllocationRunItem,
    AllocationTargetItem,
    AllocationTargetUpsert,
    AllocationWeightItem,
    AllocationWeightUpsert,
    InitiativeDependencyCreate,
    InitiativeDependencyItem,
    InitiativeDependencyListResponse,
    InitiativeDependencyRollups,
    InitiativeDependencyUpdate,
    InitiativeRef,
    ReportFilterParams,
    ReportResponse,
    SharedCostAllocationItem,
    SharedCostConfigResponse,
    SharedCostPoolCreate,
    SharedCostPoolItem,
    SharedCostPoolListResponse,
    SharedCostPoolPeriodItem,
    SharedCostPoolPeriodUpsert,
    SharedCostPoolUpdate,
    SharedCostReportingSettings,
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

    def shared_cost_config(self) -> SharedCostConfigResponse:
        initiatives = self._repo.list_initiatives()
        workstreams = self._repo.list_workstreams()
        business_units = self._repo.list_business_units()
        return SharedCostConfigResponse(
            cost_categories=self._repo.list_cost_categories(),
            scenarios=self._repo.list_financial_scenarios(),
            metric_definitions=self._repo.list_metric_definitions(),
            initiatives=[
                {
                    "id": row["id"],
                    "initiative_code": row.get("initiative_code"),
                    "name": row.get("name"),
                    "workstream_id": row.get("workstream_id"),
                    "tag": row.get("tag"),
                    "stage": row.get("stage"),
                    "rag_status": row.get("rag_status"),
                }
                for row in initiatives
            ],
            workstreams=workstreams,
            business_units=business_units,
            tags=sorted({row.get("tag") for row in initiatives if row.get("tag")}),
            countries=sorted({row.get("country") for row in initiatives if row.get("country")}),
            stages=sorted({row.get("stage") for row in initiatives if row.get("stage")}),
            allocation_methods=[
                {"key": "equal_split", "label": "Equal split"},
                {"key": "fixed_percentage", "label": "Fixed percentage"},
                {"key": "manual_amount", "label": "Manual amount"},
                {"key": "benefit_weighted", "label": "Benefit weighted"},
                {"key": "revenue_weighted", "label": "Revenue weighted"},
                {"key": "savings_weighted", "label": "Savings weighted"},
                {"key": "direct_cost_weighted", "label": "Direct cost weighted"},
                {"key": "headcount_weighted", "label": "Headcount weighted"},
                {"key": "metric_weighted", "label": "Metric weighted"},
            ],
            reporting_settings=self._settings_item(self._repo.get_reporting_settings()),
        )

    def get_reporting_settings(self) -> SharedCostReportingSettings:
        getter = getattr(self._repo, "get_reporting_settings", None)
        if not getter:
            return SharedCostReportingSettings()
        return self._settings_item(getter())

    def update_reporting_settings(
        self, data: SharedCostReportingSettings
    ) -> SharedCostReportingSettings:
        return self._settings_item(self._repo.update_reporting_settings(data.model_dump()))

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

    def list_pool_periods(self, pool_id: str) -> list[SharedCostPoolPeriodItem]:
        if not self._repo.get_pool(pool_id):
            raise HTTPException(status_code=404, detail="Shared cost pool not found")
        return [self._period_item(row) for row in self._repo.list_pool_periods(pool_id)]

    def replace_pool_periods(
        self, pool_id: str, periods: list[SharedCostPoolPeriodUpsert]
    ) -> list[SharedCostPoolPeriodItem]:
        if not self._repo.get_pool(pool_id):
            raise HTTPException(status_code=404, detail="Shared cost pool not found")
        rows = [self._period_payload(period.model_dump(exclude_none=True)) for period in periods]
        return [self._period_item(row) for row in self._repo.replace_pool_periods(pool_id, rows)]

    def list_rules(self, pool_id: str) -> list[AllocationRuleItem]:
        return [self._rule_item(row) for row in self._repo.list_rules(pool_id)]

    def create_rule(self, pool_id: str, data: AllocationRuleCreate) -> AllocationRuleItem:
        if not self._repo.get_pool(pool_id):
            raise HTTPException(status_code=404, detail="Shared cost pool not found")
        row = self._repo.create_rule(pool_id, self._rule_payload(data.model_dump()))
        return self._rule_item(row)

    def update_rule(
        self, pool_id: str, rule_id: str, data: AllocationRuleUpdate
    ) -> AllocationRuleItem:
        rule = self._repo.get_rule(rule_id)
        if not rule or rule.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Allocation rule not found")
        row = self._repo.update_rule(
            rule_id, self._rule_payload(data.model_dump(exclude_unset=True))
        )
        return self._rule_item(row)

    def replace_rule_targets(
        self,
        pool_id: str,
        rule_id: str,
        targets: list[AllocationTargetUpsert],
    ) -> list[AllocationTargetItem]:
        self._require_rule_for_pool(pool_id, rule_id)
        rows = self._repo.replace_rule_targets(
            rule_id,
            [target.model_dump(exclude_none=True) for target in targets],
        )
        return [self._target_item(row) for row in rows]

    def replace_rule_weights(
        self,
        pool_id: str,
        rule_id: str,
        weights: list[AllocationWeightUpsert],
    ) -> list[AllocationWeightItem]:
        self._require_rule_for_pool(pool_id, rule_id)
        rows = self._repo.replace_rule_weights(
            rule_id,
            [self._weight_payload(weight.model_dump(exclude_none=True)) for weight in weights],
        )
        return [self._weight_item(row) for row in rows]

    def preview_allocation_run(
        self,
        pool_id: str,
        data: AllocationPreviewRequest,
    ) -> AllocationPreviewResponse:
        pool, rule = self._pool_and_rule(pool_id, data.rule_id)
        return self._allocation_preview(pool, rule, data.scenario, data.scenario_id)

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
        preview = self._allocation_preview(pool, rule, data.scenario, data.scenario_id)
        blocking = [exc for exc in preview.exceptions if exc.severity == "blocking"]
        if blocking:
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Allocation preview has blocking exceptions",
                    "exceptions": [exc.model_dump() for exc in blocking],
                },
            )
        amount_plan = _dec(preview.reconciliation.pool_amount_plan)
        amount_actual = _dec(preview.reconciliation.pool_amount_actual)
        allocations = [
            {
                "initiative_id": row.initiative_id,
                "allocation_basis": row.allocation_basis,
                "basis_value": row.basis_value,
                "allocated_plan": row.allocated_plan,
                "allocated_actual": row.allocated_actual,
                "allocation_share": row.allocation_share,
                "rounding_adjustment": row.rounding_adjustment,
                "basis_label": row.basis_label,
                "explanation": row.explanation,
                "exception_flags": row.exception_flags,
                "period_start": preview.pool.metadata.get("period_start"),
                "period_end": preview.pool.metadata.get("period_end"),
                "scenario_id": preview.scenario_id,
                "basis_metric_definition_id": rule.get("driver_metric_definition_id"),
            }
            for row in preview.allocations
        ]
        now = datetime.now(UTC).isoformat()
        run = self._repo.create_run(
            {
                "pool_id": pool_id,
                "rule_id": data.rule_id,
                "scenario": data.scenario,
                "scenario_id": preview.scenario_id,
                "status": data.status,
                "run_type": data.run_type,
                "rule_version": rule.get("version") or 1,
                "total_amount_plan": _money(amount_plan),
                "total_amount_actual": _money(amount_actual)
                if pool.get("amount_actual") is not None
                else None,
                "period_start": preview.pool.metadata.get("period_start"),
                "period_end": preview.pool.metadata.get("period_end"),
                "input_snapshot": {
                    "pool": preview.pool.model_dump(),
                    "rule": preview.rule.model_dump(),
                },
                "exception_summary": {
                    "count": len(preview.exceptions),
                    "blocking": len(blocking),
                    "exceptions": [exc.model_dump() for exc in preview.exceptions],
                },
                "reporting_treatment": pool.get("reporting_treatment") or "report_only",
                "approved_by": str(current_user.id),
                "approved_at": now,
                "locked_by": str(current_user.id) if data.status in {"locked", "posted"} else None,
                "locked_at": now if data.status in {"locked", "posted"} else None,
                "created_by": str(current_user.id),
            },
            allocations,
        )
        self._repo.create_exceptions(
            [
                {
                    "run_id": run["id"],
                    "rule_id": data.rule_id,
                    "pool_id": pool_id,
                    "initiative_id": exc.initiative_id,
                    "exception_type": exc.exception_type,
                    "severity": exc.severity,
                    "message": exc.message,
                    "metadata": exc.metadata,
                }
                for exc in preview.exceptions
            ]
        )
        self._audit(
            "allocation_run_created",
            current_user,
            pool_id=pool_id,
            rule_id=data.rule_id,
            run_id=run["id"],
            after_state={
                "status": data.status,
                "reconciliation": preview.reconciliation.model_dump(),
            },
        )
        return self._run_item({**run, "shared_cost_allocations": allocations})

    def list_runs(self, pool_id: str) -> list[AllocationRunItem]:
        return [self._run_item(row) for row in self._repo.list_runs(pool_id)]

    def list_shared_cost_allocations(self) -> list[SharedCostAllocationItem]:
        return [
            SharedCostAllocationItem(
                id=row.get("id", ""),
                initiative_id=row["initiative_id"],
                initiative_name=None,
                allocation_basis=row["allocation_basis"],
                basis_value=_money(row.get("basis_value")),
                allocated_plan=_money(row.get("allocated_plan")),
                allocated_actual=_money(row.get("allocated_actual"))
                if row.get("allocated_actual") is not None
                else None,
                allocation_share=format(_dec(row.get("allocation_share")), "f"),
                rounding_adjustment=_money(row.get("rounding_adjustment")),
                basis_label=row.get("basis_label"),
                explanation=row.get("explanation"),
                exception_flags=row.get("exception_flags") or {},
            )
            for row in self._repo.list_allocations()
        ]

    def approve_run(
        self,
        pool_id: str,
        run_id: str,
        current_user: CurrentUser,
        lock: bool = False,
    ) -> AllocationRunItem:
        run = self._repo.get_run(run_id)
        if not run or run.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Allocation run not found")
        now = datetime.now(UTC).isoformat()
        patch: dict[str, Any] = {
            "status": "locked" if lock else "approved",
            "approved_by": str(current_user.id),
            "approved_at": now,
        }
        if lock:
            patch["locked_by"] = str(current_user.id)
            patch["locked_at"] = now
        updated = self._repo.update_run(run_id, patch)
        self._audit(
            "allocation_run_locked" if lock else "allocation_run_approved",
            current_user,
            pool_id=pool_id,
            run_id=run_id,
            before_state={"status": run.get("status")},
            after_state=patch,
        )
        return self._run_item({**run, **updated})

    def void_run(
        self,
        pool_id: str,
        run_id: str,
        reason: str,
        current_user: CurrentUser,
    ) -> AllocationRunItem:
        if not reason.strip():
            raise HTTPException(status_code=400, detail="Void reason is required")
        run = self._repo.get_run(run_id)
        if not run or run.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Allocation run not found")
        updated = self._repo.update_run(run_id, {"status": "voided", "void_reason": reason})
        self._audit(
            "allocation_run_voided",
            current_user,
            pool_id=pool_id,
            run_id=run_id,
            before_state={"status": run.get("status")},
            after_state={"status": "voided", "void_reason": reason},
        )
        return self._run_item({**run, **updated})

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
        settings = self.get_reporting_settings()
        if not settings.include_in_executive_control_tower:
            allocations = []
        else:
            allocations = [
                row
                for row in allocations
                if (row.get("shared_cost_allocation_runs") or {}).get("status", "completed")
                in {"locked", "posted", "completed"}
            ]
        available_years = sorted(
            {
                int(year)
                for year in [
                    *[row.get("year") for row in entries],
                    *[row.get("year") for row in costs],
                    *[self._allocation_year(row) for row in allocations],
                ]
                if year is not None
            }
        )
        selected_year = (
            filters.target_year
            if filters.target_year is not None
            else (available_years[-1] if available_years else None)
        )
        if selected_year:
            entries = [row for row in entries if row.get("year") == selected_year]
            costs = [row for row in costs if row.get("year") == selected_year]
            allocations = [
                row
                for row in allocations
                if self._allocation_year(row) == selected_year
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
            selected_year=selected_year,
            available_years=available_years,
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

    def _allocation_preview(
        self,
        pool: dict,
        rule: dict,
        scenario: str,
        scenario_id: str | None = None,
    ) -> AllocationPreviewResponse:
        scenario_id = scenario_id or pool.get("scenario_id") or self._scenario_id_for(scenario)
        period_start, period_end = self._period_bounds(pool)
        amount_plan = _dec(pool.get("amount_plan"))
        amount_actual = _dec(pool.get("amount_actual"))
        candidates, excluded, target_exceptions = self._allocation_candidates(rule)
        exceptions: list[AllocationExceptionItem] = target_exceptions
        if not candidates:
            exceptions.append(
                AllocationExceptionItem(
                    exception_type="no_candidates",
                    severity="blocking",
                    message="Allocation policy did not select any initiatives.",
                )
            )
        basis = self._basis_values(candidates, rule, scenario_id, period_start.year)
        exceptions.extend(basis["exceptions"])
        allocations = self._allocation_rows(
            candidates,
            rule,
            basis["values"],
            amount_plan,
            amount_actual,
            scenario,
            basis["label"],
            exceptions,
        )
        allocated_plan = sum((_dec(row.allocated_plan) for row in allocations), Decimal("0"))
        allocated_actual = sum((_dec(row.allocated_actual) for row in allocations), Decimal("0"))
        unallocated_plan = amount_plan - allocated_plan
        unallocated_actual = amount_actual - allocated_actual
        reconciled = unallocated_plan == Decimal("0.0000") and (
            pool.get("amount_actual") is None or unallocated_actual == Decimal("0.0000")
        )
        if not reconciled and allocations:
            exceptions.append(
                AllocationExceptionItem(
                    exception_type="unreconciled",
                    severity="blocking",
                    message="Allocated total does not reconcile to the shared cost pool amount.",
                    metadata={
                        "unallocated_plan": _money(unallocated_plan),
                        "unallocated_actual": _money(unallocated_actual),
                    },
                )
            )
        pool_item = self._pool_item(
            {
                **pool,
                "metadata": {
                    **(pool.get("metadata") or {}),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                },
            }
        )
        return AllocationPreviewResponse(
            pool=pool_item,
            rule=self._rule_item(rule),
            scenario=scenario,  # type: ignore[arg-type]
            scenario_id=scenario_id,
            candidate_count=len(candidates),
            excluded_count=len(excluded),
            allocations=allocations,
            exceptions=exceptions,
            reconciliation=AllocationReconciliation(
                pool_amount_plan=_money(amount_plan),
                allocated_plan=_money(allocated_plan),
                unallocated_plan=_money(unallocated_plan),
                pool_amount_actual=_money(amount_actual)
                if pool.get("amount_actual") is not None
                else None,
                allocated_actual=_money(allocated_actual)
                if pool.get("amount_actual") is not None
                else None,
                unallocated_actual=_money(unallocated_actual)
                if pool.get("amount_actual") is not None
                else None,
                rounding_adjustment=_money(
                    sum((_dec(row.rounding_adjustment) for row in allocations), Decimal("0"))
                ),
                reconciled=reconciled,
            ),
            reporting_impact={
                "allocated_costs_plan": _money(allocated_plan),
                "allocated_costs_actual": _money(allocated_actual),
                "unallocated_plan": _money(unallocated_plan),
            },
        )

    def _allocation_rows(
        self,
        candidates: list[dict],
        rule: dict,
        basis: dict[str, Decimal],
        amount_plan: Decimal,
        amount_actual: Decimal,
        scenario: str,
        basis_label: str,
        exceptions: list[AllocationExceptionItem],
    ) -> list[SharedCostAllocationItem]:
        if not candidates:
            return []
        method = rule["allocation_method"]
        if method == "manual_amount":
            return self._manual_allocation_rows(
                candidates, rule, amount_plan, amount_actual, scenario
            )
        if method == "fixed_percentage":
            return self._percentage_allocation_rows(
                candidates, rule, amount_plan, amount_actual, scenario, exceptions
            )
        total_basis = sum(basis.values(), Decimal("0"))
        if total_basis == 0:
            behavior = rule.get("missing_basis_behavior") or "fail"
            if behavior == "equal_split":
                basis = {row["id"]: Decimal("1") for row in candidates}
                total_basis = Decimal(len(candidates))
                exceptions.append(
                    AllocationExceptionItem(
                        exception_type="equal_split_fallback",
                        severity="warning",
                        message="No positive allocation basis was found; policy used equal split fallback.",
                    )
                )
            elif behavior == "zero":
                total_basis = Decimal("0")
            else:
                exceptions.append(
                    AllocationExceptionItem(
                        exception_type="missing_basis",
                        severity="blocking",
                        message="No positive allocation basis was found for the selected candidates.",
                    )
                )
                return []
        rows: list[SharedCostAllocationItem] = []
        remaining_plan = amount_plan
        remaining_actual = amount_actual
        for index, initiative in enumerate(candidates):
            initiative_id = initiative["id"]
            value = basis.get(initiative_id, Decimal("0"))
            share = Decimal("0") if total_basis == 0 else value / total_basis
            if index == len(candidates) - 1:
                allocated_plan = remaining_plan
                allocated_actual = remaining_actual
                expected_plan = (amount_plan * share).quantize(Decimal("0.0001"))
                rounding_adjustment = allocated_plan - expected_plan
            else:
                allocated_plan = (amount_plan * share).quantize(Decimal("0.0001"))
                allocated_actual = (amount_actual * share).quantize(Decimal("0.0001"))
                rounding_adjustment = Decimal("0")
                remaining_plan -= allocated_plan
                remaining_actual -= allocated_actual
            rows.append(
                self._allocation_item_from_amounts(
                    initiative,
                    method,
                    value,
                    allocated_plan,
                    allocated_actual,
                    share,
                    rounding_adjustment,
                    basis_label,
                    scenario,
                )
            )
        return rows

    def _manual_allocation_rows(
        self,
        candidates: list[dict],
        rule: dict,
        amount_plan: Decimal,
        amount_actual: Decimal,
        scenario: str,
    ) -> list[SharedCostAllocationItem]:
        manual = self._weight_lookup(rule, "manual_amount")
        rows: list[SharedCostAllocationItem] = []
        for initiative in candidates:
            amount = manual.get(initiative["id"], Decimal("0"))
            share = Decimal("0") if amount_plan == 0 else amount / amount_plan
            actual = (
                (amount_actual * share).quantize(Decimal("0.0001"))
                if amount_actual
                else Decimal("0")
            )
            rows.append(
                self._allocation_item_from_amounts(
                    initiative,
                    "manual_amount",
                    amount,
                    amount,
                    actual,
                    share,
                    Decimal("0"),
                    "Manual amount",
                    scenario,
                )
            )
        return rows

    def _percentage_allocation_rows(
        self,
        candidates: list[dict],
        rule: dict,
        amount_plan: Decimal,
        amount_actual: Decimal,
        scenario: str,
        exceptions: list[AllocationExceptionItem],
    ) -> list[SharedCostAllocationItem]:
        percentages = self._weight_lookup(rule, "percentage")
        total_percentage = sum(percentages.values(), Decimal("0"))
        if total_percentage != Decimal("100.0000"):
            exceptions.append(
                AllocationExceptionItem(
                    exception_type="invalid_percentage_total",
                    severity="blocking",
                    message="Fixed percentage allocations must total 100.0000%.",
                    metadata={"total_percentage": _money(total_percentage)},
                )
            )
            return []
        rows: list[SharedCostAllocationItem] = []
        remaining_plan = amount_plan
        remaining_actual = amount_actual
        for index, initiative in enumerate(candidates):
            pct = percentages.get(initiative["id"], Decimal("0"))
            share = pct / Decimal("100")
            if index == len(candidates) - 1:
                allocated_plan = remaining_plan
                allocated_actual = remaining_actual
                expected = (amount_plan * share).quantize(Decimal("0.0001"))
                rounding_adjustment = allocated_plan - expected
            else:
                allocated_plan = (amount_plan * share).quantize(Decimal("0.0001"))
                allocated_actual = (amount_actual * share).quantize(Decimal("0.0001"))
                rounding_adjustment = Decimal("0")
                remaining_plan -= allocated_plan
                remaining_actual -= allocated_actual
            rows.append(
                self._allocation_item_from_amounts(
                    initiative,
                    "fixed_percentage",
                    pct,
                    allocated_plan,
                    allocated_actual,
                    share,
                    rounding_adjustment,
                    "Fixed percentage",
                    scenario,
                )
            )
        return rows

    def _allocation_item_from_amounts(
        self,
        initiative: dict,
        method: str,
        basis_value: Decimal,
        allocated_plan: Decimal,
        allocated_actual: Decimal,
        share: Decimal,
        rounding_adjustment: Decimal,
        basis_label: str,
        scenario: str,
    ) -> SharedCostAllocationItem:
        return SharedCostAllocationItem(
            id="",
            initiative_id=initiative["id"],
            initiative_name=initiative.get("name"),
            allocation_basis=method,
            basis_value=_money(basis_value),
            allocated_plan=_money(allocated_plan),
            allocated_actual=_money(allocated_actual)
            if scenario == "actual" or allocated_actual != 0
            else None,
            allocation_share=format(share.quantize(Decimal("0.00000001")), "f"),
            rounding_adjustment=_money(rounding_adjustment),
            basis_label=basis_label,
            explanation=(
                f"{initiative.get('initiative_code') or initiative.get('name')} receives "
                f"{format((share * Decimal('100')).quantize(Decimal('0.0001')), 'f')}% "
                f"of the pool using {basis_label}."
            ),
        )

    def _allocation_candidates(
        self, rule: dict
    ) -> tuple[list[dict], list[dict], list[AllocationExceptionItem]]:
        initiatives = self._repo.list_initiatives()
        list_targets = getattr(self._repo, "list_rule_targets", None)
        targets = list_targets(rule["id"]) if list_targets else []
        exceptions: list[AllocationExceptionItem] = []
        if not targets:
            filters = rule.get("filters") or {}
            candidates = [row for row in initiatives if self._matches_filters(row, filters)]
            return candidates, [row for row in initiatives if row not in candidates], exceptions
        include_targets = [row for row in targets if row.get("target_mode") == "include"]
        exclude_targets = [row for row in targets if row.get("target_mode") == "exclude"]
        if not include_targets:
            include_targets = [{"dimension_type": "all", "dimension_value": None}]
        included = [row for row in initiatives if self._matches_any_target(row, include_targets)]
        excluded = [row for row in included if self._matches_any_target(row, exclude_targets)]
        candidates = [row for row in included if row not in excluded]
        if excluded:
            exceptions.append(
                AllocationExceptionItem(
                    exception_type="excluded_candidates",
                    severity="info",
                    message=f"{len(excluded)} initiatives were excluded by policy targets.",
                    metadata={"excluded_count": len(excluded)},
                )
            )
        return candidates, excluded, exceptions

    def _basis_values(
        self,
        candidates: list[dict],
        rule: dict,
        scenario_id: str | None,
        year: int,
    ) -> dict[str, Any]:
        method = rule["allocation_method"]
        exceptions: list[AllocationExceptionItem] = []
        if method == "equal_split":
            return {
                "values": {row["id"]: Decimal("1") for row in candidates},
                "label": "Equal split",
                "exceptions": exceptions,
            }
        if method == "headcount_weighted":
            return {
                "values": self._weight_lookup(rule, "weight_value", default=Decimal("1")),
                "label": "Headcount / FTE weight",
                "exceptions": exceptions,
            }
        if method in {
            "benefit_weighted",
            "revenue_weighted",
            "savings_weighted",
            "metric_weighted",
        }:
            values, label = self._metric_basis_values(candidates, rule, method, scenario_id, year)
            for row in candidates:
                if values.get(row["id"], Decimal("0")) == 0:
                    exceptions.append(
                        AllocationExceptionItem(
                            exception_type="missing_basis_value",
                            severity="warning",
                            initiative_id=row["id"],
                            message=f"{row.get('name')} has no positive basis value for {label}.",
                        )
                    )
            return {"values": values, "label": label, "exceptions": exceptions}
        if method == "direct_cost_weighted":
            values, label = self._cost_basis_values(candidates, rule, year)
            return {"values": values, "label": label, "exceptions": exceptions}
        return {
            "values": {row["id"]: Decimal("1") for row in candidates},
            "label": method.replace("_", " "),
            "exceptions": exceptions,
        }

    def _weight_lookup(
        self,
        rule: dict,
        field: str,
        default: Decimal = Decimal("0"),
    ) -> dict[str, Decimal]:
        candidates = self._repo.list_initiatives()
        values = {row["id"]: default for row in candidates}
        list_weights = getattr(self._repo, "list_rule_weights", None)
        rows = list_weights(rule["id"]) if list_weights else []
        for row in rows:
            initiative_id = row.get("initiative_id")
            if initiative_id:
                values[initiative_id] = _dec(row.get(field))
        legacy = rule.get("weights") or {}
        for initiative_id, value in legacy.items():
            if initiative_id not in values or values[initiative_id] == default:
                values[initiative_id] = _dec(value)
        return values

    def _metric_basis_values(
        self,
        candidates: list[dict],
        rule: dict,
        method: str,
        scenario_id: str | None,
        year: int,
    ) -> tuple[dict[str, Decimal], str]:
        definitions = getattr(self._repo, "list_metric_definitions", lambda: [])()
        definition_by_id = {row["id"]: row for row in definitions}
        selected_definition_id = rule.get("driver_metric_definition_id")
        if not selected_definition_id:
            selected_definition_id = self._default_metric_definition_id(definitions, method)
        selected_definition = definition_by_id.get(selected_definition_id or "")
        selected_ids = (
            {selected_definition_id}
            if selected_definition_id
            else {row["id"] for row in definitions if self._definition_matches_method(row, method)}
        )
        label = (
            selected_definition.get("label") if selected_definition else method.replace("_", " ")
        )
        values = {row["id"]: Decimal("0") for row in candidates}
        candidate_ids = set(values)
        driver_scenario_id = rule.get("driver_scenario_id") or scenario_id
        for row in getattr(self._repo, "list_metric_values", lambda: [])():
            if row.get("initiative_id") not in candidate_ids:
                continue
            if row.get("metric_definition_id") not in selected_ids:
                continue
            if driver_scenario_id and row.get("scenario_id") != driver_scenario_id:
                continue
            if int(row.get("year") or 0) != year:
                continue
            values[row["initiative_id"]] += _dec(row.get("value"))
        if not any(values.values()):
            # Compatibility fallback for tenants not fully migrated to metric values.
            entries = self._repo.list_financial_entries()
            for entry in entries:
                initiative_id = entry.get("initiative_id")
                if initiative_id not in candidate_ids or int(entry.get("year") or 0) != year:
                    continue
                if method == "revenue_weighted":
                    values[initiative_id] += _dec(entry.get("revenue_uplift_base"))
                else:
                    values[initiative_id] += _dec(entry.get("gm_uplift_base"))
        return values, str(label or method.replace("_", " "))

    @staticmethod
    def _default_metric_definition_id(definitions: list[dict], method: str) -> str | None:
        for row in definitions:
            if method == "revenue_weighted" and row.get("benefit_class") == "revenue":
                return row["id"]
            if method == "savings_weighted" and row.get("benefit_class") == "savings":
                return row["id"]
            if method == "benefit_weighted" and row.get("benefit_class") in {
                "margin",
                "savings",
                "avoidance",
                "other",
            }:
                return row["id"]
        return definitions[0]["id"] if method == "metric_weighted" and definitions else None

    @staticmethod
    def _definition_matches_method(row: dict, method: str) -> bool:
        if method == "revenue_weighted":
            return row.get("benefit_class") == "revenue"
        if method == "savings_weighted":
            return row.get("benefit_class") == "savings"
        if method == "benefit_weighted":
            return (
                bool(row.get("is_benefit") or row.get("rollup_type") == "benefit")
                and row.get("benefit_class") != "revenue"
            )
        return method == "metric_weighted"

    def _cost_basis_values(
        self,
        candidates: list[dict],
        rule: dict,
        year: int,
    ) -> tuple[dict[str, Decimal], str]:
        categories = {
            row["id"]: row for row in getattr(self._repo, "list_cost_categories", lambda: [])()
        }
        category_id = rule.get("driver_cost_category_id")
        selected_category = categories.get(category_id or "")
        values = {row["id"]: Decimal("0") for row in candidates}
        candidate_ids = set(values)
        for row in self._repo.list_direct_cost_lines():
            if row.get("initiative_id") not in candidate_ids:
                continue
            if int(row.get("year") or 0) != year:
                continue
            if category_id and row.get("category_id") != category_id:
                continue
            values[row["initiative_id"]] += _dec(row.get("amount_plan"))
        return values, selected_category.get(
            "label", "Direct cost"
        ) if selected_category else "Direct cost"

    def _matches_any_target(self, row: dict, targets: list[dict]) -> bool:
        return any(self._matches_target(row, target) for target in targets)

    @staticmethod
    def _matches_target(row: dict, target: dict) -> bool:
        dimension = target.get("dimension_type")
        value = target.get("dimension_value")
        if dimension == "all":
            return True
        if dimension == "initiative":
            return row.get("id") == value
        if dimension == "business_unit":
            return value in {
                link.get("business_unit_id") for link in row.get("initiative_business_units") or []
            }
        field_by_dimension = {
            "workstream": "workstream_id",
            "tag": "tag",
            "country": "country",
            "stage": "stage",
            "owner": "owner_id",
            "rag_status": "rag_status",
        }
        field = field_by_dimension.get(str(dimension))
        return bool(field and row.get(field) == value)

    def _scenario_id_for(self, scenario: str) -> str | None:
        scenarios = getattr(self._repo, "list_financial_scenarios", lambda: [])()
        kind = (
            "actual"
            if scenario == "actual"
            else "forecast"
            if scenario == "forecast"
            else "baseline"
            if scenario == "baseline"
            else "plan"
        )
        primary = next(
            (
                row["id"]
                for row in scenarios
                if row.get("kind") == kind and (kind != "plan" or row.get("is_primary"))
            ),
            None,
        )
        if primary:
            return str(primary)
        match = next((row["id"] for row in scenarios if row.get("kind") == kind), None)
        return str(match) if match else None

    @staticmethod
    def _period_bounds(pool: dict) -> tuple[date, date]:
        year = int(pool.get("year") or date.today().year)
        if pool.get("month"):
            month = int(pool["month"])
            return date(year, month, 1), date(year, month, monthrange(year, month)[1])
        if pool.get("quarter"):
            start_month = (int(pool["quarter"]) - 1) * 3 + 1
            end_month = start_month + 2
            return date(year, start_month, 1), date(year, end_month, monthrange(year, end_month)[1])
        return date(year, 1, 1), date(year, 12, 31)

    def _require_rule_for_pool(self, pool_id: str, rule_id: str) -> dict:
        rule = self._repo.get_rule(rule_id)
        if not rule or rule.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Allocation rule not found")
        return rule

    def _pool_and_rule(self, pool_id: str, rule_id: str) -> tuple[dict, dict]:
        pool = self._repo.get_pool(pool_id)
        rule = self._repo.get_rule(rule_id)
        if not pool or not rule or rule.get("pool_id") != pool_id:
            raise HTTPException(status_code=404, detail="Pool or allocation rule not found")
        return pool, rule

    @staticmethod
    def _settings_item(row: dict) -> SharedCostReportingSettings:
        return SharedCostReportingSettings(
            include_in_executive_control_tower=bool(
                row.get("include_in_executive_control_tower", True)
            ),
            include_in_dashboard_executive_brief=bool(
                row.get("include_in_dashboard_executive_brief", True)
            ),
            include_in_portfolio_financials=bool(row.get("include_in_portfolio_financials", False)),
            include_in_initiative_financials=bool(
                row.get("include_in_initiative_financials", True)
            ),
            include_in_bankable_plan=bool(row.get("include_in_bankable_plan", False)),
            posting_mode=row.get("posting_mode", "report_only"),
        )

    def _audit(
        self,
        event_type: str,
        current_user: CurrentUser,
        **data: Any,
    ) -> None:
        create = getattr(self._repo, "create_audit_event", None)
        if not create:
            return
        create({"event_type": event_type, "actor_id": str(current_user.id), **data})

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
        allocations = [
            a
            for a in self._repo.list_allocations()
            if a.get("pool_id") == row["id"]
            and (a.get("shared_cost_allocation_runs") or {}).get("status", "completed")
            in {"locked", "posted", "completed"}
        ]
        list_categories = getattr(self._repo, "list_cost_categories", lambda: [])
        categories = {cat["id"]: cat for cat in list_categories()}
        list_scenarios = getattr(self._repo, "list_financial_scenarios", lambda: [])
        scenarios = {scenario["id"]: scenario for scenario in list_scenarios()}
        category = categories.get(row.get("cost_category_id"))
        scenario = scenarios.get(row.get("scenario_id"))
        allocated_plan = sum((_dec(a.get("allocated_plan")) for a in allocations), Decimal("0"))
        allocated_actual = sum((_dec(a.get("allocated_actual")) for a in allocations), Decimal("0"))
        latest_run = next(
            (
                a.get("shared_cost_allocation_runs") or {}
                for a in sorted(allocations, key=lambda item: str(item.get("created_at") or ""))
            ),
            {},
        )
        return SharedCostPoolItem(
            id=row["id"],
            name=row["name"],
            description=row.get("description"),
            category_key=row.get("category_key", "other"),
            cost_category_id=row.get("cost_category_id"),
            category_label=category.get("label") if category else None,
            scenario_id=row.get("scenario_id"),
            scenario_key=scenario.get("key") if scenario else None,
            scenario_label=scenario.get("label") if scenario else None,
            year=row["year"],
            quarter=row.get("quarter"),
            month=row.get("month"),
            amount_plan=_money(row.get("amount_plan")),
            amount_actual=_money(row.get("amount_actual"))
            if row.get("amount_actual") is not None
            else None,
            is_recurring=bool(row.get("is_recurring")),
            status=row.get("status", "draft"),
            period_grain=row.get("period_grain", "annual"),
            reporting_treatment=row.get("reporting_treatment", "report_only"),
            currency_code=row.get("currency_code", "USD"),
            owner_id=row.get("owner_id"),
            locked_at=row.get("locked_at"),
            allocated_plan=_money(allocated_plan),
            allocated_actual=_money(allocated_actual),
            unallocated_plan=_money(_dec(row.get("amount_plan")) - allocated_plan),
            unallocated_actual=_money(_dec(row.get("amount_actual")) - allocated_actual),
            latest_run_status=latest_run.get("status"),
            metadata=row.get("metadata") or {},
            created_at=row.get("created_at"),
        )

    def _rule_item(self, row: dict) -> AllocationRuleItem:
        list_metrics = getattr(self._repo, "list_metric_definitions", lambda: [])
        metrics = {metric["id"]: metric for metric in list_metrics()}
        list_categories = getattr(self._repo, "list_cost_categories", lambda: [])
        categories = {cat["id"]: cat for cat in list_categories()}
        list_scenarios = getattr(self._repo, "list_financial_scenarios", lambda: [])
        scenarios = {scenario["id"]: scenario for scenario in list_scenarios()}
        metric = metrics.get(row.get("driver_metric_definition_id"))
        category = categories.get(row.get("driver_cost_category_id"))
        scenario = scenarios.get(row.get("driver_scenario_id"))
        list_targets = getattr(self._repo, "list_rule_targets", lambda _rule_id: [])
        list_weights = getattr(self._repo, "list_rule_weights", lambda _rule_id: [])
        return AllocationRuleItem(
            id=row["id"],
            pool_id=row["pool_id"],
            name=row["name"],
            allocation_method=row["allocation_method"],
            filters=row.get("filters") or {},
            weights=row.get("weights") or {},
            is_active=bool(row.get("is_active", True)),
            version=int(row.get("version") or 1),
            policy_status=row.get("policy_status", "active"),
            driver_metric_definition_id=row.get("driver_metric_definition_id"),
            driver_metric_label=metric.get("label") if metric else None,
            driver_cost_category_id=row.get("driver_cost_category_id"),
            driver_cost_category_label=category.get("label") if category else None,
            driver_scenario_id=row.get("driver_scenario_id"),
            driver_scenario_label=scenario.get("label") if scenario else None,
            driver_period_mode=row.get("driver_period_mode", "pool_period"),
            missing_basis_behavior=row.get("missing_basis_behavior", "fail"),
            cap_floor_config=row.get("cap_floor_config") or {},
            is_locked=bool(row.get("is_locked", False)),
            targets=[self._target_item(target) for target in list_targets(row["id"])],
            structured_weights=[self._weight_item(weight) for weight in list_weights(row["id"])],
        )

    @staticmethod
    def _run_item(row: dict) -> AllocationRunItem:
        allocation_rows = row.get("shared_cost_allocations") or []
        return AllocationRunItem(
            id=row["id"],
            pool_id=row["pool_id"],
            rule_id=row["rule_id"],
            scenario=row.get("scenario", "plan"),
            scenario_id=row.get("scenario_id"),
            status=row.get("status", "completed"),
            run_type=row.get("run_type", "posting"),
            rule_version=int(row.get("rule_version") or 1),
            total_amount_plan=_money(row.get("total_amount_plan")),
            total_amount_actual=_money(row.get("total_amount_actual"))
            if row.get("total_amount_actual") is not None
            else None,
            period_start=row.get("period_start"),
            period_end=row.get("period_end"),
            reporting_treatment=row.get("reporting_treatment", "report_only"),
            input_snapshot=row.get("input_snapshot") or {},
            exception_summary=row.get("exception_summary") or {},
            approved_by=row.get("approved_by"),
            approved_at=row.get("approved_at"),
            locked_by=row.get("locked_by"),
            locked_at=row.get("locked_at"),
            void_reason=row.get("void_reason"),
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
                    allocation_share=format(_dec(allocation.get("allocation_share")), "f"),
                    rounding_adjustment=_money(allocation.get("rounding_adjustment")),
                    basis_label=allocation.get("basis_label"),
                    explanation=allocation.get("explanation"),
                    exception_flags=allocation.get("exception_flags") or {},
                )
                for allocation in allocation_rows
            ],
        )

    @staticmethod
    def _target_item(row: dict) -> AllocationTargetItem:
        return AllocationTargetItem(
            id=row["id"],
            target_mode=row.get("target_mode", "include"),
            dimension_type=row.get("dimension_type", "all"),
            dimension_value=row.get("dimension_value"),
            label=row.get("label"),
        )

    @staticmethod
    def _weight_item(row: dict) -> AllocationWeightItem:
        return AllocationWeightItem(
            id=row["id"],
            initiative_id=row.get("initiative_id"),
            dimension_type=row.get("dimension_type"),
            dimension_value=row.get("dimension_value"),
            weight_value=_money(row.get("weight_value"))
            if row.get("weight_value") is not None
            else None,
            percentage=_money(row.get("percentage")) if row.get("percentage") is not None else None,
            manual_amount=_money(row.get("manual_amount"))
            if row.get("manual_amount") is not None
            else None,
            label=row.get("label"),
        )

    @staticmethod
    def _period_item(row: dict) -> SharedCostPoolPeriodItem:
        return SharedCostPoolPeriodItem(
            id=row["id"],
            pool_id=row["pool_id"],
            scenario_id=row.get("scenario_id"),
            year=int(row["year"]),
            quarter=row.get("quarter"),
            month=row.get("month"),
            period_start=row["period_start"],
            period_end=row["period_end"],
            amount_plan=_money(row.get("amount_plan")),
            amount_actual=_money(row.get("amount_actual"))
            if row.get("amount_actual") is not None
            else None,
            status=row.get("status", "active"),
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

    @classmethod
    def _rule_payload(cls, data: dict) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        if "structured_weights" in payload:
            payload["structured_weights"] = [
                cls._weight_payload(weight) for weight in payload["structured_weights"]
            ]
        return payload

    @staticmethod
    def _period_payload(data: dict) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        year = int(payload["year"])
        month = payload.get("month")
        quarter = payload.get("quarter")
        if month:
            start = date(year, int(month), 1)
            end = date(year, int(month), monthrange(year, int(month))[1])
        elif quarter:
            start_month = (int(quarter) - 1) * 3 + 1
            end_month = start_month + 2
            start = date(year, start_month, 1)
            end = date(year, end_month, monthrange(year, end_month)[1])
        else:
            start = date(year, 1, 1)
            end = date(year, 12, 31)
        payload["period_start"] = start.isoformat()
        payload["period_end"] = end.isoformat()
        for key in ("amount_plan", "amount_actual"):
            if key in payload:
                payload[key] = _money(payload[key])
        return payload

    @staticmethod
    def _weight_payload(data: dict) -> dict:
        payload = {key: value for key, value in data.items() if value is not None}
        for key in ("weight_value", "percentage", "manual_amount"):
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
        initiative_lookup = {row["id"]: row for row in initiatives}

        def attention_item(initiative_id: str, reason: str) -> dict[str, Any]:
            initiative = initiative_lookup.get(initiative_id) or {}
            return {
                "initiative_id": initiative_id,
                "initiative_code": initiative.get("initiative_code"),
                "initiative_name": initiative.get("name"),
                "reason": reason,
            }

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
                attention.append(attention_item(iid, "Missing actuals"))
            if row.get("realization_status") == "at_risk":
                attention.append(attention_item(iid, "Value realization at risk"))
            if (
                by_init_alloc[iid] > Decimal("0")
                and row.get("benefit_confidence")
                and _dec(row["benefit_confidence"]) < Decimal("50")
            ):
                attention.append(attention_item(iid, "Low confidence with allocated shared cost"))
        for blocked in dependencies.blocked_initiatives:
            attention.append(attention_item(blocked.id, "Blocked by active dependency"))
        return attention

    @staticmethod
    def _allocation_year(row: dict) -> int | None:  # type: ignore[type-arg]
        period_start = (row.get("shared_cost_allocation_runs") or {}).get("period_start")
        if period_start:
            try:
                return int(str(period_start)[:4])
            except ValueError:
                return None
        pool_year = (row.get("shared_cost_pools") or {}).get("year")
        try:
            return int(pool_year) if pool_year is not None else None
        except (TypeError, ValueError):
            return None

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
