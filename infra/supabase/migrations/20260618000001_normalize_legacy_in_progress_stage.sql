UPDATE initiatives initiative
SET stage = 'executing',
    updated_at = NOW()
WHERE initiative.stage = 'in_progress'
  AND EXISTS (
    SELECT 1
    FROM stage_gate_definitions gate
    WHERE gate.tenant_id = initiative.tenant_id
      AND gate.is_active IS TRUE
      AND (gate.from_stage = 'executing' OR gate.to_stage = 'executing')
  );
