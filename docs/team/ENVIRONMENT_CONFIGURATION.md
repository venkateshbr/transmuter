# Environment Configuration

Last updated: 2026-05-04

Copy `.env.example` to `.env` before running Transmuter:

```bash
cp .env.example .env
```

Do not commit `.env`. It contains Supabase service credentials, JWT secrets,
payment keys, webhook secrets, and optional AI/observability keys.

## Required For Any API Run

| Variable | Required | Purpose | Example / Notes |
| --- | --- | --- | --- |
| `SUPABASE_URL` | Yes | Supabase project URL used by API and scripts. | `https://<project-ref>.supabase.co` |
| `SUPABASE_ANON_KEY` | Yes | Supabase anon key for user-scoped clients and auth. | Starts with `ey...` |
| `SUPABASE_SERVICE_KEY` | Yes | Supabase service-role key for admin/server operations. | Secret. Never expose in browser. |
| `JWT_SECRET` | Yes | Signs Transmuter API JWTs after Supabase login. | At least 32 random chars. |
| `OPENROUTER_API_KEY` | Yes by current config | Enables AI agents through OpenRouter. | Use a placeholder only if AI will not be exercised. |

## App Runtime

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_NAME` | No | `Transmuter API` | FastAPI application title. |
| `VERSION` | No | `0.1.0` | Version returned by `/health`. |
| `DEBUG` | No | `false` | Enables FastAPI docs routes when true. Keep false in production. |

## Authentication

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `JWT_SECRET` | Yes | None | Must be at least 32 characters and environment-specific. |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm. Keep default unless intentionally rotating. |
| `JWT_EXPIRY_MINUTES` | No | `60` | API JWT lifetime after login. |

## Supabase And Database

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `SUPABASE_URL` | Yes | None | Supabase project URL. |
| `SUPABASE_ANON_KEY` | Yes | None | Browser-safe anon key, also used for auth flow. |
| `SUPABASE_SERVICE_KEY` | Yes | None | Server-only service-role key. |
| `DATABASE_URL` | Recommended | Empty | PostgreSQL connection string for Procrastinate background jobs. |

Use the Supabase connection string for `DATABASE_URL`, usually:

```text
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

## AI And Observability

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `AI_ENABLED` | No | `true` | Enables AI-assisted features. Agents degrade gracefully when unavailable. |
| `OPENROUTER_API_KEY` | Yes by current config | None | OpenRouter API key for PydanticAI agents. |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenAI-compatible gateway URL. |
| `DEFAULT_MODEL` | No | `anthropic/claude-sonnet-4-6` | Default model identifier for agents. |
| `LANGFUSE_SECRET_KEY` | No | Empty | Langfuse tracing secret key. |
| `LANGFUSE_PUBLIC_KEY` | No | Empty | Langfuse tracing public key. |
| `LANGFUSE_HOST` | No | `https://cloud.langfuse.com` | Langfuse host URL. |

Security rule: never send raw PII to external LLM APIs. Mask email, phone, and
display names before tool or model calls.

## Billing And Stripe

Billing is required for public SaaS signup and tenant provisioning through
checkout. Use Stripe test keys for sandbox and live keys only for production.

| Variable | Required For Signup | Purpose |
| --- | --- | --- |
| `PAYMENT_PROVIDER` | Yes | Set to `stripe`. |
| `STRIPE_SECRET_KEY` | Yes | Server-side Stripe API key, `sk_test_...` or `sk_live_...`. |
| `STRIPE_PUBLISHABLE_KEY` | Yes | Client-visible Stripe publishable key, `pk_test_...` or `pk_live_...`. |
| `STRIPE_WEBHOOK_SECRET` | Yes | Webhook signing secret, `whsec_...`, for `/billing/webhook`. |
| `STRIPE_PRICE_TEAM_MONTHLY` | Yes | Stripe Price ID for 1-50 user monthly tier. |
| `STRIPE_PRICE_TEAM_ANNUAL` | Yes | Stripe Price ID for 1-50 user annual tier. |
| `STRIPE_PRICE_BUSINESS_MONTHLY` | Yes | Stripe Price ID for 51-100 user monthly tier. |
| `STRIPE_PRICE_BUSINESS_ANNUAL` | Yes | Stripe Price ID for 51-100 user annual tier. |
| `ENCRYPTION_KEY` | Yes | Base64 32-byte Fernet-compatible key for encrypted billing metadata. |

Current product catalog direction:

- Team: 1-50 users.
- Business: 51-100 users.
- Enterprise: 101+ users, contact sales rather than self-service checkout.

Stripe webhook endpoint for the current Cloudflare deployment:

```text
https://transmuter-api.ishirock.com/billing/webhook
```

At minimum, configure these events:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

## Notifications

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `RESEND_API_KEY` | No | Empty | Enables email nudges/notifications. |
| `RESEND_FROM_EMAIL` | No | Empty | Sender identity, for example `Transmuter <notifications@example.com>`. |

Without these values, notification delivery is skipped/logged rather than blocking
core platform functionality.

## Platform Admin Access

| Variable | Required | Purpose |
| --- | --- | --- |
| `PLATFORM_ADMIN_EMAILS` | Required for `/platform` access | Comma-separated Supabase Auth emails allowed to access tenant/billing administration. |

Example:

```text
PLATFORM_ADMIN_EMAILS=admin@example.com,ops@example.com
```

## Frontend Runtime Configuration

The production frontend image writes runtime API configuration from
`TRANSMUTER_API_URL` when the container starts. This value is used by
`apps/web/docker-entrypoint.sh`.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `TRANSMUTER_API_URL` | Production recommended | `https://transmuter-api.ishirock.com` in compose, `http://localhost:8001` in static fallback | API base URL used by the Angular app at runtime. |

For the current Cloudflare deployment:

```bash
TRANSMUTER_API_URL=https://transmuter-api.ishirock.com \
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d
```

## E2E And Acceptance Test Variables

These are not required for normal runtime, but are useful for regression tests.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `RUN_REAL_ACCEPTANCE` | Acceptance tests | Unset | Set to `1` to enable real API acceptance tests. |
| `TRANSMUTER_API_BASE_URL` | Tests | `http://localhost:8000` | API URL for API/UI tests. |
| `TRANSMUTER_UI_BASE_URL` | UI E2E | `http://localhost:4300` | Angular URL for browser tests. |
| `TRANSMUTER_E2E_EMAIL` | Tests | Test default in code | Seeded test user email. |
| `TRANSMUTER_E2E_PASSWORD` | Tests | Test default in code | Seeded test user password. Do not commit real values. |

## Pre-Run Checklist

Before local or production startup:

- `.env` exists and is not committed.
- Supabase URL, anon key, and service key point to the intended project.
- JWT secret is random and at least 32 characters.
- Stripe keys, webhook secret, and Price IDs all come from the same Stripe mode
  (`test` or `live`), never mixed.
- `PLATFORM_ADMIN_EMAILS` includes the intended operator emails.
- `TRANSMUTER_API_URL` matches the URL the browser can use to reach the API.
- For production, `DEBUG=false`.
