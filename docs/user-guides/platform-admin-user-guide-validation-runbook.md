# Platform Admin User-Guide Validation Runbook

Last reviewed: 2026-08-05

Use this runbook to reproduce the release validation behind the published
Transmuter guides. It drives Chromium through external Playwright against the
real Angular application and API; it does not use the in-app browser and does
not treat mocks or manually prepared browser state as acceptance evidence.

## 1. Safety and scope

- Run the mutable suites only against the dev environment.
- Do not run seed, cleanup, password rotation, or write-path checks against
  production without a separately approved production change.
- The ACME and Meetings suites create temporary records and remove them through
  visible product workflows. If a run is interrupted, use **Admin -> Data
  Cleanup** to remove only records whose names contain the suite's unique
  acceptance suffix.
- Microsoft consent and a completed Teams transcription are external
  prerequisites. The deterministic suite validates the disconnected error path
  in the Import Transcript dialog. A live-sync success is a separate HITL check.
- Never paste passwords into a guide, ticket, terminal output, screenshot, or
  committed file.

## 2. Local credential file

Credentials are stored only in the repository-root `credentials.json`, which is
gitignored and must have file mode `0600`. The file contains these aliases:

| Alias | Purpose |
|---|---|
| `platform_admin` | Platform Control and the platform-admin-only User Guides library. |
| `five_tenant_fixture.tenant_admins.acme` | Deterministic Acme Global Manufacturing tenant administrator. |
| `five_tenant_fixture.shared_password` | Local-only password for the generated five-tenant fixture. |
| `runbook_e2e.users.*` | Unique passwords for currently active synthetic role personas. |
| `runbook_e2e.missing_identities` | Historical aliases intentionally absent; do not recreate them implicitly. |

Before use:

```bash
cd /Users/vramakrishnaiah/dev/transmuter
test "$(stat -f '%Lp' credentials.json)" = "600"
git check-ignore credentials.json
```

Both commands must succeed. If the file is missing or a login fails, rotate the
specific synthetic account through the approved admin recovery procedure while
preserving its UUID and metadata. Revoke existing refresh sessions and update
the local file atomically before testing. Do not create a replacement identity
for a missing alias.

## 3. Deterministic data preflight

The current release fixture is **Acme Global Manufacturing** with initiative
codes `ENT-001` through `ENT-010`. Confirm `/health` and `/api/health` are
healthy, then confirm the tenant contains exactly ten canonical initiatives.
The guarded seed is idempotent but is still a dev mutation; use it only when the
fixture is absent or verification reports drift:

```bash
cd /Users/vramakrishnaiah/dev/transmuter/apps/api
uv run python scripts/seed_five_tenant_transformation_program.py --help
```

Read the exact environment/confirmation flags shown by `--help`. Supply the
fixture password through `TRANSMUTER_MULTI_TENANT_PASSWORD` from the local
credential file without printing it. Save the generated manifest below
`scratch/` and verify all five tenant IDs before continuing.

## 4. Install the browser runner

```bash
cd /Users/vramakrishnaiah/dev/transmuter/apps/web
npm ci
npx playwright install chromium
```

The repository pins `@playwright/test`. Node 22.x is the supported project
runtime; a newer local Node may work but its engine warning is not release
evidence.

## 5. Real API acceptance

From `apps/api`, run the guarded verifier with the fixture password supplied as
an environment variable:

```bash
uv run python scripts/verify_five_tenant_dev_api_acceptance.py \
  --environment dev \
  --confirm verify-five-tenant-dev-api \
  --base-url https://transmuter-dev.ishirock.tech/api \
  --report ../../scratch/issue-447/five-tenant-api-acceptance.json
```

This covers real seeded users and role boundaries across five tenants, tenant
isolation, initiatives, portfolio views, financials, configuration, governance,
delivery, and reversible mutation probes. Meetings are intentionally excluded
and covered by the browser suite below.

## 6. External Playwright suites

Run each suite separately so a failure has a clear owner and cleanup boundary:

```bash
cd /Users/vramakrishnaiah/dev/transmuter/apps/web
export TRANSMUTER_DEPLOYED_COMMIT=<deployed-dev-commit-sha>
npx playwright test e2e/platform-guides-current.spec.mjs --config=playwright.config.mjs
npx playwright test e2e/acme-guide-full.spec.mjs --config=playwright.config.mjs
npx playwright test e2e/fresh-tenant-full-guide.spec.mjs --config=playwright.config.mjs
npx playwright test e2e/meetings-v4-playwright.spec.mjs --config=playwright.config.mjs
```

The suites validate:

| Suite | Required outcome |
|---|---|
| Platform guides | Platform-admin-only access, every published source renders, search/filter/deep links, dark/mobile layouts, tenant-role denial, global search, centralized Microsoft organizer UI, and Portfolio Assistant graceful behavior. |
| ACME full guide | Tenant setup, dimensions, financial configuration, roles, People, dashboards, initiative views, benefit/cost/plan flows, Shared Costs, delivery/governance, HITL authoring, meetings, and deterministic cleanup. |
| Fresh tenant full guide | Public signup, Stripe sandbox checkout/provisioning, first login, strategic/financial/governance configuration, ten-person model, ten HITL initiatives, representative locked value case, Shared Costs, full route/export inventory, and exact-slug platform cleanup. |
| Meetings V4 | Series/session lifecycle, agenda propagation and initiative context, notes, decisions, actions, manual transcript, AI minutes, completion/cancellation/cleanup, plus Microsoft disconnected-state errors inside the transcript dialog. |

Every suite must finish with no unexpected page error and no observed HTTP 5xx.
Do not convert a real failure into an allowlist merely to make the run green.

## 7. Evidence and review

Expected local evidence:

- `scratch/issue-447/five-tenant-api-acceptance.json`
- `scratch/issue-447/platform-guides-current.json`
- `scratch/issue-447/acme-guide-full.json`
- `scratch/issue-447/fresh-tenant-full-guide.json`
- `scratch/meetings-v4-browser-acceptance-results.json`
- `scratch/issue-447/playwright-report/`
- traces and screenshots below `scratch/issue-447/test-results/` for failures

Record the deployed commit, environment URL, UTC execution time, scenario
counts, cleanup result, and any external Microsoft limitation in the release
issue. Evidence may contain synthetic identifiers, so keep `scratch/` local.

## 8. Live Microsoft transcript HITL check

Use a tenant whose organizer shows **Connected** in **Admin -> Microsoft 365**.
Create and sync a Teams invite, conduct the meeting with transcription enabled,
wait for Microsoft to publish the transcript, then open the live session:

1. Select **Import Transcript**.
2. Select **Sync from Microsoft** once.
3. On success, confirm the dialog stays open and the transcript text area is
   populated for review.
4. On connection, policy, permission, or availability failure, confirm the
   message is visible inside the dialog.
5. Select **Cancel** and confirm the modal message does not reappear as a stale
   meeting-page error.

If Microsoft returns `GraphAccessToTranscriptsDisabled`, an authorized Microsoft
tenant administrator must change the relevant Graph/transcription policy; this
cannot be bypassed by Transmuter.

## 9. Exit criteria

Validation is complete only when the API suite and all four browser suites
pass against the deployed dev commit, temporary data is removed, guide metadata
shows the current review date, security-sensitive changes have Prahari review,
and Aksha has moved the issue to review. Production promotion remains a
separate explicit decision.
