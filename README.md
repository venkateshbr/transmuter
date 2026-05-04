# Transmuter — Value Creation Platform

Transmuter is a high-performance platform for managing digital transformation portfolios, governance, and AI-driven insights. It follows a rigorous multi-tenant architecture with Supabase RLS and an A&M-inspired consulting design system.

## 🚀 Quick Start

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

## 🛠 Technology Stack

- **Backend**: FastAPI 0.115+ / Python 3.12+ / PydanticAI / Procrastinate
- **Frontend**: Angular 18 standalone / Tailwind CSS / CSS variables
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
- `apps/web/`: Angular 18 frontend (Standalone components).
- `supabase/`: Database migrations and configuration.
- `domain_packs/`: Domain-specific configuration and rules.
- `team/`: Architecture, Design System, and Project Requirements.

## 🔗 Repository
https://github.com/venkateshbr/transmuter
