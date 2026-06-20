# Stripe Onboarding and Tenant Deletion E2E Regression

Purpose: reusable launch-regression scenario for the complete multi-tenant SaaS flow through the public Hostinger production hostname, Stripe sandbox checkout, webhook provisioning, tenant UI setup, and platform-admin tenant cleanup.

## Scope

This scenario validates:

- Public marketing and subscription signup on `https://transmuter.ishirock.tech`.
- Stripe sandbox checkout using the configured test product/price IDs.
- Stripe webhook delivery to `https://transmuter.ishirock.tech/api/billing/webhook`.
- Tenant provisioning from the webhook.
- Initial tenant admin login.
- Initiative creation through the tenant UI.
- Creation of representative milestones, KPIs, risks, financials, and meetings.
- Dashboard visibility for the created initiative values.
- Platform admin deletion preview and deletion through the admin UI.
- Post-delete cleanup across tenant data and Supabase Auth users.

## Prerequisites

- Production Docker stack is running and healthy.
- Public production routing is active:
  - `https://transmuter.ishirock.tech` -> frontend.
- Frontend runtime config resolves to the same-origin API proxy:
  - `https://transmuter.ishirock.tech/assets/runtime-config.js`
  - Expected: `window.__TRANSMUTER_API_URL__ = "/api";`
- Stripe sandbox webhook endpoint is enabled for:
  - `checkout.session.completed`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Platform admin can log in at `https://transmuter.ishirock.tech/auth/login`.

## Test Data

Use a unique suffix per run, for example `YYYYMMDD-HHMM`.

- Organization name: `Regression E2E <suffix>`
- Organization slug: `regression-e2e-<suffix>`
- Initial admin name: `Regression Demo Admin`
- Initial admin email: `regression-e2e-<suffix>@example.com`
- Planned users: `12`
- Billing interval: `Monthly`
- Stripe test card: `4242 4242 4242 4242`
- Expiry: any future date, for example `12/34`
- CVC: any three digits, for example `123`
- Billing country: default is acceptable unless Stripe requires an explicit value.

## Scenario 1: Public Signup and Stripe Checkout

1. Open `https://transmuter.ishirock.tech/get-started`.
2. Enter the test organization and initial admin details.
3. Click `Continue to Stripe Checkout`.
4. Confirm the browser is redirected to `https://checkout.stripe.com/...`.
5. Confirm Stripe checkout shows:
   - `Subscribe to Transmuter Team`
   - `$999.00 per month`
   - Initial admin email prefilled.
6. Enter the Stripe sandbox card details.
7. Click `Subscribe`.
8. Confirm redirect returns to:
   - `https://transmuter.ishirock.tech/subscription/success?...`

Expected result:

- Checkout completes successfully.
- No local `127.0.0.1` URLs are used during public signup, checkout, return, or webhook handling.

## Scenario 2: Webhook Provisioning Verification

After checkout completes:

1. Check Stripe sandbox dashboard for the checkout session.
2. Confirm webhook delivery succeeded for `checkout.session.completed`.
3. In the platform admin console, open `https://transmuter.ishirock.tech/platform`.
4. Confirm the new tenant appears with:
   - Correct organization name and slug.
   - Active or provisioned subscription state.
   - Planned user count `12`.
   - Stripe customer/subscription reference populated.
   - Recent signup intent shows `provisioned`.

Expected result:

- Tenant, signup intent, subscription record, and initial admin are provisioned by webhook-driven flow.

## Scenario 3: Tenant Admin Login

1. Open `https://transmuter.ishirock.tech/auth/login`.
2. Sign in as the newly provisioned tenant admin.
3. If invite delivery produced a generated password, set or reset the tenant admin password in the sandbox auth admin console before this step.
4. Confirm successful login lands on `/dashboard`.

Expected result:

- Tenant admin has `transformation_office` role.
- Tenant admin cannot access `/platform`.

## Scenario 4: Create Initiatives Through the UI

Create at least three initiatives through `Initiatives -> New`.

Suggested initiatives:

- `Procurement Savings Wave`
  - Type: `Cost Reduction`
  - Impact: `Recurring`
  - Priority: `High`
  - Planned start/end: current quarter through next quarter.
- `Working Capital Release`
  - Type: `Capability Building` or `Cost Avoidance`
  - Impact: `One-off`
  - Priority: `Medium`
- `Service Productivity Lift`
  - Type: `Cost Reduction`
  - Impact: `Recurring`
  - Priority: `Medium`

For each initiative:

1. Use `Create with Transmuter`.
2. Complete the guided form.
3. Generate suggestions.
4. Keep accepted suggestions for financials, KPIs, risks, and milestones.
5. Click `Create Initiative`.
6. Confirm the initiative detail page opens.

Expected result:

- Each initiative appears in the pipeline.
- Each initiative has non-zero financial, KPI, risk, and milestone counts.

## Scenario 5: Add Users and Validate Tenant Roles

After tenant admin login, use `People -> Invite Member` to create:

- Initiative Owner:
  - Email: `owner-<tenant-slug>@example.com`
  - Role: `Initiative Owner`
- Viewer:
  - Email: `viewer-<tenant-slug>@example.com`
  - Role: `Viewer`

For sandbox regression, set known test passwords for the generated Supabase Auth users before role login checks.

Expected API behavior:

- Transformation Office can view all initiatives and manage users/data.
- Initiative Owner can view only initiatives where they are `owner_id` or `group_owner_id`.
- Initiative Owner gets `403` when attempting to create initiatives.
- Initiative Owner gets `404` when requesting a non-owned initiative detail by direct URL/API.
- Viewer can view all initiatives.
- Viewer gets `403` when attempting to create initiatives or access tenant admin settings.

Expected UI behavior:

- Initiative Owner pipeline shows only owned initiatives.
- Viewer pipeline shows all initiatives.
- Non-admin create/admin affordances should be hidden or disabled. If visible, the API must still block writes.

## Scenario 6: Add Financials, Milestones, KPIs, Risks, and Meetings

For at least one initiative, open the detail page and validate these tabs:

- Financials:
  - Confirm summary cards show plan values.
  - Edit details if needed and save at least one quarter with revenue/gross-margin/cost values.
- Milestones:
  - Add at least one manual milestone if suggestions did not create enough coverage.
  - Add/check a checklist item.
- KPIs:
  - Confirm suggested KPIs are visible.
  - Add or update one KPI value if needed.
- Risks:
  - Add one risk with mitigation.

Then open `Meetings`:

1. Create two meeting series:
   - `Weekly Value Review`
   - `SteerCo Readout`
2. Open each meeting and add/link at least one initiative where supported.
3. Start or create a session where supported.
4. Add one agenda item and one action item where supported.

Expected result:

- Tenant data covers initiatives, financials, KPIs, risks, milestones, meetings, agenda/action items, and users.

## Scenario 7: Dashboard Rollup Verification

1. Open `/dashboard`.
2. Confirm the dashboard reflects the tenant-created data:
   - Initiative counts are non-zero.
   - Financial value cards include the created values.
   - KPI pulse has data.
   - Risk heatmap/register has data.
   - Recent activity or related widgets reflect the new records.
3. Open pipeline and verify the created initiatives are visible.

Expected result:

- Transformation Office and Viewer dashboards roll up all tenant records.
- Initiative Owner dashboard rolls up only owned initiative records.
- Financials and progress roll up from real tenant records, not manually mocked browser state.

## Scenario 8: Platform Admin Deletion Preview and Cleanup

1. Log out of the tenant admin.
2. Log in as platform admin.
3. Open `/platform`.
4. Locate the test tenant row by slug.
5. Click `Delete`.
6. Confirm the modal shows object counts for:
   - Users
   - Initiatives
   - Financials
   - KPIs
   - Risks
   - Milestones
   - Meetings
   - Action items
   - Governance
   - Billing
   - Status updates
   - Audit and AI
   - Master data
7. Type the exact tenant slug.
8. Click `Delete tenant`.
9. Confirm the completion state shows deleted counts and auth user deletion count.
10. Close the modal and refresh platform overview.

Expected result:

- Tenant no longer appears in the platform tenant list.
- Follow-up lookup of the tenant slug returns no organization.
- Tenant admin login no longer succeeds.
- Initiative Owner and Viewer logins no longer succeed.

Observed during the 2026-05-04 live regression:

- Delete preview correctly reported object groups before deletion.
- At a short in-app-browser viewport, the modal's final buttons could be below the visible area while the modal did not scroll. Treat this as a UI regression if reproduced; API deletion can still be used by platform admin after explicit destructive confirmation.
- API deletion response should match preview counts exactly.

## Evidence to Capture

Record the following for every regression run:

- Test suffix and tenant slug.
- Checkout session ID.
- Stripe webhook delivery status and timestamp.
- Screenshots or recording of:
  - Stripe checkout summary.
  - Subscription success page.
  - People invite creation for Initiative Owner and Viewer.
  - Initiative Owner pipeline showing only owned initiatives.
  - Viewer pipeline showing all initiatives.
  - Tenant dashboard after records are created.
  - Platform delete preview counts.
  - Platform deletion completed state.
- Final platform overview after deletion.

## Failure Triage

- Checkout does not redirect to Stripe:
  - Verify frontend runtime config points at `/api`.
  - Verify API CORS allows `https://transmuter.ishirock.tech`.
- Checkout succeeds but tenant is not provisioned:
  - Verify Stripe webhook endpoint URL and signing secret.
  - Check latest `checkout.session.completed` webhook delivery.
  - Check backend logs for `/billing/webhook`.
- Tenant provisioned but login fails:
  - Check Supabase Auth user creation/invite state.
  - Set a sandbox password for the generated admin user if needed.
- Delete preview fails:
  - Check tenant-scoped cleanup table list for missing tables or missing `tenant_id`.
- Delete modal button is not reachable:
  - Reproduce at the current viewport.
  - Record screenshot.
  - File UI bug for modal max-height/overflow.
  - After explicit destructive confirmation, platform admin API deletion can verify cleanup.
- Deletion completes but tenant remains:
  - Verify organization row deletion and auth user deletion errors in the response.

## Automation Notes

This flow intentionally crosses Stripe-hosted checkout, so it should run as an opt-in regression, not as a default CI test.

Recommended future command:

```bash
TRANSMUTER_UI_BASE_URL=https://transmuter.ishirock.tech \
TRANSMUTER_API_BASE_URL=https://transmuter.ishirock.tech/api \
TRANSMUTER_E2E_STRIPE=true \
npm run e2e:stripe-onboarding
```

Automation should still pause or require explicit operator approval before the final Stripe sandbox `Subscribe` click when run from an interactive assistant, because it creates a sandbox subscription and transmits payment test details to Stripe.
