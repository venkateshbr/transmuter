# Prahari Security Review: Billing, RBAC, RLS, and Stripe

Review date: 2026-05-04

Scope:

- Public signup and Stripe Checkout creation
- Stripe webhook verification and provisioning
- Tenant-scoped billing tables
- RBAC launch roles
- Admin billing and launch readiness visibility
- Platform admin cross-tenant operator visibility

## Review Result

Conditional pass for controlled beta after production Stripe and webhook configuration are completed.

## Findings Closed

### Platform Admin Is Separate From Tenant RBAC

Status: implemented

Platform admins authenticate through Supabase Auth, but authorization comes from the `PLATFORM_ADMIN_EMAILS` server-side allowlist. They receive a `platform_admin` JWT role and a reserved zero tenant identifier, and they are not inserted as users inside every tenant.

The `/platform` API surface is guarded by `require_role("platform_admin")` and uses service-role Supabase access only on the backend.

### Platform Admin Surface Is Read-Only

Status: superseded by controlled destructive demo cleanup

The launch platform console exposes tenant, signup intent, subscription, user-count, and Stripe Price ID configuration status.

The only platform mutation currently allowed is controlled tenant deletion for demo cleanup. It is guarded by `platform_admin`, requires exact tenant slug confirmation, blocks the platform pseudo-tenant, deletes tenant-scoped records in dependency order, deletes tenant auth users, and removes the tenant organization last.

Production recommendation: keep this operation restricted to platform operators with MFA and audit every invocation before general availability.

### Webhook Signature Fail-Closed

Status: fixed

The Stripe webhook endpoint now rejects requests when `STRIPE_WEBHOOK_SECRET` is missing and verifies every webhook signature before processing events. This prevents unsigned webhook payloads from provisioning tenants when configuration is incomplete.

### Billing Tables Are Tenant-Scoped

Status: verified

`subscription_plans`, `signup_intents`, and `tenant_subscriptions` all include `tenant_id`, have RLS enabled, and include tenant-scoped policies.

Latest verifier result:

- Tables checked: 34
- Tenant tables: 32
- Blockers: 0
- Warnings: 0

### RBAC Database Constraint

Status: superseded by operating-model RBAC

The launch-era three-role constraint has been replaced by the Transformation
Office operating model. The accepted tenant roles are now:

- `transformation_office`
- `tenant_admin`
- `pmo_lead`
- `finance_lead`
- `workstream_lead`
- `initiative_owner`
- `business_benefit_owner`
- `executive_sponsor`
- `viewer`

RBAC is now enforced through API capability helpers and matching RLS helper
functions rather than one-off role checks.

### Production Price ID Visibility

Status: implemented

Admin Billing now surfaces all required effective Stripe Price IDs and whether they are configured:

- `STRIPE_PRICE_TEAM_MONTHLY`
- `STRIPE_PRICE_TEAM_ANNUAL`
- `STRIPE_PRICE_BUSINESS_MONTHLY`
- `STRIPE_PRICE_BUSINESS_ANNUAL`

Launch readiness also checks the effective values. Platform Control lets platform admins update the four Price IDs remotely; environment variables remain fallback/bootstrap values when no platform override has been saved.

## Remaining Prahari Conditions

### Configure Live Stripe Price IDs

Status: open

Create live Stripe Prices for the approved catalog and save the resulting live
Price IDs in Platform Control. Until these are present, the API can continue
sandbox validation through inline `price_data`, but production self-serve
checkout is not ready.

### Configure Production Webhook URL

Status: open

Once the Cloudflare tunnel or production domain is available, configure the Stripe webhook endpoint for:

- `checkout.session.completed`
- `customer.subscription.updated`
- `customer.subscription.deleted`

The webhook URL should point to:

```text
https://<production-or-tunnel-host>/billing/webhook
```

### Confirm Production Redirect Hosts

Status: open

Checkout success, cancel, and Billing Portal return URLs should use the production application domain. Avoid allowing arbitrary redirect hosts in production.

### Complete End-to-End Stripe Live-Mode Test

Status: open

Run one live-mode or production-like test through:

1. Public homepage
2. Get Started
3. Stripe Checkout
4. Webhook provisioning
5. Initial admin login
6. Admin Billing verification

## Prahari Notes

- Stripe Price IDs are safe to display to tenant admins; secret keys and webhook secrets must never be rendered.
- Platform Control accepts only `price_...` values for saved Price IDs; Stripe secret, publishable, restricted, and webhook key prefixes must be rejected server-side.
- Service-role Supabase access remains confined to backend provisioning/admin services.
- PII is stored in signup/admin records but is not sent to external LLM APIs by this flow.
- Webhook processing is idempotent at the tenant subscription layer by tenant and Stripe subscription/session identifiers.
- Platform admin emails must be controlled through production secret/environment management, not client-side configuration.
