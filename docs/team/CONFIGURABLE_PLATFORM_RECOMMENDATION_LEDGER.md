# Configurable Platform Recommendation Ledger

Status: Active scope ledger for #227
Source inputs: `productupgrade.md`, `productupgrade_addendum.md`,
`Initiative_Portfolio_Anonymised.xlsx`

## Purpose

This ledger prevents the product-upgrade recommendations from becoming scattered
across duplicate GitHub issues. The clean configurable platform work is tracked
under #227, with focused implementation issues for backend, frontend, workbook
reload, onboarding, dashboards, security, testing, and deploy readiness.

## Source Of Truth

- #227: parent epic for the clean configurable financial/platform refactor
- #228: architecture/schema/API contract review
- #229: destructive schema replacement and backend contracts
- #230: backend financial API replacement
- #231: dynamic frontend financial/admin UI
- #232: anonymised portfolio workbook reload
- #233: Prahari security review
- #234: real API and browser acceptance
- #235: deploy readiness
- #236: blank tenant admin self-configuration onboarding
- #237: configurable gates, multi-BU initiatives, and value-ramp dashboards

## Recommendation Coverage

| Recommendation | Owner |
| --- | --- |
| Tenant-defined metric definitions with type, unit, direction, aggregation, benefit class, and rollup semantics | #229, #230, #231 |
| Monthly-only financial value store with quarter/fiscal-year rollups computed from definitions | #229, #230, #234 |
| Tenant-definable scenarios including baseline, plan base, plan high, actual, and future custom lanes | #229, #230, #231 |
| Formula metrics using Decimal-safe evaluation with cycle validation and divide-by-zero handling | #230, #233, #234 |
| Configurable value bridge rows | #229, #230, #231 |
| Reporting currency and fiscal year start month | #229, #230, #231 |
| Named initiative-level benefit lines with confidence, timing, attributes, and summary visibility | #229, #230, #231, #232 |
| Cost and benefit phasing/spreading rules | #230, #231, #232 |
| Audit columns and actual-value signoff/status | #229, #230, #233 |
| Five-stage configurable gate lifecycle and maturity funnel | #237 |
| Many-to-many initiative to business unit mapping | #237 |
| Charter fields: initiative context/problem, workstream lead, workstream sponsor | #237 |
| Run-rate year, selected scenario/case, and baseline-year reporting parameters | #230, #237 |
| Dynamic initiative financial grid with no hardcoded metric array | #231 |
| Dynamic admin metric/scenario/reporting configuration | #231, #236 |
| Workbook reload from anonymised portfolio, including initiatives, benefits, costs, KPIs, milestones, risks, actions, status updates, and validation totals | #232 |
| Portfolio financials and value bridge driven by definitions instead of fixed revenue/GM/cost fields | #230, #231, #237 |
| Run-rate value ramp dashboard | #237 |
| In-year value dashboard with stage/gate and as-of-date support | #237 |
| Blank tenant signup without business/demo data; admin configures platform before initiatives | #236 |
| Demo/sample data available only through explicit dev/test fixtures | #236, #234 |
| RLS, formula, workbook import, tenant reset/reload, and role-sensitive reporting review | #233 |
| Real seeded API and browser acceptance with deterministic reset/isolation | #234 |

## Completion Status As Of 2026-06-12

| Area | Status | Notes |
| --- | --- | --- |
| Clean metric definitions, scenarios, reporting currency, fiscal year, benefit lines, bridge rows, metric values, and RLS schema | Done for current refactor baseline | Migration exists in both Supabase migration roots and copies are byte-identical. |
| Destructive data reset and anonymised workbook reload | Done for local reload path | Loader imports 21 initiatives from parse-only and now requires `--confirm-reset` for destructive reloads. |
| Backend clean financial grid read/write | Done for monthly metric values | API reads/writes definition/scenario/month values with Decimal string responses. |
| Clean value bridge, scenario summary, break-even, portfolio financial rollups | Done for launch-functional path | Remaining polish is making every display row fully configurable from bridge rows instead of compatibility shapes. |
| Status-update draft generation | Done for AI-enabled and fallback paths | Uses OpenRouter/PydanticAI when configured; deterministic fallback only for disabled/missing/failing AI. |
| Dynamic admin metric/scenario/reporting configuration | Partial | Admin can manage definitions, scenarios, fiscal year, and currency. Bridge-row and attribute-registry editing still need UI completion. |
| Dynamic initiative financial grid | Partial | Grid is generated from clean definitions/scenarios and saves clean values. Rich benefit-line editing, formula read-only rendering, and phasing controls remain. |
| Formula metrics | Partial | Definitions store formulas and no unsafe `eval` is used. Decimal-safe formula evaluation, cycle validation, and divide-by-zero handling remain. |
| Cost and benefit phasing/spreading | Partial | Workbook reload preserves phasing metadata. Interactive phasing engine/popover and regeneration rules remain. |
| Configurable stage gates and approval criteria | Done for current launch path | Browser acceptance derives configured stages, blocks advancement before approval, submits criteria, approves, and verifies configured transition. |
| Multi-BU initiatives and filtering | Done for imported data path | Workbook reload creates initiative-BU links and repository filtering checks the many-to-many links. |
| Blank tenant self-configuration guard | Done for current launch path | Normal tenant bootstrap no longer seeds business/demo data; initiative create/import is blocked until admin setup is complete. |
| Run-rate value ramp dashboard | Open | Tracked under #237. Endpoint and UI still need implementation. |
| In-year value dashboard with as-of/stage filtering | Open | Tracked under #237. Existing portfolio financials cover part of the need, but plan-as-of-date and Gate 3+ filtering remain. |
| Workstream lead/sponsor and generic line attributes | Partial | Schema fields/JSONB attributes exist; complete admin/edit UI and reporting filters remain. |
| Security review | Done for current local batch | #233 is in review. Formula execution needs a second Prahari pass when implemented. |
| Real browser acceptance | Done for current local batch | #234 is in review after a passing real browser run against local Angular + real FastAPI. |

## Explicitly Deferred

- Multi-currency and FX conversion beyond tenant reporting currency.
- Advanced value translation modes beyond formula metrics and baseline inputs.
- Unattributed workstream actuals until product confirms whether actuals may be
  captured outside initiative attribution.

## Issue Hygiene

Older recommendation issues #203 through #208 are superseded by this ledger and
the #227 issue set. They should be closed with comments pointing here rather
than used as parallel active tracks.
