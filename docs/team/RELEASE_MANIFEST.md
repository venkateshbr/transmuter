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

Deployment note:
- Hostinger deploy commands use the remote VPS Docker project API. The API
  fetches the pushed GitHub commit and `docker-compose.hostinger.yml`, then
  builds/recreates the selected Docker project on the VPS.
- Keep `HOSTINGER_API_KEY` or `HOSTINGER_API_TOKEN` and `HOSTINGER_VPS_ID` in an
  ignored local `.env`, `infra/hostinger/.env`, `infra/hostinger/.env.dev`, or
  the operator shell.
- Dev and production remain separate Docker Compose projects on the same
  Hostinger VPS. `infra/hostinger/deploy.sh` is legacy VPS-local fallback only.

## Current Release Entries

### 2026-07-16 - Five-Tenant Launch Readiness And Browser Acceptance

Status: dev deployed and accepted; production promotion explicitly approved by
the founder on 2026-07-16; PR merge and the schema-before-code rollout below
must complete before production validation

GitHub tracking:

- Integration PR: `#416`, full-sweep commit `1f3330b`, artifact follow-up
  commit `5cbabe5`, initiative-baseline/ACME-guide runtime commit `1c5f184`,
  and final dev runtime commit `e5a769d`.
- Release findings: `#401`, `#403`-`#412`, `#414`, and `#417`-`#419`.
- Invite/password acceptance: `#216`.
- Admin bulk-meeting cleanup: `#224`.
- Parent acceptance: `#399`; browser execution: `#413`; initiative annual
  baseline UI: `#420`; fresh-tenant setup acceptance: `#421`; sequential
  strategic-parameter persistence: `#422`.
- External Microsoft Graph gates: `#220`, `#389`, and `#390`.

Dev deployment:

- Environment: `https://transmuter-dev.ishirock.tech`.
- Schema: `transmuter_dev`.
- Deployed commit: `e5a769d` (`1f3330b` was the uninterrupted five-tenant
  browser-sweep runtime and `1c5f184` the configured ACME runtime).
- Hostinger action: `104365210`, successful on `2026-07-15`; configured ACME
  action `104346054` succeeded at `2026-07-15T12:41:26Z`; artifact action
  `104308750` succeeded at `2026-07-15T09:50:16Z`; full-sweep action
  `104300670` succeeded at `2026-07-15T08:55:20Z`.
- Dev already has the two migrations required by the production rollout:
  `supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql` and
  `supabase/migrations/20260715000001_meeting_artifact_session_agenda.sql`.
- Production project, schema, data, configuration, and consent were untouched.

Acceptance evidence:

- Focused backend: 87 passing fiscal, portfolio, benefit-ledger, operating-RBAC,
  and pipeline-control tests; Ruff format/check and mypy passed.
- Frontend: 31/31 unit tests and Angular production build passed.
- Real mutable API run: 2,635 requests, 50 authenticated users, 55 isolation
  denials across five tenants.
- External headed Google Chrome: one process/worker, 29 routes per tenant,
  desktop/mobile and dark mode, USD/SGD/GBP/EUR/AUD, January/April/July fiscal
  starts, error/retry probes, viewer RBAC, and zero unexplained 5xx/page errors.
- People: real delivered Resend setup link, account activation, temporary
  password forced-change, fixture password restoration, invite list/resend/
  revoke, and guarded cleanup.
- Meetings: weekly Saturday series, `ENT-005` agenda, notes autosave, agenda-
  linked decision, AI minutes generation/edit/save/reload, completion, and a
  two-series Admin cleanup.
- Dedicated ACME guide acceptance on `1c5f184`: all 20 named scenarios passed
  in one external headed Chromium session in 2.0 minutes with zero page errors
  or observed 5xx responses. It covered a fresh HITL initiative, persisted
  annual baseline, benefit line, twelve monthly cost rows, Saturday meeting
  with agenda-linked decision and risk, and browser cleanup back to ten
  initiatives with no temporary meeting.
- Fresh-tenant setup-guide acceptance on deployed `e5a769d`: one external
  headed Chromium worker completed Stripe sandbox provisioning, first login,
  master data, five gates, ten people, ten guided initiatives, a representative
  value/delivery/governance case, four reconciled Shared Costs runs, 21 current
  routes, board-pack export, and exact-slug Platform cleanup in 4.1 minutes.
  It reported no browser page errors or observed server errors and used no API
  or database mutation shortcuts.
- The same run exposed the Admin strategic-parameter save race tracked in
  `#422`; the fix was deployed at `e5a769d` and browser-retested through route
  reload and initiative authoring.
- Dedicated headed controls: risk/KPI filter and create navigation, matrix
  contributor drilldown, and Benefit Tracking bankable-plan navigation passed.
- Headed artifact acceptance downloaded authenticated pipeline CSV, board-pack,
  initiative, blank-template, and financial workbooks; previewed the blank
  initiative import; enforced the financial lock; and exercised benefit-ledger
  import validation with zero fixture mutations.
- Final deterministic reseed restored zero meetings/sessions/agendas/actions/
  invites. Manifest SHA-256 remained
  `3ef52dd7015ee7c8953ccf7893e8d62b03a8fe9fa6588e3ab95707098cf58a50`.
- Final read-only API run: 2,450 requests, 50 users, 55 isolation denials.

Production rollout plan:

- Final-head CI run `29428043985` passed backend, frontend, specs, secret scan,
  Agent eval, and policy checks on documentation head `917001f`.
- Squash-merge PR `#416` into `main`; deploy only the resulting pushed merge
  commit.
- Stop and verify both production project aliases, then apply the forward-only
  Graph migration with `--offline-schema` before new application code starts.
- In the same stopped migration window apply the additive meeting-artifact
  migration after the Graph migration:
  `supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql`, then
  `supabase/migrations/20260715000001_meeting_artifact_session_agenda.sql`.
- Recreate production from the exact merged commit, correct the saved Graph
  scope line to the reviewed seven-scope set, and keep Microsoft Graph
  disconnected. Do not create or refresh organizer consent during this release.
- Validate public web/API health and a real read-only headed-browser login and
  route sweep. Record the action, merge commit, and result in this entry.
- Microsoft Graph callback-registration evidence, fresh organizer consent,
  live invite/join-link refresh, and transcript acceptance remain external
  follow-ups under `#220`, `#389`, and `#390`; they do not authorize weakening
  the disconnected fail-closed behavior.

### 2026-07-11 - Microsoft Graph OAuth Environment Isolation

Status: deployed and API-verified in dev; production pending explicit approval

GitHub tracking:
- Isolation bug: `#389`.
- Main implementation: PR `#394`, merge commit `8da8bee`.
- Offline rollout incident fix: PR `#395`, merge commit `7c60fbc`.
- Vastu and Prahari approved both the OAuth boundary and the final locked
  offline rollout; both PRs passed backend, frontend, specs, secret scan, and
  Agent eval CI gates.

Runtime changes:
- Bound Microsoft Graph tokens and OAuth state to the deployment environment,
  schema, Entra tenant, client, callback, encryption key, scopes, actor, and
  generation counters.
- Added tenant-specific OIDC discovery/JWKS validation, PKCE S256, nonce,
  single-use database state, refresh compare-and-swap, and account/scope checks.
- Suppressed callback request bodies, query data, cookies, and access logs from
  application and proxy observability.
- Added a same-SHA offline migration path that stops canonical writers, rejects
  ambient routing/control overrides, reads saved Hostinger dotenv as data, uses
  the canonical saved runtime environment, and requires schema-job cleanup.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Deployed commit: `7c60fbc`.
- Applied offline SQL:
  `supabase/migrations/20260711000002_harden_microsoft_graph_oauth.sql`.
- The first attempt stopped dev with action `103646379`, but the old schema
  runner sourced Hostinger dotenv and skipped SQL after an unquoted display-name
  email parse error. Dev was contained offline with action `103647000`; no
  production project, schema, consent, or credential was touched.
- The reviewed rerun emitted the schema success marker, deleted the temporary
  schema project, and deployed with action `103651377`.
- The hardened API then correctly reported Graph unconfigured because the saved
  scope line omitted `openid` and `profile`. Dev-only action `103652672` fixed
  the exact seven-scope list on the same commit.
- Public `/health` and `/api/health` passed after both final actions.

Dev acceptance:
- Live read-only SQL confirmed `integration_oauth_states`, all ten hardened
  connection columns, zero Graph connections, and zero linked external events.
- Seeded transformation-office login and `/auth/me` passed against the real API.
- OAuth start returned the exact dev callback, tenant-specific Entra authority,
  `form_post`, seven reviewed scopes, PKCE S256, nonce, 256-bit state, and a
  callback-scoped `__Secure-`/Secure/HttpOnly/SameSite=None cookie.
- A foreign environment-shaped state failed before provider exchange. The real
  dev state was cancelled through the POST callback; final SQL showed one
  cancelled state, zero pending states, zero terminal secret rows, zero context
  mismatches, and zero connections.
- Dev and production saved environments have distinct clients, client secrets,
  callbacks, and encryption keys. Disposable verification projects were deleted.
- The required in-app browser surface returned no available targets, so browser
  and interactive Entra consent evidence were not substituted with another
  backend.

Production requirements:
- Production remains on `5793115` and was not changed by this dev rollout.
- Before promotion, obtain explicit approval, correct the production OIDC scope
  line, and verify the callback in a redacted Entra app-registration export.
- Promote `7c60fbc` or a later reviewed main commit with the same migration via
  the locked offline production command.
- Complete fresh organizer consent, invite/join URL, forced refresh, transcript,
  and deterministic external-event cleanup before closing `#389` or `#220`.

### 2026-07-11 - Meetings Boundaries, JWT Audit, and Tenant Authorization Hardening

Status: promoted to production and verified

GitHub tracking:
- Meetings V3: issue `#223`, PR `#380`, merge commit `007fb50`.
- Production meeting release record: PR `#387`, merge commit `518c844`.
- JWT dependency remediation: issue `#383`, Prahari review `#384`, PR `#386`,
  merge commit `1c3e023`.
- Registration cleanup assertion: issue `#385`, PR `#386`.
- Agent eval recovery: issue `#381`, PR `#382`, merge commit `13d5db3`.
- Tenant authorization hardening: issue `#388`, PRs `#391` and `#392`, merge
  commits `370197b` and `5793115`.
- Security review: issue `#390`; the `#388` identity scope has Prahari live
  approval. The separate Microsoft Graph isolation scope remains open.

Runtime changes:
- Added an explicit recurring meeting `series_start_date` boundary.
- Added the authenticated IANA timezone catalog and timezone selectors for meeting
  series and Microsoft Teams invite setup.
- Replaced `python-jose` with the existing `joserfc` dependency for application
  JWTs and Microsoft OAuth state.
- Restricted JWT algorithms to `HS256`, `HS384`, or `HS512` and enforced a
  minimum 32-character secret.
- Removed the vulnerable unused `ecdsa` dependency reported by
  `PYSEC-2026-1325`.
- Aligned deterministic initiative-intake evals with the supported
  non-financial wizard contract and made the Agent eval suite a pull-request
  gate.
- Moved ordinary-user tenant and role authorization out of editable
  `user_metadata` into independent top-level Supabase `app_metadata` objects:
  `transmuter_authorization_transmuter_dev` and
  `transmuter_authorization_transmuter`.
- Made the API verify the exact bearer through Supabase Auth and require an
  exact active canonical `users` row match for subject, tenant, and role.
- Replaced RLS identity helpers with schema-scoped `SECURITY DEFINER` lookups
  that enforce the same canonical match and do not trust `user_metadata`.
- Added PII-free, idempotent seed/cleanup reconciliation with independent
  production and global-cleanup confirmation gates.
- Fixed the live `supabase-auth==2.29.0` integration boundary: verified ES256
  `ClaimsResponse` values are runtime mappings, not attribute-bearing objects.

CI and review evidence:
- PR `#386` passed backend lint/type/tests, the exact Python 3.12 strict
  dependency audit, frontend build/tests, spec validation, and secret scan.
- Prahari issue `#384` approved algorithm allowlisting, secret validation,
  registered-claim validation, existing-token interoperability, and Microsoft
  OAuth state handling with no blockers.
- PR `#382` passed the new pull-request Agent eval job with `22/22` tests.
- Post-merge `main` run `29138383598` passed backend, frontend, specs, secret
  scan, Agent evals, and the dependent staging job.
- PR `#391` passed backend, frontend, secret scan, spec validation, and Agent
  evals; Vastu and Prahari approved the scoped authorization design.
- PR `#392` added the red/green real-SDK mapping regression and passed the same
  gates; Vastu and Prahari approved the two-file follow-up.
- Current-main run `29141257001` passed backend, frontend, specs, secret scan,
  Agent evals, and the configured staging gate for `5793115`.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Final deployment commit: `5793115`.
- Schema SQL applied:
  - `supabase/migrations/20260701000001_meeting_series_start_date.sql`;
  - `supabase/migrations/20260711000001_harden_rls_identity_claims.sql` as
    `supabase_admin`.
- Authorization rollout actions:
  - API action `103616741` for `370197b` after schema application, successful;
  - adapter action `103620268` for `5793115`, successful at
    `2026-07-11T05:31:12Z`.
- Public `/health` and `/api/health` returned `200`.
- Authenticated login returned access and refresh tokens after the JWT library
  migration.
- Authenticated `/api/meetings/timezones` returned `486` IANA zones.
- OpenAPI exposes `timezone`, `series_start_date`, and `series_end_date` on
  meeting create/update.
- A deterministic weekly series bounded from `2026-07-13` through
  `2026-08-10` was created in `Asia/Singapore`, updated to `Europe/London`, and
  returned only bounded rolling sessions.
- The temporary meeting was deleted; meeting and generated-session reads both
  returned `404` afterward.
- PR `#380` records the matching real dev browser flow for timezone selection,
  explicit series start, persistence, and cleanup against the same frontend
  tree.
- Real ES256/API/PostgREST authorization acceptance passed for matching claims,
  wrong tenant, wrong role, missing active scope with legacy metadata,
  noncanonical tenant text, inactive users, and Auth subjects without a
  platform row. All controlled fixture mutations were restored.
- Post-cleanup fresh login, `/auth/me`, refresh, and direct RLS passed; dev seed
  and cleanup reconciliation both returned zero planned changes.

Schema SQL applied to production:
- `supabase/migrations/20260701000001_meeting_series_start_date.sql`;
- `supabase/migrations/20260711000001_harden_rls_identity_claims.sql` as
  `supabase_admin`.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `5793115`
- Meeting-series promotion action `103601800` completed successfully on
  `518c844`; authorization API action `103620844` followed the schema-before-code
  migration and completed successfully at `2026-07-11T05:34:07Z` on `5793115`.
- Saved compose content matched `docker-compose.hostinger.yml`; public web and
  API health returned `200`.
- Both RLS helpers passed owner/BYPASSRLS, `SECURITY DEFINER`, pinned
  `search_path`, ACL, and captured production-scope checks.
- Real production ES256/API/PostgREST acceptance denied wrong tenant, role,
  scope, noncanonical tenant, inactive, and unknown-subject cases while fresh
  login, `/auth/me`, refresh, and matching direct RLS passed.
- `/meetings/timezones` returned `200`; a temporary weekly series with
  `Asia/Singapore`, explicit start/end bounds, owner, attendee, and agenda item
  was created with `201`, verified, and deleted with `204`.
- Cleanup ran only after dev and production verification. It removed legacy
  authorization keys for 42 dev-union identities and 3 production-only
  identities. Final seed and cleanup dry-runs are zero-diff in both schemas;
  the canonical union has 45 users, zero missing Auth identities, and zero
  tenant/role authorization keys in `user_metadata`.
- The platform administrator remains one global-only allowlisted Auth identity
  with no tenant/scoped claim and no `users` row in either application schema.

Operational notes:
- The exposed `public` Supabase schema has no Transmuter `users` table or
  identity helper functions; the application authorization surfaces are only
  `transmuter_dev` and `transmuter`.
- Dev and production still share one Supabase Auth project, so credentials,
  sessions, and service-role administration are global even though application
  authorization is schema-scoped. Treat eventual Auth-project separation as a
  future architectural hardening opportunity.
- Later environment-only Graph isolation actions `103623230` (dev) and
  `103623550` (production) recreated containers at the same `5793115` compose;
  they did not change the authorization schema or code.

### 2026-06-30 - Platform Stripe Price Configuration

Status: promoted to production

GitHub tracking:
- Issue: `#378`
- PR: `#379`
- Implementation commit: `dbbcb32`
- Merge and production commit: `632f066`

Runtime changes:
- Added platform-owned Stripe Price ID configuration with tenant ID, RLS, and
  seeded launch plan/interval rows.
- Added platform-admin read/update APIs and editable Platform Control fields for
  the four launch Price IDs.
- Checkout now resolves platform configuration first, environment fallback
  second, and inline `price_data` when no Price ID is configured.
- Server validation accepts only `price_...` identifiers and does not expose
  Stripe secret, restricted, publishable, or webhook keys.

Dev validation:
- Applied
  `supabase/migrations/20260630000001_platform_stripe_price_config.sql` to
  `transmuter_dev`.
- Focused backend tests passed (`22 passed`), Ruff passed, and the Angular build
  passed.
- Platform-admin API read/update, invalid secret-like value rejection, and the
  four-input Platform Control UI were validated on the public dev environment.

Production promotion:
- Applied
  `supabase/migrations/20260630000001_platform_stripe_price_config.sql` to
  schema `transmuter` with the internal `supabase_admin` schema-owner
  connection; the application runtime connection was not changed.
- Promoted merge commit `632f066` to the Hostinger production project.
- Public production validation passed for health, platform-admin identity,
  Price ID read API, secret-like value rejection, and the four-input Platform
  Control UI.
- Effective production Price ID count remained `0`; checkout intentionally
  continues to use inline `price_data` until real `price_...` values are saved
  through Platform Control.

### 2026-06-29 - Wizard Financial Scope Cleanup

Status: promoted to production; authenticated production tenant validation pending

GitHub tracking:
- Issue: `#367`
- PR: `#368`
- Commits:
  - `682e48d feat: remove wizard financial suggestions`
  - `9a64511 feat: remove wizard financial suggestions (#367)`
  - `a1b7b99 test: isolate real UI financial acceptance data (#367)`
  - `ad0b023 chore: update joserfc audit dependency (#367)`

Runtime changes:
- Removed financial metric, cost category, annual baseline, and financial AI
  suggestion controls from the Create Initiative wizard.
- Added a narrative-only initiative intake endpoint and Generate Narrative
  action for summary, context/problem, value logic, and dependencies.
- Kept planning suggestions limited to KPIs, risks, and milestones; intake
  create ignores financial entries and cost lines even if old clients send them.
- Scoped Initiative Financials grid rows, benefit lines, and Add Line options
  to the initiative's configured financial scope.
- Prevented duplicate visible benefit lines for the same scoped benefit metric.
- Updated `joserfc` to `1.7.1` to satisfy the CI dependency audit for
  `CVE-2026-48990`.

Local validation:
- `cd apps/api && uv run --extra dev ruff check app/agents/initiative_intake_agent.py app/domain/initiative_intake.py app/routers/initiatives.py app/services/financial.py app/services/initiative.py tests/test_initiative_intake_agent.py tests/test_financial_portfolio.py tests/test_initiative_setup_gate.py tests/test_real_route_coverage.py tests/acceptance/test_real_api_sample_data.py`
- `cd apps/api && uv run --extra dev ruff format --check app/agents/initiative_intake_agent.py app/domain/initiative_intake.py app/routers/initiatives.py app/services/financial.py app/services/initiative.py tests/test_initiative_intake_agent.py tests/test_financial_portfolio.py tests/test_initiative_setup_gate.py tests/test_real_route_coverage.py tests/acceptance/test_real_api_sample_data.py`
- `cd apps/api && uv run --extra dev pytest tests/test_initiative_intake_agent.py tests/test_financial_portfolio.py tests/test_initiative_setup_gate.py -q`: 53 passed.
- `cd apps/web && node --check e2e/real-ui-acceptance.mjs`
- `cd apps/web && node --check e2e/runbook-remediation-validation.mjs`
- `cd apps/web && npm run build`
- `cd apps/web && npx ng test --watch=false --include src/app/features/initiatives/create/create-initiative.component.spec.ts`: 2 passed.

Known local validation note:
- `tests/test_real_route_coverage.py` is blocked in this environment before the
  changed intake route assertions by an existing login/admin-client fixture path:
  `app/routers/auth.py:320 AttributeError: NoneType object has no attribute data`.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema SQL applied: none.
- Deployed with `infra/hostinger/deploy-change-to-dev.sh`.
- Initial scripted validation hit the known immediate public `/health` 404
  readiness race after container recreation.
- Rerun `infra/hostinger/validate-dev.sh` passed for local/public `/health` and
  `/api/health`.
- Final dev redeploy after the dependency audit fix installed `joserfc==1.7.1`
  in the API image; rerun `infra/hostinger/validate-dev.sh` passed.
- Real dev API validation passed:
  - `RUN_REAL_ACCEPTANCE=1 TRANSMUTER_API_BASE_URL=https://transmuter-dev.ishirock.tech/api TRANSMUTER_E2E_EMAIL=admin@acme3-transformation.dev TRANSMUTER_E2E_PASSWORD=... uv run --extra dev pytest tests/acceptance/test_real_api_sample_data.py::test_real_api_initiative_intake_hitl_create_flow -q`
- Real dev browser validation passed:
  - `CHROME_BIN=/usr/bin/chromium-browser TRANSMUTER_UI_BASE_URL=https://transmuter-dev.ishirock.tech TRANSMUTER_API_BASE_URL=https://transmuter-dev.ishirock.tech/api TRANSMUTER_E2E_EMAIL=admin@acme3-transformation.dev TRANSMUTER_E2E_PASSWORD=... CHROME_DEBUG_PORT=9338 node e2e/real-ui-acceptance.mjs`
- Real dev API and browser validation were rerun successfully after the final
  dependency rebuild.

Prahari review:
- Required because the change touches the initiative intake agent path.
- Review note posted on PR `#368`; no merge-blocking security findings.

Schema SQL required for production:
- None.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `682e48d`
- Schema SQL applied: none.
- Promoted with `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- Rerun `infra/hostinger/validate-prod.sh` passed for local/public `/health`
  and `/api/health`.
- Public health probes passed:
  - `https://transmuter.ishirock.tech/health`
  - `https://transmuter.ishirock.tech/api/health`

Production validation note:
- Authenticated production workflow validation is pending because no valid
  production tenant acceptance credential is currently available.
- The dev ACME3 credential authenticated with Supabase Auth but hit existing
  production demo-data drift at `app/routers/auth.py:320`
  (`user_row` returned `None`).
- The stored production launch credential artifact returned `401 Unauthorized`
  for `/api/auth/login`.

### 2026-06-26 - Initiative Financials Entry and Validation Layout

Status: promoted to production

GitHub tracking:
- Issue: `#360`
- PR: `#361`
- Issue: `#362`
- PR: `#363`
- Commits:
  - `1a8287f feat: split initiative financials validation view`
  - `26219ca fix: improve benefit line entry layout`
  - `aefa8cf fix: improve benefit line entry layout`

Runtime changes:
- Split initiative Financials into local `Entry` and `Finance Validation` views.
- Kept summary cards, scenario toggle, and annual baseline above the local
  Financials workspace split.
- Kept benefit entry, cost entry, cost lines, financial grid, save action, and
  assumptions in `Entry`.
- Moved benefit validation cards/actions and the Open Register link into
  `Finance Validation`.
- Updated the benefit-line add form into a responsive two-row layout so Named
  Benefit Line remains editable and Add Line no longer overlaps the End date.

Dev deployment:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema SQL applied: none.
- Deployed with `infra/hostinger/deploy-change-to-dev.sh`.
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- Rerun dev validation passed for local/public `/health` and `/api/health`.
- Browser validation against Pinnacle initiative
  `a129a5a6-d05d-470f-b07e-86505cd6d3a4` confirmed:
  - local `Entry` and `Finance Validation` tabs render in dev;
  - `Entry` is selected by default;
  - validation controls are hidden in `Entry`;
  - the benefit-line form has no internal horizontal overflow and Add Line does
    not overlap at `1440`, `1280`, `1024`, `900`, `768`, and `390px`.

Schema SQL required for production:
- None.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `aefa8cf`
- Schema SQL applied: none.
- Promoted with `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- Rerun production validation passed for local/public `/health` and
  `/api/health`.
- Production frontend bundle confirmed: `main-FOI5MWNI.js`,
  `styles-HKGS6SFL.css`.
- Production lazy chunk confirmed both `financials-view-entry` and
  `benefit-line-entry-form` markers in `chunk-HTR5K3C2.js`.

Operational notes:
- No database or API changes are included.
- The broader mobile initiative detail page still has existing horizontal
  overflow from surrounding initiative/financial grid chrome; this entry only
  remediates the benefit-line form overflow.

### 2026-06-24 - Platform Findings Remediation

Status: promoted to production; authenticated production tenant validation pending

GitHub tracking:
- Issue: `#354`
- PR: `#355`
- Merge commit:
  - `b405442 Fix platform financial and onboarding gaps`

Runtime changes:
- Added benefit-line create/delete APIs and UI delete controls, with delete
  still blocked once financials are locked.
- Cost-line create/delete now respects locked financials; benefit-line Finance
  submit/validate/reject/risk actions remain available after lock.
- Signup intent creation pre-validates initial admin email availability before
  Stripe checkout session creation.
- Checkout completion now marks and surfaces hard provisioning failures instead
  of presenting them as indefinite pending setup.
- People invite/create-user modal now validates required input and locks the
  submit action while the request is in flight.
- Portfolio Financials and Control Tower default to the latest year with data
  and return selected/available years.
- Control Tower and Dashboard attention rows display initiative code/name
  instead of raw UUID-only labels.
- Shared-cost weight-based rules validate structured weights before preview or
  post.
- KPI suggestions now seed an initial actual value so KPI performance can
  compute.
- Gate criteria upsert now reuses existing tenant/gate/criterion rows.
- Bankable plan governance is configurable in Admin and defaults initiative
  bankable lock to Gate 3 while annual baseline lock remains Gate 2.

Local and CI validation:
- `cd apps/api && uv run ruff format --check app tests`
- `cd apps/api && uv run ruff check app tests`
- `cd apps/api && uv run pytest tests/test_platform_billing_routes.py tests/test_financial_portfolio.py tests/test_executive_control.py tests/test_workstream_target_locks.py -q`
- `cd apps/web && npm run build`
- `cd apps/web && ./node_modules/.bin/tsc --noEmit -p tsconfig.app.json`
- `cd apps/web && ./node_modules/.bin/ngc -p tsconfig.app.json`
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
- Initial scripted public validation hit the known immediate `/health` 404
  readiness race after container recreation.
- Rerun dev validation passed for local/public `/health` and `/api/health`.
- Current enterprise scenario seed passed in dev:
  - 10 initiatives.
  - 10 locked bankable plans.
  - Benefit ledger seeded.
  - 4 shared-cost pools.
- ACME full-demo browser validation passed:
  - 10 initiatives.
  - 10 locked bankable plans.
  - 10 KPIs.
  - 10 risks.
  - 40 milestones.
  - 3 dependencies.
  - Benefit ledger actuals `12053200.0020`.
  - 4 shared-cost pools.
  - Rebaseline version `2`.
- Targeted public dev API validation confirmed:
  - `/admin/financial-governance` returns initiative plan lock Gate 3 and
    baseline lock Gate 2.
  - `/portfolio/financials` defaults to selected year `2028` with available
    years `[2026, 2027, 2028]`.
  - `/reports/executive-control-tower` defaults to selected year `2028` and
    attention rows include initiative labels.
  - Locked initiative financial grid has benefit and cost lines.
  - Benefit submit after lock returns `200`.

Prahari review:
- Required because the change touches billing/provisioning and user-management
  flows.
- Review note posted on PR `#355`.
- No merge-blocking security findings: financial mutations retain
  transformation-office RBAC and tenant/initiative scoping; checkout failure
  details are bounded to signup/provisioning state; no new external PII or
  secret flows were introduced.

Schema SQL required for production:
- None.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Promotion commit: `d75df08`
- Schema SQL applied: none.
- Promoted with `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- Initial scripted validation hit the known immediate public `/health` readiness
  race after container recreation.
- Rerun production validation passed for local/public `/health` and
  `/api/health`.
- Authenticated production tenant browser validation remains pending because the
  latest local launch tenant credentials returned `401 Invalid credentials`, no
  other valid production tenant credentials were found in local launch artifacts,
  and platform-admin bootstrap credentials are not configured in
  `infra/hostinger/.env`.

Operational notes:
- Legacy `apps/web/e2e/real-ui-acceptance.mjs` was attempted against dev and
  failed on a stale `seed_dev.py` assumption around admin cost category
  configuration.
- `apps/api/scripts/seed_dev.py` is stale against the current schema because it
  expects `workstreams.business_unit_id`; current enterprise seeding uses the
  join-table model and passed.
- Do not close issue `#354` until authenticated production tenant workflow
  validation is completed with fresh credentials or an approved production
  validation tenant.

### 2026-06-23 - Platform Admin Bootstrap Production Promotion

Status: promoted to production

GitHub tracking:
- Issue: `#351`
- Related implementation issue: `#348`
- Security review: `#349`
- Documentation PR: `#352`
- Runtime promotion was operational against reviewed `main` plus ignored
  Hostinger runtime env correction.
- Runtime code commit:
  - `14ace8a chore: add platform admin startup bootstrap`

Runtime changes:
- Production Hostinger runtime configuration now targets
  `venkatesh@ishirock.com` for `PLATFORM_ADMIN_EMAILS`,
  `PLATFORM_ADMIN_BOOTSTRAP_EMAIL`, and `HOSTINGER_PLATFORM_ADMIN_EMAIL`.
- Platform admin bootstrap remains enabled in production.
- No production schema SQL is required.
- No tenant-scoped table writes are required; the shared Supabase Auth user
  already exists and has `platform_admin` app metadata.

Dev validation:
- Environment: `https://transmuter-dev.ishirock.tech`
- Schema: `transmuter_dev`
- Schema SQL applied: none.
- `infra/hostinger/validate-dev.sh` passed on 2026-06-23.
- Dev `/api/auth/login` returned `role=platform_admin` and the reserved
  platform tenant id for the configured operator.

Production pre-promotion finding:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Running production API container was from the 2026-06-23 03:04 UTC deployment
  and still allowlisted `admin@ishirock.com`.
- The same platform admin login that passed on dev returned a production 500
  because the old container fell through to tenant-user lookup after the
  allowlist mismatch.

Production promotion:
- Environment: `https://transmuter.ishirock.tech`
- Schema: `transmuter`
- Initial promotion command commit: `306e48e`
- Final production recreate command commit: `690e21f`
- Schema SQL applied: none.
- Promoted with `CONFIRM_PROMOTE=1 infra/hostinger/promote-dev-to-prod.sh`.
- The same promotion command was unintentionally rerun while creating PR `#352`;
  because commit `690e21f` is release-manifest-only, this did not change runtime
  application code. Production validation was rerun after that final recreate.
- The initial scripted public `/health` check hit the known immediate readiness
  404 after container recreation; `infra/hostinger/validate-prod.sh` passed on
  rerun after the stack settled.
- Final production API container started at 2026-06-23T18:43:12Z with
  `PLATFORM_ADMIN_EMAILS=venkatesh@ishirock.com`,
  `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true`, and
  `PLATFORM_ADMIN_BOOTSTRAP_EMAIL=venkatesh@ishirock.com`.
- Production `/api/auth/login` returned `role=platform_admin`, the reserved
  platform tenant id, and `must_change_password=false` for the configured
  operator.
- Browser validation against `https://transmuter.ishirock.tech/auth/login`
  passed: the Angular app authenticated, navigated to `/platform`, and rendered
  `Platform Control`.

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
  - `CHROME_BIN=/usr/bin/chromium-browser TRANSMUTER_UI_BASE_URL=https://transmuter-dev.ishirock.tech TRANSMUTER_API_BASE_URL=https://transmuter-dev.ishirock.tech/api TRANSMUTER_E2E_EMAIL=admin@acme3-transformation.dev TRANSMUTER_E2E_PASSWORD=<local-secret> CHROME_DEBUG_PORT=9334 node apps/web/e2e/phase2a-ui-acceptance.mjs`
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
