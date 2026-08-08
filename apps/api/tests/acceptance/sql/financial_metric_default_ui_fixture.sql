-- Idempotent development-only fixture for real browser provenance acceptance.
-- Delete through the authenticated metric API after the browser assertion.

INSERT INTO financial_metric_definitions (
  id,
  tenant_id,
  key,
  label,
  description,
  value_type,
  direction,
  aggregation,
  applies_to,
  origin,
  catalog_version,
  is_system,
  is_active,
  display_order
)
SELECT
  gen_random_uuid(),
  organization.id,
  'default_metric_ui_acceptance',
  'Default Metric UI Acceptance',
  'Reversible development fixture for the default-metric provenance badge.',
  'currency',
  'neutral',
  'sum',
  'opt_in',
  'default_catalog',
  'acceptance-fixture',
  FALSE,
  TRUE,
  99999
FROM organizations organization
WHERE organization.slug = 'acme-transformation-lab'
ON CONFLICT (tenant_id, key) DO NOTHING;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM financial_metric_definitions definition
    JOIN organizations organization ON organization.id = definition.tenant_id
    WHERE organization.slug = 'acme-transformation-lab'
      AND definition.key = 'default_metric_ui_acceptance'
      AND definition.origin = 'default_catalog'
      AND definition.catalog_version = 'acceptance-fixture'
      AND NOT definition.is_system
  ) THEN
    RAISE EXCEPTION 'Default metric UI acceptance fixture was not installed';
  END IF;
END;
$$;
