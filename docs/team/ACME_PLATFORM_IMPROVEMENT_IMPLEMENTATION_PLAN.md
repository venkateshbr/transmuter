# ACME Platform Improvement Implementation Plan

Status: Planning-only proposal for review
Source assessment: `docs/user-guides/acme-transformation-platform-improvement-opportunities.md`
Prepared: 2026-06-17

This plan turns the ACME improvement findings into a platform-wide implementation
roadmap. The target is not an ACME-only patch. The target is a durable
transformation-management upgrade that works for:

- existing tenants,
- newly provisioned tenants,
- existing initiatives,
- newly created initiatives,
- workbook-loaded initiatives,
- manually edited initiatives,
- dashboard, report, and export consumers.

No runtime implementation should begin until this plan is reviewed and approved.

---

## 1. Executive Summary

The current platform already has a strong configurable financial engine, dynamic
metric definitions, tenant baselines, initiative baselines, bankable plan
snapshots, a benefit realization ledger, portfolio financials, Bankable Plan,
Benefit Tracking, and Waterline screens.

The improvement work is therefore a platform-hardening program, not a rewrite.
The main issue is that several board-critical workflows are present but not yet
fully traceable end to end:

1. Gate criteria are configurable, but ACME is missing seeded criteria and the
   platform should make criteria completeness more visible.
2. Portfolio Financial Overview is correct at summary level, but contributor
   drilldown does not yet include clean configurable metric benefits.
3. Benefit Tracking exists, but ACME does not have seeded locked bankable plans
   and benefit ledger rows.
4. Bankable Plan exists, but ACME lacks version history and rebaseline examples.
5. Value Bridge needs explicit basis controls so users can distinguish in-year,
   target-year run-rate, cumulative, and all-years values.
6. Finance validation is not explicit at benefit-line level.
7. Benefits are embedded inside initiative financials, but there is no
   portfolio-wide Benefits Register.
8. Portfolio board-pack export is not a first-class workflow.

The recommended implementation path is four releases:

| Release | Theme | Outcome |
|---|---|---|
| R1 | Correctness and demo readiness | Dashboards reconcile, contributor drawer traces benefit drivers, ACME has gate criteria, locked plans, benefit ledger data, and a rebaseline example. |
| R2 | Governance and validation | Benefit-line Finance validation, evidence, approval state, audit trail, and locked-plan eligibility become first-class. |
| R3 | Benefits Register and board reporting | Portfolio Benefits Register and board-pack export give management a repeatable review artifact. |
| R4 | Advanced value basis and risk-adjusted reporting | Value Bridge basis controls, realization confidence, risk-adjusted value, and ownership handoff mature the product. |

---

## 2. Current-State Assessment

### 2.1 Existing Capabilities

The codebase already includes these core platform capabilities:

| Capability | Current implementation |
|---|---|
| Configurable financial engine | `financial_metric_definitions`, `financial_scenarios`, `financial_benefit_lines`, `financial_metric_values`, `financial_bridge_rows`. |
| Tenant annual baseline | `financial_tenant_annual_baselines`, surfaced in Financial Overview. |
| Initiative annual baseline | `financial_initiative_annual_baselines`, surfaced in initiative financial setup. |
| Bankable plans | `bankable_plans` table, lock/rebaseline service methods, Bankable Plan UI. |
| Benefit realization ledger | `benefit_realization_ledger` table, API endpoints, Benefit Tracking UI. |
| Waterline | Workstream target lock tables/services and Waterline UI. |
| Portfolio financials | `/portfolio/financials`, `/portfolio/financials/contributors`, `/portfolio/value-ramp`, `/portfolio/value-bridge`. |
| Governance | Stage gates, gate criteria, submissions, lock-on-approval integration. |
| ACME seed | 10 initiatives, tenant baseline, initiative baselines, configurable metrics, costs, and financial values. |

### 2.2 Current Gaps

| Gap | Type | Severity | Root cause |
|---|---|---:|---|
| ACME gate criteria missing | Seed/configuration | High | ACME seed does not populate criteria, so setup checklist remains 7/8. |
| Contributor drawer benefit gaps | Backend rollup | High | Clean configurable metric values are not included in contributor rollup the same way they are included in summary rollup. |
| ACME Benefit Tracking empty | Seed/configuration | High | ACME seed has plan/actual values but no locked bankable plans or ledger rows. |
| ACME Bankable Plan version history sparse | Seed/configuration | Medium-high | Seed does not simulate approvals, locks, and rebaseline. |
| Value Bridge basis unclear | API/UI semantics | Medium | Response and UI do not make period basis explicit enough. |
| Benefit-line Finance sign-off missing | Data model/API/UI | Medium-high | Benefit lines have confidence/status-like value fields, but no explicit validation state, validator, timestamp, evidence, or comments. |
| Benefits Register missing | Product surface | Medium | Benefit lines are initiative-local; portfolio-level management view is absent. |
| Board pack export missing | Product surface | Medium | Workbook export exists at initiative level, but no portfolio board pack generator exists. |

### 2.3 Design Principle

Financial reporting must have one rollup source of truth:

```text
Tenant configuration
  -> initiative benefit/cost lines
  -> monthly metric values and cost lines
  -> optional locked bankable plan snapshots
  -> optional benefit realization ledger actuals
  -> portfolio rollup service
  -> dashboard, register, report, export
```

Dashboards should not contain separate financial logic. They should consume
shared backend rollup APIs and display the same values as exports and reports.

---

## 3. Target Operating Model

### 3.1 Portfolio Value Lifecycle

Every tenant should support this lifecycle:

1. Configure tenant setup:
   - business units,
   - workstreams,
   - financial metrics,
   - scenarios,
   - bridge rows,
   - cost categories,
   - stage gates,
   - gate criteria,
   - baseline year and baseline values.

2. Create or import initiatives:
   - owner,
   - sponsor,
   - business unit,
   - workstream,
   - stage,
   - initiative baseline allocation,
   - benefit lines,
   - cost lines,
   - monthly plan/forecast/actual values.

3. Validate value:
   - submit benefit lines to Finance,
   - Finance validates or rejects,
   - evidence and assumptions are captured,
   - only validated value can be marked bankable if tenant governance requires
     validation.

4. Lock bankable plan:
   - stage-gate approval creates immutable snapshot,
   - snapshot includes benefit lines, cost lines, monthly values, assumptions,
     validator metadata, and summary totals,
   - rebaseline creates a new version without modifying old versions.

5. Track realization:
   - ledger entries capture actual benefit realization,
   - actuals are tied to benefit lines where possible,
   - rollups compare actuals to locked plan,
   - variance, leakage, over-delivery, and timing movement are visible.

6. Report to management:
   - Financial Overview,
   - Value Bridge,
   - Benefits Register,
   - Bankable Plan,
   - Benefit Tracking,
   - Waterline,
   - Control Tower,
   - board pack export.

### 3.2 Rules for New Tenants

New tenants should not require ACME-specific data. They should receive:

- default transformation governance template,
- default gate criteria template,
- default financial metric template,
- default bridge row template,
- default cost category template,
- blank tenant baseline values,
- blank initiative portfolio.

The setup checklist should make it clear which configuration is incomplete.
Tenant admins should be able to customize or deactivate defaults before creating
initiatives.

### 3.3 Rules for New Initiatives

New initiatives should automatically inherit:

- active tenant metric definitions,
- active financial scenarios,
- active bridge rows,
- active cost categories,
- active gate criteria,
- tenant fiscal year/reporting currency settings,
- governance settings such as lock gate and validation requirement.

New initiatives should not automatically create fake values. They should create
empty editable structures and dashboards should update as soon as values are
entered or imported.

### 3.4 Rules for Updated Initiatives

When initiative financial values, benefit lines, cost lines, gate state, or
benefit ledger rows change:

- initiative detail financials update immediately,
- portfolio financials update immediately,
- contributor drawer values update immediately,
- Benefits Register updates immediately,
- Bankable Plan remains immutable unless lock/rebaseline is triggered,
- Benefit Tracking actuals update from ledger rows,
- board pack export reflects the latest selected basis at generation time.

---

## 4. Workstream Plan

## Workstream A: Rollup Correctness and Traceability

### Goal

Make portfolio financial summaries, contributor drilldowns, Value Bridge,
Benefits Register, and board export all reconcile to the same rollup engine.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Existing dashboard values should remain stable, but contributor drilldowns may become more complete because benefits will appear where they were previously zero. |
| New tenants | Benefit/cost values entered after setup will be traceable immediately. |
| New initiatives | Once benefit/cost values are entered, initiative contributions appear in portfolio drilldowns. |
| API | Shared rollup response types may need additive fields for basis, scenario, and benefit-line contributions. |
| UI | Financial Overview contributor drawer and chart labels change. |
| Testing | Requires deterministic API and browser tests with seeded financial values. |

### Backend Tasks

1. Create a shared portfolio rollup module inside the financial service layer.
   - Inputs:
     - initiatives,
     - financial metric definitions,
     - financial scenarios,
     - financial benefit lines,
     - financial metric values,
     - financial cost lines,
     - annual baselines,
     - bankable plans where requested,
     - benefit ledger where requested.
   - Outputs:
     - period totals,
     - summary totals,
     - initiative contributors,
     - benefit-line contributors,
     - cost-line contributors,
     - bridge rows,
     - basis metadata.

2. Update `/portfolio/financials` to consume the shared rollup.

3. Update `/portfolio/financials/contributors` to include clean configurable
   metric values by initiative and benefit line.

4. Add benefit-line contribution details:
   - metric key,
   - metric label,
   - benefit line id,
   - benefit line name,
   - scenario key,
   - plan value,
   - actual value,
   - variance.

5. Add response basis metadata:
   - `basis_type`: `in_year`, `target_year_run_rate`, `cumulative`, `all_years`,
   - `basis_year`,
   - `scenario_keys`,
   - `granularity`,
   - `filters_applied`.

6. Make all totals Decimal-only and preserve string JSON output.

### Frontend Tasks

1. Update Financial Overview contributor drawer:
   - show benefit contribution,
   - show cost contribution,
   - show net run-rate contribution,
   - show benefit lines under each initiative,
   - preserve cost-line drilldown.

2. Add visible basis label near the chart and summary cards:
   - example: `FY28 run-rate / Plan Base / Yearly`.

3. Add empty states that distinguish:
   - no initiatives,
   - no benefit values,
   - no actuals,
   - no locked plans.

### Acceptance Criteria

- ACME FY28 Financial Overview remains:
  - Benefits: `$9.15M`,
  - Recurring costs: `$0.80M`,
  - Net run-rate value: `$8.35M`.
- FY28 contributor drawer sums to the same `$9.15M` benefits and `$8.35M` net.
- Contributor drawer shows the 10 ACME initiatives with benefit-line detail.
- Filtering by year, stage, workstream, business unit, tag, and cost category
  keeps summary and contributor totals reconciled.

---

## Workstream B: Governance Criteria Completeness

### Goal

Make gate criteria complete and usable for every tenant, and make missing
criteria visible before initiatives reach approval.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Existing custom gate criteria remain. Missing criteria can be backfilled from default template only when explicitly requested or by seed. |
| New tenants | Default criteria are created during tenant bootstrap. |
| New initiatives | Criteria checklist is available immediately once gates exist. |
| API/UI | Admin setup status and governance screens become clearer. |
| Security | Governance config writes remain transformation-office only. |

### Backend Tasks

1. Define default gate criteria template in a single seed/bootstrap service:
   - Gate 1: Strategic fit confirmed.
   - Gate 1: Value hypothesis documented.
   - Gate 2: Baseline approved.
   - Gate 2: Benefit assumptions documented.
   - Gate 2: Finance validation completed.
   - Gate 3: Delivery plan approved.
   - Gate 3: Owner and sponsor assigned.
   - Gate 4: Implementation evidence submitted.
   - Gate 4: Actuals collection started.
   - Gate 5: Benefits realized and accepted.

2. Add idempotent bootstrap logic:
   - create missing criteria for tenants with no criteria,
   - do not overwrite tenant-customized criteria,
   - support ACME seed backfill.

3. Extend setup-status API to return:
   - missing gate definitions count,
   - missing active criteria count,
   - per-gate completion summary.

4. Ensure gate submission checks use active configured criteria only.

### Frontend Tasks

1. Admin setup checklist:
   - show exact missing gate criteria count,
   - link directly to Admin -> Governance Engine.

2. Governance Engine:
   - show per-gate criteria completeness,
   - add one-click "seed default criteria" action for blank tenants,
   - make destructive overwrite impossible from the default action.

3. Initiative governance tab:
   - show criteria evidence status,
   - block submission when required criteria are not ticked.

### Acceptance Criteria

- ACME setup status becomes 8/8 after seed backfill.
- New tenant bootstrap creates default gate criteria.
- Existing tenants with custom criteria are not overwritten.
- Gate submission cannot bypass required active criteria.

---

## Workstream C: Bankable Plan and ACME Seed Completion

### Goal

Make ACME a complete end-to-end board demo and make seed logic reusable for any
future demo tenant.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | No automatic bankable plan locks unless explicitly backfilled. |
| ACME tenant | Gets gate criteria, Gate 2 approvals, locked bankable plans, benefit ledger rows, and one rebaseline example. |
| New tenants | Demo bootstrap can optionally load complete demo portfolio; normal tenant bootstrap remains blank. |
| Dashboards | Bankable Plan, Benefit Tracking, and Waterline become meaningful for ACME. |

### Backend/Seed Tasks

1. Update ACME seed script to create default gate criteria.

2. Simulate Gate 2 approvals for all 10 initiatives:
   - submission created,
   - criteria checked,
   - approval recorded,
   - lock-on-approval creates bankable plan snapshot.

3. Create locked bankable plans for all 10 initiatives:
   - version 1 for all initiatives,
   - include snapshot schema version,
   - include benefit lines, metric values, cost lines, annual baselines,
     selections, and summary totals.

4. Create one rebaseline example:
   - recommended initiative: `ENT-005 Enterprise Data Platform`,
   - version 1 original plan,
   - version 2 rebaseline with reason,
   - clear commentary about delayed/cost-increased scenario.

5. Seed benefit realization ledger rows:
   - FY27 and FY28 monthly rows,
   - plan amount from locked bankable plan phasing,
   - actual amount reconciled to actual financial values,
   - descriptions/evidence references.

6. Seed evidence/assumption comments for:
   - `ENT-006 Pricing & Discount Optimization`,
   - `ENT-008 Procurement Vendor Consolidation`,
   - `ENT-010 AI Service Desk Automation`.

7. Ensure seed is idempotent:
   - rerunning should update known demo rows or replace by deterministic key,
   - no duplicate bankable plan versions unless explicitly creating versioned
     rebaseline data.

### Frontend Tasks

No major new UI is required in this workstream, but verify:

- Bankable Plan shows current and history.
- Benefit Tracking shows locked baseline, actual, variance.
- Waterline preview includes locked plan source where applicable.
- Financial Overview still reconciles.

### Acceptance Criteria

- ACME Bankable Plan screen shows locked versions for all 10 initiatives.
- `ENT-005` shows at least two bankable plan versions.
- ACME Benefit Tracking shows non-zero locked baseline and actuals.
- ACME Waterline can lock or preview workstream targets with meaningful data.
- Demo guide warnings can be updated after verification.

---

## Workstream D: Benefit-Line Finance Validation and Evidence

### Goal

Make financial validation auditable at benefit-line level before value is
counted as bankable or realized.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Existing benefit lines default to `draft` or `unvalidated`. Backfill can mark ACME demo values as validated. |
| New tenants | Benefit lines include validation state from creation. |
| New initiatives | Benefit lines must be submitted and validated if governance setting requires it. |
| API | New fields and endpoints for validation workflow. |
| UI | Initiative Financials and Benefits Register show validation state. |
| Security | Finance validation is role-sensitive and requires Prahari review. |

### Data Model Changes

Add columns to `financial_benefit_lines`:

- `validation_status TEXT NOT NULL DEFAULT 'draft'`
  - allowed: `draft`, `submitted`, `finance_validated`, `rejected`,
    `superseded`
- `submitted_at TIMESTAMPTZ`
- `submitted_by UUID REFERENCES users(id)`
- `validated_at TIMESTAMPTZ`
- `validated_by UUID REFERENCES users(id)`
- `validation_comment TEXT`
- `evidence_url TEXT`
- `evidence_label TEXT`
- `rejection_reason TEXT`

Add optional history table:

```text
financial_benefit_line_validation_events
```

Columns:

- `id`
- `tenant_id`
- `benefit_line_id`
- `initiative_id`
- `from_status`
- `to_status`
- `actor_user_id`
- `comment`
- `evidence_url`
- `created_at`

### Backend Tasks

1. Add Pydantic models:
   - benefit validation status,
   - submit request,
   - validate request,
   - reject request,
   - validation event response.

2. Add service methods:
   - submit benefit line,
   - validate benefit line,
   - reject benefit line,
   - list validation history.

3. Add router endpoints:
   - `POST /initiatives/{id}/financials/benefit-lines/{line_id}/submit`
   - `POST /initiatives/{id}/financials/benefit-lines/{line_id}/validate`
   - `POST /initiatives/{id}/financials/benefit-lines/{line_id}/reject`
   - `GET /initiatives/{id}/financials/benefit-lines/{line_id}/validation-events`

4. Enforce RBAC:
   - transformation office can submit,
   - finance validator role should be introduced or mapped initially to
     transformation office,
   - viewers cannot mutate.

5. Add governance setting:
   - `require_finance_validation_for_bankable_plan`.

6. If enabled, block bankable plan lock when included benefit lines are not
   `finance_validated`.

### Frontend Tasks

1. Initiative Financials tab:
   - show validation status per benefit line,
   - submit for validation,
   - validate/reject controls for authorized users,
   - evidence/comment fields,
   - validation history drawer.

2. Financial Scope:
   - display whether selected benefits are draft/submitted/validated.

3. Bankable Plan:
   - show validation status in snapshot,
   - explain if lock is blocked by unvalidated benefits.

4. Admin Financial Governance:
   - toggle `require_finance_validation_for_bankable_plan`.

### Acceptance Criteria

- Benefit line can move draft -> submitted -> finance_validated.
- Benefit line can move submitted -> rejected with reason.
- Events are recorded with actor and timestamp.
- Bankable plan lock is blocked when validation is required and lines are not
  validated.
- Existing tenants are not broken by default.

---

## Workstream E: Portfolio Benefits Register

### Goal

Add a first-class portfolio screen for benefit management across initiatives.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Immediately see existing benefit lines in one place. |
| New tenants | Empty register until initiatives and benefit lines are created. |
| New initiatives | Benefit lines appear in register after creation. |
| Dashboards | Register becomes the working view behind board value claims. |

### Backend Tasks

1. Add `GET /portfolio/benefits-register`.

2. Supported filters:
   - initiative,
   - owner,
   - workstream,
   - business unit,
   - stage,
   - tag,
   - metric,
   - benefit class,
   - validation status,
   - realization status,
   - confidence range,
   - year,
   - scenario,
   - locked/unlocked.

3. Response row fields:
   - benefit line id,
   - initiative id/code/name,
   - owner,
   - business unit,
   - workstream,
   - stage,
   - metric key/label,
   - benefit class,
   - benefit line name,
   - confidence,
   - validation status,
   - validator,
   - evidence,
   - baseline value where applicable,
   - plan value,
   - forecast value,
   - actual value,
   - variance,
   - bankable plan version,
   - realization status,
   - next milestone/risk marker where available.

4. Response summary cards:
   - total plan benefits,
   - finance validated benefits,
   - bankable locked benefits,
   - realized benefits,
   - variance to locked plan,
   - value at risk.

### Frontend Tasks

1. Add route:
   - `/financials/benefits-register`

2. Add navigation under Financials.

3. Build dense executive table:
   - filters,
   - summary cards,
   - sortable rows,
   - validation state badges,
   - evidence link,
   - drillthrough to initiative financials,
   - export CSV/XLSX.

4. Add row actions where authorized:
   - submit,
   - validate,
   - reject,
   - open validation history.

### Acceptance Criteria

- Existing ACME benefit lines appear in register.
- Register totals reconcile to Financial Overview for selected year/scenario.
- Filtering by validation status shows draft/submitted/validated benefits.
- New benefit line created on initiative detail appears without manual refresh
  after data reload.

---

## Workstream F: Value Bridge Basis Controls

### Goal

Remove ambiguity between in-year value, cumulative value, target-year run-rate,
and all-years value.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Existing values remain, but labels and basis controls make interpretation clearer. |
| New tenants | Value bridge is understandable immediately after financial values are entered. |
| API | Additive query params and basis metadata. |
| UI | Financial Overview bridge labels and filters change. |

### Backend Tasks

1. Extend `/portfolio/value-bridge` query params:
   - `basis=in_year|target_year_run_rate|cumulative|all_years`,
   - `year`,
   - `scenario`,
   - `stage`,
   - `workstream_id`,
   - `business_unit_id`,
   - `tag`,
   - `category_key`,
   - `as_of_date`.

2. Return basis metadata:
   - selected basis,
   - selected period,
   - included periods,
   - scenarios used,
   - filters.

3. Use the same shared rollup module from Workstream A.

4. Update value bridge rows to remain tenant-configurable.

### Frontend Tasks

1. Add segmented basis control:
   - In-year,
   - Run-rate,
   - Cumulative,
   - All years.

2. Add scenario selector:
   - primary plan,
   - high/upside,
   - actual,
   - forecast if configured.

3. Show explicit label:
   - example: `FY28 run-rate / Plan Base / All active stages`.

4. Explain one-off cost treatment in label or tooltip:
   - run-rate net value excludes one-off investment from EBITDA run-rate,
   - payback/investment view includes one-off investment.

### Acceptance Criteria

- ACME FY28 run-rate bridge reconciles to Financial Overview.
- ACME all-years bridge remains available but clearly labeled as all-years.
- Switching basis changes values and labels predictably.
- Exported board pack uses the same selected basis.

---

## Workstream G: Board Pack Export

### Goal

Create a repeatable portfolio export for steering committee and board reporting.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Can export current portfolio value story without manual screenshots. |
| New tenants | Export works once data exists. |
| API | New report generation endpoint. |
| UI | New export action on Financial Overview and Control Tower. |

### Backend Tasks

1. Add endpoint:
   - `POST /reports/board-pack/export`

2. Request fields:
   - year,
   - basis,
   - scenario,
   - stage,
   - workstream,
   - business unit,
   - tag,
   - include_actuals,
   - include_risks,
   - include_appendix.

3. Generate XLSX first. PDF can be a later enhancement.

4. Workbook tabs:
   - Executive Summary,
   - Portfolio Baseline,
   - Value Bridge,
   - Financial Trend,
   - Top Initiatives,
   - Benefits Register,
   - Bankable Plan Status,
   - Benefit Realization,
   - Waterline,
   - Risks and Decisions,
   - Assumptions Appendix.

5. Use shared rollup APIs/services, not duplicated calculations.

### Frontend Tasks

1. Add export button on:
   - Financial Overview,
   - Benefits Register,
   - Control Tower.

2. Add export modal:
   - basis,
   - year,
   - scenario,
   - filters,
   - sections to include.

3. Download generated file.

### Acceptance Criteria

- ACME board pack exports and opens.
- Export totals match Financial Overview for the selected filters.
- Benefits Register tab totals match the on-screen register.
- No PII beyond authorized user-visible names is included unless explicitly
  required by the selected report.

---

## Workstream H: Risk-Adjusted Value and Ownership Handoff

### Goal

Add management-level views for value at risk and post-go-live accountability.

### Impact

| Area | Impact |
|---|---|
| Existing tenants | Uses existing confidence, risks, milestones, and owners where available. |
| New tenants | Optional until benefit lines and risks are populated. |
| New initiatives | Handoff fields can be captured during setup or before go-live. |

### Data Model Changes

Potential additions:

- `financial_benefit_lines.realization_owner_id`
- `financial_benefit_lines.handoff_status`
- `financial_benefit_lines.handoff_at`
- `financial_benefit_lines.risk_adjustment_pct`
- `financial_benefit_lines.value_at_risk_reason`

### Backend Tasks

1. Compute risk-adjusted plan:
   - `risk_adjusted_value = plan_value * confidence_pct`
   - later enhancement: incorporate open risk severity/probability.

2. Add optional filter/report fields:
   - handoff status,
   - realization owner,
   - value at risk.

3. Add dashboard summary:
   - gross plan,
   - finance validated plan,
   - risk-adjusted plan,
   - realized value.

### Frontend Tasks

1. Add risk-adjusted columns to Benefits Register.

2. Add realization owner/handoff controls.

3. Add board pack section:
   - value at risk,
   - owner handoff status,
   - decisions required.

### Acceptance Criteria

- Benefits Register can show gross, validated, risk-adjusted, bankable, and
  realized value.
- Initiatives after go-live have an accountable realization owner.
- Board pack highlights value at risk and decisions required.

---

## 5. Data Model Summary

### 5.1 Additive Schema Changes

Recommended additive migrations:

1. `financial_benefit_lines` validation fields:
   - `validation_status`,
   - `submitted_at`,
   - `submitted_by`,
   - `validated_at`,
   - `validated_by`,
   - `validation_comment`,
   - `evidence_url`,
   - `evidence_label`,
   - `rejection_reason`.

2. `financial_benefit_line_validation_events`:
   - immutable validation audit trail.

3. `benefit_realization_ledger` enhancements:
   - `benefit_line_id`,
   - `scenario_id` if needed for actual/forecast distinction,
   - `evidence_url`,
   - `evidence_label`,
   - `submitted_by`,
   - `validated_by`,
   - `validation_status`.

4. Optional board export history table:
   - `portfolio_report_exports`
   - useful for audit and regenerated pack history.

5. Optional benefit ownership fields:
   - realization owner,
   - handoff status,
   - risk adjustment.

### 5.2 RLS Requirements

Every new table must include:

- `tenant_id UUID NOT NULL`,
- RLS enabled,
- tenant-scoped select policy,
- transformation-office mutation policy,
- finance-validation mutation policy if a dedicated finance role is added,
- tenant-scoped indexes.

### 5.3 Money Rules

All financial values must preserve existing project standards:

- PostgreSQL: `NUMERIC(15,4)`,
- Python: `decimal.Decimal`,
- JSON: strings,
- no float arithmetic.

---

## 6. API Summary

### New or Extended APIs

| API | Change |
|---|---|
| `GET /portfolio/financials` | Add basis metadata from shared rollup. |
| `GET /portfolio/financials/contributors` | Add benefit-line contributions and clean metric values. |
| `GET /portfolio/value-bridge` | Add basis/scenario/filter controls and basis metadata. |
| `GET /portfolio/benefits-register` | New portfolio benefit line register. |
| `POST /initiatives/{id}/financials/benefit-lines/{line_id}/submit` | New validation workflow. |
| `POST /initiatives/{id}/financials/benefit-lines/{line_id}/validate` | New validation workflow. |
| `POST /initiatives/{id}/financials/benefit-lines/{line_id}/reject` | New validation workflow. |
| `GET /initiatives/{id}/financials/benefit-lines/{line_id}/validation-events` | New audit trail. |
| `POST /reports/board-pack/export` | New board pack export. |
| `GET /admin/setup-status` | Add per-gate criteria completeness. |
| `POST /admin/governance/default-criteria` | Optional seed missing criteria for blank tenant. |

### API Compatibility

Prefer additive response fields and new endpoints. Avoid breaking existing UI
contracts unless a single PR updates API, Angular models, and tests together.

---

## 7. Frontend Summary

### Screens to Update

| Screen | Route | Required update |
|---|---|---|
| Financial Overview | `/financials` | Contributor drawer, basis labels, value bridge controls, board pack export. |
| Bankable Plan | `/financials/bankable-plan` | Validation metadata, clearer version history, lock eligibility. |
| Benefit Tracking | `/financials/benefit-tracking` | Benefit-line/evidence-aware ledger and ACME populated state. |
| Waterline | `/financials/waterline` | Ensure locked plan source and actuals remain clear. |
| Initiative Financials | initiative detail financial tab | Benefit-line validation workflow and evidence. |
| Financial Scope | `/initiatives/:id/financial-scope` | Validation state and lock eligibility preview. |
| Governance Engine | `/admin` governance section | Gate criteria completeness and default criteria seed action. |
| Control Tower | existing report route | Board pack export and consistent rollup values. |

### New Screen

| Screen | Route | Purpose |
|---|---|---|
| Benefits Register | `/financials/benefits-register` | Portfolio-wide benefit line management, validation, evidence, realization status, and financial traceability. |

### Design Constraints

Follow the existing Transmuter design direction:

- dense executive layouts,
- CSS variables,
- light and dark support,
- restrained shadows and thin dividers,
- no purple/lavender/orb styling,
- ARIA labels on controls,
- stable table and chart dimensions.

---

## 8. Testing Plan

### Backend Unit Tests

Add or extend tests for:

- clean configurable metric contributor rollup,
- value bridge basis logic,
- benefit-line validation transitions,
- bankable plan lock blocked by unvalidated benefits when setting is enabled,
- benefit ledger rollups by benefit line,
- board pack workbook generation,
- setup-status criteria completeness.

### Real API Acceptance Tests

Required scenarios:

1. Seed deterministic tenant with:
   - users,
   - business units,
   - workstreams,
   - stage gates,
   - gate criteria,
   - initiatives,
   - benefit lines,
   - metric values,
   - cost lines,
   - bankable plans,
   - benefit ledger rows.

2. Validate:
   - portfolio financials summary,
   - contributor drawer totals,
   - value bridge basis switching,
   - Benefits Register totals,
   - bankable plan lock/rebaseline,
   - benefit validation workflow,
   - benefit tracking rollup,
   - board pack export.

### Browser Acceptance Tests

Run against real Angular app and real API:

- login as transformation office,
- configure default gate criteria,
- create initiative,
- add benefit lines and cost lines,
- submit/validate benefit line,
- approve gate and lock bankable plan,
- add ledger actual,
- verify Financial Overview updates,
- verify Benefits Register updates,
- verify Benefit Tracking updates,
- export board pack.

### ACME Regression Tests

ACME-specific assertions:

- setup checklist is 8/8,
- baseline remains `$20.0M` revenue and `$9.0M` gross margin,
- 10 initiatives exist,
- initiative baselines reconcile to tenant baseline,
- FY28 Financial Overview remains `$9.15M` benefits, `$0.80M` recurring cost,
  `$8.35M` net run-rate,
- contributor drawer totals match summary,
- Bankable Plan has locked plans,
- Benefit Tracking has non-zero locked and actual values,
- `ENT-005` has rebaseline history.

---

## 9. Deployment and Data Rollout Plan

### Dev Environment

All changes should deploy to dev first:

```bash
./infra/hostinger/deploy-change-to-dev.sh --schema path/to/schema.sql
```

Dev schema:

```text
transmuter_dev
```

Dev app:

```text
https://transmuter-dev.ishirock.tech
```

### Production Promotion

After approval and dev verification:

```bash
CONFIRM_PROMOTE=1 ./infra/hostinger/promote-dev-to-prod.sh --schema path/to/schema.sql
```

Production schema:

```text
transmuter
```

### Data Backfill Rules

1. Existing tenant data must not be destructively reset.
2. Additive schema migrations only unless explicitly approved.
3. Existing benefit lines default to `draft` or `unvalidated`.
4. Demo seed scripts may update ACME deterministic data.
5. Normal new tenants get templates, not ACME demo values.
6. Backfill scripts must be idempotent and tenant-scoped.

### Rollback Considerations

Additive schema changes are easy to leave in place during code rollback. Avoid
dropping or rewriting existing financial values. If board export history is
added, exported files or generated metadata should be safe to ignore on rollback.

---

## 10. Suggested Issue Breakdown

Create a new epic and child issues after plan approval.

### Epic

`Platform-wide benefits realization and board reporting hardening`

### P1 Issues

1. `Backend: shared portfolio rollup and contributor benefit traceability`
2. `Frontend: Financial Overview contributor drawer and basis labels`
3. `Seed: ACME gate criteria, bankable plans, benefit ledger, and rebaseline`
4. `Backend: setup-status gate criteria completeness`
5. `Acceptance: ACME financial reconciliation and dashboard regression`

### P2 Issues

6. `Schema/API: benefit-line Finance validation and evidence workflow`
7. `Frontend: benefit-line validation controls in initiative financials`
8. `Backend/UI: portfolio Benefits Register`
9. `Backend/UI: Value Bridge basis controls`
10. `Acceptance: new tenant and new initiative benefits realization workflow`

### P3 Issues

11. `Backend/UI: board pack export`
12. `Backend/UI: risk-adjusted value and ownership handoff`
13. `Docs: update ACME demo guide after platform improvements`
14. `Release: Hostinger dev deployment, validation, and production promotion`

---

## 11. SDLC and Review Requirements

Follow the canonical process in `docs/team/SDLC_PROTOCOL.md`:

1. Vishwa triage and issue setup.
2. Netra requirements for each epic slice.
3. Vastu architecture for schema/API/shared rollup.
4. Chitra design for Financial Overview, Benefits Register, and board export.
5. Karya/Rupa implementation.
6. Prahari review for:
   - RLS policies,
   - validation workflow/RBAC,
   - report exports,
   - any new tenant data bootstrap path.
7. Aksha real API and browser acceptance.
8. Sthira deploy readiness.
9. Vishwa final review and issue closure.

Documentation-only planning can skip GitHub issue creation, but runtime
implementation should not.

---

## 12. Release Sequence

### Release 1: Correctness and ACME Demo Readiness

Scope:

- shared contributor rollup fix,
- Financial Overview contributor drawer update,
- setup-status criteria completeness,
- ACME gate criteria,
- ACME bankable plans,
- ACME benefit ledger rows,
- `ENT-005` rebaseline example.

Success:

- ACME is board-demo-ready on current screens.
- No new major product surface is required.
- Dashboards reconcile end to end.

### Release 2: Finance Validation Workflow

Scope:

- benefit-line validation schema,
- validation endpoints,
- validation UI,
- lock eligibility integration,
- audit events.

Success:

- Value can be submitted, validated, rejected, and audited.
- Bankable plan lock can require Finance validation.

### Release 3: Benefits Register and Value Bridge Basis

Scope:

- Benefits Register API/UI,
- Value Bridge basis controls,
- exportable register data.

Success:

- Transformation office can manage all benefits across the portfolio.
- Boards can see whether values are in-year, run-rate, cumulative, or all-years.

### Release 4: Board Pack and Advanced Governance

Scope:

- board pack XLSX export,
- risk-adjusted value,
- ownership handoff,
- updated guides and demo scripts.

Success:

- Repeatable monthly management pack is generated from platform data.
- Benefits remain accountable after delivery.

---

## 13. Open Decisions for Approval

1. Should a dedicated `finance_validator` role be introduced, or should
   `transformation_office` perform Finance validation initially?

2. Should existing benefit lines default to `draft`, or should demo/imported
   values be backfilled to `finance_validated` when the source is trusted?

3. Should the board pack export be XLSX-only for the first release, or should
   PDF be included immediately?

4. Should benefit realization ledger actuals be captured directly against
   benefit lines in the first validation release, or should the current
   initiative-level ledger remain primary until the Benefits Register is built?

5. Should value bridge default basis be:
   - target-year run-rate, or
   - in-year value?

Recommended defaults:

- Use `transformation_office` as Finance validator initially, then add a
  dedicated role later if needed.
- Default existing benefit lines to `draft`, but seed ACME trusted demo lines as
  `finance_validated`.
- Build XLSX board pack first.
- Add `benefit_line_id` to ledger in the validation release.
- Default Value Bridge to target-year run-rate when a year is selected.

---

## 14. Approval Checklist

Implementation should start only after these decisions are confirmed:

- [ ] Approve release sequence.
- [ ] Approve P1 scope for first implementation batch.
- [ ] Confirm Finance validation role approach.
- [ ] Confirm Value Bridge default basis.
- [ ] Confirm ACME seed may be updated in dev and production demo data.
- [ ] Confirm board pack initial format.
- [ ] Confirm whether to create the suggested GitHub epic and child issues.
