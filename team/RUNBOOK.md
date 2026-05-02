# Aethos Operational Runbook

> **Owner**: Sthira (SRE)
> **Last Updated**: 2026-04-03
> **Status**: Living Document

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Infrastructure Inventory](#infrastructure-inventory)
3. [Deployment & Operations](#deployment--operations)
4. [CI/CD Pipeline](#cicd-pipeline)
5. [Database Management](#database-management)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security Posture](#security-posture)
8. [Incident Response](#incident-response)
9. [Gap Assessment](#gap-assessment)
10. [Improvement Recommendations](#improvement-recommendations)

---

## System Overview

```
                    ┌─────────────┐
     Users ───────▶ │  Frontend   │ (Angular 18, port 4300)
                    │  (Nginx)    │
                    └──────┬──────┘
                           │ HTTP
                    ┌──────▼──────┐
                    │   Backend   │ (FastAPI, port 8010)
                    │  (Uvicorn)  │
                    └──┬─────┬───┘
                       │     │
              ┌────────▼┐  ┌─▼────────┐
              │ Supabase │  │  Worker  │ (Procrastinate)
              │ (PG 15+) │  │ (Async)  │
              └──────────┘  └──────────┘
                       │
              ┌────────▼─────────┐
              │   OpenRouter     │ (LLM API)
              └──────────────────┘
```

### Service Inventory

| Service | Technology | Port | Purpose |
|---------|-----------|------|---------|
| Backend | FastAPI + Uvicorn | 8010 | API + agent orchestration |
| Worker | Procrastinate + PG | — | Background agent jobs |
| Frontend | Angular 18 + Nginx | 4300 (dev), 80 (prod) | Web UI |
| Database | Supabase (PG 15+) | — | Cloud-managed PostgreSQL |
| LLM Gateway | OpenRouter | — | AI model routing |
| Observability | Logfire (optional) | — | Traces + metrics |

---

## Infrastructure Inventory

### Docker Setup
- **`docker-compose.yml`** — 3 services: `aethos-backend`, `aethos-worker`, `aethos-frontend`
- Backend/worker share the same `Dockerfile` (backend context)
- Frontend has its own `Dockerfile`
- Comment indicates Redis was removed, migrated to Procrastinate (PostgreSQL-based queue)

### Dependencies (pyproject.toml)
| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | ≥0.115.0 | Web framework |
| `pydantic` | ≥2.10.0 | Data validation |
| `pydantic-ai` | 0.8.1 (pinned) | Agent framework |
| `pydantic-graph` | 0.8.1 (pinned) | Workflow FSMs |
| `supabase` | 2.28.2 (pinned) | Database client |
| `uvicorn` | 0.29.0 (pinned) | ASGI server |
| `httpx` | ≥0.28.1 | HTTP client |
| `logfire` | ≥0.5.1 | Observability |
| `procrastinate` | ≥2.0.0,<3.0.0 | Job queue |
| `slowapi` | ≥0.1.9 | Rate limiting |
| `python-jose` | ≥3.3.0 | JWT tokens |
| `bcrypt` | ≥4.0.0 | Password hashing |

### Database Migrations
| File | Size | Description |
|------|------|-------------|
| `schema_clean_migration.sql` | 60KB | Initial clean schema |
| `20260315120000_consolidated_schema.sql` | 108KB | Full consolidated schema |
| `20260316224000_add_agent_telemetry.sql` | 266B | Agent telemetry addition |

---

## Deployment & Operations

### Development Setup
```bash
# Backend
cd backend && uvicorn app.main:app --reload --port 8010

# Worker (separate terminal)
cd backend && procrastinate --app=app.core.procrastinate_app.app worker

# Frontend
cd frontend && ng serve
```

### Docker Setup
```bash
docker-compose up -d
```

### Environment Variables Required
| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `SUPABASE_URL` | ✅ | — | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | ✅ | — | Supabase service role key |
| `SUPABASE_ANON_KEY` | ✅ | — | Supabase anon key |
| `JWT_SECRET` | ✅ (prod) | dev default | JWT signing key |
| `ENVIRONMENT` | — | `development` | `development` / `production` |
| `OPENROUTER_API_KEY` | ✅ | — | LLM API access |
| `PROCRASTINATE_DATABASE_URL` | ✅ (worker) | — | Worker DB connection |
| `LOGFIRE_TOKEN` | — | — | Optional observability |

---

## CI/CD Pipeline

### GitHub Actions (`ci.yml`)
- **Triggers**: Push to `main`, PRs targeting `main`
- **Backend job**: Python 3.11 + `uv` → install → `pytest tests/ -v`
- **Frontend job**: Node 20 → `npm ci` → `npm run test --watch=false --browsers=ChromeHeadless`

> ⚠️ **Issue**: Frontend tests job exists in CI but there are **zero test files** — this job will fail or be a no-op.

### Missing from CI
- No lint step (`ruff check backend/`)
- No `ng lint` for frontend
- No build verification (`ng build --configuration=production`)
- No Docker image building
- No deployment step (no CD)
- No migration validation

---

## Monitoring & Observability

### Current State
- **Logfire**: Optional integration in `AgentAuditLogger` — logs agent latency and confidence warnings
- **Python logging**: Standard library logging with `aethos.*` namespace
- **Health endpoint**: `/health` at app level (checks DB connectivity)
- **Audit log**: `agent_audit_log` table captures all agent actions

### Missing
- No application metrics (Prometheus/Datadog)
- No error tracking (Sentry)
- No uptime monitoring
- No alerting system
- No log aggregation (ELK/Loki)
- No APM beyond optional Logfire

---

## Security Posture

### ✅ Implemented
| Control | Status |
|---------|--------|
| JWT authentication | ✅ HS256, 24h expiry |
| RBAC permissions | ✅ Granular per-endpoint |
| Row-Level Security | ✅ Supabase RLS on all tables |
| PII masking | ✅ Before external LLM calls |
| CORS | ✅ Configured origins only |
| Security headers | ✅ HSTS, X-Frame-Options, CSP |
| Rate limiting | ✅ SlowAPI |
| Input sanitization | ⚠️ Partial (exists but inconsistent) |

### ⚠️ Gaps
| Gap | Severity | Description |
|-----|----------|-------------|
| No secrets management | High | Env vars/`.env` files — no Vault/AWS SecretsManager |
| No CSRF protection | Medium | API relies on CORS only |
| No request size limits | Medium | No body size enforcement |
| Default JWT secret in dev | Low | Expected but could leak to prod |
| No WAF | Low | No web application firewall |

---

## Service Level Objectives (SLOs)

Measurable reliability targets. Violation of any SLO triggers a P2 incident.

| SLO | Target | Measurement | Alert Threshold |
|-----|--------|-------------|-----------------|
| **API availability** | 99.9% uptime/month | `/health` success rate | < 99.5% over 5 min |
| **API latency (P99)** | < 2,000 ms | All `/api/v1/*` endpoints | P99 > 2,000 ms over 5 min |
| **Journal entry creation** | P99 < 500 ms | `POST /api/v1/journals` | P99 > 500 ms over 5 min |
| **Agent HITL queue** | < 30 min median human review | `requires_review=true` → `human_action` set | > 60 min with no action |
| **Agent execution** | P95 < 8,000 ms | `agent_audit_log.latency_ms` | P95 > 10,000 ms over 10 min |
| **Agent accuracy** | Correction rate < 10% per agent | `agent_corrections` / `agent_audit_log` ratio | > 15% in 7-day window |
| **Worker queue depth** | < 50 pending jobs | `procrastinate_jobs WHERE status='todo'` | > 100 jobs pending > 10 min |
| **LLM error rate** | < 1% | OpenRouter 5xx via `agent_audit_log` errors | > 5% over 5 min |

**Error budget**: 99.9% uptime = 43.8 min/month downtime budget. Track monthly.

---

## Incident Response

### Severity Matrix

| Severity | Definition | Response Time | Examples |
|----------|-----------|---------------|---------|
| **P1 — Critical** | Data loss, security breach, complete outage, financial data corruption | < 15 min | RLS broken (cross-tenant data), journal entries not balancing, DB unreachable, auth bypass |
| **P2 — High** | Core feature down, SLO violation, agent loop detected | < 1 hour | Invoice creation failing, Procrastinate worker stopped, API P99 > 10s |
| **P3 — Medium** | Degraded performance, single agent failing, workaround available | < 4 hours | One agent failing (others work), Langfuse traces missing, slow reports |
| **P4 — Low** | Cosmetic issue, minor UX degradation, non-blocking | Next sprint | UI glitch, display timezone error, non-critical copy typo |

### Escalation Path

```
P3/P4  →  Sthira investigates and resolves
            ↓ not resolved in 2h
P2     →  Sthira → notify Vishwa
            ↓ data integrity risk or SLO breach confirmed
P1     →  Sthira → Vishwa → Founder (immediate)
            ↓ security breach confirmed
P1-SEC →  Sthira → Vishwa → Founder + Prahari
```

### Incident Checklist (P1/P2)
1. [ ] **Acknowledge** — post in team channel: "Incident declared: [description]. I'm on it."
2. [ ] **Assess** — determine severity and blast radius (how many tenants affected?)
3. [ ] **Contain** — apply immediate mitigation (disable agent, roll back deploy, restrict traffic)
4. [ ] **Notify** — if P1: notify Vishwa + founder within 15 min
5. [ ] **Resolve** — apply fix, verify SLOs recovering
6. [ ] **Post-mortem** — open a GitHub issue within 24h of resolution

---

### Runbook: Database Unreachable (P1)
**Symptoms**: All API 500s, health check failing, `supabase connection error` in logs
```bash
# 1. Check Supabase status
open https://status.supabase.com

# 2. Test connection
curl -X GET "${SUPABASE_URL}/rest/v1/" \
  -H "apikey: ${SUPABASE_ANON_KEY}"

# 3. Restart backend (clears connection pool)
docker-compose restart aethos-backend aethos-worker

# 4. If Supabase is up but connections still failing — rotate service key
# Supabase dashboard → Settings → API → Regenerate service_role key
# Update SUPABASE_SERVICE_KEY env var and redeploy
```

### Runbook: Worker Stopped / Queue Backed Up (P2)
**Symptoms**: Background jobs not processing, scheduled tasks not running, queue growing
```bash
# 1. Check worker process
docker-compose ps aethos-worker
docker-compose logs --tail=100 aethos-worker

# 2. Check job queue state (Supabase SQL editor)
SELECT status, count(*) FROM procrastinate_jobs GROUP BY status;
SELECT * FROM procrastinate_jobs WHERE status='failed' ORDER BY created_at DESC LIMIT 10;

# 3. Restart worker
docker-compose restart aethos-worker

# 4. Manually retry safe failed jobs
-- UPDATE procrastinate_jobs SET status='todo' WHERE status='failed' AND id = '<job_id>';
```

### Runbook: LLM API Unavailable (P2/P3)
**Symptoms**: Agent endpoints erroring, OpenRouter degradation, `confidence=0` in audit log
```bash
# 1. Check OpenRouter status: https://openrouter.ai/status

# 2. Test connectivity
curl https://openrouter.ai/api/v1/models -H "Authorization: Bearer ${OPENROUTER_API_KEY}"

# 3. Core ERP is NOT blocked — agents fail gracefully via run_agent_safe()
# Communicate: "AI suggestions temporarily unavailable. Core operations work normally."

# 4. If one model is down — update AGENT_MODEL_* env vars to a backup model
```

### Runbook: RLS / Tenant Isolation Breach (P1-SEC)
**Symptoms**: User reports seeing another tenant's data, suspicious cross-tenant queries in audit log
```bash
# IMMEDIATE: Escalate to founder within 5 minutes of suspicion. Do not investigate alone.

# 1. Check recent audit log for cross-tenant patterns (Supabase SQL editor)
SELECT tenant_id, agent_id, created_at FROM agent_audit_log
WHERE created_at > now() - interval '1 hour'
ORDER BY created_at DESC LIMIT 100;

# 2. Verify RLS on affected table
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND tablename = '<affected_table>';

# 3. Temporarily disable affected user account if breach confirmed
# Supabase dashboard → Authentication → Users → Disable user

# 4. Document exactly what data was exposed, to whom, for how long
# Engage Prahari for full security incident review
```

### Runbook: Agent Infinite Loop / Extreme Latency (P2)
**Symptoms**: Agent taking > 30s, worker thread blocked, `latency_ms` > 30,000 in audit log
```bash
# 1. Identify stuck agent
SELECT agent_id, latency_ms, created_at FROM agent_audit_log
WHERE latency_ms > 30000 ORDER BY created_at DESC LIMIT 10;

# 2. Restart worker to clear stuck coroutines
docker-compose restart aethos-worker

# 3. Disable agent for affected tenant (L0 = off)
-- UPDATE agent_configurations SET autonomy_level=0
-- WHERE agent_id='<agent_id>' AND tenant_id='<tenant_id>';
```

### Post-Mortem Template

Open a GitHub issue (`type:chore, area:infra`) within 24h of resolving any P1/P2:

```markdown
## Incident Post-Mortem: [Short Title]

**Date / Duration / Severity / Affected**:

### Summary
[2-3 sentences: what happened, user impact]

### Timeline
| Time (UTC) | Event |
|------------|-------|
| HH:MM | Detected (how?) |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Resolved |

### Root Cause
[Specific technical explanation — not "human error"]

### Action Items
| Action | Owner | Due |
|--------|-------|-----|
| [Preventive fix] | Karya/Sthira | date |
| [Monitoring gap] | Sthira | date |
| [Test coverage] | Aksha | date |

### What Went Well / What Could Be Improved
```

---

## Gap Assessment

### 🔴 Critical
1. **No error tracking** — Production errors will go unnoticed without Sentry or equivalent
2. **No CD pipeline** — No automated deployment to staging/production
3. **Frontend CI job will fail** — References tests that don't exist

### 🟡 Important
4. **No application metrics** — Cannot measure request latency, error rates, throughput
5. **No alerting** — No PagerDuty/Opsgenie for on-call
6. **No secrets management** — Environment variables used directly
7. **No staging environment** — Only development and production paths exist
8. **No backup strategy documented** — Supabase has automatic backups, but recovery procedures aren't documented

### 🟢 Minor
9. **No Docker health checks** — Docker services lack `healthcheck` configuration
10. **No resource limits** — Docker services don't specify CPU/memory limits
11. **No log rotation** — Container logs will grow unbounded

---

## Improvement Recommendations

### Priority 1 — Observability
1. Add Sentry for error tracking (backend + frontend)
2. Add Prometheus metrics endpoint with key SLIs (request latency, error rate, agent execution time)
3. Set up Logfire properly or replace with self-hosted OpenTelemetry

### Priority 2 — CI/CD
4. Fix frontend CI job (either add tests or remove the job)
5. Add lint steps: `ruff check backend/` + `ng lint`
6. Add Docker image build + push to registry
7. Add deployment stage (staging → production)

### Priority 3 — Reliability
8. Add Docker health checks for all services
9. Add resource limits (CPU/memory) to docker-compose
10. Document backup/recovery procedures for Supabase
11. Add staging environment with Supabase branch databases

### Priority 4 — Security
12. Migrate secrets to a secrets manager (AWS SSM, Vault, or Supabase Vault)
13. Add request body size limits to FastAPI
14. Add CSRF protection or document why it's not needed (SPA + JWT)

---

## Changelog

### [2026-04-03] - Initial comprehensive audit
- Documented full infrastructure: Docker setup (3 services), CI pipeline (2 jobs), Supabase cloud DB
- Identified: no error tracking, no CD, no metrics, broken frontend CI job
- Mapped all environment variables and deployment procedures
- Created prioritized improvement plan across observability, CI/CD, reliability, and security
