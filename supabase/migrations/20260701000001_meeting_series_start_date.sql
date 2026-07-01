-- Meetings V3 follow-up: explicit recurring series start boundary.

ALTER TABLE meetings
  ADD COLUMN IF NOT EXISTS series_start_date DATE;
