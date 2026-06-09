from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, ClientOptions, create_client

from app.core.config import settings

bearer = HTTPBearer()


def get_supabase_schema() -> str:
    return "transmuter" if settings.supabase_target == "local" else "public"


def get_supabase_client_options() -> ClientOptions:
    return ClientOptions(schema=get_supabase_schema())


@lru_cache
def get_supabase_admin() -> Client:
    """Service-role client for admin operations (migrations, background jobs).
    Never expose to user-facing requests — use get_supabase_user() for those.
    """
    return create_client(
        settings.supabase_url,
        settings.supabase_service_key,
        options=get_supabase_client_options(),
    )


def get_supabase_user(user_jwt: str) -> Client:
    """User-scoped client. RLS is enforced automatically via the user's JWT."""
    client = create_client(
        settings.supabase_url,
        settings.supabase_anon_key,
        options=get_supabase_client_options(),
    )
    client.postgrest.auth(user_jwt)
    return client


def get_supabase_request_client(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer)],
) -> Client:
    return get_supabase_user(credentials.credentials)
