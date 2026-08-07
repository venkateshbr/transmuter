# Transmuter Dashboards and Reporting User Guide — ACME Example

Last reviewed: 2026-08-07

This guide explains every dashboard and financial reporting screen available in
the Transmuter Dashboard menu. It is written for executives, transformation
office leaders, Finance leads, benefits owners, PMO leads, and read-only
management viewers. The worked values use the deterministic ACME transformation
tenant.

Use this guide to answer three questions:

1. What does each card, chart, table, and filter mean?
2. Which screen is authoritative for a management question?
3. How should an ACME value be reconciled from baseline through plan, actuals,
   governance, and fully burdened value?

For data entry and tenant construction, use the [ACME Detailed Setup and Demo
Guide](acme-transformation-office-detailed-setup-and-demo-guide.md). For metric,
scenario, formula, baseline, and cost-category configuration, use the [Admin
Financial Configuration User Guide](admin-financial-configuration-user-guide.md).

---

## 1. Dashboard Directory

Tenant administrators control which entries appear under **Dashboard** in
**Admin > Dashboard Configuration**. A full ACME demo should enable every entry.

| Menu entry | Route | Primary question | Primary audience |
|---|---|---|---|
| Executive Dashboard | `/dashboard` | Where does management need to focus? | Executive Sponsor, Transformation Office, PMO |
| Financial Overview | `/financials` | What is the baseline, target, plan, actual, cost, and net value? | CFO, Finance Lead, Benefits Controller |
| Initiative Portfolio | `/financials/initiative-portfolio` | Which initiatives create or dilute value? | CFO, Transformation Office |
| Investments & Payback | `/financials/investments-payback` | How much must be invested and when is it recovered? | CFO, Investment Committee |
| Bankable Plan | `/financials/bankable-plan` | Which approved value case is locked? | Finance Lead, PMO Lead |
| Benefits Register | `/financials/benefits-register` | Which benefit claims are validated and evidenced? | Finance Lead, Benefits Controller |
| Benefit Tracking | `/financials/benefit-tracking` | What value has actually been realized against the locked plan? | Benefits Controller, Benefit Owners |
| Waterline | `/financials/waterline` | Which initiatives are included in the committed workstream target? | Transformation Office, Finance Lead |
| Control Tower | `/reports/control-tower` | What decision is required after delivery risk and shared costs? | Steering Committee |
| Shared Costs | `/shared-costs` | How are central costs allocated across initiatives? | Finance Lead |

### Recommended management paths

| Meeting | Recommended sequence |
|---|---|
| Five-minute value explanation | Financial Overview → Initiative Portfolio → Benefit Tracking |
| Monthly value review | Executive Dashboard → Financial Overview → Benefits Register → Benefit Tracking |
| Steering committee | Executive Dashboard → Control Tower → Initiative Portfolio → Bankable Plan |
| Finance validation | Financial Overview → Benefits Register → Bankable Plan → Benefit Tracking → Investments & Payback |
| Fully loaded economics | Shared Costs → Control Tower |

---

## 2. ACME Financial Story and Calculation Boundaries

Use FY2028, yearly granularity, all stages, and all cost categories unless a
section says otherwise.

### 2.1 Absolute business bridge

| Measure | Formula | ACME FY2028 |
|---|---|---:|
| Baseline revenue | Tenant FY2026 annual revenue baseline | `$20.000M` |
| Revenue uplift | Sum of FY2028 plan-base `revenue_uplift` | `$4.000M` |
| Target revenue | Baseline revenue + revenue uplift | `$24.000M` |
| Baseline gross margin | Tenant FY2026 annual gross-margin baseline | `$9.000M` |
| Gross-margin uplift | Sum of FY2028 plan-base `gm_uplift` | `$5.432M` |
| Target gross margin | Baseline gross margin + gross-margin uplift | `$14.432M` |
| Target margin rate | Target gross margin / target revenue | `60.13%` |

The absolute bridge answers what the transformed business is expected to look
like. It does not add cost savings to gross margin.

### 2.2 Transformation value bridge

| Measure | Formula | ACME FY2028 |
|---|---|---:|
| Gross-margin uplift | Revenue/margin benefit | `$5.432M` |
| Cost savings and other benefits | Benefit metrics classified outside margin | `$3.750M` |
| Total benefits | Gross-margin uplift + cost savings/other benefits | `$9.182M` |
| Recurring costs | Recurring initiative run costs | `$0.800M` |
| Net run-rate value | Total benefits − recurring costs | `$8.382M` |
| One-off investment | Non-recurring investment, shown separately | `$2.500M` |

This bridge answers how much recurring transformation value is created. One-off
investment is excluded from net run-rate value and used in payback analysis.

### 2.3 Actuals boundary

The seeded ACME actuals are through `2028-06-30`, not a full FY2028 forecast.

| Actual measure | ACME through 2028-06-30 |
|---|---:|
| Actual benefit | `$4.080M` |
| Actual recurring cost | `$0.388M` |
| Net actual | `$3.692M` |

Do not compare these six-month actuals to a twelve-month plan without saying
that the actual is year to date. Use Benefit Tracking for period-by-period
realization and evidence.

---

## 3. Executive Dashboard

Route: `/dashboard`

The Executive Dashboard is the starting point for management attention. It is
not the final authority for a detailed financial reconciliation; use Financial
Overview and its contributor drawer for that purpose.

### Header and filters

| Control | Effect |
|---|---|
| Target year | Changes selected-year financial and value-matrix rollups. Select FY2028 for ACME. |
| Business unit | Restricts visible initiatives to the selected organizational unit. |
| Workstream | Restricts the portfolio to one delivery/value workstream. |
| Priority | Restricts initiatives by configured priority. |
| Tag | Restricts initiatives to a value tag such as automation, commercial, or offshoring. |

Always clear filters before quoting a total portfolio number. A filtered card
is a selected population, not the complete ACME portfolio.

### Executive summary cards

These cards summarize initiative count, portfolio health, delivery, and value.
Use them to open the discussion, then use the linked operational screen to
investigate the cause. Counts are current-state counts; financial values follow
the selected target year and the active financial mode.

### Pipeline by Stage

- **What it shows:** initiative count in every configured delivery stage.
- **How to read it:** a large early-stage population indicates a pipeline;
  concentration in execution indicates delivery load.
- **Interaction:** select a stage or its link to open Initiative Pipeline with
  that stage filter.
- **Management question:** is enough value progressing through governance, or
  is the portfolio stuck before execution?

### Health Breakdown (RAG)

- **What it shows:** counts of green, amber, and red initiatives.
- **How to read it:** amber and red are attention signals, not financial losses
  by themselves.
- **Interaction:** select a RAG state to open the filtered pipeline.
- **Management question:** which initiatives threaten the plan?

### Portfolio Pressure

- **What it shows:** delivery pressure derived from the current milestone and
  execution load.
- **Interaction:** select the card to open the milestone tracker.
- **Management question:** is the delivery system carrying more work or delay
  than it can absorb?

### Value Bridge

- **What it shows:** plan-base, plan-high, actual benefits, costs, and net value
  according to the tenant financial mode.
- **How to read it:** benefits are positive; costs are displayed as deductions;
  net is the resulting transformation value.
- **Interaction:** open the financial initiatives and continue to Financial
  Overview for exact period and contributor reconciliation.
- **Management question:** is the transformation value large enough and is
  actual delivery keeping pace?

### Risk Heatmap

- **What it shows:** open risks by impact and likelihood.
- **How to read it:** high-impact/high-likelihood cells demand immediate review.
- **Interaction:** select a heatmap cell to open Risks with the same impact and
  likelihood filters.
- **Management question:** which risk concentration can erode value?

### Bankable Workstream Targets

- **What it shows:** latest immutable workstream targets and actual realization.
- **Source:** Waterline target locks and actual benefit ledger values.
- **Management question:** are workstreams delivering against a frozen target
  rather than a moving forecast?

### Stage-gate Value vs Locked Bankable Plan

- **What it shows:** value currently progressing through configured stages
  compared with approved locked bankable value.
- **How to read it:** a gap can indicate unapproved pipeline value, delivery
  movement, or a plan awaiting governance.
- **Management question:** how much of the value story is approved and bankable?

### Workstreams × Value Tags matrix

- **Rows:** workstreams.
- **Columns:** configured initiative value tags.
- **Cells:** selected-year value contribution for that intersection.
- **Interaction:** select a non-zero cell to open the contributing initiatives.
- **Footer:** portfolio totals across the matrix.
- **Management question:** where is value concentrated by operating owner and
  value mechanism?

### My Milestones, My Actions, KPI Pulse, and Recent Activity

These are accountability widgets rather than portfolio valuation charts.

- **My Milestones:** upcoming or overdue delivery commitments owned by the user.
- **My Actions:** open actions assigned to the user.
- **KPI Pulse:** latest performance against configured KPI direction/target.
- **Recent Activity:** recent material portfolio changes.

The empty state means no matching records for the current user/context; it does
not prove that the whole tenant has no milestones, actions, KPIs, or activity.

---

## 4. Financial Overview

Route: `/financials`

This is the authoritative portfolio plan/actual reconciliation screen.

### Controls

| Control | Meaning | ACME demo setting |
|---|---|---|
| Monthly / Quarterly / Yearly | Aggregation of the period chart and table | Yearly for management; monthly for contributor proof |
| Benefits On/Off | Shows or hides benefits and net-value measures | On |
| Actuals On/Off | Shows actual and variance alongside plan when available | On |
| Year | Selects the plan/value year | 2028 |
| Stage | Restricts period financial rows to selected initiative stages | All stages for total portfolio |
| Cost category | Restricts cost values to one category | All for total; Software, Maintenance, or People Support for leakage review |
| Plan as-of date | Cuts the value ramp off at a historical date | Blank unless demonstrating a historical view |
| Value basis | All years, in-year, target-year run-rate, or cumulative | Target-year run-rate for the FY2028 story |
| Export Board Pack | Downloads an authenticated XLSX using selected year and basis | Use after reconciliation |

### Original baseline cards

The cards show the latest tenant baseline year eligible for the selected target
year:

- FY2026 annual revenue: `$20.000M`.
- FY2026 annual gross margin: `$9.000M`.
- Baseline margin rate: `45.0%`.

These values describe the original business and do not include transformation
benefits.

### FY2028 Portfolio Targets cards

The prominent target cards connect the original business to the selected-year
initiative plan:

- **Target Revenue:** `$24.000M` = `$20.000M` baseline + `$4.000M` revenue
  uplift.
- **Target Gross Margin:** `$14.432M` = `$9.000M` baseline + `$5.432M`
  gross-margin uplift.
- **Target Margin Rate:** `60.1%` = `$14.432M / $24.000M`.

The cards use the full selected-year portfolio plan-base bridge. Stage and cost
category drilldowns below do not redefine the tenant baseline. Cost savings are
shown in Benefits and Net Run-rate Value; they are not added to Target Gross
Margin.

### Plan/actual summary cards

| Card | Meaning | ACME FY2028 plan |
|---|---|---:|
| Benefits | Margin uplift plus benefit-classified savings and other benefits | `$9.182M` |
| Recurring Costs | Ongoing operating cost required to sustain the initiatives | `$0.800M` |
| One-off Costs | Non-recurring investment in the selected period | `$0.000M` in FY2028 |
| Total Costs | Recurring plus one-off cost for the selected view | Depends on selected period/basis |
| Net Run-rate Impact | Benefits minus recurring costs | `$8.382M` |

When Actuals is on, each card shows actual and variance. A positive benefit/net
variance is favorable. A positive cost variance means actual cost is greater
than plan and must be interpreted as unfavorable even if it is styled as a
numeric increase.

### Financial Trend chart

- **Metric selector:** Net Run-rate Impact, Costs, or Total Benefits.
- **Plan line:** selected metric plan by period.
- **Actual line:** selected metric actual by period when enabled.
- **Baseline reference:** original gross-margin baseline normalized to the
  selected granularity; it is contextual and is not a plan line.
- **Latest Period panel:** latest visible period, plan, and actual.
- **Interaction:** select a data point to open the contributor drawer.

Do not interpret the gross-margin baseline reference as a direct comparison to
costs or total benefits. It remains visible to preserve business context.

### In-year value

This panel shows benefit, recurring cost, one-off cost, and net values occurring
inside the selected year. Use it when management asks what lands in the P&L
during the year rather than the eventual run rate.

### Run-rate value ramp

- **Net Plan/Actual:** period contribution.
- **Cumulative Plan/Actual:** accumulated value through the period.
- **As-of date:** excludes later periods from the ramp.

Use this table to explain phasing and when the portfolio reaches its expected
run-rate. Cumulative value is not the same as one-year run-rate value.

### Value bridge

The bridge uses configured metric rows and cost categories. Switch the basis:

| Basis | Meaning |
|---|---|
| All years | Every available financial period |
| In-year | Values occurring in the selected year |
| Target-year run-rate | Selected target-year recurring value story |
| Cumulative through year | All values through the selected year |

Plan Base, Plan High, and Actual are scenarios, not confidence labels invented
by the chart. The tenant's configured scenarios and metric definitions remain
the source of truth.

### Cost and metric breakdowns

- **Cost breakdown:** groups plan, actual, and variance by configured cost
  category.
- **Metric breakdown:** groups values by active metric definitions.
- **Use:** find the source of benefit or cost concentration before opening an
  initiative.

### Period table and contributor drawer

The period table is the numeric source behind the trend. Select a monthly row,
for example `2028-M01`, for the strongest ACME contributor proof. The drawer
shows:

- contributing initiative;
- benefit plan, actual, and variance;
- recurring and one-off cost lines;
- net plan and actual;
- benefit-line validation status and evidence.

Reconcile the drawer total to the selected period row before presenting it.

---

## 5. Initiative Portfolio

Route: `/financials/initiative-portfolio`

### Filters

Baseline year, value year, scenario, business unit, workstream, stage, tag, and
initiative filters define the comparison population. Use FY2026 baseline,
FY2028 value year, and Plan Base for ACME.

### Summary cards

- **Initiatives:** number in the selected population.
- **EBITDA Benefits:** sum of margin and other benefit metrics.
- **Recurring Costs:** ongoing cost burden.
- **Net Run-rate Value:** benefits minus recurring costs.

### Baseline reconciliation

Tenant baseline, initiative baseline total, variance, and reconciliation state
show whether initiative allocations reconcile to the tenant baseline. A
non-zero variance means the absolute business bridge should not be presented as
fully reconciled until Finance fixes the allocation.

### Initiative comparison table

Each row shows baseline metrics, selected-year value metrics, benefits,
recurring cost, one-off cost, and net run-rate value. Use it to identify:

- the largest value contributors;
- negative or low-net initiatives;
- recurring-cost leakage;
- concentration in a small number of initiatives;
- initiatives requiring an assumption or scope drilldown.

Selecting an initiative opens its detail page and initiative-level P&L bridge.

---

## 6. Investments & Payback

Route: `/financials/investments-payback`

### Controls and cards

- **Value Year:** run-rate year used for value.
- **Scenario:** Plan Base, Plan High, or Actual.
- **One-off Investment:** cumulative non-recurring investment through the value
  year.
- **Net Run-rate Value:** recurring annual value after recurring costs.
- **Portfolio Payback:** `one-off investment / annual net run-rate × 12`.
- **With Payback / Not Reached:** count of initiatives with positive/recoverable
  economics versus initiatives whose net run-rate cannot repay investment.

For ACME FY2028 Plan Base, explain approximately `$2.500M` one-off investment
and `3.6 months` portfolio payback.

The ranking table identifies initiatives with immediate payback, a calculated
payback period, or payback not reached. A short payback does not replace
delivery, risk, or benefit-evidence review.

---

## 7. Bankable Plan

Route: `/financials/bankable-plan`

- **Initiative selector:** changes the approved value case being reviewed.
- **Locked/Editable badge:** whether a current immutable plan exists.
- **Locked bankable plan:** committed net value and lock timestamp.
- **Working forecast:** current editable view; it may differ from the lock.
- **Snapshot contents:** financial entries, cost lines, metric values, and
  selected financial scope captured in the version.
- **Version history:** every approved plan/rebaseline with time, reason,
  trigger, and actor.
- **Request rebaseline:** starts governance; it does not overwrite history.

Use `ENT-005 Enterprise Data and ERP Modernization` to demonstrate version 2
and a controlled rebaseline. The bankable plan is the baseline for realization,
not necessarily the latest working forecast.

---

## 8. Benefits Register

Route: `/financials/benefits-register`

### Summary cards

- **Plan benefits:** gross planned claims in the filtered register.
- **Actual benefits:** actual metric values associated with benefit lines.
- **Risk-adjusted plan:** plan after each line's risk adjustment.
- **Finance validated:** plan value whose validation state is Finance validated.

### Benefit-line table

| Column | Interpretation |
|---|---|
| Initiative / benefit line | Owner context and specific value claim |
| Status | Draft, Submitted, Finance validated, or Rejected |
| Plan / Actual | Planned claim and recorded actual |
| Risk adjusted | Plan multiplied by the risk-adjustment percentage |
| Risk / handoff | Risk classification and realization-owner handoff state |
| Evidence | Link supporting the claim |

Filter to FY2028 and then Finance validated. Do not call the entire `$9.182M`
bankable unless the relevant lines have the required approval and evidence.

---

## 9. Benefit Tracking

Route: `/financials/benefit-tracking`

### Scope and granularity

- **Portfolio:** all locked plans and ledger actuals.
- **Workstream:** selected workstream only.
- **Initiative:** one initiative and its benefit lines.
- **Weekly / Monthly / Yearly:** changes period aggregation, not the underlying
  ledger rows.

### Summary and realization status

The summary compares locked bankable baseline with realized actual, variance,
and realization percentage. Status distribution identifies value not started,
on track, at risk, or realized according to the current ledger state.

### Locked baseline vs realized benefits

This is the primary realization comparison. A negative variance can reflect
timing, delivery leakage, evidence not yet accepted, or an outdated plan. Open
the initiative and its evidence before concluding that value has failed.

### Bankable plan baseline by initiative

This table shows which plan version supplies each initiative baseline. It is the
audit bridge from Bankable Plan to the realization report.

### Period table and initiative detail

The period table shows locked plan, realized value, variance, and realization
rate by period. Initiative scope exposes the underlying benefit lines and
ledger records. Finance/authorized benefit owners can add or import actual
realization; viewers cannot.

For ACME proof, use ENT-006, ENT-008, or ENT-010 because they contain seeded,
evidence-backed actuals.

---

## 10. Waterline

Route: `/financials/waterline`

- **Workstream:** selects the target population.
- **Lock date:** cutoff for approved initiatives.
- **Preview:** calculates included and excluded initiatives without writing a
  lock.
- **Lock target:** creates an immutable snapshot; use only when governance has
  approved the cutoff.
- **Locked target / Actuals / Variance:** committed workstream value compared
  with realization.
- **Included initiatives:** approved above the cutoff and their value source.
- **Below cutoff:** excluded or pending initiatives.
- **Immutable snapshots:** versioned lock history.

Waterline is a governance target, not a substitute for FY2028 Financial
Overview. Its value may use the configured lock basis and cutoff rather than a
single-year dashboard total.

---

## 11. Shared Costs

Route: `/shared-costs`

Shared Costs is the audit source for central costs used by multiple initiatives.

- **Pools:** central plan/actual amounts and recurring/one-off classification.
- **Policy:** allocation method and eligible population.
- **Methods:** benefit weighted, equal split, manual amount, and fixed
  percentage.
- **Run preview:** expected allocation before lock.
- **Run history:** completed/locked allocation versions.
- **Reconciliation:** allocated total must equal the source pool amount.
- **Reporting settings:** control whether allocations affect Control Tower,
  Financial Overview, or Bankable Plan.

ACME uses four FY2028 pools: technology/data platform `$650K`, PMO/benefits
office `$400K`, change/training `$220K`, and advisory/vendor support `$180K`.
Open Control Tower after reviewing the locked runs.

---

## 12. Executive Control Tower

Route: `/reports/control-tower`

### Controls

- **Persona:** Management, Investor, or Owner changes the reporting lens.
- **Target Year:** select 2028 for the ACME shared-cost scenario.

### Portfolio summary

Initiatives, red, amber, realized, and attention counts provide the operating
state for the selected persona/year.

### Burdened Value Bridge

| Row | Meaning |
|---|---|
| Benefits | Direct initiative benefit plan/actual |
| Direct Costs | Costs owned directly by initiatives |
| Allocated Costs | Share of eligible central cost pools |
| Burdened Costs | Direct plus allocated cost |
| Net Before Allocation | Benefits less direct cost |
| Net After Allocation | Benefits less direct and allocated cost |

Use **Net After Allocation** for fully loaded economics. Reconcile Allocated
Costs to locked runs in Shared Costs.

### Dependency Risk

Total, blocking, at-risk, overdue, critical-path, and resolved counts explain
delivery dependencies that can threaten value timing.

### Needs Attention

This list is the exception queue. Each reason should lead to an owner, action,
governance decision, or initiative drilldown.

### Initiative Burdening

The table combines RAG, realization status, benefits, benefits actual, burdened
cost, burdened actual, and net after allocation by initiative. Use it to identify
an initiative that looks attractive on direct cost but weak after central cost
allocation.

---

## 13. ACME Validation Runbook

### Step 1 — establish an unfiltered view

1. Sign in to the ACME tenant with a permitted management or Finance role.
2. Confirm all dashboard entries are enabled by the tenant administrator.
3. Clear business-unit, workstream, stage, tag, and cost-category filters.
4. Use FY2028 and Plan Base unless validating actuals.

### Step 2 — validate the absolute bridge

On Financial Overview confirm:

- baseline revenue `$20.000M`;
- revenue uplift `$4.000M` in the target-revenue formula;
- target revenue `$24.000M`;
- baseline gross margin `$9.000M`;
- gross-margin uplift `$5.432M` in the target-margin formula;
- target gross margin `$14.432M`;
- target margin rate `60.1%`.

### Step 3 — validate transformation value

Turn Benefits and Actuals on. Confirm:

- plan benefits `$9.182M`;
- recurring plan cost `$0.800M`;
- net plan run-rate `$8.382M`;
- actual benefit `$4.080M`;
- recurring actual cost `$0.388M`;
- net actual `$3.692M`.

State that seeded actuals are through `2028-06-30`.

### Step 4 — prove contributors

1. Switch to monthly granularity.
2. Select `2028-M01` in the trend or period table.
3. Reconcile the contributor drawer to that period.
4. Open Initiative Portfolio and compare initiative net contributions.
5. Open one material initiative and inspect its Overview P&L bridge,
   Financials, benefit lines, costs, and evidence.

### Step 5 — prove approval and realization

1. In Benefits Register, filter FY2028 and Finance validated.
2. In Bankable Plan, show the current locked version and ENT-005 version 2.
3. In Benefit Tracking, compare locked baseline to actual ledger realization.
4. Drill into ENT-006, ENT-008, or ENT-010.

### Step 6 — prove investment and fully loaded economics

1. In Investments & Payback, confirm `$2.500M` one-off investment and about
   `3.6 months` payback.
2. In Shared Costs, confirm each locked run reconciles to its pool.
3. In Control Tower, select FY2028 and reconcile Allocated Costs to Shared
   Costs.
4. Present Net After Allocation as fully burdened value.

### Pass criteria

- No total is quoted while an unintended filter is active.
- Baseline, target, benefit, cost, net, and actual are named distinctly.
- Target gross margin excludes cost savings.
- One-off investment is excluded from run-rate net but included in payback.
- Actuals are identified as YTD when the period is incomplete.
- Contributor totals reconcile to the selected Financial Overview period.
- Benefit claims have visible validation/evidence status.
- Realized values reconcile to locked bankable plans and ledger periods.
- Allocated shared costs reconcile to locked allocation runs.

---

## 14. Common Interpretation Errors

| Error | Correct interpretation |
|---|---|
| “FY2028 gross margin is `$9.182M`.” | `$9.182M` is total transformation benefits. Target gross margin is `$14.432M`. |
| “The baseline plus all benefits equals target gross margin.” | Only gross-margin uplift is added to baseline gross margin. Savings stay in benefits/net value. |
| “Net run-rate includes the `$2.500M` investment.” | Net run-rate subtracts recurring costs. One-off investment is analyzed separately in payback. |
| “Actual `$3.692M` is the FY2028 full-year result.” | The seeded actual is through 2028-06-30. |
| “Waterline must equal the FY2028 dashboard.” | Waterline uses its approved cutoff and locked value basis. |
| “Net Before Allocation is fully loaded value.” | Net After Allocation includes shared-cost burden. |
| “A dashboard empty state means the tenant has no data.” | It may mean filters, user ownership, role visibility, or missing enabled dashboard configuration. |

---

## 15. Troubleshooting

| Symptom | Check |
|---|---|
| Target cards do not appear | Confirm tenant annual revenue/gross-margin baselines exist for a year no later than the selected target year. |
| Target values are zero | Confirm FY2028 Plan Base revenue-uplift and gross-margin-uplift values exist. |
| Benefits do not equal expected value | Check active benefit metrics, scenario, year, stage, and value basis. |
| Actuals are zero | Confirm Actual scenario metric values or benefit-ledger rows exist and Actuals is on. |
| Contributor drawer is empty | Use a monthly row such as `2028-M01` and clear unintended filters. |
| Bankable Plan is editable | The initiative has not yet produced a current locked plan through governance. |
| Benefit Tracking baseline is zero | Confirm a current bankable plan exists for the selected scope. |
| Control Tower allocated costs are zero | Confirm a shared-cost run is completed/locked and reporting inclusion is enabled. |
| A dashboard menu entry is missing | Ask a tenant administrator to enable it under Admin > Dashboard Configuration. |
