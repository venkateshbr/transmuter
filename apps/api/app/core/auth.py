from typing import Annotated
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

    legacy_user = _current_user_from_app_token(token)
    if legacy_user:
        return legacy_user

    return _current_user_from_supabase_token(token, request.url.path)


def _current_user_from_app_token(token: str) -> CurrentUser | None:
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

    return CurrentUser(
        id=UUID(user_id),
        tenant_id=UUID(tenant_id),
        role=role or "viewer",
        status="active",
        must_change_password=False,
    )


def _current_user_from_supabase_token(token: str, path: str) -> CurrentUser:
    try:
        anon_client = create_client(settings.supabase_url, settings.supabase_anon_key)
        auth_user = anon_client.auth.get_user(token).user
        if not auth_user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        email = (auth_user.email or "").lower()
        if email in _platform_admin_emails():
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
        if user_row.data["status"] == "deactivated":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
        if user_row.data["status"] == "ghost":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is not active",
            )
        must_change_password = bool(user_row.data.get("must_change_password"))
        if must_change_password and path not in {"/auth/me", "/auth/change-password"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required",
            )
        return CurrentUser(
            id=UUID(user_row.data["id"]),
            tenant_id=UUID(user_row.data["tenant_id"]),
            role=user_row.data["role"],
            status=user_row.data["status"],
            must_change_password=must_change_password,
        )
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


def require_role(*roles: str):
    """Factory: returns a dependency that enforces one of the given roles."""

    async def _check(user: Annotated[CurrentUser, Depends(get_current_user)]) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return _check


# Convenience role dependencies
RequireAdmin = Depends(require_role("transformation_office"))
RequireOwnerOrAdmin = Depends(require_role("transformation_office", "initiative_owner"))
AnyRole = Depends(get_current_user)
