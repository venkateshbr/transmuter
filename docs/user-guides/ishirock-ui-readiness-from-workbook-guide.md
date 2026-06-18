# Ishirock UI Readiness From Workbook Guide

This guide describes how to use the Transmuter UI to bring the `ishirock` tenant
to an ACME-style transformation-office demo readiness state using
`Initiative_Portfolio_Anonymised.xlsx` as the source of truth.

Use this guide when the goal is to test the UI workflows manually instead of
loading or correcting all data through scripts.

No credentials are included in this guide.

---

## 1. Current State

Read-only inspection on June 18, 2026 showed:

| Area | Current `ishirock` state |
|---|---:|
| Workbook initiatives present | 21 of 21 |
| Total initiatives in tenant | 23 |
| Business units | 10 |
| Workstreams | 4 |
| Benefit lines | 63 |
| Financial metric values | 4,696 |
| Cost lines | 925 |
| KPIs | 83 |
| KPI entries | 313 |
| Milestones | 292 |
| Risks | 34 |
| Status updates | 4 |
| Tenant annual baselines | 0 |
| Initiative annual baselines | 0 |
| Bankable plans | 0 |
| Benefit realization ledger rows | 0 |
| Workstream target locks | 0 |

The workbook portfolio is already mostly loaded. The main remaining readiness
work is baseline setup, Finance validation, bankable plan locking, benefit
realization entries, workstream target locks, and dashboard validation.

Dashboard financial behavior:

- The main `/dashboard` value bridge and workstream/tag value matrix read the
  configurable financial engine: active `plan_base`, `plan_high`, and `actual`
  scenario values from active benefit metric definitions, plus financial cost
  lines.
- Use `/financials`, `/financials/initiative-portfolio`,
  `/financials/benefits-register`, `/financials/bankable-plan`,
  `/financials/benefit-tracking`, `/financials/waterline`, and `/dashboard` as
  mutually reinforcing validation surfaces. The dashboard should show benefit
  values directly from configurable engine data.

---

## 2. Workbook Reference Values

Workbook source:

- `Initiative_Portfolio_Anonymised.xlsx`

Important sheets:

| Sheet | Use |
|---|---|
| `Initiative Summary` | Initiative list, workstream, BU, stage, RAG, priority, FY25 baseline, FY28 run-rate summary. |
| `Charter Details` | Initiative names, descriptions, value logic, dependencies, owners, stage gate, RAG, priority. |
| `Financial Summary` | Annual aggregate check sheet. Use for reconciliation, not direct UI entry. |
| `Benefits` | Benefit lines and plan/high/actual lanes. |
| `Costs` | Cost lines, one-off/recurring treatment, plan/actual lanes. |
| `KPIs` | KPI definitions and base/high/actual entries. |
| `Milestones` | Milestone dates, owners, status. |
| `Risks` | Risk descriptions, impact, likelihood, mitigation. |
| `Status Updates` | Existing initiative status updates. |
| `Dashboards` | Workbook-calculated management views. Use as a comparison target. |

Workbook FY25 baseline totals from `Initiative Summary`:

| FY25 baseline field | Total, USD m | Total, platform entry |
|---|---:|---:|
| Revenue FY25 Base | `134.932` | `134932000` |
| Gross Margin FY25 Base | `175.920` | `175920000` |
| Cost Plan FY25 Base | `26.530` | `26530000` |
| Net Value FY25 Base | `149.390` | `149390000` |

Workbook FY28 run-rate summary from `Initiative Summary`:

| FY28 field | Total, USD m | Expected platform value |
|---|---:|---:|
| Revenue | `30.008` | `$30.008M` |
| Gross Margin | `43.266` | `$43.266M` |
| Cost Plan | `7.120` | `$7.120M` |
| Net Value | `36.146` | `$36.146M` |

Current platform Financial Overview for FY28 may show a different benefits/net
definition because it sums configurable benefit metrics according to platform
benefit-class rules. Reconcile this explicitly during validation.

---

## 3. Readiness Target

By the end of the UI readiness pass:

1. Setup checklist is complete.
2. FY25 tenant baseline values are entered.
3. Initiative FY25 baseline values are entered where workbook values exist.
4. Workbook initiatives are reviewed from the UI and remain non-duplicated.
5. Benefit lines are submitted and Finance validated.
6. Benefit risk/handoff metadata is set.
7. Gate approvals create bankable plan snapshots.
8. Benefit realization ledger rows exist for selected initiatives or for all
   initiatives if you choose to run the full manual pass.
9. Workstream target locks exist for the 4 regional workstreams.
10. Financial Overview, Initiative Portfolio, Benefits Register, Bankable Plan,
    Benefit Tracking, Waterline, Control Tower, initiative detail pages, and PMO
    views are validated through the browser.
11. The main `/dashboard` value bridge and workstream/tag value matrix reconcile
    with configurable financial benefit values and cost lines for the selected
    year.

---

## 4. UI-Only Setup Pass

### Step 1: Sign in

Screen:

- `/auth/login`

Use a `transformation_office` user for the `ishirock` tenant.

Validation:

- Main navigation is visible.
- `/dashboard` loads.
- `/admin`, `/people`, `/financials`, and initiative edit pages are accessible.

### Step 2: Check setup status

Screen:

- `/admin`
- Tab: **General**

Actions:

1. Review **First-run setup**.
2. Confirm all checks are complete.
3. If a check is incomplete, use the relevant Admin tab to correct it before
   continuing.

Validation:

- Setup checklist should show complete.
- Financial engine, dimensions, stage gates, and users should all be configured.

### Step 3: Confirm workbook dimensions

Screen:

- `/admin`
- Tab: **Strategic Parameters**

Confirm workstreams:

- Eastbridge Region
- Northpeak Region
- Southgate Region
- Westmark Region

Confirm core workbook tags:

- automation
- commercial
- offshoring

Confirm business units include:

- BNT
- CAL
- FJD
- GROUP
- KLP
- MER
- RDG
- VER
- VSC

Validation:

- No duplicate workstreams with different casing.
- No duplicate business units with different casing.
- Pipeline filters show the same workstream and BU options.

### Step 4: Confirm financial metric configuration

Screen:

- `/admin`
- Tab: **Financial Configuration**
- Section: **Metric Definitions**

Confirm or create these metric definitions:

| Metric key | Label | Aggregation | Benefit class | Purpose |
|---|---|---|---|---|
| `revenue_uplift` | Revenue Uplift | Sum | Revenue | Commercial/revenue value. |
| `gross_margin` | Gross Margin | Sum | Margin | Workbook gross margin value. |
| `gm_uplift` | Gross Margin Uplift | Sum | Margin | Incremental margin uplift. |
| `cost_savings` | Cost Savings | Sum | Savings | Savings value if present. |
| `baseline_revenue` | Baseline Revenue | Last | None | FY25 revenue baseline. |

Recommended baseline correction:

- Set `baseline_revenue` group to `baseline` if the UI exposes group/key
  editing. This makes it eligible for initiative and tenant annual baseline
  views.

If gross margin baseline should appear as a first-class baseline metric, create
or enable:

| Metric key | Label | Aggregation | Benefit class | Purpose |
|---|---|---|---|---|
| `baseline_gross_margin` | Baseline Gross Margin | Last | None | FY25 gross margin baseline. |

Validation:

- `/initiatives/:id/edit` should show Annual Baseline fields for the active
  baseline metrics.
- `/financials/initiative-portfolio` should show `2025` as an available
  baseline year after tenant and initiative baselines are saved.

### Step 5: Enter tenant FY25 annual baseline

Screen:

- `/admin`
- Tab: **Financial Configuration**
- Section: **Annual Baselines**

Actions:

1. Set fiscal year to `2025`.
2. Enter tenant baseline values in whole dollars:
   - Baseline Revenue: `134932000`
   - Baseline Gross Margin, if configured: `175920000`
3. Click **Save**.

Validation:

- Refresh the page.
- Baseline values remain visible for fiscal year `2025`.
- `/financials/initiative-portfolio?baseline_year=2025` shows tenant baseline
  values after initiative-level baselines are also saved.

---

## 5. Initiative Baseline Pass

This is the most manual step. It is also the main UI test for baseline entry.

Screen:

- `/initiatives/pipeline`
- Open each workbook initiative.
- Click **Edit**.
- Use the **Annual Baseline** section.

Actions for each workbook initiative:

1. Set fiscal year to `2025`.
2. Enter `Revenue FY25 Base` from `Initiative Summary` into Baseline Revenue.
3. Enter `Gross Margin FY25 Base` from `Initiative Summary` into Baseline Gross
   Margin if that metric is configured.
4. Save the initiative.
5. Return to the initiative detail **Financials** tab.
6. Confirm the Annual Baseline panel shows FY25 values.

Data-entry rules:

- Enter whole dollars, not USD millions.
- Preserve zero values. Some initiatives have `0` revenue baseline; that is
  acceptable and should not be treated as missing.
- Do not enter baseline values for the 2 non-workbook initiatives unless you
  want them included in workbook demo reconciliation.

Validation:

- `/financials/initiative-portfolio`
- Set baseline year to `2025`.
- Set value year to `2028`.
- Confirm baseline reconciliation appears.
- Confirm baseline complete count increases as each initiative is updated.

Recommended sampling approach:

- First enter baselines for 3 initiatives, one from each value type:
  - `TOR-1`
  - `TOR-4`
  - `NPK-3`
- Validate the Initiative Portfolio screen.
- Then continue the remaining workbook initiatives.

---

## 6. Benefit Validation Pass

Screen:

- `/initiatives/pipeline`
- Open an initiative.
- Tab: **Financials**

Actions for each initiative:

1. Review the **Benefit lines** section.
2. For each benefit line, click **Submit**.
3. Enter a short Finance comment, for example:
   - `Workbook benefit reviewed against Initiative_Portfolio_Anonymised.xlsx.`
4. Leave evidence URL blank unless you have a specific source URL.
5. Click **Validate** for each submitted benefit line.
6. Enter a Finance validation comment, for example:
   - `Validated for demo readiness; workbook source reviewed.`
7. Click **Risk**.
8. Set risk rating:
   - `low` for green/straightforward benefits,
   - `medium` where assumptions require management attention.
9. Set risk adjustment percent:
   - `100` for fully accepted demo values,
   - lower only if you want risk-adjusted value to differ from plan.

Validation:

- `/financials/benefits-register`
- Set year to `2028`.
- Filter status to **Finance validated**.
- Confirm workbook benefit lines appear as Finance validated.
- Check totals for plan, actual, validated, risk-adjusted, bankable, and
  realized value.

Suggested manual scope:

- For a complete board demo, validate all 63 benefit lines.
- For a UI smoke pass, validate at least one initiative per workstream and tag:
  - `TOR-1` automation
  - `TOR-4` commercial
  - `TOR-3` offshoring
  - `EBR-1` automation
  - `NPK-3` commercial
  - `SGT-2` offshoring

---

## 7. Actuals Pass

There are two actuals flows:

| Actual flow | Screen | Purpose |
|---|---|---|
| Financial actuals | Initiative **Financials** tab, scenario **Actuals** | Populates plan-vs-actual reporting in Financial Overview and Initiative Portfolio. |
| Realization ledger | `/financials/benefit-tracking` | Tracks realized benefit evidence against locked bankable plan. |

The workbook actual benefit and cost lanes are mostly blank or zero. Do not
invent actuals unless the demo explicitly needs assumed actuals.

Recommended approach:

1. Leave actual financial values as workbook actuals unless you have evidence.
2. For UI testing, enter realization ledger rows for a small set of initiatives
   after bankable plans are locked.
3. Clearly label any manually entered demo realization as demo evidence.

Example ledger entries for UI testing:

| Initiative | Period | Actual amount | Description |
|---|---|---:|---|
| `TOR-1` | 2028-01-01 to 2028-12-31 | `560000` | Demo realized benefit entry for FY28. |
| `TOR-4` | 2028-01-01 to 2028-12-31 | `80000` | Demo realized benefit entry for FY28. |
| `NPK-3` | 2028-01-01 to 2028-12-31 | Use workbook net or approved amount | Demo realized benefit entry for FY28. |

Use actual values only if approved by management. Otherwise enter `0` to test
the workflow without implying realized value.

---

## 8. Governance And Bankable Plan Pass

Bankable plans are created when governance approvals are recorded. The Bankable
Plan screen is review-only; it does not create the lock directly.

Screen:

- `/initiatives/pipeline`
- Open initiative.
- Tab: **Governance**

Actions:

1. Start with a selected initiative, for example `TOR-1`.
2. In the active gate workspace, tick the visible criteria.
3. Click **Submit for Approval**.
4. As a `transformation_office` user, use the **Pending Approval** panel.
5. Enter decision commentary, for example:
   - `Approved for demo bankable plan lock from workbook source data.`
6. Click **Approve**.
7. Repeat until the initiative has reached the intended approved gate.

Workbook stage context:

- Workbook initiatives are currently stage `3`, mapped in `ishirock` as
  `committed`.
- If bankable plan governance is configured to lock at Gate 2 approval, each
  initiative may need approvals through Gate 2 before a locked plan appears.
- If the current tenant requires a different lock gate, follow that gate.

Validation:

- `/financials/bankable-plan`
- Select the initiative.
- Confirm status changes from **Editable** to **Locked**.
- Confirm version history shows a locked snapshot.
- Confirm snapshot summary, entries, metric values, and cost lines are non-zero
  where the initiative has financial data.

Recommended manual scope:

- Full readiness: approve/lock all 21 workbook initiatives.
- UI validation scope: lock at least one initiative per workstream:
  - `TOR-1`
  - `EBR-1`
  - `NPK-1`
  - `SGT-1`

---

## 9. Benefit Tracking Pass

Screen:

- `/financials/benefit-tracking`

Actions:

1. Open the **Ledger** tab.
2. Select a locked initiative.
3. Set granularity to `yearly`.
4. Set start to `2028-01-01`.
5. Set end to `2028-12-31`.
6. Enter approved actual amount.
7. Enter a description.
8. Click **Create**.

Alternative:

1. Open the **Import** tab.
2. Click **Download template**.
3. Replace the sample initiative code with workbook initiative codes such as
   `TOR-1`.
4. Upload the CSV.

Validation:

- Set scope to **Portfolio** and granularity to **Yearly**.
- Confirm:
  - locked bankable plan amount is non-zero,
  - actual amount reflects your entries,
  - variance is calculated.
- Set scope to **Workstream**.
- Confirm workstream rollups.
- Set scope to **Initiative**.
- Confirm initiative-level periods.

---

## 10. Waterline Pass

Screen:

- `/financials/waterline`

Actions for each workstream:

1. Select a workstream:
   - Eastbridge Region
   - Northpeak Region
   - Southgate Region
   - Westmark Region
2. Set lock date after the relevant approval date.
3. Click **Preview**.
4. Review included initiatives and target value.
5. Click **Lock target**.

Validation:

- Locked target history appears for the workstream.
- `/dashboard` Bankable Workstream Targets card shows locked workstreams and
  target values.
- `/financials/benefit-tracking` and `/financials/waterline` agree on locked
  target versus actual realization where data exists.

---

## 11. Dashboard And Report Validation

### Main dashboard

Screen:

- `/dashboard`

Expected to populate now:

- Total Initiatives
- At Risk
- Pending Approvals
- Pipeline by stage
- RAG breakdown
- Risk heatmap
- KPI pulse
- Recent activity
- Available filters
- Value bridge
- Workstreams x value tags matrix

Validation action:

- Select FY28 in the Workstreams x Value Tags control.
- Confirm dashboard benefit base/high/actual values are non-zero when
  `/financials` and `/financials/initiative-portfolio` show non-zero FY28
  configurable benefit values.
- Open at least one value-matrix cell and confirm the contributing initiatives,
  benefit base/high/actual, recurring costs, one-time costs, and net value are
  populated from the workbook-loaded configurable financial data.
- If the dashboard is zero while Financial Overview is non-zero, validate that
  the tenant has active `plan_base`, `plan_high`, and `actual` financial
  scenarios, active benefit metric definitions, and FY28 metric values for those
  scenarios.

### Financial Overview

Screen:

- `/financials`

Controls:

- Granularity: **Yearly**
- Year: `2028`
- Benefits: On
- Actuals: On

Expected:

- Plan benefits are non-zero.
- Plan costs are non-zero.
- Net value is non-zero.
- Actuals remain zero unless you entered actual financial values.
- Contributor drawer shows workbook initiatives.

### Initiative Portfolio

Screen:

- `/financials/initiative-portfolio`

Controls:

- Baseline year: `2025`
- Value year: `2028`
- Scenario: `Plan Base`

Expected:

- Workbook initiatives appear.
- FY25 baseline columns are populated after manual baseline entry.
- FY28 value metrics are populated.
- Recurring and one-off costs are populated.
- Baseline reconciliation shows tenant versus initiative totals.

### Benefits Register

Screen:

- `/financials/benefits-register`

Controls:

- Year: `2028`
- Status: All, then Finance validated

Expected:

- Benefit lines show validation status.
- Validated and risk-adjusted values populate after validation.
- Actual and realized values remain zero unless actuals/ledger rows are entered.

### Bankable Plan

Screen:

- `/financials/bankable-plan`

Expected:

- Locked initiatives show locked plan version.
- Unlocked initiatives show no locked plan.
- Version history appears after governance approval.

### Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Expected:

- Locked baseline appears after bankable plans are created.
- Actuals appear after ledger rows are manually entered or imported.
- Variance equals actual minus locked baseline.

### Control Tower

Screen:

- `/reports/control-tower`

Expected:

- Portfolio, risk, progress, and decision-support views reflect the workbook
  initiatives.
- Financial values should be compared with `/financials`; note any mismatch as
  a dashboard/reporting integration issue.

---

## 12. Recommended UI Test Sequence

Run this sequence in one browser session:

1. Login.
2. `/admin`: verify setup checklist and FY25 tenant baselines.
3. `/initiatives/pipeline`: filter by workstream, tag, and stage.
4. Open `TOR-1`: review Overview, Financials, Milestones, KPIs, Risks, Status,
   Governance, Team, Summary.
5. Edit `TOR-1`: save FY25 baseline values.
6. Return to `TOR-1` Financials: validate benefit lines.
7. `TOR-1` Governance: submit and approve gate to create bankable plan.
8. `/financials/bankable-plan`: confirm `TOR-1` locked plan.
9. `/financials/benefit-tracking`: enter a `TOR-1` yearly ledger row.
10. `/financials/waterline`: lock the Westmark Region target.
11. `/financials`: validate FY28 plan and actual summary.
12. `/financials/initiative-portfolio`: validate FY25 baseline and FY28 value.
13. `/financials/benefits-register`: validate Finance status and values.
14. `/dashboard`: validate operational widgets, value bridge, and workstream/tag
    value matrix.
15. `/reports/control-tower`: validate management view.
16. Repeat baseline, validation, gate, ledger, and waterline steps for the
    remaining selected initiatives or all 21 workbook initiatives.

---

## 13. Completion Criteria

Minimum UI-tested readiness:

- At least one initiative per workstream has:
  - FY25 baseline entered,
  - benefit lines Finance validated,
  - bankable plan locked,
  - benefit ledger row entered,
  - visible values in Financial Overview, Initiative Portfolio, Benefits
    Register, Bankable Plan, and Benefit Tracking.
- All 4 workstreams have waterline target locks.
- Dashboard operational widgets are validated.
- Dashboard value bridge and value matrix are validated against configurable
  financial metric values and cost lines.

Full ACME-style readiness:

- All 21 workbook initiatives have FY25 baselines entered.
- All 63 benefit lines are Finance validated.
- All 21 workbook initiatives have bankable plans locked.
- Benefit ledger rows exist for all initiatives where actual realization should
  be demonstrated.
- `/financials`, `/financials/initiative-portfolio`,
  `/financials/benefits-register`, `/financials/bankable-plan`,
  `/financials/benefit-tracking`, `/financials/waterline`, `/dashboard`, and
  `/reports/control-tower` have been browser-validated.
