# Release Manifest

This file is the durable audit trail for Hostinger dev-to-production promotion.
GitHub remains the workflow system of record: every release entry should link the
issue, PR, commit, dev validation evidence, schema SQL, and production promotion
status.

## Process

1. During feature work, deploy to Hostinger dev with:
   `infra/hostinger/deploy-change-to-dev.sh`
2. If SQL is required, apply it to dev with:
   `infra/hostinger/deploy-change-to-dev.sh --schema path/to/change.sql`
3. Before promotion, add or update the release entry below with:
   - issue and PR links,
   - commit SHA,
   - schema files applied to `transmuter_dev`,
   - validation evidence,
   - production schema files that must be applied.
4. Promote only after review/merge and explicit approval:
   `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`
5. If production SQL is required, pass every required SQL file in order:
   `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh --schema path/to/change.sql`
6. After production validation, update the entry with promotion time, validation
   result, and any operational notes.

## Current Release Entries

### 2026-06-23 - Governance Queue Initiative Labels and Production Launch Tenant

Status: promoted to production

GitHub tracking:
- Issue: `#341`
- PR: `#342`
- Merge commit:
  - `533fb7e Merge pull request #342 from venkateshbr/fix/governance-real-initiative-labels`

Runtime changes:
- PMO governance submissions now expose and display the real initiative code and
  initiative name instead of UUID-derived fallback labels.
- Governance repository/service responses include `initiative_code`,
  `initiative_name`, and nested initiative metadata for both initiative history
  and portfolio governance queue views.
- Governance API test credentials now come from the latest launch E2E tenant or
  explicit E2E credential environment variables, not hardcoded seeded admin
  credentials.

Local and CI validation:
- `uv run --project apps/api pytest apps/api/tests/test_governance.py -q`
- `uv run --project apps/api ruff check apps/api/tests/test_governance.py`
- `uv run --project apps/api ruff format --check apps/api/tests/test_governance.py`
- GitHub PR checks passed:
  - Backend lint, type check, tests.
  - Frontend lint and production build.
  - Secret scan.
  - Validate agent and workflow specs.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema SQL applied: none.
- Deployed with `infra/hostinger/deploy-change-to-dev.sh`.
- Initial scripted validation hit the known immediate public `/health` readiness
  race after container recreation.
- Manual and rerun dev validation passed for local/public `/health` and
  `/api/health`.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `533fb7e`
- Schema SQL applied: none.
- Promoted with `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- Initial scripted validation hit the known immediate public `/health` readiness
  race after container recreation.
- Manual and rerun production validation passed for local/public `/health` and
  `/api/health`.

Production browser launch validation:
- Tenant: `Acme Production Launch Demo 20260623t030517`
- Slug: `acme-prod-launch-20260623t030517`
- Admin email: `admin+acme-prod-launch-20260623t030517@ishirock.dev`
- Credentials path:
  `scratch/launch-ui-recordings/acme-prod-launch-20260623t030517/credentials.json`
- Result path:
  `scratch/launch-ui-recordings/acme-prod-launch-20260623t030517/result.json`
- Resume state:
  `scratch/launch-ui-recordings/acme-prod-launch-20260623t030517/resume-state.json`
- Run documentation:
  `scratch/launch-ui-recordings/acme-prod-launch-20260623t030517/run-documentation.md`
- Walkthrough video:
  `scratch/launch-ui-recordings/acme-prod-launch-20260623t030517/acme-launch-browser-walkthrough.mp4`
- Validation result:
  - Setup checklist complete.
  - 10 initiatives.
  - 10 locked bankable plans.
  - 10 KPIs.
  - 10 risks.
  - 40 milestones.
  - 4 shared-cost pools.
  - FY28 net run-rate value `8350000.0020`.
  - One-off investment `2500000.0008`.
  - Payback months `3.5928`.
  - Benefit ledger actuals `12053200.0020`.

Operational notes:
- Production launch was performed through the public browser UI, including
  Stripe checkout, tenant admin setup screens, initiative workbook import,
  financial entry, PMO governance approvals, benefit ledger import, shared-cost
  pool setup, rebaseline approval, and dashboard walkthrough.
- The first production browser pass failed at ENT-008 Gate 2 because the runner
  missed the `Submit for Approval` click target. The checkpoint-aware resume
  runner continued the same tenant from that point and completed governance.
- Final reconciliation then surfaced missing FY27/FY28 benefit value rows on
  already-created browser-entered benefit lines. The authenticated tenant repair
  path temporarily disabled the plan lock, filled the missing value rows,
  revalidated affected benefit lines, restored the lock setting, and reran final
  dashboard reconciliation successfully.

### 2026-06-22 - Governed Bankable Plan Rebaseline

Status: promoted to production

GitHub tracking:
- Issue: `#339`
- PR: not yet opened
- Commit:
  - `120c6db feat: add governed bankable plan rebaseline`

Runtime changes:
- Added a governed rebaseline workflow for Bankable Plan baseline changes.
- `/financials/bankable-plan` now submits a rebaseline request instead of
  directly changing the current locked plan.
- Rebaseline requests are stored as governance submissions with
  `submission_type = bankable_plan_rebaseline`.
- `/pmo/governance` shows and approves/rejects Bankable Plan rebaseline
  requests.
- Approval creates the next immutable `bankable_plans` version with
  `trigger_type = rebaseline`; pending requests do not affect Benefit Tracking,
  Waterline, dashboards, or board-pack exports.
- ACME4 `TRN-005` now has version-2 governed rebaseline history.

Local validation:
- `cd apps/api && uv run pytest tests/test_bankable_plans.py -q`
- `cd apps/web && ./node_modules/.bin/tsc --noEmit -p tsconfig.app.json`
- `cd apps/web && ./node_modules/.bin/ngc -p tsconfig.app.json`
- `node --check apps/web/e2e/acme4-full-demo-ui-e2e.mjs`
- `git diff --check`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema SQL applied:
  `supabase/migrations/20260622000001_governed_bankable_rebaseline.sql`
- Deployed with:
  `infra/hostinger/deploy-change-to-dev.sh --schema supabase/migrations/20260622000001_governed_bankable_rebaseline.sql`
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- Manual public and local dev health checks passed for `/health` and
  `/api/health`.
- ACME4 browser validation passed:
  - 10 initiatives.
  - 10 locked bankable plans.
  - 11 KPI rows.
  - 10 risk rows.
  - 20 milestones.
  - 3 dependencies.
  - Benefit ledger actuals `12053200.0020`.
  - 4 shared-cost pools.
  - `TRN-005` bankable plan `rebaselineVersion: 2`.
- Dev database validation confirmed:
  - `TRN-005` v1: `approval`, `stage_gate`, `approved`.
  - `TRN-005` v2: `rebaseline`, `bankable_plan_rebaseline`, `approved`.

Schema SQL required for production:
- `supabase/migrations/20260622000001_governed_bankable_rebaseline.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Initial promotion with `--schema` hit the known Docker-only `db` hostname
  issue from the host.
- Production schema SQL was applied through the self-hosted Supabase DB
  container as `supabase_admin`, with
  `search_path=transmuter,public,extensions`:
  - `supabase/migrations/20260622000001_governed_bankable_rebaseline.sql`
- Production deployment ran with:
  `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`
- First retry hit a transient Docker Hub auth 404 for `node:22-alpine`; rerun
  succeeded.
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- `infra/hostinger/validate-prod.sh` passed after the production stack settled.
- Public production health checks passed for `/health` and `/api/health`.
- Production schema validation confirmed `gate_submissions` has:
  - `submission_type text`
  - `requested_bankable_plan_version integer`
  - `requested_snapshot jsonb`
- Production route validation confirmed `/financials/bankable-plan` and
  `/pmo/governance` return the Angular app shell.

### 2026-06-22 - Configurable Dashboards And Investments Payback

Status: promoted to production

GitHub tracking:
- Issue: `#339`
- PR: not yet opened
- Commit:
  - `1f3f71e feat: add configurable dashboards and payback view`

Runtime changes:
- Added tenant-scoped dashboard configuration with RLS, admin controls, shell
  menu filtering, and tenant bootstrap defaults.
- Existing tenants are backfilled with all dashboards enabled.
- New tenant bootstrap enables only Executive Dashboard, Financial Overview,
  and Initiative Portfolio by default.
- Added an Investments & Payback dashboard and portfolio API using cumulative
  one-off investment through the selected value year and annual net run-rate
  payback months.
- Kept new-tenant bootstrap focused on financial engine defaults only; it does
  not seed workstreams, business units, gates, or initiatives.
- Updated initiative creation readiness to rely on the new financial engine
  definitions, scenarios, and cost categories instead of legacy financial
  configuration groups/items.

Local validation:
- `cd apps/api && uv run ruff check app/domain/dashboard_config.py app/domain/financials.py app/routers/admin.py app/routers/auth.py app/routers/dashboard.py app/routers/financials.py app/routers/platform.py app/services/dashboard_config.py app/services/financial.py app/services/tenant_bootstrap.py scripts/seed_enterprise_transformation_scenario.py tests/test_tenant_bootstrap.py tests/test_financial_portfolio.py`
- `cd apps/api && uv run pytest tests/test_financial_dynamic_value_bridge.py tests/test_executive_control.py tests/test_financial_portfolio.py tests/test_tenant_bootstrap.py -q`
- `cd apps/web && npm test -- --watch=false`
- `cd apps/web && npm run build`
- `git diff --check`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema/data SQL applied:
  `supabase/migrations/20260622000001_tenant_dashboard_configuration.sql`
- Deployed with:
  `infra/hostinger/deploy-change-to-dev.sh --schema supabase/migrations/20260622000001_tenant_dashboard_configuration.sql`
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- `infra/hostinger/validate-dev.sh` passed after the dev stack settled.
- Public dev health checks passed for `/health` and `/api/health`.
- Browser guide validation passed for tenant
  `qa-dashboard-config-1782116455704`:
  - Setup checklist complete.
  - 10 initiatives.
  - FY2028 net run-rate `8350000.0012`.
  - One-off investment `2500000.0000`.
  - Payback months `3.5928`.
- Read-only tenant integrity checks passed:
  - `acme3-transformation-lab`: 10 dashboards enabled, 5 business units,
    5 workstreams, 10 initiatives, 4 scenarios, 10 metrics,
    8 cost categories, 6 bridge rows.
  - `ishirock`: 10 dashboards enabled, 10 business units, 4 workstreams,
    23 initiatives, 4 scenarios, 11 metrics, 57 cost categories,
    6 bridge rows.
  - `qa-dashboard-config-1782116455704`: 10 dashboards enabled,
    5 business units, 5 workstreams, 10 initiatives, 4 scenarios,
    10 metrics, 8 cost categories, 6 bridge rows.

Schema/data SQL required for production:
- `supabase/migrations/20260622000001_tenant_dashboard_configuration.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Production schema SQL was applied through the self-hosted Supabase DB
  container as `supabase_admin`, with
  `search_path=transmuter,public,extensions`, because the promotion script's
  default schema DB URL resolved the Docker-only `db` hostname from the host.
- Schema/data SQL applied:
  `supabase/migrations/20260622000001_tenant_dashboard_configuration.sql`
- Production deployment ran with:
  `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- `infra/hostinger/validate-prod.sh` passed after the production stack settled.
- Public production health checks passed for `/health` and `/api/health`.
- Production schema validation confirmed:
  - 50 `tenant_dashboard_config` rows.
  - 50 enabled dashboard rows.
  - 5 organizations backfilled.
- Production route validation confirmed `/financials/investments-payback` and
  `/admin` return the Angular app shell.

### 2026-06-20 - Shared Costs Configurable Allocation Engine

Status: promoted to production

GitHub tracking:
- Issue: `#321`
- PR: `#327`
- Prahari hardening issue: `#325`
- Prahari hardening PR: `#328`
- Implementation commit: `d8bfdcb feat: add configurable shared cost allocation engine`
- Production promotion commit: `31c8805 fix: harden shared cost tenant references`

Runtime changes:
- Extended Shared Costs from raw JSON rules into a configurable allocation
  engine with tenant-scoped pool periods, allocation targets, structured
  weights, reporting settings, preview reconciliation, exceptions, audit
  events, and locked/posting run metadata.
- Added allocation methods for equal split, fixed percentage, manual amount,
  benefit weighted, revenue weighted, savings weighted, direct-cost weighted,
  headcount weighted, and metric weighted policies.
- Updated `/shared-costs` to manage pools, rules, targets, weights, preview
  reconciliation, locked runs, and dashboard/report treatment settings without
  raw JSON entry.
- Updated the ACME enterprise seed so `acme3-transformation-lab` includes 10
  initiatives, bankable plans, benefit ledger, dependency risks, management
  meetings, value-realization notes, and four FY2028 shared-cost pools.
- Prahari follow-up hardened Shared Costs tenant isolation by replacing
  id-only shared-cost ledger references with composite tenant-scoped foreign
  keys where the schema owner can enforce them, plus trigger validation for
  user actor/approval references and posted cost-line references.

Local validation:
- `cd apps/api && uv run --extra dev ruff check app/domain/executive_control.py app/services/executive_control.py app/repositories/executive_control.py app/routers/executive_control.py tests/test_executive_control.py tests/test_real_route_coverage.py tests/acceptance/test_real_api_sample_data.py scripts/seed_enterprise_transformation_scenario.py`
- `cd apps/api && uv run --extra dev pytest tests/test_executive_control.py`
- `cd apps/web && npm run build`
- `git diff --check`
- Prahari hardening follow-up:
  - `cd apps/api && uv run --extra dev pytest tests/test_security_controls.py`
  - `cd apps/api && uv run --extra dev ruff check tests/test_security_controls.py`
  - `git diff --check`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema/data SQL applied:
  `supabase/migrations/20260620000001_shared_cost_configurable_allocation_engine.sql`
  `supabase/migrations/20260620000002_harden_shared_cost_allocation_tenant_refs.sql`
- Deployed with:
  `ALLOW_INSECURE_TLS=1 infra/hostinger/deploy-change-to-dev.sh --schema supabase/migrations/20260620000001_shared_cost_configurable_allocation_engine.sql`
- Hardening SQL was applied to `transmuter_dev` through the self-hosted
  Supabase DB container as `supabase_admin`, with
  `search_path=transmuter_dev,public,extensions`, because the default schema
  apply role does not own the existing shared-cost tables.
- Dev was redeployed after hardening with:
  `ALLOW_INSECURE_TLS=1 infra/hostinger/deploy-change-to-dev.sh`
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- `ALLOW_INSECURE_TLS=1 infra/hostinger/validate-dev.sh` passed after the dev
  stack settled.
- Prahari hardening dev validation:
  - Catalog check confirmed `shared_cost_*_tenant_fk` constraints on pools,
    rules, runs, allocations, targets, weights, exceptions, audit events,
    periods, scenarios, metrics, and cost categories.
  - Catalog check confirmed same-tenant trigger validation for shared-cost
    pool user refs, run user refs, audit actor refs, and posted cost-line refs.
  - Focused real dev API acceptance passed for
    `test_real_api_executive_control_tower_phase_2a` against ACME3.
- ACME3 seeded in `transmuter_dev` with:
  - `TRANSMUTER_SEED_ORG_SLUG=acme3-transformation-lab`
  - `TRANSMUTER_SEED_ADMIN_EMAIL=admin@acme3-transformation.dev`
- Real dev API acceptance passed:
  - `test_real_api_seeded_dashboard_and_meetings`
  - `test_real_api_executive_control_tower_phase_2a`
- Real dev browser validation passed:
  - `CHROME_BIN=/usr/bin/chromium-browser TRANSMUTER_UI_BASE_URL=https://transmuter-dev.ishirock.tech TRANSMUTER_API_BASE_URL=https://transmuter-dev.ishirock.tech/api TRANSMUTER_E2E_EMAIL=admin@acme3-transformation.dev TRANSMUTER_E2E_PASSWORD=Transmuter2026! CHROME_DEBUG_PORT=9334 node apps/web/e2e/phase2a-ui-acceptance.mjs`
- ACME3 reconciliation validation passed:
  - 4 FY2028 shared-cost pools.
  - Methods covered: `benefit_weighted`, `equal_split`, `fixed_percentage`,
    `manual_amount`.
  - Shared-cost plan: `1450000.0000`; actual: `1305000.0000`.
  - Control Tower allocated plan: `1450000.0000`.
  - Control Tower net after allocation: `1400000.0004`.
  - Bankable Plan shared-cost inclusion default: `false`.

Schema/data SQL required for production:
- `supabase/migrations/20260620000001_shared_cost_configurable_allocation_engine.sql`
- `supabase/migrations/20260620000002_harden_shared_cost_allocation_tenant_refs.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Schema/data SQL applied to production through the self-hosted Supabase DB
  container as `supabase_admin`, with
  `search_path=transmuter,public,extensions`:
  - `supabase/migrations/20260620000001_shared_cost_configurable_allocation_engine.sql`
  - `supabase/migrations/20260620000002_harden_shared_cost_allocation_tenant_refs.sql`
- Production deployment ran with:
  `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- `infra/hostinger/validate-prod.sh` passed after the production stack settled.
- Production catalog validation confirmed `shared_cost_*_tenant_fk`
  constraints on pools, rules, runs, allocations, targets, weights,
  exceptions, audit events, periods, scenarios, metrics, and cost categories.
- Production catalog validation confirmed same-tenant trigger validation for
  shared-cost pool user refs, run user refs, audit actor refs, and posted
  cost-line refs.
- Production runtime API validation passed for:
  - `/shared-costs/config` with 9 allocation methods.
  - `/shared-cost-pools` responding successfully for the production ACME
    tenant.
  - `/reports/executive-control-tower` responding successfully for the
    production ACME tenant.
- Production browser validation passed for `/shared-costs` rendering the
  Shared Costs workflow on `https://transmuter.ishirock.tech`.

Operational notes:
- The full ACME3 shared-cost acceptance scenario remains dev-only until
  production demo data is backfilled. Production ACME currently has 0
  initiative dependencies and 0 shared-cost pools, so
  `test_real_api_executive_control_tower_phase_2a` fails on the known
  production seeded-data drift tracked in `#304`, not on deployment/schema
  health.

### 2026-06-20 - Financial Configuration Engine Consolidation

Status: promoted to production

GitHub tracking:
- Issue: `#316`
- PR: `#317`
- Commit:
  - `cd3ba40 feat: consolidate financial configuration engine`

Runtime changes:
- Consolidated cost categories into the tenant-scoped Financial Configuration
  Engine while retaining compatibility facades for legacy financial
  configuration routes.
- Added engine-owned `financial_cost_categories`, `category_id` on
  `financial_cost_lines`, `cost_category_ids` on `financial_bridge_rows`, and
  `initiative_financial_scope`.
- Added tenant-scoped foreign keys, RLS policies, and trigger validation for
  financial metric/category references.
- Updated admin setup, portfolio financial filters, initiative financial scope,
  workbook reload, tenant cleanup, failed-registration cleanup, and ACME
  Bankable Plan documentation.
- Bumped `pydantic-settings` to `2.14.2` to satisfy the dependency audit gate.

Local validation:
- `uv run python -m compileall app/core/auth.py app/routers/platform.py app/services/admin.py app/domain/financials.py app/services/financial.py app/repositories/financial.py app/routers/financials.py app/routers/auth.py app/services/initiative.py app/services/portfolio_workbook.py scripts/seed_enterprise_transformation_scenario.py`
- `uvx pip-audit --strict -r /tmp/transmuter-api-requirements.txt`
- `uv run ruff check app tests`
- `uv run ruff format --check app tests`
- `uv run mypy app`
- `uv run pytest tests/test_financial_dynamic_value_bridge.py tests/test_financial_formula_metrics.py tests/test_financial_portfolio.py tests/test_admin_setup_status.py tests/test_initiative_setup_gate.py tests/test_platform_billing_routes.py tests/test_security_controls.py tests/test_bankable_plans.py -q`
- `npm run build` from `apps/web`
- `git diff --check`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Deployed with:
  `infra/hostinger/deploy-change-to-dev.sh --schema supabase/migrations/20260619000001_financial_engine_cost_category_consolidation.sql`
- Initial scripted public validation hit the known transient `/health` 404
  readiness race immediately after container recreation.
- `infra/hostinger/validate-dev.sh` passed after the stack settled.
- Real dev API validation passed:
  - `/financial-engine-configuration` returned 10 definitions, 4 scenarios,
    and 8 cost categories.
  - ACME returned 10 initiatives.
  - `ENT-005` Bankable Plan returned current version `2` and 2 history rows.
  - Benefit Tracking yearly rollup returned locked baseline
    `13769999.9988` and actual `12053200.0020`.
- Real dev browser validation passed on:
  - `/dashboard`
  - `/financials`
  - `/financials/initiative-portfolio`
  - `/financials/benefits-register`
  - `/financials/benefit-tracking`
  - `/financials/bankable-plan`

Schema/data SQL applied to dev:
- `supabase/migrations/20260619000001_financial_engine_cost_category_consolidation.sql`

Schema/data SQL required for production:
- `supabase/migrations/20260619000001_financial_engine_cost_category_consolidation.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit:
  `dacee75 docs: track financial engine consolidation release`
- Schema/data SQL applied to production:
  `supabase/migrations/20260619000001_financial_engine_cost_category_consolidation.sql`
- Initial promotion with `--schema` failed before deployment because host-side
  schema application could not resolve the Docker service hostname `db`.
- Retried schema application with `POSTGRES_DOCKER_NETWORK=supabase-aethos_default`;
  the app DB user could connect but could not create objects in schema
  `transmuter`.
- Applied the SQL successfully through the self-hosted Supabase DB container as
  `supabase_admin`, with `search_path=transmuter,public,extensions`.
- Production deployment then rebuilt/restarted the API and web containers with
  `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- Initial scripted public validation hit the known transient `/health` 404
  readiness race immediately after container recreation.
- `infra/hostinger/validate-prod.sh` passed after the stack settled.
- Real production API validation passed for runtime/schema health:
  - `/financial-engine-configuration` returned 10 definitions, 4 scenarios,
    and 8 cost categories.
  - ACME returned 10 initiatives.
  - Bankable Plan API responded for all 10 initiatives.
- Real production browser validation passed for page rendering on:
  - `/dashboard`
  - `/financials`
  - `/financials/initiative-portfolio`
  - `/financials/benefits-register`
  - `/financials/benefit-tracking`
  - `/financials/bankable-plan`

Operational notes:
- Production ACME demo data is still not at dev parity. `ENT-001` has a locked
  bankable plan v1, but `ENT-002` through `ENT-010` have no locked bankable
  plan history; `ENT-005` does not show the dev v2 rebaseline example.
- Production Benefit Tracking currently reports only the `ENT-001` locked
  baseline (`-37500.0000`) and `0.0000` actuals, while Benefits Register shows
  0 lines for the ACME tenant.
- This is the known production-only seeded-data drift tracked in `#304`, not a
  deployment/schema failure. `#304` was updated with the 2026-06-20 validation
  evidence.

### 2026-06-18 - Initiative Baseline-to-Target P&L Bridge

Status: promoted to production

GitHub tracking:
- Issue: `#312`
- PR: `#313`
- Commit:
  - `1811684 Merge pull request #313 from venkateshbr/feature/312-initiative-pnl-bridge`

Runtime changes:
- Replaced the initiative overview EBITDA bridge with a baseline-to-target
  initiative P&L bridge backed by annual baselines and configurable financial
  values.
- Added `pnl_bridge` to initiative value-bridge responses, including baseline
  year, baseline revenue, baseline gross margin, scenario target values,
  recurring opex, one-off costs, and incremental net run-rate impact.
- Updated the overview bridge rendering to use the new management P&L bridge
  payload and avoid misleading zero-value revenue bars.

Local validation:
- `uv run --extra dev pytest tests/test_initiative_pnl_bridge.py -q`
- `uv run --extra dev ruff check app/domain/financials.py app/services/financial.py tests/test_initiative_pnl_bridge.py`
- `npm run build -- --configuration development` from `apps/web`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Deployed with `infra/hostinger/deploy-change-to-dev.sh`.
- Initial scripted public validation hit the known transient `/health` 404
  readiness race immediately after container recreation.
- Manual validation passed for local and public `/health` and `/api/health`.
- Real dev API validation passed for ACME `ENT-001`: initiative value bridge
  returned `pnl_bridge`, `baseline_year=2026`, and the expected seven base-case
  bridge steps.
- Real dev browser validation passed on `/initiatives/{ENT-001 id}`: the
  `initiative-pnl-bridge` component rendered FY2026, target revenue, target
  run-rate value, incremental net impact, and a nonblank ECharts canvas.

Schema/data SQL applied to dev:
- None.

Schema/data SQL required for production:
- None.

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `1811684 Merge pull request #313 from venkateshbr/feature/312-initiative-pnl-bridge`
- Schema/data SQL applied to production: none.
- Initial scripted public validation hit the known transient `/health` 404
  readiness race immediately after container recreation.
- Manual validation passed for local and public `/health` and `/api/health`.
- Real production API validation passed for ACME `ENT-001`: initiative value
  bridge returned `pnl_bridge`, `baseline_year=2026`, and the expected seven
  base-case bridge steps.
- Real production browser validation passed on `/initiatives/{ENT-001 id}`:
  the `initiative-pnl-bridge` component rendered FY2026, target revenue, target
  run-rate value, incremental net impact, and a nonblank ECharts canvas.

### 2026-06-18 - Benefit Ledger Editor and CSV Import

Status: promoted to production

GitHub tracking:
- Issue: `#306`
- PR: `#307`
- Commits:
  - `8fae6e7 feat: add benefit ledger editor import`
  - `06a2b89 docs: track benefit ledger import release`

Runtime changes:
- Added Benefit Tracking tabs for summary, ledger row editing, and CSV import.
- CSV imports use `initiative_code`, period fields, and `actual_amount`; the
  locked plan amount is derived server-side from the current bankable plan.
- Added ACME production remediation guide and a 240-row monthly import CSV for
  the 2027-2028 benefit realization ledger.

Local validation:
- `uv run --extra dev pytest tests/test_bankable_plans.py tests/test_benefit_realization_ledger.py -q`
- `uv run --extra dev ruff check app/domain/financials.py app/repositories/financial.py app/routers/financials.py app/services/financial.py tests/test_bankable_plans.py tests/test_benefit_realization_ledger.py`
- `npm run build -- --configuration development` from `apps/web`

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Deployed with `infra/hostinger/deploy-change-to-dev.sh`.
- First validation hit a transient public/local readiness race after container
  recreation; the dev compose stack was brought back up and then validated.
- `infra/hostinger/validate-dev.sh` passed for `/health` and `/api/health`.
- Real API import acceptance passed with
  `docs/user-guides/acme-benefit-ledger-import.csv`: `0 created`,
  `240 updated`, `0 errors`.
- Real browser acceptance passed on
  `https://transmuter-dev.ishirock.tech/financials/benefit-tracking` for
  `Summary`, `Ledger Entries`, and `Import` tabs.

Schema/data SQL applied to dev:
- None. Existing `benefit_realization_ledger` schema is reused.

Schema/data SQL required for production:
- None. Existing `benefit_realization_ledger` schema is reused.

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `39ec56c feat: add benefit ledger editor import`
- Schema/data SQL applied to production: none.
- `infra/hostinger/validate-prod.sh` passed for `/health` and `/api/health`.
- Real production browser validation passed for
  `/financials/benefit-tracking`, including `Summary`, `Ledger Entries`, and
  `Import` tabs.
- Production browser validation intentionally did not create, edit, delete, or
  import ledger rows; founder manual/import testing remains the next step.

### 2026-06-18 - Pipeline Stage Normalization and Dynamic Stage Dashboard

Status: promoted to production

GitHub tracking:
- Issue: `#299`
- PR: `#300`
- Issue: `#301`
- PR: `#302`
- Commits:
  - `bcfb079 fix: normalize initiative pipeline stages (#300)`
  - `0d71979 fix: make dashboard stages tenant-configured (#302)`

Runtime changes:
- Deduplicate Initiative Pipeline stage options so one stored stage renders one
  stage group.
- Normalize the ACME/demo active portfolio from legacy `in_progress` to the
  configured governance stage `executing`.
- Update ACME seed defaults so future seeded enterprise initiatives use
  `executing`.
- Build dashboard stage filters and `pipeline_by_stage` from the full configured
  gate order, including the initial `from_stage`.
- Treat tenant-configured terminal stages such as ACME `realized` as terminal
  for stage-gate waterline grouping.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Validated health: `/health`, `/api/health`
- Validated ACME API state: 10 initiatives, all with `stage=executing`
- Validated dashboard API state: ACME stages appear as `identified`,
  `validated`, `planned`, `committed`, `executing`, `realized`, with 10
  initiatives in `executing`.
- Validated browser scenario: annual baseline / Initiative Portfolio acceptance
  scenario now asserts one pipeline stage group with `data-stage-id=executing`.

Schema/data SQL applied to dev:
- `supabase/migrations/20260618000001_normalize_legacy_in_progress_stage.sql`

Schema/data SQL required for production:
- `supabase/migrations/20260618000001_normalize_legacy_in_progress_stage.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `9e6a8e8 docs: update release manifest for stage promotion (#303)`
- Schema/data SQL applied to production:
  `supabase/migrations/20260618000001_normalize_legacy_in_progress_stage.sql`
- Validated health: `/health`, `/api/health`
- Validated ACME API state: 10 initiatives, all with `stage=executing`
- Validated dashboard API state: `pipeline_by_stage` contains the configured
  ACME order `identified`, `validated`, `planned`, `committed`, `executing`,
  `realized`, with 10 initiatives in `executing`.
- Validated browser state: `/initiatives/pipeline` renders one
  `data-testid=pipeline-stage-group` with `data-stage-id=executing` and the
  subtitle `10 initiatives across 1 stage`.

Operational notes:
- The first promotion attempt with `--schema` failed before deployment because
  host-side `psql` could not resolve the Docker service hostname `db`.
- The SQL was applied through the self-hosted Supabase DB container as
  `supabase_admin`, with `search_path=transmuter,public,extensions`; it updated
  10 production initiatives.
- The subsequent production deploy rebuilt/restarted the API and web containers.
  The script exited on the known public validation 404 path after containers were
  healthy; manual health/API/browser validation passed.
- The broad annual-baseline production E2E surfaced an unrelated seeded baseline
  lock mismatch, tracked separately as `#304`.

### 2026-06-18 - ACME Platform Improvements and Initiative Portfolio

Status: promoted to production

GitHub tracking:
- Platform improvement PRs: `#283`, `#293`
- Initiative Portfolio PR: `#296`
- Release manifest tracking issue: `#297`
- Production commit: `47cbce8 feat: add initiative portfolio dashboard (#296)`

Runtime changes:
- Added benefits realization governance and Benefits Register.
- Added Initiative Portfolio dashboard under `Dashboard > Initiative Portfolio`.
- Fixed initiative baseline visibility in initiative financials and edit screens.
- Added portfolio initiative API endpoint and frontend report.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Validated health: `/health`, `/api/health`
- Validated ACME scenario: annual baseline / Initiative Portfolio acceptance
  scenario passed for 10 initiatives.

Schema SQL applied to dev:
- `supabase/migrations/20260617000003_benefit_validation_register.sql`
- `supabase/migrations/20260617000004_harden_benefit_validation_event_rls.sql`

Schema SQL applied to production:
- `supabase/migrations/20260617000003_benefit_validation_register.sql`
- `supabase/migrations/20260617000004_harden_benefit_validation_event_rls.sql`

Production validation:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Health checks passed: `/health`, `/api/health`
- Frontend bundle confirmed: `main-VLNBSQLQ.js`
- Initiative Portfolio route confirmed:
  `/financials/initiative-portfolio`
- Schema parity confirmed for:
  - 14 benefit-line validation columns,
  - `financial_benefit_line_validation_events`,
  - `fblve_select` and `fblve_insert` RLS policies,
  - benefit validation and handoff indexes.

Operational notes:
- Initial generic production schema apply failed because the configured app DB
  connection was not the owner of existing Supabase-owned tables.
- The SQL was applied through the self-hosted Supabase DB container as
  `supabase_admin`, with `search_path=transmuter,public,extensions`.
- No additional schema SQL is pending for the Initiative Portfolio PR itself.
