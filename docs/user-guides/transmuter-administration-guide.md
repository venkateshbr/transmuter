# Transmuter Administration Guide

Last reviewed: 2026-08-08

This is the canonical guide for platform administrators, tenant administrators, Transformation Office administrators, finance leads, and governance leads. It explains configuration and control features using one worked tenant, **ACME Industrial Services**. For daily portfolio work use the [User Operations Guide](transmuter-user-operations-guide.md); for interpretation and customization use the [Dashboard and Reporting Guide](transmuter-dashboard-reporting-guide.md).

## 1. Administration boundaries

| Role | Use administration for | Important boundary |
|---|---|---|
| Platform administrator | Tenant lifecycle and published user guides | Does not operate inside a tenant portfolio |
| Tenant administrator | Organization, users, access, dimensions, integrations, dashboard registry | Does not approve business value merely because access permits configuration |
| Transformation Office | Full tenant setup, portfolio taxonomy, role-default dashboards | Publishes operating standards for the tenant |
| Finance lead | Financial engine, baselines, benefits, costs, shared costs, bankable plans | Uses precise decimal amounts and governed evidence |
| PMO lead | Stage gates, criteria, governance cadence, meetings | Separates lifecycle approval from routine status reporting |

All tenant data is isolated by tenant. Give users the least-privileged role that supports their work. A platform administrator must use the Platform console, not a tenant dashboard.

## 2. ACME worked example

Use these values when learning the setup flow:

| Item | Example |
|---|---|
| Organization | ACME Industrial Services |
| Reporting currency | USD |
| Fiscal year start | January |
| Business units | Manufacturing, Commercial, Corporate |
| Workstreams | Digital Operations, Growth, Cost Transformation |
| Tags | automation, commercial, procurement |
| Example initiative | ACC-101 Invoice Automation |
| Initiative owner | Maya Chen |
| Finance lead | Daniel Ortiz |
| Executive sponsor | Priya Shah |
| Base annual benefit | $1,800,000.0000 |
| One-time implementation cost | $300,000.0000 |
| Recurring annual cost | $120,000.0000 |
| Net annual run-rate value | $1,680,000.0000 |

## 3. First-run tenant setup

Open **Admin** and complete the first-run checklist in this order.

### 3.1 Organization settings

1. Enter the organization name and save it.
2. Set the reporting currency to `USD` and fiscal start month to January for ACME.
3. Confirm timezone and any tenant-level defaults displayed by the form.

Example: a benefit stored as `1800000.0000` is displayed in ACME's reporting currency. Currency conversion is not implied merely by changing a label.

### 3.2 Strategic parameters

Create business units, workstreams, markets, themes, and tags before initiatives. These values drive ownership, filters, dashboard aggregation, and reports.

For ACME:

1. Add business unit **Manufacturing**.
2. Add workstream **Digital Operations**, assign it to Manufacturing, and select its lead and sponsor.
3. Add theme **Operational Excellence**.
4. Add tag key `automation` with label **Automation**.

Use stable keys. Renaming a label is safer than changing a key already referenced by financial configuration or imported records.

### 3.3 Stage gates and criteria

Configure the lifecycle used by your organization. A practical five-stage model is:

| Stage | Meaning | Example exit evidence |
|---|---|---|
| L1 Idea | Opportunity captured | problem, sponsor, initial value range |
| L2 Business Case | Case approved | cost, benefit, owner, risks |
| L3 Execution | Delivery underway | approved plan, milestones, KPIs |
| L4 Implemented | Change deployed | acceptance and operational handover |
| L5 Realized | Value evidenced | validated actual benefits and sustainment |

Add gate criteria under each stage. For ACC-101, the L2-to-L3 submission might require an approved $300,000 implementation cost, named benefit owner, delivery plan, and privacy review. Gate approval is a governance action under **Governance & Cadence → Gate Approvals**, not a dashboard action.

### 3.4 Roadmap scheduling policy

Before teams create milestone dependencies, publish a consistent scheduling convention:

- Require planned start and completion dates for delivery windows.
- Allow a completion-only milestone when it is a genuine event or decision point.
- Use finish-to-start as the default dependency type.
- Use lag for a real waiting period such as stabilization, notice, or approval; do not use lag to conceal an unplanned delay.
- Require owners to correct milestones with neither planned date shown in the Roadmap Explorer's **Needs scheduling** section. A record with one planned date remains visible as a diamond until its full delivery window is known.
- Keep schedule editing in initiative milestone workflows. The portfolio Gantt is a read-only control surface.

ACME policy example: system build-to-pilot dependencies use finish-to-start; deployment-to-adoption may use start-to-start with a documented 30-day lag. Cross-initiative dependencies are permitted when both milestones belong to ACME. The platform rejects self-references, cycles, and links to a milestone outside the active tenant.

### 3.5 People, roles, and invitations

Open **People**:

1. Invite the user with their work email.
2. Select the minimum suitable role.
3. Assign workstream or initiative responsibility where applicable.
4. Ask the invitee to accept the invitation and change any temporary password.
5. Verify the user can see intended pages and cannot see restricted write controls.

ACME example: assign Maya Chen as `initiative_owner`, Daniel Ortiz as `finance_lead`, and Priya Shah as `executive_sponsor`. Do not give Priya finance-write access simply to view the Financial Dashboard.

## 4. Financial Configuration Engine

Open **Admin → Financial Configuration**. This is the source of truth for portfolio financial semantics.

### 4.1 Scenarios

Create scenarios such as:

- `plan_base`: the approved conservative plan.
- `plan_high`: an upside case.
- `actual`: delivered value or incurred cost.

Example: ACC-101 has base annual benefits of $1.8M and high-case benefits of $2.2M. The difference is scenario, not a second benefit definition.

### 4.2 Metrics and formulas

Define metrics such as revenue uplift, gross-margin uplift, cost saving, cost avoidance, working-capital release, or cycle-time reduction. Configure each metric's unit, aggregation, and formula behavior.

Example: `net_run_rate_value = recurring_benefits - recurring_costs`. For ACC-101, `$1,800,000.0000 - $120,000.0000 = $1,680,000.0000`. One-time implementation cost is used in investment/payback analysis; it is not silently deducted from every annual run-rate period.

### 4.3 Cost categories

Create explicit categories and classify them as recurring or one-time:

| Category | Type | ACME example |
|---|---|---|
| Implementation | One-time | $300,000 systems integrator |
| Software | Recurring | $120,000 annual platform license |
| Internal labor | One-time or recurring by policy | project team or service desk |
| Other | Controlled fallback | temporary uncategorized item |

Review fallback `other` rows regularly; an uncategorized cost weakens the cost-breakdown dashboard.

### 4.4 Value bridge and baselines

Configure bridge rows to explain movement from baseline to target, including which metrics contribute positively or negatively. Set annual revenue and gross-margin baselines for years used in target reporting.

ACME example: FY2027 baseline revenue of $100M plus $4M revenue uplift produces $104M target revenue. A $1.8M cost saving belongs in benefits/net value and must not also be added to target gross margin unless the configured formula explicitly does so.

### 4.5 Financial scope

Financial scope controls which configured metrics and categories an initiative may use. For ACC-101 enable cost saving, implementation cost, and software cost. Avoid enabling every metric for every initiative; a smaller scope makes entry and review clearer.

### 4.6 Metric lifecycle: hide before delete

Unsaved metric rows can be discarded locally. Saved system metrics cannot be
deleted. For a saved custom metric, choose **Delete metric** to run the full
dependency check. Benefit lines, values, initiative scope and baselines,
formulas, value-bridge membership, shared-cost rules, and historical allocations
all block deletion. The dialog identifies the records that must be changed and
offers **Hide instead**.

Example: ACME cannot delete `cost_savings` while ACC-101 has a Cost Savings
benefit line or while a Net Value formula references it. Finance should hide the
metric if it is being retired. If the metric was a disposable unused pilot,
type its exact immutable key in the confirmation field and permanently delete
it. The dialog discloses any tenant annual-baseline rows that will be removed;
no surviving initiative data is cascaded.

For the field-by-field workflow and dependency examples, see the historical
deep reference [Admin Financial Configuration User Guide](admin-financial-configuration-user-guide.md#56-hide-discard-or-permanently-delete-a-metric).

## 5. Dashboard administration

The tenant navigation publishes only:

- **Operational Dashboard**
- **Financial Dashboard**
- **Initiative Portfolio** (unchanged)

Entry and maintenance pages belong under **Transformation Management**, **Financial Operations**, or **Governance & Cadence**. In **Admin → Dashboard Configuration**, administrators can enable a destination, change its label or icon, restrict allowed roles, and assign it to `dashboard`, `financial_operations`, `transformation_management`, `governance_cadence`, `primary`, or `hidden`. The legacy `operations` value remains API-readable for compatibility but is migrated to `financial_operations`.

The recommended registry is:

| Destination | Menu group |
|---|---|
| Operational Dashboard, Financial Dashboard, Initiative Portfolio | Dashboard |
| Initiative Pipeline, Progress Monitor, Roadmap & Milestones, Action Items, Status Updates, Risk Register, KPI Management | Transformation Management |
| Benefit Ledger, Benefits Register, Bankable Plans, Waterline & Target Locks, Shared Costs | Financial Operations |
| Gate Approvals, Meetings | Governance & Cadence |
| Investments & Payback analysis, compatibility Control Tower route | Hidden; reached by dashboard drill-through |

### Publishing a role-default layout

1. Open Operational or Financial Dashboard.
2. Select **Customize layout**.
3. Drag a widget or use the arrow buttons to reorder it.
4. Use **Resize** to cycle through small, medium, wide, and full widths.
5. Select **Publish role default**.

Required decision widgets cannot be hidden. A personal layout overrides a role default; **Reset** removes the personal layout and returns to the published role default or system standard.

## 6. Shared-cost administration

Use **Financial Operations → Shared Costs** to create cost pools, allocation rules, and posting runs. Do not enter shared costs from a dashboard.

Example: allocate a $240,000 PMO platform pool across Digital Operations and Growth using the approved driver. Preview the run, check recipients and rounding, post it once, and preserve the posting evidence. If the driver changes, create a governed correction/re-run according to policy rather than editing displayed dashboard totals.

## 7. Bankable plans and target locks

A bankable plan is an approved, versioned commitment. A waterline compares that locked commitment with current pipeline and realized value.

For ACC-101:

1. Confirm validated base benefits and recurring costs.
2. Review the calculated $1.68M annual net run-rate.
3. Preview the workstream target under **Financial Operations → Waterline & Target Locks**.
4. Lock only after finance/governance approval.
5. If assumptions materially change, use **Bankable Plans** to create a governed rebaseline; never overwrite historical commitment silently.

## 8. Governance and meetings configuration

Configure gate approvers and criteria before initiatives submit. Use Meetings for recurring governance forums, agendas, attendees, live sessions, decisions, transcripts, and resulting action items.

If Microsoft 365 is enabled, complete organizer consent and verify tenant policy permits the intended calendar, Teams, and transcript functions. Native Transmuter meetings remain available if the external integration is unavailable.

## 9. AI and integration controls

AI features are advisory and must degrade gracefully. Database writes require a human checkpoint. Do not place personal information in prompts sent to external models. Confirm Langfuse tracing and integration secrets through environment configuration; never paste secrets into a guide, issue, or browser form not designed for secrets.

## 10. Administration validation checklist

- A viewer can read dashboards but cannot publish layouts or edit financial records.
- An initiative owner can update assigned initiatives but not unrelated ones.
- Finance can enter and validate benefits and costs under Financial Operations.
- Required dashboard widgets remain visible.
- Personal layout reset falls back to the role or system layout.
- All money retains four-decimal precision in storage and string representation in APIs.
- A second tenant cannot read ACME records.
- Dashboard totals reconcile to the ledger, cost lines, and selected filters.
- Every gate decision, target lock, rebaseline, and shared-cost posting has an accountable audit trail.

## 11. Troubleshooting

| Symptom | Check |
|---|---|
| Initiative creation is blocked | Complete every first-run setup item |
| User cannot see a page | Role, permission, dashboard allowed roles, and invitation state |
| Financial total appears wrong | Currency, fiscal year, scenario, category, as-of date, and initiative financial scope |
| Layout will not publish | User must be Transformation Office or tenant administrator; required widgets must remain visible |
| Dashboard has no actuals | Benefit/cost actual records, validation status, and selected period |
| Teams/transcript action fails | Organizer consent, Microsoft policy, and integration health; continue with native meeting workflow |
