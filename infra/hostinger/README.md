# Hostinger Deployment

This directory contains the Hostinger-specific deployment assets and operational
notes for remote Docker project deployment.

## What gets deployed

`infra/hostinger/deploy-dev.sh` and `infra/hostinger/deploy-prod.sh` call
`deploy-remote.sh`, which deploys through the Hostinger VPS Docker project API.
The API fetches `docker-compose.hostinger.yml` from GitHub for the requested
commit, builds on the VPS, and recreates the selected Docker project.

Dev and production are separate projects on the same VPS:

- Dev project: `transmuter-dev-hostinger`
- Production project: `transmuter-hostinger`

The older `infra/hostinger/deploy.sh` script is retained as a legacy VPS-local
fallback only. It should not be used for routine dev or production deploys.

## Runtime shape

- Public app hostname: `transmuter.ishirock.tech`
- Traefik runs on the host network
- The web container binds to `127.0.0.1:4301` on the host
- The web container listens on port `80` internally
- The web nginx container proxies `/api` to `http://api:8001` on the private
  Docker network
- The API and worker are not publicly exposed

## Environment

For normal remote deployment, put the Hostinger API key in an ignored local
dotenv file:

```dotenv
HOSTINGER_API_KEY=<hostinger-api-key>
HOSTINGER_VPS_ID=1695814
```

Shell values take precedence as one-off overrides. When they are absent, the
scripts load `HOSTINGER_API_KEY` or `HOSTINGER_API_TOKEN` from the repository
root `.env`, then from the selected `infra/hostinger/.env` or `.env.dev` file.

If local Hostinger env files are present, the deploy script can send those
values to the Hostinger project. If `infra/hostinger/.env` or `.env.dev` is
absent, the script fetches and preserves the existing saved Hostinger Docker
project environment before replacing the project. This avoids wiping runtime
secrets during API deploys.

For first-time setup or secret rotation, copy the template, fill in real
secrets, and keep it uncommitted:

```bash
cp infra/hostinger/.env.example infra/hostinger/.env
```

Hostinger defaults to the local self-hosted Supabase target:

```text
SUPABASE_TARGET=local
SUPABASE_LOCAL_URL=https://supabase.ishirock.tech
DATABASE_LOCAL_URL=postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter,public,extensions
```

To roll back to Supabase Cloud for demo/fallback, populate the
`SUPABASE_CLOUD_*` and `DATABASE_CLOUD_URL` values, set
`SUPABASE_TARGET=cloud`, and restart the stack. The legacy direct
`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, and `DATABASE_URL`
variables are compatibility fallbacks only.

The local Supabase REST service must expose `transmuter` first:

```text
PGRST_DB_SCHEMAS=transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter,public,extensions
```

## Deploy

Deploy the current pushed commit to production through the Hostinger API:

```bash
./infra/hostinger/deploy-prod.sh
```

Deploy the current pushed commit to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh
```

Deploy a schema-bearing change to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh \
  --schema supabase/migrations/20260629000001_operating_model_rbac_roles.sql
```

After the local schema is built, run the minimal bootstrap from `apps/api`:

```bash
HOSTINGER_ADMIN_PASSWORD='<temporary-password>' uv run python scripts/bootstrap_hostinger_local.py
```

This creates only platform/admin auth, one blank admin tenant, subscription
shell data, financial configuration, and gate criteria. It does not seed
operational tenant data.

The API also runs the generalized platform-admin Auth bootstrap on every
startup. Configure `PLATFORM_ADMIN_EMAILS`, optionally
`PLATFORM_ADMIN_BOOTSTRAP_EMAIL`, and set `PLATFORM_ADMIN_BOOTSTRAP_PASSWORD`
only when a missing Auth user should be created. This startup path does not seed
tenant admins or tenant data.

For a one-time Auth email rename, set `PLATFORM_ADMIN_PREVIOUS_EMAIL` and run:

```bash
uv run python scripts/rotate_platform_admin_email.py
```

## Dev Environment

The dev stack is isolated from production:

- public hostname: `transmuter-dev.ishirock.tech`
- bundle root: `/docker/transmuter-dev`
- compose project: `transmuter-dev-hostinger`
- web bind: `127.0.0.1:4302`
- images: `transmuter-api:hostinger-dev`, `transmuter-web:hostinger-dev`
- Supabase schema: `transmuter_dev`

Create the dev env file from the template and fill in real secrets:

```bash
cp infra/hostinger/.env.dev.example infra/hostinger/.env.dev
```

The dev database URL must put `transmuter_dev` first in the search path:

```text
DATABASE_LOCAL_URL=postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter_dev,public,extensions
SUPABASE_SCHEMA=transmuter_dev
DB_SCHEMA=transmuter_dev
```

The self-hosted Supabase REST service must expose the dev schema before the
production schema for dev API calls:

```text
PGRST_DB_SCHEMAS=transmuter_dev,transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter_dev,transmuter,public,extensions
```

Refresh the dev schema from current production app schema/data. This still uses
the direct PostgreSQL clone helper and requires database connectivity from the
machine running the command:

```bash
./infra/hostinger/deploy-change-to-dev.sh --refresh-schema
```

When local env files are absent, `apply-schema-sql.sh` can fetch the saved
Hostinger project environment through the API. The dev/prod wrappers set
`HOSTINGER_SCHEMA_DATABASE_HOST` to the VPS public IP so container-local
database hosts are rewritten for remote schema application.

Deploy a code-only feature or fix to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh
```

Deploy a feature or fix with explicit schema SQL to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql
```

Apply only a schema SQL file to dev, without deploying containers:

```bash
./infra/hostinger/apply-schema-sql.sh dev path/to/change.sql
```

Validate dev:

```bash
./infra/hostinger/validate-dev.sh
```

Promote to production only after the branch is reviewed, merged, and pulled to
the approved production commit:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

Promote with production schema SQL:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql
```

## SRE handoff notes

- Routine deploys use Hostinger API Docker projects, not SSH or local bundle
  staging.
- The commit must be pushed to GitHub before API deployment.
- The VPS must have access to the GitHub repo/compose file. For private repos,
  keep the Hostinger VPS Docker manager deploy key configured in GitHub.
- Do not copy secrets into version control.
- Keep `HOSTINGER_API_KEY` or `HOSTINGER_API_TOKEN` in an ignored local `.env`
  file or export it only for the current shell.
- If the legacy VPS-local bundle is rebuilt manually, the compose file must
  remain at the bundle root as `docker-compose.yml`.
- If any env value contains spaces or shell-special characters, quote it before
  the deploy script sources `infra/hostinger/.env`.
