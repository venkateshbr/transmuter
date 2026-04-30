# Aethos Security Review & Posture

> **Owner**: Prahari (Security Engineer)
> **Last Updated**: 2026-04-25
> **Status**: Living Document — updated after every security review cycle

---

## Table of Contents
1. [Security Posture Summary](#security-posture-summary)
2. [Authentication & Authorization](#authentication--authorization)
3. [Tenant Isolation & RLS Audit](#tenant-isolation--rls-audit)
4. [Agent Security](#agent-security)
5. [API Security](#api-security)
6. [Dependency Vulnerability Status](#dependency-vulnerability-status)
7. [Open Findings](#open-findings)
8. [Architecture Decisions (Security)](#architecture-decisions-security)
9. [Changelog](#changelog)

---

## Security Posture Summary

| Domain | Status | Last Reviewed | Risk Level |
|--------|--------|--------------|------------|
| Authentication (JWT / Supabase) | ✅ Reviewed | 2026-04-25 | Low |
| Tenant Isolation (RLS) | ✅ Reviewed | 2026-04-25 | Low |
| Agent Tool Security | ⚠️ Partial | 2026-04-25 | Medium |
| API Input Validation | ✅ Reviewed | 2026-04-25 | Low |
| PII / Data Masking | ✅ Reviewed | 2026-04-25 | Low |
| Dependency Vulnerabilities | ⚠️ Not automated | — | Medium |
| OWASP Top 10 (2021) | ⚠️ Partial | 2026-04-25 | Medium |
| Secrets Management | ✅ Reviewed | 2026-04-25 | Low |

**Overall Risk: Medium** — No critical findings open. Priority: automate dependency scanning and complete OWASP checklist.

---

## Authentication & Authorization

### Implementation
- **Primary**: Supabase Auth (JWT). `AUTH_PROVIDER=SUPABASE` default.
- **Fallback**: Local JWT (`python-jose[cryptography]`). Used for development.
- **Provider factory**: `app/core/auth.py` — conditionally returns `SupabaseAuthProvider` or `LocalJWTProvider`.
- **Every route**: `Depends(require_permission("resource:action"))` — no unguarded routes.
- **Token injection**: `auth.interceptor.ts` injects bearer token on all frontend requests.

### Verified
- [x] JWT signature verification on every request
- [x] Token expiry enforced
- [x] No PII in JWT payload (user_id and tenant_id only)
- [x] `send_default_pii=False` in Sentry configuration
- [x] Password hashing uses bcrypt (`bcrypt>=4.0.0`)

### Open Questions
- [ ] JWT refresh token rotation — confirm rotation is enforced, not just expiry
- [ ] Session invalidation on password change — verify Supabase handles this

---

## Tenant Isolation & RLS Audit

### Implementation
- Every table has a `tenant_id UUID NOT NULL` column.
- RLS policies enforce: `USING (tenant_id = current_setting('app.current_tenant_id'))`
- `set_tenant_context` RPC called before every query in `AgentAuditLogger._set_tenant_context()`
- Defense-in-depth: application code also `.eq("tenant_id", tenant_id)` on all queries even when RLS active.

### RLS Verification Query (run against Supabase)
```sql
-- Verify all business tables have RLS enabled
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename NOT IN ('schema_migrations')
ORDER BY tablename;

-- Verify no policy gaps (tables with RLS off but should have it)
SELECT t.tablename
FROM pg_tables t
LEFT JOIN pg_policies p ON t.tablename = p.tablename
WHERE t.schemaname = 'public'
  AND p.tablename IS NULL
  AND t.tablename NOT IN ('schema_migrations', 'agent_configurations');
```

### Verified
- [x] RLS active on all financial tables
- [x] `set_tenant_context` called before all DB operations in agent layer
- [x] `get_service_db()` only used intentionally (documented in backend CLAUDE.md)
- [x] Cross-tenant data leak tested in `docs/test/auth_rbac.md` scenario AUTH-003

### Known Gaps
- [ ] Automated RLS regression test — currently manual only

---

## Agent Security

### PII Masking
- `mask_pii()` in `app/agents/base.py` — strips card numbers, bank accounts, AU ABN, IBAN before LLM calls.
- Applied to: agent tool return values, audit log `input_summary`/`output_summary`, Langfuse span attributes.

### Autonomy Level Gating
- `require_permission_for_tool()` decorator in `base.py` enforces L0-L3 gating on all agent tools.
- L0: no-op return. L1/L2: permission check. L3: always allowed.
- `accounting_guardian` runs at L3 always — cannot be disabled.

### Tool Input Validation
- [ ] **Gap**: Agent tool functions should validate LLM-generated inputs before using them in DB queries. Currently, tool args come directly from LLM output. Pydantic tool argument types enforce structure but not semantic validity.
- Recommendation: Add `assert` / Pydantic validators on tool args that touch financial records.

### Agent Secrets
- No raw API keys in agent prompts.
- OpenRouter API key loaded from env only.
- Langfuse keys loaded from env only.

---

## API Security

### Implemented
- [x] Rate limiting: `slowapi` on sensitive endpoints
- [x] Security headers middleware: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `HSTS`, `Referrer-Policy` (in `main.py`)
- [x] CORS: restricted to `CORS_ORIGINS` env var (not `*`)
- [x] Input validation: Pydantic v2 models with field constraints on all request bodies
- [x] No raw SQL string interpolation — Supabase query builder only
- [x] `Decimal` for all monetary fields — no float precision manipulation possible

### Frontend
- [x] No sensitive data in `localStorage` (JWT stored in memory / Supabase session)
- [x] `HttpOnly` cookie for auth token (Supabase default)
- [x] XSS: Angular templates auto-escape; no `[innerHTML]` with user data observed
- [ ] CSP headers — not yet configured
- [ ] Subresource Integrity (SRI) for CDN assets — not configured

---

## Dependency Vulnerability Status

### Current State
- **Backend**: No automated scanning. `pip-audit` not wired into CI.
- **Frontend**: No automated scanning. `npm audit` not in CI.

### Manual Snapshot (2026-04-25)
- No known critical CVEs in `langfuse==4.5.1`, `pydantic-ai==0.8.1`, `fastapi>=0.115.0`, `supabase==2.28.2`
- `python-jose[cryptography]` — watch for CVEs; consider migrating to `PyJWT` (more actively maintained)

### Recommended Actions
- [ ] Add `pip-audit` to GitHub Actions CI (backend)
- [ ] Add `npm audit --audit-level=high` to GitHub Actions CI (frontend)
- [ ] Add `gitleaks` to pre-commit hooks for secret scanning

---

## Open Findings

| ID | Severity | Description | Status | Owner |
|----|----------|-------------|--------|-------|
| SEC-001 | Medium | Agent tool inputs not semantically validated — LLM output used directly as DB query params | Open | Karya + Prahari |
| SEC-002 | Medium | No automated dependency scanning in CI | Open | Sthira |
| SEC-003 | Low | CSP headers not configured on frontend | Open | Rupa |
| SEC-004 | Low | JWT refresh token rotation not explicitly verified | Open | Karya |
| SEC-005 | Low | `python-jose` not actively maintained — consider migration to PyJWT | Backlog | Karya |

---

## Architecture Decisions (Security)

### SAD-001: Supabase RLS for Tenant Isolation (not service-key separation)
- **Decision**: Use PostgreSQL RLS with `set_tenant_context()` rather than separate DB users per tenant.
- **Rationale**: Simpler architecture; Supabase manages connection pooling; defense-in-depth with application-layer `.eq("tenant_id", ...)` on every query.
- **Risk**: A bug in `set_tenant_context()` call could expose cross-tenant data. Mitigated by defense-in-depth.

### SAD-002: PII Masking at Agent Layer (not DB layer)
- **Decision**: PII masked in `mask_pii()` before any LLM call — not at the database query layer.
- **Rationale**: Masking at the boundary closest to the external API (LLM) is the most reliable control point.
- **Patterns masked**: Card numbers (16-digit), bank account numbers, AU ABN, IBAN.

### SAD-003: No Raw PII to External APIs
- **Decision**: `mask_pii()` is mandatory before every `agent.run()` call. Enforced via `AgentAuditLogger`.
- **Scope**: Applies to OpenRouter (LLM), Langfuse (observability), Sentry (`send_default_pii=False`).

---

## Prahari Trigger Conditions

Prahari must be called (Vishwa triggers) in these scenarios:

| Trigger | When |
|---------|------|
| Pre-design review | Vastu ADR involves trust boundary (new auth flow, new external API, tenant data model change) |
| Pre-merge code review | Any PR touching `app/core/auth.py`, `app/core/db.py`, RLS policies, `app/agents/base.py` |
| New third-party integration | Any new external service added (payment processor, OAuth provider, webhook) |
| Agent tool expansion | New agent tool that writes to the database or calls an external API |
| Periodic audit | Quarterly full OWASP Top 10 review |

---

## Changelog

### [2026-04-25] — Initial security review document created
- Established security posture baseline
- Documented authentication, tenant isolation, agent security, and API security
- Opened 5 findings (0 critical, 2 medium, 3 low)
- Documented 3 architecture security decisions (SAD-001 through SAD-003)
- Identified: no automated dependency scanning (SEC-002), no CSP headers (SEC-003)
