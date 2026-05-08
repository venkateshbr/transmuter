from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_admin
from app.core.rbac import assert_can_manage_initiatives, assert_can_view_initiative

router = APIRouter(tags=["initiative-team"])


class TeamMemberBase(BaseModel):
    user_id: UUID
    role: str


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberResponse(TeamMemberBase):
    id: UUID
    display_name: str | None = None
    email: str | None = None


def _assert_initiative_access(client, initiative_id: UUID, tenant_id: str) -> None:
    initiative = (
        client.table("initiatives")
        .select("id")
        .eq("id", str(initiative_id))
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    if not initiative or not initiative.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Initiative not found")


def _assert_user_access(client, user_id: UUID, tenant_id: str) -> None:
    user = (
        client.table("users")
        .select("id")
        .eq("id", str(user_id))
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    if not user or not user.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")


@router.get("/initiatives/{initiative_id}/team")
async def get_initiative_team(
    initiative_id: UUID, current_user: Annotated[CurrentUser, Depends(get_current_user)]
):
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    assert_can_view_initiative(client, current_user, str(initiative_id))

    res = (
        client.table("initiative_team")
        .select("*, users(display_name, email)")
        .eq("initiative_id", str(initiative_id))
        .eq("tenant_id", tid)
        .execute()
    )

    members = []
    for row in res.data:
        user = row.get("users") or {}
        members.append(
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "role": row["role"],
                "display_name": user.get("display_name"),
                "email": user.get("email"),
            }
        )

    return {"data": members}


@router.post("/initiatives/{initiative_id}/team")
async def add_team_member(
    initiative_id: UUID,
    data: TeamMemberCreate,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    assert_can_manage_initiatives(current_user)
    _assert_initiative_access(client, initiative_id, tid)
    _assert_user_access(client, data.user_id, tid)

    res = (
        client.table("initiative_team")
        .insert(
            {
                "tenant_id": tid,
                "initiative_id": str(initiative_id),
                "user_id": str(data.user_id),
                "role": data.role,
            }
        )
        .execute()
    )

    if not res.data:
        raise HTTPException(status_code=400, detail="Failed to add team member")

    return {"data": res.data[0]}


@router.delete("/initiatives/{initiative_id}/team/{member_id}")
async def remove_team_member(
    initiative_id: UUID,
    member_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
):
    client = get_supabase_admin()
    tid = str(current_user.tenant_id)
    assert_can_manage_initiatives(current_user)
    _assert_initiative_access(client, initiative_id, tid)

    deleted = (
        client.table("initiative_team")
        .delete()
        .eq("id", str(member_id))
        .eq("initiative_id", str(initiative_id))
        .eq("tenant_id", tid)
        .execute()
    )
    if not deleted.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    return {"status": "success"}
