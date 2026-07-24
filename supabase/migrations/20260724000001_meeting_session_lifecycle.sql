-- Preserve session-specific agenda/attendee choices and record actual lifecycle times.

ALTER TABLE meeting_sessions
  ADD COLUMN IF NOT EXISTS agenda_customized BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS attendees_customized BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
