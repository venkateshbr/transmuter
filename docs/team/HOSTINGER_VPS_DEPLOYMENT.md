# Hostinger VPS Deployment Runbook

Last updated: 2026-06-29

## Target

- VPS hostname: `srv1695814.hstgr.cloud`
- VPS public IP: `76.13.208.106`
- Primary domain: `ishirock.tech`
- Public app hostname: `https://transmuter.ishirock.tech`
- Supabase API domain: `https://supabase.ishirock.tech`
- Legacy local-mode deployment directory on VPS: `/docker/transmuter`
- Legacy local-mode dev deployment directory on VPS: `/docker/transmuter-dev`
- Legacy local-mode staged compose file on VPS:
  `/docker/transmuter/docker-compose.yml`
- Legacy local-mode source compose template in repo:
  `docker-compose.hostinger.yml`
- Hostinger API compose template in repo: `docker-compose.hostinger.api.yml`
- Deployment script in repo: `infra/hostinger/deploy.sh`
- Schema migration script in repo: `infra/hostinger/migrate_supabase_schema_to_transmuter.sh`
- Dev schema clone script in repo: `infra/hostinger/clone_schema_to_dev.sh`

## Deployment Model

Dev and production are separate Docker Compose projects on the same Hostinger
VPS. They differ by project name, image tags, host bind, Supabase schema, and
Traefik hostname:

| Environment | Project | Hostname | Web bind | Images | Schema |
| --- | --- | --- | --- | --- | --- |
| Production | `transmuter-hostinger` | `transmuter.ishirock.tech` | `127.0.0.1:4301` | prod API/web tags | `transmuter` |
| Dev | `transmuter-dev-hostinger` | `transmuter-dev.ishirock.tech` | `127.0.0.1:4302` | dev API/web tags | `transmuter_dev` |

The default deployment mode is remote Hostinger VPS Docker Manager API:

- `infra/hostinger/deploy.sh` sends `docker-compose.hostinger.api.yml` and a
  generated environment payload to Hostinger's API.
- The API compose template is image-only. It does not include `build:` blocks
  because the Hostinger API cannot receive this repository's source bundle.
- Images must already exist on the VPS with
  `HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1` and `TRANSMUTER_IMAGE_PULL_POLICY=never`,
  or be pushed to a registry the VPS can pull. The deploy script can build and
  push registry images first with `HOSTINGER_BUILD_AND_PUSH_IMAGES=1`.

The legacy VPS-local deployment remains available with
`HOSTINGER_DEPLOY_MODE=local`. That path is a *staged bundle*, not a full
repository clone.

In legacy local mode, `infra/hostinger/deploy.sh` copies only the required repo
subsets to the VPS:

- `apps/api/`
- `apps/web/`
- `domain_packs/`
- `infra/hostinger/`
- `docker-compose.hostinger.yml` staged as `/docker/transmuter/docker-compose.yml`
- `infra/hostinger/.env` staged as `/docker/transmuter/.env`

The dev legacy bundle uses the same model with `infra/hostinger/.env.dev` staged to
`/docker/transmuter-dev/.env`.

## Traefik Routing

The web container is the only public app entrypoint.

- Host rule: `transmuter.ishirock.tech`
- Host-side bind: `127.0.0.1:4301`
- Container port: `80`
- Private API target: `http://api:8001`

The API is not publicly exposed; `/api` is proxied by the web nginx container on the private Docker network.

## Environment Preparation

For ordinary remote redeploys, prefer reusing the existing Hostinger Docker
project environment and exporting only the deployment control values:

```bash
export HAPI_API_TOKEN='<hostinger-api-token>'
export HOSTINGER_VPS_ID=1695814
export HOSTINGER_REUSE_REMOTE_ENV=1
export HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1
export TRANSMUTER_IMAGE_PULL_POLICY=never
```

If a command needs local runtime/database secrets, create the ignored deployment
env file from the template:

```bash
cp infra/hostinger/.env.example infra/hostinger/.env
```

Fill in:

- `HOSTINGER_DEPLOY_MODE=api`
- `HOSTINGER_API_TOKEN` or exported `HAPI_API_TOKEN`
- `HOSTINGER_VPS_ID` for the shared Hostinger VPS
- `TRANSMUTER_API_IMAGE` and `TRANSMUTER_WEB_IMAGE` for the selected
  environment. Current operational values are VPS-local image tags:
  `transmuter-api:hostinger`, `transmuter-web:hostinger`,
  `transmuter-api:hostinger-dev`, and `transmuter-web:hostinger-dev`.
- `HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1` and
  `TRANSMUTER_IMAGE_PULL_POLICY=never` when using the current VPS-local image
  tags.
- optional image build/push values:
  `HOSTINGER_BUILD_AND_PUSH_IMAGES`, `HOSTINGER_DOCKER_REGISTRY`,
  `HOSTINGER_DOCKER_USERNAME`, `HOSTINGER_DOCKER_PASSWORD`, and
  `HOSTINGER_IMAGE_PLATFORM`
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

Production wrapper:

```bash
./infra/hostinger/deploy-prod.sh
```

To run the schema migration on the VPS immediately before restarting containers:

```bash
HOSTINGER_DEPLOY_MODE=local RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
```

API mode cannot stage source or run arbitrary migration scripts on the VPS. For
code deploys, use existing VPS-local image tags or registry images. For SQL
changes, pass SQL files to
`deploy-change-to-dev.sh` or `promote-dev-to-prod.sh`; the database URL used by
`apply-schema-sql.sh` must be reachable from the machine running the command.
Use legacy local mode only for one-off VPS-local migration operations.

## Hostinger Dev Environment

The dev environment is separate from production:

- Public app hostname: `https://transmuter-dev.ishirock.tech`
- Legacy local-mode dev bundle root: `/docker/transmuter-dev`
- Dev compose project: `transmuter-dev-hostinger`
- Dev images: `transmuter-api:hostinger-dev`, `transmuter-web:hostinger-dev`
- Dev web bind: `127.0.0.1:4302`
- Dev Traefik router/service: `transmuter-dev-web`
- Dev Supabase schema: `transmuter_dev`

Create the dev env file only when local runtime/database secrets are needed:

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

Refresh dev schema from current production app schema/data. This requires a
local `.env.dev` or exported database clone URL reachable from the operator
machine:

```bash
./infra/hostinger/deploy-change-to-dev.sh --refresh-schema
```

On the Hostinger VPS, use `POSTGRES_DOCKER_NETWORK=supabase-aethos_default` if
the clone URL uses Supabase's internal `db` hostname and local `pg_dump`/`psql`
are not installed.

Deploy the current checkout to dev for every feature/fix:

```bash
./infra/hostinger/deploy-change-to-dev.sh
```

If the feature/fix includes database changes, pass explicit SQL files. They are
applied to `transmuter_dev` before the dev containers are rebuilt:

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

By default validation checks the public dev hostname only. When running directly
on the VPS, add `VALIDATE_LOCAL=1` to also check `127.0.0.1:4302`.

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
git checkout v0.4.0
./infra/hostinger/deploy.sh
```

For remote rollback, use the standard Hostinger API deployment environment
variables. Legacy local-mode rollback is available only when operating directly
on the VPS with `HOSTINGER_DEPLOY_MODE=local`.

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

What the script does:

In API mode:

1. Loads the ignored environment file, or reuses the existing Hostinger Docker
   project environment when `HOSTINGER_REUSE_REMOTE_ENV=1`.
2. References existing VPS-local images, or optionally builds and pushes the
   configured API and web registry images.
3. Sends `docker-compose.hostinger.api.yml` and generated environment variables
   to Hostinger's VPS Docker Manager API for the selected Compose project.
4. Waits for the Hostinger action to complete and prints the project/container
   summary.

In legacy local mode:

1. Creates `/docker/transmuter` on the VPS.
2. Syncs only the required repo subsets.
3. Copies `infra/hostinger/.env` to `/docker/transmuter/.env`.
4. Copies `docker-compose.hostinger.yml` to `/docker/transmuter/docker-compose.yml`.
5. Optionally runs the schema migration helper on the VPS.
6. Builds and starts `api` and `web` with Docker Compose. The `worker` service
   is available through the opt-in `worker` Compose profile.

## Validation

On the VPS, these loopback checks are available for legacy local-mode diagnosis:

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
- Keep the compose file at the bundle root as `docker-compose.yml` only for
  legacy local-mode deploys.
- The deploy script sets the remote `.env` to mode `600` after copying it only
  in legacy local mode.
- For API mode, do not rely on source files being present on the VPS. Use the
  existing VPS-local image tags with pull disabled, or switch to registry-backed
  images explicitly.
- Do not expose the API publicly unless there is a specific debugging need.
- Do not commit secrets or copy them into repo-tracked files.
- If the bundle is manually refreshed, refresh only the changed repo subsets rather than cloning the full repository.
