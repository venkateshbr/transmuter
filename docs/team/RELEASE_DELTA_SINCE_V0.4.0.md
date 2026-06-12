# Release Delta Since v0.4.0

Issue: #259
Base tag: `v0.4.0`
Base commit: `563f5b026716deb9ad889a0bd7dccc4fab260450`
Compared head: `origin/main` at `f53b49f1f628990355faf07993f2d1b76484a0e0`
Generated: 2026-06-12

## Executive Summary

The post-`v0.4.0` work refactors Transmuter from a mostly fixed financial model
into a tenant-configurable transformation platform. The main changes are a clean
configurable financial engine, configurable benefit lines and cost lines, formula
metrics, configurable value bridge rows, a workbook dry-run/load path, blank new
tenant onboarding, and real API/browser acceptance coverage for the new model.

The functional intent is that a tenant can configure its own financial metrics,
KPIs, scenarios, benefit lines, cost categories, workstreams, markets, tags, and
governance setup before loading or creating initiatives.

## Included Changes

| PR | Commit | Area | Summary |
| --- | --- | --- | --- |
| #238 | `91b3b92` | Financial engine | Added the clean configurable financial platform refactor, including tenant-scoped metric definitions, scenario definitions, benefit lines, clean metric values, and reporting settings. |
| #239 | `78fde22` | Financial calculations | Added configurable formula metric evaluation using configured metric definitions. |
| #240 | `66f12f0` | Value bridge | Exposed configurable value bridge rows through API/domain/service layers. |
| #241 | `9a885e0` | Admin UI/API | Added Admin management for configurable value bridge rows. |
| #242 | `d458d5e` | Financial grid | Rendered formula metrics as read-only rows in the initiative financial grid. |
| #243 | `8799136` | Financial grid | Added benefit line entry and display in the financial grid. |
| #244 | `12cdd0b` | Phasing | Generated phased benefit line values from configured timing/phasing inputs. |
| #245 | `5402062` | Phasing | Generated phased cost lines from configured timing/phasing inputs. |
| #246 | `a710246` | Portfolio reporting | Added portfolio value ramp reporting from configurable financial data. |
| #247 | `e8d8694` | Metadata | Added financial line attribute definitions for tenant-specific benefit/cost attributes. |
| #248 | `8d0651a` | Workbook import | Added anonymised portfolio workbook dry-run validation. |
| #249 | `12270f7` | Readiness docs | Added clean financial refactor deployment readiness notes. |
| #252 | `158b188` | Formula engine | Fixed formula evaluation by dependency order. |
| #253 | `1bc3095` | Tenant onboarding | Kept new tenant onboarding blank instead of seeding operational sample/config data. |
| #255 | `3289937` | Acceptance | Added real API configurable workbook acceptance coverage. |
| #258 | `f53b49f` | Browser E2E | Updated public browser E2E to discover configurable financial grid rows at runtime. |

## Data Model Impact

New configurable financial tables are introduced by:

- `supabase/migrations/20260611000002_clean_configurable_financial_engine.sql`
- `supabase/migrations/20260612000001_financial_attribute_definitions.sql`
- Matching Hostinger-local copies under `infra/supabase/migrations/`

The model now includes tenant-scoped configuration and transactional tables for:

- `financial_metric_definitions`
- `financial_scenarios`
- `financial_benefit_lines`
- `financial_metric_values`
- `financial_bridge_rows`
- `financial_attribute_definitions`

All new model areas are tenant-scoped and are intended to run under Supabase RLS.
Money remains represented as PostgreSQL `NUMERIC(15,4)`, Python `Decimal`, and
string JSON values at API boundaries.

The previous fixed financial entry model remains present for compatibility, but
the configurable financial path is now the primary path for new tenant setup and
portfolio workbook loading.

## Backend Impact

The backend financial domain, repository, service, and router layers now support:

- Tenant-managed financial metric definitions and scenarios.
- Benefit line definitions with phasing and optional custom attributes.
- Clean metric values by metric definition, scenario, benefit line, year, and month.
- Configurable formula metrics with dependency-ordered evaluation.
- Configurable value bridge rows and portfolio value ramp reporting.
- Workbook dry-run and load tooling through `apps/api/app/services/portfolio_workbook.py`
  and `apps/api/scripts/load_portfolio_workbook.py`.

Tenant bootstrap was changed so new tenants do not receive seeded operational data.
This supports the preferred onboarding flow where tenant admins configure their
own master data and financial model before creating initiatives.

## Frontend Impact

Admin and initiative screens now support more of the configurable platform model:

- Admin Financial Configuration includes configurable financial engine definitions,
  scenarios, value bridge rows, and financial line attributes.
- Initiative create/setup checks now expect tenant configuration to exist before
  initiative creation.
- Initiative financials render configurable benefit lines, scenario-specific clean
  metric rows, formula/read-only rows, generated phased values, and configured
  cost categories.
- Portfolio financials and dashboard views consume configurable rollups where
  available.
- Public browser E2E now discovers financial metric/cost rows from the rendered
  grid and API model rather than hardcoding legacy row keys.

## API Surface Impact

The following API areas changed materially:

- `/financial-engine-configuration`
- `/admin/financial-configuration`
- `/initiatives/{id}/financials`
- `/initiatives/{id}/financials/selections`
- `/initiatives/{id}/financials/value-bridge`
- `/initiatives/{id}/financials/scenario-summary`
- Portfolio financial reporting endpoints
- Tenant/platform bootstrap and cleanup endpoints

The API remains backward-compatible enough for existing acceptance coverage, but
new configurable tenant behavior should use financial metric definitions,
scenarios, benefit lines, cost lines, and clean metric values rather than relying
on fixed legacy fields such as `revenue_uplift_base`.

## Test And Acceptance Evidence

Automated coverage added or updated since `v0.4.0` includes:

- `apps/api/tests/test_financial_dynamic_value_bridge.py`
- `apps/api/tests/test_financial_formula_metrics.py`
- `apps/api/tests/test_portfolio_workbook.py`
- `apps/api/tests/test_tenant_bootstrap.py`
- `apps/api/tests/acceptance/test_real_api_configurable_workbook.py`
- `apps/web/e2e/real-ui-acceptance.mjs`

Observed verification during this release-delta pass:

- `node --check apps/web/e2e/real-ui-acceptance.mjs`: passed.
- `npm run build` from `apps/web`: passed.
- Public Hostinger browser acceptance passed against:
  - UI: `https://transmuter.ishirock.tech`
  - API: `https://transmuter.ishirock.tech/api`
- GitHub CI passed for PR #258 before merge.

Deployment note: Hostinger was deployed and publicly validated at `3289937`
before PR #258. PR #258 is merged into `origin/main` and its browser acceptance
script was validated against the public app, but the hosted app image still needs
to be rebuilt if we want the served bundle to include the additional acceptance
harness metadata from `f53b49f`.

## Launch Impact

This batch is launch-positive because it removes hardcoded financial assumptions
and supports the desired configurable tenant setup model. The next meaningful
launch test is issue #260: register a new public tenant, configure dimensions and
financial metrics from `Initiative_Portfolio_Anonymised.xlsx`, load the workbook
data, and validate the result through real API and browser workflows.

## Residual Risks

- Workbook load must be proven against a brand-new public tenant, not only through
  dry-run/API acceptance.
- Exact workbook-to-platform field coverage still needs to be documented during
  issue #260, especially for charter details, benefit metadata, cost metadata,
  and any free-form Excel columns that do not map cleanly to current entities.
- The hosted app should be rebuilt from `origin/main` after PR #258 if we require
  the deployed frontend harness metadata to match the repository.
- Open pre-existing issues for meetings, RBAC, tenant deletion, and Stripe runtime
  configuration remain outside this financial refactor delta.

