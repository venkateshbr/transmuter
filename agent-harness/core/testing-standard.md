# Testing Standard

## Acceptance Principle

Smoke tests and mocked API responses are useful developer checks, but they do not
count as product acceptance.

Acceptance requires evidence against the real stack or a deterministic test stack.

## Required Evidence

For backend changes:

- Unit or service tests for logic.
- API tests against a running API when behavior is user-facing.
- Database tests or migration verification when schema changes.
- Security tests for auth, RBAC, tenant isolation, and integrations.

For frontend changes:

- Type-check/build.
- Browser verification against real API for touched workflows.
- Accessibility checks for interactive controls.
- Responsive verification for important layouts.

For agent changes:

- Deterministic evals for prompts/tools.
- HITL workflow tests for write actions.
- Graceful degradation tests when model/provider is unavailable.

## Sample Data

- Tests must reset or isolate data.
- Tests must not depend on manually created browser state.
- Seed data should be deterministic and named as test/demo data.

## Verification Report

Every completion should include:

- Commands run.
- Tests passed.
- Tests not run and why.
- Residual risks.

