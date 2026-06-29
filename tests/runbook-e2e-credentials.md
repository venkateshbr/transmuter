# Transmuter Runbook E2E — Tenant Login Credentials (Second Pass)

Last updated: 2026-06-29

Environment: **dev** — https://transmuter-dev.ishirock.tech (login at `/auth/login`)
Stripe: sandbox (test card `4242 4242 4242 4242`, any future expiry/CVC).
All tenants created via real public signup + checkout. Role of each admin: `transformation_office`.

> These are throwaway dev test tenants. Same password is reused across scenarios for easy validation.

**Shared password (all scenarios):** `Transmuter#E2E2026`

| Scenario | Tenant (org) | Slug | Admin email | Currency / FY | Tenant ID |
|---|---|---|---|---|---|
| 7 — Pinnacle Professional Services | Pinnacle Professional Services | `pinnacle` | `pinnacle.to@transmuter-e2e.dev` | USD / Jan | `f9641073-e754-4dbd-9038-47c61c20bbb6` |
| 2 — Aurelia Retail Holdings | Aurelia Retail Holdings | `aurelia` | `aurelia.to@transmuter-e2e.dev` | GBP / Apr → **USD / Jan** (F14) | `4d1cec5d-d8fe-4fb3-9b6c-0e6bcbd4e663` |
| 3 — Nordvik Manufacturing | Nordvik Manufacturing | `nordvik` | `nordvik.to@transmuter-e2e.dev` | EUR / Jan → **USD / Jan** (F14) | `935b5ee1-ee8b-4d4a-aaf5-63f609f8beba` |
| 5 — Cascade Financial Services | Cascade Financial Services | `cascade` | `cascade.to@transmuter-e2e.dev` | AUD / Jul → **USD / Jan** (F14) | `cf850726-bdd7-490b-b3fe-a848ac20a5da` |
| 6 — Verdant Agritech | Verdant Agritech | `verdant` | `verdant.to@transmuter-e2e.dev` | BRL / Jan → **USD / Jan** (F14) | `6bf98baa-9b57-4f76-b77e-6918ee637e2b` |
| 4 — Helios Health Systems | Helios Health Systems | `helios` | `helios.to@transmuter-e2e.dev` | USD / Oct → **USD / Jan** (F14: fiscal only) | `da1682a8-cea7-4c4a-b78c-777ed359bea5` |
| 1 — Meridian Logistics Group | Meridian Logistics Group | `meridian` | `meridian.to@transmuter-e2e.dev` | SGD / Jan → **USD / Jan** (F14: currency only) | `13aa1b04-e939-43ee-8323-46c0f0ed35db` |
| 8 — Stellar Media & Entertainment | Stellar Media & Entertainment | `stellar` | `stellar.to@transmuter-e2e.dev` | USD / Jan (no F14 impact) | `db01be51-ab48-429f-babd-79e1ebcaa00e` |

_Rows added as each scenario is built. To validate: open the dev URL → Login → use the admin email + shared password above._

---

## ACME Operating Model Role Users

Environment: **dev** — https://transmuter-dev.ishirock.tech/auth/login

These are synthetic ACME demo users created through the **People > Add User >
Temp Password / Create User** UI flow on 2026-06-29. They are for validating the
ACME Transformation Office operating model and should not be used for production
or customer access.

All users below have completed first-login password change and are active.

**Shared current password:** `AcmeRole202606291323A1`

| Demo user | Email | Role | Validation scope |
|---|---|---|---|
| Priya Raman | `acme-to-202606291323@acme-transformation.dev` | `transformation_office` | Full tenant and portfolio permissions. Validated `/people`, `/admin`, `/shared-costs`, and `/initiatives/new`. |
| Jordan Lee | `acme-admin-202606291323@acme-transformation.dev` | `tenant_admin` | Users, access, tenant setup, dimensions, dashboard setup, governance setup, and billing portal. Validated deny on `/shared-costs` and `/initiatives/new`. |
| Maya Patel | `acme-pmo-202606291323@acme-transformation.dev` | `pmo_lead` | Governance, PMO, progress, meetings, actions, risks, KPIs, and cadence. Validated deny on `/people`, `/shared-costs`, and `/initiatives/new`. |
| Omar Haddad | `acme-finance-202606291323@acme-transformation.dev` | `finance_lead` | Financial configuration, shared costs, benefit validation, actuals, bankable plan, and benefit tracking. Validated `/admin` and `/shared-costs`; denied `/people` and `/initiatives/new`. |
| Lena Ortiz | `acme-workstream-202606291323@acme-transformation.dev` | `workstream_lead` | Assigned-workstream portfolio visibility and execution evidence. Assigned through People to the current ACME workstreams. Validated deny on setup and creation routes. |
| Ethan Brooks | `acme-owner-202606291323@acme-transformation.dev` | `initiative_owner` | Owned initiative master data, financial assumptions, and execution evidence. Assigned as market owner and group owner on `Transformation PMO & Benefits Office` (`555e952b-6bbd-4dba-ab28-421d0ecad25a`). |
| Sofia Chen | `acme-benefit-202606291323@acme-transformation.dev` | `business_benefit_owner` | Benefit realization evidence, sustainment notes, and ledger updates. Validated portfolio access and denied setup/creation routes. |
| Daniel Wright | `acme-exec-202606291323@acme-transformation.dev` | `executive_sponsor` | Read-only executive portfolio, financial, and Control Tower review. Validated deny on setup and creation routes. |
| Nora Singh | `acme-viewer-202606291323@acme-transformation.dev` | `viewer` | Read-only management portfolio and dashboard review. Validated deny on setup and creation routes. |

Setup/admin seed account used to create and validate the users:

| User | Email | Role | Password |
|---|---|---|---|
| RBAC Transformation Office Director | `rbac-transformation-office@acme-transformation.dev` | `transformation_office` | `Transmuter2026!` |

Validation completed on dev:

| Area | Result |
|---|---|
| UI user creation | All nine role users created through **People > Add User > Temp Password / Create User**; no invite links were sent. |
| First login | All nine role users logged in through `/auth/login`; first-login password changes completed. |
| User status | All nine role users are `active` with `must_change_password=false`. |
| Scoped ownership | Initiative owner assigned through the initiative edit UI and validated on the assigned initiative edit route. |
| UI permissions | Guarded route checks matched the operating-model expectations in `TRANSMUTER_E2E_TEST_RUNBOOK.md`. |
| API permissions | `/auth/me`, `/users`, duplicate `/users` create probe, and shared-cost reporting settings probes matched role expectations. |
