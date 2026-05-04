# Testing Standard

## Acceptance Principle

Smoke tests and mocked API responses are useful developer checks, but they do not
count as product acceptance.

Acceptance requires evidence against the real stack or a deterministic test stack.

For user workflows, backend-only verification is not enough. If a real user will
click through the flow, acceptance must include frontend/browser execution against
the real API and then backend validation that the data landed correctly.

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

For end-to-end product workflows:

- Start from the same entry point a customer or operator uses.
- Complete the flow in the frontend without manual database shortcuts.
- Validate the frontend displays the resulting state correctly.
- Validate backend records, totals, permissions, and integration state.
- Repeat with role-specific users when RBAC is involved.
- Capture reusable scenario steps in docs for future regression.

For agent changes:

- Deterministic evals for prompts/tools.
- HITL workflow tests for write actions.
- Graceful degradation tests when model/provider is unavailable.

## Sample Data

- Tests must reset or isolate data.
- Tests must not depend on manually created browser state.
- Seed data should be deterministic and named as test/demo data.
- Demo tenants/customers should be disposable and deletable through product/admin
  workflows where possible.

## Revenue-Critical Regression Standard

For onboarding, subscriptions, billing, payment webhooks, tenant provisioning, or
customer admin setup:

- Use sandbox/test-mode provider credentials.
- Use provider-recommended test cards or fixtures.
- Test checkout through the public frontend.
- Verify webhook delivery and signature validation.
- Verify tenant/customer/subscription records are created exactly once.
- Log in as the initial admin through the frontend.
- Create representative business data through the frontend.
- Validate dashboards/totals in the frontend and via API/database checks.
- Test RBAC with at least admin, owner/editor, and viewer/read-only users.
- Test cancellation/failure/retry paths when feasible.
- Clean up demo tenant/customer data through the admin UI or documented cleanup
  path.

## Verification Report

Every completion should include:

- Commands run.
- Tests passed.
- Frontend workflows executed.
- Backend/API records validated.
- Tests not run and why.
- Residual risks.
