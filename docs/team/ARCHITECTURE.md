# Transmuter — System Architecture
**Owner**: Vastu (Chief Architect) | **Status**: Living Document | **Last Updated**: 2026-04-30

---

## System Overview

```
Angular 21 SPA
    ↕ HTTPS / REST
FastAPI 0.115+ (Python 3.12)
    ↕ supabase-py (JWT-scoped)
Supabase (PostgreSQL 15 + Auth + Storage + RLS)
    ↕ HTTP
OpenRouter LLM Gateway → Claude Sonnet 4.6 (default)
    ↕
Langfuse (trace + eval + prompt versioning)

Background: Procrastinate (async job queue over PostgreSQL)
```

---

## ADR-001: Supabase as primary database + auth
**Status**: Accepted | **Date**: 2026-04-30

**Context**: Need managed PostgreSQL with built-in auth, row-level security, and real-time subscriptions without managing infra.

**Decision**: Supabase (hosted). PostgreSQL 15+ with RLS on every table. Supabase Auth for JWT-based user authentication. supabase-py with user-scoped JWTs for all user-facing API calls (RLS enforced automatically).

**Consequences**:
- ✅ RLS enforced at DB layer — service code tenant bugs cannot leak data
- ✅ No auth infra to maintain
- ⚠️ Service role key must never be used for user-facing queries

---

## ADR-002: Auth architecture — JWT claims + RLS pattern
**Status**: Accepted | **Date**: 2026-04-30 | **Addresses**: Issue #25

### JWT Claims Structure
```json
{
  "sub": "<user_uuid>",
  "tenant_id": "<org_uuid>",
  "role": "transformation_office | tenant_admin | pmo_lead | finance_lead | workstream_lead | initiative_owner | business_benefit_owner | executive_sponsor | viewer",
  "email": "<user_email>",
  "exp": <unix_timestamp>,
  "iat": <unix_timestamp>
}
```

Issued by Supabase Auth. `tenant_id` and `role` are stored in `user_metadata` and embedded at sign-in via a Supabase Edge Function or DB trigger.

### RLS Policy Template (all tables)
```sql
-- Enable RLS
ALTER TABLE <table> ENABLE ROW LEVEL SECURITY;

-- SELECT: any authenticated user in the same tenant
CREATE POLICY "<table>_select" ON <table>
  FOR SELECT USING (
    tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  );

-- INSERT: tenant_id auto-set from JWT (user cannot supply a different value)
CREATE POLICY "<table>_insert" ON <table>
  FOR INSERT WITH CHECK (
    tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  );

-- UPDATE/DELETE: own tenant only
CREATE POLICY "<table>_update" ON <table>
  FOR UPDATE USING (
    tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  );

CREATE POLICY "<table>_delete" ON <table>
  FOR DELETE USING (
    tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
  );
```

For capability-restricted tables (e.g., governance configuration and gate decisions):
```sql
CREATE POLICY "gate_decisions_governance" ON gate_submissions
  FOR UPDATE USING (
    tenant_id = (auth.jwt() ->> 'tenant_id')::uuid
    AND current_user_role() IN ('transformation_office', 'tenant_admin', 'pmo_lead')
  );
```

### FastAPI Dependency Design
```python
# apps/api/app/core/auth.py

async def get_current_user(credentials: HTTPAuthorizationCredentials) -> CurrentUser:
    payload = decode_token(credentials.credentials)
    return CurrentUser(id=payload.sub, tenant_id=payload.tenant_id, role=payload.role)

def require_capability(capability: str):
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_capability(user.role, capability):
            raise HTTPException(403, "Insufficient role")
        return user
    return _check

# Usage:
# @router.post("/gates/{id}/decide", dependencies=[Depends(require_capability("governance.manage"))])
```

**Consequences**:
- ✅ RLS is the enforcement layer — FastAPI role checks are defence-in-depth
- ✅ `tenant_id` cannot be forged by the client (set from JWT, not request body)
- ⚠️ Prahari must verify RLS policies before every schema migration merge

---

## ADR-003: DB schema design — conventions + key decisions
**Status**: Accepted | **Date**: 2026-04-30 | **Addresses**: Issue #28

### Primary Keys
UUID v4 (`gen_random_uuid()`) — not ULID. Reason: native Supabase/PostgreSQL support, no extra extension needed.

### Monetary Values
`NUMERIC(15,4)` in PostgreSQL. Decimal in Python. String in JSON.

```sql
revenue_uplift_base    NUMERIC(15,4) NOT NULL DEFAULT 0,
revenue_uplift_actual  NUMERIC(15,4),   -- null until entered
```

### Soft Deletes
Initiatives: `archived_at TIMESTAMPTZ` (non-destructive; excluded from default queries by `WHERE archived_at IS NULL`).
Milestones/Risks/KPIs: hard delete (no soft delete) — simpler, these are managed within an initiative.

### Timestamps
All timestamps in UTC, stored as `TIMESTAMPTZ`. Application never assumes local timezone.

### tenant_id Enforcement
Every table: `tenant_id UUID NOT NULL REFERENCES organizations(id)`.
Every INSERT policy: `tenant_id = (auth.jwt() ->> 'tenant_id')::uuid` (user cannot supply a different value).

### Indexes (standard per-table pattern)
```sql
CREATE INDEX <table>_tenant_idx ON <table>(tenant_id);
CREATE INDEX <table>_tenant_created_idx ON <table>(tenant_id, created_at DESC);
-- Additional compound indexes per query pattern (added when endpoints are implemented)
```

### Audit Log
Append-only `audit_log` table. No UPDATE or DELETE ever runs on it.
```sql
CREATE TABLE audit_log (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL,
  user_id      UUID NOT NULL,
  entity_type  TEXT NOT NULL,
  entity_id    UUID NOT NULL,
  action       TEXT NOT NULL CHECK (action IN ('create','update','delete','archive','submit')),
  before_data  JSONB,
  after_data   JSONB,
  ip_address   TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX audit_log_entity_idx ON audit_log(tenant_id, entity_type, entity_id, created_at DESC);
```

### Pressure Score Storage
Stored on the entity row itself:
```sql
pressure_score      NUMERIC(4,1),   -- total, for display and sorting
pressure_sub        JSONB,          -- {blast_radius: 1.2, slack_penalty: 0.8, ...}
pressure_updated_at TIMESTAMPTZ,    -- when last recalculated
```

---

## ADR-004: Agent framework — PydanticAI + config-driven domain packs
**Status**: Accepted | **Date**: 2026-04-30

**Decision**: Agents are defined as domain-neutral AgentSpec YAMLs (see `agents/specs/`). A domain pack (`domain_packs/transmuter/pack.yaml`) provides project-specific context. PydanticAI is the agent execution framework. OpenRouter is the LLM gateway (model-agnostic).

**Consequences**:
- ✅ Agent configs are declarative, version-controlled, and schema-validated
- ✅ Framework is reusable across future products (new domain pack = new product)
- ⚠️ Agent skill implementations in `apps/api/app/agents/` must be registered against their AgentSpec

---

## ADR-005: Angular frontend — standalone components, lazy routes, CSS variables
**Status**: Accepted | **Date**: 2026-04-30

**Decision**: Angular 21 with standalone components (no NgModules). All routes lazy-loaded. Design tokens via CSS variables (not Tailwind hardcoded classes). Dark theme via `.dark` class on `<html>`.

**Consequences**:
- ✅ Smaller initial bundle (all routes except app shell are lazy)
- ✅ CSS variables enable runtime theme switching without rebuild
- ⚠️ Never use hardcoded hex colours in component styles — always reference `var(--t-*)`

---

## ADR-006: Supabase migrations — canonical directory
**Status**: Accepted | **Date**: 2026-06-12

**Decision**: `supabase/migrations/` is the canonical source of truth for Transmuter database migrations. New migrations must be added there. `infra/supabase/migrations/` is a legacy/deployment subset and must not receive new migration work unless explicitly needed by an infra migration flow.

**Consequences**:
- ✅ Product schema history lives in one complete migration tree.
- ✅ CI checks that any migration duplicated in the legacy infra tree matches the canonical copy.
- ⚠️ The legacy infra subset should be retired once deployment tooling no longer references it.
- ⚠️ Destructive migrations must state rollback category: reversible, forward-fix-only, or requires-backup.

---

## Technical Debt Register

| ID | Description | Priority | Owner |
|---|---|---|---|
| TD-01 | mypy strict mode disabled during ramp-up | Medium | Karya |
| TD-02 | Angular lint rules set to warn-only | Low | Rupa |
| TD-03 | Legacy `infra/supabase/migrations/` subset remains during migration-directory cleanup | Medium | Sthira |
| TD-04 | Pressure score sub-formula B-7 details to confirm with stakeholder | Medium | Karya |

---

## Changelog

### 2026-04-30 — Initial architecture document
- ADR-001: Supabase auth + database
- ADR-002: JWT claims + RLS policy pattern (resolves issue #25)
- ADR-003: DB schema conventions (resolves issue #28)
- ADR-004: Agent framework design
- ADR-005: Angular frontend architecture

### 2026-06-12 — Migration ownership update
- ADR-006: `supabase/migrations/` is canonical for database migrations.
- Added CI drift check for migrations duplicated under `infra/supabase/migrations/`.
