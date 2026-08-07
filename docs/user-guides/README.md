# Transmuter User Guide Index

Last reviewed: 2026-08-05

Use this page to choose the right guide. The canonical complete Acme demo is
[`acme-transformation-office-detailed-setup-and-demo-guide.md`](acme-transformation-office-detailed-setup-and-demo-guide.md).
It includes preflight, tenant setup, initiatives, finance, governance, People,
the full Saturday meeting workflow, speaker notes, expected results, and
deterministic cleanup.

## Start here

| Guide | Use it for |
|---|---|
| [Tenant onboarding and portfolio user guide](../team/TENANT_ONBOARDING_USER_GUIDE.md) | Current end-to-end product guide for tenant setup, roles, initiatives, financials, delivery, governance, dashboards, meetings, and Microsoft 365. |
| [Dashboards and reporting — ACME example](acme-dashboard-and-reporting-user-guide.md) | End-user explanation of every dashboard/report card, chart, filter, drilldown, formula boundary, and ACME validation value. |

## Acme guides

| Guide | Use it for |
|---|---|
| [Detailed setup and demo](acme-transformation-office-detailed-setup-and-demo-guide.md) | Complete step-by-step platform demo; start here. |
| [UI tenant setup](acme-demo-tenant-ui-setup-guide.md) | Building a blank tenant through the UI. |
| [Management runbook](acme-transformation-office-management-runbook.md) | Weekly, monthly, and quarterly operating cadence. |
| [Value demonstration](acme-transformation-value-demonstration-guide.md) | Executive value story, formulas, and board questions. |
| [Benefit-ledger remediation](acme-benefit-ledger-production-remediation-guide.md) | Controlled production-data remediation only after explicit approval. |
| [Improvement opportunities](acme-transformation-platform-improvement-opportunities.md) | Product backlog/context, not a demo script. |

## Validation

| Guide | Use it for |
|---|---|
| [Platform Admin User-Guide Validation Runbook](platform-admin-user-guide-validation-runbook.md) | Reproduce the real API and external Playwright release run with local credential aliases and deterministic dev cleanup. |

## Financial configuration guides

| Guide | Use it for |
|---|---|
| [Admin financial configuration](admin-financial-configuration-user-guide.md) | Tenant currency, fiscal calendar, metrics, scenarios, bridge rows, baselines, and categories. |
| [Financial engine walkthrough](financial-engine-end-to-end-walkthrough.md) | Detailed metric, benefit, cost, formula, and rollup example. |
| [Automation scenario walkthrough](automation-productivity-financial-scenario-walkthrough.md) | Automation/productivity-specific financial scenario. |

## Ishirock guides

The Ishirock guides are a separate worked tenant and must not be mixed into the
Acme demo dataset:

- [Ishirock UI setup](ishirock-demo-tenant-ui-setup-guide.md)
- [Ishirock Transformation Office demo](ishirock-transformation-office-detailed-setup-and-demo-guide.md)
- [Ishirock value demonstration](ishirock-transformation-value-demonstration-guide.md)
- [Ishirock workbook readiness](ishirock-ui-readiness-from-workbook-guide.md)

## Validated boundary

The five-tenant real API and external Playwright acceptance procedure is
documented in the validation runbook; consult its current local evidence rather
than relying on a historical commit in this reusable index. Native Transmuter
meetings work without Teams.
The centralized tenant Microsoft 365 organizer, Teams event scheduling, and
transcript synchronization are deployed; each tenant must complete organizer
consent and Microsoft tenant policy must permit Graph transcript access. Sync
results now remain inside the Import Transcript dialog, and successful sync
fills the transcript text area for review. No guide contains a password. Keep
dev test credentials only in the gitignored repository-root `credentials.json`
file with permission mode `0600`.
