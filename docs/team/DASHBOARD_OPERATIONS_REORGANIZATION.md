# Dashboard and Operations Reorganization

**Parent issue:** #462  
**Status:** Approved for implementation  
**Roles:** Netra → Vastu → Chitra → Karya/Rupa → Prahari → Aksha → Sthira → Vishwa

## Product boundary

Transmuter separates decision surfaces from record-maintenance workflows:

- **Dashboards** are read-only analysis, exceptions, filters, exports, drill-through,
  and presentation-layout customization.
- **Operations** contains creation, editing, validation, approval, locking,
  allocation, posting, import, and maintenance.
- **Initiative Portfolio** remains functionally and visually unchanged.

The authenticated navigation exposes:

1. **Dashboards**
   - Operational Dashboard (`/dashboard`)
   - Financial Dashboard (`/financials`)
   - Initiative Portfolio (`/financials/initiative-portfolio`)
2. **Operations**
   - Delivery: Progress Monitor, Roadmap, Action Items, Status Updates, Risks,
     Dependencies, and KPI Management
   - Financial: Benefit Ledger, Benefits Register, Bankable Plans, Waterline and
     Target Locks, and Shared Costs
   - Governance and cadence: Gate Approvals and Meetings
3. **Initiatives** remains the portfolio master-data and initiative workflow area.

Legacy routes remain valid even when removed from Dashboard navigation.

## External platform review and prioritization

The review used current first-party product material rather than treating every
competitor feature as a requirement:

- [ServiceNow Strategic Portfolio Management](https://www.servicenow.com/products/strategic-portfolio-management.html)
  emphasizes strategy-to-delivery alignment, outcomes, adaptive planning, and
  a unified workflow platform. Its documented dashboard editor also supports
  owned/shared dashboard customization.
- [ServiceNow Scenario Planning](https://www.servicenow.com/products/scenario-planning.html)
  compares cost, benefit, strategic alignment, and resource utilization before
  confirming an investment scenario.
- [Planview Strategic Portfolio Management](https://www.planview.com/products-solutions/solutions/strategic-portfolio-management/)
  emphasizes interactive portfolio analytics, investment-to-outcome traceability,
  early risk signals, capacity, and what-if planning.
- [Broadcom Clarity](https://www.broadcom.com/products/software/value-stream-management/clarity/what-is-project-portfolio-management)
  brings investments, financials, resources, delivery, roadmaps, and real-time
  reporting into a connected SPM environment.
- [Atlassian Align](https://www.atlassian.com/software/jira-align)
  emphasizes enterprise-to-team alignment, dependencies, investment/capacity,
  delivery health, and integration with existing delivery systems.

### Adopt now — directly supports Transmuter's value proposition

| Capability | Decision | Implementation |
|---|---|---|
| Clear strategy/execution and finance/operations separation | Adopt | Operational and Financial dashboards plus Operations workbench |
| Exception-first executive views | Adopt | Required decision strips and supporting widgets below |
| Investment-to-outcome traceability | Adopt | Benefit realization, bankable plans, value bridge, payback and initiative drill-through |
| Configurable dashboards | Adopt with constraints | Personal and tenant/role layouts; drag, keyboard reorder, preset resize, reset |
| Governed commitment/baseline comparison | Adopt | Bankable versions, rebaseline, target locks and waterline |
| Risk, KPI, milestone and dependency visibility | Adopt | Operational widgets linking to authoritative registers |
| Audit-ready reporting | Adopt | Read-only dashboards, source drill-through, deterministic board-pack basis |

### Next — valuable, but requires authoritative data foundations

| Capability | Why next rather than now |
|---|---|
| What-if portfolio scenario planning | High value, but needs explicit capacity, constraints, scenario versioning and approval semantics |
| Resource/capacity planning | Requires skills, availability, allocation, calendar and cost models not yet authoritative |
| Strategy/OKR hierarchy and contribution maps | Useful once tenant goal ownership and measurement rules are formalized |
| Cross-tool execution connectors | Valuable for Jira/Azure DevOps/ERP adoption, but each connector needs tenant isolation, reconciliation and failure handling |
| Forecast confidence and predictive risk | Requires historical coverage, data-quality thresholds, explainability and evaluation |

### Good to have — keep below the decision layer or defer

| Capability | Treatment |
|---|---|
| Free-form dashboard canvases, rich text and decorative tiles | Defer; they create layout entropy and weaken comparability |
| Large widget marketplace | Defer until usage evidence supports additional stable analytical contracts |
| Social feeds and broad collaboration streams | Keep activity concise; meetings, actions and status are the accountable system of record |
| AI-generated narrative everywhere | Keep optional and supporting; never displace source evidence or human approval |
| Application-portfolio and technology-architecture inventory | Out of current transformation-value scope; integrate later instead of duplicating a CMDB/APM suite |
| Timesheets and detailed workforce scheduling | Out of current value-office core; pursue only with a validated buyer need |

This comparison supports a deliberate product position: Transmuter should be
strongest at governed transformation value, execution evidence, and executive
decision-making. It should integrate with specialist delivery, workforce, ERP,
and architecture systems rather than reproducing their full operational depth.

## Dashboard requirements

### Operational Dashboard

Single job: identify execution drift and management intervention.

Required top widgets:

- portfolio decision strip;
- needs-attention queue;
- execution health by workstream;
- stage progression and ageing.

Supporting widgets:

- risk heatmap;
- KPI pulse;
- upcoming milestones;
- assigned actions;
- reporting compliance;
- recent activity;
- roadmap preview;
- operational narrative.

### Financial Dashboard

Single job: show whether committed value is being realized, at what cost, and
where financial intervention is needed.

Required top widgets:

- locked plan, forecast, actual, and net-value variance;
- benefit realization and Finance-validation coverage;
- investment, recurring cost, and payback;
- bankability and locked workstream waterline.

Supporting widgets:

- plan/locked/actual trend;
- burdened value bridge;
- realization by workstream;
- investment/payback ranking;
- adverse-variance contributors;
- cost-category and benefit-class breakdowns;
- workstream by value-tag matrix;
- shared-cost reconciliation and data-quality exceptions.

## Widget layout architecture

Dashboard layout editing is an explicit mode. Required top widgets are pinned;
supporting widgets may be reordered, resized within declared constraints, hidden,
restored, and reset. Business records cannot be edited from layout mode.

Each widget declares a stable key, supported dashboard, required/removable state,
default/minimum/maximum size, allowed roles, and drill-through route. Desktop uses
a 12-column grid, tablet a 6-column grid, and mobile a fixed single-column order.
Keyboard controls provide Move earlier/later and Small/Medium/Wide/Full commands;
pointer drag is never the only interaction.

Layouts have two ownership levels:

- tenant/role defaults published by an authorized tenant administrator;
- optional user overrides inheriting from the tenant default.

Layout authorization never expands widget or data access. All persisted layout
records are tenant-scoped and protected by RLS.

## Reporting architecture

Financial headline values must come from the authoritative financial reporting
domain and retain Decimal/string money contracts. Operational aggregates must use
the same role-scoped initiative population as their drill-through destinations.
The Dashboard, Executive Control, workbook, and portfolio financial calculations
must reconcile before legacy report surfaces are retired.

Shared filters are fiscal/as-of context, scenario or locked baseline, business
unit, workstream, stage, RAG, priority, and tag. A filter must have the same
meaning across dashboard cards, charts, exports, and drill-through links.

## Design contract

The audience is a transformation office steering a live enterprise portfolio.
The page signature is the structured decision rail: a compact navy band that
states the exceptions, accountable decisions, and financial variance before any
supporting visualization.

Use the existing deep navy, steel blue, light blue, white/grey surfaces, Libre
Franklin typography, square geometry, thin dividers, restrained shadows, and
dense executive layout. Avoid decorative gradients, rounded SaaS cards, and
oversized marketing heroes. Layout-edit controls appear only in Customize mode.

## Documentation consolidation

The active published catalogue will contain:

1. **Transmuter Administration Guide** — tenant setup, roles/access, dimensions,
   financial configuration, governance, dashboard defaults, integrations,
   operating controls, and troubleshooting.
2. **Transmuter User Operations Guide** — initiatives, delivery operations,
   financial operations, governance, meetings, evidence, and role-specific work.
3. **Transmuter Dashboard and Reporting Guide** — Operational, Financial, and
   Initiative Portfolio dashboards, filters, formulas, drill-through, layout
   customization, exports, empty/error states, and worked examples.

ACME is the canonical worked example. Alternate tenant scenarios become clearly
labelled appendices or internal validation data, not parallel product manuals.
Every documented procedure must be verified against deterministic seeded data and
the real Angular application/API before release.

The source-by-source audit and implementation coverage matrix are recorded in
`docs/team/USER_GUIDE_CONSOLIDATION_REVIEW.md`.

## Acceptance boundary

- Dashboard navigation contains only the three approved decision surfaces.
- Operations navigation contains every entry, approval, lock, allocation, import,
  posting, and maintenance workflow.
- Initiative Portfolio is unchanged.
- Legacy bookmarks resolve safely.
- Layouts persist, respect required-widget constraints, and have keyboard/mobile
  alternatives.
- Tenant and role isolation hold for layouts and aggregates.
- Financial and operational totals reconcile with their source records.
- The three active user guides match the shipped UI and contain realistic worked
  examples with expected results.
