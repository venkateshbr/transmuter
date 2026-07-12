"""Run guarded real-API acceptance checks for the five dev fixture tenants.

This verifier deliberately excludes meetings, meeting integrations, and meeting-backed
action items. It uses only the public HTTP API and leaves the seeded portfolio intact:
mutable probes are either idempotent or deleted through the API in a ``finally`` block.

Usage:
    cd apps/api
    TRANSMUTER_MULTI_TENANT_PASSWORD=... \
      uv run python scripts/verify_five_tenant_dev_api_acceptance.py \
        --environment dev \
        --confirm verify-five-tenant-dev-api \
        --base-url https://transmuter-dev.ishirock.tech/api \
        --report ../../scratch/five-tenant-api-acceptance.json
"""

from __future__ import annotations

import argparse
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from scripts.multi_tenant_transformation_profiles import COMPANY_PROFILES, CompanyProfile
from scripts.seed_operating_model_users import (
    PORTFOLIO_VIEW_ROLES,
    ROLES,
    TENANT_SETUP_ROLES,
)

DEV_API_BASE_URL = "https://transmuter-dev.ishirock.tech/api"
HTTP_USER_AGENT = "transmuter-five-tenant-api-acceptance/1.0"
CONFIRMATION = "verify-five-tenant-dev-api"
PASSWORD_ENV = "TRANSMUTER_MULTI_TENANT_PASSWORD"
FORBIDDEN_PATH_FRAGMENTS = (
    "/meetings",
    "/meeting-",
    "/meeting_",
    "/action-items",
    "/integrations",
)

EXPECTED_CODES = tuple(f"ENT-{index:03d}" for index in range(1, 11))
FULL_PORTFOLIO_ROLES = PORTFOLIO_VIEW_ROLES - {"workstream_lead"}
FINANCIAL_CONFIGURATION_ROLES = {
    "transformation_office",
    "tenant_admin",
    "finance_lead",
}
AUDIT_LOG_ROLES = {"transformation_office", "tenant_admin"}


class AcceptanceFailure(AssertionError):
    """A sanitized acceptance failure safe to print in CI or a terminal."""


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, *_args: object, **_kwargs: object) -> None:
        return None


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    body: bytes
    content_type: str
    retry_after_seconds: int | None = None

    def json(self) -> Any:
        try:
            return json.loads(self.body.decode("utf-8")) if self.body else None
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise AcceptanceFailure("API returned a non-JSON response for a JSON surface") from None


@dataclass(frozen=True, slots=True)
class UserSession:
    identity: str
    role: str
    tenant_id: str
    user_id: str
    token: str = field(repr=False)


@dataclass(slots=True)
class TenantSessions:
    slug: str
    tenant_id: str
    admin: UserSession
    roles: dict[str, UserSession]

    @property
    def all(self) -> tuple[UserSession, ...]:
        return (self.admin, *(self.roles[role] for role in ROLES))


class HttpTransport:
    """Minimal no-redirect JSON/binary transport for the reviewed dev API."""

    def __init__(self, base_url: str, *, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._opener = build_opener(_NoRedirectHandler())

    def request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> ApiResponse:
        assert_non_meeting_path(path)
        if not path.startswith("/") or path.startswith("//"):
            raise AcceptanceFailure("API request path must be relative to the reviewed base URL")
        parsed_path = urlsplit(path)
        if parsed_path.scheme or parsed_path.netloc or ".." in parsed_path.path.split("/"):
            raise AcceptanceFailure("API request path could escape the reviewed base URL")

        headers = {"Accept": "application/json", "User-Agent": HTTP_USER_AGENT}
        data: bytes | None = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        request = Request(
            f"{self.base_url}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                return ApiResponse(
                    status=response.status,
                    body=response.read(),
                    content_type=response.headers.get_content_type(),
                    retry_after_seconds=_retry_after_seconds(response.headers.get("Retry-After")),
                )
        except HTTPError as exc:
            return ApiResponse(
                status=exc.code,
                body=exc.read(),
                content_type=exc.headers.get_content_type(),
                retry_after_seconds=_retry_after_seconds(exc.headers.get("Retry-After")),
            )
        except (URLError, TimeoutError, OSError):
            raise AcceptanceFailure(
                "Dev API request failed before receiving an HTTP response"
            ) from None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", choices=("dev",), required=True)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--report")
    parser.add_argument("--skip-mutations", action="store_true")
    return parser.parse_args()


def assert_dev_api_target(environment: str, confirmation: str, base_url: str) -> str:
    normalized = base_url.rstrip("/")
    parsed = urlsplit(normalized)
    expected = urlsplit(DEV_API_BASE_URL)
    if environment != "dev" or confirmation != CONFIRMATION:
        raise RuntimeError("The exact dev environment and acceptance confirmation are required")
    if (
        normalized != DEV_API_BASE_URL
        or parsed.scheme != "https"
        or parsed.hostname != expected.hostname
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path != "/api"
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"Refusing acceptance outside {DEV_API_BASE_URL!r}")
    return normalized


def required_password() -> str:
    password = os.environ.get(PASSWORD_ENV, "")
    if len(password) < 12:
        raise RuntimeError(f"{PASSWORD_ENV} must be at least 12 characters")
    return password


def assert_non_meeting_path(path: str) -> None:
    lowered = path.lower()
    if any(fragment in lowered for fragment in FORBIDDEN_PATH_FRAGMENTS):
        raise AcceptanceFailure("Meeting and action-item API surfaces are excluded from this run")


def _retry_after_seconds(value: str | None) -> int | None:
    if value is None or not value.isdigit():
        return None
    seconds = int(value)
    return seconds if 1 <= seconds <= 120 else None


def _mapping(payload: Any, label: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AcceptanceFailure(f"{label} did not return a JSON object")
    return payload


def _list(payload: Any, label: str) -> list[Any]:
    if not isinstance(payload, list):
        raise AcceptanceFailure(f"{label} did not return a JSON array")
    return payload


def _items(payload: Any, label: str) -> list[dict[str, Any]]:
    result = _mapping(payload, label)
    items = result.get("items", result.get("data"))
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        raise AcceptanceFailure(f"{label} did not return an item collection")
    return items


def _assert_total(payload: Any, expected: int, label: str) -> list[dict[str, Any]]:
    result = _mapping(payload, label)
    items = _items(result, label)
    if result.get("total") != expected or len(items) != expected:
        raise AcceptanceFailure(f"{label} did not contain exactly {expected} records")
    return items


def _assert_minimum_total(payload: Any, minimum: int, label: str) -> list[dict[str, Any]]:
    result = _mapping(payload, label)
    items = _items(result, label)
    total = result.get("total", len(items))
    if not isinstance(total, int) or total < minimum or len(items) < minimum:
        raise AcceptanceFailure(f"{label} did not contain at least {minimum} records")
    return items


def assert_secret_free_report(value: Any) -> None:
    forbidden_keys = {"email", "password", "access_token", "refresh_token", "token"}

    def visit(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                if str(key).lower() in forbidden_keys:
                    raise AcceptanceFailure("Acceptance report contains a secret or identity field")
                visit(nested)
        elif isinstance(item, list | tuple):
            for nested in item:
                visit(nested)
        elif isinstance(item, str) and "@" in item:
            raise AcceptanceFailure("Acceptance report contains an email-like value")

    visit(value)


class AcceptanceRunner:
    def __init__(
        self,
        transport: HttpTransport,
        password: str,
        *,
        exercise_mutations: bool = True,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.transport = transport
        self.password = password
        self.exercise_mutations = exercise_mutations
        self._sleep = sleep
        self.request_count = 0
        self.surface_counts: dict[str, int] = {}

    def _request(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
        expected: set[int] = frozenset({200}),
        surface: str,
    ) -> ApiResponse:
        assert_non_meeting_path(path)
        response = self.transport.request(method, path, token=token, body=body)
        self.request_count += 1
        self.surface_counts[surface] = self.surface_counts.get(surface, 0) + 1
        if response.status not in expected:
            raise AcceptanceFailure(
                f"{surface} returned HTTP {response.status}; expected {sorted(expected)}"
            )
        return response

    def _json(
        self,
        method: str,
        path: str,
        *,
        token: str | None = None,
        body: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
        expected: set[int] = frozenset({200}),
        surface: str,
    ) -> tuple[int, Any]:
        response = self._request(
            method,
            path,
            token=token,
            body=body,
            expected=expected,
            surface=surface,
        )
        return response.status, response.json()

    def _login(
        self,
        *,
        identity: str,
        expected_role: str,
        email: str,
        tenant_slug: str,
    ) -> UserSession:
        payload: Any = None
        for attempt in range(3):
            response = self._request(
                "POST",
                "/auth/login",
                body={"email": email, "password": self.password},
                expected={200, 429},
                surface="auth.login",
            )
            if response.status == 200:
                payload = response.json()
                break
            retry_after = response.retry_after_seconds
            if attempt == 2 or retry_after is None:
                raise AcceptanceFailure(
                    f"{identity} in {tenant_slug} was rate-limited without a safe bounded retry"
                )
            self._sleep(float(retry_after))
        if payload is None:
            raise AcceptanceFailure(f"{identity} in {tenant_slug} did not authenticate")
        result = _mapping(payload, "auth.login")
        token = result.get("access_token")
        tenant_id = result.get("tenant_id")
        user_id = result.get("user_id")
        role = result.get("role")
        if (
            not isinstance(token, str)
            or not token
            or not isinstance(tenant_id, str)
            or not tenant_id
            or not isinstance(user_id, str)
            or not user_id
            or role != expected_role
        ):
            raise AcceptanceFailure(
                f"{identity} in {tenant_slug} did not receive the expected authenticated identity"
            )
        session = UserSession(identity, expected_role, tenant_id, user_id, token)
        _, me_payload = self._json(
            "GET",
            "/auth/me",
            token=token,
            surface="auth.me.read",
        )
        me = _mapping(me_payload, "auth.me")
        if (
            str(me.get("id")) != user_id
            or str(me.get("tenant_id")) != tenant_id
            or me.get("role") != expected_role
            or me.get("status") != "active"
        ):
            raise AcceptanceFailure(
                f"{identity} in {tenant_slug} returned inconsistent profile claims"
            )
        if self.exercise_mutations:
            patch = {
                "display_name": me.get("display_name"),
                "title": me.get("title"),
                "onboarding_completed": bool(me.get("onboarding_completed")),
            }
            _, patched_payload = self._json(
                "PATCH",
                "/auth/me",
                token=token,
                body=patch,
                surface="auth.me.idempotent-update",
            )
            patched = _mapping(patched_payload, "auth.me.patch")
            if str(patched.get("id")) != user_id or patched.get("role") != expected_role:
                raise AcceptanceFailure(
                    f"{identity} in {tenant_slug} changed identity during profile update"
                )
        return session

    def authenticate_tenant(self, profile: CompanyProfile) -> TenantSessions:
        admin = self._login(
            identity="fixture-admin",
            expected_role="transformation_office",
            email=f"admin@{profile.email_domain}",
            tenant_slug=profile.slug,
        )
        roles: dict[str, UserSession] = {}
        for role in ROLES:
            roles[role] = self._login(
                identity=f"role:{role}",
                expected_role=role,
                email=f"rbac-{role.replace('_', '-')}@{profile.email_domain}",
                tenant_slug=profile.slug,
            )
        sessions = TenantSessions(profile.slug, admin.tenant_id, admin, roles)
        tenant_ids = {session.tenant_id for session in sessions.all}
        user_ids = {session.user_id for session in sessions.all}
        if tenant_ids != {admin.tenant_id} or len(user_ids) != 10:
            raise AcceptanceFailure(
                f"{profile.slug} did not authenticate as ten unique users in one tenant"
            )
        return sessions

    def _role_visible_initiatives(
        self,
        session: UserSession,
        profile: CompanyProfile,
    ) -> list[dict[str, Any]]:
        _, payload = self._json(
            "GET",
            "/initiatives?page_size=200",
            token=session.token,
            surface="rbac.initiative-list",
        )
        result = _mapping(payload, "role initiative list")
        items = _items(result, "role initiative list")
        total = result.get("total")
        if total != len(items):
            raise AcceptanceFailure(f"{session.identity} in {profile.slug} returned a partial list")
        if session.role in FULL_PORTFOLIO_ROLES:
            if total != 10:
                raise AcceptanceFailure(
                    f"{session.identity} in {profile.slug} did not see the full portfolio"
                )
        elif session.role == "initiative_owner":
            codes = {str(item.get("initiative_code")) for item in items}
            if total != 3 or codes != {"ENT-002", "ENT-005", "ENT-008"}:
                raise AcceptanceFailure(
                    f"{session.identity} in {profile.slug} did not see its three assignments"
                )
        elif session.role == "workstream_lead":
            if not isinstance(total, int) or not 0 < total < 10:
                raise AcceptanceFailure(
                    f"{session.identity} in {profile.slug} did not receive scoped workstream access"
                )
        return items

    def verify_role_matrix(
        self,
        profile: CompanyProfile,
        sessions: TenantSessions,
        dashboard_config: dict[str, Any],
        initiative_id: str,
    ) -> None:
        for session in sessions.all:
            visible = self._role_visible_initiatives(session, profile)
            _, dashboard_payload = self._json(
                "GET",
                "/dashboard",
                token=session.token,
                surface="rbac.dashboard",
            )
            dashboard = _mapping(dashboard_payload, "role dashboard")
            summary = _mapping(dashboard.get("summary"), "role dashboard summary")
            if summary.get("total_initiatives") != len(visible):
                raise AcceptanceFailure(
                    f"{session.identity} in {profile.slug} dashboard visibility disagreed with its list"
                )

            config_expected = {200} if session.role in PORTFOLIO_VIEW_ROLES else {403}
            self._json(
                "GET",
                "/admin/dashboard-configuration",
                token=session.token,
                expected=config_expected,
                surface="rbac.dashboard-configuration.read",
            )
            financial_expected = {200} if session.role in FINANCIAL_CONFIGURATION_ROLES else {403}
            self._json(
                "GET",
                "/admin/financial-configuration",
                token=session.token,
                expected=financial_expected,
                surface="rbac.financial-configuration.read",
            )
            audit_expected = {200} if session.role in AUDIT_LOG_ROLES else {403}
            self._json(
                "GET",
                "/admin/audit-logs?limit=5",
                token=session.token,
                expected=audit_expected,
                surface="rbac.audit-log.read",
            )
            if self.exercise_mutations:
                update_expected = {200} if session.role in TENANT_SETUP_ROLES else {403}
                self._json(
                    "PUT",
                    "/admin/dashboard-configuration",
                    token=session.token,
                    body=dashboard_config,
                    expected=update_expected,
                    surface="rbac.dashboard-configuration.idempotent-update",
                )

        viewer = sessions.roles["viewer"]
        before_status, before_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/risks",
            token=sessions.admin.token,
            surface="rbac.denial-preflight",
        )
        if before_status != 200:
            raise AcceptanceFailure("Risk denial preflight failed")
        before_total = _mapping(before_payload, "risk denial preflight").get("total")
        self._assert_create_denied(
            path=f"/initiatives/{initiative_id}/risks",
            token=viewer.token,
            body={
                "description": "API acceptance denial probe",
                "type": "operational",
                "impact": "low",
                "likelihood": "low",
            },
            denied_status=403,
            cleanup_path_prefix=f"/initiatives/{initiative_id}/risks",
            cleanup_token=sessions.admin.token,
            surface="rbac.risk-create.denied",
        )
        _, after_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/risks",
            token=sessions.admin.token,
            surface="rbac.denial-postflight",
        )
        if _mapping(after_payload, "risk denial postflight").get("total") != before_total:
            raise AcceptanceFailure("Denied risk mutation changed tenant data")

    def _download(
        self,
        path: str,
        token: str,
        *,
        surface: str,
        signature: bytes | None = None,
        minimum_bytes: int = 64,
    ) -> None:
        response = self._request("GET", path, token=token, surface=surface)
        if len(response.body) < minimum_bytes or (
            signature is not None and not response.body.startswith(signature)
        ):
            raise AcceptanceFailure(f"{surface} returned an invalid or empty artifact")

    def verify_portfolio_reads(
        self,
        profile: CompanyProfile,
        sessions: TenantSessions,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        token = sessions.admin.token
        _, initiatives_payload = self._json(
            "GET",
            "/initiatives?page_size=200",
            token=token,
            surface="initiatives.list",
        )
        initiatives = _assert_total(initiatives_payload, 10, "initiatives")
        codes = tuple(sorted(str(item.get("initiative_code")) for item in initiatives))
        names = {str(item.get("name")) for item in initiatives}
        if codes != EXPECTED_CODES or names != set(profile.initiative_names):
            raise AcceptanceFailure(
                f"{profile.slug} initiative identity set does not match its fixture"
            )

        _, dashboard_payload = self._json(
            "GET", "/dashboard", token=token, surface="dashboard.portfolio"
        )
        dashboard = _mapping(dashboard_payload, "dashboard")
        if _mapping(dashboard.get("summary"), "dashboard summary").get("total_initiatives") != 10:
            raise AcceptanceFailure(f"{profile.slug} dashboard does not roll up ten initiatives")

        _, dashboard_config_payload = self._json(
            "GET",
            "/admin/dashboard-configuration",
            token=token,
            surface="dashboard.configuration",
        )
        dashboard_config = _mapping(dashboard_config_payload, "dashboard configuration")
        dashboards = _list(dashboard_config.get("dashboards"), "dashboard registry")
        if len(dashboards) != 10 or any(
            not _mapping(item, "dashboard registry item").get("is_enabled") for item in dashboards
        ):
            raise AcceptanceFailure(f"{profile.slug} does not expose all ten dashboards")

        expected_totals: tuple[tuple[str, int, str], ...] = (
            ("/people", 10, "people.directory"),
            ("/users", 10, "people.users"),
            ("/invites", 0, "people.invites"),
            ("/business-units", 5, "portfolio.business-units"),
            ("/workstreams", 5, "portfolio.workstreams"),
            ("/portfolio/kpis", 20, "portfolio.kpis"),
            ("/portfolio/risks", 20, "portfolio.risks"),
            ("/milestones", 30, "portfolio.milestones-all"),
            ("/portfolio/milestones", 30, "portfolio.milestones"),
            ("/initiative-dependencies", 3, "dependencies.initiative"),
        )
        counts: dict[str, int] = {"initiatives": 10}
        for path, expected, surface in expected_totals:
            _, payload = self._json("GET", path, token=token, surface=surface)
            _assert_total(payload, expected, surface)
            counts[surface] = expected

        _, users_payload = self._json("GET", "/users", token=token, surface="people.profile-source")
        for user in _assert_total(users_payload, 10, "people profile source"):
            user_id = str(user["id"])
            for suffix, surface in (
                ("", "people.profile"),
                ("/pressure", "people.pressure"),
            ):
                _, payload = self._json(
                    "GET",
                    f"/users/{user_id}{suffix}",
                    token=token,
                    surface=surface,
                )
                _mapping(payload, surface)

        _, workstreams_payload = self._json(
            "GET", "/workstreams", token=token, surface="financial.workstream-source"
        )
        workstreams = _assert_total(workstreams_payload, 5, "workstream target source")
        for workstream in workstreams:
            workstream_id = str(workstream["id"])
            for suffix, surface in (
                ("/target-lock", "financial.workstream-target-history"),
                ("/target-lock/preview", "financial.workstream-target-preview"),
            ):
                _, payload = self._json(
                    "GET",
                    f"/workstreams/{workstream_id}{suffix}",
                    token=token,
                    surface=surface,
                )
                target_payload = _mapping(payload, surface)
                if suffix == "/target-lock" and (
                    target_payload.get("current") is None
                    or len(_list(target_payload.get("history"), "workstream target history")) < 1
                ):
                    raise AcceptanceFailure(
                        f"{profile.slug} is missing a seeded workstream target lock"
                    )

        _, shared_pools_payload = self._json(
            "GET", "/shared-cost-pools", token=token, surface="shared-costs.pools"
        )
        shared_pools = _assert_total(shared_pools_payload, 4, "shared cost pools")
        counts["shared-costs.pools"] = len(shared_pools)
        for pool in shared_pools:
            pool_id = str(pool["id"])
            for suffix, surface in (
                ("/periods", "shared-costs.periods"),
                ("/allocation-rules", "shared-costs.allocation-rules"),
                ("/allocation-runs", "shared-costs.allocation-runs"),
            ):
                _, payload = self._json(
                    "GET",
                    f"/shared-cost-pools/{pool_id}{suffix}",
                    token=token,
                    surface=surface,
                )
                rows = _list(payload, surface)
                if len(rows) < 1:
                    raise AcceptanceFailure(f"{profile.slug} has an incomplete shared-cost pool")

        _, benefits_payload = self._json(
            "GET",
            "/portfolio/benefits-register",
            token=token,
            surface="portfolio.benefits-register",
        )
        benefit_items = _list(
            _mapping(benefits_payload, "benefits register").get("items"),
            "benefits register items",
        )
        validation_statuses = {
            str(_mapping(item, "benefits register item").get("validation_status"))
            for item in benefit_items
        }
        if len(benefit_items) != 30 or validation_statuses != {
            "draft",
            "submitted",
            "finance_validated",
            "rejected",
        }:
            raise AcceptanceFailure(f"{profile.slug} benefits register does not contain 30 lines")
        counts["portfolio.benefits-register"] = len(benefit_items)

        _, submissions_payload = self._json(
            "GET",
            "/governance/submissions",
            token=token,
            surface="governance.submissions",
        )
        submissions = _list(submissions_payload, "governance submissions")
        if len(submissions) != 41:
            raise AcceptanceFailure(f"{profile.slug} does not have 41 governance submissions")
        counts["governance.submissions"] = len(submissions)

        _, settings_payload = self._json(
            "GET", "/admin/settings", token=token, surface="admin.settings"
        )
        settings = _mapping(settings_payload, "admin settings")
        reporting = _mapping(
            _mapping(settings.get("settings"), "organization settings").get("financial_reporting"),
            "financial reporting settings",
        )
        if (
            reporting.get("reporting_currency") != profile.currency
            or reporting.get("fiscal_year_start_month") != profile.fiscal_start_month
        ):
            raise AcceptanceFailure(
                f"{profile.slug} does not expose its configured currency and fiscal start month"
            )

        mapping_paths = (
            ("/admin/billing", "admin.billing"),
            ("/admin/launch-readiness", "admin.launch-readiness"),
            ("/admin/setup-status", "admin.setup-status"),
            ("/admin/gate-criteria", "admin.gate-criteria"),
            ("/admin/audit-logs?limit=25", "admin.audit-logs"),
            ("/billing/config", "billing.config"),
            ("/ai/tools", "ai.tool-catalog"),
            ("/search?" + urlencode({"q": "ENT-001"}), "search.global"),
            ("/portfolio/kpi-pulse", "portfolio.kpi-pulse"),
            ("/portfolio/risks/heatmap", "portfolio.risk-heatmap"),
            ("/status-updates/compliance", "status.compliance"),
            ("/portfolio/status-updates/compliance", "status.portfolio-compliance"),
            ("/portfolio/governance", "governance.portfolio"),
            ("/financial-configuration", "financial.configuration"),
            ("/financial-engine-configuration", "financial.engine-configuration"),
            ("/financial-engine/annual-baselines", "financial.annual-baselines"),
            ("/admin/financial-engine/annual-baselines", "financial.admin-baselines"),
            ("/admin/financial-governance", "financial.governance-settings"),
            ("/benefit-ledger/summary?granularity=monthly", "financial.ledger-summary"),
            ("/portfolio/value-bridge", "financial.portfolio-value-bridge"),
            ("/portfolio/financials?granularity=monthly", "financial.portfolio"),
            ("/portfolio/investments-payback", "financial.investments-payback"),
            ("/portfolio/initiative-portfolio", "financial.initiative-portfolio"),
            ("/portfolio/value-ramp?granularity=monthly", "financial.value-ramp"),
            (
                "/portfolio/financials/contributors?period=2028-01&granularity=monthly&year=2028",
                "financial.contributors",
            ),
            ("/shared-costs/config", "shared-costs.config"),
            ("/shared-costs/reporting-settings", "shared-costs.reporting-settings"),
            ("/reports/owner-cockpit", "reports.owner-cockpit"),
            ("/reports/executive-control-tower", "reports.control-tower"),
            ("/reports/investor-summary", "reports.investor-summary"),
            ("/dependencies", "dependencies.milestones"),
            ("/portfolio/dependencies", "dependencies.portfolio-milestones"),
        )
        for path, surface in mapping_paths:
            _, payload = self._json("GET", path, token=token, surface=surface)
            _mapping(payload, surface)

        list_paths = (
            ("/status-updates/portfolio", "status.portfolio-updates", 10),
            ("/status-updates/nudges", "status.nudges", 0),
            ("/governance/stage-gates", "governance.stage-gates", 5),
            ("/admin/governance/stage-gates", "governance.admin-stage-gates", 5),
            ("/admin/governance/gate-criteria", "governance.admin-criteria", None),
            ("/governance/criteria/1", "governance.criteria", None),
            ("/shared-cost-allocations", "shared-costs.allocations", 22),
        )
        for path, surface, expected_length in list_paths:
            _, payload = self._json("GET", path, token=token, surface=surface)
            rows = _list(payload, surface)
            if expected_length is not None and len(rows) != expected_length:
                raise AcceptanceFailure(
                    f"{profile.slug} {surface} did not contain {expected_length} records"
                )
            if expected_length is None and not rows:
                raise AcceptanceFailure(f"{profile.slug} {surface} is unexpectedly empty")

        self._download(
            "/dashboard/executive-summary.pdf",
            token,
            surface="exports.executive-summary-pdf",
            signature=b"%PDF",
        )
        self._download(
            "/initiatives/export",
            token,
            surface="exports.initiatives-csv",
            minimum_bytes=32,
        )
        self._download(
            "/initiatives/template",
            token,
            surface="exports.initiative-template",
            signature=b"PK\x03\x04",
        )
        self._download(
            "/portfolio/board-pack.xlsx",
            token,
            surface="exports.board-pack",
            signature=b"PK\x03\x04",
        )

        self.verify_role_matrix(
            profile,
            sessions,
            dashboard_config,
            str(initiatives[0]["id"]),
        )
        return initiatives, counts

    def verify_initiative_reads(
        self,
        profile: CompanyProfile,
        sessions: TenantSessions,
        initiatives: list[dict[str, Any]],
    ) -> dict[str, int]:
        token = sessions.admin.token
        totals = {
            "milestones": 0,
            "kpis": 0,
            "risks": 0,
            "status_updates": 0,
            "benefit_lines": 0,
            "metric_values": 0,
            "cost_lines": 0,
            "forecasts": 0,
            "ledger_entries": 0,
            "team_members": 0,
            "bankable_plan_versions": 0,
        }
        for initiative in initiatives:
            initiative_id = str(initiative["id"])
            code = str(initiative["initiative_code"])
            detail_paths = (
                (f"/initiatives/{initiative_id}", "initiative.detail"),
                (f"/initiatives/{initiative_id}/summary", "initiative.summary"),
                (f"/initiatives/{initiative_id}/ai-context", "initiative.ai-context"),
                (f"/initiatives/{initiative_id}/governance", "initiative.governance"),
                (f"/initiatives/{initiative_id}/gates", "initiative.gates"),
                (
                    f"/initiatives/{initiative_id}/gates/1/criteria",
                    "initiative.gate-criteria",
                ),
                (f"/initiatives/{initiative_id}/financials/baseline", "financial.baseline"),
                (f"/initiatives/{initiative_id}/bankable-plan", "financial.bankable-plan"),
                (
                    f"/initiatives/{initiative_id}/benefit-ledger/summary?granularity=monthly",
                    "financial.initiative-ledger-summary",
                ),
                (f"/initiatives/{initiative_id}/financials/selections", "financial.selections"),
                (
                    f"/initiatives/{initiative_id}/financials/value-bridge",
                    "financial.value-bridge",
                ),
                (
                    f"/initiatives/{initiative_id}/financials/scenario-summary?scenario=base",
                    "financial.scenario-summary",
                ),
                (
                    f"/initiatives/{initiative_id}/financials/break-even?scenario=base",
                    "financial.break-even",
                ),
                (
                    f"/initiatives/{initiative_id}/financials/assumptions",
                    "financial.assumptions",
                ),
                (f"/initiatives/{initiative_id}/dependencies", "initiative.dependencies"),
            )
            for path, surface in detail_paths:
                _, payload = self._json("GET", path, token=token, surface=surface)
                _mapping(payload, f"{surface} for {code}")

            _, kpis_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/kpis",
                token=token,
                surface="initiative.kpis",
            )
            kpis = _assert_total(kpis_payload, 2, f"{code} KPIs")
            if any(len(_list(kpi.get("entries"), f"{code} KPI entries")) != 12 for kpi in kpis):
                raise AcceptanceFailure(f"{code} KPI history does not span twelve quarters")
            totals["kpis"] += len(kpis)

            _, risks_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/risks",
                token=token,
                surface="initiative.risks",
            )
            totals["risks"] += len(_assert_total(risks_payload, 2, f"{code} risks"))

            _, milestones_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/milestones",
                token=token,
                surface="initiative.milestones",
            )
            milestones = _assert_total(milestones_payload, 3, f"{code} milestones")
            if any(milestone.get("checklist_total") != 1 for milestone in milestones):
                raise AcceptanceFailure(f"{code} milestones do not each have one checklist item")
            totals["milestones"] += len(milestones)
            first_milestone_id = str(milestones[0]["id"])
            for suffix, surface in (
                ("", "milestone.detail"),
                ("/pressure", "milestone.pressure"),
            ):
                _, payload = self._json(
                    "GET",
                    f"/milestones/{first_milestone_id}{suffix}",
                    token=token,
                    surface=surface,
                )
                _mapping(payload, surface)

            _, status_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/status-updates",
                token=token,
                surface="initiative.status-updates",
            )
            totals["status_updates"] += len(
                _assert_total(status_payload, 2, f"{code} status updates")
            )
            _, draft_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/status-updates/draft",
                token=token,
                surface="initiative.status-draft",
            )
            if draft_payload is not None:
                _mapping(draft_payload, f"{code} status draft")

            _, grid_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/financials",
                token=token,
                surface="financial.grid",
            )
            grid = _mapping(grid_payload, f"{code} financial grid")
            benefit_lines = _list(grid.get("benefit_lines"), f"{code} benefit lines")
            values = _list(grid.get("values"), f"{code} financial values")
            if len(benefit_lines) != 3 or len(values) < 222 or grid.get("locked") is not True:
                raise AcceptanceFailure(
                    f"{code} financial grid is incomplete or not governance-locked"
                )
            totals["benefit_lines"] += len(benefit_lines)
            totals["metric_values"] += len(values)
            benefit_line_id = str(_mapping(benefit_lines[0], "benefit line")["id"])
            _, validation_payload = self._json(
                "GET",
                (
                    f"/initiatives/{initiative_id}/financials/benefit-lines/"
                    f"{benefit_line_id}/validation-events"
                ),
                token=token,
                surface="financial.benefit-validation-events",
            )
            if not _list(validation_payload, "benefit validation events"):
                raise AcceptanceFailure(f"{code} benefit validation history is empty")

            _, cost_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/financials/cost-lines",
                token=token,
                surface="financial.cost-lines",
            )
            totals["cost_lines"] += len(_assert_total(cost_payload, 9, f"{code} cost lines"))

            _, forecast_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/financials/forecasts",
                token=token,
                surface="financial.forecasts",
            )
            forecasts = _list(
                _mapping(forecast_payload, f"{code} forecasts").get("items"),
                f"{code} forecast items",
            )
            if len(forecasts) != 3:
                raise AcceptanceFailure(f"{code} does not contain three forecast versions")
            totals["forecasts"] += len(forecasts)

            _, ledger_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/benefit-ledger",
                token=token,
                surface="financial.benefit-ledger",
            )
            ledger = _list(ledger_payload, f"{code} benefit ledger")
            if len(ledger) != 24:
                raise AcceptanceFailure(f"{code} benefit ledger does not span 24 months")
            totals["ledger_entries"] += len(ledger)

            _, history_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/bankable-plan/history",
                token=token,
                surface="financial.bankable-plan-history",
            )
            plan_history = _list(history_payload, f"{code} bankable plan history")
            if len(plan_history) < 1:
                raise AcceptanceFailure(f"{code} does not have an approved bankable plan")
            totals["bankable_plan_versions"] += len(plan_history)

            _, team_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/team",
                token=token,
                surface="initiative.team",
            )
            team = _list(
                _mapping(team_payload, f"{code} team").get("data"),
                f"{code} team members",
            )
            if len(team) != 3:
                raise AcceptanceFailure(f"{code} does not have its three operating-model members")
            totals["team_members"] += len(team)

            _, notes_payload = self._json(
                "GET",
                f"/initiatives/{initiative_id}/value-realization-notes",
                token=token,
                surface="initiative.value-realization-notes",
            )
            _list(notes_payload, "value realization notes")

        expected = {
            "milestones": 30,
            "kpis": 20,
            "risks": 20,
            "status_updates": 20,
            "benefit_lines": 30,
            "cost_lines": 90,
            "forecasts": 30,
            "ledger_entries": 240,
            "team_members": 30,
            "bankable_plan_versions": 11,
        }
        if (
            any(totals[key] != value for key, value in expected.items())
            or totals["metric_values"] < 2220
        ):
            raise AcceptanceFailure(
                f"{profile.slug} initiative rollups do not match fixture invariants"
            )

        first_id = str(initiatives[0]["id"])
        self._download(
            f"/initiatives/{first_id}/export",
            token,
            surface="exports.initiative-workbook",
            signature=b"PK\x03\x04",
        )
        self._download(
            f"/initiatives/{first_id}/financials/export.xlsx",
            token,
            surface="exports.financial-workbook",
            signature=b"PK\x03\x04",
        )
        return totals

    def _cleanup_delete(self, path: str, token: str, surface: str) -> None:
        self._request(
            "DELETE",
            path,
            token=token,
            expected={204, 404},
            surface=surface,
        )

    def _assert_create_denied(
        self,
        *,
        path: str,
        token: str,
        body: Mapping[str, Any],
        denied_status: int,
        cleanup_path_prefix: str,
        cleanup_token: str | None = None,
        surface: str,
    ) -> None:
        created_id: str | None = None
        unexpected_success = False
        try:
            status, payload = self._json(
                "POST",
                path,
                token=token,
                body=body,
                expected={denied_status, 201},
                surface=surface,
            )
            if status == denied_status:
                return
            unexpected_success = True
            created_id = str(_mapping(payload, surface).get("id") or "") or None
            if created_id is None:
                raise AcceptanceFailure(
                    f"{surface} unexpectedly created data without returning a cleanup identifier"
                )
        finally:
            if created_id:
                self._cleanup_delete(
                    f"{cleanup_path_prefix}/{created_id}",
                    cleanup_token or token,
                    f"{surface}.cleanup",
                )
        if unexpected_success:
            raise AcceptanceFailure(f"{surface} unexpectedly allowed a protected create")

    def _cleanup_milestone_probe(
        self,
        *,
        milestone_id: str | None,
        checklist_id: str | None,
        token: str,
    ) -> None:
        try:
            if checklist_id and milestone_id:
                self._cleanup_delete(
                    f"/milestones/{milestone_id}/checklist/{checklist_id}",
                    token,
                    "mutations.checklist.cleanup",
                )
        finally:
            if milestone_id:
                self._cleanup_delete(
                    f"/milestones/{milestone_id}",
                    token,
                    "mutations.milestone.delete",
                )

    def exercise_reversible_mutations(
        self,
        profile: CompanyProfile,
        sessions: TenantSessions,
        initiative: dict[str, Any],
    ) -> list[str]:
        if not self.exercise_mutations:
            return []
        token = sessions.admin.token
        initiative_id = str(initiative["id"])
        completed: list[str] = ["profile-idempotent-update", "dashboard-idempotent-update"]

        risk_id: str | None = None
        try:
            _, created_payload = self._json(
                "POST",
                f"/initiatives/{initiative_id}/risks",
                token=token,
                body={
                    "description": "Temporary API acceptance risk",
                    "type": "operational",
                    "impact": "low",
                    "likelihood": "low",
                    "status": "open",
                    "mitigation": "Delete after the reversible acceptance probe",
                },
                expected={201},
                surface="mutations.risk.create",
            )
            risk_id = str(_mapping(created_payload, "created risk").get("id") or "")
            if not risk_id:
                raise AcceptanceFailure("Risk create did not return an identifier")
            _, updated_payload = self._json(
                "PUT",
                f"/initiatives/{initiative_id}/risks/{risk_id}",
                token=token,
                body={"impact": "medium", "mitigation": "Updated reversible probe"},
                surface="mutations.risk.update",
            )
            if _mapping(updated_payload, "updated risk").get("impact") != "medium":
                raise AcceptanceFailure("Risk update did not persist through the API")
        finally:
            if risk_id:
                self._cleanup_delete(
                    f"/initiatives/{initiative_id}/risks/{risk_id}",
                    token,
                    "mutations.risk.delete",
                )
        completed.append("risk-create-update-delete")

        kpi_id: str | None = None
        try:
            _, created_payload = self._json(
                "POST",
                f"/initiatives/{initiative_id}/kpis",
                token=token,
                body={
                    "name": "Temporary API Acceptance KPI",
                    "type": "custom",
                    "category": "acceptance",
                    "frequency": "quarterly",
                    "unit": "index",
                },
                expected={201},
                surface="mutations.kpi.create",
            )
            kpi_id = str(_mapping(created_payload, "created KPI").get("id") or "")
            if not kpi_id:
                raise AcceptanceFailure("KPI create did not return an identifier")
            self._json(
                "PUT",
                f"/initiatives/{initiative_id}/kpis/{kpi_id}",
                token=token,
                body={"name": "Temporary API Acceptance KPI Updated"},
                surface="mutations.kpi.update",
            )
            _, entries_payload = self._json(
                "PUT",
                f"/initiatives/{initiative_id}/kpis/{kpi_id}/entries",
                token=token,
                body=[
                    {
                        "year": 2028,
                        "quarter": 2,
                        "value_base": "100.0000",
                        "value_high": "110.0000",
                        "value_actual": "105.0000",
                    }
                ],
                surface="mutations.kpi.entries",
            )
            if len(_list(entries_payload, "KPI entries")) != 1:
                raise AcceptanceFailure("KPI entry upsert did not return one entry")
        finally:
            if kpi_id:
                self._cleanup_delete(
                    f"/initiatives/{initiative_id}/kpis/{kpi_id}",
                    token,
                    "mutations.kpi.delete",
                )
        completed.append("kpi-create-update-entry-delete")

        milestone_id: str | None = None
        checklist_id: str | None = None
        try:
            _, created_payload = self._json(
                "POST",
                f"/initiatives/{initiative_id}/milestones",
                token=token,
                body={
                    "name": "Temporary API Acceptance Milestone",
                    "description": "Reversible acceptance probe",
                    "priority": "low",
                    "planned_start": "2028-07-01",
                    "planned_end": "2028-07-31",
                },
                expected={201},
                surface="mutations.milestone.create",
            )
            milestone_id = str(_mapping(created_payload, "created milestone").get("id") or "")
            if not milestone_id:
                raise AcceptanceFailure("Milestone create did not return an identifier")
            self._json(
                "PUT",
                f"/milestones/{milestone_id}",
                token=token,
                body={"status": "in_progress", "priority": "medium"},
                surface="mutations.milestone.update",
            )
            _, checklist_payload = self._json(
                "POST",
                f"/milestones/{milestone_id}/checklist",
                token=token,
                body={"text": "Temporary acceptance checklist", "sort_order": 1},
                expected={201},
                surface="mutations.checklist.create",
            )
            checklist_id = str(_mapping(checklist_payload, "created checklist").get("id") or "")
            if not checklist_id:
                raise AcceptanceFailure("Checklist create did not return an identifier")
            self._json(
                "PUT",
                f"/milestones/{milestone_id}/checklist/{checklist_id}",
                token=token,
                body={"completed": True},
                surface="mutations.checklist.toggle",
            )
            self._cleanup_delete(
                f"/milestones/{milestone_id}/checklist/{checklist_id}",
                token,
                "mutations.checklist.delete",
            )
            checklist_id = None
        finally:
            self._cleanup_milestone_probe(
                milestone_id=milestone_id,
                checklist_id=checklist_id,
                token=token,
            )
        completed.append("milestone-checklist-create-update-delete")

        _, risk_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/risks",
            token=token,
            surface="mutations.risk-postflight",
        )
        _assert_total(risk_payload, 2, f"{profile.slug} risk cleanup")
        _, kpi_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/kpis",
            token=token,
            surface="mutations.kpi-postflight",
        )
        _assert_total(kpi_payload, 2, f"{profile.slug} KPI cleanup")
        _, milestone_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/milestones",
            token=token,
            surface="mutations.milestone-postflight",
        )
        _assert_total(milestone_payload, 3, f"{profile.slug} milestone cleanup")
        _, cost_payload = self._json(
            "GET",
            f"/initiatives/{initiative_id}/financials/cost-lines",
            token=token,
            surface="mutations.financial-postflight",
        )
        _assert_total(cost_payload, 9, f"{profile.slug} financial lock cleanup")
        return completed

    def verify_cross_tenant_isolation(
        self,
        sessions: list[TenantSessions],
        initiative_ids: dict[str, str],
        user_ids: dict[str, str],
    ) -> int:
        checks = 0
        for index, source in enumerate(sessions):
            target = sessions[(index + 1) % len(sessions)]
            foreign_initiative_id = initiative_ids[target.slug]
            foreign_user_id = user_ids[target.slug]
            for session in source.all:
                self._json(
                    "GET",
                    f"/initiatives/{foreign_initiative_id}",
                    token=session.token,
                    expected={404},
                    surface="isolation.foreign-initiative-denied",
                )
                checks += 1
            self._json(
                "GET",
                f"/users/{foreign_user_id}",
                token=source.admin.token,
                expected={404},
                surface="isolation.foreign-user-denied",
            )
            checks += 1
        return checks

    def run(self) -> dict[str, Any]:
        sessions_by_slug: dict[str, TenantSessions] = {}
        tenant_ids: set[str] = set()
        tenant_reports: list[dict[str, Any]] = []
        first_initiatives: dict[str, str] = {}
        first_users: dict[str, str] = {}
        for profile in COMPANY_PROFILES:
            sessions = self.authenticate_tenant(profile)
            if sessions.tenant_id in tenant_ids:
                raise AcceptanceFailure(
                    f"{profile.slug} resolved to an already authenticated fixture tenant"
                )
            sessions_by_slug[profile.slug] = sessions
            tenant_ids.add(sessions.tenant_id)
            initiatives, portfolio_counts = self.verify_portfolio_reads(profile, sessions)
            initiative_counts = self.verify_initiative_reads(profile, sessions, initiatives)
            mutations = self.exercise_reversible_mutations(profile, sessions, initiatives[0])
            first_initiatives[profile.slug] = str(initiatives[0]["id"])
            first_users[profile.slug] = sessions.admin.user_id
            tenant_reports.append(
                {
                    "slug": profile.slug,
                    "currency": profile.currency,
                    "fiscal_start_month": profile.fiscal_start_month,
                    "authenticated_users": 10,
                    "portfolio_counts": portfolio_counts,
                    "initiative_counts": initiative_counts,
                    "mutations": mutations,
                }
            )

        if len(sessions_by_slug) != 5 or len(tenant_ids) != 5:
            raise AcceptanceFailure(
                "The five fixture profiles did not resolve to five isolated tenants"
            )

        session_list = [sessions_by_slug[profile.slug] for profile in COMPANY_PROFILES]
        isolation_checks = self.verify_cross_tenant_isolation(
            session_list,
            first_initiatives,
            first_users,
        )
        report = {
            "environment": "dev",
            "base_url": DEV_API_BASE_URL,
            "status": "passed",
            "tenant_count": 5,
            "authenticated_users": 50,
            "request_count": self.request_count,
            "isolation_denials": isolation_checks,
            "excluded_surfaces": [
                "meetings",
                "meeting integrations",
                "meeting-backed action items",
            ],
            "surface_counts": dict(sorted(self.surface_counts.items())),
            "tenants": tenant_reports,
        }
        assert_secret_free_report(report)
        return report


def write_report(path: str, report: dict[str, Any]) -> Path:
    assert_secret_free_report(report)
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def main() -> None:
    args = parse_args()
    base_url = assert_dev_api_target(args.environment, args.confirm, args.base_url)
    runner = AcceptanceRunner(
        HttpTransport(base_url),
        required_password(),
        exercise_mutations=not args.skip_mutations,
    )
    report = runner.run()
    if args.report:
        write_report(args.report, report)
    print(
        "Five-tenant dev API acceptance passed: "
        f"{report['tenant_count']} tenants, {report['authenticated_users']} users, "
        f"{report['request_count']} requests, {report['isolation_denials']} isolation denials"
    )


if __name__ == "__main__":
    main()
