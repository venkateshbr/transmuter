# ACME Transformation Office Detailed Setup and Demo Guide

Last reviewed: 2026-08-05

This guide is a complete end-to-end walkthrough for setting up and demonstrating
the **Acme Global Manufacturing** transformation tenant in Transmuter.

It expands the shorter ACME value guide with:

- the exact screens to use,
- what values to configure,
- which filters to apply,
- where benefits and costs appear,
- how to explain each screen to management,
- speaker notes for a live demo,
- the validated ACME values currently configured in the dev environment.

No credentials are included in this guide.

Historical launch-readiness evidence (`2026-07-15`): the deterministic five-tenant acceptance
and the dedicated ACME client-demo acceptance are complete in development. The
July ACME run used one external, headed Playwright Chromium session against
dev commit `1c5f184` (Hostinger action `104346054`). It passed all 20 named
browser scenarios, observed no page errors or HTTP 5xx responses, and removed
the temporary initiative and Saturday meeting through the visible Admin UI.
The broader July five-tenant run on `1f3330b` is retained as historical
cross-tenant and RBAC evidence. Use the current platform-admin validation
runbook and its local evidence for release decisions. Production was not
touched. Microsoft Graph live consent, Teams
invite/join-link refresh, and transcript acceptance remain separate external
gates under `#220`, `#389`, and `#390`; do not demonstrate those controls until
that external acceptance is complete for the ACME tenant. The platform now uses
one tenant-level organizer configured in **Admin -> Microsoft 365**. Microsoft
transcript sync keeps success or error feedback inside the Import Transcript
dialog and fills the transcript text area on success.

For a UI-only blank-tenant setup path that skips meetings, see
[`acme-demo-tenant-ui-setup-guide.md`](acme-demo-tenant-ui-setup-guide.md).

---

## 1. Validated ACME Demo State

Validated on `https://transmuter-dev.ishirock.tech` against the deterministic
**Acme Global Manufacturing** tenant. The current canonical fixture uses
`ENT-001` through `ENT-010`. A newly created browser-demo initiative receives
the next available `TRN-*` code; never assume that temporary code in advance.

| Area | Status | Validation result |
|---|---|---|
| Tenant login | Configured | ACME transformation office user can sign in. |
| Setup checklist | Configured | `7/7 complete`. ACME has 5 active stage gates and every gate requires all configured criteria. |
| Business units | Configured | Commercial, Corporate, Operations, Shared Services, Technology. |
| Workstreams | Configured | Automation, Commercial Growth, ERP & Data Platform, Offshoring & Operating Model, Procurement & Supply Chain. |
| Financial engine | Configured | Baseline, Plan Base, Plan High, Actual scenarios; revenue, gross margin, savings, formula metrics, and bridge rows. |
| Tenant FY26 baseline | Configured | Annual revenue baseline = `$20.0M`; annual gross margin baseline = `$9.0M`. |
| Initiatives | Configured | 10 ACME initiatives. |
| Initiative baseline allocation | Reconciles | Initiative baselines total `$20.0M` revenue and `$9.0M` gross margin. |
| FY28 Financial Overview | Reconciles | Benefits `$9.182M`, recurring costs `$0.800M`, net run-rate value `$8.382M`; actual benefit `$4.080M`, recurring actual `$0.388M`, net actual `$3.692M`. |
| Investments & Payback | Reconciles | One-off investment remains separately governed from recurring FY28 run-rate value. |
| Benefit Tracking / Bankable Plan | Board-demo-ready | All 10 initiatives have locked plans; `ENT-005` visibly shows version 2. Locked baseline is `$13.802M` and realized value is `$7.9732M`. |
| Contributor drawer | Reconciles | Open `2028-M01` to show initiative contributors such as `ENT-006`. The broader annual `2028` row does not expose the same initiative drawer. |
| Benefits Register | Configured | Portfolio-wide benefit lines show gross, validated, risk-adjusted, bankable, and realized values with evidence and owner metadata. |
| Shared Costs | Configured in dev | Current deterministic ACME dev data includes four FY2028 shared-cost pools covering `benefit_weighted`, `equal_split`, `fixed_percentage`, and `manual_amount` methods. Total shared-cost plan is `$1.45M`, actual is `$1.305M`, and Control Tower allocated plan is `$1.45M`. |
| Board pack export | Configured | Financial Overview can export a non-empty XLSX board pack using the same selected year and value basis. |
| Core meeting command center | Development browser pass | The headed ACME run created a weekly Saturday series, linked `ENT-005`, added and generated an initiative agenda, autosaved notes, attached a decision and risk to the active agenda, generated/edited/saved/reloaded AI minutes, completed the session, and deleted the temporary series in Admin. Passed on `1c5f184`; no temporary meeting remains. |
| People access lifecycle | Development browser pass | A real Resend setup email opened the dev app, password setup succeeded, a temporary password forced first-login change, the fixture password was restored, and a separate invite was listed, resent, and revoked. |
| Five-tenant reporting context | Development browser pass | ACME USD/January, Northstar SGD/July, Meridian GBP/April, Solstice EUR/January, and Horizon AUD/July loaded correctly across the route sweep. |

---

Production note: the Shared Costs schema, API, and UI are live on
`https://transmuter.ishirock.tech`, but production ACME demo data is not yet at
dev ACME parity. Production ACME currently has 0 shared-cost pools and 0
initiative dependencies. Treat any difference from the current cards as fixture
or environment drift and record it in the active validation issue before a demo.

### Before you start the live demo

1. Use the dev URL unless production promotion and production demo data have
   been separately approved: `https://transmuter-dev.ishirock.tech`.
2. Confirm `/health` and `/api/health` both return a healthy response.
3. Put approved dev-only login details in the gitignored local file
   repository-root `credentials.json` and set its permissions to `0600`. Never put
   the password in this guide, Git, a screenshot, a meeting note, or a shell
   command that prints it.
4. Sign in as the Acme `transformation_office` persona. Wait for the **Strategic
   Yield Dashboard** heading before using a direct link; this confirms the role
   profile has hydrated.
5. Open **Profile** and confirm **Acme Transformation Admin**, the ACME fixture
   email domain, and **Transformation Office**. The current Profile view does
   not display the legal entity name, so verify **Acme Global Manufacturing**
   under **Admin > General** before presenting tenant configuration.
6. Use a 1440-pixel-wide browser window for the main presentation. Test the
   responsive layout at about 390 pixels before the audience joins, then return
   to desktop width.
7. Create a fresh temporary meeting series for the meeting segment. The
   canonical fixture intentionally contains no meetings. Use the exact cleanup
   steps in Screen 14 before ending the rehearsal or client demo.
8. Keep the browser network/console closed during the audience demo. For formal
   acceptance evidence, capture errors separately and never expose tokens,
   headers, local storage, or invite URLs.
9. Do not select **Sync Invite** or promise a Teams transcript unless a tenant
   administrator has connected the organizer in **Admin -> Microsoft 365** and
   Graph consent has been completed for the environment. Native agendas, notes,
   decisions, AI draft minutes, and completion work without Teams.
10. Rehearse the 15-screen route in section 7 once without changing data. A
    route that redirects, shows a retry panel, or displays the wrong currency is
    a stop condition, not a valid empty state.

### Browser-validated presenter route

Use this order when the audience wants the complete platform story. For every
step, show the visible result before explaining it; do not narrate a capability
that has not loaded on screen.

| Step | What to do in the browser | Visible proof to pause on | Transformation-office explanation |
|---:|---|---|---|
| 1 | Open `/health`, `/api/health`, then sign in. | Healthy responses followed by **Strategic Yield Dashboard**. | The demo is using the deployed application and real ACME identity, not static slides. |
| 2 | Open **Profile**. | ACME admin display name, fixture email domain, and **Transformation Office** role. | Role context determines the portfolio and controls the presenter can access. |
| 3 | Open **Admin > General**. | **Acme Global Manufacturing** and `7/7 complete`. | Master data is complete before the office asks initiative owners to report value. |
| 4 | Open **Strategic Parameters**. | Five workstreams, five business units, Group/Regional markets, one theme, and four tags. | These dimensions are the common management language used in filters and rollups. |
| 5 | Open **Financial Configuration**. | USD, January fiscal start, FY26 `$20M` revenue/`$9M` gross-margin baseline, four scenarios, ten metrics, and eight cost categories. | Finance has defined one comparable value model for all initiatives. |
| 6 | Open **Governance Engine**, then **Access Control**. | Five gates with required criteria and the role catalogue. | Stage gates control commitment; RBAC separates authors, reviewers, and viewers. |
| 7 | Open **People**. | Ten user cards, **Add User**, and **Pending Access**. | The operating model is staffed across transformation, PMO, Finance, owners, benefit owners, sponsors, and viewers. |
| 8 | Open **Dashboard**. | Ten initiatives plus workstream targets, stage waterline, value matrix, actions, KPI pulse, and activity. | This is the executive landing view: value, delivery pressure, and attention areas in one place. |
| 9 | Open **Initiative Pipeline**; filter Automation, clear, filter Commercial Growth, clear. | Filter counts change and the unfiltered list returns to ten initiatives. | The office can move from portfolio to accountable slice without changing the source set. |
| 10 | Open **Financial Overview**, select FY28, Benefits and Actuals on. | `$9.182M` benefits, `$0.800M` recurring cost, `$8.382M` net; then Software/Licenses drilldown and `2028-M01` contributor drawer. | Every executive number can be traced by cost category, period, and contributing initiative. |
| 11 | Open `ENT-006 Aftermarket Revenue Growth` > **Financials**. | Original annual baseline controls are disabled with the governance-lock explanation. | An approved operating denominator cannot be silently rewritten to improve a value case. |
| 12 | Open **Bankable Plan**, **Benefits Register**, and **Benefit Tracking**. | `ENT-005` version 2 and locked state; Finance validation; `$13.802M` locked baseline and `$7.9732M` realized value. | Approved plans are versioned, benefit claims are validated, and realization is tracked against a stable commitment. |
| 13 | Open **Waterline**, preview a workstream lock, then **Initiative Portfolio** with baseline 2026/value 2028. | Previewed inclusion and an initiative table beginning with `ENT-001`. | Selection and target discipline can be reviewed before any new lock is committed. |
| 14 | Open **Shared Costs** and select each of the four pools. | Rules, targets, weights, and allocation method for platform, PMO, change/training, and advisory pools. | Central costs remain transparent and separately allocated from direct initiative economics. |
| 15 | Visit Progress, Roadmap, Status Updates, Action Items, Governance, Risks, KPIs, and Control Tower. | Each operating view loads; Control Tower shows **Allocated Costs** and **Net After Allocation** for 2028. | Finance variance is connected to milestones, status, RAID, governance, and fully loaded value. |
| 16 | Create the temporary margin-recovery initiative with **Create with Transmuter**. | **HITL Review** suggestions, then the new initiative with accepted KPI, milestone, and risk. | AI assists drafting, but a human explicitly reviews what will be written. |
| 17 | Configure its financial scope and save the FY26 annual baseline. Reload and reopen Financials. | Selected metrics/category persist; `$3.0M` revenue and `$1.35M` gross-margin baseline persist. | Scope defines the auditable model and the baseline defines the original operating denominator. |
| 18 | Add `Regional price realization uplift` and `Pricing analytics subscription`; reload. | Named benefit and twelve monthly cost rows remain visible; **Edit Details** opens the monthly grid. | Benefits and costs are named, phased, and reviewable rather than hidden in a single total. |
| 19 | Run the Saturday meeting sequence in Screen 14. | Initiative agenda, autosaved notes, agenda-linked decision/risk, generated and edited minutes, reload persistence, and `COMPLETED`. | The portfolio becomes a management cadence with evidence and decisions attached to the topic under review. |
| 20 | Use **Admin > Data Cleanup** to delete the temporary meeting and initiative; return to Pipeline and Meetings. | `10 initiatives`; temporary initiative and series absent. | Demo mutations are controlled and the canonical client environment is restored. |

The accepted automation performs exactly this sequence in one headed browser
session. Network response waits are used only to synchronize the UI; every
pass/fail assertion is based on rendered browser state or browser reload
persistence.

## 2. Executive Storyline

Use this storyline for management:

> ACME starts from an FY26 baseline business of `$20.0M` annual revenue and
> `$9.0M` annual gross margin. The transformation office has configured 10
> initiatives across automation, offshoring, commercial growth, ERP/data, and
> procurement. The current FY28 Financial Overview displays `$9.182M` of
> benefits and `$0.800M` recurring cost, resulting in `$8.382M` net run-rate
> value. With Actuals on, it shows `$4.080M` actual benefit, `$0.388M` recurring
> actual cost, and `$3.692M` net actual value. One-off implementation investment
> is governed separately from the recurring run-rate story.

Board-level value message:

```text
FY28 net run-rate value
= visible benefits - recurring run costs
= $9.182M - $0.800M
= $8.382M
```

Use the exact label shown on screen when presenting the number. If a client
asks how revenue uplift, margin uplift, or savings contribute, open the period
contributor drawer rather than summing static guide values.

Shared-cost narrative:

> ACME also tracks central platform, PMO, advisory, and change costs separately
> from direct initiative cost lines. These costs should burden executive value
> views only after Finance approves an allocation run. Direct initiative
> economics and bankable plan values remain direct-only unless Finance enables a
> burdened reporting policy.

---

## 3. ACME Initiative Portfolio

Use the following portfolio when setting up a new tenant or explaining the ACME
demo.

| Code | Initiative | BU | Workstream | Tag |
|---|---|---|---|---|
| ENT-001 | Transformation PMO and Value Office | Corporate | Automation | other |
| ENT-002 | Smart Factory Automation | Operations | Automation | automation |
| ENT-003 | Commercial Pricing Excellence | Commercial | Commercial Growth | commercial |
| ENT-004 | Shared Services Consolidation | Shared Services | Offshoring & Operating Model | offshoring |
| ENT-005 | Enterprise Data and ERP Modernization | Technology | ERP & Data Platform | automation |
| ENT-006 | Aftermarket Revenue Growth | Commercial | Commercial Growth | commercial |
| ENT-007 | Strategic Account Expansion | Commercial | Commercial Growth | commercial |
| ENT-008 | Strategic Procurement | Operations | Procurement & Supply Chain | other |
| ENT-009 | Supply Chain Control Tower | Operations | Procurement & Supply Chain | automation |
| ENT-010 | AI-enabled Predictive Maintenance | Operations | Automation | automation |

Do not use a static initiative spreadsheet as the financial reporting
authority during the demo. Open Financial Overview and the contributor drawer:
the accepted live FY28 cards are `$9.182M` benefits, `$0.800M` recurring cost,
and `$8.382M` net run-rate value. Use `ENT-006` Financials for the individual
value-case example and `ENT-005` Bankable Plan for version history.

---

## 4. Transformation Office Operating Model

The transformation office is the control layer that turns a collection of
initiatives into a managed program of value. In Transmuter, that operating
model is implemented through role-based ownership, stage gates, financial
validation, bankable plans, actual realization entries, dashboards, and meeting
cadence.

### Core roles

| Role | Primary accountability | Main screens | Data owned |
|---|---|---|---|
| Executive Sponsor / CEO / CFO | Approves portfolio ambition, funding, and major tradeoffs. Reviews value, risk, and decisions. | `/dashboard`, `/financials`, `/reports/control-tower`, board pack export | Decision outcomes, escalations, target changes approved outside the system. |
| Transformation Office Director | Owns the portfolio operating cadence and confirms that the program is governed end to end. | `/dashboard`, `/initiatives/pipeline`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower` | Portfolio priorities, stage movement, meeting cadence, executive narrative. |
| PMO Lead / Governance Manager | Maintains stage gates, milestones, risks, dependencies, actions, and meeting follow-up. | `/admin`, `/pmo/governance`, `/progress`, `/meetings`, initiative **Governance**, **Milestones**, **Risks**, **Dependencies** tabs | Gate criteria, submissions, milestones, RAID data, actions, meeting minutes. |
| Finance Lead / Benefits Controller | Owns financial definitions, baseline integrity, benefit validation, cost validation, shared-cost governance, actuals governance, and board value reconciliation. | `/admin`, `/financials`, `/shared-costs`, `/financials/benefits-register`, `/financials/bankable-plan`, `/financials/benefit-tracking`, initiative **Financials** tab | Metric definitions, scenarios, baselines, benefit validation status, cost categories, shared-cost pools, allocation policies, actual values, benefit ledger approval evidence. |
| Workstream Lead | Runs a slice of the portfolio and escalates blockers across initiatives. | `/initiatives/pipeline`, `/initiatives/matrix`, `/financials/benefit-tracking`, `/progress/roadmap`, `/reports/control-tower` | Workstream prioritization, progress narrative, cross-initiative blockers, workstream realization commentary. |
| Initiative Owner | Owns delivery, status, milestones, risks, KPIs, assumptions, and source evidence for benefits. | `/initiatives/:id`, initiative **Overview**, **Financials**, **Milestones**, **KPIs**, **Risks**, **Status**, **Team** tabs | Initiative description, owners, dates, delivery status, risks, KPIs, benefit-line assumptions, realization evidence. |
| Business Benefit Owner | Confirms that value has moved into business-as-usual operations and can be sustained. | `/financials/benefit-tracking`, `/financials/benefits-register`, initiative **Financials** and **Summary** tabs | Realization evidence, benefit ownership, sustainment notes, realized-value acceptance. |
| Tenant Administrator | Configures tenant setup, users, dimensions, fiscal settings, governance rules, and access. | `/admin`, `/people` | Tenant settings, users, roles, master data, first-run checklist. |
| Management Viewer | Reviews dashboards and reports without changing data. | `/dashboard`, `/financials`, `/financials/benefit-tracking`, `/reports/control-tower`, `/initiatives/pipeline` | No owned data; read-only consumption and challenge questions. |

### Screen ownership

| Screen | Accountable role | Supporting roles | How it is used |
|---|---|---|---|
| `/admin` General, Strategic Parameters, Financial Configuration, Governance Engine | Tenant Administrator / Finance Lead / PMO Lead | Transformation Office Director | Sets tenant identity, business units, workstreams, metrics, scenarios, cost categories, bridge rows, baselines, and gate rules. |
| `/people` | Tenant Administrator | Transformation Office Director | Creates users, assigns tenant roles, and confirms who can manage all initiatives versus assigned initiatives only. |
| `/dashboard` | Transformation Office Director | Executive Sponsor, Workstream Leads | Gives the first executive read on portfolio scale, health, and attention areas. |
| `/initiatives/pipeline` | Transformation Office Director | Workstream Leads, Initiative Owners | Source list for all initiatives; used to filter by BU, workstream, tag, priority, owner, stage, and RAG. |
| `/initiatives/matrix` | Transformation Office Director / Workstream Leads | Finance Lead | Shows portfolio value and initiative distribution by workstream and tag so management can see where value is concentrated. |
| `/initiatives/new` and `/initiatives/:id/edit` | Transformation Office Director | Initiative Owner, Workstream Lead | Creates and maintains initiative master data, ownership, stage, dates, dimensions, and initial value case. |
| `/initiatives/:id/financial-scope` | Finance Lead | Initiative Owner | Controls which metrics and cost categories are tracked for the initiative. |
| Initiative **Financials** tab | Finance Lead | Initiative Owner, Business Benefit Owner | Maintains benefit lines, cost lines, plan/high/actual scenario values, validation status, and assumptions. |
| Initiative **Milestones**, **KPIs**, **Risks**, **Dependencies**, **Status**, **Team** tabs | Initiative Owner / PMO Lead | Workstream Lead | Maintains execution evidence that explains whether the value case is credible. |
| `/financials` | Finance Lead | Transformation Office Director | Reconciles portfolio baseline, planned benefits, actuals, recurring costs, one-off investment, net run-rate value, and contributor detail. |
| `/financials/investments-payback` | Finance Lead / Transformation Office Director | Executive Sponsor | Shows cumulative one-off investment, annual net run-rate value, and payback period by portfolio and initiative. |
| `/financials/benefits-register` | Finance Lead / Benefits Controller | Initiative Owners, Business Benefit Owners | Shows each benefit line with plan, actual, validated amount, risk adjustment, evidence, owner, and validation status. |
| `/financials/bankable-plan` | Finance Lead / PMO Lead | Transformation Office Director | Shows locked approved plans and rebaseline history while actual scenario values and actual costs continue to be updated separately. |
| `/financials/benefit-tracking` | Benefits Controller | Finance Lead, Business Benefit Owners | Records and imports realized benefit ledger rows, compares actuals to locked bankable plan, and exposes variances. |
| `/financials/waterline` | Transformation Office Director / Finance Lead | Workstream Leads | Freezes workstream targets after approval so future delivery is compared against a stable target. |
| `/shared-costs` | Finance Lead | Transformation Office Director | Captures shared or cross-portfolio costs, defines allocation policies, and explains burdened value without hiding central costs inside one initiative. |
| `/progress`, `/progress/roadmap`, `/progress/action-items`, `/progress/status-updates` | PMO Lead | Initiative Owners, Workstream Leads | Runs the weekly operating cadence across milestones, actions, status reporting, and roadmap risks. |
| `/meetings` and `/meetings/sessions/:id` | PMO Lead | Transformation Office Director, Workstream Leads | Runs steering committees and workstream reviews, captures agenda, attendees, minutes, decisions, and actions. |
| `/pmo/governance`, `/pmo/risks`, `/pmo/kpis`, `/pmo/ai-insights` | PMO Lead | Finance Lead, Workstream Leads | Provides governance, risk, KPI, and AI-assisted portfolio views for program control. |
| `/reports/control-tower` | Transformation Office Director | Executive Sponsor, Finance Lead, PMO Lead | Management meeting view combining value, progress, risk, blockers, and decision support. |

### Data ownership rules

| Data | Entered by | Reviewed by | System control |
|---|---|---|---|
| Tenant dimensions, workstreams, BUs, markets, themes, tags | Tenant Administrator | Transformation Office Director | Used as filters and rollup dimensions across dashboards and reports. |
| Financial metric definitions, scenarios, cost categories, value bridge rows | Finance Lead | Transformation Office Director | Defines what can be tracked and how values reconcile. |
| Initiative master data and ownership | Transformation Office / Initiative Owner | Workstream Lead | Must be assigned to dimensions before it can be governed as part of the portfolio. |
| Initiative baseline allocation | Finance Lead | Initiative Owner | Must reconcile to tenant FY26 baseline for ACME. |
| Plan Base and Plan High benefit values | Initiative Owner / Finance Lead | Finance Lead | Maintained in the initiative financial grid by metric, scenario, benefit line, year, and month. |
| Actual financial metric values | Finance Lead / Initiative Owner, depending on control model | Finance Lead | Entered in the **Actuals** scenario and compared against plan. |
| Actual recurring and one-off costs | Finance Lead | Transformation Office Director | Entered as actual cost lines or actual cost values; recurring actuals affect net run-rate actuals. |
| Benefit-line validation status | Finance Lead | Benefits Controller | Draft -> Submitted -> Finance validated or Rejected. |
| Shared cost pools and allocation policies | Finance Lead | Transformation Office Director | Central costs are held outside direct initiative cost lines, allocated through approved runs, and consumed by burdened executive reporting. |
| Bankable plan lock / rebaseline | Finance Lead / PMO Lead | Transformation Office Director | Freezes approved plan snapshots so realization is compared against a stable baseline. |
| Benefit ledger actual realization | Benefits Controller / Business Benefit Owner | Finance Lead | Entered manually or imported by CSV in `/financials/benefit-tracking`; variance is calculated against locked plan. |
| Milestones, risks, KPIs, actions, status updates | Initiative Owner / PMO Lead | Workstream Lead | Explains delivery confidence and blockers behind the financial variance. |

### Operating lifecycle

1. **Setup**: Tenant admin and Finance configure dimensions, users, metric
   definitions, scenarios, cost categories, fiscal calendar, annual baselines,
   and stage gates.
2. **Intake**: Transformation office creates initiatives with owners,
   workstreams, business units, tags, dates, and value hypotheses.
3. **Plan**: Finance and initiative owners configure financial scope, annual
   baselines, benefit lines, cost lines, Plan Base, Plan High, and assumptions.
4. **Validate**: Finance reviews benefit lines in the initiative financial tab
   and `/financials/benefits-register`; PMO confirms gate criteria.
5. **Commit**: Approved initiatives are locked into bankable plans. Rebaseline
   is versioned rather than overwriting the prior approved plan.
6. **Run**: Initiative owners update status, milestones, risks, KPIs, actions,
   and actual financial values. The bankable-plan lock keeps the approved plan
   stable, but the initiative **Financials** tab **Actuals** scenario and actual
   cost amounts remain editable. PMO runs meetings and escalates blockers.
7. **Realize**: Benefits controller or business benefit owner enters realized
   benefit ledger rows in `/financials/benefit-tracking`, with actual amounts
   and evidence descriptions.
8. **Allocate shared costs**: Finance maintains central cost pools in
   `/shared-costs`, previews or runs allocation policies, and keeps direct
   initiative costs separate from allocated burden.
9. **Report**: Finance uses `/financials`, `/financials/benefits-register`,
   `/financials/benefit-tracking`, and board exports to reconcile value.
   Management uses `/dashboard` and `/reports/control-tower` to run decisions.
10. **Sustain**: Business benefit owner accepts the realized value into BAU,
   unresolved variance remains visible, and lessons learned are recorded in the
   initiative summary.

### Actuals and realization control

There are two related but different actuals concepts:

| Actual type | Where entered | Purpose |
|---|---|---|
| Actual financial scenario values | Initiative **Financials** tab, scenario **Actuals** | Captures actual revenue uplift, gross margin uplift, savings, and actual cost values in the same grid structure as plan. These values drive financial plan-vs-actual reporting. |
| Benefit ledger realization rows | `/financials/benefit-tracking` | Captures realized benefit evidence against the locked bankable plan. These rows are the realization record used for locked baseline versus realized benefit tracking. |

Post-lock rule:

- The bankable-plan lock freezes annual baseline values, Plan Base, Plan High,
  benefit-line structure, planned cost amounts, and the locked bankable snapshot.
- The lock does not freeze the **Actuals** scenario or actual cost amounts in the
  initiative **Financials** tab.
- Benefit Tracking remains editable and importable after a bankable plan exists,
  but it stays a separate realization ledger rather than the portfolio financial
  actuals source.
- Use governed rebaseline for approved-plan changes. Use a later period-close
  control if Finance needs to lock actuals for a reporting period.

Recommended control:

1. Initiative owner provides the operating evidence and source files.
2. Business benefit owner confirms the value is embedded in operations.
3. Finance lead confirms the calculation and enters or approves actual values.
4. Benefits controller enters or imports benefit ledger rows.
5. Transformation office reviews variance and escalates leakage through the
   steering cadence.

For ACME, use `/financials/benefit-tracking` to show realized actuals against
locked bankable plan values, and use `/financials` to show portfolio financial
plan, actual, cost, and net value reporting.

---

## 5. New Tenant Setup Sequence

Follow this sequence for a new tenant before creating initiatives.

### Step 1: Sign in and open Admin

Screen:

- `/auth/login`
- `/admin`
- Admin tab: **General**

Actions:

1. Sign in as the tenant administrator or transformation office user.
2. Open **Admin** from the main navigation.
3. On **General**, set the organization legal name and logo URL.
4. Check **First-run setup**. The tenant should eventually show all setup checks complete.

Speaker notes:

> We start by setting the tenant identity and checking the first-run setup
> checklist. This is the control point that prevents initiative creation before
> the tenant has the core dimensions, financial model, governance rules, and
> users needed for reliable value tracking.

Expected ACME demo note:

- ACME currently shows 8/8 setup checks complete.
- Gate criteria are configured and active for the five-stage governance model.

### Step 2: Configure strategic dimensions

Screen:

- `/admin`
- Admin tab: **Strategic Parameters**

Configure:

Business units:

- Corporate
- Commercial
- Operations
- Technology
- Shared Services

Workstreams:

- Automation
- Offshoring & Operating Model
- Commercial Growth
- ERP & Data Platform
- Procurement & Supply Chain

Markets:

- Group
- Regional

Themes:

- Manufacturing productivity and profitable growth

Tags:

- automation
- offshoring
- commercial
- other

Actions:

1. In **Workstream Management**, create the five ACME workstreams.
2. In **Business Units**, create the five ACME business units.
3. In **Markets**, create Group and Regional.
4. In **Themes**, create Manufacturing productivity and profitable growth.
5. In **Tags**, create automation, offshoring, commercial, and other.

Speaker notes:

> These dimensions are not cosmetic. They are how management slices the
> transformation: by business ownership, workstream, theme, market, and value
> lever. We will later use these same tags and workstreams to filter initiative
> pipeline, financial overview, matrix views, meetings, and progress reporting.

### Step 3: Configure financial reporting settings

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Financial Configuration Engine**

Configure:

| Setting | ACME value |
|---|---|
| Reporting currency | USD |
| Fiscal year start | January |

Actions:

1. Set **Currency** to `USD`.
2. Set **Fiscal Start** to `January`.
3. Click **Save Settings**.
4. Reload **Financial Overview** and confirm money uses USD. For a shifted
   fiscal tenant, also confirm the displayed fiscal year is the year in which
   the fiscal period ends: July 2027 through June 2028 is FY2028, and April 2027
   through March 2028 is FY2028.
5. Change monthly, quarterly, and yearly grains once and confirm they all retain
   the same tenant currency and fiscal-year selection.

Speaker notes:

> The fiscal calendar and reporting currency make every screen consistent:
> initiative financials, portfolio trend, value ramp, bridge rows, and exports
> all use the same reporting basis. The platform uses fiscal ending-year
> semantics, which is especially important for April and July tenants.

### Step 4: Configure financial metric definitions

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Metric Definitions**

Configure the ACME metric definitions:

| Metric key | Label | Type | Aggregation | Benefit class | Purpose |
|---|---|---|---|---|---|
| `annual_revenue_baseline` | Annual Revenue Baseline | Currency | Last | None | Original annual revenue reference. |
| `annual_gross_margin_baseline` | Annual Gross Margin Baseline | Currency | Last | None | Original annual gross margin reference. |
| `revenue_uplift` | Revenue Uplift | Currency | Sum | Revenue | Commercial growth driver. |
| `gm_uplift` | Gross Margin Uplift | Currency | Sum | Margin | EBITDA-effective margin benefit. |
| `cost_savings` | Cost Savings | Currency | Sum | Savings | EBITDA-effective recurring savings or avoided spend. |
| `target_revenue` | Target Revenue | Currency | Formula | None | Baseline revenue plus revenue uplift. |
| `target_gross_margin` | Target Gross Margin | Currency | Formula | None | Baseline GM plus GM uplift. |
| `revenue_growth_pct` | Revenue Growth % | Percent | Formula | None | Revenue uplift divided by revenue baseline. |
| `gross_margin_run_rate_pct` | Gross Margin Run-rate % | Percent | Formula | None | Target GM divided by target revenue. |
| `gm_improvement_pct` | Gross Margin Improvement % | Percent | Formula | None | GM uplift divided by GM baseline. |

Recommended formulas:

```text
target_revenue = baseline_annual_revenue_baseline + revenue_uplift
target_gross_margin = baseline_annual_gross_margin_baseline + gm_uplift
revenue_growth_pct = revenue_uplift / baseline_annual_revenue_baseline * 100
gross_margin_run_rate_pct = target_gross_margin / target_revenue * 100
gm_improvement_pct = gm_uplift / baseline_annual_gross_margin_baseline * 100
```

Actions:

1. Add or review each metric definition.
2. Use **Benefit = No** for baseline and formula metrics.
3. Use **Benefit = Revenue** for Revenue Uplift.
4. Use **Benefit = Margin** for Gross Margin Uplift.
5. Use **Benefit = Savings** for Cost Savings.
6. Click **Save** on each metric row.

Speaker notes:

> We separate baseline, driver, benefit, and formula metrics. Baselines are not
> benefits. Revenue uplift is a commercial driver. Gross margin uplift and cost
> savings are EBITDA-effective benefits. Formula rows let management see rates
> and targets without manual calculation.

### Step 5: Configure tenant annual baseline

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Annual Baselines**

Configure:

| Metric | Fiscal year | Value |
|---|---:|---:|
| Annual Revenue Baseline | 2026 | `20000000` |
| Annual Gross Margin Baseline | 2026 | `9000000` |

Actions:

1. Set **Fiscal Year** to `2026`.
2. Enter `20000000` for Annual Revenue Baseline.
3. Enter `9000000` for Annual Gross Margin Baseline.
4. Click **Save**.

Where this appears:

- `/financials`
- Top baseline cards:
  - FY26 Portfolio Baseline Annual Revenue
  - FY26 Portfolio Baseline Annual Gross Margin
  - Baseline Margin Rate
- Financial trend baseline line.

Speaker notes:

> The FY26 baseline is the denominator and starting point. It is not counted as
> transformation value. It tells the board what business we are improving from:
> `$20.0M` revenue and `$9.0M` gross margin, or a 45% gross margin rate.

### Step 6: Configure scenarios

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Scenarios**

Configure:

| Scenario key | Label | Kind | Use |
|---|---|---|---|
| `baseline` | Baseline | Baseline | Original operating reference. |
| `plan_base` | Plan Base | Plan | Main management plan. |
| `plan_high` | Plan High | Plan | Upside case. |
| `actual` | Actual | Actual | Realized or latest actual value. |

Actions:

1. Ensure all four scenarios are active.
2. Ensure **Plan Base** is the primary plan scenario.

Speaker notes:

> The scenario lanes support board-quality value discipline: baseline, base plan,
> upside, and actuals. We do not overwrite the plan when actuals change; we keep
> the plan and compare realized performance against it.

### Step 7: Configure value bridge rows

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Value Bridge Rows**

Configure:

| Bridge row | Kind | Sign | Inputs |
|---|---|---:|---|
| Revenue Uplift | Metrics | Positive | Revenue Uplift |
| Gross Margin Uplift | Metrics | Positive | Gross Margin Uplift |
| Cost Savings | Metrics | Positive | Cost Savings |
| Recurring Costs | Costs | Negative | Software, Maintenance, Labor |
| One-off Costs | Costs | Negative | Implementation, Technology Tooling, External Consultants, Training Change |
| Net Value | Net | Positive | Calculated net row |

Actions:

1. Add bridge rows in this order.
2. Select the relevant metric or cost inputs for each row.
3. Mark recurring and one-off costs with negative sign.
4. Save each row.

Speaker notes:

> This is the management bridge. It shows how the transformation moves from
> gross value to net value. Recurring costs reduce run-rate EBITDA. One-off
> implementation costs are investment and payback burden, not recurring EBITDA
> drag.

### Step 8: Configure cost categories

Screen:

- `/admin`
- Admin tab: **Financial Configuration**
- Section: **Cost Categories**

Configure:

One-off categories:

- Implementation / Project Cost
- Technology / Tooling
- External Consultants
- Training / Change Management

Recurring categories:

- Software / Licenses
- Support / Maintenance
- People Support

Actions:

1. Create one-off categories with rollup type **One-time**.
2. Create recurring categories with rollup type **Recurring**.
3. Save the cost category configuration.

Speaker notes:

> This split is critical for EBITDA storytelling. One-off investment helps us
> explain payback. Recurring run cost is what must be deducted from run-rate
> EBITDA value.

### Step 9: Configure governance stage gates

Screen:

- `/admin`
- Admin tab: **Governance Engine**

Recommended stage gates:

| Gate | Label | From stage | To stage | Approval |
|---:|---|---|---|---|
| 1 | Gate 1: Identify to Validate | identified | validated | Required |
| 2 | Gate 2: Validate to Plan | validated | planned | Required |
| 3 | Gate 3: Plan to Commit | planned | committed | Required |
| 4 | Gate 4: Commit to Execute | committed | executing | Required |
| 5 | Gate 5: Execute to Realized | executing | realized | Required |

Recommended gate criteria:

Gate 1:

- Problem statement and opportunity owner defined.
- High-level value hypothesis documented.
- Workstream and impacted business unit assigned.

Gate 2:

- FY26 baseline approved by Finance.
- Benefit calculation method documented.
- One-off and recurring cost assumptions captured.

Gate 3:

- Delivery plan and milestones agreed.
- Business owner accepts target.
- Risks and dependencies documented.

Gate 4:

- Funding and resources confirmed.
- KPI and benefit tracking cadence agreed.
- Change/adoption plan agreed.

Gate 5:

- Actual benefit evidence submitted.
- Finance validates realized value.
- Business-as-usual owner accepts sustainment.

Actions:

1. Add the five gates.
2. Add gate criteria for each gate.
3. Use `transformation_office` as the approver role.
4. Set **Require all active criteria** when gate quality needs strict control.

Speaker notes:

> Stage gates stop the portfolio from becoming a list of unverified ideas. The
> board should know which value is identified, which is validated, which is
> committed, and which is realized.

ACME validation note:

- Stage gates are configured in ACME.
- Gate criteria are configured in the current ACME seed: Gate 1 has 2
  criteria, Gate 2 has 3, Gate 3 has 2, Gate 4 has 2, and Gate 5 has 1.
- Use the setup checklist to show that no active gate is missing criteria.

### Step 10: Configure users and roles

Screens:

- `/people`
- `/admin`, tab: **Access Control**

Recommended roles:

| Role | Use |
|---|---|
| `transformation_office` | Transformation Office Director / value office with full tenant and portfolio permissions. |
| `tenant_admin` | Tenant setup, users, access, dimensions, dashboard configuration, and billing portal access. |
| `pmo_lead` | Governance, stage gates, meetings, actions, milestones, risks, KPIs, and cadence. |
| `finance_lead` | Financial configuration, baselines, benefit validation, shared costs, actuals, and benefit tracking. |
| `workstream_lead` | Assigned workstream visibility and execution updates. |
| `initiative_owner` | Owned initiative master data, execution evidence, status, and financial assumptions. |
| `business_benefit_owner` | Realization evidence, sustainment notes, and benefit ledger updates. |
| `executive_sponsor` | Read-only executive portfolio, financial, and control-tower views. |
| `viewer` | Read-only management portfolio and dashboard access. |

Demo user matrix:

| Demo user | Email pattern | Role | Scope to configure |
|---|---|---|---|
| Priya Raman | `acme-to-<run>@acme-transformation.dev` | `transformation_office` | Full tenant and portfolio control. Use this persona for the end-to-end setup and management narrative. |
| Jordan Lee | `acme-admin-<run>@acme-transformation.dev` | `tenant_admin` | Tenant setup, people, access control, dimensions, dashboard configuration, and billing portal. |
| Maya Patel | `acme-pmo-<run>@acme-transformation.dev` | `pmo_lead` | Governance, gates, meetings, actions, milestones, risks, KPIs, and cadence. |
| Omar Haddad | `acme-finance-<run>@acme-transformation.dev` | `finance_lead` | Financial configuration, shared costs, benefit validation, actuals, bankable plan, and benefit tracking. |
| Lena Ortiz | `acme-workstream-<run>@acme-transformation.dev` | `workstream_lead` | Assign to Automation, Commercial Growth, Procurement & Supply Chain, and Offshoring when the demo needs one workstream lead to see all ACME workstreams. |
| Ethan Brooks | `acme-owner-<run>@acme-transformation.dev` | `initiative_owner` | Assign as owner for at least ENT-006, ENT-008, and ENT-010 so the persona can maintain master data, execution evidence, and financial assumptions on owned initiatives. |
| Sofia Chen | `acme-benefit-<run>@acme-transformation.dev` | `business_benefit_owner` | Use on Benefits Register and Benefit Tracking for realization evidence, sustainment notes, and ledger updates. |
| Daniel Wright | `acme-exec-<run>@acme-transformation.dev` | `executive_sponsor` | Read-only executive portfolio, financial, and Control Tower review. |
| Nora Singh | `acme-viewer-<run>@acme-transformation.dev` | `viewer` | Read-only management portfolio and dashboard review. |

Actions:

1. Open **People** as the initial administrator, transformation office user, or
   tenant administrator.
2. Click **Add User** to open the **Add Platform User** modal.
3. Choose one access mode deliberately:

   - **Temp Password** creates the user immediately. Enter a unique password of
     at least 12 characters containing upper- and lower-case letters and a
     number. Give it to the synthetic test user through the approved test
     channel. On first login, confirm the app redirects to **Change password**;
     the user must enter the temporary password and a different permanent one.
   - **Invite Link** creates a pending, app-owned invitation. Enter the email,
     display name, title, role, and any workstream assignment, then select
     **Send Invite** once. The email link must open
     `/auth/accept-invite?token=...` on the current Transmuter hostname—never
     `localhost`. The recipient enters and confirms a password, selects
     **Activate account**, and lands on the dashboard.

4. For deterministic role rehearsals, prefer **Temp Password** and store only
   the shared fixture credential in the ignored local
   repository-root `credentials.json` file. Do not put it in a committed `.env`, a
   guide, or macOS Keychain for this test workflow.
5. For an invite rehearsal, open **Pending Access** and locate the exact
   synthetic address. Select **Resend** once and confirm the status remains
   `PENDING`; the old token must no longer work. Select **Revoke** and confirm
   `REVOKED`; the latest token must no longer activate the account.
6. Create each required persona in the matrix and assign each operating-model
   role according to the accountability table in
   section 4.
7. Assign workstream scope to the Workstream Lead in the People modal.
8. Assign initiative ownership on the relevant initiative master-data screens
   for the Initiative Owner.
9. Use **Admin > Access Control** to review user status and role assignment.
10. Log in once as each persona and confirm the role-specific navigation and
   permissions described in section 4.
11. After testing, revoke disposable pending invites. Do not leave an extra Auth
    identity or person row in the canonical demo tenant; use the approved reset
    process rather than direct production database deletion.

Speaker notes:

> Value delivery is role-based. The transformation office has full control,
> tenant administrators manage access and setup, PMO and Finance run their
> governance and value controls, initiative and workstream owners update scoped
> delivery evidence, benefit owners confirm realization, and executive viewers
> inspect management dashboards without changing data.

---

## 6. Initiative Setup Sequence

Repeat this sequence for each initiative.

### Step 1: Create an initiative

Screen:

- `/initiatives/pipeline`
- Button: **New Initiative**
- Screen: `/initiatives/new`

Actions:

1. Select **Create with Transmuter**.
2. Step 1: enter initiative name, workstream, business units, market, theme,
   initiative type, impact type, priority, and tag.
3. Step 2: enter summary, context/problem, value logic, and dependencies.
4. Step 3: enter market owner, group owner, planned start, and planned end.
5. Select **Generate initiative suggestions** when using AI-assisted intake.
   Review every proposed KPI, milestone, and risk in **HITL Review**; edit or
   reject suggestions before they are written.
6. Select **Create initiative** and wait for the new initiative detail page.
   Confirm its generated `TRN-*` code and its accepted KPI, milestone, and risk.
7. Configure financial scope and the annual baseline from the initiative after
   creation, as described in Steps 2 and 3 below.

Browser-tested client example (create temporarily, then delete in Admin):

| Field | Value |
|---|---|
| Initiative name | Client Demo Margin Recovery `<date-or-initials>` |
| Workstream | Commercial Growth |
| Business unit | Commercial |
| Market | Regional |
| Theme | Manufacturing productivity and profitable growth |
| Type | Revenue Growth |
| Impact type | Recurring |
| Priority | High |
| Tag | commercial |
| Planned start | 2026-08-01 |
| Planned end | 2028-06-30 |

Use this narrative in Step 2:

- **Summary:** Recover aftermarket margin by standardizing price corridors and
  managing exceptions through a weekly commercial cadence.
- **Problem:** Regional discount leakage obscures profitable growth and weakens
  accountability for realized margin.
- **Value logic:** A governed one-point margin recovery creates recurring gross
  margin uplift after adoption and data-quality controls are in place.
- **Dependency:** Reliable price-waterfall data and regional sales-owner
  adoption.

Speaker notes:

> The initiative record creates the accountable unit of value. We capture what
> business area owns it, what workstream governs it, what value lever it belongs
> to, and what assumptions explain the business case.

### Step 2: Configure financial scope

Screens:

- `/initiatives/:id`
- Tab: **Financials**
- Button: **Configure Scope**
- Screen: `/initiatives/:id/financial-scope`

Actions:

1. Select the metric rows needed for the initiative:
   - Revenue Uplift
   - Gross Margin Uplift
   - Cost Savings
   - formula rows as needed
2. Select cost categories:
   - one-off categories when implementation investment exists
   - recurring categories when ongoing run cost exists
3. Click **Save Scope**.

For the temporary margin-recovery example, select exactly:

- Annual Revenue Baseline;
- Annual Gross Margin Baseline;
- Gross Margin Uplift;
- Software / Licenses.

After **Save Scope** returns to initiative detail, reopen **Configure Scope**
and confirm all four selections remain checked. This reload-style revisit is
the visible proof that scope was persisted.

Speaker notes:

> Scope controls which financial rows appear for the initiative. This keeps the
> financial grid focused: commercial initiatives need revenue and margin rows;
> procurement initiatives need savings; technology initiatives often need both
> benefit rows and cost categories.

### Step 3: Configure initiative annual baseline

Screen:

- `/initiatives/:id`, **Financials** tab, **Annual Baseline** panel

Actions:

1. Set fiscal year to `2026`.
2. Enter initiative-specific Annual Revenue Baseline.
3. Enter initiative-specific Annual Gross Margin Baseline.
4. Select **Save Annual Baseline**.

How to validate:

1. Reload `/initiatives/:id` in the browser.
2. Open the **Financials** tab again.
3. Confirm fiscal year `2026` and both four-decimal values persist.
4. For the tested temporary example, use revenue `3000000` and gross margin
   `1350000`. Explain that these are the original operating denominator for
   this demonstration, not a benefit.
5. For a locked seeded initiative such as `ENT-006`, confirm the same controls
   are disabled and the page explains that governance has locked the baseline.

Speaker notes:

> The portfolio baseline is allocated to initiatives so each value case has a
> denominator. That allows us to explain growth percentages and margin
> improvement by initiative, not only at portfolio level.

### Step 4: Add benefit lines

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Section above the grid: **Benefit Metric / Named Benefit Line**

Actions:

1. Select a benefit metric:
   - Revenue Uplift
   - Gross Margin Uplift
   - Cost Savings
2. Enter a named benefit line.
3. Enter confidence percentage if known.
4. Choose phasing:
   - **Manual** for month-by-month entry in the grid.
   - **One-off** for a single-period benefit.
   - **Spread** for an amount spread across months.
5. Enter amount, start month, and end month.
6. Click **Add Line**.

For the temporary margin-recovery example, use:

| Field | Browser-tested value |
|---|---|
| Benefit metric | Gross Margin Uplift |
| Named benefit line | Regional price realization uplift |
| Confidence | `80` |
| Phasing | Spread |
| Base | `120000` |
| High | `150000` |
| Actual | `0` |
| Start | `2027-01` |
| End | `2027-12` |

After **Benefit line added** appears, reload initiative detail, reopen
**Financials**, and point to the named line. Explain that `$120K` is the
committed working case, `$150K` is controlled upside, and actual remains zero
until Finance has realization evidence.

Examples:

| Initiative | Benefit metric | Benefit line | FY28 amount |
|---|---|---|---:|
| ENT-006 Aftermarket Revenue Growth | Revenue Uplift | Price realization uplift | `$1.10M` |
| ENT-006 Aftermarket Revenue Growth | Gross Margin Uplift | Discount leakage reduction | `$1.05M` |
| ENT-008 Strategic Procurement | Cost Savings | Vendor-rate savings | `$0.80M` |

Speaker notes:

> Benefit lines make the value case auditable. Instead of a single unexplained
> number, each initiative has named benefit sources, confidence, timing, and
> monthly values.

### Step 5: Add one-off and recurring cost lines

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Section above the grid: **Cost Category / Cost Line**

Actions:

1. Select cost category.
2. Enter cost line name.
3. Select lane:
   - **Plan** for planned cost.
   - **Actual** for actual cost.
4. Select mode:
   - **One-off** for implementation investment.
   - **Spread** for monthly or annual run cost.
5. Enter amount, start month, and end month.
6. Click **Add Cost**.

For the same temporary example, use:

| Field | Browser-tested value |
|---|---|
| Cost category | Software / Licenses |
| Cost line | Pricing analytics subscription |
| Lane | Plan |
| Mode | Spread |
| Amount | `12000` |
| Start | `2027-01` |
| End | `2027-12` |

Wait for **12 cost lines added**, reload, and confirm both the named benefit and
named cost are visible. Select **Edit Details** and show the monthly grid, but
do not alter a cell during a client demo unless you intend to demonstrate a
controlled forecast update.

ACME cost pattern:

One-off costs are in FY27:

- 45% Implementation / Project Cost
- 35% Technology / Tooling
- 20% Training / Change Management

Recurring run costs ramp:

- 50% of FY28 recurring run-rate in FY27
- 100% run-rate in FY28
- split 40% Software, 35% Maintenance, 25% Labor

Speaker notes:

> This is where we distinguish investment from ongoing drag. One-off costs
> affect payback. Recurring costs reduce run-rate EBITDA. Management should not
> mix the two.

### Step 6: Edit detailed monthly values

Screen:

- `/initiatives/:id`
- Tab: **Financials**
- Button: **Edit Details**

Actions:

1. Use scenario toggle:
   - **Baseline** for FY26 baseline rows.
   - **Base** for conservative plan.
   - **High** for upside plan.
   - **Actuals** for realized values.
2. Click **Edit Details**.
3. Enter or review monthly values in the grid.
4. Click **Save Changes**.
5. Use the cell assumption context menu to document key assumptions.

After Gate 2 creates a locked bankable plan, **Base** and **High** become
read-only. Switch to **Actuals** to update actual metric values and actual cost
amounts without changing the approved plan.

Speaker notes:

> The grid is the detailed financial ledger. The annual management numbers are
> the rollup of these period values. We can trace a portfolio value back to
> scenario, metric, benefit line, month, and initiative.

### Step 7: Add milestones, KPIs, risks, status, and team

Screen:

- `/initiatives/:id`
- Tabs: **Milestones**, **KPIs**, **Risks**, **Status**, **Team**

Recommended ACME minimum:

Milestones:

- Gate 2 baseline and business case confirmed.
- FY28 run-rate benefits activated.

Risks:

- Data readiness risk.
- Adoption/change risk.
- Finance validation risk.

KPIs:

- Revenue uplift.
- Gross margin uplift.
- Cost savings.
- Process cycle time, productivity, adoption, or service-level KPI depending on initiative.

Speaker notes:

> Finance value is only one part of transformation control. Milestones, KPIs,
> risks, dependencies, and status updates explain whether the value is likely to
> materialize and what management must unblock.

### Step 8: Remove the temporary initiative after the demo

1. Record the generated `TRN-*` code shown on the initiative Overview; do not
   guess it from a previous rehearsal.
2. Open `/admin` and select **Data Cleanup**.
3. Find the exact temporary initiative name and select its deletion control.
4. Enter the generated code in **Initiative delete confirmation code**.
5. Wait for any transient status overlay to close, then select **Delete selected
   initiative** once.
6. Confirm `Deleted <code>.` appears.
7. Return to `/initiatives/pipeline`; confirm `10 initiatives` and verify the
   temporary name is absent.

Speaker notes:

> We use the same controlled cleanup surface as an administrator. The demo
> proves real create-and-persist behavior, then returns the shared client
> environment to its deterministic portfolio without direct database edits.

### Shared cost scenario pack

Screen:

- `/shared-costs`

Use this after initiatives and financial configuration exist. Shared costs are
not direct initiative cost lines. They are central costs allocated for burdened
executive reporting and, later, optional burdened bankable-plan reporting if
Finance enables that policy.

Current deterministic ACME proof in dev:

| Scenario | Pool | Category | Suggested method | Candidate initiatives | Demo point |
|---|---|---|---|---|---|
| Platform burden | Group technology and data platform | Software / Licenses | Benefit weighted | ENT-002, ENT-005, ENT-006, ENT-009, ENT-010 | Plan `$650K`, actual `$585K`; shows metric-backed allocation from gross-margin uplift. |
| PMO governance burden | Transformation PMO and benefits office | Labor / Operations | Equal split | All 10 ACME initiatives | Plan `$400K`, actual `$360K`; shows central governance cost without hiding it in one direct cost line. |
| Change/adoption burden | Shared change and training support | Training / Change Management | Manual amount | ENT-002, ENT-004, ENT-005, ENT-010 | Plan `$220K`, actual `$198K`; validates manual amounts for process-heavy adoption costs. |
| Advisory/vendor burden | Central advisory and vendor support | External Consultants | Fixed percentage | ENT-005, ENT-008, ENT-009 | Plan `$180K`, actual `$162K`; tests fixed percentage allocation for central vendor support. |

Current seeded totals:

| Measure | Value |
|---|---:|
| Shared-cost plan | `$1.45M` |
| Shared-cost actual | `$1.305M` |
| Control Tower allocated plan | `$1.45M` |
| Control Tower net after allocation | `$1,400,000.0004` |
| Bankable Plan shared-cost inclusion | `false` by default |

Recommended demo actions:

1. Open `/shared-costs`.
2. Select each of the four FY2028 pools to show the method variety.
3. Explain the pool, method, plan amount, actual amount, policy status, and run
   history.
4. Open `/reports/control-tower` with target year `2028`.
5. Show allocated costs, burdened costs, and net after allocation.
6. Explain that `/financials` direct cost views remain direct-only unless
   Finance enables generated cost-line posting.
7. Explain that `/financials/bankable-plan` remains direct-only by default;
   burdened bankable value should require a tenant setting and a locked
   allocation run.

Speaker notes:

> Shared Costs answer a different question from initiative financials. Direct
> initiative costs answer what the owner controls. Shared-cost burden answers
> what the portfolio looks like after central platform, PMO, advisory, or change
> costs are fairly allocated. We keep the two views separate so executives can
> see fully loaded economics without corrupting initiative accountability.

---

## 7. Where to Demonstrate Value

### Screen 1: Executive Dashboard

Screen:

- `/dashboard`

Accountable role:

- Transformation Office Director

Use it for:

- first executive landing view,
- portfolio status,
- high-level transformation posture,
- deciding which value, risk, or delivery area needs deeper review.

Speaker notes:

> This is the executive landing page. It gives management a first read on the
> transformation portfolio before we move into financial proof. It is the
> starting point for the weekly or monthly management cadence: what is healthy,
> what is off track, and what needs an executive decision?

### Screen 2: Initiative Pipeline

Screen:

- `/initiatives/pipeline`

Accountable role:

- Transformation Office Director
- Workstream Leads for their own filtered views

Filters to apply:

| Filter | Demo use |
|---|---|
| Search | Search `Pricing`, `Procurement`, or `Automation`. |
| Business Unit | Filter to Commercial, Operations, or Shared Services. |
| Workstream | Filter to Automation, Commercial Growth, or Procurement & Supply Chain. |
| Priority | Show high-priority initiatives. |
| Tag | Show automation, offshoring, or commercial initiatives. |

Speaker notes:

> This is the transformation control list. Every management number must trace
> back to an initiative with an owner, stage, workstream, RAG status, and value
> case.

Management use:

- Confirms that all value claims are attached to named initiatives.
- Lets the transformation office challenge orphan initiatives with weak
  ownership, stale status, or unclear business-unit accountability.
- Gives workstream leads a filtered backlog for weekly execution review.

### Screen 3: Financial Overview

Screen:

- `/financials`

Accountable role:

- Finance Lead / Benefits Controller

Default demo settings:

| Control | Demo setting |
|---|---|
| Granularity | Yearly |
| Benefits | On |
| Actuals | On |
| Year | 2028 |
| Plan as-of date | Blank unless demonstrating historical cutoff. |
| Stage | All stages for total portfolio; Executing when showing active portfolio. |
| Cost category | All categories for total value; Software, Maintenance, Labor for recurring-cost drilldown. |

Expected FY28 values:

| Metric | Expected plan value |
|---|---:|
| Benefits | `$9.182M` |
| Recurring costs | `$0.80M` |
| One-off costs | `$0.00M` |
| Net run-rate value | `$8.382M` |

Top baseline cards:

| Card | Expected value |
|---|---:|
| FY26 Portfolio Baseline Annual Revenue | `$20.00M` |
| FY26 Portfolio Baseline Annual Gross Margin | `$9.00M` |
| Baseline Margin Rate | `45.0%` |

Demo sequence:

1. Set **Year** to `2028`.
2. Set granularity to **Yearly**.
3. Turn **Benefits On**.
4. Turn **Actuals On**.
5. Point to the FY26 baseline cards.
6. Point to the trend chart baseline line.
7. Point to Benefits, Recurring Costs, and Net Run-rate Value.
8. Change year to `2027` to show ramp year.
9. Change back to `2028` to show run-rate.
10. Open `/financials/investments-payback` to show `$2.50M` one-off
    investment and the `3.6` month payback period.

Speaker notes:

> This is the board proof screen. The top row answers the baseline question:
> what business were we improving? The summary cards answer the value question:
> what recurring EBITDA-effective run-rate value are we delivering? In FY28,
> ACME shows `$9.182M` gross benefits, `$0.800M` recurring run cost, and `$8.382M`
> net run-rate value.

Important current product note:

- Use the summary cards and period table for FY28 portfolio values.
- Select a monthly row such as `2028-M01` to open the contributor drawer. Do
  not use the broader annual `2028` cost row for this proof: it does not expose
  the same initiative-level list. The drawer includes benefit-line detail,
  recurring costs, net run-rate contribution, and Finance validation metadata.
- Use the **Value basis** control when explaining the trend or value bridge:
  select target-year run-rate for the FY28 management story, and switch basis
  only when you want to discuss in-year, cumulative, or all-years values.

Management use:

- CFO view of plan, actual, variance, recurring costs, one-off investment, and
  net value.
- Board view of the baseline-to-value bridge.
- Drilldown view for which initiatives contribute to a selected year, value
  basis, cost category, or stage.
- Export source for the board pack, using the selected year and value basis.

### Screen 4: Financial Overview cost-category drilldown

Screen:

- `/financials`

Accountable role:

- Finance Lead

Filters:

| Control | Demo setting |
|---|---|
| Granularity | Yearly |
| Benefits | On |
| Actuals | On |
| Year | 2028 |
| Cost category | Software / Licenses |

Repeat for:

- Support / Maintenance
- People Support

Speaker notes:

> This is how we isolate recurring run cost. Management can see whether net
> value leakage comes from software, maintenance, or people support.

Management use:

- Separates recurring EBITDA drag from one-off investment.
- Identifies whether technology, maintenance, or labor support costs are
  eroding value.
- Supports budget decisions when run costs need owner action.

### Screen 5: Initiative detail financials

Screen:

- `/initiatives/pipeline`
- Open **ENT-006 Aftermarket Revenue Growth**
- Tab: **Financials**

Accountable role:

- Initiative Owner for assumptions and evidence
- Finance Lead for validation and actuals control

Demo settings:

| Control | Setting |
|---|---|
| Scenario | Base |
| View | Quarterly Summary View first |
| Then | Edit Details for monthly grid |

Expected ENT-006 FY28:

| Value | Amount |
|---|---:|
| Revenue uplift | `$1.10M` |
| Gross margin uplift | `$1.05M` |
| Recurring cost | `$0.05M` |
| EBITDA net | `$1.00M` |
| One-off investment | `$0.25M` |

Speaker notes:

> We can trace the portfolio number to a single initiative. Aftermarket Revenue
> Growth contributes `$1.10M` revenue uplift and `$1.05M` gross margin
> uplift in FY28, with only `$0.05M` recurring run cost. That creates `$1.00M`
> EBITDA-effective net run-rate value.

Management use:

- Audits the story behind a portfolio number.
- Confirms benefit lines, costs, scenario values, actuals, and assumptions.
- Shows whether Finance has validated the benefit before it is treated as
  bankable.

### Screen 6: Initiative financial scope

Screen:

- `/initiatives/:id/financial-scope`

Accountable role:

- Finance Lead

Use it for:

- explaining why certain metric rows appear,
- adding/removing active benefit or cost rows,
- showing locked financial scope behavior.

Speaker notes:

> This is the control surface for what finance tracks on each initiative. We
> avoid forcing every initiative into every metric. Commercial initiatives track
> revenue and margin; procurement initiatives track savings; technology
> initiatives may track margin, savings, and run cost.

### Screen 7: Initiative workbook export

Screen:

- `/initiatives/:id`
- Button: **Export Excel**

Accountable role:

- Finance Lead

Use it for:

- offline finance review,
- initiative owner working sessions,
- audit backup.

Speaker notes:

> The workbook export lets Finance and initiative owners review the same
> financial structure offline. The system remains the source of record; the
> workbook is a review and import channel.

### Screen 8: Bankable Plan

Screen:

- `/financials/bankable-plan`

Accountable role:

- Finance Lead / PMO Lead

Use it for:

- showing whether an initiative has a locked plan snapshot,
- comparing versions after rebaseline,
- navigating to editable financial scope.

What the bankable plan means:

- A bankable plan is the locked, read-only snapshot of an approved initiative
  value case.
- The editable source remains the initiative financial scope and financial grid:
  selected metrics, selected cost categories, benefit lines, cost lines,
  annual baselines, and plan/actual scenario values.
- Once the configured governance approval path locks the plan, realization
  reporting compares actual benefit delivery against that approved snapshot
  instead of against a moving forecast.
- Rebaseline creates a new version. It does not overwrite the prior approved
  version, so Finance can explain what changed, when it changed, and why.

When it applies:

1. During planning, initiatives are still editable and are not yet bankable.
2. After the initiative passes the configured approval gate, the system creates
   the locked bankable snapshot.
3. After lock, the plan is treated as the committed baseline for realization
   tracking and governance reporting.
4. If scope, assumptions, timing, or value materially changes, Finance or PMO
   creates a rebaseline version instead of changing the old lock.

Feature behavior:

| Capability | What it does | ACME demo proof |
|---|---|---|
| Current lock status | Shows whether the selected initiative is still editable or has a locked plan. | Select any seeded ACME initiative to show a locked status. |
| Snapshot summary | Shows locked net value, entry count, cost-line count, metric count, and selected scope count. | Use it to prove the bankable value is generated from the initiative value case. |
| Version history | Lists approval and rebaseline versions with lock time, reason, trigger, and locked-by metadata. | Select `ENT-005 Enterprise Data and ERP Modernization` to show current version 2 created from governed rebaseline approval. |
| Editable scope link | Opens the underlying initiative financial scope without changing the locked snapshot. | Explain that scope edits require a new approval or rebaseline before they become bankable. |
| Rebaseline governance | Preserves prior versions while creating a new current baseline. | Use `ENT-005` to explain controlled baseline movement through Bankable Plan request and Governance approval. |

Primary use cases:

- Board commitment: show the approved value case that management agreed to
  count as bankable.
- Benefits realization: compare actual delivered value against a fixed baseline
  by period, workstream, and initiative.
- Finance control: stop late edits to plan assumptions from silently improving
  variance.
- Steering committee review: explain whether variance is caused by delivery
  leakage, timing delay, or a formally approved rebaseline.
- Audit trail: retain a versioned record of approval and rebaseline decisions.

Dashboards and reports impacted:

| Surface | Impact of bankable plan |
|---|---|
| `/financials/bankable-plan` | Primary review page for locked snapshots, current version, and rebaseline history. |
| `/financials/benefit-tracking` | Uses locked plan values as the baseline for realized benefit ledger rows, portfolio/workstream/initiative variance, and period summaries. |
| `/financials/waterline` | Shows whether initiative value is sourced from a locked bankable plan or a current financial preview when building workstream target views. |
| `/dashboard` | Shows bankable workstream target widgets and stage-gate value versus locked bankable plan context. |
| Board-pack export | Includes benefit ledger rollups that compare actual realization against bankable baseline amounts. |
| Initiative financial views | Shows locked financial mode when a current bankable plan exists; users can still edit forecast and actuals, but the approved baseline stays fixed. |
| `/reports/control-tower` | Uses the same portfolio financial and realization story for executive review, so bankable-plan maturity affects how credible the value narrative is. |

Shared-cost policy:

- Default bankable plan values should remain direct-only.
- Allocated shared costs should not reduce bankable value unless Finance enables
  a burdened bankable reporting setting.
- If burdened bankable value is enabled later, the screen should explain which
  locked shared-cost allocation run reduced the value.

Current ACME demo note:

- ACME has locked bankable plan snapshots seeded for the 10 initiatives.
- ACME has locked current plans and `ENT-005 Enterprise Data and ERP Modernization` carries
  version-2 governed rebaseline history.
- Use this screen as the governance proof that approved value cases are locked
  before realization is tracked.

Speaker notes:

> The bankable plan is the immutable version of an approved value case. Once an
> initiative passes the configured approval gate, the plan becomes the baseline
> for realization tracking. ACME now has locked bankable plans and a governed
> ENT-005 rebaseline example, so we can show both the current approved plan and a
> controlled baseline-change approval.

Management use:

- Proves that realization is being compared against an approved version, not a
  moving target.
- Shows when a value case was locked and whether later rebaseline versions were
  controlled.
- Helps the steering committee distinguish approved commitment from working
  forecast.

### Screen 9: Benefits Register

Screen:

- `/financials/benefits-register`

Accountable role:

- Finance Lead / Benefits Controller

Controls:

| Control | Demo use |
|---|---|
| Year | Select `2028` for ACME run-rate view. |
| Validation status | Show all, then filter to Finance validated. |
| Search | Search a benefit line or initiative code when asked for proof. |

Use it for:

- portfolio-wide list of benefit lines,
- Finance validation status,
- evidence and owner metadata,
- plan, actual, validated, risk-adjusted, bankable, and realized values.

Speaker notes:

> The Benefits Register is the finance control sheet for benefits. It is where
> management can see whether a value line is still a draft, has been submitted,
> has been Finance validated, or was rejected. This prevents unvalidated value
> from being presented as bankable.

Management use:

- Separates gross plan from Finance-validated and risk-adjusted value.
- Shows which benefit owner and evidence support each value claim.
- Provides the handoff point from planned benefit to realization tracking.

### Screen 10: Benefit Tracking

Screen:

- `/financials/benefit-tracking`

Accountable role:

- Benefits Controller / Business Benefit Owner

Controls:

| Control | Demo use |
|---|---|
| Scope | Portfolio, Workstream, Initiative |
| Granularity | Weekly, Monthly, Yearly |
| Workstream | Select a workstream when scope = Workstream |
| Initiative | Select an initiative when scope = Initiative |

Current ACME demo note:

- ACME benefit tracking shows non-zero locked baseline and realized actuals.
- Use yearly granularity first, then drill to monthly or weekly if the
  management audience wants phasing detail.
- For initiative-level proof, select `ENT-006 Aftermarket Revenue Growth`,
  `ENT-008 Strategic Procurement`, or `ENT-010 AI-enabled Predictive
  Maintenance` to show evidence-backed benefit lines.

Speaker notes:

> This is where the operating model moves from planned value to realized value.
> It should compare actual benefit ledger values against locked bankable plans.
> For the ACME demo, this screen is now board-ready: locked plans provide the
> baseline, ledger rows provide actuals, and variance shows where realization is
> ahead of or behind the approved case.

Management use:

- Shows actual realized benefits against the locked plan baseline.
- Lets the benefits controller enter or import actual realization rows.
- Exposes realization gaps by portfolio, workstream, initiative, and period.
- Gives executives one place to ask whether value is real, not just planned.

### Screen 11: Waterline

Screen:

- `/financials/waterline`

Accountable role:

- Transformation Office Director / Finance Lead

Use it for:

- workstream target lock,
- showing which initiatives are included above the cutoff,
- comparing actuals to frozen target.

Recommended demo setup:

1. Select a workstream.
2. Set lock date after Gate 2 approvals.
3. Click **Preview**.
4. Confirm included initiatives.
5. Click **Lock target** only in a prepared demo tenant.

Speaker notes:

> The waterline gives management a frozen target by workstream. It prevents
> shifting goalposts after approval and creates a basis for actual realization
> comparison.

Management use:

- Locks a workstream target once the steering committee has approved scope.
- Shows which initiatives are above or below the cutoff.
- Helps management decide whether adding initiatives changes the committed
  value target or remains below the line.

### Screen 12: Initiative Portfolio Financial View

Screen:

- `/financials/initiative-portfolio`

Accountable role:

- Finance Lead / Transformation Office Director

Use it for:

- comparing initiatives by value, cost, stage, and contribution,
- identifying concentration risk,
- prioritizing leadership attention across the portfolio.

Speaker notes:

> This view is the financial ranking table. It helps management see which
> initiatives carry the most value, which ones have cost leakage, and which
> ones need executive attention because their financial contribution is material.

### Screen 13: Shared Costs

Screen:

- `/shared-costs`

Accountable role:

- Finance Lead

Use it for:

- costs that support multiple initiatives,
- platform, PMO, licensing, or shared delivery costs,
- preventing shared costs from being hidden inside a single initiative,
- explaining fully loaded portfolio economics in Executive Control Tower.

Current deterministic ACME demo proof:

| Pool | Plan | Actual | Allocation method | Reporting impact |
|---|---:|---:|---|---|
| Group technology and data platform | `$650K` | `$585K` | Benefit weighted | Metric-backed burden for technology and automation initiatives in target year `2028`. |
| Transformation PMO and benefits office | `$400K` | `$360K` | Equal split | Governance burden across all 10 ACME initiatives in target year `2028`. |
| Shared change and training support | `$220K` | `$198K` | Manual amount | Adoption and training burden for process-heavy initiatives in target year `2028`. |
| Central advisory and vendor support | `$180K` | `$162K` | Fixed percentage | Vendor support burden for selected ERP/data and supply-chain initiatives in target year `2028`. |

Demo sequence:

1. Open `/shared-costs`.
2. Select **Group technology and data platform**.
3. Show that the pool is active, recurring, and tracked separately from direct
   initiative costs.
4. Open the allocation policy and explain the benefit-weighted method.
5. Select the remaining pools to show equal split, manual amount, and fixed
   percentage policies.
6. Show run history and confirm that each locked run reconciles to the pool
   amount.
7. Open reporting settings and confirm Executive Control Tower inclusion is on,
   Portfolio Financials inclusion is off, and Bankable Plan inclusion is off by
   default.

Speaker notes:

> Shared costs keep the portfolio economics honest. If a license, platform, or
> central support cost benefits multiple initiatives, Finance should track it
> centrally instead of distorting one initiative's value case. The important
> principle is separation: initiative financials show direct accountability,
> while Control Tower can show fully loaded economics after allocation.

### Screen 14: Progress, PMO, and Meetings

Screens:

- `/progress`
- `/progress/roadmap`
- `/progress/action-items`
- `/progress/status-updates`
- `/pmo/governance`
- `/pmo/risks`
- `/pmo/kpis`
- `/meetings`
- `/meetings/sessions/:id`

Accountable role:

- PMO Lead / Governance Manager

Use them for:

- milestone progress,
- cross-workstream roadmap review,
- action-item ownership,
- recurring status updates,
- stage gate submissions and approvals,
- risks and blockers,
- KPI actuals,
- steering committee agendas, minutes, and decisions.

Speaker notes:

> These screens explain why value is on track or off track. Financial variance
> is rarely self-explanatory; the PMO views connect the value story to delivery
> evidence, blockers, actions, risks, and decisions.

#### Saturday meeting command-center demo

Status: **Headed-browser workflow passed on development on 2026-07-15** using
commit `1c5f184` and Hostinger action `104346054`. The uninterrupted ACME run
used the external Playwright CLI with headed Chromium. Generated minutes
retained the selected `ENT-005` decision and risk; **Save Draft** displayed a
success message and the presenter edit survived reload. The session completed
and the one temporary series was deleted through Admin. Production was not
touched.

Use a PMO Lead or Transformation Office user. Use a temporary series name with
the date so it is easy to find and remove. Choose the next Saturday in the
browser's configured timezone and keep that same date throughout the sequence.

##### A. Create the meeting series

1. Open `/meetings` and wait for the **Meetings** heading and **Create meeting
   series** button. If either is missing, stop and confirm that the signed-in
   role can manage the program cadence.
2. Select **Create meeting series**. Confirm the **New meeting series** dialog
   opens.
3. Enter the following safe demo values:

   | Field | Demo value |
   |---|---|
   | Name | `ACME Saturday Value Steering - <YYYY-MM-DD>` |
   | Scope | `All` |
   | Recurrence | `Weekly` |
   | Day | `Saturday` |
   | Series start | Next Saturday, `<YYYY-MM-DD>` |
   | Series end | A later Saturday after the required test window |
   | Start | `09:00` |
   | Duration | `60` |
   | Timezone | The browser/user timezone used for the demo; record it in the evidence. |
   | Owner | The current PMO Lead or Transformation Office user. |
   | Participants | Select at least one synthetic ACME demo user. |
   | Default agenda | Leave blank; add an initiative-linked item after creation. |
   | Description | `Launch-readiness steering review for ACME value, delivery, and risks.` |

4. Select **Create series** once. Wait for navigation to `/meetings/<id>` and
   confirm the new series detail page is visible. Do not press **Sync Invite**;
   Microsoft Teams is a separate external integration and is not required for
   this core workflow.

##### B. Link `ENT-005` and prepare an initiative-backed agenda

1. In the meeting's **Initiatives** card, select **Link initiative**.
2. Choose `ENT-005 Enterprise Data and ERP Modernization` and confirm it appears
   in the linked-initiative list. This series link is required before generated
   agenda suggestions can carry initiative context.
3. Confirm at least one synthetic participant is selected for the series. Add
   more attendees only when needed for the demo; do not use real customer or
   employee addresses in the deterministic fixture.
4. Select **Add agenda item**. Enter `ENT-005 migration risk and value
   realization for 2028-03-31`, choose `ENT-005` in **Agenda initiative**, and
   select **Add**. Confirm the exact topic and `ENT-005` appear on the series.
5. Start the Saturday session as described below, then select **Generate
   Agenda** in the live session. Wait for the generated rows to appear.
6. Confirm the agenda displays `ENT-005`. Select that row and
   verify that its initiative context contains the initiative name, delivery
   status, plan/actual financial context, milestones, and risks.
7. Continue only after **All changes saved** is visible. The later minutes
   reload is the persistence checkpoint for the completed meeting record.

##### C. Open the Saturday session

1. From the series, select **Start Session**. In the dialog, enter the scheduled
   Saturday date selected above and select **Start** once.
2. Confirm navigation to `/meetings/sessions/<id>`.
3. Confirm the header date is Saturday, the state is **Live** or
   `in_progress`, and the agenda contains an `ENT-005` topic.
4. Select the agenda topic. Confirm **Current Topic** changes and the center
   panel loads initiative summary, financial context, milestones, and risks.
   If it instead says to select an initiative-linked item, return to the series
   and repair the agenda-to-initiative link before continuing.

##### D. Capture notes and agenda-scoped items

1. In **Notes**, enter complete sentences that repeat the agenda language so
   the generated agenda summary can associate them reliably:

   ```text
   ENT-005 value realization remains on plan, subject to Finance confirming the benefit owner.
   The migration risk needs a named rollback owner before the next gate review.
   The steering committee decided to keep the weekly Saturday checkpoint until the risk is green.
   ```

2. Wait for **All changes saved** before adding artifacts. This ensures the
   generated minutes use persisted notes rather than unsaved editor state.
3. Keep the `ENT-005` agenda item selected. In **Action Center**, choose
   **Decision**, priority **High**, enter `Keep the Saturday checkpoint until
   migration risk is green`, and select **Add Decision**.
4. Add a second item with type **Risk**, priority **High**, and text `Migration
   rollback owner is not confirmed`. Confirm both cards appear under **Action
   Center**. These records are attached to the active source agenda item.

##### E. Generate and review AI-assisted minutes

1. Select **Generate Minutes**. This UI action creates a draft with an **AI
   Summary** and agenda-organized discussion from the saved notes/transcript and
   captured items. It does not send email and does not require a Teams invite.
2. Wait for `Draft minutes generated.` and the **Draft meeting minutes** editor.
3. Confirm the draft contains all of the following:

   - `## AI Summary`;
   - `## Agenda Discussion`;
   - a heading for the `ENT-005` agenda topic;
   - the rollback-owner discussion;
   - `Captured items:` followed by the decision and risk;
   - global **Decisions** and **Risks And Issues** sections.

4. Correct wording in **Draft meeting minutes** if needed and select **Save
   Draft**. Wait for `Draft minutes saved.`, reload, and confirm the edited draft
   persists with status `draft`.
5. Do not select **Send Minutes** during routine demo preparation. That action
   sends external email when Resend and attendee email addresses are configured.

##### F. Complete and verify the session

1. Select **Complete Session** once.
2. Confirm navigation back to `/meetings/<meeting-id>`.
3. In **Sessions**, confirm the selected Saturday row is `COMPLETED`.
4. Open the completed row again and confirm notes, draft minutes, agenda,
   attendee, decision, and risk are still visible and the session is no longer
   presented as a new live session.
5. Open `/progress/action-items` only if an **Action** artifact was created;
   confirm it appears with the expected status and initiative. Decisions and
   risks should be checked in their respective meeting/PMO views.

##### G. Deterministic cleanup

1. Preserve screenshots, console/network results, session ID, and meeting ID in
   the acceptance evidence without recording tokens or participant email
   addresses.
2. Open `/admin`, select **Data Cleanup**, and select the checkbox whose
   accessible name begins **Select meeting** followed by your exact temporary
   series name.
3. Enter the exact confirmation phrase `DELETE MEETINGS`. Confirm **Delete
   selected meetings** remains disabled until at least one meeting is selected
   and the phrase matches exactly, then select it once.
4. Wait for `Deleted 1 meeting series.` and for
   the selected rows to disappear.
5. Return to `/meetings`; confirm the temporary series is gone and unrelated
   meetings remain.
6. Return to `/meetings` and confirm the exact temporary series name is absent.
   This browser-visible cleanup is the demo acceptance checkpoint. Do not use
   production.

### Screen 15: Control Tower

Screen:

- `/reports/control-tower`

Accountable role:

- Transformation Office Director

Use it for:

- management meeting view,
- consolidated decision support,
- executive reporting,
- burdened value after shared-cost allocation.

Shared-cost impact to call out:

| Field | Meaning |
|---|---|
| Allocated Costs | Shared-cost allocations from completed or locked runs. |
| Burdened Costs | Direct initiative costs plus allocated shared-cost burden. |
| Net After Allocation | Benefits less direct costs and allocated shared costs. |

Demo action:

1. Set target year to `2028` when demonstrating the current ACME shared-cost
   pools.
2. Point to **Allocated Costs** and **Net After Allocation**.
3. Explain that the number should drill back to `/shared-costs` pool, rule, run,
   and allocation basis.

Speaker notes:

> The control tower is the management meeting view. It combines portfolio,
> financials, risks, progress, blockers, and decision support into one operating
> cadence. It is also where executives should see burdened value after central
> shared costs are allocated.

Management use:

- Runs steering committee reviews from a single page.
- Connects value leakage to execution blockers and decisions.
- Helps executives focus on the few decisions that protect value realization.

---

## 8. Full Management Demo Script

### Opening

Screen:

- `/dashboard`

Speaker notes:

> Today we will walk through ACME's enterprise transformation portfolio. The
> goal is to show not only a list of initiatives, but how the transformation
> office converts a baseline business into bankable, trackable value.

### Segment 1: Show portfolio structure

Screen:

- `/initiatives/pipeline`

Actions:

1. Show 10 initiatives.
2. Filter by tag `automation`.
3. Filter by workstream `Commercial Growth`.
4. Clear filters.

Speaker notes:

> ACME has 10 initiatives. The portfolio is structured by workstream, business
> unit, and value tag. This lets management answer: where is the value coming
> from, who owns it, and which operating lever is responsible?

### Segment 2: Show baseline and FY28 run-rate value

Screen:

- `/financials`

Actions:

1. Set **Year** to `2028`.
2. Set **Yearly**.
3. Turn **Benefits On**.
4. Turn **Actuals On**.
5. Point to baseline cards.
6. Point to Net Run-rate Value.

Speaker notes:

> The baseline is FY26: `$20.0M` revenue and `$9.0M` gross margin. Against that
> baseline, the FY28 plan shows `$9.182M` benefits and `$0.800M` recurring cost,
> which gives `$8.382M` net run-rate value.

### Segment 3: Explain FY27 ramp versus FY28 run-rate

Screen:

- `/financials`

Actions:

1. Change **Year** to `2027`.
2. Show ramp-year net value.
3. Change **Year** to `2028`.
4. Show run-rate value.

Expected values:

| Year | Benefits | Recurring costs | One-off costs | Net run-rate value |
|---:|---:|---:|---:|---:|
| 2027 | `$4.62M` | `$0.40M` | `$2.50M` | `$4.22M` |
| 2028 | `$9.182M` | `$0.800M` | `$0.00M` | `$8.382M` |

Speaker notes:

> FY27 is the ramp year. Benefits begin, but one-off implementation investment
> is also incurred. FY28 is the target run-rate year. That is why FY28 is the
> cleanest year for EBITDA run-rate value.

### Segment 4: Show an initiative value case

Screen:

- `/initiatives/pipeline`
- Open **ENT-006 Aftermarket Revenue Growth**
- Tab: **Financials**

Actions:

1. Select **Base** scenario.
2. Show summary cards.
3. Click **Edit Details** to show monthly detail.
4. Do not save changes during demo.

Speaker notes:

> This is one source of the portfolio value. Pricing contributes revenue growth
> and margin uplift through discount optimization. The same monthly values roll
> into the portfolio financial overview.

### Segment 5: Explain cost treatment

Screen:

- `/financials`

Actions:

1. Keep **Year** = `2028`.
2. Select cost category **Software / Licenses**.
3. Select **Support / Maintenance**.
4. Select **People Support**.
5. Clear the cost category filter.

Speaker notes:

> We separate one-off investment from recurring cost. The FY28 EBITDA run-rate
> calculation subtracts recurring costs. One-off investment is used for payback
> and funding discussion, not recurring EBITDA.

### Segment 6: Explain shared-cost burdening

Screens:

- `/shared-costs`
- `/reports/control-tower`

Actions:

1. Open **Shared Costs**.
2. Select the group technology and data platform pool.
3. Show the pool amount, actual amount, allocation policy, and run history.
4. Switch through the PMO, change/training, and advisory/vendor pools to show
   equal split, manual amount, and fixed percentage allocation methods.
5. Open **Executive Control Tower**.
6. Set target year to `2028` for the current ACME shared-cost proof.
7. Point to allocated costs, burdened costs, and net after allocation.

Speaker notes:

> Direct initiative financials show what each initiative owner controls. Shared
> Costs show central platform, PMO, license, advisory, or change costs that
> support multiple initiatives. We allocate those centrally so the Control Tower
> can show fully loaded value without hiding central costs inside a single
> initiative. Bankable plan values remain direct-only unless Finance explicitly
> enables burdened bankable reporting.

### Segment 7: Explain governance and realization

Screens:

- `/financials/bankable-plan`
- `/financials/benefits-register`
- `/financials/benefit-tracking`
- `/financials/waterline`

Actions:

1. Open **Bankable Plan** and show that ACME initiatives have locked approved
   plan snapshots.
2. Open **Benefits Register** and show validation status, evidence metadata,
   risk-adjusted value, and owner metadata.
3. Open **Benefit Tracking** and show locked baseline versus realized actuals.
4. Show yearly rollup first, then drill to workstream or initiative if asked.
5. Open **Waterline** to explain frozen workstream targets.

Speaker notes:

> The next level of maturity is to lock bankable plans at approval gates and
> then track realized benefits against that locked plan. ACME has locked
> bankable plan snapshots and benefit ledger rows, so this is now the main
> board evidence for realized value. The Benefits Register controls validation;
> Benefit Tracking shows actual realization against the locked baseline. The
> locked plan is not an actuals lock; actual scenario values and actual cost
> amounts continue to be entered in initiative Financials.

### Segment 8: Run the management cadence in Meetings

Screens:

- `/meetings`
- `/meetings/sessions/:id`

Actions:

1. Create the temporary weekly Saturday series using Screen 14, section A.
2. Link `ENT-005`, add the initiative-backed agenda topic, and open the Saturday
   session.
3. Generate the agenda, select its `ENT-005` topic, and show the initiative
   context panel.
4. Enter the prepared notes and wait for **All changes saved**.
5. Add the agenda-scoped decision and risk, generate minutes, add a short
   presenter correction, select **Save Draft**, reload, and show the correction.
6. Complete the session and show `COMPLETED` on the series detail page.
7. Point out the agenda-specific **Captured items** section and explain that
   actions and risks can flow into portfolio follow-up while the meeting retains
   the decision record.
8. After the audience segment, delete the temporary series through **Admin >
   Data Cleanup** and verify it is absent from Meetings.

Speaker notes:

> The financial and delivery views become an operating cadence here. The PMO
> prepares an initiative-linked agenda, runs the review with live portfolio
> context, records decisions and risks against the active topic, and generates
> a reviewable draft rather than losing the meeting outcome in personal notes.
> Microsoft Teams is optional: the platform meeting, agenda, notes, decisions,
> and completion flow works independently and degrades gracefully when no
> organizer integration is connected.

### Close

Screen:

- `/financials`

Actions:

1. Return to **Year** = `2028`.
2. Show baseline cards and net run-rate value.

Speaker notes:

> The ACME portfolio demonstrates the core transformation management story:
> baseline, initiatives, planned benefit, recurring cost, actual variance, and
> management drilldown. The headline is `$8.382M` FY28 net
> run-rate value on a `$20.0M` revenue and `$9.0M` gross margin baseline.

---

## 9. Recommended Board Questions and Answers

| Board question | Where to answer | Answer pattern |
|---|---|---|
| What is the starting point? | `/financials` baseline cards | FY26 revenue baseline `$20.0M`, gross margin baseline `$9.0M`. |
| What is the FY28 run-rate value? | `/financials`, Year = 2028 | `$8.382M` net run-rate value. |
| How much is growth versus cost-out? | `/financials`; initiative financial tabs | Revenue uplift `$4.0M`, GM uplift `$5.4M`, savings `$3.75M`. |
| What costs are recurring? | `/financials`, cost category filter | FY28 recurring run cost `$0.80M`. |
| What investment is needed? | `/financials`, Year = 2027; cost breakdown | One-off investment `$2.5M`. |
| Who owns the value? | `/initiatives/pipeline`; initiative detail | Owner, group owner, BU, and workstream per initiative. |
| Is the plan locked? | `/financials/bankable-plan` | ACME has locked bankable plan snapshots for all 10 initiatives; use `ENT-005` to show version 2 and governed rebaseline history. |
| Which benefit lines are Finance validated? | `/financials/benefits-register` | Filter by Finance validated and show owner, evidence, plan, actual, validated, risk-adjusted, bankable, and realized values. |
| Is value realized or just planned? | `/financials/benefit-tracking` | ACME has realized actuals in the benefit ledger; compare actuals to locked bankable plan by portfolio, workstream, initiative, and period. |
| Where are risks and blockers? | Initiative **Risks**, **Status**, `/pmo/risks`, `/progress/status-updates` | Show RAG status, risk list, and overdue updates. |

---

## 10. Operating Cadence for a Transformation Office

Weekly:

- Initiative owners update status, risks, dependencies, and action items.
- Transformation office reviews overdue updates and blockers.
- PMO lead prepares workstream or steering committee agendas in `/meetings`.

Bi-weekly:

- Workstream owners review initiative pipeline and milestone progress.
- Finance reviews material changes to benefit and cost assumptions.
- Benefits controller reviews submitted benefit lines and rejects or validates
  them before they are presented as bankable.

Monthly:

- Transformation office reviews `/financials` with Year and Actuals filters.
- Benefits and recurring costs are reconciled by initiative.
- Finance and business benefit owners enter or import realized benefit ledger
  rows in `/financials/benefit-tracking`.
- Benefits Register validation status is reviewed for new or changed value
  claims.
- Steering committee reviews risks, delays, and value leakage.

Quarterly:

- Lock or refresh bankable plans after governance approvals.
- Review waterline target locks by workstream.
- Present board pack with baseline, run-rate value, actuals, variance, risks,
  and decisions required.
- Move realized initiatives through Gate 5 only after actual evidence and BAU
  ownership are confirmed.

---

## 11. Practical Demo Warnings

1. Do not call revenue uplift EBITDA. Revenue becomes EBITDA-effective only
   through margin conversion.
2. Do not subtract one-off investment from FY28 run-rate EBITDA. Use it for
   payback and investment discussion.
3. Do not mix value bases in one management statement. Say whether a chart is
   using target-year run-rate, in-year, cumulative, or all-years value.
4. Do not call unvalidated or rejected benefit lines bankable. Use the Benefits
   Register validation status before making Finance-backed claims.
5. Do not promote ACME demo values as a template for every tenant. New tenants
   should get reusable configuration templates; ACME's portfolio values are
   deterministic sample data for demonstration and acceptance testing.
