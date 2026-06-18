# ACME Transformation Office Management Runbook

This runbook is the high-level operating guide for management users running the
ACME transformation program in Transmuter. It complements the detailed setup and
demo guide:

- `docs/user-guides/acme-transformation-office-detailed-setup-and-demo-guide.md`

No credentials are included in this runbook.

---

## 1. Purpose

Use Transmuter as the weekly and monthly operating layer for the ACME
transformation office:

1. Set up the portfolio structure.
2. Govern initiatives through stage gates.
3. Validate benefit and cost assumptions.
4. Lock approved value into bankable plans.
5. Track actual realization against locked plan.
6. Run management reviews from dashboards, reports, risks, actions, and meeting
   records.

The management outcome is a single version of the truth for:

- who owns each initiative,
- what value is planned,
- what value is Finance validated,
- what has been locked as bankable,
- what has actually been realized,
- what decisions are needed to protect value.

---

## 2. Roles

| Role | What they do in the program | Main screens |
|---|---|---|
| Executive Sponsor | Reviews value, risk, funding, and major decisions. | `/dashboard`, `/financials`, `/reports/control-tower` |
| Transformation Office Director | Owns the portfolio cadence and management story. | `/dashboard`, `/initiatives/pipeline`, `/financials`, `/reports/control-tower` |
| Finance Lead / Benefits Controller | Owns baselines, benefit validation, actuals, costs, and value reconciliation. | `/admin`, `/financials`, `/financials/benefits-register`, `/financials/bankable-plan`, `/financials/benefit-tracking` |
| PMO Lead | Owns gates, milestones, risks, actions, meetings, and delivery discipline. | `/progress`, `/pmo/governance`, `/pmo/risks`, `/meetings` |
| Workstream Lead | Runs a portfolio slice and escalates blockers. | `/initiatives/pipeline`, `/initiatives/matrix`, `/progress/roadmap`, `/financials/benefit-tracking` |
| Initiative Owner | Maintains initiative delivery data, assumptions, evidence, status, risks, KPIs, and actions. | `/initiatives/:id` |
| Business Benefit Owner | Confirms realized value is embedded in operations and sustainable. | `/financials/benefit-tracking`, `/financials/benefits-register`, initiative **Summary** tab |
| Tenant Administrator | Maintains users, roles, dimensions, tenant setup, and access. | `/admin`, `/people` |

---

## 3. Management Rhythm

### Weekly workstream review

Audience:

- Transformation office,
- workstream leads,
- initiative owners,
- PMO lead.

Run sequence:

1. Open `/initiatives/pipeline`.
2. Filter by workstream and review initiatives by stage, RAG, owner, and
   priority.
3. Open `/progress/roadmap` for milestone movement and blockers.
4. Open `/progress/action-items` for overdue or unassigned actions.
5. Open `/pmo/risks` for high-severity risks.
6. Capture decisions and next actions in `/meetings`.

Decision focus:

- Which initiatives are stuck?
- Which blockers need executive help?
- Which owners owe data updates?
- Which stage gate submissions are ready?

### Monthly value review

Audience:

- Executive sponsor,
- transformation office director,
- finance lead,
- PMO lead,
- workstream leads.

Run sequence:

1. Open `/financials`.
2. Set the target year, usually `2028` for ACME run-rate.
3. Review baseline cards: FY26 revenue baseline, FY26 gross margin baseline,
   and baseline margin rate.
4. Review benefits, recurring costs, one-off costs, net run-rate value, and
   actual variance.
5. Use the contributor drawer to trace portfolio value to initiatives.
6. Open `/financials/benefits-register` and review validation status.
7. Open `/financials/benefit-tracking` and compare realized actuals to locked
   bankable plan.
8. Open `/reports/control-tower` for the management decision view.

Decision focus:

- Is FY28 net run-rate value still credible?
- Which initiatives are causing value leakage?
- Which benefit lines are not Finance validated?
- Which actuals are missing or below locked plan?
- Which risks or actions need leadership decisions?

### Quarterly board review

Audience:

- Executive sponsor,
- CFO,
- transformation office director,
- finance lead,
- PMO lead.

Run sequence:

1. Open `/financials` and confirm the selected year and value basis.
2. Export the board pack from Financial Overview.
3. Open `/financials/bankable-plan` to confirm locked plans and rebaseline
   history.
4. Open `/financials/benefit-tracking` to review realization against locked
   baseline.
5. Open `/financials/waterline` to review frozen workstream targets.
6. Open `/reports/control-tower` to run the decision discussion.

Decision focus:

- What is the committed bankable value?
- What value has been realized?
- What variance requires action?
- Are targets changing through approved rebaseline or unmanaged drift?
- Which decisions should be recorded for the next quarter?

---

## 4. Standard Program Flow

### Step 1: Set up the transformation office

Owner:

- Tenant Administrator,
- Finance Lead,
- Transformation Office Director.

Screens:

- `/admin`,
- `/people`.

Outcome:

- Business units, workstreams, markets, themes, and tags are configured.
- Users have roles.
- Fiscal calendar, currency, metrics, scenarios, cost categories, value bridge,
  and annual baselines are configured.
- Governance stage gates and criteria are active.

### Step 2: Build the initiative portfolio

Owner:

- Transformation Office Director,
- Workstream Leads,
- Initiative Owners.

Screens:

- `/initiatives/pipeline`,
- `/initiatives/new`,
- `/initiatives/:id`.

Outcome:

- Every initiative has an owner, workstream, BU, tag, stage, planned dates,
  delivery narrative, and value hypothesis.
- ACME has 10 initiatives across automation, offshoring, commercial growth,
  ERP/data platform, and procurement/supply chain.

### Step 3: Build and validate the financial case

Owner:

- Finance Lead,
- Initiative Owners.

Screens:

- `/initiatives/:id/financial-scope`,
- initiative **Financials** tab,
- `/financials/benefits-register`,
- `/financials`.

Outcome:

- Initiative financial scope is configured.
- FY26 baseline allocation reconciles to the tenant baseline.
- Plan Base, Plan High, and Actual scenarios are available.
- Benefit lines and cost lines are named, phased, and evidenced.
- Finance validation status is visible in the Benefits Register.

### Step 4: Lock bankable plans

Owner:

- Finance Lead,
- PMO Lead,
- Transformation Office Director.

Screens:

- initiative **Governance** tab,
- `/pmo/governance`,
- `/financials/bankable-plan`.

Outcome:

- Approved initiatives have locked plan snapshots.
- Rebaseline is versioned rather than silently overwriting the approved plan.
- Management can compare actual realization to a stable baseline.

### Step 5: Run delivery

Owner:

- Initiative Owners,
- Workstream Leads,
- PMO Lead.

Screens:

- initiative **Milestones**, **KPIs**, **Risks**, **Dependencies**, **Status**,
  and **Team** tabs,
- `/progress`,
- `/meetings`.

Outcome:

- Owners keep delivery data current.
- PMO tracks actions, blockers, and decision follow-up.
- Management can explain financial variance through delivery evidence.

### Step 6: Enter actuals and realized benefits

Owner:

- Finance Lead,
- Benefits Controller,
- Business Benefit Owner.

Screens:

- initiative **Financials** tab, scenario **Actuals**,
- `/financials/benefit-tracking`,
- `/financials/benefits-register`.

Outcome:

- Actual financial values are entered in the Actuals scenario.
- Realized benefit ledger rows are entered or imported.
- Benefit Tracking compares actual realization to locked bankable plan.
- Finance can distinguish planned value, validated value, bankable value, and
  realized value.

### Step 7: Report, decide, and realize

Owner:

- Executive Sponsor,
- Transformation Office Director,
- Finance Lead,
- PMO Lead.

Screens:

- `/dashboard`,
- `/financials`,
- `/financials/benefit-tracking`,
- `/reports/control-tower`.

Outcome:

- Management reviews baseline, value, costs, actuals, variance, risks, and
  decisions.
- Realized initiatives move toward Gate 5 only when evidence and BAU ownership
  are confirmed.
- Lessons learned and final value are captured in the initiative summary.

---

## 5. Dashboard And Report Usage

| Dashboard or report | Use it to answer | Management action |
|---|---|---|
| `/dashboard` | What is the portfolio posture? | Decide where to drill in. |
| `/initiatives/pipeline` | Which initiatives exist, who owns them, and what stage are they in? | Challenge ownership, stage readiness, or stale updates. |
| `/initiatives/matrix` | Where is value concentrated by workstream and tag? | Rebalance focus across value levers. |
| `/financials` | What is the baseline, planned value, actual value, cost, variance, and net run-rate value? | Approve value narrative and investigate leakage. |
| `/financials/benefits-register` | Which benefit lines are validated, rejected, risk adjusted, bankable, or realized? | Prevent unvalidated benefits from reaching the board story. |
| `/financials/bankable-plan` | What approved plan is locked, and has it been rebaselined? | Confirm whether actuals are compared to the right baseline. |
| `/financials/benefit-tracking` | What has been realized against locked plan? | Ask owners to explain positive or negative variance. |
| `/financials/waterline` | What target is frozen by workstream? | Prevent unmanaged target drift. |
| `/shared-costs` | Which central costs affect portfolio economics? | Allocate or challenge shared run costs. |
| `/progress` and `/progress/roadmap` | Are milestones and delivery plans on track? | Escalate blocked milestones. |
| `/progress/action-items` | Who owes what by when? | Clear overdue actions. |
| `/pmo/governance` | Which gates need submission or approval? | Approve, reject, or request more evidence. |
| `/pmo/risks` | Which risks threaten value or timeline? | Assign mitigation owners. |
| `/pmo/kpis` | Are operating KPIs moving with the financial case? | Challenge benefit credibility when KPIs do not support it. |
| `/meetings` | What decisions and actions came from reviews? | Keep meeting evidence and follow-up in the system. |
| `/reports/control-tower` | What should management decide now? | Run the steering committee from one consolidated view. |

---

## 6. ACME Value Narrative

For the ACME demo, use this management summary:

```text
FY28 EBITDA-effective net run-rate value
= Gross Margin Uplift + Cost Savings - Recurring Run Costs
= $5.40M + $3.75M - $0.80M
= $8.35M
```

Do not call revenue uplift EBITDA. Revenue uplift is the commercial driver; its
EBITDA effect should be discussed through gross margin uplift.

Key ACME facts:

| Item | ACME value |
|---|---:|
| FY26 revenue baseline | `$20.00M` |
| FY26 gross margin baseline | `$9.00M` |
| Baseline margin rate | `45.0%` |
| FY28 revenue uplift | `$4.00M` |
| FY28 gross margin uplift | `$5.40M` |
| FY28 cost savings | `$3.75M` |
| FY28 recurring run cost | `$0.80M` |
| FY28 net run-rate value | `$8.35M` |
| One-off implementation investment | `$2.50M` |

---

## 7. Management Checks

Use these checks before a steering committee or board review:

| Check | Owner | Where to verify |
|---|---|---|
| Users and roles are current. | Tenant Administrator | `/people`, `/admin` |
| Initiative owners and workstreams are assigned. | Transformation Office Director | `/initiatives/pipeline` |
| Initiative baseline allocation reconciles to tenant baseline. | Finance Lead | `/financials`, initiative **Financials** tabs |
| Benefit lines have validation status. | Finance Lead | `/financials/benefits-register` |
| Approved plans are locked. | Finance Lead / PMO Lead | `/financials/bankable-plan` |
| Actuals are entered for the reporting period. | Finance Lead | Initiative **Financials** tab, scenario **Actuals** |
| Benefit ledger rows are entered or imported. | Benefits Controller | `/financials/benefit-tracking` |
| Risks and actions have owners. | PMO Lead | `/pmo/risks`, `/progress/action-items` |
| Meeting decisions are recorded. | PMO Lead | `/meetings` |
| Board pack uses the correct year and value basis. | Finance Lead | `/financials` |

---

## 8. Common Management Rules

1. Use FY28 as the ACME run-rate year unless the discussion is explicitly about
   FY27 ramp.
2. Use EBITDA-effective net run-rate value for management value claims:
   gross margin uplift plus cost savings minus recurring run costs.
3. Treat one-off costs as implementation investment and payback burden, not
   recurring EBITDA drag.
4. Treat the locked bankable plan as the realization baseline.
5. Treat benefit ledger actuals as the evidence-backed realization record.
6. Do not present draft, rejected, or unvalidated benefit lines as Finance
   validated value.
7. Do not let target changes bypass bankable-plan rebaseline governance.
8. Use Control Tower for decisions and Financial Overview for reconciliation.
