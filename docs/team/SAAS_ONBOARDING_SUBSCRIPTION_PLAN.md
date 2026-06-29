# SaaS Homepage and Subscription Plan

## Goal

Turn Transmuter from a tenant-seeded internal app into a self-serve multi-tenant SaaS flow:

1. Public homepage explains the enterprise transformation platform, value drivers, and operating model.
2. Visitors can choose `Login` or `Get Started`.
3. `Get Started` collects organization details and the initial admin user.
4. Stripe checkout creates the subscription.
5. Successful payment provisions the tenant, creates the initial admin, and sends the admin into setup.

## Public Homepage

Route: `/`

Unauthenticated users should see a public homepage. Authenticated users should still land on the dashboard.

Recommended sections:

- Hero: “Enterprise transformation control tower” with direct `Login` and `Get Started` actions.
- Value proof: portfolio value bridge, milestone pressure, governance cadence, and AI assistant benefits.
- Platform modules: initiatives, roadmap, financials, KPIs, risks, meetings, people, admin.
- Enterprise controls: tenant isolation, RBAC, audit log, RLS, data masking for AI.
- Pricing summary: banded subscription plan for 1-50 users, 51-100 users, and enterprise contact-sales pricing for 101+ users.

Design direction: A&M-inspired executive consulting aesthetic already codified in `team/DESIGN_SYSTEM.md`: deep navy, steel blue, sharp panels, restrained editorial typography, no pill-heavy SaaS marketing visuals.

## Get Started Flow

Route: `/get-started`

Fields:

- Organization name
- Organization slug, generated from name but editable
- Initial admin display name
- Initial admin work email
- Initial admin password or invite-email mode
- Planned user count
- Terms/privacy acceptance

Submit behavior:

1. Create a pending signup record.
2. Reserve the tenant organization and tenant-specific plan snapshot.
3. Create a Stripe Checkout Session for subscription mode.
4. Redirect the browser to Stripe Checkout.
5. On webhook success, provision the initial admin and tenant subscription.
6. Redirect to `/auth/login?signup=success` or directly establish a session if the backend supports secure post-checkout session exchange.

## Backend Work

New tables:

- `subscription_plans`
  - `id`, `tenant_id`, `code`, `stripe_price_id`, `amount_cents`, `currency`, `billing_interval`, `is_active`
- `tenant_subscriptions`
  - `tenant_id`, `stripe_customer_id`, `stripe_subscription_id`, `status`, `quantity`, `current_period_end`
- `signup_intents`
  - `id`, `tenant_id`, `organization_name`, `organization_slug`, `admin_email`, `admin_display_name`, `planned_user_count`, `stripe_checkout_session_id`, `status`

New endpoints:

- `POST /billing/signup-intents`
  - Validates organization/admin input and creates a pending signup intent.
- `POST /billing/checkout-session`
  - Creates Stripe Checkout Session using the signup intent and planned seat count.
- `POST /billing/webhook`
  - Verifies Stripe signature.
  - On `checkout.session.completed`, provisions organization, initial admin, and tenant subscription.
  - On subscription update/cancel events, updates `tenant_subscriptions`.
- `GET /billing/subscription`
  - Authenticated tenant admin view of subscription state.
- `POST /billing/portal-session`
  - Opens Stripe Billing Portal for admins.

Security requirements:

- Never trust client-provided price IDs.
- Verify Stripe webhook signatures.
- Make tenant provisioning idempotent by signup intent and Stripe session ID.
- Keep org slug globally unique.
- Use service-role Supabase only inside backend provisioning.

## RBAC Model

Initial tenant roles:

- `transformation_office`: full tenant and portfolio permissions.
- `tenant_admin`: users, access, tenant setup, dimensions, dashboard
  configuration, governance configuration, and billing portal access.
- `pmo_lead`: governance, meetings, actions, milestones, risks, KPIs, and
  program cadence.
- `finance_lead`: financial configuration, initiative financials, benefit
  validation, shared costs, bankable plans, actuals, and benefit tracking.
- `workstream_lead`: assigned-workstream portfolio visibility and execution
  evidence.
- `initiative_owner`: owned-initiative master data, execution evidence, status,
  and financial assumptions.
- `business_benefit_owner`: portfolio visibility plus benefit realization
  evidence and ledger updates.
- `executive_sponsor`: read-only executive portfolio and financial views.
- `viewer`: read-only management portfolio and dashboard access.

Role assignment:

- Initial signup admin is provisioned as `transformation_office`.
- `transformation_office` and `tenant_admin` users can invite users or change
  user roles.
- API validation accepts the nine operating-model tenant roles listed above.

## Frontend Work

Routing:

- Public shell routes: `/`, `/get-started`, `/auth/login`
- Authenticated app shell: dashboard and all product routes

Components:

- `HomeComponent`
- `GetStartedComponent`
- `SubscriptionSuccessComponent`
- `SubscriptionCancelComponent`
- Optional `BillingSettingsComponent` inside Admin

Auth guard changes:

- Allow public routes without redirect.
- If authenticated and visiting `/`, route to dashboard.
- If unauthenticated and visiting app routes, route to `/auth/login`.

## Stripe Model

Recommended launch catalog:

- Product: `Transmuter Platform`
- Team: 1-50 users, 999 USD/month or 9,990 USD/year
- Business: 51-100 users, 1,999 USD/month or 19,990 USD/year
- Enterprise: 101+ users, contact sales
- Checkout mode: `subscription`
- Customer metadata: signup intent ID and requested org slug
- Subscription metadata: tenant ID after provisioning
- Production Checkout should use Stripe Price IDs from the production catalog; inline sandbox `price_data` is only for validation before those Price IDs exist.

Future-ready additions:

- Seat reconciliation from active users.
- Trial periods.
- Enterprise invoice/manual payment path.

## Acceptance Checks

- Unauthenticated visitor sees homepage at `/`.
- `Login` navigates to `/auth/login`.
- `Get Started` captures organization and admin details.
- Checkout session is created only by backend.
- Stripe webhook provisions a tenant exactly once.
- Initial admin can log in and invite/manage users.
- Tenant subscription status is visible to transformation-office admins.
