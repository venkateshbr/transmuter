# Codex Context - Transmuter

Last updated: 2026-06-30

This file captures durable working context for future Codex sessions. It supplements
`AGENTS.md`, `docs/team/SDLC_PROTOCOL.md`, and `team/DESIGN_SYSTEM.md`; it does not
replace them.

## Current Launch State

- First release snapshot is committed as `3ab8dcb` and tagged `v0.1.0`.
- Dashboard value matrix work is committed after the release tag as `9015e86`.
- Current release snapshot is committed as `e9b670f` and tagged `v0.3.1`.
- `v0.3.1` includes the Alchemist workbook/dashboard acceptance test updates and
  the CI/CD pipeline gates from issue #77.
- Shared Costs configurable allocation engine is promoted to production from
  app commit `31c8805`, with the docs-only release-manifest update at
  `b7c32e3`.
- Hostinger production Docker project uses API image `transmuter-api:hostinger`
  and web image `transmuter-web:hostinger`.
- Hostinger dev Docker project uses API image `transmuter-api:hostinger-dev`
  and web image `transmuter-web:hostinger-dev`.
- Hostinger VPS / domain context:
  - Primary domain owned for the VPS: `ishirock.tech`.
  - VPS hostname: `srv1695814.hstgr.cloud`.
  - VPS public IP: `76.13.208.106`.
  - Public app hostname: `https://transmuter.ishirock.tech`, routed through
    Traefik to the Hostinger web container.
  - Local Supabase Docker instance is exposed at `https://supabase.ishirock.tech`.
  - Runtime Supabase selection is controlled by `SUPABASE_TARGET=cloud|local`.
    Hostinger primary runtime should use `local` with
    `DATABASE_LOCAL_URL` search path `transmuter,public,extensions`; Cloud remains
    the fallback/demo target.
  - Hostinger deployment runbook: `docs/team/HOSTINGER_VPS_DEPLOYMENT.md`.
  - Hostinger source compose template in the repo: `docker-compose.hostinger.yml`.
  - Hostinger remote deploy script: `infra/hostinger/deploy-remote.sh`.
  - `infra/hostinger/deploy.sh` is legacy VPS-local fallback only.
  - Hostinger API deploys fetch the pushed GitHub commit/compose file; local
    uncommitted changes are not deployable through the API.
  - Default dev deployment command for every feature/fix:
    `infra/hostinger/deploy-change-to-dev.sh`.
  - If a feature/fix includes database changes, apply explicit SQL to the dev
    schema during dev deploy with
    `infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql`.
  - Dev environment uses `https://transmuter-dev.ishirock.tech`, compose project
    `transmuter-dev-hostinger`, images `transmuter-api:hostinger-dev` /
    `transmuter-web:hostinger-dev`, host bind `127.0.0.1:4302`, and Supabase
    schema `transmuter_dev`.
  - Production promotion command is
    `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`; if schema SQL is
    required, pass `--schema path/to/change.sql` so it applies to production
    schema `transmuter` before deployment.
  - Dev-to-production release tracking lives in
    `docs/team/RELEASE_MANIFEST.md`. Update it before promotion with the PR,
    commit, dev validation, schema SQL, and production validation result.
  - Cloud-to-local Supabase schema migration script:
    `infra/hostinger/migrate_supabase_schema_to_transmuter.sh`.
  - When the user asks to build, test, and deploy, deploy to dev through
    `infra/hostinger/deploy-change-to-dev.sh` after the commit is pushed, then
    validate the real public dev domain `https://transmuter-dev.ishirock.tech`.
    Promote production only after review/merge and explicit confirmation.
  - Post-deploy validation should include `https://transmuter.ishirock.tech/health`,
    `https://transmuter.ishirock.tech/api/health`, login through the browser,
    and the touched real workflows on the public domain.
  - Hostinger `worker` is opt-in via Compose profile `worker`. The current
    cloud Supabase direct DB hostname resolves IPv6-only from this VPS, so the
    Procrastinate worker should not be started until an IPv4-capable Postgres
    pooler/direct URL is configured.
- Frontend runtime config should point to `/api`; the web nginx container proxies
  that path to the Docker Compose API service at `http://api:8001`.
- Current public app and Stripe webhook traffic use the same-origin Hostinger
  hostname `https://transmuter.ishirock.tech`; no separate public API hostname
  is required for normal operation.

## Knowledge Graph And Agent Memory

- Graphifyy is installed for this repository. The local generated graph lives at
  `graphify-out/` and is intentionally ignored by git because it is generated
  source-derived context.
- Current graph baseline was built from commit `632f066e` with `graphify update .`;
  it contains the code/navigation graph used by `graphify query`, `graphify path`,
  and `graphify explain`.
- Agents should use the graph before broad source searches when
  `graphify-out/graph.json` exists. For example:
  `graphify query "How is Stripe billing configured?"`.
- After code or agent-context documentation changes, run `graphify update .` so
  the local knowledge graph stays current. The command is AST/code-only and has
  no API token cost.
- Local git hooks are installed with `graphify hook install`; every clone or
  agent machine should run that once so post-commit and post-checkout refreshes
  keep the graph aligned with commits. If work is not committed yet, run
  `graphify update .` manually before final review.
- If the graph becomes stale or missing, regenerate it with `graphify update .`.
  Full semantic extraction for docs/papers/images should only be enabled with an
  explicit approved LLM backend/API key decision.

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
- Current platform admin operator email is `venkatesh@ishirock.com`; API startup
  idempotently ensures that Supabase Auth user has platform-admin app metadata
  when `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true`.
- Tenant administrator role (`tenant_admin`) configures tenant master data,
  users, access, dashboard configuration, and billing portal access.
- Supported tenant roles:
  - `transformation_office`: full tenant and portfolio permissions.
  - `tenant_admin`: users, access, tenant setup, dimensions, dashboard setup,
    governance configuration, and billing portal access.
  - `pmo_lead`: governance, meetings, actions, milestones, risks, KPIs, and
    program cadence.
  - `finance_lead`: financial configuration, initiative financials, benefit
    validation, shared costs, bankable plans, actuals, and benefit tracking.
  - `workstream_lead`: assigned-workstream visibility and execution evidence.
  - `initiative_owner`: owned-initiative master data, execution evidence,
    status, and financial assumptions.
  - `business_benefit_owner`: portfolio visibility plus benefit realization
    evidence and ledger updates.
  - `executive_sponsor`: read-only executive portfolio and financial views.
  - `viewer`: read-only management portfolio and dashboard access.
- RBAC must be enforced in the API; UI affordances should also hide forbidden actions.

## Stripe And Webhooks

- Stripe checkout and webhook flow has been tested through the public Hostinger
  hostname.
- Webhook endpoint is `https://transmuter.ishirock.tech/api/billing/webhook`.
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
- Known production demo-data drift:
  - #304: production ACME is not yet at dev ACME3 parity. Shared Costs schema,
    API, and UI are live in production, but the full 4-pool FY2028 ACME3 shared
    cost acceptance scenario is dev-only until production demo data is
    backfilled.
- `scratch/` contains local helper scripts and should not be included in release
  commits unless explicitly requested.
