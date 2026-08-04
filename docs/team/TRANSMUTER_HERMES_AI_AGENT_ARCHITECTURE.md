# Transmuter AI and Hermes Agent Architecture

Status: implemented, disabled by default  
Owner: Vishwa / Vastu  
Security review: Prahari issue #444  
Reference: [Aethos Atlas and Hermes architecture](https://github.com/venkateshbr/aethos-ps/blob/main/docs/architecture/atlas-hermes-ai-agent-architecture.md)

## Purpose

Transmuter AI remains the user-facing assistant. Hermes is an optional advanced
agent runtime behind the existing `/ai/chat` facade. Transmuter remains the
system of record for tenants, users, initiatives, governance, financials,
permissions, approvals, and audit evidence.

The integration is intentionally a safe first vertical slice. Hermes can
orchestrate read-only portfolio tools. All create/update requests continue to
use Transmuter's built-in draft, guardrail, and explicit-confirmation workflow.

## Design Rules

- The browser and user never select the runtime; the API selects it.
- The existing `/ai/chat` request and response contract remains stable.
- `transmuter_basic` is the default and remains available without Hermes.
- Hermes never receives a database credential, Supabase token, tenant ID, user
  ID, user email, phone number, display name, or role as a tool argument.
- Known tenant display names are masked before a prompt leaves Transmuter.
- Hermes receives an encrypted, short-lived `context_ref`; only Transmuter can
  decrypt and verify its tenant/user/thread authority.
- The tool broker rechecks the canonical active user and role on every call.
- Tool arguments cannot contain tenant, user, or role authority fields.
- The allowlist contains read tools only. Hermes cannot write to Transmuter.
- Tool results are compact read packs, not raw database rows, and omit people,
  contact details, owner IDs, free-text descriptions, and internal record IDs.
- Responses containing tool internals, context references, credentials, email
  addresses, or stack traces are rejected before reaching the browser.
- Hermes failures fall back to built-in Transmuter AI by default.

## Runtime Modes

| Runtime | Configuration | Behavior |
| --- | --- | --- |
| Built-in Transmuter AI | `TRANSMUTER_AI_RUNTIME=transmuter_basic` | Existing deterministic read answers and confirmation-gated writes. |
| Hermes Agent | `TRANSMUTER_AI_RUNTIME=hermes_agent` | Hermes handles read orchestration; write intent stays on the built-in path. |

## Components

| Component | Location | Responsibility |
| --- | --- | --- |
| Chat facade | `apps/api/app/routers/ai.py` | Authenticated, backward-compatible `/ai/chat` API. |
| Runtime adapter | `apps/api/app/services/transmuter_ai_runtime.py` | Server-side runtime choice, PII masking, safe fallback, output filtering. |
| Built-in runtime | `apps/api/app/services/ai.py` | Current tenant-scoped answers, action drafts, guardrails, confirmation. |
| Hermes client | `apps/api/app/services/hermes_client.py` | Private `/v1/responses` client with split timeouts and bounded retries. |
| Context service | `apps/api/app/services/hermes_context.py` | Encrypted, scoped, expiring tenant/user/thread authority. |
| Private broker | `apps/api/app/routers/hermes_tools.py` | Bearer authentication and context verification. |
| Broker service | `apps/api/app/services/hermes_tool_broker.py` | Canonical user recheck, authority-key rejection, allowlist dispatch. |
| Read packs | `apps/api/app/services/hermes_read_packs.py` | Role-aware, tenant-scoped, PII-safe business summaries. |
| MCP bridge | `integrations/hermes/transmuter_mcp_server.py` | Hermes MCP tools that call the private broker. |
| Hermes profile | `integrations/hermes/transmuter-profile/` | Persona, tool allowlist, and portfolio-advisor skill. |

## Read Request Flow

```mermaid
sequenceDiagram
    participant User
    participant UI as Transmuter UI
    participant API as /ai/chat
    participant Runtime as Runtime adapter
    participant Hermes
    participant MCP as Transmuter MCP bridge
    participant Broker as /ai-tools/execute
    participant Service as Read-pack service
    participant DB as Supabase/Postgres

    User->>UI: Ask a portfolio question
    UI->>API: Authenticated prompt
    API->>Runtime: Current user plus tenant-scoped client
    Runtime->>Runtime: Mask known display names
    Runtime->>Runtime: Encrypt short-lived context_ref
    Runtime->>Hermes: PII-masked prompt and context_ref
    Hermes->>MCP: Select read tool
    MCP->>Broker: Bearer token, context_ref, business filters
    Broker->>Broker: Decrypt scope; reject supplied authority
    Broker->>DB: Recheck canonical user, tenant, role, status
    Broker->>Service: Execute allowlisted read pack
    Service->>DB: Explicit tenant-scoped queries
    Service-->>Hermes: PII-safe structured summary
    Hermes-->>Runtime: Business answer
    Runtime->>Runtime: Reject unsafe/internal output
    Runtime-->>UI: Existing ChatResponse contract
```

## Write Request Flow

The runtime adapter detects write intent before calling Hermes. Write requests
go directly to `AIService`, which creates a tenant/user-bound draft with a
payload hash, expiry, permission checks, and guardrails. No database mutation
occurs until the authenticated user calls the existing confirmation endpoint.
Hermes never receives or confirms the action.

## Private Tool Contract

```text
POST /ai-tools/execute
Authorization: Bearer <HERMES_TOOL_TOKEN>
```

```json
{
  "context_ref": "ctx_<encrypted-token>",
  "tool_name": "transmuter.portfolio.overview",
  "arguments": {}
}
```

The endpoint is not a user API. It requires the private broker token and a
valid context. Unknown tools return 404. Invalid/tampered/expired contexts
return 400. Attempts to supply `tenant_id`, `user_id`, `role`, or
`current_user` anywhere in arguments return 422.

## Tool Catalog

| Broker tool | MCP wrapper | Purpose |
| --- | --- | --- |
| `transmuter.portfolio.overview` | `transmuter_portfolio_overview` | Aggregate initiative, risk, milestone, action, and KPI health. |
| `transmuter.portfolio.initiatives` | `transmuter_portfolio_initiatives` | Filtered initiative status without owners or internal IDs. |
| `transmuter.governance.read_pack` | `transmuter_governance_read_pack` | Aggregate risk and milestone governance health. |
| `transmuter.financials.read_pack` | `transmuter_financials_read_pack` | Decimal-safe value and cost totals, optionally by year. |
| `transmuter.tools.catalog` | `transmuter_tools_catalog` | Read-only user-facing built-in capability catalog. |

## Configuration and Activation

Generate two different random secrets of at least 32 characters for the broker
token and context encryption. Configure the API and Hermes service with:

```text
COMPOSE_PROFILES=hermes
TRANSMUTER_AI_RUNTIME=hermes_agent
HERMES_BASE_URL=http://hermes:8642
HERMES_API_SERVER_KEY=<private Hermes API key>
HERMES_TOOL_TOKEN=<private MCP-to-broker token>
HERMES_CONTEXT_SIGNING_SECRET=<dedicated context encryption secret>
HERMES_FALLBACK_TO_BASIC=true
HERMES_OPENROUTER_API_KEY=<optional separate model key>
```

The broker token must match in the API and Hermes container. Keep every value
in the saved Hostinger Docker project environment; never commit it. The Hermes
service has no published host port and is reachable only on the Compose network.
The base image is pinned to an immutable multi-platform OCI digest; upgrades
must be deliberate and reviewed.

To disable Hermes without removing the service, set:

```text
TRANSMUTER_AI_RUNTIME=transmuter_basic
```

## Verification

Focused contract checks:

```bash
cd apps/api
JWT_SECRET=test-secret-that-is-at-least-32-characters \
OPENROUTER_API_KEY=test \
uv run pytest tests/test_hermes_integration.py -q
```

Deployment acceptance must also use a real seeded tenant and running API:

1. Confirm built-in runtime read and write-confirmation behavior.
2. Start the `hermes` Compose profile with matching secrets.
3. Ask for portfolio, initiative, governance, and financial summaries.
4. Confirm the user sees business answers but no tool/context internals.
5. Stop Hermes and confirm read prompts fall back to built-in Transmuter AI.
6. Confirm a write prompt still returns the existing proposed action and requires
   explicit confirmation.
7. Verify tenant-crossing contexts, unknown tools, bad bearer tokens, expired
   contexts, and supplied authority arguments are rejected.

## Phase-Two Candidates

- Conversation/thread persistence and memory retention policy.
- Additional PII-safe initiative evidence packs.
- Langfuse trace correlation across Transmuter and Hermes without raw prompts.
- Review-only Hermes action proposals, still materialized exclusively by the
  existing Transmuter confirmation path.
- An explicit Hermes image upgrade cadence after operational soak testing.

These are intentionally outside the first production-safe vertical slice.
