from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.database import get_supabase_request_client
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
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, object]:
    """Create a new workstream."""
    return svc.create_workstream(body)


@router.put("/{workstream_id}")
async def update_workstream(
    workstream_id: str,
    body: dict[str, object],
    svc: Annotated[WorkstreamService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, object]:
    """Update an existing workstream."""
    return svc.update_workstream(workstream_id, body)


@router.delete("/{workstream_id}", status_code=204)
async def delete_workstream(
    workstream_id: str,
    svc: Annotated[WorkstreamService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> None:
    """Delete a workstream."""
    svc.delete_workstream(workstream_id)
    return None
