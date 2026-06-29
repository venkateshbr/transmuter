from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from supabase import create_client

from app.core.config import settings
from app.core.database import get_supabase_admin

bearer = HTTPBearer()


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
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None

    user_id = payload.get("sub")
    tenant_id = payload.get("tenant_id")
    role = payload.get("role")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

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
    return _current_user_from_user_row(user_row.data, path)


def _current_user_from_supabase_token(token: str, path: str) -> CurrentUser:
    try:
        anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
        auth_user = anon_client.auth.get_user(token).user
        if not auth_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        email = (auth_user.email or "").lower()
        if _is_platform_admin_auth_user(auth_user, email):
            return CurrentUser(
                id=UUID(str(auth_user.id)),
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                role="platform_admin",
                status="active",
                must_change_password=False,
            )

        user_row = (
            get_supabase_admin()
            .table("users")
            .select("id, tenant_id, role, status, must_change_password")
            .eq("id", str(auth_user.id))
            .maybe_single()
            .execute()
        )
        if not user_row.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account not found in platform",
            )
        return _current_user_from_user_row(user_row.data, path)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _platform_admin_emails() -> set[str]:
    return {
        item.strip().lower() for item in settings.platform_admin_emails.split(",") if item.strip()
    }


def _auth_metadata(user: Any, key: str) -> dict[str, Any]:
    value = getattr(user, key, None) or {}
    return value if isinstance(value, dict) else {}


def _is_platform_admin_auth_user(user: Any, email: str | None) -> bool:
    if (email or "").lower() not in _platform_admin_emails():
        return False
    app_metadata = _auth_metadata(user, "app_metadata")
    return (
        app_metadata.get("role") == "platform_admin" or app_metadata.get("platform_admin") is True
    )


def _current_user_from_user_row(row: dict[str, Any], path: str) -> CurrentUser:
    if row["status"] == "deactivated":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    if row["status"] == "ghost":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not active",
        )
    must_change_password = bool(row.get("must_change_password"))
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
