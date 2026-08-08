# User Guide Consolidation Review

Last reviewed: 2026-08-08  
Parent issue: #462

## Outcome

The in-product catalogue was reduced from 16 overlapping guides to three
canonical, role-oriented guides:

1. `transmuter-administration-guide.md`
2. `transmuter-user-operations-guide.md`
3. `transmuter-dashboard-reporting-guide.md`

All use ACME Industrial Services and ACC-101 Invoice Automation as the same
worked example. Historical sources remain in Git for traceability but are no
longer published as parallel operating instructions.

## Source-by-source disposition

| Previous source | Review finding | Consolidated destination |
|---|---|---|
| `team/TENANT_ONBOARDING_USER_GUIDE.md` | Broad but duplicated setup, finance, operations, dashboards and demos; prior navigation no longer canonical | Administration + User Operations + Dashboard & Reporting |
| `acme-transformation-office-detailed-setup-and-demo-guide.md` | Valuable complete scenario, but too long and mixed administrator/user audiences | ACME examples distributed across all three |
| `acme-demo-tenant-ui-setup-guide.md` | Strong setup sequence; duplicated tenant onboarding | Administration sections 2–5 |
| `acme-transformation-office-management-runbook.md` | Useful cadence; separate from feature instructions | User Operations weekly routine |
| `acme-transformation-value-demonstration-guide.md` | Useful executive story and formula examples; overlapped reporting guide | Dashboard & Reporting formulas/reconciliation |
| `acme-dashboard-and-reporting-user-guide.md` | Based on the previous many-dashboard navigation | Replaced by Dashboard & Reporting's three-dashboard model |
| `admin-financial-configuration-user-guide.md` | Detailed finance setup; duplicated onboarding and engine walkthrough | Administration Financial Configuration Engine |
| `financial-engine-end-to-end-walkthrough.md` | Valuable mechanics, but separate terminology/example path | Administration configuration + User Operations ledger/cost workflow |
| `automation-productivity-financial-scenario-walkthrough.md` | Narrow scenario duplicated financial walkthrough | ACC-101 example across the three guides |
| `ishirock-demo-tenant-ui-setup-guide.md` | Alternate tenant caused users to translate terms and values | Historical reference; ACME is canonical |
| `ishirock-transformation-office-detailed-setup-and-demo-guide.md` | Parallel end-to-end manual | Historical reference; ACME is canonical |
| `ishirock-transformation-value-demonstration-guide.md` | Parallel reporting story | Historical reference; ACME is canonical |
| `ishirock-ui-readiness-from-workbook-guide.md` | Readiness/validation material rather than normal use | Internal reference; user-facing setup is in Administration |
| `acme-benefit-ledger-production-remediation-guide.md` | Sensitive remediation runbook, not routine user help | Retained as internal operational reference; normal ledger flow is in User Operations |
| `platform-admin-user-guide-validation-runbook.md` | Release validation procedure, not product use | Retained as internal test reference |
| `acme-transformation-platform-improvement-opportunities.md` | Product backlog/review, not user instruction | Superseded for dashboard scope by `DASHBOARD_OPERATIONS_REORGANIZATION.md` |

## Implementation coverage review

| Implemented surface | Canonical coverage |
|---|---|
| Signup, invitation, password change, profile | Administration and User Operations |
| Organization, dimensions, workstreams, tags, stages, criteria | Administration |
| People, roles, permissions | Administration |
| Financial engine, metrics, scenarios, categories, bridge, baselines, scope | Administration + User Operations |
| Dashboard registry and role defaults | Administration |
| Operational Dashboard and all eight widgets | Dashboard & Reporting |
| Financial Dashboard and all eight widgets | Dashboard & Reporting |
| Initiative Portfolio | Dashboard & Reporting + User Operations |
| Layout drag, keyboard movement, sizing, hide/show, save, publish, reset | Administration + Dashboard & Reporting |
| Initiative create/edit/detail, pipeline and matrix | User Operations |
| Milestones, roadmap, dependencies, actions, status | User Operations |
| Risks and KPIs | User Operations + Dashboard & Reporting |
| Gate approval | User Operations |
| Meetings, agenda, attendees, live session, decisions, actions, transcript | User Operations |
| Benefit Ledger and validation | User Operations |
| Costs and Shared Costs | Administration + User Operations + Dashboard reconciliation |
| Bankable plans, rebaseline, waterline and target locks | All three by role/use |
| Executive brief, Board Pack and drill-through | Dashboard & Reporting |
| AI assistant and AI Insights boundary | Administration + User Operations |
| Microsoft 365/Teams integration boundary | Administration + User Operations |
| Platform guide library | Administration guide plus this internal review |

## Corrections made during review

- Dashboard labels and guide terminology now say Operational Dashboard and
  Financial Dashboard.
- Ledger, validation, locks, shared costs, approvals, and all other write
  workflows are documented under Operations, not as dashboards.
- The former Control Tower and Investments & Payback menu entries are treated as
  consolidated content/drill-through rather than peer dashboards.
- Initiative Portfolio is explicitly unchanged.
- Dashboard editing is described as presentation configuration only; it never
  grants data access or edits business records.
- The guide catalogue is available to authenticated tenant users as well as
  platform administrators.
- Examples state source records, periods, scenarios, recurring treatment,
  formula boundaries, expected results, and reconciliation steps.

## Remaining verification boundary

Release acceptance must render all three guides in the real Angular app, follow
the ACC-101 procedures against deterministic seeded data and the running API,
and verify links, headings, expected calculations, permissions, light/dark
themes, layout persistence, mobile stacking, exports, and reset behavior.
