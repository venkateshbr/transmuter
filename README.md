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

## Knowledge Graph

This repository is configured for [Graphify](https://graphify.net/) so agents can
query a local code knowledge graph before broad source searches. The project
integration lives in `.codex/`, and `AGENTS.md` tells Codex how to use
`graphify query`, `graphify path`, and `graphify explain`.

Install the CLI if it is missing:

```bash
uv tool install graphifyy
```

Refresh the local code graph after code changes:

```bash
graphify update .
```

The generated graph is written to `graphify-out/` and is intentionally ignored by
git. Local git hooks are installed with `graphify hook install` so commits and
checkouts refresh the graph on this machine; run that command once on another
machine if the hooks are missing.

Query the graph:

```bash
graphify query "How is Stripe billing configured?"
graphify path "BillingProvisioningService" "stripe_price_configuration()"
graphify explain "BillingProvisioningService"
```

## Hostinger Remote Deployment

Dev and production run on the same Hostinger VPS as separate Docker Compose
projects, image names, bind ports, domains, and Supabase schemas:

- Dev: `transmuter-dev-hostinger`, `transmuter-api:hostinger-dev`,
  `transmuter-web:hostinger-dev`, `https://transmuter-dev.ishirock.tech`,
  schema `transmuter_dev`.
- Production: `transmuter-hostinger`, `transmuter-api:hostinger`,
  `transmuter-web:hostinger`, `https://transmuter.ishirock.tech`,
  schema `transmuter`.

Deployments are remote-first through the Hostinger VPS Docker project API. The
API fetches `docker-compose.hostinger.yml` from GitHub, builds on the VPS, and
recreates the selected Docker project. Because the API fetches from GitHub, the
commit being deployed must be committed and pushed first; uncommitted local
files are not deployable through this path.

Set the Hostinger API key in an ignored local dotenv file. Shell values still
take precedence, but when they are absent the deploy scripts read
`HOSTINGER_API_KEY` or `HOSTINGER_API_TOKEN` from the repository root `.env`,
then from the selected `infra/hostinger/.env` or `.env.dev` file:

```dotenv
HOSTINGER_API_KEY=<hostinger-api-key>
HOSTINGER_VPS_ID=1695814
```

Do not commit `.env` or Hostinger env files; they contain secrets.

Deploy the current pushed commit to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh
```

Deploy a schema-bearing change to dev:

```bash
./infra/hostinger/deploy-change-to-dev.sh \
  --schema supabase/migrations/20260629000001_operating_model_rbac_roles.sql
```

Validate dev:

```bash
./infra/hostinger/validate-dev.sh
```

Promote the reviewed, merged, and pulled production commit:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh
```

Promote with production schema SQL:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh \
  --schema supabase/migrations/20260629000001_operating_model_rbac_roles.sql
```

The legacy `infra/hostinger/deploy.sh` script still exists only for emergency
VPS-local fallback when you are already on the VPS and intentionally want to
stage `/docker/transmuter` from that machine. Routine dev and production
deployments should use the remote API wrappers above.

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
