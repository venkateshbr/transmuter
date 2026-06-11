-- Meetings V3 follow-up: bounded recurring series support.

ALTER TABLE meetings
  ADD COLUMN IF NOT EXISTS series_end_date DATE;
