# Aethos Test Strategy & Quality Assurance

> **Owner**: Aksha (SDET)
> **Last Updated**: 2026-04-03
> **Status**: Living Document

---

## Table of Contents
1. [Test Infrastructure Summary](#test-infrastructure-summary)
2. [Backend Test Inventory](#backend-test-inventory)
3. [Agent Eval Inventory](#agent-eval-inventory)
4. [Frontend Test Status](#frontend-test-status)
5. [Coverage Analysis](#coverage-analysis)
6. [Gap Assessment](#gap-assessment)
7. [Recommended Test Plan](#recommended-test-plan)

---

## Test Infrastructure Summary

### Transmuter Acceptance Standard
- Smoke tests do not count as acceptance criteria.
- Mocked API responses do not count as acceptance criteria for product workflows.
- Acceptance requires real API tests against a running API and deterministic seeded sample data.
- Acceptance requires browser UI tests against the real Angular app and real API.
- Tests must reset or isolate sample data predictably; no test may depend on manually created browser state.
- Aksha sign-off must include real sample-data UI/API verification for touched workflows.
- Existing unit tests and TestClient tests may remain as developer checks, but they do not replace real API + browser UI acceptance.

### Backend
- **Framework**: pytest + pytest-asyncio
- **Test Files**: 24 (includes scripts and debug files)
- **Actual Test Files**: ~10 (14 are debug/seed/migration scripts)
- **Total Test LoC**: 3,242
- **Agent Evals**: 5 (PydanticAI eval framework)
- **Fixtures**: `conftest.py` with `async_client` (httpx → FastAPI) and tenant headers
- **Test Model**: PydanticAI `TestModel` for deterministic agent testing
- **Commands**: `cd backend && pytest` (all), `cd backend && pytest tests/evals/` (evals only)

### Frontend
- **Framework**: Karma + Jasmine (configured)
- **Test Files**: 5 `.spec.ts` files (loading, theme, auth guard, auth service, toast)
- **Karma config**: `karma.conf.js` ✅
- **tsconfig.spec.json**: ✅
- **angular.json test architect**: ✅
- **Test runner**: `ng test`

---

## Backend Test Inventory

### Test Files (by purpose)

| Category | File | LoC | Purpose |
|----------|------|-----|---------|
| **Integration** | `test_scenarios.py` | 853 | Comprehensive API workflow tests (invoice lifecycle, payments, etc.) |
| **Integration** | `test_phase2.py` | 445 | Phase 2 feature tests (quotes, credit notes, items, etc.) |
| **Integration** | `test_api.py` | 408 | Core API endpoint tests |
| **Unit** | `test_accounting_rules.py` | 355 | GAAP validation rule tests (VR-01..VR-12, DE-01) |
| **Unit** | `test_fastapi_validation.py` | 56 | FastAPI request validation |
| **Unit** | `test_login.py` | 24 | Auth login flow |
| **Unit** | `test_bcrypt.py` | — | Password hashing validation |

### Agent Evals

| Eval File | LoC | Agent Under Test |
|-----------|-----|-----------------|
| `test_duplicate_detection.py` | 292 | `duplicate_detector` |
| `test_ap_invoice_extraction.py` | 203 | `ap_invoice_agent` |
| `test_gl_classification.py` | 194 | `gl_classifier_agent` |
| `test_accounting_guardian_eval.py` | 86 | `accounting_guardian` |
| `test_agent_evals.py` | 52 | Multi-agent eval runner |

### Utility/Debug Scripts (not real tests)

| File | Purpose |
|------|---------|
| `debug_route.py` | Route debugging |
| `debug_login.py` | Login flow debugging |
| `debug_passlib.py` | Password library debugging |
| `track_passlib.py` | Passlib version tracking |
| `check_db.py` | Database connection check |
| `migrate_db.py` | Migration runner |
| `run_migration_018.py` | Specific migration |
| `run_migration_019.py` | Specific migration |
| `seed_venkatesh.py` | Seed data for dev tenant |
| `test_bcrypt_err.py` | Bcrypt error debugging |
| `test_bcrypt_err2.py` | Bcrypt error debugging |

### Test Fixtures (`conftest.py`)
- `async_client`: httpx AsyncClient wired to FastAPI app (no live server needed)
- Hardcoded `TENANT_ID` and `HEADERS` with admin role
- Auth override: injects `CurrentUser` dependency to bypass JWT in tests
- PydanticAI `TestModel` available for deterministic agent behavior

---

## Coverage Analysis

### Backend Coverage Map

| Module | Test Coverage | Assessment |
|--------|--------------|------------|
| **API Routers** (33) | ~5-6 routers tested | **~18%** — Only core routes (invoices, payments, contacts, quotes) |
| **Services** (23) | Indirect via API tests | **Low** — No isolated service unit tests |
| **Agents** (24) | 4 agents have evals | **~17%** — 20 agents have no evals |
| **Domain Rules** (9) | `test_accounting_rules.py` | **~100%** — Well tested |
| **Auth/RBAC** | `test_login.py` | **Minimal** — Basic login only |
| **Event Bus** | None | **0%** |
| **Worker** | None | **0%** |
| **Repositories** | None | **0%** |

### Frontend Coverage
5 spec files (core services + auth guard). Baseline established.

---

## Gap Assessment

### 🔴 Critical Gaps

1. **Frontend: Zero tests** — No unit, integration, or E2E tests exist
2. **20 of 24 agents have no evals** — Only AP Invoice, GL Classifier, Duplicate Detector, and Accounting Guardian are tested
3. **No worker tests** — Background job processing is completely untested
4. **No event bus tests** — Domain event publishing/handling is untested

### 🟡 Important Gaps

5. **Service layer untested** — All 23 services lack isolated unit tests (only tested indirectly via API tests)
6. **Auth/RBAC minimal coverage** — Only basic login tested; permission checks, role hierarchy, JWT refresh untested
7. **No repository tests** — 7 repositories have no tests
8. **Debug scripts mixed with tests** — 11 of 24 "test" files are actually debug/seed/migration scripts, inflating the count
9. **No CI pipeline evidence** — No GitHub Actions, CircleCI, or Jenkins config found
10. **No load/performance tests** — No k6, Locust, or Artillery config

### 🟢 Bright Spots

11. **Accounting rules well-tested** (355 LoC) — GAAP validation rules have thorough coverage
12. **Integration test patterns solid** — `test_scenarios.py` tests full invoice lifecycle
13. **PydanticAI eval framework** in place — Good foundation for expanding agent evals
14. **Test fixtures well-structured** — `conftest.py` provides clean async client and auth mocking

---

## Recommended Test Plan

### Phase 1: Foundation (Week 1-2)

#### Backend
- [ ] Clean up test directory: move debug/seed scripts to `scripts/` folder
- [ ] Add service-layer unit tests for top 5 services: `invoice_service`, `reporting_service`, `banking_service`, `collections_service`, `po_service`
- [ ] Add worker tests: mock job queue, verify agent dispatch
- [ ] Add event bus tests: verify publish/subscribe and handler isolation

#### Frontend
- [ ] Set up Karma/Jasmine or Jest test runner
- [ ] Add tests for `api.service.ts` (mock HttpClient)
- [ ] Add tests for `auth.service.ts` and `auth.guard.ts`
- [ ] Add tests for `auth.interceptor.ts`

### Phase 2: Agent Coverage (Week 3-4)
- [ ] Create evals for high-risk agents: `reconciliation_agent`, `payment_matching_agent`, `cash_coding_agent`, `period_close_agent`, `depreciation_agent`
- [ ] Create evals for intelligence agents: `anomaly_detection_agent`, `cashflow_forecast_agent`, `budget_variance_agent`
- [ ] Standardize eval patterns using `test_agent_evals.py` runner

### Phase 3: E2E & Integration (Week 5-6)
- [ ] Playwright is already configured (`erpcore/frontend/playwright.config.ts`) — write E2E specs
- [ ] Critical flows: Login → Dashboard → Create Invoice → Record Payment → View Reports
- [ ] Agent flows: Trigger agent → View HITL queue → Approve/Reject → Verify audit log
- [ ] Add API integration tests for untested routers (budgets, workflows, collections, fixed assets)

### Phase 4: Quality Gates (Week 7-8)
- [ ] Set up CI pipeline (GitHub Actions)
- [ ] Add coverage thresholds: 60% backend, 40% frontend
- [ ] Add linting gates: `ruff check backend/` + `ng lint`
- [ ] Add pre-commit hooks for test + lint

---

## Test Scenarios Repository

All test scenarios live in **`docs/test/`** — this is the canonical reference for all testing and regression:

| Document | Scenarios | Coverage |
|----------|-----------|----------|
| `regression_suites.md` | Full regression control map | Test layers, gates, execution order, and suite links |
| `agent_scenarios/` | One file per registered runtime ERP agent | Agent-specific data, steps, and assertions |
| `e2e_order_to_cash.md` | 12 | O2C with 7 agents |
| `e2e_procure_to_pay.md` | 10 | P2P with 9 agents |
| `e2e_record_to_report.md` | 12 | R2R with 9 agents |
| `agents.md` | 7 | Cross-agent (HITL, corrections, degradation) |
| `accounting_rules.md` | 14 | GAAP VR-01..VR-12 + DE-01 |
| `auth_rbac.md` | 4 | JWT, RBAC, tenant isolation |

**Total: 59 test scenarios** across 3 E2E processes + 3 cross-cutting domains.

---

## Changelog

### [2026-04-30] - Full regression suite and per-agent scenario catalog
- Added `docs/test/regression_suites.md` as the top-level regression control document.
- Added `docs/test/agent_scenarios/` with one `.md` scenario file per registered runtime ERP agent.
- Updated Aksha's agent context to load the regression map and per-agent catalog at the start of QA work.
- Regression expectation: agent changes require both isolated per-agent tests and linked E2E business-process tests.

### [2026-04-03] - Test scenario repository created
- Created `docs/test/` with 59 scenarios across 6 documents
- 3 E2E process tests: O2C (12), P2P (10), R2R (12)
- Agent test matrix for all 26 registered agents
- GAAP rules + auth/RBAC test scenarios
- All scenarios grounded in actual API endpoints, agent names, and validation rules

### [2026-04-03] - Initial comprehensive audit
- Inventoried all backend tests: 10 real test files (3,242 LoC), 5 agent evals, 11 debug/utility scripts
- Confirmed **zero frontend test coverage** — no .spec.ts files, no Karma/Cypress config
- Identified 4 well-tested agents out of 24 total (17% eval coverage)
- Found accounting rules as only well-tested domain module
- Created phased 8-week test improvement plan across 4 phases
