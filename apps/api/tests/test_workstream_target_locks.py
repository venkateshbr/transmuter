from __future__ import annotations

from datetime import date
from typing import Any, cast
from uuid import UUID

from app.domain.financials import (
    FinancialEntryUpdate,
    FinancialForecastUpdate,
    FinancialGridUpdate,
    WorkstreamTargetLockRequest,
)
from app.services.financial import FinancialService

TENANT_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = "22222222-2222-2222-2222-222222222222"
WORKSTREAM_ID = "33333333-3333-3333-3333-333333333333"
APPROVED_INITIATIVE_ID = "44444444-4444-4444-4444-444444444444"
PENDING_INITIATIVE_ID = "55555555-5555-5555-5555-555555555555"


class FakeTargetRepo:
    def __init__(self) -> None:
        self.settings: dict[str, object] = {
            "bankable_plan_governance": {
                "initiative_plan_lock_gate_number": 2,
                "locked_value_basis": "net_run_rate",
            }
        }
        self.target_locks: list[dict[str, object]] = []
        self.forecasts: list[dict[str, object]] = []
        self.saved_entries: list[dict[str, object]] = []
        self.entries = [
            {
                "id": "entry-1",
                "initiative_id": APPROVED_INITIATIVE_ID,
                "year": 2026,
                "quarter": 1,
                "month": None,
                "revenue_uplift_base": "100.0000",
                "revenue_uplift_high": "150.0000",
                "revenue_uplift_actual": None,
                "revenue_uplift_pct_base": "0.0000",
                "revenue_uplift_pct_high": "0.0000",
                "revenue_uplift_pct_actual": None,
                "gross_margin_base": "0.0000",
                "gross_margin_high": "0.0000",
                "gross_margin_actual": None,
                "gm_pct_base": "0.0000",
                "gm_pct_high": "0.0000",
                "gm_pct_actual": None,
                "gm_uplift_base": "100.0000",
                "gm_uplift_high": "150.0000",
                "gm_uplift_actual": None,
                "gm_uplift_pct_base": "0.0000",
                "gm_uplift_pct_high": "0.0000",
                "gm_uplift_pct_actual": None,
                "cogs_base": "0.0000",
                "cogs_high": "0.0000",
                "cogs_actual": None,
                "cogs_pct_base": "0.0000",
                "cogs_pct_high": "0.0000",
                "cogs_pct_actual": None,
            }
        ]

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id in {APPROVED_INITIATIVE_ID, PENDING_INITIATIVE_ID}

    def get_initiative_period(self, initiative_id: str) -> dict[str, object] | None:
        if not self.initiative_exists(initiative_id):
            return None
        return {
            "id": initiative_id,
            "stage": "in_progress",
            "planned_start": "2026-01-01",
            "planned_end": "2026-12-31",
        }

    def get_organization_settings(self) -> dict[str, object]:
        return self.settings

    def update_organization_settings(self, settings: dict[str, object]) -> dict[str, object]:
        self.settings = settings
        return {"settings": settings}

    def list_workstreams(self) -> list[dict[str, object]]:
        return [{"id": WORKSTREAM_ID, "name": "Operations"}]

    def list_workstream_initiatives(self, workstream_id: str) -> list[dict[str, object]]:
        assert workstream_id == WORKSTREAM_ID
        return [
            {
                "id": APPROVED_INITIATIVE_ID,
                "initiative_code": "TRN-001",
                "name": "Approved Initiative",
                "stage": "in_progress",
                "workstream_id": WORKSTREAM_ID,
            },
            {
                "id": PENDING_INITIATIVE_ID,
                "initiative_code": "TRN-002",
                "name": "Pending Initiative",
                "stage": "scoping",
                "workstream_id": WORKSTREAM_ID,
            },
        ]

    def list_approved_gate_submissions(
        self,
        initiative_ids: list[str],
        gate_number: int,
        cutoff_date: date,
    ) -> list[dict[str, object]]:
        assert gate_number == 2
        assert cutoff_date == date(2026, 6, 30)
        assert APPROVED_INITIATIVE_ID in initiative_ids
        return [
            {
                "initiative_id": APPROVED_INITIATIVE_ID,
                "gate_number": 2,
                "decision": "approved",
                "decided_at": "2026-06-15T00:00:00+00:00",
            }
        ]

    def get_latest_bankable_plan(self, initiative_id: str) -> dict[str, object] | None:
        if initiative_id != APPROVED_INITIATIVE_ID:
            return None
        return {
            "id": "plan-1",
            "initiative_id": APPROVED_INITIATIVE_ID,
            "version": 1,
            "trigger_type": "approval",
            "trigger_submission_id": "submission-1",
            "locked_by_id": USER_ID,
            "locked_at": "2026-06-15T00:00:00+00:00",
            "locked_reason": "Approved",
            "snapshot": {
                "summary": {
                    "net_value_plan": "125.0000",
                    "net_value_actual": "90.0000",
                }
            },
        }

    def list_bankable_plans(self, initiative_id: str) -> list[dict[str, object]]:
        latest = self.get_latest_bankable_plan(initiative_id)
        return [latest] if latest else []

    def list_workstream_target_locks(self, workstream_id: str) -> list[dict[str, object]]:
        return [row for row in self.target_locks if row["workstream_id"] == workstream_id]

    def get_latest_workstream_target_lock(self, workstream_id: str) -> dict[str, object] | None:
        rows = self.list_workstream_target_locks(workstream_id)
        return rows[-1] if rows else None

    def create_workstream_target_lock(self, data: dict[str, object]) -> dict[str, object]:
        row = {"id": f"target-{len(self.target_locks) + 1}", **data}
        self.target_locks.append(row)
        return row

    def get_entries(self, initiative_id: str) -> list[dict[str, object]]:
        return [row for row in self.entries if row["initiative_id"] == initiative_id]

    def list_cost_lines(self, _initiative_id: str) -> list[dict[str, object]]:
        return []

    def list_metric_values(self, _initiative_id: str) -> list[dict[str, object]]:
        return []

    def list_financial_selections(self, _initiative_id: str) -> list[dict[str, object]]:
        return []

    def list_config_groups(self) -> list[dict[str, object]]:
        return []

    def list_config_items(self) -> list[dict[str, object]]:
        return []

    def upsert_entries_batch(
        self,
        _initiative_id: str,
        rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        self.saved_entries = rows
        return rows

    def upsert_forecasts_batch(
        self,
        initiative_id: str,
        rows: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        saved = [
            {
                "id": f"forecast-{len(self.forecasts) + idx + 1}",
                "initiative_id": initiative_id,
                **row,
            }
            for idx, row in enumerate(rows)
        ]
        self.forecasts.extend(saved)
        return saved

    def list_forecasts(self, initiative_id: str) -> list[dict[str, object]]:
        return [row for row in self.forecasts if row["initiative_id"] == initiative_id]


def service(repo: FakeTargetRepo) -> FinancialService:
    financial_service = cast(Any, FinancialService.__new__(FinancialService))
    financial_service._repo = repo
    financial_service._tenant_id = TENANT_ID
    return financial_service


def test_workstream_target_preview_and_lock_use_configured_gate_and_net_run_rate() -> None:
    repo = FakeTargetRepo()
    financial_service = service(repo)

    preview = financial_service.get_workstream_target_preview(WORKSTREAM_ID, date(2026, 6, 30))

    assert preview.settings.initiative_plan_lock_gate_number == 2
    assert preview.settings.locked_value_basis == "net_run_rate"
    assert [item.initiative_id for item in preview.included] == [APPROVED_INITIATIVE_ID]
    assert [item.initiative_id for item in preview.excluded] == [PENDING_INITIATIVE_ID]
    assert preview.locked_run_rate_value == "125.0000"
    assert preview.actual_total == "90.0000"
    assert preview.variance == "-35.0000"

    locked = financial_service.lock_workstream_target(
        WORKSTREAM_ID,
        WorkstreamTargetLockRequest(lock_date=date(2026, 6, 30)),
        USER_ID,
    )

    assert locked.version == 1
    assert locked.locked_value_basis == "net_run_rate"
    assert locked.included_initiative_ids == [APPROVED_INITIATIVE_ID]
    assert locked.snapshot.locked_run_rate_value == "125.0000"


def test_locked_financial_grid_preserves_plan_fields_and_allows_actuals() -> None:
    repo = FakeTargetRepo()
    financial_service = service(repo)

    result = financial_service.update_financial_grid(
        APPROVED_INITIATIVE_ID,
        FinancialGridUpdate(
            entries=[
                FinancialEntryUpdate(
                    year=2026,
                    quarter=1,
                    revenue_uplift_base="999.0000",
                    revenue_uplift_high="999.0000",
                    revenue_uplift_actual="80.0000",
                    gm_uplift_base="999.0000",
                    gm_uplift_high="999.0000",
                    gm_uplift_actual="80.0000",
                )
            ]
        ),
    )

    assert result.locked is True
    assert repo.saved_entries[0]["revenue_uplift_base"] == "100.0000"
    assert repo.saved_entries[0]["revenue_uplift_high"] == "150.0000"
    assert repo.saved_entries[0]["revenue_uplift_actual"] == "80.0000"


def test_forecasts_are_separate_post_lock_outlook_rows() -> None:
    repo = FakeTargetRepo()
    financial_service = service(repo)

    response = financial_service.update_forecasts(
        APPROVED_INITIATIVE_ID,
        [
            FinancialForecastUpdate(
                line_type="metric",
                line_key="net_run_rate",
                year=2026,
                quarter=1,
                amount_forecast="140.0000",
                notes="Updated outlook after approval.",
            )
        ],
    )

    assert len(response.items) == 1
    assert response.items[0].amount_forecast == "140.0000"
    assert response.items[0].notes == "Updated outlook after approval."
