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

### 2026-06-18 - Benefit Ledger Editor and CSV Import

Status: dev validated; production promotion pending review and explicit approval

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
- Pending promotion.

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
