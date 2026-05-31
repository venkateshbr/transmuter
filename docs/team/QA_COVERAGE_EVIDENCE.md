# QA Coverage Evidence

Date: 2026-05-24
Owner: Aksha
Scope: Phase 5 full coverage issue #81.

## Automated Gates

- Backend route coverage: `cd apps/api && uv run --extra dev pytest tests --ignore=tests/acceptance -q --tb=short --cov=app/routers --cov-report=xml --cov-report=term-missing --cov-fail-under=80`
- Backend real API sample data: `cd apps/api && RUN_REAL_ACCEPTANCE=1 TRANSMUTER_API_BASE_URL=http://127.0.0.1:8000 uv run --extra dev pytest tests/acceptance/test_real_api_sample_data.py -v --tb=short`
- Agent evals: `cd apps/api && uv run pytest ../../tests/evals -v --tb=short`
- Backend lint/type gates: `ruff`, `ruff format --check`, and `mypy`
- Frontend type gate: `cd apps/web && npx tsc -p tsconfig.app.json --noEmit`
- Frontend production build: `cd apps/web && npm run build`
- Frontend unit coverage: `cd apps/web && npx ng test --watch=false --coverage`
- Real browser acceptance: `cd apps/web && TRANSMUTER_UI_BASE_URL=http://127.0.0.1:4304 TRANSMUTER_API_BASE_URL=http://127.0.0.1:8000 node e2e/real-ui-acceptance.mjs`
- Expired session/auth regression: `cd apps/web && TRANSMUTER_UI_BASE_URL=http://127.0.0.1:4304 TRANSMUTER_API_BASE_URL=http://127.0.0.1:8000 node e2e/signup-expired-session.mjs`

## Named E2E Coverage

- Public signup and onboarding flow
- Login with Supabase Auth session token
- Expired-session handling
- Dashboard and portfolio drilldowns
- Initiative create/detail/import workflows
- Create initiative, add milestone, add risk, submit G1 gate, and attempt stage advancement with real governance checks
- Generate status update draft, edit/submit, and verify compliance surfaces
- Milestones, checklists, dependencies, roadmap, KPIs, risks, status updates, and action items
- Meeting command center session, notes/action extraction, approval, and action item surfaces
- Financial entries, cost lines, scenario toggles, assumptions, Excel export/import, and value bridge
- RBAC and RLS-backed cross-tenant protection

## Current Coverage Position

- Backend API route coverage is above the phase target: 80.59% on
  `app/routers` with 88 passed, 1 skipped.
- Real API sample-data acceptance is green: 16 passed against the running
  FastAPI app and Supabase-backed sample data.
- Agent eval coverage is committed under `tests/evals`: 18 passed, covering
  10 deterministic initiative-intake scenarios plus prompt-injection/PII safety
  checks.
- Frontend unit coverage artifacts are generated and the current app-wide
  coverage is above the phase target: 72.90% statements and 77.49% lines.
- Real browser acceptance passed against the running Angular app and real API.
  It covers login, dashboard, people/invite, initiative create/import, overview,
  team, summary, milestones/dependencies/roadmap, KPIs, risks, meetings,
  status updates, financial grid, assumptions, Excel roundtrip, and value bridge.
- Signup/expired-session browser regression passed and verifies the public
  signup path remains accessible when an expired session exists.

## Follow-Up Threshold Policy

Keep the CI thresholds aligned to the issue acceptance targets: backend route
coverage stays at 80%, frontend unit coverage stays at 60% or higher, and the
committed eval suite must run instead of reporting a missing-dataset notice.
