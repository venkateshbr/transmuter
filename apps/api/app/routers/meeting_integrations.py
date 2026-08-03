from __future__ import annotations

from typing import Annotated
from urllib.parse import parse_qsl, urlencode
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from supabase import Client

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.database import get_supabase_admin, get_supabase_request_client
from app.core.rbac import assert_can_manage_tenant_setup, assert_can_view_portfolio
from app.services.meeting_integrations import (
    OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS,
    OAUTH_BINDING_COOKIE_PATH,
    OAUTH_MAX_CODE_LENGTH,
    MeetingIntegrationService,
    OAuthCallbackForm,
    OAuthCallbackResult,
    OAuthCallbackTransport,
    oauth_binding_cookie_name,
    parse_oauth_state,
)

router = APIRouter(prefix="/meeting-integrations", tags=["meeting-integrations"])

OAUTH_CALLBACK_MAX_BODY_BYTES = 16_384
OAUTH_CALLBACK_MAX_FIELDS = 20
OAUTH_CALLBACK_ALLOWED_FIELDS = frozenset(
    {"state", "code", "error", "error_description", "error_uri", "session_state"}
)
OAUTH_CALLBACK_REASON_CODES = frozenset(
    {
        "authorization_cancelled",
        "configuration_error",
        "connection_failed",
        "consent_invalid",
        "invalid_callback",
        "provider_error",
    }
)


class OAuthStartResponse(BaseModel):
    authorization_url: str
    configured: bool
    detail: str | None = None


@router.get("")
async def list_meeting_integrations(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    client: Annotated[Client, Depends(get_supabase_request_client)],
) -> dict[str, object]:
    assert_can_view_portfolio(current_user)
    return MeetingIntegrationService(client, current_user.tenant_id).list_integrations()


@router.post("/microsoft/oauth/start", response_model=OAuthStartResponse)
async def start_microsoft_oauth(
    response: Response,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> OAuthStartResponse:
    assert_can_manage_tenant_setup(current_user)
    result = MeetingIntegrationService(get_supabase_admin(), current_user.tenant_id).start_oauth(
        current_user
    )
    if result.cookie_name and result.cookie_value:
        _set_oauth_binding_cookie(response, result.cookie_name, result.cookie_value)
    return OAuthStartResponse(
        authorization_url=result.authorization_url,
        configured=result.configured,
        detail=result.detail,
    )


@router.post("/microsoft/oauth/callback")
async def microsoft_oauth_callback(request: Request) -> RedirectResponse:
    cookie_names_to_clear: list[str] = []
    try:
        form = await _parse_oauth_callback_form(request)
        cookie_name = oauth_binding_cookie_name(form.state)
        cookie_names_to_clear = [cookie_name]
        browser_binding = _extract_oauth_binding_cookie(request, cookie_name)
        tenant_id, _ = parse_oauth_state(form.state)
        transport = _oauth_callback_transport(request)
        result = MeetingIntegrationService(get_supabase_admin(), tenant_id).complete_callback(
            form, transport, browser_binding
        )
    except ValueError:
        result = OAuthCallbackResult("failed", "invalid_callback")

    response = _oauth_redirect(result)
    for cookie_name in cookie_names_to_clear:
        _clear_oauth_binding_cookie(response, cookie_name)
    return response


@router.delete("/microsoft/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_microsoft_graph(
    connection_id: UUID,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> None:
    assert_can_manage_tenant_setup(current_user)
    disconnected = MeetingIntegrationService(
        get_supabase_admin(), current_user.tenant_id
    ).disconnect(current_user, connection_id)
    if not disconnected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")
    return None


async def _parse_oauth_callback_form(request: Request) -> OAuthCallbackForm:
    if request.url.query:
        raise ValueError("OAuth callback query parameters are not supported")

    content_type_values = request.headers.getlist("content-type")
    if len(content_type_values) != 1:
        raise ValueError("OAuth callback content type is invalid")
    content_type_parts = [part.strip().lower() for part in content_type_values[0].split(";")]
    if content_type_parts[0] != "application/x-www-form-urlencoded":
        raise ValueError("OAuth callback content type is invalid")
    if any(part not in {"charset=utf-8", "charset=us-ascii"} for part in content_type_parts[1:]):
        raise ValueError("OAuth callback content type is invalid")

    content_length_values = request.headers.getlist("content-length")
    if len(content_length_values) > 1:
        raise ValueError("OAuth callback content length is invalid")
    if content_length_values:
        try:
            content_length = int(content_length_values[0])
        except ValueError:
            raise ValueError("OAuth callback content length is invalid") from None
        if content_length < 1 or content_length > OAUTH_CALLBACK_MAX_BODY_BYTES:
            raise ValueError("OAuth callback body is invalid")

    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > OAUTH_CALLBACK_MAX_BODY_BYTES:
            raise ValueError("OAuth callback body is invalid")
        body.extend(chunk)
    if not body:
        raise ValueError("OAuth callback body is invalid")
    if content_length_values and len(body) != content_length:
        raise ValueError("OAuth callback content length is invalid")
    try:
        encoded = bytes(body).decode("ascii")
        pairs = parse_qsl(
            encoded,
            keep_blank_values=True,
            strict_parsing=True,
            encoding="utf-8",
            errors="strict",
            max_num_fields=OAUTH_CALLBACK_MAX_FIELDS,
        )
    except (UnicodeDecodeError, UnicodeError, ValueError):
        raise ValueError("OAuth callback body is invalid") from None

    fields: dict[str, str] = {}
    for key, value in pairs:
        if key not in OAUTH_CALLBACK_ALLOWED_FIELDS or key in fields:
            raise ValueError("OAuth callback fields are invalid")
        if len(key) > 64 or len(value) > OAUTH_MAX_CODE_LENGTH:
            raise ValueError("OAuth callback field is invalid")
        fields[key] = value

    state_value = fields.get("state")
    code_value = fields.get("code")
    error_value = fields.get("error")
    if (
        not state_value
        or (bool(code_value) == bool(error_value))
        or (error_value is not None and len(error_value) > 128)
    ):
        raise ValueError("OAuth callback fields are invalid")
    return OAuthCallbackForm(state=state_value, code=code_value, error=error_value)


def _oauth_callback_transport(request: Request) -> OAuthCallbackTransport:
    return OAuthCallbackTransport(
        origin=_single_header(request, "origin"),
        host=_forwarded_or_direct_header(request, "x-forwarded-host", "host"),
        scheme=_forwarded_or_request_scheme(request),
        fetch_site=_optional_single_header(request, "sec-fetch-site"),
        fetch_mode=_optional_single_header(request, "sec-fetch-mode"),
        fetch_dest=_optional_single_header(request, "sec-fetch-dest"),
    )


def _single_header(request: Request, name: str) -> str | None:
    values = request.headers.getlist(name)
    if len(values) != 1 or "," in values[0]:
        return None
    return values[0]


def _optional_single_header(request: Request, name: str) -> str | None:
    values = request.headers.getlist(name)
    if not values:
        return None
    if len(values) != 1 or "," in values[0]:
        return "invalid"
    return values[0]


def _forwarded_or_direct_header(
    request: Request,
    forwarded_name: str,
    direct_name: str,
) -> str | None:
    forwarded = request.headers.getlist(forwarded_name)
    if forwarded:
        if len(forwarded) != 1 or "," in forwarded[0]:
            return None
        return forwarded[0]
    return _single_header(request, direct_name)


def _forwarded_or_request_scheme(request: Request) -> str | None:
    forwarded = request.headers.getlist("x-forwarded-proto")
    if forwarded:
        if len(forwarded) != 1 or "," in forwarded[0]:
            return None
        return forwarded[0]
    return request.url.scheme


def _extract_oauth_binding_cookie(request: Request, cookie_name: str) -> str | None:
    matches: list[str] = []
    for header in request.headers.getlist("cookie"):
        for item in header.split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == cookie_name:
                matches.append(value)
    if len(matches) != 1:
        return None
    return matches[0]


def _set_oauth_binding_cookie(response: Response, cookie_name: str, cookie_value: str) -> None:
    response.set_cookie(
        key=cookie_name,
        value=cookie_value,
        max_age=OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS,
        expires=OAUTH_BINDING_COOKIE_MAX_AGE_SECONDS,
        path=OAUTH_BINDING_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="none",
    )


def _clear_oauth_binding_cookie(response: Response, cookie_name: str) -> None:
    response.delete_cookie(
        key=cookie_name,
        path=OAUTH_BINDING_COOKIE_PATH,
        secure=True,
        httponly=True,
        samesite="none",
    )


def _oauth_redirect(result: OAuthCallbackResult) -> RedirectResponse:
    reason = result.reason if result.reason in OAUTH_CALLBACK_REASON_CODES else None
    params = {"microsoft_graph": result.status}
    if reason:
        params["reason"] = reason
    response = RedirectResponse(
        f"{settings.app_public_url.rstrip('/')}/admin?{urlencode(params)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
