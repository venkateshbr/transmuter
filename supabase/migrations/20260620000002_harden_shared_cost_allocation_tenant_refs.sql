-- Harden Shared Costs tenant isolation by replacing id-only references with
-- composite tenant-scoped foreign keys.

CREATE UNIQUE INDEX IF NOT EXISTS shared_cost_pools_tenant_id_id_uidx
  ON shared_cost_pools(tenant_id, id);

CREATE UNIQUE INDEX IF NOT EXISTS shared_cost_allocation_rules_tenant_id_id_uidx
  ON shared_cost_allocation_rules(tenant_id, id);

CREATE UNIQUE INDEX IF NOT EXISTS shared_cost_allocation_runs_tenant_id_id_uidx
  ON shared_cost_allocation_runs(tenant_id, id);

ALTER TABLE shared_cost_allocation_rules
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_rules_pool_id_fkey;

ALTER TABLE shared_cost_allocation_runs
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_runs_pool_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_runs_rule_id_fkey;

ALTER TABLE shared_cost_allocations
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_run_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_pool_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_rule_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocations_initiative_id_fkey;

ALTER TABLE shared_cost_pool_periods
  DROP CONSTRAINT IF EXISTS shared_cost_pool_periods_pool_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_pool_periods_scenario_id_fkey;

ALTER TABLE shared_cost_allocation_targets
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_targets_rule_id_fkey;

ALTER TABLE shared_cost_allocation_weights
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_weights_rule_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_weights_initiative_id_fkey;

ALTER TABLE shared_cost_allocation_exceptions
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_exceptions_run_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_exceptions_rule_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_exceptions_pool_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_exceptions_initiative_id_fkey;

ALTER TABLE shared_cost_allocation_audit_events
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_audit_events_pool_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_audit_events_rule_id_fkey,
  DROP CONSTRAINT IF EXISTS shared_cost_allocation_audit_events_run_id_fkey;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_rules_pool_tenant_fk'
      AND conrelid = 'shared_cost_allocation_rules'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_rules
      ADD CONSTRAINT shared_cost_rules_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_runs_pool_tenant_fk'
      AND conrelid = 'shared_cost_allocation_runs'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_runs
      ADD CONSTRAINT shared_cost_runs_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_runs_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocation_runs'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_runs
      ADD CONSTRAINT shared_cost_runs_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_allocations_run_tenant_fk'
      AND conrelid = 'shared_cost_allocations'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocations
      ADD CONSTRAINT shared_cost_allocations_run_tenant_fk
      FOREIGN KEY (tenant_id, run_id)
      REFERENCES shared_cost_allocation_runs(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_allocations_pool_tenant_fk'
      AND conrelid = 'shared_cost_allocations'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocations
      ADD CONSTRAINT shared_cost_allocations_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_allocations_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocations'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocations
      ADD CONSTRAINT shared_cost_allocations_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_allocations_initiative_tenant_fk'
      AND conrelid = 'shared_cost_allocations'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocations
      ADD CONSTRAINT shared_cost_allocations_initiative_tenant_fk
      FOREIGN KEY (tenant_id, initiative_id)
      REFERENCES initiatives(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_pool_periods_pool_tenant_fk'
      AND conrelid = 'shared_cost_pool_periods'::regclass
  ) THEN
    ALTER TABLE shared_cost_pool_periods
      ADD CONSTRAINT shared_cost_pool_periods_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_pool_periods_scenario_tenant_fk'
      AND conrelid = 'shared_cost_pool_periods'::regclass
  ) THEN
    ALTER TABLE shared_cost_pool_periods
      ADD CONSTRAINT shared_cost_pool_periods_scenario_tenant_fk
      FOREIGN KEY (tenant_id, scenario_id)
      REFERENCES financial_scenarios(tenant_id, id)
      ON DELETE SET NULL (scenario_id);
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_targets_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocation_targets'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_targets
      ADD CONSTRAINT shared_cost_targets_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_weights_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocation_weights'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_weights
      ADD CONSTRAINT shared_cost_weights_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_weights_initiative_tenant_fk'
      AND conrelid = 'shared_cost_allocation_weights'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_weights
      ADD CONSTRAINT shared_cost_weights_initiative_tenant_fk
      FOREIGN KEY (tenant_id, initiative_id)
      REFERENCES initiatives(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_exceptions_run_tenant_fk'
      AND conrelid = 'shared_cost_allocation_exceptions'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_exceptions
      ADD CONSTRAINT shared_cost_exceptions_run_tenant_fk
      FOREIGN KEY (tenant_id, run_id)
      REFERENCES shared_cost_allocation_runs(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_exceptions_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocation_exceptions'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_exceptions
      ADD CONSTRAINT shared_cost_exceptions_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_exceptions_pool_tenant_fk'
      AND conrelid = 'shared_cost_allocation_exceptions'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_exceptions
      ADD CONSTRAINT shared_cost_exceptions_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_exceptions_initiative_tenant_fk'
      AND conrelid = 'shared_cost_allocation_exceptions'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_exceptions
      ADD CONSTRAINT shared_cost_exceptions_initiative_tenant_fk
      FOREIGN KEY (tenant_id, initiative_id)
      REFERENCES initiatives(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_audit_pool_tenant_fk'
      AND conrelid = 'shared_cost_allocation_audit_events'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_audit_events
      ADD CONSTRAINT shared_cost_audit_pool_tenant_fk
      FOREIGN KEY (tenant_id, pool_id)
      REFERENCES shared_cost_pools(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_audit_rule_tenant_fk'
      AND conrelid = 'shared_cost_allocation_audit_events'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_audit_events
      ADD CONSTRAINT shared_cost_audit_rule_tenant_fk
      FOREIGN KEY (tenant_id, rule_id)
      REFERENCES shared_cost_allocation_rules(tenant_id, id)
      ON DELETE CASCADE;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'shared_cost_audit_run_tenant_fk'
      AND conrelid = 'shared_cost_allocation_audit_events'::regclass
  ) THEN
    ALTER TABLE shared_cost_allocation_audit_events
      ADD CONSTRAINT shared_cost_audit_run_tenant_fk
      FOREIGN KEY (tenant_id, run_id)
      REFERENCES shared_cost_allocation_runs(tenant_id, id)
      ON DELETE CASCADE;
  END IF;
END $$;

CREATE OR REPLACE FUNCTION shared_cost_validate_tenant_refs()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_TABLE_NAME = 'shared_cost_pools' THEN
    IF NEW.owner_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.owner_id
    ) THEN
      RAISE EXCEPTION 'shared_cost_pools.owner_id must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
    IF NEW.locked_by IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.locked_by
    ) THEN
      RAISE EXCEPTION 'shared_cost_pools.locked_by must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
  ELSIF TG_TABLE_NAME = 'shared_cost_allocation_runs' THEN
    IF NEW.created_by IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.created_by
    ) THEN
      RAISE EXCEPTION 'shared_cost_allocation_runs.created_by must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
    IF NEW.approved_by IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.approved_by
    ) THEN
      RAISE EXCEPTION 'shared_cost_allocation_runs.approved_by must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
    IF NEW.locked_by IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.locked_by
    ) THEN
      RAISE EXCEPTION 'shared_cost_allocation_runs.locked_by must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
  ELSIF TG_TABLE_NAME = 'shared_cost_allocation_audit_events' THEN
    IF NEW.actor_id IS NOT NULL AND NOT EXISTS (
      SELECT 1 FROM users u WHERE u.tenant_id = NEW.tenant_id AND u.id = NEW.actor_id
    ) THEN
      RAISE EXCEPTION 'shared_cost_allocation_audit_events.actor_id must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
  ELSIF TG_TABLE_NAME = 'shared_cost_allocations' THEN
    IF NEW.posted_cost_line_id IS NOT NULL AND NOT EXISTS (
      SELECT 1
      FROM financial_cost_lines line
      WHERE line.tenant_id = NEW.tenant_id
        AND line.id = NEW.posted_cost_line_id
    ) THEN
      RAISE EXCEPTION 'shared_cost_allocations.posted_cost_line_id must belong to the same tenant'
        USING ERRCODE = '23503';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS shared_cost_pools_user_tenant_refs_biur ON shared_cost_pools;
CREATE TRIGGER shared_cost_pools_user_tenant_refs_biur
  BEFORE INSERT OR UPDATE OF tenant_id, owner_id, locked_by ON shared_cost_pools
  FOR EACH ROW EXECUTE FUNCTION shared_cost_validate_tenant_refs();

DROP TRIGGER IF EXISTS shared_cost_runs_user_tenant_refs_biur ON shared_cost_allocation_runs;
CREATE TRIGGER shared_cost_runs_user_tenant_refs_biur
  BEFORE INSERT OR UPDATE OF tenant_id, created_by, approved_by, locked_by
  ON shared_cost_allocation_runs
  FOR EACH ROW EXECUTE FUNCTION shared_cost_validate_tenant_refs();

DROP TRIGGER IF EXISTS shared_cost_audit_user_tenant_refs_biur
  ON shared_cost_allocation_audit_events;
CREATE TRIGGER shared_cost_audit_user_tenant_refs_biur
  BEFORE INSERT OR UPDATE OF tenant_id, actor_id ON shared_cost_allocation_audit_events
  FOR EACH ROW EXECUTE FUNCTION shared_cost_validate_tenant_refs();

DROP TRIGGER IF EXISTS shared_cost_allocations_posted_line_tenant_refs_biur
  ON shared_cost_allocations;
CREATE TRIGGER shared_cost_allocations_posted_line_tenant_refs_biur
  BEFORE INSERT OR UPDATE OF tenant_id, posted_cost_line_id ON shared_cost_allocations
  FOR EACH ROW EXECUTE FUNCTION shared_cost_validate_tenant_refs();

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM shared_cost_pools row
    WHERE (row.owner_id IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.owner_id
      ))
      OR (row.locked_by IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.locked_by
      ))
  ) THEN
    RAISE EXCEPTION 'shared_cost_pools contains cross-tenant user references'
      USING ERRCODE = '23503';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM shared_cost_allocation_runs row
    WHERE (row.created_by IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.created_by
      ))
      OR (row.approved_by IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.approved_by
      ))
      OR (row.locked_by IS NOT NULL AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.locked_by
      ))
  ) THEN
    RAISE EXCEPTION 'shared_cost_allocation_runs contains cross-tenant user references'
      USING ERRCODE = '23503';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM shared_cost_allocation_audit_events row
    WHERE row.actor_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM users u WHERE u.tenant_id = row.tenant_id AND u.id = row.actor_id
      )
  ) THEN
    RAISE EXCEPTION 'shared_cost_allocation_audit_events contains cross-tenant user references'
      USING ERRCODE = '23503';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM shared_cost_allocations row
    WHERE row.posted_cost_line_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1
        FROM financial_cost_lines line
        WHERE line.tenant_id = row.tenant_id
          AND line.id = row.posted_cost_line_id
      )
  ) THEN
    RAISE EXCEPTION 'shared_cost_allocations contains cross-tenant posted cost line references'
      USING ERRCODE = '23503';
  END IF;
END $$;
