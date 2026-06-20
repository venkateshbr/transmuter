# Shared Costs Configurable Revamp Plan

Status: Planning draft
Owner role: Vishwa
Date: 2026-06-20
Scope: Product, architecture, data model, API, UI, reporting, and acceptance plan for revamping the top-level `/shared-costs` capability.

## 1. Executive Summary

Shared Costs is present in the platform today, but it is still a seed-level
financial governance feature rather than a configurable Finance operating model.
The current implementation can create a central cost pool, attach one allocation
rule, run the allocation, and show allocated costs in Executive Control Tower
burdened-value views. That is useful, but it is not yet aligned with the same
principles as the configurable financial metrics engine:

- Finance-owned configuration should be selectable and validated, not entered as
  raw JSON.
- Allocation methods should be understandable to a portfolio user, with visible
  math, candidate lists, basis values, and reconciliation.
- Shared cost categories, scenarios, and reporting treatment should reuse the
  tenant financial engine instead of inventing parallel strings.
- Allocation runs should support preview, approval, lock, versioning, and audit
  before they affect executive dashboards.
- Allocations should be available as a separate burden ledger and optionally as
  posted initiative financial cost lines, depending on tenant policy.

The recommended revamp is to turn Shared Costs into a configurable allocation
engine:

```text
Cost pool -> allocation policy -> preview -> approved run -> allocation ledger -> reporting impact
```

The top-level menu should remain. It should become the Finance Lead's control
surface for central PMO, platform, cloud, license, vendor, and shared delivery
costs that support multiple initiatives.

## 2. Current Branch Review

### 2.1 Current product surface

Current UI:

- Route: `/shared-costs`
- Component: `apps/web/src/app/features/financials/shared-costs.component.ts`
- Top-level navigation: `apps/web/src/app/app.ts`

What a user can do today:

- Create a pool with name, category key, year, planned amount, and actual amount.
- Select a pool.
- Create an allocation rule.
- Choose one of six allocation methods.
- Enter filters and weights as raw JSON.
- Run an allocation immediately for `plan`.
- View run history counts and total amounts.

Current UI limitations:

- Pool category is free text, not selected from tenant cost categories.
- Quarter, month, recurrence, status, and scenario are mostly hidden.
- Allocation filters and weights require raw JSON.
- There is no guided initiative selection.
- There is no preview before posting.
- There is no rule versioning, approval, lock, or void reason.
- There is no allocation detail table showing which initiatives received what
  and why.
- There is no reporting impact preview.
- There is no clear connection to financial scenarios, metric definitions, cost
  categories, value bridge rows, or bankable plan settings.

### 2.2 Current schema

The current migration creates these tables in
`supabase/migrations/20260510000001_executive_control_tower.sql`:

| Table | Current purpose |
|---|---|
| `shared_cost_pools` | Stores one central cost pool with year, optional quarter/month, plan/actual amounts, category key, recurrence flag, and status. |
| `shared_cost_allocation_rules` | Stores one rule per pool, including method, filters JSON, weights JSON, and active flag. |
| `shared_cost_allocation_runs` | Stores completed or voided runs for a pool/rule/scenario. |
| `shared_cost_allocations` | Stores initiative-level allocated plan/actual amounts for a run. |

Strengths:

- Tables are tenant-scoped with `tenant_id`.
- RLS policies exist.
- Money uses `NUMERIC(15,4)`.
- Allocations are stored as a ledger separate from direct initiative cost lines.
- Runs create immutable-ish allocation rows rather than recomputing every report.

Gaps:

- `category_key` is a plain text field instead of a relationship to
  `financial_cost_categories`.
- `scenario` is a fixed enum of `plan` and `actual`, not tenant-defined
  `financial_scenarios`.
- Pools store one plan/actual amount, so monthly or quarterly allocation is not
  first-class.
- Rules are mutable without version snapshots.
- Filters and weights are arbitrary JSON with no schema, no labels, and weak
  validation.
- Allocations only target initiatives directly.
- There is no approval status such as `draft`, `previewed`, `approved`,
  `locked`, `posted`, `voided`.
- There is no posting mode or reporting policy.
- There is no audit trail for who changed the basis, approved a run, or voided a
  run.

### 2.3 Current backend behavior

Backend files:

- Domain models: `apps/api/app/domain/executive_control.py`
- Router: `apps/api/app/routers/executive_control.py`
- Service: `apps/api/app/services/executive_control.py`
- Repository: `apps/api/app/repositories/executive_control.py`

Current API surface:

```text
GET    /shared-cost-pools
POST   /shared-cost-pools
PATCH  /shared-cost-pools/{pool_id}
GET    /shared-cost-pools/{pool_id}/allocation-rules
POST   /shared-cost-pools/{pool_id}/allocation-rules
PATCH  /shared-cost-pools/{pool_id}/allocation-rules/{rule_id}
GET    /shared-cost-pools/{pool_id}/allocation-runs
POST   /shared-cost-pools/{pool_id}/allocation-runs
```

Current allocation methods:

- `equal_split`
- `fixed_percentage`
- `manual_amount`
- `benefit_weighted`
- `revenue_weighted`
- `headcount_weighted`

Current engine behavior:

- Candidate initiatives are selected by a small filter set:
  `business_unit_id`, `workstream_id`, `tag`, `country`, `rag_status`, `stage`,
  and `owner_id`.
- `benefit_weighted` uses legacy financial entries and
  `gm_uplift_base`.
- `revenue_weighted` uses legacy financial entries and
  `revenue_uplift_base`.
- `fixed_percentage`, `manual_amount`, and `headcount_weighted` read values
  from weights JSON keyed by initiative ID.
- If total basis is zero, the engine falls back to equal split.
- The last allocation row absorbs rounding so allocated total reconciles to the
  pool amount.
- A posted run is immediately stored with status `completed`.

Strengths:

- Decimal arithmetic is used in the service.
- The allocation total reconciles to the pool total.
- Service and repository separation exists.
- Reporting reads stored allocations instead of recomputing live.

Gaps:

- `manual_amount` is treated as a weighting basis, not as explicit allocation
  amounts. This is confusing because manual dollars are normalized as shares.
- `fixed_percentage` does not appear to validate that percentages total 100%.
- Zero-basis fallback to equal split may hide missing driver data.
- Benefit and revenue methods use legacy fields instead of the configurable
  metric engine.
- The current router marks runs complete on creation; there is no preview or
  approval path.
- There is no explicit error model for excluded initiatives, missing basis data,
  or unreconciled weights.

### 2.4 Current reporting impact

Shared Costs already affects:

| Surface | Current impact |
|---|---|
| Executive Control Tower `/reports/control-tower` | Adds allocated costs into burdened value bridge and `net_after_allocation`. |
| Dashboard executive brief | Shows allocated costs, burdened costs, and net after allocation from the executive report. |
| Executive Control Tower table | Shows initiative-level burdened cost and net after allocation. |
| Needs Attention | Flags low-confidence initiatives that have allocated shared cost. |

Current behavior is intentionally report-only. Allocations do not overwrite
direct initiative cost lines.

Reporting gaps:

- No visible lineage from a dashboard number back to pool, rule, run, and basis.
- No report setting for "include shared cost burden" versus "direct-only value".
- No separate "allocated shared cost" dimension in Portfolio Financials.
- No initiative financial tab section for allocated burden.
- No bankable plan/waterline policy for whether allocated shared costs reduce
  bankable value.
- No reporting freshness indicator showing which allocation run is driving the
  number.

### 2.5 Current tests

Current coverage:

- Unit-style service tests prove allocation reconciliation and report impact.
- Real API acceptance checks seeded pools, rules, runs, allocation totals, and
  Executive Control Tower allocated cost output.
- Browser acceptance checks route availability at a high level.

Coverage gaps:

- No real browser flow for configuring a pool, rule, preview, approval, and
  allocation detail review.
- No tests for financial-engine-backed metrics or cost categories.
- No tests for invalid weights, missing basis, zero basis, partial filters, or
  allocation exclusions.
- No tests for RLS isolation across tenants for allocation data.
- No tests for reporting mode toggles or bankable plan impact.

## 3. Platform Product Principle

Shared Costs should answer this Finance question:

```text
Which central costs should be fairly burdened across initiatives, and how does
that change portfolio value without distorting direct initiative ownership?
```

The feature should keep three concepts separate and visible:

| Concept | Meaning | Reporting treatment |
|---|---|---|
| Direct initiative cost | Cost owned by a specific initiative. | Initiative financials and value bridge as direct cost. |
| Shared cost pool | Central cost that supports multiple initiatives. | Managed centrally in `/shared-costs`. |
| Allocated burden | A calculated share of a shared cost pool assigned to initiatives. | Shown in burdened value, optionally posted to initiative financials if tenant policy allows. |

This distinction matters because direct initiative economics answer "what does
the initiative owner control?", while burdened economics answer "what is the
fully loaded portfolio value after central costs?"

## 4. Target User Experience

### 4.1 Top-level navigation

Keep Shared Costs as a top-level menu item. It should feel like a Finance
workbench, not an admin-only table.

Recommended tabs:

| Tab | Purpose |
|---|---|
| Overview | Pool totals, allocated/unallocated amounts, latest approved runs, reporting impact, exceptions. |
| Pools | Create and maintain central cost pools by category, scenario, period, and recurrence. |
| Policies | Configure reusable allocation policies and rule versions. |
| Preview and Runs | Preview allocations, resolve exceptions, approve, lock, void, or re-run. |
| Allocation Ledger | Search allocations by initiative, pool, period, scenario, and report status. |
| Reporting Impact | Show where allocations affect dashboards, reports, bankable plan, and initiative views. |

### 4.2 Pool configuration

Replace the single inline create form with a structured pool editor.

Pool fields:

| Field | Source | Notes |
|---|---|---|
| Name | User input | Required. |
| Description | User input | Explains what the pool represents. |
| Cost category | `financial_cost_categories` | Required; no free-text category for active pools. |
| Cost behavior | Category default, overrideable | One-off, recurring, total cost. |
| Scenario | `financial_scenarios` | Plan base, plan high, forecast, actual, etc. |
| Period grain | Select | Annual, quarterly, monthly. |
| Amounts | Decimal inputs | Periodized pool amounts. |
| Currency | Tenant currency setting | Future-proof; keep money as Decimal/string in API. |
| Recurrence | Checkbox/select | Recurring yearly/monthly rules. |
| Reporting treatment | Policy select | Report-only burden, post allocated cost lines, or both. |
| Status | Workflow | Draft, active, archived. |
| Owner | User/role | Finance owner accountable for pool. |

### 4.3 Allocation policy builder

Replace raw JSON with a guided policy builder.

Policy builder sections:

| Section | User-facing behavior |
|---|---|
| Scope | Select included initiatives by workstream, business unit, tag, country, stage, owner, gate level, or explicit initiative list. |
| Exclusions | Exclude initiatives, archived/cancelled stages, or below-threshold candidates. |
| Basis | Select allocation method and driver. |
| Driver period | Choose same period, trailing 12 months, full year, or custom period. |
| Caps/floors | Optional min/max allocation per initiative or percentage cap. |
| Rounding | Standard rounding and final-row reconciliation rule. |
| Exceptions | Choose whether missing basis fails preview or falls back to equal split. |
| Reporting | Choose whether run affects dashboards immediately after approval. |

Allocation methods:

| Method | Behavior |
|---|---|
| Equal split | Divide equally across selected initiatives. |
| Fixed percentage | User enters percentages; system must validate total equals 100%. |
| Manual amount | User enters exact amounts; system must validate total equals pool total or show unallocated remainder. |
| Benefit weighted | Weight by selected benefit-class metric from `financial_metric_definitions`. |
| Revenue weighted | Weight by selected revenue-class metric. |
| Savings weighted | Weight by selected savings-class metric. |
| Direct cost weighted | Weight by selected direct cost category totals. |
| Headcount weighted | Weight by configurable headcount metric or initiative attribute. |
| FTE/workload weighted | Weight by a numeric metric or line attribute. |
| Custom formula | Use a validated financial-engine formula or restricted expression referencing configured metrics. |

The policy builder should always render a plain-language formula, for example:

```text
Each selected initiative receives:
pool amount x initiative FY2026 gross margin uplift / selected initiatives FY2026 gross margin uplift
```

### 4.4 Preview, approval, and lock

No allocation should affect reports until a user approves or locks a run.

Recommended flow:

```text
Draft policy -> Preview -> Resolve exceptions -> Approve run -> Lock run -> Reports consume latest locked run
```

Preview page must show:

- Pool total.
- Candidate count.
- Excluded initiatives and reasons.
- Basis metric used.
- Basis value by initiative.
- Calculated share.
- Allocated plan/forecast/actual amount.
- Rounding adjustment.
- Reconciliation status.
- Report impact before and after allocation.

Approval fields:

| Field | Purpose |
|---|---|
| Approved by | Audit. |
| Approved at | Audit. |
| Approval note | Explains policy decision. |
| Locked by | Prevents silent mutation. |
| Locked at | Defines reporting effective time. |
| Void reason | Required when voiding. |

### 4.5 Allocation ledger

Add a ledger view that answers "where did this number come from?"

Ledger columns:

- Initiative code and name.
- Pool.
- Category.
- Scenario.
- Period.
- Rule version.
- Allocation method.
- Basis metric.
- Basis value.
- Share percentage.
- Allocated amount.
- Run status.
- Reporting treatment.
- Created/approved/locked metadata.

Ledger filters:

- Year, quarter, month.
- Scenario.
- Pool.
- Category.
- Method.
- Workstream.
- Business unit.
- Initiative.
- Run status.
- Reporting treatment.

## 5. Target Data Model

All new tables must include `tenant_id uuid not null`, RLS, tenant-scoped
indexes, audit columns, and service-layer tenant enforcement.

### 5.1 Extend existing tables

`shared_cost_pools` additions:

| Column | Purpose |
|---|---|
| `cost_category_id uuid` | References `financial_cost_categories(id)`. |
| `scenario_id uuid` | References `financial_scenarios(id)` for the primary planning lane. |
| `period_grain text` | `annual`, `quarterly`, or `monthly`. |
| `reporting_treatment text` | `report_only`, `post_cost_lines`, or `report_and_post`. |
| `currency_code text` | Defaults from tenant; needed for future multi-currency support. |
| `owner_id uuid` | Finance accountable user. |
| `locked_at timestamptz` | Optional pool lock. |
| `locked_by uuid` | Lock audit. |

`shared_cost_allocation_rules` additions:

| Column | Purpose |
|---|---|
| `version integer` | Immutable policy version number. |
| `driver_metric_definition_id uuid` | References selected metric basis where applicable. |
| `driver_cost_category_id uuid` | References direct cost category basis where applicable. |
| `driver_scenario_id uuid` | References scenario used for basis values. |
| `driver_period_mode text` | Same period, fiscal year, trailing 12, custom. |
| `missing_basis_behavior text` | Fail, zero, or equal split fallback. |
| `cap_floor_config jsonb` | Structured min/max configuration. |
| `is_locked boolean` | Prevents mutation after approved use. |

`shared_cost_allocation_runs` additions:

| Column | Purpose |
|---|---|
| `status text` | `preview`, `approved`, `locked`, `posted`, `voided`. |
| `run_type text` | `preview` or `posting`. |
| `period_start date` | Reporting period start. |
| `period_end date` | Reporting period end. |
| `rule_version integer` | Snapshot of rule used. |
| `input_snapshot jsonb` | Immutable pool/rule/basis snapshot. |
| `exception_summary jsonb` | Missing basis, excluded initiatives, validation errors. |
| `approved_by uuid` | Approval audit. |
| `approved_at timestamptz` | Approval audit. |
| `locked_by uuid` | Lock audit. |
| `locked_at timestamptz` | Lock audit. |
| `void_reason text` | Required when voided. |

`shared_cost_allocations` additions:

| Column | Purpose |
|---|---|
| `period_start date` | Allocation period. |
| `period_end date` | Allocation period. |
| `scenario_id uuid` | Tenant scenario. |
| `basis_metric_definition_id uuid` | Metric used for basis. |
| `basis_label text` | Human-readable basis label snapshot. |
| `allocation_share numeric(15,8)` | Share before multiplying by pool total. |
| `rounding_adjustment numeric(15,4)` | Explicit reconciliation adjustment. |
| `explanation text` | Plain-language line explanation. |
| `posted_cost_line_id uuid` | Optional link to generated `financial_cost_lines`. |

### 5.2 New tables

Recommended new tables:

| Table | Purpose |
|---|---|
| `shared_cost_pool_periods` | Periodized pool amounts by year/month/scenario. Avoids overloading one annual amount. |
| `shared_cost_rule_targets` | Structured target/include/exclude records, replacing opaque filters JSON. |
| `shared_cost_rule_weights` | Structured manual amount, fixed percentage, or headcount/FTE weights by initiative or dimension. |
| `shared_cost_reporting_settings` | Tenant policy for report-only vs posted allocations, default inclusion in dashboards, and bankable plan treatment. |
| `shared_cost_allocation_exceptions` | Stores preview/run exceptions for missing data, excluded candidates, zero basis, cap/floor adjustments. |
| `shared_cost_allocation_audit_events` | Records rule changes, previews, approvals, locks, voids, and postings. |

### 5.3 Backward compatibility

Keep current endpoints during migration. Add new endpoints rather than breaking
the existing UI until the revamp is complete.

Migration rules:

- Existing `category_key` should map to `financial_cost_categories.key` where
  possible.
- Existing `scenario = plan` should map to the primary plan scenario.
- Existing `scenario = actual` should map to the primary actual scenario.
- Existing completed runs should be treated as locked report-only runs unless a
  tenant admin chooses otherwise.
- Existing filters JSON should be migrated into structured targets where it
  matches known keys; unknown filters should remain in a legacy metadata field
  and appear as migration warnings.

## 6. API Plan

Use thin routers, service-layer business logic, and repository persistence. All
money values must be Decimal in Python and strings in JSON responses.

### 6.1 Configuration APIs

```text
GET  /shared-costs/config
GET  /shared-costs/reporting-settings
PUT  /shared-costs/reporting-settings
```

`/shared-costs/config` should return:

- Active financial scenarios.
- Active cost categories.
- Active metric definitions grouped by benefit class and value type.
- Available workstreams, business units, tags, countries, stages.
- Supported allocation methods.
- Tenant reporting defaults.

### 6.2 Pool APIs

```text
GET    /shared-cost-pools
POST   /shared-cost-pools
GET    /shared-cost-pools/{pool_id}
PATCH  /shared-cost-pools/{pool_id}
POST   /shared-cost-pools/{pool_id}/archive
POST   /shared-cost-pools/{pool_id}/lock
GET    /shared-cost-pools/{pool_id}/periods
PUT    /shared-cost-pools/{pool_id}/periods
```

### 6.3 Policy APIs

```text
GET    /shared-cost-pools/{pool_id}/allocation-policies
POST   /shared-cost-pools/{pool_id}/allocation-policies
GET    /shared-cost-pools/{pool_id}/allocation-policies/{policy_id}
PATCH  /shared-cost-pools/{pool_id}/allocation-policies/{policy_id}
POST   /shared-cost-pools/{pool_id}/allocation-policies/{policy_id}/version
POST   /shared-cost-pools/{pool_id}/allocation-policies/{policy_id}/lock
```

Keep the current `allocation-rules` endpoints as compatibility aliases until
the UI fully moves to policies.

### 6.4 Preview and run APIs

```text
POST /shared-cost-pools/{pool_id}/allocation-policies/{policy_id}/preview
POST /shared-cost-pools/{pool_id}/allocation-runs/{run_id}/approve
POST /shared-cost-pools/{pool_id}/allocation-runs/{run_id}/lock
POST /shared-cost-pools/{pool_id}/allocation-runs/{run_id}/void
POST /shared-cost-pools/{pool_id}/allocation-runs/{run_id}/post-cost-lines
GET  /shared-cost-pools/{pool_id}/allocation-runs
GET  /shared-cost-allocation-runs/{run_id}
```

Preview response should include:

- Pool snapshot.
- Policy snapshot.
- Candidate initiatives.
- Excluded initiatives.
- Basis values.
- Allocations.
- Exceptions.
- Reconciliation.
- Reporting impact.

### 6.5 Ledger and impact APIs

```text
GET /shared-cost-allocations
GET /shared-cost-allocations/export
GET /shared-costs/reporting-impact
GET /initiatives/{initiative_id}/shared-cost-allocations
```

Ledger filters should support year, period, scenario, category, pool, method,
initiative, workstream, business unit, and status.

## 7. Allocation Engine Rules

### 7.1 Reconciliation

Every approved run must satisfy:

```text
sum(allocated_amount) = pool_period_amount
```

The response should expose:

- `pool_amount`
- `allocated_amount`
- `unallocated_amount`
- `rounding_adjustment`
- `reconciled`

Manual amount mode should not normalize values unless the user chooses a
"scale to pool total" option. By default:

- If manual amounts equal pool total, approve is allowed.
- If manual amounts are less than pool total, show unallocated remainder.
- If manual amounts exceed pool total, block approval.

Fixed percentage mode must validate:

```text
sum(percentages) = 100.0000
```

### 7.2 Basis selection

The basis selection should come from configured financial engine definitions:

- Revenue-class metric definitions for revenue weighting.
- Non-revenue benefit metric definitions for value/benefit weighting.
- Savings-class metric definitions for savings weighting.
- Cost categories for direct-cost weighting.
- Numeric metric definitions or attributes for headcount/FTE/workload weighting.

Legacy `gm_uplift_base` and `revenue_uplift_base` should remain only as fallback
compatibility for older seeded data.

### 7.3 Missing data policy

Do not silently equal-split when a selected driver has no data unless the policy
explicitly says so.

Supported behaviors:

| Behavior | Use case |
|---|---|
| Fail preview | Finance wants clean basis data before allocation. |
| Treat as zero | Initiative should receive no allocation without driver data. |
| Equal split fallback | Small pools where missing driver data should not block. |

The preview must clearly label whichever behavior was applied.

### 7.4 Candidate dimensions

Targets should support:

- Explicit initiative list.
- Workstream.
- Business unit.
- Country/region.
- Tag.
- Stage/gate.
- Owner.
- RAG status.
- Initiative attribute.
- Cost category participation.
- Benefit metric participation.

Longer term, policies can allocate to dimensions first, then cascade to
initiatives:

```text
Pool -> business unit share -> workstream share -> initiative share
```

That should be a later phase unless Finance requires multi-step allocations in
the first release.

## 8. Reporting and Dashboard Impact

### 8.1 Reporting policy

Add tenant-level and pool-level settings:

| Setting | Meaning |
|---|---|
| `include_in_executive_control_tower` | Whether locked allocations affect Executive Control Tower. |
| `include_in_dashboard_executive_brief` | Whether dashboard brief includes allocated burden. |
| `include_in_portfolio_financials` | Whether Portfolio Financials includes allocated shared costs as a separate layer. |
| `include_in_initiative_financials` | Whether initiative pages show allocated burden. |
| `include_in_bankable_plan` | Whether bankable plan/waterline subtracts allocated shared costs. |
| `posting_mode` | Report-only, post cost lines, or both. |

Default should be conservative:

```text
Executive burdened views include locked shared-cost allocations.
Direct initiative economics remain direct-only unless Finance opts into posting.
Bankable plan excludes shared allocations until Finance explicitly enables it.
```

### 8.2 Impact matrix

| Surface | Target behavior |
|---|---|
| `/shared-costs` | Source of truth for pools, policies, previews, approvals, runs, and allocation ledger. |
| `/reports/control-tower` | Uses latest locked runs; shows allocated costs, burdened costs, and net after allocation. |
| Dashboard executive brief | Shows allocated costs and net after allocation with a link to the driving run. |
| Portfolio Financials | Adds optional layer/filter for allocated shared costs; keeps direct costs separate. |
| Initiative detail Financials | Shows an "Allocated Shared Costs" section with read-only burden lines and run lineage. |
| Bankable plan/waterline | Configurable: direct-only by default, burdened bankable value when enabled. |
| Value bridge | Adds configurable bridge rows for allocated shared costs when reporting setting is enabled. |
| Board/investor exports | Include a footnote for allocation policy, latest locked run, and whether allocations are included. |

### 8.3 Dashboard explainability

Any dashboard number affected by shared costs should offer a drill path:

```text
Allocated Costs -> pool -> run -> policy -> initiative allocation lines
```

The UI should show:

- Latest locked run date.
- Policy name and version.
- Pool total.
- Candidate count.
- Allocation method.
- Exceptions count.

## 9. UI Design Plan

The revamp should follow the existing Transmuter executive design direction:
deep navy, steel blue, light blue accents, white/grey surfaces, square geometry,
thin dividers, restrained shadows, dense executive layouts, and no purple
palette.

### 9.1 Overview

Top area:

- Total active pool amount.
- Allocated amount.
- Unallocated amount.
- Latest locked run date.
- Exceptions requiring Finance review.
- Reporting impact status.

Main layout:

- Left: pool list with category, period, amount, status.
- Right: selected pool summary, current policy, latest run, and impact.

### 9.2 Pool editor

Use selectors, segmented controls, and numeric inputs:

- Cost category select.
- Scenario select.
- Period grain segmented control.
- Monthly/quarterly amount grid.
- Reporting treatment segmented control.
- Recurring toggle.
- Status selector.

### 9.3 Policy builder

Use a stepper:

1. Scope.
2. Basis.
3. Weights/caps.
4. Preview.
5. Approval.

No raw JSON fields should be visible for normal users.

### 9.4 Preview table

Columns:

- Initiative.
- Workstream.
- Business unit.
- Basis value.
- Share.
- Plan allocation.
- Actual/forecast allocation.
- Exceptions.
- Explanation.

Include a right-side reconciliation panel:

- Pool amount.
- Allocated amount.
- Rounding adjustment.
- Unallocated amount.
- Approval readiness.

### 9.5 Reporting impact panel

Show before/after values:

- Benefits.
- Direct costs.
- Allocated costs.
- Burdened costs.
- Net before allocation.
- Net after allocation.
- Bankable value impact, if enabled.

## 10. Security, RBAC, and RLS

Prahari review is mandatory because this work touches RLS, financial data, and
reporting semantics.

Rules:

- Read access follows existing portfolio visibility rules.
- Pool/policy/run management should require transformation-office or Finance
  configuration permission.
- Initiative owners may view allocations that affect their initiatives, but
  should not see unrelated pool allocations unless they have portfolio access.
- RLS must enforce tenant isolation for all new tables.
- Posted generated cost lines must preserve tenant_id and source lineage.
- External LLM calls are not needed for this feature. If a future explanation
  assistant is added, do not send PII or raw user names to LLMs.

## 11. Implementation Phases

### ACME demo scenario pack

Use these scenarios as concrete examples for requirements, seeded data, UI
acceptance, and demo validation.

Current seeded proof:

| Pool | Year | Category key | Method | Plan | Actual | Initiatives |
|---|---:|---|---|---:|---:|---|
| Group technology platform allocation | 2026 | software | Benefit weighted | `$600K` | `$540K` | TRN-001 North Asia Revenue Acceleration, TRN-002 ERP Consolidation & Automation, TRN-004 Back-Office Offshoring - Finance & HR |

Canonical ACME 10-initiative scenarios for the revamped feature:

| Scenario | Pool | Category | Suggested method | Candidate initiatives | Acceptance focus |
|---|---|---|---|---|---|
| Platform burden | Group technology and data platform | Software / Licenses | Benefit weighted by Gross Margin Uplift or technology-tag weighted | ENT-002 Finance Process Automation, ENT-005 Enterprise Data Platform, ENT-006 Pricing & Discount Optimization, ENT-009 Supply Chain Control Tower, ENT-010 AI Service Desk Automation | Shows metric-backed allocation from the configurable financial engine. |
| PMO governance burden | Transformation PMO and benefits office | People Support | Equal split across active bankable initiatives, or value weighted after benefits mature | All 10 ACME initiatives, optionally excluding ENT-001 when it represents the PMO itself | Shows central governance cost without hiding it in one direct cost line. |
| Change/adoption burden | Shared change and training support | Training / Change Management | Manual amount or impacted-headcount weighted | ENT-002 Finance Process Automation, ENT-004 Back-office Finance & HR Offshoring, ENT-005 Enterprise Data Platform, ENT-010 AI Service Desk Automation | Tests manual amount validation, explainability, and adoption-cost allocation. |
| Advisory/vendor burden | Central transformation advisory support | External Consultants | Fixed percentage by workstream | ENT-005 Enterprise Data Platform, ENT-008 Procurement Vendor Consolidation, ENT-009 Supply Chain Control Tower | Tests fixed percentage validation and workstream/dimension targeting. |

Demo policy defaults:

- Shared costs remain separate from direct initiative cost lines.
- Executive Control Tower includes allocated burden from locked runs.
- Portfolio Financials remains direct-only unless the burdened layer is enabled.
- Bankable plan remains direct-only unless Finance enables burdened bankable
  reporting.
- Any burdened dashboard number should drill back to pool, policy, run, and
  allocation basis.

### Phase 0: Netra/Vishwa requirements closure

Deliverables:

- Confirm Finance operating policy for report-only versus posted allocations.
- Confirm whether bankable plan should include shared cost burden by default.
- Confirm required allocation methods for first release.
- Confirm period granularity required for ACME demo and production tenants.
- Confirm RBAC role names for Finance Lead versus transformation office.

Exit criteria:

- Approved requirements issue.
- Decision log attached to issue.
- No schema work starts until these decisions are recorded.

### Phase 1: Vastu architecture and schema

Deliverables:

- Migration for extended pool, rule, run, allocation fields.
- New tables for pool periods, structured targets, structured weights,
  reporting settings, exceptions, and audit events.
- Backfill migration from current `category_key`, filters JSON, and plan/actual
  scenarios.
- RLS policies for all new tables.
- Repository methods for the new model.

Exit criteria:

- Migration applies locally and on seeded database.
- Existing Shared Costs API remains compatible.
- Tenant isolation tests cover new tables.
- Prahari review completed for RLS and generated cost-line linkage.

### Phase 2: Karya backend allocation engine

Deliverables:

- Preview service that has no database side effects except optional preview run
  storage.
- Approval and lock services.
- Structured basis resolver using configurable financial engine data.
- Allocation calculators for equal split, fixed percentage, manual amount,
  benefit weighted, revenue weighted, savings weighted, direct cost weighted,
  headcount/FTE weighted.
- Exception model for missing basis, invalid weights, exclusions, caps, and
  reconciliation.
- Reporting-impact service.
- Optional cost-line posting service with lineage to run/allocation.

Exit criteria:

- Unit tests cover all allocation methods.
- Decimal-only money arithmetic verified.
- Manual amount and fixed percentage validation cannot silently misallocate.
- Reports only consume locked runs unless explicitly asked for preview impact.

### Phase 3: Rupa frontend revamp

Deliverables:

- Replace current single-page form with tabbed Finance workbench.
- Add pool editor with financial-engine-backed selectors.
- Add policy builder with structured target filters and basis selection.
- Add preview/reconciliation table.
- Add run approval, lock, void, and audit display.
- Add allocation ledger.
- Add reporting impact panel.
- Add initiative drill links.

Exit criteria:

- No raw JSON required for normal configuration.
- UI works in light and dark themes.
- All interactive controls have ARIA labels.
- Text fits across desktop and mobile viewports.
- Design matches existing A&M-inspired Transmuter direction.

### Phase 4: Reporting integration

Deliverables:

- Executive Control Tower reads latest locked runs by period/scenario.
- Dashboard executive brief shows run lineage and stale-run warnings.
- Portfolio Financials has direct-only versus burdened toggle.
- Initiative Financials shows read-only allocated burden section.
- Bankable plan/waterline honors tenant setting for shared cost inclusion.
- Board/investor exports include allocation policy footnotes.

Exit criteria:

- Direct costs and allocated costs remain separately visible.
- Report-only default does not create direct initiative cost lines.
- Optional posting creates traceable generated cost lines and avoids duplicates.
- Bankable plan impact is explicit and configurable.

### Phase 5: Aksha acceptance and seeded data

Deliverables:

- Seed deterministic shared-cost pools, categories, policies, preview exceptions,
  and locked runs.
- Real API tests against running API and seeded Supabase data.
- Browser UI tests against real Angular app and real API.
- Cross-tenant RLS tests.
- Regression tests for existing Executive Control Tower fields.

Acceptance scenarios:

1. Finance creates an annual software pool from engine cost categories.
2. Finance builds a benefit-weighted policy from a configurable metric.
3. Finance previews allocations, sees basis values and reconciliation.
4. Finance approves and locks the run.
5. Executive Control Tower shows allocated costs from the locked run.
6. Dashboard executive brief shows net after allocation and links to Shared
   Costs.
7. Initiative detail shows read-only allocated burden.
8. Portfolio Financials can switch between direct-only and burdened view.
9. Bankable plan excludes shared costs by default.
10. Enabling bankable shared-cost inclusion changes bankable net value with a
    visible explanation.
11. Manual amount mode blocks approval when total exceeds the pool.
12. Fixed percentage mode blocks approval when percentages do not equal 100%.
13. A user from another tenant cannot read or mutate shared-cost data.

Exit criteria:

- Acceptance tests reset or isolate sample data deterministically.
- No smoke-only acceptance.
- No manually created browser state dependency.
- `NUMERIC(15,4)`/Decimal/string-money standards verified.

### Phase 6: Sthira deploy readiness

Deliverables:

- Migration runbook.
- Backfill validation query set.
- Release notes.
- Rollback plan.
- Dev deployment validation.
- Production promotion checklist.

Exit criteria:

- Dev seeded tenant validates full flow.
- Existing production pools migrate without data loss.
- Production reports match pre-migration numbers until a locked new run is
  created or settings are changed.

## 12. Proposed GitHub Issue Breakdown

Create one parent feature issue:

```text
Revamp Shared Costs into configurable allocation engine
```

Child issues:

| Issue | Labels | Scope |
|---|---|---|
| Netra requirements for Shared Costs operating model | `type: feature`, `agent: netra`, `status: triage` | Resolve report-only/posting, bankable plan inclusion, first-release methods. |
| Vastu schema and API architecture for shared-cost allocation engine | `type: feature`, `agent: vastu` | Data model, API contracts, RLS, migration/backfill design. |
| Chitra Shared Costs Finance workbench design | `type: feature`, `agent: chitra` | UX flows, tabs, policy builder, preview table, impact panel. |
| Karya backend allocation preview/approval engine | `type: feature`, `agent: karya` | Services, repositories, calculators, validation, lineage. |
| Rupa Shared Costs frontend revamp | `type: feature`, `agent: rupa` | Angular workbench implementation. |
| Prahari RLS and financial data security review | `type: task`, `agent: prahari` | RLS, RBAC, generated cost-line lineage. |
| Aksha real API and UI acceptance for Shared Costs | `type: feature`, `agent: aksha` | Seeded acceptance tests and browser flows. |
| Sthira deployment and migration readiness | `type: task`, `agent: sthira` | Dev deploy, prod promotion checklist, rollback. |

## 13. Open Decisions

These need founder/Finance confirmation before implementation:

| Decision | Recommended default |
|---|---|
| Should shared costs post generated cost lines into initiative financials? | No by default. Keep report-only unless Finance opts in. |
| Should bankable plan subtract allocated shared costs? | No by default. Add explicit tenant setting. |
| Should zero-basis allocations fall back to equal split? | No by default. Fail preview unless policy allows fallback. |
| Should manual amount mode scale amounts to pool total? | No by default. Require exact reconciliation or show unallocated remainder. |
| Should initiative owners see pool totals? | Only for pools allocated to their initiatives unless they have portfolio access. |
| Should historical locked runs be immutable? | Yes. New data creates a new run/version. |
| Should actual allocations be separate from plan allocations? | Yes. Scenario and period should be explicit. |

## 14. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Finance users do not trust allocation math. | Show basis values, formulas, shares, and reconciliation on every run. |
| Allocations distort initiative-owner accountability. | Keep direct and allocated costs separate, with report-only default. |
| Bankable plan becomes confusing. | Default to direct-only bankable values and show a visible burdened toggle/setting. |
| Legacy seeded data uses old financial entries. | Backfill to configured metrics where possible and retain compatibility fallback. |
| RLS leaks portfolio allocation details. | Add Prahari review and cross-tenant tests for every new table/API. |
| Manual allocations create unreconciled dashboards. | Block approval unless reconciliation rules pass. |
| Generated cost lines duplicate on rerun. | Use source run/allocation lineage and idempotency keys. |

## 15. Definition of Done

The revamp is complete when:

- Shared Costs uses configured financial scenarios, cost categories, and metric
  definitions.
- Finance can configure pools and policies without raw JSON.
- Allocation preview explains candidates, basis, shares, exceptions, and
  reconciliation.
- Reports consume locked runs only.
- Dashboards and reports show direct costs and allocated shared costs
  separately.
- Bankable plan treatment is tenant-configurable and visible.
- Optional posting to cost lines is traceable and idempotent.
- RLS and RBAC are reviewed and tested.
- Real API and browser acceptance tests cover seeded shared-cost flows.
- Existing report totals remain stable after migration unless settings or locked
  runs are changed.
