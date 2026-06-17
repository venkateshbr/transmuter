DROP POLICY IF EXISTS "fblve_insert" ON financial_benefit_line_validation_events;

CREATE POLICY "fblve_insert"
  ON financial_benefit_line_validation_events
  FOR INSERT
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'transformation_office'
    AND EXISTS (
      SELECT 1
      FROM financial_benefit_lines line
      WHERE line.id = benefit_line_id
        AND line.tenant_id = current_tenant_id()
        AND line.initiative_id = financial_benefit_line_validation_events.initiative_id
    )
  );
