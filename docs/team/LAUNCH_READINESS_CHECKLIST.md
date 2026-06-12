# Transmuter Launch Readiness Checklist

## Current Status

Local launch gate reports:

- Blockers: 0
- Warnings: 1
- Runtime: API and Angular app verified locally
- Billing: Stripe Checkout, webhook provisioning, formal signup intents, tenant subscription records, Admin billing status, and Billing Portal handoff are implemented
- RBAC: Transformation Office, Initiative Owner, and Viewer are enforced on core portfolio routes
- RLS: Supabase catalog verification passed on 2026-05-04 with 34 tables checked, 32 tenant tables, 0 blockers, and 0 warnings
- Prahari: Billing/RBAC/RLS security review is documented in `docs/team/PRAHARI_SECURITY_REVIEW_BILLING_RBAC.md`
- Platform Admin: SaaS operator login and `/platform` console are available through server-side `PLATFORM_ADMIN_EMAILS`
- Clean configurable financial engine: `v0.4.0` is tagged as the pre-refactor
  rollback baseline; current rollout uses blank-tenant self-configuration and
  optional anonymised workbook reload.

## Launch-Critical Controls

- Public homepage and Get Started flow are available.
- Stripe Checkout is created server-side.
- Stripe webhook signatures are verified before provisioning.
- Signup creates a pending tenant, signup intent, and tenant-specific plan record before redirecting to Stripe Checkout.
- Initial signup admin is provisioned as `transformation_office`.
- Admins can view billing state and open Stripe Billing Portal after checkout has created a customer.
- Admins can view production Stripe Price ID configuration status in Admin Billing.
- Platform admins can view cross-tenant signup, billing, tenant, and Stripe catalog readiness without being tenant members.
- Admins can grant only `transformation_office`, `initiative_owner`, or `viewer`.
- Initiative owners are scoped to initiatives where they are owner or group owner.
- Viewers can see portfolio data but cannot mutate initiative data or grant roles.
- Transformation Office owns mutation paths for users, initiatives, meetings, action items, governance, financials, KPIs, risks, milestones, dependencies, and team assignments.
- Supabase RLS verification is repeatable via `apps/api/scripts/verify_rls.py`.

## Remaining Production Hardening

- Configure production Stripe product/price IDs from `docs/team/STRIPE_PRODUCT_CATALOG.md`; Admin Billing and Launch Readiness now show missing IDs.
- Configure Stripe webhook endpoint in the Stripe dashboard for production.
- Configure production domain redirect URLs for checkout success, cancel, and Billing Portal return.
- Decide whether beta tenants start empty or with optional sample data.
- Run the full real API acceptance suite and browser E2E suite in CI against a seeded test tenant.
- Complete Prahari security review for auth, RLS, Stripe, Supabase service-role usage, and AI data masking.
- Configure production `PLATFORM_ADMIN_EMAILS` with named operator accounts and require MFA in Supabase Auth.

## Clean Financial Refactor Launch Gate

- Confirm target Supabase has a pre-refactor backup before applying clean
  financial migrations.
- Confirm `git rev-parse v0.4.0` resolves and is documented as the code rollback
  baseline.
- Run workbook dry-run before destructive reload:

```bash
cd apps/api
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id <tenant-uuid> \
  --user-id <tenant-admin-user-uuid> \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --dry-run
```

- Dry-run must return `ready: true` and the deterministic workbook counts from
  `docs/team/HOSTINGER_VPS_DEPLOYMENT.md`.
- Destructive reload must use `--confirm-reset`; no other reset path is approved
  for launch data.
- New tenant signup must remain blank: no initiatives, business units,
  workstreams, financial config, metric definitions, scenarios, stage gates,
  gate criteria, meetings, KPIs, risks, or cost lines should be seeded by normal
  provisioning.
- Tenant admins must be able to complete self-configuration through Admin before
  initiative creation/import is enabled.
- Public-domain validation must include:

```bash
curl -fsS https://transmuter.ishirock.tech/health
curl -fsS https://transmuter.ishirock.tech/api/health
```

- Browser validation must cover Admin setup, metric/scenario/gate configuration,
  workbook reload result visibility, Portfolio Financials value ramp, and an
  initiative detail financial grid after reload.
