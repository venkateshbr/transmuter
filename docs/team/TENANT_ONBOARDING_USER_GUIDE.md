# Transmuter Tenant Onboarding and Portfolio User Guide

Last updated: 2026-06-20

This guide explains how a newly onboarded tenant should configure Transmuter, create or load initiatives, manage financials, and read the available dashboards. It uses the anonymised portfolio workbook `Initiative_Portfolio_Anonymised.xlsx` as a realistic example.

Public application URL: `https://transmuter.ishirock.tech`

For a step-by-step ACME-style demo tenant setup using only the UI, see
[`docs/user-guides/acme-demo-tenant-ui-setup-guide.md`](../user-guides/acme-demo-tenant-ui-setup-guide.md).

## 1. Who This Guide Is For

Use this guide if you are:

- A tenant administrator setting up a new transformation office.
- A transformation office user configuring workstreams, financial metrics, stage gates, and initiative taxonomy.
- An initiative owner creating initiatives and maintaining milestones, KPIs, risks, status updates, and financial values.
- A viewer interpreting dashboards and portfolio reports.

Roles used in the platform:

| Role | Typical user | Capabilities |
|---|---|---|
| `transformation_office` | PMO / transformation office / tenant admin | Configure tenant setup, create and edit initiatives, manage financials, gates, users, meetings, and portfolio reporting. |
| `initiative_owner` | Initiative lead | Maintain owned initiatives, progress, risks, KPIs, milestones, and status updates where permitted. |
| `viewer` | Sponsor / leadership / read-only stakeholder | View initiatives, dashboards, portfolio reports, financials, risks, and KPIs. |
| `platform_admin` | Transmuter operator | Manage tenants and platform-level administration. This is not a normal tenant user. |

## 2. New Tenant Onboarding Flow

### 2.1 Public Signup

1. Open `https://transmuter.ishirock.tech`.
2. Select **Get Started**.
3. Complete the tenant signup and subscription checkout flow.
4. Log in with the initial tenant administrator account.
5. After login, open **Admin** from the main navigation.

New tenants are intentionally not pre-seeded with demo operating data. The tenant must configure its own business units, workstreams, financial model, stage gates, and users before creating initiatives.

### 2.2 First-Run Setup Checklist

Open **Admin**. The top of the Admin screen shows **First-run setup**.

Initiative creation is blocked until these checks are complete:

| Setup item | Why it matters |
|---|---|
| Organization settings | Defines tenant-level identity and strategic parameter storage. |
| Business units | Defines business segments, markets, regions, brands, or functions used for ownership and filters. |
| Workstreams | Defines the main transformation streams used in initiative grouping and dashboards. |
| Financial configuration | Defines metrics, formulas, scenarios, cost categories, bridge rows, reporting currency, and fiscal calendar. |
| Stage gates | Defines the tenant lifecycle from idea through realization. |
| Gate criteria | Defines the checklist that controls movement from one stage to the next. |
| Users | Defines the people available for ownership, sponsorship, approvals, and collaboration. |

Once the checklist is complete, users can create initiatives manually or upload an initiative workbook.

## 3. Example Configuration Based on the Anonymised Portfolio Workbook

The workbook represents a transformation portfolio with:

- 4 workstreams.
- 21 initiatives.
- 9 business units.
- 3 initiative tags.
- Multi-year benefits, costs, KPIs, milestones, risks, and status updates.
- Five governance gates.

### 3.1 Business Units

In the workbook, business units are carried in **Initiative Summary** and **Charter Details**.

Example business units:

| Code | Use in the example portfolio |
|---|---|
| `CAL` | Used by initiatives such as `TOR-1`, `TOR-2`, `TOR-3`, and `TOR-5`. |
| `VER` | Used by `TOR-4` and group initiatives. |
| `MER` | Used by Eastbridge initiatives such as `EBR-1`. |
| `RDG` | Used by Eastbridge initiatives such as document automation and new logos. |
| `FJD` | Used by Northpeak initiatives. |
| `GROUP` | Used for cross-business-unit initiatives. |
| `BNT`, `KLP`, `VSC` | Additional business units found in the workbook. |

Configure these in **Admin -> Strategic Parameters -> Business Units**.

### 3.2 Workstreams

The workbook uses four workstreams:

| Workstream | Example initiative |
|---|---|
| Westmark Region | `TOR-1 - CAL Accounting System Integration & Automation` |
| Eastbridge Region | `EBR-1 - MER Billing System Integration & Automation` |
| Northpeak Region | `NPK-1 - FJD Reconciliation Automation (RPA)` |
| Southgate Region | Additional regional portfolio initiatives in the workbook |

Configure these in **Admin -> Strategic Parameters -> Workstream Management**.

For each workstream, optionally assign:

- Business unit.
- Workstream lead.
- Sponsor.

### 3.3 Markets and Themes

The anonymised workbook does not populate market/country or theme fields. The platform supports these fields, but this workbook could not validate them with real source data.

If your organization needs them, configure examples such as:

| Parameter | Example values |
|---|---|
| Markets | `Hong Kong`, `Singapore`, `UK`, `Europe`, `North America` |
| Themes | `Automation`, `Shared Services`, `Revenue Growth`, `Operating Model`, `Compliance` |

Configure these in **Admin -> Strategic Parameters -> Markets** and **Themes**.

### 3.4 Initiative Tags

The workbook uses these tags:

| Tag | Meaning |
|---|---|
| `automation` | Technology, workflow, system integration, OCR, RPA, or process automation. |
| `commercial` | Revenue growth, new logos, retention, cross-border expansion, and client-facing growth initiatives. |
| `offshoring` | Movement of work to shared-service centers or alternative delivery locations. |

Configure these in **Admin -> Strategic Parameters -> Tags**.

Tags are used in portfolio filters, the dashboard value matrix, and initiative segmentation.

## 4. Financial Configuration

Financial configuration is managed through one tenant-scoped engine under
**Admin -> Financial Configuration**. The engine controls metric definitions,
scenarios, formulas, reporting currency, cost categories, initiative financial
scope, and value bridge rollups.

Legacy financial configuration rows may still exist for upgraded tenants and
older reports, but new tenant setup should use the Financial Configuration
Engine as the source of truth.

### 4.1 Reporting Settings

Set:

| Field | Example from workbook |
|---|---|
| Reporting currency | `USD` |
| Fiscal start | Use your tenant fiscal start month. The workbook uses FY26-FY31 annual views and monthly values. |

The workbook values are expressed as `USD m`. In the platform, money is stored as precise decimal values and returned by the API as strings.

### 4.2 Financial Scenarios

The workbook uses three scenarios:

| Scenario key | Workbook lane | Meaning |
|---|---|---|
| `plan_base` | `Plan Base` / `Base Case` | Conservative or base plan. |
| `plan_high` | `Plan High` / `High Case` | Higher upside plan. |
| `actual` | `Actual` | Actual delivered value or actual cost. |

Create these in **Admin -> Financial Configuration -> Financial Configuration Engine**.

### 4.3 Financial Metrics

The workbook requires these metric keys:

| Metric key | Workbook label | Use |
|---|---|---|
| `revenue_uplift` | Revenue Uplift | Revenue plan and actual values. |
| `gm_uplift_pct` | Gross Margin Uplift | Percentage uplift driver where used. |
| `gross_margin` | Gross Margin | Gross margin value. |
| `gm_uplift` | Gross Margin Uplift / value metric | Gross margin uplift value used in rollups and value bridge. |

In a tenant implementation, define the metrics that matter for your operating model. Examples:

- Revenue Uplift.
- Gross Margin.
- Cost Avoidance.
- EBITDA Uplift.
- Working Capital Release.
- Customer Churn Reduction.
- Process Cycle Time Reduction.

### 4.4 Cost Categories

The workbook has cost rows such as:

- Architecture / Solution Consulting.
- Implementation Cost.
- Licensing & Operation Cost.

However, the workbook's **Cost Category** column is blank. During the test load, cost lines were assigned to the fallback category `other`.

For a production tenant, configure engine cost categories before loading or creating initiatives. Example:

| Cost category | Rollup type | Examples |
|---|---|---|
| Implementation | One-time | Build, implementation, migration, training. |
| Vendor / Consulting | One-time | Advisory, integration partner, external delivery support. |
| Software | Recurring | SaaS licenses, cloud subscriptions, support fees. |
| Labor / Operations | Recurring | Run costs, support pods, offshore operations. |
| Other | No default or fallback | Temporary uncategorized costs. |

### 4.5 Value Bridge Rows

Value bridge rows determine how portfolio value is presented.

Recommended rows for the workbook example:

| Row | Meaning |
|---|---|
| Revenue | Revenue uplift from commercial initiatives. |
| Gross Margin | Margin benefit from automation, offshoring, pricing, and commercial initiatives. |
| One-time Costs | Implementation, vendor, migration, and one-off transition costs. |
| Recurring Costs | Software, support, and ongoing operating costs. |
| Net Value | Benefits minus recurring and one-time costs, depending on report view. |

Use the value bridge to answer: "What is the value of the portfolio after costs?"

### 4.6 Shared Costs

Shared Costs are central costs that support more than one initiative. They are
managed in `/shared-costs` and allocated for burdened executive reporting rather
than entered as direct initiative cost lines by default.

Use Shared Costs for items such as:

- Shared technology platforms.
- PMO and benefits-office run costs.
- Cloud, license, or integration services used across initiatives.
- Central change, training, advisory, or vendor support.

Recommended setup sequence:

1. Configure the relevant cost categories and financial scenarios in
   **Admin -> Financial Configuration**.
2. Open `/shared-costs`.
3. Create a pool with the fiscal year, category, scenario, plan amount, actual
   amount if known, and reporting treatment.
4. Define the allocation policy using guided targets, method, and weights.
5. Preview the allocation and reconcile it to the pool amount.
6. Approve or lock the run before using it in board reporting.

Default interpretation:

- `/financials` remains the direct initiative economics view.
- `/reports/control-tower` shows fully loaded executive economics when locked
  shared-cost allocations are present.
- Bankable Plan remains direct-only unless Finance enables a burdened bankable
  reporting policy.

## 5. Governance and Stage Gates

Configure stage gates in **Admin -> Governance Engine**.

The workbook uses five gates:

| Gate | Label | Stage value used by platform |
|---|---|---|
| Gate 1 | Scoping | `scoping` |
| Gate 2 | Planning | `planning` |
| Gate 3 | In Execution | `in_execution` |
| Gate 4 | Completed | `complete` |
| Gate 5 | Value Realized | `realized` |

The workbook's **Initiative Summary** uses stage number `3` for many initiatives. In Transmuter, that maps to **In Execution**.

The workbook's **Dashboards** sheet defines "completed initiative" as an initiative in **G4**. In the platform, that corresponds to stage `complete`.

### 5.1 Gate Criteria

Each gate can have checklist criteria. Example checklist:

| Gate | Example criteria |
|---|---|
| Gate 1 - Scoping | Problem statement documented; business owner confirmed; high-level value hypothesis captured. |
| Gate 2 - Planning | Milestones created; financial metrics selected; benefit logic documented; risks identified. |
| Gate 3 - In Execution | Delivery plan approved; owner assigned; weekly status cadence active; KPIs defined. |
| Gate 4 - Completed | Milestones complete; completion evidence attached; actual go-live date captured. |
| Gate 5 - Value Realized | Actual benefit recorded; variance explained; benefit confidence updated. |

For each stage gate, configure:

- From stage.
- To stage.
- Whether approval is required.
- Approver roles.
- Whether all criteria must be complete before movement.

## 6. User and Access Setup

Open **People** to invite and manage tenant users.

Open **Admin -> Access Control** to review user role and status.

Recommended operating model:

| User type | Role |
|---|---|
| Transformation office members | `transformation_office` |
| Initiative leads | `initiative_owner` |
| Steering committee / executives | `viewer` |

Assign owners and group owners on initiatives so dashboards, meetings, and status reporting have accountable people.

## 7. Creating Initiatives

Go to **Initiatives -> Create Initiative** or open `/initiatives/new`.

You have two current UI paths:

1. **Create with Transmuter**: guided form with optional AI-assisted suggestions.
2. **Upload Excel Template**: upload a Transmuter single-initiative workbook template.

Important current limitation:

- The UI supports single-initiative creation/import.
- The full `Initiative_Portfolio_Anonymised.xlsx` portfolio reload is currently an operator CLI flow, not a tenant self-service bulk upload page.

### 7.1 Manual Guided Creation

Use **Create with Transmuter** for one initiative at a time.

Step 1 - Basic details:

- Initiative name.
- Workstream.
- Business unit.
- Market.
- Theme.
- Type.
- Impact type.
- Priority.
- Tag.

Example from workbook:

| Field | Example value |
|---|---|
| Initiative name | `CAL Accounting System Integration & Automation` |
| Reference | `TOR-1` |
| Workstream | `Westmark Region` |
| Business unit | `CAL` |
| Type | `cost_reduction` |
| Tag | `automation` |
| Stage | Gate 3 / In Execution |
| RAG | Green |
| Priority | High |
| Owner | Dana Reyes |

Step 2 - Description and context:

- Summary / description.
- Context and problem.
- Value logic / main assumptions.
- Dependencies.

Step 3 - Ownership and timeline:

- Market owner.
- Group owner.
- Planned start date.
- Planned completion date.
- Active financial metrics.
- Active cost categories.

Step 4 - Suggestions:

- Generate suggestions if OpenRouter is configured.
- Review every suggested financial row, cost line, KPI, risk, and milestone before saving.
- AI suggestions are optional; the platform should still work without AI.

### 7.2 Single-Initiative Excel Template Upload

Use **Upload Excel Template** when you want to prepare one initiative offline.

1. Open `/initiatives/new`.
2. Select **Upload Excel Template**.
3. Download the blank template.
4. Fill the workbook.
5. Upload it.
6. Review validation errors.
7. Import only after preview passes.

The single-initiative workbook supports:

- Initiative overview.
- Financial rows.
- Costs.
- KPIs.
- Risks.
- Milestones.
- Status updates.

### 7.3 Bulk Loading a Portfolio Workbook

The anonymised portfolio workbook is loaded today through an operator script:

```bash
cd apps/api
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id <tenant_uuid> \
  --user-id <tenant_admin_user_uuid> \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --dry-run
```

If the dry run is ready:

```bash
cd apps/api
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id <tenant_uuid> \
  --user-id <tenant_admin_user_uuid> \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --confirm-reset
```

Warning: `--confirm-reset` deletes and reloads portfolio data for that tenant. It preserves tenant account records but resets portfolio rows such as initiatives, milestones, risks, KPIs, financial rows, and status updates.

Dry-run readiness checks validate:

- Required metric keys exist.
- Required scenario keys exist.
- Required stage gate numbers exist.
- Workbook structure can be parsed.

The anonymised workbook test loaded:

| Data type | Count |
|---|---:|
| Initiatives | 21 |
| Business units | 9 |
| Workstreams | 4 |
| Initiative-business-unit links | 25 |
| Benefit lines | 63 |
| Financial metric values | 4,694 |
| Cost lines | 867 |
| KPIs | 83 |
| KPI entries | 313 |
| Milestones | 292 |
| Risks | 33 |
| Status updates | 4 |

## 8. Workbook Sheet Mapping

The workbook is not loaded sheet-for-sheet into matching database tables. It is interpreted into Transmuter's operating model.

| Workbook sheet | Platform use |
|---|---|
| `config` | Informs tenant setup: workstreams, impact types, tags, approval flows, gate criteria. |
| `Initiative Summary` | Initiative list, workstream, business units, type, tag, stage, RAG, priority, owner, completion date, summary value columns. |
| `Charter Details` | Detailed initiative charter fields, stage, RAG, priority, type, tag, business units, ownership, assumptions, dependencies. |
| `Financial Summary` | Reviewed as an aggregate/check sheet. Not loaded as a source table. The platform recomputes financial summaries from benefits and costs. |
| `Benefits` | Benefit lines and monthly/annual metric values by scenario. |
| `Costs` | Cost lines, plan/actual lane, one-off/recurring/manual modes, timing, amount, and cost metadata. |
| `KPIs` | KPI definitions and KPI entries. |
| `Milestones` | Milestone plan, actual dates, status, owner, dependencies, and pressure inputs. |
| `Risks` | Risk register entries, impact, likelihood, mitigation, status, and SME consultation flag. |
| `Status Updates` | Initiative status history and weekly summaries. |
| `Dashboards` | Defines desired run-rate and in-year dashboard views. The platform surfaces these through Financials and dashboard components. |
| `to do` | Workbook author notes, not loaded. |
| `DO NOT USE` | Ignored. |

## 9. Maintaining an Initiative After Creation

Open **Initiatives -> Pipeline**, then select an initiative.

The initiative detail page provides these tabs:

| Tab | Use |
|---|---|
| Overview | Core charter, ownership, stage, RAG, value summary, and editable metadata. |
| Financials | Benefit metrics, costs, scenarios, value bridge, exports, and imports. |
| Milestones | Delivery plan, milestone status, dependencies, and checklist progress. |
| KPIs | Leading and lagging metrics, cadence, unit, thresholds, and actual values. |
| Risks | Risk register, impact, likelihood, mitigation, status, and escalation. |
| Status Updates | Weekly or periodic reporting history. |
| Governance | Gate submissions and stage movement evidence. |
| Summary | Consolidated executive summary of the initiative. |

### 9.1 Initiative Financials

Use the **Financials** tab on an initiative to maintain:

- Benefit rows by configured metric.
- Scenario values such as base, high, and actual.
- Cost lines by configured cost category.
- One-time and recurring costs.
- Financial assumptions.
- Value bridge and break-even view.

Example from `TOR-1`:

| Financial item | Example from workbook |
|---|---|
| Revenue Plan - Base | 0 across FY26-FY31 |
| Gross Margin Plan - Base | 0 in FY26, then ramps in FY27-FY31 |
| Gross Margin Actual | 0 in the provided example rows |
| Cost Plan | Implementation and consulting cost rows |
| Cost Actual | Blank in many workbook rows, so actual costs may appear as zero until entered |

### 9.2 KPIs

Example KPIs from `TOR-1`:

| KPI | Type | Unit | Cadence |
|---|---|---|---|
| `% of clients on CoreLedger / Alternative System` | Operational | pct | Quarterly |
| `Automation Coverage` | Operational | pct | Quarterly |
| `Gross Margin` | Operational | pct | Monthly |

Use KPIs to validate whether the initiative is likely to deliver the financial benefit.

### 9.3 Milestones

Examples from `TOR-1`:

- Conduct high-level SOP assessment.
- Develop initial solution options.
- Brainstorm and align solution options.
- Estimate effort and investment requirements.
- Kick off project governance and delivery team.
- Lock solution design and implementation plan.

Milestones drive delivery progress, pressure score, dependency views, and status reporting.

### 9.4 Risks

Examples from `TOR-1`:

- Change adoption and capability gaps.
- Data migration and integration complexity.
- Vendor or platform support dependency.

Risks should include:

- Description.
- Impact.
- Likelihood.
- Mitigation.
- Owner.
- Status.

## 10. Portfolio Dashboards and Reports

### 10.1 Main Dashboard

Route: `/dashboard`

Use this page for a portfolio command-center view.

Available views include:

- Portfolio summary cards.
- Pipeline by stage.
- RAG distribution.
- Pressure and risk heatmap.
- Workstream x tag value matrix.
- KPI pulse.
- My actions.
- Recent activity.
- Executive brief export.

How to interpret:

| Widget | Interpretation |
|---|---|
| Summary cards | Total portfolio count, at-risk items, pending approvals, and value rollups based on dashboard filters. |
| Pipeline by stage | Shows how many initiatives sit in each configured stage. Large volumes in early stages may indicate pipeline immaturity; large volumes stuck in execution may indicate delivery bottlenecks. |
| RAG distribution | Green/amber/red view of initiative health. Red and amber should be reviewed with milestone and risk context. |
| Pressure | Delivery pressure based on milestone health, overdue items, and execution signals. |
| Risk heatmap | Concentration of risks by impact and likelihood. High-impact/high-likelihood risks need active mitigation. |
| Workstream x tag value matrix | Shows value concentration by workstream and tag, such as automation, commercial, and offshoring. Cells can be used to identify where the portfolio value is concentrated. |
| KPI pulse | Highlights KPI coverage and status. Low coverage means benefits may not be measurable. |
| My actions | User-scoped tasks requiring attention. |

Filters:

- Business unit.
- Workstream.
- Priority.
- Tag.

Use filters to answer questions like:

- "What is the Westmark automation value?"
- "Which high-priority commercial initiatives are at risk?"
- "Which business unit has the most red initiatives?"

### 10.2 Financials Overview

Route: `/financials`

Use this page for portfolio-level financial reporting.

Controls:

| Control | Meaning |
|---|---|
| Monthly / Quarterly / Yearly | Changes the reporting grain. |
| Benefits On/Off | Shows or hides benefit columns. |
| Actuals On/Off | Shows actual and variance columns when actual data exists. |
| Year | Filters to a fiscal year and drives `run_rate_year` for value ramp. |
| Plan as-of date | Limits the value-ramp view to periods up to the selected date. |
| Stage | Filters by stage, such as In Execution or Complete. |
| Category | Filters cost categories. |

Panels:

| Panel | Use |
|---|---|
| Summary cards | Benefits, costs, and net value totals for the selected filters. |
| Trend chart | Time-phased portfolio financial trend by month, quarter, or year. |
| In-year value | Total benefits, recurring costs, one-time costs, and net value for the selected year/filter. |
| Run-rate value ramp | Cumulative net value by period. Use stage filter `Complete` to approximate the workbook's "completed initiatives" run-rate view. |
| Planned Financials / Plan vs Actuals table | Period-by-period benefits, recurring costs, one-time costs, total costs, and net run-rate impact. |
| Cost breakdown | Cost categories and rollup contribution. |
| Metric breakdown | Contribution by configured financial metric. |
| Contributor drawer | Click a period row to see which initiatives and cost lines contribute. |

Workbook dashboard mapping:

| Workbook dashboard | Where to view it in platform |
|---|---|
| Run rate value of completed initiatives | `/financials`, **Run-rate value ramp** panel. Use stage filter `Complete` and the required year/as-of filters. |
| In-year value of initiatives | `/financials`, **In-year value** panel. |

Current caveat:

- The workbook has a dedicated `Dashboards` sheet with workstream rows. The platform currently surfaces the core values through the Financials page, but the deployed value-ramp response does not yet expose full workstream-level rollups in the exact workbook layout.

### 10.3 Bankable Plan

Route: `/financials/bankable-plan`

Use this page to review and lock bankable plan snapshots. A locked bankable plan is the baseline for later realization tracking.

Use it when:

- The initiative has passed the planning gate.
- The financial case is ready to freeze.
- Leadership wants plan-vs-actual accountability.

### 10.4 Benefit Tracking

Route: `/financials/benefit-tracking`

Use this page to compare actual realized benefits against locked plan baselines.

Views:

- Portfolio.
- Workstream.
- Initiative.

Interpretation:

- Actual below locked plan means value leakage or delayed realization.
- Actual above locked plan means outperformance or underestimated baseline.
- Missing actuals mean the initiative is not yet being measured after delivery.

### 10.5 Waterline

Route: `/financials/waterline`

Use this page to preview approved initiatives by cutoff date, lock a per-workstream net run-rate target, and compare actual realization against the frozen target line.

Typical use:

1. Select a workstream.
2. Select a cutoff date.
3. Preview initiatives approved by that cutoff.
4. Lock the target snapshot.
5. Track actual value against the locked target.

### 10.6 Shared Costs

Route: `/shared-costs`

Use this page for central costs that should burden multiple initiatives without
hiding those costs in one initiative owner's direct cost case.

Typical workflow:

1. Create the shared-cost pool.
2. Select the allocation method, such as benefit weighted, equal split, fixed
   percentage, manual amount, or another configured method.
3. Select target initiatives or dimensions.
4. Preview the allocation and resolve exceptions.
5. Approve or lock the allocation run.
6. Review the resulting allocated-cost impact in Executive Control Tower.

### 10.7 Control Tower

Route: `/reports/control-tower`

Use this page for executive-level reporting across:

- Portfolio value.
- Burdened value bridge.
- Dependency risk.
- Governance attention.
- High-level health signals.

Use it for leadership readouts rather than day-to-day editing.

### 10.8 Progress Monitor

Routes:

- `/progress`
- `/progress/roadmap`
- `/progress/action-items`
- `/progress/status-updates`
- `/progress/dependencies`

Use these screens to manage delivery execution:

| Page | Use |
|---|---|
| Progress overview | Portfolio delivery health. |
| Roadmap | Timeline of portfolio milestones. |
| Action items | Open, overdue, completed, and cancelled action tracking. |
| Status updates | Reporting cadence and narrative updates. |
| Dependencies | Cross-initiative dependency tracking. |

### 10.9 PMO / Governance Views

Routes:

- `/pmo/governance`
- `/pmo/risks`
- `/pmo/kpis`
- `/pmo/ai-insights`

Use these screens for:

- Gate submissions and approvals.
- Risk register management.
- KPI portfolio view.
- AI-assisted insights where configured.

### 10.10 Meetings

Route: `/meetings`

Use Meetings to manage recurring workstream reviews, steering committees, agenda items, sessions, transcripts, minutes, decisions, and action items.

Meeting features include:

- Meeting series.
- Workstream-scoped meetings.
- Teams sync where Microsoft Graph is connected.
- Transcript import.
- AI-assisted action item, decision, and minutes extraction.
- Series cancellation when supported by provider integration.

## 11. How to Interpret the Example Portfolio

Use the workbook examples to understand realistic operating behavior.

### 11.1 Example: `TOR-1 - CAL Accounting System Integration & Automation`

This is an automation/cost-reduction initiative in Westmark Region.

What to inspect:

1. Open **Initiatives -> Pipeline**.
2. Filter Workstream = `Westmark Region`.
3. Filter Tag = `automation`.
4. Open `CAL Accounting System Integration & Automation`.
5. Review:
   - Overview for charter and ownership.
   - Financials for gross margin, cost rows, and value bridge.
   - Milestones for delivery plan.
   - KPIs for adoption and automation coverage.
   - Risks for data migration, adoption, and vendor dependency.

Expected interpretation:

- Financial benefit is mainly gross-margin / productivity-driven, not revenue-driven.
- Costs are mostly implementation and consulting.
- Benefits depend on system migration and automation adoption.
- Key risks are data migration, vendor dependency, and change adoption.

### 11.2 Example: `TOR-4 - Verland-Norvia New Logos - FDI`

This is a commercial/revenue initiative.

What to inspect:

1. Filter Tag = `commercial`.
2. Open the initiative.
3. Compare Revenue, Gross Margin, Cost Plan, and Net Value.
4. Review KPIs and milestones to determine whether commercial execution supports the plan.

Expected interpretation:

- Revenue and gross margin should both matter.
- Costs may be lower than technology initiatives but still need tracking.
- Pipeline and conversion KPIs are likely more important than operational automation KPIs.

### 11.3 Example: Offshoring Initiatives

Examples include tax, payroll, or bookkeeping offshoring initiatives.

What to inspect:

1. Filter Tag = `offshoring`.
2. Compare workstreams.
3. Review recurring costs and gross margin uplift.
4. Review milestones for transition readiness and stabilization.
5. Review risks for capability ramp, quality, and turnaround.

Expected interpretation:

- Value often ramps after transition milestones complete.
- Realization risk depends on operating stability and handover quality.
- KPIs should measure productivity, quality, SLA adherence, and rework.

## 12. Operating Rhythm After Setup

Recommended cadence:

| Cadence | Activity |
|---|---|
| Weekly | Initiative owners update status, milestones, risks, action items, and actuals where available. |
| Weekly | Workstream leads review workstream dashboard filters and meetings. |
| Bi-weekly | Transformation office reviews RAG, pressure, risks, dependencies, and stalled gate movement. |
| Monthly | Finance reviews portfolio financials, actuals, cost lines, value bridge, and in-year value. |
| Monthly | Steering committee reviews Control Tower, value ramp, benefit tracking, and gate approvals. |
| Quarterly | Rebaseline or lock bankable plans where governance requires it. |

## 13. Quality Checks Before Leadership Reporting

Before using dashboard numbers in a leadership pack, confirm:

- Every initiative has a workstream.
- Every initiative has a business unit or business-unit link.
- Every initiative has a tag.
- Stage gates and gate criteria are active.
- Financial metrics and scenarios are configured.
- Costs have categories other than `other` where possible.
- Planned completion dates are populated.
- Completed initiatives are moved to `complete`.
- Value-realized initiatives are moved to `realized`.
- Actual benefits and actual costs are entered for completed initiatives.
- KPIs have current values and thresholds.
- Risks have owners and mitigations.
- Status updates are current.

## 14. Current Known Gaps and Practical Workarounds

| Gap | Practical workaround |
|---|---|
| Full portfolio workbook upload is not a self-service UI feature yet. | Use the operator CLI load process for initial bulk migration, then maintain initiatives in the UI. |
| Workbook cost categories were blank. | Configure tenant cost categories first, then classify cost lines in the initiative Financials tab. |
| Workbook market/country and theme were blank. | Configure markets/themes in Admin and assign them during initiative review. |
| `Financial Summary` is not loaded as a source table. | Treat it as an Excel check sheet; Transmuter recomputes summaries from Benefits and Costs. |
| Workbook `Dashboards` sheet has workstream rows not fully reproduced as a dedicated UI page. | Use `/financials` for in-year value and run-rate ramp; use Dashboard filters and value matrix for workstream/tag analysis. |
| AI generation depends on OpenRouter availability. | Create initiatives and financials manually if AI is unavailable. Core workflows remain usable. |

## 15. Recommended Setup Sequence for a New Tenant

Follow this sequence for the cleanest implementation:

1. Register the tenant and log in as the initial tenant admin.
2. Open **Admin** and review the setup checklist.
3. Add users in **People** and assign roles.
4. Add business units.
5. Add workstreams and assign leads/sponsors.
6. Add markets, themes, and tags.
7. Configure financial reporting settings.
8. Configure financial scenarios.
9. Configure financial metric rows.
10. Configure cost categories.
11. Configure value bridge rows.
12. Configure stage gates.
13. Configure gate checklist criteria.
14. Confirm setup checklist is complete.
15. Create initiatives manually or import single-initiative templates.
16. For bulk migration, ask the platform operator to run a dry-run and reload using the portfolio workbook loader.
17. Review loaded initiatives in **Initiatives -> Pipeline**.
18. Review financials in **Financials -> Overview**.
19. Review dashboard rollups in **Dashboard**.
20. Start the operating rhythm: status updates, meetings, milestones, risks, KPIs, and actual financials.

## 16. Quick Reference: Where to Go

| Task | Route / navigation |
|---|---|
| Configure tenant setup | **Admin** / `/admin` |
| Add business units, workstreams, markets, themes, tags | **Admin -> Strategic Parameters** |
| Configure financial metrics, scenarios, cost categories, value bridge | **Admin -> Financial Configuration** |
| Configure stage gates and gate checklist | **Admin -> Governance Engine** |
| Invite users | **People** / `/people` |
| Create initiative | **Initiatives -> Create Initiative** / `/initiatives/new` |
| View portfolio pipeline | **Initiatives** / `/initiatives/pipeline` |
| View workstream x tag matrix | `/initiatives/matrix` and dashboard value matrix |
| Maintain initiative financials | Initiative detail -> **Financials** |
| View portfolio financials | **Financials -> Overview** / `/financials` |
| View run-rate ramp | `/financials`, **Run-rate value ramp** panel |
| View in-year value | `/financials`, **In-year value** panel |
| Review bankable plans | `/financials/bankable-plan` |
| Track realized benefits | `/financials/benefit-tracking` |
| Lock workstream target line | `/financials/waterline` |
| Review executive control tower | `/reports/control-tower` |
| Manage milestones and roadmap | `/progress` and `/progress/roadmap` |
| Manage risks | `/pmo/risks` |
| Manage KPIs | `/pmo/kpis` |
| Manage meetings | `/meetings` |
