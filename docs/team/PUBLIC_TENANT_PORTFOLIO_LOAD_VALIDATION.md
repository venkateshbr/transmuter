# Public Tenant Portfolio Load Validation

Issue: #260
Date: 2026-06-12
Public URL: `https://transmuter.ishirock.tech`
Workbook: `Initiative_Portfolio_Anonymised.xlsx`

## Tenant

- Tenant slug: `portfolio-load-20260612141414`
- Tenant ID: `bf1053b2-5ea1-44cc-8746-c05a27863f2a`
- Initial admin user ID: `b686e1a7-db43-4fae-ada8-8a2c16268af5`
- Signup path: public Stripe sandbox checkout through `/api/billing/checkout-session`,
  followed by `/api/billing/checkout-completion`.
- Provisioning status: `provisioned`
- Login status: `login_ready`

No credentials, tokens, Stripe secrets, or passwords are stored in this document.

## Workbook Review

Reviewed sheets:

- `Initiative Summary`
- `Charter Details`
- `Financial Summary`
- `Benefits`
- `Costs`
- Also parsed and loaded supporting sheets: `KPIs`, `Milestones`, `Risks`,
  and `Status Updates`

Workbook-derived configuration:

- Business units: `BNT`, `CAL`, `FJD`, `GROUP`, `KLP`, `MER`, `RDG`, `VER`, `VSC`
- Workstreams: `Eastbridge Region`, `Northpeak Region`, `Southgate Region`,
  `Westmark Region`
- Tags: `automation`, `commercial`, `offshoring`
- Markets/countries: none populated in the workbook charter fields
- Themes: none populated in the workbook charter fields
- Required metric keys: `gm_uplift`, `gm_uplift_pct`, `gross_margin`,
  `revenue_uplift`
- Required scenario keys: `actual`, `plan_base`, `plan_high`
- Required stage gate numbers: `3`
- Cost categories: workbook rows did not populate `Cost Category`, so loaded cost
  lines use the platform fallback category `other`

Important mapping note:

- `Financial Summary` is an annual aggregate/reporting sheet. It was reviewed as
  an output/check sheet, but it is not loaded as a separate source table. The
  platform system of record is loaded from the monthly `Benefits` and `Costs`
  rows, which then drive initiative financials, portfolio financials, value
  bridge, and dashboard rollups.

## Tenant Configuration

The tenant was configured through public authenticated APIs before loading any
initiatives.

Configuration created:

- 9 business units
- 4 workstreams
- 3 strategic tags
- 2 financial configuration groups
- 5 financial configuration items
- 4 financial metric definitions
- 3 financial scenarios
- 5 value bridge rows
- 10 financial attribute definitions
- 5 stage-gate transitions:
  - Gate 1: Scoping
  - Gate 2: Planning
  - Gate 3: In Execution
  - Gate 4: Completed
  - Gate 5: Value Realized
- 3 gate criteria per gate

Setup checklist after configuration:

- Completed: `8/8`
- Status: complete

## Dry Run

Command:

```bash
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id bf1053b2-5ea1-44cc-8746-c05a27863f2a \
  --user-id b686e1a7-db43-4fae-ada8-8a2c16268af5 \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --dry-run
```

Result:

- `ready`: `true`
- Missing metric keys: none
- Missing scenario keys: none
- Missing stage gate numbers: none

Expected parsed counts:

- Initiatives: 21
- Benefit lines: 63
- Metric values: 4,694
- Cost lines: 867
- KPIs: 83
- KPI entries: 313
- Milestones: 292
- Risks: 33
- Status updates: 4

## Load

Command:

```bash
uv run python scripts/load_portfolio_workbook.py \
  --tenant-id bf1053b2-5ea1-44cc-8746-c05a27863f2a \
  --user-id b686e1a7-db43-4fae-ada8-8a2c16268af5 \
  --workbook ../../Initiative_Portfolio_Anonymised.xlsx \
  --confirm-reset
```

The reset was tenant-scoped and deleted/reloaded portfolio data only for the new
validation tenant.

Loaded counts:

- Initiatives: 21
- Business units: 9
- Workstreams: 4
- Initiative-business-unit links: 25
- Benefit lines: 63
- Metric values: 4,694
- Cost lines: 867
- KPIs: 83
- KPI entries: 313
- Milestones: 292
- Risks: 33
- Status updates: 4

## Public API Validation

Validated through `https://transmuter.ishirock.tech/api` using the new tenant
admin session.

Observed:

- `/initiatives?page_size=100`: 21 initiatives
- `/admin/setup-status`: complete, `8/8`
- `/financial-engine-configuration`: 4 definitions, 3 scenarios, 5 bridge rows,
  10 attributes
- `/financial-configuration`: 2 groups, 5 items
- Sample initiative `EBR-1`:
  - Name: `MER Billing System Integration & Automation`
  - Stage: `in_execution`
  - Tag: `automation`
  - Financial definitions: 4
  - Financial scenarios: 3
  - Benefit lines: 3
  - Financial values: 228
  - Cost lines: 59
- Portfolio supporting counts:
  - KPIs: 83
  - Milestones: 292
  - Risks: 33
  - Status updates: 4
- Dashboard API summary:
  - Total initiatives: 21
  - Pipeline stages: 5
  - Risk heatmap items: 5

Observation:

- `/portfolio/value-ramp` returned 65 periods, but the deployed response did not
  expose workstream rollups in the summary shape checked during this validation.
  This should be reviewed separately if workstream-level value ramp visualization
  is required for launch acceptance.

## Browser Validation

Validated through headless Chromium against `https://transmuter.ishirock.tech`.

Checks passed:

- Authenticated as the new tenant admin.
- Dashboard rendered for the new tenant.
- Initiative list rendered loaded workbook initiatives.
- Initiative detail rendered loaded workbook data.
- Financials tab rendered for sample initiative
  `e70cf436-b10b-4f91-819b-75907bf82c03`.

## Assessment

The configurability test passed for the current workbook and platform model:

- A blank tenant can be onboarded through the public signup/checkout path.
- Tenant setup can be completed without seeded demo data.
- Workbook-derived business units, workstreams, tags, financial metrics,
  scenarios, stage gates, gate criteria, benefit metadata, cost metadata, KPIs,
  milestones, risks, and status updates can be configured/loaded.
- The loaded portfolio is visible through public API and browser workflows.

Remaining gaps:

- The workbook does not contain populated Country/Market or Theme fields, so
  those dimensions could not be validated with real workbook values.
- `Financial Summary` is not loaded directly; it is treated as a workbook
  aggregate over the transactional `Benefits` and `Costs` sheets.
- Cost categories in the workbook are blank, so only fallback category `other`
  was validated.
- Workstream-level value-ramp response shape should be reviewed before launch if
  that visualization is a hard requirement.

