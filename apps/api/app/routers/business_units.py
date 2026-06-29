from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.database import get_supabase_request_client
from app.core.rbac import assert_can_manage_tenant_setup
from app.services.business_unit import BusinessUnitService

router = APIRouter(prefix="/business-units", tags=["business-units"])


def _svc(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> BusinessUnitService:
    return BusinessUnitService(client, current_user.tenant_id)


@router.get("")
async def list_business_units(
    svc: Annotated[BusinessUnitService, Depends(_svc)],
) -> dict[str, object]:
    """List all business units for the tenant."""
    return svc.list_business_units()


@router.post("", status_code=201)
async def create_business_unit(
    body: dict[str, object],
    svc: Annotated[BusinessUnitService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    """Create a new business unit."""
    assert_can_manage_tenant_setup(current_user)
    return svc.create_business_unit(body)


@router.put("/{bu_id}")
async def update_business_unit(
    bu_id: str,
    body: dict[str, object],
    svc: Annotated[BusinessUnitService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, object]:
    """Update an existing business unit."""
    assert_can_manage_tenant_setup(current_user)
    return svc.update_business_unit(bu_id, body)


@router.delete("/{bu_id}", status_code=204)
async def delete_business_unit(
    bu_id: str,
    svc: Annotated[BusinessUnitService, Depends(_svc)],
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    """Delete a business unit."""
    assert_can_manage_tenant_setup(current_user)
    svc.delete_business_unit(bu_id)
    return None
