-- Roadmap Gantt scheduling semantics for milestone dependencies.

ALTER TABLE milestone_dependencies
  ADD COLUMN IF NOT EXISTS dependency_type TEXT NOT NULL DEFAULT 'finish_to_start',
  ADD COLUMN IF NOT EXISTS lag_days INTEGER NOT NULL DEFAULT 0;

ALTER TABLE milestone_dependencies
  DROP CONSTRAINT IF EXISTS milestone_dependencies_dependency_type_check,
  ADD CONSTRAINT milestone_dependencies_dependency_type_check CHECK (
    dependency_type IN (
      'finish_to_start',
      'start_to_start',
      'finish_to_finish',
      'start_to_finish'
    )
  ),
  DROP CONSTRAINT IF EXISTS milestone_dependencies_lag_days_check,
  ADD CONSTRAINT milestone_dependencies_lag_days_check CHECK (
    lag_days BETWEEN -3650 AND 3650
  );

CREATE INDEX IF NOT EXISTS milestone_dependencies_tenant_link_idx
  ON milestone_dependencies(tenant_id, upstream_milestone_id, downstream_milestone_id);

ALTER TABLE milestones
  DROP CONSTRAINT IF EXISTS milestones_planned_date_order_check,
  ADD CONSTRAINT milestones_planned_date_order_check CHECK (
    planned_start IS NULL OR planned_end IS NULL OR planned_start <= planned_end
  ) NOT VALID;

-- Enforce that both dependency endpoints belong to the active tenant even when
-- a caller writes directly through the tenant-scoped Supabase API.
DROP POLICY IF EXISTS "deps_insert" ON milestone_dependencies;
CREATE POLICY "deps_insert" ON milestone_dependencies FOR INSERT WITH CHECK (
  tenant_id = current_tenant_id()
  AND EXISTS (
    SELECT 1 FROM milestones upstream
    WHERE upstream.id = upstream_milestone_id
      AND upstream.tenant_id = current_tenant_id()
  )
  AND EXISTS (
    SELECT 1 FROM milestones downstream
    WHERE downstream.id = downstream_milestone_id
      AND downstream.tenant_id = current_tenant_id()
  )
);
