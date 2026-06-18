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
| Setup checklist | Configured | 8 of 8 checks complete. ACME has 5 active stage gates, 10 active gate criteria, and 0 gates missing criteria. |
| Business units | Configured | Commercial, Corporate, Operations, Shared Services, Technology. |
| Workstreams | Configured | Automation, Commercial Growth, ERP & Data Platform, Offshoring & Operating Model, Procurement & Supply Chain. |
| Financial engine | Configured | Baseline, Plan Base, Plan High, Actual scenarios; revenue, gross margin, savings, formula metrics, and bridge rows. |
| Tenant FY26 baseline | Configured | Annual revenue baseline = `$20.0M`; annual gross margin baseline = `$9.0M`. |
| Initiatives | Configured | 10 ACME initiatives. |
| Initiative baseline allocation | Reconciles | Initiative baselines total `$20.0M` revenue and `$9.0M` gross margin. |
| FY28 Financial Overview | Reconciles | Benefits `$9.15M`, recurring costs `$0.80M`, net run-rate value `$8.35M`. |
| Benefit Tracking / Bankable Plan | Board-demo-ready | ACME has locked bankable plans, non-zero locked baseline and actual benefit ledger values, and `ENT-005` rebaseline history. |
| FY28 contributor drawer | Reconciles | Contributor drawer shows all 10 initiatives, benefit-line detail, validation status, and totals that reconcile to the Financial Overview summary. |
| Benefits Register | Configured | Portfolio-wide benefit lines show gross, validated, risk-adjusted, bankable, and realized values with evidence and owner metadata. |
| Board pack export | Configured | Financial Overview can export a non-empty XLSX board pack using the same selected year and value basis. |

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

## 4. Transformation Office Operating Model

The transformation office is the control layer that turns a collection of
initiatives into a managed program of value. In Transmuter, that operating
model is implemented through role-based ownership, stage gates, financial
validation, bankable plans, actual realization entries, dashboards, and meeting
cadence.

### Core roles

| Role | Primary accountability | Main screens | Data owned |
|---|---|---|---|
| Executive Sponsor / CEO / CFO | Approves portfolio ambition, funding, and major tradeoffs. Reviews value, risk, and decisions. | `/dashboard`, `/financials`, `/reports/control-tower`, board pack export | Decision outcomes, escalations, target changes approved outside the system. |
| Transformation Office Director | Owns the portfolio operating cadence and confirms that the program is governed end to end. | `/dashboard`, `/initiatives/pipeline`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower` | Portfolio priorities, stage movement, meeting cadence, executive narrative. |
| PMO Lead / Governance Manager | Maintains stage gates, milestones, risks, dependencies, actions, and meeting follow-up. | `/admin`, `/pmo/governance`, `/progress`, `/meetings`, initiative **Governance**, **Milestones**, **Risks**, **Dependencies** tabs | Gate criteria, submissions, milestones, RAID data, actions, meeting minutes. |
| Finance Lead / Benefits Controller | Owns financial definitions, baseline integrity, benefit validation, cost validation, actuals governance, and board value reconciliation. | `/admin`, `/financials`, `/financials/benefits-register`, `/financials/bankable-plan`, `/financials/benefit-tracking`, initiative **Financials** tab | Metric definitions, scenarios, baselines, benefit validation status, cost categories, actual values, benefit ledger approval evidence. |
| Workstream Lead | Runs a slice of the portfolio and escalates blockers across initiatives. | `/initiatives/pipeline`, `/initiatives/matrix`, `/financials/benefit-tracking`, `/progress/roadmap`, `/reports/control-tower` | Workstream prioritization, progress narrative, cross-initiative blockers, workstream realization commentary. |
| Initiative Owner | Owns delivery, status, milestones, risks, KPIs, assumptions, and source evidence for benefits. | `/initiatives/:id`, initiative **Overview**, **Financials**, **Milestones**, **KPIs**, **Risks**, **Status**, **Team** tabs | Initiative description, owners, dates, delivery status, risks, KPIs, benefit-line assumptions, realization evidence. |
| Business Benefit Owner | Confirms that value has moved into business-as-usual operations and can be sustained. | `/financials/benefit-tracking`, `/financials/benefits-register`, initiative **Financials** and **Summary** tabs | Realization evidence, benefit ownership, sustainment notes, realized-value acceptance. |
| Tenant Administrator | Configures tenant setup, users, dimensions, fiscal settings, governance rules, and access. | `/admin`, `/people` | Tenant settings, users, roles, master data, first-run checklist. |
| Management Viewer | Reviews dashboards and reports without changing data. | `/dashboard`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower`, `/initiatives/pipeline` | No owned data; read-only consumption and challenge questions. |

### Screen ownership

| Screen | Accountable role | Supporting roles | How it is used |
|---|---|---|---|
| `/admin` General, Strategic Parameters, Financial Configuration, Governance Engine | Tenant Administrator / Finance Lead / PMO Lead | Transformation Office Director | Sets tenant identity, business units, workstreams, metrics, scenarios, cost categories, bridge rows, baselines, and gate rules. |
| `/people` | Tenant Administrator | Transformation Office Director | Creates users, assigns tenant roles, and confirms who can manage all initiatives versus assigned initiatives only. |
| `/dashboard` | Transformation Office Director | Executive Sponsor, Workstream Leads | Gives the first executive read on portfolio scale, health, and attention areas. |
| `/initiatives/pipeline` | Transformation Office Director | Workstream Leads, Initiative Owners | Source list for all initiatives; used to filter by BU, workstream, tag, priority, owner, stage, and RAG. |
| `/initiatives/matrix` | Transformation Office Director / Workstream Leads | Finance Lead | Shows portfolio value and initiative distribution by workstream and tag so management can see where value is concentrated. |
| `/initiatives/new` and `/initiatives/:id/edit` | Transformation Office Director | Initiative Owner, Workstream Lead | Creates and maintains initiative master data, ownership, stage, dates, dimensions, and initial value case. |
| `/initiatives/:id/financial-scope` | Finance Lead | Initiative Owner | Controls which metrics and cost categories are tracked for the initiative. |
| Initiative **Financials** tab | Finance Lead | Initiative Owner, Business Benefit Owner | Maintains benefit lines, cost lines, plan/high/actual scenario values, validation status, and assumptions. |
| Initiative **Milestones**, **KPIs**, **Risks**, **Dependencies**, **Status**, **Team** tabs | Initiative Owner / PMO Lead | Workstream Lead | Maintains execution evidence that explains whether the value case is credible. |
| `/financials` | Finance Lead | Transformation Office Director | Reconciles portfolio baseline, planned benefits, actuals, recurring costs, one-off investment, net run-rate value, and contributor detail. |
| `/financials/benefits-register` | Finance Lead / Benefits Controller | Initiative Owners, Business Benefit Owners | Shows each benefit line with plan, actual, validated amount, risk adjustment, evidence, owner, and validation status. |
| `/financials/bankable-plan` | Finance Lead / PMO Lead | Transformation Office Director | Shows locked approved plans and rebaseline history before actual realization is tracked against them. |
| `/financials/benefit-tracking` | Benefits Controller | Finance Lead, Business Benefit Owners | Records and imports realized benefit ledger rows, compares actuals to locked bankable plan, and exposes variances. |
| `/financials/waterline` | Transformation Office Director / Finance Lead | Workstream Leads | Freezes workstream targets after approval so future delivery is compared against a stable target. |
| `/shared-costs` | Finance Lead | Transformation Office Director | Captures shared or cross-portfolio costs that are not naturally owned by a single initiative. |
| `/progress`, `/progress/roadmap`, `/progress/action-items`, `/progress/status-updates` | PMO Lead | Initiative Owners, Workstream Leads | Runs the weekly operating cadence across milestones, actions, status reporting, and roadmap risks. |
| `/meetings` and `/meetings/sessions/:id` | PMO Lead | Transformation Office Director, Workstream Leads | Runs steering committees and workstream reviews, captures agenda, attendees, minutes, decisions, and actions. |
| `/pmo/governance`, `/pmo/risks`, `/pmo/kpis`, `/pmo/ai-insights` | PMO Lead | Finance Lead, Workstream Leads | Provides governance, risk, KPI, and AI-assisted portfolio views for program control. |
| `/reports/control-tower` | Transformation Office Director | Executive Sponsor, Finance Lead, PMO Lead | Management meeting view combining value, progress, risk, blockers, and decision support. |

### Data ownership rules

| Data | Entered by | Reviewed by | System control |
|---|---|---|---|
| Tenant dimensions, workstreams, BUs, markets, themes, tags | Tenant Administrator | Transformation Office Director | Used as filters and rollup dimensions across dashboards and reports. |
| Financial metric definitions, scenarios, cost categories, value bridge rows | Finance Lead | Transformation Office Director | Defines what can be tracked and how values reconcile. |
| Initiative master data and ownership | Transformation Office / Initiative Owner | Workstream Lead | Must be assigned to dimensions before it can be governed as part of the portfolio. |
| Initiative baseline allocation | Finance Lead | Initiative Owner | Must reconcile to tenant FY26 baseline for ACME. |
| Plan Base and Plan High benefit values | Initiative Owner / Finance Lead | Finance Lead | Maintained in the initiative financial grid by metric, scenario, benefit line, year, and month. |
| Actual financial metric values | Finance Lead / Initiative Owner, depending on control model | Finance Lead | Entered in the **Actuals** scenario and compared against plan. |
| Actual recurring and one-off costs | Finance Lead | Transformation Office Director | Entered as actual cost lines or actual cost values; recurring actuals affect net run-rate actuals. |
| Benefit-line validation status | Finance Lead | Benefits Controller | Draft -> Submitted -> Finance validated or Rejected. |
| Bankable plan lock / rebaseline | Finance Lead / PMO Lead | Transformation Office Director | Freezes approved plan snapshots so realization is compared against a stable baseline. |
| Benefit ledger actual realization | Benefits Controller / Business Benefit Owner | Finance Lead | Entered manually or imported by CSV in `/financials/benefit-tracking`; variance is calculated against locked plan. |
| Milestones, risks, KPIs, actions, status updates | Initiative Owner / PMO Lead | Workstream Lead | Explains delivery confidence and blockers behind the financial variance. |

### Operating lifecycle

1. **Setup**: Tenant admin and Finance configure dimensions, users, metric
   definitions, scenarios, cost categories, fiscal calendar, annual baselines,
   and stage gates.
2. **Intake**: Transformation office creates initiatives with owners,
   workstreams, business units, tags, dates, and value hypotheses.
3. **Plan**: Finance and initiative owners configure financial scope, annual
   baselines, benefit lines, cost lines, Plan Base, Plan High, and assumptions.
4. **Validate**: Finance reviews benefit lines in the initiative financial tab
   and `/financials/benefits-register`; PMO confirms gate criteria.
5. **Commit**: Approved initiatives are locked into bankable plans. Rebaseline
   is versioned rather than overwriting the prior approved plan.
6. **Run**: Initiative owners update status, milestones, risks, KPIs, actions,
   and actual financial values. PMO runs meetings and escalates blockers.
7. **Realize**: Benefits controller or business benefit owner enters realized
   benefit ledger rows in `/financials/benefit-tracking`, with actual amounts
   and evidence descriptions.
8. **Report**: Finance uses `/financials`, `/financials/benefits-register`,
   `/financials/benefit-tracking`, and board exports to reconcile value.
   Management uses `/dashboard` and `/reports/control-tower` to run decisions.
9. **Sustain**: Business benefit owner accepts the realized value into BAU,
   unresolved variance remains visible, and lessons learned are recorded in the
   initiative summary.

### Actuals and realization control

There are two related but different actuals concepts:

| Actual type | Where entered | Purpose |
|---|---|---|
| Actual financial scenario values | Initiative **Financials** tab, scenario **Actuals** | Captures actual revenue uplift, gross margin uplift, savings, and actual cost values in the same grid structure as plan. These values drive financial plan-vs-actual reporting. |
| Benefit ledger realization rows | `/financials/benefit-tracking` | Captures realized benefit evidence against the locked bankable plan. These rows are the realization record used for locked baseline versus realized benefit tracking. |

Recommended control:

1. Initiative owner provides the operating evidence and source files.
2. Business benefit owner confirms the value is embedded in operations.
3. Finance lead confirms the calculation and enters or approves actual values.
4. Benefits controller enters or imports benefit ledger rows.
5. Transformation office reviews variance and escalates leakage through the
   steering cadence.

For ACME, use `/financials/benefit-tracking` to show realized actuals against
locked bankable plan values, and use `/financials` to show portfolio financial
plan, actual, cost, and net value reporting.

---

## 5. New Tenant Setup Sequence

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

- ACME currently shows 8/8 setup checks complete.
- Gate criteria are configured and active for the five-stage governance model.

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
- Gate criteria are configured in the current ACME seed: Gate 1 has 2
  criteria, Gate 2 has 3, Gate 3 has 2, Gate 4 has 2, and Gate 5 has 1.
- Use the setup checklist to show that no active gate is missing criteria.

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

## 6. Initiative Setup Sequence

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

## 7. Where to Demonstrate Value

### Screen 1: Executive Dashboard

Screen:

- `/dashboard`

Accountable role:

- Transformation Office Director

Use it for:

- first executive landing view,
- portfolio status,
- high-level transformation posture,
- deciding which value, risk, or delivery area needs deeper review.

Speaker notes:

> This is the executive landing page. It gives management a first read on the
> transformation portfolio before we move into financial proof. It is the
> starting point for the weekly or monthly management cadence: what is healthy,
> what is off track, and what needs an executive decision?

### Screen 2: Initiative Pipeline

Screen:

- `/initiatives/pipeline`

Accountable role:

- Transformation Office Director
- Workstream Leads for their own filtered views

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

Management use:

- Confirms that all value claims are attached to named initiatives.
- Lets the transformation office challenge orphan initiatives with weak
  ownership, stale status, or unclear business-unit accountability.
- Gives workstream leads a filtered backlog for weekly execution review.

### Screen 3: Financial Overview

Screen:

- `/financials`

Accountable role:

- Finance Lead / Benefits Controller

Default demo settings:

| Control | Demo setting |
|---|---|
| Granularity | Yearly |
| Benefits | On |
| Actuals | On |
| Year | 2028 |
| Plan as-of date | Blank unless demonstrating historical cutoff. |
| Stage | All stages for total portfolio; Executing when showing active portfolio. |
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
- Use the contributor drawer to show how the FY28 summary reconciles to the 10
  initiatives. The drawer includes benefit-line detail, recurring costs, net
  run-rate contribution, and Finance validation metadata.
- Use the **Value basis** control when explaining the trend or value bridge:
  select target-year run-rate for the FY28 management story, and switch basis
  only when you want to discuss in-year, cumulative, or all-years values.

Management use:

- CFO view of plan, actual, variance, recurring costs, one-off investment, and
  net value.
- Board view of the baseline-to-value bridge.
- Drilldown view for which initiatives contribute to a selected year, value
  basis, cost category, or stage.
- Export source for the board pack, using the selected year and value basis.

### Screen 4: Financial Overview cost-category drilldown

Screen:

- `/financials`

Accountable role:

- Finance Lead

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

Management use:

- Separates recurring EBITDA drag from one-off investment.
- Identifies whether technology, maintenance, or labor support costs are
  eroding value.
- Supports budget decisions when run costs need owner action.

### Screen 5: Initiative detail financials

Screen:

- `/initiatives/pipeline`
- Open an initiative, for example **ENT-006 Pricing & Discount Optimization**
- Tab: **Financials**

Accountable role:

- Initiative Owner for assumptions and evidence
- Finance Lead for validation and actuals control

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

Management use:

- Audits the story behind a portfolio number.
- Confirms benefit lines, costs, scenario values, actuals, and assumptions.
- Shows whether Finance has validated the benefit before it is treated as
  bankable.

### Screen 6: Initiative financial scope

Screen:

- `/initiatives/:id/financial-scope`

Accountable role:

- Finance Lead

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

Accountable role:

- Finance Lead

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

Accountable role:

- Finance Lead / PMO Lead

Use it for:

- showing whether an initiative has a locked plan snapshot,
- comparing versions after rebaseline,
- navigating to editable financial scope.

Current ACME demo note:

- ACME has locked bankable plan snapshots seeded for the 10 initiatives.
- Use `ENT-005 Enterprise Data Platform` to demonstrate version history and
  rebaseline handling; the current plan is version 2.
- Use this screen as the governance proof that approved value cases are locked
  before realization is tracked.

Speaker notes:

> The bankable plan is the immutable version of an approved value case. Once an
> initiative passes the configured approval gate, the plan becomes the baseline
> for realization tracking. ACME now has locked bankable plans, so we can show
> both the current approved plan and a controlled rebaseline example.

Management use:

- Proves that realization is being compared against an approved version, not a
  moving target.
- Shows when a value case was locked and whether later rebaseline versions were
  controlled.
- Helps the steering committee distinguish approved commitment from working
  forecast.

### Screen 9: Benefits Register

Screen:

- `/financials/benefits-register`

Accountable role:

- Finance Lead / Benefits Controller

Controls:

| Control | Demo use |
|---|---|
| Year | Select `2028` for ACME run-rate view. |
| Validation status | Show all, then filter to Finance validated. |
| Search | Search a benefit line or initiative code when asked for proof. |

Use it for:

- portfolio-wide list of benefit lines,
- Finance validation status,
- evidence and owner metadata,
- plan, actual, validated, risk-adjusted, bankable, and realized values.

Speaker notes:

> The Benefits Register is the finance control sheet for benefits. It is where
> management can see whether a value line is still a draft, has been submitted,
> has been Finance validated, or was rejected. This prevents unvalidated value
> from being presented as bankable.

Management use:

- Separates gross plan from Finance-validated and risk-adjusted value.
- Shows which benefit owner and evidence support each value claim.
- Provides the handoff point from planned benefit to realization tracking.

### Screen 10: Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Accountable role:

- Benefits Controller / Business Benefit Owner

Controls:

| Control | Demo use |
|---|---|
| Scope | Portfolio, Workstream, Initiative |
| Granularity | Monthly, Quarterly, Yearly |
| Workstream | Select a workstream when scope = Workstream |
| Initiative | Select an initiative when scope = Initiative |

Current ACME demo note:

- ACME benefit tracking shows non-zero locked baseline and realized actuals.
- Use yearly granularity first, then drill to quarterly or monthly if the
  management audience wants phasing detail.
- For initiative-level proof, select `ENT-006 Pricing & Discount Optimization`,
  `ENT-008 Procurement Vendor Consolidation`, or `ENT-010 AI Service Desk
  Automation` to show evidence-backed benefit lines.

Speaker notes:

> This is where the operating model moves from planned value to realized value.
> It should compare actual benefit ledger values against locked bankable plans.
> For the ACME demo, this screen is now board-ready: locked plans provide the
> baseline, ledger rows provide actuals, and variance shows where realization is
> ahead of or behind the approved case.

Management use:

- Shows actual realized benefits against the locked plan baseline.
- Lets the benefits controller enter or import actual realization rows.
- Exposes realization gaps by portfolio, workstream, initiative, and period.
- Gives executives one place to ask whether value is real, not just planned.

### Screen 11: Waterline

Screen:

- `/financials/waterline`

Accountable role:

- Transformation Office Director / Finance Lead

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

Management use:

- Locks a workstream target once the steering committee has approved scope.
- Shows which initiatives are above or below the cutoff.
- Helps management decide whether adding initiatives changes the committed
  value target or remains below the line.

### Screen 12: Initiative Portfolio Financial View

Screen:

- `/financials/initiative-portfolio`

Accountable role:

- Finance Lead / Transformation Office Director

Use it for:

- comparing initiatives by value, cost, stage, and contribution,
- identifying concentration risk,
- prioritizing leadership attention across the portfolio.

Speaker notes:

> This view is the financial ranking table. It helps management see which
> initiatives carry the most value, which ones have cost leakage, and which
> ones need executive attention because their financial contribution is material.

### Screen 13: Shared Costs

Screen:

- `/shared-costs`

Accountable role:

- Finance Lead

Use it for:

- costs that support multiple initiatives,
- platform, PMO, licensing, or shared delivery costs,
- preventing shared costs from being hidden inside a single initiative.

Speaker notes:

> Shared costs keep the portfolio economics honest. If a license, platform, or
> central support cost benefits multiple initiatives, Finance should track it
> centrally instead of distorting one initiative's value case.

### Screen 14: Progress, PMO, and Meetings

Screens:

- `/progress`
- `/progress/roadmap`
- `/progress/action-items`
- `/progress/status-updates`
- `/pmo/governance`
- `/pmo/risks`
- `/pmo/kpis`
- `/meetings`
- `/meetings/sessions/:id`

Accountable role:

- PMO Lead / Governance Manager

Use them for:

- milestone progress,
- cross-workstream roadmap review,
- action-item ownership,
- recurring status updates,
- stage gate submissions and approvals,
- risks and blockers,
- KPI actuals,
- steering committee agendas, minutes, and decisions.

Speaker notes:

> These screens explain why value is on track or off track. Financial variance
> is rarely self-explanatory; the PMO views connect the value story to delivery
> evidence, blockers, actions, risks, and decisions.

### Screen 15: Control Tower

Screen:

- `/reports/control-tower`

Accountable role:

- Transformation Office Director

Use it for:

- management meeting view,
- consolidated decision support,
- executive reporting.

Speaker notes:

> The control tower is the management meeting view. It combines portfolio,
> financials, risks, progress, blockers, and decision support into one operating
> cadence.

Management use:

- Runs steering committee reviews from a single page.
- Connects value leakage to execution blockers and decisions.
- Helps executives focus on the few decisions that protect value realization.

---

## 8. Full Management Demo Script

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
- `/financials/benefits-register`
- `/financials/benefit-tracking`
- `/financials/waterline`

Actions:

1. Open **Bankable Plan** and show that ACME initiatives have locked approved
   plan snapshots.
2. Open **Benefits Register** and show validation status, evidence metadata,
   risk-adjusted value, and owner metadata.
3. Open **Benefit Tracking** and show locked baseline versus realized actuals.
4. Show yearly rollup first, then drill to workstream or initiative if asked.
5. Open **Waterline** to explain frozen workstream targets.

Speaker notes:

> The next level of maturity is to lock bankable plans at approval gates and
> then track realized benefits against that locked plan. ACME has locked
> bankable plan snapshots and benefit ledger rows, so this is now the main
> board evidence for realized value. The Benefits Register controls validation;
> Benefit Tracking shows actual realization against the locked baseline.

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

## 9. Recommended Board Questions and Answers

| Board question | Where to answer | Answer pattern |
|---|---|---|
| What is the starting point? | `/financials` baseline cards | FY26 revenue baseline `$20.0M`, gross margin baseline `$9.0M`. |
| What is the FY28 run-rate value? | `/financials`, Year = 2028 | `$8.35M` EBITDA-effective net run-rate value. |
| How much is growth versus cost-out? | `/financials`; initiative financial tabs | Revenue uplift `$4.0M`, GM uplift `$5.4M`, savings `$3.75M`. |
| What costs are recurring? | `/financials`, cost category filter | FY28 recurring run cost `$0.80M`. |
| What investment is needed? | `/financials`, Year = 2027; cost breakdown | One-off investment `$2.5M`. |
| Who owns the value? | `/initiatives/pipeline`; initiative detail | Owner, group owner, BU, and workstream per initiative. |
| Is the plan locked? | `/financials/bankable-plan` | ACME has locked bankable plan snapshots; use `ENT-005` to show version 2 and rebaseline history. |
| Which benefit lines are Finance validated? | `/financials/benefits-register` | Filter by Finance validated and show owner, evidence, plan, actual, validated, risk-adjusted, bankable, and realized values. |
| Is value realized or just planned? | `/financials/benefit-tracking` | ACME has realized actuals in the benefit ledger; compare actuals to locked bankable plan by portfolio, workstream, initiative, and period. |
| Where are risks and blockers? | Initiative **Risks**, **Status**, `/pmo/risks`, `/progress/status-updates` | Show RAG status, risk list, and overdue updates. |

---

## 10. Operating Cadence for a Transformation Office

Weekly:

- Initiative owners update status, risks, dependencies, and action items.
- Transformation office reviews overdue updates and blockers.
- PMO lead prepares workstream or steering committee agendas in `/meetings`.

Bi-weekly:

- Workstream owners review initiative pipeline and milestone progress.
- Finance reviews material changes to benefit and cost assumptions.
- Benefits controller reviews submitted benefit lines and rejects or validates
  them before they are presented as bankable.

Monthly:

- Transformation office reviews `/financials` with Year and Actuals filters.
- Benefits and recurring costs are reconciled by initiative.
- Finance and business benefit owners enter or import realized benefit ledger
  rows in `/financials/benefit-tracking`.
- Benefits Register validation status is reviewed for new or changed value
  claims.
- Steering committee reviews risks, delays, and value leakage.

Quarterly:

- Lock or refresh bankable plans after governance approvals.
- Review waterline target locks by workstream.
- Present board pack with baseline, run-rate value, actuals, variance, risks,
  and decisions required.
- Move realized initiatives through Gate 5 only after actual evidence and BAU
  ownership are confirmed.

---

## 11. Practical Demo Warnings

1. Do not call revenue uplift EBITDA. Revenue becomes EBITDA-effective only
   through margin conversion.
2. Do not subtract one-off investment from FY28 run-rate EBITDA. Use it for
   payback and investment discussion.
3. Do not mix value bases in one management statement. Say whether a chart is
   using target-year run-rate, in-year, cumulative, or all-years value.
4. Do not call unvalidated or rejected benefit lines bankable. Use the Benefits
   Register validation status before making Finance-backed claims.
5. Do not promote ACME demo values as a template for every tenant. New tenants
   should get reusable configuration templates; ACME's portfolio values are
   deterministic sample data for demonstration and acceptance testing.
