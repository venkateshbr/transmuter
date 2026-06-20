# ACME Transformation Value Demonstration Guide

This guide explains how the **Acme Global Manufacturing** transformation tenant is
structured, how initiative financials are calculated, and how to demonstrate
value through Transmuter dashboards and reports.

It is written for business reviewers who need to explain the 10 ACME initiatives,
the FY26 baseline, FY27/FY28 value delivery, one-off and recurring costs, EBITDA
impact, and the dashboard story.

No credentials are included in this guide.

---

## 1. Executive storyline

ACME is modeled as a two-year enterprise transformation that starts from an FY26
baseline and targets run-rate value by FY28.

The portfolio story is:

1. ACME has a baseline business of **$20.0M annual revenue** and **$9.0M annual
   gross margin** in FY26.
2. The transformation portfolio contains **10 initiatives** across automation,
   offshoring, commercial growth, data platform, procurement, and service desk
   automation.
3. FY27 is the ramp year. Initiatives start generating value, but recurring run
   costs and one-off implementation costs are also incurred.
4. FY28 is the run-rate target year. The portfolio is expected to deliver:
   - **$4.0M revenue uplift**
   - **$5.4M gross margin uplift**
   - **$3.75M cost savings**
   - **$0.8M recurring run cost**
   - **$8.35M EBITDA-effective net run-rate value**
5. One-off implementation investment totals **$2.5M**. It is visible in the
   bridge and cost reports, but it should not be confused with recurring
   EBITDA drag.
6. Shared platform, PMO, advisory, and change costs are managed separately from
   direct initiative costs. They affect burdened executive reporting only after
   Finance approves or runs an allocation.

The clean executive message is:

> ACME is moving from a $20.0M revenue / $9.0M gross margin FY26 baseline toward
> a FY28 run-rate case with $4.0M revenue growth and $8.35M EBITDA-effective net
> run-rate value after recurring operating costs.

When discussing shared costs, add:

> Direct initiative economics remain the owner-accountable view. Executive
> Control Tower can also show a fully loaded view after shared platform, PMO, or
> support costs are allocated across the initiatives that benefit from them.

---

## 2. How the initiatives are structured

Each initiative belongs to a business unit, a workstream, and a value tag. The
tenant uses these dimensions for portfolio filtering, dashboard drilldowns, and
executive reporting.

| Code | Initiative | Business unit | Workstream | Tag | Value type |
|---|---|---|---|---|---|
| ENT-001 | Transformation PMO & Benefits Office | Corporate | Automation | other | Capability building |
| ENT-002 | Finance Process Automation | Shared Services | Automation | automation | Cost reduction |
| ENT-003 | Customer Onboarding Automation | Commercial | Automation | automation | Revenue growth |
| ENT-004 | Back-office Finance & HR Offshoring | Shared Services | Offshoring & Operating Model | offshoring | Cost reduction |
| ENT-005 | Enterprise Data Platform | Technology | ERP & Data Platform | automation | Capability building |
| ENT-006 | Pricing & Discount Optimization | Commercial | Commercial Growth | commercial | Revenue growth |
| ENT-007 | Sales Coverage Expansion | Commercial | Commercial Growth | commercial | Revenue growth |
| ENT-008 | Procurement Vendor Consolidation | Operations | Procurement & Supply Chain | offshoring | Cost reduction |
| ENT-009 | Supply Chain Control Tower | Operations | Procurement & Supply Chain | automation | Cost avoidance |
| ENT-010 | AI Service Desk Automation | Technology | Automation | automation | Cost reduction |

Each initiative also has:

- an owner and group owner,
- stage and RAG status,
- milestones for baseline approval and FY28 run-rate activation,
- risks and status updates,
- financial baseline rows,
- monthly financial metric values,
- cost lines split between one-off and recurring costs.

In the seeded ACME scenario all initiatives are in progress. Some are tagged
amber to show execution risk, but the financial model is populated for all 10.

---

## 3. Baseline concept

The baseline is the starting point before transformation value is counted.

ACME uses FY26 as the baseline year:

| Baseline metric | Portfolio baseline |
|---|---:|
| Annual revenue baseline | $20.0M |
| Annual gross margin baseline | $9.0M |
| Baseline gross margin rate | 45.0% |

The tenant baseline is allocated down to individual initiatives. For example,
commercial initiatives receive a portion of the FY26 revenue and gross margin
baseline so their uplift can be measured against a real starting point.

Baseline metrics answer:

- What revenue or margin already existed before the initiative?
- What is the denominator for growth percentages?
- What is the starting point for target revenue and target gross margin?

Baseline values are not the delivered benefit. They are the reference point used
to calculate uplift.

---

## 4. Financial scenarios

ACME uses four scenario lanes:

| Scenario | Meaning | How to use it |
|---|---|---|
| Baseline | FY26 starting point | Use for original revenue and gross margin reference. |
| Base | Conservative plan case | Use as the main board or steering committee plan. |
| High | Upside plan case | Use to show upside if adoption and execution outperform. |
| Actuals | Realized or latest actual case | Use to compare delivery against plan. |

In the seed data:

- FY27 plan base is the ramp case.
- FY28 plan base is the run-rate target case.
- High case applies upside multipliers to revenue, margin, and savings.
- Actuals are loaded below plan to demonstrate variance reporting.

---

## 5. Financial metrics

The ACME financial engine has these main metrics:

| Metric | What it means | EBITDA treatment |
|---|---|---|
| Annual Revenue Baseline | Starting annual revenue before transformation | Baseline only, not a benefit. |
| Annual Gross Margin Baseline | Starting annual gross margin before transformation | Baseline only, not a benefit. |
| Revenue Uplift | Incremental revenue attributed to initiatives | Revenue driver, not automatically EBITDA unless converted to margin. |
| Gross Margin Uplift | Incremental gross margin value | EBITDA-effective benefit. |
| Cost Savings | Recurring savings or avoided spend | EBITDA-effective benefit. |
| Target Revenue | Baseline revenue plus revenue uplift | Formula metric. |
| Target Gross Margin | Baseline gross margin plus gross margin uplift | Formula metric. |
| Revenue Growth % | Revenue uplift divided by baseline revenue | Formula metric. |
| Gross Margin Run-rate % | Target gross margin divided by target revenue | Formula metric. |
| Gross Margin Improvement % | Gross margin uplift divided by baseline gross margin | Formula metric. |

For EBITDA reviews, focus on:

```text
Gross Margin Uplift + Cost Savings - Recurring Costs
```

Revenue uplift is important, but it is better treated as the commercial driver.
The EBITDA effect of revenue should be visible through gross margin uplift.

---

## 6. Portfolio value calculations

### FY27 ramp case

FY27 plan-base value across all 10 initiatives:

| Driver | Amount |
|---|---:|
| Revenue uplift | $2.00M |
| Gross margin uplift | $2.62M |
| Cost savings | $2.00M |
| Recurring run cost | $0.40M |
| EBITDA-effective net run-rate value | $4.22M |

Formula:

```text
FY27 EBITDA-effective net value
= Gross Margin Uplift + Cost Savings - Recurring Costs
= $2.62M + $2.00M - $0.40M
= $4.22M
```

FY27 also includes one-off setup investment. That investment should be discussed
as implementation cost or payback, not as recurring EBITDA drag.

### FY28 run-rate case

FY28 plan-base value across all 10 initiatives:

| Driver | Amount |
|---|---:|
| Revenue uplift | $4.00M |
| Gross margin uplift | $5.40M |
| Cost savings | $3.75M |
| Recurring run cost | $0.80M |
| EBITDA-effective net run-rate value | $8.35M |

Formula:

```text
FY28 EBITDA-effective net value
= Gross Margin Uplift + Cost Savings - Recurring Costs
= $5.40M + $3.75M - $0.80M
= $8.35M
```

### Enterprise value including revenue uplift

If a reviewer asks for total enterprise value including revenue uplift, that is
a broader value view:

```text
FY28 enterprise value view
= Revenue Uplift + Gross Margin Uplift + Cost Savings - Recurring Costs
= $4.00M + $5.40M + $3.75M - $0.80M
= $12.35M
```

Do not describe this as EBITDA. It includes revenue uplift as a value driver.

---

## 7. One-off vs recurring costs

ACME cost lines are deliberately split into one-off and recurring costs.

### One-off costs

One-off costs are implementation investment. ACME categories include:

- implementation,
- technology tooling,
- training and change.

In the ACME scenario, total one-off investment is **$2.5M**. These costs are
loaded in FY27 and actuals are seeded at 95% of plan.

Use one-off costs to answer:

- What investment is required to unlock the benefit?
- What is the payback burden?
- Which initiatives have heavy setup cost?

Do not treat one-off costs as recurring EBITDA run-rate drag.

### Recurring costs

Recurring costs are ongoing run costs. ACME categories include:

- software,
- maintenance,
- labor.

Recurring costs ramp at 50% in FY27 and full run-rate in FY28. Actuals are
seeded at 97% of plan.

Use recurring costs to answer:

- What ongoing cost remains after transformation?
- What should be subtracted from run-rate EBITDA benefits?
- Which initiatives have operating-cost leakage?

Recurring costs are subtracted when calculating EBITDA-effective net run-rate
value.

---

## 8. How financials are entered in the system

Use the initiative financials tab for initiative-level entry.

Navigation:

```text
Initiatives -> open initiative -> Financials tab
```

The financials tab supports:

- scenario toggles: Baseline, Base, High, Actuals,
- monthly metric entry,
- computed formula rows,
- named benefit lines,
- one-off and recurring cost lines,
- import/export of initiative financial workbooks,
- assumptions on individual financial cells,
- financial scope configuration for metrics and cost categories.

### Benefit entry

Benefit values are stored as monthly metric values. Each value has:

- metric definition,
- scenario,
- year,
- month,
- amount,
- status,
- optional benefit line.

For ACME, annual benefit totals are divided into monthly values. For example, a
$1.2M annual benefit is entered as $100k per month across the year.

The user enters or loads:

- Revenue Uplift,
- Gross Margin Uplift,
- Cost Savings.

The system calculates:

- Target Revenue,
- Target Gross Margin,
- Revenue Growth %,
- Gross Margin Run-rate %,
- Gross Margin Improvement %.

### Cost entry

Cost lines are entered separately from benefits. Each cost line has:

- cost category,
- line name,
- plan or actual lane,
- amount,
- start period,
- end period if spread,
- recurring flag.

Use **one-off** mode for implementation costs. Use **spread** mode for recurring
costs that should distribute across months.

The financial engine then rolls cost lines into:

- recurring costs plan,
- recurring costs actual,
- one-off costs plan,
- one-off costs actual,
- total costs.

### Shared cost pools

Shared costs are central costs that benefit more than one initiative. They are
not entered as direct initiative cost lines by default. Finance manages them in
`/shared-costs` and allocates them for burdened executive reporting.

Use shared cost pools for:

- group technology and data platform costs,
- transformation PMO and benefits-office costs,
- shared cloud, license, or integration costs,
- change/adoption support teams,
- central advisory or vendor support.

Current dev proof:

| Pool | Year | Plan | Actual | Allocation basis | Report impact |
|---|---:|---:|---:|---|---|
| Group technology platform allocation | 2026 | `$600K` | `$540K` | Benefit weighted | Executive Control Tower allocated costs and net after allocation. |

Recommended canonical ACME pools for future demo refresh:

| Pool | Candidate initiatives | Basis |
|---|---|---|
| Group technology and data platform | ENT-002, ENT-005, ENT-006, ENT-009, ENT-010 | Gross Margin Uplift or technology-tag weighted. |
| Transformation PMO and benefits office | All 10 active or bankable initiatives | Equal split or value weighted. |
| Shared change and training support | ENT-002, ENT-004, ENT-005, ENT-010 | Manual amount or impacted-headcount weighted. |
| Central advisory/vendor support | ENT-005, ENT-008, ENT-009 | Fixed percentage by workstream. |

Default policy:

- Keep shared costs separate from direct initiative costs.
- Keep bankable plan values direct-only unless Finance enables burdened
  bankable reporting.
- Use Control Tower for the fully loaded executive view.

---

## 9. How to read the EBITDA value bridge

The value bridge explains how value moves from gross drivers to net value.

ACME bridge rows are configured as:

| Bridge row | Source | Sign | Interpretation |
|---|---|---:|---|
| Revenue Uplift | Revenue uplift metric | + | Commercial growth driver. |
| Gross Margin Uplift | Gross margin uplift metric | + | EBITDA-effective margin benefit. |
| Cost Savings | Cost savings metric | + | EBITDA-effective savings benefit. |
| Recurring Costs | Software, maintenance, labor costs | - | Ongoing cost subtracted from EBITDA run-rate. |
| One-off Costs | Implementation, tooling, training/change costs | - | Setup investment shown for transparency. |
| Net Value | Calculated net row | + | Net value after cost treatment. |

For EBITDA interpretation, use this bridge logic:

```text
EBITDA-effective net run-rate
= Gross Margin Uplift + Cost Savings - Recurring Costs
```

For investment/payback interpretation, also look at one-off costs:

```text
Investment burden
= One-off Costs
```

For broader enterprise value, include revenue uplift separately:

```text
Enterprise value view
= Revenue Uplift + Gross Margin Uplift + Cost Savings - Recurring Costs
```

If someone says "net value", ask which view they mean:

- EBITDA-effective net run-rate,
- enterprise value including revenue uplift,
- net after one-off investment,
- net after shared-cost allocation in the control tower.

That distinction prevents most value-bridge confusion.

---

## 10. Dashboards and reports to demonstrate value

### Dashboard

Navigation:

```text
/dashboard
```

Use the dashboard to start the executive story.

Recommended talking points:

- overall portfolio health,
- initiative count and RAG mix,
- stage distribution,
- value bridge summary,
- risks and executive decision queue,
- dashboard filters by business unit, workstream, priority, and tag.

Use this screen when the audience wants a short steering-committee view.

### Portfolio Financials

Navigation:

```text
/financials
```

Use Portfolio Financials as the reconciliation view. This is the best screen
for explaining the numbers.

It shows:

- summary cards for plan, actual, and variance,
- monthly, quarterly, and yearly rollups,
- benefits plan and actual,
- recurring costs,
- one-off costs,
- total costs,
- net value,
- in-year value,
- cumulative run-rate value ramp,
- drilldown contributors by period,
- filtering by year, stage, and cost category.

Recommended demonstration:

1. Set granularity to **Yearly**.
2. Review FY27 as the ramp year.
3. Review FY28 as the run-rate year.
4. Turn **Actuals** on to show variance.
5. Filter to a cost category to isolate recurring cost pressure.
6. Click a period to show contributing initiatives.

This is the strongest screen for proving that portfolio totals reconcile to
initiative financial data.

### Initiative Financials

Navigation:

```text
Initiatives -> initiative detail -> Financials
```

Use this screen when a reviewer asks where a number came from.

Show:

- Baseline scenario for original FY26 revenue and gross margin,
- Base scenario for plan,
- High scenario for upside,
- Actuals for current realized values,
- computed formula rows,
- one-off cost lines,
- recurring cost lines,
- assumptions and notes,
- workbook export/import.

Recommended use:

- Open ENT-006 Pricing & Discount Optimization to explain commercial revenue and
  margin uplift.
- Open ENT-004 Back-office Finance & HR Offshoring to explain savings and
  recurring operating-model costs.
- Open ENT-005 Enterprise Data Platform to explain high one-off investment and
  enabling-value logic.

### Executive Control Tower

Navigation:

```text
/reports/control-tower
```

Use the control tower for board or transformation-office governance.

It shows:

- burdened value bridge,
- direct costs,
- allocated costs,
- net before allocation,
- net after allocation,
- dependency risk,
- initiatives needing attention,
- initiative-level burdened value table,
- persona views for management, investor, and owner.

Shared-cost interpretation:

- **Allocated Costs** are shared-cost allocations from completed or locked runs.
- **Burdened Costs** are direct costs plus allocated shared costs.
- **Net After Allocation** is the fully loaded executive value view.
- Use target year `2026` for the current seeded group technology platform proof.
- Keep `/financials` as the direct portfolio financial view unless Finance has
  enabled generated cost-line posting.

Use this screen when the audience asks:

- Which initiatives need leadership attention?
- What is the value after direct and allocated costs?
- Which dependencies threaten value realization?
- Which initiatives have good value but weak execution health?

### Bankable Plan Review

Navigation:

```text
/financials/bankable-plan
```

Use this screen when Finance wants the governed baseline story.

ACME tenant settings require plan approval and baseline lock governance. The
bankable plan concept is:

- approve the business case,
- lock the baseline,
- compare future delivery against the locked plan,
- rebaseline only through governance.

### Benefit Tracking

Navigation:

```text
/financials/benefit-tracking
```

Use this when discussing realization discipline rather than planning.

It is intended for:

- plan vs realized benefit tracking,
- workstream or initiative rollups,
- benefit ledger review,
- realization status conversations.

### Waterline

Navigation:

```text
/financials/waterline
```

Use this to frame above/below baseline performance where configured.

It is useful when stakeholders ask:

- Which value is above the approved baseline?
- Which value is below plan?
- Where is the gap between committed and realized value?

---

## 11. Recommended executive demo flow

Use this order for a clean demo:

1. **Start at Dashboard**
   - Explain that ACME has 10 initiatives across five workstreams.
   - Show portfolio health, RAG mix, stage distribution, and key risks.

2. **Move to Portfolio Financials**
   - Switch to yearly view.
   - Explain FY26 baseline, FY27 ramp, and FY28 run-rate.
   - State the FY28 EBITDA-effective formula:

```text
$5.40M GM uplift + $3.75M cost savings - $0.80M recurring cost = $8.35M
```

3. **Drill into a sample initiative**
   - Open a commercial initiative for revenue and margin uplift.
   - Open a cost-reduction initiative for savings and recurring costs.
   - Show how monthly entries roll into portfolio totals.

4. **Explain one-off costs**
   - Show one-off setup costs separately from recurring costs.
   - Explain that one-off costs affect investment/payback, not recurring EBITDA
     run-rate.

5. **Open Executive Control Tower**
   - Show burdened value, dependencies, and needs-attention list.
   - Use this to connect financial value with execution risk.

6. **Close with the value statement**
   - FY26 baseline: $20.0M revenue and $9.0M gross margin.
   - FY28 plan-base: $4.0M revenue uplift and $8.35M EBITDA-effective net
     run-rate value.
   - One-off investment: $2.5M to unlock the transformation.

---

## 12. Common reviewer questions

### Why is revenue uplift separate from EBITDA?

Revenue is a top-line driver. EBITDA impact comes from the margin and savings
that revenue creates. In ACME, use Gross Margin Uplift as the EBITDA-effective
commercial value, not raw Revenue Uplift.

### Why do one-off costs show in the bridge if they do not reduce run-rate EBITDA?

They are shown for transparency and payback analysis. They explain the investment
required to deliver value. Recurring EBITDA should subtract recurring costs, not
one-time implementation spend.

### What is the difference between gross margin uplift and cost savings?

Gross margin uplift is incremental margin from growth, pricing, productivity, or
mix. Cost savings are reductions in recurring spend or avoided spend. Both are
EBITDA-effective when accepted by Finance.

### What should I call "net value" in an executive meeting?

Use precise language:

- **EBITDA-effective net run-rate value** when using GM uplift plus savings less
  recurring costs.
- **Enterprise value including revenue uplift** when revenue uplift is included.
- **Net after investment** when one-off implementation costs are subtracted.
- **Net after allocation** when shared costs have been allocated in the control
  tower.

### Which report is the source of truth?

Use **Portfolio Financials** and **Initiative Financials** for financial
reconciliation. Use **Dashboard** and **Executive Control Tower** for executive
storytelling, governance, and risk context.

---

## 13. Quick formulas

```text
Target Revenue
= Annual Revenue Baseline + Revenue Uplift
```

```text
Target Gross Margin
= Annual Gross Margin Baseline + Gross Margin Uplift
```

```text
Revenue Growth %
= Revenue Uplift / Annual Revenue Baseline
```

```text
Gross Margin Run-rate %
= Target Gross Margin / Target Revenue
```

```text
Gross Margin Improvement %
= Gross Margin Uplift / Annual Gross Margin Baseline
```

```text
EBITDA-effective Net Run-rate Value
= Gross Margin Uplift + Cost Savings - Recurring Costs
```

```text
Enterprise Value View
= Revenue Uplift + Gross Margin Uplift + Cost Savings - Recurring Costs
```

```text
Investment / Payback Cost
= One-off Costs
```
