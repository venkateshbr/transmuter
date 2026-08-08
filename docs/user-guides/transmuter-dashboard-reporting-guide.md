# Transmuter Dashboard and Reporting Guide

Last reviewed: 2026-08-08

This guide explains every current dashboard, widget, control, drill-through, and reporting boundary. It uses **ACME Industrial Services** and initiative **ACC-101 Invoice Automation** for realistic examples. Dashboards are read-only: use **Transformation Management**, **Financial Operations**, **Governance & Cadence**, or initiative detail to change source records.

## 1. Dashboard portfolio

The Dashboard menu contains exactly three destinations:

| Dashboard | Question answered | Write behavior |
|---|---|---|
| Operational Dashboard | Where does leadership need to intervene? | None; filters, drill-through, export, layout only |
| Financial Dashboard | Are value, cost, investment, and commitments performing? | None; drill through to Financial Operations for entry |
| Initiative Portfolio | How do initiatives compare at row level? | Unchanged; open initiative detail for maintenance |

Legacy Control Tower content is represented in the Operational Dashboard. Investments & Payback remains available as a Financial Dashboard drill-through, not as a fourth dashboard menu item.

## 2. Shared dashboard controls

### Filters

Filters change the displayed population and are carried into supported drill-through/export actions. Before interpreting a number, check workstream, business unit, stage, priority, tag, year, scenario, as-of date, and actuals/benefits toggles shown on that page.

Example: selecting **Digital Operations**, **Automation**, and FY2027 should include ACC-101 but exclude unrelated Growth initiatives. Clear filters before quoting a tenant-wide total.

### Customize layout

1. Select **Customize layout**.
2. Drag a widget onto another widget to reorder it, or use the left/right arrow controls for keyboard operation.
3. Select **Resize** to cycle through Small, Medium, Wide, and Full.
4. Hide optional widgets with ×; required decision widgets cannot be hidden.
5. Select **Save my layout** for a personal view.
6. Transformation Office and tenant administrators may select **Publish role default**.
7. Select **Reset** to remove the personal layout and return to the role default or system layout.

Desktop uses a 12-column grid, tablet uses a constrained grid, and mobile stacks widgets. The saved source label tells you whether the active view is Personal, Role default, or Standard.

## 3. Operational Dashboard

The default order places decision-critical widgets first.

### 3.1 Decision strip — required, full width

Shows portfolio size, red initiatives, and pending gate decisions. Each measure opens the relevant operational list.

ACME example: 21 active initiatives, 3 red, and 2 pending gates means leadership should open the red population and decision queue before reviewing supporting charts.

### 3.2 Needs attention — required, wide

Combines the exception counts most likely to need action: at-risk initiatives, pending approvals, and the current user's open actions. Drill-throughs lead to the relevant Transformation Management or Governance & Cadence workbench.

Example: if ACC-101 is amber but its gate decision is pending and Daniel has an overdue validation action, those are separate exceptions and must be resolved in their source features.

### 3.3 Execution health — required, medium

Displays portfolio pressure/health derived from the current operational population. Treat it as a signal, then drill into RAG, risks, milestones, and actions.

### 3.4 Stage progression — required, wide

Shows initiative counts by configured lifecycle stage. A large L2 population with little L3 progression may indicate approval capacity, incomplete cases, or weak sponsorship.

ACME example: ACC-101 moving from L2 to L3 changes the stage count only after the approved governance transition; changing a status narrative does not move it.

### 3.5 Risk heatmap — optional, medium

Aggregates open risks by likelihood and impact. The highest-concentration critical cells deserve first review.

Example: ACC-101's High-likelihood/Medium-impact API limit risk contributes to that cell until closed or reassessed in Risk Register.

### 3.6 KPI Pulse — optional, medium

Shows KPI health and recent KPI items based on latest actuals versus targets. Open KPI Management to add or correct actuals.

Example: touchless invoice rate of 72% against a 75% base target is below target. The chart is not an editable spreadsheet.

### 3.7 My Work — optional, medium

Summarizes actions and upcoming milestones assigned to the signed-in user. It is personal operational context, not a tenant-wide workload measure.

### 3.8 Recent Activity — optional, medium

Lists recently submitted initiative status updates. Open an initiative for full context. Draft notes that were never submitted do not belong in the activity feed.

### Executive brief and decision queue

**Executive Brief** prepares a management/investor/owner-oriented summary from current filters. **Decision Queue** brings together intervention routes. Check the source records before distributing the summary.

## 4. Financial Dashboard

The Financial Dashboard separates portfolio interpretation from financial entry.

### 4.1 Financial position — required, full width

Shows primary plan values and, when enabled and available, actual and variance. The visible metrics depend on tenant financial configuration and the benefits toggle.

Variance is displayed as actual relative to plan for the metric. Favorable direction depends on meaning: higher benefit actual can be favorable, while higher cost actual can be unfavorable.

### 4.2 Benefit realization — required, wide

Compares planned benefits with recorded actual realization and links to Benefit Ledger. Validation status and period basis matter.

ACC-101 example: annual base benefit is $1.8M; a validated July actual of $150,000 is one period of realization, not proof that $1.8M has already been realized.

### 4.3 Investment and payback — required, medium

Links to detailed investment/payback analysis. It compares investment timing with cumulative value recovery.

Simplified ACC-101 example: $300,000 one-time investment and $140,000 monthly net benefit after go-live crosses payback during the third realized month. The real view uses configured periods and all applicable costs/benefits.

### 4.4 Value waterline — required, wide

Shows locked target context and links to target-lock operations. Above-waterline value is bankable/implemented according to configured stage rules; below-waterline value is pipeline. A lock is a governed snapshot, not a live forecast.

Example: if Digital Operations has a locked $5M net run-rate target and current eligible value is $4.6M, the gap is $0.4M. A new L1 idea must not be counted as locked commitment merely because its high case is attractive.

### 4.5 Financial trend — optional, wide

Plots benefits, recurring costs, one-time costs, net value, and actuals across month, quarter, or year. Selecting a period opens contributing initiatives where supported.

Example: an implementation-cost spike in Q2 followed by benefit ramp in Q3 is normal for ACC-101; compare cumulative value before judging a single negative period.

### 4.6 Value bridge — optional, medium

Shows base, high, and actual net value for the selected basis: all years, in-year, target-year run-rate, or cumulative where configured.

Formula example: `$1.8M benefits - $0.12M recurring costs = $1.68M base net run-rate`. The $0.3M one-time implementation cost affects investment/cumulative views according to timing and must not be double-counted.

### 4.7 Cost breakdown — optional, medium

Groups portfolio costs by configured category and links to Shared Costs. Missing or excessive `Other` values indicate data-quality work under Financial Operations.

### 4.8 Initiative value matrix — optional, full width

Links to the unchanged Initiative Portfolio for initiative-level comparison. It is the preferred row-level drill-through instead of adding another dashboard.

### Baseline-to-target section

Where configured, the detailed financial analysis shows baseline revenue, baseline gross margin, target revenue, target gross margin, and margin rate. Cost savings contribute to benefits/net value; they are not automatically added to target gross margin.

Example: $100M baseline revenue + $4M revenue uplift = $104M target revenue. If baseline gross margin is $30M and configured gross-margin uplift is $1M, target gross margin is $31M and target margin rate is `31 / 104 = 29.8077%`.

### Board Pack

The Board Pack export uses current filters, granularity, year, as-of date, and display basis. Record these selections with the distributed pack so another user can reproduce it.

## 5. Initiative Portfolio — unchanged

Initiative Portfolio remains the detailed portfolio comparison. Use it to scan initiatives across ownership, stage, value, investment/payback, and configured columns; use filters to narrow the list; open the initiative for evidence and maintenance.

ACME example: compare ACC-101 with other Digital Operations initiatives, then open ACC-101 to inspect its assumptions rather than inferring detail from a rolled-up cell.

## 6. Data and formula boundaries

| Concept | Interpretation |
|---|---|
| Plan base | Approved/base scenario |
| Plan high | Upside scenario, not commitment |
| Actual | Recorded delivery/cost for its period and validation state |
| Recurring cost | Repeats according to configured timing |
| One-time cost | Investment in its entered period |
| Net run-rate | Recurring benefits minus recurring costs for the stated basis |
| Cumulative net value | Period benefits less applicable costs accumulated through the selected period |
| Locked plan | Immutable governed snapshot/version |
| Pipeline value | Current forecast not necessarily bankable |

Amounts are stored with decimal precision and returned by APIs as strings. Display rounding must not be used to reconstruct ledger amounts.

## 7. Reconciliation example

For ACC-101 in FY2027:

1. Base benefit plan: $1,800,000.0000.
2. Recurring software plan: $120,000.0000.
3. Net annual run-rate: $1,680,000.0000.
4. One-time implementation: $300,000.0000.
5. Simplified first-year net including that investment: $1,380,000.0000, subject to configured benefit ramp and timing.
6. July validated benefit actual: $150,000.0000.

To reconcile, filter to ACC-101's workstream/year, open the contributing initiative/period, compare benefit ledger entries and cost lines, then confirm scenario, validation, recurrence, fiscal calendar, and as-of date. Never “fix” the displayed total directly.

## 8. Common mistakes

- Treating the high case as committed value.
- Adding cost saving to gross margin twice.
- Comparing annual plan with one month's actual.
- Ignoring filters or the as-of date.
- Editing ledger/source data solely to make a chart look right.
- Counting an L1/L2 pipeline value as locked waterline value.
- Distributing a board pack without its filter/data basis.
- Hiding context widgets and assuming required decision widgets can be removed.

## 9. Dashboard review checklist

1. Confirm tenant, reporting currency, period, filters, and as-of date.
2. Start with required top widgets and exceptions.
3. Drill through before deciding.
4. Reconcile financial exceptions to ledger/cost source records.
5. Assign actions or complete approvals in Operations.
6. Save a personal layout only for presentation preference; publish role defaults deliberately.
7. Export only after the view is reproducible.
