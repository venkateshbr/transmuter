# Admin Financial Configuration User Guide

Last updated: 2026-06-19

Audience: tenant admins, transformation office users, finance leads, benefits
controllers, and implementation teams configuring a new tenant.

This guide explains the **Admin -> Financial Configuration** menu in Transmuter,
including the configurable financial metric engine, annual baselines, scenarios,
value bridge rows, line attributes, reporting settings, and cost categories.

It also explains how these settings are implemented in the current system, how
they relate to initiative financial entry and portfolio reporting, what breaks
when they are missing or configured incorrectly, and how the ACME tenant is
configured as a worked example.

Related guides:

- `docs/user-guides/acme-transformation-value-demonstration-guide.md`
- `docs/user-guides/acme-transformation-office-detailed-setup-and-demo-guide.md`
- `docs/user-guides/financial-engine-end-to-end-walkthrough.md`
- `docs/team/CLEAN_CONFIGURABLE_FINANCIAL_ENGINE.md`

---

## 1. What This Menu Controls

The Admin Financial Configuration menu controls the tenant's financial model.
It answers these questions:

| Question | Configuration area |
|---|---|
| What financial metrics can initiatives use? | Financial Configuration Engine -> Metric Definitions |
| What is the original business baseline? | Financial Configuration Engine -> Annual Baselines |
| Which lanes should be tracked? | Financial Configuration Engine -> Scenarios |
| How should value be presented to executives? | Financial Configuration Engine -> Value Bridge Rows |
| Which extra fields should benefit and cost lines capture? | Financial Configuration Engine -> Line Attribute Registry |
| Which cost categories can cost lines use? | Financial Configuration Engine -> Cost Categories |
| What fiscal calendar and currency should reports use? | Reporting Settings |

There is now one active configuration layer in this screen:

**Financial Configuration Engine**

- Tenant-scoped source of truth for metric definitions, scenarios, benefit
  lines, monthly metric values, formulas, annual baselines, cost categories,
  bridge rows, line attributes, and reporting settings.
- Cost lines are assigned to engine-owned cost categories. The category key is
  still stored for import/export and backward-compatible reporting, but the
  category definition is managed by the engine.
- Legacy calculation groups and metric rows are retained only as compatibility
  facades for old data paths and historical `financial_entries` views. Do not
  configure them as a second model for new tenants.

For a new tenant, configure only the Financial Configuration Engine. ACME and
Ishirock are the protected tenant examples; other sample tenants can be reset or
removed during cleanup if they are not needed for a release validation run.

---

## 2. Current Implementation Model

### 2.1 Primary tables and API contracts

Financial configuration is tenant-scoped. Every financial configuration table has
`tenant_id`, and API routes are scoped to the authenticated tenant.

Primary backend models live in:

- `apps/api/app/domain/financials.py`
- `apps/api/app/services/financial.py`
- `apps/api/app/repositories/financial.py`
- `apps/api/app/routers/financials.py`

Primary tables:

| Table | Purpose |
|---|---|
| `financial_metric_definitions` | Defines tenant metrics such as revenue uplift, gross margin uplift, cost savings, formulas, and custom drivers. |
| `financial_scenarios` | Defines lanes such as baseline, plan base, plan high, forecast, and actual. |
| `financial_tenant_annual_baselines` | Stores tenant-wide annual baseline values by metric and year. |
| `financial_initiative_annual_baselines` | Stores initiative-level baseline allocation by metric and year. |
| `financial_benefit_lines` | Stores named benefit lines under initiatives, tied to metric definitions. |
| `financial_metric_values` | Stores monthly values by initiative, metric, scenario, optional benefit line, year, and month. |
| `financial_cost_lines` | Stores initiative cost lines with category, plan amount, actual amount, period, and recurring flag. |
| `financial_cost_categories` | Defines tenant-owned cost categories used by cost lines, value bridge cost rows, and filters. |
| `financial_bridge_rows` | Defines report bridge rows and their metric/cost inputs. |
| `financial_attribute_definitions` | Defines reusable benefit-line and cost-line attribute names/types. |
| `initiative_financial_scope` | Stores the engine metric and cost category scope selected for each initiative. |
| `financial_config_groups` | Compatibility grouping for older calculation and metric row paths. Not the active engine. |
| `financial_config_items` | Compatibility items for older metric row and cost category paths. Not the active engine. |

### 2.2 Money handling

All money is handled as:

- PostgreSQL: `NUMERIC(15,4)`
- Python: `decimal.Decimal`
- API JSON: string values such as `"8350000.0000"`

This prevents floating-point rounding errors in financial reports.

### 2.3 Monthly values are the source of truth

The configurable engine stores financial values monthly. Quarterly and yearly
views are derived by aggregation.

The core shape is:

```text
initiative_id
+ metric_definition_id
+ optional benefit_line_id
+ scenario_id
+ year
+ month
+ value
```

This means:

- A metric definition says what the number is.
- A scenario says which lane it belongs to.
- A benefit line says which named business claim it supports.
- The year/month says where it lands in time.
- The value is the Decimal amount or percentage/number.

---

## 3. Recommended Configuration Sequence

For a new tenant, configure in this order:

1. **Reporting settings**
   - Fiscal year start month.
   - Reporting currency.

2. **Metric definitions**
   - Baseline metrics.
   - Benefit input metrics.
   - Formula metrics.

3. **Scenarios**
   - Baseline.
   - Plan Base.
   - Plan High.
   - Actual.
   - Optional Forecast.

4. **Annual baselines**
   - Tenant baseline year and values.

5. **Cost categories**
   - One-off implementation categories.
   - Recurring operating categories.

6. **Value bridge rows**
   - Revenue or commercial drivers.
   - EBITDA-effective benefits.
   - Recurring costs.
   - One-off costs.
   - Net value.

7. **Line attributes**
   - Finance owner, benefit owner, evidence source, P&L line, confidence,
     dependency, vendor, cost nature, or other tenant-specific fields.

8. **Initiative financial setup**
   - Add initiative baselines, benefit lines, monthly values, and cost lines.

9. **Governance**
   - Configure stage gates, gate criteria, bankable plan lock, and benefit
     validation expectations.

---

## 4. Reporting Settings

### What it controls

Reporting settings control portfolio financial presentation:

| Field | Meaning |
|---|---|
| Fiscal year start month | Month used by financial reporting and fiscal-year interpretation. |
| Reporting currency | Three-letter currency code displayed in reports. |

### Implementation

Reporting settings are stored on the tenant organization record and returned as
`FinancialReportingSettings`.

Admin API:

```text
PUT /admin/financial-engine/reporting-settings
```

Read API:

```text
GET /financial-engine-configuration
```

### Impact if not configured

The system defaults to:

| Setting | Default |
|---|---|
| Fiscal year start month | January |
| Reporting currency | USD |

If this is wrong for the tenant, portfolio totals may still calculate correctly,
but users may interpret periods incorrectly and see the wrong currency label.

### Best-practice guidance

Set the fiscal year and currency before importing data or creating initiatives.
Changing these later can confuse historical interpretation, even if stored
monthly values remain unchanged.

---

## 5. Financial Configuration Engine

Metric definitions are the heart of the configurable financial model.

### 5.1 Metric definition fields

| Field | Purpose | Example |
|---|---|---|
| Key | Stable machine key used in formulas and imports. | `gm_uplift` |
| Label | User-facing row name. | `Gross Margin Uplift` |
| Group key | Logical grouping. | `margin` |
| Value type | `currency`, `percent`, or `number`. | `currency` |
| Unit | Optional unit label. | `%`, `hours`, `USD/hour` |
| Direction | Whether increase or decrease is favorable. | `increase_good` |
| Aggregation | How monthly values roll up. | `sum`, `avg`, `last`, `formula` |
| Rollup type | Reporting rollup hint. | `benefit`, `total_cost` |
| Is benefit | Whether values count as benefits. | `true` |
| Benefit class | Benefit type. | `revenue`, `margin`, `savings`, `avoidance`, `other` |
| Formula | Expression for computed rows. | `gm_uplift / revenue_uplift * 100` |
| Formula inputs | Metric keys referenced by the formula. | `gm_uplift`, `revenue_uplift` |
| Precision | Decimal precision for display/calculation. | `4` |
| Applies to | Whether all initiatives inherit it or opt in. | `all`, `opt_in` |
| Active | Whether the metric appears and participates. | `true` |

### 5.2 Metric types

Use these metric patterns.

| Pattern | Typical configuration | Example |
|---|---|---|
| Baseline metric | `aggregation = last`, `is_benefit = false` | Annual Revenue Baseline |
| Benefit input metric | `aggregation = sum`, `is_benefit = true` | Gross Margin Uplift |
| Driver metric | `aggregation = sum`, often `is_benefit = false` or `benefit_class = revenue` | Revenue Uplift |
| Formula metric | `aggregation = formula`, `is_benefit = false` unless intentionally a computed benefit | Gross Margin % |
| Operational quantity | `value_type = number`, often `is_benefit = false` | Hours Saved |
| Unit economics input | `value_type = currency`, `aggregation = avg` or `last` | Margin per Hour |

### 5.3 Aggregation

Aggregation tells the platform how to turn monthly values into quarter, year, and
portfolio totals.

| Aggregation | Meaning | Best use |
|---|---|---|
| `sum` | Add monthly values. | Revenue uplift, GM uplift, cost savings, monthly costs. |
| `avg` | Average monthly values. | Rates or assumptions when averaging is meaningful. |
| `last` | Use the last available value in the period. | Baseline, headcount, run-rate snapshot, ending ARR. |
| `formula` | Compute at read time from other metrics. | Percentages, target values, ratios. |

Important: formula metrics are read-only. The backend rejects attempts to save
values for formula metric definitions.

### 5.4 Benefit flag and benefit class

`is_benefit` and `benefit_class` determine whether values are treated as value
delivery in portfolio rollups.

| Benefit class | Typical meaning | Reporting treatment |
|---|---|---|
| `revenue` | Top-line growth driver. | Shown as revenue/commercial uplift; should not automatically be treated as EBITDA. |
| `margin` | Incremental gross margin or EBITDA-effective margin value. | Counted as benefit in net value rollups. |
| `savings` | Recurring spend reduction or avoided spend. | Counted as benefit. |
| `avoidance` | Avoided future cost or risk-adjusted avoided spend. | Counted as benefit if accepted by Finance. |
| `other` | Tenant-specific value. | Counted as benefit, but should be carefully labeled. |

Current dashboard behavior:

- Configurable dashboard summary converts active non-formula benefit metrics into
  base/high/actual financial entries.
- Metrics with `benefit_class = revenue` are treated as revenue uplift.
- Other benefit metrics roll into gross margin/value style benefit buckets.
- Portfolio Initiative view excludes revenue-class metrics from EBITDA benefits
  total and uses non-revenue benefit metrics plus recurring costs for net
  run-rate.

### 5.5 Calculated values and formulas

Formula metrics are evaluated server-side. The system supports:

- `+`
- `-`
- `*`
- `/`
- parentheses
- metric keys
- baseline aliases such as `baseline_annual_revenue_baseline`

Formula validation:

- Formula must be present for `aggregation = formula`.
- Referenced metric keys must exist and be active.
- `formula_inputs` must match keys used in the formula if provided.
- Formula metrics cannot reference themselves.
- Formula dependency cycles are rejected.
- Formula rows are computed on read, not stored as user-entered values.
- Divide-by-zero currently results in a computed zero in rendered values.

Operational caution: because divide-by-zero currently renders as zero, Finance
users should treat a zero percentage on a formula row as a possible missing
denominator, not automatically as true zero performance. For example, a zero
`revenue_growth_pct` can mean no growth, but it can also mean the baseline
revenue denominator was not configured.

Example:

```text
gm_uplift_pct = gm_uplift / revenue_uplift * 100
```

Example with baseline:

```text
target_revenue = baseline_annual_revenue_baseline + revenue_uplift
```

### 5.6 Impact if metrics are missing or misconfigured

| Misconfiguration | Impact |
|---|---|
| No active benefit metrics | Initiative financials can still show costs, but benefit and net value reports are empty or zero. |
| Benefit metrics not marked `is_benefit` | Values may be entered but will not roll into portfolio benefits or value bridge correctly. |
| Revenue metric marked as EBITDA benefit without margin conversion | Executive net value can overstate EBITDA. |
| Formula references unknown key | Save fails with formula validation error. |
| Formula metric expected as input | Users cannot enter it because formula metrics are read-only. |
| Percentage metric uses `sum` instead of `formula` or carefully chosen `avg` | Portfolio percentages can be mathematically wrong. |
| Baseline metrics missing | Baseline cards, initiative portfolio reconciliation, and target/rate formulas are incomplete. |
| Inactive metrics used in formulas | Formula save or calculation can fail or return zero. |

---

## 6. Annual Baselines

Annual baselines store the original operating values for a tenant and optionally
for each initiative.

### 6.1 Tenant annual baselines

Tenant baseline values are configured in Admin:

```text
Admin -> Financial Configuration -> Annual Baselines
```

The admin chooses a fiscal year and enters values for active non-formula metrics.

API:

```text
GET /admin/financial-engine/annual-baselines
PUT /admin/financial-engine/annual-baselines
GET /financial-engine/annual-baselines
```

### 6.2 Initiative annual baselines

Initiative baselines allocate the tenant baseline down to initiatives. These are
used by initiative financial setup, initiative portfolio reconciliation, and
formula calculations with `baseline_` metric aliases.

### 6.3 ACME example

ACME uses FY26 as the baseline year.

| Baseline metric | FY26 value |
|---|---:|
| Annual Revenue Baseline | $20.0M |
| Annual Gross Margin Baseline | $9.0M |
| Baseline gross margin rate | 45.0% |

ACME then allocates the baseline across initiatives so the Initiative Portfolio
can reconcile initiative baseline totals back to the tenant baseline.

### 6.4 Impact if baselines are missing

| Missing baseline | Impact |
|---|---|
| Tenant baseline missing | Portfolio baseline cards do not appear or show zero. |
| Initiative baselines missing | Initiative Portfolio marks rows incomplete and reconciliation fails. |
| Formula baseline inputs missing | Formulas using `baseline_...` aliases compute zero or cannot produce meaningful values. |
| Wrong baseline year | Reports compare value against the wrong starting point. |

### 6.5 Best-practice guidance

Use baselines for original business state, not for transformation benefits.

Good baseline metrics:

- annual revenue baseline,
- annual gross margin baseline,
- baseline headcount,
- baseline cost to serve,
- baseline working capital,
- baseline cycle time,
- baseline service level.

Do not use baseline values as a place to store target benefits. Targets and
uplift belong in scenario metric values.

---

## 7. Scenarios

Scenarios define lanes for financial values.

### 7.1 Standard scenario set

Recommended starting set:

| Key | Label | Kind | Purpose |
|---|---|---|---|
| `baseline` | Baseline | `baseline` | Original operating reference. |
| `plan_base` | Plan Base | `plan` | Main approved plan. |
| `plan_high` | Plan High | `plan` | Upside case. |
| `actual` | Actual | `actual` | Realized/latest actual values. |
| `forecast` | Forecast | `forecast` | Optional current outlook. |

### 7.2 Current key dependencies

The current code is configurable, but several report paths still expect these
standard keys for base/high/actual interpretation:

```text
plan_base
plan_high
actual
baseline
```

If a tenant renames labels, that is fine. If a tenant changes keys, some
dashboard rollups, value bridge cases, and Initiative Portfolio scenario filters
may not populate as expected.

### 7.3 ACME example

ACME uses:

| Scenario | Use |
|---|---|
| Baseline | FY26 starting point. |
| Plan Base | Conservative board plan. |
| Plan High | Upside case. |
| Actual | Realized/latest actual values. |

In the ACME data:

- FY27 plan base is the ramp case.
- FY28 plan base is the run-rate target case.
- Plan high applies upside assumptions.
- Actuals sit below plan to demonstrate variance reporting.

### 7.4 Impact if scenarios are missing

| Missing or inactive scenario | Impact |
|---|---|
| `plan_base` | Base plan values do not roll into many portfolio views. |
| `plan_high` | High/upside columns and bridge case are empty. |
| `actual` | Actual toggles are unavailable or show zero. |
| `baseline` | Baseline scenario entry is unavailable. |
| No primary plan | Users may not know which plan lane is management-approved. |

### 7.5 Best-practice guidance

Keep plan, forecast, and actual separate. Do not overwrite plan values with
actuals. Use actuals to measure variance and forecast to represent the current
view if it differs from the approved plan.

---

## 8. Value Bridge Rows

Value bridge rows control how benefits, costs, and net value are presented in
value bridge reports.

### 8.1 Row fields

| Field | Meaning |
|---|---|
| Key | Stable bridge row key. |
| Label | User-facing row name. |
| Kind | `metric_set`, `cost_set`, `subtotal`, or `net`. |
| Metric inputs | Metric definitions included in the row. |
| Cost category inputs | Cost categories included in the row. |
| Sign | Positive or negative. |
| Display order | Row ordering. |
| Active | Whether the row is shown. |

### 8.2 Row kinds

| Kind | Meaning | Example |
|---|---|---|
| `metric_set` | Sum selected metrics by scenario. | Gross Margin Uplift |
| `cost_set` | Sum selected cost categories. | Recurring Costs |
| `subtotal` | Presentation row for grouped values. | Total Benefits |
| `net` | Calculated net row. | Net Value |

### 8.3 ACME example

ACME bridge rows are configured as:

| Bridge row | Kind | Sign | Inputs |
|---|---|---:|---|
| Revenue Uplift | Metrics | + | Revenue Uplift |
| Gross Margin Uplift | Metrics | + | Gross Margin Uplift |
| Cost Savings | Metrics | + | Cost Savings |
| Recurring Costs | Costs | - | Software, maintenance, labor |
| One-off Costs | Costs | - | Implementation, technology tooling, training/change |
| Net Value | Net | + | Calculated |

Recommended executive interpretation:

```text
EBITDA-effective net run-rate
= Gross Margin Uplift + Cost Savings - Recurring Costs
```

One-off costs should be shown for investment and payback analysis, but not mixed
into recurring EBITDA run-rate unless the tenant explicitly wants a net-after-
investment view.

### 8.4 Impact if bridge rows are missing

| Missing bridge row | Impact |
|---|---|
| Benefit metric rows | Value bridge does not explain benefit drivers. |
| Cost rows | Cost burden is hidden or net value appears overstated. |
| Net row | Executives cannot see clear net value. |
| Wrong metric IDs | Values show zero even when initiative data exists. |
| Wrong cost category selections | Cost rows show zero or omit costs. |

### 8.5 Best-practice guidance

Build bridge rows in management language, not table language. A CFO or steering
committee should be able to read the bridge without knowing the implementation.

Good bridge rows:

- Revenue Uplift,
- Gross Margin Uplift,
- Cost Savings,
- Working Capital Release,
- Recurring Costs,
- One-off Investment,
- Net Run-rate Value,
- Net After Investment.

Avoid double-counting. If revenue uplift is already converted into GM uplift,
do not add both to EBITDA net value.

---

## 9. Line Attribute Registry

Line attributes define reusable metadata for benefit and cost lines.

### 9.1 Attribute fields

| Field | Meaning |
|---|---|
| Key | Stable machine key. |
| Label | User-facing field name. |
| Applies to | `benefit_line` or `cost_line`. |
| Value type | `text`, `number`, `currency`, `percent`, `date`, `select`, `boolean`. |
| Options | Allowed values for select attributes. |
| Required | Whether users should provide it. |
| Active | Whether it is available. |

### 9.2 Current implementation note

Benefit-line attributes are persisted on each benefit line in the `attributes`
object.

Cost-line attribute definitions can be registered. The current public cost-line
API model does not yet expose cost-line instance attributes in the same complete
way, so treat cost-line attributes as a configuration registry until the cost
line entry UI/API fully captures those values.

### 9.3 Recommended attributes

For benefit lines:

- Benefit owner,
- Finance validator,
- Evidence source,
- P&L line,
- Confidence,
- Realization dependency,
- Realization start date,
- Benefit type,
- Risk adjustment,
- Handoff status.

For cost lines:

- Vendor/team,
- Contract reference,
- Cost nature,
- Capex/opex treatment,
- Recharge basis,
- Allocation basis,
- Start/end date.

### 9.4 Impact if attributes are missing

Financial totals can still work without attributes, but finance governance is
weaker:

- benefit evidence is harder to audit,
- ownership is unclear,
- validation and handoff workflows are less useful,
- risk-adjusted reporting loses context,
- board pack narratives are less defensible.

---

## 10. Legacy Compatibility Model

Older Transmuter releases used `financial_config_groups`,
`financial_config_items`, `financial_entries`, and
`initiative_financial_selections` to model calculation groups, display metric
rows, and cost categories. Those records can still exist because some older
tenants, imports, exports, and compatibility endpoints may read them.

They are no longer the active admin configuration model.

### 10.1 Current role

The Financial Configuration Engine owns:

- metric definitions instead of legacy metric rows,
- cost categories instead of legacy cost category items,
- bridge rows instead of fixed calculation group behavior,
- initiative financial scope instead of legacy initiative selections.

When an initiative scope is saved, the platform writes the engine scope and
mirrors the older selection shape for compatibility. When cost lines are saved,
the platform resolves the engine cost category and also stores the category key
for reports and workbook flows that still expect a stable text key.

### 10.2 Why compatibility remains

The compatibility tables and endpoints remain available to protect upgraded
tenants and reduce rollout risk:

| Compatibility area | Why it remains |
|---|---|
| `financial_entries` | Older initiative financial grids and historical data may still reference legacy row keys. |
| `financial_config_groups` / `financial_config_items` | Existing tenants may have saved labels and row visibility settings. |
| `initiative_financial_selections` | Older initiative scope reads can still resolve selected rows during migration. |
| `financial_cost_lines.category_key` | Workbook import/export, category filters, and older reports use stable category keys. |

For ACME and Ishirock, the engine should be the source of truth. Non-essential
sample tenants can be deleted or reloaded once ACME and Ishirock have been
validated against the engine.

### 10.3 Impact of moving under one engine

| Area | Impact |
|---|---|
| Admin setup | Admins configure one model instead of matching two separate financial surfaces. |
| Cost classification | Cost lines resolve to tenant-owned engine categories while preserving keys for compatibility. |
| Value bridge | Cost-set rows reference engine category IDs, reducing key drift and deleted-category errors. |
| Initiative scope | Scope can include both metric definitions and cost categories in one tenant-scoped table. |
| Tenant cleanup | Deleting a tenant must remove `initiative_financial_scope` and `financial_cost_categories` along with cost lines and metric values. |
| Migration risk | Existing data must be backfilled so old category keys map to engine categories before legacy categories are de-emphasized. |

### 10.4 Best-practice guidance

Do not create new calculation groups or metric rows for new tenant work. Create
metric definitions, scenarios, cost categories, and bridge rows in the engine.
Treat legacy configuration screens or endpoints as migration aids only.

---

## 11. Cost Categories

Cost categories define the taxonomy used by initiative cost lines.

### 11.1 What they control

Cost categories control:

- cost line category selector,
- cost breakdown in Portfolio Financials,
- category filter in Portfolio Financials,
- value bridge cost row inputs,
- contributor drawer cost labels,
- recurring versus one-off defaults in the UI.

### 11.2 Cost category fields

| Field | Meaning |
|---|---|
| ID | Tenant-scoped engine category identifier used by cost lines and bridge rows. |
| Key | Stable category key saved on cost lines. |
| Label | User-facing category name. |
| Group key | Category group, such as implementation, operating, technology, or people. |
| Rollup type | `recurring_cost`, `one_off_cost`, `total_cost`, or blank. |
| Display order | Sort order in selectors and admin lists. |
| Attributes | Optional tenant-specific metadata. |
| Active | Whether available in selectors. |

Admin API:

```text
POST /admin/financial-engine/cost-categories
PATCH /admin/financial-engine/cost-categories/{cost_category_id}
GET /financial-engine-configuration
```

### 11.3 Default categories

Common defaults:

| Category | Recommended rollup |
|---|---|
| Implementation | `one_off_cost` |
| Vendor / Consulting | `one_off_cost` |
| Software / Licenses | `recurring_cost` |
| Maintenance | `recurring_cost` |
| Labor / Operations | `recurring_cost` |
| Other | blank or tenant-specific |

### 11.4 ACME example

ACME deliberately separates cost treatment:

| Cost type | Examples | Treatment |
|---|---|---|
| One-off costs | implementation, technology tooling, training/change | Investment/payback, not recurring run-rate drag. |
| Recurring costs | software, maintenance, labor | Subtracted from EBITDA-effective net run-rate. |

ACME FY28 management story:

```text
$5.40M GM uplift + $3.75M cost savings - $0.80M recurring cost
= $8.35M EBITDA-effective net run-rate value
```

ACME also shows $2.5M one-off investment separately for payback discussion.

### 11.5 Impact if categories are missing or wrong

| Problem | Impact |
|---|---|
| No categories | Users cannot classify costs well; breakdowns are weak. |
| Wrong recurring/one-off treatment | Net run-rate can be materially wrong. |
| Category key removed while cost lines exist | Existing costs need reassignment. |
| Bridge rows do not include the relevant cost categories | Costs are missing from value bridge. |
| Everything classified as Other | Dashboards work, but management insight is poor. |

### 11.6 Best-practice guidance

Create a small, finance-approved cost taxonomy before entering data. Avoid
overly granular categories unless they support decision-making.

Recommended minimum:

- Implementation,
- External Consulting,
- Software / Licenses,
- Internal Labor,
- Operations / Run,
- Training / Change,
- Other.

---

## 12. How The Pieces Relate

The financial model is connected like this:

```text
Metric Definitions
  -> Benefit Lines
  -> Monthly Metric Values
  -> Formula Metrics
  -> Initiative Summary
  -> Portfolio Financials
  -> Dashboard / Value Bridge / Reports / Board Pack

Scenarios
  -> Monthly Metric Values
  -> Base / High / Actual cases
  -> Plan vs Actuals and variance

Annual Baselines
  -> Baseline formulas
  -> Portfolio baseline cards
  -> Initiative Portfolio reconciliation
  -> Target revenue/margin formulas

Cost Categories
  -> Cost Lines
  -> Cost Breakdown
  -> Value Bridge cost rows
  -> Net run-rate calculations

Bridge Rows
  -> Value Bridge presentation
  -> Executive explanation of benefits, costs, and net value
```

### 12.1 Example: ACME metric flow

ACME has these benefit metrics:

| Metric | Benefit class | Executive interpretation |
|---|---|---|
| Revenue Uplift | Revenue | Commercial growth driver. |
| Gross Margin Uplift | Margin | EBITDA-effective margin value. |
| Cost Savings | Savings | EBITDA-effective recurring savings. |

Monthly values are loaded for `plan_base`, `plan_high`, and `actual`.

The portfolio services then calculate:

```text
Benefits = GM Uplift + Cost Savings
Net Run-rate = Benefits - Recurring Costs
```

Revenue uplift remains visible as a driver, but should not be added to EBITDA
net value unless the tenant intentionally defines a separate enterprise-value
view.

### 12.2 Hypothetical example: automation productivity

Suppose a tenant wants to model productivity:

| Metric | Type | Aggregation | Benefit? |
|---|---|---|---|
| `hours_saved` | number | sum | no |
| `gm_value_per_hour` | currency | last or avg | no |
| `productivity_gm_gain` | currency | formula | yes, margin |
| `realization_pct` | percent | formula | no |

Formulas:

```text
productivity_gm_gain = hours_saved * gm_value_per_hour
realization_pct = productivity_gm_gain / 120000 * 100
```

This is valid when Finance agrees that released hours convert into margin. If
released hours only create capacity and not recognized margin, keep
`productivity_gm_gain` out of benefit rollups until conversion is approved.

---

## 13. Dashboard, Report, And Chart Mapping

This section maps each financial configuration item to the user-facing screens.

### 13.1 Dashboard `/dashboard`

Financial configuration affects:

| Dashboard area | Configuration used | Notes |
|---|---|---|
| Value matrix | Metric definitions, scenarios, cost lines, cost categories, workstream, tag | Shows tenant-configured benefit ranges by workstream and tag. Current mapping uses `plan_base`, `plan_high`, and `actual`; revenue-class metrics are revenue uplift, other benefit metrics become GM/value uplift. |
| Value bridge chart/card | Metric definitions, scenarios, costs | Shows benefits base/high/actual, costs plan/actual, and net base/high/actual. |
| Stage gate waterline | Workstream target locks, value matrix net value, stage gate definitions | Shows above/below waterline value by workstream and stage maturity. |
| Executive brief | Dashboard value bridge and value matrix | PDF/XLSX summary uses dashboard financial overview values. |
| Decision queue financial context | Dashboard financial totals | Helps prioritize financial risk and value. |

If metrics are not configured, the dashboard still shows initiative counts,
RAG, risks, milestones, actions, and KPIs, but financial value cards and matrix
cells will be zero or incomplete.

### 13.2 Portfolio Financials `/financials`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Baseline cards | Tenant annual baseline metrics. |
| Summary cards | Benefit metric definitions, cost lines, scenarios. |
| Trend chart | Monthly metric values, cost lines, granularity, annual baselines. |
| In-year value | Metric values, cost lines, stage filter, scenario availability. |
| Run-rate value ramp | Period net value from benefits less recurring costs. |
| Value bridge | Bridge rows, metric definitions, scenarios, cost categories. |
| Plan vs Actuals table | Scenarios, monthly values, cost plan/actual amounts. |
| Cost Breakdown | Engine cost categories and cost line category assignments. |
| Contributor drawer | Benefit lines, benefit validation, evidence, cost lines. |
| Board Pack export | Same selected financial basis and report payload. |

If cost categories are not configured, cost breakdown and category filters are
weak. If benefit metrics are not configured, benefits and net value are zero.
If scenarios are missing, actual toggles and base/high cases are incomplete.

### 13.3 Initiative Portfolio `/financials/initiative-portfolio`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Baseline columns | Active non-formula baseline-relevant metric definitions and initiative baselines. |
| Baseline reconciliation | Tenant annual baseline compared with initiative baseline totals. |
| Value metric columns | Active non-formula benefit metric definitions. |
| Benefits total | Non-revenue benefit metric values. |
| Recurring costs | Cost lines where `is_recurring = true`. |
| One-off costs | Cost lines where `is_recurring = false`. |
| Net run-rate | Benefits total less recurring costs. |

If initiative baselines are missing, rows are flagged incomplete and
reconciliation fails. If benefit metrics are not marked as benefits, value
columns may not appear or totals may be zero.

### 13.4 Benefits Register `/financials/benefits-register`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Benefit line list | Benefit lines tied to metric definitions. |
| Metric label/class | Metric definition label and benefit class. |
| Plan/actual totals | Monthly metric values for `plan_base` and `actual`. |
| Risk-adjusted value | Benefit line risk adjustment/confidence. |
| Finance validation | Benefit line validation status and evidence fields. |

If benefit lines are not created, the register is empty even if summary values
exist at metric level. For good governance, use benefit lines for material value
claims.

### 13.5 Benefit Tracking `/financials/benefit-tracking`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Locked baseline | Bankable plan snapshots and/or benefit ledger basis. |
| Realized actuals | Benefit realization ledger entries. |
| Plan vs actual variance | Locked plan compared with realized benefit values. |
| Scope filters | Workstream, initiative, and period data. |

Metric definitions and benefit lines provide the planning structure, but Benefit
Tracking also depends on bankable plan locks and actual realization ledger data.
If plans are not locked or actual ledger rows are missing, this screen cannot
show realization discipline.

### 13.6 Bankable Plan `/financials/bankable-plan`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Locked snapshot | Metric definitions, scenarios, benefit lines, cost lines, annual baselines. |
| Plan version history | Governance lock/rebaseline settings. |
| Summary values | Benefit and cost rollups at lock time. |

If financial configuration is incomplete before a lock, the locked snapshot will
preserve incomplete financial data. Rebaseline should be governed and auditable.

### 13.7 Waterline `/financials/waterline`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Workstream locked target | Bankable plan net run-rate or configured locked value basis. |
| Actual total | Realized values or actuals. |
| Variance | Locked plan minus actual/realized progress. |

If workstream target locks are missing, the waterline cannot show committed
value. If net value is miscalculated because recurring costs are wrong, the
waterline will also be wrong.

### 13.8 Shared Costs `/shared-costs`

Financial configuration should affect this directly as the shared-cost feature
is revamped.

Shared costs allocate central pools across initiatives. Use this for platform,
PMO, license, cloud, shared delivery, central vendor, and transformation-office
costs that support more than one initiative. These allocations should appear in
Executive Control Tower burdened value views as allocated cost burden, not as
direct initiative cost lines unless Finance explicitly enables generated cost
line posting.

Current implementation:

| Area | Current behavior |
|---|---|
| Pools | Created from `/shared-costs` with name, free-text category key, year, plan amount, and actual amount. |
| Rules | Allocation method plus filters/weights JSON. |
| Runs | Created immediately and stored as completed allocation runs. |
| Reporting | Executive Control Tower and dashboard executive brief consume allocated costs in burdened value views. |

Target configurable model:

| Area | Configuration source |
|---|---|
| Cost category | Active `financial_cost_categories`, not free-text category keys. |
| Scenario | Active `financial_scenarios`, such as Plan Base, Forecast, or Actual. |
| Allocation basis | Active metric definitions, direct cost categories, initiative dimensions, or manual weights. |
| Reporting treatment | Tenant or pool setting: report-only burden, generated cost lines, or both. |
| Bankable plan treatment | Tenant setting; default should be direct-only until Finance enables burdened bankable value. |

Recommended shared-cost operating model:

```text
Cost pool -> allocation policy -> preview -> approved/locked run -> allocation ledger -> reporting impact
```

Recommended examples:

| Shared cost pool | Typical category | Allocation basis | Example initiatives impacted |
|---|---|---|---|
| Group technology platform | Software / Licenses | Benefit weighted or usage weighted | Data platform, automation, pricing, ERP, service desk. |
| Transformation PMO and benefits office | People Support | Equal split or stage/value weighted | All active initiatives or all bankable initiatives. |
| Shared cloud and integration services | Software / Licenses | Workload, API volume, or technology tag | ERP, data platform, AI service desk, automation initiatives. |
| Change adoption and training team | Training / Change | Manual amount or impacted headcount | ERP, offshoring, finance automation, customer onboarding. |
| Central vendor advisory support | External Consultants | Fixed percentage by workstream | ERP/data, procurement, commercial growth, shared services. |

Best-practice guidance:

- Keep direct initiative costs and allocated shared costs visibly separate.
- Do not let allocations affect bankable plan values unless Finance has
  approved that reporting policy.
- Avoid raw JSON rules for production tenants; use guided filters, selected
  metrics, and explainable basis values.
- Require preview and reconciliation before reports consume a new allocation
  run.
- Lock historical runs so board reports can trace every allocated-cost number
  back to pool, rule, basis, period, and approver.

### 13.9 Executive Control Tower `/reports/control-tower`

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Benefits | Financial entries/metric values. |
| Direct costs | Cost lines. |
| Allocated costs | Shared cost allocation runs. |
| Burdened costs | Direct plus allocated costs. |
| Net after allocation | Benefits less direct and allocated costs. |

The Control Tower answers a different question from the core value bridge:

```text
What is the portfolio value after shared cost burden?
```

Use it after the core metric engine and direct cost categories are working.

### 13.10 Initiative Detail Financials

Financial configuration affects:

| Area | Configuration used |
|---|---|
| Scenario toggle | Active scenarios. |
| Financial grid rows | Active metric definitions and formula rows. |
| Read-only formula rows | Formula metric definitions. |
| Benefit line creation | Active non-formula benefit metric definitions. |
| Cost line creation | Active cost categories. |
| Summary cards | Metric values, scenarios, cost lines. |
| Value bridge | Bridge rows, metric values, cost lines. |
| Assumptions | Financial cell assumption APIs. |

If metric definitions are missing, users cannot enter meaningful benefit values.
If cost categories are missing, cost line creation falls back to poor taxonomy.

---

## 14. What Functionality Is Unavailable Without Proper Configuration

| Missing configuration | Functionality degraded or unavailable |
|---|---|
| Metric definitions | Initiative benefit entry, formulas, metric-based reports, value bridge metric rows, Initiative Portfolio value columns. |
| Benefit flags/classes | Portfolio benefits, net value, dashboard value matrix, Benefits Register totals. |
| Formula definitions | Target values, percentages, run-rate rates, ratio charts. |
| Annual baselines | Baseline cards, baseline formulas, Initiative Portfolio reconciliation. |
| Scenarios | Base/high/actual reporting, variance, actual toggles, scenario summaries. |
| Cost categories | Cost breakdown, category filter, cost bridge rows, recurring/one-off clarity. |
| Shared cost pools and locked allocation runs | Executive Control Tower burdened value, dashboard allocated-cost cards, net after allocation, and any burdened bankable view if enabled. |
| Bridge rows | Executive bridge narrative and custom bridge row presentation. |
| Benefit lines | Benefits Register, validation workflow, evidence, handoff, risk adjustment. |
| Bankable plan locks | Benefit Tracking and Waterline locked-plan comparisons. |
| Benefit realization ledger | Realization tracking actuals. |
| Stage gates/criteria | Governance setup completeness, lock readiness, waterline maturity. |

---

## 15. Finance And Transformation Best-Practice Assessment

### 15.1 What the current model does well

The current model aligns with strong finance/transformation practice in these
ways:

1. It separates **baseline**, **plan**, **upside**, and **actual**.
2. It stores values monthly and rolls them up, which supports phasing discipline.
3. It separates benefit metrics from cost lines.
4. It separates one-off investment from recurring cost drag.
5. It supports Finance validation, evidence, and benefit handoff.
6. It supports bankable plan locks and rebaseline history.
7. It supports tenant-specific metrics instead of hardcoded value models.
8. It uses Decimal money handling.
9. It supports benefit line drilldown, not just top-line summary numbers.

### 15.2 Where tenants must be careful

The model is powerful enough to create bad reporting if configured poorly.

Common risks:

| Risk | Why it matters | Prevention |
|---|---|---|
| Double-counting revenue and margin | Revenue is not EBITDA by itself. | Treat revenue as driver and GM uplift as EBITDA value. |
| Treating one-off costs as recurring run-rate | Understates recurring EBITDA value. | Separate one-off investment from recurring cost. |
| Using averages for percentages blindly | Portfolio percentages become misleading. | Prefer formulas from rolled-up numerator/denominator. |
| Missing actual lane | No variance discipline. | Always configure `actual`. |
| Missing benefit line evidence | Board values are less defensible. | Require benefit lines and evidence for material benefits. |
| Too many custom metrics | Users cannot maintain the model. | Start with a small, finance-approved metric set. |
| Changing keys after data load | Formulas/imports/reports may break. | Treat keys as permanent after launch. |

### 15.3 ACME assessment

ACME is configured correctly for a board-demo transformation tenant:

| Area | Assessment |
|---|---|
| Baselines | Good: FY26 revenue and gross margin baseline are explicit and allocated. |
| Scenarios | Good: baseline, plan base, plan high, and actual are present. |
| Benefit metrics | Good: revenue driver is separated from GM uplift and cost savings. |
| EBITDA treatment | Good: executive net run-rate uses GM uplift plus cost savings less recurring cost. |
| Costs | Good: one-off and recurring costs are separated. |
| Shared costs | Emerging: report-only allocations exist and affect burdened Executive Control Tower views, but configuration should be promoted to engine-backed pools, scenarios, policies, previews, and locked runs. |
| Benefit lines | Good: ACME has named lines, validation status, evidence, risk adjustment, and handoff metadata. |
| Dashboards | Good: FY28 Financial Overview, contributor drawer, Benefits Register, Benefit Tracking, Waterline, and board pack are populated. |
| Caveat | Revenue uplift should remain a driver, not be added into EBITDA net value. |

### 15.4 Better ways to use the model

For production tenants, improve on demo configuration by adding:

- a Finance-approved metric dictionary before data load,
- documented definitions for each metric and benefit class,
- minimum evidence rules by value materiality,
- explicit stage gate criteria for when value becomes bankable,
- explicit shared-cost allocation policies for central PMO, platform, cloud,
  training, and advisory pools,
- formula metrics for every percentage instead of manually entered percentages,
- initiative baseline allocation reconciliation before portfolio reporting,
- periodic actuals upload or integration with Finance systems,
- risk-adjusted benefit views for steering committee decisions,
- a forecast scenario for current outlook separate from plan and actual.

---

## 16. Quick-Start Template For A New Tenant

Use this as a starting point.

### 16.1 Metric definitions

| Key | Label | Type | Aggregation | Benefit class | Benefit? |
|---|---|---|---|---|---|
| `annual_revenue_baseline` | Annual Revenue Baseline | currency | last | none | no |
| `annual_gross_margin_baseline` | Annual Gross Margin Baseline | currency | last | none | no |
| `revenue_uplift` | Revenue Uplift | currency | sum | revenue | yes |
| `gm_uplift` | Gross Margin Uplift | currency | sum | margin | yes |
| `cost_savings` | Cost Savings | currency | sum | savings | yes |
| `target_revenue` | Target Revenue | currency | formula | none | no |
| `target_gross_margin` | Target Gross Margin | currency | formula | none | no |
| `revenue_growth_pct` | Revenue Growth % | percent | formula | none | no |
| `gross_margin_run_rate_pct` | Gross Margin Run-rate % | percent | formula | none | no |
| `gm_improvement_pct` | Gross Margin Improvement % | percent | formula | none | no |

Formulas:

```text
target_revenue = baseline_annual_revenue_baseline + revenue_uplift
target_gross_margin = baseline_annual_gross_margin_baseline + gm_uplift
revenue_growth_pct = revenue_uplift / baseline_annual_revenue_baseline * 100
gross_margin_run_rate_pct = target_gross_margin / target_revenue * 100
gm_improvement_pct = gm_uplift / baseline_annual_gross_margin_baseline * 100
```

### 16.2 Scenarios

| Key | Label | Kind |
|---|---|---|
| `baseline` | Baseline | baseline |
| `plan_base` | Plan Base | plan |
| `plan_high` | Plan High | plan |
| `actual` | Actual | actual |
| `forecast` | Forecast | forecast |

### 16.3 Cost categories

| Key | Label | Rollup |
|---|---|---|
| `implementation` | Implementation | one-off |
| `external_consulting` | External Consulting | one-off |
| `technology_tooling` | Technology Tooling | one-off |
| `training_change` | Training and Change | one-off |
| `software` | Software / Licenses | recurring |
| `maintenance` | Maintenance | recurring |
| `labor` | Labor / Operations | recurring |
| `other` | Other | blank |

### 16.4 Value bridge rows

| Row | Kind | Inputs | Sign |
|---|---|---|---:|
| Revenue Uplift | metric_set | `revenue_uplift` | + |
| Gross Margin Uplift | metric_set | `gm_uplift` | + |
| Cost Savings | metric_set | `cost_savings` | + |
| Recurring Costs | cost_set | software, maintenance, labor | - |
| One-off Investment | cost_set | implementation, consulting, tooling, training | - |
| Net Run-rate Value | net | calculated | + |

### 16.5 Baselines

Set at least:

- Annual Revenue Baseline,
- Annual Gross Margin Baseline.

Then allocate the same baseline metrics across initiatives. The Initiative
Portfolio should reconcile to zero variance or an explained rounding variance.

### 16.6 Shared cost pools

Configure only after initiatives, cost categories, and scenarios exist.

Recommended starter pools:

| Pool | Category | Scenario | Allocation method | Reporting treatment |
|---|---|---|---|---|
| Transformation PMO and benefits office | People Support | Plan Base | Equal split across active initiatives, or benefit weighted once benefit data is mature. | Report-only burden. |
| Group technology platform | Software / Licenses | Plan Base | Benefit weighted or technology-tag weighted. | Report-only burden. |
| Shared change and adoption support | Training / Change | Plan Base | Manual amount or impacted-headcount weighted. | Report-only burden. |

Recommended default:

```text
Do not post generated initiative cost lines and do not reduce bankable plan
value until Finance explicitly approves those policies.
```

---

## 17. Operating Checklist

Before go-live:

- Active metric definitions exist for baseline, revenue, margin, and savings.
- Formula metrics save without validation errors.
- `baseline`, `plan_base`, `plan_high`, and `actual` scenarios are active.
- Tenant annual baseline year and values are set.
- Initiative baseline allocations reconcile to tenant baseline.
- Cost categories distinguish one-off from recurring.
- Shared cost pools are documented separately from direct initiative cost lines.
- Shared cost allocation runs reconcile to the pool amount before they are used
  in executive reporting.
- Value bridge rows include all material benefit metrics and cost categories.
- Benefit lines exist for material value claims.
- Evidence and Finance validation workflow are agreed.
- Stage gates and gate criteria are configured.
- Bankable plan lock behavior is configured.
- Portfolio Financials, Initiative Portfolio, Dashboard, Benefits Register,
  Benefit Tracking, Waterline, and Control Tower are reviewed with sample data.

Monthly operating cadence:

- Update actual values or benefit realization ledger.
- Review plan vs actual variances.
- Validate or reject submitted benefit lines.
- Refresh risk-adjusted value.
- Lock or rebaseline only through governance.
- Export board pack from Portfolio Financials for steering committee review.

---

## 18. Recommendations

1. Keep `plan_base`, `plan_high`, `actual`, and `baseline` keys as standard
   keys. Rename labels if needed, but avoid changing keys.

2. Treat revenue uplift as a commercial driver. Use gross margin uplift and cost
   savings for EBITDA-effective benefit.

3. Separate one-off investment from recurring operating cost. Use recurring cost
   for run-rate net value and one-off cost for payback/investment analysis.

4. Use formulas for percentages and targets. Do not ask users to manually enter
   calculated percentages unless Finance explicitly requires manual override.

5. Make benefit lines mandatory for material benefits. Metric-level totals are
   useful, but benefit lines provide ownership, evidence, validation, and
   realization handoff.

6. Configure baseline metrics before initiative load. Reconciliation is much
   easier if baselines are set before values are entered.

7. Keep the first metric set small. Add specialized metrics only when a tenant
   has an owner, definition, calculation method, and report consumer.

8. Run a sample initiative end to end before loading the full portfolio:
   baseline, plan base, plan high, actual, cost lines, formulas, value bridge,
   benefits register, benefit tracking, and dashboard.

9. For production tenants, add a forecast scenario. Plan is the approved case,
   actual is realized performance, and forecast is the current outlook.

10. Review value bridge rows with Finance. The bridge is the executive story; it
    should match the CFO's language and avoid double-counting.
