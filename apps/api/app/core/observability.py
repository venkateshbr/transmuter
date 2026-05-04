from typing import Any, Protocol, TypeVar, runtime_checkable
from langfuse import Langfuse
from app.core.config import settings

@runtime_checkable
class Traceable(Protocol):
    def flush(self) -> None: ...

_langfuse_client: Langfuse | None = None

def get_langfuse() -> Langfuse | None:
    global _langfuse_client
    if _langfuse_client is None:
        if settings.langfuse_public_key and settings.langfuse_secret_key:
            _langfuse_client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
    return _langfuse_client

def start_trace(name: str, user_id: str | None = None, tags: list[str] | None = None) -> Any:
    client = get_langfuse()
    if not client:
        return None
    return client.trace(name=name, user_id=user_id, tags=tags)
