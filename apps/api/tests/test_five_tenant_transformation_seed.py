from __future__ import annotations

from argparse import Namespace
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from scripts import seed_enterprise_transformation_scenario as enterprise
from scripts import seed_five_tenant_transformation_program as five_tenant


class _Result:
    def __init__(self, data: list[dict[str, object]] | None = None) -> None:
        self.data = data or []


class _InsertQuery:
    def __init__(self, rows: dict[str, list[dict[str, object]]], table: str) -> None:
        self._rows = rows
        self._table = table

    def insert(self, payload: object) -> _InsertQuery:
        values = payload if isinstance(payload, list) else [payload]
        self._rows[self._table].extend(values)  # type: ignore[arg-type]
        return self

    def execute(self) -> _Result:
        return _Result()


class _InsertClient:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, object]]] = defaultdict(list)

    def table(self, name: str) -> _InsertQuery:
        return _InsertQuery(self.rows, name)


def _patch_seed_orchestration(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    calls: list[str] = []

    def record(name: str, result: object = None):
        def inner(*_args: object, **_kwargs: object) -> object:
            calls.append(name)
            return result

        return inner

    monkeypatch.setattr(enterprise, "ensure_org", record("organization", "tenant-1"))
    monkeypatch.setattr(enterprise, "assert_seed_target_allowed", record("guard"))
    monkeypatch.setattr(enterprise, "ensure_admin_user", record("admin", "user-1"))
    monkeypatch.setattr(enterprise, "delete_tenant_rows", record("reset"))
    monkeypatch.setattr(enterprise, "insert_business_units", record("business_units", {}))
    monkeypatch.setattr(enterprise, "insert_workstreams", record("workstreams", {}))
    monkeypatch.setattr(enterprise, "insert_stage_gates", record("stage_gates"))
    monkeypatch.setattr(enterprise, "insert_gate_criteria", record("gate_criteria", []))
    monkeypatch.setattr(enterprise, "insert_financial_config", record("financial_config"))
    monkeypatch.setattr(enterprise, "insert_engine_config", record("engine", ({}, {})))
    monkeypatch.setattr(enterprise, "insert_tenant_baselines", record("baselines"))
    initiative_ids = {f"ENT-{index:03d}": f"initiative-{index}" for index in range(1, 11)}
    monkeypatch.setattr(enterprise, "insert_initiatives", record("initiatives", initiative_ids))
    monkeypatch.setattr(enterprise, "insert_initiative_financial_scope", record("scope"))
    monkeypatch.setattr(enterprise, "insert_initiative_controls", record("controls"))
    monkeypatch.setattr(enterprise, "insert_bankable_plan_and_realization_demo", record("plans"))
    monkeypatch.setattr(enterprise, "insert_forecasts_and_workstream_targets", record("forecasts"))
    monkeypatch.setattr(enterprise, "insert_shared_cost_demo", record("shared_costs"))
    monkeypatch.setattr(enterprise, "insert_initiative_dependencies", record("dependencies"))
    monkeypatch.setattr(enterprise, "insert_meeting_demo", record("meetings"))

    class _DashboardConfig:
        def __init__(self, *_args: object) -> None:
            pass

        def enable_all_defaults(self) -> None:
            calls.append("dashboards")

    monkeypatch.setattr(enterprise, "DashboardConfigService", _DashboardConfig)
    return calls


def test_enterprise_seed_can_explicitly_exclude_all_meeting_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_seed_orchestration(monkeypatch)

    result = enterprise.seed_enterprise_transformation_scenario(
        object(),  # type: ignore[arg-type]
        admin_password="long-test-password",
        fixture_owner="unit-test-fixture",
        include_meetings=False,
    )

    assert result["initiative_count"] == 10
    assert result["meetings_included"] is False
    assert "dependencies" in calls
    assert "meetings" not in calls


def test_enterprise_seed_preserves_opt_in_meeting_demo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_seed_orchestration(monkeypatch)

    result = enterprise.seed_enterprise_transformation_scenario(
        object(),  # type: ignore[arg-type]
        admin_password="long-test-password",
        fixture_owner="unit-test-fixture",
        include_meetings=True,
    )

    assert result["meetings_included"] is True
    assert calls[-2:] == ["dependencies", "meetings"]


def test_initiative_controls_cover_every_initiative_with_quarterly_data() -> None:
    client = _InsertClient()
    initiative_ids = {f"ENT-{index:03d}": f"initiative-{index}" for index in range(1, 11)}

    enterprise.insert_initiative_controls(  # type: ignore[arg-type]
        client,
        "tenant-1",
        "user-1",
        initiative_ids,
    )

    assert len(client.rows["kpis"]) == 20
    assert len(client.rows["kpi_entries"]) == 240
    assert len(client.rows["risks"]) == 20
    assert len(client.rows["status_updates"]) == 20
    assert {row["initiative_id"] for row in client.rows["kpis"]} == set(initiative_ids.values())
    assert all(isinstance(row["value_base"], str) for row in client.rows["kpi_entries"])
    submitted_dates = {
        date.fromisoformat(str(row["submitted_at"])[:10])
        for row in client.rows["status_updates"]
        if row["submitted_at"] is not None
    }
    assert submitted_dates == {
        enterprise.STATUS_CADENCE_AS_OF_DATE - timedelta(days=4),
        enterprise.STATUS_CADENCE_AS_OF_DATE - timedelta(days=22),
    }


def test_dependency_seed_never_writes_meeting_tables() -> None:
    client = _InsertClient()
    initiative_ids = {f"ENT-{index:03d}": f"initiative-{index}" for index in range(1, 11)}

    enterprise.insert_initiative_dependencies(  # type: ignore[arg-type]
        client,
        "tenant-1",
        "user-1",
        initiative_ids,
        {},
    )

    assert len(client.rows["initiative_dependencies"]) == 3
    assert set(client.rows) == {"initiative_dependencies"}


def test_workstreams_use_the_decoupled_current_schema() -> None:
    client = _InsertClient()

    workstreams = enterprise.insert_workstreams(client, "tenant-1")  # type: ignore[arg-type]

    assert len(workstreams) == 5
    assert set(workstreams) == {
        "Automation",
        "Offshoring & Operating Model",
        "Commercial Growth",
        "ERP & Data Platform",
        "Procurement & Supply Chain",
    }
    assert all(set(row) == {"id", "tenant_id", "name"} for row in client.rows["workstreams"])


def test_reporting_year_helpers_match_the_platform_year_period_contract() -> None:
    assert enterprise.reporting_year_months(2028) == [(2028, month) for month in range(1, 13)]
    assert enterprise.reporting_year_bounds(2028) == (
        date(2028, 1, 1),
        date(2028, 12, 31),
    )
    assert enterprise.reporting_year_actual_fraction(2027) == Decimal("1")
    assert enterprise.reporting_year_actual_fraction(2028) == Decimal("0.5")
    assert enterprise.reporting_year_actual_fraction(2029) == Decimal("0")


class _MetricQuery:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, object]] = []

    def select(self, *_columns: str) -> _MetricQuery:
        return self

    def eq(self, key: str, value: object) -> _MetricQuery:
        self._filters.append((key, value))
        return self

    def execute(self) -> _Result:
        return _Result(
            [
                row
                for row in self._rows
                if all(row.get(key) == value for key, value in self._filters)
            ]
        )


class _MetricClient:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def table(self, name: str) -> _MetricQuery:
        assert name == "financial_metric_values"
        return _MetricQuery(self._rows)


def test_reporting_year_metric_totals_use_post_rebaseline_database_values() -> None:
    client = _MetricClient(
        [
            {
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-5",
                "metric_definition_id": "metric-margin",
                "scenario_id": "scenario-plan",
                "year": 2028,
                "value": "45.0000",
            },
            {
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-5",
                "metric_definition_id": "metric-margin",
                "scenario_id": "scenario-plan",
                "year": 2028,
                "value": "54.0000",
            },
            {
                "tenant_id": "tenant-1",
                "initiative_id": "initiative-5",
                "metric_definition_id": "metric-margin",
                "scenario_id": "scenario-plan",
                "year": 2027,
                "value": "999.0000",
            },
        ]
    )

    totals = enterprise.reporting_year_metric_totals(  # type: ignore[arg-type]
        client,
        "tenant-1",
        "metric-margin",
        "scenario-plan",
        2028,
    )

    assert totals == {"initiative-5": Decimal("99.0000")}


def test_financial_actuals_and_costs_apply_the_scenario_cutoff_consistently() -> None:
    client = _InsertClient()
    seed = enterprise.INITIATIVES[0]
    metric_ids = {
        "annual_revenue_baseline": "metric-baseline-revenue",
        "annual_gross_margin_baseline": "metric-baseline-margin",
        "revenue_uplift": "metric-revenue",
        "gm_uplift": "metric-margin",
        "cost_savings": "metric-savings",
    }
    scenario_ids = {
        "baseline": "scenario-baseline",
        "plan_base": "scenario-plan-base",
        "plan_high": "scenario-plan-high",
        "actual": "scenario-actual",
    }

    enterprise.insert_initiatives(  # type: ignore[arg-type]
        client,
        "tenant-1",
        "user-1",
        {"CORP": "bu-corp", "COM": "bu-com", "OPS": "bu-ops", "TECH": "bu-tech", "SHR": "bu-shr"},
        {
            "Automation": "ws-automation",
            "Offshoring & Operating Model": "ws-offshoring",
            "Commercial Growth": "ws-commercial",
            "ERP & Data Platform": "ws-data",
            "Procurement & Supply Chain": "ws-procurement",
        },
        metric_ids,
        scenario_ids,
        initiatives=[seed],
    )

    actual_rows = [
        row
        for row in client.rows["financial_metric_values"]
        if row["scenario_id"] == "scenario-actual"
    ]
    expected_fy27_periods = set(enterprise.reporting_year_months(2027))
    expected_fy28_actual_periods = {(2028, month) for month in range(1, 7)}
    actual_periods = {(int(row["year"]), int(row["month"])) for row in actual_rows}
    assert actual_periods == expected_fy27_periods | expected_fy28_actual_periods
    assert all(
        date(int(row["year"]), int(row["month"]), 1) <= enterprise.SCENARIO_AS_OF_DATE
        for row in actual_rows
    )
    fy28_recurring_costs = [
        row
        for row in client.rows["financial_cost_lines"]
        if row["year"] == 2028 and row["is_recurring"] is True
    ]
    assert len(fy28_recurring_costs) == 3
    for row in fy28_recurring_costs:
        assert Decimal(str(row["amount_actual"])) == (
            Decimal(str(row["amount_plan"])) * Decimal("0.97") * Decimal("0.5")
        ).quantize(enterprise.MONEY)


class _DeleteQuery:
    def __init__(
        self,
        tables: list[str],
        table: str,
        failures: dict[str, str],
    ) -> None:
        self._tables = tables
        self._table = table
        self._failures = failures

    def delete(self) -> _DeleteQuery:
        return self

    def eq(self, _key: str, _value: object) -> _DeleteQuery:
        return self

    def execute(self) -> _Result:
        if code := self._failures.get(self._table):
            raise _DeleteError(code)
        self._tables.append(self._table)
        return _Result()


class _DeleteError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(f"delete failed with {code}")


class _DeleteClient:
    def __init__(self, failures: dict[str, str] | None = None) -> None:
        self.tables: list[str] = []
        self.failures = failures or {}

    def table(self, name: str) -> _DeleteQuery:
        return _DeleteQuery(self.tables, name, self.failures)


def test_tenant_reset_clears_dashboard_configuration_but_not_integrations() -> None:
    client = _DeleteClient()

    enterprise.delete_tenant_rows(client, "tenant-1")  # type: ignore[arg-type]

    assert "tenant_dashboard_config" in client.tables
    assert "integration_connections" not in client.tables
    assert "integration_oauth_states" not in client.tables


def test_tenant_reset_ignores_only_explicit_missing_relation_errors() -> None:
    missing_optional = _DeleteClient({"ai_copilot_actions": "PGRST205"})

    enterprise.delete_tenant_rows(missing_optional, "tenant-1")  # type: ignore[arg-type]

    assert "tenant_dashboard_config" in missing_optional.tables

    permission_failure = _DeleteClient({"ai_copilot_actions": "42501"})
    with pytest.raises(_DeleteError, match="42501"):
        enterprise.delete_tenant_rows(permission_failure, "tenant-1")  # type: ignore[arg-type]

    missing_required = _DeleteClient({"tenant_dashboard_config": "PGRST205"})
    with pytest.raises(_DeleteError, match="PGRST205"):
        enterprise.delete_tenant_rows(missing_required, "tenant-1")  # type: ignore[arg-type]


class _ScopeQuery:
    def __init__(self, client: _ScopeClient, table: str) -> None:
        self._client = client
        self._table = table
        self._selecting = False

    def select(self, *_columns: str) -> _ScopeQuery:
        self._selecting = True
        return self

    def eq(self, _key: str, _value: object) -> _ScopeQuery:
        return self

    def insert(self, payload: object) -> _ScopeQuery:
        values = payload if isinstance(payload, list) else [payload]
        self._client.rows[self._table].extend(values)  # type: ignore[arg-type]
        return self

    def execute(self) -> _Result:
        if self._selecting and self._table == "financial_cost_categories":
            return _Result(self._client.cost_categories)
        return _Result()


class _ScopeClient:
    def __init__(self) -> None:
        self.rows: dict[str, list[dict[str, object]]] = defaultdict(list)
        self.cost_categories = [
            {"id": "cost-implementation", "key": "implementation"},
            {"id": "cost-software", "key": "software"},
            {"id": "cost-unselected", "key": "facilities"},
        ]

    def table(self, name: str) -> _ScopeQuery:
        return _ScopeQuery(self, name)


def test_financial_scope_exposes_formula_and_source_metrics_for_every_initiative() -> None:
    client = _ScopeClient()
    initiative_ids = {"ENT-001": "initiative-1", "ENT-002": "initiative-2"}
    metric_ids = {
        "revenue_uplift": "metric-revenue",
        "gm_uplift": "metric-margin",
        "cost_savings": "metric-savings",
        "gross_margin_target": "metric-margin-target",
        "gross_margin_pct": "metric-margin-percent",
    }

    enterprise.insert_initiative_financial_scope(  # type: ignore[arg-type]
        client,
        "tenant-1",
        initiative_ids,
        metric_ids,
    )

    metric_scope_rows = [
        row
        for row in client.rows["initiative_financial_scope"]
        if row["scope_type"] == "metric_definition"
    ]
    active_metric_ids = {
        str(row["metric_definition_id"]) for row in metric_scope_rows if row["is_active"] is True
    }
    assert active_metric_ids == set(metric_ids.values())
    assert len(metric_scope_rows) == len(initiative_ids) * len(metric_ids)


def _dev_args() -> Namespace:
    return Namespace(confirm=five_tenant.CONFIRMATION)


def test_dev_target_guard_requires_exact_dev_url_schema_and_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSMUTER_ENVIRONMENT", "development")
    monkeypatch.setenv("SUPABASE_SCHEMA", five_tenant.DEV_SCHEMA)
    monkeypatch.setenv("APP_PUBLIC_URL", five_tenant.DEV_APP_URL)
    monkeypatch.setenv("SUPABASE_TARGET", "local")
    monkeypatch.setenv("SUPABASE_LOCAL_URL", five_tenant.DEV_SUPABASE_URL)

    five_tenant.assert_dev_target(_dev_args())

    monkeypatch.setenv("SUPABASE_TARGET", "cloud")
    with pytest.raises(RuntimeError, match="SUPABASE_TARGET=local"):
        five_tenant.assert_dev_target(_dev_args())
    monkeypatch.setenv("SUPABASE_TARGET", "local")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://transmuter.ishirock.tech")
    with pytest.raises(RuntimeError, match="Refusing seed outside"):
        five_tenant.assert_dev_target(_dev_args())


def test_dev_target_guard_requires_exact_confirmation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSMUTER_ENVIRONMENT", "development")
    monkeypatch.setenv("SUPABASE_SCHEMA", five_tenant.DEV_SCHEMA)
    monkeypatch.setenv("APP_PUBLIC_URL", five_tenant.DEV_APP_URL)
    monkeypatch.setenv("SUPABASE_TARGET", "local")
    monkeypatch.setenv("SUPABASE_LOCAL_URL", five_tenant.DEV_SUPABASE_URL)

    with pytest.raises(RuntimeError, match="--confirm"):
        five_tenant.assert_dev_target(Namespace(confirm="wrong"))


def test_password_is_required_and_never_has_a_source_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TRANSMUTER_MULTI_TENANT_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="at least 12"):
        five_tenant.required_password()

    monkeypatch.setenv("TRANSMUTER_MULTI_TENANT_PASSWORD", "long-test-password")
    assert five_tenant.required_password() == "long-test-password"


def test_enterprise_seed_guard_rejects_production_and_accepts_exact_dev(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TRANSMUTER_ENVIRONMENT", "development")
    monkeypatch.setenv("APP_PUBLIC_URL", enterprise.DEV_APP_URL)
    monkeypatch.setenv("SUPABASE_TARGET", "local")
    monkeypatch.setenv("SUPABASE_LOCAL_URL", enterprise.DEV_SUPABASE_URL)
    monkeypatch.setattr(enterprise, "get_supabase_schema", lambda: enterprise.DEV_SCHEMA)

    enterprise.assert_seed_target_allowed("dev", enterprise.DEV_SEED_CONFIRMATION)

    monkeypatch.setenv("SUPABASE_TARGET", "cloud")
    with pytest.raises(RuntimeError, match="SUPABASE_TARGET=local"):
        enterprise.assert_seed_target_allowed("dev", enterprise.DEV_SEED_CONFIRMATION)
    monkeypatch.setenv("SUPABASE_TARGET", "local")
    monkeypatch.setenv("APP_PUBLIC_URL", "https://transmuter.ishirock.tech")
    with pytest.raises(RuntimeError, match="Dev seed requires schema"):
        enterprise.assert_seed_target_allowed("dev", enterprise.DEV_SEED_CONFIRMATION)
    with pytest.raises(RuntimeError, match="explicitly set"):
        enterprise.assert_seed_target_allowed("", "")


class _AuthUser:
    def __init__(
        self,
        app_metadata: dict[str, object],
        *,
        user_id: str = "auth-user-1",
        email: str = "existing@acme-global-manufacturing.qa.transmuter-dev.ishirock.tech",
        user_metadata: dict[str, object] | None = None,
        is_super_admin: bool = False,
    ) -> None:
        self.id = user_id
        self.email = email
        self.app_metadata = app_metadata
        self.user_metadata = user_metadata or {}
        self.is_super_admin = is_super_admin


class _AuthAdmin:
    def __init__(self, users: list[_AuthUser]) -> None:
        self._users = users

    def list_users(self, **_kwargs: object) -> list[_AuthUser]:
        return self._users

    def get_user_by_id(self, user_id: str) -> SimpleNamespace:
        user = next((candidate for candidate in self._users if candidate.id == user_id), None)
        return SimpleNamespace(user=user)


class _Auth:
    def __init__(self, users: list[_AuthUser]) -> None:
        self.admin = _AuthAdmin(users)


class _AuthOnlyClient:
    def __init__(self, user: _AuthUser) -> None:
        self.auth = _Auth([user])


def test_existing_auth_email_with_production_scope_is_never_reset() -> None:
    user = _AuthUser(
        {
            "transmuter_authorization_transmuter_dev": {
                "tenant_id": "tenant-1",
                "role": "viewer",
            },
            "transmuter_authorization_transmuter": {
                "tenant_id": "production-tenant",
                "role": "viewer",
            },
        }
    )

    with pytest.raises(RuntimeError, match="multi-scope"):
        five_tenant.assert_auth_email_safe(  # type: ignore[arg-type]
            _AuthOnlyClient(user),
            email=user.email,
            expected_tenant_id="tenant-1",
            expected_role="viewer",
        )


def test_existing_auth_email_requires_fixture_ownership_marker() -> None:
    user = _AuthUser(
        {
            "transmuter_authorization_transmuter_dev": {
                "tenant_id": "tenant-1",
                "role": "viewer",
            }
        }
    )

    with pytest.raises(RuntimeError, match="not owned"):
        five_tenant.assert_auth_email_safe(  # type: ignore[arg-type]
            _AuthOnlyClient(user),
            email=user.email,
            expected_tenant_id="tenant-1",
            expected_role="viewer",
        )


class _SecurityResult:
    def __init__(self, data: object, count: int | None = None) -> None:
        self.data = data
        self.count = count


class _SecurityQuery:
    def __init__(self, client: _SecurityClient, table: str) -> None:
        self._client = client
        self._table = table
        self._filters: list[tuple[str, object]] = []
        self._single = False
        self._count = False

    def select(self, *_columns: str, count: str | None = None) -> _SecurityQuery:
        self._count = count == "exact"
        return self

    def eq(self, key: str, value: object) -> _SecurityQuery:
        self._filters.append((key, value))
        return self

    def maybe_single(self) -> _SecurityQuery:
        self._single = True
        return self

    def limit(self, _value: int) -> _SecurityQuery:
        return self

    def execute(self) -> _SecurityResult:
        rows = [
            row
            for row in self._client.tables.get(self._table, [])
            if all(row.get(key) == value for key, value in self._filters)
        ]
        if self._count:
            return _SecurityResult(rows[:1], count=len(rows))
        if self._single:
            return _SecurityResult(rows[0] if rows else None)
        return _SecurityResult(rows)


class _SecurityClient:
    def __init__(
        self,
        *,
        tables: dict[str, list[dict[str, object]]],
        auth_users: list[_AuthUser],
    ) -> None:
        self.tables = tables
        self.auth = _Auth(auth_users)

    def table(self, name: str) -> _SecurityQuery:
        return _SecurityQuery(self, name)


def _owned_admin_identity() -> tuple[dict[str, object], _AuthUser]:
    profile = five_tenant.COMPANY_PROFILES[0]
    tenant_id = "tenant-1"
    email = f"admin@{profile.email_domain}"
    platform = {
        "id": "auth-admin-1",
        "tenant_id": tenant_id,
        "email": email,
        "role": "transformation_office",
    }
    auth_user = _AuthUser(
        {
            "transmuter_authorization_transmuter_dev": {
                "tenant_id": tenant_id,
                "role": "transformation_office",
            },
            "transmuter_fixture": {
                "owner": five_tenant.FIXTURE_OWNER,
                "tenant_id": tenant_id,
            },
        },
        user_id="auth-admin-1",
        email=email,
    )
    return platform, auth_user


def _owned_fixture_tables(
    platform_rows: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    profile = five_tenant.COMPANY_PROFILES[0]
    return {
        "organizations": [
            {
                "id": "tenant-1",
                "slug": profile.slug,
                "settings": {
                    "qa_fixture": {
                        "owner": five_tenant.FIXTURE_OWNER,
                        "slug": profile.slug,
                    }
                },
            }
        ],
        "users": platform_rows,
        "integration_connections": [],
        "integration_oauth_states": [],
        "user_invites": [],
    }


def test_owned_fixture_identity_preflight_accepts_exact_subject_parity() -> None:
    platform, auth_user = _owned_admin_identity()
    client = _SecurityClient(
        tables=_owned_fixture_tables([platform]),
        auth_users=[auth_user],
    )

    five_tenant.assert_profile_auth_emails_safe(client, five_tenant.COMPANY_PROFILES[0])


def test_fixture_identity_preflight_rejects_subject_mismatch() -> None:
    platform, auth_user = _owned_admin_identity()
    auth_user.email = "changed@acme-global-manufacturing.qa.transmuter-dev.ishirock.tech"
    client = _SecurityClient(
        tables=_owned_fixture_tables([platform]),
        auth_users=[auth_user],
    )

    with pytest.raises(RuntimeError, match="subject mismatch"):
        five_tenant.assert_profile_auth_emails_safe(client, five_tenant.COMPANY_PROFILES[0])


def test_fixture_identity_preflight_rejects_duplicates_without_logging_email() -> None:
    platform, auth_user = _owned_admin_identity()
    duplicate = {**platform, "id": "auth-admin-2"}
    client = _SecurityClient(
        tables=_owned_fixture_tables([platform, duplicate]),
        auth_users=[auth_user],
    )

    with pytest.raises(RuntimeError, match="invalid or duplicate") as exc_info:
        five_tenant.assert_profile_auth_emails_safe(client, five_tenant.COMPANY_PROFILES[0])
    assert str(platform["email"]) not in str(exc_info.value)


@pytest.mark.parametrize("protected_table", ["user_invites", "integration_connections"])
def test_fixture_preflight_rejects_protected_tenant_state(protected_table: str) -> None:
    platform, auth_user = _owned_admin_identity()
    tables = _owned_fixture_tables([platform])
    tables[protected_table] = [{"id": "protected-1", "tenant_id": "tenant-1"}]
    client = _SecurityClient(tables=tables, auth_users=[auth_user])

    with pytest.raises(RuntimeError, match=protected_table):
        five_tenant.assert_profile_auth_emails_safe(client, five_tenant.COMPANY_PROFILES[0])


def test_seed_rejects_non_qa_admin_email_before_org_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _patch_seed_orchestration(monkeypatch)

    with pytest.raises(RuntimeError, match="approved dev QA domain"):
        enterprise.seed_enterprise_transformation_scenario(
            object(),  # type: ignore[arg-type]
            fixture_owner="unit-test-fixture",
            admin_email="admin@example.com",
            admin_password="long-test-password",
        )
    assert calls == ["guard"]


def test_hostinger_environment_fetch_fails_closed_on_redirect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_headers: dict[str, str] = {}

    class _RedirectingOpener:
        def open(self, request: object, timeout: int) -> object:
            del timeout
            captured_headers.update(dict(request.header_items()))  # type: ignore[attr-defined]
            raise HTTPError(
                "https://developers.hostinger.com/api/test",
                302,
                "redirect",
                {},
                None,
            )

    monkeypatch.setenv("HOSTINGER_API_KEY", "sensitive-token")
    monkeypatch.setattr(five_tenant, "build_opener", lambda *_args: _RedirectingOpener())

    with pytest.raises(RuntimeError, match="lookup failed") as exc_info:
        five_tenant.fetch_hostinger_environment_safely(
            five_tenant.DEV_HOSTINGER_PROJECT,
            "1695814",
        )
    assert "sensitive-token" not in str(exc_info.value)
    assert captured_headers["User-agent"] == five_tenant.HTTP_USER_AGENT
    assert captured_headers["Accept"] == "application/json"
    with pytest.raises(RuntimeError, match="reviewed dev target"):
        five_tenant.fetch_hostinger_environment_safely(
            five_tenant.DEV_HOSTINGER_PROJECT,
            "not-a-vps",
        )


def test_all_profiles_are_preflighted_before_first_seed_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import database

    calls: list[str] = []

    def preflight(_client: object, profile: object) -> None:
        calls.append(profile.slug)  # type: ignore[attr-defined]
        if len(calls) == len(five_tenant.COMPANY_PROFILES):
            raise RuntimeError("last profile conflict")

    monkeypatch.setattr(database, "get_supabase_schema", lambda: five_tenant.DEV_SCHEMA)
    monkeypatch.setattr(five_tenant, "assert_profile_auth_emails_safe", preflight)
    monkeypatch.setattr(
        enterprise,
        "seed_enterprise_transformation_scenario",
        lambda *_args, **_kwargs: pytest.fail("seed write occurred before all preflights"),
    )

    with pytest.raises(RuntimeError, match="last profile conflict"):
        five_tenant.seed_profiles(object(), "long-test-password")
    assert calls == [profile.slug for profile in five_tenant.COMPANY_PROFILES]
