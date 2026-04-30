# Transmuter — Root Coding Rules

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
- FastAPI dependency: `get_current_tenant()` injected into every route

### Security
- Never send PII (email, phone, display_name) to external LLM APIs — mask first
- JWT secret min 32 chars; never hardcode — use environment variable
- Prahari reviews any PR touching auth, RLS, agent tools, or JWT

### Agents / AI
- Agents never block core platform functionality (graceful degradation)
- All LLM calls are traced via Langfuse
- HITL checkpoint required for any agent action that writes to DB
- Correction rate > 10% triggers a P3 incident issue

### Code Quality
- Service layer pattern: Router (thin) → Service (business logic) → Repository (data)
- No business logic in routers or Angular components
- Type hints on all Python functions
- Verify third-party package APIs before writing integration code (see karya_skills: Package Verification Protocol)

### Angular
- Standalone components only (no NgModules)
- All routes lazy-loaded
- CSS variable design tokens (not hardcoded hex)
- Every component: light + dark theme support
- ARIA labels on all interactive elements

## Agent Execution Order (per feature)
```
Netra (requirements) → Vastu (architecture) → Chitra (design)
→ Karya + Rupa (implement, parallel) → Aksha (test)
→ Sthira (deploy) → Vishwa (final review + close)
```
Prahari triggered on: auth / RLS / agent tools / integrations

## Issue Labels
```
type: feature | bug | task | chore | spike
priority: high | medium | low
agent: vishwa | vastu | netra | chitra | rupa | karya | aksha | sthira | prahari | dhruva
status: triage | assigned | in-progress | in-qa | in-review
```

## GitHub Repo
https://github.com/venkateshbr/transmuter
