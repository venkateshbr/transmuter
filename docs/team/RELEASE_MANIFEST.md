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

### 2026-06-18 - Pipeline Stage Normalization

Status: dev validated, pending production promotion

GitHub tracking:
- Issue: `#299`
- PR: `#300`
- Commit: pending merge commit

Runtime changes:
- Deduplicate Initiative Pipeline stage options so one stored stage renders one
  stage group.
- Normalize the ACME/demo active portfolio from legacy `in_progress` to the
  configured governance stage `executing`.
- Update ACME seed defaults so future seeded enterprise initiatives use
  `executing`.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Validated health: `/health`, `/api/health`
- Validated ACME API state: 10 initiatives, all with `stage=executing`
- Validated browser scenario: annual baseline / Initiative Portfolio acceptance
  scenario now asserts one pipeline stage group with `data-stage-id=executing`.

Schema/data SQL applied to dev:
- `supabase/migrations/20260618000001_normalize_legacy_in_progress_stage.sql`

Schema/data SQL required for production:
- `supabase/migrations/20260618000001_normalize_legacy_in_progress_stage.sql`

Production validation:
- Pending production promotion.

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
