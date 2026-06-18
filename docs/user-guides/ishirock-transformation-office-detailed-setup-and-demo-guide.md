# Ishirock Transformation Office Detailed Setup And Demo Guide

This guide is a complete end-to-end walkthrough for setting up and demonstrating
the `ishirock` transformation tenant in Transmuter using
`Initiative_Portfolio_Anonymised.xlsx` as the business source of truth.

It expands the shorter Ishirock value guide with:

- the exact screens to use,
- what values to configure,
- which roles own which data,
- how benefits, costs, baselines, actuals, and realization are tracked,
- how dashboards and reports should be validated,
- a management runbook for running the program.

No credentials are included in this guide.

---

## 1. Current Ishirock Readiness State

Read-only inspection on June 18, 2026 showed:

| Area | Current `ishirock` state |
|---|---:|
| Workbook initiatives present | 21 of 21 |
| Total initiatives in tenant | 23 |
| Business units | 10 |
| Workstreams | 4 |
| Benefit lines | 63 |
| Financial metric values | 4,696 |
| Cost lines | 925 |
| KPIs | 83 |
| KPI entries | 313 |
| Milestones | 292 |
| Risks | 34 |
| Status updates | 4 |
| Tenant annual baselines | 0 |
| Initiative annual baselines | 0 |
| Bankable plans | 0 |
| Benefit realization ledger rows | 0 |
| Workstream target locks | 0 |

Readiness interpretation:

- Initiative master data and most workbook operating data are already loaded.
- The remaining work is baseline setup, Finance validation, bankable plan
  locking, actuals entry, benefit realization, waterline target locks, and
  browser validation.
- `/dashboard` now reads the configurable financial engine for value bridge and
  workstream/tag matrix values.

---

## 2. Executive Storyline

Use this storyline for management:

> Ishirock has a 21-initiative transformation portfolio across Westmark,
> Eastbridge, Northpeak, and Southgate. The FY25 baseline is `$67.466M` revenue,
> `$87.960M` workbook margin/value baseline, `$13.265M` cost plan, and
> `$74.695M` net value. By FY28, the Plan Base case shows `$15.004M` revenue
> uplift, `$21.633M` gross margin value, `$3.560M` cost plan, and `$18.073M`
> net value.

Board-level value message:

```text
FY28 Plan Base Net Value
= Gross Margin - Cost Plan
= $21.633M - $3.560M
= $18.073M
```

Upside value message:

```text
FY28 Plan High Net Value
= Gross Margin - Cost Plan
= $29.283M - $3.560M
= $25.723M
```

Do not double-count the `PORTFOLIO TOTAL` row in `Initiative Summary`; use the
21 initiative rows only.

---

## 3. Ishirock Portfolio Summary

| Dimension | Count | FY28 net value |
|---|---:|---:|
| Total workbook initiatives | 21 | `$18.073M` |
| Westmark Region | 6 | `$4.880M` |
| Eastbridge Region | 5 | `$4.762M` |
| Northpeak Region | 6 | `$4.906M` |
| Southgate Region | 4 | `$3.525M` |
| Automation tag | 7 | `$4.715M` |
| Commercial tag | 10 | `$6.406M` |
| Offshoring tag | 4 | `$6.952M` |

The detailed initiative list is in
`docs/user-guides/ishirock-transformation-value-demonstration-guide.md`.

---

## 4. Transformation Office Operating Model

The transformation office is the control layer that turns initiatives into a
governed program of value. In Transmuter, that operating model is implemented
through role-based ownership, stage gates, Finance validation, bankable plans,
actual realization entries, dashboards, and meeting cadence.

### Core roles

| Role | Primary accountability | Main screens | Data owned |
|---|---|---|---|
| Executive Sponsor / CEO / CFO | Approves ambition, funding, value claims, and major tradeoffs. | `/dashboard`, `/financials`, `/reports/control-tower`, board pack export | Decision outcomes, escalations, and approved target changes. |
| Transformation Office Director | Owns the portfolio cadence and confirms the program is governed end to end. | `/dashboard`, `/initiatives/pipeline`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower` | Portfolio priorities, stage movement, executive narrative, steering actions. |
| PMO Lead / Governance Manager | Maintains stage gates, criteria, milestones, risks, actions, dependencies, and meeting follow-up. | `/admin`, `/pmo/governance`, `/progress`, `/meetings`, initiative governance tabs | Gate rules, submissions, milestones, RAID data, action items, meeting notes. |
| Finance Lead / Benefits Controller | Owns financial definitions, baseline integrity, benefit validation, costs, actuals governance, and reconciliation. | `/admin`, `/financials`, `/financials/benefits-register`, `/financials/bankable-plan`, `/financials/benefit-tracking`, initiative **Financials** tab | Metric definitions, scenarios, baselines, benefit validation, cost categories, actual values, realization evidence. |
| Workstream Lead | Runs a regional slice of the portfolio and escalates blockers. | `/initiatives/pipeline`, `/initiatives/matrix`, `/financials/benefit-tracking`, `/progress/roadmap`, `/reports/control-tower` | Regional progress, blockers, cross-initiative dependencies, workstream realization commentary. |
| Initiative Owner | Owns delivery, status, milestones, risks, KPIs, assumptions, and source evidence. | `/initiatives/:id`, initiative **Overview**, **Financials**, **Milestones**, **KPIs**, **Risks**, **Status**, **Team** tabs | Initiative description, dates, delivery status, risks, KPIs, assumptions, evidence. |
| Business Benefit Owner | Confirms that value has moved into business-as-usual operations. | `/financials/benefit-tracking`, `/financials/benefits-register`, initiative **Financials** tab | Realization evidence, sustainment notes, realized-value acceptance. |
| Tenant Administrator | Configures tenant setup, users, dimensions, fiscal settings, governance rules, and access. | `/admin`, `/people` | Tenant settings, users, roles, business units, workstreams, checklist completion. |
| Management Viewer | Reviews dashboards and reports without changing data. | `/dashboard`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower`, `/initiatives/pipeline` | No owned data. Reviews and challenges the management narrative. |

### Screen ownership

| Screen | Accountable role | Supporting roles | How it is used |
|---|---|---|---|
| `/admin` General, Strategic Parameters, Financial Configuration, Governance Engine | Tenant Administrator / Finance Lead / PMO Lead | Transformation Office Director | Sets tenant identity, workstreams, business units, metrics, scenarios, baselines, bridge rows, cost categories, and gates. |
| `/people` | Tenant Administrator | Transformation Office Director | Creates users, assigns tenant roles, and confirms who can manage initiatives. |
| `/dashboard` | Transformation Office Director | Executive Sponsor, Workstream Leads, Finance Lead | Gives the first executive read on portfolio scale, health, risk, KPI pulse, value bridge, and workstream/tag matrix. |
| `/initiatives/pipeline` | Transformation Office Director | Workstream Leads, Initiative Owners | Source list for all initiatives and filters by BU, workstream, tag, priority, owner, stage, and RAG. |
| `/initiatives/matrix` | Transformation Office Director / Workstream Leads | Finance Lead | Shows initiative distribution and value by workstream and tag. |
| Initiative detail pages | Initiative Owner | Workstream Lead, PMO Lead, Finance Lead | Maintains charter, delivery evidence, financial scope, benefit lines, costs, milestones, risks, KPIs, status, and team. |
| `/financials` | Finance Lead | Transformation Office Director | Reconciles portfolio baseline, planned benefits, actuals, costs, net value, and contributor detail. |
| `/financials/initiative-portfolio` | Finance Lead | Initiative Owners | Shows initiative-level financials, FY25 baselines, FY28 plan values, and readiness gaps. |
| `/financials/benefits-register` | Finance Lead / Benefits Controller | Initiative Owners, Business Benefit Owners | Tracks benefit lines, validation, evidence, risk adjustment, bankable value, and realized value. |
| `/financials/bankable-plan` | Finance Lead / PMO Lead | Transformation Office Director | Locks approved plans and shows rebaseline history. |
| `/financials/benefit-tracking` | Benefits Controller | Finance Lead, Business Benefit Owners | Records realized benefit ledger rows and compares actuals to locked plan. |
| `/financials/waterline` | Transformation Office Director / Finance Lead | Workstream Leads | Freezes workstream targets and tracks delivery above or below target. |
| `/progress`, `/pmo`, `/meetings` | PMO Lead | Initiative Owners, Workstream Leads | Runs milestones, actions, status, risks, governance, and meeting cadence. |
| `/reports/control-tower` | Transformation Office Director | Executive Sponsor, Finance Lead, PMO Lead | Management meeting view combining value, progress, risk, blockers, and decisions. |

### Data ownership rules

| Data | Entered by | Reviewed by | System control |
|---|---|---|---|
| Business units, workstreams, markets, themes, tags | Tenant Administrator | Transformation Office Director | Drives filters and rollups. |
| Financial metric definitions, scenarios, cost categories, value bridge rows | Finance Lead | Transformation Office Director | Defines what can be tracked and how values reconcile. |
| Tenant FY25 annual baseline | Finance Lead | Executive Sponsor / CFO | Establishes the portfolio baseline. |
| Initiative FY25 baseline allocation | Finance Lead | Initiative Owner | Must reconcile to the workbook baseline for the 21 initiatives. |
| Initiative master data | Transformation Office / Initiative Owner | Workstream Lead | Establishes ownership, region, BU, tag, stage, priority, and dates. |
| Plan Base and Plan High values | Initiative Owner / Finance Lead | Finance Lead | Maintained in configurable financial values by metric, scenario, year, and month. |
| Actual financial scenario values | Finance Lead / Initiative Owner | Finance Lead | Entered in the `actual` scenario for plan-vs-actual reporting. |
| Cost plan and actual cost values | Finance Lead | Transformation Office Director | Cost plan affects net value; actual costs affect realized net value. |
| Benefit validation status | Finance Lead / Benefits Controller | Transformation Office Director | Draft, submitted, validated, rejected, and evidence statuses control report confidence. |
| Bankable plan lock / rebaseline | Finance Lead / PMO Lead | Transformation Office Director | Freezes the approved plan so actuals are compared against a stable target. |
| Benefit ledger actual realization | Benefits Controller / Business Benefit Owner | Finance Lead | Captures realized value, evidence, and variance against locked plan. |
| Milestones, risks, KPIs, actions, status updates | Initiative Owner / PMO Lead | Workstream Lead | Explains delivery confidence and blockers behind financial variance. |

### Operating lifecycle

1. **Setup**: Configure dimensions, users, financial metrics, scenarios, costs,
   fiscal calendar, annual baselines, and stage gates.
2. **Intake**: Confirm all 21 workbook initiatives exist once and are assigned
   to the right region, BU, tag, owner, stage, priority, and RAG.
3. **Plan**: Configure initiative financial scope, FY25 baselines, benefit
   lines, cost lines, Plan Base, Plan High, and assumptions.
4. **Validate**: Finance validates benefit lines and cost logic in initiative
   financials and `/financials/benefits-register`.
5. **Commit**: Approved initiatives are locked into bankable plans. Rebaseline
   creates a new version rather than overwriting prior commitments.
6. **Run**: Initiative owners update status, milestones, risks, KPIs, actions,
   and actual financial values.
7. **Realize**: Business benefit owners and benefits control enter realization
   ledger rows in `/financials/benefit-tracking`.
8. **Report**: Finance reconciles `/financials`, Benefits Register, Bankable
   Plan, and Benefit Tracking. Management uses `/dashboard` and Control Tower.
9. **Sustain**: Realized value is accepted into BAU and unresolved variance
   remains visible until closed.

---

## 5. New Tenant Setup Sequence

Use this sequence if creating a new tenant to match the Ishirock workbook state.
If working in the existing `ishirock` tenant, use the same sequence as a
validation checklist.

### Step 1: Sign in and open Admin

Screen:

- `/auth/login`
- `/admin`
- Admin tab: **General**

Actions:

1. Sign in as a tenant administrator or transformation office user.
2. Open **Admin**.
3. Confirm the organization identity and setup checklist.
4. Confirm the first-run setup checklist eventually shows complete.

Expected result:

- Admin, People, Financials, Dashboard, Initiative Pipeline, and initiative edit
  pages are accessible.

### Step 2: Configure strategic dimensions

Screen:

- `/admin`
- Admin tab: **Strategic Parameters**

Workstreams:

- Westmark Region
- Eastbridge Region
- Northpeak Region
- Southgate Region

Business units:

- BNT
- CAL
- FJD
- GROUP
- KLP
- MER
- RDG
- VER
- VSC

Core tags:

- automation
- commercial
- offshoring

Validation:

- No duplicate workstreams with different casing.
- No duplicate business units with different casing.
- Pipeline filters and dashboard filters show these dimensions.

### Step 3: Configure financial reporting settings

Screen:

- `/admin`
- Admin tab: **Financial Configuration**

Recommended settings:

| Setting | Value |
|---|---|
| Reporting currency | USD |
| Fiscal year start month | January unless the tenant requires otherwise |
| Baseline year | FY25 |
| Run-rate demo year | FY28 |
| Primary plan scenario | Plan Base |
| Upside scenario | Plan High |
| Actual scenario | Actual |

Validation:

- `/financials` can show FY26, FY27, and FY28.
- `/financials/initiative-portfolio` can show FY25 baseline fields after
  baselines are entered.

### Step 4: Configure metric definitions

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Metric Definitions**

Minimum metric definitions:

| Metric key | Label | Aggregation | Benefit class | Purpose |
|---|---|---|---|---|
| `revenue_uplift` | Revenue Uplift | Sum | Revenue | Commercial/revenue value. |
| `gross_margin` | Gross Margin | Sum | Margin | Workbook gross margin value. |
| `gm_uplift` | Gross Margin Uplift | Sum | Margin | Incremental margin uplift where used. |
| `cost_savings` | Cost Savings | Sum | Savings | Savings value where used. |
| `baseline_revenue` | Baseline Revenue | Last | None | FY25 revenue baseline. |
| `baseline_margin_value` | Baseline Margin / Value | Last | None | Workbook FY25 margin/value baseline, if Finance wants it tracked separately. |

Rules:

- Dashboard financial widgets read active benefit metrics from the configurable
  engine.
- Formula metrics should stay formula metrics. Do not expect formula metrics to
  independently drive dashboard benefit totals.
- Revenue-class metrics are shown as revenue drivers. Margin and savings
  benefit metrics drive benefit and net value views.

### Step 5: Configure scenarios

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Scenarios**

Required scenarios:

| Label | Key | Purpose |
|---|---|---|
| Baseline | `baseline` | FY25 starting point. |
| Plan Base | `plan_base` | Main management plan. |
| Plan High | `plan_high` | Upside management plan. |
| Actual | `actual` | Realized or latest actual values. |

Validation:

- All required scenarios are active.
- `/dashboard` value bridge and matrix have non-zero Plan Base and Plan High
  values when FY28 values exist.

### Step 6: Configure tenant annual baseline

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Annual Baselines**

Enter FY25 tenant baseline values in whole dollars:

| Baseline field | Workbook value | Platform entry |
|---|---:|---:|
| Baseline Revenue | `$67.466M` | `67466000` |
| Baseline Margin / Value, only if Finance confirms | `$87.960M` | `87960000` |
| Baseline Cost Plan, if configured | `$13.265M` | `13265000` |
| Baseline Net Value, if configured | `$74.695M` | `74695000` |

Validation note:

- The workbook `Gross Margin FY25 Base` total exceeds FY25 revenue.
- Cost-reduction initiatives carry `$50.250M` of FY25 margin/value baseline
  with `$0.000M` FY25 revenue baseline.
- Do not configure this as conventional gross margin unless Finance confirms
  that workbook definition.

Validation:

- Refresh and confirm FY25 baseline values remain visible.
- `/financials/initiative-portfolio` shows FY25 baseline options after
  initiative baselines are entered.

### Step 7: Configure value bridge rows

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Value Bridge Rows**

Recommended rows:

| Row | Source |
|---|---|
| Revenue Uplift | `revenue_uplift` |
| Gross Margin | `gross_margin` or `gm_uplift` depending on tenant convention |
| Cost Savings | `cost_savings` if used |
| Costs | cost lines |
| Net Value | benefits less cost plan |

Validation:

- `/financials` value bridge labels match the management language.
- `/dashboard` and `/financials` use configurable metrics and cost lines.

### Step 8: Configure governance stage gates

Screen:

- `/admin`
- Admin tab: **Governance Engine**

Recommended five-stage model:

| Gate | From | To | Purpose |
|---|---|---|---|
| Gate 1 | Identified | Validated | Idea has owner, scope, and value hypothesis. |
| Gate 2 | Validated | Planned | Finance and PMO agree the case is credible. |
| Gate 3 | Planned | Committed | Approved for execution and bankable plan lock. |
| Gate 4 | Committed | Executing | Delivery is active and tracked. |
| Gate 5 | Executing | Realized | Value is embedded and evidenced. |

Validation:

- Gate criteria exist for each gate.
- Initiative stage values from the workbook map cleanly to the configured stage
  model.

### Step 9: Configure users and roles

Screen:

- `/people`

Minimum role setup:

| Role | Access expectation |
|---|---|
| Tenant admin | Admin and People setup. |
| Transformation office | Full portfolio management. |
| Finance lead | Financial configuration, validation, bankable plan, benefit tracking. |
| PMO lead | Governance, meetings, milestones, risks, actions. |
| Workstream leads | Regional initiative oversight. |
| Initiative owners | Assigned initiative updates and evidence. |
| Viewer | Read-only management reporting. |

Validation:

- Transformation office user can access all 21 initiatives.
- Initiative owner access is scoped to assigned initiatives.
- Viewer can open reports without mutating data.

---

## 6. Initiative Setup Sequence

Repeat this sequence for each of the 21 workbook initiatives, or use it as a
validation pass when data is already loaded.

### Step 1: Confirm initiative master data

Screen:

- `/initiatives/pipeline`
- `/initiatives/:id/edit`

Validate:

- Reference code and initiative name match the workbook.
- Workstream is one of the four regions.
- Business unit matches workbook BU.
- Tag is automation, commercial, or offshoring.
- Owner, stage, RAG, priority, and planned completion are populated.
- There is no duplicate initiative for the same workbook reference.

### Step 2: Configure financial scope

Screen:

- `/initiatives/:id/financial-scope`

Actions:

1. Select relevant benefit metrics.
2. Select relevant cost categories.
3. Save scope.

Validation:

- Initiative **Financials** tab shows the expected metrics and cost categories.
- Unused metrics are not cluttering the financial grid.

### Step 3: Configure initiative annual baseline

Screen:

- `/initiatives/:id/edit`
- Annual Baseline section

Actions:

1. Set baseline year to `2025`.
2. Enter workbook FY25 baseline values where present.
3. Save and refresh.

Validation:

- Initiative annual baselines appear in `/financials/initiative-portfolio`.
- The sum of initiative baselines reconciles to:
  - `$67.466M` revenue baseline,
  - `$87.960M` workbook margin/value baseline, if Finance chooses to track it,
  - `$13.265M` cost plan baseline,
  - `$74.695M` net baseline.

### Step 4: Add and validate benefit lines

Screen:

- Initiative **Financials** tab
- `/financials/benefits-register`

Actions:

1. Confirm the benefit lines from the workbook are present.
2. Submit draft benefit lines if needed.
3. Finance reviews assumptions, value logic, and evidence.
4. Finance marks benefit lines validated or sends them back for correction.

Validation:

- Benefits Register shows all 63 benefit lines.
- Benefit lines have owners, evidence, and validation status.
- Benefit values reconcile with the FY28 workbook case.

### Step 5: Add cost lines

Screen:

- Initiative **Financials** tab

Actions:

1. Confirm plan cost lines from the workbook are present.
2. Classify each cost line as one-off, recurring, annual spread, or manual as
   appropriate.
3. Enter actual cost values where actuals are known.

Validation:

- FY28 cost plan reconciles to `$3.560M`.
- Cost values appear in `/financials`, dashboard value bridge, and matrix
  drilldowns.

### Step 6: Enter actuals

Screen:

- Initiative **Financials** tab
- Scenario: **Actual**

Actions:

1. Enter actual revenue, gross margin, savings, and cost values where known.
2. Use the same metric definitions and periods as plan values.
3. Save and refresh.

Validation:

- `/financials` Actual values update.
- `/dashboard` Actual value bridge and value matrix update.
- Actuals remain zero only where the business has not provided realized data.

### Step 7: Lock bankable plan

Screen:

- Initiative governance / gate approval flow
- `/financials/bankable-plan`

Actions:

1. Confirm benefit lines and cost logic are Finance validated.
2. Move the initiative through the required gate approval.
3. Lock the bankable plan snapshot.

Validation:

- Bankable Plan shows the approved plan.
- Rebaseline history is versioned if the approved plan changes.

### Step 8: Enter benefit realization

Screen:

- `/financials/benefit-tracking`

Actions:

1. Select initiative and benefit line.
2. Enter period, realized amount, and evidence narrative.
3. Submit or approve according to the Finance control model.

Validation:

- Realized value appears against the locked bankable plan.
- Variance is visible.
- Business benefit owner has confirmed sustainment.

### Step 9: Validate operating evidence

Screens:

- Initiative **Milestones**
- Initiative **KPIs**
- Initiative **Risks**
- Initiative **Status**
- `/progress`
- `/pmo`

Validation:

- Milestones have owners, dates, status, and evidence where available.
- KPIs have base/high/actual lanes.
- Risks have impact, likelihood, status, and mitigation.
- Status updates explain current RAG and next actions.

---

## 7. Dashboard And Report Validation

### Screen 1: Executive Dashboard

Screen:

- `/dashboard`

Validate:

- Total initiatives and at-risk counts populate.
- Pipeline by stage and RAG breakdown populate.
- Risk heatmap and KPI pulse populate.
- FY28 value bridge is non-zero for Plan Base and Plan High when financial
  values exist.
- Workstreams x Value Tags matrix shows regional/tag values.
- Matrix cell drilldown shows contributing initiatives, benefit values, costs,
  and net values.

Speaker notes:

> This is the executive landing page. It summarizes portfolio health and value,
> and it lets management drill from a regional/tag value cell into the
> initiatives behind the number.

### Screen 2: Initiative Pipeline

Screen:

- `/initiatives/pipeline`

Validate:

- 21 workbook initiatives are visible without duplicates.
- Filters work for each region, BU, tag, RAG, stage, and priority.
- Owners and planned completion are populated.

Speaker notes:

> This is the operating list for the transformation office. It answers who owns
> each initiative, where it sits in the governance lifecycle, and which region or
> value lever it belongs to.

### Screen 3: Financial Overview

Screen:

- `/financials`

Recommended controls:

- Granularity: Yearly
- Year: 2028
- Scenario/value basis: Plan Base first, then Plan High and Actual

Validate:

- FY28 Plan Base reconciles to workbook financial summary after configuration:
  - revenue `$15.004M`,
  - gross margin `$21.633M`,
  - cost plan `$3.560M`,
  - net value `$18.073M`.
- Actuals remain zero or partial only where actual values are not loaded.
- Contributor drawer shows initiative-level detail.

Speaker notes:

> Finance uses this screen to reconcile the management value case. It is the
> main place to prove that benefits, costs, actuals, and net value tie together.

### Screen 4: Initiative Portfolio Financial View

Screen:

- `/financials/initiative-portfolio`

Validate:

- 21 workbook initiatives are visible.
- FY25 baseline fields are populated after baseline entry.
- FY28 values reconcile by initiative.
- Sort and filter by region, BU, tag, and owner.

Speaker notes:

> This view turns the portfolio into an initiative-level financial ledger. It is
> useful when management asks which initiatives explain the value.

### Screen 5: Initiative Detail Financials

Screen:

- `/initiatives/:id`
- Tab: **Financials**

Validate:

- Benefit lines match workbook intent.
- Plan Base, Plan High, and Actual scenarios are visible.
- Cost lines are present.
- Finance validation status is visible.
- Assumptions and evidence are captured.

Speaker notes:

> This is where the value case lives at initiative level. Finance can challenge
> the benefit logic, the owner can provide evidence, and the transformation
> office can see whether the case is ready for governance.

### Screen 6: Benefits Register

Screen:

- `/financials/benefits-register`

Validate:

- 63 benefit lines are visible.
- Draft/submitted/validated status is clear.
- Risk adjustment, evidence, owners, bankable value, and realized value are
  populated as the readiness pass progresses.

Speaker notes:

> This is Finance's benefit control register. It prevents unvalidated value from
> being presented as committed transformation value.

### Screen 7: Bankable Plan

Screen:

- `/financials/bankable-plan`

Validate:

- Approved initiative plans appear after gate approval.
- Locked values and rebaseline history are visible.
- Actual realization is compared against the locked plan, not a moving target.

Speaker notes:

> Bankable plan is the commitment layer. Once approved, the plan is locked so
> delivery and actuals can be measured against the same baseline.

### Screen 8: Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Validate:

- Benefit realization ledger rows exist for demo initiatives or all 21
  initiatives if running the full readiness pass.
- Realized values, periods, and evidence are populated.
- Variance against locked bankable plan is visible.

Speaker notes:

> This is where the transformation office proves that benefits have landed. It
> should be owned by Finance, benefits control, and business benefit owners.

### Screen 9: Waterline

Screen:

- `/financials/waterline`

Validate:

- Four workstream target locks exist.
- Regional targets are compared against realized or actual values.
- Above-waterline and below-waterline views are meaningful.

Speaker notes:

> Waterline freezes regional commitments. It is the right view for asking which
> regions are above target, below target, or blocked.

### Screen 10: Progress, PMO, And Meetings

Screens:

- `/progress`
- `/progress/roadmap`
- `/progress/action-items`
- `/progress/status-updates`
- `/pmo/governance`
- `/pmo/risks`
- `/pmo/kpis`
- `/meetings`

Validate:

- Milestones, actions, status updates, risks, and KPIs are visible.
- Meeting agenda, attendees, decisions, and action items can be captured.
- PMO views explain the operational reasons behind financial variance.

Speaker notes:

> Financial value is only credible if execution evidence supports it. These
> screens show the work, risks, decisions, and cadence behind the value case.

### Screen 11: Control Tower

Screen:

- `/reports/control-tower`

Validate:

- Value, risk, stage, KPI, and action information is visible.
- The view supports a management meeting without jumping across too many pages.
- Open risks and decisions are clear.

Speaker notes:

> This is the steering committee view. It brings value, progress, risk, and
> required decisions into one operating view.

---

## 8. Full Management Demo Script

### Opening

> Today we are reviewing the Ishirock transformation office. The tenant contains
> a 21-initiative regional portfolio across Westmark, Eastbridge, Northpeak, and
> Southgate. The FY25 baseline is `$74.695M` net value, and the FY28 Plan Base
> case is `$18.073M` net value.

### Segment 1: Portfolio structure

Open:

- `/dashboard`
- `/initiatives/pipeline`

Show:

- 21 initiatives,
- four regional workstreams,
- automation, commercial, and offshoring tags,
- stage, RAG, owner, priority, and filters.

Speaker notes:

> The transformation office can slice the portfolio by region, business unit,
> value lever, owner, and status. This makes the program governable rather than
> just a spreadsheet of initiatives.

### Segment 2: Baseline and run-rate value

Open:

- `/financials`
- `/financials/initiative-portfolio`

Show:

- FY25 baseline values,
- FY28 Plan Base values,
- FY28 Plan High upside,
- initiative-level contribution.

Speaker notes:

> Finance can reconcile the portfolio from baseline to FY28 run-rate value. The
> run-rate case is not just a total; every number traces back to initiatives,
> benefit lines, and costs.

### Segment 3: Regional value concentration

Open:

- `/dashboard`
- Workstreams x Value Tags matrix

Show:

- Regional rows,
- automation, commercial, and offshoring columns,
- one cell drilldown.

Speaker notes:

> Management can see whether value is concentrated by region or value lever. The
> drilldown shows exactly which initiatives create the number.

### Segment 4: Initiative value case

Open one initiative detail page.

Show:

- charter,
- financial scope,
- benefit lines,
- costs,
- milestones,
- KPIs,
- risks,
- status updates.

Speaker notes:

> This is how we challenge the credibility of a value claim. We can inspect the
> owner, assumptions, delivery plan, risks, KPIs, and evidence before Finance
> validates the benefit.

### Segment 5: Benefit validation and bankable plan

Open:

- `/financials/benefits-register`
- `/financials/bankable-plan`

Show:

- validation status,
- evidence,
- risk-adjusted values,
- locked plan snapshots,
- rebaseline history.

Speaker notes:

> Benefits move from draft to validated to bankable. Once a plan is locked,
> realization is measured against that locked plan rather than a changing target.

### Segment 6: Actuals and realization

Open:

- Initiative **Financials** tab with Actual scenario
- `/financials/benefit-tracking`
- `/financials/waterline`

Show:

- actual scenario entry,
- realization ledger rows,
- variance against bankable plan,
- workstream target locks.

Speaker notes:

> Ishirock still needs an actuals readiness pass. Actual financial values and
> benefit realization ledger rows must be entered before the tenant can be used
> as a complete end-to-end actuals demo.

### Close

Open:

- `/reports/control-tower`

Close with:

> The management run is: govern the initiatives, validate the benefits, lock the
> bankable plan, capture actuals, prove realization, and use dashboard and
> control tower views to run decisions.

---

## 9. Management Runbook

### Weekly workstream review

Audience:

- Workstream lead,
- initiative owners,
- PMO lead,
- Finance representative.

Screens:

- `/initiatives/pipeline`
- `/progress/roadmap`
- `/progress/action-items`
- `/pmo/risks`
- initiative detail pages.

Agenda:

1. Review initiatives by workstream.
2. Confirm milestone progress and overdue actions.
3. Review RAG changes and blockers.
4. Confirm benefit assumptions that changed.
5. Assign actions and owners.
6. Escalate risks requiring transformation office support.

Outputs:

- Updated status,
- updated risks,
- updated milestones,
- new action items,
- clear escalations.

### Biweekly Finance and benefits control

Audience:

- Finance lead,
- benefits controller,
- initiative owners,
- business benefit owners.

Screens:

- initiative **Financials** tab,
- `/financials`,
- `/financials/benefits-register`,
- `/financials/bankable-plan`,
- `/financials/benefit-tracking`.

Agenda:

1. Review draft and submitted benefit lines.
2. Validate assumptions and evidence.
3. Confirm cost plan and actual cost updates.
4. Lock or rebaseline bankable plans where approved.
5. Enter actual scenario values.
6. Enter benefit realization ledger rows.
7. Review variance against bankable plan.

Outputs:

- Validated or rejected benefit lines,
- updated actuals,
- locked plan snapshots,
- realization ledger rows,
- variance actions.

### Monthly transformation office review

Audience:

- Transformation office director,
- Finance lead,
- PMO lead,
- workstream leads,
- selected initiative owners.

Screens:

- `/dashboard`,
- `/financials`,
- `/financials/waterline`,
- `/reports/control-tower`.

Agenda:

1. Review portfolio health, stage movement, and RAG.
2. Review FY28 Plan Base and Plan High value.
3. Review actuals and realization where loaded.
4. Review waterline by region.
5. Review top risks, blocked milestones, and required decisions.
6. Confirm executive narrative for the next steering committee.

Outputs:

- Updated management narrative,
- escalated decisions,
- target lock updates,
- steering committee actions.

### Quarterly steering committee

Audience:

- Executive sponsor,
- CFO,
- transformation office director,
- Finance lead,
- PMO lead,
- workstream leads.

Screens:

- `/dashboard`,
- `/financials`,
- board pack export,
- `/reports/control-tower`.

Agenda:

1. Confirm portfolio value versus baseline.
2. Review Plan Base, Plan High, and Actual.
3. Review value by region and tag.
4. Review bankable plan and realization variance.
5. Decide on funding, scope, rebaseline, and escalation items.

Outputs:

- Approved decisions,
- funding changes,
- rebaseline approvals,
- executive action list.

---

## 10. Completion Criteria

Minimum UI-tested readiness:

- Setup checklist complete.
- 21 workbook initiatives reviewed with no duplicates.
- FY25 tenant baseline entered.
- At least one initiative per region has:
  - FY25 baseline entered,
  - benefit lines Finance validated,
  - bankable plan locked,
  - actual scenario values entered if actuals are being demoed,
  - benefit realization ledger row entered.
- Four workstream target locks created.
- `/dashboard`, `/financials`, `/financials/initiative-portfolio`,
  `/financials/benefits-register`, `/financials/bankable-plan`,
  `/financials/benefit-tracking`, `/financials/waterline`, and
  `/reports/control-tower` validated in the browser.

Full ACME-style readiness:

- All 21 workbook initiatives have FY25 baselines entered.
- All 63 benefit lines are Finance validated.
- All 21 workbook initiatives have bankable plans locked.
- Actual scenario values are entered for initiatives where actual performance
  should be demonstrated.
- Benefit ledger rows exist for all initiatives where realization should be
  demonstrated.
- Waterline target locks exist for all four regional workstreams.
- Management runbook has been exercised through the UI.

---

## 11. Practical Demo Warnings

- Do not double-count the `PORTFOLIO TOTAL` row in `Initiative Summary`.
- Do not present missing actuals as underperformance. Missing actuals mean the
  actuals readiness pass is incomplete.
- Use configurable metric values and cost lines for `/dashboard` financial
  validation.
- Do not treat benefit validation, bankable plan, and realization as the same
  control. They are separate gates.
- Do not call the tenant demo-complete until browser validation confirms the
  dashboard, financials, benefit tracking, waterline, and control tower views all
  populate from the configured data.
