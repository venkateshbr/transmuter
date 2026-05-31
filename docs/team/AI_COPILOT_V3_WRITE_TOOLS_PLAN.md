# AI Copilot V3 Write Tools Plan

Issue: #176  
Owner: Vishwa  
Status: Proposed next increment after v2 QA and Prahari review

## Summary

V3 should expand the copilot from single-record draft actions into governed portfolio
operations. The principle stays the same: every write is drafted, validated, cited,
and explicitly confirmed before execution.

## Prerequisites

- V2 durable `ai_copilot_actions` ledger is deployed with RLS.
- Prahari signs off on tool guardrails, payload hashing, and confirmation auditability.
- Aksha acceptance includes real API and browser confirmation flows.
- Copilot evals exist for tool selection, tenant isolation, financial math, and denied writes.

## V3 Write Tool Candidates

### Low-Risk Operational Writes

- `update_milestone_status`
  - Change milestone status, actual start/end dates, and checklist completion.
  - Require initiative visibility and manage permission.
- `update_action_item`
  - Change action item status, due date, priority, and assignee.
  - Useful for meeting follow-ups and owner workload cleanup.
- `create_status_update_draft`
  - Draft a structured status update from current milestones, risks, KPIs, and notes.
  - Submit only after user review.
- `create_meeting_agenda_item`
  - Add agenda items linked to initiatives, risks, or open actions.

### Medium-Risk Portfolio Writes

- `update_initiative_metadata`
  - Edit owner, priority, RAG, planned dates, country, tag, workstream, and summary.
  - Require field-by-field diff before confirmation.
- `create_dependency`
  - Add initiative or milestone dependencies with cycle checks and severity rationale.
- `update_risk`
  - Update mitigation, owner, escalation, status, impact, and likelihood.
  - Show before/after risk rating.
- `upsert_kpi_entry`
  - Add KPI actual/base/high values for a period.
  - Require Decimal validation and period collision handling.

### High-Risk Financial And Governance Writes

- `update_financial_grid_batch`
  - Multi-period financial edits from natural language or pasted tables.
  - Require preview table, variance summary, and explicit scenario/period confirmation.
- `allocate_shared_costs`
  - Draft allocation run against existing shared cost rules.
  - Require total reconciliation and affected initiative list.
- `submit_gate_decision`
  - Draft gate approval/rejection commentary.
  - Require role checks and explicit confirmation because it can change lifecycle state.
- `bulk_import_from_chat`
  - Convert a pasted initiative/financial table into a workbook preview.
  - Confirm through existing import preview mechanics, never direct blind insert.

## Copilot Experience Enhancements

- Add an action review drawer showing:
  - Proposed diff.
  - Source claims and cited records.
  - Guardrails passed/failed.
  - Permission check result.
  - Expiry time and action hash.
- Add saved copilot threads per tenant/user with redacted context summaries.
- Add suggested next actions after every answer:
  - "Draft a status update"
  - "Create mitigation action"
  - "Open initiative detail"
  - "Generate steering brief"
- Add report recipes:
  - Weekly transformation office brief.
  - Steering committee pack.
  - Initiative owner cockpit.
  - Risk escalation brief.
  - Value realization variance report.

## Acceptance Criteria For V3

- Every write tool has typed request/response models and service-layer execution.
- Every confirmed action creates an `audit_log` entry and updates `ai_copilot_actions`.
- UI shows a before/after diff for updates and a preview for creates.
- Viewer and unauthorized owner write attempts are denied before draft confirmation.
- Financial tools preserve `Decimal` arithmetic and string JSON money values.
- Evals cover at least 30 seeded user prompts across read, draft, confirm, deny, and report flows.
