from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from time import monotonic

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response

from app.core.config import settings
from app.core.observability import (
    configure_observability,
    notify_p1_p2_error,
    record_request_metrics,
    start_request_timer,
)
from app.routers import (
    action_items,
    admin,
    ai,
    auth,
    billing,
    business_units,
    dashboard,
    dependencies,
    executive_control,
    financials,
    governance,
    health,
    initiatives,
    kpis,
    meeting_artifacts,
    meetings,
    milestones,
    people,
    platform,
    risks,
    search,
    status_updates,
    team,
    workstreams,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)
configure_observability(app)

_login_attempts: defaultdict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def enforce_api_security_controls(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    started_at = start_request_timer()
    content_length = request.headers.get("content-length")
    request_body_size = int(content_length) if content_length and content_length.isdigit() else 0
    if request_body_size > settings.max_request_body_bytes:
        record_request_metrics(request.method, request.url.path, 413, started_at)
        return JSONResponse(
            status_code=413,
            content={"detail": "Request body exceeds the 10 MB limit"},
        )

    if request.method == "POST" and request.url.path in {
        "/auth/login",
        "/auth/change-password",
        "/auth/register",
    }:
        now = monotonic()
        client_ip = request.client.host if request.client else "unknown"
        attempts = _login_attempts[f"{request.url.path}:{client_ip}"]
        window_start = now - settings.auth_login_rate_window_seconds
        while attempts and attempts[0] < window_start:
            attempts.popleft()
        if len(attempts) >= settings.auth_login_rate_limit:
            record_request_metrics(request.method, request.url.path, 429, started_at)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many authentication attempts. Try again later."},
                headers={"Retry-After": str(settings.auth_login_rate_window_seconds)},
            )
        attempts.append(now)

    try:
        response = await call_next(request)
    except Exception as exc:
        record_request_metrics(request.method, request.url.path, 500, started_at)
        notify_p1_p2_error(
            source="api",
            message="Unhandled API exception",
            severity="P1",
            context={
                "method": request.method,
                "path": request.url.path,
                "error": str(exc),
            },
        )
        raise
    record_request_metrics(request.method, request.url.path, response.status_code, started_at)
    if response.status_code >= 500:
        notify_p1_p2_error(
            source="api",
            message="API returned server error response",
            severity="P2",
            context={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
            },
        )
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
    )
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4300",
        "http://127.0.0.1:4300",
        "http://localhost:4301",
        "http://127.0.0.1:4301",
        "http://localhost:4302",
        "http://127.0.0.1:4302",
        "http://localhost:4303",
        "http://127.0.0.1:4303",
        "http://localhost:4304",
        "http://127.0.0.1:4304",
        "https://transmuter.ishirock.tech",
        "https://transmuter.ishirock.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(billing.router)
app.include_router(dashboard.router)
app.include_router(meetings.router)
app.include_router(meeting_artifacts.router)
app.include_router(people.router)
app.include_router(platform.router)
app.include_router(workstreams.router)
app.include_router(business_units.router)
app.include_router(admin.router)
app.include_router(ai.router)
app.include_router(action_items.router)
app.include_router(dependencies.router)
app.include_router(executive_control.router)
app.include_router(initiatives.router)
app.include_router(financials.router)
app.include_router(milestones.router)
app.include_router(kpis.router)
app.include_router(risks.router)
app.include_router(search.router)
app.include_router(status_updates.router)
app.include_router(governance.router)
app.include_router(team.router)
