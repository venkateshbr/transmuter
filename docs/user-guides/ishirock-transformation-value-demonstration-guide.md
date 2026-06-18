# Ishirock Transformation Value Demonstration Guide

This guide explains how the `ishirock` transformation tenant is structured, how
the workbook value case should be read, and how to demonstrate value through
Transmuter dashboards and reports.

It is written for business reviewers who need to explain the 21 workbook
initiatives, the FY25 baseline, the FY26-FY28 ramp, regional workstream value,
benefits, costs, actuals readiness, and management dashboards.

No credentials are included in this guide.

---

## 1. Executive Storyline

Ishirock is modeled as a regional transformation portfolio across four regional
workstreams. The source of truth for the target demo data is
`Initiative_Portfolio_Anonymised.xlsx`.

The portfolio story is:

1. The FY25 starting baseline is `$67.466M` revenue, `$87.960M` workbook
   margin/value baseline, `$13.265M` cost plan, and `$74.695M` net value.
2. The portfolio contains 21 initiatives across Westmark, Eastbridge,
   Northpeak, and Southgate regions.
3. The value levers are automation, offshoring, and commercial growth.
4. FY26 and FY27 are ramp years. FY28 is the run-rate demonstration year.
5. The FY28 plan-base case from the workbook is:
   - `$15.004M` revenue uplift
   - `$21.633M` gross margin value
   - `$3.560M` cost plan
   - `$18.073M` net value
6. The FY28 high case from `Financial Summary` is `$25.723M` net value.
7. Actuals are not yet fully loaded in the Ishirock tenant. Treat actuals as a
   readiness task before calling the tenant end-to-end demo complete.

The clean executive message is:

> Ishirock has a 21-initiative regional transformation portfolio with a FY25
> baseline of `$74.695M` net value and a FY28 plan-base run-rate opportunity of
> `$18.073M` net value across automation, offshoring, and commercial growth.

---

## 2. Workbook Source And Counting Rule

Workbook source:

- `Initiative_Portfolio_Anonymised.xlsx`

Primary sheets:

| Sheet | Use |
|---|---|
| `Initiative Summary` | Initiative list, workstream, BU, tag, stage, RAG, priority, owner, FY25 baseline, and FY28 summary values. |
| `Charter Details` | Initiative purpose, scope, owners, stage gate, RAG, priority, dependencies, and governance detail. |
| `Financial Summary` | Annual plan-base and plan-high values by initiative and metric. Use this for annual reconciliation. |
| `Benefits` | Benefit lines and scenario lanes. |
| `Costs` | One-off, recurring, manual, plan, and actual cost lines. |
| `KPIs` | KPI definitions and base/high/actual KPI entries. |
| `Milestones` | Milestones, owners, planned dates, actual dates, and status. |
| `Risks` | Risk register and mitigation detail. |
| `Status Updates` | Existing narrative status updates. |
| `Dashboards` | Workbook-calculated management views for comparison. |

Important counting rule:

- `Initiative Summary` includes a `PORTFOLIO TOTAL` row.
- Do not add the `PORTFOLIO TOTAL` row to the 21 initiative rows.
- The totals in this guide use the 21 initiative rows only.

---

## 3. Initiative Portfolio

Each initiative belongs to a regional workstream, one or more business units,
and a value tag. These dimensions drive dashboard filters, value matrix
drilldowns, financial reports, and management review.

| Code | Initiative | Workstream | BU | Type | Tag | Owner | FY28 revenue | FY28 gross margin | FY28 cost | FY28 net |
|---|---|---|---|---|---|---|---:|---:|---:|---:|
| TOR-1 | CAL Accounting System Integration & Automation | Westmark Region | CAL | cost_reduction | automation | Dana Reyes | `$0.000M` | `$0.620M` | `$0.060M` | `$0.560M` |
| TOR-2 | CAL CoSec System Implementation, Integration & Automation | Westmark Region | CAL | cost_reduction | automation | Olivia Tan | `$0.000M` | `$0.920M` | `$0.100M` | `$0.820M` |
| TOR-3 | Offshoring to Tavel SSC (+ Automation) - Tax | Westmark Region | CAL | cost_reduction | offshoring | Marcus Lee | `$0.000M` | `$1.860M` | `$0.100M` | `$1.760M` |
| TOR-4 | Verland-Norvia New Logos - FDI | Westmark Region | VER | revenue | commercial | Lukas Brandt | `$1.100M` | `$0.720M` | `$0.640M` | `$0.080M` |
| TOR-5 | Advisory - Geographical Expansion | Westmark Region | CAL | revenue | commercial | Grace Liang | `$2.460M` | `$1.420M` | `$0.000M` | `$1.420M` |
| TOR-6 | Revenue Retention: Proactive Churn Management, Westmark | Westmark Region | GROUP, CAL, VER | revenue | commercial | Julien Moreau | `$0.400M` | `$0.240M` | `$0.000M` | `$0.240M` |
| EBR-1 | MER Billing System Integration & Automation | Eastbridge Region | MER | cost_reduction | automation | Priya Nadkarni | `$0.000M` | `$0.682M` | `$0.066M` | `$0.616M` |
| EBR-2 | Offshoring to Caldez SSC (+ Automation) - Payroll | Eastbridge Region | MER | cost_reduction | offshoring | Marcus Lee | `$0.000M` | `$1.674M` | `$0.090M` | `$1.584M` |
| EBR-3 | Audit Practice - Cross-Border Expansion | Eastbridge Region | MER | revenue | commercial | Niels Berg | `$2.829M` | `$1.633M` | `$0.000M` | `$1.633M` |
| EBR-4 | MER-RDG New Logos - Manufacturing | Eastbridge Region | RDG | revenue | commercial | Aisha Rahman | `$0.935M` | `$0.612M` | `$0.544M` | `$0.068M` |
| EBR-5 | RDG Document Automation & OCR Rollout | Eastbridge Region | RDG | cost_reduction | automation | Elena Vasquez | `$0.000M` | `$0.966M` | `$0.105M` | `$0.861M` |
| NPK-1 | FJD Reconciliation Automation (RPA) | Northpeak Region | FJD | cost_reduction | automation | Priya Nadkarni | `$0.000M` | `$0.589M` | `$0.057M` | `$0.532M` |
| NPK-2 | Offshoring to Solva SSC (+ Automation) - Bookkeeping | Northpeak Region | FJD | cost_reduction | offshoring | Aisha Rahman | `$0.000M` | `$2.232M` | `$0.120M` | `$2.112M` |
| NPK-3 | Advisory - Energy Sector Expansion | Northpeak Region | KLP | revenue | commercial | Niels Berg | `$1.968M` | `$1.136M` | `$0.000M` | `$1.136M` |
| NPK-4 | KLP New Logos - Public Sector | Northpeak Region | KLP | revenue | commercial | Marcus Lee | `$1.210M` | `$0.792M` | `$0.704M` | `$0.088M` |
| NPK-5 | FJD CoSec Workflow Automation | Northpeak Region | FJD | cost_reduction | automation | Wei Chen | `$0.000M` | `$0.828M` | `$0.090M` | `$0.738M` |
| NPK-6 | Revenue Retention: Proactive Churn Management, Northpeak | Northpeak Region | GROUP, FJD, KLP | revenue | commercial | Omar Haddad | `$0.500M` | `$0.300M` | `$0.000M` | `$0.300M` |
| SGT-1 | BNT Tax Compliance Automation | Southgate Region | BNT | cost_reduction | automation | Priya Nadkarni | `$0.000M` | `$0.651M` | `$0.063M` | `$0.588M` |
| SGT-2 | Offshoring to Pravin SSC (+ Automation) - Audit Support | Southgate Region | BNT | cost_reduction | offshoring | Grace Liang | `$0.000M` | `$1.581M` | `$0.085M` | `$1.496M` |
| SGT-3 | VSC New Logos - Financial Services | Southgate Region | VSC | revenue | commercial | Aisha Rahman | `$1.265M` | `$0.828M` | `$0.736M` | `$0.092M` |
| SGT-4 | Advisory - Geographical Expansion, Vandor | Southgate Region | VSC | revenue | commercial | Marco Bianchi | `$2.337M` | `$1.349M` | `$0.000M` | `$1.349M` |
| **Total** |  |  |  |  |  |  | **`$15.004M`** | **`$21.633M`** | **`$3.560M`** | **`$18.073M`** |

---

## 4. Portfolio Dimensions

### Workstream summary

| Workstream | Initiatives | FY28 gross margin | FY28 cost | FY28 net |
|---|---:|---:|---:|---:|
| Eastbridge Region | 5 | `$5.567M` | `$0.805M` | `$4.762M` |
| Northpeak Region | 6 | `$5.877M` | `$0.971M` | `$4.906M` |
| Southgate Region | 4 | `$4.409M` | `$0.884M` | `$3.525M` |
| Westmark Region | 6 | `$5.780M` | `$0.900M` | `$4.880M` |
| **Total** | **21** | **`$21.633M`** | **`$3.560M`** | **`$18.073M`** |

### Value tag summary

| Tag | Initiatives | FY28 net |
|---|---:|---:|
| automation | 7 | `$4.715M` |
| commercial | 10 | `$6.406M` |
| offshoring | 4 | `$6.952M` |

### Value type summary

| Type | Initiatives | FY28 revenue | FY28 gross margin | FY28 net |
|---|---:|---:|---:|---:|
| cost_reduction | 11 | `$0.000M` | `$12.603M` | `$11.667M` |
| revenue | 10 | `$15.004M` | `$9.030M` | `$6.406M` |

Use these summaries when explaining how the portfolio balances regional
delivery, automation, offshoring, and commercial expansion.

---

## 5. Baseline Concept

The FY25 baseline is the starting reference before transformation value is
counted.

Ishirock FY25 baseline from the 21 initiative rows:

| Baseline metric | Portfolio baseline |
|---|---:|
| Revenue baseline | `$67.466M` |
| Workbook margin/value baseline | `$87.960M` |
| Cost plan baseline | `$13.265M` |
| Net value baseline | `$74.695M` |

Baseline values answer:

- What financial state existed before the transformation case?
- What is the denominator for uplift and growth views?
- Which initiatives and regions carry the original revenue, margin, and cost
  starting point?

Baseline values are not realized benefits. They are reference values used to
measure uplift and run-rate movement.

Important validation note:

- The workbook field named `Gross Margin FY25 Base` is higher than FY25 revenue.
- That is not a valid conventional gross-margin relationship.
- The reason is that cost-reduction initiatives carry `$50.250M` of FY25
  margin/value baseline with `$0.000M` FY25 revenue baseline.
- Treat the field as a workbook margin/value baseline unless Finance confirms it
  should be configured as true accounting gross margin.

---

## 6. Financial Scenarios

Ishirock should use the configurable financial engine across all dashboards and
reports.

| Scenario | System key | Meaning | How to use it |
|---|---|---|---|
| Baseline | `baseline` | FY25 starting reference | Use for original revenue, gross margin, cost, and net baseline. |
| Plan Base | `plan_base` | Main management plan case | Use for the steering committee plan and readiness walkthrough. |
| Plan High | `plan_high` | Upside plan case | Use to show upside if execution and adoption outperform. |
| Actual | `actual` | Realized or latest actual case | Use for plan-vs-actual and benefit realization once actuals are loaded. |

Current readiness note:

- Plan Base and Plan High values are loaded for many Ishirock financial views.
- Actuals are currently incomplete. The dashboard and financial reports should
  show zero or partial actuals until actual scenario values and benefit ledger
  rows are entered.

---

## 7. Annual Portfolio Value

Use `Financial Summary` for annual plan reconciliation.

### Plan Base

| Year | Revenue | Gross margin | Cost plan | Net value |
|---|---:|---:|---:|---:|
| FY26 | `$1.690M` | `$3.266M` | `$2.205M` | `$1.061M` |
| FY27 | `$8.115M` | `$14.617M` | `$3.543M` | `$11.074M` |
| FY28 | `$15.004M` | `$21.633M` | `$3.560M` | `$18.073M` |

Formula:

```text
Net Value = Gross Margin - Cost Plan
FY28 Plan Base Net Value = $21.633M - $3.560M = $18.073M
```

### Plan High

| Year | Revenue | Gross margin | Cost plan | Net value |
|---|---:|---:|---:|---:|
| FY26 | `$2.535M` | `$4.324M` | `$2.205M` | `$2.119M` |
| FY27 | `$11.511M` | `$19.967M` | `$3.543M` | `$16.424M` |
| FY28 | `$20.208M` | `$29.283M` | `$3.560M` | `$25.723M` |

Formula:

```text
FY28 Plan High Net Value = $29.283M - $3.560M = $25.723M
```

Use Plan Base as the main committed management case. Use Plan High to discuss
upside if adoption, offshoring transition, commercial conversion, and automation
throughput outperform.

---

## 8. Benefits And Costs

The workbook contains:

| Area | Workbook rows | Meaning |
|---|---:|---|
| Benefit rows | 189 | 63 benefit lines across Plan Base, Plan High, and Actual lanes. |
| Cost rows | 66 | 33 cost lines across Plan and Actual lanes. |
| KPI rows | 249 | 83 KPIs across Base Case, High Case, and Actual lanes. |
| Milestones | 292 | Delivery evidence, stage readiness, and timing. |
| Risks | 33 | Risk register and mitigation evidence. |
| Status updates | 4 | Existing narrative updates for initiative history. |

Benefit interpretation:

- Revenue benefits drive commercial growth and market expansion.
- Gross margin benefits are the core financial value measure in the workbook.
- Automation and offshoring benefits are mostly cost-reduction and margin
  expansion levers.

Cost interpretation:

- Cost plan is subtracted from gross margin to calculate net value.
- Cost rows include one-off, annual spread, and manual lines.
- Actual cost rows need to be populated or validated before actual net value is
  demo-ready.

---

## 9. How To Read Dashboard Value

The main dashboard uses the configurable financial engine. The value bridge and
workstream/tag matrix are populated from:

- active financial scenarios,
- active metric definitions,
- active benefit metric values,
- financial cost lines.

For Ishirock:

1. Open `/dashboard`.
2. Set the value matrix year to FY28.
3. Confirm the Workstreams x Value Tags matrix has non-zero Plan Base and Plan
   High benefit values.
4. Open a cell to show contributing initiatives and their benefit/cost/net
   values.
5. Explain that Actual is expected to remain zero or partial until actual
   scenario values are entered.

Recommended dashboard message:

> The dashboard reads the same configurable financial engine used by Financial
> Overview and Initiative Portfolio.

---

## 10. Dashboards And Reports To Demonstrate Value

### `/dashboard`

Use for:

- executive portfolio health,
- pipeline stage and RAG status,
- risk heatmap,
- KPI pulse,
- FY28 value bridge,
- Workstreams x Value Tags matrix.

Demo talk track:

> This is the management landing page. It connects value, stage movement, risk,
> and KPI health. The FY28 value matrix lets us open any workstream/tag cell and
> inspect the initiatives behind the number.

### `/financials`

Use for:

- annual and monthly financial overview,
- selected year and value basis,
- benefit, cost, and net value reconciliation,
- contributor drawer,
- board pack export.

Demo talk track:

> Finance uses this as the portfolio reconciliation screen. For Ishirock, FY28
> Plan Base should reconcile to the workbook run-rate case after baseline,
> benefit validation, and financial configuration are complete.

### `/financials/initiative-portfolio`

Use for:

- initiative-level financial table,
- FY25 baseline visibility,
- FY28 plan values,
- initiative comparison across regions and value tags.

Demo talk track:

> This is the cross-initiative financial ledger. It is where management can see
> which initiatives carry the FY28 value and which baseline values still need to
> be entered.

### `/financials/benefits-register`

Use for:

- benefit-line ownership,
- validation status,
- evidence,
- risk adjustment,
- bankable and realized values.

Demo talk track:

> This is Finance's control register. It turns each benefit from an idea into a
> validated claim with ownership, evidence, and realization status.

### `/financials/bankable-plan`

Use for:

- locked approved plan snapshots,
- rebaseline history,
- approved benefit and cost cases.

Demo talk track:

> Once an initiative passes governance, the approved plan is locked here. Future
> actuals are compared against this bankable plan rather than a moving target.

### `/financials/benefit-tracking`

Use for:

- benefit realization ledger rows,
- actual realized value,
- variance against locked plan,
- realization evidence.

Demo talk track:

> This is where the business confirms value has actually landed. It is separate
> from plan entry and should be owned jointly by Finance, benefits control, and
> business benefit owners.

### `/financials/waterline`

Use for:

- workstream target locks,
- target versus realized comparison,
- regional delivery accountability.

Demo talk track:

> Waterline freezes workstream targets after approval so the program can track
> whether each region is above or below its committed value line.

### `/reports/control-tower`

Use for:

- management review,
- value, risk, milestones, and decisions in one view,
- steering committee walkthroughs.

Demo talk track:

> The control tower is the meeting view. It brings together the financial case,
> stage progression, risks, blockers, and decisions required from management.

---

## 11. Recommended Executive Demo Flow

1. Start with the portfolio storyline.
   - 21 initiatives.
   - Four regional workstreams.
   - FY25 net baseline `$74.695M`.
   - FY28 Plan Base net value `$18.073M`.
2. Open `/dashboard`.
   - Show RAG, stage, risk, KPI, and value matrix.
   - Drill into one regional value cell.
3. Open `/initiatives/pipeline`.
   - Filter by Westmark, Eastbridge, Northpeak, or Southgate.
   - Show stage, owner, priority, RAG, and tag distribution.
4. Open `/financials`.
   - Set FY28.
   - Explain Plan Base, Plan High, cost, and net value.
5. Open `/financials/initiative-portfolio`.
   - Show the initiative-level values and baseline fields.
6. Open one initiative detail page.
   - Show charter, financials, milestones, KPIs, risks, and status.
7. Open `/financials/benefits-register`.
   - Explain Finance validation and evidence.
8. Open `/financials/bankable-plan`.
   - Explain locked plan governance.
9. Open `/financials/benefit-tracking`.
   - Explain actual realization and why Ishirock actuals must be loaded before
     the tenant is demo-complete.
10. Close in `/reports/control-tower`.
    - Summarize value, risk, actions, and management decisions.

---

## 12. Common Reviewer Questions

### Why is the FY28 revenue total `$15.004M`, not `$30.008M`?

Because the `Initiative Summary` sheet contains both 21 initiative rows and a
`PORTFOLIO TOTAL` row. Adding all rows double-counts the portfolio. Use the 21
initiative rows only.

### What is the difference between gross margin and net value?

Gross margin is the value generated before subtracting the cost plan. Net value
is gross margin minus cost plan. In FY28 Plan Base:

```text
$21.633M gross margin - $3.560M cost plan = $18.073M net value
```

### Why are actuals zero or missing?

The tenant currently needs an actuals readiness pass. Enter or import actual
scenario values in initiative financials, then enter benefit realization ledger
rows in `/financials/benefit-tracking`.

### Which screen is the source of truth?

Use different screens for different controls:

| Question | Source |
|---|---|
| Portfolio value reconciliation | `/financials` |
| Initiative-level values | `/financials/initiative-portfolio` |
| Benefit-line status and evidence | `/financials/benefits-register` |
| Locked approved plan | `/financials/bankable-plan` |
| Realized benefit actuals | `/financials/benefit-tracking` |
| Executive summary and drilldown | `/dashboard` and `/reports/control-tower` |

### What must be done before calling Ishirock demo-ready?

At minimum:

- FY25 tenant and initiative baselines entered.
- Benefit lines submitted and Finance validated.
- Bankable plans locked for selected initiatives or all 21 initiatives.
- Actual financial scenario values entered where actuals are required.
- Benefit realization ledger rows entered.
- Workstream waterline targets locked.
- Dashboard, Financial Overview, Benefits Register, Bankable Plan, Benefit
  Tracking, Waterline, and Control Tower validated through the browser.

---

## 13. Quick Formulas

```text
FY28 Plan Base Net Value
= Gross Margin - Cost Plan
= $21.633M - $3.560M
= $18.073M
```

```text
FY28 Plan High Net Value
= Gross Margin - Cost Plan
= $29.283M - $3.560M
= $25.723M
```

```text
FY25 Baseline Net Value
= Workbook Margin / Value Baseline - Cost Plan Baseline
= $87.960M - $13.265M
= $74.695M
```
