# Transmuter Platform Overview

Last updated: 2026-05-10  
Branch context: `2a`  
Primary inputs: repository source, `docs/team/CODEX_CONTEXT.md`, `docs/team/ARCHITECTURE.md`, GitHub issues #1-#157, and current market reference pages listed in [Competitive Context](#competitive-context).

## 1. Executive Summary

Transmuter is a multi-tenant enterprise transformation platform for transformation offices, initiative owners, management teams, and investors. It combines initiative lifecycle management, financial value realization, governance, dependency management, meeting/action discipline, dashboards, and AI-assisted workflows into one operating system for transformation delivery.

The current platform has moved beyond basic initiative tracking. It now supports:

- Multi-tenant SaaS onboarding, billing, tenant provisioning, and platform administration.
- Initiative pipeline, matrix, detail pages, import/export, AI-guided intake, and owner-scoped visibility.
- Financial modeling with base, high, and actual cases; configurable financial taxonomies; portfolio rollups; value bridge; break-even analysis; assumptions; and workbook import/export.
- Milestones, milestone dependencies, deterministic pressure scoring, KPIs, risks, status updates, action items, meetings, governance gates, and people/workload views.
- Phase 2A Executive Control Tower capabilities: initiative-to-initiative dependencies, shared cost pools, allocation runs, value realization notes, burdened value reporting, and persona reports for owners, management, and investors.

The product thesis is simple: transformation leadership needs a control tower that reconciles delivery, value, risk, and accountability. Spreadsheets can model value, project tools can track tasks, and portfolio suites can show plans, but Transmuter is built around the daily transformation office question: "Which initiatives will deliver value, what is blocking them, who owns the next move, and what is the fully burdened economics?"

## 2. User Personas And Roles

### Platform Admin

Operates the SaaS platform. Platform admins can view tenant signup and subscription state, inspect tenant deletion previews, and clean demo or regression tenants. They do not operate individual transformation portfolios unless separately provisioned inside a tenant.

### Transformation Office / Tenant Admin

Owns the transformation operating rhythm. This role can create and manage initiatives, users, workstreams, strategic parameters, gate criteria, financial configuration, shared cost pools, allocation rules, dependencies, governance submissions, and management reports.

### Initiative Owner

Owns execution of assigned initiatives. Initiative owners see owned initiatives, dependencies touching their initiatives, allocated costs for owned initiatives, due updates, milestones, actions, KPIs, risks, and owner cockpit reporting. They can update assigned dependency resolution notes and statuses within constrained permissions.

### Viewer

Consumes portfolio information without mutation rights. Viewers can see dashboards and reports permitted by tenant-level RBAC but cannot create or update transformation records.

## 3. Platform Architecture

Transmuter uses a modern SaaS architecture:

- Backend: FastAPI 0.115+ on Python 3.12+.
- Frontend: Angular standalone components with lazy routes and CSS variable design tokens.
- Database and auth: Supabase PostgreSQL 15+ with Supabase Auth and RLS.
- Financial precision: PostgreSQL `NUMERIC(15,4)`, Python `decimal.Decimal`, and string money values in JSON responses.
- AI layer: PydanticAI agents through OpenRouter with Langfuse tracing and HITL checkpoints for DB writes.
- Background work: Procrastinate.
- Deployment context: production Docker images behind Cloudflare hostnames.

Core architectural rules:

- Every tenant-scoped table carries `tenant_id uuid NOT NULL`.
- Every API query is scoped to the current tenant.
- RLS policies are mandatory for all tenant tables.
- Routers remain thin; business logic belongs in service classes; persistence belongs in repositories.
- Financial calculations never use floats.

## 4. Product Surface

### Public SaaS And Billing

The public flow supports marketing homepage, get-started signup, Stripe checkout, subscription success, webhook-driven tenant provisioning, and platform-admin tenant operations.

Key capabilities:

- Subscription signup using Stripe sandbox/product configuration.
- Checkout session creation and webhook processing.
- Tenant provisioning from successful checkout events.
- Platform console for tenant overview and deletion preview.
- Same-origin production API proxy support.
- Tenant deletion cleanup across initiatives, users, financials, KPIs, risks, milestones, meetings, action items, governance, billing, audit/AI, and master data groups.

### Authentication And Tenant Isolation

Transmuter uses Supabase Auth with JWT claims for tenant and role. The API exposes login, current profile, and profile update flows. Tenant isolation is enforced in service/repository queries and database RLS.

Key roles:

- `platform_admin`
- `transformation_office`
- `initiative_owner`
- `viewer`

RBAC patterns:

- Transformation office can create and manage portfolio data.
- Initiative owners are scoped to initiatives where they are `owner_id` or `group_owner_id`.
- Viewers are read-only.
- Platform admin routes are separate from tenant operating routes.

### Initiative Portfolio

The initiative module is the system of record for transformation work.

Current capabilities:

- Pipeline view.
- Matrix view.
- Initiative creation and editing.
- CSV and workbook import/export.
- AI-guided intake suggestions.
- Detail pages with tabs for overview, financials, milestones, KPIs, risks, status updates, governance, team/people, and summary/results.
- Archive and delete controls with RBAC.
- Strategic parameter picklists for business unit, workstream, tag, country, stage, priority, RAG, and owner fields.
- Initiative summary editing for target outcomes, latest narrative, next steps, decisions needed, and executive-facing descriptions.

Core initiative dimensions:

- `initiative_code`
- name and description
- business unit and workstream
- owner and group owner
- stage
- RAG status
- priority
- tag
- country
- start/end dates
- pressure score
- value realization fields introduced in Phase 2A: benefit confidence and realization status

### Financials And Value Realization

Financials are one of Transmuter's central differentiators. The platform models transformation economics at initiative and portfolio level rather than merely storing budget fields.

Current capabilities:

- Multi-period financial grid with monthly, quarterly, and annual records.
- Base case, high case, and actual values.
- Revenue uplift, gross margin, gross margin percentage, gross margin uplift, and COGS.
- Direct cost lines with category, plan, actual, period, and recurring/non-recurring classification.
- Tenant-configurable financial groups, metrics, and cost categories.
- Value bridge at initiative and portfolio level.
- Scenario summaries for base, high, and actual.
- Break-even and run-rate analysis.
- Financial cell assumptions/comments.
- XLSX financial workbook export/import.
- Alchemist workbook support and reconciliation.
- Portfolio financial page with period rollups, summary cards, cost breakdowns, metric breakdowns, and contributor drilldowns.

### Executive Control Tower

Phase 2A adds enterprise control-tower capabilities for cross-initiative execution and fully burdened economics.

#### Initiative Dependency Network

Initiative-to-initiative dependencies are first-class records, separate from milestone dependencies.

Supported dependency types:

- `blocks`
- `enables`
- `informs`
- `duplicates`
- `requires_decision`

Supported statuses:

- `proposed`
- `active`
- `at_risk`
- `blocking`
- `resolved`
- `cancelled`

Each dependency captures:

- upstream initiative
- downstream initiative
- type
- status
- severity
- owner
- due date
- resolution notes
- optional linked milestone
- optional linked action item

Rollups include:

- total dependencies
- blocking dependencies
- at-risk dependencies
- overdue dependencies
- resolved dependencies
- critical path risk
- blocked initiatives
- top blockers
- blast radius

Cycle prevention is enforced before dependency creation. A dependency cannot point to itself, and adding a new edge is rejected if it creates a circular initiative graph.

#### Shared Cost Pools And Allocation

Shared cost pools model transformation costs that cannot be directly tied to one initiative but must be included in investor and management economics.

Examples:

- technology platforms
- group PMO costs
- vendor retainers
- cloud or AI infrastructure
- shared implementation teams
- corporate overhead

Allocation methods:

- fixed percentage
- equal split
- manual amount
- benefit weighted
- revenue weighted
- headcount weighted

Allocation rules include filters and weights. Filters scope the candidate initiatives. Weights drive manual, fixed, and headcount-style allocations. Allocation runs generate auditable allocated-cost rows without overwriting direct cost lines.

Supported run scenarios:

- plan
- actual

Supported period dimensions:

- year
- quarter
- month

#### Persona Reports

Three report endpoints support distinct operating cadences:

- Owner cockpit: owner-specific blockers, due updates, open actions, stale KPIs, unresolved dependencies, and value plan vs actual.
- Executive control tower: management view of value bridge, dependency risk, RAG pressure, top contributors, cost allocation, and governance exceptions.
- Investor summary: board-facing view of delivered value vs plan, pipeline by stage, major risks/dependencies, management actions, capital/expense burden, and net burdened value.

All reports support filters for:

- business unit
- workstream
- tag
- country
- owner
- RAG status
- stage
- target year

### Dashboard And Analytics

The dashboard aggregates portfolio health and execution signals.

Current widgets and aggregates include:

- total initiatives
- at-risk initiatives
- pending approvals
- pipeline by stage
- RAG breakdown
- portfolio pressure
- risk heatmap
- KPI pulse
- value bridge
- workstream-by-tag value matrix
- my milestones
- my actions
- recent activity
- available filters

The workstream-by-tag matrix groups rows by workstream and columns by tags such as automation, offshoring, commercial, and other. It calculates base, high, and actual gross-margin uplift by target year, and each cell includes initiative contributors with gross margin, recurring costs, one-time costs, and net value components.

### Milestones, Dependencies, And Progress

The progress module tracks execution detail below the initiative level.

Capabilities:

- milestone CRUD
- milestone checklist items
- milestone dependency graph
- portfolio milestone tracker
- roadmap view
- action item list
- status update compliance
- dependency visualization
- deterministic milestone pressure score

Milestone dependencies are separate from Phase 2A initiative dependencies. They support operational execution sequencing inside or across initiatives, while initiative dependencies represent portfolio-level governance relationships.

### KPIs

KPIs capture non-financial and operational performance.

Capabilities:

- KPI CRUD per initiative.
- KPI type and unit metadata.
- Quarterly KPI entries.
- Base, high, and actual KPI values.
- Portfolio KPI pulse.
- Dashboard status based on latest actual vs base case.

### Risks

Risks capture delivery and value uncertainty.

Capabilities:

- initiative risk register
- portfolio risk register
- risk heatmap
- impact and likelihood fields
- rating auto-calculation
- mitigation and owner tracking

Risk rating is derived from impact and likelihood and then used in initiative pressure scoring and heatmap aggregation.

### Governance

The governance module manages stage-gate discipline.

Capabilities:

- configurable gate criteria
- initiative gate criteria listing
- gate submissions
- approval/rejection decisions
- portfolio governance dashboard
- overdue governance visibility

Phase 2A extends gate expectations:

- G1 requires dependency review and shared-cost applicability review.
- G2 requires value-realization explanation and allocation reconciliation.

### Meetings And Collaboration

The meetings module supports the cadence layer around transformation delivery.

Capabilities:

- meeting series
- meeting detail pages
- live meeting sessions
- agenda items
- attendees
- linked initiatives
- action items
- meeting notes workflows

The intended operating model is that SteerCo, value reviews, and working sessions produce action items and updates that connect back to initiatives, milestones, and dependencies.

### People And Workload

The people module manages users, roles, workstream assignment, invites, profile data, and workload/pressure.

Capabilities:

- user directory
- user profile
- invite flow
- ghost/deactivate user operations
- workstream assignments
- user pressure score
- role-aware visibility

### Admin And Configuration

Tenant admins can configure the operating model instead of hardcoding it.

Capabilities:

- organization settings
- billing visibility
- launch readiness
- portfolio cleanup preview and execution
- strategic parameter management
- tag and picklist management
- gate criteria editor
- financial configuration editor
- cost category and metric deactivation
- audit log visibility

### AI-Assisted Workflows

Transmuter has an agentic foundation for AI workflows but treats AI as assistive, not blocking.

Current and planned workflows from the issue trail include:

- initiative field extraction
- KPI suggestion
- risk pattern scan
- initiative intake and HITL review
- meeting transcript chunking
- action item extraction
- decision extraction
- meeting notes extraction
- status update drafting
- portfolio RAG assistant
- executive summary generation
- Langfuse tracing and evaluation datasets
- correction-rate monitoring

Governance rules:

- agents never block core platform functionality
- external LLM calls are traced
- PII is masked before external calls
- human approval is required for agent actions that write to the database
- correction rate above 10% triggers a project incident issue

## 5. Calculation Catalogue

### Money Precision

All money calculations follow a strict precision contract:

- PostgreSQL: `NUMERIC(15,4)`
- Python: `decimal.Decimal`
- API JSON: string values

This prevents floating-point drift and keeps financial totals reconcilable in dashboards, reports, and workbook exports.

### Financial Grid Metrics

For each period, initiatives can store:

- `revenue_uplift_base`
- `revenue_uplift_high`
- `revenue_uplift_actual`
- `gross_margin_base`
- `gross_margin_high`
- `gross_margin_actual`
- `gm_uplift_base`
- `gm_uplift_high`
- `gm_uplift_actual`
- `cogs_base`
- `cogs_high`
- `cogs_actual`

Cost lines store:

- category
- period
- planned amount
- actual amount
- recurring flag

### Initiative Financial Summary

The initiative financial summary aggregates across all periods.

Key calculations:

- plan revenue uplift = sum of base revenue uplift
- high revenue uplift = sum of high revenue uplift
- actual revenue uplift = sum of actual revenue uplift
- plan gross margin = sum of base gross margin
- high gross margin = sum of high gross margin
- actual gross margin = sum of actual gross margin
- plan gross margin uplift = sum of base gross margin uplift
- high gross margin uplift = sum of high gross margin uplift
- actual gross margin uplift = sum of actual gross margin uplift
- COGS = revenue uplift minus gross margin where applicable
- recurring costs = sum of recurring cost lines
- one-off costs = sum of non-recurring cost lines
- total costs = recurring costs + one-off costs
- net value = gross margin uplift minus recurring costs

One-off costs are shown separately in the summary because they matter for cash impact and break-even, while recurring cost drag is used for run-rate value.

### Value Bridge

The value bridge has base, high, and actual cases.

For each case:

- revenue uplift = sum of relevant revenue uplift values
- gross margin = sum of relevant gross margin values
- gross margin uplift = sum of relevant GM uplift values
- recurring costs = sum of recurring cost lines for plan or actual
- one-off costs = sum of non-recurring cost lines for plan or actual
- total costs = recurring costs + one-off costs
- net = gross margin uplift - recurring costs

Dashboard-level value bridge uses:

- `benefits_base` = sum of `gm_uplift_base`
- `benefits_high` = sum of `gm_uplift_high`
- `benefits_actual` = sum of `gm_uplift_actual`
- `costs_plan` = sum of direct planned costs
- `costs_actual` = sum of direct actual costs
- `net_base` = benefits base - planned costs
- `net_high` = benefits high - planned costs
- `net_actual` = benefits actual - actual costs

Executive Control Tower value bridge adds allocated shared costs:

- benefits plan = sum of `gm_uplift_base`
- benefits actual = sum of `gm_uplift_actual`
- direct costs plan/actual = sum of direct cost lines
- allocated costs plan/actual = sum of allocation rows
- total burdened costs = direct costs + allocated shared costs
- net before allocation = benefits - direct costs
- net after allocation = benefits - direct costs - allocated shared costs

### Scenario Summary

Scenario summary accepts `base`, `high`, or `actual`.

For the selected scenario:

- revenue uplift = sum selected revenue metric
- gross margin = sum selected gross margin metric
- GM uplift = sum selected GM uplift metric
- COGS = revenue uplift - gross margin
- recurring costs = recurring planned costs for base/high, recurring actual costs for actual
- one-off costs = one-off planned costs for base/high, one-off actual costs for actual
- total costs = recurring + one-off
- net value = GM uplift - recurring costs

### Break-Even Analysis

Break-even is calculated across sorted periods.

For each period:

- period GM uplift = selected scenario GM uplift
- period costs = selected scenario direct cost amount
- cumulative GM uplift += period GM uplift
- cumulative costs += period costs
- cumulative net = cumulative GM uplift - cumulative costs
- break-even period = first period where cumulative net is at least zero after costs have been incurred

Run-rate fields expose the latest cumulative benefit and cost movement for the selected scenario.

### Portfolio Financials

Portfolio financials aggregate initiative financial entries and cost lines into monthly, quarterly, or yearly buckets.

For each bucket:

- benefits plan = sum of base GM uplift
- benefits actual = sum of actual GM uplift
- recurring costs plan/actual = sum of recurring cost lines
- one-off costs plan/actual = sum of non-recurring cost lines
- total costs = recurring + one-off
- net value = benefits - total costs

The service also returns:

- broader period totals for rows whose granularity does not match the selected bucket.
- cost breakdown by configured cost category.
- metric breakdown by configured metric group/item.
- contributor drilldowns by initiative and cost line.

### Workstream-By-Tag Value Matrix

The dashboard matrix selects a target year from available financial rows or from the requested filter.

For each initiative:

- annual rows are preferred when present; otherwise period rows are summed.
- base/high/actual values use GM uplift.
- recurring and one-time costs are split by cost-line flag.
- net value base/high/actual = GM uplift - recurring costs - one-time costs.

Rows are grouped by workstream. Columns are grouped by tag. Cells include totals plus initiative-level contributor details.

### KPI Pulse

KPI pulse compares the latest actual KPI entry against base case.

For each KPI:

- if no actual entry exists: status = `no_data`
- if latest actual >= latest base: status = `on_track`
- otherwise: status = `at_risk`

Portfolio health score:

```text
tracked = hitting_base + missing_base
health_score = 0 if tracked == 0 else hitting_base / tracked * 100
```

The score is rounded to one decimal place.

### Risk Rating And Heatmap

Risks carry impact and likelihood. The dashboard heatmap groups risk counts by `impact_likelihood`. Risk ratings are used in initiative pressure:

- high open risk = 0.8 pressure contribution
- medium open risk = 0.3
- low open risk = 0.1
- risk exposure is capped at 2.0

### Milestone Pressure Score

Milestone pressure is deterministic on a 0-10 scale.

Components:

- blast radius, max 3.5: direct dependents count 1.0 each; indirect dependents count 0.4 each; capped at 3.5.
- dependent urgency, max 2.5: downstream due date urgency, with overdue and near-term downstream milestones scoring higher.
- cluster bonus, max 1.5: struggling sibling milestones in the same initiative add 0.5 each.
- slack penalty, max 1.5: rises as planned end approaches or passes; completed milestones score 0.
- checklist, max 0.5: incomplete checklist fraction times 0.5.
- self status, max 0.5: status-derived penalty, including not-started-after-start-date behavior.

Final:

```text
milestone_pressure = blast_radius
                   + dependent_urgency
                   + cluster_bonus
                   + slack_penalty
                   + checklist
                   + self_status
```

The score is capped at 10 and rounded to one decimal place.

### Initiative Pressure Score

Initiative pressure is deterministic on a 0-10 scale.

Components:

- schedule, max 2.5: expected progress by elapsed time compared with completed milestone percentage; falls back to due-date proximity when milestone data is limited.
- milestone health, max 2.0: proportion of non-complete milestones that are overdue, due within 7 days, or high pressure.
- risk exposure, max 2.0: weighted open risk count.
- KPI performance, max 1.5: fraction of KPIs below base case; no actuals creates a 0.5 uncertainty penalty.
- financial, max 1.0: negative gap between planned net value and actual net value.
- self-reported, max 1.0: latest non-draft status update RAG plus staleness bonus.

Final:

```text
initiative_pressure = schedule
                    + milestone_health
                    + risk_exposure
                    + kpi_performance
                    + financial
                    + self_reported
```

The score is capped at 10 and rounded to one decimal place.

### User Pressure Score

User pressure is a workload signal:

```text
user_pressure = average_owned_milestone_pressure * 0.6
              + average_owned_initiative_pressure * 0.4
```

Only active, non-complete owned milestones and initiatives are included. The result is capped at 10.

### Initiative Dependency Rollups

Dependency rollups use active dependencies unless stated otherwise.

Definitions:

- active dependency = status is not `resolved` or `cancelled`
- blocked initiative = downstream initiative of an active dependency where status is `blocking` or dependency type is `blocks`
- top blocker = upstream initiative ranked by active blocking count and blast radius
- critical path risk = active high-severity dependency whose status is `blocking`, `at_risk`, or `active`
- overdue = due date is before today and status is not `resolved` or `cancelled`

Blast radius is calculated by traversing downstream dependencies from an upstream initiative and counting unique downstream initiatives reached.

### Shared Cost Allocation

Shared cost allocation starts with a pool amount and an allocation rule.

Candidate initiatives:

- all initiatives matching the allocation rule filters.

Basis values:

- fixed percentage: initiative-specific weight value.
- manual amount: initiative-specific weight value.
- benefit weighted: sum of candidate initiative `gm_uplift_base`.
- revenue weighted: sum of candidate initiative `revenue_uplift_base`.
- headcount weighted: initiative-specific weight, defaulting to 1.
- equal split and fallback: basis value 1.

Allocation:

```text
total_basis = sum(candidate basis values)
share = 1 / candidate_count if total_basis == 0 else initiative_basis / total_basis
allocated_plan = pool.amount_plan * share
allocated_actual = pool.amount_actual * share for actual runs when actual amount exists
```

Amounts are quantized to four decimal places. The final candidate absorbs the remaining rounding difference so allocation totals reconcile exactly to the pool amount.

### Needs Attention

Control-tower reports surface attention items when:

- an in-progress initiative has no actual benefit values.
- realization status is `at_risk`.
- an initiative has allocated shared cost and benefit confidence below 50.
- an initiative is blocked by an active dependency.

## 6. API Surface

Representative API resources include:

- `/auth/login`
- `/auth/me`
- `/billing/config`
- `/billing/checkout-session`
- `/billing/webhook`
- `/platform/overview`
- `/platform/tenants/{tenant_id}/delete-preview`
- `/initiatives`
- `/initiatives/export`
- `/initiatives/template`
- `/initiatives/import/preview`
- `/initiatives/import`
- `/initiatives/intake/suggestions`
- `/initiatives/intake/create`
- `/initiatives/{initiative_id}/financials`
- `/initiatives/{initiative_id}/financials/export.xlsx`
- `/initiatives/{initiative_id}/cost-lines`
- `/initiatives/{initiative_id}/value-bridge`
- `/initiatives/{initiative_id}/scenario-summary`
- `/initiatives/{initiative_id}/break-even`
- `/portfolio/value-bridge`
- `/portfolio/financials`
- `/portfolio/financials/contributors`
- `/dashboard`
- `/milestones`
- `/portfolio/milestones`
- `/milestones/{milestone_id}/pressure`
- `/portfolio/dependencies`
- `/kpis`
- `/kpis/pulse`
- `/risks`
- `/risks/heatmap`
- `/governance`
- `/meetings`
- `/sessions`
- `/actions`
- `/people`
- `/users`
- `/invites`
- `/admin/settings`
- `/admin/gate-criteria`
- `/admin/financial-configuration`
- `/initiative-dependencies`
- `/initiatives/{id}/dependencies`
- `/shared-cost-pools`
- `/shared-cost-pools/{id}/allocation-rules`
- `/shared-cost-pools/{id}/allocation-runs`
- `/initiatives/{id}/value-realization-notes`
- `/reports/owner-cockpit`
- `/reports/executive-control-tower`
- `/reports/investor-summary`
- `/ai/chat`

## 7. Frontend Navigation

Main routes:

- `/`
- `/get-started`
- `/subscription/success`
- `/auth/login`
- `/platform`
- `/dashboard`
- `/financials`
- `/shared-costs`
- `/reports/control-tower`
- `/initiatives/pipeline`
- `/initiatives/matrix`
- `/initiatives/new`
- `/initiatives/:id`
- `/progress`
- `/progress/roadmap`
- `/progress/action-items`
- `/progress/status-updates`
- `/progress/dependencies`
- `/meetings`
- `/meetings/:id`
- `/meetings/sessions/:id`
- `/people`
- `/pmo/governance`
- `/pmo/risks`
- `/pmo/kpis`
- `/pmo/ai-insights`
- `/admin`

## 8. Data Model Summary

Core tenant-scoped entities:

- organizations
- business units
- workstreams
- initiatives
- milestones
- milestone dependencies
- milestone checklist items
- KPIs
- KPI entries
- risks
- status updates
- gate criteria
- gate submissions
- financial entries
- financial cost lines
- financial configuration groups/items
- financial cell assumptions
- meetings
- meeting sessions
- agenda items
- action items
- users
- invites
- audit logs
- AI audit/correction records
- shared cost pools
- shared cost allocation rules
- shared cost allocation runs
- shared cost allocations
- initiative dependencies
- initiative value realization notes

Phase 2A tables:

- `initiative_dependencies`
- `shared_cost_pools`
- `shared_cost_allocation_rules`
- `shared_cost_allocation_runs`
- `shared_cost_allocations`
- `initiative_value_realization_notes`

## 9. Testing And Release Discipline

The project standard distinguishes developer checks from acceptance.

Acceptance requires:

- real API tests against a running API
- deterministic seeded sample data
- browser UI tests against the real Angular app and real API
- role coverage for transformation office, initiative owner, viewer, and platform admin where relevant
- tenant isolation verification
- financial reconciliation checks using Decimal math
- no mock-led acceptance sign-off for core flows

The reusable launch regression covers:

- public signup
- Stripe checkout
- webhook provisioning
- tenant admin login
- initiative creation
- user invite and RBAC behavior
- financials, milestones, KPIs, risks, meetings
- dashboard rollups
- platform tenant deletion preview and cleanup

## 10. Competitive Context

Current enterprise transformation and strategic portfolio tools cluster around several patterns:

- Planview Strategic Portfolio Management emphasizes enterprise portfolio management, scenario planning, financial initiative planning, benefits realization, executive dashboards, dependency visualization, demand prioritization, capacity forecasting, and financial actuals. Source: [Planview SPM](https://www.planview.com/products-solutions/solutions/strategic-portfolio-management/).
- ServiceNow Strategic Portfolio Management emphasizes connecting strategy to delivery, adaptive planning, demand and resource management, investment funding, scenario planning, strategic alignment, AI management, and a single enterprise workflow platform. Sources: [ServiceNow SPM](https://www.servicenow.com/products/strategic-portfolio-management.html), [ServiceNow Scenario Planning](https://www.servicenow.com/products/scenario-planning.html).
- IBM Apptio and Cloudability emphasize showback/chargeback, shared cost allocation, direct/shared/total cost transparency, cloud financial planning, unit economics, dashboards, and rule-based cost sharing. Sources: [Apptio Cloudability Cost Sharing](https://www.apptio.com/products/cloudability/cost-sharing/), [IBM Cloudability cost sharing docs](https://www.ibm.com/docs/en/cloudability-commercial/cloudability-essentials/saas?topic=setup-sharing-cost-in-cloudability), [Apptio Showback and Chargeback](https://www.apptio.com/solutions/itfm/showback-chargeback/).
- Shibumi emphasizes strategic portfolio management, lifecycle management, value realization, financial and non-financial KPIs, what-if scenario modeling, interdependencies, capacity mapping, demand prioritization, constraints, and risks. Sources: [Shibumi SPM](https://shibumi.com/strategic-portfolio-management/), [Shibumi platform](https://shibumi.com/).

## 11. Why Transmuter Is Different

Transmuter is not trying to be a generic project portfolio management suite or a narrow FinOps product. Its differentiation is the combination of transformation-office operating cadence and financial accountability:

- It treats initiative economics as first-class: value bridge, base/high/actual cases, break-even, direct cost lines, shared cost allocation, and burdened value.
- It connects dependencies to executive governance, not just task planning.
- It gives different personas different report modes instead of forcing all users through one portfolio dashboard.
- It blends stage-gate governance, meeting/action cadence, risk/KPI tracking, and owner updates into one operating model.
- It is built for multi-tenant SaaS from the start, with tenant isolation, RBAC, provisioning, and platform-admin operations.
- It uses deterministic calculations for financials and pressure scoring, reserving AI for drafting, extraction, recommendations, and summarization.
- It keeps investor-facing reporting tied to auditable operational records rather than slide-only narratives.

## 12. Roadmap

### Phase 2A: Executive Control Tower

Status: implemented locally and in QA/security-review flow.

Scope:

- initiative dependencies
- shared cost pools
- allocation rules
- allocation runs
- persona reports
- value realization notes
- benefit confidence and realization status
- gate criteria updates for dependency and allocation review

### Phase 2B: Scenario And Prioritization

Recommended next scope:

- delay, accelerate, cancel, or descope what-if views
- portfolio scoring by value, risk, confidence, dependency impact, and cost burden
- demand/intake scoring for pre-approval initiatives
- strategy, OKR, and investor-theme alignment
- scenario comparison exports for SteerCo and board packs

### Phase 3: AI Operating Assistant

Recommended scope:

- portfolio RAG assistant
- status update drafting
- meeting notes extraction
- action and decision extraction
- AI-generated executive summaries with source citations
- correction-rate analytics and quality dashboards

### Phase 4: Enterprise Integration And Board Automation

Recommended scope:

- Jira, Asana, ServiceNow, ERP, HRIS, and data warehouse connectors
- recurring board pack generation
- PDF/PPT exports
- investor portal views
- audit-ready evidence packages for realized value

## 13. Review Notes

Areas requiring continued Prahari review:

- RBAC and RLS for new tenant-scoped tables.
- Financial allocation correctness and auditability.
- Investor-report visibility.
- AI tool inputs, PII masking, and HITL write checkpoints.
- Stripe webhook and tenant provisioning behavior.

Areas requiring Aksha acceptance:

- real API tests for seeded tenants and seeded users.
- browser tests for owner, management, and viewer permissions.
- allocation reconciliation for every allocation method.
- dependency cycle prevention and blast-radius rollups.
- reporting reconciliation from financial entries, direct costs, allocated costs, and value bridge totals.

