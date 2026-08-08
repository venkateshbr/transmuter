# Transmuter User Operations Guide

Last reviewed: 2026-08-08

This is the canonical day-to-day guide for Transformation Office, PMO, finance, workstream leads, initiative owners, benefit owners, sponsors, and viewers. It uses **ACC-101 Invoice Automation** at ACME Industrial Services as a repeatable example. Setup belongs in the [Administration Guide](transmuter-administration-guide.md), while dashboard interpretation belongs in the [Dashboard and Reporting Guide](transmuter-dashboard-reporting-guide.md).

## 1. Navigation model

| Menu | Purpose |
|---|---|
| Dashboard | Read-only decision views: Operational, Financial, and Initiative Portfolio |
| Transformation Management | Initiative pipeline, milestones, roadmap, actions, status, risks, and KPIs |
| Financial Operations | Benefit evidence, registers, plans, target locks, and shared costs |
| Governance & Cadence | Gate approvals, meetings, decisions, and follow-up |
| People | Tenant user administration when permitted |
| Profile | Your account and preferences |

The key rule is simple: **read and decide in dashboards; enter and maintain in the relevant operating menu or Initiative detail**.

## 2. Sign in and profile

Accept an invitation from your administrator, sign in, and complete any forced password change. Open **Profile** to confirm your display information and role. If a required page or control is absent, request the correct role rather than sharing another user's account.

## 3. Operating workbenches

The former Operations menu is separated by job-to-be-done:

- **Transformation Management:** Initiative Pipeline, Progress Monitor, Roadmap & Milestones, Action Items, Status Updates, Risk Register, KPI Management.
- **Financial Operations:** Benefit Ledger, Benefits Register, Bankable Plans, Waterline & Target Locks, Shared Costs.
- **Governance & Cadence:** Gate Approvals and Meetings.

Each top-level menu opens a focused workbench describing its destinations. Permissions may prevent some users from opening restricted functions. Dependencies are managed and traced within **Roadmap & Milestones**, so there is no duplicate Dependencies menu item. Benefit validation is performed within **Benefits Register**, so there is no separate duplicate validation destination.

## 4. Initiative lifecycle

### 4.1 Create an initiative

Users with initiative-management permission open **Transformation Management → Initiative Pipeline → New** and enter the business problem, name, owner, sponsor, business unit, workstream, stage, priority, dates, tags, and narrative.

ACME example:

| Field | Value |
|---|---|
| Code/name | ACC-101 Invoice Automation |
| Workstream | Digital Operations |
| Owner | Maya Chen |
| Sponsor | Priya Shah |
| Stage | L2 Business Case |
| Priority | High |
| Tag | automation |
| Objective | Reduce manual invoice effort and processing errors |

Save and open the initiative detail. If creation is blocked, an administrator must finish tenant setup.

### 4.2 Pipeline and matrix

The Pipeline is the portfolio list. Filter and sort it to locate work, then open a row for detail. Use the Matrix view when comparing initiatives across configured dimensions. Filters narrow the working set; they do not change underlying records.

Example: filter workstream **Digital Operations**, priority **High**, and tag **Automation** to find ACC-101 and its peers.

### 4.3 Initiative detail

Use the tabs on initiative detail to maintain the complete record:

- Overview/charter: case, scope, ownership, dates, and narrative.
- Financials: scoped metrics, scenarios, benefits, cost lines, and timing.
- Milestones/roadmap: delivery checkpoints and dependencies.
- KPIs: outcome measures, targets, and actuals.
- Risks: likelihood, impact, mitigation, owner, and status.
- Status updates: periodic RAG, summary, accomplishments, blockers, and next steps.
- Governance: stage criteria and submissions.
- Activity/history where shown: evidence of change over time.

Keep facts in their dedicated feature. Do not put a risk only in a status narrative or a financial actual only in meeting notes.

## 5. Delivery operations

### 5.1 Progress Monitor

Use Progress Monitor to review initiative delivery and open the relevant record. For ACC-101, a delayed integration milestone should drive an amber/red status and a corrective action, not an edit to a dashboard chart.

### 5.2 Roadmap, milestones, and dependencies

Create milestones from the initiative's **Milestones** tab. Enter both **Planned Start** and **Target Completion** when the milestone represents a delivery window. If only the completion date is known, the Roadmap Explorer shows a diamond instead of inventing a duration.

Open **Transformation Management → Roadmap & Milestones** to use the portfolio Gantt:

1. Select **Fit all** to show the earliest planned start through the latest planned completion in the filtered portfolio.
2. Change **Scale** between Year, Quarter, Month, and Week without changing saved dates.
3. Filter by workstream, status, milestone, initiative, or owner.
4. Expand a workstream and initiative to see its milestone bars. The bar is the planned delivery window; the diamond at its right edge is planned completion.
5. Choose **Blocking and at risk** to reduce connector clutter, or **Selected chain** to trace one milestone's upstream and downstream consequences.
6. Select either a milestone name in the left register or its bar/diamond to review dates, owner, pressure, upstream blockers, and downstream dependents. Use **Open milestone details** to open the initiative's Milestones tab with that record expanded when it needs correction. The Gantt itself is read-only.

#### ACC-101 worked dependency example

Create these three milestones:

| Milestone | Planned start | Planned completion | Owner |
|---|---|---|---|
| ERP connector build | 1 August 2026 | 15 September 2026 | Maya Chen |
| Pilot invoice processing | 16 September 2026 | 30 September 2026 | Maya Chen |
| Production release | 1 October 2026 | 15 October 2026 | Operations Lead |

On **Pilot invoice processing**, add **ERP connector build** as the upstream milestone. Select dependency type **Finish to start** and lag `1` day. On **Production release**, add **Pilot invoice processing** as **Finish to start** with lag `0`.

Dependency types mean:

| Type | Use when |
|---|---|
| Finish to start | The downstream milestone cannot start until the upstream milestone finishes |
| Start to start | The two work windows may overlap, but the downstream start depends on the upstream start |
| Finish to finish | Completion of the downstream milestone depends on upstream completion |
| Start to finish | The downstream milestone cannot finish until the upstream milestone starts; use only for a genuine handover pattern |

Lag is the delay after the dependency condition. `+5` means wait five days; `-2` represents a two-day lead or overlap. After saving, open the Roadmap Explorer, select **Production release**, and choose **Trace dependency chain**. The connector build, pilot, and production release remain emphasized while unrelated work is dimmed.

If the connector slips to 20 September, update its Target Completion in the initiative milestone workflow. Then reopen the Gantt and assess whether the pilot or production dates also require an approved schedule change. The Roadmap Explorer never silently reschedules dependent records.

Milestones with only one planned date still appear as a diamond. Milestones with neither a planned start nor planned completion appear under **Needs scheduling** below the Gantt. Assign dates in the source initiative rather than leaving operational work outside the schedule.

### 5.3 Action Items

Action Items are accountable follow-ups, commonly created from meetings. Set a clear action, owner, due date, linked initiative, and status.

Good example: “Daniel Ortiz to validate the July $150,000 benefit evidence by 12 August.” Avoid vague items such as “Check benefits.”

### 5.4 Status Updates

Submit periodic updates with an honest RAG state, concise summary, accomplishments, blockers, and next steps. A submitted update feeds recent activity and operational reporting.

ACC-101 example: Amber; connector testing is five days late; 80% of pilot invoices prepared; vendor recovery plan agreed; next step is production readiness review.

### 5.5 Risk Register

Create risks with likelihood, impact, mitigation, owner, and status. The Operational Dashboard heatmap aggregates these fields.

Example: “ERP API rate limits delay nightly processing,” likelihood High, impact Medium, owner Maya, mitigation performance test plus vendor quota increase. Close the risk when evidence supports closure.

### 5.6 KPI Management

Define outcome measures and record actuals against base/high targets.

Example: **Invoice touchless rate**, base target 75%, high target 85%, July actual 72%. This appears below target in KPI Pulse; update the actual in KPI Management, never in the chart.

## 6. Governance operations

### 6.1 Gate submissions and approvals

The initiative owner completes required criteria and submits the stage gate. An authorized approver reviews evidence, approves or rejects, and records rationale.

ACC-101 example: submit L2 with business case, benefit owner, $300,000 implementation cost, security review, and milestone plan. The PMO approves progression to L3 only when criteria are complete. A pending count appears on the Operational Dashboard until decided.

### 6.2 Meetings

Use Meetings to create the forum, agenda, attendees, and linked initiatives. During a live session capture discussion, decisions, and actions. Afterward finalize notes/transcript and track actions in Action Items.

Example weekly value review:

1. Create **ACME Weekly Value Review** for Friday 10:00.
2. Add ACC-101 benefit validation and connector risk as agenda items.
3. Invite Maya, Daniel, and Priya.
4. Start the session; record the decision to accept July evidence subject to invoice sample confirmation.
5. Create Daniel's validation action with due date.
6. End the session and review the resulting actions.

When configured, Microsoft 365 may schedule Teams and synchronize transcript material. If unavailable, continue with the native meeting and manual transcript workflow.

## 7. Financial operations

### 7.1 Financial scope and plan

Authorized users open the initiative's Financial Scope and enable only relevant metrics/categories. Enter base/high plan values and timing in the initiative financial view.

For ACC-101:

- Base recurring cost-saving benefit: $1,800,000 annually.
- High case: $2,200,000 annually.
- One-time implementation cost: $300,000.
- Recurring software cost: $120,000 annually.
- Base net annual run-rate: $1,680,000.

### 7.2 Benefit Ledger

Use **Financial Operations → Benefit Ledger** to enter or import realized evidence. Supply initiative, period, metric, amount, evidence/reference, and status as required.

Example: record ACC-101 July actual cost saving of `$150,000.0000`, link the finance evidence reference, and submit it for validation. Do not type this value into the Financial Dashboard.

### 7.3 Benefits Register and validation

Use Benefits Register to inspect accountable benefits and validation state. Finance or the authorized reviewer validates or rejects evidence according to policy.

Example: Daniel compares the $150,000 July entry with the approved invoice sample. If supported, validate it; otherwise reject it with a specific correction note. Dashboard realized values should only be interpreted with their validation/status basis understood.

### 7.4 Costs

Maintain initiative cost lines in initiative financials. Select the correct category, recurring/one-time treatment, scenario, period, and amount. For shared portfolio costs use Shared Costs instead.

### 7.5 Shared Costs

Authorized finance users create a pool, define allocation rules, preview recipients, and post a run. A $240,000 PMO platform pool allocated to workstreams must be traceable to its driver and posting run. Review before posting; do not try to correct allocations through dashboard totals.

### 7.6 Bankable Plans, rebaseline, and Waterline locks

Use Bankable Plans to inspect versions and govern rebaselines. Use Waterline & Target Locks to preview and lock workstream commitments.

Example: lock Digital Operations after ACC-101 and peer initiatives have approved assumptions. If ACC-101 scope later changes, raise a rebaseline with rationale and approval. The original lock remains historical evidence.

## 8. Dashboards and reports

Operational and Financial dashboards are read-only decision surfaces with filters, drill-through, export, and personal layout customization. Initiative Portfolio remains unchanged. See the [Dashboard and Reporting Guide](transmuter-dashboard-reporting-guide.md) for every widget and formula example.

## 9. AI assistant and insights

Use the assistant for questions such as “Show at-risk initiatives” or “Summarize the portfolio.” Review cited sources and open the underlying records before acting. AI output is advisory; it must not replace evidence, approval, or human review. AI Insights under PMO may be available based on role and configuration.

## 10. Exports and board packs

The Operational Dashboard can prepare an executive brief. The Financial Dashboard can export a board pack using the current filters and data basis. Verify the selected fiscal period, scenario, actuals toggle, and as-of date before distribution.

## 11. Weekly ACME operating routine

1. Owners update milestones, risks, KPIs, and status.
2. Benefit owners enter evidence in Benefit Ledger.
3. Finance validates benefits and checks cost lines.
4. PMO clears overdue actions and prepares meeting agenda.
5. Approvers decide submitted gates.
6. Transformation Office reviews Operational Dashboard exceptions.
7. Finance reviews Financial Dashboard variance and waterline.
8. The governance meeting records decisions and assigns follow-ups.

## 12. Quality checklist

- Each initiative has an accountable owner and sponsor.
- Dates, milestones, and dependencies agree.
- Risks have mitigation and owner.
- KPI actuals have the right period.
- Money uses the correct scenario, period, category, and recurring treatment.
- Actual benefit evidence is entered once and validated.
- Dashboard filters are cleared or intentionally recorded before sharing results.
- Decisions become approvals or actions, not untracked narrative.
