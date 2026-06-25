# Transmuter — End-to-End Test Runbook (8 Tenants)

Last updated: 2026-06-24

This runbook turns the eight test scenarios into **step-by-step UI sequences you follow one after another**, in the same style as the ACME demo tenant UI setup guide (`docs/user-guides/acme-demo-tenant-ui-setup-guide.md`). Each scenario is a separate tenant. Work through them top to bottom; within a scenario, follow the numbered steps in order.

All companies, people, and numbers are fictional. Values are in each tenant's reporting currency, in millions unless a raw figure is shown.

**Environments**

```text
Production:  https://transmuter.ishirock.tech
Dev / test:  https://transmuter-dev.ishirock.tech
```

Use **dev** for this runbook.

---

## Section A — The standard setup sequence (read once)

Every scenario reuses the same nine-step skeleton below. Each scenario section gives you the **data** for these steps plus any **deviations**; it does not re-print the clicks. When a scenario step says "run Standard Step n with the table below", come back here for the navigation.

> Screens referenced throughout: `/admin` (tabs: **Strategic Parameters**, **Access Control**, **Financial Configuration**, **Governance**), `/people`, `/initiatives/new`, `/initiatives/pipeline`, each initiative's **Financials** / **Governance** / **Milestones** / **KPIs** / **Risks** tabs, `/financials/*`, `/pmo/*`, `/reports/control-tower`.

**Standard Step 1 — Create the tenant**
1. Open the dev URL.
2. Select **Get Started**.
3. Create the tenant with the scenario's organization name and slug.
4. Complete signup / checkout and log in as the initial administrator.
5. Open `/dashboard` and confirm there is no portfolio data yet.
6. Open `/admin` and review **First-run setup**. Keep it open.

**Standard Step 2 — Master data** (`/admin` → **Strategic Parameters**)
1. Create the **Business units** from the scenario table. Save.
2. Create the **Workstreams** from the scenario table. Save.
3. Create **Market**, **Theme**, and **Tags** from the scenario table. Save.

**Standard Step 3 — Users** (`/people` + `/admin` → **Access Control**)
1. Create one `transformation_office` user, one `initiative_owner`, one `viewer`.
2. In **Access Control**, confirm each role. For a fast pass, the admin can own all initiatives.

**Standard Step 4 — Financial engine** (`/admin` → **Financial Configuration**)
1. **Reporting Settings** — set the scenario's **reporting currency** and **fiscal year start**. Save. *(This is the most common per-scenario deviation — do not skip.)*
2. **Scenarios** — confirm/create: `baseline` (Baseline), `plan_base` (Plan, **primary**), `plan_high` (Plan), `actual` (Actual).
3. **Metric Definitions** — confirm the default revenue / gross-margin / savings metrics. Add the scenario-specific metric only where the scenario calls for it. Precision `4` for money/percent.
4. **Tenant Annual Baselines** — enter the scenario's baseline-year revenue/margin.
5. **Cost Categories** — confirm one-off (implementation, technology, training) and recurring (software, labour) categories exist.
6. **Value Bridge Rows** — confirm the default bridge (baseline → uplift → savings → recurring cost → net run-rate).

**Standard Step 5 — Governance** (`/admin` → **Governance**)
1. Confirm the **five stage gates** (Identify → Validate to Plan → Build → Execute → Realize). Gate 2 = **Validate to Plan** = bankable-plan lock gate.
2. Confirm **Gate criteria** (baseline approved, benefit assumptions documented, finance validation completed for Gate 2).
3. Enable the full **dashboard menu** for the tenant.

**Standard Step 6 — Create initiatives** (`/initiatives/new`)
1. For each row in the scenario's initiative table, select **Create with Transmuter** and enter name, BU, workstream, tag, type, priority, RAG, stage, owner, impact type, planned start/end, summary, value logic, dependencies text.

**Standard Step 7 — Financials: baselines, benefits, costs** (initiative **Financials** tab)
1. Open each initiative → **Financials**.
2. Enter **Plan Base** and **Plan High** benefit-line values from the scenario's financial table.
3. Enter **cost lines** (one-off and recurring) where the scenario specifies them.

**Standard Step 8 — Milestones, KPIs, risks, dependencies** (initiative tabs)
1. **Milestones** — add the scenario's milestones with planned dates and status.
2. **KPIs** — add the scenario's KPIs with type, unit, direction, baseline, target; enter the latest actual.
3. **Risks** — add the scenario's risks with type, impact, likelihood, status.
4. **Dependencies** — link the predecessor/successor pairs from the scenario.

**Standard Step 9 — Validate, lock, actuals**
1. **Validate benefits** — initiative **Financials** → submit each benefit line to Finance → set the validation status the scenario specifies (Draft / Submitted / Finance Validated / Rejected).
2. **Lock** (only where the scenario marks an initiative *Locked*) — initiative **Governance** → **Gate 2: Validate to Plan** → tick all criteria → submit → approve → `/financials/bankable-plan` → confirm **Locked** + version number.
3. **Actuals** — initiative **Financials** → **Actuals** → **Edit Details** → enter actual metric/cost values. Realization ledger rows: `/financials/benefit-tracking` → **Ledger Entries**.

Each scenario then ends with a **Validation** block — numbered dashboard checks with expected results.

---

## Scenario 1 — Meridian Logistics Group (SGD) — pressure scoring & planned-vs-actual

**Tests:** planned_vs_actual mode, decrease-good operational KPIs, pressure score from overdue milestone + open risk + KPI miss.

**Step 1 — Create tenant.** Org name `Meridian Logistics Group`, slug `meridian`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Operations; Technology; Procurement; Corporate | Operations; Technology; Procurement | Market: Singapore / APAC · Theme: Supply-chain cost & service transformation · Tags: `cost`, `automation`, `ops`, `other` |

**Step 3 — Users.** Standard three roles.

**Step 4 — Financial engine.** Reporting currency **SGD**, fiscal year **January**. Baseline year FY26. Standard scenarios and metrics.

**Step 5 — Governance.** Standard five gates.

**Step 6 — Create initiatives.** Common fields: impact **Recurring** (except MER-006 = One-off), planned start `2026-01-01`, planned end `2027-12-31`, stage **Executing**.

| Code | Name | BU | Workstream | Type | Pri | RAG |
|---|---|---|---|---|---|---|
| MER-001 | Network & Route Optimisation | Operations | Operations | Cost Reduction | High | Green |
| MER-002 | Supply Chain Control Tower | Technology | Technology | Cost Reduction | High | Amber |
| MER-003 | Warehouse Labour Productivity | Operations | Operations | Cost Reduction | Medium | Green |
| MER-004 | Fuel & Fleet Telematics | Operations | Operations | Cost Avoidance | Medium | Amber |
| MER-005 | Procurement Demand Management | Procurement | Procurement | Cost Reduction | Medium | Green |
| MER-006 | Returns & Reverse-Logistics Rework | Operations | Operations | Cost Avoidance | Low | Amber |

**Step 7 — Financials (benefit lines, SGD m).**

| Code | Benefit class | Plan Base | Plan High | Actual-to-date |
|---|---|---:|---:|---:|
| MER-001 | Savings | 14.2 | 18.6 | 5.8 |
| MER-002 | Savings | 9.4 | 12.1 | 1.2 |
| MER-003 | Savings | 6.7 | 8.9 | 3.1 |
| MER-004 | Avoidance | 4.1 | 5.5 | 0.4 |
| MER-005 | Savings | 7.8 | 9.2 | 0.9 |
| MER-006 | Avoidance | 2.3 | 3.0 | 0.0 |

**Step 8 — Milestones / KPIs / risks / dependencies.**
- Milestones: MER-002 *Control-tower data integration* planned `2026-04-30`, status **Overdue** (pressure driver); MER-002 *Carrier API onboarding* `2026-06-15` In progress; MER-001 *Phase-2 lane rollout* `2026-03-20` Complete.
- KPIs: MER-001 *Cost per shipment (SGD)* operational, decrease-good, baseline 42.10 / target 36.00 / actual 38.40 → on_track. MER-002 *On-time-in-full %* increase-good, 87.2 / 94.0 / 88.1 → at_risk. MER-003 *Units / labour hr* 61 / 78 / 72 → on_track. MER-004 *Fuel cost / 100km* decrease-good, 31.5 / 27.0 / 31.2 → critical.
- Risks: MER-002 *Carrier integration delays* technology, **high impact / medium likelihood**, open. MER-004 *Driver adoption* people, medium / high, open. MER-001 *Seasonality erodes savings* financial, medium / low, open.
- Dependencies: MER-005 depends on MER-002; MER-004 depends on MER-001.

**Step 9 — Validate / actuals.** Finance-validate all benefit lines. **No locks.** Enter the Actual-to-date values from Step 7 via **Financials → Actuals → Edit Details** (this puts the tenant in planned-vs-actual mode).

**Validation**
1. `/financials` — MER-001/003 show **planned-vs-actual variance**, not a base/high toggle.
2. `/initiatives/:id` (MER-002) — open the **pressure** breakdown; `schedule`, `milestone_health`, `risk_exposure`, `kpi_performance` are all non-zero.
3. `/pmo/kpis` — MER-001 (decrease-good) reads on_track while trending down toward target; MER-004 reads critical.
4. `/financials/initiative-portfolio` — cost-reduction rollup totals in **SGD**.

---

## Scenario 2 — Aurelia Retail Holdings (GBP, April FY) — multi-scenario & actual benefits

**Tests:** multi_scenario base/high, non-January fiscal year, margin vs revenue benefit classes, and an actual that beats plan without requiring a locked baseline.

**Step 1 — Create tenant.** Org `Aurelia Retail Holdings`, slug `aurelia`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Commercial; Digital; Operations; Corporate | Commercial; Digital; Operations | Market: United Kingdom · Theme: Omnichannel revenue & margin · Tags: `revenue`, `margin`, `digital`, `other` |

**Step 4 — Financial engine.** Reporting currency **GBP**, fiscal year **April**. Baseline FY26 (Apr-25→Mar-26). Ensure metric `gm_uplift` carries benefit class **Margin** and `revenue_uplift` carries **Revenue**.

**Step 6 — Create initiatives.** Impact **Recurring**, stage **Executing**, planned `2025-04-01`→`2026-09-30`.

| Code | Name | BU | Workstream | Type | Pri | RAG |
|---|---|---|---|---|---|---|
| AUR-001 | Pricing & Markdown Optimisation | Commercial | Commercial | Revenue Growth | High | Green |
| AUR-002 | Loyalty & Personalisation | Digital | Digital | Revenue Growth | High | Green |
| AUR-003 | Range & Margin Mix | Commercial | Commercial | Revenue Growth | Medium | Green |
| AUR-004 | Store Labour Scheduling | Operations | Operations | Cost Reduction | Medium | Green |
| AUR-005 | Omnichannel Fulfilment | Digital | Digital | Revenue Growth | Low | Amber |

**Step 7 — Financials (GBP m).**

| Code | Benefit class | Plan Base | Plan High | Actual |
|---|---|---:|---:|---:|
| AUR-001 | Margin | 11.6 | 15.2 | **12.1** (beats base) |
| AUR-002 | Revenue | 8.3 | 11.7 | 4.6 |
| AUR-003 | Revenue | 6.9 | 9.4 | 1.8 |
| AUR-004 | Savings | 4.2 | 5.1 | 2.7 |
| AUR-005 | Revenue | 3.4 | 5.8 | 0.3 |

**Step 8.** KPIs: AUR-001 *Gross margin %* gross_margin type, increase-good, 38.4 / 41.0 / 40.6 → on_track; *Full-price sell-through %* 61 / 70 / 69 → on_track. AUR-002 *Repeat purchase rate %* 22.1 / 30.0 / 26.8 → on_track. Milestones: AUR-001 *Pricing engine go-live* `2025-11-01` Complete; AUR-003 *Range review sign-off* `2026-05-30`. Risks: AUR-005 *Peak fulfilment SLA* operational, medium/medium, open; AUR-002 *Opt-in below model* financial, low/medium, open.

**Step 9.** Finance-validate all. Enter AUR-001 Actual `12.1`. No locks (this scenario demonstrates live multi-scenario and actual-value handling, not bankable lock realization).

**Validation**
1. `/financials` — toggle **Plan Base ↔ Plan High**; totals switch cleanly.
2. AUR-001 Actual shows **favourable variance** (12.1 > 11.6) without breaking the rollup.
3. `/financials/waterline` — **Margin** and **Revenue** appear as distinct bands.
4. FY columns label **Apr–Mar**; in-year run-rate uses the April cut.
5. `/financials/benefits-register` and initiative Financials — AUR-001 shows Actual `12.1` and finance-validated status. Locked-baseline realization ledger coverage remains in Scenario 5.

---

## Scenario 3 — Nordvik Manufacturing (EUR) — bankable lock & cost behaviours

**Tests:** bankable_locked mode, the `approved_at ≤ lock_date` cut-off, cost_avoidance + capability_building, one-time capex + recurring cost with inflation, finance_validated benefits, zero-benefit compliance.

**Step 1 — Create tenant.** Org `Nordvik Manufacturing`, slug `nordvik`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Operations; Technology; People; Governance | Operations; Technology; People; Governance | Market: Germany / EU · Theme: Industrial cost & capability · Tags: `avoidance`, `capability`, `compliance`, `other` |

**Step 4 — Financial engine.** Reporting currency **EUR**, fiscal year **January**. Confirm a recurring cost category supports an **inflation %** field.

**Step 6 — Create initiatives.** Stage **Executing** (NOR-006 = **Build**).

| Code | Name | BU | Workstream | Type | Impact | Pri | RAG |
|---|---|---|---|---|---|---|---|
| NOR-001 | Energy & Utilities Reduction | Operations | Operations | Cost Avoidance | Recurring | High | Green |
| NOR-002 | Predictive Maintenance Platform | Technology | Technology | Cost Avoidance | Recurring | High | Green |
| NOR-003 | Plant Automation (Cell 4/5) | Operations | Operations | Cost Reduction | One-off | High | Amber |
| NOR-004 | Engineering Capability Academy | People | People | Capability Building | One-off | Medium | Green |
| NOR-005 | EU Energy Compliance (CSRD) | Governance | Governance | Compliance | Recurring | High | Amber |
| NOR-006 | Digital Twin / Throughput | Technology | Technology | Capability Building | One-off | Medium | Green |

**Step 7 — Financials (EUR m).**

| Code | Benefit class | Plan Base | Plan High | Notable costs |
|---|---|---:|---:|---|
| NOR-001 | Avoidance | 16.8 | 21.4 | recurring run cost 0.6/yr |
| NOR-002 | Avoidance | 9.7 | 13.2 | **one-time 4.6** (lump 2026-Mar) + **recurring 0.9/yr @ 3% inflation** |
| NOR-003 | Savings | 12.4 | 16.0 | **one-time capex 8.1** phased 2026-Q2→Q4 |
| NOR-004 | (none) | 1.2 | 1.8 | one-time 0.5 |
| NOR-005 | (none — compliance) | **0.0** | **0.0** | recurring 0.7/yr |
| NOR-006 | (none) | 5.3 | 7.9 | one-time 1.1 |

**Step 9 — Validate & lock (the core of this scenario).**
1. Finance-validate NOR-001 and NOR-002 benefit lines.
2. Lock **NOR-001** and **NOR-002**: Governance → **Gate 2** → tick criteria → submit → approve → `/financials/bankable-plan` → confirm **Locked v1**. Record the lock date as `2026-02-15`.
3. For **NOR-003**, approve its Gate 2 **after** the lock date (`2026-03-10`) so it is excluded from the locked baseline.
4. After locking, open NOR-001 **Financials**, edit a benefit value, and confirm it surfaces as a **re-baseline delta** (use **Request rebaseline** at `/financials/bankable-plan`, approve at `/pmo/governance?status=pending`), not a silent overwrite.

**Validation**
1. `/financials/bankable-plan` — NOR-001/002 show **Locked + version**; the rebaselined one shows **v2** with history.
2. NOR-003 (approved post-lock) is **absent** from the bankable-locked run-rate.
3. `/financials` — one-time vs recurring costs aggregate separately; NOR-002 recurring cost compounds 3%/yr.
4. NOR-005 renders with cost, **zero benefit**, valid RAG — no divide-by-zero on `/financials/waterline`.
5. `/financials/benefits-register` — NOR-001/002 flagged **Finance Validated**.

---

## Scenario 4 — Helios Health Systems (USD, October FY) — the negative path

**Tests:** compliance type, at_risk realization, **rejected** benefit, the **high×high risk** heatmap cell, red RAG, pressure-score upper bound. Scoped to operational/financial/compliance transformation only — **no PHI / clinical data**.

**Step 1 — Create tenant.** Org `Helios Health Systems`, slug `helios`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Finance; Operations; Procurement; People; Governance | Finance; Operations; Procurement; People; Governance | Market: United States · Theme: Operational & regulatory turnaround · Tags: `compliance`, `cost`, `revenue`, `other` |

**Step 4 — Financial engine.** Reporting currency **USD**, fiscal year **October**.

**Step 6 — Create initiatives.** Impact **Recurring**.

| Code | Name | BU | Workstream | Type | Pri | RAG | Stage |
|---|---|---|---|---|---|---|---|
| HEL-001 | Revenue Cycle Remediation | Finance | Finance | Revenue Growth | High | **Red** | Build |
| HEL-002 | Regulatory Controls Uplift | Governance | Governance | Compliance | High | Red | Build |
| HEL-003 | Procurement & Supplies Savings | Procurement | Procurement | Cost Reduction | High | Amber | Executing |
| HEL-004 | Facilities Energy & Space | Operations | Operations | Cost Avoidance | Medium | Amber | Build |
| HEL-005 | Workforce Scheduling | People | People | Cost Reduction | Medium | Red | Identify |

**Step 7 — Financials (USD m).**

| Code | Benefit class | Plan Base | Plan High | Actual |
|---|---|---:|---:|---:|
| HEL-001 | Other | 18.2 | 24.0 | **1.1** |
| HEL-002 | (compliance) | 0.0 | 0.0 | 0.0 |
| HEL-003 | Savings | 9.6 | 12.3 | 2.4 |
| HEL-004 | Avoidance | 3.8 | 5.0 | 0.2 |
| HEL-005 | Savings | 5.4 | 7.1 | 0.0 |

**Step 8 — Risks (build the high×high cell).**
- HEL-001 *Billing data integrity* — technology, **High impact / High likelihood**, open.
- HEL-002 *Regulatory deadline slip* — financial, **High / High**, open.
- HEL-005 *Union / change resistance* — people, High / Medium, open.
- HEL-003 *Supplier pushback* — operational, Medium / Medium, open.
- Milestones: HEL-001 *Billing cutover* `2026-02-28` **Overdue**; HEL-002 *Controls gap closure* `2026-03-31` **Overdue**.
- KPIs: HEL-001 *Clean claim rate %* increase-good, 71 / 90 / **70** → critical; HEL-003 *Supplies cost / unit* decrease-good, 188 / 165 / 181 → at_risk.

**Step 9 — Validate (the rejected line).**
1. Submit HEL-001's benefit line to Finance, then **Reject** it with reason `Disputed recovery methodology; awaiting revised baseline evidence`.
2. Set **HEL-001 realization = at_risk**; enter Actual `1.1`.
3. Finance-validate HEL-003/004 only.

**Validation**
1. `/financials/benefits-register` — HEL-001 shows **Rejected** with the reject event; it is **excluded** from forecast/committed run-rate.
2. `/pmo/risks` heatmap — **two** entries in the top-right (High × High) cell; portfolio risk-exposure pressure near maximum.
3. HEL-001 pressure score is the **highest in the whole pack** — use as the upper-bound sanity check.
4. `/reports/control-tower` — Helios surfaces as the worst-performing tenant across the portfolio.

---

## Scenario 5 — Cascade Financial Services (AUD, July FY) — offshoring & realization ledger

**Tests:** labour-arbitrage recurring savings, the realization ledger ramp, multi-BU rollup reconciliation, AI service desk, a second bankable lock, finance_validated.

**Step 1 — Create tenant.** Org `Cascade Financial Services`, slug `cascade`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Retail Bank; Wealth; Business Bank; Group Functions | Shared Services; Technology; Operations; Commercial; Governance | Market: Australia · Theme: Operating-model & cost transformation · Tags: `offshoring`, `automation`, `revenue`, `compliance` |

**Step 4 — Financial engine.** Reporting currency **AUD**, fiscal year **July**.

**Step 6 — Create initiatives.** Impact **Recurring**, stage **Executing** (CAS-003 = Pilot, CAS-007 = Build). Tag each to a BU for rollup.

| Code | Name | BU | Workstream | Type | Pri | RAG |
|---|---|---|---|---|---|---|
| CAS-001 | Back-office Offshoring (F&A) | Group Functions | Shared Services | Cost Reduction | High | Green |
| CAS-002 | Offshoring Wave 2 (Ops & KYC) | Retail Bank | Shared Services | Cost Reduction | High | Amber |
| CAS-003 | AI Service Desk Automation | Group Functions | Technology | Cost Reduction | High | Green |
| CAS-004 | Contact Centre Consolidation | Retail Bank | Operations | Cost Reduction | Medium | Green |
| CAS-005 | Wealth Advisory Revenue | Wealth | Commercial | Revenue Growth | Medium | Green |
| CAS-006 | Procurement Savings Wave | Group Functions | Operations | Cost Reduction | Medium | Green |
| CAS-007 | AML/CTF Compliance Uplift | Group Functions | Governance | Compliance | High | Amber |

**Step 7 — Financials (AUD m).**

| Code | Benefit class | Plan Base | Plan High |
|---|---|---:|---:|
| CAS-001 | Savings | 22.4 | 27.8 |
| CAS-002 | Savings | 14.1 | 18.0 |
| CAS-003 | Savings | 6.8 | 9.5 |
| CAS-004 | Savings | 5.2 | 6.9 |
| CAS-005 | Revenue | 9.3 | 13.1 |
| CAS-006 | Savings | 7.1 | 8.8 |
| CAS-007 | (compliance) | 0.0 | 0.0 |

**Step 9 — Validate, lock, ledger.**
1. Finance-validate CAS-001 and CAS-006.
2. **Lock CAS-001** at Gate 2 → confirm Locked at `/financials/bankable-plan`.
3. Realization ledger — `/financials/benefit-tracking` → **Ledger Entries**. CAS-001 went live `2025-09-01`. Enter **monthly** rows ramping from `0.40` (Sep-25) to `1.90` (latest), e.g. 0.40, 0.70, 0.95, 1.20, 1.45, 1.70, 1.90 across successive months. Set CAS-001/005/006 realization = **partially_realized**.

**Validation**
1. `/financials/benefit-tracking` — CAS-001 cumulative realized ≈ Σ of the monthly rows; ramp curve visible against the locked plan.
2. `/financials/initiative-portfolio` — switch dimension **Workstream ↔ Business Unit**; both reconcile to the same portfolio total (Group carries CAS-001/003/006/007; Retail carries CAS-002/004).
3. FY columns label **Jul–Jun**; all values **AUD**.
4. `/financials/benefits-register` — CAS-001/006 **Finance Validated**.

---

## Scenario 6 — Verdant Agritech (BRL) — pre-lock, no-actuals fallback, dependencies

**Tests:** pre_lock mode, the planned-vs-actual **fallback with zero actuals**, no_data KPIs, deep dependency graph, non-major currency.

**Step 1 — Create tenant.** Org `Verdant Agritech`, slug `verdant`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Technology; Operations; Procurement; People; Governance | Technology; Operations; Procurement; People; Governance | Market: Brazil / LATAM · Theme: Data-led agribusiness modernization · Tags: `capability`, `revenue`, `cost`, `compliance` |

**Step 4 — Financial engine.** Reporting currency **BRL**, fiscal year **January**.

**Step 6 — Create initiatives.** Stage **Design** for all (early). Impact per table.

| Code | Name | BU | Workstream | Type | Impact | Pri | RAG |
|---|---|---|---|---|---|---|---|
| VER-001 | Data Platform Modernisation | Technology | Technology | Capability Building | One-off | High | Green |
| VER-002 | Yield & Agronomy Analytics | Technology | Technology | Revenue Growth | Recurring | High | Green |
| VER-003 | Logistics & Cold-Chain | Operations | Operations | Cost Reduction | Recurring | Medium | Amber |
| VER-004 | Export Compliance & Traceability | Governance | Governance | Compliance | Recurring | High | Green |
| VER-005 | Procurement (Inputs) | Procurement | Procurement | Cost Reduction | Recurring | Medium | Green |
| VER-006 | Workforce Digital Enablement | People | People | Capability Building | One-off | Low | Green |

**Step 7 — Financials (BRL m).** Enter **Plan Base / Plan High only — no Actual, no scenario inputs** (this is the fallback test).

| Code | Plan Base | Plan High |
|---|---:|---:|
| VER-001 | 8.9 | 12.4 |
| VER-002 | 19.6 | 28.2 |
| VER-003 | 11.3 | 15.0 |
| VER-004 | 0.0 | 0.0 |
| VER-005 | 9.4 | 12.1 |
| VER-006 | 1.7 | 2.6 |

**Step 8 — KPIs (define but leave empty) + dependencies.**
1. Add KPIs to VER-002/003 but **enter no readings** → they must show **no_data**.
2. Dependencies: VER-001 → VER-002, VER-003, VER-005 (hard predecessor); VER-004 → VER-002.
3. Realization: VER-002/005 = **forecasted**, the rest **not_started**.

**Step 9.** Do **not** validate, lock, or enter any actuals. Tenant stays in **pre_lock**.

**Validation**
1. `/financials` and `/reports/control-tower` — every view **falls back to planned** values; no blanks, no false zeros, no errors.
2. `/pmo/kpis` — no_data KPIs are **excluded** from the health-score denominator (don't count as misses).
3. Dependency view — VER-001 fan-out to {002,003,005} and the VER-004 → VER-002 gate render; downstream initiatives flagged blocked on predecessors.
4. `/financials/bankable-plan` — shows the **locked-not-available** empty state (nothing locked yet).
5. BRL formatting/separators correct throughout.

---

## Scenario 7 — Pinnacle Professional Services (USD) — regression baseline

**Tests:** known-good regression anchor mirroring the anonymised sample portfolio; new-logo revenue; multi-region rollup. Run this **first** as a smoke test.

**Step 1 — Create tenant.** Org `Pinnacle Professional Services`, slug `pinnacle`.

**Step 2 — Master data.** Use **regions** as business units.

| Business units (regions) | Workstreams | Market / Theme / Tags |
|---|---|---|
| Westmark; Eastgate; Northpoint; Southvale; Group | Automation; Commercial Growth; ERP & Systems; Offshoring; Compliance | Market: Multi-region · Theme: Corporate-services growth & efficiency · Tags: `revenue`, `cost`, `offshoring`, `compliance` |

**Step 4 — Financial engine.** Reporting currency **USD**, fiscal year **January**.

**Step 6 — Create initiatives.** Impact **Recurring** (PIN-001 = One-off), stage **Executing** (PIN-005/006 = Build, PIN-007 = Pilot).

| Code | Name | Region | Workstream | Type | Pri | RAG |
|---|---|---|---|---|---|---|
| PIN-001 | Accounting System Implementation | Westmark | ERP & Systems | Capability Building | High | Green |
| PIN-002 | CoSec Workflow Automation | Westmark | Automation | Cost Reduction | Medium | Green |
| PIN-003 | Offshoring to SSC (Finance) | Group | Offshoring | Cost Reduction | High | Green |
| PIN-004 | New Logos — Fund Admin | Eastgate | Commercial Growth | Revenue Growth | High | Green |
| PIN-005 | Advisory — Geographic Expansion | Northpoint | Commercial Growth | Revenue Growth | Medium | Amber |
| PIN-006 | Reconciliation Automation | Eastgate | Automation | Cost Reduction | Medium | Green |
| PIN-007 | Tax Compliance Automation | Southvale | Compliance | Compliance | Medium | Green |
| PIN-008 | Group Revenue Retention | Group | Commercial Growth | Revenue Growth | High | Green |

**Step 7 — Financials (USD m).**

| Code | Benefit class | Plan Base | Plan High |
|---|---|---:|---:|
| PIN-001 | (none) | 1.4 | 2.0 |
| PIN-002 | Savings | 3.6 | 4.5 |
| PIN-003 | Savings | 12.8 | 16.2 |
| PIN-004 | Revenue | 9.7 | 14.3 |
| PIN-005 | Revenue | 6.2 | 9.1 |
| PIN-006 | Savings | 2.9 | 3.7 |
| PIN-007 | (compliance) | 0.6 | 0.9 |
| PIN-008 | Revenue | 7.4 | 10.8 |

**Step 9.** Finance-validate all lines. Set PIN-002/003/004/008 realization = **partially_realized**; no locks needed for the baseline.

**Validation**
1. `/financials/initiative-portfolio` — record the Base and High portfolio totals **once** as the regression baseline; assert no drift across releases unless inputs change.
2. Region rollup = workstream rollup = portfolio total (three paths, one number).
3. Cross-check the equivalent initiatives against the imported `Initiative_Portfolio_Anonymised.xlsx` — behaviour should match.

---

## Scenario 8 — Stellar Media & Entertainment (USD) — AI agents & benefit state machine

**Tests:** AI-automation benefits, churn/retention KPIs, **Draft + Submitted** benefit states, and the meeting-notes / status-update / initiative-intake **agent + HITL** flows.

**Step 1 — Create tenant.** Org `Stellar Media & Entertainment`, slug `stellar`.

**Step 2 — Master data.**

| Business units | Workstreams | Market / Theme / Tags |
|---|---|---|
| Digital; Technology; Commercial; Operations | Digital; Technology; Commercial; Operations | Market: Pan-Asia · Theme: Streaming growth & AI automation · Tags: `revenue`, `automation`, `capability`, `cost` |

**Step 4 — Financial engine.** Reporting currency **USD**, fiscal year **January**.

**Step 6 — Create initiatives.** Stage **Executing** (STE-003 = Pilot, STE-006 = Design).

| Code | Name | BU | Workstream | Type | Impact | Pri | RAG |
|---|---|---|---|---|---|---|---|
| STE-001 | Churn & Retention Engine | Digital | Digital | Revenue Growth | Recurring | High | Amber |
| STE-002 | AI Content Tagging & Discovery | Technology | Technology | Capability Building | Recurring | High | Green |
| STE-003 | AI Customer Support Automation | Technology | Technology | Cost Reduction | Recurring | Medium | Amber |
| STE-004 | Ad Yield Optimisation | Commercial | Commercial | Revenue Growth | Recurring | High | Green |
| STE-005 | Content Cost Rationalisation | Operations | Operations | Cost Reduction | One-off | Medium | Amber |
| STE-006 | Data & Measurement Capability | Technology | Technology | Capability Building | One-off | Low | Green |

**Step 7 — Financials (USD m).**

| Code | Benefit class | Plan Base | Plan High | Actual |
|---|---|---:|---:|---:|
| STE-001 | Revenue | 13.9 | 19.7 | 4.2 |
| STE-002 | (capability) | 6.4 | 9.0 | 0.8 |
| STE-003 | Savings | 4.7 | 6.3 | 0.5 |
| STE-004 | Revenue | 8.1 | 11.6 | 3.0 |
| STE-005 | Savings | 5.5 | 7.2 | 0.6 |
| STE-006 | (capability) | 1.9 | 2.8 | 0.0 |

**Step 8.** KPIs: STE-001 *Monthly churn %* decrease-good, 5.8 / 3.5 / 4.9 → on_track; *ARPU (USD)* increase-good, 7.20 / 8.50 / 7.80 → on_track. Realization: STE-001/004 = partially_realized; STE-002/003/005 = committed/forecasted.

**Step 9 — Benefit state machine + actuals.**
1. Leave **STE-002** benefit line in **Draft**.
2. **Submit STE-003** to Finance (status **Submitted**, not validated).
3. Finance-validate the remaining lines.
4. Enter the Actual values from Step 7.

**Step 10 — Agent / HITL flows (the AI test).**
1. **Meeting-notes agent** — feed a transcript of a "Stellar steering committee" meeting; confirm it extracts action items + decisions, tenant-scoped, with PII/secret screening applied before the agent runs and a Langfuse trace emitted.
2. **Status-update agent** — generate a status update for STE-001; confirm it is a **HITL draft** and does **not** write to the DB without approval.
3. **Initiative-intake agent** — paste a free-text brief; confirm structured field extraction with a HITL checkpoint before persistence.

**Validation**
1. `/financials/benefits-register` — STE-002 **Draft** and STE-003 **Submitted** are visible but **excluded** from committed run-rate.
2. Agent outputs are tenant-scoped, traced, and gated behind HITL — no autonomous DB writes.
3. `/pmo/kpis` — decrease-good churn and increase-good ARPU both read correctly on the same initiative.

---

## Run order & cross-tenant check

Follow the scenarios in this order:

1. **Scenario 7 — Pinnacle** (smoke / regression baseline). If totals are wrong here, stop and fix before continuing.
2. **Scenarios 2, 3, 5** (financial engine: multi-scenario, bankable lock, realization ledger).
3. **Scenario 6** (resilience: fallback, no_data, dependencies).
4. **Scenario 4** (negative path: red, rejected, high-risk, pressure upper bound).
5. **Scenario 1** (pressure components, decrease-good KPIs).
6. **Scenario 8** (AI agents, HITL, benefit state machine).
7. **All eight loaded** — open `/reports/control-tower` and confirm cross-tenant aggregation is correct and there is **no cross-tenant data leakage** (multi-tenant isolation).

## Coverage confirmation

- `InitiativeType` — all five (revenue_growth, cost_reduction, cost_avoidance, compliance, capability_building).
- `RealizationStatus` — all six (not_started, forecasted, committed, partially_realized, realized, at_risk).
- Benefit class — all five (savings, avoidance, revenue, margin, other).
- Cost behaviour — recurring + one_time, plus inflation modifier.
- Benefit validation — draft, submitted, finance_validated, rejected.
- Financial mode — pre_lock, planned_vs_actual, multi_scenario, bankable_locked.
- RAG — green, amber, red. Risk heatmap — high×high populated.
- KPI health — on_track, at_risk, critical, no_data; decrease-good + increase-good.
- Fiscal years — Jan, Apr, Jul, Oct. Currencies — USD, GBP, EUR, AUD, SGD, BRL.
- Rollup dimensions — workstream, business unit, region.
- AI agents — meeting-notes, status-update, initiative-intake, all HITL-gated.
