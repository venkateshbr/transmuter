# Aethos Backend Codebase Review

> **Owner**: Karya (Backend Engineer)
> **Last Updated**: 2026-04-03
> **Status**: Living Document

---

## Table of Contents
1. [Backend Architecture Summary](#backend-architecture-summary)
2. [Module Inventory](#module-inventory)
3. [Code Quality Assessment](#code-quality-assessment)
4. [Pattern Compliance Audit](#pattern-compliance-audit)
5. [Security Review](#security-review)
6. [Technical Debt & Bugs](#technical-debt--bugs)
7. [Improvement Recommendations](#improvement-recommendations)

---

## Backend Architecture Summary

The backend is a **FastAPI 0.115+** monolith running on **Python 3.12+**, deployed with Uvicorn. It connects to **Supabase (PostgreSQL 15+)** via the Supabase Python client (not raw asyncpg). AI agents use **PydanticAI** with models routed through **OpenRouter**.

### Architecture Layers
```
┌─ API Layer (33 routers, 8,632 LoC) ──────────────────────────┐
│  Thin routers, auth via get_current_user, rate limiting       │
├─ Service Layer (23 services, 2,950 LoC) ─────────────────────┤
│  Business logic, inherits BaseService for tenant-scoped CRUD  │
├─ Agent Layer (35 agent files, 24 registered) ─────────────────┤
│  PydanticAI agents with structured outputs, audit logging     │
├─ Repository Layer (7 repos) ─────────────────────────────────┤
│  Typed CRUD wrappers (partial coverage)                       │
├─ Domain Layer (6 modules) ───────────────────────────────────┤
│  Rules, Money, Enums, Events, Journal Patterns                │
├─ Core Layer (7 modules) ─────────────────────────────────────┤
│  Auth/RBAC, Config, DB, Logging, Sanitization, Task Queue     │
└──────────────────────────────────────────────────────────────┘
```

### Key Infrastructure
- **Background Worker**: Custom polling worker (not Celery/Temporal), reads `procrastinate_jobs` table, runs agents per tenant
- **Event Bus**: In-process async pub/sub (`app/events/bus.py`), 4 handlers (journal, notification, agent trigger, anomaly)
- **Rate Limiting**: SlowAPI with `get_remote_address`
- **Observability**: Optional Logfire integration (Pydantic Logfire)
- **Security**: JWT auth + legacy X-Tenant-Id headers, RBAC permissions, CORS, security headers middleware

---

## Module Inventory

### API Routers (33 files, 8,632 LoC)

| Phase | Routers | Description |
|-------|---------|-------------|
| Phase 1 | `dashboard`, `accounts`, `contacts`, `invoices`, `payments`, `expenses`, `banking`, `journals`, `reports`, `agents` | Core ERP |
| Phase 2 | `quotes`, `credit_notes`, `items`, `tax_rates`, `tracking`, `purchase_orders`, `fixed_assets`, `settings`, `ai_copilot` | Extended features |
| RBAC | `admin`, `tenants`, `master_data`, `auth` | Multi-tenancy & RBAC |
| Phase 3 | `ap_master`, `workflows` | Enhanced AP |
| Phase 4 | `collections`, `recurring_invoices` | AR & Collections |
| Phase 5 | `budgets` | Budgeting (33KB — largest router) |
| Phase 6 | `gl_enhanced` | Enhanced GL & Reporting |
| Phase 7 | `assets_leasing` | Assets & Leasing |
| Phase 8 | `cost_accounting` | Cost Accounting |
| Phase 9 | `ai_insights` | AI/ML & Messaging |
| Phase 10 | `agent_endpoints` | Agent Direct Endpoints |

### Services (23 files, 2,950 LoC)

All services extend `BaseService` which provides tenant-scoped CRUD helpers (`_query`, `_insert`, `_update`, `_soft_delete`, `_list`, `_find_by_id`, `_require_by_id`).

| Service | LoC | Assessment |
|---------|-----|------------|
| `reporting_service` | 327 | Largest — generates P&L, BS, TB, cashflow |
| `banking_service` | 294 | Bank feed import, reconciliation helpers |
| `invoice_service` | 262 | AR invoice lifecycle |
| `collections_service` | 245 | Overdue tracking, reminder generation |
| `po_service` | 216 | Purchase orders, 3-way matching |
| `base_service` | 168 | Foundation — well-structured |
| Others (17) | ~60-170 each | Standard CRUD services |

### Agents (35 implementation files, 24 registered in registry)

| Domain | Agents | Registration |
|--------|--------|-------------|
| GL | `accounting_guardian`, `period_close`, `depreciation`, `reporting`, `revenue_recognition` | 4 registered, 1 unregistered (`revenue_recognition`) |
| AP | `ap_invoice`, `gl_classifier`, `duplicate_detector` | All registered |
| AR | `ar_invoice`, `payment_matching`, `collections` | All registered |
| Banking | `cash_coding`, `reconciliation` | All registered |
| Intelligence | `anomaly_detection`, `cashflow_forecast`, `budget_variance`, `budget_generator`, `workforce_planning` | All registered |
| Core | `copilot`, `onboarding`, `fx_management`, `recurring_txn` | All registered |
| Contacts | `contact_intelligence` | Registered |
| Tax | `tax_compliance` | Registered |
| Workflows | `smart_approval` | Registered |
| Procurement | `procurement_agent` | **Not registered** |

**Graphs** (5 workflow FSMs): `approval_workflow`, `bank_reconciliation`, `copilot_graph`, `invoice_processing`, `period_end_close`

### Repositories (7 files)
`base_repository`, `contact_repository`, `expense_repository`, `invoice_repository`, `journal_repository`, `payment_repository`

> ⚠️ **Gap**: Only 6 entity repos exist. Many services (banking, quotes, PO, budgets, fixed assets) access Supabase directly via BaseService without a dedicated repository.

### Domain Layer (6 files)
- `money.py` — `Money` value object, `to_money()`, `to_quantity()` using `Decimal`
- `rules.py` — 9 validation rules (VR-01 through VR-11, DE-01)
- `journal_patterns.py` — 8 GAAP journal templates (Invoice, Payment, Depreciation, FX, etc.)
- `events.py` — Domain event base classes
- `enums.py` — Status enums
- `__init__.py` — Exports

### Core Layer (7 files)
- `auth.py` — JWT + RBAC + legacy header auth (269 LoC)
- `config.py` — Settings + per-agent model config (138 LoC)
- `db.py` — Supabase client factory
- `sanitization.py` — SQL injection prevention
- `logging.py` — Logger setup
- `procrastinate_app.py` — Job queue config
- `task_queue.py` — Task queue helpers

---

## Code Quality Assessment

### ✅ Strengths
1. **Consistent service layer pattern** — All services extend `BaseService`, providing uniform tenant-scoped CRUD
2. **Strong financial domain** — `Money` value object uses `Decimal` throughout, GAAP rules enforced, journal balance validation
3. **Agent framework is solid** — `AgentDeps` for dependency injection, `AgentAuditLogger` for append-only audit trails, `run_agent_safe()` for graceful degradation
4. **PII masking** — Card numbers, bank accounts, ABN, IBAN masked before external LLM calls
5. **Security headers** — HSTS, X-Frame-Options, CSP basics in middleware
6. **Soft-delete pattern** — `deleted_at` timestamp, filtered out by default queries
7. **Rate limiting** — SlowAPI integrated at app level
8. **Event bus with isolation** — Per-handler exception isolation prevents cascading failures

### ⚠️ Concerns
1. **Missing type hints** — `BaseService` methods use `Dict[str, Any]` extensively instead of typed Pydantic models
2. **Inconsistent error handling** — Some routers catch exceptions, others let them propagate
3. **Repository layer incomplete** — Only 6 repos; most services bypass the repository pattern and call `self.client.table()` directly
4. **Worker uses `asyncio.run()` inside sync loop** — `worker.py` line 287 calls `asyncio.run()` per tenant, which is inefficient and creates a new event loop each time
5. **Auth legacy path** — Development mode allows unauthenticated access with admin role (intentional but risky)
6. **`datetime.utcnow()` deprecated** — Used in `auth.py` for JWT creation; should use `datetime.now(timezone.utc)`
7. **Logfire import inside audit logger** — `base.py` line 143 imports `logfire` inside a method; will fail silently if Logfire is not installed

---

## Pattern Compliance Audit

| Rule | Status | Notes |
|------|--------|-------|
| Decimal for money | ✅ Compliant | `Money` value object, `to_money()` helper, DB uses `NUMERIC(15,2)` |
| Tenant isolation (RLS) | ✅ Compliant | `BaseService._query()` always adds `.eq("tenant_id", ...)`, `set_tenant_context` RPC for agents |
| Balanced journals | ✅ Compliant | `validate_journal_balance()` in `rules.py`, DB triggers also enforce |
| Posted txn immutability | ✅ Compliant | Corrections via reversing entries in `journal_patterns.py` |
| Agent graceful degradation | ✅ Compliant | `run_agent_safe()` catches all exceptions, returns fallback |
| PII masking before LLM | ✅ Compliant | `mask_pii()` covers cards, bank accounts, ABN, IBAN |
| Agent structured outputs | ✅ Compliant | All agents use PydanticAI with typed output models |
| Service layer pattern | ⚠️ Partial | Routers are thin, but some have business logic (e.g., `budgets.py` at 33KB) |
| Input sanitization | ⚠️ Partial | `sanitize_for_like()` and `sanitize_for_search()` exist but not consistently used |

---

## Security Review

### ✅ Good Practices
- JWT with HS256, configurable expiry, separate dev/prod handling
- RBAC with granular permissions (`require_permission`, `require_any_permission`)
- CORS restricted to configured origins
- SQL injection prevention via Supabase client (parameterized) + sanitization helpers
- Security headers (HSTS, X-Frame-Options, X-XSS-Protection)
- PII masking before external LLM calls

### ⚠️ Risks
1. **Default JWT secret in dev** — Hardcoded `"aethos-super-secret-key-change-in-production"` in `auth.py:33`
2. **Super admin bypass** — `is_super_admin` users bypass all tenant checks (expected but needs auditing)
3. **No CSRF protection** — API relies on CORS only
4. **No request body size limit** — Could be used for DoS
5. **`HTTP_400_DETAIL`** — Typo in `auth.py:146` — should be `HTTP_400_BAD_REQUEST`

---

## Technical Debt & Bugs

### 🔴 Critical
1. **`auth.py:146`** — `status.HTTP_400_DETAIL` is not a valid status code constant; should be `status.HTTP_400_BAD_REQUEST`. Will crash at runtime on that path.
2. **`auth.py:41-42`** — Uses deprecated `datetime.utcnow()`

### 🟡 Important
3. **`budgets.py` (33KB)** — Largest router, contains significant business logic that belongs in a service. High coupling risk.
4. **Worker asyncio anti-pattern** — `asyncio.run()` per-tenant creates new event loops repeatedly. Should use a single `async` worker with `asyncio.gather()`.
5. **2 unregistered agents** — `revenue_recognition_agent` and `procurement_agent` have implementation files but are not in the registry. They cannot be discovered or configured.
6. **Repository layer gap** — Only 6 of 23+ entities have repositories. Services directly access Supabase, making unit testing harder.

### 🟢 Minor
7. **Logfire import in hot path** — `base.py:143` imports `logfire` inside `log()` method. Should be imported at module level with a try/except guard.
8. **Health check `redis` key** — `main.py:262` checks "redis" but the system uses Procrastinate/PostgreSQL for queues now; the check is misleading.
9. **Legacy `get_query()` in BaseService** — Line 165-167 is marked as kept for backward compatibility. Should be audited and removed.

---

## Improvement Recommendations

### Priority 1 — Fix Bugs
1. Fix `HTTP_400_DETAIL` → `HTTP_400_BAD_REQUEST` in `auth.py`
2. Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` in `auth.py`
3. Register `revenue_recognition_agent` and `procurement_agent` in the registry

### Priority 2 — Architecture
4. Extract business logic from `budgets.py` router into a `BudgetService`
5. Refactor worker to use a proper async event loop instead of `asyncio.run()` per task
6. Expand repository layer to cover all major entities (quotes, POs, budgets, fixed assets, banking)

### Priority 3 — Quality
7. Add type hints to `BaseService` methods with proper Pydantic return types
8. Add consistent input sanitization across all routers that accept search/filter parameters
9. Remove misleading Redis health check; replace with Procrastinate queue health
10. Module-level Logfire import with graceful fallback

### Priority 4 — Testing
11. The repository gap makes unit testing services difficult — expanding repos enables proper mocking
12. Add integration tests for agent audit logging flow

---

## Changelog

### [2026-04-03] - Initial comprehensive review
- Audited full backend: 33 routers (8,632 LoC), 23 services (2,950 LoC), 35 agent files (24 registered), 7 repos, 6 domain modules, 7 core modules
- Found 2 critical bugs (`auth.py` status code typo + deprecated datetime)
- Identified 2 unregistered agents, incomplete repository layer, oversized budget router
- Confirmed compliance on all critical financial patterns (Decimal, RLS, balanced journals, PII masking)
- Documented 12 improvement recommendations across 4 priority tiers
