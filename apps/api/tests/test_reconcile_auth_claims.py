from __future__ import annotations

import json
from copy import deepcopy
from io import StringIO
from types import SimpleNamespace
from typing import Any

import pytest

from app.cli.reconcile_auth_claims import main, reconcile_auth_claims
from app.core.auth_metadata import authorization_metadata_key

PUBLIC_KEY = authorization_metadata_key("public")
DEV_KEY = authorization_metadata_key("transmuter_dev")
PROD_KEY = authorization_metadata_key("transmuter")


def _auth_user(
    user_id: str,
    *,
    email: str,
    app_metadata: dict[str, Any] | None = None,
    user_metadata: dict[str, Any] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        email=email,
        app_metadata=deepcopy(app_metadata or {}),
        user_metadata=deepcopy(user_metadata or {}),
    )


class FakeUsersQuery:
    def __init__(
        self,
        rows: list[dict[str, Any]],
        range_calls: list[tuple[int, int]],
    ) -> None:
        self._rows = rows
        self._range_calls = range_calls
        self._start = 0
        self._end = len(rows) - 1

    def select(self, columns: str) -> FakeUsersQuery:
        assert columns == "id, tenant_id, role"
        return self

    def order(self, column: str) -> FakeUsersQuery:
        assert column == "id"
        return self

    def range(self, start: int, end: int) -> FakeUsersQuery:
        self._range_calls.append((start, end))
        self._start = start
        self._end = end
        return self

    def execute(self) -> SimpleNamespace:
        return SimpleNamespace(data=deepcopy(self._rows[self._start : self._end + 1]))


class FakeAuthAdmin:
    def __init__(self, users: list[SimpleNamespace]) -> None:
        self.users = {str(user.id): deepcopy(user) for user in users}
        self.list_calls: list[tuple[int, int]] = []
        self.update_calls: list[tuple[str, dict[str, Any]]] = []
        self.get_calls: list[str] = []
        self.update_error: Exception | None = None
        self.refetch_error: Exception | None = None
        self.retain_deleted_user_claims = False

    def list_users(self, *, page: int, per_page: int) -> list[SimpleNamespace]:
        self.list_calls.append((page, per_page))
        users = [self.users[key] for key in sorted(self.users)]
        start = (page - 1) * per_page
        return deepcopy(users[start : start + per_page])

    def update_user_by_id(self, user_id: str, payload: dict[str, Any]) -> SimpleNamespace:
        self.update_calls.append((user_id, deepcopy(payload)))
        if self.update_error is not None:
            raise self.update_error
        user = self.users[user_id]
        for key, value in payload.get("app_metadata", {}).items():
            if value is None:
                user.app_metadata.pop(key, None)
            else:
                user.app_metadata[key] = deepcopy(value)
        for key, value in payload.get("user_metadata", {}).items():
            if value is None:
                user.user_metadata.pop(key, None)
            else:
                user.user_metadata[key] = deepcopy(value)
        if self.retain_deleted_user_claims:
            user.user_metadata["tenant_id"] = "residual-tenant"
        return SimpleNamespace(user=deepcopy(user))

    def get_user_by_id(self, user_id: str) -> SimpleNamespace:
        self.get_calls.append(user_id)
        if self.refetch_error is not None:
            raise self.refetch_error
        return SimpleNamespace(user=deepcopy(self.users[user_id]))


class FakeClient:
    def __init__(
        self, platform_rows: list[dict[str, Any]], auth_users: list[SimpleNamespace]
    ) -> None:
        self.platform_rows = platform_rows
        self.platform_range_calls: list[tuple[int, int]] = []
        self.auth_admin = FakeAuthAdmin(auth_users)
        self.auth = SimpleNamespace(admin=self.auth_admin)

    def table(self, name: str) -> FakeUsersQuery:
        assert name == "users"
        return FakeUsersQuery(self.platform_rows, self.platform_range_calls)


def test_default_seed_dry_run_paginates_reports_pii_free_and_skips_platform_admin() -> None:
    client = FakeClient(
        [
            {"id": "user-1", "tenant_id": "tenant-a", "role": "tenant_admin"},
            {"id": "user-2", "tenant_id": "tenant-b", "role": "viewer"},
        ],
        [
            _auth_user(
                "platform-1",
                email="operator@example.com",
                app_metadata={"role": "platform_admin", "platform_admin": True},
                user_metadata={"display_name": "Private Operator", "role": "platform_admin"},
            ),
            _auth_user(
                "user-1",
                email="person.one@example.com",
                app_metadata={
                    "provider": "email",
                    PUBLIC_KEY: {"tenant_id": "wrong", "role": "viewer"},
                },
                user_metadata={
                    "display_name": "Private Person",
                    "tenant_id": "legacy-tenant",
                    "role": "viewer",
                },
            ),
            _auth_user(
                "user-2",
                email="person.two@example.com",
                app_metadata={PUBLIC_KEY: {"tenant_id": "tenant-b", "role": "viewer"}},
                user_metadata={"locale": "fr", "tenant_id": "legacy-tenant"},
            ),
        ],
    )

    report = reconcile_auth_claims(
        client,
        page_size=2,
        allowed_platform_admin_emails=["operator@example.com"],
    )

    assert report.has_errors is False
    assert report.phase == "seed"
    assert report.authorization_scope == "public"
    assert report.counts == {
        "platform_users_scanned": 2,
        "auth_users_scanned": 3,
        "platform_admins_skipped": 1,
        "unchanged": 1,
        "updates_planned": 1,
        "updates_applied": 0,
        "missing_auth_users": 0,
        "orphan_auth_users": 0,
        "structural_errors": 0,
        "update_errors": 0,
        "residual_errors": 0,
    }
    assert client.platform_range_calls == [(0, 1), (2, 3)]
    assert client.auth_admin.list_calls == [(1, 2), (2, 2)]
    assert client.auth_admin.update_calls == []
    serialized = json.dumps(report.as_dict())
    for private_value in (
        "person.one@example.com",
        "Private Person",
        "operator@example.com",
        "wrong",
        "user-1",
        "tenant-a",
    ):
        assert private_value not in serialized
    assert "set_scoped_authorization" in serialized


def test_seed_preserves_user_metadata_and_public_dev_prod_sibling_scopes() -> None:
    original_user_metadata = {
        "display_name": "Private Person",
        "tenant_id": "legacy-tenant",
        "role": "legacy-role",
        "locale": "en",
    }
    client = FakeClient(
        [{"id": "shared-user", "tenant_id": "dev-tenant", "role": "tenant_admin"}],
        [
            _auth_user(
                "shared-user",
                email="shared@example.com",
                app_metadata={
                    "provider": "email",
                    PUBLIC_KEY: {"tenant_id": "public-tenant", "role": "viewer"},
                    DEV_KEY: {"tenant_id": "stale-dev", "role": "viewer"},
                    PROD_KEY: {"tenant_id": "prod-tenant", "role": "finance_lead"},
                },
                user_metadata=original_user_metadata,
            )
        ],
    )

    first = reconcile_auth_claims(
        client,
        apply=True,
        phase="seed",
        authorization_scope="transmuter_dev",
    )

    assert first.has_errors is False
    assert first.counts["updates_applied"] == 1
    assert client.auth_admin.update_calls == [
        (
            "shared-user",
            {
                "app_metadata": {
                    DEV_KEY: {"tenant_id": "dev-tenant", "role": "tenant_admin"},
                    "tenant_id": None,
                    "role": None,
                    "platform_admin": None,
                }
            },
        )
    ]
    user = client.auth_admin.users["shared-user"]
    assert user.app_metadata == {
        "provider": "email",
        PUBLIC_KEY: {"tenant_id": "public-tenant", "role": "viewer"},
        DEV_KEY: {"tenant_id": "dev-tenant", "role": "tenant_admin"},
        PROD_KEY: {"tenant_id": "prod-tenant", "role": "finance_lead"},
    }
    assert user.user_metadata == original_user_metadata

    second = reconcile_auth_claims(
        client,
        apply=True,
        phase="seed",
        authorization_scope="transmuter_dev",
    )

    assert second.counts["unchanged"] == 1
    assert second.counts["updates_planned"] == 0
    assert len(client.auth_admin.update_calls) == 1


def test_seed_removes_global_app_authorization_markers_for_ordinary_user() -> None:
    original_user_metadata = {
        "display_name": "Private Person",
        "tenant_id": "legacy-user-tenant",
        "role": "legacy-user-role",
    }
    client = FakeClient(
        [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
        [
            _auth_user(
                "user-1",
                email="person@example.com",
                app_metadata={
                    "provider": "email",
                    "tenant_id": "global-tenant",
                    "role": "platform_admin",
                    "platform_admin": True,
                    PUBLIC_KEY: {"tenant_id": "tenant-a", "role": "viewer"},
                    DEV_KEY: {"tenant_id": "dev-tenant", "role": "finance_lead"},
                },
                user_metadata=original_user_metadata,
            )
        ],
    )

    report = reconcile_auth_claims(client, apply=True, authorization_scope="public")

    assert report.has_errors is False
    assert report.counts["updates_planned"] == 1
    assert report.counts["updates_applied"] == 1
    assert client.auth_admin.update_calls == [
        (
            "user-1",
            {
                "app_metadata": {
                    PUBLIC_KEY: {"tenant_id": "tenant-a", "role": "viewer"},
                    "tenant_id": None,
                    "role": None,
                    "platform_admin": None,
                }
            },
        )
    ]
    user = client.auth_admin.users["user-1"]
    assert user.app_metadata == {
        "provider": "email",
        PUBLIC_KEY: {"tenant_id": "tenant-a", "role": "viewer"},
        DEV_KEY: {"tenant_id": "dev-tenant", "role": "finance_lead"},
    }
    assert user.user_metadata == original_user_metadata


def test_cleanup_tombstones_legacy_claims_and_preserves_sibling_scopes() -> None:
    client = FakeClient(
        [{"id": "shared-user", "tenant_id": "dev-tenant", "role": "tenant_admin"}],
        [
            _auth_user(
                "shared-user",
                email="shared@example.com",
                app_metadata={
                    "provider": "email",
                    PUBLIC_KEY: {"tenant_id": "public-tenant", "role": "viewer"},
                    DEV_KEY: {"tenant_id": "stale-dev", "role": "viewer"},
                    PROD_KEY: {"tenant_id": "prod-tenant", "role": "finance_lead"},
                },
                user_metadata={
                    "display_name": "Private Person",
                    "tenant_id": "legacy-tenant",
                    "role": "viewer",
                    "locale": "en",
                },
            )
        ],
    )

    first = reconcile_auth_claims(
        client,
        apply=True,
        phase="cleanup",
        authorization_scope="transmuter_dev",
    )

    assert first.has_errors is False
    assert first.counts["updates_applied"] == 1
    assert client.auth_admin.update_calls == [
        (
            "shared-user",
            {
                "app_metadata": {
                    DEV_KEY: {"tenant_id": "dev-tenant", "role": "tenant_admin"},
                    "tenant_id": None,
                    "role": None,
                    "platform_admin": None,
                },
                "user_metadata": {"tenant_id": None, "role": None},
            },
        )
    ]
    user = client.auth_admin.users["shared-user"]
    assert user.app_metadata[PUBLIC_KEY] == {"tenant_id": "public-tenant", "role": "viewer"}
    assert user.app_metadata[PROD_KEY] == {
        "tenant_id": "prod-tenant",
        "role": "finance_lead",
    }
    assert user.user_metadata == {"display_name": "Private Person", "locale": "en"}

    second = reconcile_auth_claims(
        client,
        apply=True,
        phase="cleanup",
        authorization_scope="transmuter_dev",
    )

    assert second.counts["unchanged"] == 1
    assert len(client.auth_admin.update_calls) == 1


def test_missing_auth_blocks_while_shared_directory_orphan_only_warns() -> None:
    client = FakeClient(
        [
            {"id": "matched", "tenant_id": "tenant-a", "role": "viewer"},
            {"id": "missing", "tenant_id": "tenant-a", "role": "viewer"},
        ],
        [
            _auth_user("matched", email="matched@example.com"),
            _auth_user("other-schema", email="other-schema@example.com"),
        ],
    )

    report = reconcile_auth_claims(client, apply=True)

    assert report.has_errors is True
    assert report.counts["missing_auth_users"] == 1
    assert report.counts["orphan_auth_users"] == 1
    assert report.counts["updates_planned"] == 0
    assert client.auth_admin.update_calls == []
    serialized = json.dumps(report.as_dict())
    assert "matched@example.com" not in serialized
    assert "other-schema@example.com" not in serialized


def test_orphan_warning_allows_updates_and_strict_mode_blocks() -> None:
    platform_rows = [{"id": "matched", "tenant_id": "tenant-a", "role": "viewer"}]
    auth_users = [
        _auth_user("matched", email="matched@example.com"),
        _auth_user("other-schema", email="other-schema@example.com"),
    ]
    client = FakeClient(platform_rows, auth_users)

    report = reconcile_auth_claims(client, apply=True)

    assert report.has_errors is False
    assert report.counts["orphan_auth_users"] == 1
    assert report.counts["updates_applied"] == 1
    orphan = next(record for record in report.records if record.get("code") == "orphan_auth_user")
    assert orphan["outcome"] == "warning"

    strict_client = FakeClient(platform_rows, auth_users)
    strict_report = reconcile_auth_claims(strict_client, apply=True, strict_orphans=True)
    assert strict_report.has_errors is True
    assert strict_client.auth_admin.update_calls == []


def test_claim_references_surface_cross_schema_conflicts_without_claim_values() -> None:
    auth_user = _auth_user("shared-user", email="private@example.com")
    first = reconcile_auth_claims(
        FakeClient(
            [{"id": "shared-user", "tenant_id": "tenant-a", "role": "viewer"}],
            [auth_user],
        ),
        authorization_scope="transmuter_dev",
    )
    second = reconcile_auth_claims(
        FakeClient(
            [{"id": "shared-user", "tenant_id": "tenant-b", "role": "tenant_admin"}],
            [auth_user],
        ),
        authorization_scope="transmuter",
    )

    assert first.records[0]["user_ref"] == second.records[0]["user_ref"]
    assert first.records[0]["canonical_claims_ref"] != second.records[0]["canonical_claims_ref"]
    serialized = json.dumps([first.as_dict(), second.as_dict()])
    for private_value in ("shared-user", "tenant-a", "tenant-b", "private@example.com"):
        assert private_value not in serialized


def test_malformed_identity_rows_fail_structural_preflight() -> None:
    client = FakeClient(
        [
            {"id": "matched", "tenant_id": "tenant-a", "role": "viewer"},
            {"id": "invalid", "tenant_id": "", "role": "viewer"},
        ],
        [
            _auth_user("matched", email="matched@example.com"),
            _auth_user("", email="private-invalid@example.com"),
        ],
    )

    report = reconcile_auth_claims(client, apply=True)

    assert report.has_errors is True
    assert report.counts["structural_errors"] == 2
    assert client.auth_admin.update_calls == []
    serialized = json.dumps(report.as_dict())
    assert "private-invalid@example.com" not in serialized
    assert "invalid_platform_user" in serialized
    assert "invalid_auth_user" in serialized


def test_platform_admin_with_current_scope_platform_row_is_structural_error() -> None:
    client = FakeClient(
        [{"id": "platform-1", "tenant_id": "tenant-a", "role": "tenant_admin"}],
        [
            _auth_user(
                "platform-1",
                email="operator@example.com",
                app_metadata={"role": "platform_admin", "platform_admin": True},
            )
        ],
    )

    report = reconcile_auth_claims(
        client,
        apply=True,
        allowed_platform_admin_emails=["operator@example.com"],
    )

    assert report.has_errors is True
    assert report.counts["structural_errors"] == 1
    assert report.counts["platform_admins_skipped"] == 0
    assert report.records[0]["code"] == "platform_admin_platform_user_conflict"
    assert client.auth_admin.update_calls == []


@pytest.mark.parametrize(
    "hybrid_metadata",
    [
        {"tenant_id": "tenant-a"},
        {DEV_KEY: {"tenant_id": "tenant-a", "role": "viewer"}},
    ],
)
def test_hybrid_allowlisted_platform_admin_is_structural_error(
    hybrid_metadata: dict[str, Any],
) -> None:
    client = FakeClient(
        [],
        [
            _auth_user(
                "platform-1",
                email="operator@example.com",
                app_metadata={
                    "role": "platform_admin",
                    "platform_admin": True,
                    **hybrid_metadata,
                },
            )
        ],
    )

    report = reconcile_auth_claims(
        client,
        apply=True,
        allowed_platform_admin_emails=["operator@example.com"],
    )

    assert report.has_errors is True
    assert report.counts["structural_errors"] == 1
    assert report.counts["platform_admins_skipped"] == 0
    assert report.counts["orphan_auth_users"] == 0
    assert report.records[0]["code"] == "hybrid_platform_admin_authorization"
    assert client.auth_admin.update_calls == []


def test_cleanup_fails_when_refetched_metadata_retains_legacy_claims() -> None:
    client = FakeClient(
        [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
        [_auth_user("user-1", email="person@example.com", user_metadata={"role": "viewer"})],
    )
    client.auth_admin.retain_deleted_user_claims = True

    report = reconcile_auth_claims(client, apply=True, phase="cleanup")

    assert report.has_errors is True
    assert report.counts["updates_applied"] == 0
    assert report.counts["residual_errors"] == 1
    assert report.records[-1]["residual_codes"] == [
        "user_metadata_mismatch",
        "authorization_in_user_metadata",
    ]


@pytest.mark.parametrize(
    ("failure_point", "expected_count", "expected_code"),
    [
        ("update", "update_errors", "update_failed"),
        ("refetch", "residual_errors", "refetch_failed"),
    ],
)
def test_apply_reports_pii_free_update_and_refetch_errors(
    failure_point: str,
    expected_count: str,
    expected_code: str,
) -> None:
    client = FakeClient(
        [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
        [_auth_user("user-1", email="private@example.com")],
    )
    private_error = RuntimeError("private@example.com must not be reported")
    if failure_point == "update":
        client.auth_admin.update_error = private_error
    else:
        client.auth_admin.refetch_error = private_error

    report = reconcile_auth_claims(client, apply=True)

    assert report.has_errors is True
    assert report.counts[expected_count] == 1
    assert report.records[-1]["code"] == expected_code
    serialized = json.dumps(report.as_dict())
    assert "private@example.com" not in serialized
    assert "must not be reported" not in serialized


def test_production_seed_apply_requires_production_confirmation() -> None:
    client = FakeClient(
        [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
        [_auth_user("user-1", email="person@example.com")],
    )
    output = StringIO()

    exit_code = main(
        ["--apply"],
        client=client,
        environment="production",
        authorization_scope="transmuter",
        allowed_platform_admin_emails=[],
        environ={},
        stdout=output,
    )

    assert exit_code == 2
    assert client.auth_admin.list_calls == []
    assert json.loads(output.getvalue())["error"] == "production_confirmation_required"


def test_production_scope_requires_confirmation_even_with_development_environment() -> None:
    client = FakeClient(
        [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
        [_auth_user("user-1", email="person@example.com")],
    )
    output = StringIO()

    exit_code = main(
        ["--apply"],
        client=client,
        environment="development",
        authorization_scope="transmuter",
        allowed_platform_admin_emails=[],
        environ={},
        stdout=output,
    )

    assert exit_code == 2
    assert json.loads(output.getvalue())["error"] == "production_confirmation_required"
    assert client.auth_admin.list_calls == []


@pytest.mark.parametrize(
    ("environment", "authorization_scope"),
    [("production", "transmuter"), ("development", "transmuter_dev")],
)
def test_cleanup_apply_requires_cleanup_and_production_confirmations(
    environment: str,
    authorization_scope: str,
) -> None:
    def run(environ: dict[str, str]) -> tuple[int, FakeClient, dict[str, Any]]:
        client = FakeClient(
            [{"id": "user-1", "tenant_id": "tenant-a", "role": "viewer"}],
            [
                _auth_user(
                    "user-1",
                    email="person@example.com",
                    user_metadata={"tenant_id": "legacy", "role": "viewer"},
                )
            ],
        )
        output = StringIO()
        exit_code = main(
            ["--apply", "--phase", "cleanup"],
            client=client,
            environment=environment,
            authorization_scope=authorization_scope,
            allowed_platform_admin_emails=[],
            environ=environ,
            stdout=output,
        )
        return exit_code, client, json.loads(output.getvalue())

    exit_code, client, payload = run({})
    assert exit_code == 2
    assert payload["error"] == "production_confirmation_required"
    assert client.auth_admin.list_calls == []

    exit_code, client, payload = run({"CONFIRM_PROD_AUTH_RECONCILE": "1"})
    assert exit_code == 2
    assert payload["error"] == "cleanup_confirmation_required"
    assert client.auth_admin.list_calls == []

    exit_code, client, payload = run(
        {
            "CONFIRM_PROD_AUTH_RECONCILE": "1",
            "CONFIRM_AUTH_CLAIM_CLEANUP": "1",
        }
    )
    assert exit_code == 0
    assert payload["status"] == "ok"
    assert payload["phase"] == "cleanup"
    assert payload["authorization_scope"] == authorization_scope
    assert client.auth_admin.users["user-1"].user_metadata == {}
