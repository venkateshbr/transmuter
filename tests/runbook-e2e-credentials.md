# Transmuter Runbook E2E — Tenant Login Credentials (Second Pass)

Last updated: 2026-08-05

Environment: **dev** — https://transmuter-dev.ishirock.tech (login at `/auth/login`)
Stripe: sandbox (test card `4242 4242 4242 4242`, any future expiry/CVC).
All tenants created via real public signup + checkout. Role of each admin: `transformation_office`.

> Credentials are never committed. Active identities use unique passwords stored
> in the ignored, mode-`0600` local `credentials.json` file.

**Credential source (active scenarios):** local `credentials.json` under `runbook_e2e.users`; each active user has a unique password.

| Scenario | Tenant (org) | Slug | Admin email | Currency / FY | Tenant ID |
|---|---|---|---|---|---|
| 7 — Pinnacle Professional Services | Pinnacle Professional Services | `pinnacle` | `pinnacle.to@transmuter-e2e.dev` | USD / Jan | `f9641073-e754-4dbd-9038-47c61c20bbb6` |
| 2 — Aurelia Retail Holdings | Aurelia Retail Holdings | `aurelia` | Identity absent; historical scenario only | GBP / Apr → **USD / Jan** (F14) | Historical |
| 3 — Nordvik Manufacturing | Nordvik Manufacturing | `nordvik` | Identity absent; historical scenario only | EUR / Jan → **USD / Jan** (F14) | Historical |
| 5 — Cascade Financial Services | Cascade Financial Services | `cascade` | Identity absent; historical scenario only | AUD / Jul → **USD / Jan** (F14) | Historical |
| 6 — Verdant Agritech | Verdant Agritech | `verdant` | Identity absent; historical scenario only | BRL / Jan → **USD / Jan** (F14) | Historical |
| 4 — Helios Health Systems | Helios Health Systems | `helios` | Identity absent; historical scenario only | USD / Oct → **USD / Jan** (F14: fiscal only) | Historical |
| 1 — Meridian Logistics Group | Meridian Logistics Group | `meridian` | Identity absent; historical scenario only | SGD / Jan → **USD / Jan** (F14: currency only) | Historical |
| 8 — Stellar Media & Entertainment | Stellar Media & Entertainment | `stellar` | Identity absent; historical scenario only | USD / Jan (no F14 impact) | Historical |

Only Pinnacle remains an active scenario identity. The seven other historical
identities were absent from shared Supabase Auth on 2026-08-05 and their exposed
credentials were rejected by both public environments. Use credential alias
`runbook_e2e.users.scenario_pinnacle` for the active scenario.

---

## ACME Operating Model Role Users

Environment: **dev** — https://transmuter-dev.ishirock.tech/auth/login

These are synthetic ACME demo users created through the **People > Add User >
Temp Password / Create User** UI flow on 2026-06-29. They are for validating the
ACME Transformation Office operating model and should not be used for production
or customer access.

All users below have completed first-login password change and are active.

**Credential source:** local `credentials.json` under the matching `runbook_e2e.users.acme_*` alias; each user has a unique password.

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

| User | Email | Role | Credential alias |
|---|---|---|---|
| RBAC Transformation Office Director | `rbac-transformation-office@acme-transformation.dev` | `transformation_office` | `runbook_e2e.users.acme_rbac_setup` |

Validation completed on dev:

| Area | Result |
|---|---|
| UI user creation | All nine role users created through **People > Add User > Temp Password / Create User**; no invite links were sent. |
| First login | All nine role users logged in through `/auth/login`; first-login password changes completed. |
| User status | All nine role users are `active` with `must_change_password=false`. |
| Scoped ownership | Initiative owner assigned through the initiative edit UI and validated on the assigned initiative edit route. |
| UI permissions | Guarded route checks matched the operating-model expectations in `TRANSMUTER_E2E_TEST_RUNBOOK.md`. |
| API permissions | `/auth/me`, `/users`, duplicate `/users` create probe, and shared-cost reporting settings probes matched role expectations. |
