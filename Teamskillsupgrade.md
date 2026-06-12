# Team Skills Upgrade Plan — Enterprise-Grade SaaS Readiness

> **Status:** Proposal (no code or skill files changed yet)
> **Date:** 2026-06-11
> **Scope:** Review of all agent role/skill files (`agents/`, `agents/skills/`), AI context files (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`), team docs (`docs/team/`), and the live codebase (`apps/api`, `apps/web`, `infra/`, `supabase/`).
> **Owner for triage:** Vishwa (per `docs/team/SDLC_PROTOCOL.md`)

---

## 1. Executive Summary

The Transmuter agent team is **unusually well-documented and disciplined** for its stage. The 10-role structure (Vishwa → Dhruva), the canonical SDLC, and the skills files are concrete and largely *practiced, not just written*: the backend genuinely follows Router → Service → Repository, RLS is on every table, money is `Decimal`/`NUMERIC(15,4)` end-to-end, PII is masked before LLM calls, and audit logging with PII redaction exists (`apps/api/app/repositories/audit.py`).

What separates the current state from **enterprise-grade SaaS** is not architecture — it is *operational maturity and verification depth*:

| Dimension | Current | Enterprise bar |
|---|---|---|
| Frontend test coverage | ~6% (3 spec files / 48 components) | 60%+ on business logic, enforced in CI |
| E2E testing | Custom 2,394-line CDP harness, manual-only | Standard framework (Playwright), gating every PR |
| Backend coverage gate | 80% on **routers only** | Services + repositories included |
| Secrets | Local `.env` (correctly gitignored), no rotation story | Managed secrets + documented rotation runbook |
| Migrations | **Two divergent directories** (`supabase/migrations/` 27 files vs `infra/supabase/migrations/` 10 files) | Single source of truth + drift check in CI |
| Rollback / DR | None documented | Tested rollback per release, backup/restore drills |
| Load / capacity | SLOs defined, never tested | k6/Locust baseline tied to SLOs |
| Context docs | 3 near-duplicate root files with contradictions | One source of truth, freshness audits |
| Compliance posture | Strong technical controls, no compliance mapping | SOC 2-style control matrix, SLA definitions |

The recommendations below upgrade each agent's **skills file** so that the team's written protocols close these gaps — the same way `karya_skills.md`'s Package Verification Protocol institutionalized a real past failure.

---

## 2. Highest-Leverage Fix: Context-File Consolidation

The three root context files have drifted, and drift in instruction files silently degrades every agent session.

### Findings (verified)

1. **Triple redundancy:** `CLAUDE.md` (92 lines), `AGENTS.md` (100 lines), `GEMINI.md` (110 lines) are near-identical, but:
   - `CLAUDE.md` is **stale**: Prahari triggers omit RBAC, billing, and payments (present in `AGENTS.md`/`GEMINI.md`); design-system rules and the key-context-files index are missing.
   - `GEMINI.md` differs from `AGENTS.md` only in formatting — pure maintenance overhead.
2. **Financial precision contradiction:** `docs/team/ARCHITECTURE.md` (dated 2026-04-30) says `NUMERIC(15,2)`; `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, and `domain_packs/transmuter/pack.yaml` all say `NUMERIC(15,4)`. The migrations use 15,4 — ARCHITECTURE.md is wrong.
3. **Design token naming drift:** `agents/chitra.md` specifies slate/indigo/amber Tailwind tokens; `AGENTS.md` and `docs/team/CODEX_CONTEXT.md` describe "deep navy, steel blue, light blue accents." The live app uses CSS variables (`--t-*` in `apps/web/src/styles.css`). Three vocabularies for one palette.
4. **Dual migration directories:** `supabase/migrations/` (27 files) and `infra/supabase/migrations/` (10 files) overlap but are not identical (e.g., `20260502000001_collaboration.sql` exists only in one). No skill file assigns ownership of keeping them coherent.
5. **Missing referenced docs:** `PRD.md`, `DESIGN_SYSTEM.md`, `TEST_STRATEGY.md`, `RUNBOOK.md` are referenced throughout agent role files and the SDLC context-loading tiers but do not exist in `docs/team/`.
6. **Agent autonomy levels (L0–L3)** are used in `netra_skills.md` user-story templates but formally defined nowhere.

### Recommendations

- **R2.1** — Make `AGENTS.md` the single source of truth. Reduce `CLAUDE.md` and `GEMINI.md` to a short preamble + "the canonical rules live in AGENTS.md" pointer (both Claude Code and Gemini read referenced files fine). Assign Vishwa as owner with a documented sync rule if full duplication must remain.
- **R2.2** — Fix `CLAUDE.md` Prahari trigger list (add RBAC, billing, payments) immediately if R2.1 is deferred.
- **R2.3** — Correct `ARCHITECTURE.md` to `NUMERIC(15,4)` and add a changelog entry; add a quarterly doc-freshness review to Vishwa's rhythm (see §3.1).
- **R2.4** — Reconcile design vocabulary: Chitra to publish `docs/team/DESIGN_SYSTEM.md` mapping the marketing palette names → CSS variables (`--t-*`) → Tailwind classes, and update `chitra.md`/`rupa_skills.md` to reference it instead of inlining tokens.
- **R2.5** — Declare **one** migrations directory canonical (recommend `supabase/migrations/` since it is the fuller set), document the decision as an ADR (Vastu), and add a CI drift check (Sthira) that fails if the two diverge until the duplicate is removed.
- **R2.6** — Create the four missing docs with their natural owners: `PRD.md` (Netra), `DESIGN_SYSTEM.md` (Chitra), `TEST_STRATEGY.md` (Aksha), `RUNBOOK.md` (Sthira).
- **R2.7** — Vastu to write a one-page **Agent Autonomy Levels spec** (L0 suggest-only → L3 autonomous-with-audit) in `docs/team/` and reference it from `pack.yaml` and `netra_skills.md`.

---

## 3. Per-Agent Skill Upgrades

Each section: what the agent's skill file already does well, the gap observed in the **actual code**, and the concrete skill additions.

### 3.1 Vishwa (CPTO / Orchestrator) — `agents/vishwa.md`, `agents/skills/vishwa_skills.md`

**Strengths:** Clear triage matrix, issue lifecycle enforcement, code-review checklist, 95% confidence gate.

**Gaps observed:** No release-management discipline (squash-merge to main is defined, but no versioning/changelog/go-no-go); doc drift (§2) shows nobody audits instruction freshness; `docs/team/LAUNCH_READINESS_CHECKLIST.md` exists but is not wired into Vishwa's protocol.

**Add to `vishwa_skills.md`:**
1. **Release Management Protocol** — semantic version tagging, generated changelog per release, go/no-go checklist that references `LAUNCH_READINESS_CHECKLIST.md`, and a rule that production deploys map to a tagged release (today `infra/hostinger/deploy.sh` deploys whatever is staged).
2. **Quarterly Doc-Freshness Audit** — diff `CLAUDE.md`/`AGENTS.md`/`GEMINI.md`, verify `ARCHITECTURE.md` ADRs against reality, check that referenced docs exist. Output: a `type:chore` issue per stale doc.
3. **Risk Register Cadence** — a lightweight monthly review of open `priority:high` issues + Prahari findings + Dhruva SLO reports, producing a top-5 risk list in the issue tracker.

### 3.2 Vastu (Chief Architect) — `agents/vastu.md`, `agents/skills/vastu_skills.md`

**Strengths:** ADR template, multi-tenant checklist, STRIDE threat modeling — genuinely good.

**Gaps observed:** No capacity/scale review skill (SLOs like `api_p99_slo_ms=2000` exist in `apps/api/app/core/observability.py` but no load model validates them); no DR/RPO-RTO architecture; migrations are forward-only with no rollback design standard; `ARCHITECTURE.md` staleness (§2.3).

**Add to `vastu_skills.md`:**
1. **Capacity & Scale Review Template** — expected tenants/users/requests per endpoint class, DB connection budget (Supabase pooling limits), worker queue throughput, and a rule: any new feature touching portfolio-wide queries (e.g., the financial grid in `apps/api/app/services/financial.py`) gets a query-plan review.
2. **DR / Business Continuity Skill** — define RPO/RTO targets per data class (financial entries vs. UI preferences), document the Supabase backup posture for the self-hosted Hostinger instance, and require a restore-tested backup before any tenant-facing SLA is offered.
3. **Migration Rollback Design Standard** — every migration PR must state its rollback strategy (reversible / forward-fix-only / requires-backup), reviewed by Vastu for destructive changes. Today no migration in `supabase/migrations/` documents rollback.
4. **ADR for the canonical migrations directory** (R2.5).

### 3.3 Netra (Product Manager) — `agents/netra.md`, `agents/skills/netra_skills.md`

**Strengths:** User-story template with agent-autonomy level and HITL checkpoint; PRD template; competitive analysis framework.

**Gaps observed:** No enterprise-buyer lens — nothing in the skills about compliance, SLAs, data residency, or plan entitlements, yet billing/Stripe is live (`docs/team/SAAS_ONBOARDING_SUBSCRIPTION_PLAN.md`, `test_platform_billing_routes.py`). `PRD.md` referenced but missing.

**Add to `netra_skills.md`:**
1. **Compliance Requirements Matrix** — a template mapping enterprise-buyer asks (SOC 2 control areas, GDPR data-subject rights, data residency, retention/deletion policy) to existing technical controls (RLS, audit log, PII masking) and gaps. This becomes the seed for any future compliance effort and a sales asset.
2. **SLA Definition Template** — uptime target, support response tiers, RPO/RTO commitments (sourced from Vastu's DR work), and the rule that no SLA is published without Sthira/Vastu sign-off.
3. **Plan & Entitlement Requirements Skill** — a structured way to specify feature gating per subscription plan (seats, initiative counts, AI usage quotas) so Karya doesn't invent entitlement logic ad hoc.
4. **Author `docs/team/PRD.md`** (R2.6) — the context-loading tiers in the SDLC require it for Vastu/Netra sessions.

### 3.4 Chitra (Frontend Design Lead) — `agents/chitra.md`, `agents/skills/chitra_skills.md`

**Strengths:** Component spec template, WCAG 2.1 AA quick reference with pre-computed contrast ratios, agent UI patterns (confidence meter, HITL dialog).

**Gaps observed:** No component-library governance — 48 components with ad-hoc shared pieces in `apps/web/src/app/shared/`; no visual-regression process; accessibility is "ARIA labels present" but never machine-verified; theme selection is not persisted (resets on refresh — `apps/web/src/app/core/services/theme.service.ts`); token naming drift (§2.4).

**Add to `chitra_skills.md`:**
1. **Design System Documentation Skill** — own `docs/team/DESIGN_SYSTEM.md` as the single token/palette/typography source (R2.4); skill includes the update protocol when tokens change.
2. **Component Library Governance** — criteria for promoting a feature component to `shared/`, a component inventory checklist, and (P2) a Storybook adoption plan with visual-regression snapshots as the design QA gate.
3. **Automated Accessibility Audit Protocol** — run axe-core (or pa11y) against key routes per release; define the severity rubric; hand violations to Rupa as `type:bug`. Target: axe checks in CI (with Aksha/Sthira).
4. **Theme & Preference UX Standard** — require persistence of theme (and future user preferences) across sessions; spec the storage mechanism with Rupa (localStorage for theme is acceptable; JWT stays out of localStorage per `rupa_skills.md`).

### 3.5 Karya (Backend Engineer) — `agents/karya.md`, `agents/skills/karya_skills.md`

**Strengths:** The strongest skills file in the repo — Package Verification Protocol, service-layer templates, PydanticAI integration patterns, migration checklist, secure-coding checklist. The code shows it works.

**Gaps observed:** Coverage gate is routers-only (`--cov=app/routers --cov-fail-under=80` in `.github/workflows/ci.yml`) — services and repositories, where the business logic lives, are unmeasured. Only **one** background job exists (`apps/api/app/jobs/status_nudges.py`) with no retry policy or dead-letter handling. No API versioning/deprecation policy. No graceful-shutdown handling (SIGTERM can cut in-flight requests during Hostinger deploys).

**Add to `karya_skills.md`:**
1. **Coverage Standard Extension** — new/changed services and repositories require tests; coordinate with Aksha/Sthira to extend the CI gate to `--cov=app` with a realistic ratcheting threshold (start at measured baseline, raise per quarter).
2. **Background Job Reliability Pattern** — for every Procrastinate task: idempotency key, explicit retry policy (`retry=` strategy), failure alerting via the existing `record_worker_job()` metrics, and a documented dead-letter/quarantine approach for jobs that exhaust retries. Today a failed nudge run is silently lost.
3. **API Versioning & Deprecation Policy** — rules for breaking-change detection (response shape, status codes), a deprecation window convention, and OpenAPI doc discipline (FastAPI generates the spec — the skill is keeping summaries/response models accurate and publishing `/docs` access policy).
4. **Graceful Shutdown Checklist** — uvicorn lifespan handling, draining in-flight requests, worker `--stop-when-empty`-style shutdown on deploy; pairs with Sthira's deploy script.
5. **Webhook Integrity Pattern** — Stripe webhooks are live; codify signature verification, idempotent event processing, and replay handling as a reusable template (extend the existing secure-coding section).

### 3.6 Rupa (UI Engineer) — `agents/rupa.md`, `agents/skills/rupa_skills.md`

**Strengths:** Angular standalone/signals patterns, theme compliance checklist, frontend security checklist (no `innerHTML`, JWT in memory, no autocomplete on sensitive fields).

**Gaps observed — this is the largest single skills gap in the team:**
- **~6% unit test coverage** (3 spec files for 48 components; e.g., `dashboard.component.ts`, `initiatives/detail`, `meetings/live-session` are all untested).
- **Bare `catch {}` blocks** swallow errors with no user feedback (e.g., `pipeline.component.ts`, `dashboard.component.ts`, `ai-insights.component.ts`).
- `ApiService` (`apps/web/src/app/core/services/api.service.ts`) has no retry, timeout, or backoff.
- No frontend error tracking (Sentry exists backend-side only; `core/observability/` has a stub).
- Note: `rupa.md` says Angular 19 / NgRx Signal Store; the app is on **Angular 21** with plain service signals — the role file itself is stale.

**Add to `rupa_skills.md`:**
1. **Component Testing Skill (P0)** — Vitest + Angular TestBed patterns for the project's actual idioms (signal-based services, lazy routes, HttpTestingController); a Definition-of-Done rule: *no new/changed component without a spec covering its logic*; target 60% coverage on `features/` and `core/`, ratcheted in CI.
2. **Centralized Error Handling Pattern (P0)** — an Angular `ErrorHandler` + notification/toast service; explicit ban on empty `catch` blocks (add to the checklist: "every catch either recovers, notifies the user, or reports to telemetry — never silent"); a `catch {}`-free sweep of existing components as a `type:task`.
3. **API Client Resilience Pattern** — RxJS `retry` with backoff for idempotent GETs, `timeout` defaults, typed error mapping in `ApiService`; pairs with the error handler.
4. **Frontend Observability Skill** — wire Sentry browser SDK (DSN already in env scheme), capture unhandled errors + route-change breadcrumbs, mask PII before sending (same rule as backend).
5. **Refresh `rupa.md`** — Angular 21, signals-first state (document when a store library would actually be warranted instead of prescribing NgRx that isn't used).

### 3.7 Aksha (SDET) — `agents/aksha.md`, `agents/skills/aksha_skills.md`

**Strengths:** The no-smoke-test/no-mock acceptance standard is excellent and rare; security test patterns (tenant isolation, auth bypass); financial-correctness tests.

**Gaps observed:** The acceptance standard is **not enforceable today** — the e2e suite is a custom Chrome DevTools Protocol harness (`apps/web/e2e/real-ui-acceptance.mjs`, 2,394 lines of raw CDP/WebSocket handling) that runs only manually; acceptance tests (`apps/api/tests/acceptance/`) are excluded from CI; no deterministic data-reset command exists (seeding is one-shot via `scripts/pilot/` SQL and `apps/api/scripts/seed_users.py`); no load testing despite defined SLOs. The skills file references **Cypress** patterns that don't match the actual harness.

**Add to `aksha_skills.md`:**
1. **Playwright Migration Skill (P0)** — replace the custom CDP client with Playwright: built-in waiting, trace/screenshot/video on failure, parallelism, CI reporters. Port the existing `real-ui-acceptance.mjs` scenarios (login, signup, session expiry, core flows) as the seed suite. Remove the stale Cypress references.
2. **E2E-in-CI Gating Protocol (P0)** — define the CI job: boot API + web via `infra/docker-compose.dev.yml`, seed deterministic data, run Playwright suite, gate merges to main. Coordinate with Sthira on the workflow change.
3. **Deterministic Data Reset Skill** — a `make test-reset` (or script) that drops/reseeds the test tenant to a known state; the acceptance standard already *requires* "tests must reset or isolate sample data predictably" — give it an implementation. Own the seed-data fixtures as versioned artifacts.
4. **Load & Performance Baseline Skill** — k6 (or Locust) scenarios for the top endpoints (portfolio grid, dashboard, meetings), run pre-release, asserting the SLOs in `observability.py` (API p99 < 2000ms, agent p95 < 12s). First run establishes the baseline; regressions become `type:bug`.
5. **Coverage Gap Reporting** — a per-release report of true coverage (services/repos/frontend, not just routers) feeding the ratchet thresholds; author `docs/team/TEST_STRATEGY.md` (R2.6) capturing the full test taxonomy and gates.

### 3.8 Sthira (SRE) — `agents/sthira.md`, `agents/skills/sthira_skills.md`

**Strengths:** Package installation protocol, CI/CD template with SAST/secrets scanning (gitleaks is live in CI), runbook template, observability and infra-security checklists, breach-response steps.

**Gaps observed:** No secrets *lifecycle* (local `.env` with real keys is gitignored — good — but there is no rotation schedule or manager); no backup/restore drills for the self-hosted Supabase on Hostinger; `infra/hostinger/deploy.sh` has no rollback path (stops old containers, builds new — a bad build means downtime); no uptime monitoring/alerting beyond Sentry error events; migration-drift risk (§2.5); worker has no documented lifecycle in deploys.

**Add to `sthira_skills.md`:**
1. **Secrets Lifecycle Runbook (P0)** — inventory of all secrets (JWT, OpenRouter, Langfuse, Stripe, encryption key, DB), rotation cadence per secret class, exact rotation steps for the Hostinger stack, and a pre-commit gitleaks hook so secret-scanning happens before push, not just in CI.
2. **Backup & Restore Drill Skill (P0)** — scheduled pg_dump (or Supabase backup) for the self-hosted instance, off-VPS storage, and a quarterly *restore test* documented in `RUNBOOK.md`. An untested backup is not a backup; today there is none visible at all.
3. **Deployment Rollback Procedure** — keep the previous image/bundle, define a one-command rollback in `deploy.sh` (re-tag + compose up), healthcheck-gated cutover; document expected downtime. Pairs with Vishwa's release tagging (3.1.1).
4. **Uptime & Alerting Skill** — external uptime probe on `/health` for API and web, alert routing (the P1/P2 webhook already exists in `observability.py` — extend to availability), and a basic alert-response runbook entry.
5. **Migration Drift CI Check** — fail CI if `supabase/migrations/` and `infra/supabase/migrations/` diverge (until R2.5 removes one); also verify migration filename ordering/uniqueness.
6. **Worker Operations Section** — Procrastinate worker deploy/restart sequencing, queue-depth alerting (Dhruva's SLO of < 50 exists but nothing measures it in prod), and dead-letter triage steps.
7. **Author `docs/team/RUNBOOK.md`** (R2.6) consolidating the above with the existing runbook template.

### 3.9 Prahari (Security Engineer) — `agents/prahari.md`, `agents/skills/prahari_skills.md`

**Strengths:** Exceptional — full OWASP Top 10 mapping with project-specific checks, tenant-isolation audit SQL, JWT review procedure, CI security pipeline, severity rubric. The code reflects it: rate-limited auth, security headers, CSP, Fernet-encrypted integration tokens.

**Gaps observed:** No token-revocation mechanism (JWTs valid until expiry; a compromised token can't be killed); CSRF posture for the SPA is undocumented (Bearer-token SPAs are largely CSRF-resistant, but the cookie/refresh-token flow should be explicitly analyzed); dependency pinning/SBOM not audited as a routine; tenant-isolation audit is on-demand only, not a recurring regression suite; positive finding worth recording — `.env` is **not** committed (verified via `git ls-files`), keep it that way.

**Add to `prahari_skills.md`:**
1. **RLS Regression Suite (recurring)** — promote the on-demand tenant-isolation audit SQL into an automated pytest suite (`test_rls_behavior.py` exists — extend it to cover every table whenever a migration adds one) run in CI; a new table without an RLS test fails the build.
2. **Token Revocation & Session Review** — analyze and document the revocation story (short expiry + refresh rotation vs. denylist), the refresh-token storage/rotation flow in `auth.interceptor.ts` and `routers/auth.py`, and password-change/forced-logout semantics.
3. **CSRF Posture Statement** — explicit analysis of the SPA auth model (Bearer header, no auth cookies → CSRF-safe; if cookies are ever introduced, SameSite + CSRF tokens become mandatory). Add to the OWASP A01 section.
4. **Dependency & SBOM Audit Cadence** — monthly `pip-audit`/`npm audit` review beyond CI gating, exact-version pinning verification, Docker base-image digest pinning (currently `python:3.12-slim` and `nginx:1.27-alpine` are tag-pinned, not digest-pinned).
5. **Git-History Secret Scan Cadence** — periodic full-history gitleaks scan (CI scans diffs; history scans catch anything that slipped in before the gate existed).

### 3.10 Dhruva (Data & Analytics) — `agents/dhruva.md`, `agents/skills/dhruva_skills.md`

**Strengths:** Concrete SQL-driven weekly agent-quality review, correction-rate thresholds with decision rules, Langfuse dataset/eval workflow, SLO report template.

**Gaps observed:** No LLM **cost** observability (OpenRouter spend per tenant/agent is unmeasured — an enterprise SaaS needs unit economics and abuse detection); SLO monitoring covers agents but not frontend (no error-rate or web-vitals signal — pairs with Rupa's missing Sentry); no data-retention policy monitoring (audit log and agent logs grow unbounded).

**Add to `dhruva_skills.md`:**
1. **LLM Cost Observability Skill** — capture token usage/cost per agent run (Langfuse already records usage; add the cost rollup), report cost-per-tenant monthly, alert on anomalous spend (runaway loops, abuse), and feed Netra's plan-entitlement quotas (3.3.3).
2. **Frontend Health SLOs** — once frontend Sentry lands (3.6.4): JS error rate, route-level p75 load time, and a weekly trend line in the existing SLO report.
3. **Data Retention Monitoring** — define retention windows per table class with Vastu (audit log, agent_audit_log, corrections), monitor table growth, and flag when retention jobs are needed — this also feeds Netra's GDPR matrix (3.3.1).

---

## 4. Cross-Cutting Process Upgrades

These change shared artifacts (SDLC, CI, Definition of Done) rather than one agent's file.

1. **CI gate additions** (`.github/workflows/ci.yml`, owner Sthira, P0–P1):
   - New **e2e job**: compose up → seed → Playwright suite (after 3.7.1/3.7.2).
   - Run `apps/api/tests/acceptance/` against the composed stack (currently excluded).
   - **Frontend coverage threshold** (start at measured baseline, ratchet quarterly).
   - Backend coverage widened from `app/routers` to `app` (ratcheted).
   - **Migration drift check** (3.8.5).
   - axe-core accessibility check on key routes (3.4.3).
2. **Definition of Done amendments** (`docs/team/SDLC_PROTOCOL.md`, owner Vishwa):
   - Frontend: "component has unit spec covering its logic" and "no silent catch blocks."
   - Backend: "background jobs declare retry/idempotency behavior" and "migration PR states rollback strategy."
   - All: "secrets touched → rotation runbook updated."
3. **Quarterly rhythm additions:** Vishwa doc-freshness audit (3.1.2), Sthira restore drill (3.8.2), Prahari history scan (3.9.5), Dhruva cost report (3.10.1).

---

## 5. Prioritized Roadmap

Priorities follow the SDLC label scheme so Vishwa can convert rows directly into GitHub issues.

### P0 — Do first (production-risk or foundation for everything else)

| # | Item | Owner | Type | Ref |
|---|---|---|---|---|
| 1 | Secrets lifecycle runbook + pre-commit gitleaks + rotation of any long-lived keys | Sthira (Prahari review) | task | 3.8.1 |
| 2 | Backup + tested restore for self-hosted Supabase (Hostinger) | Sthira | task | 3.8.2 |
| 3 | Resolve dual migration directories (ADR + CI drift check) | Vastu + Sthira | chore | R2.5 |
| 4 | Playwright migration of e2e suite | Aksha | task | 3.7.1 |
| 5 | E2E + acceptance tests gating CI | Aksha + Sthira | task | 3.7.2, §4.1 |
| 6 | Centralized frontend error handling (ban silent catch) | Rupa | task | 3.6.2 |
| 7 | Frontend component-testing skill + DoD rule | Rupa + Aksha | task | 3.6.1 |
| 8 | Context-file consolidation + contradiction fixes | Vishwa | chore | R2.1–R2.4 |

### P1 — High impact

| # | Item | Owner | Type | Ref |
|---|---|---|---|---|
| 9 | Deployment rollback procedure + release tagging | Sthira + Vishwa | task | 3.8.3, 3.1.1 |
| 10 | Coverage gates widened (backend full-app, frontend threshold) | Aksha + Karya + Rupa | task | 3.5.1, §4.1 |
| 11 | Background-job reliability (retry, idempotency, DLQ, alerts) | Karya | task | 3.5.2 |
| 12 | Uptime monitoring + alert routing | Sthira | task | 3.8.4 |
| 13 | RLS regression suite auto-covering new tables | Prahari + Aksha | task | 3.9.1 |
| 14 | Frontend Sentry + API client resilience | Rupa | task | 3.6.3, 3.6.4 |
| 15 | Missing docs: PRD, DESIGN_SYSTEM, TEST_STRATEGY, RUNBOOK + L0–L3 spec | Netra/Chitra/Aksha/Sthira/Vastu | chore | R2.6, R2.7 |
| 16 | Token revocation & CSRF posture review | Prahari | spike | 3.9.2, 3.9.3 |

### P2 — Maturity build-out

| # | Item | Owner | Type | Ref |
|---|---|---|---|---|
| 17 | Load-test baseline tied to SLOs (k6) | Aksha | task | 3.7.4 |
| 18 | LLM cost observability per tenant | Dhruva | task | 3.10.1 |
| 19 | Compliance matrix + SLA templates | Netra | spike | 3.3.1, 3.3.2 |
| 20 | DR/RPO-RTO architecture + capacity review skills | Vastu | task | 3.2.1, 3.2.2 |
| 21 | Storybook + visual regression | Chitra + Rupa | spike | 3.4.2 |
| 22 | axe-core accessibility CI check | Chitra + Sthira | task | 3.4.3 |
| 23 | API versioning/deprecation policy + graceful shutdown | Karya | task | 3.5.3, 3.5.4 |
| 24 | Digest-pinned Docker bases + SBOM cadence | Prahari + Sthira | chore | 3.9.4 |
| 25 | Data retention policy + monitoring | Dhruva + Vastu | spike | 3.10.3 |
| 26 | IaC evaluation (Terraform for the Hostinger/Traefik stack) | Sthira | spike | — |

---

## 6. What NOT to change

Worth stating, since enterprise upgrades often regress what already works:

- **Keep** the no-mock acceptance standard — make it enforceable (CI) rather than diluting it.
- **Keep** the Package Verification Protocol and Vishwa-first triage — these prevent real failure modes.
- **Keep** the Decimal/RLS/PII-masking non-negotiables exactly as written; the code complies today.
- **Keep** service-signal state management on the frontend — do not adopt NgRx preemptively; revisit only if real cross-component state pain appears (and fix `rupa.md`, which currently prescribes a store the app doesn't use).
