"""Role based access-control helpers."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from supabase import Client

from app.core.auth import CurrentUser, get_current_user

ROLE_TRANSFORMATION_OFFICE = "transformation_office"
ROLE_TENANT_ADMIN = "tenant_admin"
ROLE_PMO_LEAD = "pmo_lead"
ROLE_FINANCE_LEAD = "finance_lead"
ROLE_WORKSTREAM_LEAD = "workstream_lead"
ROLE_INITIATIVE_OWNER = "initiative_owner"
ROLE_BUSINESS_BENEFIT_OWNER = "business_benefit_owner"
ROLE_EXECUTIVE_SPONSOR = "executive_sponsor"
ROLE_VIEWER = "viewer"

VALID_ROLES: set[str] = {
    ROLE_TRANSFORMATION_OFFICE,
    ROLE_TENANT_ADMIN,
    ROLE_PMO_LEAD,
    ROLE_FINANCE_LEAD,
    ROLE_WORKSTREAM_LEAD,
    ROLE_INITIATIVE_OWNER,
    ROLE_BUSINESS_BENEFIT_OWNER,
    ROLE_EXECUTIVE_SPONSOR,
    ROLE_VIEWER,
}

ROLE_LABELS: dict[str, str] = {
    ROLE_TRANSFORMATION_OFFICE: "Transformation Office",
    ROLE_TENANT_ADMIN: "Tenant Administrator",
    ROLE_PMO_LEAD: "PMO Lead / Governance Manager",
    ROLE_FINANCE_LEAD: "Finance Lead / Benefits Controller",
    ROLE_WORKSTREAM_LEAD: "Workstream Lead",
    ROLE_INITIATIVE_OWNER: "Initiative Owner",
    ROLE_BUSINESS_BENEFIT_OWNER: "Business Benefit Owner",
    ROLE_EXECUTIVE_SPONSOR: "Executive Sponsor",
    ROLE_VIEWER: "Management Viewer",
}

CAP_VIEW_PORTFOLIO = "portfolio.view"
CAP_VIEW_ALL_INITIATIVES = "initiatives.view_all"
CAP_MANAGE_USERS = "users.manage"
CAP_MANAGE_TENANT_SETUP = "tenant_setup.manage"
CAP_MANAGE_INITIATIVES = "initiatives.manage_all"
CAP_MANAGE_ASSIGNED_INITIATIVE = "initiatives.manage_assigned"
CAP_MANAGE_WORKSTREAM_INITIATIVES = "initiatives.manage_workstream"
CAP_MANAGE_FINANCIALS = "financials.manage"
CAP_MANAGE_ASSIGNED_FINANCIALS = "financials.manage_assigned"
CAP_VALIDATE_BENEFITS = "benefits.validate"
CAP_MANAGE_BENEFIT_REALIZATION = "benefits.realize"
CAP_MANAGE_SHARED_COSTS = "shared_costs.manage"
CAP_MANAGE_GOVERNANCE = "governance.manage"
CAP_MANAGE_PROGRAM_CADENCE = "program_cadence.manage"
CAP_MANAGE_EXECUTION_EVIDENCE = "execution_evidence.manage"
CAP_MANAGE_ASSIGNED_EXECUTION_EVIDENCE = "execution_evidence.manage_assigned"
CAP_MANAGE_WORKSTREAM_EXECUTION_EVIDENCE = "execution_evidence.manage_workstream"
CAP_VIEW_AUDIT_LOG = "audit_log.view"

ROLE_CAPABILITIES: dict[str, set[str]] = {
    ROLE_TRANSFORMATION_OFFICE: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
        CAP_MANAGE_USERS,
        CAP_MANAGE_TENANT_SETUP,
        CAP_MANAGE_INITIATIVES,
        CAP_MANAGE_ASSIGNED_INITIATIVE,
        CAP_MANAGE_WORKSTREAM_INITIATIVES,
        CAP_MANAGE_FINANCIALS,
        CAP_MANAGE_ASSIGNED_FINANCIALS,
        CAP_VALIDATE_BENEFITS,
        CAP_MANAGE_BENEFIT_REALIZATION,
        CAP_MANAGE_SHARED_COSTS,
        CAP_MANAGE_GOVERNANCE,
        CAP_MANAGE_PROGRAM_CADENCE,
        CAP_MANAGE_EXECUTION_EVIDENCE,
        CAP_MANAGE_ASSIGNED_EXECUTION_EVIDENCE,
        CAP_MANAGE_WORKSTREAM_EXECUTION_EVIDENCE,
        CAP_VIEW_AUDIT_LOG,
    },
    ROLE_TENANT_ADMIN: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
        CAP_MANAGE_USERS,
        CAP_MANAGE_TENANT_SETUP,
        CAP_MANAGE_GOVERNANCE,
        CAP_VIEW_AUDIT_LOG,
    },
    ROLE_PMO_LEAD: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
        CAP_MANAGE_GOVERNANCE,
        CAP_MANAGE_PROGRAM_CADENCE,
        CAP_MANAGE_EXECUTION_EVIDENCE,
    },
    ROLE_FINANCE_LEAD: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
        CAP_MANAGE_FINANCIALS,
        CAP_VALIDATE_BENEFITS,
        CAP_MANAGE_BENEFIT_REALIZATION,
        CAP_MANAGE_SHARED_COSTS,
    },
    ROLE_WORKSTREAM_LEAD: {
        CAP_VIEW_PORTFOLIO,
        CAP_MANAGE_WORKSTREAM_INITIATIVES,
        CAP_MANAGE_WORKSTREAM_EXECUTION_EVIDENCE,
    },
    ROLE_INITIATIVE_OWNER: {
        CAP_MANAGE_ASSIGNED_INITIATIVE,
        CAP_MANAGE_ASSIGNED_FINANCIALS,
        CAP_MANAGE_ASSIGNED_EXECUTION_EVIDENCE,
    },
    ROLE_BUSINESS_BENEFIT_OWNER: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
        CAP_MANAGE_BENEFIT_REALIZATION,
    },
    ROLE_EXECUTIVE_SPONSOR: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
    },
    ROLE_VIEWER: {
        CAP_VIEW_PORTFOLIO,
        CAP_VIEW_ALL_INITIATIVES,
    },
}


def assert_valid_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role must be one of: {', '.join(sorted(VALID_ROLES))}",
        )


def has_capability(role: str, capability: str) -> bool:
    return capability in ROLE_CAPABILITIES.get(role, set())


def require_capability(capability: str) -> Callable[..., object]:
    """Factory: returns a dependency that enforces a tenant capability."""

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_capability(user.role, capability):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _check


def can_view_all_initiatives(role: str) -> bool:
    return has_capability(role, CAP_VIEW_ALL_INITIATIVES)


def assert_can_manage_users(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_USERS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_tenant_setup(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_TENANT_SETUP):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_initiatives(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_INITIATIVES):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_initiative_master_data(
    client: Client,
    user: CurrentUser,
    initiative_id: str,
) -> None:
    if has_capability(user.role, CAP_MANAGE_INITIATIVES):
        return
    row = _initiative_access_row(client, user, initiative_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    if has_capability(user.role, CAP_MANAGE_ASSIGNED_INITIATIVE) and _user_owns_initiative(
        row, user
    ):
        return
    if has_capability(user.role, CAP_MANAGE_WORKSTREAM_INITIATIVES) and (
        _user_leads_initiative_workstream(client, user, row)
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_view_portfolio(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_VIEW_PORTFOLIO):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Portfolio access requires an operating-model portfolio role",
        )


def assert_can_manage_financial_configuration(user: CurrentUser) -> None:
    if not (
        has_capability(user.role, CAP_MANAGE_FINANCIALS)
        or has_capability(user.role, CAP_MANAGE_TENANT_SETUP)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_financials(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_FINANCIALS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_validate_benefits(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_VALIDATE_BENEFITS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_benefit_realization(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_BENEFIT_REALIZATION):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_shared_costs(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_SHARED_COSTS):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_governance(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_GOVERNANCE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_program_cadence(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_MANAGE_PROGRAM_CADENCE):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_view_audit_log(user: CurrentUser) -> None:
    if not has_capability(user.role, CAP_VIEW_AUDIT_LOG):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def _assigned_workstream_ids(client: Client, user: CurrentUser) -> set[str]:
    result = (
        client.table("user_workstreams")
        .select("workstream_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("user_id", str(user.id))
        .execute()
    )
    return {str(row["workstream_id"]) for row in result.data or [] if row.get("workstream_id")}


def _initiative_access_row(client: Client, user: CurrentUser, initiative_id: str) -> dict | None:
    result = (
        client.table("initiatives")
        .select("id, owner_id, group_owner_id, workstream_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("id", initiative_id)
        .maybe_single()
        .execute()
    )
    return result.data if result and result.data else None


def _user_owns_initiative(row: dict, user: CurrentUser) -> bool:
    user_id = str(user.id)
    return row.get("owner_id") == user_id or row.get("group_owner_id") == user_id


def _user_leads_initiative_workstream(client: Client, user: CurrentUser, row: dict) -> bool:
    workstream_id = row.get("workstream_id")
    if not workstream_id:
        return False
    return str(workstream_id) in _assigned_workstream_ids(client, user)


def assert_can_manage_initiative_execution(
    client: Client,
    user: CurrentUser,
    initiative_id: str,
) -> None:
    if has_capability(user.role, CAP_MANAGE_EXECUTION_EVIDENCE):
        return
    row = _initiative_access_row(client, user, initiative_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    if has_capability(user.role, CAP_MANAGE_ASSIGNED_EXECUTION_EVIDENCE) and _user_owns_initiative(
        row, user
    ):
        return
    if has_capability(user.role, CAP_MANAGE_WORKSTREAM_EXECUTION_EVIDENCE) and (
        _user_leads_initiative_workstream(client, user, row)
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_milestone_execution(
    client: Client,
    user: CurrentUser,
    milestone_id: str,
) -> None:
    result = (
        client.table("milestones")
        .select("initiative_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("id", milestone_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    assert_can_manage_initiative_execution(client, user, result.data["initiative_id"])


def assert_can_manage_initiative_financials(
    client: Client,
    user: CurrentUser,
    initiative_id: str,
) -> None:
    if has_capability(user.role, CAP_MANAGE_FINANCIALS):
        return
    row = _initiative_access_row(client, user, initiative_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")
    if has_capability(user.role, CAP_MANAGE_ASSIGNED_FINANCIALS) and _user_owns_initiative(
        row, user
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_view_meeting(
    client: Client,
    user: CurrentUser,
    meeting_id: str,
) -> None:
    if can_view_all_initiatives(user.role):
        return

    links = (
        client.table("meeting_initiatives")
        .select("initiative_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("meeting_id", meeting_id)
        .execute()
    )
    if not links.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")
    for link in links.data:
        try:
            assert_can_view_initiative(client, user, link["initiative_id"])
            return
        except HTTPException:
            continue
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")


def assert_can_view_session(
    client: Client,
    user: CurrentUser,
    session_id: str,
) -> None:
    if can_view_all_initiatives(user.role):
        return
    result = (
        client.table("meeting_sessions")
        .select("meeting_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("id", session_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    assert_can_view_meeting(client, user, result.data["meeting_id"])


def assert_can_view_initiative(
    client: Client,
    user: CurrentUser,
    initiative_id: str,
) -> None:
    if can_view_all_initiatives(user.role):
        return

    row = _initiative_access_row(client, user, initiative_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")

    if _user_owns_initiative(row, user):
        return

    if has_capability(user.role, CAP_MANAGE_WORKSTREAM_INITIATIVES) and (
        _user_leads_initiative_workstream(client, user, row)
    ):
        return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")


def assert_can_view_milestone(
    client: Client,
    user: CurrentUser,
    milestone_id: str,
) -> None:
    if can_view_all_initiatives(user.role):
        return

    result = (
        client.table("milestones")
        .select("id, initiative_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("id", milestone_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Milestone not found")
    assert_can_view_initiative(client, user, result.data["initiative_id"])


def initiative_owner_filter(user: CurrentUser) -> UUID | None:
    if user.role == ROLE_INITIATIVE_OWNER:
        return user.id
    return None


def workstream_lead_filter(client: Client, user: CurrentUser) -> list[str] | None:
    if user.role != ROLE_WORKSTREAM_LEAD:
        return None
    return sorted(_assigned_workstream_ids(client, user))
