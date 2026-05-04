# Quality Gates

## Confidence Gate

Do not modify code until confidence is at least 95%.

If confidence is lower:

- Inspect code.
- Read docs.
- Run focused searches.
- Ask one concise clarification question if needed.

## Package Verification Gate

Before using a third-party API, library, CLI, or SDK:

- Check installed package versions when available.
- Prefer official docs or source code.
- Verify import paths, method signatures, and required configuration.
- Document assumptions when version-specific behavior matters.

## Money Gate

For financial domains:

- Database: fixed precision decimal, for example `NUMERIC(15,4)`.
- Backend: exact decimal type, never floating point.
- API: serialize money as strings.
- Tests: assert exact decimal totals and reconciliation.

## Multi-Tenant Gate

For SaaS or tenant-scoped systems:

- Every tenant-owned table has `tenant_id`.
- Every query is scoped by tenant.
- Database policies enforce tenant isolation when supported.
- Service-role/admin clients are isolated to intentional admin workflows.
- Cross-tenant access tests exist for high-risk paths.

## AI / Agent Gate

- Core product functionality must degrade gracefully when AI is unavailable.
- External LLM calls are traced when observability is configured.
- No raw PII is sent to external LLMs.
- Agent write actions require HITL approval unless explicitly classified as safe.

## Customer Onboarding / Payments Gate

For signup, subscription, payment, webhook, tenant provisioning, or billing portal
work:

- Prahari review is required.
- Use sandbox credentials and provider test fixtures during development.
- Verify webhook signatures; never trust unsigned provider callbacks.
- Store provider customer/subscription IDs idempotently.
- Make provisioning idempotent for duplicate webhook delivery.
- Test the public frontend flow first, then validate backend records.
- Verify the initial admin can log in and configure the tenant.
- Verify billing status is visible to both tenant admins and platform admins.
- Document cleanup for demo tenants and provider-side test customers.

## RBAC Regression Gate

For role or permission work:

- Test through the frontend as each role.
- Validate forbidden UI actions are hidden or disabled.
- Validate forbidden API calls return 403 or equivalent.
- Test direct URL access, not only navigation menus.
- Confirm dashboards and detail pages only show permitted data.
