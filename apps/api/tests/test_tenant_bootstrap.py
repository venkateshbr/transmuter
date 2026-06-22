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
        self._payload: object = None

    def select(self, *_args: str) -> _Query:
        self._operation = "select"
        return self

    def update(self, payload: dict[str, object]) -> _Query:
        self._operation = "update"
        self._payload = payload
        return self

    def insert(self, payload: object) -> _Query:
        self._operation = "insert"
        self._payload = payload
        return self

    def eq(self, *_args: object) -> _Query:
        return self

    def maybe_single(self) -> _Query:
        return self

    def execute(self) -> _Result:
        self._client.executed.append((self._table_name, self._operation))
        if self._table_name == "organizations" and self._operation == "select":
            return _Result({"id": "tenant-1", "settings": {}})
        if self._operation == "select":
            return _Result(self._client.rows.get(self._table_name, []))
        if self._operation == "insert":
            payload_rows = self._payload if isinstance(self._payload, list) else [self._payload]
            self._client.rows.setdefault(self._table_name, []).extend(payload_rows)
            return _Result(payload_rows)
        return _Result()


class _Client:
    def __init__(self) -> None:
        self.touched_tables: list[str] = []
        self.executed: list[tuple[str, str]] = []
        self.rows: dict[str, list[object]] = {}

    def table(self, table_name: str) -> _Query:
        self.touched_tables.append(table_name)
        return _Query(self, table_name)


def test_tenant_bootstrap_creates_financial_and_dashboard_defaults_only() -> None:
    client = _Client()

    result = TenantBootstrapService(client).bootstrap_tenant("tenant-1")  # type: ignore[arg-type]

    assert result["settings"] == 1
    assert result["financial_scenarios"] == 4
    assert result["financial_metric_definitions"] == 10
    assert result["financial_cost_categories"] == 8
    assert result["financial_bridge_rows"] == 6
    assert result["dashboards"] == 10
    assert result["gate_criteria"] == 0
    assert result["stage_gate_definitions"] == 0
    assert "business_units" not in client.touched_tables
    assert "workstreams" not in client.touched_tables
    dashboards = client.rows["tenant_dashboard_config"]
    enabled = {row["dashboard_key"] for row in dashboards if row["is_enabled"]}  # type: ignore[index]
    assert enabled == {
        "executive_dashboard",
        "financial_overview",
        "initiative_portfolio",
    }
