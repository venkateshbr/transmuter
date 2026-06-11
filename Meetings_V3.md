# Meetings V3

## Product Decisions

- Store one-off meetings as backend recurrence value `ad_hoc` and display them as `One-off`.
- Interpret bimonthly as every two weeks and display it as `Biweekly`.
- Meeting-level Microsoft Teams invite sync creates a recurring Microsoft Graph series when a recurring meeting has `series_end_date`; session-level sync creates one Microsoft Teams event per dated session.
- Treat series agenda and participants as defaults only. Dated sessions snapshot their own agenda and attendees when generated or opened.
- Capture `day_of_week`, `start_time`, `timezone`, `duration_minutes`, `one_off_date`, and `series_end_date`. Default duration is 60 minutes.
- Use post-meeting Microsoft transcript sync for V3 Teams notes. Real-time Teams transcription is deferred.

## Backend Scope

- `MeetingCreate` and `MeetingUpdate` accept schedule fields, participant user IDs, and default agenda items.
- Meeting detail includes `sessions_window`, a generated rolling window of the last 3 and next 3 sessions around an anchor date.
- `GET /meetings/{meeting_id}/sessions` pages that window with `anchor_date` and `page_size`.
- Session agenda endpoints operate on session snapshots:
  - `POST /meetings/sessions/{session_id}/agenda`
  - `PUT /meetings/sessions/{session_id}/agenda/{item_id}`
  - `DELETE /meetings/sessions/{session_id}/agenda/{item_id}`
  - `POST /meetings/sessions/{session_id}/agenda/suggestions`
- Session attendee endpoints operate on session snapshots:
  - `POST /meetings/sessions/{session_id}/attendees`
  - `DELETE /meetings/sessions/{session_id}/attendees/{attendee_id}`
- Microsoft Teams invite sync supports session-specific rows through:
  - `POST /meetings/sessions/{session_id}/external-events/microsoft`
- Transcript sync now prefers the session-specific Microsoft event and falls back to legacy series rows.

## Schema Scope

- Added schedule columns to `meetings`.
- Added scheduled start/end columns to `meeting_sessions`.
- Added tenant-scoped RLS tables for `meeting_session_agenda_items` and `meeting_session_attendees`.
- Added nullable `session_id` to `meeting_external_events`, preserving legacy series-level rows while allowing per-session uniqueness.

## Frontend Scope

- Meetings list displays real recurrence and schedule metadata.
- New series modal captures cadence/date, time, duration, timezone, participants, and default agenda.
- Meeting detail shows default agenda, default participants, and a rolling Sessions window with previous/next controls.
- Session page supports pre-start setup for session agenda, attendees, AI agenda suggestions, and per-session Teams invite sync.
- Live session continues to support notes, artifacts/actions, minutes, transcript import, Teams join links, and Microsoft transcript sync.

## Required Review

Prahari review remains required because this touches Microsoft Graph, token-backed integrations, transcript data, tenant-scoped RLS, and external event persistence.
