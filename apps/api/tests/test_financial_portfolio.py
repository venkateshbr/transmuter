from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.domain.financials import (
    CostLineCreate,
    CostLineUpdate,
    FinancialCellAssumptionUpdate,
    FinancialConfigGroup,
    FinancialConfigItem,
    FinancialConfigurationResponse,
)
from app.services.financial import FinancialService


def _config() -> FinancialConfigurationResponse:
    return FinancialConfigurationResponse(
        groups=[
            FinancialConfigGroup(
                id="g1",
                key="gross_margin",
                label="Gross Margin",
                kind="metric",
                display_order=1,
                is_system=True,
            ),
            FinancialConfigGroup(
                id="g2",
                key="operating",
                label="Operating Costs",
                kind="cost_category",
                display_order=2,
                is_system=True,
            ),
        ],
        items=[
            FinancialConfigItem(
                id="m1",
                group_id="g1",
                group_key="gross_margin",
                key="gm_uplift_base",
                label="GM Uplift (Base)",
                item_type="metric",
                system_metric_key="gm_uplift_base",
                display_order=1,
                is_system=True,
            ),
            FinancialConfigItem(
                id="c1",
                group_id="g2",
                group_key="operating",
                key="software",
                label="Software",
                item_type="cost_category",
                rollup_type="recurring_cost",
                display_order=1,
                is_system=True,
            ),
        ],
    )


def test_portfolio_financials_keeps_broader_periods_separate_for_monthly_view() -> None:
    response = FinancialService._compute_portfolio_financials(
        entries=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 1,
                "quarter": None,
                "gm_uplift_base": "1000.0000",
                "gm_uplift_actual": "900.0000",
                "revenue_uplift_base": "1500.0000",
                "cogs_base": "500.0000",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": None,
                "quarter": 1,
                "gm_uplift_base": "3000.0000",
                "gm_uplift_actual": "2500.0000",
                "revenue_uplift_base": "4500.0000",
                "cogs_base": "1500.0000",
            },
        ],
        cost_lines=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 1,
                "quarter": None,
                "amount_plan": "100.0000",
                "amount_actual": "90.0000",
                "is_recurring": True,
                "category_key": "software",
            },
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": None,
                "quarter": 1,
                "amount_plan": "300.0000",
                "amount_actual": "275.0000",
                "is_recurring": True,
                "category_key": "software",
            },
        ],
        config=_config(),
        granularity="monthly",
    )

    assert response.periods[0].period == "2026-M01"
    assert response.periods[0].benefits_plan == "1000.0000"
    assert response.periods[0].recurring_costs_actual == "90.0000"
    assert response.broader_period_totals[0].period == "2026-Q1"
    assert response.broader_period_totals[0].benefits_plan == "3000.0000"
    assert response.broader_period_totals[0].recurring_costs_actual == "275.0000"
    assert response.summary[0].plan == "4000.0000"
    assert response.summary[1].actual == "365.0000"


def test_portfolio_contributors_group_period_values_by_initiative() -> None:
    response = FinancialService._compute_portfolio_contributors(
        entries=[
            {
                "tenant_id": "t1",
                "initiative_id": "i1",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "gm_uplift_base": "60000.0000",
                "gm_uplift_actual": "45000.0000",
            }
        ],
        cost_lines=[
            {
                "id": "cl1",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "name": "Implementation partner",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "amount_plan": "180000.0000",
                "amount_actual": "125000.0000",
                "is_recurring": False,
                "category_key": "software",
            },
            {
                "id": "cl2",
                "tenant_id": "t1",
                "initiative_id": "i1",
                "name": "Platform subscription",
                "year": 2026,
                "month": 6,
                "quarter": None,
                "amount_plan": "10000.0000",
                "amount_actual": "9500.0000",
                "is_recurring": True,
                "category_key": "software",
            },
        ],
        initiatives={"i1": {"id": "i1", "name": "ERP modernization"}},
        config=_config(),
        granularity="monthly",
        period="2026-M06",
        period_key=("2026-M06", 2026, None, 6),
    )

    assert response.period == "2026-M06"
    assert len(response.contributors) == 1
    contributor = response.contributors[0]
    assert contributor.initiative_name == "ERP modernization"
    assert contributor.benefits_plan == "60000.0000"
    assert contributor.one_off_costs_actual == "125000.0000"
    assert contributor.recurring_costs_plan == "10000.0000"
    assert contributor.total_costs_plan == "190000.0000"
    assert contributor.net_value_plan == "-130000.0000"
    assert contributor.cost_lines[0].category_label == "Software"


class _ConfigRepo:
    def __init__(self) -> None:
        self.groups = {
            "kept": {
                "id": "g1",
                "key": "kept",
                "label": "Kept",
                "kind": "cost_category",
                "display_order": 1,
                "is_system": False,
                "is_active": True,
            },
            "omitted": {
                "id": "g2",
                "key": "omitted",
                "label": "Omitted",
                "kind": "cost_category",
                "display_order": 2,
                "is_system": False,
                "is_active": True,
            },
        }
        self.items = {
            "kept_item": {
                "id": "i1",
                "group_id": "g1",
                "key": "kept_item",
                "label": "Kept item",
                "item_type": "cost_category",
                "display_order": 1,
                "is_system": False,
                "is_active": True,
            },
            "omitted_item": {
                "id": "i2",
                "group_id": "g2",
                "key": "omitted_item",
                "label": "Omitted item",
                "item_type": "cost_category",
                "display_order": 2,
                "is_system": False,
                "is_active": True,
            },
        }

    def list_config_groups(self) -> list[dict]:
        return list(self.groups.values())

    def list_config_items(self) -> list[dict]:
        return list(self.items.values())

    def upsert_config_group(self, data: dict) -> dict:
        current = self.groups.get(data["key"], {"id": f"g{len(self.groups) + 1}"})
        current.update(data)
        self.groups[data["key"]] = current
        return current

    def upsert_config_item(self, data: dict) -> dict:
        current = self.items.get(data["key"], {"id": f"i{len(self.items) + 1}"})
        current.update(data)
        self.items[data["key"]] = current
        return current

    def deactivate_config_groups_except(self, active_keys: set[str]) -> None:
        for key, group in self.groups.items():
            if key not in active_keys:
                group["is_active"] = False

    def deactivate_config_items_except(self, active_keys: set[str]) -> None:
        for key, item in self.items.items():
            if key not in active_keys:
                item["is_active"] = False


def test_update_configuration_deactivates_omitted_groups_and_items() -> None:
    repo = _ConfigRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    response = service.update_configuration(
        FinancialConfigurationResponse(
            groups=[
                FinancialConfigGroup(
                    id="g1",
                    key="kept",
                    label="Kept",
                    kind="cost_category",
                    display_order=1,
                    is_active=True,
                )
            ],
            items=[
                FinancialConfigItem(
                    id="i1",
                    group_id="g1",
                    group_key="kept",
                    key="kept_item",
                    label="Kept item",
                    item_type="cost_category",
                    display_order=1,
                    is_active=True,
                )
            ],
        )
    )

    groups = {group.key: group for group in response.groups}
    items = {item.key: item for item in response.items}
    assert groups["kept"].is_active is True
    assert groups["omitted"].is_active is False
    assert items["kept_item"].is_active is True
    assert items["omitted_item"].is_active is False


def test_update_configuration_rejects_cross_tenant_group_id() -> None:
    repo = _ConfigRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    with pytest.raises(HTTPException) as exc:
        service.update_configuration(
            FinancialConfigurationResponse(
                groups=[
                    FinancialConfigGroup(
                        id="g1",
                        key="kept",
                        label="Kept",
                        kind="cost_category",
                        display_order=1,
                        is_active=True,
                    )
                ],
                items=[
                    FinancialConfigItem(
                        group_id="foreign-group-id",
                        group_key="kept",
                        key="foreign_item",
                        label="Foreign item",
                        item_type="cost_category",
                        display_order=1,
                        is_active=True,
                    )
                ],
            )
        )

    assert exc.value.status_code == 400


class _MissingInitiativeRepo:
    def initiative_exists(self, initiative_id: str) -> bool:
        return False


def test_create_cost_line_rejects_missing_tenant_initiative() -> None:
    service = FinancialService.__new__(FinancialService)
    service._repo = _MissingInitiativeRepo()

    with pytest.raises(HTTPException) as exc:
        service.create_cost_line(
            "foreign-initiative-id",
            CostLineCreate(
                name="Cross tenant attempt",
                year=2026,
                amount_plan="1.0000",
                is_recurring=False,
            ),
        )

    assert exc.value.status_code == 404


class _InitiativeBoundMutationRepo:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def initiative_exists(self, initiative_id: str) -> bool:
        return initiative_id == "initiative-1"

    def update_cost_line(self, initiative_id: str, cost_line_id: str, data: dict) -> dict:
        self.calls.append(("update_cost_line", initiative_id, cost_line_id))
        return {
            "id": cost_line_id,
            "initiative_id": initiative_id,
            "name": data.get("name", "Updated cost"),
            "category_key": "other",
            "year": 2026,
            "quarter": None,
            "month": None,
            "amount_plan": "1.0000",
            "amount_actual": None,
            "is_recurring": False,
        }

    def delete_cost_line(self, initiative_id: str, cost_line_id: str) -> None:
        self.calls.append(("delete_cost_line", initiative_id, cost_line_id))

    def update_cell_assumption(
        self,
        initiative_id: str,
        assumption_id: str,
        comment: str,
        user_id: str,
    ) -> dict:
        self.calls.append(("update_cell_assumption", initiative_id, assumption_id))
        return {
            "id": assumption_id,
            "initiative_id": initiative_id,
            "row_key": "gm_uplift_base",
            "column_key": "col_2026_q1",
            "comment": comment,
            "updated_by": user_id,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    def delete_cell_assumption(self, initiative_id: str, assumption_id: str) -> None:
        self.calls.append(("delete_cell_assumption", initiative_id, assumption_id))


def test_nested_financial_mutations_bind_rows_to_url_initiative() -> None:
    repo = _InitiativeBoundMutationRepo()
    service = FinancialService.__new__(FinancialService)
    service._repo = repo

    service.update_cost_line("initiative-1", "cost-1", CostLineUpdate(name="Updated cost"))
    service.delete_cost_line("initiative-1", "cost-1")
    service.update_cell_assumption(
        "initiative-1",
        "assumption-1",
        FinancialCellAssumptionUpdate(comment="Updated"),
        "user-1",
    )
    service.delete_cell_assumption("initiative-1", "assumption-1")

    assert repo.calls == [
        ("update_cost_line", "initiative-1", "cost-1"),
        ("delete_cost_line", "initiative-1", "cost-1"),
        ("update_cell_assumption", "initiative-1", "assumption-1"),
        ("delete_cell_assumption", "initiative-1", "assumption-1"),
    ]
