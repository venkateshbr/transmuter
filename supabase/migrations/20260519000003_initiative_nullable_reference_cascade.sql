-- Migration: ensure initiative delete cascades for nullable meeting task references

ALTER TABLE agenda_items
  DROP CONSTRAINT IF EXISTS agenda_items_initiative_id_fkey,
  ADD CONSTRAINT agenda_items_initiative_id_fkey
  FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;

ALTER TABLE action_items
  DROP CONSTRAINT IF EXISTS action_items_initiative_id_fkey,
  ADD CONSTRAINT action_items_initiative_id_fkey
  FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
