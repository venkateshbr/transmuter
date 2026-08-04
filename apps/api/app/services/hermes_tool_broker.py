"""Allowlisted execution boundary between Hermes MCP and Transmuter services."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from supabase import Client

from app.core.auth import CurrentUser
from app.services.hermes_context import HermesToolContext
from app.services.hermes_read_packs import HermesReadPackService

_FORBIDDEN_AUTHORITY_KEYS = {"tenant_id", "user_id", "role", "current_user"}


class HermesToolBrokerService:
    def __init__(self, client: Client) -> None:
        self.client = client

    def execute(
        self,
        *,
        context: HermesToolContext,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> Any:
        if _contains_authority(arguments):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Tool arguments cannot supply authorization context",
            )
        user = self._canonical_user(context)
        read_packs = HermesReadPackService(self.client, user)
        handlers: dict[str, Callable[[], Any]] = {
            "transmuter.portfolio.overview": read_packs.portfolio_overview,
            "transmuter.portfolio.initiatives": lambda: read_packs.initiatives_read_pack(
                search=_optional_string(arguments.get("search")),
                rag_status=_optional_choice(
                    arguments.get("rag_status"), {"red", "amber", "green", "grey"}
                ),
                stage=_optional_string(arguments.get("stage")),
                limit=_bounded_int(arguments.get("limit"), default=25, maximum=50),
            ),
            "transmuter.governance.read_pack": read_packs.governance_read_pack,
            "transmuter.financials.read_pack": lambda: read_packs.financials_read_pack(
                year=_optional_year(arguments.get("year"))
            ),
            "transmuter.tools.catalog": read_packs.tool_catalog,
        }
        handler = handlers.get(tool_name)
        if handler is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Hermes tool is not available",
            )
        return handler()

    def _canonical_user(self, context: HermesToolContext) -> CurrentUser:
        try:
            response = (
                self.client.table("users")
                .select("id,tenant_id,role,status,must_change_password")
                .eq("id", context.user_id)
                .eq("tenant_id", context.tenant_id)
                .maybe_single()
                .execute()
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hermes authorization source is unavailable",
            ) from exc
        row = response.data if response else None
        if not row or row.get("status") != "active" or row.get("must_change_password"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hermes tool context is no longer authorized",
            )
        try:
            return CurrentUser(
                id=UUID(str(row["id"])),
                tenant_id=UUID(str(row["tenant_id"])),
                role=str(row["role"]),
                status=str(row["status"]),
                must_change_password=bool(row.get("must_change_password")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Hermes tool context is no longer authorized",
            ) from exc


def _contains_authority(value: Any) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).lower() in _FORBIDDEN_AUTHORITY_KEYS or _contains_authority(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_authority(item) for item in value)
    return False


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if len(text) > 200:
        raise HTTPException(status_code=422, detail="Tool string argument is too long")
    return text or None


def _optional_choice(value: object, allowed: set[str]) -> str | None:
    text = _optional_string(value)
    if text is not None and text not in allowed:
        raise HTTPException(status_code=422, detail="Tool choice argument is invalid")
    return text


def _bounded_int(value: object, *, default: int, maximum: int) -> int:
    try:
        parsed = default if value is None else int(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Tool integer argument is invalid") from exc
    if parsed < 1 or parsed > maximum:
        raise HTTPException(status_code=422, detail="Tool integer argument is out of range")
    return parsed


def _optional_year(value: object) -> int | None:
    if value is None:
        return None
    year = _bounded_int(value, default=date.today().year, maximum=2100)
    if year < 2020:
        raise HTTPException(status_code=422, detail="Tool year argument is out of range")
    return year
