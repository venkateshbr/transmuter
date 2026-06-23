# Environment Configuration

Last updated: 2026-06-20

Copy `.env.example` to `.env` before running Transmuter:

```bash
cp .env.example .env
```

Do not commit `.env`. It contains Supabase service credentials, JWT secrets,
payment keys, webhook secrets, and optional AI/observability keys.

## Required For Any API Run

| Variable | Required | Purpose | Example / Notes |
| --- | --- | --- | --- |
| `SUPABASE_TARGET` | Yes | Selects the active Supabase target. | `cloud` or `local`. |
| `SUPABASE_<TARGET>_URL` | Yes | Supabase project URL used by API and scripts for the selected target. | `SUPABASE_CLOUD_URL` or `SUPABASE_LOCAL_URL`. |
| `SUPABASE_<TARGET>_ANON_KEY` | Yes | Supabase anon key for user-scoped clients and auth for the selected target. | Starts with `ey...` |
| `SUPABASE_<TARGET>_SERVICE_KEY` | Yes | Supabase service-role key for admin/server operations for the selected target. | Secret. Never expose in browser. |
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
| `SUPABASE_TARGET` | Yes | `cloud` | Active target. Must be `cloud` or `local`. |
| `SUPABASE_CLOUD_URL` | Required when `SUPABASE_TARGET=cloud` | None | Supabase Cloud project URL. |
| `SUPABASE_CLOUD_ANON_KEY` | Required when `SUPABASE_TARGET=cloud` | None | Supabase Cloud anon key. |
| `SUPABASE_CLOUD_SERVICE_KEY` | Required when `SUPABASE_TARGET=cloud` | None | Supabase Cloud service-role key. |
| `DATABASE_CLOUD_URL` | Recommended when `SUPABASE_TARGET=cloud` | Empty | Supabase Cloud PostgreSQL connection string for Procrastinate/background jobs. |
| `SUPABASE_LOCAL_URL` | Required when `SUPABASE_TARGET=local` | None | Hostinger local Supabase API URL, currently `https://supabase.ishirock.tech`. |
| `SUPABASE_LOCAL_ANON_KEY` | Required when `SUPABASE_TARGET=local` | None | Hostinger local Supabase anon key. |
| `SUPABASE_LOCAL_SERVICE_KEY` | Required when `SUPABASE_TARGET=local` | None | Hostinger local Supabase service-role key. |
| `DATABASE_LOCAL_URL` | Recommended when `SUPABASE_TARGET=local` | Empty | Hostinger local PostgreSQL connection string with `transmuter` first in `search_path`. |
| `SUPABASE_URL` | Compatibility fallback | Empty | Legacy direct Supabase URL used only when the selected target-specific URL is absent. |
| `SUPABASE_ANON_KEY` | Compatibility fallback | Empty | Legacy direct anon key used only when the selected target-specific anon key is absent. |
| `SUPABASE_SERVICE_KEY` | Compatibility fallback | Empty | Legacy direct service key used only when the selected target-specific service key is absent. |
| `DATABASE_URL` | Compatibility fallback | Empty | Legacy direct PostgreSQL URL used only when the selected target-specific database URL is absent. |

Use the Supabase Cloud connection string for `DATABASE_CLOUD_URL`, usually:

```text
postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

For Hostinger local Supabase, keep `transmuter` first in the database search path:

```text
postgresql://postgres:<password>@host.docker.internal:5432/postgres?options=-csearch_path%3Dtransmuter,public,extensions
```

The local Supabase REST/PostgREST service must also expose `transmuter` first
because the API uses unqualified Supabase `.table(...)` calls:

```text
PGRST_DB_SCHEMAS=transmuter,public,graphql_public
PGRST_DB_EXTRA_SEARCH_PATH=transmuter,public,extensions
```

Switching between Cloud and Hostinger local requires only changing
`SUPABASE_TARGET` and restarting the API/container, assuming both target blocks
are populated.

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

Stripe webhook endpoint for the current Hostinger production deployment:

```text
https://transmuter.ishirock.tech/api/billing/webhook
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
| `PLATFORM_ADMIN_BOOTSTRAP_ENABLED` | Optional | When true, API startup checks the configured platform admin Supabase Auth user. Defaults to true. |
| `PLATFORM_ADMIN_BOOTSTRAP_EMAIL` | Optional | Supabase Auth email to create or metadata-normalize at API startup. Defaults to the first `PLATFORM_ADMIN_EMAILS` entry. |
| `PLATFORM_ADMIN_BOOTSTRAP_PASSWORD` | Required only if startup must create a missing Auth user | Temporary password used only when the platform admin Auth user is missing. Existing users are skipped or metadata-normalized without password changes. |
| `PLATFORM_ADMIN_PREVIOUS_EMAIL` | One-time rotation only | Previous Supabase Auth email consumed by `scripts/rotate_platform_admin_email.py`; not used by API startup. |

Example:

```text
PLATFORM_ADMIN_EMAILS=venkatesh@ishirock.com
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true
PLATFORM_ADMIN_BOOTSTRAP_EMAIL=venkatesh@ishirock.com
PLATFORM_ADMIN_BOOTSTRAP_PASSWORD=<temporary-password-if-user-is-missing>
PLATFORM_ADMIN_PREVIOUS_EMAIL=<old-email-only-while-rotating>
```

The startup bootstrap only uses Supabase Auth admin APIs. It does not insert a
tenant `users` row and does not seed tenants, tenant admins, subscriptions, or
operational sample data.

To rename an existing platform admin Auth user while preserving its Supabase
Auth identity and password, run:

```bash
cd apps/api
PLATFORM_ADMIN_PREVIOUS_EMAIL=admin@ishirock.com \
PLATFORM_ADMIN_BOOTSTRAP_EMAIL=venkatesh@ishirock.com \
uv run python scripts/rotate_platform_admin_email.py
```

## Frontend Runtime Configuration

The production frontend image writes runtime API configuration from
`TRANSMUTER_API_URL` when the container starts. This value is used by
`apps/web/docker-entrypoint.sh`.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `TRANSMUTER_API_URL` | Optional | `/api` | API base URL used by the Angular app at runtime. In the production web container, nginx proxies `/api` to `http://api:8001` on the Docker network. |

For the current Hostinger production deployment:

```bash
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d
```

## E2E And Acceptance Test Variables

These are not required for normal runtime, but are useful for regression tests.

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `RUN_REAL_ACCEPTANCE` | Acceptance tests | Unset | Set to `1` to enable real API acceptance tests. |
| `TRANSMUTER_API_BASE_URL` | Tests | `http://localhost:8000` | API URL for API/UI tests. |
| `TRANSMUTER_UI_BASE_URL` | UI E2E | `http://localhost:4300` | Angular URL for browser tests. |
| `DB_SCHEMA` | RLS verification | `public` | Schema inspected by RLS metadata/behavior checks. Use `transmuter` for Hostinger local Supabase. |
| `TRANSMUTER_E2E_EMAIL` | Tests | Test default in code | Seeded test user email. |
| `TRANSMUTER_E2E_PASSWORD` | Tests | Test default in code | Seeded test user password. Do not commit real values. |

## Pre-Run Checklist

Before local or production startup:

- `.env` exists and is not committed.
- `SUPABASE_TARGET` points to the intended project, and that target's URL, anon
  key, service key, and database URL are populated.
- JWT secret is random and at least 32 characters.
- Stripe keys, webhook secret, and Price IDs all come from the same Stripe mode
  (`test` or `live`), never mixed.
- `PLATFORM_ADMIN_EMAILS` includes the intended operator emails, and
  `PLATFORM_ADMIN_BOOTSTRAP_EMAIL` is either blank or included in that allowlist.
- `TRANSMUTER_API_URL` is `/api` for the production web container unless there is
  a deliberate reason to call an external API origin from the browser.
- For production, `DEBUG=false`.
