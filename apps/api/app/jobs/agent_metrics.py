"""Scheduled agent metric rollups."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

import httpx
import procrastinate
from procrastinate.contrib.aiopg import AiopgConnector

from app.core.config import settings
from app.core.database import get_supabase_admin
from app.services.agent_observability import AgentObservabilityService

CORRECTION_RATE_INCIDENT_THRESHOLD = 10.0
QUALITY_EPIC_ISSUE_NUMBER = int(os.environ.get("TRANSMUTER_AGENT_QUALITY_EPIC", "17"))

app = procrastinate.App(
    connector=AiopgConnector(dsn=settings.database_url),
    import_paths=["app.jobs.agent_metrics"],
)


def _tenant_ids() -> list[UUID]:
    result = get_supabase_admin().table("organizations").select("id").execute()
    return [UUID(row["id"]) for row in result.data or []]


@app.periodic(cron="30 1 * * *", periodic_id="daily-agent-metrics-rollup")
@app.task(name="agent_metrics.rollup_daily", queue="analytics")
def rollup_daily_agent_metrics() -> dict[str, Any]:
    """Roll up yesterday's agent audit/correction records into agent_metrics."""
    metric_date = datetime.now(UTC).date() - timedelta(days=1)
    totals = {"metric_date": metric_date.isoformat(), "tenants": 0, "rows": 0}
    for tenant_id in _tenant_ids():
        totals["tenants"] += 1
        rows = AgentObservabilityService(get_supabase_admin(), tenant_id).rollup_daily_metrics(
            metric_date
        )
        totals["rows"] += len(rows)
    return totals


@app.periodic(cron="0 9 * * MON", periodic_id="weekly-agent-quality-report")
@app.task(name="agent_metrics.weekly_quality_report", queue="analytics")
def weekly_agent_quality_report() -> dict[str, Any]:
    """Post weekly agent correction-rate report and open P3 issues for breaches."""
    start_date = datetime.now(UTC).date() - timedelta(days=7)
    rows = _weekly_quality_rows(start_date)
    breached = [
        row
        for row in rows
        if float(row["correction_rate_pct"]) > CORRECTION_RATE_INCIDENT_THRESHOLD
    ]
    report = _render_quality_report(start_date, rows, breached)
    github_result = _post_github_comment(QUALITY_EPIC_ISSUE_NUMBER, report)
    incident_result = None
    if breached:
        incident_result = _create_quality_incident(start_date, breached)
    return {
        "start_date": start_date.isoformat(),
        "rows": len(rows),
        "breaches": len(breached),
        "github": github_result,
        "incident": incident_result,
    }


def _weekly_quality_rows(start_date: date) -> list[dict[str, Any]]:
    rows_by_agent: dict[str, dict[str, Any]] = {}
    for tenant_id in _tenant_ids():
        service_rows = AgentObservabilityService(
            get_supabase_admin(),
            tenant_id,
        ).weekly_quality_rows(start_date)
        for row in service_rows:
            agent = rows_by_agent.setdefault(
                row["agent_id"],
                {
                    "agent_id": row["agent_id"],
                    "total_runs": 0,
                    "correction_count": 0,
                },
            )
            agent["total_runs"] += int(row["total_runs"])
            agent["correction_count"] += int(row["correction_count"])
    rows = []
    for row in rows_by_agent.values():
        total_runs = row["total_runs"]
        correction_count = row["correction_count"]
        correction_rate_pct = (
            round((correction_count / total_runs) * 100, 1) if total_runs else 0.0
        )
        rows.append({**row, "correction_rate_pct": correction_rate_pct})
    return sorted(rows, key=lambda item: item["correction_rate_pct"], reverse=True)


def _render_quality_report(
    start_date: date,
    rows: list[dict[str, Any]],
    breached: list[dict[str, Any]],
) -> str:
    lines = [
        "## Weekly Agent Quality Report",
        "",
        f"Window start: {start_date.isoformat()}",
        f"Correction threshold: > {CORRECTION_RATE_INCIDENT_THRESHOLD:.1f}%",
        "",
        "| Agent | Runs | Corrections | Correction rate |",
        "| --- | ---: | ---: | ---: |",
    ]
    if rows:
        for row in rows:
            lines.append(
                "| {agent_id} | {total_runs} | {correction_count} | {correction_rate_pct:.1f}% |".format(
                    **row
                )
            )
    else:
        lines.append("| No agent metrics | 0 | 0 | 0.0% |")
    if breached:
        lines.extend(
            [
                "",
                "P3 threshold breached:",
                *[
                    f"- {row['agent_id']}: {row['correction_rate_pct']:.1f}%"
                    for row in breached
                ],
            ]
        )
    else:
        lines.extend(["", "No P3 correction-rate breach detected."])
    return "\n".join(lines)


def _post_github_comment(issue_number: int, body: str) -> dict[str, Any]:
    owner_repo = os.environ.get("TRANSMUTER_GITHUB_REPOSITORY", "venkateshbr/transmuter")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"status": "skipped", "reason": "GITHUB_TOKEN not configured"}
    owner, repo = owner_repo.split("/", 1)
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={"body": body},
        timeout=10,
    )
    response.raise_for_status()
    return {"status": "posted", "url": response.json().get("html_url")}


def _create_quality_incident(
    start_date: date,
    breached: list[dict[str, Any]],
) -> dict[str, Any]:
    owner_repo = os.environ.get("TRANSMUTER_GITHUB_REPOSITORY", "venkateshbr/transmuter")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return {"status": "skipped", "reason": "GITHUB_TOKEN not configured"}
    owner, repo = owner_repo.split("/", 1)
    body = _render_quality_report(start_date, breached, breached)
    response = httpx.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "title": f"[P3] Agent correction-rate breach since {start_date.isoformat()}",
            "body": body,
            "labels": [
                "type:spike",
                "priority:medium",
                "agent:dhruva",
                "agent:karya",
                "status:triage",
            ],
        },
        timeout=10,
    )
    response.raise_for_status()
    return {"status": "created", "url": response.json().get("html_url")}
