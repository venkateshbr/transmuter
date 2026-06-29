# Hostinger Deployment

This directory contains the Hostinger-specific deployment assets and operational
notes for the remote API deployment path plus the legacy staged-bundle fallback.

## What gets deployed

`infra/hostinger/deploy.sh` now defaults to `HOSTINGER_DEPLOY_MODE=api`, which
uses Hostinger's VPS Docker Manager API from the operator machine or CI runner.
Dev and production are separate Docker Compose projects on the same Hostinger
VPS:

- production project: `transmuter-hostinger`
- dev project: `transmuter-dev-hostinger`

They use different image tags, bind ports, Supabase schemas, and Traefik
hostnames. The API mode sends an image-only Compose file to Hostinger; it does
not stage this repository's source tree on the VPS.

Legacy `HOSTINGER_DEPLOY_MODE=local` still stages only the files needed to build
and run the Hostinger stack into `/docker/transmuter` on the current machine.
Use local mode only when the command is running directly on the VPS.

The legacy staged bundle contains:

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

Most operator deploys should not need local runtime secret files. Reuse the
existing Hostinger Docker project environment and provide only the deployment
control variables in the shell:

```bash
export HAPI_API_TOKEN='<hostinger-api-token>'
export HOSTINGER_VPS_ID=1695814
export HOSTINGER_REUSE_REMOTE_ENV=1
export HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1
export TRANSMUTER_IMAGE_PULL_POLICY=never
```

For API mode, configure:

```text
HOSTINGER_DEPLOY_MODE=api
HOSTINGER_API_TOKEN=replace-with-token-from-hPanel-API
HOSTINGER_VPS_ID=replace-with-Hostinger-virtual-machine-ID
TRANSMUTER_API_IMAGE=transmuter-api:hostinger
TRANSMUTER_WEB_IMAGE=transmuter-web:hostinger
TRANSMUTER_IMAGE_PULL_POLICY=never
```

`HAPI_API_TOKEN` is also accepted, matching Hostinger's official CLI. The
deployment script can discover the VPS ID from `HOSTINGER_SSH_HOST` or
`HOSTINGER_PUBLIC_IP`, but setting `HOSTINGER_VPS_ID` is less ambiguous.

Hostinger's Docker API cannot receive the app source bundle. In API mode either:

- use images already built on the VPS by setting
  `HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1` and `TRANSMUTER_IMAGE_PULL_POLICY=never`,
- push images separately and set `HOSTINGER_BUILD_AND_PUSH_IMAGES=0`, or
- set `HOSTINGER_BUILD_AND_PUSH_IMAGES=1` and provide registry credentials with
  `HOSTINGER_DOCKER_REGISTRY`, `HOSTINGER_DOCKER_USERNAME`, and
  `HOSTINGER_DOCKER_PASSWORD`.

The default target platform for locally built images is `linux/amd64`.

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

To build and push images before asking Hostinger to recreate the Docker project:

```bash
HOSTINGER_BUILD_AND_PUSH_IMAGES=1 ./infra/hostinger/deploy.sh
```

To use the previous on-VPS staged build workflow:

```bash
HOSTINGER_DEPLOY_MODE=local ./infra/hostinger/deploy.sh
```

To run the schema migration on the VPS before rebuilding containers in legacy
local mode:

```bash
HOSTINGER_DEPLOY_MODE=local RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
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
- legacy local-mode bundle root: `/docker/transmuter-dev`
- compose project: `transmuter-dev-hostinger`
- web bind: `127.0.0.1:4302`
- images: `transmuter-api:hostinger-dev`, `transmuter-web:hostinger-dev`
- Supabase schema: `transmuter_dev`

Create the dev env file from the template and fill in real secrets:

```bash
cp infra/hostinger/.env.dev.example infra/hostinger/.env.dev
```

This file is optional for ordinary remote redeploys when
`HOSTINGER_REUSE_REMOTE_ENV=1` is set. It is still required for local schema
clone helpers or any command that needs database/runtime secrets from the
operator machine.

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

Refresh the dev schema from current production app schema/data:

```bash
./infra/hostinger/deploy-change-to-dev.sh --refresh-schema
```

On the Hostinger VPS, use `POSTGRES_DOCKER_NETWORK=supabase-aethos_default` if
the clone URL uses Supabase's internal `db` hostname and local `pg_dump`/`psql`
are not installed.

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

Validation defaults to public health checks because API deploys run away from
the VPS. When running validation directly on the VPS, add `VALIDATE_LOCAL=1` to
also check `127.0.0.1:4302`.

Promote to production only after the branch is reviewed, merged, and pulled to
the approved production commit:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

Promote with production schema SQL:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql
```

Validation defaults to public production health checks. When running validation
directly on the VPS, add `VALIDATE_LOCAL=1` to also check `127.0.0.1:4301`.

## SRE handoff notes

- Treat `/docker/transmuter` as the legacy local-mode deployment bundle root,
  not a full repo checkout.
- Do not expect hPanel to use `/opt/transmuter`.
- Do not copy secrets into version control.
- If the bundle is rebuilt manually, the compose file must remain at the bundle
  root as `docker-compose.yml`.
- API mode deploys `docker-compose.hostinger.api.yml` through the Hostinger VPS
  Docker Manager API. The current operational mode reuses existing VPS-local
  images with `HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1` and
  `TRANSMUTER_IMAGE_PULL_POLICY=never`; registry-backed images are optional.
- If any env value contains spaces or shell-special characters, quote it before
  the deploy script sources an ignored env file.
- The deploy script sets the remote `.env` to mode `600` after copying it only
  in legacy local mode.
- If the bundle needs to be refreshed, stage only changed repo subsets rather
  than cloning the whole repository.
