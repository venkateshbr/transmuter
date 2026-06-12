# Clean Configurable Financial Engine

Status: Draft architecture contract for issue #228
Parent: #227
Baseline release: `v0.4.0`

## Decision

Transmuter will replace the current hardcoded financial model with a clean
tenant-configurable metric engine. Current local/seed financial and initiative
data may be deleted and reloaded. There is no requirement for a v1/v2 dual-write
period, no legacy financial response compatibility, and no migration of existing
demo data except through the new workbook reload path.

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
  `display_order`, `applies_to`, `validation`, active/system flags, audit
  columns.

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
- divide-by-zero returns null/blank, not an exception in report rendering
- formula metrics are read-only in entry grids
- percentages should be recomputed from rolled-up inputs at each grain, not
  averaged unless the tenant explicitly chooses average aggregation

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

The current implementation can be removed as each area is replaced. Avoid
maintaining parallel legacy contracts unless needed temporarily for a single PR
to keep the app buildable.
