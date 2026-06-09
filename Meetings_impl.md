# Meetings Functionality Implementation Plan

## Summary
Current Meetings work is partially implemented. Closed GH issues cover the original MVP (#11, #50, #51, #62, #167, #196), but the live code is missing key behaviors: multi-workstream meeting series, date-specific session start/resume, usable transcript/minutes UI, and reviewable AI agenda suggestions.

## Key Changes

- **Meeting series workstreams**
  - Add `meeting_workstreams` join table with `tenant_id`, `meeting_id`, `workstream_id`, unique `(tenant_id, meeting_id, workstream_id)`, RLS, and indexes.
  - Keep existing `meetings.workstream_id` as backward-compatible legacy field; backfill it into `meeting_workstreams`.
  - Update meeting create/update contracts to accept `workstream_ids: string[]`.
  - API list/detail should return `workstreams: [{ id, name }]`.
  - UI create/edit series modals should show multi-select workstream checkboxes.

- **Start session by date**
  - Change `POST /meetings/{meeting_id}/sessions/start` to accept `{ session_date: "YYYY-MM-DD" }`.
  - Add unique DB constraint/index for one session per `(tenant_id, meeting_id, session_date)`.
  - If the selected date already has a session, return that session instead of creating a new one.
  - UI Start Session opens a date modal defaulted to today; after submit, navigate to the returned session.

- **Transcript and minutes**
  - Replace the current “Import Transcript” button behavior with a modal supporting pasted transcript text and `.txt` upload.
  - Show success/error state after import; set `has_transcript=true`.
  - Keep “Generate Minutes” enabled when notes, transcript, agenda, or artifacts exist; show clear error if nothing exists.
  - “Send Minutes” should remain disabled only when no draft minutes exist; once sent, show `minutes_status=sent`.
  - Keep Resend-backed delivery from #196, but add better frontend error display for missing attendees/email config/provider failure.

- **AI agenda suggestions**
  - Add `POST /meetings/{meeting_id}/agenda/suggestions`.
  - Suggestions are review-first, not auto-created.
  - Inputs: meeting workstreams, open carry-forward action items, initiatives tagged to selected workstreams, linked initiatives, recent risks/milestones where available.
  - Output: `[{ text, initiative_id, rationale, source_type }]`.
  - UI shows a review panel where admin can accept/edit/reject suggestions; accepted items are saved through existing agenda create or a new bulk endpoint.
  - LLM use must mask PII and trace via Langfuse; deterministic fallback should produce useful agenda suggestions if AI is unavailable.

## GitHub Issue Review Findings
- #50/#51: CRUD and pages exist, but workstream selection is incomplete and session start is date-blind.
- #62: AI notes extraction endpoint exists, but transcript import/HITL persistence is not fully usable from UI.
- #167: Command center shell exists, but transcript/minutes actions lack usable UI flow and status handling.
- #196: Backend minutes delivery exists, but frontend still feels greyed out because draft generation/import flow is unclear.
- New implementation issue should track this as “Meetings v2 completion: multi-workstream, dated sessions, transcript/minutes UX, AI agenda suggestions.” Prahari review required for AI and email behavior.

## Test Plan
- Backend tests:
  - Create/update meeting with multiple workstreams.
  - Existing single `workstream_id` meetings backfill/read correctly.
  - Starting same meeting/date twice returns same session.
  - Starting different dates creates separate sessions.
  - Agenda suggestions use workstream initiatives and prior open actions.
  - Transcript import, minutes generation, and minutes send success/failure paths.

- Frontend checks:
  - Angular compile and template checks.
  - Browser test for create/edit meeting with multiple workstreams.
  - Browser test for Start Session date modal returning existing same-day session.
  - Browser test for transcript import, generate minutes, send minutes.
  - Browser test for AI suggestions review and accepted agenda persistence.

- Acceptance:
  - Run real API tests against local Supabase sample data.
  - Run real browser validation against public Hostinger domain after deploy.
  - Validate seeded users, initiatives, workstreams, meetings, agenda, attendees, sessions, action items, and minutes delivery states.

## Assumptions
- AI agenda suggestions are review-first, per user choice.
- Existing meeting series with single `workstream_id` must remain compatible.
- Session date is date-only in tenant/user local UI, stored as existing `meeting_sessions.session_date`.
- No automatic external email/calendar behavior is added beyond existing minutes delivery and Microsoft Teams scaffolding.
