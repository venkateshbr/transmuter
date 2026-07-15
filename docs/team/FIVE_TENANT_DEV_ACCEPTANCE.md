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

Test every tenant route on all five tenants, including dashboard,
initiative, progress, governance, finance, shared-cost, control-tower, people,
profile, and administration views. Exercise controlled create/update/delete,
import/export, filters, drilldowns, approval, and role-boundary workflows where
the role permits them. On Acme, additionally exercise the complete native
meeting command center, invite/password lifecycle, and Admin bulk meeting
cleanup through the browser.

External-integration exclusions:

- Do not grant Microsoft Graph consent, create a live Teams event, or fetch a
  live Teams transcript unless the environment owner has separately approved
  the tenant registration and consent window under #220/#389/#390.
- Core Transmuter meeting series, sessions, agenda, notes, AI draft minutes,
  artifacts, completion, and tenant-scoped Admin cleanup are in scope and do
  not depend on Teams.
- Do not leave meeting-backed actions, invite rows, or temporary meeting series
  in the canonical fixture after acceptance.
- Paid signup/Stripe provisioning is independent of this deterministic fixture.
  Test the public home and login boundary, but use
  [`STRIPE_ONBOARDING_E2E_REGRESSION.md`](STRIPE_ONBOARDING_E2E_REGRESSION.md)
  for checkout acceptance.

The final reset must leave `meetings`, `meeting_sessions`, `agenda_items`,
`action_items`, and `user_invites` at exactly zero for every tenant.

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
6. Install Playwright locally under ignored `scratch/` and launch one headed
   Chrome process from the CLI. Acceptance evidence from a mocked API, a
   manually prepared browser state, or a smoke-only check does not count.

## Tenant Profiles

Each tenant has initiative codes `ENT-001` through `ENT-010`, with sector-specific
names, structures, values, risks, KPIs, and financial assumptions.

| Tenant                     | Slug and login domain                                                                                      | Country/region | Currency / fiscal start | Baseline revenue / gross margin | Program theme                                            |
| -------------------------- | ---------------------------------------------------------------------------------------------------------- | -------------- | ----------------------- | ------------------------------- | -------------------------------------------------------- |
| Acme Global Manufacturing  | `qa-e2e-20260712-acme-global-manufacturing`<br>`acme-global-manufacturing.qa.transmuter-dev.ishirock.tech` | United States  | USD / January           | 20,000,000 / 9,000,000          | Manufacturing productivity and profitable growth         |
| Northstar Retail Group     | `qa-e2e-20260712-northstar-retail-group`<br>`northstar-retail-group.qa.transmuter-dev.ishirock.tech`       | Singapore      | SGD / July              | 160,000,000 / 72,000,000        | Omnichannel retail growth and operating efficiency       |
| Meridian Commercial Bank   | `qa-e2e-20260712-meridian-commercial-bank`<br>`meridian-commercial-bank.qa.transmuter-dev.ishirock.tech`   | United Kingdom | GBP / April             | 240,000,000 / 108,000,000       | Digital banking growth, control, and productivity        |
| Solstice Health Network    | `qa-e2e-20260712-solstice-health-network`<br>`solstice-health-network.qa.transmuter-dev.ishirock.tech`     | European Union | EUR / January           | 120,000,000 / 54,000,000        | Patient access, clinical capacity, and sustainable value |
| Horizon Energy & Utilities | `qa-e2e-20260712-horizon-energy-utilities`<br>`horizon-energy-utilities.qa.transmuter-dev.ishirock.tech`   | Australia      | AUD / July              | 300,000,000 / 135,000,000       | Reliable energy transition and asset productivity        |

Login conventions:

- Tenant admin: `admin@<login-domain>` with role `transformation_office`.
- Role probe: `rbac-<role-with-hyphens>@<login-domain>`.
- Seeded roles: `transformation_office`, `tenant_admin`, `pmo_lead`,
  `finance_lead`, `workstream_lead`, `initiative_owner`,
  `business_benefit_owner`, `executive_sponsor`, and `viewer`.
- All fixture identities use the exact controlled
  `*.qa.transmuter-dev.ishirock.tech` domain allowlist and the same
  runtime-provided fixture password. Store the dev-only password in the ignored
  `scratch/test-credentials.json` file with mode `0600`; never commit it or put
  it in a guide, manifest, issue, screenshot, or command output. The headed
  invite test may send only to these synthetic QA identities and must retrieve
  the link through the configured delivery provider without logging its token.

## Controlled Email Migration

Run this migration only when the five owned fixture tenants already exist with
the legacy `*.transmuter.test` emails. It changes the same 50 Auth subjects and
platform-user rows to the controlled login-safe domains above; it does not
create identities, change passwords, or change subject IDs or authorization
metadata. A new environment with no legacy fixture tenants skips this section.

Load the approved Hostinger credential without placing it in shell history, then
run the default dry-run from `apps/api`:

```bash
cd /Users/vramakrishnaiah/dev/transmuter
read -rs 'HOSTINGER_API_KEY?Dev Hostinger API token: '
export HOSTINGER_API_KEY
printf '\n'

cd apps/api
uv run python scripts/migrate_five_tenant_fixture_email_domains.py \
  --environment dev \
  --hostinger-project transmuter-dev-hostinger \
  --confirm migrate-five-tenant-fixture-emails-dev
```

For an unmigrated legacy fixture, the exact result is:

```text
Fixture email migration dry-run passed: 50 pending, 0 complete
```

If the dry-run instead reports `0 pending, 50 complete`, the migration is already
complete; do not apply it again. Stop on every other count. After quiescing dev
authentication, provisioning, invitation, and integration activity, apply the
reviewed plan with a redacted local journal:

```bash
uv run python scripts/migrate_five_tenant_fixture_email_domains.py \
  --environment dev \
  --hostinger-project transmuter-dev-hostinger \
  --confirm migrate-five-tenant-fixture-emails-dev \
  --apply \
  --journal ../../scratch/five-tenant-fixture-email-migration.redacted.json
```

The exact apply result is:

```text
Fixture email migration completed for 5 tenants and 50 identities
```

Run the same dry-run command again as the postflight:

```bash
uv run python scripts/migrate_five_tenant_fixture_email_domains.py \
  --environment dev \
  --hostinger-project transmuter-dev-hostinger \
  --confirm migrate-five-tenant-fixture-emails-dev
```

The exact postflight result is:

```text
Fixture email migration dry-run passed: 0 pending, 50 complete
```

Verify the redacted journal without printing its contents:

```bash
jq -e \
  '.environment == "dev" and .status == "complete" and (.completed | length) == 50' \
  ../../scratch/five-tenant-fixture-email-migration.redacted.json >/dev/null
```

Dev and production share one Supabase Auth directory. The email change is
therefore globally visible at the Auth layer even though these subjects are
owned, development-scoped fixtures. Do not run the migration against a real
person, production tenant, production schema, a target email already in use, or
any fixture with invites, integrations, OAuth state, unexpected users, or a
non-dev authorization scope. The reviewed script must preserve every unrelated
shared-Auth identity and will attempt a full rollback on failure; a
`rollback_failed` journal is a release stop requiring Prahari review. Never copy
the journal to production or treat it as authorization to promote.

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

| Surface                  | Required checks                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authentication           | `POST /api/auth/login` and `GET /api/auth/me` return the expected subject, tenant, and role. Invalid and anonymous requests fail with 401. Dev identities have only the `transmuter_authorization_transmuter_dev` authorization scope.                                                                                                                                                                                                                                                                                                   |
| Portfolio                | Initiative list/detail returns exactly the tenant's ten codes and sector-specific names. Dashboard, matrix, roadmap, risk, KPI, milestone, status, governance, dependency, and search results contain no other tenant's IDs or labels.                                                                                                                                                                                                                                                                                                   |
| Financials               | Portfolio financials, value bridge, value ramp, benefits register, initiative portfolio, investments/payback, contributor, board-pack, initiative grid, cost lines, forecasts, assumptions, benefit ledger, bankable plan/history, and target lock endpoints return coherent tenant currency and fiscal reporting periods. Every seeded financial grid reports `locked=true`; no API mutation is attempted against the lock. Decimal money is represented as JSON strings. April and July starts must shift monthly, quarterly, and annual periods consistently. |
| Governance               | Gate 1-4 history is approved for every initiative; criteria snapshots are present; `ENT-005` has the approved rebaseline submission and two bankable plan versions.                                                                                                                                                                                                                                                                                                                                                                      |
| Delivery controls        | Every initiative has three milestones, checklist coverage, two KPIs with quarterly entries, two risks, one submitted plus one draft status update, and expected cross-initiative dependency coverage.                                                                                                                                                                                                                                                                                                                                    |
| Shared costs and reports | Four pools reconcile plan/actual allocations to their pool totals; preview/approved/locked state is explainable; Control Tower direct, allocated, burdened, and net values reconcile.                                                                                                                                                                                                                                                                                                                                                    |
| Admin and people         | Setup is complete, configuration is tenant-specific, ten users are present, workstream/team assignments are correct, and audit output contains only tenant events. Integration connections, OAuth state, and pending invites remain zero.                                                                                                                                                                                                                                                                                                |
| Final canonical state    | Meeting, meeting-session, agenda, action-item, and invite counts return to zero after the accepted browser workflows and guarded cleanup.                                                                                                                                                                                                                                                                                                                                                                                               |

April and July fiscal starts are mandatory edge cases. Northstar and Horizon
use July starts; Meridian uses April. The reporting year uses the fiscal
ending-year convention, so monthly, quarterly, yearly, contributor, shared-cost,
and dashboard periods must all shift from the same tenant configuration. This
behavior passed the final API and headed-browser run under
[#401](https://github.com/venkateshbr/transmuter/issues/401).

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

| Route                                                      | Required UI checks                                                                                                                                                                                                                                                                                                                                                                                            |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/`, `/auth/login`, `/profile`                             | Public shell and login render; valid/invalid login and logout work; tenant/name/role are correct; profile/theme changes persist or are restored.                                                                                                                                                                                                                                                              |
| `/dashboard`                                               | Summary, pipeline, RAG, pressure, risk heatmap, value matrix, KPI pulse, decision/action areas, recent activity, all BU/workstream/priority/tag filters, cell drilldown, reset, and executive PDF/XLSX export reconcile to the selected tenant.                                                                                                                                                               |
| `/initiatives/pipeline`                                    | Ten initiatives, stage/RAG/value labels, search/filter/sort, pagination, detail navigation, and archive state. Open/cancel create on all tenants; complete one temporary create/governance flow and reset afterward.                                                                                                                                                                                          |
| `/initiatives/matrix`                                      | Workstream-by-tag cells, totals, empty cells, filters, and contributor drilldowns reconcile to pipeline and dashboard values.                                                                                                                                                                                                                                                                                 |
| `/initiatives/new`                                         | Guided fields, required validation, financial setup readiness, AI-assisted intake graceful degradation, create/cancel, permissions, and navigation. Create only a temporary test initiative and remove it with the final reseed.                                                                                                                                                                              |
| `/initiatives/:id`, `/initiatives/:id/edit`                | Summary, team, milestones/checklists, dependencies, KPIs, risks, status, governance, financials, benefit evidence, ownership, save/cancel, validation, and permissions. Verify every seeded financial grid reports locked and its edit affordances are disabled; use only a temporary unlocked initiative for financial mutation tests. Test one controlled CRUD cycle for each other non-meeting child type. |
| `/initiatives/:id/financial-scope`                         | Active metrics, formula rows, scenarios, cost categories, baseline, save/reload, and role restrictions. Formula rows remain read-only while calculated values update.                                                                                                                                                                                                                                         |
| `/financials`                                              | Monthly/quarterly/yearly, fiscal reporting year, plan as-of, stage/category, benefit/actual toggles, baselines, summary, trend, in-year value, run-rate, plan-vs-actual, cost/metric breakdown, contributor drawer, value bridge, and board-pack export reconcile under the tenant fiscal-calendar contract.                                                                                               |
| `/financials/initiative-portfolio`                         | Ten rows, tenant currency, baselines, metric columns, one-time/recurring cost, net run-rate, completeness flags, sort/filter, and detail navigation reconcile.                                                                                                                                                                                                                                                |
| `/financials/benefits-register`                            | Thirty lines, metric/class, validation statuses and history, evidence, plan/actual, risk adjustment, filter/sort, submit/validate/reject/handoff permissions, and totals reconcile.                                                                                                                                                                                                                           |
| `/financials/benefit-tracking`                             | Portfolio/workstream/initiative scopes, locked baseline, actual realization, variance, reporting-period filters, evidence/notes, and 240 ledger rows reconcile to bankable plans and actuals.                                                                                                                                                                                                                 |
| `/financials/bankable-plan`                                | Ten initiatives, eleven versions, Gate 2 locks, locked snapshot detail, history, `ENT-005` version 2 and 8% FY2028 GM rebaseline, audit reason, and permission boundaries.                                                                                                                                                                                                                                    |
| `/financials/investments-payback`                          | Investment, benefit, payback, break-even, filter/sort, negative/zero state, and initiative drilldown reconcile to cost and benefit data.                                                                                                                                                                                                                                                                      |
| `/financials/waterline`                                    | Five workstream locks, cutoff/reporting-year filters, approved initiatives, committed versus actual value, variance, preview, and locked state reconcile.                                                                                                                                                                                                                                                     |
| `/shared-costs`                                            | Four pools, periods, category/scenario, policies, targets, weights, all seeded allocation methods, preview reconciliation, approve/lock/void permissions, audit trail, and reporting treatment. Use a temporary pool for mutation tests and reset it.                                                                                                                                                         |
| `/reports/control-tower`                                   | Portfolio filters, dependency/governance attention, direct benefits/costs, allocated costs, burdened costs, net after allocation, owner/investor views where linked, exports, and dashboard reconciliation.                                                                                                                                                                                                   |
| `/progress`, `/progress/roadmap`, `/progress/dependencies` | Thirty milestones, checklist state, overdue/in-progress/completed chronology, pressure, dependency lines, filters, zoom/date behavior, detail navigation, CRUD permissions, and the dependencies-to-roadmap redirect.                                                                                                                                                                                         |
| `/progress/status-updates`                                 | Ten submitted and ten draft updates, compliance/recency, RAG narrative, draft/generate/edit/submit workflow, filters, nudges where permitted, and scenario chronology. Agent failure must degrade gracefully.                                                                                                                                                                                                 |
| `/progress/action-items`                                   | Valid zero-count empty state only. Do not create, edit, complete, cancel, or delete action items.                                                                                                                                                                                                                                                                                                             |
| `/pmo/governance`                                          | Portfolio gate history, criteria snapshots, approved decisions, stage state, filters, submission/decision permissions, and bankable-plan linkage. Use a temporary initiative for a write flow, then reset.                                                                                                                                                                                                    |
| `/pmo/risks`                                               | Twenty risks, matrix/heatmap, owner/mitigation, severity and status filters, initiative link, CRUD, and role restrictions.                                                                                                                                                                                                                                                                                    |
| `/pmo/kpis`                                                | Twenty KPIs and 240 quarterly entries, targets/actuals/trends, configured fiscal-start display versus current calendar-period behavior, filters, initiative link, CRUD, and role restrictions.                                                                                                                                                                                                                |
| `/pmo/ai-insights`                                         | Read/suggestion experience, loading/failure/disabled states, traceable responses, and graceful degradation. Any agent-proposed database write requires an explicit HITL confirmation.                                                                                                                                                                                                                         |
| `/people`                                                  | Ten users, role/title/status/workstream/team assignments, filters/detail, admin affordances, and role denial. Test one synthetic invite through the UI, revoke it in the same flow, and confirm no invite or Auth identity remains.                                                                                                                                                                           |
| `/admin`                                                   | Setup `8/8`, organization settings, business units, workstreams, markets/themes/tags, reporting currency/fiscal start, metrics/formulas, baselines, scenarios, cost categories, value bridge, attributes, stage gates/criteria, dashboard configuration, audit log, billing status, and non-destructive cleanup preview. Restore changes or reseed.                                                           |
| `/platform`                                                | Tenant users are denied. With the existing dev platform-admin only, verify all five tenants are listed and do not invoke tenant deletion.                                                                                                                                                                                                                                                                     |

Imports and exports must include a portfolio/initiative export, initiative import
preview, one initiative workbook roundtrip, financial XLSX roundtrip, board-pack
XLSX, and executive summary PDF. Verify file type, non-empty content, tenant
branding/currency, row counts, formulas/values, and no cross-tenant data.

## Rerun And Reset

The full seed is repeatable but intentionally destructive inside its owned
fixture tenants:

- Before any write, all five profiles are checked for exact fixture ownership,
  approved dev QA email domains, Auth/platform subject parity, dev-scoped roles, and
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

| Evidence                                      | Result                                                                                       |
| --------------------------------------------- | -------------------------------------------------------------------------------------------- |
| Application commit / PR                       | `1f3330b` / draft [#416](https://github.com/venkateshbr/transmuter/pull/416)                  |
| Hostinger dev action / completion time        | `104300670`, success at `2026-07-15T08:55:20Z`                                               |
| API and web health                            | Pass at `https://transmuter-dev.ishirock.tech`                                               |
| Email migration dry-run / apply / postflight  | `50/0` pending/complete, apply success, then `0/50`                                          |
| Redacted migration journal validation         | Pass, `complete` with 50 identities                                                          |
| Initial seed manifest / count summary         | Pass, five tenants and ten initiatives each                                                  |
| Repeat-seed logical diff                      | Byte-identical SHA-256 `3ef52dd7015ee7c8953ccf7893e8d62b03a8fe9fa6588e3ab95707098cf58a50`    |
| 50-user guarded API verifier                  | Pass, 2,635 mutable-run requests; 2,450 final post-reset read-only requests                  |
| 50-user role/RBAC results                     | Pass across the admin plus nine operating-model identities per tenant                        |
| Cross-tenant isolation matrix                 | Pass, 55 foreign-initiative/user denials in each full run                                    |
| Browser target / desktop and mobile viewports | One external headed Chrome process: five tenants at 1440x1000, plus 390x844 responsive checks |
| Light/dark and accessibility checks           | Pass: dark theme, login names/autocomplete/error alert/focus, keyboard-resolvable controls   |
| Console/network error log                     | Zero page errors and zero unexplained 5xx; two intentional 503 recovery probes passed         |
| Export/import artifacts and reconciliation    | API export signatures and financial reconciliation pass; UI import/export roundtrips pending |
| Invite/password lifecycle                     | Pass through delivered Resend setup link, forced temporary-password change, and restoration   |
| Acme meeting / Admin cleanup                  | Pass: Saturday session plus two-series browser deletion; no meeting residue                   |
| Final canonical reseed / read verification    | Pass; SHA-256 `3ef52dd7015ee7c8953ccf7893e8d62b03a8fe9fa6588e3ab95707098cf58a50`; 2,450 requests / 55 denials |

### Per-tenant result

| Tenant                     | Seed | API/data | RBAC | Isolation | Browser routes | Currency / fiscal start | Result |
| -------------------------- | ---- | -------- | ---- | --------- | -------------- | ----------------------- | ------ |
| Acme Global Manufacturing  | Pass | Pass     | Pass | Pass      | 29/29          | USD / January           | Pass   |
| Northstar Retail Group     | Pass | Pass     | Pass | Pass      | 29/29          | SGD / July              | Pass   |
| Meridian Commercial Bank   | Pass | Pass     | Pass | Pass      | 29/29          | GBP / April             | Pass   |
| Solstice Health Network    | Pass | Pass     | Pass | Pass      | 29/29          | EUR / January           | Pass   |
| Horizon Energy & Utilities | Pass | Pass     | Pass | Pass      | 29/29          | AUD / July              | Pass   |

### 2026-07-15 final headed-browser addendum

The final uninterrupted Playwright CLI run used one externally launched headed
Google Chrome process, one worker, isolated browser contexts, real seeded users,
the public Angular application, and the public dev API. All five Transformation
Office identities loaded 29 tenant routes, ten initiatives, their configured
currency, and January/April/July fiscal starts. Desktop, mobile, light/dark,
pipeline controls, workstream-by-tag matrix, bankable-plan navigation, dashboard
and financial failure/retry states, and viewer RBAC passed. No page error or
unexplained server error occurred.

Acme browser acceptance created a weekly Saturday series, linked `ENT-005`,
added an initiative agenda item, opened the Saturday session, generated the
agenda, autosaved notes, attached a high-priority decision to the active agenda,
generated and edited AI minutes, observed the explicit draft-save confirmation,
reloaded the draft, completed the session, and confirmed `COMPLETED`. It then
created a second series and selected both series in Admin Data Cleanup; the
single confirmed operation reported two deleted series and removed all dependent
meeting data.

People acceptance sent a real password-setup email through Resend to an existing
synthetic Acme fixture identity, followed the delivered dev-host invite URL,
activated the account, assigned a distinct temporary password in People, proved
the first login was forced to `/auth/change-password`, and restored the shared
fixture password. A separate synthetic pending invite was created, listed,
resent, and revoked. Seven accepted/revoked acceptance-only invite rows were
guard-checked and removed before the final reseed. The deterministic post-reset
manifest retained SHA-256 `3ef52dd…`, and the 2,450-request read-only verifier
confirmed 50 users, zero invites/meetings/actions, and 55 isolation denials.

Microsoft Teams correctly remained disconnected in dev. Live Microsoft Graph
consent, event/join-link refresh, and transcript acceptance remain external
release gates under #220/#389/#390. Production was not touched.

### Finding log

Create a GitHub issue for each reproducible product defect and link it here. Use
P0 for security/data loss or a release stop, P1 for a broken critical workflow,
P2 for a material workaround or incorrect report, and P3 for minor usability or
cosmetic defects.

| ID / issue                                                   | Severity | Tenant / role                                 | Route                                           | Steps and evidence                                                                                 | Expected                                                                    | Actual                                                                                                         | Fix / retest                                                                          | Status |
| ------------------------------------------------------------ | -------- | --------------------------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ------ |
| [#401](https://github.com/venkateshbr/transmuter/issues/401) | P1       | Northstar, Meridian, Horizon / finance roles  | `/financials`, financial dashboards and reports | Compare configured July/April fiscal starts with reporting-year periods and totals.                | Periods and annual totals follow the configured tenant fiscal calendar.     | Fiscal ending-year mapping now drives monthly, quarterly, yearly, contributor, and shared-cost periods.         | Unit/API matrix plus 29-route browser pass on `1f3330b`.                                 | Dev pass |
| [#403](https://github.com/venkateshbr/transmuter/issues/403) | P2       | Acme / transformation office                  | `/portfolio/financials/contributors`            | Request monthly contributors with noncanonical `period=2028-01`; canonical `2028-M01` returns 200. | Reject invalid input with 422 or explicitly support the alternate format.   | Invalid contributor periods now return bounded HTTP 422; canonical fiscal periods return 200.                  | Focused route regression and full API matrix passed.                                  | Dev pass |
| [#404](https://github.com/venkateshbr/transmuter/issues/404) | P1       | All tenants / admin-capable roles             | `/admin`                                        | Inspect the Admin initial-load request set.                                                        | General Admin load makes no meeting-related request.                        | General/Admin route load makes no meeting-cleanup request; Data Cleanup loads candidates on demand.             | Five-tenant route sweep and Acme Data Cleanup pass on `1f3330b`.                       | Dev pass |
| [#405](https://github.com/venkateshbr/transmuter/issues/405) | P1       | Northstar, Meridian, Solstice, Horizon        | Financial dashboards, grids, and shared costs   | Compare configured SGD/GBP/EUR/AUD currencies with frontend formatters/defaults.                   | All financial UI uses tenant reporting currency.                            | Currency context now propagates through API responses, financial UI, and shared-cost defaults.                 | USD/SGD/GBP/EUR/AUD browser and API checks passed.                                    | Dev pass |
| [#406](https://github.com/venkateshbr/transmuter/issues/406) | P1       | Read-only/scoped roles                        | Initiative tabs and `/admin`                    | Inspect capability gating for viewer/executive/benefit/finance/PMO/setup roles.                    | Unauthorized controls and requests are hidden or denied before dispatch.    | Exact backend capabilities now gate frontend controls and lazy Admin tabs.                                      | Viewer KPI mutation hidden, Admin denied, focused permission tests and Prahari review passed. | Dev pass |
| [#407](https://github.com/venkateshbr/transmuter/issues/407) | P2       | All tenants / finance roles                   | Benefit Tracking bankable-plan link             | Follow the rendered target against Angular routes.                                                 | Link opens the selected initiative plan.                                    | Link now targets `/financials/bankable-plan?initiative_id=<id>` and preserves selection.                        | Headed click/navigation check passed.                                                 | Dev pass |
| [#408](https://github.com/venkateshbr/transmuter/issues/408) | P1       | All tenants / PMO roles                       | `/pmo/risks`, `/pmo/kpis`                       | Inspect primary create, drilldown, search, and filter controls.                                    | Visible controls execute supported, role-gated workflows.                   | Controls now navigate to initiative create/detail state; risk/KPI portfolio filters execute.                   | Dedicated headed navigation/filter/drilldown pass on `1f3330b`.                       | Dev pass |
| [#409](https://github.com/venkateshbr/transmuter/issues/409) | P2       | All tenants / portfolio roles                 | `/initiatives/matrix`                           | Compare the matrix with the workstream-by-tag reconciliation contract.                              | Matrix totals and contributor drilldowns reconcile with pipeline/dashboard. | Workstream-by-tag cells, totals, ranges, and contributor drawer now use the real portfolio matrix API.          | Five-tenant render plus headed contributor drilldown passed.                          | Dev pass |
| [#410](https://github.com/venkateshbr/transmuter/issues/410) | P1       | All tenants / executive and finance roles     | `/dashboard`, `/financials`                     | Induce 503 responses on primary dashboard and portfolio-financial requests.                         | Failures render explicit bounded error/retry state.                         | Explicit error panels and retry actions now distinguish failed requests from valid zero data.                  | Two intentional 503/recovery browser probes passed.                                   | Dev pass |
| [#414](https://github.com/venkateshbr/transmuter/issues/414) | P1       | Acme / Transformation Office                  | Meeting generated minutes                       | Add a decision while an initiative agenda item is active, then generate minutes.                     | Captured item appears under that agenda discussion and the global summary.   | Explicit session-agenda artifact reference and tenant/session validation retain the decision context.           | Fresh Saturday headed-browser pass on `1f3330b`.                                     | Dev pass |
| [#417](https://github.com/venkateshbr/transmuter/issues/417) | P1       | Acme / Transformation Office                  | Meeting agenda suggestions and minutes          | Generate agenda/minutes containing ISO dates and a date-bearing meeting title.                      | Dates remain intact while phone numbers and email addresses are masked.      | Agenda/minutes preserve the tested ISO dates while the masking boundary remains active.                          | Fresh Saturday headed-browser pass on `1f3330b`.                                     | Dev pass |
| [#216](https://github.com/venkateshbr/transmuter/issues/216) | P1       | Acme / tenant admin and initiative owner      | `/people`, invite email, auth setup/change       | Send setup link, activate, assign temporary password, force change, restore; create/resend/revoke.   | Tokens are app-owned, single-use, tenant-scoped, expirable, and never localhost. | Real delivered-email link and browser password lifecycle passed; fixture password restored.                  | Prahari security tests plus final zero-invite verifier passed.                        | Dev pass |
| [#224](https://github.com/venkateshbr/transmuter/issues/224) | P1       | Acme / tenant admin                            | `/admin`, Data Cleanup                          | Select a completed dependent meeting and a second series, confirm one bulk deletion.                 | Both series and tenant-scoped dependants are removed in one action.          | Browser reported two deleted series; final canonical verifier found zero meeting/session/agenda/action rows.     | Real API coverage and deployed headed-browser pass.                                   | Dev pass |
| [#411](https://github.com/venkateshbr/transmuter/issues/411) | P2       | Large portfolios / transformation office      | `/initiatives/pipeline`                         | Inspect server sort, page, archive inclusion, and restore contracts.                                | Users can sort, page, and include/exclude archived initiatives.             | Server-backed controls and restore behavior are implemented; the five-tenant fixture remains ten rows each.     | Service/repository regressions and browser control pass; >200 real-row performance remains follow-up scope. | Accepted follow-up |
| [#412](https://github.com/venkateshbr/transmuter/issues/412) | P3       | Public login / keyboard and screen-reader use | `/auth/login`                                   | Resolve labels, autocomplete, invalid error, and focus behavior through the accessibility tree.     | Labels and validation errors programmatically name their inputs.            | Associated labels, autocomplete hints, alert semantics, and invalid-login focus are implemented.               | Headed accessibility assertions passed.                                               | Dev pass |

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
