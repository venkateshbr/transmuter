"""Scheduled status-update compliance nudges."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import procrastinate
from procrastinate.contrib.aiopg import AiopgConnector

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.core.observability import record_worker_job, start_worker_timer
from app.services.status_update import StatusUpdateService

app = procrastinate.App(
    connector=AiopgConnector(dsn=settings.database_url),
    import_paths=["app.jobs.status_nudges"],
)


def _tenant_ids() -> list[UUID]:
    result = get_supabase_admin().table("organizations").select("id").execute()
    return [UUID(row["id"]) for row in result.data or []]


@app.periodic(cron="0 9 * * *", periodic_id="daily-status-compliance-nudges")
@app.task(name="status_nudges.nudge_non_compliant", queue="notifications")
def nudge_non_compliant_initiatives() -> dict[str, Any]:
    """Queue daily nudges for overdue/nuclear initiatives across tenants."""
    started_at = start_worker_timer()
    totals = {"tenants": 0, "nudges": 0, "sent": 0, "queued": 0, "failed": 0}
    try:
        for tenant_id in _tenant_ids():
            totals["tenants"] += 1
            service = StatusUpdateService(get_supabase_admin(), tenant_id, None)
            responses = service.nudge_non_compliant_initiatives()
            totals["nudges"] += len(responses)
            for response in responses:
                totals[response.delivery_status] += 1
        record_worker_job(
            "notifications", "status_nudges.nudge_non_compliant", "succeeded", started_at
        )
        return totals
    except Exception:
        record_worker_job(
            "notifications", "status_nudges.nudge_non_compliant", "failed", started_at
        )
        raise
