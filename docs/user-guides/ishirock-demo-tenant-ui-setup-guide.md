# Ishirock Demo Tenant UI Setup Guide

Last updated: 2026-06-21

This guide explains how a normal tenant user can review, correct, and
demonstrate the `ishirock` tenant through the Transmuter UI using
`Initiative_Portfolio_Anonymised.xlsx` as the business source of truth.

Use this guide for the existing `ishirock` tenant and for any new tenant that
must reproduce the Ishirock workbook portfolio. The guide is intentionally
similar in structure to `docs/user-guides/acme-demo-tenant-ui-setup-guide.md`,
but it reflects the actual Ishirock workbook and the current tenant rows loaded
from that workbook.

No credentials are included in this guide.

## 1. Demo Outcome

After completing this guide, the tenant can demonstrate:

- Tenant onboarding and first-run setup.
- Master data: business units, workstreams, tags, markets, and theme.
- Financial configuration: scenarios, metrics, baselines, cost categories,
  value bridge rows, and fiscal settings.
- Governance stage gates and gate criteria.
- Twenty-one Ishirock workbook initiatives with regional workstreams, business
  units, tags, stages, RAG, priority, owners, benefits, costs, KPIs,
  milestones, risks, and status updates.
- Baseline setup using the workbook FY25 values.
- Benefit validation, bankable plan readiness, realization ledger readiness,
  and waterline target locks.
- Dashboard and report reconciliation against the workbook `Dashboards`,
  `Initiative Summary`, and `Financial Summary` sheets.

This guide intentionally skips Meeting setup. The current workbook load does not
create meetings, agenda items, attendees, sessions, or action items.

Expected Ishirock workbook totals:

| Area | Expected result |
|---|---:|
| Workbook initiatives | `21` |
| Workstreams | `4` |
| Business units in workbook | `9` |
| FY25 revenue baseline | `$67.466M` |
| FY25 workbook margin/value baseline | `$87.960M` |
| FY25 cost plan baseline | `$13.265M` |
| FY25 net value baseline | `$74.695M` |
| FY28 revenue uplift | `$15.004M` |
| FY28 gross margin value | `$21.633M` |
| FY28 cost plan | `$3.560M` |
| FY28 net value | `$18.073M` |

FY28 workbook net value formula:

```text
Gross Margin - Cost Plan
= $21.633M - $3.560M
= $18.073M
```

Important dashboard interpretation:

- In the main `/dashboard` value bridge and workstream/tag value matrix,
  `benefits_base` and matrix `base` values are dashboard benefit values. For
  Ishirock, that should reconcile to workbook gross margin value, not to
  revenue uplift.
- Revenue uplift is still loaded and should be validated through `/financials`
  and `/financials/initiative-portfolio`, but it is not the main dashboard
  value-matrix base number.
- Use FY28 as the primary dashboard reconciliation year because it is the
  workbook's selected base run-rate year.

## 2. Sources Reviewed

This guide was validated against:

| Source | Purpose |
|---|---|
| `docs/user-guides/acme-demo-tenant-ui-setup-guide.md` | Structure and level of detail for a UI setup guide. |
| `Initiative_Portfolio_Anonymised.xlsx` | Business source of truth for initiatives, baselines, benefits, costs, KPIs, milestones, risks, status updates, and dashboard values. |
| Current local `ishirock` tenant rows | Actual data currently present in the platform. |
| `apps/api/app/services/portfolio_workbook.py` | Workbook import behavior and field mapping. |
| `apps/api/app/services/dashboard.py` | Main dashboard value bridge and value matrix rollup behavior. |
| `supabase/migrations/20260611000002_clean_configurable_financial_engine.sql` | Configurable metric, scenario, benefit-line, and metric-value tables. |
| `supabase/migrations/20260615000001_annual_financial_baselines.sql` | Tenant and initiative annual baseline tables. |

## 3. Tenant State

Initial read-only inspection of the local `ishirock` tenant on 2026-06-21
showed:

| Area | Current tenant state |
|---|---:|
| Workbook initiatives present | `21 of 21` |
| Total active initiatives | `23` |
| Business units | `10` |
| Workstreams | `4` |
| Benefit lines | `63` |
| Financial metric values | `4,696` |
| Cost lines | `925` |
| KPIs | `83` |
| KPI entries | `313` |
| Milestones | `292` |
| Risks | `34` |
| Status updates | `4` |
| Tenant annual baselines | `0` |
| Initiative annual baselines | `0` |
| Bankable plans | `0` |
| Benefit realization ledger rows | `0` |
| Workstream target locks | `0` |

Clean workbook parser summary from the current implementation:

| Area | Clean parser result |
|---|---:|
| Initiatives | `21` |
| Business units | `9` |
| Workstreams | `4` |
| Benefit lines | `63` |
| Financial metric values | `4,694` |
| Cost lines | `867` |
| KPIs | `83` |
| KPI entries | `313` |
| Milestones | `292` |
| Risks | `33` |
| Status updates | `4` |

Interpretation:

- The 21 workbook initiatives are present.
- The current tenant has two extra active non-workbook initiatives:
  `TRN-007` and `TRN-008`.
- The current tenant has extra configuration/data drift beyond a clean workbook
  reload: extra business unit, extra cost lines, two extra zero metric rows, one
  extra risk attached to a non-workbook initiative, and inactive test cost
  categories.
- Baselines, bankable plans, benefit realization ledger rows, and workstream
  target locks were not yet configured.

Post-remediation state after issue `#335` on 2026-06-21:

| Area | Current tenant state |
|---|---:|
| Active workbook initiatives | `21` |
| Archived non-workbook initiatives | `2` |
| Business units | `9` |
| Workstreams | `4` |
| Benefit lines | `63` |
| Finance-validated benefit lines | `63` |
| Cost lines | `867` |
| Gate 3 approved submissions | `21` |
| Tenant annual baselines | `4` FY25 values |
| Initiative annual baselines | `84` FY25 values |
| Bankable plans | `21` |
| Benefit realization ledger rows | `0` |
| Workstream target locks | `4` |

Post-remediation interpretation:

- `TRN-007` and `TRN-008` are archived, not deleted.
- Business unit names and initiative BU links now match the workbook.
- `EBR-1` duplicate grid cost rows have been removed.
- FY25 tenant and initiative baselines reconcile exactly.
- All 63 benefit lines are Finance validated and assigned to the transformation
  office for demo handoff.
- Bankable plans and waterline target locks exist for all 21 workbook
  initiatives.
- Benefit realization actuals are still intentionally blank because the workbook
  does not provide actual values for the reviewed dashboard lanes.

## 4. Create Or Open The Tenant

Use the public app URL for production validation:

```text
https://transmuter.ishirock.tech
```

For dev validation, use:

```text
https://transmuter-dev.ishirock.tech
```

### 4.1 Existing Tenant

If using the existing tenant:

1. Open the target environment.
2. Sign in as a `transformation_office` or tenant administrator user for the
   `ishirock` tenant.
3. Open `/dashboard`.
4. Confirm the tenant has Ishirock workbook portfolio data.
5. Open `/admin`.
6. Review **First-run setup**.

### 4.2 New Tenant

If creating a new tenant:

1. Open the target environment.
2. Select **Get Started**.
3. Create the tenant using:

| Field | Value |
|---|---|
| Organization name | `Ishirock` |
| Suggested slug | `ishirock` or an environment-specific slug such as `ishirock-demo` |
| Planned users | Use the expected transformation-office team size. |

4. Complete the subscription checkout flow for the environment.
5. Return to Transmuter and sign in as the initial administrator.
6. Open `/dashboard` and confirm the tenant starts blank.
7. Open `/admin` and keep it open for the setup steps below.

New tenants should start blank. Do not expect business units, workstreams,
initiatives, or financial configuration to be preloaded unless an operator has
already run the workbook reload.

## 5. Configure Master Data

Screen:

- `/admin`
- Tab: **Strategic Parameters**

### 5.1 Business Units

Create these workbook business units:

| Business unit | Purpose |
|---|---|
| BNT | Southgate business unit used by tax and audit support initiatives. |
| CAL | Westmark business unit used by accounting, CoSec, tax, and advisory initiatives. |
| FJD | Northpeak business unit used by reconciliation, bookkeeping, and CoSec initiatives. |
| GROUP | Group-level unit used by revenue retention initiatives. |
| KLP | Northpeak business unit used by energy and public-sector commercial initiatives. |
| MER | Eastbridge business unit used by billing, payroll, and audit expansion initiatives. |
| RDG | Eastbridge business unit used by manufacturing and document automation initiatives. |
| VER | Westmark business unit used by FDI new-logo initiatives. |
| VSC | Southgate business unit used by financial-services and advisory initiatives. |

Current tenant issue:

- The current tenant has `Group` instead of workbook `GROUP`.
- The current tenant also has `Southeast Asia`, which is not in the workbook.

Recommended correction for strict workbook matching:

1. Rename `Group` to `GROUP`.
2. Remove or leave unused `Southeast Asia` if no active initiative should filter
   through it.
3. Confirm `/initiatives/pipeline` and `/dashboard` filters show the workbook
   business units exactly once.

### 5.2 Workstreams

Create or confirm these workstreams:

| Workstream | Purpose |
|---|---|
| Westmark Region | Westmark regional transformation portfolio. |
| Eastbridge Region | Eastbridge regional transformation portfolio. |
| Northpeak Region | Northpeak regional transformation portfolio. |
| Southgate Region | Southgate regional transformation portfolio. |

Validation:

- No duplicate workstreams with different casing.
- Each workbook initiative has exactly one of the four workstreams.

### 5.3 Market, Theme, Tags

Create:

| Type | Values |
|---|---|
| Market | Use the market/country value required by the tenant demo. The workbook rows do not require one single market for reconciliation. |
| Theme | Enterprise transformation portfolio from workbook source data. |
| Tags | `automation`, `commercial`, `offshoring` |

Validation:

- Pipeline filters show `automation`, `commercial`, and `offshoring`.
- No blank tag appears for the 21 workbook initiatives.
- A blank tag may still appear if the two non-workbook `TRN-*` initiatives are
  retained.

## 6. Configure Users

Screens:

- `/people`
- `/admin`, tab: **Access Control**

Minimum demo users:

| User type | Role |
|---|---|
| Transformation office lead | `transformation_office` |
| Tenant administrator | `tenant_admin` |
| PMO / governance lead | `pmo_lead` |
| Finance lead / benefits controller | `finance_lead` |
| Workstream lead | `workstream_lead` |
| Initiative owner | `initiative_owner` |
| Business benefit owner | `business_benefit_owner` |
| Executive sponsor | `executive_sponsor` |
| Management viewer | `viewer` |

Steps:

1. Open **People**.
2. Invite or create the transformation office user.
3. Invite or create the finance user.
4. Invite or create at least one initiative owner.
5. Invite or create the PMO, finance, workstream, benefit-owner,
   executive-sponsor, and viewer users needed for the walkthrough.
6. Open **Admin > Access Control**.
7. Confirm each user has the intended role.

Workbook owner note:

- The workbook includes owner names such as Dana Reyes, Priya Nadkarni, and
  Aisha Rahman.
- The current workbook reload implementation does not automatically create or
  match users by those owner names. It assigns the reload user as owner and
  group owner.
- If the demo requires named owner accountability, create users manually and
  reassign initiative owners in the UI.

## 7. Configure Financial Engine

Screen:

- `/admin`
- Tab: **Financial Configuration**

### 7.1 Reporting Settings

Set:

| Setting | Value |
|---|---|
| Reporting currency | `USD` |
| Fiscal year start | `January` |

Save settings.

### 7.2 Scenarios

Create or confirm these active scenarios:

| Key | Label | Kind | Primary |
|---|---|---|---|
| `baseline` | Baseline | Baseline | No |
| `plan_base` | Plan Base | Plan | Yes |
| `plan_high` | Plan High | Plan | No |
| `actual` | Actual | Actual | No |

Use **Plan Base** as the primary management case.

### 7.3 Metric Definitions

Create or confirm these metric definitions:

| Key | Label | Type | Aggregation | Benefit class | Required for |
|---|---|---|---|---|---|
| `revenue_uplift` | Revenue Uplift | Currency | Sum | Revenue | Workbook revenue values. |
| `gross_margin` | Gross Margin | Currency | Sum | Margin | Workbook gross-margin value and `/dashboard` base benefits. |
| `gm_uplift` | Gross Margin Uplift | Currency | Sum | Margin | Compatibility with value bridge and older demo metrics. |
| `cost_savings` | Cost Savings | Currency | Sum | Savings | Optional savings benefits. Not used by the current workbook parser. |
| `baseline_revenue` | Baseline Revenue | Currency | Last | None | FY25 revenue baseline. |
| `revenue_uplift_pct` | Revenue Uplift % | Percent | Formula | None | Optional formula metric. |
| `gm_pct` | Gross Margin % | Percent | Formula | None | Optional formula metric. |
| `gm_uplift_pct` | Gross Margin Uplift % | Percent | Formula | None | Workbook percentage benefit line. |
| `cogs` | Cost of Goods Sold | Currency | Sum | None | Optional cost metric. |
| `cogs_pct` | COGS % | Percent | Formula | None | Optional formula metric. |
| `roi_actual` | ROI Actual % | Percent | Formula | None | Optional actual ROI metric. |

Important:

- The workbook parser creates metric values for `gm_uplift_pct`, but the
  dashboard intentionally skips formula metrics when calculating dollar benefit
  values.
- The `/dashboard` gross-margin benefit value comes from non-revenue active
  benefit metrics, primarily `gross_margin`.

### 7.4 Tenant Annual Baselines

In **Annual Baselines**, enter:

| Metric | Baseline year | Value |
|---|---:|---:|
| Baseline Revenue | 2025 | `67466000` |

Do not enter workbook `Gross Margin FY25 Base` as conventional accounting gross
margin unless Finance confirms that interpretation.

Recommended Finance-controlled option:

| Metric | Baseline year | Value |
|---|---:|---:|
| Baseline Margin / Value | 2025 | `87960000` |

Use a neutral metric name such as `baseline_margin_value` if Finance wants to
track the workbook field as an addressable margin/value baseline.

Why this matters:

- Workbook FY25 gross margin/value baseline is `$87.960M`.
- Workbook FY25 revenue baseline is `$67.466M`.
- Gross margin higher than revenue is not a normal accounting relationship.
- The workbook is using the gross margin field as a value/margin baseline for
  cost-reduction initiatives that have no revenue baseline.

### 7.5 Cost Categories

Create or confirm these active categories:

| Key | Label | Group | Rollup |
|---|---|---|---|
| `implementation` | Implementation / Project Cost | Implementation | One-off |
| `technology_tooling` | Technology / Tooling | Implementation | One-off |
| `external_consultants` | External Consultants | Implementation | One-off |
| `training_change` | Training / Change Management | Implementation | One-off |
| `other_one_off` | Other One-off Cost | Implementation | One-off |
| `software_subscriptions` | Software Subscriptions | Operating | Recurring |
| `software` | Software / Licenses | Operating | Recurring |
| `support_maintenance` | Support / Maintenance | Operating | Recurring |
| `maintenance` | Maintenance | Operating | Recurring |
| `labor` | Labor / Operations | Operating | Recurring |
| `additional_headcount` | Additional Headcount | Operating | Recurring |
| `run_rate_operating` | Run-rate Operating Cost | Operating | Recurring |
| `other` | Other | Uncategorized | None |

Current tenant issue:

- The current tenant has many inactive `ui_acceptance_category_*` and
  `acceptance_*` categories.
- They are inactive and should not affect normal dashboard calculations, but
  they clutter Admin configuration.

Recommended correction:

1. Leave inactive categories alone if you only need runtime demo behavior.
2. Delete or archive inactive acceptance/test categories if Admin cleanliness is
   important for the walkthrough.
3. Do not map workbook cost lines to inactive test categories.

### 7.6 Value Bridge Rows

Create or confirm these bridge rows:

| Key | Label | Row kind | Sign | Inputs |
|---|---|---|---:|---|
| `revenue` | Revenue Uplift | Metric set | `+` | Revenue Uplift |
| `margin` | Gross Margin Uplift | Metric set | `+` | Gross Margin Uplift or Gross Margin, depending on tenant bridge configuration. |
| `other_benefits` | Other Benefits | Metric set | `+` | Cost Savings, if used. |
| `recurring_costs` | Recurring Costs | Cost set | `-` | Recurring cost categories. |
| `one_off_costs` | One-off Costs | Cost set | `-` | One-off cost categories. |
| `net_value` | Net Value | Net | `+` | Calculated net row. |

For exact Ishirock FY28 dashboard matching, the bridge and dashboard should
show:

```text
Gross Margin Benefit - Cost Plan
= $21.633M - $3.560M
= $18.073M
```

## 8. Configure Governance

Screen:

- `/admin`
- Tab: **Governance Engine**

### 8.1 Stage Gates

Create or confirm five gates:

| Gate | Key | Label | From stage | To stage | Approval |
|---:|---|---|---|---|---|
| 1 | `g1_identify_validate` | Gate 1: Identify to Validate | identified | validated | Required |
| 2 | `g2_validate_plan` | Gate 2: Validate to Plan | validated | planned | Required |
| 3 | `g3_plan_commit` | Gate 3: Plan to Commit | planned | committed | Required |
| 4 | `g4_commit_execute` | Gate 4: Commit to Execute | committed | executing | Required |
| 5 | `g5_execute_realize` | Gate 5: Execute to Realized | executing | realized | Required |

Set approver role to `transformation_office`. Enable **Require all criteria**
where the UI offers it.

### 8.2 Gate Criteria

Create these criteria:

| Gate | Criterion | Guidance |
|---:|---|---|
| 1 | Strategic fit confirmed | Initiative supports the regional transformation thesis. |
| 1 | Value hypothesis documented | Initial revenue, margin, or cost value logic is documented. |
| 2 | FY25 baseline approved | Workbook FY25 baseline allocation and measurement method are agreed. |
| 2 | Benefit assumptions documented | Revenue, margin, cost, and timing assumptions are captured. |
| 2 | Finance validation completed | Finance has validated the benefit logic before bankable plan lock. |
| 3 | Delivery plan approved | Milestones, dependencies, budget, and owner accountability are approved. |
| 3 | Owner and sponsor assigned | Business owner, sponsor, and transformation office owner are assigned. |
| 4 | Implementation evidence submitted | Execution evidence confirms the initiative is live or materially complete. |
| 4 | Actuals collection started | Benefit realization actuals are being captured in the ledger. |
| 5 | Benefits realized and accepted | Realized value is accepted by Finance and the business owner. |

Current tenant state:

- All 21 workbook initiatives are currently at stage `committed`.
- Gate approvals and bankable plans are not yet present.
- To demonstrate bankable plan locking, submit and approve the required gates
  through the UI rather than manually editing stage values.

## 9. Create Or Validate The Ishirock Initiatives

Screen:

- `/initiatives/new` for a new tenant.
- `/initiatives/pipeline` for the existing tenant.

Create or validate these 21 workbook initiatives. Values are from
`Initiative Summary`; money columns are USD millions.

| Code | Initiative | Workstream | BU | Type | Tag | Owner from workbook | FY25 revenue | FY25 margin/value | FY25 cost | FY25 net | FY28 revenue | FY28 gross margin | FY28 cost | FY28 net |
|---|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| TOR-1 | CAL Accounting System Integration & Automation | Westmark Region | CAL | cost_reduction | automation | Dana Reyes | `0.000` | `2.192` | `0.295` | `1.897` | `0.000` | `0.620` | `0.060` | `0.560` |
| TOR-2 | CAL CoSec System Implementation, Integration & Automation | Westmark Region | CAL | cost_reduction | automation | Olivia Tan | `0.000` | `3.100` | `0.322` | `2.778` | `0.000` | `0.920` | `0.100` | `0.820` |
| TOR-3 | Offshoring to Tavel SSC (+ Automation) - Tax | Westmark Region | CAL | cost_reduction | offshoring | Marcus Lee | `0.000` | `8.652` | `0.406` | `8.246` | `0.000` | `1.860` | `0.100` | `1.760` |
| TOR-4 | Verland-Norvia New Logos - FDI | Westmark Region | VER | revenue | commercial | Lukas Brandt | `3.961` | `3.016` | `1.961` | `1.055` | `1.100` | `0.720` | `0.640` | `0.080` |
| TOR-5 | Advisory - Geographical Expansion | Westmark Region | CAL | revenue | commercial | Grace Liang | `10.967` | `6.120` | `0.000` | `6.120` | `2.460` | `1.420` | `0.000` | `1.420` |
| TOR-6 | [GROUP] Revenue Retention: Reinvent CSM for Proactive Churn Management (Westmark) | Westmark Region | GROUP, CAL, VER | revenue | commercial | Julien Moreau | `1.545` | `1.024` | `0.000` | `1.024` | `0.400` | `0.240` | `0.000` | `0.240` |
| EBR-1 | MER Billing System Integration & Automation | Eastbridge Region | MER | cost_reduction | automation | Priya Nadkarni | `0.000` | `3.200` | `0.261` | `2.939` | `0.000` | `0.682` | `0.066` | `0.616` |
| EBR-2 | Offshoring to Caldez SSC (+ Automation) - Payroll | Eastbridge Region | MER | cost_reduction | offshoring | Marcus Lee | `0.000` | `7.339` | `0.322` | `7.017` | `0.000` | `1.674` | `0.090` | `1.584` |
| EBR-3 | Audit Practice - Cross-Border Expansion | Eastbridge Region | MER | revenue | commercial | Niels Berg | `12.722` | `7.592` | `0.000` | `7.592` | `2.829` | `1.633` | `0.000` | `1.633` |
| EBR-4 | MER-RDG New Logos - Manufacturing | Eastbridge Region | RDG | revenue | commercial | Aisha Rahman | `3.967` | `2.337` | `2.143` | `0.194` | `0.935` | `0.612` | `0.544` | `0.068` |
| EBR-5 | RDG Document Automation & OCR Rollout | Eastbridge Region | RDG | cost_reduction | automation | Elena Vasquez | `0.000` | `4.022` | `0.323` | `3.699` | `0.000` | `0.966` | `0.105` | `0.861` |
| NPK-1 | FJD Reconciliation Automation (RPA) | Northpeak Region | FJD | cost_reduction | automation | Priya Nadkarni | `0.000` | `1.947` | `0.253` | `1.694` | `0.000` | `0.589` | `0.057` | `0.532` |
| NPK-2 | Offshoring to Solva SSC (+ Automation) - Bookkeeping | Northpeak Region | FJD | cost_reduction | offshoring | Aisha Rahman | `0.000` | `7.116` | `0.447` | `6.669` | `0.000` | `2.232` | `0.120` | `2.112` |
| NPK-3 | Advisory - Energy Sector Expansion | Northpeak Region | KLP | revenue | commercial | Niels Berg | `8.578` | `5.277` | `0.000` | `5.277` | `1.968` | `1.136` | `0.000` | `1.136` |
| NPK-4 | KLP New Logos - Public Sector | Northpeak Region | KLP | revenue | commercial | Marcus Lee | `5.986` | `3.216` | `2.541` | `0.675` | `1.210` | `0.792` | `0.704` | `0.088` |
| NPK-5 | FJD CoSec Workflow Automation | Northpeak Region | FJD | cost_reduction | automation | Wei Chen | `0.000` | `3.091` | `0.417` | `2.674` | `0.000` | `0.828` | `0.090` | `0.738` |
| NPK-6 | [GROUP] Revenue Retention: Proactive Churn Management (Northpeak) | Northpeak Region | GROUP, FJD, KLP | revenue | commercial | Omar Haddad | `2.478` | `1.432` | `0.000` | `1.432` | `0.500` | `0.300` | `0.000` | `0.300` |
| SGT-1 | BNT Tax Compliance Automation | Southgate Region | BNT | cost_reduction | automation | Priya Nadkarni | `0.000` | `2.090` | `0.281` | `1.809` | `0.000` | `0.651` | `0.063` | `0.588` |
| SGT-2 | Offshoring to Pravin SSC (+ Automation) - Audit Support | Southgate Region | BNT | cost_reduction | offshoring | Grace Liang | `0.000` | `7.501` | `0.263` | `7.238` | `0.000` | `1.581` | `0.085` | `1.496` |
| SGT-3 | VSC New Logos - Financial Services | Southgate Region | VSC | revenue | commercial | Aisha Rahman | `6.256` | `3.109` | `3.030` | `0.079` | `1.265` | `0.828` | `0.736` | `0.092` |
| SGT-4 | Advisory - Geographical Expansion (Vandor) | Southgate Region | VSC | revenue | commercial | Marco Bianchi | `11.006` | `4.587` | `0.000` | `4.587` | `2.337` | `1.349` | `0.000` | `1.349` |
| **Total** |  |  |  |  |  |  | **`67.466`** | **`87.960`** | **`13.265`** | **`74.695`** | **`15.004`** | **`21.633`** | **`3.560`** | **`18.073`** |

Use these common fields for new manual initiative creation:

| Field | Value |
|---|---|
| Stage | `committed` after gates are approved. Use `identified` first if you want to demonstrate gate progression. |
| RAG | `green` |
| Priority | `high` |
| Impact type | `recurring` where the UI requires one default. |
| Planned completion | Use the workbook planned completion date. |
| Summary | Use the workbook Charter Details description. |
| Value logic | Use the workbook Charter Details value logic and assumptions. |
| Dependencies text | Use the workbook Charter Details dependencies. |

## 10. Validate Initiative Dimensions

Screen:

- `/initiatives/pipeline`
- Open each initiative
- Click **Edit**

### 10.1 Workstream, Tag, Stage, RAG, Priority

Expected current workbook state:

| Dimension | Expected result |
|---|---:|
| `committed` stage | `21` workbook initiatives |
| `green` RAG | `21` workbook initiatives |
| `high` priority | `21` workbook initiatives |
| `automation` tag | `7` workbook initiatives |
| `commercial` tag | `10` workbook initiatives |
| `offshoring` tag | `4` workbook initiatives |

Current tenant note:

- The two non-workbook initiatives are `identified`, `green`, `medium`, and
  have blank tags.
- They affect dashboard summary counts and filters. They do not currently
  affect FY28 financial totals because they have no workbook financial values.

Recommended correction:

1. Archive or delete `TRN-007` and `TRN-008` if this tenant must be a clean
   workbook demo.
2. Keep them only if you need meeting-command-center test data visible in the
   same tenant.

### 10.2 Business Unit Links

For strict workbook matching, initiative BU links should match the BU column in
the table in section 9.

Current tenant issue:

- Several initiatives are linked to extra BUs beyond the workbook summary.
- This does not change workstream/tag FY28 financial totals.
- It does change BU filters and any BU-based dashboard or portfolio view.

Recommended BU link cleanup:

| Current issue | Correction |
|---|---|
| `TOR-1`, `TOR-2`, `TOR-3`, `TOR-4`, and `TOR-5` include `Group` as an extra BU. | Remove the extra `Group` link. |
| `NPK-1`, `NPK-2`, `NPK-3`, `NPK-4`, and `NPK-5` include `Group` as an extra BU. | Remove the extra `Group` link. |
| `EBR-1`, `EBR-2`, and `EBR-3` include `RDG` as an extra BU. | Remove the extra `RDG` link. |
| `SGT-1` and `SGT-2` include `VSC` as an extra BU. | Remove the extra `VSC` link. |
| `TOR-6` and `NPK-6` use `Group`. | Keep the group link, but rename the BU to `GROUP` for workbook matching. |

Validation:

- `/initiatives/pipeline` BU filters match the workbook.
- Filtering by `CAL`, `MER`, `FJD`, `BNT`, and `VSC` returns only the expected
  initiatives.
- Filtering by `GROUP` returns only `TOR-6` and `NPK-6`.

## 11. Configure Initiative Financial Scope

For each initiative:

1. Open `/initiatives/pipeline`.
2. Select the initiative.
3. Open **Financials**.
4. Select **Configure Scope** or open `/initiatives/:id/financial-scope`.
5. Enable these metrics:
   - Revenue Uplift
   - Gross Margin
   - Gross Margin Uplift
   - Gross Margin Uplift %
   - Baseline Revenue
6. Enable relevant cost categories:
   - Implementation / Project Cost
   - Technology / Tooling
   - External Consultants
   - Training / Change Management
   - Software Subscriptions
   - Software / Licenses
   - Support / Maintenance
   - Maintenance
   - Labor / Operations
   - Additional Headcount
   - Run-rate Operating Cost
   - Other One-off Cost
   - Other
7. Save scope.

For a clean demo, keep all workbook-required metrics enabled for every
initiative. Some initiatives have zero revenue or zero costs; those zeros are
valid and should not be treated as missing.

## 12. Enter Initiative Baselines

Screen:

- `/initiatives/pipeline`
- Open initiative
- Click **Edit**
- Use the **Annual Baseline** section

For each workbook initiative:

1. Set baseline year to `2025`.
2. Enter `Revenue FY25 Base` from section 9 into Baseline Revenue.
3. Enter `Gross Margin FY25 Base` only into a Finance-approved neutral
   margin/value baseline metric.
4. Do not enter workbook gross margin baseline as conventional accounting gross
   margin without Finance approval.
5. Save.
6. Return to the initiative **Financials** tab.
7. Confirm the Annual Baseline panel shows FY25 values.

Data-entry rules:

- Enter whole dollars, not USD millions.
- Preserve zero values.
- Do not enter baseline values for `TRN-007` or `TRN-008` if they remain in the
  tenant.

Portfolio validation:

| Baseline metric | Expected 21-initiative total |
|---|---:|
| Baseline Revenue | `67466000` |
| Baseline Margin / Value, if used | `87960000` |

Screen validation:

1. Open `/financials/initiative-portfolio`.
2. Set baseline year to `2025`.
3. Set value year to `2028`.
4. Confirm initiative baselines reconcile to the tenant baseline.

## 13. Validate Benefit Lines

Screen:

- `/initiatives/pipeline`
- Open initiative
- Tab: **Financials**

The workbook load creates three benefit lines per initiative:

| Benefit line | Metric key | Dashboard treatment |
|---|---|---|
| Revenue Uplift | `revenue_uplift` | Loaded and visible in financial views; not counted as dashboard matrix base benefit. |
| Gross Margin Uplift | `gm_uplift_pct` | Percentage/formula-style workbook line; skipped by dashboard dollar benefit rollup. |
| Gross Margin | `gross_margin` | Main Ishirock dashboard benefit value. |

Actions for each initiative:

1. Review the three benefit lines.
2. Submit each line to Finance.
3. Enter a short Finance comment:

```text
Workbook benefit reviewed against Initiative_Portfolio_Anonymised.xlsx.
```

4. Validate each submitted benefit line.
5. Enter validation comment:

```text
Validated for demo readiness; workbook source reviewed.
```

6. Set benefit risk rating to `medium` unless Finance wants a different
   risk-adjustment story.
7. Keep risk adjustment at `100` if dashboard values should equal workbook
   values.

Current tenant state:

| Benefit status area | Current state |
|---|---:|
| Benefit lines | `63` |
| Validation status | All `draft` |
| Risk rating | All `medium` |
| Handoff status | All `not_started` |

Validation:

- Open `/financials/benefits-register`.
- Set year to `2028`.
- Filter status to **Finance validated** after validation.
- Confirm all 63 workbook benefit lines appear when validation is complete.

## 14. Validate Cost Lines

Screen:

- `/initiatives/pipeline`
- Open initiative
- Tab: **Financials**
- Cost lines section

Workbook cost behavior:

- Plan and Actual lanes are loaded.
- Zero monthly values are skipped.
- Workbook money values are converted from USD millions to dollars.
- Current implementation imports one-off rows using fallback period data when a
  row has an amount and start month but no monthly values.

Expected FY28 workbook cost by workstream:

| Workstream | FY28 cost plan |
|---|---:|
| Eastbridge Region | `$0.805M` |
| Northpeak Region | `$0.971M` |
| Southgate Region | `$0.884M` |
| Westmark Region | `$0.900M` |
| **Total** | **`$3.560M`** |

Current tenant issue:

- `EBR-1` has duplicate imported grid cost rows.
- Current FY28 platform cost is `$3.626M`, which is `$0.066M` higher than the
  workbook.
- The duplicate rows are `Recurring Costs (Grid)` under `EBR-1`.
- The same duplicate grid family also includes a 2026 `One-off Costs (Grid)`
  duplicate.

Recommended correction:

1. Open `EBR-1`.
2. Open **Financials**.
3. In cost lines, locate rows named:
   - `Recurring Costs (Grid)`
   - `One-off Costs (Grid)`
4. Delete those `EBR-1` grid rows.
5. Keep the workbook source rows:
   - `Architecture / Solution Consulting`
   - `Implementation Cost`
   - `Licensing & Operation Cost`
6. Recheck `/dashboard` with target year `2028`.

Expected result after correction:

| Area | Current before correction | Expected after correction |
|---|---:|---:|
| EBR-1 FY28 cost | `$0.132M` | `$0.066M` |
| Eastbridge FY28 cost | `$0.871M` | `$0.805M` |
| Portfolio FY28 cost | `$3.626M` | `$3.560M` |
| Portfolio FY28 dashboard net | `$18.007M` | `$18.073M` |

Optional metric cleanup:

- `EBR-1` has two zero metric-value rows that a clean current parser would not
  load.
- They do not change dashboard totals.
- Leave them unless you need exact row-count parity with a fresh reload.

## 15. Validate KPIs, Milestones, Risks, And Status Updates

### 15.1 KPIs

Screens:

- Initiative detail, tab: **KPIs**
- `/dashboard` KPI pulse

Expected workbook-loaded data:

| Area | Expected |
|---|---:|
| KPIs | `83` |
| KPI entries | `313` |

Validation:

1. Open representative initiatives:
   - `TOR-1`
   - `EBR-1`
   - `NPK-1`
   - `SGT-1`
2. Confirm KPI definitions and entries are present.
3. Open `/dashboard`.
4. Confirm KPI pulse is populated.

### 15.2 Milestones

Screens:

- Initiative detail, tab: **Milestones**
- `/progress`

Expected workbook-loaded data:

| Area | Expected |
|---|---:|
| Milestones | `292` |

Validation:

1. Open `TOR-1`.
2. Confirm milestones and dates exist.
3. Open `/progress`.
4. Confirm milestone rollups are populated.

### 15.3 Risks

Screens:

- Initiative detail, tab: **Risks**
- `/dashboard` risk heatmap
- `/reports/control-tower`

Expected clean workbook data:

| Area | Expected |
|---|---:|
| Workbook initiative risks | `33` |

Current tenant state:

| Area | Current |
|---|---:|
| Total risks | `34` |

Reason:

- The extra risk belongs to a non-workbook `TRN-*` initiative.

Recommended correction:

1. Archive or delete non-workbook initiatives if this must be a clean workbook
   tenant.
2. Otherwise, explain that risk totals include one non-workbook test risk.

### 15.4 Status Updates

Screens:

- Initiative detail, tab: **Status**
- `/dashboard` recent activity

Expected workbook-loaded data:

| Area | Expected |
|---|---:|
| Status updates | `4` |

Validation:

1. Open `/dashboard`.
2. Confirm recent activity shows submitted status updates.
3. Open initiatives with updates and review narrative status.

## 16. Validate Benefits And Lock Bankable Plans

### 16.1 Submit And Validate Benefit Lines

For each initiative:

1. Open **Financials**.
2. Submit the three benefit lines.
3. Validate them as Finance.
4. Attach evidence where available.

For demo variety, you can leave a small number of lines in non-final states,
but do not do this if the goal is exact readiness.

Recommended complete readiness:

| Benefit-line status | Count |
|---|---:|
| Finance validated | `63` |

### 16.2 Approve Gates And Lock Plans

For each initiative:

1. Open the initiative.
2. Open **Governance**.
3. Submit and approve required gates through Gate 3.
4. Confirm the initiative reaches `committed`.
5. Open `/financials/bankable-plan`.
6. Select the initiative.
7. Confirm a locked plan version exists.

Current tenant state:

- Workbook initiatives already show stage `committed`.
- Post-remediation, all 21 workbook initiatives have approved Gate 3
  submissions and bankable plan version `1` locked from those approvals.
- If a tenant is reloaded from scratch and the UI requires approval history to
  create bankable plans, use the governance workflow instead of editing stage
  directly.

Recommended lock sequence:

| Scope | Initiatives |
|---|---|
| Minimum validation | `TOR-1`, `EBR-1`, `NPK-1`, `SGT-1` |
| Complete demo readiness | All 21 workbook initiatives |

## 17. Enter Benefit Tracking Actuals

Screen:

- `/financials/benefit-tracking`

The workbook actual financial lanes are blank or zero for the dashboard-ready
values reviewed in this guide. Do not invent actuals unless the demo explicitly
needs assumed actuals.

Recommended approach:

1. Leave actual financial values as workbook actuals unless Finance has evidence.
2. For UI testing, enter realization ledger rows for a small set of locked
   initiatives.
3. Clearly label any manually entered realization as demo evidence.

Example ledger rows for UI testing:

| Initiative | Period | Actual amount | Description |
|---|---|---:|---|
| `TOR-1` | 2028-01-01 to 2028-12-31 | `560000` | Demo realized benefit entry for FY28. |
| `EBR-1` | 2028-01-01 to 2028-12-31 | `616000` | Demo realized benefit entry for FY28. |
| `NPK-1` | 2028-01-01 to 2028-12-31 | `532000` | Demo realized benefit entry for FY28. |
| `SGT-1` | 2028-01-01 to 2028-12-31 | `588000` | Demo realized benefit entry for FY28. |

Validation:

- `/financials/benefit-tracking` shows locked plan, actual amount, and variance.
- Actual values are clearly marked as demo entries unless Finance has approved
  them as real actuals.

## 18. Lock Workstream Waterline Targets

Screen:

- `/financials/waterline`

Actions for each workstream:

1. Select the workstream:
   - Westmark Region
   - Eastbridge Region
   - Northpeak Region
   - Southgate Region
2. Set lock date after the relevant approval date.
3. Click **Preview**.
4. Review included initiatives and target value.
5. Click **Lock target**.

Expected FY28 net targets after EBR-1 duplicate-cost cleanup:

| Workstream | FY28 net target |
|---|---:|
| Westmark Region | `$4.880M` |
| Eastbridge Region | `$4.762M` |
| Northpeak Region | `$4.906M` |
| Southgate Region | `$3.525M` |
| **Total** | **`$18.073M`** |

Post-remediation locked waterline target values:

| Workstream | Locked target value |
|---|---:|
| Westmark Region | `$23.760M` |
| Eastbridge Region | `$22.863M` |
| Northpeak Region | `$22.200M` |
| Southgate Region | `$15.604M` |
| **Total** | **`$84.427M`** |

Important impact:

- The FY28 net target table above is the correct value to reconcile
  `/dashboard` and Initiative Portfolio against the workbook `Dashboards` sheet.
- The locked waterline target values are higher because the current platform
  lock implementation uses each initiative bankable snapshot
  `summary.net_value_plan`, which aggregates the stored plan run-rate basis
  instead of accepting a `target_year` such as FY28.
- For management demos focused on exact workbook dashboard matching, show the
  FY28 dashboard and Initiative Portfolio views.
- For waterline demos, explain that the lock currently represents the all-period
  bankable target basis. If the desired behavior is FY28-only waterline targets,
  create a product change to add a target-year parameter to waterline preview
  and lock snapshots.

Validation:

- Locked target history appears for each workstream.
- `/dashboard` FY28 plan values match the workbook dashboard when FY28 is
  selected.
- `/financials/benefit-tracking` and `/financials/waterline` agree after
  realization rows are entered.

## 19. Match The Platform Dashboard To The Workbook Dashboard

Workbook sheet:

- `Dashboards`

Platform screen:

- `/dashboard`

Controls:

1. Set target year to `FY28`.
2. Clear filters unless testing a specific workstream or tag.
3. Use all 21 workbook initiatives.
4. Exclude or archive non-workbook initiatives if they confuse summary counts.

### 19.1 Workbook Rows To Use

Use the `Dashboards` sheet section **In-year value of initiatives**:

| Workbook row | FY28 value |
|---|---:|
| Total Revenue | `$15.004M` |
| Total Gross Margin | `$21.633M` |
| Total Cost Plan | `$3.560M` |
| Total Net Value | `$18.073M` |

Use the first section, **Run rate value of completed initiatives**, only when
you are explaining cumulative planned completion value by date. The platform
main dashboard value matrix is a selected-year rollup, not that cumulative
date-series chart.

### 19.2 Current Platform Dashboard Reconciliation

Before data cleanup, the current tenant reconciles like this for FY28:

| Measure | Workbook FY28 | Current platform FY28 | Variance | Reason |
|---|---:|---:|---:|---|
| Revenue uplift | `$15.004M` | `$15.004M` | `$0.000M` | Loaded metric values match. |
| Dashboard benefit / gross margin | `$21.633M` | `$21.633M` | `$0.000M` | Loaded gross-margin values match. |
| Cost plan | `$3.560M` | `$3.626M` | `+$0.066M` | Duplicate `EBR-1` grid recurring cost rows. |
| Net value | `$18.073M` | `$18.007M` | `-$0.066M` | Cost duplicate reduces net value. |

After removing the duplicate `EBR-1` grid cost rows, FY28 should reconcile to:

| Measure | Expected platform FY28 |
|---|---:|
| Revenue uplift | `$15.004M` |
| Dashboard benefit / gross margin | `$21.633M` |
| Cost plan | `$3.560M` |
| Net value | `$18.073M` |

### 19.3 Workstream Reconciliation

Expected FY28 after cleanup:

| Workstream | Revenue | Gross margin | Cost plan | Net value |
|---|---:|---:|---:|---:|
| Eastbridge Region | `$3.764M` | `$5.567M` | `$0.805M` | `$4.762M` |
| Northpeak Region | `$3.678M` | `$5.877M` | `$0.971M` | `$4.906M` |
| Southgate Region | `$3.602M` | `$4.409M` | `$0.884M` | `$3.525M` |
| Westmark Region | `$3.960M` | `$5.780M` | `$0.900M` | `$4.880M` |
| **Total** | **`$15.004M`** | **`$21.633M`** | **`$3.560M`** | **`$18.073M`** |

### 19.4 Tag Reconciliation

Expected FY28 after cleanup:

| Tag | Initiatives | Revenue | Gross margin | Cost plan | Net value |
|---|---:|---:|---:|---:|---:|
| automation | `7` | `$0.000M` | `$5.256M` | `$0.541M` | `$4.715M` |
| commercial | `10` | `$15.004M` | `$9.030M` | `$2.624M` | `$6.406M` |
| offshoring | `4` | `$0.000M` | `$7.347M` | `$0.395M` | `$6.952M` |

### 19.5 What To Click In The Dashboard

1. Open `/dashboard`.
2. Set target year to `FY28`.
3. Confirm **Total Initiatives**:
   - `21` if non-workbook initiatives are removed.
   - `23` if `TRN-007` and `TRN-008` remain.
4. Confirm RAG:
   - Workbook initiatives: all green.
5. Confirm value bridge:
   - Benefits base should be `$21.633M`.
   - Costs plan should be `$3.560M` after cleanup.
   - Net base should be `$18.073M` after cleanup.
6. Open the workstream/tag matrix.
7. Click each populated cell and confirm contributing initiatives.
8. Compare row totals to section 19.3 and tag totals to section 19.4.

## 20. Validate Financial Reports

### 20.1 Financial Overview

Screen:

- `/financials`

Controls:

- Granularity: **Yearly**
- Year: `2028`
- Scenario: **Plan Base**

Expected:

| Measure | Expected FY28 |
|---|---:|
| Revenue uplift | `$15.004M` |
| Gross margin / benefit | `$21.633M` |
| Cost plan after cleanup | `$3.560M` |
| Net value after cleanup | `$18.073M` |
| Actuals | Zero or blank unless manually entered. |

### 20.2 Initiative Portfolio

Screen:

- `/financials/initiative-portfolio`

Controls:

- Baseline year: `2025`
- Value year: `2028`
- Scenario: `Plan Base`

Expected:

- 21 workbook initiatives appear.
- FY25 baseline columns populate after manual baseline entry.
- FY28 revenue, gross margin, cost, and net values match section 9.
- Baseline reconciliation shows tenant versus initiative totals.

### 20.3 Benefits Register

Screen:

- `/financials/benefits-register`

Controls:

- Year: `2028`
- Status: All, then Finance validated

Expected:

- 63 benefit lines after full workbook validation.
- Risk-adjusted plan equals plan if risk adjustment is 100%.
- Actual/realized values remain zero unless actuals or ledger rows are entered.

### 20.4 Bankable Plan

Screen:

- `/financials/bankable-plan`

Expected after gate approvals:

- Locked plan versions exist for approved initiatives.
- Plan values reflect workbook values.
- Rebaseline history is empty unless you intentionally create a rebaseline.

### 20.5 Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Expected after ledger entries:

- Portfolio, workstream, and initiative scopes show bankable plan, actual, and
  variance.
- Actual rows are traceable to evidence or demo labels.

### 20.6 Waterline

Screen:

- `/financials/waterline`

Expected after locks:

- Four workstream target locks exist.
- Locked target values match the platform bankable snapshot basis described in
  section 18.
- Locked target values do not match the FY28-only workbook dashboard values
  until the platform supports target-year waterline locks.

## 21. Impact And Remediation Review

Use this section to decide what to correct before a management demo.

| Issue | Impact | Recommended action | Required for exact FY28 dashboard match |
|---|---|---|---|
| Resolved: two non-workbook initiatives, `TRN-007` and `TRN-008`. | Dashboard initiative count showed `23` instead of workbook `21`; blank tag appeared. | Archived during issue `#335`; keep archived for clean workbook demos. | No for financial totals, yes for count/filter cleanliness. |
| Resolved: extra business unit `Southeast Asia`. | Admin and filters included a non-workbook BU. | Removed during issue `#335`. | No for FY28 financial totals. |
| Resolved: `Group` named differently from workbook `GROUP`. | BU filter label did not match workbook. | Renamed to `GROUP` during issue `#335`. | No for FY28 workstream/tag totals; yes for BU-level matching. |
| Resolved: extra BU links on multiple initiatives. | BU filters did not match the workbook BU column. | Extra links removed during issue `#335`. | No for workstream/tag totals; yes for BU-level matching. |
| Inactive UI acceptance cost categories. | Admin configuration clutter. | Delete/archive inactive test categories if demo users will inspect Admin. | No. |
| Resolved: duplicate `EBR-1` grid cost rows. | FY28 dashboard cost was `$3.626M` instead of `$3.560M`; net was `$18.007M` instead of `$18.073M`. | Duplicate `EBR-1` `Recurring Costs (Grid)` and `One-off Costs (Grid)` rows removed during issue `#335`. | Yes. |
| Two extra zero metric rows on `EBR-1`. | Row count is `4,696` instead of clean parser `4,694`; totals are unchanged. | Leave or clean through reload/database maintenance. | No. |
| Resolved: no tenant or initiative annual baselines. | Initiative Portfolio could not reconcile FY25 baseline. | FY25 tenant and initiative baselines entered during issue `#335`. | Required for baseline reports, not for FY28 dashboard value. |
| Resolved: no bankable plans. | Bankable Plan and Benefit Tracking could not show locked plan. | Gate 3 approvals and plan locks created during issue `#335`. | Required for bankable/realization demo, not for raw dashboard values. |
| No realization ledger rows. | Benefit Tracking actuals remain blank/zero. | Enter approved or explicitly labeled demo actuals. | No for workbook plan match; yes for actuals demo. |
| Waterline locks use all-period bankable plan value, not FY28-only dashboard value. | `/financials/waterline` locked totals show `$84.427M`, while FY28 workbook dashboard net is `$18.073M`. | For the current demo, use FY28 dashboard and Initiative Portfolio for workbook matching; create a product change if waterline must lock by target year. | No for `/dashboard`; yes if the demo claims waterline equals FY28 dashboard. |
| FY26 platform dashboard subtracts one-off imported cost lines. | FY26 `/dashboard` net will not match workbook `Dashboards` annual net unless one-off costs are excluded. | Use FY28 for exact dashboard match, or decide whether one-off investment should be excluded from dashboard cost treatment. | Not relevant if demo focuses on FY28. |

## 22. Recommended Demo Script

Use this sequence after the corrections in section 21 are complete.

1. Open `/dashboard`.
2. Set target year to `FY28`.
3. State the portfolio headline:

```text
Ishirock has 21 workbook initiatives across four regional workstreams with
$21.633M of FY28 gross-margin benefit, $3.560M of FY28 cost plan, and
$18.073M of FY28 net value.
```

4. Show the workstream/tag value matrix.
5. Click the Eastbridge automation cell and show `EBR-1` and `EBR-5`.
6. Explain that `EBR-1` duplicate cost rows were removed so Eastbridge reconciles
   to the workbook.
7. Open `/financials`.
8. Show FY28 yearly Plan Base values.
9. Open `/financials/initiative-portfolio`.
10. Show FY25 baseline year and FY28 value year.
11. Open `TOR-1`.
12. Review Overview, Financials, KPIs, Milestones, Risks, and Status.
13. Open `/financials/benefits-register`.
14. Show Finance validation state.
15. Open `/financials/bankable-plan`.
16. Show locked plan status for the sample initiatives.
17. Open `/financials/benefit-tracking`.
18. Show plan versus actual only if ledger rows have been intentionally entered.

## 23. Validation Checklist

Before calling Ishirock demo-ready:

| Check | Expected |
|---|---|
| Workbook initiatives | 21 present, no duplicates. |
| Non-workbook initiatives | Removed/archived, or explicitly explained. |
| Workstreams | Westmark, Eastbridge, Northpeak, Southgate. |
| Business units | BNT, CAL, FJD, GROUP, KLP, MER, RDG, VER, VSC. |
| Tags | automation, commercial, offshoring. |
| Financial scenarios | baseline, plan_base, plan_high, actual. |
| Metrics | Required workbook metrics active. |
| Tenant FY25 baseline | Revenue, margin/value, cost, and net entered from the workbook. |
| Initiative FY25 baselines | Entered for all 21 workbook initiatives. |
| Benefit lines | 63 reviewed and Finance validated for full readiness. |
| EBR-1 duplicate cost rows | Removed for exact FY28 dashboard match. |
| Dashboard FY28 gross margin | `$21.633M`. |
| Dashboard FY28 cost plan | `$3.560M` after cleanup. |
| Dashboard FY28 net value | `$18.073M` after cleanup. |
| Bankable plans | Locked for all 21 workbook initiatives. |
| Benefit ledger | Actuals entered only if explicitly approved or labeled as demo. |
| Workstream target locks | Four locks exist; total locked target basis is `$84.427M`. |

## 24. Notes On Implementation Behavior

The following implementation details explain why the UI behaves the way it does:

- `portfolio_workbook.py` imports workbook money values as USD millions and
  stores dollars in the platform.
- Zero monthly benefit and cost values are skipped by the workbook parser.
- Benefit lines are de-duplicated by source line/name/metric, which produces
  three benefit lines per initiative from the workbook lanes.
- Cost rows are loaded only for workbook `Plan` and `Actual` lanes.
- One-off cost rows can be loaded through fallback start-year/start-month logic
  even when annual workbook dashboard rows do not include them in net value.
- The loader does not create tenant annual baselines, initiative annual
  baselines, bankable plans, benefit realization ledger rows, workstream target
  locks, or meetings.
- `/dashboard` reads active configurable metric values and scenarios. For
  Ishirock, non-revenue active benefit metrics roll into dashboard benefit/base
  value, while costs are subtracted from net.
- `/dashboard` chooses the maximum available year if no target year is selected.
  Select `FY28` explicitly when matching the workbook dashboard.
- `/financials/waterline` target locks use current bankable plan snapshot
  `summary.net_value_plan` and do not currently take a `target_year` parameter.
  For Ishirock, this means waterline locks represent the all-period bankable
  target basis rather than the FY28-only workbook dashboard value.
