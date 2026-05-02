# Transmuter — Antigravity Coding Rules

> [!NOTE]
> For general project information and startup instructions, see [README.md](file:///Users/vramakrishnaiah/dev/transmuter/README.md).


## Domain Pack
This project uses domain pack: `domain_packs/transmuter/pack.yaml`

## Canonical SDLC
The single canonical engineering process is `docs/team/SDLC_PROTOCOL.md`. Do not use or recreate duplicate SDLC documents.

## Stack
- **Backend**: FastAPI 0.115+ / Python 3.12+ / PydanticAI / Procrastinate
- **Frontend**: Angular 18 standalone / Tailwind CSS / CSS variables
- **Database**: Supabase PostgreSQL 15+ / RLS enforced
- **LLM**: OpenRouter gateway / PydanticAI agents
- **Observability**: Langfuse (traces + evals)
- **Auth**: Supabase Auth (JWT)

## Non-Negotiable Rules

### SDLC / Vishwa-First Execution
- Vishwa is the default role for every unassigned request and must triage before implementation.
- Before writing code, sync GitHub Issues, confirm or create the relevant issue, and move the active issue to `status:in-progress`.
- Use existing issues when they match scope; create new issues only for missing work or blockers.
- Follow the required order for feature work: Netra requirements → Vastu architecture → Chitra design → Karya/Rupa implementation → Vastu post-review → Aksha testing → Sthira deploy readiness → Vishwa final review/close.
- Only Vishwa closes issues; only Aksha moves tested work to `status:in-review`.
- Prahari review is mandatory for auth, JWT, RLS, agent tools, integrations, and security-sensitive changes.

### Testing Standard
- No smoke tests or mock-led acceptance tests count as completion.
- Acceptance requires real API tests against a running API and deterministic seeded sample data.
- Acceptance requires browser UI tests against the real Angular app and real API.
- UI/API tests must cover real seeded users, initiatives, meetings, agenda items, attendees, sessions, action items, financial entries, and cost lines when those areas are touched.
- Tests must reset or isolate sample data predictably; no test may depend on manually created browser state.
- Existing unit or TestClient tests may remain as developer checks, but Aksha sign-off must include real sample-data UI/API verification.

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
- `start.sh` / `stop.sh` — Local development control
- `backend.log` / `frontend.log` — Server logs


## GitHub Repo
https://github.com/venkateshbr/transmuter
