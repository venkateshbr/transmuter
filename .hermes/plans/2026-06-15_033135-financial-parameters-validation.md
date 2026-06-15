# Financial Parameters Configuration Validation Plan

> **For Hermes:** Planning/review only. Do **not** change application code for this task. If execution is later approved, use read-only inspection first and only propose code changes after Venk confirms.

**Goal:** Validate whether the financial parameters configuration is fully implemented, and explain how initiative financial calculated/read-only values are displayed and configured.

**Architecture:** Transmuter currently has two financial models in the codebase: a legacy/system-metric grid backed by `financial_entries`, `financial_metric_values`, `financial_config_groups`, and `financial_config_items`; and a newer configurable financial engine backed by `financial_metric_definitions`, `financial_scenarios`, `financial_metric_values`, `financial_benefit_lines`, `financial_bridge_rows`, and `financial_attribute_definitions`. The active initiative financials route now returns the configurable grid and includes dynamic formula rows computed by the backend.

**Tech Stack:** FastAPI, Supabase/Postgres, Pydantic v2, Angular, Handsontable, pytest.

---

## Current evidence gathered read-only

### Commands run

- Targeted tests:
  - `env -u SSL_CERT_FILE uv run pytest tests/test_financial_formula_metrics.py tests/test_financial_dynamic_value_bridge.py tests/test_admin_setup_status.py tests/test_initiative_setup_gate.py -q`
  - Result: `9 passed in 2.70s`
- Live hosted API read-only checks against `https://transmuter.ishirock.tech/api`:
  - Login succeeded for the Vish Demo Lab tenant.
  - `GET /financial-engine-configuration` returned:
    - 3 metric definitions
    - 4 scenarios
    - 0 bridge rows
    - 0 attribute definitions
  - First initiative financial grid returned:
    - 3 definitions
    - 4 scenarios
    - 0 benefit lines
    - 0 values
    - 0 cost lines
    - 0 formula definitions / computed values in the seeded demo tenant

### Key implementation files inspected

- Backend domain models:
  - `apps/api/app/domain/financials.py`
- Backend service logic:
  - `apps/api/app/services/financial.py`
- Backend repository/data access:
  - `apps/api/app/repositories/financial.py`
- Backend routes:
  - `apps/api/app/routers/financials.py`
- Admin UI financial configuration:
  - `apps/web/src/app/features/admin/admin.component.ts`
- Initiative financial UI:
  - `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts`
- Dashboard/reporting UI and model helpers:
  - `apps/web/src/app/features/dashboard/dashboard.component.ts`
  - `apps/web/src/app/features/dashboard/dashboard-echart-card.component.ts`
  - `apps/web/src/app/features/reports/executive-control-tower.component.ts`
  - `apps/web/src/app/features/financials/financials-view.models.ts`
- Tests:
  - `apps/api/tests/test_financial_formula_metrics.py`
  - `apps/api/tests/test_financial_dynamic_value_bridge.py`
  - `apps/api/tests/test_admin_setup_status.py`
  - `apps/api/tests/test_initiative_setup_gate.py`
- DB migrations:
  - `infra/supabase/migrations/20260611000002_clean_configurable_financial_engine.sql`
  - `supabase/migrations/20260611000002_clean_configurable_financial_engine.sql`
  - older legacy config migrations under `supabase/migrations/202605*.sql`

---

## Findings so far

### 1. Financial parameter configuration is implemented at multiple levels

#### Backend data model

Implemented in `apps/api/app/domain/financials.py`:

- `FinancialMetricDefinitionBase`
  - `key`, `label`, `description`, `group_key`
  - `value_type`: `currency | percent | number`
  - `direction`: `increase_good | decrease_good | neutral`
  - `aggregation`: `sum | avg | last | formula`
  - `rollup_type`: `benefit | recurring_cost | one_off_cost | total_cost | net_value`
  - `is_benefit`, `benefit_class`, `cost_behavior`
  - `formula`, `formula_inputs`
  - `precision`, `display_order`, `applies_to`, `validation`, `is_system`, `is_active`
- `FinancialScenarioDefinitionBase`
  - `key`, `label`, `kind`, `is_primary`, `is_system`, `is_active`, `display_order`
- `FinancialBridgeRow`
  - Defines value bridge rows from metric definitions and cost categories.
- `FinancialAttributeDefinition`
  - Defines reusable benefit/cost-line attributes.
- `FinancialEngineConfigurationResponse`
  - Bundles definitions, scenarios, bridge rows, attribute definitions, and reporting settings.

#### Backend service/router

Implemented in:

- `apps/api/app/routers/financials.py`
  - `GET /financial-engine-configuration`
  - `PATCH /admin/financial-engine/reporting-settings`
  - `POST/PATCH /admin/financial-engine/metrics`
  - `POST/PATCH /admin/financial-engine/scenarios`
  - `POST/PATCH /admin/financial-engine/bridge-rows`
  - `POST/PATCH /admin/financial-engine/attribute-definitions`
- `apps/api/app/services/financial.py`
  - `get_engine_configuration()` returns tenant engine config.
  - `create_metric_definition()` / `update_metric_definition()` validate and persist metric definitions.
  - `create_scenario_definition()` / `update_scenario_definition()` persist scenarios.
  - `create_bridge_row()` / `update_bridge_row()` persist bridge rows.
  - `create_attribute_definition()` / `update_attribute_definition()` persist line attributes.

#### Admin UI

Implemented in `apps/web/src/app/features/admin/admin.component.ts`:

- Metric Definitions panel:
  - label, type, aggregation, benefit class, active/hidden, formula field for aggregation `formula`.
- Scenarios panel:
  - label, kind, active/hidden.
- Value Bridge Rows panel:
  - row kind, sign, order, metric inputs, cost category inputs.
- Line Attribute Registry:
  - reusable fields for benefit and cost lines.

### 2. Initiative financial grid is now the configurable-grid route

Implemented in `apps/api/app/routers/financials.py`:

- `GET /initiatives/{initiative_id}/financials` returns `ConfigurableFinancialGridResponse` from `FinancialService.get_configurable_financial_grid()`.
- `PUT /initiatives/{initiative_id}/financials` writes configurable monthly values via `FinancialService.update_configurable_financial_grid()`.

Implemented in `apps/api/app/services/financial.py`:

- `get_configurable_financial_grid()` returns:
  - metric definitions
  - scenarios
  - benefit lines
  - values, including computed formula rows
  - cost lines
  - reporting settings
  - legacy summary for compatibility

### 3. “Calculated values / not configurable” are formula metrics

Backend behavior in `apps/api/app/services/financial.py`:

- Formula metric definitions are metric definitions where `aggregation == "formula"`.
- They are configured in the tenant financial engine via `financial_metric_definitions.formula` and `financial_metric_definitions.formula_inputs`.
- Formula expressions are validated by:
  - `_validate_metric_definition_payload()`
  - `_validate_formula_expression()`
  - `_validate_formula_graph()`
- Unsafe syntax and cycles are rejected.
- Computed values are generated at read time by `_values_with_formula_metrics()`.
- Formula values get synthetic IDs shaped like:
  - `formula:{initiative_id}:{scenario_id}:{year}:{month}:{definition_id}`
- Formula values get:
  - `status = "approved"`
  - `note = "Computed formula metric"`
  - `_computed_formula = True`
- Writes to formula metrics are rejected by `_assert_no_formula_metric_values()` with:
  - `Formula metrics are read-only and are computed from input metrics`

Frontend behavior in `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts`:

- The initiative financial grid maps definitions into rows in `configuredMetrics`.
- Formula rows are labelled with ` - computed`.
- Formula rows set:
  - `readOnly: true`
  - `formula: definition.formula`
- Computed rows receive CSS class `hot-computed-cell`.
- Attempts to edit a computed row through the acceptance harness throw:
  - `Financial row is computed and read-only: {rowKey}`
- In the UI they are visually styled as computed/read-only rows by `.hot-computed-cell`.

### 4. Important distinction: current live demo tenant has no formula definitions

The live Vish Demo Lab tenant currently has only these metric definitions:

- `gross_margin_uplift` — sum, benefit class `margin`
- `ebitda_benefit` — sum, benefit class `savings`
- `one_off_cost` — sum, non-benefit

So in that tenant, there are currently no formula metric rows to display as computed/read-only. The code supports them, and tests pass, but the seed data used for this tenant did not configure formula metrics.

### 5. Default formula definitions exist in migration seed data, but may not be present in tenant shell/demo tenant

`infra/supabase/migrations/20260611000002_clean_configurable_financial_engine.sql` and the mirrored `supabase/...` file include default formula metric candidates such as:

- `revenue_uplift_pct`: `revenue_uplift / baseline_revenue * 100`
- `gm_pct`: `gross_margin / revenue_uplift * 100`
- `gm_uplift_pct`: `gm_uplift / revenue_uplift * 100`
- `cogs_pct`: `cogs / revenue_uplift * 100`
- `roi_actual`: marked as formula but default formula is `NULL`, which would be rejected by current service validation if saved through the API as formula without a formula expression.

Need to verify whether production tenant bootstrap is supposed to seed these defaults for new tenants or whether that migration only seeded organizations that existed at migration time.

### 6. Dashboards/reports use configuration, but there are likely two code paths to keep straight

Backend:

- Portfolio clean/configurable reporting path computes portfolio summary and periods from `financial_metric_values` plus `financial_cost_lines`.
- `_clean_value_case()` classifies values by metric definition key / benefit class / rollup type.
- `_clean_dynamic_bridge_rows()` uses `financial_bridge_rows` when configured.
- Without bridge rows, dynamic bridge rows are empty and dashboard/reporting falls back to summary-derived values or default mode helpers.

Frontend:

- `financials-view.models.ts` has default financial mode descriptors including `multi_scenario`.
- Dashboard/report components use `resolveFinancialMode(...)` and show value bridge/summary rows when backend response contains those structures.

---

## Validation plan, no code changes

### Task 1: Confirm production DB configuration shape for at least two tenants

**Objective:** Verify whether the new configurable financial engine tables are populated consistently for new/demo tenants and any known production tenant.

**Files:** Read-only/API only.

**Steps:**

1. Authenticate via API for the target tenant.
2. Call `GET /financial-engine-configuration`.
3. Record counts and exact rows for:
   - `definitions`
   - `scenarios`
   - `bridge_rows`
   - `attribute_definitions`
4. Compare against expected migration defaults.
5. Specifically check for formula metrics:
   - definitions where `aggregation == "formula"`
   - non-empty `formula`
   - `formula_inputs` matching identifiers in `formula`

**Expected outcome:** A short matrix per tenant showing whether metric definitions, scenarios, bridge rows, and formula metrics are present.

### Task 2: Trace tenant setup / bootstrap default creation

**Objective:** Determine whether new tenants automatically receive the full financial engine defaults.

**Files:**

- `apps/api/app/services/tenant_bootstrap.py`
- `apps/api/app/routers/auth.py`
- `apps/api/scripts/bootstrap_hostinger_local.py`
- migrations under `infra/supabase/migrations/` and `supabase/migrations/`

**Steps:**

1. Inspect tenant registration flow.
2. Inspect tenant bootstrap service.
3. Inspect any hostinger bootstrap scripts.
4. Confirm whether financial engine defaults are inserted during tenant creation or only in DB migrations.
5. Document mismatch if bootstrap creates only shell settings while migrations created defaults only for existing organizations.

**Expected outcome:** Definitive answer to: “If a tenant is created today, does it get all financial defaults automatically?”

### Task 3: Validate formula metric display path in initiative financials

**Objective:** Confirm how formula rows are shown and why they are not editable.

**Files:**

- `apps/api/app/services/financial.py`
- `apps/web/src/app/features/initiatives/detail/financials/financials-tab.component.ts`
- `apps/api/tests/test_financial_formula_metrics.py`

**Steps:**

1. Confirm backend returns formula rows via `_values_with_formula_metrics()`.
2. Confirm backend rejects formula writes via `_assert_no_formula_metric_values()`.
3. Confirm frontend sets `readOnly` when `definition.aggregation === 'formula'`.
4. Confirm label suffix ` - computed`.
5. Confirm CSS class `hot-computed-cell` and Handsontable cell-level readOnly behavior.

**Expected outcome:** Plain-English explanation plus file/line references.

### Task 4: Validate dashboard/report usage of initiative financial data

**Objective:** Confirm dashboards and reports consume the initiative financial values and configuration correctly.

**Files:**

- `apps/api/app/services/financial.py`
- `apps/api/app/services/dashboard.py`
- `apps/api/app/repositories/dashboard.py`
- `apps/api/app/services/executive_control.py`
- `apps/web/src/app/features/dashboard/dashboard.component.ts`
- `apps/web/src/app/features/reports/executive-control-tower.component.ts`
- `apps/web/src/app/features/financials/portfolio-financials.component.ts`

**Steps:**

1. Identify backend endpoints used by dashboard/report screens.
2. Trace whether they call configurable clean financial engine data or legacy fields.
3. Use live API read-only calls to compare:
   - initiative financial grid values
   - portfolio financial summary
   - dashboard value bridge/summary
   - executive control tower values
4. If dashboards show zero values, determine whether the issue is absence of financial values/benefit lines/cost lines, not a code bug.
5. If dashboards ignore configurable rows while values exist, document exact mismatch.

**Expected outcome:** A source-to-screen data-flow map and a “dashboard values are correct/incorrect because…” answer.

### Task 5: Run targeted read-only verification suite

**Objective:** Validate existing automated coverage without code changes.

**Commands:**

```bash
cd /root/dev/transmuter/apps/api
env -u SSL_CERT_FILE uv run pytest \
  tests/test_financial_formula_metrics.py \
  tests/test_financial_dynamic_value_bridge.py \
  tests/test_admin_setup_status.py \
  tests/test_initiative_setup_gate.py \
  -q
```

**Already observed:** `9 passed in 2.70s`.

**Optional next checks:**

```bash
cd /root/dev/transmuter/apps/api
env -u SSL_CERT_FILE uv run pytest tests/test_financial_portfolio.py -q
```

Only run broader tests if Venk wants deeper validation because they may take longer.

---

## Risks / open questions

1. **Bootstrap gap risk:** `TenantBootstrapService.bootstrap_tenant()` appears to create only shell settings, not financial engine defaults. If true, new tenants may not receive the default formula metrics unless migration/default seeding is run separately.
2. **Legacy vs clean engine overlap:** The frontend still contains legacy fallback code paths (`financial_entries`, `financial_config_items`, hard-coded system metrics). Need to confirm all active screens use the intended configurable engine path.
3. **Bridge rows absent in live tenant:** The live demo tenant has `0` bridge rows, so dynamic configurable value bridge reporting will be empty/fallback until bridge rows are configured.
4. **Formula defaults not present in live tenant:** The live demo tenant has no `aggregation='formula'` metric definitions, so computed/read-only rows will not appear there yet.
5. **Seed data lacks financial values:** The 10 initiatives currently have no benefit lines, metric values, or cost lines in the live demo tenant, so dashboards may correctly report zero financials even though initiatives exist.

---

## Preliminary answer

- The configurable financial parameter framework is implemented in backend domain/service/repository/router layers and in the Admin UI.
- Formula/calculated initiative financial rows are configured as metric definitions with `aggregation = 'formula'` and a formula expression.
- Backend computes formula values at read time, marks them as computed, and rejects writes.
- Frontend labels these rows with ` - computed`, marks them read-only, and styles them via `hot-computed-cell`.
- The current live demo tenant does **not** have formula definitions, bridge rows, benefit lines, metric values, or cost lines, so its dashboards should not yet show meaningful financial totals from the seeded initiatives.
- Next validation should focus on whether tenant bootstrap should seed the full default financial engine config and whether dashboards use configurable data end-to-end when values exist.
