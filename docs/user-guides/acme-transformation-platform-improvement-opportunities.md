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

Validated state as of 2026-06-22:

- ACME4 is now the canonical complete dev demo tenant. It was registered
  through the dev browser signup flow and enriched through browser automation
  against the current financial engine.
- ACME3 remains the legacy reference tenant for the original `ENT-*` initiative
  code sequence.
- The current platform now bootstraps financial engine defaults for new tenants,
  but not business units, workstreams, governance gates, or initiatives.
- Dashboard visibility is tenant-configurable in Admin. New tenants start with
  Executive Dashboard, Financial Overview, and Initiative Portfolio enabled;
  demo tenants should enable the remaining dashboards from Admin > Dashboard
  Configuration.

| Area | Current strength |
|---|---|
| Portfolio baseline | Tenant FY26 baseline is configured: `$20.0M` revenue and `$9.0M` gross margin. |
| Initiative baseline allocation | Initiative annual baselines reconcile back to the portfolio baseline. |
| Financial metric model | Baseline, revenue uplift, gross margin uplift, savings, target metrics, and percentage formulas are configured in the new financial engine. |
| Scenario discipline | Baseline, Plan Base, Plan High, and Actual are configured as separate lanes. |
| Cost classification | One-off investment and recurring costs are separated; one-off investment is used for payback, not recurring EBITDA drag. |
| FY28 management story | Financial Overview reconciles to `$8.35M` FY28 EBITDA-effective net run-rate value. |
| Investments and payback | `/financials/investments-payback` shows cumulative one-off investment through the selected value year and portfolio payback months. |
| Strategic dimensions | Business units, workstreams, markets, themes, and tags are configured in demo tenants. |
| Stage gates | Stage gate definitions and gate criteria exist for a five-gate transformation lifecycle in ACME4. |
| Contributor drilldown | FY28 portfolio contributor detail now includes benefit-line contribution and reconciles to Financial Overview. |
| Benefit controls | Benefit-line validation states, Benefits Register, locked Bankable Plan, and Benefit Tracking are implemented. |
| Board export | Financial board-pack export is available and returns a non-empty XLSX. |
| Dashboard configuration | Admin can enable, hide, label, group, and order dashboards per tenant. |

---

## 3. Implementation Status Of Earlier Opportunities

| Earlier opportunity | Current status | Notes |
|---|---|---|
| Gate criteria for all gates | Done | ACME4 validation has 5 active gates and 10 active criteria. |
| FY28 contributor drawer benefit drilldown | Done | Contributor totals reconcile to `$9.15M` benefits, `$0.80M` recurring costs, and `$8.35M` net run-rate. |
| Populate Benefit Tracking for ACME | Done for ACME4 | ACME4 has 240 benefit realization ledger rows loaded through the browser guide runner. |
| Populate Bankable Plan versions | Done for ACME4 | ACME4 has locked bankable plans for all 10 initiatives and `TRN-005` has version-2 history created through governed rebaseline request and approval. |
| Clarify Value Bridge basis | Mostly done | APIs and UI support target-year run-rate and related basis labels. Continue to watch for copy that could imply one-off investment reduces recurring EBITDA run-rate. |
| Finance sign-off per benefit line | Done | Benefit lines support Draft, Submitted, Finance Validated, and Rejected states with validation events. |
| Portfolio Benefits Register | Done | `/financials/benefits-register` exposes portfolio benefit lines, validation status, evidence, risk adjustment, and totals. |
| Portfolio board-pack export | Done | `/portfolio/board-pack.xlsx` exports a non-empty XLSX for selected basis/year. |
| Configurable tenant dashboards | Done | Admin > Dashboard Configuration controls menu visibility. |
| Investment payback dashboard | Done | `/financials/investments-payback` reports one-off investment, net run-rate, and payback months. |
| New-engine-only initiative creation | Done | Initiative creation now depends on financial engine definitions, scenarios, and cost categories, not legacy financial configuration groups/items. |
| Full ACME4 browser E2E | Done | `apps/web/e2e/acme4-full-demo-ui-e2e.mjs` signs in through the browser, enriches Acme4, imports ledger actuals, configures shared costs, requests and approves `TRN-005` rebaseline, and validates dashboard routes. |

---

## 4. Remaining Gaps And Current Findings

### Gap 1: ACME4 uses generated `TRN-*` initiative codes

Observation:

- ACME4 was created by the current platform and uses generated initiative codes
  `TRN-001` through `TRN-010`.
- Older ACME guide tables use the historical `ENT-001` through `ENT-010`
  scenario sequence.
- The browser runner maps `ENT-*` guide rows to ACME4's generated `TRN-*` codes
  by row order.

Why it matters:

- Demo instructions and ledger imports can appear inconsistent if users expect
  ACME4 to have `ENT-*` codes.

Recommendation:

- Keep guide tables in scenario order, but explicitly document the ACME4
  `ENT-*` to `TRN-*` mapping.
- Consider adding a tenant-level code-prefix setting if customers need
  branded initiative-code sequences.

Priority:

- Medium.

### Gap 2: Full UI data entry is still too manual for repeatable ACME setup

Observation:

- The guide is written for a normal user and remains valid, but entering all
  monthly financial values, cost lines, benefit ledger rows, shared-cost rules,
  milestones, KPIs, risks, and dependencies manually is lengthy.
- The current ACME4 E2E runner uses visible UI flows for initiative enrichment
  and shared-cost configuration. For the Benefit Tracking import, headless
  Chromium selected the mapped CSV in the UI file control, but the visible
  Import button did not reliably invoke the upload handler. The runner completes
  that import with the authenticated browser session and `FormData`.

Why it matters:

- A strict UI-only regression should be able to repeat the guide without direct
  database seed scripts. It should also be robust in headless CI.

Recommendation:

- Add first-class UI import/bulk actions for:
  - initiative portfolio setup,
  - financial benefit values,
  - cost lines,
  - benefit ledger rows,
- Harden the Benefit Tracking import button and file-selection event handling
  for headless browser automation.

Priority:

- High for sustainable guide regression.

### Gap 3: Demo tenant dashboard enablement is now a setup step

Observation:

- New tenants intentionally start with only Executive Dashboard, Financial
  Overview, and Initiative Portfolio enabled.
- ACME demos need additional dashboards such as Investments & Payback, Benefits
  Register, Benefit Tracking, Bankable Plan, Waterline, Shared Costs, and
  Control Tower.

Why it matters:

- A fresh tenant can be correctly configured but appear incomplete if dashboard
  configuration is not updated.

Recommendation:

- Keep the UI setup guide explicit: for ACME demos, enable all dashboard/report
  entries in Admin > Dashboard Configuration after financial setup.

Priority:

- Medium.

### Implemented: Bankable Plan rebaseline is governed

Observation:

- ACME4 has 10 locked bankable plans.
- `TRN-005` has a version-2 bankable plan created by a governed rebaseline
  request from `/financials/bankable-plan` and approval in `/pmo/governance`.
- The public rebaseline route now creates a pending governance submission; it no
  longer immediately changes the current bankable baseline.

Why it matters:

- Baseline changes affect Benefit Tracking, Waterline, dashboards, and board-pack
  exports, so they need approval and an audit trail before becoming current.

Recommendation:

- Keep rebaseline request, approval, and version history in the maintained ACME4
  browser E2E.
- Consider adding a richer preview delta later: current locked value, requested
  value, benefit delta, cost delta, and affected years before the request is
  submitted.

Priority:

- Done for governed workflow; delta preview is a future enhancement.

### Gap 5: Production ACME seeded data remains behind dev ACME4

Observation:

- The platform features are promoted to production.
- Production ACME demo data is still not at dev ACME4 parity for the full
  shared-cost/dependency proof.

Why it matters:

- Production demos may not show the complete ACME4 shared-cost and dependency
  story unless production data is backfilled.

Recommendation:

- Continue tracking production seeded-data parity separately from platform
  feature readiness.

Priority:

- Medium.

---

## 5. Recommended Product Roadmap Items

| Priority | Improvement | Outcome |
|---|---|---|
| P1 | Add maintained browser E2E coverage for the full ACME guide | ACME setup can be regression-tested end to end without relying on manual spot checks. |
| P1 | Add or harden bulk UI import paths for high-volume ACME data | The guide can be executed through visible tenant UI controls at production scale. |
| P1 | Harden Benefit Tracking import for headless UI automation | The ACME4 guide runner can complete ledger import through the visible Import button without a browser-authenticated `FormData` fallback. |
| P2 | Add dashboard-configuration checklist hints for demo tenants | Admins know why some dashboards are hidden by default and how to enable them. |
| P2 | Continue tightening value-basis copy around run-rate, payback, allocation, and cumulative views | Prevents confusion between EBITDA run-rate, enterprise value, one-off investment, and shared-cost burden. |
| P2 | Add rebaseline delta preview | Reviewers can compare current locked plan to requested scope before approving a new baseline. |
| P3 | Add richer realization confidence and ownership handoff views | Management can see gross value, risk-adjusted value, actual value, and post-go-live accountability. |

---

## 6. Demo Positioning

Use ACME4 for the full board-ready dev demo:

- `/dashboard`
- `/financials`
- `/financials/investments-payback`
- `/financials/initiative-portfolio`
- `/financials/benefits-register`
- `/financials/bankable-plan`
- `/financials/benefit-tracking`
- `/shared-costs`
- `/reports/control-tower`
- `/initiatives/pipeline`
- initiative detail tabs for Financials, Governance, Milestones, Dependencies,
  Status, and Team

ACME4 validation on 2026-06-22 confirmed:

| Area | Result |
|---|---:|
| Initiatives | 10 |
| Locked bankable plans | 10 |
| KPI rows | 11 |
| Risk rows | 10 |
| Milestones | 20 |
| Dependencies | 3 |
| Benefit ledger rows | 240 |
| Shared-cost pools and locked runs | 4 |
| Governed bankable-plan rebaseline | TRN-005 version 2 |

Use ACME3 only when the audience specifically needs the historical `ENT-*`
initiative-code sequence.
