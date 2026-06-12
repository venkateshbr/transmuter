# Product Upgrade Plan: Fully Configurable Financial Metrics & Value Realization

**Date:** 2026-06-11
**Scope:** Initiative financials, admin financial configuration, monthly data entry with quarter/year rollups, portfolio reporting, value realization tracking.
**Goal:** Every tenant defines its own financial metrics (revenue, GM uplift $ / GM %, cost savings, costs, …) in the Admin menu. Those metrics appear at initiative creation, users enter values **monthly**, and the data rolls up automatically to **quarter** and **year** — turning Transmuter into a fully SaaS-grade enterprise transformation platform with per-tenant value-realization models.

---

## 1. Executive Summary

### 1.1 Completion assessment: ~55–60%

The stated assumption was 60–70% complete. After a full review of the schema, backend, frontend, and GitHub issues, my assessment is **slightly lower: 55–60%** against the *fully configurable* vision. The plumbing is excellent — the configurability layer is the gap.

| Capability | Status | Notes |
|---|---|---|
| Multi-tenant isolation (RLS, `tenant_id` everywhere) | ✅ Done | Every financial table scoped; policies consistent |
| Money correctness (`NUMERIC(15,4)`, `Decimal`, string JSON) | ✅ Done | No float anywhere in the financial path |
| Cost categories (tenant-configurable) | ✅ Done | `financial_config_items` + `category_key` on cost lines; add/rename/delete with migration |
| Metric rename / hide / reorder | ✅ Done | Admin Financial Configuration tab |
| Per-initiative metric/cost scoping | ✅ Done | `initiative_financial_selections`, create-flow step 3 |
| Bankable plan lock + versioning | ✅ Done | Immutable JSONB snapshots, gate-approval trigger, rebaseline |
| Benefit realization ledger | ✅ Done | Weekly/monthly/yearly actuals vs locked plan, variance |
| Portfolio rollups, value bridge, break-even | ✅ Done | But structure is hardcoded (see below) |
| Scenarios (base / high / actual) | 🟡 Partial | Fixed triplet baked into column names; not tenant-definable |
| Monthly entry → quarter/year rollup | 🟡 Partial | Monthly, quarterly, and annual rows coexist in one table; service dedupes at read time; quarterly rollup is implicit, not a first-class computed view |
| **Tenant-defined metrics (the core ask)** | ❌ Missing | 24 hardcoded columns on `financial_entries` (`revenue_uplift_*`, `gross_margin_*`, `gm_uplift_*`, `cogs_*` × base/high/actual × $/%) mirrored by a hardcoded `METRICS` array in the frontend. `financial_metric_values` exists as a generic escape hatch but is second-class (no type, unit, formula, or rollup semantics) |
| Metric semantics (type, unit, direction, aggregation) | ❌ Missing | No way to say "this is a %, average it" vs "this is $, sum it" |
| Derived/formula metrics (GM % = GM $ / Revenue) | ❌ Missing | % values are manually entered, can drift from $ values |
| Configurable value bridge | ❌ Missing | `ValueBridgeCase` has fixed fields (revenue_uplift, gross_margin, gm_uplift, other_benefits, cogs, costs) |
| Fiscal year / currency configuration | ❌ Missing | Calendar year and USD assumed everywhere (frontend hardcodes `currency: 'USD'`) |
| Audit columns on financial entries | ❌ Missing | No `created_by`/`updated_by` on `financial_entries` / `financial_cost_lines` |
| Benefit maturity stages (Wave L1–L5 style) | ❌ Missing | Stage-gates exist but benefits are not staged by confidence/maturity |

### 1.2 Top 10 recommendations (priority order)

1. **Introduce `financial_metric_definitions`** — a first-class, tenant-scoped metric registry with `value_type`, `unit`, `direction`, `aggregation`, `rollup_type`, `is_benefit`, `cost_behavior`, and optional `formula`. This replaces both the hardcoded `financial_entries` columns and the `system_metric_key` indirection in `financial_config_items`. (§4.1)
2. **Make monthly the single source of truth** in a new `financial_metric_values_v2` table; compute quarter and fiscal-year rollups (never store them), with aggregation semantics per metric (`sum` for $, recomputed `formula` for %). (§4.1, §4.2)
3. **Introduce `financial_scenarios`** — tenant-definable scenario sets (seeded base/high/actual) so tenants who only want plan-vs-actual aren't forced into a three-scenario model. Aligns with the existing `FinancialModeDescriptor` / issue #206. (§4.1)
4. **Build the Admin Metric Builder UI** — create/edit metrics, scenarios, fiscal year, currency, and value-bridge rows; extract from the 1,650-line `admin.component.ts` into `features/admin/financial-config/`. (§4.3)
5. **Generate the financial entry grid dynamically** from metric definitions — delete the hardcoded `METRICS` array in `financials-tab.component.ts`; monthly entry cells with read-only computed quarter/FY subtotal columns. (§4.3)
6. **Formula engine for derived metrics** — safe Decimal-only evaluator; GM % computed from GM $ / Revenue at every grain (month, quarter, year), eliminating manual % entry drift. (§4.2)
7. **Migrate with expand → backfill → contract** — dual-write window with nightly reconciliation; never rewrite locked bankable-plan snapshots (version the snapshot schema instead). (§5)
8. **Add benefit maturity stages** (identified → validated → planned → executing → realized, Wave L1–L5 style) on top of the existing gate machinery, so portfolio reporting can show a value funnel and quantify value leakage between stages. (§4.4)
9. **Add audit columns + finance sign-off on actuals** — `created_by`/`updated_by` on all value tables, plus an optional per-tenant approval step before actuals count as "realized" (Sievo/finance-credibility pattern). (§4.4)
10. **Configurable value bridge** — bridge rows defined per tenant (`financial_bridge_rows`), seeded to match today's structure, rendered dynamically. (§4.1, §4.3)

### 1.3 Relationship to in-flight work

Open issue **#206 — "Backend: make financial model, scenarios, and rollups configuration-driven"** (epic #203) already asks for exactly this direction, and `docs/team/BANKABLE_PLAN_IMPLEMENTATION_ROADMAP.md` proposes `financial_templates` / `initiative_financial_models` tables. **This document is the detailed design for #206 and its frontend siblings (#207, #208), not a competing plan.** Recommendation: treat "financial templates" (named reusable definition sets) as a v2 follow-on; this plan delivers the per-tenant definition layer that templates would later package.

---

## 2. Current-State Review

### 2.1 Data model (what exists)

All in `supabase/migrations/`, all with tenant RLS:

| Table | Purpose | Key observation |
|---|---|---|
| `financial_entries` | Per-initiative period rows: `(initiative_id, year, quarter NULL, month NULL)` unique | **24 hardcoded metric columns**: `revenue_uplift_{base,high,actual}`, `revenue_uplift_pct_*`, `gross_margin_*`, `gm_pct_*`, `gm_uplift_*`, `gm_uplift_pct_*`, `cogs_*`, `cogs_pct_*`. Annual/quarterly/monthly rows coexist; service deduplicates at read time |
| `financial_cost_lines` | Cost line items: name, `category_key`, period, `amount_plan`, `amount_actual`, `is_recurring` | Already fully generic — keep as-is |
| `financial_config_groups` / `financial_config_items` | Tenant config: groups (calculation/metric/cost_category), items with `system_metric_key` → hardcoded column mapping, `rollup_type` (benefit/recurring_cost/one_off_cost/total_cost/net_value), rename/hide/reorder | Configuration **of presentation**, not of substance — can't add a real new metric |
| `financial_metric_values` | Generic custom metrics: `metric_key`, period, `value_{base,high,actual}` | The escape hatch — but no type/unit/aggregation/formula semantics; second-class in summaries, bridge, XLSX |
| `initiative_financial_selections` | Per-initiative soft scoping of metrics/cost categories | Keep; re-key to new definitions |
| `bankable_plans` | Versioned immutable JSONB snapshots, locked on gate approval, rebaseline support | Keep; snapshots reference the old row shape — needs schema versioning |
| `benefit_realization_ledger` | Weekly/monthly/yearly realized amounts vs locked plan | Metric-agnostic (single amount) — unaffected |
| `financial_forecasts` | Post-lock outlook per `line_key` | Keep; `line_key` becomes a definition key |
| `financial_cell_assumptions` | Per-cell comments keyed by `row_key`/`column_key` | Keep; key format becomes `metric:{key}:{scenario}` |
| `workstream_target_locks` | Frozen workstream targets, run-rate basis | Stores derived values — unaffected |

Governance settings (`FinancialGovernanceSettings`) live in `organizations.settings` JSONB: lock gate number, lock-on-approval, rebaseline roles, workstream lock cadence, valuation basis.

### 2.2 Backend (what exists)

- `apps/api/app/domain/financials.py` — Pydantic models; `FinancialScenario = Literal["base","high","actual"]` and `FinancialEntryRow` hardcode the metric set; `FinancialModeDescriptor` (`pre_lock | planned_vs_actual | multi_scenario | bankable_locked`) already anticipates mode-aware reporting.
- `apps/api/app/services/financial.py` — the heart: `_ENTRY_FIELDS` constant enumerates the hardcoded columns; `_compute_summary` does monthly/quarterly dedup in Python with Decimal; portfolio rollups, value bridge (`get_value_bridge` with fixed `ValueBridgeCase` shape), break-even, scenario summary, XLSX import/export, bankable plan snapshot/restore, benefit ledger summaries, workstream target locks.
- `apps/api/app/routers/financials.py` — ~40 endpoints: grid CRUD, cost lines, selections, assumptions, forecasts, bankable plan, benefit ledger, portfolio financials/contributors, value bridge, workstream targets, admin financial-configuration + governance.
- Strengths: clean Router → Service → Repository layering; Decimal everywhere; permission checks (`can_view_initiative`, `can_manage_initiatives`, `can_view_portfolio`); transformation_office gating on locks.

### 2.3 Frontend (what exists)

- `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts` (~1,000+ lines) — Handsontable grid; **hardcoded `METRICS` array** mirroring the DB columns; scenario toggle (base/high/actual); quarterly-summary vs detailed-entry views; cell assumptions modal; XLSX export/import; summary cards.
- `apps/web/src/app/features/admin/admin.component.ts` (~1,650 lines) — 8 tabs; Financial Configuration tab supports renaming/hiding/reordering metrics, cost-category CRUD, calculation groups; Governance Engine tab for gate criteria.
- `apps/web/src/app/features/initiatives/create/create-initiative.component.ts` — step 3 loads `/financial-configuration` and offers metric/cost-category checkboxes (defaults: revenue uplift + GM uplift + implementation + maintenance).
- `apps/web/src/app/features/financials/` — portfolio financials (granularity toggle monthly/quarterly/yearly, contributors drawer), benefit tracking, bankable plan review, waterline (stub), value waterfall component.
- `formatMoney()` in `financials-view.models.ts` **hardcodes `currency: 'USD'`**.

### 2.4 GitHub issue landscape

| Issue | State | Relevance |
|---|---|---|
| #203 [Epic] Bankable plan baseline & benefit realization | OPEN, in-qa | Umbrella for #204–#209 |
| #204 Bankable plan model + lock-on-approval | OPEN, in-qa | Backend largely present in code already |
| #205 Benefit realization ledger + frequency rollups | OPEN, in-qa | Present in code |
| **#206 Config-driven financial model, scenarios, rollups** | OPEN, in-qa | **This document = detailed design for #206** |
| #207 Bankable plan / benefit tracking / waterline screens | OPEN, in-qa | Screens exist; waterline incomplete |
| #208 Mode-aware dashboard/portfolio/control tower | OPEN, in-qa | Depends on #206 contract |
| #209 Migration, seeding, acceptance tests | OPEN, in-progress | Phase gating for this plan too |
| #146/#191/#165/#160/#140 | CLOSED (PR #158, #193) | Delivered config groups/items, run-rate semantics, scope selections, monthly-entry UX, Alchemist workbook |

Discrepancy worth fixing while creating new issues: #203–#208 are labeled `in-qa` with no merged PRs — re-triage labels before layering the new work packages on top.

### 2.5 Gap list (severity-ranked)

| # | Gap | Severity | Why it matters |
|---|---|---|---|
| G1 | Metrics hardcoded as DB columns + frontend array | **Critical** | Blocks the entire per-tenant configurability vision; every new metric today = migration + code change in 4 layers |
| G2 | No metric semantics (type/unit/direction/aggregation) | **Critical** | Can't roll up correctly without knowing sum-vs-average; can't render correctly without unit |
| G3 | No derived/formula metrics | High | % metrics manually entered → drift from $ values; reconciliation bugs already fixed once (#160) |
| G4 | Mixed-grain storage (annual+quarterly+monthly rows) with read-time dedup | High | Fragile; double-count bugs; rollup logic duplicated across summary/portfolio/bridge paths |
| G5 | Fixed scenario triplet | High | Tenants wanting plan-vs-actual only, or adding a "downside" case, can't |
| G6 | Hardcoded value bridge structure | High | Bridge must reflect tenant's own metric taxonomy |
| G7 | No fiscal year / currency configuration | Medium | FY-start-month is table stakes for enterprise; USD hardcoded in UI |
| G8 | No audit columns on entries/cost lines | Medium | Finance credibility requires who-changed-what |
| G9 | No benefit maturity stages / value funnel | Medium | Industry-standard (Wave L1–L5); needed for credible exec reporting |
| G10 | XLSX round-trip assumes fixed columns | Medium | Breaks once metrics are dynamic |
| G11 | No multi-currency / FX | Low (roadmap) | Defer; design for it (currency on org now, per-entity later) |
| G12 | Quarterly rollups recomputed per request in Python | Low | Fine at current scale; SQL view solves it as a side effect of G4 |

---

## 3. Industry Benchmark: What Transformation Platforms Capture

### 3.1 Patterns observed

**McKinsey Wave** — the reference standard for transformation value tracking:
- Initiatives progress through **L1–L5 benefit maturity stages**: L1 identified/estimated → L2 validated business case → L3 planned with execution milestones → L4 milestones complete/finance-assessed → L5 value realized in actual cash flows / P&L.
- McKinsey's own data: L1 estimates fall ~45% by L2, ~70% cumulatively by L5 — which is exactly why staged tracking matters: it quantifies **value leakage** between stages.
- Baselines, targets, and **attribution rules agreed with Finance up front**; impact tracked **weekly (leading indicators)** and **booked monthly (lagging)** against a transparent **value bridge**.

**Shibumi** — the configurability benchmark: tracks "metrics of any description," financial (ROI, cost savings) and non-financial (CSAT, efficiency), with per-client metric definitions, benefit types/categories, and forecast-vs-realized tracking through execution stages.

**Sievo / Per Angusta** (savings-tracking specialists): three value states — **forecasted → realized → avoided**; finance-agreed **calculation methodology per metric** (vs historic baseline, vs budget, vs benchmark); separation of controllable vs non-controllable factors (price vs volume/market/FX); **approval workflow with audit trail at every stage**; fiscal-year phasing (a deal closed in June realizes savings July→June across two fiscal years).

**General taxonomy** common across Planview-class benefits-realization tools:
- Benefit types: recurring cost savings (EBITDA/run-rate), one-time savings, **cost avoidance** (distinct — spend that never happened), revenue uplift, margin uplift, working capital, capex reduction.
- Series per metric: **baseline → target → forecast → actual**, time-phased monthly with multi-year ramps.
- Run-rate vs in-year P&L impact distinguished (Transmuter's #191 already adopted this — good).
- Reporting: value waterfall/bridge, initiative pipeline by stage (funnel), plan-vs-actual variance trends.

### 3.2 Implications for Transmuter

| Benchmark practice | Transmuter today | Action in this plan |
|---|---|---|
| Configurable metric definitions per client | Rename/hide only | §4.1 metric definitions |
| Recurring vs one-time, benefit vs cost semantics | Partial (#191, cost lines) | `is_benefit`, `cost_behavior`, `rollup_type` on definitions |
| Cost avoidance as distinct type | Missing | A `rollup_type='benefit'` + `benefit_class='avoidance'` tag (§4.4) |
| Benefit maturity stages + leakage | Gates exist, no value staging | §4.4 maturity stages |
| Baseline/target/forecast/actual series | base/high/actual + separate forecasts table | Scenario `kind` + semantics (§4.1) |
| Finance sign-off on actuals + audit | Missing | §4.4 |
| Monthly phasing, fiscal calendar | Calendar-year only | `fiscal_year_start_month` (§4.1) |
| Value bridge | Hardcoded | `financial_bridge_rows` (§4.1) |

Sources: [McKinsey — Keeping transformations on target](https://www.mckinsey.com/capabilities/rts/our-insights/keeping-transformations-on-target), [Wave by McKinsey](https://www.mckinsey.com/capabilities/transformation/how-we-help-clients/wave/overview), [Shibumi — Critical Capabilities](https://shibumi.com/critical-capabilities/), [Shibumi product](https://shibumi.com/product/), [Sievo — Initiative Management](https://sievo.com/products/initiative-management), [Sievo — Procurement savings tracking](https://sievo.com/blog/procurement-savings-tracking), [Suplari — Realized savings](https://suplari.com/blog/realize-savings-in-procurement-how-to-prove-what-your-team-actually-delivered), [SpendHQ — Savings vs avoidance](https://www.spendhq.com/blog/tracking-cost-savings-and-cost-avoidance-to-measure-procurements-performance/), [Planview — Benefits realization](https://success.planview.com/Planview_Enterprise/Resource_Center/Best_Practices/1.62.0_Benefits_Realization_at_a_Glance).

---

## 4. Target Architecture: The Configurable Metric Engine

**Headline decision: migrate fully to a generic metric store; do not keep the hybrid.** The hybrid (hardcoded columns + `financial_metric_values` side-table) is the source of most current complexity: `_ENTRY_FIELDS`, the `system_metric_key` indirection, and duplicated scoping/summary code paths. Volume is low (per-initiative monthly planning rows, not telemetry), so EAV performance concerns don't apply with a proper covering index. Every future feature (formulas, scenarios, currency, audit, sign-off) gets built **once** instead of twice.

### 4.1 (a) Data model

New migrations in `supabase/migrations/`, RLS pattern copied verbatim from `20260508000001_financial_configuration.sql` (SELECT for tenant members, writes for `transformation_office`).

```sql
-- 1. Metric registry (replaces metric-type financial_config_items + the 24 columns)
CREATE TABLE financial_metric_definitions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       UUID NOT NULL REFERENCES organizations(id),
  key             TEXT NOT NULL,                    -- stable slug: 'revenue_uplift'
  label           TEXT NOT NULL,
  description     TEXT,
  group_id        UUID REFERENCES financial_config_groups(id),  -- reuse existing groups
  value_type      TEXT NOT NULL CHECK (value_type IN ('currency','percent','number')),
  unit            TEXT,                             -- '%', 'FTE'; currency type falls back to org currency
  direction       TEXT NOT NULL DEFAULT 'increase_good'
                    CHECK (direction IN ('increase_good','decrease_good','neutral')),
  aggregation     TEXT NOT NULL DEFAULT 'sum'
                    CHECK (aggregation IN ('sum','avg','last','formula')),
  rollup_type     TEXT CHECK (rollup_type IN
                    ('benefit','recurring_cost','one_off_cost','total_cost','net_value')),
  is_benefit      BOOLEAN NOT NULL DEFAULT FALSE,   -- contributes to Total Benefits
  benefit_class   TEXT CHECK (benefit_class IN ('savings','avoidance','revenue','margin','other')),
  cost_behavior   TEXT CHECK (cost_behavior IN ('recurring','one_time')),
  formula         TEXT,                             -- 'gm_uplift / revenue_uplift * 100'
  formula_inputs  TEXT[] NOT NULL DEFAULT '{}',     -- referenced keys; validated acyclic at save
  precision       SMALLINT NOT NULL DEFAULT 4,
  display_order   INTEGER NOT NULL DEFAULT 0,
  applies_to      TEXT NOT NULL DEFAULT 'opt_in' CHECK (applies_to IN ('all','opt_in')),
  is_system       BOOLEAN NOT NULL DEFAULT FALSE,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  validation      JSONB NOT NULL DEFAULT '{}',      -- {"min":0,"max":100,"required_scenarios":["base"]}
  created_by UUID, updated_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (tenant_id, key)
);

-- 2. Tenant-defined scenarios (seeded: base, high, actual)
CREATE TABLE financial_scenarios (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  key           TEXT NOT NULL,                      -- 'base' | 'high' | 'actual' | 'downside' | …
  label         TEXT NOT NULL,
  kind          TEXT NOT NULL CHECK (kind IN ('plan','actual')),
  is_primary    BOOLEAN NOT NULL DEFAULT FALSE,     -- the plan-of-record among 'plan' scenarios
  display_order INTEGER NOT NULL DEFAULT 0,
  is_system     BOOLEAN NOT NULL DEFAULT FALSE,
  is_active     BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (tenant_id, key)
);
CREATE UNIQUE INDEX financial_scenarios_one_actual
  ON financial_scenarios (tenant_id) WHERE kind = 'actual' AND is_active;

-- 3. Values: MONTHLY is the only stored grain
CREATE TABLE financial_metric_values_v2 (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id),
  initiative_id         UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  metric_definition_id  UUID NOT NULL REFERENCES financial_metric_definitions(id),
  scenario_id           UUID NOT NULL REFERENCES financial_scenarios(id),
  year                  INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2060),
  month                 SMALLINT NOT NULL CHECK (month BETWEEN 1 AND 12),
  value                 NUMERIC(15,4) NOT NULL DEFAULT 0,
  note                  TEXT,                       -- e.g. 'backfilled-quarterly'
  created_by UUID, updated_by UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (initiative_id, metric_definition_id, scenario_id, year, month)
);
CREATE INDEX fmv2_lookup ON financial_metric_values_v2
  (tenant_id, initiative_id, metric_definition_id, scenario_id, year, month);

-- 4. Fiscal/currency settings
ALTER TABLE organizations
  ADD COLUMN fiscal_year_start_month SMALLINT NOT NULL DEFAULT 1
  CHECK (fiscal_year_start_month BETWEEN 1 AND 12);
-- organizations.currency already exists in core schema — surface it via the settings API + UI

-- 5. Rollup view: quarter & fiscal-year computed, never stored.
--    Non-formula metrics aggregate per their `aggregation`; formula metrics are
--    computed in the service layer at each grain FROM the rolled-up inputs
--    (GM% @ Q1 = sum(GM$ months)/sum(Rev months), NOT avg of monthly GM%).
CREATE VIEW financial_metric_rollups AS
  SELECT v.tenant_id, v.initiative_id, v.metric_definition_id, v.scenario_id,
         fy.fiscal_year, fy.fiscal_quarter,
         CASE d.aggregation
           WHEN 'sum'  THEN SUM(v.value)
           WHEN 'avg'  THEN AVG(v.value)
           WHEN 'last' THEN (ARRAY_AGG(v.value ORDER BY v.year DESC, v.month DESC))[1]
         END AS value
  FROM financial_metric_values_v2 v
  JOIN financial_metric_definitions d ON d.id = v.metric_definition_id
  JOIN organizations o ON o.id = v.tenant_id
  CROSS JOIN LATERAL (
    SELECT CASE WHEN v.month >= o.fiscal_year_start_month THEN v.year ELSE v.year - 1 END
             + CASE WHEN o.fiscal_year_start_month = 1 THEN 0 ELSE 1 END - 1 AS fiscal_year,
           ((12 + v.month - o.fiscal_year_start_month) % 12) / 3 + 1          AS fiscal_quarter
  ) fy
  WHERE d.aggregation <> 'formula'
  GROUP BY GROUPING SETS
    ((v.tenant_id, v.initiative_id, v.metric_definition_id, v.scenario_id, fy.fiscal_year, fy.fiscal_quarter),
     (v.tenant_id, v.initiative_id, v.metric_definition_id, v.scenario_id, fy.fiscal_year));

-- 6. Configurable value bridge (seeded to mirror today's fixed structure)
CREATE TABLE financial_bridge_rows (
  id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES organizations(id),
  key       TEXT NOT NULL,
  label     TEXT NOT NULL,
  row_kind  TEXT NOT NULL CHECK (row_kind IN ('metric_set','cost_set','subtotal','net')),
  metric_definition_ids UUID[] NOT NULL DEFAULT '{}',
  cost_category_keys    TEXT[] NOT NULL DEFAULT '{}',
  sign      SMALLINT NOT NULL DEFAULT 1,            -- +1 benefit, -1 cost
  display_order INTEGER NOT NULL DEFAULT 0,
  UNIQUE (tenant_id, key)
);

-- 7. Snapshot schema versioning (never rewrite old locked snapshots)
ALTER TABLE bankable_plans ADD COLUMN snapshot_schema_version SMALLINT NOT NULL DEFAULT 1;
```

**Kept as-is (adapt keys only):** `financial_cost_lines` (already generic), `bankable_plans` mechanics, `benefit_realization_ledger` (metric-agnostic amounts), `financial_forecasts` (`line_key` → definition key), `financial_cell_assumptions` (`row_key` format → `metric:{key}:{scenario}`), `initiative_financial_selections` (`metric_keys` → definition keys), `workstream_target_locks`, governance settings.

**Deprecated at the end:** the 24 metric columns on `financial_entries`, `financial_config_items` rows with `item_type='metric'` (cost-category rows stay), `system_metric_key`, old `financial_metric_values`.

**Seed mapping (per existing tenant + `tenant_bootstrap.py` for new tenants):** the current 8 metric families become system definitions:

| Definition key | value_type | aggregation | is_benefit | Notes |
|---|---|---|---|---|
| `revenue_uplift` | currency | sum | ✅ benefit/revenue | |
| `gross_margin` | currency | sum | ✅ benefit/margin | |
| `gm_uplift` | currency | sum | ✅ benefit/margin | |
| `cogs` | currency | sum | — | |
| `revenue_uplift_pct` | percent | **formula** | — | becomes derived where possible; else `avg` |
| `gm_pct` | percent | **formula** (`gross_margin / revenue * 100`) | — | tenant can re-point inputs |
| `gm_uplift_pct` | percent | **formula** | — | |
| `cogs_pct` | percent | **formula** | — | |
| `cost_savings` | currency | sum | ✅ benefit/savings | already exists as custom metric |

Scenarios seeded: `base` (plan, primary), `high` (plan), `actual` (actual). The `{base,high,actual}` column triplet maps to (definition × scenario) pairs.

### 4.2 (b) Backend APIs

All tenant-scoped, money as strings in JSON, `Decimal` internally, in `apps/api/app/routers/financials.py` + `services/financial.py` + `repositories/financial.py`.

**New admin endpoints:**

```
GET    /admin/financial-metric-definitions
       → { definitions: MetricDefinition[], scenarios: Scenario[] }
POST   /admin/financial-metric-definitions            (transformation_office)
       body: { key, label, description?, group_key?, value_type, unit?, direction,
               aggregation, rollup_type?, is_benefit, benefit_class?, cost_behavior?,
               formula?, display_order, applies_to, validation? }
PUT    /admin/financial-metric-definitions/{id}
POST   /admin/financial-metric-definitions/{id}/deactivate
       -- never hard-delete a definition that has values (mirrors existing deactivate_metric)
GET / POST / PUT /admin/financial-scenarios
       -- deleting a scenario with data → 409 + reassignment option
GET / PUT /admin/financial-settings
       → { fiscal_year_start_month, currency }
GET / PUT /admin/financial-bridge-config
       → { rows: BridgeRow[] }
```

**Rewritten value endpoints (replacing column-shaped payloads):**

```
GET /initiatives/{id}/financials?granularity=monthly|quarterly|yearly&fiscal=true
→ {
    initiative_id,
    definitions: [...],                -- active + selected for this initiative
    scenarios:   [...],
    values: [ { metric_key, scenario_key, year, quarter?, month?,
                value: "12345.0000", derived: false } ],
    cost_lines: [...],
    selections, locked, lock_reason, financial_mode,
    summary: { cards: [ { key, label, value_type, plan, actual, variance } ] }
  }

PUT /initiatives/{id}/financials
    body: { values: [ { metric_key, scenario_key, year, month, value } ],
            cost_lines?: [...] }
    -- MONTHLY ONLY. Writes to derived (formula) metrics rejected with 422.
    -- Validation rules from definition.validation enforced server-side.

GET /initiatives/{id}/financials/rollup?granularity=quarterly&fiscal=true
GET /portfolio/financials?granularity=...           -- same response shape, internally definition-driven
GET /initiatives/{id}/financials/value-bridge
→ { rows: [ { key, label, row_kind, values: { base: "...", high: "...", actual: "..." } } ],
    financial_mode }                                 -- scenario columns come from financial_scenarios
```

**Formula engine** (new module, e.g. `apps/api/app/services/financial_formula.py`): small operator-precedence parser over `+ - * / ( )` and metric keys; **Decimal-only arithmetic, no `eval`**; divide-by-zero → `null`; cycle detection at definition-save time (DFS over `formula_inputs`); computed at every grain from rolled-up inputs.

**Adapted endpoints (shape change only):** XLSX export/import (`services/financial_workbook.py`) generates columns from definitions and embeds definition keys + a config hash in a hidden sheet — import validates against current config and fails with actionable per-row errors; forecasts/assumptions/selections re-keyed; bankable snapshot builder writes the v2 shape with `snapshot_schema_version=2`, and a **read adapter** converts v1 snapshots (old `FinancialEntryRow` shape → `(metric_key, scenario_key)` pairs) on read, forever.

**Compatibility:** during the transition (Phases 3–5 in §6), `GET /initiatives/{id}/financials` serves both old and new shapes (a `?shape=v2` param or response superset) so the frontend can cut over independently.

### 4.3 (c) Frontend design

**Admin Metric Builder** — new lazily-loaded `features/admin/financial-config/` (extracted from `admin.component.ts`, which at 1,650 lines should not grow further):
- *Metrics list*: table of definitions (label, type chip, aggregation, benefit/cost badge, active toggle, drag-reorder).
- *Create/edit drawer*: name → auto-slug key (immutable after creation), value type, unit, direction, aggregation, rollup/benefit/cost behavior, `applies_to`, validation min/max, and a **formula editor** with chip-insertion of existing metric keys + live server-side validation (parse + cycle check). Derived metrics show a "computed, not entered" badge.
- *Scenario manager*: list + add/rename/deactivate; exactly one actual; mark primary plan scenario.
- *Financial settings*: fiscal-year start month dropdown, currency selector (drives `formatMoney`, replacing the hardcoded `'USD'`).
- *Value bridge config*: ordered rows mapping metric sets / cost-category sets / subtotals.
- All per existing standards: standalone components, CSS variable tokens, light+dark, ARIA labels.

**Initiative financials grid** (`financials-tab.component.ts`):
- Delete the hardcoded `METRICS` array and `DEFAULT_METRIC_KEYS`; build grid rows from `definitions × scenarios` in the API response. The existing `GridMetric` interface already supports a dynamic shape — this is an evolution, not a rewrite.
- **Columns = months** within the initiative's date range; **read-only computed Q1–Q4 and FY subtotal columns** rendered inline (visually distinct), recomputed live on edit.
- Derived (formula) rows read-only with a tooltip showing the formula.
- Percent cells render with `%`, currency cells with the org currency; direction drives variance coloring (a cost going down is green).
- Scenario toggle driven by `financial_scenarios` (1 plan scenario → simple plan/actual view; N → multi-scenario toggle), feeding the existing `FinancialModeDescriptor` fallback logic (#208).
- Extract a shared `financial-grid-builder.service.ts` (row/column generation) reused by the XLSX preview.

**Initiative create flow** (`create-initiative.component.ts` step 3): load definitions; `applies_to='all'` metrics shown pre-checked and locked; `opt_in` metrics selectable, grouped, with benefit/cost badges; cost categories unchanged.

**Portfolio & reporting:** portfolio financials columns, summary cards, contributors drawer, and the value waterfall all render from definitions/bridge config instead of fixed keys; control tower consumes the same `financial_mode` metadata (already planned in #208).

### 4.4 (d) Specific features beyond configurability (benchmark-driven)

1. **Benefit maturity stages (Wave-style L1–L5).** Add `benefit_stage` to initiatives (`identified → validated → planned → executing → realized`), auto-advanced by existing gate approvals (configurable mapping in governance settings: e.g. Gate 1 approval ⇒ `planned`, bankable lock ⇒ `executing`, finance sign-off of actuals ⇒ `realized`). Portfolio gains a **value funnel** view: total value by stage + leakage % between stages. This is the single highest-credibility exec report in the category.
2. **Scenario semantics: baseline / target / forecast / actual.** The scenario table supports this taxonomy without schema change (they're just `plan`-kind scenarios plus the `actual`); document the recommended convention and seed labels accordingly. The existing `financial_forecasts` table covers post-lock forecast updates and stays.
3. **Finance sign-off on actuals (optional per tenant).** Governance setting `actuals_require_signoff: bool` + `signoff_role`. When enabled, actual-scenario values and benefit-ledger entries carry `status: draft | submitted | approved` and only `approved` actuals count in "Realized" reporting. Mirrors Sievo's finance-credibility model. Prahari review required (auth/roles).
4. **Audit trail.** `created_by`/`updated_by` on `financial_metric_values_v2` (in schema above) and added to `financial_cost_lines`; all admin config changes written to the existing `audit_log`.
5. **Cost avoidance vs savings.** `benefit_class` on definitions (`savings | avoidance | revenue | margin | other`) so avoidance can be reported separately from EBITDA-effective savings (it should never silently inflate run-rate numbers).
6. **Validation rules.** `validation` JSONB per definition (min/max, required scenarios) enforced server-side on PUT and client-side in the grid; percent metrics default `max: 100` where sensible.
7. **Multi-currency (roadmap, not now).** This design makes it tractable later: currency lives on the org today; a future phase adds optional `currency` + `fx_rate_set` at initiative level with conversion at rollup. Explicitly out of scope for this program — document as ADR.
8. **YoY comparison view** in portfolio financials (trivially enabled once fiscal-year rollups are a view).

---

## 5. Migration & Backfill Plan (expand → backfill → contract)

1. **Expand (zero behavior change).** Ship all new tables/columns/views (§4.1). Seed system definitions + scenarios per existing tenant inside the migration (same `CROSS JOIN organizations` pattern as `20260508000001`); extend `tenant_bootstrap.py` for new tenants.
2. **Backfill (idempotent migration, `ON CONFLICT DO NOTHING`).**
   - Monthly `financial_entries` rows: explode 24 columns → (definition × scenario) v2 rows.
   - Old `financial_metric_values` rows (custom metrics): map `metric_key` → definition, `value_{base,high,actual}` → scenario rows.
   - **Quarterly/annual-only rows**: assign the full amount to the **last month of the period** with `note='backfilled-quarterly'` (preserves all totals exactly — which is what locked plans and workstream locks depend on — at the cost of synthetic monthly phasing, which the UI flags).
   - Reconciliation script: per initiative × metric × scenario, assert old-sum == new-sum; CI-gated.
3. **Dual-write window.** `update_financial_grid` writes both stores; nightly reconciliation job (Procrastinate) alerts on drift. Direct quarterly/annual entry is disabled behind a flag (monthly-only going forward — consistent with the #160 decision that quarterly is computed).
4. **Read cutover.** Summaries, portfolio, bridge, break-even, XLSX read from v2 + rollup view. Golden tests assert v2 outputs match v1 outputs on seeded data before the flag flips.
5. **Bankable snapshots.** v1 JSONB snapshots are **never rewritten**; the read adapter (§4.2) converts on read permanently. New locks write `snapshot_schema_version=2`. Benefit ledger (amounts only) and workstream target locks (derived run-rate values) are unaffected.
6. **Contract.** Only after ≥1 full release cycle with reconciliation green: stop dual-write, drop the 24 columns, delete `_ENTRY_FIELDS` / hardcoded `FinancialEntryRow` fields / frontend `METRICS` / `system_metric_key`, deprecate old `financial_metric_values`.

---

## 6. Phased Roadmap — GitHub-Issue-Ready Work Packages

Each phase = 1 issue (or a small cluster) following the repo's SDLC (Netra → Vastu → Chitra → Karya/Rupa → Aksha → Sthira → Vishwa; **Prahari review on Phases 2, 4, and the sign-off feature** — new RLS tables + role checks). Acceptance per the repo testing standard: **real API tests against a running API with seeded data + browser UI tests against the real Angular app** — no mock-led acceptance.

> Suggested epic: **"Configurable Financial Metrics Engine"** — supersedes/absorbs the backend half of #206; coordinate labels with the in-flight #203 epic first (re-triage the stale `in-qa` labels).

**Phase 1 — Schema + seeding (backend, no behavior change).**
Scope: migrations for `financial_metric_definitions`, `financial_scenarios`, `financial_metric_values_v2`, `financial_bridge_rows`, `organizations.fiscal_year_start_month`, `bankable_plans.snapshot_schema_version`, rollup view; per-tenant seeds; `tenant_bootstrap.py`; Pydantic models in `domain/financials.py`.
Acceptance: migrations apply cleanly on a seeded DB; every existing tenant has 9 system definitions + 3 scenarios; RLS verified per table; zero change to any API response.
Depends on: nothing.

**Phase 2 — Admin definition/scenario/settings API.** *(Prahari review)*
Scope: endpoints in §4.2 (definitions CRUD + deactivate, scenarios, settings, bridge config); repository + service methods; formula validation (parse, key whitelist, cycle detection); audit-log writes.
Acceptance: real-API tests for CRUD, formula cycle rejection (422), scenario-with-data delete (409), non-TO role denial; seeded tenant round-trips config.
Depends on: Phase 1.

**Phase 3 — Dual-write + backfill + reconciliation.**
Scope: `update_financial_grid` dual-writes; backfill migration per §5.2; reconciliation script + nightly Procrastinate job; disable direct quarterly/annual entry behind flag.
Acceptance: backfill on seeded data passes reconciliation exactly; idempotent re-run; locked-plan summaries byte-identical before/after.
Depends on: Phase 2.

**Phase 4 — Backend read cutover (definition-driven engine).** *(Prahari review)*
Scope: `_compute_summary`, portfolio financials/contributors, value bridge (reads `financial_bridge_rows`), break-even, scenario summary, XLSX export/import (definition-driven + config hash), formula engine, snapshot v2 writer + v1 read adapter, `financial_mode` derived from scenarios, monthly→quarter/FY rollups via view with fiscal-year support.
Acceptance: golden tests — every existing endpoint returns identical values on seeded data pre/post cutover; new granularity/fiscal params covered; formula metrics recomputed-at-grain verified (GM% quarter = ΣGM$/ΣRev); v1 bankable snapshot renders correctly through adapter.
Depends on: Phase 3. **Unblocks frontend issues #207/#208 contract.**

**Phase 5 — Frontend: dynamic grid + Admin Metric Builder.**
Scope: delete `METRICS`; grid generated from definitions × scenarios; monthly entry + computed Q/FY subtotal columns; derived rows read-only; `features/admin/financial-config/` (metric builder, scenario manager, fiscal/currency settings, bridge config); `formatMoney` uses org currency; shared `financial-grid-builder.service.ts`.
Acceptance: browser tests with seeded data — admin creates a new metric ("Working Capital Release", currency, sum, benefit) → appears in an initiative's grid → monthly values entered → Q/FY subtotals and portfolio rollup reflect it; a formula metric shows computed values and rejects edits; light+dark, ARIA verified.
Depends on: Phases 2 + 4.

**Phase 6 — Create flow, selections re-key, configurable bridge UI, value funnel.**
Scope: create-initiative step 3 driven by definitions (`applies_to` semantics); selections re-keyed; dynamic value bridge + portfolio columns; benefit maturity stages + value funnel view (§4.4.1); optional finance sign-off on actuals (§4.4.3, *Prahari review*).
Acceptance: browser tests — two seeded tenants with **different metric sets** (one revenue-led, one GM-uplift-led) each see only their own metrics at creation, entry, bridge, and portfolio; funnel shows staged value; sign-off gate blocks unapproved actuals from "Realized".
Depends on: Phase 5.

**Phase 7 — Contract & cleanup.**
Scope: stop dual-write; drop 24 columns; remove `_ENTRY_FIELDS`, legacy models, `system_metric_key`, old `financial_metric_values`; docs update.
Acceptance: full regression suite green; reconciliation job retired; no references to dropped columns anywhere (grep-clean).
Depends on: all prior phases + ≥1 release cycle of green reconciliation.

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Backfill grain mismatch (quarterly-only data → synthetic monthly phasing) | Misleading monthly variance for old initiatives | Period-end-month rule preserves totals exactly; `note` flag surfaces "backfilled" in UI; exclude flagged rows from monthly variance analytics |
| Formula engine bugs (cycles, div-by-zero, precision) | Wrong derived numbers | No `eval`; Decimal-only parser; cycle check at save; div-by-zero → null; golden tests reproducing today's GM% behavior |
| Percent aggregation semantics (`avg` of monthly % ≠ recomputed ratio) | Subtly wrong quarterly % | Migrate system % metrics as `formula`; document `avg`/`last` as explicit tenant choices in the builder UI |
| Locked-plan invariants broken by migration | Finance-credibility loss | Snapshots never rewritten; v1 read adapter permanent; reconciliation gates every phase; benefit ledger & workstream locks store amounts, not keys |
| EAV fan-out on portfolio rollups | Latency at scale | Rollup view + covering index; EXPLAIN checks in Phase 4 acceptance; materialized view as a later option if needed |
| XLSX round-trip drift once columns are dynamic | Failed imports | Definition keys + config hash embedded in hidden sheet; import fails fast with per-row actionable errors |
| RLS/role gaps on new tables | Tenant data leak | Copy the proven policy pattern from `20260508000001_financial_configuration.sql` verbatim; Prahari review on Phases 2 & 4 |
| Collision with in-flight epic #203–#209 | Duplicate/conflicting work | Position this as the design for #206; re-triage stale `in-qa` labels before opening new issues; sequence Phase 4 to land the contract #207/#208 are waiting on |
| Lower-cost implementation model misreads intent | Rework | Each phase issue should copy its scope + acceptance verbatim from §6 and link to §4 sections; DDL and endpoint sketches here are intentionally prescriptive |

---

## 8. Key Files Index (for issue authoring)

| Area | Path |
|---|---|
| Service layer (rollups, summary, bridge, locks) | `apps/api/app/services/financial.py` |
| Domain models | `apps/api/app/domain/financials.py` |
| Repository | `apps/api/app/repositories/financial.py` |
| Router (~40 endpoints) | `apps/api/app/routers/financials.py` |
| XLSX | `apps/api/app/services/financial_workbook.py` |
| Tenant seeding | `apps/api/app/services/tenant_bootstrap.py`, `apps/api/scripts/seed_dev.py` |
| Config migration pattern | `supabase/migrations/20260508000001_financial_configuration.sql` |
| Entry grid (hardcoded `METRICS`) | `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts` |
| Admin (Financial Configuration tab) | `apps/web/src/app/features/admin/admin.component.ts` |
| Create flow (step 3 selections) | `apps/web/src/app/features/initiatives/create/create-initiative.component.ts` |
| Portfolio / benefit tracking / bridge | `apps/web/src/app/features/financials/`, `apps/web/src/app/shared/components/value-waterfall/` |
| Formatting (`USD` hardcoded) | `apps/web/src/app/features/financials/financials-view.models.ts` |
| Existing roadmap to reconcile | `docs/team/BANKABLE_PLAN_IMPLEMENTATION_ROADMAP.md` |
