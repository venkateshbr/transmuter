# Transmuter Runbook E2E — Second Assessment Pass (Findings Log)

**Method:** 100% browser/UI-driven via Chrome DevTools Protocol (headless), exactly as a customer would — navigate, type, click. Reads for validation taken from rendered DOM and the tenant's own authenticated API session. No DB seeding, no out-of-band API writes for setup.
**Environment:** Dev — https://transmuter-dev.ishirock.tech (Stripe sandbox).
**Reference:** `tests/TRANSMUTER_E2E_TEST_RUNBOOK.md` (scenarios) + `docs/user-guides/acme-demo-tenant-ui-setup-guide.md` (sequence/style).
**Started:** 2026-06-25
**Prior pass:** `platform-assessment.md` / `northwind-assessment-findings.md` (findings reportedly fixed; this pass re-checks them).

Run order per the runbook: **Scenario 7 (Pinnacle) first as the smoke/regression baseline.**

---

## Executive summary — all 8 scenarios run + cross-tenant check (completed 2026-06-25)

Eight fresh tenants stood up end-to-end through the real UI (public signup → Stripe sandbox checkout → provisioning), each exercising its scenario. **The financial/governance/analytics core reconciles exactly everywhere** — portfolio totals, 3-way rollups (workstream = business unit = portfolio), EBITDA-vs-total value bridge, bankable lock + governed rebaseline (v2), realization-ledger ramp, planned-vs-actual variance, benefit state machine, pressure scoring, and the High×High risk heatmap all compute correctly.

| Scenario | Tenant | Verdict |
|---|---|---|
| 7 — regression baseline | Pinnacle | ✅ PASS (Base $44.6M / High $61.5M; 3-way rollup reconciles) |
| 2 — multi-scenario & realized | Aurelia | ⚠️ core PASS; blocked on currency/FY (F14) + realized-ledger-needs-lock (F15) |
| 3 — bankable lock & costs | Nordvik | ✅ PASS (lock, rebaseline v2, cost separation); F16 (no inflation) |
| 5 — offshoring & realization ledger | Cascade | ✅ PASS (ramp $8.3M, rollup $64.9M reconciles) |
| 6 — pre-lock fallback, no_data, deps | Verdant | ✅ PASS |
| 4 — negative path | Helios | ✅ core PASS (rejected excluded, High×High=2, pressure); F17 (no reject reason), F18 (RAG) |
| 1 — pressure & planned-vs-actual | Meridian | ✅ PASS planned-vs-actual; ⚠️ pressure partial (F19) |
| 8 — AI agents & state machine | Stellar | ✅ PASS (state machine; status-update + intake HITL, no DB writes) |

**Cross-tenant isolation: ✅ PASS** — each tenant session sees only its own initiatives; cross-tenant access to another tenant's initiative (by ID) returns **404** (no leakage).

### Prior findings re-checked — FIXED this pass
- **F3** (placeholder trend deltas) ✅ · **F5** (subtitle miscount) ✅ · **F6** (no benefit/cost-line delete — Delete now present) ✅ · **F11** (validation blocked post-lock — now works post-lock) ✅ · **F10** (AI KPIs had no values — now seed readings) ✅ improved.

### New findings this pass (severity-ranked)
- 🔴 **F14 [HIGH]** — Reporting currency / fiscal-year change returns 200 but **is not persisted** (silent no-op); USD/January is the only reachable state. Blocks the entire currency matrix (GBP/EUR/AUD/SGD/BRL) and non-Jan fiscal years for Scenarios 1–6.
- 🔴 **F16 [Med]** — No inflation-% modifier on recurring costs.
- 🟠 **F15 [Med]** — Realized ledger requires a lock, but Scenario 2 specifies "no locks" (runbook/platform tension; works fine where a lock exists — Scenario 5).
- 🟠 **F18 [Med]** — No effective UI path to set an initiative's headline RAG; the Status-Heartbeat RAG persists as a status-update but doesn't propagate to `rag_status` (stays green on dashboards).
- 🟠 **F17 [Low-Med]** — Benefit "Reject" captures no reason.
- 🟠 **F19 [Low-Med]** — Past-due milestones don't drive milestone pressure; no UI to mark a milestone overdue.
- 🟡 **F13 [Med]** — Setting Plan Base + Plan High on one benefit line is non-obvious; the natural path creates a duplicate line (totals still reconcile).
- 🟡 **F7-R [Med]** — Silent line/item drop under rapid sequential adds (re-confirmed prior F7); add-forms still give no submit feedback.

**Bottom line:** the analytics/governance engine is solid and the prior pass's biggest gaps (F6, F11) are fixed. The headline new issue is **F14** — currency/fiscal can't be changed from USD/January via the UI, which blocks a whole dimension of the test matrix. The rest are data-entry-UX and workflow-completeness gaps, not engine-correctness problems.

> Detailed per-scenario write-ups follow (most recent first). Credentials for all 8 tenants: `tests/runbook-e2e-credentials.md`.

---

## Scenario 8 — Stellar Media & Entertainment (USD, Jan FY) — AI agents & benefit state machine

**Tenant:** `stellar` · admin `stellar.to@transmuter-e2e.dev` · tenant_id `db01be51-ab48-429f-babd-79e1ebcaa00e`
**Tests:** AI-automation benefits, **Draft + Submitted** benefit states, and the meeting-notes / status-update / initiative-intake **agent + HITL** flows. (No F14 impact — USD/Jan is the default.)

### Build
Signup → 4 BUs + 4 workstreams + tags → added Other metric (capability) → gates + criteria → 6 initiatives → Base/High/Actual benefits → benefit state machine (STE-002 Draft, STE-003 Submitted, rest validated).

### Scenario 8 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials/benefits-register` — STE-002 **Draft** + STE-003 **Submitted** visible but excluded from committed run-rate | ✅ **PASS (exact)** — committed (finance-validated) run-rate **$29.4M** (STE-001 13.9 + STE-004 8.1 + STE-005 5.5 + STE-006 1.9) **excludes** STE-002 Draft ($6.4M) and STE-003 Submitted ($4.7M); register shows all three states (Draft/Submitted/Finance-Validated). |
| 2 | Agent outputs tenant-scoped, HITL-gated, **no autonomous DB writes** | ✅ **PASS (2 of 3 agents driven)** — **status-update agent**: "Generate Draft" produced a contextual, tenant-scoped summary ("0 of 3 milestones complete, 1 high + 3 medium risks open…") from the initiative's own data and **wrote nothing to the DB** (status-updates stayed 0 until an explicit Submit). **initiative-intake agent**: the "Create with Transmuter" wizard is HITL (AI suggestions reviewed/accepted before persist) — exercised 40+ times across all scenarios (ran `DETERMINISTIC_FALLBACK`). **meeting-notes agent**: Meetings module present (series/steering committees); the transcript→action-item extraction requires series→instance→transcript and was not fully driven this pass. |
| 3 | `/pmo/kpis` — decrease-good churn + increase-good ARPU on same initiative | ◻️ **Not isolated** — `/pmo/kpis` loads; KPI good-direction is inferred from target-vs-baseline (no explicit field), so the specific churn↓/ARPU↑ pair wasn't hand-seeded this pass. Mechanism present. |

> **Langfuse tracing / PII-secret screening** are backend behaviours (telemetry + pre-agent guardrails) not observable from the browser UI — they'd need Langfuse/log access to confirm. HITL gating and tenant-scoping (the UI-observable guarantees) are confirmed.

### Scenario 8 verdict
**PASS on the benefit state machine and the HITL agent guarantees.** Draft/Submitted/Validated states behave correctly and the committed run-rate excludes non-validated lines exactly; the **AI status-update agent is HITL with no autonomous DB write**, and the **intake wizard's HITL** is proven across the whole assessment. The meeting-notes agent's deep flow and the Langfuse trace weren't driven from the UI this pass.

---

## Scenario 1 — Meridian Logistics Group (SGD, Jan FY → USD/Jan via F14) — pressure scoring & planned-vs-actual

**Tenant:** `meridian` · admin `meridian.to@transmuter-e2e.dev` · tenant_id `13aa1b04-e939-43ee-8323-46c0f0ed35db`
**Tests:** planned_vs_actual mode, decrease-good operational KPIs, pressure score from overdue milestone + open risk + KPI miss.

### Build
Signup → 4 BUs + 3 workstreams + tags → added Cost Avoidance metric → gates + criteria → 6 initiatives (MER-001…006) → Base/High + **Actual-to-date** benefit lines → past-due milestones on MER-001/002.

### Scenario 1 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials` — MER-001/003 show planned-vs-actual **variance** (actuals entered) | ✅ **PASS** — portfolio **plan_base $44.5M vs actual $11.4M** (both exact: plan 14.2+9.4+6.7+4.1+7.8+2.3; actual 5.8+1.2+3.1+0.4+0.9+0); `/financials` renders the Actual scenario → planned-vs-actual mode active. |
| 2 | `/initiatives/:id` (MER-002) pressure breakdown — schedule, milestone, risk, KPI all non-zero | ⚠️ **PARTIAL** — breakdown renders (**VALUE PRESSURE 0.9**): **Schedule 2/10** ✅, **Risks 2.5/10** ✅ non-zero; but **Milestones 0/10** and **Financials 0/10**. See F19. |
| 3 | `/pmo/kpis` — MER-001 decrease-good on_track; MER-004 critical | ◻️ **Not isolated** — KPIs have **no explicit direction field**; good-direction is inferred from target-vs-baseline (target<baseline ⇒ decrease-good). The AI KPIs use generic values, so the specific decrease-good readings (cost-per-shipment 42.10→36.00→38.40) weren't hand-seeded this pass. The inference mechanism is present; the specific assertion wasn't re-keyed. |
| 4 | `/financials/initiative-portfolio` — cost-reduction rollup totals | ✅ **PASS** — $44.5M base rolls up across Operations/Technology/Procurement (all cost-reduction/avoidance), currency USD (F14). |

### 🟠 F19 — Past-due milestones don't drive milestone pressure (and no UI to mark a milestone overdue). [Severity: Low-Med]
The pressure model has a **Milestones** component, but it read **0/10** for MER-002 despite two milestones with **planned-end dates in the past** (2026-04-30, before "today" 2026-06-25). All milestones are created as `not_started`, and the **New Milestone** modal offers no way to set status to *in-progress/overdue* — so a genuinely overdue milestone never registers as overdue and contributes nothing to pressure. The schedule/risk components do work (Schedule 2/10, Risks 2.5/10), so pressure scoring is real; but the milestone-health driver is effectively unreachable via the UI for not-yet-started work. _(Derive "overdue" from planned-end < today for non-complete milestones, or expose a milestone status control.)_

### Scenario 1 verdict
**PASS on planned-vs-actual and rollup; PARTIAL on pressure.** The planned-vs-actual engine (plan $44.5M vs actual $11.4M) and the cost-reduction rollup are exact. Pressure scoring is real and multi-component (Schedule + Risks non-zero, VALUE PRESSURE 0.9), but the **milestone-health component can't be driven** because overdue isn't derived from past dates and there's no status control (F19). Decrease-good KPI direction is inferred from target-vs-baseline (mechanism present; specific readings not hand-seeded). Built USD/Jan (F14).

---

## Scenario 4 — Helios Health Systems (USD, Oct FY → USD/Jan via F14) — the negative path

**Tenant:** `helios` · admin `helios.to@transmuter-e2e.dev` · tenant_id `da1682a8-cea7-4c4a-b78c-777ed359bea5`
**Tests:** compliance type, **rejected** benefit, the **High×High** risk heatmap cell, red RAG, pressure-score upper bound. (Operational/financial/compliance only — no PHI/clinical data, per the runbook scope note.)

### Build
Signup → 5 BUs + 5 workstreams + tags → **added Cost Avoidance + Other benefit metrics** (so all 5 benefit classes exist) → gates + criteria → 5 initiatives → Base/High/Actual benefit lines (HEL-002 zero; HEL-005 actual 0) → 4 risks → reject HEL-001 → finance-validate HEL-003/004 → status reports.

### Scenario 4 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials/benefits-register` — HEL-001 **Rejected**, excluded from committed run-rate | ✅ **PASS** — HEL-001 base line **rejected**; portfolio **committed (finance-validated) run-rate = $13.4M** (HEL-003 $9.6M + HEL-004 $3.8M only) — correctly **excludes** the rejected HEL-001 ($18.2M) and the draft HEL-005. Register shows HEL-001 Rejected. |
| 2 | `/pmo/risks` heatmap — two entries in the **High × High** cell | ✅ **PASS (exact)** — exactly **2** risks at High impact × High likelihood (HEL-001 billing integrity, HEL-002 regulatory slip); the 20 AI-suggested risks added none at High×High. |
| 3 | HEL-001 pressure score highest in the pack | ✅ **PASS (in substance)** — troubled initiatives HEL-001/002/005 = **1.2** vs healthy HEL-003/004 = 0.8/0.9; HEL-001 sits at the top tier (tied with 002/005, since I added the same High risk to each and did not hand-seed HEL-001's overdue-milestone/critical-KPI). Pressure scoring clearly separates the negative-path initiatives. |
| 4 | `/reports/control-tower` — Helios is the worst-performing tenant across the portfolio | ⚠️ **Not testable in-tenant** — the Control Tower is tenant-scoped; a cross-tenant "worst tenant" ranking would need a platform-admin view across tenants, not available from a single tenant's session. |

### 🟠 F17 — Benefit "Reject" captures no reason. [Severity: Low-Med]
The runbook calls for rejecting HEL-001 "with reason `Disputed recovery methodology; awaiting revised baseline evidence`." The benefit-line **Reject** button rejects **immediately with no reason prompt** (no modal, no text field); the resulting line has `validation_status: rejected` but `rejection_reason: null`. Finance can't record *why* a benefit was rejected. _(Add a reason prompt on reject.)_

### 🟠 F18 — No effective UI path to set an initiative's headline RAG; status-report RAG doesn't propagate. [Severity: Medium]
RAG is **not** captured in the create wizard, and the **Edit Initiative** form has no RAG control (only type/impact/priority/tag). RAG *can* be chosen in the **Status Heartbeat** report (GREEN/AMBER/RED) and that selection **persists as a status-update** (`/status-updates` shows `rag_status: red`), but it **does not update the initiative's own `rag_status`** — which stays **green** on the pipeline and dashboards. Net: the negative-path "Red RAG" cannot be surfaced on the portfolio views by any UI path found. HEL-001 (high×high risk + rejected benefit + pressure 1.2) still shows **green** everywhere. _(Either let Edit set RAG, derive it from pressure/risk/KPI signals, or propagate the latest status-report RAG to the initiative.)_

### Scenario 4 verdict
**PASS on the core negative-path mechanics** — the **rejected benefit** is correctly excluded from the committed run-rate, the **High×High risk heatmap** populates with exactly 2, and **pressure scoring** separates the troubled initiatives. Two real gaps surfaced: **F17** (reject has no reason) and **F18** (RAG can't be driven Red on portfolio views). Cross-tenant "worst tenant" isn't testable from one tenant.

---

## Scenario 6 — Verdant Agritech (BRL, Jan FY → USD/Jan via F14) — pre-lock fallback, no_data, dependencies

**Tenant:** `verdant` · admin `verdant.to@transmuter-e2e.dev` · tenant_id `6bf98baa-9b57-4f76-b77e-6918ee637e2b`
**Tests:** pre_lock mode, planned-vs-actual fallback with zero actuals, no_data KPIs, deep dependency graph.

### Build
Signup → 5 BUs + 5 workstreams + market/theme/tags → gates + criteria → 6 initiatives (VER-001…006; VER-004 compliance = zero benefit) → Plan Base + High benefit lines **only (no actuals, no locks)** → dependency graph → 2 reading-less KPIs.

### Scenario 6 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials` and `/reports/control-tower` fall back to planned; no blanks/false zeros/errors | ✅ **PASS** — portfolio benefits **plan $31.3M** (EBITDA savings; revenue excluded), **actual $0**; Control Tower renders with **no NaN/Infinity/errors**, value bridge present. |
| 2 | `/pmo/kpis` — no_data KPIs excluded from the health denominator (not misses) | ✅ **PASS** — created reading-less KPIs on VER-002/003 → **health_status = `no_data`** (0 entries), a status **distinct** from at_risk/critical, so they don't count as misses. Portfolio tally: 30 readable (at_risk) + 2 `no_data`. |
| 3 | Dependency view — VER-001 fan-out to {002,003,005} + VER-004 → VER-002 | ✅ **PASS** — 4 dependencies created via the Dependencies tab (VER-001 *blocks* 002/003/005; VER-004 *requires-decision* 002). |
| 4 | `/financials/bankable-plan` — locked-not-available empty state (nothing locked) | ✅ **PASS** — no locked plans; bankable view shows the empty state, no `LOCKED Vn`. |
| 5 | BRL formatting | N/A — USD due to F14. |

### Re-check — F10 (KPIs created with no value) appears ADDRESSED
The prior pass noted AI-suggested KPIs were created with a target but **no latest value** (portfolio efficiency stuck at 0.0%). This pass: the AI wizard's KPIs now arrive **with a reading entry** (`value_actual` populated), so they compute a real health status rather than being valueless. _(Minor: the deterministic-fallback seed values are generic 125000/190000 placeholders, not initiative-specific — cosmetic.)_

### Scenario 6 verdict
**PASS.** The pre-lock planned fallback (no actuals → views read planned, no false zeros/errors), the **no_data** KPI status (reading-less KPIs correctly excluded from misses), the **dependency graph** (fan-out + requires-decision), and the **bankable-plan empty state** all behave correctly. Built USD/Jan (F14).

---

## Scenario 5 — Cascade Financial Services (AUD, Jul FY → USD/Jan via F14) — offshoring & realization ledger

**Tenant:** `cascade` · admin `cascade.to@transmuter-e2e.dev` · tenant_id `cf850726-bdd7-490b-b3fe-a848ac20a5da`
**Tests:** labour-arbitrage recurring savings, realization-ledger ramp, multi-BU rollup reconciliation, a second bankable lock, finance_validated.

### Build
Signup → 4 BUs + 5 workstreams + market/theme/tags → gates 1–3 + criteria (lock gate set to 2) → 7 initiatives (CAS-001…007; CAS-007 compliance = zero benefit) → benefit lines → **locked CAS-001** (Gate 2) → finance-validated CAS-001/006 → realization-ledger ramp.

### Scenario 5 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials/benefit-tracking` — CAS-001 cumulative realized ≈ Σ monthly rows; ramp vs locked plan | ✅ **PASS** — 7 monthly rows (0.40→1.90) → **realized $8,300,000** (= exact Σ); **locked baseline $13,066,667** (CAS-001 $22.4M/yr prorated to the 7 ramp months), **variance −$4.77M** — ramp-up correctly reads below the steady-state plan line. |
| 2 | `/financials/initiative-portfolio` — workstream rollup = BU rollup = portfolio total | ✅ **PASS (exact)** — Base **$64.9M** = by-BU sum = by-workstream sum. **Group Functions $36.3M** (CAS-001/003/006/007), **Retail Bank $19.3M** (CAS-002/004), Wealth $9.3M; Shared Services $36.5M, Technology $6.8M, Operations $12.3M, Commercial $9.3M, Governance $0. EBITDA (savings only) $55.6M; High total $84.1M. |
| 3 | FY columns Jul–Jun; all values AUD | 🔴 **BLOCKED by F14** — fiscal Jan, currency USD. |
| 4 | `/financials/benefits-register` — CAS-001/006 Finance Validated | ✅ **PASS** — both finance-validated. |

**Second bankable lock:** ✅ CAS-001 LOCKED v1. **F15 corroborated:** the realization ledger **works once a lock exists** (here it did; the 400 "lock required" seen in Scenario 2 was because Aurelia had no lock). The ledger UI's monthly granularity, per-period rows, and prorated-baseline rule all compute correctly.

### Scenario 5 verdict
**PASS.** Realization-ledger ramp, the locked-baseline proration, three-path rollup reconciliation (BU = workstream = portfolio = $64.9M), the second bankable lock, and finance-validation all work and reconcile exactly. Only the **AUD/Jul** dimension is blocked (F14).

---

## Scenario 3 — Nordvik Manufacturing (EUR, Jan FY → USD/Jan via F14) — bankable lock & cost behaviours

**Tenant:** `nordvik` · admin `nordvik.to@transmuter-e2e.dev` · tenant_id `935b5ee1-ee8b-4d4a-aaf5-63f609f8beba`
**Tests:** bankable_locked mode, `approved_at ≤ lock_date` cut-off, cost_avoidance + capability_building, one-time + recurring cost (with inflation), finance_validated benefits, zero-benefit compliance, governed rebaseline.

### Build
Signup → 4 BUs + 4 workstreams + market/theme/tags → **added a Cost Avoidance metric** (benefit class Avoidance — ADD METRIC worked, persisted) → set **bankable-plan lock gate = 2** (governance Save Settings persisted correctly) → 5 gates + criteria → 6 initiatives (NOR-001…006) → benefit lines (NOR-005 intentionally zero) → costs.

### Scenario 3 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials/bankable-plan` — NOR-001/002 Locked + version; rebaselined one shows v2 with history | ✅ **PASS** — NOR-001 **LOCKED v1 $16.8M** then governed-rebaselined to **v2** (2 versions in history); NOR-002 **LOCKED v1 $9.7M**. Gate 1→Gate 2 approval auto-locked the plan. |
| 2 | NOR-003 (post-lock) absent from the bankable-locked run-rate | ✅ **PASS (by lock state)** — only NOR-001/002 are locked; NOR-003–006 are unlocked and excluded from the locked baseline. ⚠️ The *date-precise* `approved_at ≤ lock_date` cut-off (Feb-15 vs Mar-10) **could not be tested via UI** — gate approvals are timestamped "now" and there is no backdating control. The lock-membership exclusion itself is demonstrated. |
| 3 | One-time vs recurring costs aggregate separately; NOR-002 recurring compounds 3%/yr | ✅ **PASS for separation** — by cost-category rollup: NOR-003 one-off $8.1M, NOR-006 one-off $1.1M, NOR-005 recurring $0.7M; portfolio shows 2026 one-off $9.2M vs 2027 recurring $0.7M. 🔴 **inflation NOT supported** — see F16. |
| 4 | NOR-005 renders with cost, zero benefit, no divide-by-zero on `/financials/waterline` | ✅ **PASS** — NOR-005 (0 benefit, $0.7M cost) renders; waterline shows clean `$0` target/actual/variance, **no NaN/Infinity/divide-by-zero**. |
| 5 | `/financials/benefits-register` — NOR-001/002 Finance Validated | ✅ **PASS** — both finance-validated (see F11 re-check below). |

### 🟢 F11 — Benefit validation post-lock is now FIXED (prior High finding resolved)
The prior Northwind pass found benefit Submit/Validate **disabled with no reason after the Gate-2 lock** (validation had to precede the first lock, with no recovery). This pass: after locking NOR-001/002, the benefit-line **Submit/Validate buttons are ENABLED**, and both initiatives' lines were driven **draft → submitted → finance_validated entirely post-lock**. F11 is resolved.

### 🔴 F16 — No inflation-% modifier on recurring costs. [Severity: Medium]
The runbook (and the coverage matrix) call for a recurring-cost **inflation modifier** (NOR-002 recurring $0.9M/yr **@ 3% inflation**). There is **no inflation field** anywhere in the cost UI — cost-category fields are only label / group / rollup / display order, and the cost-line form is category / lane / phasing / amount / start-month / end-month. Recurring costs are entered flat; a 3%/yr compounding modifier cannot be expressed. _(Either add an inflation field to recurring cost lines, or drop the inflation assertion from the runbook coverage.)_

### Scenario 3 verdict
**PASS on the core — the bankable-lock engine is solid.** Gate-driven lock (auto-lock at the configured gate), version history, **governed rebaseline to v2**, locked-baseline exclusion of unlocked initiatives, one-time/recurring cost separation, the new **Avoidance** benefit class, and zero-benefit compliance all work and reconcile. **F11 is confirmed FIXED.** Two gaps: **F16 (no inflation modifier)** and the **date-precise lock cut-off isn't UI-testable** (no backdating). Built in USD/Jan due to **F14**.

**Tenant:** `aurelia` · admin `aurelia.to@transmuter-e2e.dev` · tenant_id `4d1cec5d-d8fe-4fb3-9b6c-0e6bcbd4e663`
**Tests:** multi_scenario base/high, non-January fiscal year, margin vs revenue benefit classes, an actual that beats plan, a fully realized benefit.

### 🔴 F14 — Reporting currency / fiscal-year change returns 200 but is NOT persisted (silent no-op). [Severity: HIGH — blocks the whole currency/FY test dimension]

`/admin` → **Financial Configuration** → set Reporting currency `GBP`, Fiscal year start `April` → **Save Settings**. Reproduced airtight (network-captured):

```
BEFORE  /financial-engine-configuration .settings = {fiscal_year_start_month:1, reporting_currency:"USD"}
SAVE    PUT /api/admin/financial-engine/reporting-settings  body {fiscal_year_start_month:4, reporting_currency:"GBP"}  ->  200 OK, response echoes {4,"GBP"}
AFTER   /financial-engine-configuration .settings = {fiscal_year_start_month:1, reporting_currency:"USD"}   ← UNCHANGED
UI      reverts the field to USD / January after save; NO error/toast shown.
```

The PUT succeeds (200) and echoes the new values, but the canonical config is unchanged — the change is silently dropped with no error. **Signup has no currency field, so USD/January is the only reachable state via the UI.** This blocks the runbook's currency matrix (GBP/EUR/AUD/SGD/BRL) and fiscal-year matrix (Apr/Jul/Oct) — i.e. Scenarios 1, 2, 3, 4, 5, 6 cannot be configured to their specified currency/FY through the UI. Aurelia therefore had to be built in **USD / January**, which directly blocks S2 **Validation 4** (FY columns labelled Apr–Mar) and means money displays as `$` not `£`. _(Recommend: persist the setting, or if currency is intentionally immutable post-provisioning, surface that and disable the field / collect currency at signup.)_

**Note (positive):** metric benefit classes are correct by default — `Revenue Uplift` → benefit class **Revenue**, `Gross Margin Uplift` → **Margin** (verified in Financial Configuration), so the margin-vs-revenue band test (S2 Validation 3) is still exercisable.

### Build progress (Scenario 2)

| Std Step | Action | Result |
|---|---|---|
| 1 | Signup → Stripe sandbox → provision → login | ✅ tenant `aurelia` provisioned; empty dashboard ("0 strategic initiatives") |
| 2 | Master data: 4 BUs, 3 workstreams, market (United Kingdom), theme, +3 tags (revenue/margin/digital) | ✅ all persisted |
| 4 | Reporting currency GBP / fiscal April | 🔴 **BLOCKED by F14** — stays USD/January (built remainder in USD/Jan) |
| 5 | Governance: 5 gates + criteria | ✅ first-run 7/7 complete |
| 6 | 5 initiatives via guided wizard | ✅ TRN-001…005 ↔ AUR-001…005 |
| 7 | Benefit lines — Plan Base + Plan High + **Actual** for all 5 | ✅ exact (3 lines each: base/high/actual) |

### Scenario 2 — VALIDATION RESULTS

| # | Check | Result |
|---|---|---|
| 1 | `/financials` toggle Plan Base ↔ Plan High — totals switch cleanly | ✅ **PASS** — EBITDA Base **$15.8M** ↔ High **$20.3M** ↔ Actual **$14.8M** (margin+savings; revenue excluded). Portfolio raw totals Base $34.4M / High $47.2M / Actual $21.5M — all exact. |
| 2 | AUR-001 Actual shows favourable variance (12.1 > 11.6) without breaking rollup | ✅ **PASS** — AUR-001 actual margin $12.1M > base $11.6M; Actual EBITDA $14.8M computed cleanly. |
| 3 | `/financials/waterline` — Margin and Revenue as distinct bands | ✅ **PASS (in substance)** — benefit-class split distinct (margin $11.6M / revenue $18.6M / savings $4.2M); Waterline net-run-rate basis includes margin (AUR-001 previews $11.6M) and **excludes** revenue (AUR-003 previews $0) — the margin-vs-revenue treatment is correct. |
| 4 | FY columns label Apr–Mar; April cut | 🔴 **BLOCKED by F14** — fiscal stuck at January, money shows `$` not `£`. |
| 5 | `/financials/benefits-register` and initiative Financials — AUR-001 Actual and finance validation | 🛠️ **RUNBOOK RECTIFIED** — unlocked realized-ledger assertion moved out of Scenario 2; Scenario 5 remains the locked-baseline ledger proof. |

### 🟠 F15 — Realized ledger requires a locked bankable plan, but Scenario 2 specifies "no locks" (runbook/platform tension). [Severity: Medium — runbook design issue]

Adding a realized ledger row at `/financials/benefit-tracking` → Ledger Entries (AUR-001, Yearly 2026, actual $12.1M) returns **HTTP 400: `"A locked bankable plan is required before ledger rows can be created."`** Scenario 2 Step 9 says *"No locks (this scenario demonstrates live multi-scenario, not bankable lock)"* yet Validation 5 asks for AUR-001 in the **realized ledger** — which the platform won't allow without a lock. The platform behaviour is defensible (you can't track realization against an unlocked, moving baseline — the page is literally titled "Locked Baseline Realization"). **Recommendation:** fix the runbook — either lock AUR-001 in S2, or move the realized-ledger assertion to a lock-based scenario (5/Cascade, 3/Nordvik). _(The realized-ledger capability itself was proven in the prior Northwind pass and is re-tested under Scenario 5.)_ The ledger UI, initiative picker, granularity, period, and amount fields all work; only the lock precondition blocks it here.

**Rectification:** Scenario 2 now validates AUR-001 Actual `12.1` and finance validation in the benefits register / initiative Financials, while Scenario 5 remains the locked-baseline realization ledger scenario.

### Scenario 2 verdict
**PASS on its core intent** (multi-scenario base/high engine, an actual that beats plan, and distinct margin/revenue/savings benefit classes — all exact). **Two checks could not be completed:** Validation 4 is **blocked by a real bug (F14, currency/FY not persisted)**, and Validation 5 is blocked by a **runbook inconsistency (F15, realized ledger needs a lock)**. F14 is the headline — it blocks the currency/fiscal dimension for every non-USD/non-Jan scenario.

**Deviations (documented):** built in USD/January (F14); initiatives at default *Identified* stage (no gate progression); runbook-specific KPIs/milestones/risks left at the wizard's AI-suggested defaults (S2's validations are financial); bulk finance-validation not completed (same per-line ambiguity as S7).

---

## Scenario 7 — Pinnacle Professional Services (USD, Jan FY) — regression baseline

**Tenant:** `pinnacle` · admin `pinnacle.to@transmuter-e2e.dev` · tenant_id `f9641073-e754-4dbd-9038-47c61c20bbb6`
**Tests:** known-good regression anchor; new-logo revenue; multi-region rollup (region = business unit).

### Progress log

| Std Step | Action | Screen | Result |
|---|---|---|---|
| 1 | Signup form → Stripe sandbox checkout → provisioning | `/get-started` → `checkout.stripe.com` → `/subscription/success` | ✅ Tenant provisioned ("Account setup complete"); test card 4242 accepted; signed in as `transformation_office` admin |
| 1 | Empty dashboard confirmed | `/dashboard` | ✅ 0 initiatives, health 0%, 0 pending gates |
| 2 | Master data: 5 workstreams, 5 BUs (regions), market, theme, +3 tags | `/admin` → Strategic Parameters | ✅ all persisted (after retry — see F7-R) |
| 4 | Financial config confirmed (USD / January default; 10 metrics; scenarios) | `/admin` → Financial Configuration | ✅ defaults match Scenario 7; no tenant annual baseline required |
| 5 | Governance: 5 stage gates (Identify→Realize) + gate criteria | `/admin` → Governance Engine | ✅ all 5 gates + 10 criteria; first-run setup 7/7 complete |
| 6 | 8 initiatives via guided "Create with Transmuter" wizard | `/initiatives/new` | ✅ TRN-001…008 ↔ PIN-001…008 (codes auto-assigned TRN-###; PIN code carried in name). AI step ran `DETERMINISTIC_FALLBACK` |
| 7 | Benefit lines (Plan Base + Plan High) for all 8 | initiative → Financials → Edit Details | ✅ all 8 base+high entered exactly |
| 9 | Finance-validate benefit lines | initiative → Financials | ⏳ (validation workflow proven on single line: draft→submitted→finance_validated) |

### Scenario 7 — VALIDATION RESULTS (regression baseline) ✅

| Check | Expected | Platform | Result |
|---|---|---|---|
| Portfolio benefit total — Plan Base (raw sum, all classes) | $44.60M | $44,600,000 | ✅ exact |
| Portfolio benefit total — Plan High | $61.50M | $61,500,000 | ✅ exact |
| EBITDA-effective benefits (savings only; revenue excluded) — Base | $21.30M | $21,300,000 | ✅ exact (revenue $23.3M correctly excluded from EBITDA) |
| EBITDA-effective benefits — Plan High | $27.30M | $27,300,000 | ✅ exact; Plan Base↔High toggle switches cleanly in `/financials/initiative-portfolio` |
| **3-way rollup reconciliation** | workstream = business unit = portfolio | $44.6M = $44.6M = $44.6M | ✅ no double-count, no drop |

**Regression anchor recorded** (assert no drift across releases unless inputs change): Plan Base total **$44.60M** ($21.3M EBITDA + $23.3M revenue); Plan High total **$61.50M** ($27.3M EBITDA + $34.2M revenue).

Per-initiative (Plan Base / Plan High, USD): PIN-001 1.4/2.0 · PIN-002 3.6/4.5 · PIN-003 12.8/16.2 · PIN-004 9.7/14.3 · PIN-005 6.2/9.1 · PIN-006 2.9/3.7 · PIN-007 0.6/0.9 · PIN-008 7.4/10.8. Workstream rollup: ERP&Systems 1.4 · Automation 6.5 · Offshoring 12.8 · Commercial Growth 23.3 · Compliance 0.6. BU rollup: Westmark 5.0 · Group 20.2 · Eastgate 12.6 · Northpoint 6.2 · Southvale 0.6.

> Validation 3 (cross-check vs `Initiative_Portfolio_Anonymised.xlsx`): the value-bridge behaviour — EBITDA = savings + margin, revenue excluded — matches the documented model and the prior Northwind pass. Not re-keyed line-by-line against the xlsx in this run.

### Positive observations (Scenario 7, so far)
- **P-S7-1 — Setup gating enforced.** `/initiatives/new` refuses creation while Stage gates / Gate criteria are incomplete ("Tenant setup required"), with a live checklist. Good guardrail against half-configured tenants.
- **P-S7-2 — Onboarding pipeline clean.** Public signup → Stripe sandbox checkout → provisioning → first login worked end-to-end with no orphaned-subscription/pending issues at this stage. (Re-checks prior F1/F2 path — no failure observed for a fresh unique email; full F1 re-test would need a duplicate-email attempt.)
- **P-S7-3 — Bulk Excel intake available.** `/initiatives/new` offers "Upload Excel Template" (download blank → fill → upload) alongside the guided "Create with Transmuter" wizard.

### Re-check of prior findings (at empty-state)
- **F3 (placeholder trend deltas on empty dashboard)** — appears **FIXED**: fresh tenant `TOTAL INITIATIVES 0 / Current portfolio` shows no "↑ 2 from last week" chip.
- **F5 (subtitle "N strategic workstreams" mislabels initiatives)** — appears **FIXED**: subtitle now reads "Real-time synchronization across **0 strategic initiatives**".

### New findings (Scenario 7)

- **F7-R — Silent line/item drop under rapid sequential adds (re-confirmed; prior F7).** Adding the 5 business units back-to-back via the Strategic Parameters add-form, 2 of 5 (Eastgate, Group) were **silently dropped** — no toast, error, or field highlight; the API confirmed only 3 persisted. Re-adding one-at-a-time with a pause succeeded every time. The add-forms still give no submit feedback and don't lock during submit, so fast entry races and loses items undetected. [Severity: Medium] _(A human at human speed likely avoids the race, but the no-feedback gap remains.)_ Note: the **governance gate-criteria** add-form, exercised one-at-a-time, persisted all 10 with no drops.

- **F13 — Setting Plan Base + Plan High on one benefit line is non-obvious; the natural path creates a duplicate line. [Severity: Medium]** In the Financials → Edit Details view, the benefit add-form writes its amount to the **currently selected scenario** (Base/High/Actuals toggle). To add the Plan High value to an existing line, switching to **High** and using **Add Line** again creates a *second* benefit line (verified: two lines, base-only + high-only). The monthly **DETAILED ENTRY grid** rows for the non-primary scenario (e.g. "… / Cost Savings (Plan High)") render as **dimmed/read-only** Handsontable cells, so there was no obvious in-view way to set the existing line's High value. Net effect: populating Plan High produces a duplicate, identically-named benefit line. Portfolio Base/High **totals still reconcile correctly** (the base total reads the base line, the high total the high line), but the Benefits Register is cluttered and per-line actions become ambiguous (see F-val). _Caveat: an intended grid-edit path may exist that I could not trigger via headless automation (Handsontable double-click editing is hard to drive over CDP); worth a human check before treating as a hard bug._

- **F-val — Per-line benefit actions are hard to disambiguate with duplicate-named lines (workflow itself works). [Severity: Low]** The validation workflow functions correctly on a single line — **Submit → `submitted`, Validate → `finance_validated`**, persisted immediately (no lock present, so the prior **F11** post-lock block does not apply here; Scenario 3 will test the locked path). But with two identically-named lines per initiative (from F13), the Submit/Validate buttons repeat per row and are hard to target unambiguously; bulk finance-validation across all 16 lines was not reliably completed in this automated pass. A real user clicking the visible row buttons would not hit this; it is largely an artifact of F13 + blind automation.

### Re-checked prior findings — status this pass
- **F3 (placeholder trend deltas)** — ✅ **FIXED** (no "from last week" chip at 0 or 8 initiatives).
- **F5 (subtitle mislabels initiatives as "workstreams")** — ✅ **FIXED** (reads "across 8 strategic initiatives"; count matches).
- **F6 (no way to delete a benefit/cost line)** — ✅ **appears FIXED**: benefit-line rows now expose a **Delete** action (alongside Submit/Validate/Reject/Risk). _(Not exercised destructively this pass; presence confirmed.)_
- **F1 / F2 (pre-payment email validation / provisioning error UX)** — not re-tested for the duplicate-email failure path this pass (used a fresh unique email; happy-path signup→checkout→provision was clean). Worth a dedicated duplicate-email retest.
- **F11 (validation blocked post-lock)** — deferred to Scenario 3 (Nordvik), which exercises the bankable lock.

### Scenario 7 verdict
**PASS (regression baseline).** The smoke/regression anchor holds: onboarding, master data, financial engine, governance setup, guided initiative intake (×8), benefit entry, and the portfolio financial engine all work, and the **Base $44.60M / High $61.50M** totals plus **3-way workstream=BU=portfolio reconciliation** are exact. New issues are concentrated in **data-entry UX** (F13/F-val) and the persistent **add-form race** (F7-R), not the analytics core. Three prior findings (F3, F5, F6) are confirmed fixed.

**Deviations from the runbook in this build (documented, non-blocking for S7's checks):** initiatives left at default **Identified** stage (S7 needs no locks and stage doesn't affect the regression totals; advancing to Executing/Build/Pilot needs full gate progression); per-initiative **realization = partially_realized** (PIN-002/003/004/008) not set; **bulk finance-validation** not fully completed (see F-val). None affect the recorded regression totals or the rollup reconciliation.
