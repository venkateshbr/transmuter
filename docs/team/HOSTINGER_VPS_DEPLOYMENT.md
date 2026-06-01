# Hostinger VPS Deployment Runbook

Last updated: 2026-05-31

Issue: #178

## Target

- VPS hostname: `srv1695814.hstgr.cloud`
- VPS public IP: `76.13.208.106`
- Primary domain: `ishirock.tech`
- Public app hostname: `https://transmuter.ishirock.tech`
- Supabase API domain: `https://supabase.ishirock.tech`
- Deployment directory: `infra/hostinger/`
- Transmuter app compose file: `infra/hostinger/docker-compose.yml`
- Deployment script: `infra/hostinger/deploy.sh`
- Schema migration script: `infra/hostinger/migrate_supabase_schema_to_transmuter.sh`

## Clarifying Decisions To Confirm

1. Confirm whether Hostinger SSH uses `root` on port `22`, or a different deploy user.
2. Confirm the self-hosted Supabase Postgres port is reachable on the VPS host as `127.0.0.1:5432`.
3. Confirm whether the schema migration should be schema-only or should later include data/auth/storage migration. The current script is schema-only.
4. Confirm the Traefik HTTPS entrypoint and certificate resolver names. This runbook defaults to `websecure` and `letsencrypt`.

## Traefik Routing

Create the DNS CNAME for:

```text
transmuter.ishirock.tech
```

Traefik runs on the host network. The Hostinger Compose file publishes only the
`web` container to localhost on `127.0.0.1:4301`; the API is not published. The
`web` container declares labels for:

```text
Host(`transmuter.ishirock.tech`)
```

The Traefik router/service labels use the Transmuter-specific `transmuter-web`
names:

```text
traefik.http.routers.transmuter-web.rule=Host(`transmuter.ishirock.tech`)
traefik.http.routers.transmuter-web.entrypoints=websecure
traefik.http.routers.transmuter-web.tls.certresolver=letsencrypt
traefik.http.services.transmuter-web.loadbalancer.server.port=80
```

The service port label is `80` because Traefik's Docker provider routes to the
container port, and the Transmuter web nginx container listens on port `80`.
The host-side published port is `4301`.

The `web` container also joins the private `app` network. Its nginx config proxies
same-origin `/api` requests to:

```text
http://api:8001
```

So browser traffic only needs one public hostname: `transmuter.ishirock.tech`.

## One-Time Supabase Requirement

The local Supabase stack must expose the `transmuter` schema through PostgREST.
For self-hosted Supabase, configure the REST service so `transmuter` is the first
exposed schema, followed by public schemas needed by Supabase:

```text
PGRST_DB_SCHEMAS=transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter,public,extensions
```

Restart the Supabase REST/API services after changing this. Without this step,
the Transmuter API may connect successfully but Supabase REST calls will still
look for tables in `public`.

## Prepare Environment

Create the local deployment env file from the template:

```bash
cp infra/hostinger/.env.example infra/hostinger/.env
```

Fill in:

- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `DATABASE_URL`
- `SOURCE_DATABASE_URL`
- `TARGET_DATABASE_URL`
- `JWT_SECRET`
- OpenRouter/Langfuse values as needed
- Stripe values if billing/signup should work
- `PLATFORM_ADMIN_EMAILS`

Keep `infra/hostinger/.env` uncommitted.
URL-encode any special characters in database passwords before placing them in
`DATABASE_URL`, `SOURCE_DATABASE_URL`, or `TARGET_DATABASE_URL`.

For local Supabase Docker, keep the app database search path on `transmuter`:

```text
DATABASE_URL=postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter,public
```

If the migration script runs on the VPS and the database is published on the host:

```text
TARGET_DATABASE_URL=postgresql://postgres:<password>@127.0.0.1:5432/postgres
```

## Migrate Schema

Run schema migration by itself when you want to verify the database before a deploy:

```bash
set -a
. ./infra/hostinger/.env
set +a
./infra/hostinger/migrate_supabase_schema_to_transmuter.sh
```

By default, this creates `transmuter` if missing and imports the schema from the
cloud Supabase `public` schema. To reset and recreate the local target schema:

```bash
RESET_TARGET_SCHEMA=true ./infra/hostinger/migrate_supabase_schema_to_transmuter.sh
```

This is destructive for the target schema only; it does not touch cloud Supabase.

## Deploy

Run:

```bash
./infra/hostinger/deploy.sh
```

To run the schema migration on the VPS immediately before restarting containers:

```bash
RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
```

The script:

1. Creates `/opt/transmuter` on the VPS.
2. Syncs the repository with `rsync`.
3. Copies `infra/hostinger/.env` to the VPS.
4. Optionally runs the schema migration script on the VPS.
5. Builds and starts `api`, `worker`, and `web` with Docker Compose.

## Reverse Proxy

Recommended routing:

```text
transmuter.ishirock.tech -> web container port 80
host fallback/debug      -> http://127.0.0.1:4301
```

The frontend nginx container proxies `/api` to the API container on the Docker
Compose network, so a separate public API hostname is not required.

## Validation

On the VPS:

```bash
cd /opt/transmuter
docker compose -f infra/hostinger/docker-compose.yml --env-file infra/hostinger/.env ps
docker compose -f infra/hostinger/docker-compose.yml --env-file infra/hostinger/.env exec web wget -qO- http://127.0.0.1/health
curl -fsS http://127.0.0.1:4301/health
```

From outside the VPS after DNS/reverse proxy routing:

```bash
curl -fsS https://transmuter.ishirock.tech/health
curl -fsS https://transmuter.ishirock.tech/api/health
curl -fsS https://supabase.ishirock.tech/rest/v1/
```

If Stripe signup is enabled for this hostname, configure the webhook endpoint as:

```text
https://transmuter.ishirock.tech/api/billing/webhook
```

## Security Notes

- Do not commit `infra/hostinger/.env`.
- Do not expose the Supabase service-role key in browser runtime config.
- Keep API and worker unpublished on the private Docker network.
- Auth, RLS, service-role usage, and deployment boundary changes require Prahari review before final release sign-off.
