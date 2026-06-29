from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import assert_can_manage_tenant_setup
from app.services.workstream import WorkstreamService

router = APIRouter(prefix="/workstreams", tags=["workstreams"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> WorkstreamService:
    return WorkstreamService(client, current_user.tenant_id)


@router.get("")
async def list_workstreams(
    svc: Annotated[WorkstreamService, Depends(_svc)],
) -> dict[str, object]:
    """List all workstreams for the tenant."""
    return svc.list_workstreams()


@router.post("", status_code=201)
async def create_workstream(
    body: dict[str, object],
    svc: Annotated[WorkstreamService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    """Create a new workstream."""
    assert_can_manage_tenant_setup(current_user)
    return svc.create_workstream(body)


@router.put("/{workstream_id}")
async def update_workstream(
    workstream_id: str,
    body: dict[str, object],
    svc: Annotated[WorkstreamService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    """Update an existing workstream."""
    assert_can_manage_tenant_setup(current_user)
    return svc.update_workstream(workstream_id, body)


@router.delete("/{workstream_id}", status_code=204)
async def delete_workstream(
    workstream_id: str,
    svc: Annotated[WorkstreamService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    """Delete a workstream."""
    assert_can_manage_tenant_setup(current_user)
    svc.delete_workstream(workstream_id)
    return None
