from typing import Annotated

from fastapi import APIRouter, Depends
from supabase import Client

from app.core.auth import CurrentUser, get_current_user, require_role
from app.core.database import get_supabase_request_client
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
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, object]:
    """Create a new business unit."""
    return svc.create_business_unit(body)


@router.put("/{bu_id}")
async def update_business_unit(
    bu_id: str,
    body: dict[str, object],
    svc: Annotated[BusinessUnitService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> dict[str, object]:
    """Update an existing business unit."""
    return svc.update_business_unit(bu_id, body)


@router.delete("/{bu_id}", status_code=204)
async def delete_business_unit(
    bu_id: str,
    svc: Annotated[BusinessUnitService, Depends(_svc)],
    _current_user: Annotated[CurrentUser, Depends(require_role("transformation_office"))],
) -> None:
    """Delete a business unit."""
    svc.delete_business_unit(bu_id)
    return None
