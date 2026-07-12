# Five-Tenant Dev Acceptance Runbook

Issues: [#398](https://github.com/venkateshbr/transmuter/issues/398) (fixture),
[#399](https://github.com/venkateshbr/transmuter/issues/399) (acceptance)
Date: 2026-07-12
Environment: `https://transmuter-dev.ishirock.tech`
Scenario as-of date: `2028-06-30`

This runbook validates a realistic 2026-2028 transformation program across five
isolated development tenants. It follows
[`SDLC_PROTOCOL.md`](SDLC_PROTOCOL.md), especially the requirement for a real
running API, deterministic data, and browser testing against the real Angular
application. Production is never a target for this procedure.

The scenario and checks are based on:

- [`acme-demo-tenant-ui-setup-guide.md`](../user-guides/acme-demo-tenant-ui-setup-guide.md)
- [`acme-transformation-office-detailed-setup-and-demo-guide.md`](../user-guides/acme-transformation-office-detailed-setup-and-demo-guide.md)
- [`acme-transformation-office-management-runbook.md`](../user-guides/acme-transformation-office-management-runbook.md)
- [`admin-financial-configuration-user-guide.md`](../user-guides/admin-financial-configuration-user-guide.md)
- [`financial-engine-end-to-end-walkthrough.md`](../user-guides/financial-engine-end-to-end-walkthrough.md)
- [`automation-productivity-financial-scenario-walkthrough.md`](../user-guides/automation-productivity-financial-scenario-walkthrough.md)
- [`ishirock-transformation-office-detailed-setup-and-demo-guide.md`](../user-guides/ishirock-transformation-office-detailed-setup-and-demo-guide.md)
- [`TENANT_ONBOARDING_USER_GUIDE.md`](TENANT_ONBOARDING_USER_GUIDE.md)

## Scope

Test every non-meeting tenant route on all five tenants, including dashboard,
initiative, progress, governance, finance, shared-cost, control-tower, people,
profile, and administration views. Exercise controlled create/update/delete,
import/export, filters, drilldowns, approval, and role-boundary workflows where
the role permits them.

Explicit exclusions:

- Do not open or call `/meetings`, meeting-series, meeting-session, agenda,
  attendee, transcript, minutes, Microsoft Graph, or meeting-artifact workflows.
- Do not exercise meeting-backed action-item CRUD. Open
  `/progress/action-items` only to verify its valid empty state.
- Do not call Admin meeting-cleanup actions.
- Paid signup/Stripe provisioning is independent of this deterministic fixture.
  Test the public home and login boundary, but use
  [`STRIPE_ONBOARDING_E2E_REGRESSION.md`](STRIPE_ONBOARDING_E2E_REGRESSION.md)
  for checkout acceptance.

The fixture must leave `meetings`, `meeting_sessions`, `agenda_items`, and
`action_items` at exactly zero for every tenant.

## Prerequisites

1. Confirm #398 is `status:in-progress` while the fixture is being prepared and
   #399 is assigned to Aksha. Only Aksha moves accepted work to
   `status:in-review`; only Vishwa closes the issues.
2. Merge and deploy the exact fixture/application commit to the Hostinger dev
   project `transmuter-dev-hostinger`. Record the commit and deployment action in
   the evidence table below.
3. Confirm both dev health surfaces succeed:

   ```bash
   curl --fail --show-error --silent https://transmuter-dev.ishirock.tech/health
   curl --fail --show-error --silent https://transmuter-dev.ishirock.tech/api/health
   ```

4. Obtain an approved Hostinger API token and a shared fixture password of at
   least 12 characters. Do not store either value in this file, a manifest,
   screenshots, shell history, or issue comments.
5. Quiesce dev tenant provisioning, invitation, and integration activity for the
   seed window. The script preflights all five profiles before the first write,
   but the preflight is not protected by a cross-tenant transaction lock.
6. Make the in-app Browser target available. Acceptance evidence from a mocked
   API, a manually prepared browser state, or a smoke-only check does not count.

## Tenant Profiles

Each tenant has initiative codes `ENT-001` through `ENT-010`, with sector-specific
names, structures, values, risks, KPIs, and financial assumptions.

| Tenant                     | Slug and login domain                                                                      | Country/region | Currency / fiscal start | Baseline revenue / gross margin | Program theme                                            |
| -------------------------- | ------------------------------------------------------------------------------------------ | -------------- | ----------------------- | ------------------------------- | -------------------------------------------------------- |
| Acme Global Manufacturing  | `qa-e2e-20260712-acme-global-manufacturing`<br>`acme-global-manufacturing.transmuter.test` | United States  | USD / January           | 20,000,000 / 9,000,000          | Manufacturing productivity and profitable growth         |
| Northstar Retail Group     | `qa-e2e-20260712-northstar-retail-group`<br>`northstar-retail-group.transmuter.test`       | Singapore      | SGD / July              | 160,000,000 / 72,000,000        | Omnichannel retail growth and operating efficiency       |
| Meridian Commercial Bank   | `qa-e2e-20260712-meridian-commercial-bank`<br>`meridian-commercial-bank.transmuter.test`   | United Kingdom | GBP / April             | 240,000,000 / 108,000,000       | Digital banking growth, control, and productivity        |
| Solstice Health Network    | `qa-e2e-20260712-solstice-health-network`<br>`solstice-health-network.transmuter.test`     | European Union | EUR / January           | 120,000,000 / 54,000,000        | Patient access, clinical capacity, and sustainable value |
| Horizon Energy & Utilities | `qa-e2e-20260712-horizon-energy-utilities`<br>`horizon-energy-utilities.transmuter.test`   | Australia      | AUD / July              | 300,000,000 / 135,000,000       | Reliable energy transition and asset productivity        |

Login conventions:

- Tenant admin: `admin@<login-domain>` with role `transformation_office`.
- Role probe: `rbac-<role-with-hyphens>@<login-domain>`.
- Seeded roles: `transformation_office`, `tenant_admin`, `pmo_lead`,
  `finance_lead`, `workstream_lead`, `initiative_owner`,
  `business_benefit_owner`, `executive_sponsor`, and `viewer`.
- All fixture identities use the reserved `.transmuter.test` suffix and the same
  runtime-provided fixture password.

## Seed Command

Run from a clean checkout of the reviewed commit. The prompts below avoid
placing secrets in command history.

```bash
cd /Users/vramakrishnaiah/dev/transmuter
read -rs 'HOSTINGER_API_KEY?Dev Hostinger API token: '
export HOSTINGER_API_KEY
printf '\n'
read -rs 'TRANSMUTER_MULTI_TENANT_PASSWORD?Shared fixture password (12+ chars): '
export TRANSMUTER_MULTI_TENANT_PASSWORD
printf '\n'

cd apps/api
uv run python scripts/seed_five_tenant_transformation_program.py \
  --environment dev \
  --hostinger-project transmuter-dev-hostinger \
  --confirm seed-five-tenant-dev-program \
  --manifest ../../scratch/five-tenant-dev-manifest.json
```

The command must finish with `Seeded and verified 5 isolated dev tenants`.
The local manifest contains tenant IDs, fixture emails, currencies, fiscal
starts, scenario date, and counts; it contains no password or token. Keep it
under `scratch/` and do not treat the manifest alone as acceptance evidence.

## Expected Data

The seed itself enforces these tenant-scoped invariants. Values marked `>=` are
minimums because the scenario as-of cutoff can affect the number of time-phased
rows; use the generated manifest for the observed count.

| Data set                               |    Per tenant | Five-tenant total |
| -------------------------------------- | ------------: | ----------------: |
| Users                                  |            10 |                50 |
| Initiatives                            |    10 exactly |        50 exactly |
| Milestones / checklist items           |       30 / 30 |         150 / 150 |
| KPIs / KPI entries                     |      20 / 240 |       100 / 1,200 |
| Risks / status updates                 |       20 / 20 |         100 / 100 |
| Initiative dependencies                |             3 |                15 |
| Approved gate/rebaseline submissions   |         >= 41 |            >= 205 |
| Benefit lines                          |            30 |               150 |
| Financial metric values                |      >= 2,220 |         >= 11,100 |
| Financial cost lines / forecasts       |       90 / 30 |         450 / 150 |
| Bankable plan versions                 |            11 |                55 |
| Benefit realization ledger rows        |           240 |             1,200 |
| Workstream target locks                |             5 |                25 |
| Shared-cost pools                      |             4 |                20 |
| Dashboard configuration rows           |            10 |                50 |
| Meetings / sessions / agenda / actions | 0 / 0 / 0 / 0 |     0 / 0 / 0 / 0 |

Also verify five business units and five workstreams per tenant, two KPIs and two
risks per initiative, three milestones and three benefit lines per initiative,
all four benefit validation states (`draft`, `submitted`, `rejected`, and
`finance_validated`), `baseline`/`plan_base`/`plan_high`/`actual` scenarios,
direct and recurring costs, locked workstream targets, four shared-cost methods,
Gate 1-4 approval history, and the governed `ENT-005` bankable-plan rebaseline to
version 2. Future actual periods must not be fabricated beyond `2028-06-30`.

## API And RBAC Acceptance

### Guarded real-API verifier

Run the public-API verifier first. It is pinned to the exact HTTPS dev API,
refuses redirects and meeting/action-item paths, authenticates all 50 identities,
checks portfolio and per-initiative counts, exercises reversible mutations,
downloads representative exports, and performs cross-tenant denial checks. Its
report is validated to contain no tokens, passwords, or email addresses.

```bash
uv run python scripts/verify_five_tenant_dev_api_acceptance.py \
  --environment dev \
  --confirm verify-five-tenant-dev-api \
  --base-url https://transmuter-dev.ishirock.tech/api \
  --report ../../scratch/five-tenant-api-acceptance.json
```

The command must finish with `Five-tenant dev API acceptance passed`; the report
must show five tenants, 50 authenticated users, and 55 cross-tenant denials. It
also verifies configured currency/fiscal-start inputs, people and pressure,
workstream locks, shared-cost periods/rules/runs, exports, and role scoping.
Preserve the summary and secret-free report as evidence. Use `--skip-mutations`
only for a follow-up read-only rerun, not for the primary acceptance run.

### Real API matrix

Capture status, tenant ID, counts, and reconciliation results without recording
tokens. Repeat the read matrix for every tenant admin; use the role identities
for permission checks.

| Surface                  | Required checks                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication           | `POST /api/auth/login` and `GET /api/auth/me` return the expected subject, tenant, and role. Invalid and anonymous requests fail with 401. Dev identities have only the `transmuter_authorization_transmuter_dev` authorization scope.                                                                                                                                                                                                 |
| Portfolio                | Initiative list/detail returns exactly the tenant's ten codes and sector-specific names. Dashboard, matrix, roadmap, risk, KPI, milestone, status, governance, dependency, and search results contain no other tenant's IDs or labels.                                                                                                                                                                                                 |
| Financials               | Portfolio financials, value bridge, value ramp, benefits register, initiative portfolio, investments/payback, contributor, board-pack, initiative grid, cost lines, forecasts, assumptions, benefit ledger, bankable plan/history, and target lock endpoints return coherent tenant currency and calendar reporting periods. Decimal money is represented as JSON strings. Non-January fiscal reporting is the known limitation below. |
| Governance               | Gate 1-4 history is approved for every initiative; criteria snapshots are present; `ENT-005` has the approved rebaseline submission and two bankable plan versions.                                                                                                                                                                                                                                                                    |
| Delivery controls        | Every initiative has three milestones, checklist coverage, two KPIs with quarterly entries, two risks, one submitted plus one draft status update, and expected cross-initiative dependency coverage.                                                                                                                                                                                                                                  |
| Shared costs and reports | Four pools reconcile plan/actual allocations to their pool totals; preview/approved/locked state is explainable; Control Tower direct, allocated, burdened, and net values reconcile.                                                                                                                                                                                                                                                  |
| Admin and people         | Setup is complete, configuration is tenant-specific, ten users are present, workstream/team assignments are correct, and audit output contains only tenant events. Integration connections, OAuth state, and pending invites remain zero.                                                                                                                                                                                              |
| Excluded data            | Meeting, meeting-session, agenda, and action-item counts remain zero. Do not call their mutation APIs.                                                                                                                                                                                                                                                                                                                                 |

April and July fiscal starts are edge-case inputs, not a claim that current
reports are fiscal-calendar correct. The platform currently persists the tenant
setting but its reporting services aggregate by calendar year and month. Confirm
the behavior on Northstar, Meridian, and Horizon under
[#401](https://github.com/venkateshbr/transmuter/issues/401), and do not sign off
shifted-fiscal-period accuracy until that high-severity defect is fixed and
retested.

### Permission and isolation matrix

Validate allowed and denied behavior in both API responses and visible UI
affordances:

| Role                     | Positive check                                                                                                      | Negative/boundary check                                                                                                                  |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `transformation_office`  | Full tenant, portfolio, governance, finance, user, and setup workflows.                                             | Cannot access the platform-admin console or another tenant.                                                                              |
| `tenant_admin`           | User access, setup, dimensions, dashboard, governance configuration, and billing status.                            | No cross-tenant or platform-admin access.                                                                                                |
| `pmo_lead`               | Governance, milestone, checklist, dependency, risk, KPI, and status workflows.                                      | User administration and financial-engine changes are denied.                                                                             |
| `finance_lead`           | Financial scope, values, costs, validation, bankable plans, realization, forecasts, shared costs, and target locks. | User administration and unrelated setup changes are denied.                                                                              |
| `workstream_lead`        | Assigned-workstream initiatives and execution evidence only.                                                        | An initiative in an unassigned workstream is hidden or returns 403/404.                                                                  |
| `initiative_owner`       | Owned initiative edit, execution evidence, status, and financial assumptions.                                       | An unowned initiative is read-only, hidden, or returns 403/404 for mutation. Seeded owned codes are `ENT-002`, `ENT-005`, and `ENT-008`. |
| `business_benefit_owner` | Portfolio read plus realization evidence and benefit-ledger updates.                                                | Financial-engine and user administration are denied.                                                                                     |
| `executive_sponsor`      | Executive dashboard, financials, and Control Tower read access.                                                     | Every tenant-data mutation is denied and no edit control is shown.                                                                       |
| `viewer`                 | Management dashboard and portfolio read access.                                                                     | Every tenant-data mutation is denied and no edit control is shown.                                                                       |

For tenant isolation, obtain a valid resource ID from tenant B, then request it
with tenant A's token. Test initiative detail, financials, team, milestones,
risks, KPIs, status, governance, benefit ledger, dependencies, and shared-cost
resources. Every request must return 403/404, never 200 and never a payload that
reveals tenant B. Repeat with at least one read/write-capable role and one
read-only role. A tenant token must also be denied at `/api/platform/overview`.

## Browser UI Matrix

Run every view row below on all five tenant admins against the public dev app.
Exercise role-specific mutations with the matching role, distributing mutations
across tenants while retaining read coverage everywhere. Test desktop and mobile
viewports, light and dark themes, direct URL reloads, browser back/forward,
loading/empty/error states, keyboard access, visible focus, responsive text, and
the browser console/network log. No unexplained 4xx/5xx, uncaught exception,
tenant leak, overlap, clipped control, or blank visualization is acceptable.

| Route                                                      | Required UI checks                                                                                                                                                                                                                                                                                                                                          |
| ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`, `/auth/login`, `/profile`                             | Public shell and login render; valid/invalid login and logout work; tenant/name/role are correct; profile/theme changes persist or are restored.                                                                                                                                                                                                            |
| `/dashboard`                                               | Summary, pipeline, RAG, pressure, risk heatmap, value matrix, KPI pulse, decision/action areas, recent activity, all BU/workstream/priority/tag filters, cell drilldown, reset, and executive PDF/XLSX export reconcile to the selected tenant.                                                                                                             |
| `/initiatives/pipeline`                                    | Ten initiatives, stage/RAG/value labels, search/filter/sort, pagination, detail navigation, and archive state. Open/cancel create on all tenants; complete one temporary create/governance flow and reset afterward.                                                                                                                                        |
| `/initiatives/matrix`                                      | Workstream-by-tag cells, totals, empty cells, filters, and contributor drilldowns reconcile to pipeline and dashboard values.                                                                                                                                                                                                                               |
| `/initiatives/new`                                         | Guided fields, required validation, financial setup readiness, AI-assisted intake graceful degradation, create/cancel, permissions, and navigation. Create only a temporary test initiative and remove it with the final reseed.                                                                                                                            |
| `/initiatives/:id`, `/initiatives/:id/edit`                | Summary, team, milestones/checklists, dependencies, KPIs, risks, status, governance, financials, benefit evidence, ownership, save/cancel, validation, and permissions. Test one controlled CRUD cycle for each non-meeting child type.                                                                                                                     |
| `/initiatives/:id/financial-scope`                         | Active metrics, formula rows, scenarios, cost categories, baseline, save/reload, and role restrictions. Formula rows remain read-only while calculated values update.                                                                                                                                                                                       |
| `/financials`                                              | Monthly/quarterly/yearly, reporting year, plan as-of, stage/category, benefit/actual toggles, baselines, summary, trend, in-year value, run-rate, plan-vs-actual, cost/metric breakdown, contributor drawer, value bridge, and board-pack export reconcile under the current calendar-period contract. Record the non-January fiscal limitation separately. |
| `/financials/initiative-portfolio`                         | Ten rows, tenant currency, baselines, metric columns, one-time/recurring cost, net run-rate, completeness flags, sort/filter, and detail navigation reconcile.                                                                                                                                                                                              |
| `/financials/benefits-register`                            | Thirty lines, metric/class, validation statuses and history, evidence, plan/actual, risk adjustment, filter/sort, submit/validate/reject/handoff permissions, and totals reconcile.                                                                                                                                                                         |
| `/financials/benefit-tracking`                             | Portfolio/workstream/initiative scopes, locked baseline, actual realization, variance, reporting-period filters, evidence/notes, and 240 ledger rows reconcile to bankable plans and actuals.                                                                                                                                                               |
| `/financials/bankable-plan`                                | Ten initiatives, eleven versions, Gate 2 locks, locked snapshot detail, history, `ENT-005` version 2 and 8% FY2028 GM rebaseline, audit reason, and permission boundaries.                                                                                                                                                                                  |
| `/financials/investments-payback`                          | Investment, benefit, payback, break-even, filter/sort, negative/zero state, and initiative drilldown reconcile to cost and benefit data.                                                                                                                                                                                                                    |
| `/financials/waterline`                                    | Five workstream locks, cutoff/reporting-year filters, approved initiatives, committed versus actual value, variance, preview, and locked state reconcile.                                                                                                                                                                                                   |
| `/shared-costs`                                            | Four pools, periods, category/scenario, policies, targets, weights, all seeded allocation methods, preview reconciliation, approve/lock/void permissions, audit trail, and reporting treatment. Use a temporary pool for mutation tests and reset it.                                                                                                       |
| `/reports/control-tower`                                   | Portfolio filters, dependency/governance attention, direct benefits/costs, allocated costs, burdened costs, net after allocation, owner/investor views where linked, exports, and dashboard reconciliation.                                                                                                                                                 |
| `/progress`, `/progress/roadmap`, `/progress/dependencies` | Thirty milestones, checklist state, overdue/in-progress/completed chronology, pressure, dependency lines, filters, zoom/date behavior, detail navigation, CRUD permissions, and the dependencies-to-roadmap redirect.                                                                                                                                       |
| `/progress/status-updates`                                 | Ten submitted and ten draft updates, compliance/recency, RAG narrative, draft/generate/edit/submit workflow, filters, nudges where permitted, and scenario chronology. Agent failure must degrade gracefully.                                                                                                                                               |
| `/progress/action-items`                                   | Valid zero-count empty state only. Do not create, edit, complete, cancel, or delete action items.                                                                                                                                                                                                                                                           |
| `/pmo/governance`                                          | Portfolio gate history, criteria snapshots, approved decisions, stage state, filters, submission/decision permissions, and bankable-plan linkage. Use a temporary initiative for a write flow, then reset.                                                                                                                                                  |
| `/pmo/risks`                                               | Twenty risks, matrix/heatmap, owner/mitigation, severity and status filters, initiative link, CRUD, and role restrictions.                                                                                                                                                                                                                                  |
| `/pmo/kpis`                                                | Twenty KPIs and 240 quarterly entries, targets/actuals/trends, configured fiscal-start display versus current calendar-period behavior, filters, initiative link, CRUD, and role restrictions.                                                                                                                                                              |
| `/pmo/ai-insights`                                         | Read/suggestion experience, loading/failure/disabled states, traceable responses, and graceful degradation. Any agent-proposed database write requires an explicit HITL confirmation.                                                                                                                                                                       |
| `/people`                                                  | Ten users, role/title/status/workstream/team assignments, filters/detail, admin affordances, and role denial. Test one synthetic invite through the UI, revoke it in the same flow, and confirm no invite or Auth identity remains.                                                                                                                         |
| `/admin`                                                   | Setup `8/8`, organization settings, business units, workstreams, markets/themes/tags, reporting currency/fiscal start, metrics/formulas, baselines, scenarios, cost categories, value bridge, attributes, stage gates/criteria, dashboard configuration, audit log, billing status, and non-destructive cleanup preview. Restore changes or reseed.         |
| `/platform`                                                | Tenant users are denied. With the existing dev platform-admin only, verify all five tenants are listed and do not invoke tenant deletion.                                                                                                                                                                                                                   |

Imports and exports must include a portfolio/initiative export, initiative import
preview, one initiative workbook roundtrip, financial XLSX roundtrip, board-pack
XLSX, and executive summary PDF. Verify file type, non-empty content, tenant
branding/currency, row counts, formulas/values, and no cross-tenant data.

## Rerun And Reset

The full seed is repeatable but intentionally destructive inside its owned
fixture tenants:

- Before any write, all five profiles are checked for exact fixture ownership,
  reserved email domains, Auth/platform subject parity, dev-scoped roles, and
  absence of unexpected users, invites, integrations, or OAuth state.
- The script refuses a tenant without the exact `qa_fixture` owner/slug marker or
  an Auth identity without the matching `transmuter_fixture` marker. It also
  refuses production, cloud Supabase, a non-dev schema, the production hostname,
  a different Hostinger project, or an incorrect confirmation string.
- A successful rerun deletes and recreates tenant-scoped configuration,
  initiative, governance, financial, dashboard, progress, and shared-cost rows.
  It does not reset another tenant and it does not proceed past a failed
  preflight.
- Generated UUIDs change. Do not use stable database IDs as an idempotence
  assertion, and discard old deep links after a rerun. Compare slugs, codes,
  logical content, counts, totals, and role behavior instead.
- Portfolio mutations made during UI testing are removed by a rerun. Organization
  settings and existing identity changes must be restored explicitly. Never
  leave a pending invite or unexpected identity; either causes the next
  preflight to stop.

Recommended order:

1. Seed once and archive the redacted manifest/count output.
2. Seed a second time before product testing; verify the same logical counts and
   reconciliations to prove reset repeatability.
3. Run API, RBAC, isolation, and full browser matrices.
4. Record findings and issues; fix/redeploy/reseed/retest as needed.
5. After mutation tests, seed once more to return dev to the canonical state,
   then repeat health, invariant, dashboard, and isolation read checks.
6. Clear secrets from the shell:

   ```bash
   unset TRANSMUTER_MULTI_TENANT_PASSWORD
   unset HOSTINGER_API_KEY
   ```

## Evidence And Findings

Do not record passwords, bearer/refresh tokens, Hostinger environment output, or
unredacted personal information. Fixture emails are synthetic, but screenshots
must still exclude browser storage and authorization headers.

### Run evidence

| Evidence                                      | Result  |
| --------------------------------------------- | ------- |
| Application commit / PR                       | Pending |
| Hostinger dev action / completion time        | Pending |
| API and web health                            | Pending |
| Initial seed manifest / count summary         | Pending |
| Repeat-seed logical diff                      | Pending |
| 50-user guarded API verifier                  | Pending |
| 50-user role/RBAC results                     | Pending |
| Cross-tenant isolation matrix                 | Pending |
| Browser target / desktop and mobile viewports | Pending |
| Light/dark and accessibility checks           | Pending |
| Console/network error log                     | Pending |
| Export/import artifacts and reconciliation    | Pending |
| Final canonical reseed / read verification    | Pending |

### Per-tenant result

| Tenant                     | Seed    | API/data | RBAC    | Isolation | All UI routes | Dashboards/reconciliation | Imports/exports | Result  |
| -------------------------- | ------- | -------- | ------- | --------- | ------------- | ------------------------- | --------------- | ------- |
| Acme Global Manufacturing  | Pending | Pending  | Pending | Pending   | Pending       | Pending                   | Pending         | Pending |
| Northstar Retail Group     | Pending | Pending  | Pending | Pending   | Pending       | Pending                   | Pending         | Pending |
| Meridian Commercial Bank   | Pending | Pending  | Pending | Pending   | Pending       | Pending                   | Pending         | Pending |
| Solstice Health Network    | Pending | Pending  | Pending | Pending   | Pending       | Pending                   | Pending         | Pending |
| Horizon Energy & Utilities | Pending | Pending  | Pending | Pending   | Pending       | Pending                   | Pending         | Pending |

### Finding log

Create a GitHub issue for each reproducible product defect and link it here. Use
P0 for security/data loss or a release stop, P1 for a broken critical workflow,
P2 for a material workaround or incorrect report, and P3 for minor usability or
cosmetic defects.

| ID / issue                                                   | Severity | Tenant / role                                | Route                                           | Steps and evidence                                                                  | Expected                                                                | Actual                                                                                                         | Fix / retest                                                                          | Status  |
| ------------------------------------------------------------ | -------- | -------------------------------------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------- |
| [#401](https://github.com/venkateshbr/transmuter/issues/401) | P1       | Northstar, Meridian, Horizon / finance roles | `/financials`, financial dashboards and reports | Compare configured July/April fiscal starts with reporting-year periods and totals. | Periods and annual totals follow the configured tenant fiscal calendar. | Known limitation: reporting services aggregate by calendar year/month despite the stored fiscal-start setting. | Fix and rerun affected API/UI/dashboard rows before shifted-fiscal accuracy can pass. | Open    |
| Pending                                                      | Pending  | Pending                                      | Pending                                         | Pending                                                                             | Pending                                                                 | Pending                                                                                                        | Pending                                                                               | Pending |

Aksha may mark #399 accepted only when every required row has evidence, all P0/P1
findings are resolved and retested, remaining P2/P3 items have explicit issue and
release decisions, the canonical final seed is restored, and production remains
untouched.

## Production Safety

Never substitute `transmuter.ishirock.tech`, schema `transmuter`,
`SUPABASE_TARGET=cloud`, a production Docker project, or a production tenant in
any command in this runbook. Do not run production promotion as part of #398 or
#399. Production promotion requires the normal release manifest, Sthira
readiness, Vishwa review, and a separate explicit founder confirmation after dev
acceptance is complete.
