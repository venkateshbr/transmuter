-- Split the legacy Operations menu into explicit operating disciplines.

BEGIN;

UPDATE tenant_dashboard_config
SET menu_group = 'financial_operations',
    updated_at = NOW()
WHERE menu_group = 'operations'
  AND dashboard_key IN (
    'benefit_tracking',
    'benefits_register',
    'bankable_plan',
    'waterline',
    'shared_costs'
  );

COMMIT;
