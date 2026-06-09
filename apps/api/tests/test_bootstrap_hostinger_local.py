from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from scripts import bootstrap_hostinger_local as bootstrap_script


class FakeAuthAdmin:
    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}

    def list_users(self, page: int, per_page: int) -> list[SimpleNamespace]:
        assert page >= 1
        assert per_page > 0
        return [
            SimpleNamespace(id=user["id"], email=email)
            for email, user in sorted(self.users.items())
        ]

    def create_user(self, payload: dict[str, Any]) -> SimpleNamespace:
        user_id = f"auth-{len(self.users) + 1}"
        self.users[payload["email"].lower()] = {"id": user_id, **payload}
        return SimpleNamespace(user=SimpleNamespace(id=user_id))

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> None:
        for email, user in self.users.items():
            if user["id"] == user_id:
                self.users[email] = {**user, **payload}
                return
        raise AssertionError(f"missing auth user {user_id}")


class FakeClient:
    def __init__(self) -> None:
        self.auth = SimpleNamespace(admin=FakeAuthAdmin())
        self.tables: dict[str, list[dict[str, Any]]] = {}

    def table(self, name: str) -> FakeTableQuery:
        return FakeTableQuery(self, name)


class FakeTableQuery:
    def __init__(self, client: FakeClient, table: str) -> None:
        self.client = client
        self.table = table
        self.filters: list[tuple[str, Any]] = []
        self.payload: dict[str, Any] | None = None
        self.mode = "select"

    def select(self, _columns: str) -> FakeTableQuery:
        self.mode = "select"
        return self

    def eq(self, column: str, value: Any) -> FakeTableQuery:
        self.filters.append((column, value))
        return self

    def maybe_single(self) -> FakeTableQuery:
        return self

    def insert(self, payload: dict[str, Any]) -> FakeTableQuery:
        self.mode = "insert"
        self.payload = payload
        return self

    def update(self, payload: dict[str, Any]) -> FakeTableQuery:
        self.mode = "update"
        self.payload = payload
        return self

    def execute(self) -> SimpleNamespace:
        rows = self.client.tables.setdefault(self.table, [])
        if self.mode == "insert":
            assert self.payload is not None
            row = {"id": self.payload.get("id") or f"{self.table}-{len(rows) + 1}", **self.payload}
            rows.append(row)
            return SimpleNamespace(data=[row])
        if self.mode == "update":
            assert self.payload is not None
            matched = self._matched_rows(rows)
            for row in matched:
                row.update(self.payload)
            return SimpleNamespace(data=matched)
        matched = self._matched_rows(rows)
        return SimpleNamespace(data=matched[0] if matched else None)

    def _matched_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if all(row.get(column) == value for column, value in self.filters)
        ]


class FakeTenantBootstrapService:
    def __init__(self, _client: FakeClient) -> None:
        pass

    def bootstrap_tenant(self, _tenant_id: str) -> dict[str, int]:
        return {"settings": 1, "financial_groups": 10, "financial_items": 18, "gate_criteria": 8}


def test_hostinger_bootstrap_seeds_only_admin_shell_and_master_config(
    monkeypatch,
) -> None:
    client = FakeClient()
    config = bootstrap_script.BootstrapConfig(
        tenant_name="Transmuter Platform Admin",
        tenant_slug="transmuter-admin",
        tenant_admin_email="admin@example.com",
        tenant_admin_name="Tenant Admin",
        tenant_admin_password="Password2026!",
        platform_admin_email="operator@example.com",
        platform_admin_password="Password2026!",
        planned_user_count=1,
    )
    monkeypatch.setattr(bootstrap_script, "TenantBootstrapService", FakeTenantBootstrapService)

    result = bootstrap_script.bootstrap(client, config)

    assert result["tenant_slug"] == "transmuter-admin"
    assert result["subscription_plan_count"] == 5
    assert len(client.auth.admin.users) == 2
    assert client.auth.admin.users["operator@example.com"]["app_metadata"]["platform_admin"] is True
    assert len(client.tables["organizations"]) == 1
    assert len(client.tables["users"]) == 1
    assert len(client.tables["subscription_plans"]) == 5
    assert len(client.tables["tenant_subscriptions"]) == 1
    assert "initiatives" not in client.tables
    assert "meetings" not in client.tables
    assert "financial_entries" not in client.tables
    assert "financial_cost_lines" not in client.tables
