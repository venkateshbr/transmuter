from __future__ import annotations

import re
from collections import defaultdict, deque
from statistics import quantiles
from time import perf_counter
from typing import Any, Protocol, runtime_checkable

import httpx
import logfire
import sentry_sdk
from fastapi import FastAPI
from langfuse import Langfuse
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.core.config import settings

_configured = False
_langfuse_client: Langfuse | None = None
_request_counter = logfire.metric_counter(
    "transmuter.api.requests",
    unit="1",
    description="API requests by method, route, and status code.",
)
_request_latency = logfire.metric_histogram(
    "transmuter.api.request_latency_ms",
    unit="ms",
    description="API request latency by method, route, and status code.",
)
_latency_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=500))
_request_counts: dict[str, int] = defaultdict(int)
_agent_latency = logfire.metric_histogram(
    "transmuter.agent.latency_ms",
    unit="ms",
    description="Agent latency by agent, tenant, and status.",
)
_agent_counter = logfire.metric_counter(
    "transmuter.agent.runs",
    unit="1",
    description="Agent runs by agent, tenant, and status.",
)
_agent_corrections = logfire.metric_counter(
    "transmuter.agent.corrections",
    unit="1",
    description="Human corrections by agent and tenant.",
)
_worker_latency = logfire.metric_histogram(
    "transmuter.worker.job_latency_ms",
    unit="ms",
    description="Worker job latency by queue, job, and status.",
)
_worker_counter = logfire.metric_counter(
    "transmuter.worker.jobs",
    unit="1",
    description="Worker jobs by queue, job, and status.",
)
_agent_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=500))
_agent_counts: dict[str, int] = defaultdict(int)
_agent_correction_counts: dict[str, int] = defaultdict(int)
_worker_samples: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=500))
_worker_counts: dict[str, int] = defaultdict(int)
_worker_queue_depths: dict[str, int] = defaultdict(int)
_alert_counts: dict[str, int] = defaultdict(int)
_PII_PATTERNS = (
    re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
)


@runtime_checkable
class Traceable(Protocol):
    def flush(self) -> None: ...


def configure_observability(app: FastAPI) -> None:
    global _configured
    if _configured:
        return

    if settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            release=settings.version,
            traces_sample_rate=settings.sentry_traces_sample_rate,
            send_default_pii=False,
            integrations=[FastApiIntegration()],
        )

    logfire.configure(
        token=settings.logfire_token or None,
        service_name=settings.app_name,
        service_version=settings.version,
        environment=settings.environment,
        send_to_logfire=bool(settings.logfire_token),
        console=False,
        inspect_arguments=False,
    )
    logfire.instrument_fastapi(
        app,
        capture_headers=False,
        excluded_urls="/health,/metrics",
    )
    _configured = True


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


def start_request_timer() -> float:
    return perf_counter()


def record_request_metrics(method: str, path: str, status_code: int, started_at: float) -> None:
    duration_ms = (perf_counter() - started_at) * 1000
    attributes = {
        "http.method": method,
        "http.route": _normalize_path(path),
        "http.status_code": status_code,
    }
    _request_counter.add(1, attributes)
    _request_latency.record(duration_ms, attributes)

    key = f"{method} {_normalize_path(path)}"
    _request_counts[key] += 1
    _latency_samples[key].append(duration_ms)


def start_agent_timer() -> float:
    return perf_counter()


def start_worker_timer() -> float:
    return perf_counter()


def record_agent_run(
    agent_name: str,
    tenant_id: str,
    status: str,
    started_at: float,
    corrected: bool = False,
) -> None:
    duration_ms = (perf_counter() - started_at) * 1000
    attributes = {
        "agent.name": agent_name,
        "tenant.id": tenant_id,
        "agent.status": status,
    }
    _agent_counter.add(1, attributes)
    _agent_latency.record(duration_ms, attributes)
    if corrected:
        _agent_corrections.add(1, attributes)

    key = f"{agent_name} tenant={tenant_id} status={status}"
    aggregate_key = f"{agent_name} tenant={tenant_id}"
    _agent_counts[key] += 1
    _agent_counts[aggregate_key] += 1
    _agent_samples[key].append(duration_ms)
    _agent_samples[aggregate_key].append(duration_ms)
    if corrected:
        _agent_correction_counts[aggregate_key] += 1


def record_worker_job(queue: str, job_name: str, status: str, started_at: float) -> None:
    duration_ms = (perf_counter() - started_at) * 1000
    attributes = {
        "worker.queue": queue,
        "worker.job": job_name,
        "worker.status": status,
    }
    _worker_counter.add(1, attributes)
    _worker_latency.record(duration_ms, attributes)

    key = f"{queue} {job_name} status={status}"
    _worker_counts[key] += 1
    _worker_samples[key].append(duration_ms)


def record_worker_queue_depth(queue: str, depth: int) -> None:
    _worker_queue_depths[queue] = max(0, depth)


def notify_p1_p2_error(
    source: str,
    message: str,
    severity: str = "P1",
    context: dict[str, Any] | None = None,
) -> None:
    if severity not in {"P1", "P2"}:
        severity = "P2"
    payload = {
        "service": settings.app_name,
        "environment": settings.environment,
        "severity": severity,
        "source": source,
        "message": _mask_value(message),
        "context": _mask_value(context or {}),
    }
    _alert_counts[severity] += 1
    sentry_sdk.capture_message(f"{severity} {source}: {message}", level="error")
    if not settings.alert_webhook_url:
        return
    try:
        httpx.post(settings.alert_webhook_url, json=payload, timeout=3)
    except Exception as exc:
        sentry_sdk.capture_exception(exc)


def metrics_snapshot() -> dict[str, Any]:
    routes = []
    for key, samples in sorted(_latency_samples.items()):
        ordered = sorted(samples)
        routes.append(
            {
                "route": key,
                "count": _request_counts[key],
                "p50_ms": _percentile(ordered, 50),
                "p95_ms": _percentile(ordered, 95),
                "p99_ms": _percentile(ordered, 99),
            }
        )
    agents = []
    for key, samples in sorted(_agent_samples.items()):
        if " status=" in key:
            continue
        ordered = sorted(samples)
        runs = _agent_counts[key]
        corrections = _agent_correction_counts[key]
        agents.append(
            {
                "agent": key,
                "count": runs,
                "p50_ms": _percentile(ordered, 50),
                "p95_ms": _percentile(ordered, 95),
                "p99_ms": _percentile(ordered, 99),
                "correction_rate": round(corrections / runs, 4) if runs else 0.0,
            }
        )
    workers = []
    for key, samples in sorted(_worker_samples.items()):
        ordered = sorted(samples)
        workers.append(
            {
                "job": key,
                "count": _worker_counts[key],
                "p50_ms": _percentile(ordered, 50),
                "p95_ms": _percentile(ordered, 95),
                "p99_ms": _percentile(ordered, 99),
            }
        )
    return {
        "service": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "routes": routes,
        "agents": agents,
        "workers": {
            "jobs": workers,
            "queue_depths": dict(sorted(_worker_queue_depths.items())),
        },
        "alerts": {
            "configured": bool(settings.alert_webhook_url),
            "counts": dict(sorted(_alert_counts.items())),
        },
        "slo": _slo_snapshot(routes, agents),
    }


def _percentile(values: list[float], percentile: int) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 2)
    index = min(98, max(0, percentile - 1))
    return round(quantiles(values, n=100, method="inclusive")[index], 2)


def _normalize_path(path: str) -> str:
    if path.startswith("/initiatives/"):
        parts = path.split("/")
        if len(parts) > 2:
            parts[2] = "{initiative_id}"
        return "/".join(parts)
    if path.startswith("/milestones/"):
        parts = path.split("/")
        if len(parts) > 2:
            parts[2] = "{milestone_id}"
        return "/".join(parts)
    if path.startswith("/meetings/"):
        parts = path.split("/")
        if len(parts) > 2:
            parts[2] = "{meeting_id}"
        return "/".join(parts)
    return path


def _slo_snapshot(routes: list[dict[str, Any]], agents: list[dict[str, Any]]) -> dict[str, Any]:
    api_violations = [
        route["route"]
        for route in routes
        if route.get("p99_ms") is not None and route["p99_ms"] > settings.api_p99_slo_ms
    ]
    agent_latency_violations = [
        agent["agent"]
        for agent in agents
        if agent.get("p99_ms") is not None and agent["p99_ms"] > settings.agent_latency_slo_ms
    ]
    correction_violations = [
        agent["agent"]
        for agent in agents
        if agent.get("correction_rate", 0.0) > settings.agent_correction_rate_slo
    ]
    return {
        "api_p99_ms_target": settings.api_p99_slo_ms,
        "agent_latency_ms_target": settings.agent_latency_slo_ms,
        "agent_correction_rate_target": settings.agent_correction_rate_slo,
        "api_p99_violations": api_violations,
        "agent_latency_violations": agent_latency_violations,
        "agent_correction_rate_violations": correction_violations,
    }


def _mask_value(value: Any) -> Any:
    if isinstance(value, str):
        masked = value
        for pattern in _PII_PATTERNS:
            masked = pattern.sub("[redacted]", masked)
        return masked
    if isinstance(value, dict):
        return {key: _mask_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask_value(item) for item in value]
    return value
