"""People router — directory, profile, invites, and pressure."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from supabase import Client

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.database import get_supabase_request_client
from app.domain.people import InviteCreate, UserUpdate, WorkstreamAssignment
from app.services.people import PeopleService

router = APIRouter(tags=["people"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> PeopleService:
    return PeopleService(client, current_user.tenant_id)


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


@router.put("/users/{user_id}")
async def update_user_profile(
    user_id: str,
    body: UserUpdate,
    svc: Annotated[PeopleService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, Any]:
    return svc.update_profile(user_id, body)


@router.post("/users/{user_id}/ghost")
async def ghost_user(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, Any]:
    return svc.ghost_user(user_id)


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    svc: Annotated[PeopleService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, Any]:
    return svc.deactivate_user(user_id)


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
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, Any]:
    return svc.assign_workstreams(user_id, body)


@router.post("/invites", status_code=201)
async def create_invite(
    body: InviteCreate,
    svc: Annotated[PeopleService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, Any]:
    return svc.invite_user(body)


@router.get("/invites")
async def list_invites(
    svc: Annotated[PeopleService, Depends(_svc)],
) -> dict[str, Any]:
    return svc.list_invites()
