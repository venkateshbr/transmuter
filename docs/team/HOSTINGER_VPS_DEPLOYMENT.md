# Hostinger VPS Deployment Runbook

Last updated: 2026-06-07

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

- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `DATABASE_URL`
- `SOURCE_DATABASE_URL`
- `TARGET_DATABASE_URL`
- `JWT_SECRET`
- OpenRouter / Langfuse values as needed
- Stripe values if billing/signup should work
- `PLATFORM_ADMIN_EMAILS`

Keep `infra/hostinger/.env` uncommitted.
If any value contains spaces or shell-special characters, quote it in the `.env`
file because the deploy script sources that file with shell syntax.

## One-Time Supabase Requirement

The local/self-hosted Supabase stack must expose the `transmuter` schema through PostgREST.

Recommended schema exposure:

```text
PGRST_DB_SCHEMAS=transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter,public,extensions
```

Restart Supabase REST/API services after changing this.

## Deploy

```bash
./infra/hostinger/deploy.sh
```

To run the schema migration on the VPS immediately before restarting containers:

```bash
RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
```

What the script does:

1. Creates `/docker/transmuter` on the VPS.
2. Syncs only the required repo subsets.
3. Copies `infra/hostinger/.env` to `/docker/transmuter/.env`.
4. Copies `docker-compose.hostinger.yml` to `/docker/transmuter/docker-compose.yml`.
5. Optionally runs the schema migration helper on the VPS.
6. Builds and starts `api`, `worker`, and `web` with Docker Compose.

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
