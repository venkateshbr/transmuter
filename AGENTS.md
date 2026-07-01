# Transmuter — Root Coding Rules

> [!NOTE]
> For general project information and startup instructions, see [README.md](file:///Users/vramakrishnaiah/dev/transmuter/README.md).

## Domain Pack
This project uses domain pack: `domain_packs/transmuter/pack.yaml`

## Canonical SDLC
The single canonical engineering process is `docs/team/SDLC_PROTOCOL.md`. Do not use or recreate duplicate SDLC documents.

## Durable Project Context
Before continuing launch, billing, deployment, RBAC, dashboard, or design work, read
`docs/team/CODEX_CONTEXT.md` for current hostnames, Docker paths, release state,
product assumptions, and known follow-up issues.

## Stack
- **Backend**: FastAPI 0.115+ / Python 3.12+ / PydanticAI / Procrastinate
- **Frontend**: Angular 21 standalone / Tailwind CSS / CSS variables
- **Database**: Supabase PostgreSQL 15+ / RLS enforced
- **LLM**: OpenRouter gateway / PydanticAI agents
- **Observability**: Langfuse (traces + evals)
- **Auth**: Supabase Auth (JWT)

## Non-Negotiable Rules

### SDLC / Vishwa-First Execution
- Vishwa is the default role for every unassigned request and must triage before implementation.
- Before writing code, sync GitHub Issues, confirm or create the relevant issue, and move the active issue to `status:in-progress`.
- Founder-directed governance, team-skill, and documentation hygiene batches may skip GitHub issue creation when they do not change runtime behavior; record the exception in the final summary.
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
- Every new or changed frontend page/component must follow `team/DESIGN_SYSTEM.md`.
- Use the A&M-inspired Transmuter design direction: deep navy, steel blue, light blue accents, white/grey surfaces, Libre Franklin typography, square structural geometry, thin dividers, restrained shadows, and dense executive layouts.
- Do not introduce purple/lavender/violet palettes, purple gradients, decorative blobs/orbs, or rounded pill-heavy SaaS styling unless explicitly required by an existing component contract.

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

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- Run `graphify hook install` once per clone/agent machine so post-commit and post-checkout hooks refresh the local graph automatically.
