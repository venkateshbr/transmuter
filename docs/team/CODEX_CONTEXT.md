# Codex Context - Transmuter

Last updated: 2026-05-08

This file captures durable working context for future Codex sessions. It supplements
`AGENTS.md`, `docs/team/SDLC_PROTOCOL.md`, and `team/DESIGN_SYSTEM.md`; it does not
replace them.

## Current Launch State

- First release snapshot is committed as `3ab8dcb` and tagged `v0.1.0`.
- Dashboard value matrix work is committed after the release tag as `9015e86`.
- Current release snapshot is committed as `e9b670f` and tagged `v0.3.1`.
- `v0.3.1` includes the Alchemist workbook/dashboard acceptance test updates and
  the CI/CD pipeline gates from issue #77.
- Running production Docker stack uses:
  - API image `transmuter-api:prod` on host port `8001`.
  - Frontend image `transmuter-web:prod` on host port `4301`.
  - Compose file `infra/docker-compose.prod.yml`.
- Docker CLI path on this machine is `/usr/local/bin/docker`.
- Cloudflare tunnel hostnames:
  - Frontend: `https://transmuter.ishirock.com`
  - Optional direct API: `https://transmuter-api.ishirock.com`
- Frontend runtime config should point to `/api`; the web nginx container proxies
  that path to the Docker Compose API service at `http://api:8001`.

## Product Direction

- Transmuter is a multi-tenant enterprise transformation SaaS platform.
- Public homepage should describe the enterprise transformation platform, value add,
  benefits, and mock case studies.
- Signup flow is public homepage -> Get Started -> subscription checkout -> tenant
  provisioning -> initial admin setup.
- Stripe sandbox is used for onboarding regression; do not persist or print Stripe
  secrets in docs or responses.
- Product catalog direction:
  - Starter tier for fewer than 50 users.
  - Growth tier for 50-100 users.
  - Enterprise tier for more than 100 users, contact sales.

## Roles And Tenancy

- Platform admin can view tenant signups, billing status, and delete demo tenants.
- Tenant admin configures tenant master data and users.
- Supported tenant roles:
  - `transformation_office`: can see and manage all initiatives.
  - `initiative_owner`: can see assigned/owned initiatives only.
  - `viewer`: can view portfolio data but should not create or mutate data.
- RBAC must be enforced in the API; UI affordances should also hide forbidden actions.

## Stripe And Webhooks

- Stripe checkout and webhook flow has been tested through Cloudflare.
- Webhook endpoint is `https://transmuter.ishirock.com/api/billing/webhook`.
- Stripe events handled include checkout completion and subscription updates/deletes.
- Use test card `4242 4242 4242 4242` only in sandbox regression runs.
- Payment, auth, webhook, tenant provisioning, and RBAC changes require Prahari review.

## Dashboard And Financials

- Financial data must use PostgreSQL `NUMERIC(15,4)`, Python `Decimal`, and JSON
  string values.
- Dashboard values must reconcile to initiative financial entries and value bridge
  totals.
- Workstream x tag value matrix requirements:
  - Rows are workstreams.
  - Columns are initiative tags such as Automation, Offshoring, Commercial, Other.
  - Configurable target year.
  - Values show gross margin uplift base-high ranges.
  - Cells are clickable and show contributing initiatives.
  - Footer shows portfolio totals and existing value bridge context.

## Design Direction

- Use `skills/transmuter-frontend-design/SKILL.md` and `team/DESIGN_SYSTEM.md` for
  every frontend change.
- Visual direction is A&M-inspired without copying A&M proprietary assets:
  deep navy, steel blue, light blue accents, white/grey surfaces, Libre Franklin,
  square structural geometry, thin dividers, restrained shadows, dense executive
  layouts.
- Avoid purple/lavender/violet palettes, decorative blobs/orbs, and generic rounded
  SaaS styling unless already required by the component contract.

## Regression Notes

- Reusable Stripe onboarding regression scenario lives at
  `docs/team/STRIPE_ONBOARDING_E2E_REGRESSION.md`.
- Known follow-up issues from live E2E:
  - #125: platform tenant deletion modal overflow at smaller viewports.
  - #126: tighten RBAC UI affordances and forbidden initiative detail state.
  - #127: dashboard workstream by tag value matrix.
- `scratch/` contains local helper scripts and should not be included in release
  commits unless explicitly requested.
