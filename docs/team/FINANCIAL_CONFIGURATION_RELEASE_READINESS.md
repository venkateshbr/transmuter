# Financial Configuration Release Readiness

Issue: #153
Parent: #146
Owner: Sthira
Last updated: 2026-05-14

## Scope

This release introduces tenant-scoped financial configuration groups/items,
cost-line category assignment, and portfolio financial reporting by category.

## Migration

Migration file:

- `supabase/migrations/20260508000001_financial_configuration.sql`

Safety checks:

- Creates `financial_config_groups` and `financial_config_items` with
  `tenant_id uuid NOT NULL`.
- Enables RLS on both new tables.
- Allows read access only for the current tenant.
- Allows insert/update/delete only for the current tenant when
  `current_user_role() = 'transformation_office'`.
- Adds `financial_cost_lines.category_key TEXT NOT NULL DEFAULT 'other'`.
- Adds an index on `(tenant_id, category_key)` for portfolio filtering.
- Historical migration seeded default groups/items for existing tenants with
  `ON CONFLICT (tenant_id, key) DO NOTHING`; normal new-tenant onboarding no
  longer seeds financial configuration rows.
- Backfills blank or null cost-line categories to `other`.

Default cost categories:

- `implementation`: one-time implementation costs.
- `vendor`: one-time vendor / consulting costs.
- `software`: recurring software / license costs.
- `labor`: recurring labor / operations costs.
- `other`: uncategorized fallback.

Default metric groups:

- Revenue
- COGS
- Gross Margin

## Operational Checks

Before release:

- Confirm the migration has been applied once in the target Supabase project.
- Confirm existing upgraded tenants have default financial configuration rows;
  newly registered tenants should start blank and self-configure.
- Confirm existing financial cost lines have non-empty `category_key`.
- Confirm transformation office users can save Admin financial configuration.
- Confirm viewers can read `/financial-configuration` and `/portfolio/financials`.
- Confirm initiative owners cannot mutate Admin financial configuration.

Verification commands used for readiness:

```bash
cd apps/api
./.venv/bin/python -m pytest tests/test_financial_portfolio.py -q
RUN_REAL_ACCEPTANCE=1 TRANSMUTER_API_BASE_URL=http://127.0.0.1:8000 ./.venv/bin/python -m pytest \
  tests/acceptance/test_real_api_sample_data.py::test_real_api_financial_grid_save_reload_and_value_bridge \
  tests/acceptance/test_real_api_sample_data.py::test_real_api_financial_configuration_category_reassignment_and_portfolio_rollup \
  tests/acceptance/test_real_api_sample_data.py::test_real_api_financial_excel_export_import_roundtrip \
  -q
```

Observed results:

- `tests/test_financial_portfolio.py`: 6 passed.
- Focused real API financial acceptance: 3 passed.
- Prior real browser acceptance for issue #154 passed with Admin financial
  category creation and portfolio Financials category rollup.

## Rollout Notes

- No destructive data migration is required.
- Existing cost lines retain their amounts and are categorized as `other` if no
  category is present.
- Financial configuration changes remain tenant-local.
- The API continues to serialize money as strings and compute with Decimal.
- Prahari review for issue #151 passed after RLS and tenant-parent validation
  fixes.

## Rollback

If release validation fails before production cutover, do not remove the new
columns or tables. Disable the frontend route/entry point for `/financials` and
Admin Financial Configuration, then investigate with the seeded acceptance
scenario. The schema additions are additive and should be left in place to avoid
dropping tenant financial taxonomy data.
