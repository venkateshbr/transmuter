# Transmuter API — Backend Coding Rules

## Stack
FastAPI 0.115+ · Python 3.12+ · Pydantic v2 · PydanticAI · Supabase · Procrastinate · Langfuse

## Required Context
- Root rules: `../../AGENTS.md`
- Durable context: `../../docs/team/CODEX_CONTEXT.md`
- Graphify: use the root Graphify rules; query `graphify-out/graph.json` before broad backend searches and run `graphify update .` after code or agent-context documentation changes when no commit hook has run yet.

## Non-Negotiable Rules

### Money
- `NUMERIC(15,4)` in PostgreSQL — never FLOAT
- `decimal.Decimal` in Python — never `float`
- String in JSON (serialise with `str()` before returning)

### Tenant Isolation
- Every query: `WHERE tenant_id = :current_tenant_id`
- Use `get_supabase_user(jwt)` for user requests (RLS enforced)
- Never use `get_supabase_admin()` for user-facing data reads

### Service Layer
```
Router (thin: parse + respond) → Service (business logic) → Repository (data access)
```
- No business logic in routers
- No Supabase calls in routers — always via service/repository

### Auth
- All routes require `Depends(get_current_user)` unless explicitly public
- Tenant authorization: prefer `app.core.rbac` capability helpers such as
  `require_capability(...)`, `assert_can_manage_users(...)`, and
  initiative-scoped helpers. Use direct role checks only for platform-admin or
  explicitly role-specific exceptions.
- Never log or return JWT tokens in responses

### Agents / AI
- Wrap every PydanticAI call with a Langfuse trace
- Always return typed Pydantic models (no raw dicts from LLM)
- Graceful degradation: agent failure must not block core API
- Never send raw PII to OpenRouter — mask first

### Package Verification Protocol
Before writing any third-party import:
```bash
uv run python -c "import <pkg>; print(<pkg>.__version__)"
uv run python -c "from <pkg>.<sub> import <Class>; print('OK')"
```

## Linting
```bash
uv run ruff check app/
uv run ruff format --check app/
uv run mypy app/
```

## Tests
```bash
uv run pytest tests/ -v
```
