from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings

bearer = HTTPBearer()


class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    role: str
    email: str


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> CurrentUser:
    token = credentials.credentials

    try:
        # Decode and verify using our own secret
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role")
        email = payload.get("email")

        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        return CurrentUser(
            id=UUID(user_id),
            tenant_id=UUID(tenant_id),
            role=role or "viewer",
            email=email or "",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth failure: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
