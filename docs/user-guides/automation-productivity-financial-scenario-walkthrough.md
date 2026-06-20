# Automation Productivity Financial Scenario Walkthrough

This guide documents a second end-to-end financial-engine scenario in the **Vish Demo Lab** tenant.

- **Initiative:** `Automation productivity uplift for delivery teams`
- **Initiative code:** `TRN-011`
- **Initiative ID:** `04b62a1a-4725-4e30-a214-fb5ede63ee03`
- **Planned start:** `2026-07-15`
- **Planned end:** `2028-06-15`
- **Workstream:** Automation & AI Enablement
- **Business units:** Delivery & Support, Product & Technology

The scenario models an automation initiative that releases productive team capacity and converts that released capacity into gross-margin gain.

---

## 1. Business scenario

The hypothetical business case is:

> Deploy workflow automation and AI-assist capabilities across delivery teams to reduce repeatable manual work, release productive hours, and convert that capacity into gross-margin uplift.

The initiative has three financial phases:

1. **Build phase:** mid-July 2026 through mid-2027.
2. **Benefit accrual phase:** starts in mid-2027.
3. **Full realization:** by mid-2028.

The financial model intentionally includes:

- productivity uplift measured as gross-margin gain,
- one-time implementation costs,
- runtime / operations costs,
- recurring platform and support costs,
- computed read-only formula rows,
- value bridge rows,
- yearly and monthly portfolio rollups.

---

## 2. Scenario timeline

### Benefits timeline

Benefits start in **July 2027** and run evenly through **June 2028**.

That creates 12 equal monthly benefit periods:

- July 2027 through December 2027: 6 months
- January 2028 through June 2028: 6 months

This satisfies the requested design:

- benefits begin starting in mid-2027,
- benefits are fully realized by mid-2028,
- benefits are distributed evenly across 2027 and 2028.

### Cost timeline

One-time build costs are distributed every two months over the year after kickoff:

- July 2026
- September 2026
- November 2026
- January 2027
- March 2027
- May 2027

Post-implementation recurring and runtime costs begin in July 2027 and continue through June 2028.

---

## 3. Scenario lanes

The scenario uses the same scenario keys that the backend financial engine expects for base/high/actual rollups:

| Key | Label | Role |
|---|---|---|
| `plan_base` | Plan Base | Base-case plan |
| `plan_high` | Plan High / Upside | Upside/high case |
| `actual` | Actual | Actual or actualized scenario lane |

The scenario keys matter because value bridge and portfolio rollups look for these keys when building the base, high, and actual cases.

---

## 4. Metric definitions configured

Four automation-specific metric definitions were configured.

| Metric key | Label | Type | Input or computed? | Formula / purpose |
|---|---|---|---|---|
| `auto_hours_saved` | Automation Hours Released | number, hours | Input | Monthly productive hours released by automation. |
| `auto_gm_rate_per_hour` | Gross Margin Value per Released Hour | currency, USD/hour | Input | Gross-margin value assigned to each released hour. |
| `auto_gross_margin_gain` | Automation Gross Margin Gain | currency, USD | Computed/read-only | `auto_hours_saved * auto_gm_rate_per_hour` |
| `auto_realization_pct` | Automation Realisation % of Full Run Rate | percent | Computed/read-only | `auto_gross_margin_gain / 120000 * 100` |

### Why this tests configurability

This setup tests that the financial engine can configure:

- non-currency metrics (`auto_hours_saved`),
- currency assumption metrics (`auto_gm_rate_per_hour`),
- formula metrics that become financial benefits (`auto_gross_margin_gain`),
- formula metrics that are informational and not benefits (`auto_realization_pct`),
- bridge rows driven by metric definition IDs,
- cost bridge rows driven by engine cost category IDs with stable category keys
  retained for import/export.

---

## 5. Attribute definitions configured

Three attribute definitions were configured for this scenario.

| Attribute key | Label | Entity type | Value type | Options |
|---|---|---|---|---|
| `auto_benefit_owner` | Automation Benefit Owner | benefit_line | text | none |
| `auto_adoption_dependency` | Adoption Dependency | benefit_line | select | Workflow adoption, Model quality, Process standardisation, Data readiness |
| `auto_cost_nature` | Automation Cost Nature | cost_line | select | Build, Run, Recurring licence, Operations support |

### Implementation note

Benefit-line attributes are saved on each benefit line in the `attributes` object.

Cost-line attribute definitions can be registered, but the current cost-line API payload does not expose a cost-line instance `attributes` object. So cost-line attribute *definitions* are configurable, but cost-line attribute *values* are not yet captured by the API model.

---

## 6. Benefit lines configured

Two benefit/input lines were created.

| Benefit line | Metric definition | Timing | Example attributes |
|---|---|---|---|
| Released delivery-team productivity hours | `auto_hours_saved` | Accrual begins mid-2027; full realization by mid-2028 | Owner = Automation Transformation Lead; Dependency = Workflow adoption |
| Gross margin value per released hour | `auto_gm_rate_per_hour` | Accrual begins mid-2027; full realization by mid-2028 | Owner = Automation Transformation Lead; Dependency = Process standardisation |

There is no manually-entered benefit line for `auto_gross_margin_gain` because that row is computed from the two input metrics.

The model is:

```text
auto_hours_saved + auto_gm_rate_per_hour
  -> auto_gross_margin_gain formula row
  -> benefit rollup / value bridge / portfolio financials
```

---

## 7. Benefit input values

Benefits are distributed evenly across July 2027 through June 2028.

### Plan Base

Each month from July 2027 to June 2028:

```text
2,400 released hours * $50/hour = $120,000 gross margin gain
```

Annual split:

- 2027: 6 months * 120,000 = 720,000
- 2028: 6 months * 120,000 = 720,000
- Total Plan Base benefit = 1,440,000

### Plan High / Upside

Each month from July 2027 to June 2028:

```text
2,800 released hours * $50/hour = $140,000 gross margin gain
```

Annual split:

- 2027: 6 months * 140,000 = 840,000
- 2028: 6 months * 140,000 = 840,000
- Total Plan High benefit = 1,680,000

### Actual lane

Each month from July 2027 to June 2028:

```text
2,200 released hours * $50/hour = $110,000 gross margin gain
```

Annual split:

- 2027: 6 months * 110,000 = 660,000
- 2028: 6 months * 110,000 = 660,000
- Total Actual benefit = 1,320,000

---

## 8. Read-only computed formula rows

Two formula rows are computed automatically.

### Formula row 1: Automation Gross Margin Gain

Formula:

```text
auto_gross_margin_gain = auto_hours_saved * auto_gm_rate_per_hour
```

Expected monthly values:

| Scenario | Monthly hours | Rate | Monthly computed GM gain |
|---|---:|---:|---:|
| Plan Base | 2,400 | 50 | 120,000 |
| Plan High | 2,800 | 50 | 140,000 |
| Actual | 2,200 | 50 | 110,000 |

### Formula row 2: Automation Realisation % of Full Run Rate

Formula:

```text
auto_realization_pct = auto_gross_margin_gain / 120000 * 100
```

Expected monthly values:

| Scenario | Monthly computed GM gain | Formula result |
|---|---:|---:|
| Plan Base | 120,000 | 100.0000% |
| Plan High | 140,000 | 116.6667% |
| Actual | 110,000 | 91.6667% |

### How the formula rows are handled

The user does **not** input these values directly.

The backend computes them when the financial grid is read:

1. Load all stored input metric values for the initiative.
2. Group values by tenant, initiative, scenario, year, and month.
3. Evaluate formula metric definitions in dependency order.
4. Return synthetic formula rows with generated IDs.
5. Reject writes to formula metrics.

In the frontend financial grid, formula rows are shown as read-only computed rows. The label receives the suffix:

```text
- computed
```

So an end user should expect rows such as:

```text
Automation Gross Margin Gain (Plan Base) - computed
Automation Realisation % of Full Run Rate (Plan Base) - computed
```

---

## 9. Cost lines configured

### One-time costs

One-time build/integration costs were distributed evenly every two months over the first year.

| Month | Category | Plan | Actual | Recurring? |
|---|---|---:|---:|---:|
| Jul 2026 | `auto_one_time_build` | 100,000 | 95,000 | no |
| Sep 2026 | `auto_one_time_build` | 100,000 | 95,000 | no |
| Nov 2026 | `auto_one_time_build` | 100,000 | 95,000 | no |
| Jan 2027 | `auto_one_time_build` | 100,000 | 95,000 | no |
| Mar 2027 | `auto_one_time_build` | 100,000 | 95,000 | no |
| May 2027 | `auto_one_time_build` | 100,000 | 95,000 | no |

Totals:

- Plan one-time cost = 600,000
- Actual one-time cost = 570,000

### Runtime / operations costs

Runtime operations costs start when benefits start, July 2027 through June 2028.

Each month:

- Plan = 30,000
- Actual = 28,000
- Recurring = yes

Total over 12 months:

- Plan runtime operations cost = 360,000
- Actual runtime operations cost = 336,000

### Recurring platform and support costs

Recurring platform and support costs also run July 2027 through June 2028.

Each month:

- Plan = 20,000
- Actual = 22,000
- Recurring = yes

Total over 12 months:

- Plan recurring platform cost = 240,000
- Actual recurring platform cost = 264,000

### Cost handling rule

The financial engine treats costs this way:

```text
amount_plan -> plan/base/high calculations
amount_actual -> actual calculations
is_recurring = true -> recurring cost bucket
is_recurring = false -> one-off cost bucket
```

Net run-rate impact subtracts recurring costs. One-off costs are shown in cost totals and bridge rows, but they are not subtracted from net run-rate impact.

---

## 10. Bridge rows configured

The following automation-specific bridge rows were configured.

| Bridge row | Kind | Inputs | Sign | Meaning |
|---|---|---|---:|---|
| Automation Hours Released | `metric_set` | `auto_hours_saved` | +1 | Sums released hours across months. |
| Automation Gross Margin Gain | `metric_set` | `auto_gross_margin_gain` | +1 | Sums computed GM benefit across months. |
| Automation One-time Build Costs | `cost_set` | `auto_one_time_build` | -1 | Displays one-time build costs as negative values. |
| Automation Runtime / Operations Costs | `cost_set` | `auto_runtime_ops` | -1 | Displays runtime operations costs as negative values. |
| Automation Recurring Platform Costs | `cost_set` | `auto_recurring_platform` | -1 | Displays recurring platform/support costs as negative values. |
| Automation Net Run-rate Impact | `net` | automatic | +1 | Benefits total minus recurring costs. |

### How to interpret bridge row kinds

#### `metric_set`

Sums metric values for the listed metric definition IDs.

Example:

```text
Automation Gross Margin Gain, Plan Base
= 12 months * 120,000
= 1,440,000
```

#### `cost_set`

Sums cost lines for the selected engine cost categories.

If sign is `-1`, the displayed bridge row is negative.

Example:

```text
Automation Runtime / Operations Costs, Plan Base
= 12 months * 30,000 * -1
= -360,000
```

#### `net`

Calculated automatically as:

```text
benefits_total - recurring_costs
```

In this scenario, recurring costs are:

```text
runtime operations + recurring platform/support
```

One-time build costs are displayed, but they do not reduce net run-rate impact.

---

## 11. Verified initiative value bridge output

The live initiative value bridge returned the following automation rows.

| Bridge row | Base case | High case | Actual |
|---|---:|---:|---:|
| Automation Hours Released | 28,800 | 33,600 | 26,400 |
| Automation Gross Margin Gain | 1,440,000 | 1,680,000 | 1,320,000 |
| Automation One-time Build Costs | -600,000 | -600,000 | -570,000 |
| Automation Runtime / Operations Costs | -360,000 | -360,000 | -336,000 |
| Automation Recurring Platform Costs | -240,000 | -240,000 | -264,000 |
| Automation Net Run-rate Impact | 840,000 | 1,080,000 | 720,000 |

### Net calculation

Base case:

```text
1,440,000 gross margin gain
- 360,000 runtime ops
- 240,000 recurring platform/support
= 840,000 net run-rate impact
```

High case:

```text
1,680,000 - 360,000 - 240,000 = 1,080,000
```

Actual:

```text
1,320,000 - 336,000 - 264,000 = 720,000
```

---

## 12. Verified yearly portfolio rollup

The live portfolio financial endpoint filtered to this initiative returned the following yearly rollup.

| Year | Benefits plan | Benefits actual | Recurring costs plan | Recurring costs actual | One-off costs plan | One-off costs actual | Net value plan | Net value actual |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2026 | 0 | 0 | 0 | 0 | 300,000 | 285,000 | 0 | 0 |
| 2027 | 720,000 | 660,000 | 300,000 | 300,000 | 300,000 | 285,000 | 420,000 | 360,000 |
| 2028 | 720,000 | 660,000 | 300,000 | 300,000 | 0 | 0 | 420,000 | 360,000 |

This confirms the requested timing:

- one-time costs start in 2026 and continue every two months into 2027,
- benefits begin in 2027,
- benefits are evenly split across 2027 and 2028,
- benefits are fully realized by mid-2028.

---

## 13. Verified portfolio summary filtered to the initiative

The live portfolio financial endpoint filtered to this initiative returned:

| Card | Plan | Actual | Variance |
|---|---:|---:|---:|
| Benefits | 1,440,000 | 720,000 | -120,000 |
| Costs | 1,200,000 | 1,170,000 | -30,000 |
| Net Value | 840,000 | 720,000 | -120,000 |

Note: as seen in the prior walkthrough, the Benefits card's `actual` field appears to mirror net actual in the current API response shape. The period-level rollups and value bridge provide the clearer source of truth.

---

## 14. Front-end walkthrough expectations

### A. Initiative overview

The initiative should be visible as:

```text
TRN-011 — Automation productivity uplift for delivery teams
```

Expected metadata:

- Workstream: Automation & AI Enablement
- Priority: High
- Type: Capability building
- Impact type: Recurring
- Planned start: 15 Jul 2026
- Planned end: 15 Jun 2028

### B. Financials tab

In the initiative Financials tab, the user should see input rows for:

- Automation Hours Released
- Gross Margin Value per Released Hour

And computed/read-only rows for:

- Automation Gross Margin Gain - computed
- Automation Realisation % of Full Run Rate - computed

Expected behavior:

- Users can edit the input rows.
- Users cannot edit formula rows directly.
- Formula rows should recalculate after input values are saved and reloaded.

### C. Cost rows

The cost section should show plan and actual cost lines for:

- one-time build/integration costs,
- runtime operations costs,
- recurring platform/support costs.

### D. Value bridge

The initiative value bridge should show:

- gross margin gain as a positive benefit,
- one-time build costs as negative cost rows,
- runtime and recurring costs as negative cost rows,
- net run-rate impact as benefits minus recurring costs.

### E. Portfolio financials

Portfolio financials filtered to this initiative should show:

- no benefits in 2026,
- 720,000 plan benefits in 2027,
- 720,000 plan benefits in 2028,
- one-time costs split across 2026 and 2027,
- recurring costs in 2027 and 2028,
- net value of 420,000 in both 2027 and 2028.

---

## 15. Dashboard validation results

The dedicated financial endpoints behaved as expected:

- `GET /initiatives/{initiative_id}/financials`
  - returned stored input values and computed formula rows.
- `GET /initiatives/{initiative_id}/financials/value-bridge`
  - returned the correct automation bridge rows and net run-rate impact.
- `GET /portfolio/value-bridge`
  - included the configured financial bridge rows across portfolio data.
- `GET /portfolio/financials?granularity=monthly&initiative_id={initiative_id}`
  - returned the expected monthly cost and benefit timing.
- `GET /portfolio/financials?granularity=yearly&initiative_id={initiative_id}`
  - returned the expected 2026/2027/2028 timing split.

### Broader dashboard caveat

The broader dashboard/report endpoints still appear partially disconnected from the configurable financial-engine benefits:

- `GET /dashboard`
  - reflected increased costs after this scenario was added,
  - but still returned `0.0000` benefits in its high-level `value_bridge`.
- `GET /reports/executive-control-tower`
  - reflected increased costs,
  - but still returned `0.0000` plan benefits in the high-level bridge.

This is the same class of issue observed in the previous walkthrough: the core financial endpoints are working, but some executive dashboard/report aggregations appear to still use older or incomplete benefit aggregation logic.

---

## 16. Configurability test findings

### Confirmed configurable

The following were successfully configured and verified:

- metric definitions,
- scenario definitions,
- formula definitions,
- formula dependency ordering,
- benefit-line attributes,
- benefit lines,
- monthly metric values,
- one-time cost lines,
- recurring cost lines,
- bridge rows,
- initiative value bridge rollup,
- portfolio financial monthly/yearly rollup.

### Partially configurable / follow-up needed

1. **Cost-line attributes**
   - Attribute definitions for cost lines can be configured.
   - The current API model does not yet store arbitrary `attributes` on cost-line instances.

2. **Initiative-specific metric selection**
   - The current financial grid receives active tenant-level metric definitions.
   - This means formula definitions from other walkthroughs can appear as zero-value computed rows for this initiative if their input metrics are not present.
   - A future improvement would be to enforce `applies_to` / initiative opt-in behavior more explicitly.

3. **Executive/dashboard rollups**
   - Dedicated financial endpoints are correct.
   - Broader dashboard/report endpoints need alignment with the configurable financial engine.

---

## 17. Mental model for this scenario

```text
Input rows
  ├─ auto_hours_saved
  └─ auto_gm_rate_per_hour

Formula rows
  ├─ auto_gross_margin_gain = hours saved * GM rate per hour
  └─ auto_realization_pct = GM gain / 120000 * 100

Cost rows
  ├─ one-time build costs every two months during build phase
  ├─ runtime operations costs after implementation
  └─ recurring platform/support costs after implementation

Bridge rows
  ├─ show hours released
  ├─ show computed GM gain
  ├─ subtract cost categories visually
  └─ calculate net run-rate impact as benefits - recurring costs

Portfolio rollups
  ├─ 2026: build cost only
  ├─ 2027: remaining build cost + first six months of benefits/costs
  └─ 2028: final six months of benefits/costs
```

The key end-user rule is:

> For automation productivity initiatives, users should enter operational drivers and assumptions. Gross-margin benefits can be configured as formula rows and calculated automatically, while bridge rows define how the initiative's economics are interpreted in summaries and portfolio rollups.
