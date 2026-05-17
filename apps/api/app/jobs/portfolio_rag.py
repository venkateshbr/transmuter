"""Portfolio RAG rebuild jobs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import procrastinate
from procrastinate.contrib.aiopg import AiopgConnector

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.services.portfolio_rag import PortfolioRAGService

app = procrastinate.App(
    connector=AiopgConnector(dsn=settings.database_url),
    import_paths=["app.jobs.portfolio_rag"],
)


@app.task(name="portfolio_rag.rebuild_tenant_index", queue="analytics")
def rebuild_tenant_index(tenant_id: str) -> dict[str, Any]:
    """Rebuild the tenant-scoped portfolio retrieval index."""
    count = PortfolioRAGService(get_supabase_admin(), UUID(tenant_id)).rebuild_index()
    return {"tenant_id": tenant_id, "documents": count}


def enqueue_portfolio_rag_rebuild(tenant_id: UUID) -> None:
    """Queue a best-effort portfolio index rebuild after source data changes."""
    try:
        rebuild_tenant_index.defer(tenant_id=str(tenant_id))
    except Exception:
        PortfolioRAGService(get_supabase_admin(), tenant_id).rebuild_index()
