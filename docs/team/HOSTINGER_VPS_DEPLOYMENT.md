# Hostinger VPS Deployment Runbook

Last updated: 2026-06-12

## Target

- VPS hostname: `srv1695814.hstgr.cloud`
- VPS public IP: `76.13.208.106`
- Primary domain: `ishirock.tech`
- Public app hostname: `https://transmuter.ishirock.tech`
- Supabase API domain: `https://supabase.ishirock.tech`
- Deployment directory on VPS: `/docker/transmuter`
- Staged compose file on VPS: `/docker/transmuter/docker-compose.yml`
- Source compose template in repo: `docker-compose.hostinger.yml`
- Deployment script in repo: `infra/hostinger/deploy.sh`
- Schema migration script in repo: `infra/hostinger/migrate_supabase_schema_to_transmuter.sh`

## Bundle Model

The Hostinger deployment is a *staged bundle*, not a full repository clone.

`infra/hostinger/deploy.sh` copies only the required repo subsets to the VPS:

- `apps/api/`
- `apps/web/`
- `domain_packs/`
- `infra/hostinger/`
- `docker-compose.hostinger.yml` staged as `/docker/transmuter/docker-compose.yml`
- `infra/hostinger/.env` staged as `/docker/transmuter/.env`

## Traefik Routing

The web container is the only public app entrypoint.

- Host rule: `transmuter.ishirock.tech`
- Host-side bind: `127.0.0.1:4301`
- Container port: `80`
- Private API target: `http://api:8001`

The API is not publicly exposed; `/api` is proxied by the web nginx container on the private Docker network.

## Environment Preparation

Create the local deployment env file from the template:

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
- `HOSTINGER_ADMIN_PASSWORD` for one-time minimal local bootstrap, or separate
  `HOSTINGER_PLATFORM_ADMIN_PASSWORD` and `HOSTINGER_TENANT_ADMIN_PASSWORD`

Keep `infra/hostinger/.env` uncommitted.
If any value contains spaces or shell-special characters, quote it in the `.env`
file because the deploy script sources that file with shell syntax.

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
./infra/hostinger/deploy.sh
```

To run the schema migration on the VPS immediately before restarting containers:

```bash
RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
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
git checkout v0.4.0
./infra/hostinger/deploy.sh
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

What the script does:

1. Creates `/docker/transmuter` on the VPS.
2. Syncs only the required repo subsets.
3. Copies `infra/hostinger/.env` to `/docker/transmuter/.env`.
4. Copies `docker-compose.hostinger.yml` to `/docker/transmuter/docker-compose.yml`.
5. Optionally runs the schema migration helper on the VPS.
6. Builds and starts `api` and `web` with Docker Compose. The `worker` service
   is available through the opt-in `worker` Compose profile.

## Validation

On the VPS:

```bash
cd /docker/transmuter
docker compose -f docker-compose.yml --env-file .env ps
docker compose -f docker-compose.yml --env-file .env exec web wget -qO- http://127.0.0.1/health
curl -fsS http://127.0.0.1:4301/health
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

- Do not treat `/docker/transmuter` as a source checkout.
- Keep the compose file at the bundle root as `docker-compose.yml`.
- The deploy script sets the remote `.env` to mode `600` after copying it.
- Do not expose the API publicly unless there is a specific debugging need.
- Do not commit secrets or copy them into repo-tracked files.
- If the bundle is manually refreshed, refresh only the changed repo subsets rather than cloning the full repository.
