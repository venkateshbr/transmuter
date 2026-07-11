from collections.abc import Mapping
from typing import Annotated, Any, NoReturn
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from joserfc.errors import JoseError
from pydantic import BaseModel
from supabase import create_client

from app.core.auth_metadata import AUTHORIZATION_SCOPES, authorization_metadata_key
from app.core.config import settings
from app.core.database import get_supabase_admin, get_supabase_schema
from app.core.jwt_tokens import decode_token

bearer = HTTPBearer()
CLAIM_SYNC_ERROR = "Authentication claims are out of sync. Contact an administrator."


class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    role: str
    status: str = "active"
    must_change_password: bool = False


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
    request: Request,
) -> CurrentUser:
    token = credentials.credentials

    legacy_user = _current_user_from_app_token(token, request.url.path)
    if legacy_user:
        return legacy_user

    return _current_user_from_supabase_token(token, request.url.path)


def _current_user_from_app_token(token: str, path: str) -> CurrentUser | None:
    try:
        payload = decode_token(token, settings.jwt_secret, settings.jwt_algorithm)
    except JoseError:
        return None

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")
    app_role = payload.get("app_role")

    if not user_id or not tenant_id or not isinstance(role, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )
    if app_role != role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CLAIM_SYNC_ERROR,
        )
    try:
        canonical_user_id = str(UUID(str(user_id)))
        canonical_tenant_id = str(UUID(str(tenant_id)))
    except (TypeError, ValueError):
        _raise_claim_sync_error()
    if str(user_id) != canonical_user_id or str(tenant_id) != canonical_tenant_id:
        _raise_claim_sync_error()

    if role == "platform_admin" and tenant_id == "00000000-0000-0000-0000-000000000000":
        return CurrentUser(
            id=UUID(user_id),
            tenant_id=UUID(tenant_id),
            role="platform_admin",
            status="active",
            must_change_password=False,
        )

    user_row = (
        get_supabase_admin()
        .table("users")
        .select("id, tenant_id, role, status, must_change_password")
        .eq("id", user_id)
        .eq("tenant_id", tenant_id)
        .maybe_single()
        .execute()
    )
    if not user_row or not user_row.data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account not found in platform",
        )
    if str(user_row.data.get("role")) != str(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=CLAIM_SYNC_ERROR,
        )
    return _current_user_from_user_row(user_row.data, path)


def _current_user_from_supabase_token(token: str, path: str) -> CurrentUser:
    try:
        anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
        claims = get_verified_supabase_claims(anon_client, token)

        if is_platform_admin_claims(claims):
            return CurrentUser(
                id=UUID(str(claims["sub"])),
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                role="platform_admin",
                status="active",
                must_change_password=False,
            )

        user_row = (
            get_supabase_admin()
            .table("users")
            .select("id, tenant_id, role, status, must_change_password")
            .eq("id", str(claims.get("sub") or ""))
            .maybe_single()
            .execute()
        )
        if not user_row.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account not found in platform",
            )
        assert_supabase_claims_match_user(claims, user_row.data)
        return _current_user_from_user_row(user_row.data, path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _platform_admin_emails() -> set[str]:
    return {
        item.strip().lower() for item in settings.platform_admin_emails.split(",") if item.strip()
    }


def get_verified_supabase_claims(client: Any, token: str) -> dict[str, Any]:
    """Return the exact, verified Supabase access-token claims snapshot."""
    try:
        response = client.auth.get_claims(token)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    claims = (
        response.get("claims")
        if isinstance(response, Mapping)
        else getattr(response, "claims", None)
    )
    if not isinstance(claims, Mapping):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid JWT",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return dict(claims)


def is_platform_admin_claims(claims: dict[str, Any]) -> bool:
    email = str(claims.get("email") or "").lower()
    if email not in _platform_admin_emails():
        return False
    app_metadata = claims.get("app_metadata") or {}
    if not isinstance(app_metadata, dict):
        return False
    if "tenant_id" in app_metadata or any(
        authorization_metadata_key(scope) in app_metadata for scope in AUTHORIZATION_SCOPES
    ):
        return False
    return (
        app_metadata.get("role") == "platform_admin" and app_metadata.get("platform_admin") is True
    )


def assert_supabase_claims_match_user(
    claims: dict[str, Any],
    user_row: dict[str, Any],
    authorization_scope: str | None = None,
) -> None:
    """Fail closed unless immutable claims match the canonical platform user."""
    app_metadata = claims.get("app_metadata") or {}
    if not isinstance(app_metadata, dict):
        _raise_claim_sync_error()
    if any(key in app_metadata for key in ("tenant_id", "role", "platform_admin")):
        _raise_claim_sync_error()
    scope = authorization_scope or get_supabase_schema()
    authorization = app_metadata.get(authorization_metadata_key(scope)) or {}
    if not isinstance(authorization, dict):
        _raise_claim_sync_error()
    try:
        claim_user_id = UUID(str(claims.get("sub") or ""))
        claim_tenant_value = authorization.get("tenant_id")
        if not isinstance(claim_tenant_value, str):
            _raise_claim_sync_error()
        UUID(claim_tenant_value)
        canonical_user_id = UUID(str(user_row.get("id") or ""))
        canonical_tenant_value = str(UUID(str(user_row.get("tenant_id") or "")))
    except (TypeError, ValueError):
        _raise_claim_sync_error()

    claim_role = authorization.get("role")
    canonical_role = user_row.get("role")
    if (
        claim_user_id != canonical_user_id
        or claim_tenant_value != canonical_tenant_value
        or not isinstance(claim_role, str)
        or claim_role != canonical_role
    ):
        _raise_claim_sync_error()


def _raise_claim_sync_error() -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=CLAIM_SYNC_ERROR,
    )


def _current_user_from_user_row(row: dict[str, Any], path: str) -> CurrentUser:
    if row["status"] == "deactivated":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    if row["status"] == "ghost":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    must_change_password = bool(row.get("must_change_password")) or row["status"] == "pending"
    if must_change_password and path not in {"/auth/me", "/auth/change-password"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Password change required",
        )
    return CurrentUser(
        id=UUID(row["id"]),
        tenant_id=UUID(row["tenant_id"]),
        role=row["role"],
        status=row["status"],
        must_change_password=must_change_password,
    )


def require_role(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""

    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _check


AnyRole = Depends(get_current_user)
