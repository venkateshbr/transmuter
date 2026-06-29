"""People router — directory, profile, invites, and pressure."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import assert_can_manage_users
from app.domain.people import (
    InviteCreate,
    UserCreate,
    UserTemporaryPassword,
    UserUpdate,
    WorkstreamAssignment,
)
from app.services.people import PeopleService

router = APIRouter(tags=["people"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> PeopleService:
    return PeopleService(get_supabase_admin(), current_user.tenant_id)


@router.get("/people")
@router.get("/users")
async def list_users(
    svc: Annotated[PeopleService, Depends(_svc)],
    role: str | None = None,
    status: str | None = Query(default=None, alias="status"),
    search: str | None = None,
) -> dict[str, Any]:
    return svc.list_users(role=role, status_filter=status, search=search)


@router.get("/users/{user_id}")
async def get_user_profile(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
) -> dict[str, Any]:
    return svc.get_profile(user_id)


@router.post("/users", status_code=201)
async def create_user(
    body: UserCreate,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.create_user(body)


@router.put("/users/{user_id}")
async def update_user_profile(
    user_id: str,
    body: UserUpdate,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.update_profile(user_id, body)


@router.post("/users/{user_id}/ghost")
async def ghost_user(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.ghost_user(user_id)


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.deactivate_user(user_id)


@router.post("/users/{user_id}/password-reset-link")
async def send_password_reset_link(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.send_password_setup_link(user_id, created_by_id=str(current_user.id))


@router.post("/users/{user_id}/temporary-password")
async def set_temporary_password(
    user_id: str,
    body: UserTemporaryPassword,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.set_temporary_password(user_id, body)


@router.get("/users/{user_id}/pressure")
async def get_user_pressure(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
) -> dict[str, Any]:
    return svc.get_pressure(user_id)


@router.put("/users/{user_id}/workstreams")
async def assign_user_workstreams(
    user_id: str,
    body: WorkstreamAssignment,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.assign_workstreams(user_id, body)


@router.post("/invites", status_code=201)
async def create_invite(
    body: InviteCreate,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.invite_user(body, created_by_id=str(current_user.id))


@router.get("/invites")
async def list_invites(
    svc: Annotated[PeopleService, Depends(_svc)],
) -> dict[str, Any]:
    return svc.list_invites()


@router.post("/invites/{invite_id}/resend")
async def resend_invite(
    invite_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.resend_invite(invite_id)


@router.post("/invites/{invite_id}/revoke")
async def revoke_invite(
    invite_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    assert_can_manage_users(current_user)
    return svc.revoke_invite(invite_id)
