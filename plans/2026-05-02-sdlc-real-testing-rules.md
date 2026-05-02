# SDLC + Real Testing Rules

Status: Active
Date: 2026-05-02

## Durable Rules

- Vishwa-first applies to all Transmuter work: sync GitHub Issues, create or reuse an issue, move the active issue to `status:in-progress`, then implement.
- GitHub Issues are the source of truth for work tracking. Do not use ad hoc markdown trackers.
- Follow the team pipeline for feature work: Netra -> Vastu -> Chitra -> Karya/Rupa -> Vastu -> Aksha -> Sthira -> Vishwa.
- Prahari review is mandatory for auth, JWT, RLS, agent tools, integrations, and security-sensitive changes.
- Only Vishwa closes issues. Only Aksha moves tested work to `status:in-review`.
- Acceptance cannot rely on smoke tests.
- Acceptance cannot rely on mocked API responses.
- Acceptance must include real API tests against a running API and deterministic seeded sample data.
- Acceptance must include browser UI tests against the real Angular app and real API for user-facing workflows.
- Tests must reset or isolate data predictably and must not depend on manually created browser state.

## Current Build Sequence

1. Stabilization: auth seed/login, deterministic sample data, Angular build, real browser UI test harness.
2. Meetings MVP: meeting CRUD, agenda, attendees, sessions, action items, live-session UI.
3. Financials Core: grid save/load, batch updates, cost lines, calculations, value bridge, Excel import/export.
4. Remaining platform phases after the above are verified.
