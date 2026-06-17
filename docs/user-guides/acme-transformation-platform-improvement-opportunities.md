# ACME Transformation Platform Improvement Opportunities

This document reviews the ACME transformation value demo against common
transformation office and benefits-realization practices. It separates:

- current ACME configuration observations,
- platform or seed-data gaps,
- recommended improvements for board-grade transformation reporting.

References reviewed:

- PMI guidance on benefits realization roles, lifecycle, and value management:
  https://www.pmi.org/learning/library/guidelines-successful-benefits-realization-9909
- UK Government Project Delivery guidance on benefits registers, benefits
  profiles, benefits realization plans, and lifecycle review:
  https://projectdelivery.gov.uk/teal-book/home/part-e-planning-and-control/chapter-19-benefits-management/
- Gartner value realization office direction for measurable business outcomes:
  https://www.gartner.com/en/documents/7001498
- McKinsey transformation impact-tracking case examples around baseline,
  EBITDA gap, and initiative value tracking:
  https://www.mckinsey.com/capabilities/transformation/how-we-help-clients/wave/our-impact/energy-retailer-deploys-transformation-program-to-increase-baseline-and-improve-overall-ebitda

---

## 1. What Boards and Management Typically Look For

Board and management reviews usually look for evidence in six areas:

1. **Baseline clarity**
   - What was the starting point?
   - Who approved the baseline?
   - Is the baseline immutable or versioned after approval?

2. **Value bridge**
   - How do gross benefits convert to net EBITDA or cash impact?
   - What is revenue, margin, savings, recurring cost, and one-off investment?
   - What is in plan, forecast, actual, and run-rate?

3. **Ownership and accountability**
   - Who owns each initiative?
   - Who owns benefit realization after go-live?
   - Who validates the financial benefit?

4. **Stage-gate quality**
   - Which initiatives are ideas, validated, committed, executing, or realized?
   - What evidence is required to move stages?
   - Who approved each gate?

5. **Realization evidence**
   - What actual benefit has been realized?
   - How does actual compare to locked plan?
   - What is timing variance, value leakage, or over-delivery?

6. **Risk and decision support**
   - Which value is at risk?
   - What decisions are required?
   - What is the residual forecast after risks, delays, or adoption issues?

---

## 2. Current ACME Strengths

| Area | Current strength |
|---|---|
| Portfolio baseline | Tenant FY26 baseline is configured: `$20.0M` revenue and `$9.0M` gross margin. |
| Initiative baseline allocation | Initiative annual baselines reconcile back to the portfolio baseline. |
| Financial metric model | Baseline, revenue uplift, gross margin uplift, savings, target metrics, and percentage formulas are configured. |
| Scenario discipline | Baseline, Plan Base, Plan High, and Actual are configured as separate lanes. |
| Cost classification | One-off and recurring costs are separated. |
| FY28 management story | Financial Overview reconciles to `$8.35M` FY28 EBITDA-effective net run-rate value. |
| Strategic dimensions | Business units, workstreams, markets, themes, and tags are configured. |
| Stage gates | Stage gate definitions exist for a five-gate transformation lifecycle. |

---

## 3. Gaps Found in Current ACME Demo

### Gap 1: Gate criteria are not configured

Observation:

- ACME setup status is `7/8`.
- The missing check is gate criteria.

Why it matters:

- Benefits-realization practice expects clear evidence criteria before value is
  accepted as validated, committed, or realized.
- Without criteria, stage movement is weaker as an audit control.

Recommendation:

- Seed or configure criteria for each gate.
- Minimum criteria should include baseline approval, Finance validation,
  assumptions documented, delivery plan approved, and actual evidence submitted.

Priority:

- High for board-demo readiness.

### Gap 2: FY28 Financial Overview contributor drawer omits benefit contribution

Observation:

- `/financials` Year = 2028 correctly shows:
  - Benefits: `$9.15M`
  - Recurring costs: `$0.80M`
  - Net value: `$8.35M`
- The FY28 contributor endpoint currently returns cost contribution by initiative
  but benefit contribution as zero for clean financial-engine values.

Why it matters:

- A board reviewer will expect to click FY28 and see which initiatives drive the
  `$9.15M` benefits.
- The summary is correct, but the drilldown does not yet support the same
  benefit traceability.

Recommendation:

- Update portfolio contributor logic to include clean financial-engine metric
  value contributions by initiative, scenario, period, and benefit line.
- The drawer should show:
  - revenue uplift,
  - gross margin uplift,
  - cost savings,
  - recurring costs,
  - one-off costs,
  - net run-rate value.

Priority:

- High for management-demo credibility.

### Gap 3: Benefit Tracking is not populated for ACME

Observation:

- `/financials/benefit-tracking` currently has zero locked baseline amount and
  zero realized ledger amount for ACME.
- ACME has plan and actual financial values, but no locked bankable-plan
  snapshots or benefit ledger rows in the current seed.

Why it matters:

- Industry benefits realization separates planned value from realized value.
- Boards often ask whether benefits are realized, not just planned.

Recommendation:

- Seed locked bankable-plan snapshots for the 10 ACME initiatives.
- Seed benefit ledger actuals that reconcile to the current actual values.
- Add a demo script for locking a plan and submitting realization evidence.

Priority:

- High for full end-to-end realization demo.

### Gap 4: Bankable Plan screen lacks populated ACME versions

Observation:

- The Bankable Plan screen is available, but the ACME demo data does not include
  locked plan version history.

Why it matters:

- A locked plan provides the immutable comparator for benefit realization.
- Version history is critical for rebaseline governance.

Recommendation:

- Seed Gate 2 approvals and bankable plan snapshots.
- Add version history for at least one rebaseline example.

Priority:

- Medium-high.

### Gap 5: Portfolio Value Bridge needs clearer period/filter semantics

Observation:

- Financial Overview supports year, stage, and category filters.
- Portfolio Value Bridge appears to aggregate across broader value data and can
  be interpreted differently from the FY28 run-rate view.

Why it matters:

- Boards need to distinguish:
  - in-year value,
  - cumulative value,
  - target-year run-rate,
  - all-years value.

Recommendation:

- Add explicit labels and filters to the value bridge:
  - Year
  - Scenario
  - Stage
  - Workstream
  - Tag
  - Run-rate year versus cumulative all-years
- Display a clear basis label such as `FY28 run-rate` or `All-years plan`.

Priority:

- Medium.

### Gap 6: Finance sign-off is not explicit per benefit line

Observation:

- Benefit lines can capture confidence and assumptions, and gate approval can
  lock plans.
- There is no obvious per-benefit Finance sign-off state in the current UI.

Why it matters:

- Benefits-realization best practice usually requires Finance validation before
  value is counted as bankable or realized.

Recommendation:

- Add benefit-line validation status:
  - Draft
  - Submitted
  - Finance validated
  - Rejected / needs evidence
- Capture validator, timestamp, evidence link, and comment.

Priority:

- Medium-high.

### Gap 7: Benefits register/profile view is implicit, not explicit

Observation:

- Benefit lines exist within initiative financials.
- There is no standalone benefits register that shows all benefit lines,
  owners, assumptions, confidence, timing, evidence, and status.

Why it matters:

- Benefits management guidance commonly uses benefits registers and benefits
  profiles to manage realization through the lifecycle.

Recommendation:

- Add a portfolio Benefits Register screen with:
  - benefit line,
  - initiative,
  - owner,
  - metric,
  - baseline,
  - target,
  - forecast,
  - actual,
  - confidence,
  - Finance validation status,
  - evidence link,
  - realization date.

Priority:

- Medium.

### Gap 8: Board pack export is not yet first-class

Observation:

- Initiative workbook export exists.
- A board-ready portfolio pack export is not clearly available from the
  dashboard/financial screens.

Why it matters:

- Management and boards often need a repeatable monthly pack with consistent
  charts, filters, and commentary.

Recommendation:

- Add a portfolio board-pack export:
  - baseline page,
  - value bridge,
  - run-rate trend,
  - top initiatives,
  - workstream view,
  - risks and decisions,
  - realization status,
  - appendix with assumptions.

Priority:

- Medium.

---

## 4. Recommended Product Roadmap Items

| Priority | Improvement | Outcome |
|---|---|---|
| P1 | Fix clean-engine contributor drawer benefit drilldown | FY28 summary values become traceable to initiative contributors. |
| P1 | Seed ACME gate criteria, locked bankable plans, and benefit ledger rows | ACME becomes a complete end-to-end board demo. |
| P1 | Add Finance validation state per benefit line | Bankable and realized benefits become auditable. |
| P2 | Add Benefits Register screen | Transformation office can manage benefits across initiatives. |
| P2 | Add period/scenario filters and basis labels to Value Bridge | Prevents confusion between run-rate, in-year, and cumulative value. |
| P2 | Add portfolio board-pack export | Supports repeatable steering committee and board reporting. |
| P3 | Add realization confidence/risk-adjusted value views | Management can see gross value, risk-adjusted value, and actual value. |
| P3 | Add ownership handoff after go-live | Benefits remain accountable after implementation ends. |

---

## 5. Suggested ACME Seed Enhancements

To make the ACME tenant a complete demo, add:

1. Gate criteria for all five gates.
2. Gate 2 approval submissions for all 10 initiatives.
3. Bankable plan snapshots for all 10 initiatives.
4. Benefit ledger rows for FY27 and FY28 actuals.
5. At least one rebaseline example, preferably:
   - ENT-005 Enterprise Data Platform, because it is amber and has higher
     implementation cost.
6. Evidence links or assumption comments for:
   - ENT-006 Pricing & Discount Optimization,
   - ENT-008 Procurement Vendor Consolidation,
   - ENT-010 AI Service Desk Automation.
7. A board-demo meeting series linked to the portfolio and key initiatives.

---

## 6. Demo Positioning Until Gaps Are Closed

Use these screens as board-ready now:

- `/financials`
- `/initiatives/pipeline`
- initiative detail **Financials** tab
- initiative detail **Milestones**, **Risks**, **Status**, **Team**
- `/admin` configuration screens for setup explanation

Use these screens as workflow preview until ACME seed is enhanced:

- `/financials/bankable-plan`
- `/financials/benefit-tracking`
- `/financials/waterline`

Avoid claiming the following until fixed or seeded:

- That ACME has fully locked bankable plans.
- That ACME has realized benefit ledger values.
- That the FY28 contributor drawer fully explains benefit contribution.
- That stage movement criteria are complete.
