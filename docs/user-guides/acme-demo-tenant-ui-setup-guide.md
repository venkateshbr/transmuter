# Transformation Tenant UI Setup Guide With ACME Example

Last updated: 2026-06-22

This guide explains how a normal tenant user can create a blank tenant and
configure a transformation office through the Transmuter UI. ACME is used as a
complete worked example, but the same sequence should be used for any customer
or internal transformation program.

Use the ACME values as reference data, not as required tenant data. For a real
tenant, replace ACME's business units, workstreams, initiatives, financial
baselines, benefits, costs, owners, risks, KPIs, shared costs, and dashboard
choices with the tenant's own transformation model.

For Transmuter demo environments, ACME4 is the canonical full demo state in dev
because it was created through the current signup flow, uses the current
financial engine, and includes Shared Costs allocation, benefit ledger rows,
milestones, KPIs, risks, dependencies, locked bankable plans, and governed
rebaseline history. ACME3 remains the legacy reference tenant for the original
`ENT-*` initiative-code sequence.

No credentials are included in this guide.

## 1. Setup Outcome

After completing this guide, the tenant should have a usable transformation
office that can demonstrate:

- Tenant onboarding and first-run setup.
- Master data: business units, workstreams, markets, themes, and tags.
- Financial configuration: scenarios, metrics, baselines, cost categories, value
  bridge rows, and fiscal settings.
- Governance stage gates and gate criteria.
- Initiatives with owners, dimensions, financial scope, baselines, benefits,
  costs, KPIs, risks, milestones, dependencies, and bankable plan locks.
- Benefit validation, benefit tracking, realization ledger, and plan-vs-actual
  variance.
- Shared Costs pools, allocation policies, previews, locked runs, and reporting
  treatment.
- Dashboards and reports: Executive Dashboard, Pipeline, Initiative Matrix,
  Financial Overview, Initiative Portfolio, Bankable Plan, Benefits Register,
  Benefit Tracking, Waterline, Shared Costs, Progress, Governance, PMO KPIs,
  PMO Risks, and Executive Control Tower.

This guide intentionally skips Meeting setup.

ACME example totals:

| Area | Expected result |
|---|---:|
| FY26 annual revenue baseline | `$20.00M` |
| FY26 annual gross margin baseline | `$9.00M` |
| FY28 revenue uplift | `$4.00M` |
| FY28 gross margin uplift | `$5.40M` |
| FY28 cost savings | `$3.75M` |
| FY28 recurring run cost | `$0.80M` |
| FY28 EBITDA-effective net run-rate | `$8.35M` |
| FY28 one-off investment | `$2.50M` |
| FY28 shared-cost plan | `$1.45M` |
| FY28 shared-cost actual | `$1.305M` |

EBITDA-effective net run-rate formula:

```text
Gross Margin Uplift + Cost Savings - Recurring Costs
= $5.40M + $3.75M - $0.80M
= $8.35M
```

For your own tenant, keep this formula only if the tenant's value basis matches
the standard transformation value pattern:

```text
EBITDA-effective net run-rate
= margin uplift + cost savings - recurring run costs
```

Use one-off investment for funding and payback-period analysis, not as recurring
EBITDA drag.

### 1.1 How To Use This Guide For A Non-ACME Tenant

Before entering data, define the tenant's own transformation model:

| Setup area | Tenant-specific decision | ACME example |
|---|---|---|
| Organization | Company or business unit running the program. | Acme Global Manufacturing 4 |
| Baseline year | Last stable year used for revenue, margin, cost, or operating baseline. | FY2026 |
| Target year | Year used for board run-rate value. | FY2028 |
| Business units | Management or reporting units that own value. | Corporate, Commercial, Operations, Shared Services, Technology |
| Workstreams | Transformation programs or delivery lanes. | Automation, Commercial Growth, ERP & Data Platform, Offshoring, Procurement |
| Value metrics | The measures that prove benefit. | Revenue Uplift, Gross Margin Uplift, Cost Savings |
| Cost model | One-off investment and recurring run-cost categories. | Implementation, technology/tooling, training, software, labor |
| Governance | Gates and criteria used to make value bankable. | Five-gate identify-to-realize lifecycle |
| Dashboards | Which dashboards the tenant needs in its menu. | Full demo menu enabled |

Use ACME tables in later sections as examples of scale, sequencing, and data
shape. A tenant with 6 initiatives should create 6 initiatives; a tenant with 30
initiatives should create 30. The key requirement is that baselines, benefits,
costs, owners, and governance decisions reconcile for that tenant.

### 1.2 Tenant Setup Worksheet

Capture this information before starting UI entry:

| Question | Tenant answer |
|---|---|
| What is the transformation office name and purpose? |  |
| Which baseline year and target value year will leadership use? |  |
| Which business units own the value? |  |
| Which workstreams organize delivery? |  |
| Which value levers matter: revenue, margin, savings, avoidance, working capital, service quality, risk reduction? |  |
| Which metrics should become financial metrics versus operational KPIs? |  |
| Which cost categories are one-off investment and which are recurring? |  |
| Who can submit, validate, approve, and rebaseline value cases? |  |
| Which dashboards should be visible for this tenant? |  |
| Which initiatives need shared-cost allocation rather than direct initiative cost lines? |  |

## 2. Create The Tenant

Use the public app URL for the target environment:

```text
https://transmuter.ishirock.tech
```

For dev validation, use:

```text
https://transmuter-dev.ishirock.tech
```

### 2.1 Signup

1. Open the public app URL.
2. Select **Get Started**.
3. Create the tenant using the customer's organization name and slug. For ACME
   demo tenants, use one of these names:

| Tenant | Organization name | Suggested slug |
|---|---|---|
| ACME | Acme Global Manufacturing | `acme-transformation-lab` |
| ACME2 | Acme Global Manufacturing 2 | `acme2-transformation-lab` |
| ACME3 | Acme Global Manufacturing 3 | `acme3-transformation-lab` |
| ACME4 | Acme Global Manufacturing 4 | `acme4-transformation-lab` |

4. Enter the initial administrator name and email.
5. Enter planned users, for example `12`.
6. Complete the subscription checkout flow for the environment.
7. Return to Transmuter and sign in as the initial administrator.

New tenants should start without business units, workstreams, initiatives, stage
gates, or gate criteria. The platform does bootstrap default financial engine
configuration and default dashboard configuration:

- Financial engine defaults: scenarios, metric definitions, cost categories,
  value bridge rows, and reporting settings.
- Dashboard defaults: Executive Dashboard, Financial Overview, and Initiative
  Portfolio are enabled. Other dashboards are enabled from Admin > Dashboard
  Configuration when a demo tenant needs the full menu.

Current platform-created tenants generate initiative codes such as `TRN-001`
through `TRN-010`. The guide tables still use the historical `ENT-001` through
`ENT-010` scenario sequence. For ACME4, use the same row order and map:

| Historical guide code | ACME4 generated code |
|---|---|
| `ENT-001` | `TRN-001` |
| `ENT-002` | `TRN-002` |
| `ENT-003` | `TRN-003` |
| `ENT-004` | `TRN-004` |
| `ENT-005` | `TRN-005` |
| `ENT-006` | `TRN-006` |
| `ENT-007` | `TRN-007` |
| `ENT-008` | `TRN-008` |
| `ENT-009` | `TRN-009` |
| `ENT-010` | `TRN-010` |

### 2.2 First Login

1. Open `/dashboard`.
2. Confirm the tenant has no portfolio data yet.
3. Open `/admin`.
4. Review **First-run setup**.
5. Keep `/admin` open for the setup steps below.

The setup checklist should move toward complete as master data, financial
configuration, governance, and users are configured.

## 3. Configure Master Data

Screen:

- `/admin`
- Tab: **Strategic Parameters**

### 3.1 Business Units

Create business units that match the tenant's management accountability model.
For ACME, create these business units:

| Business unit | Purpose |
|---|---|
| Corporate | PMO, enterprise value office, governance. |
| Commercial | Revenue growth, pricing, sales coverage, onboarding. |
| Operations | Procurement and supply chain. |
| Shared Services | Finance, HR, back-office operations. |
| Technology | Data platform, AI, ERP, service desk. |

### 3.2 Workstreams

Create workstreams that match the tenant's transformation program structure.
For ACME, create these workstreams:

| Workstream | Primary focus |
|---|---|
| Automation | Process automation and service productivity. |
| Commercial Growth | Pricing, sales coverage, customer growth. |
| ERP & Data Platform | Enterprise data, ERP, integration, analytics. |
| Offshoring & Operating Model | Shared services and delivery model change. |
| Procurement & Supply Chain | Vendor consolidation and supply-chain control. |

### 3.3 Market, Theme, Tags

Create markets, themes, and tags that match how the tenant wants to filter
portfolio value. For ACME, create:

| Type | Values |
|---|---|
| Market | United States |
| Theme | Enterprise gross margin and growth transformation |
| Tags | `automation`, `commercial`, `offshoring`, `other` |

Save each section before moving on.

## 4. Configure Users

Screens:

- `/people`
- `/admin`, tab: **Access Control**

Minimum demo users:

| User type | Role |
|---|---|
| Transformation office lead | `transformation_office` |
| Initiative owner | `initiative_owner` |
| Executive viewer | `viewer` |

Steps:

1. Open **People**.
2. Invite or create the transformation office user.
3. Invite or create at least one initiative owner.
4. Invite or create at least one viewer.
5. Open **Admin > Access Control**.
6. Confirm each user has the intended role.

For a simple demo, the initial administrator can own all initiatives. Add
separate users only when you want to demonstrate role-based visibility.

## 5. Configure Financial Engine

Screen:

- `/admin`
- Tab: **Financial Configuration**

New tenants include the standard financial engine rows by default. Use this
section to confirm the defaults, adjust labels or formulas if needed, and enter
the tenant's baseline values. Do not recreate duplicate rows if the default rows
already exist.

### 5.1 Reporting Settings

Set:

| Setting | Value |
|---|---|
| Reporting currency | `USD` |
| Fiscal year start | `January` |

Save settings.

### 5.2 Scenarios

Create or confirm the active scenarios the tenant needs. ACME uses:

| Key | Label | Kind | Primary |
|---|---|---|---|
| `baseline` | Baseline | Baseline | No |
| `plan_base` | Plan Base | Plan | Yes |
| `plan_high` | Plan High | Plan | No |
| `actual` | Actual | Actual | No |

Use **Plan Base** as the primary board plan.

### 5.3 Metric Definitions

Create metric definitions that match the tenant's value story. ACME uses a
revenue, gross margin, and savings model:

| Key | Label | Type | Aggregation | Benefit class | Formula |
|---|---|---|---|---|---|
| `annual_revenue_baseline` | Annual Revenue Baseline | Currency | Last | None |  |
| `annual_gross_margin_baseline` | Annual Gross Margin Baseline | Currency | Last | None |  |
| `revenue_uplift` | Revenue Uplift | Currency | Sum | Revenue |  |
| `gm_uplift` | Gross Margin Uplift | Currency | Sum | Margin |  |
| `cost_savings` | Cost Savings | Currency | Sum | Savings |  |
| `target_revenue` | Target Revenue | Currency | Formula | None | `baseline_annual_revenue_baseline + revenue_uplift` |
| `target_gross_margin` | Target Gross Margin | Currency | Formula | None | `baseline_annual_gross_margin_baseline + gm_uplift` |
| `revenue_growth_pct` | Revenue Growth % | Percent | Formula | None | `revenue_uplift / baseline_annual_revenue_baseline * 100` |
| `gross_margin_run_rate_pct` | Gross Margin Run-rate % | Percent | Formula | None | `target_gross_margin / target_revenue * 100` |
| `gm_improvement_pct` | Gross Margin Improvement % | Percent | Formula | None | `gm_uplift / baseline_annual_gross_margin_baseline * 100` |

Use precision `4` for money and percent metrics where the UI asks for
precision.

### 5.4 Tenant Annual Baselines

In **Annual Baselines**, enter the tenant's approved starting baseline. ACME
uses:

| Metric | Baseline year | Value |
|---|---:|---:|
| Annual Revenue Baseline | 2026 | `20000000` |
| Annual Gross Margin Baseline | 2026 | `9000000` |

This sets ACME's starting point at `$20.0M` revenue and `$9.0M` gross margin.
For another tenant, replace both the baseline year and values with the tenant's
approved source baseline.

### 5.5 Cost Categories

Create cost categories that separate one-off investment from recurring costs.
ACME uses:

| Key | Label | Group | Rollup |
|---|---|---|---|
| `implementation` | Implementation / Project Cost | Implementation | One-off |
| `technology_tooling` | Technology / Tooling | Implementation | One-off |
| `external_consultants` | External Consultants | Implementation | One-off |
| `training_change` | Training / Change Management | Implementation | One-off |
| `software` | Software / Licenses | Operating | Recurring |
| `maintenance` | Support / Maintenance | Operating | Recurring |
| `labor` | People Support | Operating | Recurring |
| `other` | Other | Uncategorized | None |

### 5.6 Value Bridge Rows

Create value bridge rows that match how leadership wants benefits and costs to
reconcile. ACME uses these rows in order:

| Key | Label | Row kind | Sign | Inputs |
|---|---|---|---:|---|
| `revenue` | Revenue Uplift | Metric set | `+` | Revenue Uplift |
| `margin` | Gross Margin Uplift | Metric set | `+` | Gross Margin Uplift |
| `savings` | Cost Savings | Metric set | `+` | Cost Savings |
| `recurring_costs` | Recurring Costs | Cost set | `-` | Software / Licenses, Support / Maintenance, People Support |
| `one_off_costs` | One-off Costs | Cost set | `-` | Implementation / Project Cost, Technology / Tooling, External Consultants, Training / Change Management |
| `net_value` | Net Value | Net | `+` | Calculated net row |

Use this bridge to explain why ACME FY28 run-rate value is `$8.35M`. For another
tenant, the same row pattern can be reused with different metric inputs and
different totals.

## 6. Configure Governance

Screen:

- `/admin`
- Tab: **Governance Engine**

### 6.1 Stage Gates

Create gates that match the tenant's approval lifecycle. ACME uses five gates:

| Gate | Key | Label | From stage | To stage | Approval |
|---:|---|---|---|---|---|
| 1 | `g1_identify_validate` | Gate 1: Identify to Validate | identified | validated | Required |
| 2 | `g2_validate_plan` | Gate 2: Validate to Plan | validated | planned | Required |
| 3 | `g3_plan_commit` | Gate 3: Plan to Commit | planned | committed | Required |
| 4 | `g4_commit_execute` | Gate 4: Commit to Execute | committed | executing | Required |
| 5 | `g5_execute_realize` | Gate 5: Execute to Realized | executing | realized | Required |

Set approver role to `transformation_office`. Enable **Require all criteria**
where the UI offers it.

### 6.2 Gate Criteria

Create criteria that make the tenant's value cases auditable. ACME uses:

| Gate | Criterion | Guidance |
|---:|---|---|
| 1 | Strategic fit confirmed | Initiative supports the enterprise transformation thesis and target operating model. |
| 1 | Value hypothesis documented | Initial benefit type, value driver, and owner are documented. |
| 2 | Baseline approved | FY26 baseline allocation and measurement method are agreed. |
| 2 | Benefit assumptions documented | Revenue, margin, savings, cost, and timing assumptions are captured. |
| 2 | Finance validation completed | Finance has validated the benefit logic before bankable plan lock. |
| 3 | Delivery plan approved | Milestones, dependencies, budget, and owner accountability are approved. |
| 3 | Owner and sponsor assigned | Business owner, sponsor, and transformation office owner are assigned. |
| 4 | Implementation evidence submitted | Execution evidence confirms the initiative is live or materially complete. |
| 4 | Actuals collection started | Benefit realization actuals are being captured in the ledger. |
| 5 | Benefits realized and accepted | Realized value is accepted by the transformation office and business owner. |

## 6.3 Configure Demo Dashboards

Screen:

- `/admin`
- Tab: **Dashboard Configuration**

Enable the dashboards this tenant needs. For a full ACME demo tenant, enable:

- Executive Dashboard
- Financial Overview
- Initiative Portfolio
- Investments & Payback
- Bankable Plan
- Benefits Register
- Benefit Tracking
- Waterline
- Executive Control Tower
- Shared Costs

New tenants intentionally start with only the three starter dashboards enabled.
This setup step makes the chosen tenant menu visible. Do not enable dashboards
that the tenant will not maintain with real data.

## 7. Create Initiatives

Screen:

- `/initiatives/new`

Create the tenant's actual initiatives. Use **Create with Transmuter** and enter
the tenant's own names, owners, dimensions, stages, dates, and value logic. ACME
uses ten initiatives as a complete example:

| Code | Name | BU | Workstream | Tag | Type | Priority | RAG | Stage |
|---|---|---|---|---|---|---|---|---|
| ENT-001 | Transformation PMO & Benefits Office | Corporate | Automation | other | Capability Building | Medium | Green | Executing |
| ENT-002 | Finance Process Automation | Shared Services | Automation | automation | Cost Reduction | Medium | Green | Executing |
| ENT-003 | Customer Onboarding Automation | Commercial | Automation | automation | Revenue Growth | Medium | Green | Executing |
| ENT-004 | Back-office Finance & HR Offshoring | Shared Services | Offshoring & Operating Model | offshoring | Cost Reduction | High | Green | Executing |
| ENT-005 | Enterprise Data Platform | Technology | ERP & Data Platform | automation | Capability Building | Medium | Amber | Executing |
| ENT-006 | Pricing & Discount Optimization | Commercial | Commercial Growth | commercial | Revenue Growth | High | Green | Executing |
| ENT-007 | Sales Coverage Expansion | Commercial | Commercial Growth | commercial | Revenue Growth | High | Green | Executing |
| ENT-008 | Procurement Vendor Consolidation | Operations | Procurement & Supply Chain | offshoring | Cost Reduction | Medium | Green | Executing |
| ENT-009 | Supply Chain Control Tower | Operations | Procurement & Supply Chain | automation | Cost Avoidance | Medium | Amber | Executing |
| ENT-010 | AI Service Desk Automation | Technology | Automation | automation | Cost Reduction | Medium | Green | Executing |

For ACME, use these common fields:

| Field | Value |
|---|---|
| Market | United States |
| Theme | Enterprise gross margin and growth transformation |
| Impact type | Recurring |
| Planned start | 2027-01-01 |
| Planned end | 2028-12-31 |
| Summary | Two-year enterprise initiative contributing to FY28 revenue growth, gross margin expansion, and bankable run-rate value. |
| Value logic | Measured against FY26 annual baseline metrics with plan-only bankable value. |
| Dependencies text | Dependent on enterprise data readiness, BU sponsorship, and change adoption. |

For another tenant, use the actual initiative owner and accountable sponsor. If
the program is still being prepared, the transformation office lead can own the
first pass and reassign individual owners later.

## 8. Configure Initiative Financial Scope

For each initiative:

1. Open `/initiatives/pipeline`.
2. Select the initiative.
3. Open **Financials**.
4. Select **Configure Scope** or open `/initiatives/:id/financial-scope`.
5. Enable these metrics:
   - Annual Revenue Baseline
   - Annual Gross Margin Baseline
   - Revenue Uplift
   - Gross Margin Uplift
   - Cost Savings
   - formula rows used by your demo
6. Enable these cost categories:
   - Implementation / Project Cost
   - Technology / Tooling
   - External Consultants
   - Training / Change Management
   - Software / Licenses
   - Support / Maintenance
   - People Support
7. Save scope.

For a tenant setup, enable only the metrics and cost categories that apply to the
initiative. For ACME, all metrics and categories can stay enabled for every
initiative so the demo remains consistent even when some values are zero.

## 9. Enter Initiative Baselines And Benefits

### 9.1 Annual Initiative Data

Use the tenant's approved baseline and target-year board case for each
initiative. The ACME example uses each initiative's FY26 baseline and FY28 board
case:

| Code | FY26 revenue baseline | FY26 GM baseline | FY28 revenue uplift | FY28 GM uplift | FY28 savings | FY28 recurring cost | One-off investment |
|---|---:|---:|---:|---:|---:|---:|---:|
| ENT-001 | `500000` | `225000` | `0` | `100000` | `0` | `125000` | `250000` |
| ENT-002 | `1600000` | `720000` | `0` | `450000` | `650000` | `75000` | `300000` |
| ENT-003 | `2200000` | `990000` | `700000` | `500000` | `150000` | `55000` | `280000` |
| ENT-004 | `2000000` | `900000` | `0` | `800000` | `1000000` | `100000` | `220000` |
| ENT-005 | `1200000` | `540000` | `450000` | `400000` | `200000` | `150000` | `500000` |
| ENT-006 | `3000000` | `1350000` | `1100000` | `1050000` | `0` | `50000` | `250000` |
| ENT-007 | `3400000` | `1530000` | `950000` | `650000` | `0` | `70000` | `200000` |
| ENT-008 | `2300000` | `1035000` | `0` | `550000` | `800000` | `40000` | `200000` |
| ENT-009 | `2400000` | `1080000` | `300000` | `450000` | `450000` | `65000` | `180000` |
| ENT-010 | `1400000` | `630000` | `500000` | `450000` | `500000` | `70000` | `120000` |

### 9.2 Baseline Entry

For each initiative:

1. Open the initiative.
2. Open **Financials** or **Edit Initiative**, depending on where the UI exposes
   annual baseline.
3. Set baseline year to `2026`.
4. Enter Annual Revenue Baseline.
5. Enter Annual Gross Margin Baseline.
6. Save.

The ten initiative baselines should total `$20.00M` revenue and `$9.00M` gross
margin.

### 9.3 Benefit Lines

For each initiative, create benefit lines for the metrics that apply. ACME uses
three named benefit lines where relevant:

| Metric | Benefit line name |
|---|---|
| Revenue Uplift | `<initiative code> revenue uplift` |
| Gross Margin Uplift | `<initiative code> gross margin uplift` |
| Cost Savings | `<initiative code> cost savings` |

For ACME, use these settings:

| Field | Value |
|---|---|
| Impact type | Recurring |
| Timing | FY27-FY28 ramp to run-rate |
| Confidence | `80` for revenue, `85` for margin and savings |
| Evidence label | ACME assumption pack |
| Realization owner | Transformation office lead |
| Handoff due date | 2028-03-31 |

For benefit values, use **Spread** when available:

| Year | Scenario | Amount to spread |
|---|---|---|
| 2027 | Plan Base | Use the 2027 plan values in section 9.4. |
| 2028 | Plan Base | Use the FY28 values in section 9.1. |
| 2027 | Plan High | Revenue x 1.15, GM x 1.12, savings x 1.10. |
| 2028 | Plan High | Revenue x 1.12, GM x 1.10, savings x 1.08. |
| 2027 | Actual | Revenue x 0.88, GM x 0.86, savings x 0.82. |
| 2028 | Actual | Revenue x 0.92, GM x 0.90, savings x 0.88. |

If the UI requires monthly entry, divide the annual amount by 12 and enter the
same value for January through December.

### 9.4 FY27 Ramp Values

For ACME, enter these Plan Base FY27 values before using the multipliers above.
For another tenant, replace these with the tenant's ramp-year forecast:

| Code | 2027 revenue uplift | 2027 GM uplift | 2027 savings |
|---|---:|---:|---:|
| ENT-001 | `0` | `50000` | `0` |
| ENT-002 | `0` | `225000` | `300000` |
| ENT-003 | `400000` | `260000` | `100000` |
| ENT-004 | `0` | `400000` | `550000` |
| ENT-005 | `200000` | `180000` | `100000` |
| ENT-006 | `700000` | `520000` | `0` |
| ENT-007 | `500000` | `300000` | `0` |
| ENT-008 | `0` | `280000` | `450000` |
| ENT-009 | `100000` | `200000` | `250000` |
| ENT-010 | `100000` | `205000` | `250000` |

## 10. Enter Cost Lines

For each initiative, add the tenant's one-off and recurring cost lines on the
**Financials** tab. ACME uses the allocation pattern below.

### 10.1 One-Off Costs

Create one-off cost lines in FY2027:

| Category | Formula |
|---|---:|
| Implementation / Project Cost | One-off investment x 45% |
| Technology / Tooling | One-off investment x 35% |
| Training / Change Management | One-off investment x 20% |

Set actual amount to plan x 95% if the UI asks for actual cost.

### 10.2 Recurring Costs

Create recurring cost lines for FY2027 and FY2028:

| Category | Formula |
|---|---:|
| Software / Licenses | FY28 recurring cost x 40% |
| Support / Maintenance | FY28 recurring cost x 35% |
| People Support | FY28 recurring cost x 25% |

For FY2027, multiply each recurring amount by 50%. For FY2028, use 100%.
Set actual amount to plan x 97% if the UI asks for actual cost.

Validation totals:

| Measure | Expected plan |
|---|---:|
| FY27 recurring costs | `$0.40M` |
| FY28 recurring costs | `$0.80M` |
| FY27 one-off costs | `$2.50M` |

## 11. Configure Milestones, KPIs, Risks, And Dependencies

### 11.1 Milestones

For each initiative, open **Milestones** and create milestones that prove
delivery progress. ACME uses:

| Milestone | Planned start | Planned end | Status |
|---|---|---|---|
| Gate 2 baseline and business case confirmed | 2027-01-01 | 2027-03-31 | Complete |
| FY28 run-rate benefits activated | 2028-01-01 | 2028-12-15 | In Progress |

### 11.2 KPIs

For each initiative, open **KPIs** and create two or three KPIs that prove the
operational driver behind the benefit. ACME examples:

| Initiative type | Suggested KPIs |
|---|---|
| Revenue Growth | Revenue uplift, gross margin uplift, conversion rate, discount leakage. |
| Cost Reduction | Cost savings, cycle time reduction, automation coverage, productivity hours. |
| Capability Building | Platform adoption, data quality, reporting cycle time, service availability. |
| Cost Avoidance | Avoided spend, risk event reduction, supply-chain visibility, exception cycle time. |

Use:

- Cadence: Monthly or Quarterly.
- Unit: Currency, Percent, Count, Days, or Hours.
- Target: align to the initiative benefit logic.
- Latest actual: enough to show green/amber/red KPI status.

### 11.3 Risks

For each initiative, open **Risks** and create at least two risks that could
affect delivery or realization. ACME examples:

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Data readiness risk | High | Medium | Confirm source-system quality and owner signoff before Gate 4. |
| Adoption/change risk | Medium | Medium | Add change champions, training, and weekly adoption tracking. |
| Finance validation risk | High | Low | Attach source evidence and review benefit assumptions with Finance. |

Set ENT-005 and ENT-009 to amber or higher attention so dashboards have risk
signals to show.

### 11.4 Dependencies

Open **Dependencies** on the initiative detail page where available. For a real
tenant, model the dependencies that leadership must manage. ACME uses:

| Upstream | Downstream | Type | Status | Severity | Due date | Notes |
|---|---|---|---|---|---|---|
| ENT-004 | ENT-005 | Blocks | Blocking | High | 2028-03-31 | ERP process standardization must stabilize before procurement wave 2 cutover. |
| ENT-006 | ENT-002 | Requires decision | At Risk | High | 2028-02-28 | Enterprise data model decision gates the revenue analytics rollout. |
| ENT-010 | ENT-008 | Enables | Active | Medium | 2028-04-15 | Collaboration tooling adoption enables the shared services productivity case. |

Dependencies feed the Control Tower risk and attention views.

## 12. Validate Benefits And Lock Bankable Plans

### 12.1 Submit And Validate Benefit Lines

For each initiative:

1. Open **Financials**.
2. In the benefit line section, submit each benefit line to Finance.
3. Validate most lines as Finance.
4. For a live tenant, use the real validation status. For an ACME demo, leave a
   few lines in different statuses to demonstrate the Benefits Register:

| Example | Status |
|---|---|
| ENT-005 Revenue Uplift | Submitted |
| ENT-008 Revenue Uplift | Submitted |
| ENT-009 Cost Savings | Rejected pending updated vendor baseline evidence |
| ENT-010 Revenue Uplift | Draft |
| All other lines | Finance Validated |

### 12.2 Approve Gate 2 And Lock Plans

For each initiative:

1. Open the initiative.
2. Open **Governance**.
3. Select **Gate 2: Validate to Plan**.
4. Tick all Gate 2 criteria:
   - Baseline approved.
   - Benefit assumptions documented.
   - Finance validation completed.
5. Submit the gate.
6. Approve the gate as a transformation office user.
7. Open `/financials/bankable-plan`.
8. Select the initiative.
9. Confirm the plan shows **Locked** and a version number.

After Gate 2 is approved and the plan is locked, move each initiative forward
to its current delivery stage. For the ACME demo, move initiatives to
**Executing**:

1. Return to the initiative **Governance** or **Overview** tab.
2. Submit and approve Gate 3 and Gate 4 where the UI requires gate movement.
3. Confirm the initiative stage is **Executing**.
4. Leave Gate 5 unapproved unless you want to demonstrate fully realized
   initiatives.

### 12.3 Confirm Post-Lock Financial Edit Rules

After the bankable plan is locked, the approved planning structure is fixed:

- annual baseline values,
- Plan Base and Plan High scenario values,
- benefit-line definitions,
- planned cost amounts,
- bankable plan snapshots.

The lock does **not** freeze execution actuals. Users can still open the
initiative **Financials** tab, switch to **Actuals**, click **Edit Details**, and
enter:

- Actual scenario metric values,
- actual recurring cost amounts,
- actual one-off cost amounts.

Use governed rebaseline only when the approved plan itself must change. Do not
use the Gate 2 bankable-plan lock as a period-close lock for actuals.

If a tenant has approved a baseline change, run a governed bankable-plan
rebaseline. ACME uses ENT-005/TRN-005 as the example:

1. Open `/financials/bankable-plan`.
2. Select ENT-005, or TRN-005 in ACME4.
3. Select **Request rebaseline**.
4. Enter this reason:

```text
Enterprise Data Platform delivery timing and tooling assumptions were refreshed.
```

5. Submit the request.
6. Open `/pmo/governance?status=pending`.
7. Approve the **Bankable plan rebaseline** request.
8. Return to `/financials/bankable-plan` and confirm ENT-005/TRN-005 shows
   version `2` with a rebaseline history entry.

## 13. Enter Benefit Tracking Actuals

Screen:

- `/financials/benefit-tracking`

You can enter actuals manually in **Ledger Entries** or upload them in
**Import**.

Benefit Tracking is a separate realization ledger. It records evidence-backed
realized benefits against the locked bankable plan. It does not replace the
initiative **Financials** tab **Actuals** scenario, which remains the source for
portfolio financial actuals and actual cost amounts.

For a tenant setup, enter the tenant's actual realization ledger rows. For a
fast ACME UI demo, enter yearly rows:

| Code | 2027 bankable plan | 2027 actual | 2028 bankable plan | 2028 actual |
|---|---:|---:|---:|---:|
| ENT-001 | `0.0000` | `0.0000` | `100000.0000` | `90000.0000` |
| ENT-002 | `525000.0000` | `439500.0000` | `1100000.0000` | `977000.0000` |
| ENT-003 | `360000.0000` | `305600.0000` | `650000.0000` | `582000.0000` |
| ENT-004 | `950000.0000` | `795000.0000` | `1800000.0000` | `1600000.0000` |
| ENT-005 | `280000.0000` | `236800.0000` | `600000.0000` | `536000.0000` |
| ENT-006 | `520000.0000` | `447200.0000` | `1050000.0000` | `945000.0000` |
| ENT-007 | `300000.0000` | `258000.0000` | `650000.0000` | `585000.0000` |
| ENT-008 | `730000.0000` | `609800.0000` | `1350000.0000` | `1199000.0000` |
| ENT-009 | `450000.0000` | `377000.0000` | `900000.0000` | `801000.0000` |
| ENT-010 | `455000.0000` | `381300.0000` | `950000.0000` | `845000.0000` |

For each code, create two ledger rows:

| Field | 2027 row | 2028 row |
|---|---|---|
| Initiative | Initiative code | Initiative code |
| Granularity | Yearly | Yearly |
| Period start | 2027-01-01 | 2028-01-01 |
| Period end | 2027-12-31 | 2028-12-31 |
| Actual amount | Use 2027 actual | Use 2028 actual |
| Description | ACME 2027 realization actual | ACME 2028 realization actual |

The system derives bankable plan amount from the locked plan. If the locked plan
amount is zero or missing, return to section 12 and confirm Gate 2 approval and
plan lock.

Expected benefit tracking totals:

| Year | Bankable plan | Actual |
|---|---:|---:|
| 2027 | `$4.57M` | `$3.8502M` |
| 2028 | `$9.15M` | `$8.16M` |

## 14. Configure Shared Costs

Screen:

- `/shared-costs`

### 14.1 Reporting Settings

Open reporting settings and set:

| Setting | Value |
|---|---|
| Include in Executive Control Tower | On |
| Include in dashboard executive brief | On |
| Include in Portfolio Financials | Off |
| Include in Initiative Financials | On |
| Include in Bankable Plan | Off |
| Posting mode | Report only |

This keeps `/financials` direct-only while Control Tower can show fully loaded
economics.

### 14.2 Pools And Policies

Create shared-cost pools only for costs that support multiple initiatives. ACME
uses four FY2028 pools:

| Pool | Category | Plan | Actual | Method | Targets |
|---|---|---:|---:|---|---|
| Group technology and data platform | Software / Licenses | `650000` | `585000` | Benefit weighted | ENT-002, ENT-005, ENT-006, ENT-009, ENT-010 |
| Transformation PMO and benefits office | People Support | `400000` | `360000` | Equal split | All 10 initiatives |
| Shared change and training support | Training / Change Management | `220000` | `198000` | Manual amount | ENT-002, ENT-004, ENT-005, ENT-010 |
| Central advisory and vendor support | External Consultants | `180000` | `162000` | Fixed percentage | ENT-005, ENT-008, ENT-009 |

For each pool:

1. Create the pool.
2. Set year to `2028`.
3. Set scenario to **Plan Base**.
4. Set period grain to **Annual**.
5. Set reporting treatment to **Report only**.
6. Save the pool.
7. Create an allocation policy.
8. Add targets.
9. Add weights if required.
10. Select **Preview Allocation**.
11. Confirm preview status is **Reconciled**.
12. Select **Post Locked Run**.

Manual amount weights:

| Initiative | Manual amount |
|---|---:|
| ENT-002 | `55000` |
| ENT-004 | `70000` |
| ENT-005 | `55000` |
| ENT-010 | `40000` |

Fixed percentage weights:

| Initiative | Percentage |
|---|---:|
| ENT-005 | `40` |
| ENT-008 | `35` |
| ENT-009 | `25` |

Expected shared-cost totals:

| Measure | Value |
|---|---:|
| Shared-cost plan | `$1.45M` |
| Shared-cost actual | `$1.305M` |
| Control Tower allocated plan | `$1.45M` |

## 15. Dashboard And Report Demo Walkthrough

Use this sequence after setup is complete. For a non-ACME tenant, keep the route
sequence but replace the example filters, initiative names, and expected values
with the tenant's own data.

### 15.1 Executive Dashboard `/dashboard`

Use it to open the demo.

Show:

- Portfolio count: 10 initiatives.
- RAG mix: mostly green with ENT-005 and ENT-009 amber.
- Stage distribution: all 10 initiatives in Executing for the ACME demo.
- Workstream x tag value matrix.
- KPI pulse and risk widgets.
- Executive brief value cards.

Explain:

> This is the first management readout. It tells leadership how much work is in
> flight, where value is concentrated, which items are at risk, and whether the
> portfolio has enough KPI and financial evidence.

### 15.2 Initiative Pipeline `/initiatives/pipeline`

Show:

- Filters by business unit, workstream, tag, priority, owner, RAG, and stage.
- Stage grouping.
- Initiative cards or rows.

Demo filters:

1. Filter Workstream = **Commercial Growth**.
2. Filter Tag = `commercial`.
3. Open ENT-006 Pricing & Discount Optimization.

Explain:

> The pipeline is the operating list. It lets the transformation office move
> from portfolio-level questions to the individual initiatives that explain the
> value and risk.

### 15.3 Initiative Detail `/initiatives/:id`

Use ENT-006 or ENT-005.

Show:

- Overview: owner, dimensions, dates, RAG, value summary.
- Financials: baseline, Plan Base, Plan High, Actual, benefit lines, cost lines,
  and value bridge.
- Milestones: Gate 2 complete and FY28 run-rate activation in progress.
- KPIs: value and operational KPIs.
- Risks: adoption, data readiness, and finance validation risks.
- Dependencies: upstream/downstream dependency relationships.
- Governance: Gate 2 approval and criteria snapshot.

Explain:

> The initiative page is the source of truth for one value case. Dashboards are
> credible only because this page holds the assumptions, financials, evidence,
> delivery status, and governance history.

### 15.4 Initiative Matrix `/initiatives/matrix`

Show:

- Rows by workstream.
- Columns by tag.
- Value concentration by workstream and value lever.
- Clickable cells where available.

Explain:

> This answers where value is concentrated. ACME has automation value across
> several workstreams, commercial value in Commercial Growth, and offshoring
> value in Shared Services and Procurement.

### 15.5 Financial Overview `/financials`

Set:

| Control | Value |
|---|---|
| Granularity | Yearly |
| Year | 2028 |
| Benefits | On |
| Actuals | On |
| Stage | All or Executing |

Show:

- Benefits: `$9.15M`.
- Recurring costs: `$0.80M`.
- Net run-rate value: `$8.35M`.
- One-off investment: `$2.50M`.
- Trend chart.
- In-year value panel.
- Planned Financials / Plan vs Actuals table.
- Cost breakdown.
- Metric breakdown.
- Contributor drawer by clicking FY2028 row.

Explain:

> Financial Overview reconciles the value. FY28 run-rate value is gross margin
> uplift plus cost savings minus recurring cost. One-off investment is shown for
> payback and funding, but it is not recurring EBITDA drag.

### 15.6 Initiative Portfolio `/financials/initiative-portfolio`

Show:

- Initiative-level value ranking.
- Cost and benefit comparison.
- Stage and RAG context.
- Which initiatives carry the largest benefit or cost burden.

Explain:

> This is the finance ranking table. It helps identify material initiatives,
> concentration risk, and value cases that need leadership attention.

### 15.7 Investments & Payback `/financials/investments-payback`

Show:

- Portfolio one-off investment: `$2.50M`.
- FY28 net run-rate value: `$8.35M`.
- Portfolio payback period: about `3.6` months.
- Initiative-level payback rows.

Explain:

> This view separates investment funding from recurring EBITDA run-rate. One-off
> investment is accumulated through the selected value year and compared with
> annual net run-rate value to show payback period.

### 15.8 Benefits Register `/financials/benefits-register`

Show:

- All benefit lines across the portfolio.
- Validation statuses: Draft, Submitted, Finance Validated, Rejected.
- Evidence labels and realization owner.
- Risk adjustment and bankable amounts where shown.

Demo:

1. Filter status = **Finance validated**.
2. Filter status = **Submitted**.
3. Filter status = **Rejected** and show ENT-009 cost savings.

Explain:

> The Benefits Register is Finance's control sheet. It separates submitted
> value from validated value and keeps evidence, owner, risk, and handoff status
> visible.

### 15.9 Bankable Plan `/financials/bankable-plan`

Show:

- Select an initiative.
- Locked state and version.
- Net plan.
- Included metric values and cost lines.
- History and rebaseline trail, especially ENT-005 if rebaseline was created.

Explain:

> Bankable Plan freezes the approved plan. Once Gate 2 is approved, realization
> tracking compares actuals to this locked baseline instead of chasing a moving
> target. The lock does not freeze actuals entry; Actuals scenario values and
> actual cost amounts stay open for reporting-period updates.

### 15.10 Benefit Tracking `/financials/benefit-tracking`

Set scope:

- Portfolio.
- Workstream.
- Initiative.

Show:

- Locked baseline.
- Realized actuals.
- Variance.
- Workstream chart.
- Ledger Entries tab.
- Import tab.

Expected 2028 portfolio view:

| Measure | Value |
|---|---:|
| Locked baseline | `$9.15M` |
| Realized actual | `$8.16M` |
| Variance | `-$0.99M` |

Explain:

> Benefit Tracking is the actual realization layer. It shows whether approved
> bankable value has moved into actual business results. It is separate from
> initiative Financials actuals, which feed portfolio financial reporting.

### 15.11 Waterline `/financials/waterline`

Use it to demonstrate locked targets by workstream.

Steps:

1. Select a workstream.
2. Select a cutoff date after Gate 2 approvals.
3. Preview approved initiatives.
4. Lock the target snapshot if the demo requires it.
5. Compare actual realization against the locked target.

Explain:

> Waterline freezes what the workstream committed to by a cutoff date. It is
> useful when leadership wants to know whether realized value is above or below
> the approved target line.

### 15.12 Shared Costs `/shared-costs`

Show:

- Four pools.
- Benefit weighted, equal split, manual amount, and fixed percentage policies.
- Targets and weights.
- Preview reconciliation.
- Locked run history.
- Reporting settings.

Explain:

> Shared Costs keep direct initiative economics separate from fully loaded
> executive economics. The initiative owner remains accountable for direct
> benefits and costs; Control Tower can show the portfolio after central PMO,
> platform, change, and vendor support costs are allocated.

### 15.13 Progress `/progress` And Roadmap `/progress/roadmap`

Show:

- Milestone status across the portfolio.
- Roadmap timing.
- Overdue or in-progress milestone indicators.

Explain:

> Progress explains whether the financial case is deliverable. It connects the
> value story to milestone execution.

### 15.14 Governance `/pmo/governance`

Show:

- Gate submissions.
- Gate 2 approvals.
- Criteria completion.
- Initiatives by governance state.

Explain:

> Governance proves that value is not just entered into a spreadsheet. Each
> initiative passes controlled stages, and the bankable plan is locked from an
> approved gate.

### 15.15 PMO KPIs `/pmo/kpis`

Show:

- KPI coverage by initiative.
- KPI statuses and latest values.
- Missing or stale KPI signals.

Explain:

> KPIs prove whether the operational drivers behind the financial benefits are
> moving. If benefits are planned but KPIs are missing, realization confidence
> should be challenged.

### 15.16 PMO Risks `/pmo/risks`

Show:

- Portfolio risk register.
- High-impact risks.
- Risks attached to ENT-005 and ENT-009.
- Mitigation status.

Explain:

> Risks explain why value may not land. A strong financial plan with unmanaged
> data, adoption, or finance-validation risk should still get leadership
> attention.

### 15.17 Executive Control Tower `/reports/control-tower`

Set target year to `2028`.

Show:

- Burdened value bridge.
- Direct costs.
- Allocated costs.
- Net before allocation.
- Net after allocation.
- Dependency risk.
- Initiatives needing attention.
- Initiative-level burdened value table.
- Persona views if available.

Explain:

> Control Tower is the executive operating view. It combines value, cost, shared
> cost burden, delivery risk, dependencies, and attention items. Use this when
> management asks, "What is the value after direct and allocated costs, and
> what could put it at risk?"

## 16. Final Demo Readiness Checklist

Before presenting or handing the tenant to users, verify:

| Check | Expected |
|---|---|
| First-run setup | Complete or no blockers for initiative creation. |
| Business units | Tenant's configured management units; ACME has 5. |
| Workstreams | Tenant's configured transformation lanes; ACME has 5. |
| Financial scenarios | Tenant's active scenarios; ACME uses Baseline, Plan Base, Plan High, Actual. |
| Metrics | Baselines, benefit metrics, and formulas configured. |
| Cost categories | One-off and recurring categories configured. |
| Stage gates | Tenant's approval gates with criteria; ACME has 5. |
| Initiatives | Tenant's active transformation portfolio; ACME has 10. |
| Initiative baselines | Initiative baselines reconcile to tenant baseline; ACME totals `$20.00M` revenue and `$9.00M` GM. |
| Target-year financials | Tenant target-year benefits, recurring costs, and net value reconcile; ACME FY28 net is `$8.35M`. |
| Benefit lines | Real validation statuses, or a demo mix of Finance Validated, Submitted, Draft, and Rejected. |
| Bankable plans | Locked for initiatives that have passed the configured approval gate. |
| Benefit ledger | Actual rows entered or imported for the realization periods being demonstrated. |
| Shared Costs | Shared pools and locked runs only where central costs need allocation. |
| Control Tower | Shows allocated costs and net after allocation for the selected target year. |
| Dashboards | Dashboard, Financials, Benefits Register, Benefit Tracking, and PMO views show non-empty data. |

## 17. Common Demo Questions

| Question | Where to answer it | Answer |
|---|---|---|
| What is the target-year run-rate value? | `/financials`, target year | Tenant-specific net run-rate; ACME FY28 is `$8.35M`. |
| Why not count revenue uplift directly in EBITDA? | `/financials`, value bridge | Revenue is a commercial driver; GM uplift and savings are EBITDA-effective. |
| Where did a benefit number come from? | Initiative Financials and Benefits Register | Benefit line, scenario, period values, evidence, and validation status. |
| What is locked for accountability? | `/financials/bankable-plan` | Approved bankable plan snapshot after Gate 2. |
| Are actuals tracked? | Initiative Financials and `/financials/benefit-tracking` | Initiative Financials Actuals feed portfolio actuals and costs; Benefit Tracking ledger actuals compare realized benefit evidence to locked plan. |
| Which initiatives are at risk? | `/dashboard`, `/pmo/risks`, `/reports/control-tower` | Tenant-specific risk items; ACME highlights ENT-005 and ENT-009. |
| What do Shared Costs change? | `/shared-costs`, `/reports/control-tower` | They add allocated central burden to executive reporting without changing direct initiative accountability. |
| Why can `/financials` and Control Tower differ? | `/financials` and `/reports/control-tower` | `/financials` is direct-only by default; Control Tower can include allocated shared-cost burden. |

## 18. Browser E2E Validation

The maintained browser automation for this guide is:

```bash
TRANSMUTER_E2E_EMAIL=admin@acme4-transformation.dev \
TRANSMUTER_E2E_PASSWORD='<password>' \
node apps/web/e2e/acme4-full-demo-ui-e2e.mjs
```

Use `TRANSMUTER_UI_BASE_URL` and `TRANSMUTER_API_BASE_URL` to point the runner
at another environment. The runner signs in through the browser, maps the
historical `ENT-*` guide sequence to ACME4's generated `TRN-*` initiative codes,
uses UI screens to enrich initiatives, configures Shared Costs, imports the
benefit ledger, and verifies the dashboard routes.

Validated on dev on 2026-06-22:

| Area | Result |
|---|---:|
| Initiatives | 10 |
| Bankable plans | 10 |
| KPIs | 11 |
| Risks | 10 |
| Milestones | 20 |
| Dependencies | 3 |
| Benefit ledger actuals | `$12,053,200.0020` |
| Shared-cost pools | 4 |
| ENT-005/TRN-005 bankable plan version | 2 |

The Benefit Tracking import screen accepts the mapped CSV through the UI file
control. In headless Chromium the visible Import button did not reliably fire
the upload handler, so the runner completes the import with the same
authenticated browser session using `FormData` against the platform API. This is
a UI automation reliability gap, not a data setup shortcut; no database writes
are used by the runner.

## 19. Notes For ACME, ACME2, ACME3, And ACME4

- Use the same setup data for all demo tenants.
- For customer or internal tenant onboarding, use the workflow in this guide but
  replace the ACME setup data with the tenant's own operating model, initiatives,
  financial baselines, benefit assumptions, costs, owners, and dashboard needs.
- ACME4 should be treated as the canonical full demo in dev because it proves
  tenant signup, the current financial engine, current dashboard configuration,
  shared-cost allocation, benefit tracking, governed bankable-plan rebaseline,
  and initiative delivery artifacts.
- ACME3 remains useful as the legacy reference tenant for original `ENT-*` demo
  codes.
- Use unique slugs and user emails for each tenant.
- If production ACME does not show the ACME4 shared-cost pools, that is the
  known production demo-data drift tracked in issue `#304`; it is not a Shared
  Costs schema or deployment failure.
