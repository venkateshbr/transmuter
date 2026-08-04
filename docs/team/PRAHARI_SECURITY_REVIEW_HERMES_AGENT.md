# Prahari Security Review — Hermes Agent Integration

Date: 2026-08-04  
Issue: #444  
Parent: #443  
Decision: approved for merge while Hermes remains disabled by default

## Scope

- Runtime selection and graceful fallback
- External-model PII boundary
- Encrypted tenant/user context references
- Private MCP-to-API broker authentication
- Tenant isolation and canonical role revalidation
- Tool allowlisting and write/HITL separation
- Output filtering, logs, configuration, and deployment

## Findings

### No critical or high findings

Hermes has no Supabase credential, database connection, tenant selector, or
write-capable tool. The browser cannot enable Hermes. Existing action drafts,
payload hashes, permission guardrails, expiry, and explicit confirmation remain
inside Transmuter.

### Controls verified

| Threat | Control | Evidence |
| --- | --- | --- |
| Model chooses another tenant/user/role | Authority is encrypted in a per-turn context; authority keys in arguments are rejected recursively. | Context and broker contract tests. |
| Stolen or replayed context | Fernet-authenticated reference, 15-minute default expiry, read-only scope, and canonical active-user recheck per call. | Tamper, expiry, and membership tests. |
| Broker endpoint called without Hermes | Constant-time comparison against a server-only bearer token; absent config fails closed. | Missing/bad-token test. |
| Unknown or raw database tool | Fixed five-tool allowlist; unknown names return 404. | Unknown-tool test. |
| Cross-tenant service-role read | Every registry query supplies verified `tenant_id`; role restrictions are rebuilt from the current canonical user. | Cross-tenant denial and seeded read-pack tests. |
| PII leaves Transmuter | Email/phone/secret input validation remains active; known display names are masked; read packs omit people, contacts, user/owner IDs, and raw/free-text rows. | Runtime mask and response-content tests. |
| Tool internals reach browser | Hermes output containing context/tool/config/credential markers or email is rejected; safe fallback is default. | Unsafe-output path and runtime tests. |
| Hermes bypasses HITL | Runtime detects supported write intent before Hermes; broker exposes no write tools. | Write-path preservation test. |
| Hermes outage blocks users | `HERMES_FALLBACK_TO_BASIC=true` by default. | Upstream failure/fallback test. |

## Residual Risks and Activation Conditions

1. The Hermes base image is pinned to the reviewed multi-platform OCI digest
   `sha256:fcbe95482353e41cd30d39ddfc0f57ba3720f6da6969a7a69cdfb0d84b045cb6`.
   Future upgrades require a new digest review rather than following `latest`.
2. Real Hermes acceptance requires infrastructure secrets that are intentionally
   absent from the repository: API server key, broker token, context encryption
   secret, and model-provider key.
3. Production activation requires real seeded-tenant verification of the five
   MCP tools, output suppression, outage fallback, and built-in write
   confirmation. Unit/TestClient evidence alone is not release acceptance.
4. Free-form initiative names are business data and may be sent in a read pack.
   Tenant operators must not place personal contact data in initiative names.
   Future richer free-text packs require a stronger entity-redaction pass.

## Decision

The disabled-by-default integration is safe to merge. It is not approved for
runtime activation until secrets are installed through the Hostinger project
environment and real dev acceptance passes. No database or RLS migration is
introduced by this phase.
