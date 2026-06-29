# Transmuter — Value Creation Platform

Transmuter is a high-performance platform for managing digital transformation portfolios, governance, and AI-driven insights. It follows a rigorous multi-tenant architecture with Supabase RLS and an A&M-inspired consulting design system.

## 🚀 Quick Start

### Prerequisites

Install these tools before building from a fresh checkout:

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for the FastAPI backend
- Node.js 22 LTS and npm 11+
- Docker 28+ with Docker Compose v2 for production images
- Access to a configured Supabase project and the required environment variables

On this deployment host, Docker is available at `/usr/local/bin/docker`. On most
developer machines, `docker` on `PATH` is enough.

### Checkout

```bash
git clone https://github.com/venkateshbr/transmuter.git
cd transmuter
```

### Environment File

Create `.env` in the repository root from the example file:

```bash
cp .env.example .env
```

Fill in the Supabase, JWT, OpenRouter/Langfuse, Stripe, and payment settings for
your environment. Do not commit `.env`; it contains secrets.

For the complete environment variable reference, requiredness, and pre-run
checklist, see [docs/team/ENVIRONMENT_CONFIGURATION.md](docs/team/ENVIRONMENT_CONFIGURATION.md).

### Startup & Stop Scripts
The project provides convenience scripts in the root folder for local development:

- **Start Servers**: `./start.sh`
  - Starts the FastAPI backend (Port 8000) and Angular frontend (Port 4300) in the background.
  - Logs are written to `backend.log` and `frontend.log` in the root directory.
- **Stop Servers**: `./stop.sh`
  - Gracefully terminates the backend and frontend processes.

To monitor logs:
```bash
tail -f frontend.log backend.log
```

The local development URLs are:

- Frontend: `http://127.0.0.1:4300`
- API: `http://127.0.0.1:8000`
- API health: `http://127.0.0.1:8000/health`

### Manual Local Backend Commands

Use these commands when you want to run or verify the backend directly:

```bash
cd apps/api
uv sync --extra dev
uv run uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd apps/api
uv run python -m compileall app
uv run --extra dev pytest tests/ -v
uv run ruff check app/
```

### Manual Local Frontend Commands

Use these commands when you want to run or verify the Angular app directly:

```bash
cd apps/web
npm ci --legacy-peer-deps
npm start -- --port 4300
```

In another terminal:

```bash
cd apps/web
./node_modules/.bin/tsc -p tsconfig.app.json --noEmit
npm run build
npm run e2e:real
```

The real UI acceptance test expects the API and frontend to be running against
deterministic sample data.

## Production Docker Build

This section is for local production-image testing or direct Docker operation.
For the public Hostinger VPS deployment, use the remote API commands in
[Hostinger Remote Deployment](#hostinger-remote-deployment).

Production uses two images:

- `transmuter-api:prod`, exposed on host port `8001`
- `transmuter-web:prod`, exposed on host port `4301`

The production compose file is `infra/docker-compose.prod.yml`.

### Build Images

```bash
docker compose -f infra/docker-compose.prod.yml build
```

If Docker is installed at `/usr/local/bin/docker`, use:

```bash
/usr/local/bin/docker compose -f infra/docker-compose.prod.yml build
```

### Start Or Recreate The Local Production Stack

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d
```

Equivalent convenience script:

```bash
./start-prod.sh
```

### Rebuild Only The Frontend

```bash
docker compose -f infra/docker-compose.prod.yml build web
docker compose -f infra/docker-compose.prod.yml up -d web
```

### Rebuild Only The API

```bash
docker compose -f infra/docker-compose.prod.yml build api
docker compose -f infra/docker-compose.prod.yml up -d api
```

### Check Local Production Container Status

```bash
docker compose -f infra/docker-compose.prod.yml ps
curl -fsS http://127.0.0.1:8001/health
curl -fsS http://127.0.0.1:4301/health
```

For the current Hostinger production deployment, public health checks should
also pass:

```bash
curl -fsS https://transmuter.ishirock.tech/health
curl -fsS https://transmuter.ishirock.tech/api/health
```

## Hostinger Remote Deployment

Hostinger deployments are run remotely through the Hostinger VPS Docker Manager
API. Dev and production are separate Docker Compose projects on the same VPS:

- Dev: `transmuter-dev-hostinger`, `https://transmuter-dev.ishirock.tech`,
  images `transmuter-api:hostinger-dev` / `transmuter-web:hostinger-dev`
- Production: `transmuter-hostinger`, `https://transmuter.ishirock.tech`,
  images `transmuter-api:hostinger` / `transmuter-web:hostinger`

Set the shared remote deployment environment once in the shell:

```bash
export HAPI_API_TOKEN='<hostinger-api-token>'
export HOSTINGER_VPS_ID=1695814
export HOSTINGER_REUSE_REMOTE_ENV=1
export HOSTINGER_ALLOW_LOCAL_IMAGE_TAGS=1
export TRANSMUTER_IMAGE_PULL_POLICY=never
```

Deploy to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh
./infra/hostinger/validate-dev.sh
```

Deploy to dev with SQL:

```bash
./infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql
./infra/hostinger/validate-dev.sh
```

Promote to production after merge and approval:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
./infra/hostinger/validate-prod.sh
```

Redeploy production with the current production images:

```bash
./infra/hostinger/deploy-prod.sh
./infra/hostinger/validate-prod.sh
```

Do not commit Hostinger API tokens or runtime secrets. The legacy on-VPS staged
bundle path remains available only for one-off operations with
`HOSTINGER_DEPLOY_MODE=local`.

### Stop Local Production Stack

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env down
```

Equivalent convenience script:

```bash
./stop-prod.sh
```

## 🛠 Technology Stack

- **Backend**: FastAPI 0.115+ / Python 3.12+ / PydanticAI / Procrastinate
- **Frontend**: Angular 21 standalone / Tailwind CSS / CSS variables
- **Database**: Supabase PostgreSQL 15+ / RLS enforced
- **LLM**: OpenRouter gateway / PydanticAI agents
- **Observability**: Langfuse (traces + evals)
- **Auth**: Supabase Auth (JWT)

## 📜 Development Guidelines

For detailed coding rules and standards, refer to:
- [docs/team/SDLC_PROTOCOL.md](file:///Users/vramakrishnaiah/dev/transmuter/docs/team/SDLC_PROTOCOL.md) — Canonical Vishwa-first SDLC and real sample-data acceptance protocol.
- [GEMINI.md](file:///Users/vramakrishnaiah/dev/transmuter/GEMINI.md) — Antigravity/Gemini specific coding rules.
- [CLAUDE.md](file:///Users/vramakrishnaiah/dev/transmuter/CLAUDE.md) — Core project rules and agent workflows.

### Non-Negotiable Rules

- **Financials**: Use `NUMERIC(15,4)` in DB and `decimal.Decimal` in Python. Never use `float` for money.
- **Multi-Tenancy**: Every table MUST have `tenant_id`. All queries MUST be scoped by `tenant_id`.
- **Security**: Supabase RLS policies are mandatory on all tables. Never send raw PII to external LLMs.
- **AI Agents**: All LLM calls must be traced via Langfuse. HITL (Human-In-The-Loop) checkpoints are required for DB writes by agents.
- **UI/UX**: Follow the A&M-inspired Transmuter Design System (`team/DESIGN_SYSTEM.md`). Components must support both Light and Dark modes using CSS variables (`--t-*`).

## 📂 Project Structure

- `apps/api/`: FastAPI backend (Router → Service → Repository pattern).
- `apps/web/`: Angular 21 frontend (Standalone components).
- `supabase/`: Database migrations and configuration.
- `domain_packs/`: Domain-specific configuration and rules.
- `team/`: Architecture, Design System, and Project Requirements.

## 🔗 Repository
https://github.com/venkateshbr/transmuter
