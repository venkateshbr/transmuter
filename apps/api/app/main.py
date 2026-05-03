from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, financials, governance, health, initiatives, kpis, milestones, risks, status_updates, dashboard, meetings, people, ai, action_items, dependencies, workstreams, business_units, team

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

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
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(meetings.router)
app.include_router(people.router)
app.include_router(workstreams.router)
app.include_router(business_units.router)
app.include_router(ai.router)
app.include_router(action_items.router)
app.include_router(dependencies.router)
app.include_router(initiatives.router)
app.include_router(financials.router)
app.include_router(milestones.router)
app.include_router(kpis.router)
app.include_router(risks.router)
app.include_router(status_updates.router)
app.include_router(governance.router)
app.include_router(team.router)
