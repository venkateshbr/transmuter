from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from urllib.parse import quote, urlencode
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.crypto import encrypt_secret
from app.core.database import get_supabase_admin, get_supabase_request_client
from app.core.rbac import assert_can_manage_initiatives, assert_can_view_portfolio
from app.repositories.meeting import MeetingRepository

router = APIRouter(prefix="/meeting-integrations", tags=["meeting-integrations"])


class OAuthStartResponse(BaseModel):
    authorization_url: str
    configured: bool
    detail: str | None = None


@router.get("")
async def list_meeting_integrations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict:
    assert_can_view_portfolio(current_user)
    repo = MeetingRepository(client, current_user.tenant_id)
    connections = repo.list_integration_connections()
    return {
        "items": connections,
        "providers": [
            {
                "provider": "microsoft_graph",
                "configured": bool(
                    settings.microsoft_graph_client_id
                    and settings.microsoft_graph_client_secret
                    and settings.encryption_key
                ),
            },
            {
                "provider": "recall_ai",
                "enabled": settings.recall_meeting_bot_enabled,
            },
            {
                "provider": "fireflies",
                "enabled": settings.fireflies_meeting_bot_enabled,
            },
        ],
    }


@router.post("/microsoft/oauth/start", response_model=OAuthStartResponse)
async def start_microsoft_oauth(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> OAuthStartResponse:
    assert_can_manage_initiatives(current_user)
    missing = [
        name
        for name, value in (
            ("MICROSOFT_GRAPH_CLIENT_ID", settings.microsoft_graph_client_id),
            ("MICROSOFT_GRAPH_CLIENT_SECRET", settings.microsoft_graph_client_secret),
            ("ENCRYPTION_KEY", settings.encryption_key),
        )
        if not value
    ]
    if missing:
        return OAuthStartResponse(
            authorization_url="",
            configured=False,
            detail=f"Missing required setting(s): {', '.join(missing)}.",
        )

    state = jwt.encode(
        {
            "purpose": "microsoft_graph_oauth",
            "tenant_id": str(current_user.tenant_id),
            "user_id": str(current_user.id),
            "exp": datetime.now(UTC) + timedelta(minutes=10),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    params = {
        "client_id": settings.microsoft_graph_client_id,
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "response_mode": "query",
        "scope": settings.microsoft_graph_scopes,
        "state": state,
        "prompt": "select_account",
    }
    return OAuthStartResponse(
        authorization_url=f"{_authorize_url()}?{urlencode(params)}",
        configured=True,
    )


@router.get("/microsoft/oauth/callback")
async def microsoft_oauth_callback(
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
    error_description: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    if error:
        return _oauth_redirect("failed", error_description or error)
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Microsoft OAuth callback requires code and state.",
        )
    payload = _decode_oauth_state(state)
    tenant_id = UUID(payload["tenant_id"])

    token_response = httpx.post(
        _token_url(),
        data={
            "client_id": settings.microsoft_graph_client_id,
            "client_secret": settings.microsoft_graph_client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
            "scope": settings.microsoft_graph_scopes,
        },
        timeout=10,
    )
    token_response.raise_for_status()
    token_body = token_response.json()
    access_token = token_body["access_token"]
    profile = _graph_me(access_token)
    repo = MeetingRepository(get_supabase_admin(), tenant_id)
    expires_in = int(token_body.get("expires_in") or 3600)
    organizer_email = profile.get("mail") or profile.get("userPrincipalName")
    repo.upsert_integration_connection(
        "microsoft_graph",
        {
            "organizer_email": organizer_email,
            "external_account_id": profile.get("id"),
            "access_token_encrypted": encrypt_secret(access_token),
            "refresh_token_encrypted": encrypt_secret(token_body.get("refresh_token")),
            "token_expires_at": (datetime.now(UTC) + timedelta(seconds=expires_in)).isoformat(),
            "scopes": settings.microsoft_graph_scopes.split(),
            "sync_status": "connected",
            "sync_error": None,
            "last_synced_at": datetime.now(UTC).isoformat(),
        },
    )
    return _oauth_redirect("connected", None)


def _decode_oauth_state(state: str) -> dict:
    try:
        payload = jwt.decode(state, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Microsoft OAuth state.",
        ) from exc
    if payload.get("purpose") != "microsoft_graph_oauth":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Microsoft OAuth state purpose.",
        )
    return payload


def _graph_me(access_token: str) -> dict:
    response = httpx.get(
        "https://graph.microsoft.com/v1.0/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _oauth_redirect(status_value: str, detail: str | None) -> RedirectResponse:
    params = {"microsoft_graph": status_value}
    if detail:
        params["detail"] = detail[:200]
    return RedirectResponse(f"{settings.app_public_url.rstrip('/')}/meetings?{urlencode(params)}")


def _redirect_uri() -> str:
    if settings.microsoft_graph_redirect_uri:
        return settings.microsoft_graph_redirect_uri
    return (
        f"{settings.app_public_url.rstrip('/')}/api/meeting-integrations/microsoft/oauth/callback"
    )


def _authorize_url() -> str:
    tenant = settings.microsoft_graph_tenant_id or "common"
    return f"https://login.microsoftonline.com/{quote(tenant, safe='')}/oauth2/v2.0/authorize"


def _token_url() -> str:
    tenant = settings.microsoft_graph_tenant_id or "common"
    return f"https://login.microsoftonline.com/{quote(tenant, safe='')}/oauth2/v2.0/token"
