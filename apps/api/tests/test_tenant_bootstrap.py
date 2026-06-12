from __future__ import annotations

from app.services.tenant_bootstrap import TenantBootstrapService


class _Result:
    def __init__(self, data: object = None) -> None:
        self.data = data


class _Query:
    def __init__(self, client: _Client, table_name: str) -> None:
        self._client = client
        self._table_name = table_name
        self._operation = "select"

    def select(self, *_args: str) -> _Query:
        self._operation = "select"
        return self

    def update(self, _payload: dict[str, object]) -> _Query:
        self._operation = "update"
        return self

    def eq(self, *_args: object) -> _Query:
        return self

    def maybe_single(self) -> _Query:
        return self

    def execute(self) -> _Result:
        self._client.executed.append((self._table_name, self._operation))
        if self._table_name == "organizations" and self._operation == "select":
            return _Result({"id": "tenant-1", "settings": {}})
        return _Result()


class _Client:
    def __init__(self) -> None:
        self.touched_tables: list[str] = []
        self.executed: list[tuple[str, str]] = []

    def table(self, table_name: str) -> _Query:
        self.touched_tables.append(table_name)
        return _Query(self, table_name)


def test_tenant_bootstrap_creates_only_blank_tenant_shell_settings() -> None:
    client = _Client()

    result = TenantBootstrapService(client).bootstrap_tenant("tenant-1")  # type: ignore[arg-type]

    assert result == {
        "settings": 1,
        "financial_groups": 0,
        "financial_items": 0,
        "gate_criteria": 0,
        "stage_gate_definitions": 0,
    }
    assert set(client.touched_tables) == {"organizations"}
    assert client.executed == [
        ("organizations", "select"),
        ("organizations", "update"),
    ]
