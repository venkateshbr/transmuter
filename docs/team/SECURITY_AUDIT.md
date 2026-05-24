# Security Audit Evidence

Date: 2026-05-23
Owner: Prahari
Scope: Phase 5 enterprise hardening issue #80.

## Summary

The platform was reviewed against the OWASP Top 10 areas that apply to the current
FastAPI, Angular, Supabase Auth, Supabase RLS, PydanticAI, and Procrastinate stack.
The hardening controls below are implemented and covered by automated tests where
they are deterministic in local CI.

## Controls Reviewed

- Broken access control: Supabase RLS is enabled for core tables and API routes use
  tenant-scoped dependencies. User-facing Supabase clients forward the caller JWT so
  RLS is exercised by PostgREST.
- Cryptographic failures: API JWT secrets are environment-driven, refresh-token
  rotation is enabled in Supabase config, and `/auth/refresh` rotates sessions via
  Supabase Auth.
- Injection: Routers use structured repository calls instead of SQL string building.
  Agent-facing text is validated for prompt-injection, obvious PII, and secret
  material before agent execution.
- Insecure design: AI suggestions remain HITL review artifacts. Agent failures
  degrade to deterministic fallback behavior and do not block core workflows.
- Security misconfiguration: API responses include CSP, frame, content-type,
  referrer, and permissions headers. Swagger/Redoc are disabled unless debug mode is
  enabled.
- Vulnerable components: CI contains Python and npm audit gates for dependency
  scanning. No third-party CDN assets are loaded by `apps/web/src/index.html`.
- Authentication failures: Login and authenticated password-change attempts are
  rate-limited, Supabase Auth is the source of session truth, profile password
  changes reauthenticate the current password before update, and refresh tokens
  rotate on refresh.
- Software/data integrity failures: Browser assets are local application assets;
  the SRI/CDN review test fails if external script/link assets are introduced
  without review.
- Logging and monitoring failures: Sentry, Logfire, Langfuse, alert webhooks, API
  SLO snapshots, agent latency/correction-rate metrics, and worker job metrics are
  implemented.
- SSRF: There are no user-controlled server-side URL fetch paths in the reviewed
  routes. Alert webhook destination is environment-controlled.

## Evidence

- Backend security tests: `apps/api/tests/test_security_controls.py`
- RLS tests: `apps/api/tests/test_rls_behavior.py`,
  `apps/api/tests/test_rls_metadata.py`
- Observability tests: `apps/api/tests/test_observability.py`
- Frontend SRI/CDN review: `test_static_index_has_no_unreviewed_external_cdn_assets`
- Supabase token rotation config: `supabase/config.toml`

## Residual Risk

- Full production alert routing requires the deployment environment to provide
  `ALERT_WEBHOOK_URL`.
- Manual penetration testing should be repeated after each new externally exposed
  integration or agent tool is added.
