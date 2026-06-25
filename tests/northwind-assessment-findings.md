# Northwind Health Partners — Running Findings Log

Tenant: northwind-health-transformation (id cb3cf2de-3b04-45a9-b166-549f7f4ea81e)
Admin: venkatesh.br@live.com
Environment: production https://transmuter.ishirock.tech (Stripe sandbox)
Started: 2026-06-24

## Findings

### F1 — Email-uniqueness validated AFTER payment, not before checkout [Severity: High]
Signing up with venkatesh.br@gmail.com (already registered) was allowed to proceed all the
way through Stripe Checkout and complete payment. Only the post-payment
`/billing/checkout-completion` call returned HTTP 409 "Initial admin email already belongs to
another tenant", and provisioning failed — leaving a paid (sandbox) subscription with no tenant.
In live mode this would charge a customer for a workspace that never provisions.
Recommendation: validate admin email + org slug uniqueness on the /get-started form (server
pre-check) before creating the Stripe Checkout session.

### F3 — Empty-portfolio dashboard shows placeholder trend deltas [Severity: Low]
Fresh tenant dashboard with 0 initiatives still renders "TOTAL INITIATIVES 0 ↑ 2 from last week".
Hardcoded/placeholder week-over-week deltas appear even when there is no history. Minor, but
undermines trust in the executive header metrics. Recommendation: suppress trend chips until there
is real prior-period data.

### F4 — "Add Platform User" modal: no feedback when submit is blocked [Severity: Medium]
The Add Platform User modal (Create User / Send Invite) was the only configuration form that did
not complete: clicking the (enabled) Create/Invite buttons fired no network request and produced
no toast, inline error, or field highlight — the modal simply stayed open. Every other admin form
(strategic params, financial config, stage gates, dashboard config) accepted the same programmatic
fill and saved. A human typing into the fields may satisfy the form binding, but the complete lack
of validation feedback when submission is blocked is a real UX gap. Also note the modal renders two
identical "Send Invite" buttons in the DOM. Recommendation: surface validation errors on submit and
disable the action button until the form is valid. (Proceeded with admin-as-sole-owner, which the
setup guide explicitly permits for a demo.)

### F5 — Dashboard header says "N strategic workstreams" but counts initiatives [Severity: Low]
Executive dashboard subtitle reads "Real-time synchronization across 10 strategic workstreams"
when there are 10 initiatives across 6 workstreams. Wording/metric mismatch.

### F6 — No way to DELETE a benefit or cost line in Initiative Financials [Severity: High]
In the Financials tab (incl. "Edit Details" mode) each benefit/cost line offers Submit / Validate /
Reject / Risk actions but NO delete/remove control, and no aria-labelled delete anywhere. A real
transformation officer who mis-keys a benefit or cost line (wrong amount, duplicate, wrong metric)
has no UI path to remove it. This is a correctness and data-hygiene gap. Recommendation: add a
per-line delete (with confirm) for unlocked plans.

### POSITIVE P1 — Financial engine aggregation and value bridge are correct
Portfolio Financial Overview (FY2029, Yearly): Benefits $17.14M − Costs $1.12M = Net Value $16.02M
(exact), FY2026 baseline reconciles to $60.0M revenue / $21.0M gross margin / 35% margin rate, and
the Actual scenario ($11.59M) renders alongside Plan for variance. Per-initiative net run-rate is
computed exactly as (Gross Margin Uplift + Cost Savings − Recurring Costs); revenue uplift is
correctly EXCLUDED from EBITDA run-rate (verified TRN-001 $50K, TRN-002 $1.97M, TRN-003 $610K,
TRN-005 $2.22M, TRN-007 $1.10M, TRN-008 $730K, TRN-009 $1.47M — all match the model). Target-year
run-rate mode, Benefits/Actuals toggles, stage and category filters all work.

### F7 — Financial line add-form has no success/failure feedback; races possible [Severity: Medium]
The benefit "Add Line" and cost "Add Cost" actions give no toast/confirmation and the form does not
visibly lock during submit. Rapid sequential adds (automation) occasionally dropped a line
(TRN-006 lost one ~$48K recurring line) or, after an error+retry with no idempotency guard,
duplicated lines (TRN-010 overstated). Combined with F6 (no delete), a dropped/duplicated line is
hard to detect and impossible to correct in-UI. Recommendation: confirmation on add, disable form
during submit, and per-line delete.

### F2 — Provisioning errors surfaced to user as generic "pending" [Severity: Medium]
subscription-success.component maps any error (incl. the 409 above) to setupState='pending'
with copy "we are finishing your workspace setup. Please try signing in shortly." A user hitting
a real provisioning failure (duplicate email) is told to keep waiting forever with no actionable
message. Recommendation: distinguish hard failures (409/4xx) from transient pending and show a
recovery path (e.g., "this email is already in use — contact support / use another email").

### F11 — Benefit Finance-validation impossible after Gate-2 lock [Severity: High]
Once the bankable plan is locked, benefit-line Submit/Validate/Reject are disabled with no
disabled-reason. A governed rebaseline re-locks immediately at V2 without reopening validation.
Validation must precede the first lock; no recovery if you lock first. (My plans were all locked
before validating, so Benefits Register is stuck at 40 Draft / $0 validated.)

### F12 — Shared-cost Manual/Fixed-% weighting is a fragile two-track UI [Severity: Low-Med]
Targeting scope and structured weights are separate controls; Manual-amount with no weights
previews "$0 Blocked". Benefit-weighted/Equal-split post with no weight entry. Substituted
benefit-weighted to post the two weight-based pools.

### POSITIVE P2 — Shared-cost allocation -> burdened Control Tower works end-to-end
All 4 pools previewed (Reconciled) and posted as locked runs; allocated $1.85M / unallocated $0.
Control Tower: Net before $16.02M -> Net after allocation $14.17M, burdened costs $2.97M. Exact.

### POSITIVE P3 — Governed rebaseline + versioning works
TRN-001 rebaseline request -> finance-baseline approval -> bankable plan V2 with v1/v2 history.

### POSITIVE P4 — Benefit-tracking ledger realization works
FY2029 realized rows for all 10; realized $14.58M vs locked baseline $16.02M, variance -9%.
