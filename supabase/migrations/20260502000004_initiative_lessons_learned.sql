-- Migration: Persist Initiative Summary & Results lessons learned narrative.
ALTER TABLE initiatives
ADD COLUMN IF NOT EXISTS lessons_learned TEXT;
