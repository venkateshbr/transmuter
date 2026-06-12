from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from app.services.tenant_bootstrap import TenantBootstrapService


class FakeQuery:
    def __init__(self, table_name: str, tables: dict[str, list[dict[str, Any]]]) -> None:
        self.table_name = table_name
        self.tables = tables
        self.filters: list[tuple[str, Any]] = []
        self.payload: dict[str, Any] | None = None
        self.single = False

    def select(self, *_args: str, **_kwargs: Any) -> FakeQuery:
        return self

    def eq(self, column: str, value: Any) -> FakeQuery:
        self.filters.append((column, value))
        return self

    def maybe_single(self) -> FakeQuery:
        self.single = True
        return self

    def update(self, payload: dict[str, Any]) -> FakeQuery:
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        rows = self.tables.setdefault(self.table_name, [])
        matched = [
            row
            for row in rows
            if all(str(row.get(column)) == str(value) for column, value in self.filters)
        ]
        if self.payload is not None:
            for row in matched:
                row.update(self.payload)
            return SimpleNamespace(data=matched)
        return SimpleNamespace(data=(matched[0] if self.single and matched else matched))


class FakeClient:
    def __init__(self) -> None:
        self.tables: dict[str, list[dict[str, Any]]] = {
            "organizations": [{"id": "tenant-1", "settings": {}}],
        }
        self.touched_tables: list[str] = []

    def table(self, name: str) -> FakeQuery:
        self.touched_tables.append(name)
        return FakeQuery(name, self.tables)


def test_tenant_bootstrap_does_not_seed_business_configuration() -> None:
    client = FakeClient()

    result = TenantBootstrapService(client).bootstrap_tenant("tenant-1")

    assert result == {
        "settings": 1,
        "financial_groups": 0,
        "financial_items": 0,
        "gate_criteria": 0,
        "stage_gate_definitions": 0,
    }
    assert "financial_config_groups" not in client.touched_tables
    assert "financial_config_items" not in client.touched_tables
    assert "gate_criteria" not in client.touched_tables
    assert "stage_gate_definitions" not in client.touched_tables
