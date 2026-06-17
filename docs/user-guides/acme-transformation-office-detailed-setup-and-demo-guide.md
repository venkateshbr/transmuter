# ACME Transformation Office Detailed Setup and Demo Guide

This guide is a complete end-to-end walkthrough for setting up and demonstrating
the **Acme Global Manufacturing** transformation tenant in Transmuter.

It expands the shorter ACME value guide with:

- the exact screens to use,
- what values to configure,
- which filters to apply,
- where benefits and costs appear,
- how to explain each screen to management,
- speaker notes for a live demo,
- the validated ACME values currently configured in the dev environment.

No credentials are included in this guide.

---

## 1. Validated ACME Demo State

Validated on `https://transmuter-dev.ishirock.tech` against the ACME tenant.

| Area | Status | Validation result |
|---|---|---|
| Tenant login | Configured | ACME transformation office user can sign in. |
| Setup checklist | Mostly configured | 7 of 8 checks complete. Gate criteria are the open setup gap. |
| Business units | Configured | Commercial, Corporate, Operations, Shared Services, Technology. |
| Workstreams | Configured | Automation, Commercial Growth, ERP & Data Platform, Offshoring & Operating Model, Procurement & Supply Chain. |
| Financial engine | Configured | Baseline, Plan Base, Plan High, Actual scenarios; revenue, gross margin, savings, formula metrics, and bridge rows. |
| Tenant FY26 baseline | Configured | Annual revenue baseline = `$20.0M`; annual gross margin baseline = `$9.0M`. |
| Initiatives | Configured | 10 ACME initiatives. |
| Initiative baseline allocation | Reconciles | Initiative baselines total `$20.0M` revenue and `$9.0M` gross margin. |
| FY28 Financial Overview | Reconciles | Benefits `$9.15M`, recurring costs `$0.80M`, net run-rate value `$8.35M`. |
| Benefit Tracking / Bankable Plan | Not board-demo-ready yet | ACME has plan/actual financials, but no locked bankable-plan baseline or benefit ledger rows in the current seed. |
| FY28 contributor drawer | Gap found | Contributor drawer currently shows recurring cost contribution but not benefit contribution for clean financial-engine values. Use the summary table and initiative financial tabs for benefit detail until fixed. |

---

## 2. Executive Storyline

Use this storyline for management:

> ACME starts from an FY26 baseline business of `$20.0M` annual revenue and
> `$9.0M` annual gross margin. The transformation office has configured 10
> initiatives across automation, offshoring, commercial growth, ERP/data, and
> procurement. By FY28, the portfolio plan shows `$4.0M` revenue uplift,
> `$5.4M` gross margin uplift, `$3.75M` savings, and `$0.80M` recurring run
> cost. The resulting FY28 EBITDA-effective net run-rate value is `$8.35M`,
> excluding `$2.5M` one-off implementation investment.

Board-level value message:

```text
FY28 EBITDA-effective net run-rate value
= Gross Margin Uplift + Cost Savings - Recurring Run Costs
= $5.40M + $3.75M - $0.80M
= $8.35M
```

Broader enterprise value view:

```text
FY28 enterprise value view
= Revenue Uplift + Gross Margin Uplift + Cost Savings - Recurring Run Costs
= $4.00M + $5.40M + $3.75M - $0.80M
= $12.35M
```

Use the first formula for EBITDA. Use the second only when discussing broader
commercial value.

---

## 3. ACME Initiative Portfolio

Use the following portfolio when setting up a new tenant or explaining the ACME
demo.

| Code | Initiative | BU | Workstream | Tag | FY26 revenue baseline | FY26 GM baseline | FY28 revenue uplift | FY28 GM uplift | FY28 savings | FY28 recurring cost | FY28 EBITDA net | One-off investment |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ENT-001 | Transformation PMO & Benefits Office | Corporate | Automation | other | `$0.50M` | `$0.22M` | `$0.00M` | `$0.10M` | `$0.00M` | `$0.12M` | `-$0.02M` | `$0.25M` |
| ENT-002 | Finance Process Automation | Shared Services | Automation | automation | `$1.60M` | `$0.72M` | `$0.00M` | `$0.45M` | `$0.65M` | `$0.08M` | `$1.02M` | `$0.30M` |
| ENT-003 | Customer Onboarding Automation | Commercial | Automation | automation | `$2.20M` | `$0.99M` | `$0.70M` | `$0.50M` | `$0.15M` | `$0.06M` | `$0.60M` | `$0.28M` |
| ENT-004 | Back-office Finance & HR Offshoring | Shared Services | Offshoring & Operating Model | offshoring | `$2.00M` | `$0.90M` | `$0.00M` | `$0.80M` | `$1.00M` | `$0.10M` | `$1.70M` | `$0.22M` |
| ENT-005 | Enterprise Data Platform | Technology | ERP & Data Platform | automation | `$1.20M` | `$0.54M` | `$0.45M` | `$0.40M` | `$0.20M` | `$0.15M` | `$0.45M` | `$0.50M` |
| ENT-006 | Pricing & Discount Optimization | Commercial | Commercial Growth | commercial | `$3.00M` | `$1.35M` | `$1.10M` | `$1.05M` | `$0.00M` | `$0.05M` | `$1.00M` | `$0.25M` |
| ENT-007 | Sales Coverage Expansion | Commercial | Commercial Growth | commercial | `$3.40M` | `$1.53M` | `$0.95M` | `$0.65M` | `$0.00M` | `$0.07M` | `$0.58M` | `$0.20M` |
| ENT-008 | Procurement Vendor Consolidation | Operations | Procurement & Supply Chain | offshoring | `$2.30M` | `$1.04M` | `$0.00M` | `$0.55M` | `$0.80M` | `$0.04M` | `$1.31M` | `$0.20M` |
| ENT-009 | Supply Chain Control Tower | Operations | Procurement & Supply Chain | automation | `$2.40M` | `$1.08M` | `$0.30M` | `$0.45M` | `$0.45M` | `$0.06M` | `$0.84M` | `$0.18M` |
| ENT-010 | AI Service Desk Automation | Technology | Automation | automation | `$1.40M` | `$0.63M` | `$0.50M` | `$0.45M` | `$0.50M` | `$0.07M` | `$0.88M` | `$0.12M` |
| **Total** |  |  |  |  | **`$20.00M`** | **`$9.00M`** | **`$4.00M`** | **`$5.40M`** | **`$3.75M`** | **`$0.80M`** | **`$8.35M`** | **`$2.50M`** |

---

## 4. New Tenant Setup Sequence

Follow this sequence for a new tenant before creating initiatives.

### Step 1: Sign in and open Admin

Screen:

- `/auth/login`
- `/admin`
- Admin tab: **General**

Actions:

1. Sign in as the tenant administrator or transformation office user.
2. Open **Admin** from the main navigation.
3. On **General**, set the organization legal name and logo URL.
4. Check **First-run setup**. The tenant should eventually show all setup checks complete.

Speaker notes:

> We start by setting the tenant identity and checking the first-run setup
> checklist. This is the control point that prevents initiative creation before
> the tenant has the core dimensions, financial model, governance rules, and
> users needed for reliable value tracking.

Expected ACME demo note:

- ACME currently shows 7/8 setup checks complete.
- Gate criteria are the open configuration gap.

### Step 2: Configure strategic dimensions

Screen:

- `/admin`
- Admin tab: **Strategic Parameters**

Configure:

Business units:

- Corporate
- Commercial
- Operations
- Technology
- Shared Services

Workstreams:

- Automation
- Offshoring & Operating Model
- Commercial Growth
- ERP & Data Platform
- Procurement & Supply Chain

Markets:

- United States

Themes:

- Enterprise gross margin and growth transformation

Tags:

- automation
- offshoring
- commercial
- other

Actions:

1. In **Workstream Management**, create the five ACME workstreams.
2. In **Business Units**, create the five ACME business units.
3. In **Markets**, create United States.
4. In **Themes**, create the enterprise transformation theme.
5. In **Tags**, create automation, offshoring, commercial, and other.

Speaker notes:

> These dimensions are not cosmetic. They are how management slices the
> transformation: by business ownership, workstream, theme, market, and value
> lever. We will later use these same tags and workstreams to filter initiative
> pipeline, financial overview, matrix views, meetings, and progress reporting.

### Step 3: Configure financial reporting settings

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Financial Metric Engine**

Configure:

| Setting | ACME value |
|---|---|
| Reporting currency | USD |
| Fiscal year start | January |

Actions:

1. Set **Currency** to `USD`.
2. Set **Fiscal Start** to `January`.
3. Click **Save Settings**.

Speaker notes:

> The fiscal calendar and reporting currency make every screen consistent:
> initiative financials, portfolio trend, value ramp, bridge rows, and exports
> all use the same reporting basis.

### Step 4: Configure financial metric definitions

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Metric Definitions**

Configure the ACME metric definitions:

| Metric key | Label | Type | Aggregation | Benefit class | Purpose |
|---|---|---|---|---|---|
| `annual_revenue_baseline` | Annual Revenue Baseline | Currency | Last | None | Original annual revenue reference. |
| `annual_gross_margin_baseline` | Annual Gross Margin Baseline | Currency | Last | None | Original annual gross margin reference. |
| `revenue_uplift` | Revenue Uplift | Currency | Sum | Revenue | Commercial growth driver. |
| `gm_uplift` | Gross Margin Uplift | Currency | Sum | Margin | EBITDA-effective margin benefit. |
| `cost_savings` | Cost Savings | Currency | Sum | Savings | EBITDA-effective recurring savings or avoided spend. |
| `target_revenue` | Target Revenue | Currency | Formula | None | Baseline revenue plus revenue uplift. |
| `target_gross_margin` | Target Gross Margin | Currency | Formula | None | Baseline GM plus GM uplift. |
| `revenue_growth_pct` | Revenue Growth % | Percent | Formula | None | Revenue uplift divided by revenue baseline. |
| `gross_margin_run_rate_pct` | Gross Margin Run-rate % | Percent | Formula | None | Target GM divided by target revenue. |
| `gm_improvement_pct` | Gross Margin Improvement % | Percent | Formula | None | GM uplift divided by GM baseline. |

Recommended formulas:

```text
target_revenue = baseline_annual_revenue_baseline + revenue_uplift
target_gross_margin = baseline_annual_gross_margin_baseline + gm_uplift
revenue_growth_pct = revenue_uplift / baseline_annual_revenue_baseline * 100
gross_margin_run_rate_pct = target_gross_margin / target_revenue * 100
gm_improvement_pct = gm_uplift / baseline_annual_gross_margin_baseline * 100
```

Actions:

1. Add or review each metric definition.
2. Use **Benefit = No** for baseline and formula metrics.
3. Use **Benefit = Revenue** for Revenue Uplift.
4. Use **Benefit = Margin** for Gross Margin Uplift.
5. Use **Benefit = Savings** for Cost Savings.
6. Click **Save** on each metric row.

Speaker notes:

> We separate baseline, driver, benefit, and formula metrics. Baselines are not
> benefits. Revenue uplift is a commercial driver. Gross margin uplift and cost
> savings are EBITDA-effective benefits. Formula rows let management see rates
> and targets without manual calculation.

### Step 5: Configure tenant annual baseline

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Annual Baselines**

Configure:

| Metric | Fiscal year | Value |
|---|---:|---:|
| Annual Revenue Baseline | 2026 | `20000000` |
| Annual Gross Margin Baseline | 2026 | `9000000` |

Actions:

1. Set **Fiscal Year** to `2026`.
2. Enter `20000000` for Annual Revenue Baseline.
3. Enter `9000000` for Annual Gross Margin Baseline.
4. Click **Save**.

Where this appears:

- `/financials`
- Top baseline cards:
  - FY26 Portfolio Baseline Annual Revenue
  - FY26 Portfolio Baseline Annual Gross Margin
  - Baseline Margin Rate
- Financial trend baseline line.

Speaker notes:

> The FY26 baseline is the denominator and starting point. It is not counted as
> transformation value. It tells the board what business we are improving from:
> `$20.0M` revenue and `$9.0M` gross margin, or a 45% gross margin rate.

### Step 6: Configure scenarios

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Scenarios**

Configure:

| Scenario key | Label | Kind | Use |
|---|---|---|---|
| `baseline` | Baseline | Baseline | Original operating reference. |
| `plan_base` | Plan Base | Plan | Main management plan. |
| `plan_high` | Plan High | Plan | Upside case. |
| `actual` | Actual | Actual | Realized or latest actual value. |

Actions:

1. Ensure all four scenarios are active.
2. Ensure **Plan Base** is the primary plan scenario.

Speaker notes:

> The scenario lanes support board-quality value discipline: baseline, base plan,
> upside, and actuals. We do not overwrite the plan when actuals change; we keep
> the plan and compare realized performance against it.

### Step 7: Configure value bridge rows

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Value Bridge Rows**

Configure:

| Bridge row | Kind | Sign | Inputs |
|---|---|---:|---|
| Revenue Uplift | Metrics | Positive | Revenue Uplift |
| Gross Margin Uplift | Metrics | Positive | Gross Margin Uplift |
| Cost Savings | Metrics | Positive | Cost Savings |
| Recurring Costs | Costs | Negative | Software, Maintenance, Labor |
| One-off Costs | Costs | Negative | Implementation, Technology Tooling, External Consultants, Training Change |
| Net Value | Net | Positive | Calculated net row |

Actions:

1. Add bridge rows in this order.
2. Select the relevant metric or cost inputs for each row.
3. Mark recurring and one-off costs with negative sign.
4. Save each row.

Speaker notes:

> This is the management bridge. It shows how the transformation moves from
> gross value to net value. Recurring costs reduce run-rate EBITDA. One-off
> implementation costs are investment and payback burden, not recurring EBITDA
> drag.

### Step 8: Configure cost categories

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Cost Categories**

Configure:

One-off categories:

- Implementation / Project Cost
- Technology / Tooling
- External Consultants
- Training / Change Management

Recurring categories:

- Software / Licenses
- Support / Maintenance
- People Support

Actions:

1. Create one-off categories with rollup type **One-time**.
2. Create recurring categories with rollup type **Recurring**.
3. Save the cost category configuration.

Speaker notes:

> This split is critical for EBITDA storytelling. One-off investment helps us
> explain payback. Recurring run cost is what must be deducted from run-rate
> EBITDA value.

### Step 9: Configure governance stage gates

Screen:

- `/admin`
- Admin tab: **Governance Engine**

Recommended stage gates:

| Gate | Label | From stage | To stage | Approval |
|---:|---|---|---|---|
| 1 | Gate 1: Identify to Validate | identified | validated | Required |
| 2 | Gate 2: Validate to Plan | validated | planned | Required |
| 3 | Gate 3: Plan to Commit | planned | committed | Required |
| 4 | Gate 4: Commit to Execute | committed | executing | Required |
| 5 | Gate 5: Execute to Realized | executing | realized | Required |

Recommended gate criteria:

Gate 1:

- Problem statement and opportunity owner defined.
- High-level value hypothesis documented.
- Workstream and impacted business unit assigned.

Gate 2:

- FY26 baseline approved by Finance.
- Benefit calculation method documented.
- One-off and recurring cost assumptions captured.

Gate 3:

- Delivery plan and milestones agreed.
- Business owner accepts target.
- Risks and dependencies documented.

Gate 4:

- Funding and resources confirmed.
- KPI and benefit tracking cadence agreed.
- Change/adoption plan agreed.

Gate 5:

- Actual benefit evidence submitted.
- Finance validates realized value.
- Business-as-usual owner accepts sustainment.

Actions:

1. Add the five gates.
2. Add gate criteria for each gate.
3. Use `transformation_office` as the approver role.
4. Set **Require all active criteria** when gate quality needs strict control.

Speaker notes:

> Stage gates stop the portfolio from becoming a list of unverified ideas. The
> board should know which value is identified, which is validated, which is
> committed, and which is realized.

ACME validation note:

- Stage gates are configured in ACME.
- Gate criteria are not configured in the current ACME seed and should be added
  before using ACME as a full governance demonstration.

### Step 10: Configure users and roles

Screens:

- `/people`
- `/admin`, tab: **Access Control**

Recommended roles:

| Role | Use |
|---|---|
| `transformation_office` | PMO / value office, full portfolio management. |
| `initiative_owner` | Own assigned initiatives and updates. |
| `viewer` | Read-only portfolio and dashboard access. |

Actions:

1. Open **People** to create or invite users.
2. Assign transformation office, initiative owner, or viewer roles.
3. Use **Admin > Access Control** to review user status and role assignment.

Speaker notes:

> Value delivery is role-based. The transformation office governs portfolio
> value, owners maintain their initiatives, and viewers can inspect management
> dashboards without changing data.

---

## 5. Initiative Setup Sequence

Repeat this sequence for each initiative.

### Step 1: Create an initiative

Screen:

- `/initiatives/pipeline`
- Button: **New Initiative**
- Screen: `/initiatives/new`

Actions:

1. Select **Create with Transmuter**.
2. Step 1: enter initiative name, workstream, business units, market, theme,
   initiative type, impact type, priority, and tag.
3. Step 2: enter summary, context/problem, value logic, and dependencies.
4. Step 3: enter market owner, group owner, planned start, and planned end.
5. Step 3 also includes financial metrics, cost categories, and annual baseline
   values. Configure them immediately if the value case is known.
6. Step 4: review suggestions if using AI-assisted intake.

ACME example for ENT-006:

| Field | Value |
|---|---|
| Initiative name | Pricing & Discount Optimization |
| Workstream | Commercial Growth |
| Business unit | Commercial |
| Market | United States |
| Theme | Enterprise gross margin and growth transformation |
| Type | Revenue Growth |
| Impact type | Recurring |
| Priority | High |
| Tag | commercial |
| Planned start | 2027-01-01 |
| Planned end | 2028-12-31 |

Speaker notes:

> The initiative record creates the accountable unit of value. We capture what
> business area owns it, what workstream governs it, what value lever it belongs
> to, and what assumptions explain the business case.

### Step 2: Configure financial scope

Screens:

- `/initiatives/:id`
- Tab: **Financials**
- Button: **Configure Scope**
- Screen: `/initiatives/:id/financial-scope`

Actions:

1. Select the metric rows needed for the initiative:
   - Revenue Uplift
   - Gross Margin Uplift
   - Cost Savings
   - formula rows as needed
2. Select cost categories:
   - one-off categories when implementation investment exists
   - recurring categories when ongoing run cost exists
3. Click **Save Scope**.

Speaker notes:

> Scope controls which financial rows appear for the initiative. This keeps the
> financial grid focused: commercial initiatives need revenue and margin rows;
> procurement initiatives need savings; technology initiatives often need both
> benefit rows and cost categories.

### Step 3: Configure initiative annual baseline

Screens:

- `/initiatives/new`, Step 3, **Annual Baseline**
- or `/initiatives/:id/edit`, Step 3, **Annual Baseline**

Actions:

1. Set fiscal year to `2026`.
2. Enter initiative-specific Annual Revenue Baseline.
3. Enter initiative-specific Annual Gross Margin Baseline.
4. Save the initiative.

How to validate:

1. Open `/initiatives/:id`.
2. Open the **Financials** tab.
3. Toggle scenario to **Baseline**.
4. Confirm baseline rows appear for the initiative.

Speaker notes:

> The portfolio baseline is allocated to initiatives so each value case has a
> denominator. That allows us to explain growth percentages and margin
> improvement by initiative, not only at portfolio level.

### Step 4: Add benefit lines

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Section above the grid: **Benefit Metric / Named Benefit Line**

Actions:

1. Select a benefit metric:
   - Revenue Uplift
   - Gross Margin Uplift
   - Cost Savings
2. Enter a named benefit line.
3. Enter confidence percentage if known.
4. Choose phasing:
   - **Manual** for month-by-month entry in the grid.
   - **One-off** for a single-period benefit.
   - **Spread** for an amount spread across months.
5. Enter amount, start month, and end month.
6. Click **Add Line**.

Examples:

| Initiative | Benefit metric | Benefit line | FY28 amount |
|---|---|---|---:|
| ENT-006 Pricing & Discount Optimization | Revenue Uplift | Price realization uplift | `$1.10M` |
| ENT-006 Pricing & Discount Optimization | Gross Margin Uplift | Discount leakage reduction | `$1.05M` |
| ENT-008 Procurement Vendor Consolidation | Cost Savings | Vendor-rate savings | `$0.80M` |

Speaker notes:

> Benefit lines make the value case auditable. Instead of a single unexplained
> number, each initiative has named benefit sources, confidence, timing, and
> monthly values.

### Step 5: Add one-off and recurring cost lines

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Section above the grid: **Cost Category / Cost Line**

Actions:

1. Select cost category.
2. Enter cost line name.
3. Select lane:
   - **Plan** for planned cost.
   - **Actual** for actual cost.
4. Select mode:
   - **One-off** for implementation investment.
   - **Spread** for monthly or annual run cost.
5. Enter amount, start month, and end month.
6. Click **Add Cost**.

ACME cost pattern:

One-off costs are in FY27:

- 45% Implementation / Project Cost
- 35% Technology / Tooling
- 20% Training / Change Management

Recurring run costs ramp:

- 50% of FY28 recurring run-rate in FY27
- 100% run-rate in FY28
- split 40% Software, 35% Maintenance, 25% Labor

Speaker notes:

> This is where we distinguish investment from ongoing drag. One-off costs
> affect payback. Recurring costs reduce run-rate EBITDA. Management should not
> mix the two.

### Step 6: Edit detailed monthly values

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Button: **Edit Details**

Actions:

1. Use scenario toggle:
   - **Baseline** for FY26 baseline rows.
   - **Base** for conservative plan.
   - **High** for upside plan.
   - **Actuals** for realized values.
2. Click **Edit Details**.
3. Enter or review monthly values in the grid.
4. Click **Save Changes**.
5. Use the cell assumption context menu to document key assumptions.

Speaker notes:

> The grid is the detailed financial ledger. The annual management numbers are
> the rollup of these period values. We can trace a portfolio value back to
> scenario, metric, benefit line, month, and initiative.

### Step 7: Add milestones, KPIs, risks, status, and team

Screen:

- `/initiatives/:id`
- Tabs: **Milestones**, **KPIs**, **Risks**, **Status**, **Team**

Recommended ACME minimum:

Milestones:

- Gate 2 baseline and business case confirmed.
- FY28 run-rate benefits activated.

Risks:

- Data readiness risk.
- Adoption/change risk.
- Finance validation risk.

KPIs:

- Revenue uplift.
- Gross margin uplift.
- Cost savings.
- Process cycle time, productivity, adoption, or service-level KPI depending on initiative.

Speaker notes:

> Finance value is only one part of transformation control. Milestones, KPIs,
> risks, dependencies, and status updates explain whether the value is likely to
> materialize and what management must unblock.

---

## 6. Where to Demonstrate Value

### Screen 1: Executive Dashboard

Screen:

- `/dashboard`

Use it for:

- first executive landing view,
- portfolio status,
- high-level transformation posture.

Speaker notes:

> This is the executive landing page. It gives management a first read on the
> transformation portfolio before we move into financial proof.

### Screen 2: Initiative Pipeline

Screen:

- `/initiatives/pipeline`

Filters to apply:

| Filter | Demo use |
|---|---|
| Search | Search `Pricing`, `Procurement`, or `Automation`. |
| Business Unit | Filter to Commercial, Operations, or Shared Services. |
| Workstream | Filter to Automation, Commercial Growth, or Procurement & Supply Chain. |
| Priority | Show high-priority initiatives. |
| Tag | Show automation, offshoring, or commercial initiatives. |

Speaker notes:

> This is the transformation control list. Every management number must trace
> back to an initiative with an owner, stage, workstream, RAG status, and value
> case.

### Screen 3: Financial Overview

Screen:

- `/financials`

Default demo settings:

| Control | Demo setting |
|---|---|
| Granularity | Yearly |
| Benefits | On |
| Actuals | On |
| Year | 2028 |
| Plan as-of date | Blank unless demonstrating historical cutoff. |
| Stage | All stages for total portfolio; In-Progress when showing active portfolio. |
| Cost category | All categories for total value; Software, Maintenance, Labor for recurring-cost drilldown. |

Expected FY28 values:

| Metric | Expected plan value |
|---|---:|
| Benefits | `$9.15M` |
| Recurring costs | `$0.80M` |
| One-off costs | `$0.00M` |
| Net run-rate value | `$8.35M` |

Top baseline cards:

| Card | Expected value |
|---|---:|
| FY26 Portfolio Baseline Annual Revenue | `$20.00M` |
| FY26 Portfolio Baseline Annual Gross Margin | `$9.00M` |
| Baseline Margin Rate | `45.0%` |

Demo sequence:

1. Set **Year** to `2028`.
2. Set granularity to **Yearly**.
3. Turn **Benefits On**.
4. Turn **Actuals On**.
5. Point to the FY26 baseline cards.
6. Point to the trend chart baseline line.
7. Point to Benefits, Recurring Costs, and Net Run-rate Value.
8. Change year to `2027` to show ramp year.
9. Change back to `2028` to show run-rate.

Speaker notes:

> This is the board proof screen. The top row answers the baseline question:
> what business were we improving? The summary cards answer the value question:
> what recurring EBITDA-effective run-rate value are we delivering? In FY28,
> ACME shows `$9.15M` gross benefits, `$0.80M` recurring run cost, and `$8.35M`
> net run-rate value.

Important current product note:

- Use the summary cards and period table for FY28 portfolio values.
- The contributor drawer currently does not show clean-engine benefit
  contribution by initiative for FY28. It shows recurring cost contribution.
  This is logged in the platform improvement document.

### Screen 4: Financial Overview cost-category drilldown

Screen:

- `/financials`

Filters:

| Control | Demo setting |
|---|---|
| Granularity | Yearly |
| Benefits | On |
| Actuals | On |
| Year | 2028 |
| Cost category | Software / Licenses |

Repeat for:

- Support / Maintenance
- People Support

Speaker notes:

> This is how we isolate recurring run cost. Management can see whether net
> value leakage comes from software, maintenance, or people support.

### Screen 5: Initiative detail financials

Screen:

- `/initiatives/pipeline`
- Open an initiative, for example **ENT-006 Pricing & Discount Optimization**
- Tab: **Financials**

Demo settings:

| Control | Setting |
|---|---|
| Scenario | Base |
| View | Quarterly Summary View first |
| Then | Edit Details for monthly grid |

Expected ENT-006 FY28:

| Value | Amount |
|---|---:|
| Revenue uplift | `$1.10M` |
| Gross margin uplift | `$1.05M` |
| Recurring cost | `$0.05M` |
| EBITDA net | `$1.00M` |
| One-off investment | `$0.25M` |

Speaker notes:

> We can trace the portfolio number to a single initiative. Pricing & Discount
> Optimization contributes `$1.10M` revenue uplift and `$1.05M` gross margin
> uplift in FY28, with only `$0.05M` recurring run cost. That creates `$1.00M`
> EBITDA-effective net run-rate value.

### Screen 6: Initiative financial scope

Screen:

- `/initiatives/:id/financial-scope`

Use it for:

- explaining why certain metric rows appear,
- adding/removing active benefit or cost rows,
- showing locked financial scope behavior.

Speaker notes:

> This is the control surface for what finance tracks on each initiative. We
> avoid forcing every initiative into every metric. Commercial initiatives track
> revenue and margin; procurement initiatives track savings; technology
> initiatives may track margin, savings, and run cost.

### Screen 7: Initiative workbook export

Screen:

- `/initiatives/:id`
- Button: **Export Excel**

Use it for:

- offline finance review,
- initiative owner working sessions,
- audit backup.

Speaker notes:

> The workbook export lets Finance and initiative owners review the same
> financial structure offline. The system remains the source of record; the
> workbook is a review and import channel.

### Screen 8: Bankable Plan

Screen:

- `/financials/bankable-plan`

Use it for:

- showing whether an initiative has a locked plan snapshot,
- comparing versions after rebaseline,
- navigating to editable financial scope.

Current ACME demo note:

- ACME does not currently have locked bankable plan snapshots seeded.
- Use this screen to explain the intended governance workflow, not as the main
  ACME value proof until gate submissions and locks are populated.

Speaker notes:

> The bankable plan is the immutable version of an approved value case. Once an
> initiative passes the configured approval gate, the plan becomes the baseline
> for realization tracking. Today the ACME financial plan exists, but the locked
> bankable-plan history still needs to be populated for a full governance demo.

### Screen 9: Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Controls:

| Control | Demo use |
|---|---|
| Scope | Portfolio, Workstream, Initiative |
| Granularity | Monthly, Quarterly, Yearly |
| Workstream | Select a workstream when scope = Workstream |
| Initiative | Select an initiative when scope = Initiative |

Current ACME demo note:

- ACME benefit tracking currently shows zero locked baseline and zero realized
  benefit ledger because locked bankable plans and ledger rows are not seeded.

Speaker notes:

> This is where the operating model moves from planned value to realized value.
> It should compare actual benefit ledger values against locked bankable plans.
> For the ACME demo, this screen needs locked plans and actual benefit ledger
> rows before it becomes board-ready.

### Screen 10: Waterline

Screen:

- `/financials/waterline`

Use it for:

- workstream target lock,
- showing which initiatives are included above the cutoff,
- comparing actuals to frozen target.

Recommended demo setup:

1. Select a workstream.
2. Set lock date after Gate 2 approvals.
3. Click **Preview**.
4. Confirm included initiatives.
5. Click **Lock target** only in a prepared demo tenant.

Speaker notes:

> The waterline gives management a frozen target by workstream. It prevents
> shifting goalposts after approval and creates a basis for actual realization
> comparison.

### Screen 11: Control Tower

Screen:

- `/reports/control-tower`

Use it for:

- management meeting view,
- consolidated decision support,
- executive reporting.

Speaker notes:

> The control tower is the management meeting view. It combines the portfolio,
> financials, risks, and progress signals into one operating cadence.

---

## 7. Full Management Demo Script

### Opening

Screen:

- `/dashboard`

Speaker notes:

> Today we will walk through ACME's enterprise transformation portfolio. The
> goal is to show not only a list of initiatives, but how the transformation
> office converts a baseline business into bankable, trackable value.

### Segment 1: Show portfolio structure

Screen:

- `/initiatives/pipeline`

Actions:

1. Show 10 initiatives.
2. Filter by tag `automation`.
3. Filter by workstream `Commercial Growth`.
4. Clear filters.

Speaker notes:

> ACME has 10 initiatives. The portfolio is structured by workstream, business
> unit, and value tag. This lets management answer: where is the value coming
> from, who owns it, and which operating lever is responsible?

### Segment 2: Show baseline and FY28 run-rate value

Screen:

- `/financials`

Actions:

1. Set **Year** to `2028`.
2. Set **Yearly**.
3. Turn **Benefits On**.
4. Turn **Actuals On**.
5. Point to baseline cards.
6. Point to Net Run-rate Value.

Speaker notes:

> The baseline is FY26: `$20.0M` revenue and `$9.0M` gross margin. Against that
> baseline, the FY28 plan shows `$9.15M` benefits and `$0.80M` recurring cost,
> which gives `$8.35M` EBITDA-effective net run-rate value.

### Segment 3: Explain FY27 ramp versus FY28 run-rate

Screen:

- `/financials`

Actions:

1. Change **Year** to `2027`.
2. Show ramp-year net value.
3. Change **Year** to `2028`.
4. Show run-rate value.

Expected values:

| Year | Benefits | Recurring costs | One-off costs | Net run-rate value |
|---:|---:|---:|---:|---:|
| 2027 | `$4.62M` | `$0.40M` | `$2.50M` | `$4.22M` |
| 2028 | `$9.15M` | `$0.80M` | `$0.00M` | `$8.35M` |

Speaker notes:

> FY27 is the ramp year. Benefits begin, but one-off implementation investment
> is also incurred. FY28 is the target run-rate year. That is why FY28 is the
> cleanest year for EBITDA run-rate value.

### Segment 4: Show an initiative value case

Screen:

- `/initiatives/pipeline`
- Open **ENT-006 Pricing & Discount Optimization**
- Tab: **Financials**

Actions:

1. Select **Base** scenario.
2. Show summary cards.
3. Click **Edit Details** to show monthly detail.
4. Do not save changes during demo.

Speaker notes:

> This is one source of the portfolio value. Pricing contributes revenue growth
> and margin uplift through discount optimization. The same monthly values roll
> into the portfolio financial overview.

### Segment 5: Explain cost treatment

Screen:

- `/financials`

Actions:

1. Keep **Year** = `2028`.
2. Select cost category **Software / Licenses**.
3. Select **Support / Maintenance**.
4. Select **People Support**.
5. Clear the cost category filter.

Speaker notes:

> We separate one-off investment from recurring cost. The FY28 EBITDA run-rate
> calculation subtracts recurring costs. One-off investment is used for payback
> and funding discussion, not recurring EBITDA.

### Segment 6: Explain governance and realization

Screens:

- `/financials/bankable-plan`
- `/financials/benefit-tracking`
- `/financials/waterline`

Actions:

1. Show the screens briefly.
2. Explain intended workflow.
3. Be transparent that ACME needs locked bankable plans and benefit ledger rows
   for a full realization demo.

Speaker notes:

> The next level of maturity is to lock bankable plans at approval gates and
> then track realized benefits against that locked plan. The platform supports
> those screens, but the current ACME demo data needs locked plans and ledger
> values populated before these become the main board evidence.

### Close

Screen:

- `/financials`

Actions:

1. Return to **Year** = `2028`.
2. Show baseline cards and net run-rate value.

Speaker notes:

> The ACME portfolio demonstrates the core transformation management story:
> baseline, initiatives, planned benefit, recurring cost, actual variance, and
> management drilldown. The headline is `$8.35M` FY28 EBITDA-effective net
> run-rate value on a `$20.0M` revenue and `$9.0M` gross margin baseline.

---

## 8. Recommended Board Questions and Answers

| Board question | Where to answer | Answer pattern |
|---|---|---|
| What is the starting point? | `/financials` baseline cards | FY26 revenue baseline `$20.0M`, gross margin baseline `$9.0M`. |
| What is the FY28 run-rate value? | `/financials`, Year = 2028 | `$8.35M` EBITDA-effective net run-rate value. |
| How much is growth versus cost-out? | `/financials`; initiative financial tabs | Revenue uplift `$4.0M`, GM uplift `$5.4M`, savings `$3.75M`. |
| What costs are recurring? | `/financials`, cost category filter | FY28 recurring run cost `$0.80M`. |
| What investment is needed? | `/financials`, Year = 2027; cost breakdown | One-off investment `$2.5M`. |
| Who owns the value? | `/initiatives/pipeline`; initiative detail | Owner, group owner, BU, and workstream per initiative. |
| Is the plan locked? | `/financials/bankable-plan` | Current ACME seed needs locked plan snapshots populated. |
| Is value realized or just planned? | `/financials/benefit-tracking` | Current ACME seed needs benefit ledger rows populated for realized-value demo. |
| Where are risks and blockers? | Initiative **Risks**, **Status**, `/pmo/risks`, `/progress/status-updates` | Show RAG status, risk list, and overdue updates. |

---

## 9. Operating Cadence for a Transformation Office

Weekly:

- Initiative owners update status, risks, dependencies, and action items.
- Transformation office reviews overdue updates and blockers.

Bi-weekly:

- Workstream owners review initiative pipeline and milestone progress.
- Finance reviews material changes to benefit and cost assumptions.

Monthly:

- Transformation office reviews `/financials` with Year and Actuals filters.
- Benefits and recurring costs are reconciled by initiative.
- Steering committee reviews risks, delays, and value leakage.

Quarterly:

- Lock or refresh bankable plans after governance approvals.
- Review waterline target locks by workstream.
- Present board pack with baseline, run-rate value, actuals, variance, risks,
  and decisions required.

---

## 10. Practical Demo Warnings

1. Do not call revenue uplift EBITDA. Revenue becomes EBITDA-effective only
   through margin conversion.
2. Do not subtract one-off investment from FY28 run-rate EBITDA. Use it for
   payback and investment discussion.
3. Do not rely on the FY28 contributor drawer for benefit contribution until the
   clean-engine contributor gap is fixed.
4. Do not position Benefit Tracking as complete for ACME until bankable plans
   and benefit ledger rows are populated.
5. Do not ignore the Admin setup gap: gate criteria need to be configured for a
   complete governance demo.
