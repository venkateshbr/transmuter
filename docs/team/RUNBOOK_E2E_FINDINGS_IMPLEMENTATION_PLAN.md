# Runbook E2E Findings Implementation Plan

Date: 2026-06-25

Source findings:
- `tests/runbook-e2e-findings.md`
- `tests/TRANSMUTER_E2E_TEST_RUNBOOK.md`

Scope:
- Findings F14, F16, F15, F18, F17, F19, F13, and F7-R from the second runbook
  E2E assessment pass.
- Planning only. Runtime implementation must follow `docs/team/SDLC_PROTOCOL.md`
  with GitHub Issues and role handoff before code changes.

## Executive Assessment

F14 is the release-blocking issue because it prevents every non-USD and
non-January fiscal-year scenario from being represented through the UI. The
financial engine itself reconciled in the runbook, but the settings persistence
path silently no-ops and then tells the user the save succeeded.

The remaining findings are mostly workflow completeness and data-entry
ergonomics:
- F7-R can silently lose admin master-data rows during rapid entry and should be
  treated as a data-loss UX bug.
- F18 and F19 reduce dashboard fidelity because user-entered health signals do
  not reliably affect portfolio health or pressure.
- F17, F13, and F20 are finance workflow auditability, usability, and state
  integrity issues.
- F16 is a product feature gap for admin-configurable inflation modelling, not a
  reconciliation bug. The default should avoid double-counting by leaving
  recurring cost inflation as manual entry unless the tenant enables platform
  calculation.
- F15 is primarily a runbook/platform contract mismatch. The current platform
  requirement that realization ledger rows require a locked baseline is coherent.

## Findings Matrix

| ID | Severity | Implementation Decision | Primary Impact | Code Areas |
|---|---:|---|---|---|
| F14 | High | Fix immediately | Currency/FY matrix blocked; UI returns success for a no-op | `apps/api/app/routers/financials.py`, `apps/api/app/repositories/financial.py`, `apps/api/app/services/financial.py`, `apps/web/src/app/features/admin/admin.component.ts`, `organizations` RLS/migrations |
| F7-R | Medium | Fix in same remediation train | Rapid add can drop business units/workstreams/tags with no feedback | `apps/web/src/app/features/admin/admin.component.ts`, admin settings/business-unit/workstream routes |
| F18 | Medium | Fix after F14/F7-R | Status heartbeat RAG does not update headline initiative RAG used by dashboards | `apps/api/app/services/status_update.py`, `apps/api/app/repositories/status_update.py`, `apps/api/app/services/initiative.py`, `apps/web/src/app/features/initiatives/detail/status-updates/status-updates-tab.component.ts` |
| F19 | Low-Med | Fix after F18 or with it | Past due milestones do not affect initiative milestone pressure unless explicitly marked overdue | `apps/api/app/repositories/initiative.py`, `apps/api/app/services/initiative.py`, `apps/api/app/services/milestone.py`, milestone UI |
| F17 | Low-Med | Fix with finance UX batch | Rejected benefit may have no required business reason | `apps/api/app/services/financial.py`, `apps/api/app/domain/financials.py`, `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts` |
| F13 | Medium | Fix with finance UX batch | Natural Plan High entry path creates duplicate benefit lines | `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts`, financial grid update APIs |
| F20 | Medium | Fix with finance validation batch | State-inappropriate Submit/Validate/Reject/Delete actions can mutate or remove already validated lines | `apps/api/app/services/financial.py`, `apps/api/app/repositories/financial.py`, `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts` |
| F16 | Medium | Admin-configurable policy, then implement | Recurring cost inflation can be enabled per tenant and applied only where desired | `organizations.settings`, `financial_cost_lines` schema, `CostLineCreate/Update`, financial service rollups, Admin financial settings, financials UI |
| F15 | Medium | Update runbook unless product decides otherwise | Scenario 2 asks for realized ledger without lock; platform requires lock | `tests/TRANSMUTER_E2E_TEST_RUNBOOK.md`, scenario validation text |

## Recommended GitHub Issue Structure

Reuse open issue `#354` only if it is still intended to cover this new runbook
remediation pass. Otherwise create a new parent:

- `[Bug] Remediate second runbook E2E findings`
  - Labels: `type:bug`, `priority:high`, `agent:vishwa`, `status:assigned`

Recommended sub-issues:
- `[Karya/Prahari] Persist tenant reporting currency and fiscal year`
- `[Rupa/Karya] Harden admin add forms and finance line feedback`
- `[Karya/Rupa] Propagate or expose initiative headline RAG status`
- `[Karya/Rupa] Derive milestone overdue pressure from due dates`
- `[Karya/Rupa] Require audited benefit rejection reasons and validation state guards`
- `[Netra/Vastu/Karya/Rupa] Add configurable recurring cost inflation modelling`
- `[Netra/Aksha] Align runbook realized-ledger scenario with locked-baseline rule`

Prahari is required for F14 if implementation touches `organizations` RLS or
uses the service-role client for tenant settings writes.

## Phase 1 - F14 Reporting Settings Persistence

### Impact

The API route `PUT /admin/financial-engine/reporting-settings` accepts
`fiscal_year_start_month` and `reporting_currency`. In the observed E2E run, it
returned `200 OK` and echoed the requested values, but a subsequent
`GET /financial-engine-configuration` returned the old values.

Code inspection shows the repository writes to `organizations`:

- `FinancialRepository.get_reporting_settings()`
- `FinancialRepository.update_reporting_settings()`

`update_reporting_settings()` currently returns the request payload when Supabase
returns no rows. That masks failed writes:

```text
result.data[0] if result.data else payload
```

The base migrations define only an `organizations` SELECT RLS policy. Admin
routes use a service-role client, but this financial route currently uses the
request client. That makes a silent no-op plausible under RLS.

### Implementation Plan

1. Confirm the runtime failure with a focused real API test:
   - Login as a seeded transformation-office user.
   - GET `/financial-engine-configuration`.
   - PUT `/admin/financial-engine/reporting-settings` with `GBP` and month `4`.
   - GET again and assert settings persist.

2. Choose the persistence strategy:
   - Preferred: route admin financial-engine mutations through `_admin_svc`
     using `get_supabase_admin()`, while retaining explicit role checks in the
     router and tenant scoping in the service.
   - Alternative: add an RLS UPDATE policy for `organizations` restricted to the
     current tenant and transformation-office role. This is broader and needs
     more Prahari scrutiny because RLS cannot easily constrain updates to only
     reporting columns.

3. Make the repository fail closed:
   - After update, reselect `fiscal_year_start_month,reporting_currency`.
   - If no row is returned, raise an API error instead of echoing the payload.
   - Validate currency codes as uppercase 3-letter ISO-like codes.
   - Preserve Decimal discipline for downstream financial calculations; this
     change itself does not add money arithmetic.

4. Update the Admin UI:
   - Add `reportingSettingsSaving`, success, and error state.
   - Disable Save while pending.
   - On success, show explicit confirmation with the persisted values.
   - On failure, keep the user-entered values visible and show the API error.

5. Audit all consumers:
   - Financials portfolio pages should read the settings from
     `/financial-engine-configuration`.
   - Shared-cost reporting settings are separate and should not be conflated.
   - Check currency symbols and fiscal-year labels wherever annual/monthly
     columns are rendered.

### Acceptance Criteria

- Real API test proves PUT then GET persists `GBP/April`, `EUR/January`,
  `AUD/July`, `SGD/January`, and `BRL/January` for isolated seeded tenants.
- Browser UI test saves GBP/April in Admin, reloads the page, and sees GBP/April
  still selected.
- Scenario 2 validates Apr-Mar fiscal labels and GBP formatting.
- Scenarios 1, 3, 5, and 6 can be configured to their requested currencies.
- Failed persistence cannot return a success toast or echoed fake response.
- Prahari review is complete if RLS or service-role write routing changes.

## Phase 2 - F7-R Admin Add-Form Reliability

### Impact

Rapid sequential adds in Admin -> Strategic Parameters silently dropped business
units in the browser run. The UI currently posts workstream/business-unit rows
without a per-form saving state or success/error feedback. Some strategic
parameters are array-based and saved through `/admin/settings`, which can race
if rapid clicks issue overlapping writes from stale local state.

### Implementation Plan

1. Add per-form pending state:
   - `businessUnitSaving`
   - `workstreamSaving`
   - `marketSaving`
   - `themeSaving`
   - `tagSaving`

2. Disable the relevant add button and input while its request is in flight.

3. Show deterministic feedback:
   - Success message: item added.
   - Error message: server reason, with input preserved.
   - Do not clear input until persistence succeeds.

4. For array-backed settings, serialize writes:
   - Use a queue or single `saveStrategicParameterConfig` pending promise.
   - Merge changes against the latest local signal before sending.
   - Reload settings after save and reconcile the visible list.

5. Consider backend idempotency:
   - Add tenant-level uniqueness constraints for business-unit name/code and
     workstream name only if product accepts duplicate prevention.
   - Otherwise keep duplicates allowed but ensure no request is dropped silently.

### Acceptance Criteria

- Browser E2E rapidly adds five business units and five workstreams; all persist.
- Buttons show pending state and prevent double-submit while a request is active.
- API failure leaves the form data intact and shows a visible error.
- Existing one-at-a-time add behavior remains unchanged.

## Phase 3 - F18 Headline RAG Status

### Impact

Dashboards, pipeline, matrix, executive control, shared-cost dimensions, and AI
context all read `initiatives.rag_status`. Status Heartbeat stores RAG on
`status_updates.rag_status`, but submitting a heartbeat does not update the
initiative headline RAG. The initiative Overview edit modal already has a RAG
Status control, so the issue is not strictly absence of an edit path. It is that
the status workflow does not drive the portfolio signal the runbook expects.

### Product Decision

Choose exactly one canonical rule:

1. Latest submitted Status Heartbeat controls headline RAG.
2. Headline RAG is manually controlled on the initiative Overview, and the
   heartbeat RAG remains a historical status-report attribute.
3. Headline RAG is derived from pressure/risk/KPI rules, with manual override.

Recommended for this product: option 1, with an explicit override later if
needed. It matches user expectation that a submitted health report updates the
portfolio health signal.

### Implementation Plan

1. Extend `StatusUpdateService.create_update`, `patch_update`, and
   `submit_update` so a newly submitted update writes
   `initiatives.rag_status = update.rag_status` for the same tenant and
   initiative.

2. Add repository method:
   - `StatusUpdateRepository.update_initiative_rag(initiative_id, rag_status)`.
   - Scope by `tenant_id` and `initiative_id`.

3. Preserve HITL:
   - AI draft generation remains read-only.
   - Only explicit save/submit updates the initiative.

4. Update UI copy minimally:
   - On Status Heartbeat submit, show confirmation that portfolio RAG was updated.
   - Avoid explanatory in-app instructional text beyond concise status feedback.

### Acceptance Criteria

- Real API test creates a submitted red status update and verifies
  `/initiatives/{id}` returns `rag_status=red`.
- Browser test submits a Red heartbeat and confirms dashboard/pipeline RAG turns
  red after reload.
- Draft generation does not update initiative RAG.
- Tenant isolation test confirms another tenant cannot affect the initiative.

## Phase 4 - F19 Milestone Pressure From Past-Due Dates

### Impact

Initiative pressure uses `milestones_overdue` from `InitiativeRepository.get_counts`.
That count only checks explicit `status == "overdue"`. Milestone pressure itself
has more nuanced date logic, and the roadmap UI can visually treat past due
dates as due, but the initiative-level pressure breakdown does not.

### Implementation Plan

1. Update initiative counts:
   - Select `status, planned_end`.
   - Count a milestone as overdue if:
     - `status == "overdue"`, or
     - `status != "complete"` and `planned_end < today`.

2. Keep explicit status support:
   - The detail tab already has a status selector.
   - Add status to the create modal only if product wants direct creation as
     overdue/in-progress. Otherwise derive overdue from date.

3. Recalculate milestone pressure after create/update:
   - Already happens in `MilestoneService`.
   - Add tests that prove initiative pressure updates after planned-end changes.

4. Align display:
   - Milestone filters should include derived-overdue milestones when filter is
     `overdue`, even if stored status is `not_started`.
   - Avoid mutating stored status automatically unless explicitly chosen.

### Acceptance Criteria

- Real API test creates a milestone with planned_end before today and status
  `not_started`; initiative detail returns non-zero milestone pressure.
- Browser UI shows the milestone as overdue/pressure-bearing after reload.
- Complete milestones with past dates do not count as overdue.

## Phase 5 - F17 and F20 Audited Benefit Validation Workflow

### Impact

The backend supports `rejection_reason`, and current UI code uses a browser
prompt for rejection. However, the prompt is not a robust enterprise workflow:
it is optional, hard to automate reliably, visually inconsistent, and allows
empty reasons to persist as null.

Additional observation from Scenario 7:

PIN-001 Accounting System Implementation shows two identically named benefit
lines in the Finance Validation section:

- one `Finance validated`;
- one `Submitted to Finance`.

Both rows show Submit, Validate, Reject, Risk, and Delete. Current code renders
all actions for every row and the backend transition method accepts all
transitions without checking the current validation status.

Button impact in current `main`:

- Submit:
  - Calls `POST /initiatives/{id}/financials/benefit-lines/{line_id}/submit`.
  - Sets `validation_status = submitted`.
  - Can downgrade an already `finance_validated` line to `submitted`.
  - Does not clear `validated_at` or `validated_by`, so status and audit fields
    can become inconsistent.
- Validate:
  - Calls `POST .../{line_id}/validate`.
  - Sets `validation_status = finance_validated`.
  - Can validate a draft or rejected line directly.
  - Clears `rejection_reason`.
- Reject:
  - Calls `POST .../{line_id}/reject`.
  - Sets `validation_status = rejected`.
  - Can reject an already finance-validated line.
  - Stores `rejection_reason = comment`, but the comment is currently optional.
- Risk:
  - Calls `PUT .../{line_id}/handoff`.
  - Updates `risk_rating`, `risk_adjustment_pct`, and handoff metadata.
  - Does not change validation status.
  - Can affect risk-adjusted benefit values in the Benefits Register.
- Delete:
  - Calls `DELETE /initiatives/{id}/financials/benefit-lines/{line_id}`.
  - Is disabled only when the initiative financials are locked.
  - Deletes the benefit line and cascades related metric values and validation
    events through existing foreign keys.
  - Can remove a submitted or finance-validated line if the initiative is not
    locked.

This is not correct enterprise finance-control behavior. It creates avoidable
data and audit risk even though the underlying line-state fields exist.

### Implementation Plan

1. Backend validation:
   - For reject action, require `comment` to be non-empty after trimming.
   - Return `422` or `400` with a clear message if missing.
   - Continue storing the comment in both `validation_comment` and
     `rejection_reason`, and record it in validation events.
   - Add explicit allowed transitions:
     - `draft -> submitted`
     - `submitted -> finance_validated`
     - `submitted -> rejected`
     - `rejected -> submitted` only if resubmission is explicitly allowed.
   - Block `finance_validated -> submitted`, `finance_validated -> rejected`,
     and delete of `submitted` or `finance_validated` lines unless a separate
     governed reversal/rebaseline flow is introduced.
   - When transitions are blocked, return `409 Conflict` with the current status
     and allowed next actions.
   - If downgrades remain product-approved, clear stale status-specific audit
     columns so `validation_status`, `submitted_at`, `validated_at`, and actor
     fields remain coherent.

2. UI replacement:
   - Replace `window.prompt` with a compact modal or inline action panel.
   - Reject action requires a reason textarea.
   - Validate action may keep optional finance comment.
   - Evidence URL/label should be optional fields in the same modal.
   - Render only valid actions for the current line status:
     - Draft: Submit, Risk, Delete.
     - Submitted: Validate, Reject, Risk.
     - Finance validated: Risk, View evidence/history. No Submit/Reject/Delete.
     - Rejected: Submit for resubmission, Risk, View reason/history.
   - If two rows have the same name, include scenario coverage, metric label,
     and plan/actual amounts in the row header so the user can distinguish them.

3. Audit and list display:
   - Benefits Register already displays `rejection_reason`; ensure rejected rows
     show the reason and validation event history includes it.
   - Add validation event history access from the initiative financials tab or
     link directly to the Benefits Register filtered for the line.

### Acceptance Criteria

- Real API rejects missing rejection comment.
- Browser test rejects a benefit with reason text and verifies Benefits Register
  displays the reason.
- Existing submit/validate flows still work.
- Real API returns `409` when attempting to submit or reject a
  `finance_validated` line.
- Browser UI hides invalid state actions for finance-validated and submitted
  lines.
- Delete is unavailable for submitted and finance-validated lines unless a
  governed reversal path exists.

## Phase 6 - F13 Scenario-Aware Benefit Line Entry

### Impact

The current add-line flow creates a benefit line and then generates values for
the currently selected scenario. A natural user path for Plan High can create a
second line with the same name rather than adding Plan High values to the
existing line. Totals reconcile, but the Benefits Register becomes cluttered and
per-line actions become ambiguous.

### Implementation Plan

1. Make scenario targeting explicit in the Add Benefit Line panel:
   - Include Plan Base, Plan High, and Actual amount fields in the same create
     form, or
   - Provide a "scenario" segmented control plus an "update existing line" mode.

2. Prefer a single-line multi-scenario create flow:
   - Create one `financial_benefit_lines` row.
   - Generate `financial_metric_values` rows for any provided Base/High/Actual
     fields against the same `benefit_line_id`.
   - Keep manual grid editing for advanced monthly phasing.

3. Improve row disambiguation:
   - Display scenario coverage on each benefit line.
   - Include metric, scenario values, and validation status in action labels.
   - Avoid duplicate unnamed/identically named lines unless the user explicitly
     chooses duplicate.

4. Optional backend guard:
   - Detect exact duplicate line names for the same initiative and metric and
     return a warning or merge suggestion. Do not hard-block duplicates unless
     product agrees.

### Acceptance Criteria

- Browser test creates one named benefit line with Base and High values.
- Portfolio Base and High totals reconcile.
- Benefits Register shows one line, not duplicate base-only/high-only rows.
- Validation buttons are unambiguous by row.

## Phase 7 - F16 Recurring Cost Inflation

### Impact

Current cost lines support one-off versus recurring separation, but there is no
inflation modifier. This is a feature gap against the runbook's Nordvik scenario,
not a current calculation regression.

Inflation must be configurable, not forced globally. Some tenants will want the
platform to calculate recurring-cost inflation from a base amount. Others will
prefer to calculate inflation outside the system and enter the already-inflated
cost values directly. Applying automatic inflation by default would create a
material double-counting risk.

### Product Design Decision

Define tenant-level inflation policy before coding:

- Admin should own a recurring-cost inflation policy under Financial Engine
  settings.
- Recommended default: `manual_entry`, meaning no automatic inflation. Users can
  enter already-inflated cost amounts directly.
- Recommended configurable modes:
  - `manual_entry`: no platform compounding; hide or disable inflation controls
    in cost-line creation.
  - `optional_per_line`: expose inflation controls for recurring cost lines, but
    default each line to no inflation unless the user opts in.
  - `default_on`: apply the tenant default rate to recurring cost lines unless a
    line overrides it to a different rate or zero.
- Recommended admin settings:
  - `recurring_cost_inflation_mode`.
  - `default_annual_inflation_rate_pct`.
  - `allow_cost_line_inflation_override`.
- Store the tenant policy in `organizations.settings.financial_engine` unless
  Vastu chooses a dedicated typed table for financial-engine settings.

When platform inflation is enabled for a line, use these calculation semantics:

- Recommended line fields: `inflation_enabled` and
  `annual_inflation_rate_pct`.
- Applies only to generated recurring plan cost rows.
- Base amount means first fiscal-year annual amount.
- Each subsequent fiscal year compounds by
  `base * (1 + inflation_rate_pct / 100) ^ year_offset`.
- Monthly rows split the inflated annual amount across the applicable months.
- Store all resulting row values as `NUMERIC(15,4)` and use Python
  `decimal.Decimal`.

### Implementation Plan

1. Schema:
   - Store tenant policy in `organizations.settings.financial_engine`:
     `recurring_cost_inflation_mode`,
     `default_annual_inflation_rate_pct`, and
     `allow_cost_line_inflation_override`.
   - Add `inflation_enabled BOOLEAN NOT NULL DEFAULT false` and
     `annual_inflation_rate_pct NUMERIC(7,4) NOT NULL DEFAULT 0` to
     `financial_cost_lines`, or store the generator metadata in an attributes
     JSON column if cost lines get a broader metadata refactor.
   - Add matching migration under both `supabase/` and `infra/supabase/` if that
     duplication remains the repo pattern.

2. API:
   - Extend `CostLineCreate`, `CostLineUpdate`, and `CostLineItem`.
   - Add financial-engine settings read/write support for the tenant inflation
     policy, likely alongside existing Admin financial configuration.
   - Validate percentage range, for example `0 <= pct <= 100`.
   - If tenant mode is `manual_entry`, ignore or reject automatic inflation
     inputs so accidental API callers cannot double-count.
   - If tenant mode is `optional_per_line`, require `inflation_enabled=true`
     before applying `annual_inflation_rate_pct`.
   - If tenant mode is `default_on`, apply the tenant default unless a permitted
     per-line override is supplied.
   - Ensure all calculations use Decimal.

3. Admin UI:
   - Add a Recurring Cost Inflation control to the Financial Engine / reporting
     settings area.
   - Controls:
     - mode selector: manual entry, optional per line, default on.
     - default annual inflation percentage.
     - allow per-line override toggle.
   - Default mode must be manual entry to prevent surprise inflation.

4. Financials UI:
   - Show inflation controls only when recurring is selected and tenant policy
     allows platform-calculated inflation.
   - In `manual_entry`, keep the UI focused on direct amount entry.
   - In `optional_per_line`, show an "Apply inflation" toggle and rate input.
   - In `default_on`, prefill the tenant default rate and allow override only
     when Admin permits it.
   - During cost-line generation, preview generated annual totals by year.
   - Keep one-off costs unaffected.

5. Rollups:
   - Existing rollups can continue summing persisted cost rows.
   - Inflation should be applied at generation time, not hidden inside every
     report calculation.

### Acceptance Criteria

- Real API in `manual_entry` mode generates recurring costs without automatic
  inflation even if the user manually enters varied annual amounts.
- Real API in `optional_per_line` mode generates recurring costs for multiple
  years with 3 percent annual compounding only when `inflation_enabled=true`.
- Real API in `default_on` mode applies the tenant default rate unless an
  allowed per-line override sets a different rate or zero.
- Browser Admin test changes inflation mode and default rate, reloads, and sees
  the persisted settings.
- Browser Financials test enters a recurring cost with 3 percent inflation and
  sees the expected FY totals.
- One-off costs remain unchanged.

## Phase 8 - F15 Runbook/Platform Contract

### Assessment

The platform behavior is coherent: realization ledger rows require a locked
bankable baseline. Scenario 2 says "no locks" but also expects a realized ledger
row. Scenario 5 already proves the ledger works once a lock exists.

### Implementation Plan

1. Update `tests/TRANSMUTER_E2E_TEST_RUNBOOK.md`:
   - Remove the realized-ledger assertion from Scenario 2, or
   - Add an explicit lock step for AUR-001 before ledger entry.

2. Preferred option:
   - Keep Scenario 2 as no-lock, multi-scenario, margin/revenue/fiscal-year
     coverage.
   - Move realized-ledger assertion to Scenario 5 and keep Scenario 5 as the
     locked-baseline realization proof.

3. Update `tests/runbook-e2e-findings.md` after implementation:
   - Mark F15 as runbook contract corrected, not platform bug.

### Acceptance Criteria

- Runbook no longer asks for unlocked realization ledger entry.
- Scenario 2 validates Base/High/Actual and fiscal-year/currency only.
- Scenario 5 remains the canonical locked realization-ledger scenario.

## Sequencing

1. F14 first.
   - It unblocks the test matrix and touches tenant settings/RLS-sensitive code.

2. F7-R second.
   - It removes silent setup-data loss during repeated scenario creation.

3. F18 and F19 together.
   - Both affect portfolio health and pressure signals.

4. F17 and F13 together.
   - Both improve finance line workflow and auditability.

5. F15 runbook correction can happen in parallel with any phase.

6. F16 only after Netra/Vastu confirm inflation policy and calculation
   semantics.
   - It is a feature addition with admin configuration, schema, UI, and
     calculation scope.

## Test Strategy

Developer checks are not sufficient for sign-off. Aksha acceptance must include:

- Real API tests against a running API and deterministic seeded tenants.
- Browser UI tests against the Angular app and real API.
- Predictable tenant setup and cleanup.

Minimum automated coverage by finding:

- F14:
  - API: PUT/GET persistence for multiple currencies and fiscal starts.
  - Browser: Admin Financial Configuration save and reload.
  - Browser: Scenario 2 Apr-Mar labels and GBP formatting.

- F7-R:
  - Browser: rapid add of business units/workstreams/tags, with all persisted.
  - API or browser: failed add shows error and preserves input.

- F18:
  - API: submitted status update changes initiative `rag_status`.
  - Browser: red status heartbeat updates pipeline/dashboard.

- F19:
  - API: past-due incomplete milestone drives non-zero milestone pressure.
  - Browser: milestone appears overdue/pressure-bearing without manual status
    mutation.

- F17:
  - API: reject without reason fails.
  - Browser: reject with reason persists and displays in Benefits Register.

- F13:
  - Browser: one benefit line can carry Base and High values without duplicate
    line creation.

- F16:
  - API and browser: Admin inflation policy persists and reloads.
  - API: `manual_entry` mode does not auto-inflate recurring costs.
  - API and browser: optional per-line inflation generates exact compounded cost
    rows only when enabled.
  - API: default-on policy applies tenant default and respects allowed per-line
    overrides.

- F15:
  - Documentation review and scenario rerun confirm no unlocked ledger assertion.

## Release And Deployment Notes

- F14, F16, and any RLS migration require dev deployment with explicit schema SQL
  if migrations are added.
- Update `docs/team/RELEASE_MANIFEST.md` before production promotion.
- Validate on `https://transmuter-dev.ishirock.tech` first.
- Production promotion should include:
  - `/health`
  - `/api/health`
  - Browser login
  - Touched workflows from this plan

## Open Questions

1. Should tenant reporting currency be mutable after tenant provisioning, or
   should signup collect currency and fiscal year once?
2. Should latest Status Heartbeat always set headline RAG, or should headline RAG
   be manually controlled with status updates as history only?
3. Should overdue be derived at read time only, or should a scheduled job
   materialize milestone status changes?
4. Should recurring cost inflation use the proposed three-mode Admin policy
   (`manual_entry`, `optional_per_line`, `default_on`) or a simpler enabled
   toggle plus default rate?
5. Should duplicate business-unit/workstream names be blocked per tenant?
