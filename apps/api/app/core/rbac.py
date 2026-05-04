"""Role based access-control helpers."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.auth import CurrentUser

ROLE_TRANSFORMATION_OFFICE = "transformation_office"
ROLE_INITIATIVE_OWNER = "initiative_owner"
ROLE_VIEWER = "viewer"

VALID_ROLES = {
    ROLE_TRANSFORMATION_OFFICE,
    ROLE_INITIATIVE_OWNER,
    ROLE_VIEWER,
}


def assert_valid_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be transformation_office, initiative_owner, or viewer",
        )


def can_view_all_initiatives(role: str) -> bool:
    return role in {ROLE_TRANSFORMATION_OFFICE, ROLE_VIEWER}


def assert_can_manage_users(user: CurrentUser) -> None:
    if user.role != ROLE_TRANSFORMATION_OFFICE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_manage_initiatives(user: CurrentUser) -> None:
    if user.role != ROLE_TRANSFORMATION_OFFICE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def assert_can_view_portfolio(user: CurrentUser) -> None:
    if not can_view_all_initiatives(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Portfolio access requires viewer or transformation office")


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

    result = (
        client.table("initiatives")
        .select("id, owner_id, group_owner_id")
        .eq("tenant_id", str(user.tenant_id))
        .eq("id", initiative_id)
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")

    row = result.data
    user_id = str(user.id)
    if row.get("owner_id") == user_id or row.get("group_owner_id") == user_id:
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
