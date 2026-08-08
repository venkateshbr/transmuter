"""Authenticated access to the maintained product guide library."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import CurrentUser, get_current_user
from app.services.platform_guides import get_platform_guide, list_platform_guides

router = APIRouter(prefix="/guides", tags=["guides"])


@router.get("")
async def guides(
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return {"items": list_platform_guides()}


@router.get("/{slug}")
async def guide(
    slug: str,
    _current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    item = get_platform_guide(slug)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Guide not found")
    return item
