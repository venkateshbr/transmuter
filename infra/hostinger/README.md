# Hostinger Deployment

This directory contains the Hostinger-specific deployment assets and the
operational notes for the staged bundle.

## What gets deployed

`infra/hostinger/deploy.sh` stages only the files needed to build and run the
Hostinger stack into `/docker/transmuter` on the VPS.

The staged bundle contains:

- `docker-compose.yml` at the bundle root
- `.env` at the bundle root
- `apps/api/`
- `apps/web/`
- `domain_packs/`
- `infra/hostinger/`

The compose file that gets staged to the bundle root is the repo-root template:

- `docker-compose.hostinger.yml`

## Runtime shape

- Public app hostname: `transmuter.ishirock.tech`
- Traefik runs on the host network
- The web container binds to `127.0.0.1:4301` on the host
- The web container listens on port `80` internally
- The web nginx container proxies `/api` to `http://api:8001` on the private
  Docker network
- The API and worker are not publicly exposed

## Environment

Copy the template, fill in real secrets, and keep it uncommitted:

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

```bash
./infra/hostinger/deploy.sh
```

To run the schema migration on the VPS before rebuilding containers:

```bash
RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
```

After the local schema is built, run the minimal bootstrap from `apps/api`:

```bash
HOSTINGER_ADMIN_PASSWORD='<temporary-password>' uv run python scripts/bootstrap_hostinger_local.py
```

This creates only platform/admin auth, one blank admin tenant, subscription
shell data, financial configuration, and gate criteria. It does not seed
operational tenant data.

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

Clone the current production app schema/data into dev:

```bash
set -a
. infra/hostinger/.env.dev
set +a
RESET_TARGET_SCHEMA=true CONFIRM_RESET_DEV_SCHEMA=1 \
  ./infra/hostinger/clone_schema_to_dev.sh
```

On the Hostinger VPS, use `POSTGRES_DOCKER_NETWORK=supabase-aethos_default` if
the clone URL uses Supabase's internal `db` hostname and local `pg_dump`/`psql`
are not installed.

Deploy the currently checked-out branch to dev:

```bash
./infra/hostinger/deploy-dev.sh
```

Validate:

```bash
curl -fsS https://transmuter-dev.ishirock.tech/health
curl -fsS https://transmuter-dev.ishirock.tech/api/health
```

Promote to production only after the branch is reviewed, merged, and pulled to
the approved production commit:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

## SRE handoff notes

- Treat `/docker/transmuter` as the deployment bundle root, not a full repo
  checkout.
- Do not expect hPanel to use `/opt/transmuter`.
- Do not copy secrets into version control.
- If the bundle is rebuilt manually, the compose file must remain at the bundle
  root as `docker-compose.yml`.
- If any env value contains spaces or shell-special characters, quote it before
  the deploy script sources `infra/hostinger/.env`.
- The deploy script sets the remote `.env` to mode `600` after copying it.
- If the bundle needs to be refreshed, stage only changed repo subsets rather
  than cloning the whole repository.
