from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException

from app.core.auth import CurrentUser
from app.core.rbac import (
    CAP_MANAGE_EXECUTION_EVIDENCE,
    CAP_MANAGE_GOVERNANCE,
    CAP_VIEW_ALL_INITIATIVES,
    ROLE_BUSINESS_BENEFIT_OWNER,
    ROLE_EXECUTIVE_SPONSOR,
    ROLE_FINANCE_LEAD,
    ROLE_INITIATIVE_OWNER,
    ROLE_PMO_LEAD,
    ROLE_TENANT_ADMIN,
    ROLE_TRANSFORMATION_OFFICE,
    ROLE_VIEWER,
    ROLE_WORKSTREAM_LEAD,
    VALID_ROLES,
    assert_can_manage_benefit_realization,
    assert_can_manage_financials,
    assert_can_manage_governance,
    assert_can_manage_initiative_execution,
    assert_can_manage_initiative_financials,
    assert_can_manage_initiative_master_data,
    assert_can_manage_shared_costs,
    assert_can_manage_tenant_setup,
    assert_can_manage_users,
    assert_can_validate_benefits,
    assert_can_view_initiative,
    assert_valid_role,
    has_capability,
    workstream_lead_filter,
)

TENANT_ID = uuid4()
USER_ID = uuid4()
OTHER_USER_ID = uuid4()
INITIATIVE_ID = str(uuid4())
OTHER_INITIATIVE_ID = str(uuid4())
WORKSTREAM_ID = str(uuid4())
OTHER_WORKSTREAM_ID = str(uuid4())


@dataclass
class FakeResult:
    data: object


class FakeQuery:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows
        self._filters: list[tuple[str, object]] = []
        self._maybe_single = False

    def select(self, *_args: object, **_kwargs: object) -> FakeQuery:
        return self

    def eq(self, key: str, value: object) -> FakeQuery:
        self._filters.append((key, value))
        return self

    def maybe_single(self) -> FakeQuery:
        self._maybe_single = True
        return self

    def execute(self) -> FakeResult:
        rows = self._rows
        for key, value in self._filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        if self._maybe_single:
            return FakeResult(dict(rows[0]) if rows else None)
        return FakeResult([dict(row) for row in rows])


class FakeClient:
    def __init__(self) -> None:
        self._tables = {
            "initiatives": [
                {
                    "id": INITIATIVE_ID,
                    "tenant_id": str(TENANT_ID),
                    "owner_id": str(USER_ID),
                    "group_owner_id": None,
                    "workstream_id": WORKSTREAM_ID,
                },
                {
                    "id": OTHER_INITIATIVE_ID,
                    "tenant_id": str(TENANT_ID),
                    "owner_id": str(OTHER_USER_ID),
                    "group_owner_id": None,
                    "workstream_id": OTHER_WORKSTREAM_ID,
                },
            ],
            "user_workstreams": [
                {
                    "tenant_id": str(TENANT_ID),
                    "user_id": str(USER_ID),
                    "workstream_id": WORKSTREAM_ID,
                }
            ],
            "milestones": [
                {
                    "id": str(uuid4()),
                    "tenant_id": str(TENANT_ID),
                    "initiative_id": INITIATIVE_ID,
                }
            ],
        }

    def table(self, name: str) -> FakeQuery:
        return FakeQuery(self._tables.get(name, []))


def current_user(role: str, user_id: UUID = USER_ID) -> CurrentUser:
    return CurrentUser(id=user_id, tenant_id=TENANT_ID, role=role)


def assert_forbidden(fn: object, *args: object) -> None:
    with pytest.raises(HTTPException) as exc:
        fn(*args)  # type: ignore[misc]
    assert exc.value.status_code == 403


def test_all_operating_model_roles_are_valid() -> None:
    assert {
        ROLE_TRANSFORMATION_OFFICE,
        ROLE_TENANT_ADMIN,
        ROLE_PMO_LEAD,
        ROLE_FINANCE_LEAD,
        ROLE_WORKSTREAM_LEAD,
        ROLE_INITIATIVE_OWNER,
        ROLE_BUSINESS_BENEFIT_OWNER,
        ROLE_EXECUTIVE_SPONSOR,
        ROLE_VIEWER,
    } == VALID_ROLES
    for role in VALID_ROLES:
        assert_valid_role(role)


def test_transformation_office_has_full_operating_permissions() -> None:
    user = current_user(ROLE_TRANSFORMATION_OFFICE)
    client = FakeClient()

    assert_can_manage_users(user)
    assert_can_manage_tenant_setup(user)
    assert_can_manage_governance(user)
    assert_can_manage_financials(user)
    assert_can_validate_benefits(user)
    assert_can_manage_benefit_realization(user)
    assert_can_manage_shared_costs(user)
    assert_can_manage_initiative_master_data(client, user, OTHER_INITIATIVE_ID)
    assert_can_manage_initiative_execution(client, user, OTHER_INITIATIVE_ID)
    assert_can_manage_initiative_financials(client, user, OTHER_INITIATIVE_ID)


def test_tenant_admin_permissions_are_setup_and_access_scoped() -> None:
    user = current_user(ROLE_TENANT_ADMIN)

    assert_can_manage_users(user)
    assert_can_manage_tenant_setup(user)
    assert_can_manage_governance(user)
    assert_forbidden(assert_can_manage_financials, user)
    assert_forbidden(assert_can_manage_shared_costs, user)


def test_pmo_finance_business_benefit_and_viewer_permissions() -> None:
    pmo = current_user(ROLE_PMO_LEAD)
    finance = current_user(ROLE_FINANCE_LEAD)
    benefit_owner = current_user(ROLE_BUSINESS_BENEFIT_OWNER)
    viewer = current_user(ROLE_VIEWER)
    executive = current_user(ROLE_EXECUTIVE_SPONSOR)

    assert has_capability(pmo.role, CAP_MANAGE_GOVERNANCE)
    assert has_capability(pmo.role, CAP_MANAGE_EXECUTION_EVIDENCE)
    assert_forbidden(assert_can_manage_financials, pmo)

    assert_can_manage_financials(finance)
    assert_can_validate_benefits(finance)
    assert_can_manage_benefit_realization(finance)
    assert_can_manage_shared_costs(finance)
    assert_forbidden(assert_can_manage_governance, finance)

    assert_can_manage_benefit_realization(benefit_owner)
    assert_forbidden(assert_can_validate_benefits, benefit_owner)
    assert_forbidden(assert_can_manage_financials, benefit_owner)

    assert has_capability(executive.role, CAP_VIEW_ALL_INITIATIVES)
    assert has_capability(viewer.role, CAP_VIEW_ALL_INITIATIVES)
    assert_forbidden(assert_can_manage_users, viewer)


def test_initiative_owner_and_workstream_lead_are_assignment_scoped() -> None:
    client = FakeClient()
    owner = current_user(ROLE_INITIATIVE_OWNER)
    workstream_lead = current_user(ROLE_WORKSTREAM_LEAD)

    assert_can_view_initiative(client, owner, INITIATIVE_ID)
    assert_can_manage_initiative_master_data(client, owner, INITIATIVE_ID)
    assert_can_manage_initiative_execution(client, owner, INITIATIVE_ID)
    assert_can_manage_initiative_financials(client, owner, INITIATIVE_ID)
    assert_forbidden(assert_can_manage_initiative_master_data, client, owner, OTHER_INITIATIVE_ID)
    assert_forbidden(assert_can_manage_initiative_financials, client, owner, OTHER_INITIATIVE_ID)

    assert workstream_lead_filter(client, workstream_lead) == [WORKSTREAM_ID]
    assert_can_view_initiative(client, workstream_lead, INITIATIVE_ID)
    assert_can_manage_initiative_master_data(client, workstream_lead, INITIATIVE_ID)
    assert_can_manage_initiative_execution(client, workstream_lead, INITIATIVE_ID)
    assert_forbidden(
        assert_can_manage_initiative_master_data,
        client,
        workstream_lead,
        OTHER_INITIATIVE_ID,
    )
    assert_forbidden(assert_can_manage_initiative_financials, client, workstream_lead, INITIATIVE_ID)


def test_migration_expands_roles_and_updates_financial_rls() -> None:
    migration = (
        Path(__file__).resolve().parents[3]
        / "supabase"
        / "migrations"
        / "20260629000001_operating_model_rbac_roles.sql"
    ).read_text()

    for role in VALID_ROLES:
        assert f"'{role}'" in migration

    assert "app_can_manage_initiative_financials" in migration
    assert "app_can_validate_benefits" in migration
    assert "app_can_manage_benefit_realization" in migration
    assert 'DROP POLICY IF EXISTS "fblve_insert"' in migration
    assert 'DROP POLICY IF EXISTS "brl_insert"' in migration
