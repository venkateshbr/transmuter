# Product Upgrade Addendum: `Initiative_Portfolio_Anonymised.xlsx` Fit-Gap Review

**Date:** 2026-06-11
**Companion to:** `productupgrade.md` (Configurable Financial Metrics Engine)
**Inputs:** Sheet-by-sheet review of `Initiative_Portfolio_Anonymised.xlsx` (Initiative Summary → Charter Details → Financial Summary → Benefits → Costs → Dashboards → config/to-do), **plus direct inspection of the live local Supabase database** (schema `transmuter`, 3 orgs / 41 initiatives) rather than migrations alone.

---

## 1. Verdict up front

The hypothesis "most of what is in the Excel can be accommodated" is **correct for the financial core (~80%)** — metrics (Revenue Uplift, Gross Margin, GM Uplift $ and %), Plan Base / Plan High / Actual lanes, monthly phasing FY26–FY31, annual rollups, cost categories, net value, and per-initiative charter basics all map cleanly onto the current model, and map even better onto the `productupgrade.md` metric engine (the workbook's "Lane" column *is* the proposed `financial_scenarios` table; its "Denomination" column *is* the proposed `value_type`).

However, the workbook exposes **eight concrete gaps** that neither the current implementation nor the upgrade plan as written fully covers. None invalidate the recommended architecture — all slot into it — but five require **additions to the recommended design** and three require **corrections to the current-state claims** in `productupgrade.md`. They are detailed in §4 and folded into the phase plan in §6.

The biggest three: **(1) a 5-stage-gate lifecycle** (workbook initiatives sit at "Gate 3"; the live DB hard-constrains `gate_number IN (1,2)` and `stage IN ('scoping','in_progress','complete')`), **(2) initiative-level *named benefit lines*** (e.g., "Revenue Uplift from Improved Retention") rather than only tenant-level metrics, and **(3) cost phasing rules** (One-off / Annual spread / Manual with start–end months and inflation %) instead of hand-typing every monthly cell.

---

## 2. Corrections to `productupgrade.md` from live-DB inspection

These were verified against the running database (`docker exec supabase-db psql`), not just migrations:

| # | Correction | Evidence |
|---|---|---|
| C1 | **App schema is `transmuter`, not `public`.** All DDL in the upgrade plan must target `transmuter.*` and reuse `transmuter.current_tenant_id()` in RLS policies. | `pg_tables`: all app tables under schema `transmuter` |
| C2 | **`organizations` has NO `currency` column.** The Plan-agent design assumed one exists; it doesn't — only `settings.billing.currency` (Stripe billing, value `"usd"`), which is a billing concern and must not be reused as the reporting currency. The upgrade must **add** `reporting_currency` (column or a first-class key in settings) alongside `fiscal_year_start_month`. | `\d transmuter.organizations`: `id, name, slug, logo_url, settings, created_at, updated_at` |
| C3 | **Benefit-maturity machinery partially exists already.** `initiatives` carries `benefit_confidence NUMERIC(5,2)` (0–100) and `realization_status` (`not_started / forecasted / committed / partially_realized / realized / at_risk`), and `initiative_value_realization_notes` stores per-period planned/actual/explanation. Recommendation #8 in `productupgrade.md` ("add benefit maturity stages") should be reframed as: **promote and surface the existing `realization_status` + `benefit_confidence`**, map them onto the L1–L5 funnel, and wire stage transitions to the (expanded) gate model — not green-field work. | `\d transmuter.initiatives` check constraints |
| C4 | `financial_entries` confirmed exactly as documented: 24 hardcoded metric columns, `NUMERIC(15,4)` for $ and `NUMERIC(8,4)` for %, unique `(initiative_id, year, quarter, month)`. `financial_metric_values` exists but is **empty (0 rows)** in live data; `bankable_plans` and `benefit_realization_ledger` are also empty — so the migration/backfill risk in practice is concentrated in `financial_entries` (10 rows) and `financial_cost_lines` (9 rows). The expand/backfill/contract plan stands but is lower-risk than assumed at current data volumes. | Column listing + row counts |
| C5 | **Data hygiene:** the live tenant's `financial_config_items` contains ~13 leftover `ui_acceptance_category_*` / `acceptance_*` rows from browser acceptance tests (inactive but present). The acceptance-test teardown should clean these; worth a small chore issue. | `select * from transmuter.financial_config_items` |
| C6 | Initiatives already have `initiative_code` (unique per tenant) — the workbook's `TOR-1`/`EBR-3` references map directly. No change needed; noted because `productupgrade.md` didn't mention it. | `initiatives_tenant_id_initiative_code_key` |

---

## 3. Sheet-by-sheet fit assessment

### 3.1 Initiative Summary (21 initiatives, 4 regions)

| Workbook element | Current support | With upgrade plan | Gap? |
|---|---|---|---|
| Reference (TOR-1…), Name, Workstream, Owner, Priority, RAG, Type, Tag, Planned Completion | ✅ all exist (`initiative_code`, `workstream_id`, `owner_id`, `priority`, `rag_status`, `type`, `tag`, `planned_end`) | ✅ | No |
| Type values `cost_reduction` / `revenue` | ✅ enum has `cost_reduction`, `revenue_growth` (label mapping only) | ✅ | No |
| **Business Units, multi-valued** ("GROUP, CAL, VER") | ❌ BU reachable only via `workstreams.business_unit_id` (one BU per workstream; initiative has no BU FK at all) | ❌ not addressed | **Yes → A2** |
| **Stage = "3"** (of 5 gates) | ❌ `stage` CHECK allows 3 values; `stage_gates.gate_number` CHECK allows only 1–2; `gate_criteria` seeded for gates 1–2 only | ❌ not addressed | **Yes → A1** |
| Summary value columns parameterised by **"Base Run Rate Year ▶ FY28"** and **"Case ▶ Base"** | 🟡 run-rate annualization exists but no selectable run-rate year; scenario fixed | ✅ scenario selectable; run-rate year still missing | **Yes → A5** |
| **Baseline FY25 column** (prior-year baseline per metric) | ❌ no baseline concept | 🟡 scenario model can host it | **Yes → A5** |
| Counts of milestones/KPIs/risks/actions/updates | ✅ all tables exist | ✅ | No |

### 3.2 Charter Details

| Workbook field | Current support | Gap? |
|---|---|---|
| Name, Reference, Stage gate, RAG, Priority, Type, Tag, Workstream, Owner, Planned/Actual Completion | ✅ | No |
| Description / **Context & Problem** / Value Logic & Assumptions | 🟡 `summary` + `value_logic` exist; **no separate "context & problem" field** (workbook keeps Description and Context & Problem distinct) | **Yes → A6** |
| **Workstream Lead / Workstream Sponsor** | ❌ `workstreams` has only `name` + `business_unit_id`; no lead/sponsor user FKs | **Yes → A6** |
| Initiative Value (Base / High, USD m) | ✅ derivable from financial summary (net value run-rate per case) | No |

### 3.3 Financial Summary (per initiative, annual FY26–FY31 + All Years + FY25 baseline)

| Workbook element | Current support | With upgrade plan | Gap? |
|---|---|---|---|
| Revenue / GM Plan Base, Plan High, Actual per FY | ✅ system metrics + scenarios | ✅ | No |
| Cost Plan / Cost Actual per FY | ✅ cost lines | ✅ | No |
| Net Value Base / High / Actual | ✅ computed (`net_value` rollup) | ✅ definition-driven | No |
| Multi-year horizon (6 years) + "All Years" total | ✅ (`year` 2020–2040) | ✅ | No |
| **ROI (Actual, %)** row | ❌ not computed | ✅ formula metric (`net_value_actual / cost_actual`) — seed it as a system formula metric | No (covered; add to seed list) |
| **FY25 Baseline column** | ❌ | 🟡 | **Yes → A5** |
| FY labels (FY26 = Jan–Dec 2026 here) | ✅ calendar; upgrade adds fiscal-start-month for tenants that need it | ✅ | No |

### 3.4 Benefits sheet — the most instructive sheet

Structure: one row per **(named benefit line × lane)** with columns `Name, Lane (Plan Base | Plan High | Actual), Benefit Type (Revenue | Gross Margin), Denomination (USD | %), P&L Line, Impact Type (Recurring), Timing (Immediate), Confidence, Description`, hidden system columns (`_id`, `_value_translation`, `_sort_order`, `_is_draft`, `_metadata.show_in_summary`, `_created_at/_updated_at` — this workbook is itself an export of an Alchemist-style system, which is good news for #140 import compatibility), then annual FY columns + **72 monthly columns** (FY26-Jan … FY31-Dec).

| Workbook concept | Mapping | Gap? |
|---|---|---|
| Lane = Plan Base / Plan High / Actual | = `financial_scenarios` exactly | No (validates the design) |
| Denomination USD vs % | = `value_type` currency vs percent | No (validates the design) |
| Monthly values over 6 years | = monthly-only `financial_metric_values_v2` | No |
| Benefit Type (Revenue / Gross Margin) | = definition `group` / `benefit_class` | No |
| **Named, initiative-specific benefit lines** — e.g. TOR-6 has "Revenue Uplift from Improved Retention" alongside the standard "Revenue Uplift"; 5 distinct names across the portfolio, 2 of them initiative-specific | ❌ current + planned model only has tenant-level metric definitions; an initiative cannot have two differently-named lines of the same metric, nor a locally-named line | **Yes → A3 (key adjustment)** |
| **`_value_translation` (mode: none)** — % lines translatable into USD (e.g. GM-uplift-% applied to a baseline) | ❌ nothing equivalent | **Yes → A5 (baseline) + formula metrics cover the computed direction; "translation modes" beyond formulas are out of scope v1 — document as such** |
| Impact Type (Recurring) / Timing (Immediate) / Confidence / P&L Line per benefit line | 🟡 initiative-level `impact_type` + `benefit_confidence` exist; nothing line-level | **Yes → A3 carries these as line attributes** |
| `show_in_summary` flag | 🟡 ≈ `initiative_financial_selections` is_active | Minor — selection model already covers intent |

### 3.5 Costs sheet

Structure: one row per **(cost line × lane Plan/Actual)** with `Name, Plan Mode (One-off | Manual | Annual spread), Amount, Start FY/Month, End FY/Month, Lump Month, Inflation %, Cost Category, P&L Line, Service Line, Timing, Confidence, Impact Type (One-off | Recurring)` + monthly columns.

| Workbook concept | Mapping | Gap? |
|---|---|---|
| Named cost lines with category + recurring/one-off | ✅ `financial_cost_lines` (name, category_key, is_recurring) | No |
| Plan vs Actual lanes | ✅ `amount_plan` / `amount_actual` | No |
| Monthly phasing | ✅ month column exists | No |
| **Plan Mode: One-off (amount @ month) / Annual spread (annual amount ÷ months) / Manual (type each month)** with Start/End FY-Month and Lump Month | ❌ today every monthly cell is typed by hand (one row per period) | **Yes → A4 (key adjustment)** |
| **Inflation % escalator** | ❌ | **Yes → A4 (phase-2 option of the spreading engine)** |
| P&L Line / Service Line attributes | ❌ | **Yes → A7 (generic line attributes)** |

### 3.6 Dashboards sheet (the required dashboards)

Two dashboards are specified (the workbook's own to-do list says the second is *not yet built even in Excel* — "build in-year value dashboard"):

**D1 — Run-rate value ramp of completed initiatives.** Monthly buckets Jul-2026 → Dec-2027, rows = workstreams + total. *Plan variant:* cumulative run-rate value where each initiative's value lands in the month of its **planned completion date**, using the **plan locked on a selected date**. *Actual variant:* same, by **actual completion date and actual value**.
- Current support: ❌ no screen computes value-by-completion-date ramps. Ingredients all exist or are planned: run-rate value per initiative (summary), `planned_end` / `actual_end`, bankable plan versions (plan-as-of-date), workstream grouping.
- → **A8** (new dashboard + one endpoint). Note this is closely related to, but distinct from, the in-flight Waterline screen (#207): waterline = pipeline by gate stage vs locked line; D1 = time-phased completion ramp.

**D2 — In-year value of initiatives.** Annual FY26–FY30 + monthly columns, rows = workstreams × {Revenue, Gross Margin, Cost Plan, Net Value}. *Plan variant:* "locked on [selected date] — based on initiatives in Gate 3+". *Actual variant:* "**regardless of which initiatives delivered it**".
- Current support: 🟡 Portfolio Financials already does monthly/quarterly/yearly plan-vs-actual with workstream filters and benefit/cost/net rows — ~70% of D2.
- Missing: (a) **plan-as-of-date** — render the portfolio from bankable-plan snapshots whose lock date ≤ a selected date, instead of the live editable plan; (b) **stage filter** ("Gate 3+ only") on the portfolio query; (c) the "actuals regardless of initiative" phrasing implies actuals may be captured **at workstream level when attribution is unclear** — today actuals only enter per initiative.
- → **A8** (a, b are straightforward; c is a product decision — recommend a lightweight "unattributed actuals" entry at workstream level, see A8).

### 3.7 `config` sheet (the client's own configurability checklist)

Configurable per the client: workstreams ✅ done, financial impact types ✅ done, initiative tags ✅ done, **approval flows** (open — partially covered by gate criteria + the upgrade's finance sign-off feature), **stage-gate progression requirements/checklists** ✅ gate criteria exist. Fixed per the client: **5 stage gates** → A1.

---

## 4. Adjustments to the recommended upgrade (the delta)

These extend `productupgrade.md`; section references are to that document.

### A1 — Five-stage-gate lifecycle (extends §4.4.1) — **High priority**
The live constraints `initiatives.stage IN ('scoping','in_progress','complete')`, `stage_gates.gate_number IN (1,2)`, and `gate_criteria` seeded for gates 1–2 cannot represent the client's fixed 5-gate model (workbook initiatives are "Gate 3"). Change:
- Replace the 3-value `stage` enum with a tenant-configurable **stage set** (seeded default: L1 Identify → L2 Validate → L3 Plan/Commit → L4 Execute → L5 Realized; 5 gates between/closing them), stored as config (e.g., `stage_gate_definitions` per tenant: gate_number 1–N, label, from/to stage, criteria) rather than CHECK constraints.
- Relax `stage_gates_gate_number_check` and `gate_criteria` to N gates; `FinancialGovernanceSettings.initiative_plan_lock_gate_number` already supports 1–10, so plan-lock-on-gate-K works unchanged.
- This merges with the maturity-stage recommendation: gates **are** the L1–L5 funnel (per C3, wire `realization_status` transitions to gate approvals instead of inventing a parallel stage field).
- Migration: map existing `scoping→L1–L2`, `in_progress→L3–L4`, `complete→L5`; existing gate 1/2 submissions keep their numbers.

### A2 — Many-to-many initiative ↔ business units — **High priority**
Workbook initiatives span multiple BUs ("GROUP, CAL, VER") and BU is independent of workstream (workstream = region). Add `initiative_business_units (tenant_id, initiative_id, business_unit_id, UNIQUE(initiative_id, business_unit_id))`; keep `workstreams.business_unit_id` as an optional default; portfolio filters accept multiple BUs; create/edit flow gets a BU multi-select. (Without this, the workbook's GROUP-level retention initiatives can't be represented.)

### A3 — Initiative-level **benefit lines** (adjusts §4.1) — **High priority, design-level**
The workbook treats benefits symmetrically to costs: an initiative holds *named lines* ("Revenue Uplift from Improved Retention"), each referencing a benefit type, with its own denomination, recurring/one-time flag, timing, confidence, and description. The upgrade plan as written attaches values directly to tenant-level definitions, which cannot express two lines of the same metric or initiative-local names. Adjustment:

```sql
CREATE TABLE transmuter.financial_benefit_lines (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL,
  initiative_id UUID NOT NULL REFERENCES transmuter.initiatives(id) ON DELETE CASCADE,
  metric_definition_id UUID NOT NULL REFERENCES transmuter.financial_metric_definitions(id),
  name TEXT NOT NULL,                -- defaults to the definition label
  description TEXT,
  impact_type TEXT CHECK (impact_type IN ('recurring','one_time')),
  timing TEXT,                       -- e.g. 'immediate', 'ramped'
  confidence NUMERIC(5,2),
  attributes JSONB NOT NULL DEFAULT '{}',   -- P&L line, service line, etc. (see A7)
  show_in_summary BOOLEAN NOT NULL DEFAULT TRUE,
  display_order INTEGER NOT NULL DEFAULT 0,
  created_by UUID, updated_by UUID, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ
);
-- financial_metric_values_v2 gains: benefit_line_id UUID NULL REFERENCES financial_benefit_lines(id)
--   (NULL = the plain "one line per definition" case; uniqueness becomes
--    UNIQUE NULLS NOT DISTINCT (initiative_id, metric_definition_id, benefit_line_id, scenario_id, year, month))
```

Default UX stays simple (selecting a metric auto-creates one line named after it); power users add extra named lines. Rollups group by `metric_definition_id`, so summaries/bridge/portfolio are unaffected. This also makes benefits and costs symmetrical (cost lines already work this way via `category_key`).

### A4 — Phasing/spreading engine for cost (and benefit) lines — **High priority**
Replace hand-typed monthly cells as the only entry mode. Per line, an optional plan-entry rule:
- `plan_mode: manual | one_off | even_spread | annual_spread`, with `amount`, `start_year/start_month`, `end_year/end_month`, `lump_month`, and (v2) `inflation_pct`.
- The rule **generates** the monthly rows in `financial_metric_values_v2` / cost-line periods (stored expanded, so all rollups are unchanged); editing a generated cell flips the line to `manual` (or stores an override — recommend flip-to-manual for v1 simplicity, matching the workbook's Manual mode).
- Store the rule on the line (`phasing JSONB`) so it can be re-run when dates shift. Applies to `financial_cost_lines` first (workbook usage) and `financial_benefit_lines` for parity.
- Frontend: a small "phasing" popover per line (mode, amount, range) above the grid; Actual lanes always manual.

### A5 — Baseline scenario + run-rate-year reporting parameter — **Medium priority**
The workbook carries a **FY25 baseline** per metric and renders summary value columns for a **selected run-rate year** ("Base Run Rate Year ▶ FY28") and **selected case** ("Case ▶ Base"). Adjustments:
- Seed a fourth system scenario `baseline` (`kind='plan'`, flagged `is_baseline`) so baseline-year values are first-class data, enterable per metric (the workbook's "calibrate baseline" to-do). Uplift-vs-baseline then becomes expressible as formula metrics.
- Add `run_rate_year` as a report parameter (query param on summary/portfolio endpoints + a year selector in the UI): "run-rate value" = the selected scenario's value in that year, replacing the current implicit annualization. Default = first fully-ramped year.
- This also future-proofs the `_value_translation` concept: %-denominated metrics with a baseline can be translated to $ via formula (pct × baseline) without a bespoke translation engine. Anything beyond that (workbook shows only `mode:"none"`) is explicitly out of scope.

### A6 — Charter & workstream fields — **Low effort, do with Phase 6**
- Add `context_problem TEXT` to `initiatives` (workbook keeps Description and Context & Problem distinct; today only `summary` + `value_logic` exist). Surface in create-flow step 2 and the Overview tab.
- Add `lead_user_id` and `sponsor_user_id` to `workstreams` + admin Strategic Parameters UI fields (workbook Charter rows "Workstream Lead", "Workstream Sponsor").

### A7 — Generic line attributes (P&L Line, Service Line) — **Low priority**
Rather than new columns per attribute, add a tenant-configurable attribute registry (reuse `strategic_parameters`-style settings: list of attribute keys with allowed values) rendered as dropdowns on benefit/cost lines and stored in the line's `attributes JSONB`. Covers the workbook's P&L Line / Service Line / Timing without schema churn, and is filterable in portfolio queries via JSONB containment.

### A8 — Two new dashboards (extends §4.4 / issue #208 scope) — **Medium priority**
1. **Run-rate value ramp** (`GET /portfolio/value-ramp?basis=plan|actual&as_of=<lock-date>&granularity=monthly`): for each month, cumulative run-rate value of initiatives whose (planned|actual) completion date ≤ month-end, grouped by workstream; plan basis reads bankable-plan snapshots locked on/before `as_of`. Chart: stacked area/line by workstream + total, plan vs actual overlay.
2. **In-year value dashboard**: extend Portfolio Financials with (a) `as_of` plan-snapshot mode (resolve each initiative's bankable plan version at the selected date; fall back to live plan for unlocked initiatives, clearly badged), (b) a minimum-gate/stage filter ("Gate 3+"), and (c) rows = Revenue / GM / Cost / Net per workstream — already definition-driven post-upgrade.
3. **Unattributed actuals (product decision needed):** the workbook tracks actuals "regardless of which initiatives delivered it". Recommend a thin `workstream_actuals` entry (workstream × metric definition × month × value) included in portfolio actual rows with an "unattributed" tag — keeps initiative-level attribution honest instead of forcing fake allocations. If not wanted, document that actuals must always be attributed to an initiative.

---

## 5. Things the workbook confirmed the plan already gets right

- **Scenario table ≅ "Lane"** (Plan Base / Plan High / Actual) — exact match, including tenants that may want more/fewer lanes.
- **`value_type` ≅ "Denomination"** (USD vs %) including mixed-denomination metric sets (GM $ + GM uplift %).
- **Monthly-as-source-of-truth with computed FY rollups** — the workbook stores 72 monthly columns and computes FY totals, exactly the proposed model; its FY26-Jan…Dec layout also validates the fiscal-year-start-month design (here FY = calendar).
- **ROI as a formula metric** — the Financial Summary's "ROI (Actual, %)" row falls out of the formula engine; add `roi_actual` to the system seed list.
- **Cost categories + recurring/one-off** — already fully covered.
- **Alchemist-format kinship** — the Benefits/Costs sheets carry `_id`/`_metadata` system columns from an Alchemist-style export; the #140 workbook import pathway plus the upgrade's definition-driven XLSX engine is the right vehicle for ingesting files like this one. Add this exact workbook to the import acceptance fixtures.

---

## 6. Impact on the phased roadmap (`productupgrade.md` §6)

| Adjustment | Lands in | Note |
|---|---|---|
| C1 (schema `transmuter`), C2 (`reporting_currency`) | Phase 1 | Correct DDL targets; add currency column |
| A3 benefit lines (table + `benefit_line_id` on values) | Phase 1 (schema) + Phase 4 (rollups group by definition) + Phase 5 (grid rows per line) | Cheap if designed in now; expensive to retrofit |
| A5 baseline scenario + ROI seed | Phase 1 (seeds) + Phase 4 (`run_rate_year` param) | |
| A1 five-gate lifecycle | New **Phase 2b** (parallel to Phase 2; touches governance, not the metric engine) | Prahari review (roles/approvals); merges maturity-stage work from §4.4.1 |
| A2 initiative ↔ BU M:N | Phase 2b | Small, but touches create flow + portfolio filters |
| A4 phasing engine | New **Phase 5b** (after dynamic grid exists) | Backend rule-expansion + grid popover |
| A6 charter/workstream fields | Phase 6 | Trivial adds |
| A7 line attributes | Phase 6 | JSONB + settings registry |
| A8 dashboards | New **Phase 6b** (with #208) | Needs Phase 4's snapshot-as-of-date adapter |
| C5 test-data hygiene | Standalone chore issue | Acceptance teardown fix |

Revised completion read: the workbook does not change the **55–60%** core assessment, but it shifts emphasis — the governance/lifecycle dimension (5 gates, BU mapping, baseline, dashboards) is further from done than the metric engine itself, and should be planned as the parallel track above rather than bolted onto the metric-engine phases.
