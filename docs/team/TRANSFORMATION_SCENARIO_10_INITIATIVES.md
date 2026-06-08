# 10-Initiative Transformation Scenario for End-to-End Testing

> Purpose: provide a deterministic, realistic transformation portfolio that can be used for browser QA, API acceptance checks, and registration/bootstrap smoke tests.

## Scenario overview

- **Company:** Ishirock
- **Transformation horizon:** 30 months
- **Portfolio size:** 10 initiatives
- **Primary use:** end-to-end validation of financial planning, bankable-plan locking, benefit tracking, rollups, dashboard control-tower fallback, and scenario-aware reporting
- **Bootstrap intent:** when a new tenant is registered in dev/demo mode, the tenant should receive the standard system defaults *plus* this sample transformation portfolio so QA can test with real data immediately

## Portfolio design goals

The scenario is intentionally balanced across:

- revenue growth
- cost reduction
- compliance
- operating model change
- shared services / offshoring
- data and platform modernization
- AI/automation
- benefits tracking and realization

It should include:

- quarterly financials for at least 10 initiatives across 2–3 years
- a mix of base / high / actual values
- at least one initiative that has been approved and locked into a bankable plan
- monthly benefit-ledger rows for at least the first year after go-live
- cross-initiative dependencies that affect control-tower views
- enough variation to exercise planned-vs-actual fallback when scenario inputs are absent

## Recommended 10 initiatives

### Wave 1 — foundation and control

1. **TRN-001 — Transformation PMO & Benefits Office**
   - Purpose: portfolio governance, benefits governance, cadence, and reporting discipline
   - Why it exists: unlocks consistent reporting and gate management across the rest of the program

2. **TRN-002 — ERP Consolidation & Automation**
   - Purpose: consolidate legacy finance systems and automate key finance processes
   - Why it exists: establishes the finance operating foundation for later offshoring and analytics

3. **TRN-003 — Data Privacy & Regulatory Compliance Programme**
   - Purpose: regulatory remediation, controls uplift, privacy impact assessments, training
   - Why it exists: reduces execution risk and enables later data/platform rollouts

4. **TRN-004 — Group Productivity / Hybrid Ways of Working**
   - Purpose: collaboration tooling, employee enablement, and productivity lift
   - Why it exists: supports operating-model adoption and AI service rollout later

### Wave 2 — value capture and scale

5. **TRN-005 — North Asia Revenue Acceleration**
   - Purpose: pricing discipline, account segmentation, and key-account expansion
   - Why it exists: revenue-growth anchor for the portfolio

6. **TRN-006 — Back-office Offshoring (Finance & HR)**
   - Purpose: labour arbitrage, shared service transition, and run-rate savings
   - Why it exists: recurring cost reduction and a strong candidate for lock-on-approval

7. **TRN-007 — Procurement Savings Wave**
   - Purpose: vendor consolidation, contract renegotiation, and demand management
   - Why it exists: recurring savings with clear benefits tracking over time

8. **TRN-008 — Pricing & Discount Optimisation**
   - Purpose: margin uplift via pricing guardrails and discount governance
   - Why it exists: higher-margin recurring benefit with scenario sensitivity

### Wave 3 — automation and sustainment

9. **TRN-009 — Supply Chain Control Tower**
   - Purpose: inventory visibility, service-level improvement, and supply risk reduction
   - Why it exists: multi-scenario / operational improvement use case with real KPI tracking

10. **TRN-010 — AI Service Desk Automation**
    - Purpose: ticket deflection, knowledge automation, and service productivity gains
    - Why it exists: demonstrates modern automation benefits and post-go-live realization tracking

## Recommended timeline

### Months 0–6
- TRN-010 establishes the benefits office and transformation governance
- TRN-003 and TRN-002 begin foundational remediation
- TRN-004 improves adoption readiness

### Months 6–18
- TRN-005, TRN-006, TRN-007, and TRN-008 capture the main financial value
- TRN-002 reaches lock-on-approval and becomes the first bankable-plan baseline

### Months 18–30
- TRN-009 and TRN-010 enter scale / sustainment
- benefits ledger becomes the source of truth for realization vs. locked plan

## Data requirements for bootstrap

When the tenant is created, seed the following for each initiative:

- initiative master record
- 3 milestones minimum
  - charter / design
  - build / pilot
  - rollout / benefit lock-in
- quarterly financial rows across the 30-month horizon
- at least one actual row on initiatives that are already live
- cost lines where applicable
- dependencies between initiatives
- benefit-realization ledger rows for go-live initiatives
- governance metadata such as stage, RAG, owner, and priority

## Suggested dependency graph

- **TRN-001** depends on governance visibility from **TRN-010**
- **TRN-002** enables **TRN-006**, **TRN-008**, and **TRN-009**
- **TRN-003** must clear before broader platform rollout in **TRN-009** and **TRN-010**
- **TRN-004** supports adoption for **TRN-010**
- **TRN-005** depends on pricing governance from **TRN-008**
- **TRN-006** provides early savings and is a candidate for bankable-plan locking
- **TRN-007** and **TRN-008** reinforce recurring benefits in year 2
- **TRN-009** and **TRN-010** deliver sustainment value in years 2–3

## E2E test targets

Use this scenario to validate:

- registration/bootstrap behavior for a new tenant
- portfolio and initiative rollups
- bankable-plan lock and version snapshots
- benefit tracking weekly / monthly / yearly views
- planned-vs-actual fallback when base/high data is missing
- dashboard and control-tower mode labels
- financial charts and tables with non-empty real data
- dependency and risk summaries

## Acceptance rule of thumb

If the scenario is loaded correctly, a browser QA pass should be able to:

- log in with the new tenant admin
- open the dashboard and see non-zero portfolio data
- open the financial pages and find real initiatives rather than placeholder empties
- lock a bankable plan on one approved initiative
- inspect benefit-ledger rollups for at least one go-live initiative
- navigate to the control tower and confirm the same financial mode is propagated consistently
