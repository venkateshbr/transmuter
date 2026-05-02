# Transmuter — Antigravity Coding Rules

## Domain Pack
This project uses domain pack: `domain_packs/transmuter/pack.yaml`

## Stack
- **Backend**: FastAPI 0.115+ / Python 3.12+ / PydanticAI / Procrastinate
- **Frontend**: Angular 18 standalone / Tailwind CSS / CSS variables
- **Database**: Supabase PostgreSQL 15+ / RLS enforced
- **LLM**: OpenRouter gateway / PydanticAI agents
- **Observability**: Langfuse (traces + evals)
- **Auth**: Supabase Auth (JWT)

## Non-Negotiable Rules

### Money
- `NUMERIC(15,4)` in PostgreSQL
- `decimal.Decimal` in Python — never `float`
- String representation in JSON API responses
- All financial calculations use Decimal arithmetic

### Multi-Tenancy
- Every table has `tenant_id uuid NOT NULL`
- Every query is scoped: `WHERE tenant_id = :tenant_id`
- Supabase RLS policies on ALL tables — no exceptions
- FastAPI dependency: `get_current_user()` injected into every route

### Security
- Never send PII (email, phone, display_name) to external LLM APIs — mask first
- JWT secret min 32 chars; never hardcode — use environment variable

### Agents / AI
- Agents never block core platform functionality (graceful degradation)
- All LLM calls are traced via Langfuse
- HITL checkpoint required for any agent action that writes to DB
- Correction rate > 10% triggers a P3 incident issue

### Code Quality
- Service layer pattern: Router (thin) → Service (business logic) → Repository (data)
- No business logic in routers or Angular components
- Type hints on all Python functions
- Verify third-party package APIs before writing integration code

### Angular
- Standalone components only (no NgModules)
- All routes lazy-loaded
- CSS variable design tokens (not hardcoded hex) — see `team/DESIGN_SYSTEM.md`
- Every component: light + dark theme support (purple design system)
- ARIA labels on all interactive elements

## UI Design System
- **Primary accent**: Purple (`#7c3aed` light / `#a78bfa` dark)
- **All tokens**: Defined in `apps/web/src/styles.css` as `--t-*` CSS variables
- **Full spec**: `team/DESIGN_SYSTEM.md`
- **Component classes**: `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.card`, `.glass-panel`, `.input-field`, `.nav-item`, `.badge-*`
- **NEVER hardcode hex colors** for theme-sensitive properties — always use `var(--t-*)`

## Key Files
- `prd.txt` — Full product requirements (708 lines, 12 modules)
- `supabase/migrations/20260430000001_core_schema.sql` — All 25 tables
- `apps/api/` — FastAPI backend (Router → Service → Repository)
- `apps/web/` — Angular 18 frontend
- `team/DESIGN_SYSTEM.md` — Authoritative purple design system
- `team/ARCHITECTURE.md` — System architecture

## GitHub Repo
https://github.com/venkateshbr/transmuter
