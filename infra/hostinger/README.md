# Hostinger Deployment

This directory contains the Hostinger-specific Transmuter deployment assets:

- `docker-compose.yml`: app, worker, and web containers with Traefik labels.
- `.env.example`: uncommitted `.env` template for VPS secrets and routing.
- `deploy.sh`: SSH/rsync deployment script for `srv1695814.hstgr.cloud`.
- `migrate_supabase_schema_to_transmuter.sh`: schema-only Supabase Cloud to local Supabase migration.

The public app hostname is `transmuter.ishirock.tech`. Traefik runs on the host
network for this VPS. The web container binds to `127.0.0.1:4301` on the host and
listens on port `80` inside the container. The router/service label names are
`transmuter-web`.

The API is not exposed through Traefik. The web nginx container proxies `/api` to
`http://api:8001` on the private Compose network.

## Setup

```bash
cp infra/hostinger/.env.example infra/hostinger/.env
```

Fill in real secrets and deployment values, then run:

```bash
./infra/hostinger/deploy.sh
```

To also migrate the Supabase Cloud schema into local Supabase schema
`transmuter` before recreating containers:

```bash
RUN_DB_SCHEMA_MIGRATION=1 ./infra/hostinger/deploy.sh
```
