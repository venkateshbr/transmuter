-- Allow tenant-configured initiative tags.
--
-- The application reads tags from organization.settings.strategic_parameters.tags.
-- A legacy fixed-value check constraint blocked those configurable values at write time.
alter table public.initiatives
  drop constraint if exists initiatives_tag_check;
