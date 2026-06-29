# Hostinger VPS Deployment Runbook

Last updated: 2026-06-29

## Target

- VPS hostname: `srv1695814.hstgr.cloud`
- VPS public IP: `76.13.208.106`
- Primary domain: `ishirock.tech`
- Public app hostname: `https://transmuter.ishirock.tech`
- Supabase API domain: `https://supabase.ishirock.tech`
- Source compose template in repo: `docker-compose.hostinger.yml`
- Remote deployment script in repo: `infra/hostinger/deploy-remote.sh`
- Dev wrapper: `infra/hostinger/deploy-change-to-dev.sh`
- Production wrapper: `infra/hostinger/promote-dev-to-prod.sh`
- Schema migration script in repo: `infra/hostinger/migrate_supabase_schema_to_transmuter.sh`
- Dev schema clone script in repo: `infra/hostinger/clone_schema_to_dev.sh`

## Remote Deployment Model

The canonical Hostinger deployment path is remote-first through the Hostinger
VPS Docker project API. The API fetches `docker-compose.hostinger.yml` from
GitHub for the requested pushed commit, builds on the VPS, and replaces the
selected Docker Compose project while preserving project volumes.

The same VPS runs two separate Transmuter Docker projects:

- Dev: `transmuter-dev-hostinger`
- Production: `transmuter-hostinger`

Because Hostinger fetches source from GitHub, the commit being deployed must be
committed and pushed before running the deploy wrapper. Uncommitted local files
cannot be deployed through the Hostinger API.

`infra/hostinger/deploy.sh` is retained only as a legacy VPS-local fallback for
emergency manual staging on the VPS. It is not the routine deploy path.

## Traefik Routing

The web container is the only public app entrypoint.

- Host rule: `transmuter.ishirock.tech`
- Host-side bind: `127.0.0.1:4301`
- Container port: `80`
- Private API target: `http://api:8001`

The API is not publicly exposed; `/api` is proxied by the web nginx container on the private Docker network.

## Environment Preparation

Set the Hostinger API key in an ignored local dotenv file:

```dotenv
HOSTINGER_API_KEY=<hostinger-api-key>
HOSTINGER_VPS_ID=1695814
```

Shell exports remain valid one-off overrides and take precedence. When they are
absent, the remote deploy and schema scripts load Hostinger control values from
the repository root `.env`, then from the selected `infra/hostinger/.env` or
`.env.dev` file.

For first-time setup or secret rotation, create the deployment env file from
the template:

```bash
cp infra/hostinger/.env.example infra/hostinger/.env
```

Fill in:

- `SUPABASE_TARGET` (`local` for Hostinger primary, `cloud` for fallback/demo)
- `SUPABASE_LOCAL_URL`
- `SUPABASE_LOCAL_ANON_KEY`
- `SUPABASE_LOCAL_SERVICE_KEY`
- `DATABASE_LOCAL_URL`
- `SUPABASE_CLOUD_URL`
- `SUPABASE_CLOUD_ANON_KEY`
- `SUPABASE_CLOUD_SERVICE_KEY`
- `DATABASE_CLOUD_URL`
- `SOURCE_DATABASE_URL`
- `TARGET_DATABASE_URL`
- `JWT_SECRET`
- OpenRouter / Langfuse values as needed
- Stripe values if billing/signup should work
- `PLATFORM_ADMIN_EMAILS`
- `PLATFORM_ADMIN_BOOTSTRAP_EMAIL`
- `PLATFORM_ADMIN_BOOTSTRAP_PASSWORD` if the platform admin Auth user may need
  to be created during API startup
- `HOSTINGER_ADMIN_PASSWORD` for one-time minimal local bootstrap, or separate
  `HOSTINGER_PLATFORM_ADMIN_PASSWORD` and `HOSTINGER_TENANT_ADMIN_PASSWORD`

Keep `infra/hostinger/.env` and `.env.dev` uncommitted. If these files are
absent during remote deployment, `deploy-remote.sh` fetches and reuses the
existing saved Hostinger Docker project environment so a project replacement
does not wipe runtime secrets.

If any value contains spaces or shell-special characters, quote it in the `.env`
file because local scripts source that file with shell syntax.

The legacy direct variables `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`SUPABASE_SERVICE_KEY`, and `DATABASE_URL` remain compatibility fallbacks. Leave
them blank when the target-specific values are configured so the active target is
controlled only by `SUPABASE_TARGET`.

## One-Time Supabase Requirement

The local/self-hosted Supabase stack must expose the `transmuter` schema through PostgREST.

Recommended schema exposure:

```text
PGRST_DB_SCHEMAS=transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter,public,extensions
```

Restart Supabase REST/API services after changing this.

The API continues to use unqualified Supabase `.table(...)` calls. With
`SUPABASE_TARGET=local`, `transmuter` must therefore be first in both PostgREST
schema exposure and the direct PostgreSQL search path:

```text
DATABASE_LOCAL_URL=postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter,public,extensions
```

To roll back to Supabase Cloud, set `SUPABASE_TARGET=cloud` and restart the
Transmuter stack. To return to Hostinger local Supabase, set
`SUPABASE_TARGET=local` and restart again.

## Deploy

```bash
./infra/hostinger/deploy-prod.sh
```

Production wrapper:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

Production schema SQL is explicit:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh \
  --schema supabase/migrations/20260629000001_operating_model_rbac_roles.sql
```

## Hostinger Dev Environment

The dev environment is separate from production:

- Public app hostname: `https://transmuter-dev.ishirock.tech`
- Dev compose project: `transmuter-dev-hostinger`
- Dev images: `transmuter-api:hostinger-dev`, `transmuter-web:hostinger-dev`
- Dev web bind: `127.0.0.1:4302`
- Dev Traefik router/service: `transmuter-dev-web`
- Dev Supabase schema: `transmuter_dev`

Create the dev env file:

```bash
cp infra/hostinger/.env.dev.example infra/hostinger/.env.dev
```

Required dev database/search-path settings:

```text
SUPABASE_TARGET=local
SUPABASE_SCHEMA=transmuter_dev
DB_SCHEMA=transmuter_dev
DATABASE_LOCAL_URL=postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter_dev,public,extensions
```

The self-hosted Supabase REST service must expose `transmuter_dev` before the
production schema for dev API calls:

```text
PGRST_DB_SCHEMAS=transmuter_dev,transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter_dev,transmuter,public,extensions
```

Refresh dev schema from current production app schema/data:

```bash
./infra/hostinger/deploy-change-to-dev.sh --refresh-schema
```

`--refresh-schema` still uses direct PostgreSQL clone tooling and requires
database connectivity from the machine running it.

Deploy the current pushed commit to dev for every feature/fix:

```bash
./infra/hostinger/deploy-change-to-dev.sh
```

If the feature/fix includes database changes, pass explicit SQL files. They are
applied to `transmuter_dev` before the dev containers are rebuilt. When local
env files are absent, the schema helper fetches the saved Hostinger project
environment and rewrites container-local database hosts to the VPS public host:

```bash
./infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql
```

For schema-only dev updates:

```bash
./infra/hostinger/apply-schema-sql.sh dev path/to/change.sql
```

Validate dev:

```bash
./infra/hostinger/validate-dev.sh
```

Promotion rule:

- Deploy branches and PRs to dev.
- Promote to production only after review/merge and explicit approval. Promotion
  applies any supplied schema SQL to production schema `transmuter`, deploys the
  production containers, and validates production health checks.
- Production promotion command for code-only changes:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

- Production promotion command with schema changes:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql
```

## v0.4.0 Clean Financial Refactor Rollout

`v0.4.0` is the rollback baseline before the clean configurable financial
metrics refactor. The refactor intentionally replaces reloadable tenant
portfolio data with the clean financial engine and the anonymised workbook
reload path.

Preflight from the repo root:

```bash
git fetch origin --tags
git rev-parse v0.4.0
git diff --check
```

Before destructive reset/reload, validate the anonymised workbook without
writing data:

```bash
cd apps/api
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id <tenant-uuid> \
  --user-id <tenant-admin-user-uuid> \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --dry-run
```

The dry run must report `ready: true` before reload. Expected deterministic
workbook counts:

- 21 initiatives
- 9 business units and 4 workstreams
- 63 benefit lines and 4,694 metric values
- 867 cost lines
- 83 KPIs and 313 KPI entries
- 292 milestones, 33 risks, and 4 status updates
- Required metrics: `gm_uplift`, `gm_uplift_pct`, `gross_margin`, `revenue_uplift`
- Required scenarios: `actual`, `plan_base`, `plan_high`
- Required stage gate numbers: `3`

After deploy and migration, run the destructive reload only with explicit
confirmation:

```bash
cd apps/api
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id <tenant-uuid> \
  --user-id <tenant-admin-user-uuid> \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --confirm-reset
```

Do not use the reload command for normal tenant signup. New tenants should
start blank and self-configure master data, financial metrics, scenarios, stage
gates, gate criteria, workstreams, and business units through Admin before
creating or importing initiatives.

Rollback to the pre-refactor baseline:

```bash
HOSTINGER_DEPLOY_REF=v0.4.0 ./infra/hostinger/deploy-prod.sh
```

If the schema migration has already been applied, rollback also requires
restoring the target Supabase database from a pre-refactor backup. Code rollback
alone does not reverse destructive table truncation or clean-model schema
changes.

## Minimal Local Bootstrap

After the local `transmuter` schema has been built and `SUPABASE_TARGET=local`
is configured, seed only platform/admin shell data:

```bash
cd apps/api
HOSTINGER_ADMIN_PASSWORD='<temporary-password>' uv run python scripts/bootstrap_hostinger_local.py
```

The bootstrap creates or updates:

- One platform admin Supabase Auth user with platform admin app metadata.
- One blank admin tenant and tenant admin user.
- Subscription plans and a `tenant_subscriptions` shell.
- Organization reporting defaults required for safe empty-state operation.

It intentionally does not create initiatives, meetings, agenda items, attendees,
sessions, action items, business units, workstreams, financial configuration,
financial metrics, financial scenarios, stage gates, gate criteria, cost lines,
risks, KPIs, or other operational tenant data.

Normal API startup also runs `apps/api/app/bootstrap/platform_admin.py`, which
ensures the configured `PLATFORM_ADMIN_BOOTSTRAP_EMAIL` exists in Supabase Auth
with platform-admin app metadata. That startup path never creates tenant users,
tenant admins, organizations, subscriptions, or operational tenant data.

For a one-time platform-admin email rotation, run this from the checked-out API
directory with the Hostinger environment loaded:

```bash
PLATFORM_ADMIN_PREVIOUS_EMAIL=admin@ishirock.com \
PLATFORM_ADMIN_BOOTSTRAP_EMAIL=venkatesh@ishirock.com \
uv run python scripts/rotate_platform_admin_email.py
```

Legacy VPS-local fallback only:

`infra/hostinger/deploy.sh` can still be run from the VPS to rebuild a staged
`/docker/transmuter` bundle manually. This path creates `/docker/transmuter`,
copies repo subsets and env files into it, and runs Docker Compose locally on
the VPS. Use it only when the Hostinger API path is unavailable.

## Validation

Remote validation:

```bash
./infra/hostinger/validate-dev.sh
./infra/hostinger/validate-prod.sh
```

Optional local bind validation when already on the VPS:

```bash
VALIDATE_LOCAL=1 ./infra/hostinger/validate-prod.sh
```

From outside the VPS after DNS / reverse-proxy routing:

```bash
curl -fsS https://transmuter.ishirock.tech/health
curl -fsS https://transmuter.ishirock.tech/api/health
curl -fsS https://supabase.ishirock.tech/rest/v1/
```

For local Supabase validation, also verify browser login as the platform/admin
seed user and `/auth/me` through the app API. Platform/admin pages should load
with only bootstrap/admin shell data, not migrated operational tenant data.

For the clean financial refactor rollout, validate:

- Admin Setup Status shows blank-tenant prerequisites when no tenant master data
  has been configured.
- Initiative create/import flows are blocked until required tenant configuration
  exists.
- Admin Financial Configuration can create metrics, scenarios, bridge rows, and
  line attribute definitions.
- Admin Governance Engine can create stage gates and gate criteria.
- Portfolio Financials loads after workbook reload and shows in-year value plus
  run-rate value ramp data.
- Public domain checks pass:

```bash
curl -fsS https://transmuter.ishirock.tech/health
curl -fsS https://transmuter.ishirock.tech/api/health
```

If Stripe signup is enabled, use:

```text
https://transmuter.ishirock.tech/api/billing/webhook
```

## SRE Notes

- Routine deployments use Hostinger API Docker project replacement. Do not
  require SSH or assume the Hostinger VPS is the local machine.
- The commit must be pushed to GitHub before deployment.
- The VPS Docker manager must be able to fetch the repo/compose path. For
  private repositories, keep the VPS deploy key configured in GitHub.
- Do not treat `/docker/transmuter` as the canonical source checkout.
- Do not expose the API publicly unless there is a specific debugging need.
- Do not commit secrets or copy them into repo-tracked files.
- If the legacy VPS-local bundle is manually refreshed, keep the compose file at
  the bundle root as `docker-compose.yml`.
