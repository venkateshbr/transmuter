from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services.initiative import InitiativeService


class FakeQuery:
    def __init__(self, table_name: str, counts: dict[str, int]) -> None:
        self.table_name = table_name
        self.counts = counts

    def select(self, *_args: str, **_kwargs: object) -> FakeQuery:
        return self

    def eq(self, *_args: object, **_kwargs: object) -> FakeQuery:
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(count=self.counts.get(self.table_name, 0), data=[])


class FakeClient:
    def __init__(self, counts: dict[str, int]) -> None:
        self.counts = counts

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(name, self.counts)


def test_create_initiative_requires_tenant_setup() -> None:
    client = FakeClient(
        {
            "business_units": 1,
            "workstreams": 1,
            "financial_metric_definitions": 1,
            "financial_scenarios": 1,
            "financial_cost_categories": 1,
            "stage_gate_definitions": 1,
            "gate_criteria": 1,
        }
    )
    service = InitiativeService(client, UUID("00000000-0000-0000-0000-000000000001"))

    service._assert_tenant_ready_for_creation()


def test_create_initiative_blocks_when_setup_is_missing() -> None:
    client = FakeClient(
        {
            "business_units": 1,
            "workstreams": 0,
            "financial_metric_definitions": 0,
            "financial_scenarios": 0,
            "financial_cost_categories": 0,
            "stage_gate_definitions": 1,
            "gate_criteria": 0,
        }
    )
    service = InitiativeService(client, UUID("00000000-0000-0000-0000-000000000001"))

    with pytest.raises(HTTPException) as exc:
        service._assert_tenant_ready_for_creation()

    assert exc.value.status_code == 400
    assert "workstreams" in str(exc.value.detail)
    assert "financial cost categories" in str(exc.value.detail)
    assert "gate criteria" in str(exc.value.detail)
