from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from scripts import verify_five_tenant_dev_api_acceptance as acceptance
from scripts.multi_tenant_transformation_profiles import COMPANY_PROFILES


class _FakeTransport:
    def __init__(self, responses: dict[tuple[str, str], acceptance.ApiResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []
        self.tokens: list[str | None] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> acceptance.ApiResponse:
        del body
        self.calls.append((method, path))
        self.tokens.append(token)
        return self.responses.get(
            (method, path),
            acceptance.ApiResponse(
                500, b'{"detail":"unexpected fake request"}', "application/json"
            ),
        )


class _QueueTransport:
    def __init__(self, responses: dict[tuple[str, str], list[acceptance.ApiResponse]]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> acceptance.ApiResponse:
        del token, body
        self.calls.append((method, path))
        return self.responses[(method, path)].pop(0)


def _json_response(status: int, payload: object) -> acceptance.ApiResponse:
    import json

    return acceptance.ApiResponse(
        status,
        json.dumps(payload).encode("utf-8"),
        "application/json",
    )


def _session(role: str = "transformation_office") -> acceptance.UserSession:
    return acceptance.UserSession(
        identity=f"role:{role}",
        role=role,
        tenant_id="tenant-1",
        user_id=f"user-{role}",
        token=f"opaque-{role}",
    )


def test_dev_api_guard_accepts_only_exact_reviewed_target() -> None:
    assert (
        acceptance.assert_dev_api_target(
            "dev",
            acceptance.CONFIRMATION,
            acceptance.DEV_API_BASE_URL + "/",
        )
        == acceptance.DEV_API_BASE_URL
    )

    rejected = (
        "https://transmuter.ishirock.tech/api",
        "http://transmuter-dev.ishirock.tech/api",
        "https://user:secret@transmuter-dev.ishirock.tech/api",
        "https://transmuter-dev.ishirock.tech/api?target=prod",
        "https://transmuter-dev.ishirock.tech",
    )
    for target in rejected:
        with pytest.raises(RuntimeError, match="Refusing acceptance outside"):
            acceptance.assert_dev_api_target("dev", acceptance.CONFIRMATION, target)


def test_dev_api_guard_requires_exact_confirmation_and_environment() -> None:
    with pytest.raises(RuntimeError, match="exact dev environment"):
        acceptance.assert_dev_api_target(
            "production", acceptance.CONFIRMATION, acceptance.DEV_API_BASE_URL
        )
    with pytest.raises(RuntimeError, match="exact dev environment"):
        acceptance.assert_dev_api_target("dev", "wrong", acceptance.DEV_API_BASE_URL)


def test_password_has_no_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(acceptance.PASSWORD_ENV, raising=False)
    with pytest.raises(RuntimeError, match="at least 12"):
        acceptance.required_password()

    monkeypatch.setenv(acceptance.PASSWORD_ENV, "long-test-password")
    assert acceptance.required_password() == "long-test-password"


@pytest.mark.parametrize(
    "path",
    (
        "/meetings",
        "/meetings/series-1",
        "/admin/meeting-cleanup-candidates",
        "/action-items",
        "/portfolio/action-items",
        "/integrations/microsoft",
    ),
)
def test_non_meeting_guard_rejects_excluded_surfaces(path: str) -> None:
    with pytest.raises(acceptance.AcceptanceFailure, match="excluded"):
        acceptance.assert_non_meeting_path(path)


@pytest.mark.parametrize(
    "path",
    (
        "/dashboard",
        "/initiatives/initiative-1/risks",
        "/portfolio/financials",
        "/reports/executive-control-tower",
    ),
)
def test_non_meeting_guard_accepts_reviewed_surfaces(path: str) -> None:
    acceptance.assert_non_meeting_path(path)


def test_report_guard_rejects_secrets_emails_and_tokens() -> None:
    acceptance.assert_secret_free_report(
        {"environment": "dev", "tenants": [{"slug": "qa-fixture", "count": 10}]}
    )

    for unsafe in (
        {"email": "redacted"},
        {"token": "opaque"},
        {"note": "person@example.test"},
    ):
        with pytest.raises(acceptance.AcceptanceFailure, match="contains"):
            acceptance.assert_secret_free_report(unsafe)


def test_report_writer_never_persists_identity_material(tmp_path: Any) -> None:
    report = {"status": "passed", "tenants": [{"slug": "qa-fixture"}]}
    target = acceptance.write_report(str(tmp_path / "report.json"), report)
    assert target.read_text(encoding="utf-8").endswith("\n")

    with pytest.raises(acceptance.AcceptanceFailure, match="contains"):
        acceptance.write_report(str(tmp_path / "unsafe.json"), {"access_token": "do-not-write"})
    assert not (tmp_path / "unsafe.json").exists()


def test_tenant_session_set_contains_admin_plus_all_nine_roles() -> None:
    admin = acceptance.UserSession(
        "fixture-admin", "transformation_office", "tenant-1", "admin-1", "admin-token"
    )
    roles = {role: _session(role) for role in acceptance.ROLES}
    sessions = acceptance.TenantSessions("fixture", "tenant-1", admin, roles)

    assert len(sessions.all) == 10
    assert len({session.user_id for session in sessions.all}) == 10


def test_full_portfolio_roles_do_not_include_scoped_workstream_lead() -> None:
    assert "workstream_lead" not in acceptance.FULL_PORTFOLIO_ROLES
    assert "initiative_owner" not in acceptance.FULL_PORTFOLIO_ROLES
    assert {
        "transformation_office",
        "tenant_admin",
        "pmo_lead",
        "finance_lead",
        "business_benefit_owner",
        "executive_sponsor",
        "viewer",
    } == acceptance.FULL_PORTFOLIO_ROLES


def test_role_visibility_validates_three_initiative_owner_assignments() -> None:
    items = [
        {"id": f"id-{code}", "initiative_code": code} for code in ("ENT-002", "ENT-005", "ENT-008")
    ]
    transport = _FakeTransport(
        {
            ("GET", "/initiatives?page_size=200"): _json_response(
                200, {"items": items, "total": 3, "page": 1, "page_size": 200}
            )
        }
    )
    runner = acceptance.AcceptanceRunner(transport, "long-test-password")  # type: ignore[arg-type]

    visible = runner._role_visible_initiatives(  # noqa: SLF001
        _session("initiative_owner"), COMPANY_PROFILES[0]
    )

    assert visible == items


def test_login_failure_message_never_exposes_email_password_or_response_detail() -> None:
    transport = _FakeTransport(
        {
            ("POST", "/auth/login"): _json_response(
                401,
                {"detail": "rejected person@example.test with long-test-password"},
            )
        }
    )
    runner = acceptance.AcceptanceRunner(transport, "long-test-password")  # type: ignore[arg-type]

    with pytest.raises(acceptance.AcceptanceFailure) as exc_info:
        runner._login(  # noqa: SLF001
            identity="fixture-admin",
            expected_role="transformation_office",
            email="person@example.test",
            tenant_slug="fixture-tenant",
        )

    message = str(exc_info.value)
    assert "person@example.test" not in message
    assert "long-test-password" not in message
    assert "rejected" not in message


def test_risk_probe_cleans_up_when_update_fails() -> None:
    initiative_id = "initiative-1"
    risk_id = "risk-probe-1"
    transport = _FakeTransport(
        {
            ("POST", f"/initiatives/{initiative_id}/risks"): _json_response(201, {"id": risk_id}),
            ("PUT", f"/initiatives/{initiative_id}/risks/{risk_id}"): _json_response(
                500, {"detail": "update failed"}
            ),
            ("DELETE", f"/initiatives/{initiative_id}/risks/{risk_id}"): acceptance.ApiResponse(
                204, b"", "application/json"
            ),
        }
    )
    runner = acceptance.AcceptanceRunner(transport, "long-test-password")  # type: ignore[arg-type]
    admin = _session()
    sessions = acceptance.TenantSessions(
        COMPANY_PROFILES[0].slug,
        admin.tenant_id,
        admin,
        {role: _session(role) for role in acceptance.ROLES},
    )

    with pytest.raises(acceptance.AcceptanceFailure, match="mutations.risk.update"):
        runner.exercise_reversible_mutations(COMPANY_PROFILES[0], sessions, {"id": initiative_id})

    assert transport.calls[-1] == (
        "DELETE",
        f"/initiatives/{initiative_id}/risks/{risk_id}",
    )


def test_viewer_risk_probe_uses_admin_token_to_clean_unexpected_success() -> None:
    path = "/initiatives/initiative-1/risks"
    cleanup_prefix = "/initiatives/initiative-1/risks"
    created_id = "unexpected-created-row"
    transport = _FakeTransport(
        {
            ("POST", path): _json_response(201, {"id": created_id}),
            ("DELETE", f"{cleanup_prefix}/{created_id}"): acceptance.ApiResponse(
                204, b"", "application/json"
            ),
        }
    )
    runner = acceptance.AcceptanceRunner(transport, "long-test-password")  # type: ignore[arg-type]

    with pytest.raises(acceptance.AcceptanceFailure, match="unexpectedly allowed"):
        runner._assert_create_denied(  # noqa: SLF001
            path=path,
            token="opaque-token",
            body={"name": "probe"},
            denied_status=403,
            cleanup_path_prefix=cleanup_prefix,
            cleanup_token="admin-cleanup-token",
            surface="protected.create",
        )

    assert transport.calls == [
        ("POST", path),
        ("DELETE", f"{cleanup_prefix}/{created_id}"),
    ]
    assert transport.tokens == ["opaque-token", "admin-cleanup-token"]


def test_milestone_cleanup_runs_even_when_checklist_cleanup_fails() -> None:
    milestone_id = "milestone-probe"
    checklist_id = "checklist-probe"
    checklist_path = f"/milestones/{milestone_id}/checklist/{checklist_id}"
    milestone_path = f"/milestones/{milestone_id}"
    transport = _FakeTransport(
        {
            ("DELETE", checklist_path): _json_response(500, {"detail": "failed"}),
            ("DELETE", milestone_path): acceptance.ApiResponse(204, b"", "application/json"),
        }
    )
    runner = acceptance.AcceptanceRunner(transport, "long-test-password")  # type: ignore[arg-type]

    with pytest.raises(acceptance.AcceptanceFailure, match="checklist.cleanup"):
        runner._cleanup_milestone_probe(  # noqa: SLF001
            milestone_id=milestone_id,
            checklist_id=checklist_id,
            token="opaque-token",
        )

    assert transport.calls == [
        ("DELETE", checklist_path),
        ("DELETE", milestone_path),
    ]


def test_login_honors_bounded_retry_after_without_exposing_credentials() -> None:
    login_path = "/auth/login"
    me_path = "/auth/me"
    transport = _QueueTransport(
        {
            ("POST", login_path): [
                acceptance.ApiResponse(
                    429,
                    b'{"detail":"rate limited"}',
                    "application/json",
                    retry_after_seconds=60,
                ),
                _json_response(
                    200,
                    {
                        "access_token": "opaque-token",
                        "tenant_id": "tenant-1",
                        "user_id": "user-1",
                        "role": "viewer",
                    },
                ),
            ],
            ("GET", me_path): [
                _json_response(
                    200,
                    {
                        "id": "user-1",
                        "tenant_id": "tenant-1",
                        "role": "viewer",
                        "status": "active",
                    },
                )
            ],
        }
    )
    sleeps: list[float] = []
    runner = acceptance.AcceptanceRunner(
        transport,  # type: ignore[arg-type]
        "long-test-password",
        exercise_mutations=False,
        sleep=sleeps.append,
    )

    session = runner._login(  # noqa: SLF001
        identity="role:viewer",
        expected_role="viewer",
        email="viewer@fixture.transmuter.test",
        tenant_slug="fixture-tenant",
    )

    assert session.user_id == "user-1"
    assert sleeps == [60.0]
    assert transport.calls == [("POST", login_path), ("POST", login_path), ("GET", me_path)]


def test_retry_after_parser_accepts_only_bounded_integer_seconds() -> None:
    assert acceptance._retry_after_seconds("60") == 60  # noqa: SLF001
    for value in (None, "", "0", "121", "1.5", "later"):
        assert acceptance._retry_after_seconds(value) is None  # noqa: SLF001


def test_http_transport_rejects_paths_that_escape_base_url() -> None:
    transport = acceptance.HttpTransport(acceptance.DEV_API_BASE_URL)
    for path in ("https://example.test/api", "//example.test/api", "/../production"):
        with pytest.raises(acceptance.AcceptanceFailure, match="relative|escape"):
            transport.request("GET", path)
