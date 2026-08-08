# Clean Configurable Financial Engine

Status: Canonical architecture contract
Current feature: #491
Baseline release: `v0.4.0`

## Decision

Transmuter uses a tenant-configurable metric engine. Recommended metrics are
installed as tenant-owned starter templates exactly once when a tenant is
created. A starter metric is not a permanently protected platform object: an
administrator may edit it or permanently delete it through the same governed,
dependency-aware workflow used for any other tenant metric.

Existing tenant financial history is durable. Catalogue upgrades must preserve
metric IDs and references unless a tenant explicitly completes a reviewed
migration. Re-running registration, billing provisioning, or environment
bootstrap must never recreate a starter metric that a tenant intentionally
deleted.

The release tag `v0.4.0` preserves the pre-refactor implementation.

## Source Inputs

- `productupgrade.md`
- `productupgrade_addendum.md`
- `Initiative_Portfolio_Anonymised.xlsx`
- Live Supabase schema `transmuter`
- Current backend financial service, router, repository, and domain contracts
- Current Angular financial, admin, create-flow, dashboard, and reporting code

Corrections applied to the recommendation set:

- DDL targets schema `transmuter`, not `public`.
- `organizations.currency` does not exist; reporting currency must be added as a
  reporting setting, separate from Stripe billing currency.
- Benefit maturity is partly present through `initiatives.benefit_confidence`
  and `initiatives.realization_status`; the refactor should surface and map
  those concepts instead of creating a duplicate maturity field.
- Workbook reload is canonical after reset.

## Target Data Model

All new tenant data tables must include `tenant_id uuid not null`, RLS, and
tenant-scoped indexes. Admin/config writes should be restricted at both API and
RLS layers to transformation-office users unless explicitly read-only.

Core tables:

- `financial_metric_definitions`
  Defines tenant metrics such as revenue uplift, gross margin, GM uplift,
  cost savings, ROI, and custom metrics.
  Required semantics: `key`, `label`, `value_type`, `unit`, `direction`,
  `aggregation`, `rollup_type`, `is_benefit`, `benefit_class`,
  `cost_behavior`, `formula`, `formula_inputs`, `precision`,
  `display_order`, `applies_to`, `validation`, `origin`, `catalog_version`,
  optional `semantic_role`, formula evaluation grain, active flag, and audit
  columns. `is_system` is reserved for genuinely platform-invariant records;
  financial starter metrics are tenant-owned.

- `financial_scenarios`
  Defines tenant lanes such as baseline, plan base, plan high, actual, downside,
  or forecast. Scenario keys are data, not code literals.

- `financial_benefit_lines`
  Initiative-level named benefit lines. A line references a metric definition
  but has its own name, description, impact type, timing, confidence, attributes,
  show-in-summary flag, and display order. This maps the workbook Benefits sheet
  directly.

- `financial_cost_lines`
  Keep the existing concept, but extend it with line attributes and phasing
  metadata. Costs remain named initiative-level lines.

- `financial_metric_values`
  Replace the current custom-metric-only table with the primary monthly value
  store. Each row is initiative, metric definition, optional benefit line,
  scenario, year, month, value, status/signoff metadata, notes, and audit
  columns. Month is the only stored grain.

- `financial_bridge_rows`
  Tenant-configurable value bridge rows. Reports render these rows dynamically
  rather than relying on fixed `ValueBridgeCase` fields.

- `financial_attribute_definitions`
  Tenant-configurable registry for benefit-line and cost-line attributes. This
  lets admins define reusable text, numeric, currency, percent, date, select, or
  boolean fields without hardcoding workbook-specific columns into the product.

- `initiative_business_units`
  Many-to-many mapping so initiatives can span multiple business units
  independently of workstream.

- `stage_gate_definitions`
  Tenant-configurable gate definitions. Seed the default five-gate model from
  the workbook and remove hard limits to gates 1 and 2.

Organization-level reporting settings:

- `fiscal_year_start_month`
- `reporting_currency`
- financial governance settings, including plan lock gate, actual signoff, and
  stage/maturity mappings

Existing structures to remove or demote:

- hardcoded financial metric columns on `financial_entries`
- code-level `FinancialScenario = Literal["base", "high", "actual"]`
- fixed `FinancialEntryRow` metric fields as the primary API contract
- frontend hardcoded `METRICS`
- fixed `ValueBridgeCase` shape as the primary report contract
- old `financial_metric_values` shape with `value_base`, `value_high`,
  `value_actual`

## API Contract Direction

Admin/config APIs:

- list/create/update/deactivate metric definitions
- preview dependency-aware metric deletion and permanently delete any unused
  tenant-owned metric only after exact-key confirmation
- list/create/update/deactivate scenarios
- get/update reporting settings
- list/update bridge rows
- list/update gate definitions
- validate formulas

Initiative APIs:

- get/update initiative financial grid as definitions, scenarios, benefit lines,
  cost lines, and monthly values
- generate or update phasing rules for cost and benefit lines
- manage financial selections by metric definition and cost/benefit lines
- export/import workbook-driven financial data using definition keys

Portfolio/reporting APIs:

- portfolio financials by granularity, fiscal year, scenario, workstream,
  business unit, stage/gate, tag, metric, and as-of date where relevant
- portfolio value bridge from configurable bridge rows
- value ramp dashboard from completion dates and selected basis
- in-year value dashboard with gate filters and optional unattributed actuals
- benefit tracking and waterline reports from the new model

## Formula Rules

Formula evaluation must use Decimal arithmetic only. Do not use Python `eval`,
JavaScript `eval`, SQL dynamic expression execution, or untrusted expressions.

Required behavior:

- supported operators: `+`, `-`, `*`, `/`, parentheses, metric keys
- formula inputs must be validated against active metric definitions
- dependency cycles must be rejected before saving definitions
- missing inputs and divide-by-zero return an explicit not-computable status,
  not a financial zero
- formula metrics are read-only in entry grids
- percentages should be recomputed from rolled-up inputs at each grain, not
  averaged unless the tenant explicitly chooses average aggregation
- annual formulas aggregate their period inputs by initiative, scenario, and
  year before injecting an annual baseline once
- computed outputs must satisfy the definition's validation range

## Default Financial Metric Catalogue

The current starter catalogue for a newly created tenant is versioned and
installed once. Entered metrics are:

| Key | Label | Meaning |
|---|---|---|
| `annual_revenue_baseline` | Annual Revenue Baseline | Original annual revenue. |
| `annual_gross_profit_baseline` | Annual Gross Profit Baseline | Original annual gross-profit amount. |
| `revenue_uplift` | Revenue Uplift | Incremental revenue. |
| `gross_profit_uplift` | Gross Profit Uplift | Incremental gross profit. |
| `cost_savings` | Cost Savings | Savings not already represented as gross-profit uplift. |

Derived annual metrics are:

```text
target_revenue = annual_revenue_baseline + revenue_uplift
target_gross_profit = annual_gross_profit_baseline + gross_profit_uplift
target_cogs = target_revenue - target_gross_profit
revenue_growth_pct = revenue_uplift / annual_revenue_baseline * 100
baseline_gross_margin_pct = annual_gross_profit_baseline / annual_revenue_baseline * 100
target_gross_margin_pct = target_gross_profit / target_revenue * 100
gross_margin_change_pp = target_gross_margin_pct - baseline_gross_margin_pct
target_cogs_pct = target_cogs / target_revenue * 100
```

The catalogue does not seed a generic ROI metric. ROI requires a governed
definition of eligible costs, benefit basis, measurement horizon, and
annualization. Gross profit is a currency amount; gross margin is a percentage.

Catalogue installation has a durable tenant-scoped installation record. It is
not a missing-key repair loop. An explicit future restore action may offer
recommended defaults, but it must disclose conflicts and never overwrite a
tenant metric.

## Metric Deletion Contract

Metric deletion is a governed destructive action, not a generic table delete.
A tenant-owned metric is deletable only when no surviving tenant record depends
on it. `default_catalog`, `legacy_default`, and `tenant` provenance all use the
same safety policy.

| Reference | Metric-side action | Deletion treatment |
|---|---|---|
| `financial_benefit_lines` | `RESTRICT` | Blocks and identifies benefit line and initiative. |
| `financial_metric_values` | `RESTRICT` | Blocks and identifies initiative and period. |
| `initiative_financial_scope` | `RESTRICT` | Blocks even when the scope row is inactive. |
| `financial_initiative_annual_baselines` | `RESTRICT` | Blocks and identifies initiative and year. |
| `initiative_financial_selections` | `RESTRICT` through normalized metric ID | Blocks legacy key-based initiative usage. |
| `financial_config_items` | `RESTRICT` through normalized metric ID | Blocks compatibility configuration usage. |
| `financial_metric_formula_dependencies` | `RESTRICT` on input metric | Blocks direct and `baseline_` formula references, including inactive formulas. |
| `financial_bridge_metric_memberships` | `RESTRICT` | Blocks active and inactive value-bridge membership. |
| `shared_cost_allocation_rules` | `RESTRICT` | Prevents an allocation driver from changing silently. |
| `shared_cost_allocations` | `RESTRICT` | Preserves the metric used by historical allocation evidence. |
| `financial_tenant_annual_baselines` | `CASCADE` | Allowed cleanup, but the preview must disclose its count. |

Formula dependencies and bridge membership are normalized and maintained by
database triggers while the public configuration response retains formula keys
and bridge metric-ID arrays. Legacy selection and compatibility rows retain
their text keys but also store a tenant-composite metric ID.

The API contract is:

```text
GET    /admin/financial-engine/metrics/{metric_id}/deletion-impact
DELETE /admin/financial-engine/metrics/{metric_id}
       body: { "confirmation_key": "immutable_metric_key" }
```

The preview groups blocker counts and a bounded list of actionable references.
The delete function locks the metric, recomputes impact in the same PostgreSQL
transaction, validates the immutable key, and deletes only when the current
impact is safe. A database trigger rejects direct authenticated deletes that do
not pass through this confirmed workflow. Missing and cross-tenant metric IDs
both return `404`; blockers return `409` with the refreshed impact.

Tenant-facing create input does not contain `is_system`, catalogue provenance,
or catalogue version. The service creates tenant-origin metrics, and database
controls prevent a direct authenticated insert from claiming platform or
catalogue provenance. API capability checks and RLS both permit financial
configuration only to `transformation_office`, `tenant_admin`, and
`finance_lead`.

## Workbook Reload

`Initiative_Portfolio_Anonymised.xlsx` becomes the deterministic reload fixture
after reset.

Required mappings:

- Initiative Summary: initiatives, workstreams, business units, owners, tags,
  stage/gate, RAG, priority, planned completion, baseline summary values.
- Charter Details: charter fields, value logic, context/problem, workstream lead
  and sponsor once supported.
- Benefits: named benefit lines, lanes to scenarios, denomination to value type,
  benefit type/class, confidence, timing, P&L line, monthly values.
- Costs: named cost lines, plan/actual lanes, plan mode, amount, date range,
  lump month, inflation, category, P&L line, service line, impact type, monthly
  values.
- Financial Summary: annual validation totals and baseline values.
- KPIs, milestones, risks, action items, and status updates: load into existing
  domain tables where possible.
- Dashboards: validate value ramp and in-year value reports.

Reload must be idempotent for a selected tenant and must be able to reset the
tenant portfolio predictably.

## Frontend Contract

The frontend should not infer financial rows from hardcoded names. It should
render from API-provided definitions, scenarios, lines, values, bridge rows, and
settings.

Required surfaces:

- Admin Metric Builder
- scenario and reporting settings management
- dynamic initiative financial grid
- benefit and cost line management with phasing controls
- create/edit initiative dynamic financial scope
- multi-BU initiative assignment
- dynamic portfolio financials and value bridge
- value ramp, in-year value, waterline, and benefit tracking views

All frontend work must follow `team/DESIGN_SYSTEM.md`: dense executive layout,
CSS variable tokens, light/dark support, accessible interactive controls, and no
purple/orb SaaS styling.

## Security And Review

Prahari review is required before merge for:

- new RLS policies
- destructive tenant reset/reload paths
- formula validation
- workbook import trust boundaries
- actuals signoff and role-sensitive reporting

## Implementation Sequence

1. Schema and bootstrap seeds.
2. Backend domain/repository/service/router replacement.
3. Workbook reload and deterministic seed.
4. Frontend dynamic admin and grid.
5. Portfolio dashboards and reporting cutover.
6. Real API and browser acceptance.
7. Deploy readiness and release notes.

The pre-refactor implementation can be removed as each area is replaced. Avoid
maintaining parallel legacy contracts unless needed temporarily for a single PR
to keep the app buildable.

## Release Notes

### Clean Configurable Financial Engine

This release is a breaking financial data model change. The pre-refactor code
baseline is tagged as `v0.4.0`; rolling back code should use that tag.

What changed:

- Financial metrics, scenarios, bridge rows, and line attributes are now tenant
  configuration rather than hardcoded application assumptions.
- Initiative financial values are stored as monthly configurable metric values
  by metric definition, scenario, and optional benefit line.
- Benefit lines and cost lines support phasing metadata and free-form
  attributes governed by tenant attribute definitions.
- Stage gates, approval criteria, and dashboard stage reporting are
  tenant-configurable.
- Initiatives can map to multiple business units.
- Portfolio financials include dynamic value bridge rows, in-year value, and a
  cumulative run-rate value ramp.
- Normal tenant onboarding is blank; tenants configure business units,
  workstreams, financial metrics, scenarios, gates, and criteria before creating
  or importing initiatives.

Operational impact:

- Existing demo/portfolio financial data is reloadable, not migrated in place.
- Destructive reloads must use `scripts/load_portfolio_workbook.py
  --confirm-reset`.
- Run `scripts/load_portfolio_workbook.py --dry-run` before reset/reload to
  confirm required tenant metrics, scenarios, and stage gates exist.
- Rollback after migrations/data reload requires restoring the target Supabase
  database from a pre-refactor backup; code rollback to `v0.4.0` alone is not
  enough after destructive reset.
