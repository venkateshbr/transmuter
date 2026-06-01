-- Pilot seed data for a self-hosted/local Supabase Transmuter instance.
--
-- Run after applying all database migrations and after exposing the `transmuter`
-- schema through Supabase REST/PostgREST.
--
-- Example:
--   psql "$TARGET_DATABASE_URL" -v ON_ERROR_STOP=1 \
--     -f scripts/pilot/202606010001_seed_pilot_data.sql
--
-- Default seeded login:
--   admin@ishirock.dev / Transmuter2026!
--
-- The script is intentionally idempotent. Re-running it refreshes the pilot
-- tenant dataset without touching any other tenant.

\set ON_ERROR_STOP on

BEGIN;

CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA extensions;

SET search_path = transmuter, public, extensions;

DO $$
DECLARE
  pilot_tenant_id CONSTANT uuid := '11111111-1111-4111-8111-111111111111';
  admin_user_id CONSTANT uuid := '11111111-1111-4111-8111-111111111101';
  owner_user_id CONSTANT uuid := '11111111-1111-4111-8111-111111111102';
  viewer_user_id CONSTANT uuid := '11111111-1111-4111-8111-111111111103';
  finance_user_id CONSTANT uuid := '11111111-1111-4111-8111-111111111104';
  risk_user_id CONSTANT uuid := '11111111-1111-4111-8111-111111111105';

  bu_ops_id CONSTANT uuid := '11111111-1111-4111-8111-111111112001';
  bu_growth_id CONSTANT uuid := '11111111-1111-4111-8111-111111112002';
  bu_finance_id CONSTANT uuid := '11111111-1111-4111-8111-111111112003';

  ws_ops_id CONSTANT uuid := '11111111-1111-4111-8111-111111113001';
  ws_growth_id CONSTANT uuid := '11111111-1111-4111-8111-111111113002';
  ws_finance_id CONSTANT uuid := '11111111-1111-4111-8111-111111113003';
  ws_people_id CONSTANT uuid := '11111111-1111-4111-8111-111111113004';

  init_rev_asia_id CONSTANT uuid := '11111111-1111-4111-8111-111111114001';
  init_ap_auto_id CONSTANT uuid := '11111111-1111-4111-8111-111111114002';
  init_procure_id CONSTANT uuid := '11111111-1111-4111-8111-111111114003';
  init_workforce_id CONSTANT uuid := '11111111-1111-4111-8111-111111114004';
  init_controls_id CONSTANT uuid := '11111111-1111-4111-8111-111111114005';

  ms_rev_pilot_id CONSTANT uuid := '11111111-1111-4111-8111-111111115001';
  ms_rev_scale_id CONSTANT uuid := '11111111-1111-4111-8111-111111115002';
  ms_ap_baseline_id CONSTANT uuid := '11111111-1111-4111-8111-111111115003';
  ms_ap_erp_id CONSTANT uuid := '11111111-1111-4111-8111-111111115004';
  ms_procure_wave_id CONSTANT uuid := '11111111-1111-4111-8111-111111115005';
  ms_workforce_launch_id CONSTANT uuid := '11111111-1111-4111-8111-111111115006';

  mtg_steer_id CONSTANT uuid := '11111111-1111-4111-8111-111111116001';
  mtg_north_asia_id CONSTANT uuid := '11111111-1111-4111-8111-111111116002';
  sess_steer_id CONSTANT uuid := '11111111-1111-4111-8111-111111117001';
  sess_north_asia_id CONSTANT uuid := '11111111-1111-4111-8111-111111117002';

  action_erp_id CONSTANT uuid := '11111111-1111-4111-8111-111111118001';
  action_korea_id CONSTANT uuid := '11111111-1111-4111-8111-111111118002';

  shared_pool_id CONSTANT uuid := '11111111-1111-4111-8111-111111119001';
  shared_rule_id CONSTANT uuid := '11111111-1111-4111-8111-111111119002';
  shared_run_id CONSTANT uuid := '11111111-1111-4111-8111-111111119003';

  auth_has_provider_id boolean;
BEGIN
  -- Clean and rebuild only the deterministic pilot tenant. This keeps the seed
  -- predictable for browser/API acceptance without risking other tenants.
  DELETE FROM shared_cost_allocations WHERE tenant_id = pilot_tenant_id;
  DELETE FROM shared_cost_allocation_runs WHERE tenant_id = pilot_tenant_id;
  DELETE FROM shared_cost_allocation_rules WHERE tenant_id = pilot_tenant_id;
  DELETE FROM shared_cost_pools WHERE tenant_id = pilot_tenant_id;
  DELETE FROM initiative_value_realization_notes WHERE tenant_id = pilot_tenant_id;
  DELETE FROM initiative_dependencies WHERE tenant_id = pilot_tenant_id;
  DELETE FROM meeting_artifacts WHERE tenant_id = pilot_tenant_id;
  DELETE FROM action_items WHERE tenant_id = pilot_tenant_id;
  DELETE FROM agenda_items WHERE tenant_id = pilot_tenant_id;
  DELETE FROM meeting_sessions WHERE tenant_id = pilot_tenant_id;
  DELETE FROM meeting_initiatives WHERE tenant_id = pilot_tenant_id;
  DELETE FROM meeting_attendees WHERE tenant_id = pilot_tenant_id;
  DELETE FROM meetings WHERE tenant_id = pilot_tenant_id;
  DELETE FROM status_updates WHERE tenant_id = pilot_tenant_id;
  DELETE FROM financial_metric_values WHERE tenant_id = pilot_tenant_id;
  DELETE FROM initiative_financial_selections WHERE tenant_id = pilot_tenant_id;
  DELETE FROM financial_cost_lines WHERE tenant_id = pilot_tenant_id;
  DELETE FROM financial_entries WHERE tenant_id = pilot_tenant_id;
  DELETE FROM risks WHERE tenant_id = pilot_tenant_id;
  DELETE FROM kpi_entries WHERE tenant_id = pilot_tenant_id;
  DELETE FROM kpis WHERE tenant_id = pilot_tenant_id;
  DELETE FROM milestone_dependencies WHERE tenant_id = pilot_tenant_id;
  DELETE FROM milestones WHERE tenant_id = pilot_tenant_id;
  DELETE FROM initiative_team WHERE tenant_id = pilot_tenant_id;
  DELETE FROM initiatives WHERE tenant_id = pilot_tenant_id;
  DELETE FROM user_workstreams WHERE tenant_id = pilot_tenant_id;
  DELETE FROM workstreams WHERE tenant_id = pilot_tenant_id;
  DELETE FROM business_units WHERE tenant_id = pilot_tenant_id;
  DELETE FROM financial_config_items WHERE tenant_id = pilot_tenant_id;
  DELETE FROM financial_config_groups WHERE tenant_id = pilot_tenant_id;
  DELETE FROM tenant_subscriptions WHERE tenant_id = pilot_tenant_id;
  DELETE FROM signup_intents WHERE tenant_id = pilot_tenant_id;
  DELETE FROM subscription_plans WHERE tenant_id = pilot_tenant_id;
  DELETE FROM users WHERE tenant_id = pilot_tenant_id;
  DELETE FROM organizations WHERE id = pilot_tenant_id;

  -- Supabase Auth users for the pilot login personas.
  INSERT INTO auth.users (
    instance_id,
    id,
    aud,
    role,
    email,
    encrypted_password,
    email_confirmed_at,
    raw_app_meta_data,
    raw_user_meta_data,
    created_at,
    updated_at,
    confirmation_token,
    email_change,
    email_change_token_new,
    recovery_token
  )
  VALUES
    ('00000000-0000-0000-0000-000000000000', admin_user_id, 'authenticated', 'authenticated', 'admin@ishirock.dev', extensions.crypt('Transmuter2026!', extensions.gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}'::jsonb, '{"display_name":"Vishwa Rao"}'::jsonb, NOW(), NOW(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', owner_user_id, 'authenticated', 'authenticated', 'owner@ishirock.dev', extensions.crypt('Transmuter2026!', extensions.gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}'::jsonb, '{"display_name":"Rupa Menon"}'::jsonb, NOW(), NOW(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', viewer_user_id, 'authenticated', 'authenticated', 'viewer@ishirock.dev', extensions.crypt('Transmuter2026!', extensions.gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}'::jsonb, '{"display_name":"Aksha Shah"}'::jsonb, NOW(), NOW(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', finance_user_id, 'authenticated', 'authenticated', 'finance@ishirock.dev', extensions.crypt('Transmuter2026!', extensions.gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}'::jsonb, '{"display_name":"Dhruva Iyer"}'::jsonb, NOW(), NOW(), '', '', '', ''),
    ('00000000-0000-0000-0000-000000000000', risk_user_id, 'authenticated', 'authenticated', 'risk@ishirock.dev', extensions.crypt('Transmuter2026!', extensions.gen_salt('bf')), NOW(), '{"provider":"email","providers":["email"]}'::jsonb, '{"display_name":"Prahari Singh"}'::jsonb, NOW(), NOW(), '', '', '', '')
  ON CONFLICT (id) DO UPDATE SET
    email = EXCLUDED.email,
    encrypted_password = EXCLUDED.encrypted_password,
    email_confirmed_at = EXCLUDED.email_confirmed_at,
    raw_app_meta_data = EXCLUDED.raw_app_meta_data,
    raw_user_meta_data = EXCLUDED.raw_user_meta_data,
    updated_at = NOW();

  SELECT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'auth'
      AND table_name = 'identities'
      AND column_name = 'provider_id'
  )
  INTO auth_has_provider_id;

  IF auth_has_provider_id THEN
    INSERT INTO auth.identities (
      id,
      user_id,
      identity_data,
      provider,
      provider_id,
      last_sign_in_at,
      created_at,
      updated_at
    )
    SELECT
      seeded.id::text,
      seeded.id,
      jsonb_build_object('sub', seeded.id::text, 'email', seeded.email, 'email_verified', true),
      'email',
      seeded.email,
      NOW(),
      NOW(),
      NOW()
    FROM (
      VALUES
        (admin_user_id, 'admin@ishirock.dev'),
        (owner_user_id, 'owner@ishirock.dev'),
        (viewer_user_id, 'viewer@ishirock.dev'),
        (finance_user_id, 'finance@ishirock.dev'),
        (risk_user_id, 'risk@ishirock.dev')
    ) AS seeded(id, email)
    ON CONFLICT DO NOTHING;
  ELSE
    INSERT INTO auth.identities (
      id,
      user_id,
      identity_data,
      provider,
      last_sign_in_at,
      created_at,
      updated_at
    )
    SELECT
      seeded.id::text,
      seeded.id,
      jsonb_build_object('sub', seeded.id::text, 'email', seeded.email, 'email_verified', true),
      'email',
      NOW(),
      NOW(),
      NOW()
    FROM (
      VALUES
        (admin_user_id, 'admin@ishirock.dev'),
        (owner_user_id, 'owner@ishirock.dev'),
        (viewer_user_id, 'viewer@ishirock.dev'),
        (finance_user_id, 'finance@ishirock.dev'),
        (risk_user_id, 'risk@ishirock.dev')
    ) AS seeded(id, email)
    ON CONFLICT DO NOTHING;
  END IF;

  INSERT INTO organizations (id, name, slug, settings)
  VALUES (
    pilot_tenant_id,
    'Ishirock Pilot Transformation Office',
    'ishirock-pilot',
    '{"pilot":true,"target_year":2026,"currency":"USD"}'::jsonb
  );

  INSERT INTO subscription_plans (
    id,
    tenant_id,
    code,
    name,
    user_limit_min,
    user_limit_max,
    amount_cents,
    currency,
    billing_interval,
    is_active
  )
  VALUES (
    '11111111-1111-4111-8111-111111119501',
    pilot_tenant_id,
    'business',
    'Pilot Business',
    1,
    100,
    0,
    'usd',
    'custom',
    TRUE
  );

  INSERT INTO tenant_subscriptions (
    id,
    tenant_id,
    plan_id,
    provider,
    status,
    checkout_status,
    payment_status,
    planned_user_count,
    metadata
  )
  VALUES (
    '11111111-1111-4111-8111-111111119502',
    pilot_tenant_id,
    '11111111-1111-4111-8111-111111119501',
    'stripe',
    'active',
    'seeded',
    'paid',
    25,
    '{"pilot_seed":true}'::jsonb
  );

  INSERT INTO users (
    id,
    tenant_id,
    email,
    display_name,
    title,
    department,
    market,
    timezone,
    role,
    status,
    onboarding_completed
  )
  VALUES
    (admin_user_id, pilot_tenant_id, 'admin@ishirock.dev', 'Vishwa Rao', 'Transformation Office Lead', 'Transformation Office', 'Singapore', 'Asia/Singapore', 'transformation_office', 'active', TRUE),
    (owner_user_id, pilot_tenant_id, 'owner@ishirock.dev', 'Rupa Menon', 'Commercial Workstream Owner', 'Growth', 'Singapore', 'Asia/Singapore', 'initiative_owner', 'active', TRUE),
    (viewer_user_id, pilot_tenant_id, 'viewer@ishirock.dev', 'Aksha Shah', 'Executive Sponsor', 'Executive Office', 'Singapore', 'Asia/Singapore', 'viewer', 'active', TRUE),
    (finance_user_id, pilot_tenant_id, 'finance@ishirock.dev', 'Dhruva Iyer', 'Finance Controller', 'Finance', 'Singapore', 'Asia/Singapore', 'transformation_office', 'active', TRUE),
    (risk_user_id, pilot_tenant_id, 'risk@ishirock.dev', 'Prahari Singh', 'Risk Lead', 'Risk', 'Singapore', 'Asia/Singapore', 'transformation_office', 'active', TRUE);

  INSERT INTO business_units (id, tenant_id, name, code)
  VALUES
    (bu_ops_id, pilot_tenant_id, 'Operations', 'OPS'),
    (bu_growth_id, pilot_tenant_id, 'Growth', 'GRO'),
    (bu_finance_id, pilot_tenant_id, 'Finance', 'FIN');

  INSERT INTO workstreams (id, tenant_id, business_unit_id, name)
  VALUES
    (ws_ops_id, pilot_tenant_id, bu_ops_id, 'Operations Excellence'),
    (ws_growth_id, pilot_tenant_id, bu_growth_id, 'Commercial Growth'),
    (ws_finance_id, pilot_tenant_id, bu_finance_id, 'Finance Transformation'),
    (ws_people_id, pilot_tenant_id, bu_ops_id, 'People and Change');

  INSERT INTO user_workstreams (tenant_id, user_id, workstream_id)
  VALUES
    (pilot_tenant_id, admin_user_id, ws_ops_id),
    (pilot_tenant_id, admin_user_id, ws_growth_id),
    (pilot_tenant_id, owner_user_id, ws_growth_id),
    (pilot_tenant_id, finance_user_id, ws_finance_id),
    (pilot_tenant_id, risk_user_id, ws_ops_id)
  ON CONFLICT (user_id, workstream_id) DO NOTHING;

  INSERT INTO financial_config_groups (tenant_id, key, label, kind, rollup_type, display_order, is_system)
  VALUES
    (pilot_tenant_id, 'benefits', 'Total Benefits', 'calculation', 'benefit', 10, TRUE),
    (pilot_tenant_id, 'recurring_costs', 'Recurring Costs', 'calculation', 'recurring_cost', 20, TRUE),
    (pilot_tenant_id, 'one_off_costs', 'One-off Costs', 'calculation', 'one_off_cost', 30, TRUE),
    (pilot_tenant_id, 'net_value', 'Net Run-rate Impact', 'calculation', 'net_value', 40, TRUE),
    (pilot_tenant_id, 'payback_period', 'Payback Period', 'calculation', NULL, 50, TRUE),
    (pilot_tenant_id, 'revenue', 'Revenue', 'metric', NULL, 10, TRUE),
    (pilot_tenant_id, 'gross_margin', 'Gross Margin', 'metric', NULL, 20, TRUE),
    (pilot_tenant_id, 'savings', 'Savings', 'metric', NULL, 30, TRUE),
    (pilot_tenant_id, 'implementation', 'One-off Costs', 'cost_category', NULL, 10, TRUE),
    (pilot_tenant_id, 'operating', 'Recurring Costs', 'cost_category', NULL, 20, TRUE),
    (pilot_tenant_id, 'uncategorized', 'Uncategorized', 'cost_category', NULL, 99, TRUE);

  INSERT INTO financial_config_items (
    tenant_id,
    group_id,
    key,
    label,
    item_type,
    system_metric_key,
    rollup_type,
    display_order,
    is_system
  )
  SELECT pilot_tenant_id, grp.id, item.key, item.label, item.item_type, item.system_metric_key, item.rollup_type, item.display_order, TRUE
  FROM financial_config_groups grp
  JOIN (
    VALUES
      ('revenue', 'revenue_uplift_base', 'Revenue Uplift ($) (Base)', 'metric', 'revenue_uplift_base', 'benefit', 10),
      ('revenue', 'revenue_uplift_actual', 'Revenue Uplift ($) (Actual)', 'metric', 'revenue_uplift_actual', 'benefit', 20),
      ('gross_margin', 'gm_uplift_base', 'Gross Margin Uplift ($) (Base)', 'metric', 'gm_uplift_base', 'benefit', 30),
      ('gross_margin', 'gm_uplift_actual', 'Gross Margin Uplift ($) (Actual)', 'metric', 'gm_uplift_actual', 'benefit', 40),
      ('savings', 'cost_savings', 'Cost Savings ($)', 'metric', NULL, 'benefit', 50),
      ('implementation', 'implementation', 'Implementation / Project Cost', 'cost_category', NULL, 'one_off_cost', 10),
      ('implementation', 'other_one_off', 'Other One-off Cost', 'cost_category', NULL, 'one_off_cost', 90),
      ('operating', 'software_subscriptions', 'Software Subscriptions', 'cost_category', NULL, 'recurring_cost', 20),
      ('operating', 'support_maintenance', 'Support / Maintenance', 'cost_category', NULL, 'recurring_cost', 30),
      ('operating', 'labor', 'Labor / Operations', 'cost_category', NULL, 'recurring_cost', 40),
      ('uncategorized', 'other', 'Other', 'cost_category', NULL, NULL, 99)
  ) AS item(group_key, key, label, item_type, system_metric_key, rollup_type, display_order)
    ON item.group_key = grp.key
  WHERE grp.tenant_id = pilot_tenant_id;

  INSERT INTO initiatives (
    id,
    tenant_id,
    initiative_code,
    name,
    workstream_id,
    owner_id,
    group_owner_id,
    type,
    impact_type,
    theme,
    country,
    tag,
    priority,
    rag_status,
    stage,
    summary,
    value_logic,
    dependencies_text,
    planned_start,
    actual_start,
    planned_end,
    pressure_score,
    benefit_confidence,
    realization_status,
    variance_explanation
  )
  VALUES
    (init_rev_asia_id, pilot_tenant_id, 'TRN-001', 'North Asia Commercial Lift', ws_growth_id, owner_user_id, admin_user_id, 'revenue_growth', 'recurring', 'Commercial acceleration', 'Japan', 'commercial', 'high', 'green', 'in_progress', 'Japan pilot and Korea scale-up to improve win rate and gross margin on strategic accounts.', 'Commercial playbook adoption increases qualified conversion and GM uplift.', 'Korea launch depends on pricing governance readiness.', '2026-01-15', '2026-01-20', '2026-09-30', 7.2, 82.50, 'partially_realized', 'Japan wave is ahead of plan; Korea requires final pricing governance.'),
    (init_ap_auto_id, pilot_tenant_id, 'TRN-002', 'AP Automation and Cycle-Time Reduction', ws_ops_id, finance_user_id, admin_user_id, 'cost_reduction', 'recurring', 'Process automation', 'Singapore', 'automation', 'high', 'amber', 'in_progress', 'Automate invoice ingestion, approval routing, and exception handling across the regional finance hub.', 'Lower processing effort and fewer payment defects reduce operating cost.', 'ERP integration completion gates scale deployment.', '2026-02-01', '2026-02-08', '2026-10-31', 8.6, 68.00, 'forecasted', 'ERP integration delay is creating timing risk.'),
    (init_procure_id, pilot_tenant_id, 'TRN-003', 'Procurement Wave 2 Vendor Consolidation', ws_finance_id, finance_user_id, admin_user_id, 'cost_reduction', 'recurring', 'Spend productivity', 'Singapore', 'other', 'medium', 'green', 'scoping', 'Consolidate long-tail vendors and renegotiate strategic supplier terms.', 'Savings are captured through recurring vendor-rate reductions.', 'Requires finance sign-off on category baselines.', '2026-03-01', NULL, '2026-12-15', 5.8, 61.00, 'forecasted', NULL),
    (init_workforce_id, pilot_tenant_id, 'TRN-004', 'Shared Services Workforce Transition', ws_people_id, risk_user_id, admin_user_id, 'capability_building', 'one_off', 'Operating model', 'Philippines', 'offshoring', 'medium', 'red', 'in_progress', 'Move repeatable back-office work into a governed shared services model.', 'Capacity release is tracked through role migration and SLA stabilization.', 'Labor consultation and training calendar are on the critical path.', '2026-01-01', '2026-01-10', '2026-08-31', 9.1, 45.00, 'at_risk', 'People risk and training delays require steering decision.'),
    (init_controls_id, pilot_tenant_id, 'TRN-005', 'Regulatory Controls Evidence Uplift', ws_ops_id, risk_user_id, admin_user_id, 'compliance', 'one_off', 'Controls', 'Singapore', 'other', 'low', 'green', 'complete', 'Standardize control evidence collection and monthly review cadence.', 'Avoided remediation and audit readiness are measured through control evidence completion.', 'No active dependency.', '2025-10-01', '2025-10-03', '2026-03-31', 3.4, 90.00, 'realized', 'Benefits realized through reduced audit preparation effort.');

  INSERT INTO initiative_team (tenant_id, initiative_id, user_id, role)
  VALUES
    (pilot_tenant_id, init_rev_asia_id, owner_user_id, 'owner'),
    (pilot_tenant_id, init_rev_asia_id, admin_user_id, 'reviewer'),
    (pilot_tenant_id, init_ap_auto_id, finance_user_id, 'owner'),
    (pilot_tenant_id, init_procure_id, finance_user_id, 'owner'),
    (pilot_tenant_id, init_workforce_id, risk_user_id, 'owner'),
    (pilot_tenant_id, init_controls_id, risk_user_id, 'owner')
  ON CONFLICT (initiative_id, user_id) DO UPDATE SET role = EXCLUDED.role;

  INSERT INTO milestones (
    id,
    tenant_id,
    initiative_id,
    name,
    description,
    owner_id,
    priority,
    status,
    sort_order,
    planned_start,
    actual_start,
    planned_end,
    actual_end,
    pressure_score
  )
  VALUES
    (ms_rev_pilot_id, pilot_tenant_id, init_rev_asia_id, 'Japan pilot account conversion', 'Convert first strategic account cohort and validate playbook.', owner_user_id, 'high', 'complete', 10, '2026-01-15', '2026-01-20', '2026-03-31', '2026-03-28', 3.0),
    (ms_rev_scale_id, pilot_tenant_id, init_rev_asia_id, 'Korea scale launch', 'Launch Korea sales motion after pricing governance sign-off.', owner_user_id, 'high', 'in_progress', 20, '2026-05-01', '2026-05-05', '2026-06-30', NULL, 6.8),
    (ms_ap_baseline_id, pilot_tenant_id, init_ap_auto_id, 'Invoice baseline complete', 'Baseline current invoice cycle time and defect rates.', finance_user_id, 'medium', 'complete', 10, '2026-02-01', '2026-02-08', '2026-03-15', '2026-03-12', 2.5),
    (ms_ap_erp_id, pilot_tenant_id, init_ap_auto_id, 'ERP integration ready', 'Complete ERP event bridge and exception queue.', finance_user_id, 'high', 'overdue', 20, '2026-04-01', '2026-04-02', '2026-05-15', NULL, 9.0),
    (ms_procure_wave_id, pilot_tenant_id, init_procure_id, 'Wave 2 supplier shortlist', 'Agree category shortlist and negotiation owner model.', finance_user_id, 'medium', 'not_started', 10, '2026-06-01', NULL, '2026-07-15', NULL, 4.1),
    (ms_workforce_launch_id, pilot_tenant_id, init_workforce_id, 'Shared services training launch', 'Start training wave for first migrated roles.', risk_user_id, 'high', 'overdue', 10, '2026-03-01', '2026-03-05', '2026-04-30', NULL, 9.4);

  INSERT INTO milestone_dependencies (tenant_id, upstream_milestone_id, downstream_milestone_id)
  VALUES
    (pilot_tenant_id, ms_ap_erp_id, ms_rev_scale_id),
    (pilot_tenant_id, ms_workforce_launch_id, ms_procure_wave_id)
  ON CONFLICT (upstream_milestone_id, downstream_milestone_id) DO NOTHING;

  INSERT INTO kpis (id, tenant_id, initiative_id, name, type, category, frequency, unit)
  VALUES
    ('11111111-1111-4111-8111-111111120001', pilot_tenant_id, init_rev_asia_id, 'Qualified conversion rate', 'operational', 'Commercial', 'quarterly', '%'),
    ('11111111-1111-4111-8111-111111120002', pilot_tenant_id, init_ap_auto_id, 'Invoice cycle time reduction', 'operational', 'Operations', 'monthly', '%'),
    ('11111111-1111-4111-8111-111111120003', pilot_tenant_id, init_procure_id, 'Addressable spend under contract', 'custom', 'Procurement', 'quarterly', '%'),
    ('11111111-1111-4111-8111-111111120004', pilot_tenant_id, init_workforce_id, 'Roles transitioned to shared services', 'operational', 'People', 'monthly', 'roles'),
    ('11111111-1111-4111-8111-111111120005', pilot_tenant_id, init_controls_id, 'Control evidence completion', 'custom', 'Controls', 'monthly', '%');

  INSERT INTO kpi_entries (tenant_id, kpi_id, year, quarter, value_base, value_high, value_actual)
  VALUES
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120001', 2026, 1, 18.0000, 22.0000, 24.0000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120001', 2026, 2, 24.0000, 28.0000, 27.5000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120002', 2026, 1, 15.0000, 20.0000, 12.0000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120002', 2026, 2, 30.0000, 38.0000, 22.0000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120003', 2026, 2, 35.0000, 50.0000, 28.0000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120004', 2026, 2, 40.0000, 55.0000, 22.0000),
    (pilot_tenant_id, '11111111-1111-4111-8111-111111120005', 2026, 1, 85.0000, 95.0000, 96.0000)
  ON CONFLICT (kpi_id, year, quarter) DO UPDATE SET
    value_base = EXCLUDED.value_base,
    value_high = EXCLUDED.value_high,
    value_actual = EXCLUDED.value_actual,
    updated_at = NOW();

  INSERT INTO risks (
    id,
    tenant_id,
    initiative_id,
    description,
    type,
    impact,
    likelihood,
    rating,
    status,
    owner_id,
    mitigation,
    escalated,
    created_at
  )
  VALUES
    ('11111111-1111-4111-8111-111111121001', pilot_tenant_id, init_ap_auto_id, 'ERP dependency may slip and delay AP automation scale-up.', 'technology', 'high', 'medium', 'high', 'open', finance_user_id, 'Create daily integration stand-up and unblock environment access.', TRUE, '2026-05-14T00:00:00+00:00'),
    ('11111111-1111-4111-8111-111111121002', pilot_tenant_id, init_workforce_id, 'Role transition resistance may slow shared services adoption.', 'people', 'high', 'high', 'high', 'open', risk_user_id, 'Escalate consultation plan and publish manager enablement pack.', TRUE, '2026-05-08T00:00:00+00:00'),
    ('11111111-1111-4111-8111-111111121003', pilot_tenant_id, init_procure_id, 'Supplier baseline quality may limit savings confidence.', 'financial', 'medium', 'medium', 'medium', 'open', finance_user_id, 'Finance to certify category baselines before negotiation.', FALSE, '2026-05-20T00:00:00+00:00'),
    ('11111111-1111-4111-8111-111111121004', pilot_tenant_id, init_controls_id, 'Evidence ownership was unclear during first audit cycle.', 'operational', 'medium', 'low', 'low', 'closed', risk_user_id, 'Closed after evidence calendar ownership was assigned.', FALSE, '2026-02-01T00:00:00+00:00');

  INSERT INTO financial_entries (
    tenant_id,
    initiative_id,
    year,
    quarter,
    month,
    revenue_uplift_base,
    revenue_uplift_high,
    revenue_uplift_actual,
    gross_margin_base,
    gross_margin_high,
    gross_margin_actual,
    gm_pct_base,
    gm_pct_high,
    gm_pct_actual,
    gm_uplift_base,
    gm_uplift_high,
    gm_uplift_actual,
    cogs_base,
    cogs_high,
    cogs_actual
  )
  VALUES
    (pilot_tenant_id, init_rev_asia_id, 2026, 1, NULL, 800000.0000, 1100000.0000, 920000.0000, 320000.0000, 440000.0000, 392000.0000, 40.0000, 40.0000, 42.6087, 320000.0000, 440000.0000, 392000.0000, 480000.0000, 660000.0000, 528000.0000),
    (pilot_tenant_id, init_rev_asia_id, 2026, 2, NULL, 950000.0000, 1250000.0000, 990000.0000, 380000.0000, 500000.0000, 410000.0000, 40.0000, 40.0000, 41.4141, 380000.0000, 500000.0000, 410000.0000, 570000.0000, 750000.0000, 580000.0000),
    (pilot_tenant_id, init_ap_auto_id, 2026, 2, NULL, 0.0000, 0.0000, 0.0000, 210000.0000, 310000.0000, 125000.0000, 0.0000, 0.0000, 0.0000, 210000.0000, 310000.0000, 125000.0000, 0.0000, 0.0000, 0.0000),
    (pilot_tenant_id, init_procure_id, 2026, 3, NULL, 0.0000, 0.0000, NULL, 260000.0000, 420000.0000, NULL, 0.0000, 0.0000, NULL, 260000.0000, 420000.0000, NULL, 0.0000, 0.0000, NULL),
    (pilot_tenant_id, init_workforce_id, 2026, 2, NULL, 0.0000, 0.0000, 0.0000, 180000.0000, 280000.0000, 60000.0000, 0.0000, 0.0000, 0.0000, 180000.0000, 280000.0000, 60000.0000, 0.0000, 0.0000, 0.0000),
    (pilot_tenant_id, init_controls_id, 2026, 1, NULL, 0.0000, 0.0000, 0.0000, 90000.0000, 130000.0000, 120000.0000, 0.0000, 0.0000, 0.0000, 90000.0000, 130000.0000, 120000.0000, 0.0000, 0.0000, 0.0000)
  ON CONFLICT (tenant_id, initiative_id, year, quarter, month) DO UPDATE SET
    revenue_uplift_base = EXCLUDED.revenue_uplift_base,
    revenue_uplift_high = EXCLUDED.revenue_uplift_high,
    revenue_uplift_actual = EXCLUDED.revenue_uplift_actual,
    gross_margin_base = EXCLUDED.gross_margin_base,
    gross_margin_high = EXCLUDED.gross_margin_high,
    gross_margin_actual = EXCLUDED.gross_margin_actual,
    gm_pct_base = EXCLUDED.gm_pct_base,
    gm_pct_high = EXCLUDED.gm_pct_high,
    gm_pct_actual = EXCLUDED.gm_pct_actual,
    gm_uplift_base = EXCLUDED.gm_uplift_base,
    gm_uplift_high = EXCLUDED.gm_uplift_high,
    gm_uplift_actual = EXCLUDED.gm_uplift_actual,
    cogs_base = EXCLUDED.cogs_base,
    cogs_high = EXCLUDED.cogs_high,
    cogs_actual = EXCLUDED.cogs_actual,
    updated_at = NOW();

  INSERT INTO financial_cost_lines (
    id,
    tenant_id,
    initiative_id,
    name,
    year,
    quarter,
    amount_plan,
    amount_actual,
    is_recurring,
    category_key
  )
  VALUES
    ('11111111-1111-4111-8111-111111122001', pilot_tenant_id, init_rev_asia_id, 'Sales enablement partner', 2026, 1, 65000.0000, 62000.0000, FALSE, 'implementation'),
    ('11111111-1111-4111-8111-111111122002', pilot_tenant_id, init_ap_auto_id, 'AP automation software', 2026, 2, 85000.0000, 72000.0000, TRUE, 'software'),
    ('11111111-1111-4111-8111-111111122003', pilot_tenant_id, init_procure_id, 'Category analytics support', 2026, 3, 55000.0000, NULL, FALSE, 'implementation'),
    ('11111111-1111-4111-8111-111111122004', pilot_tenant_id, init_workforce_id, 'Training and transition support', 2026, 2, 140000.0000, 118000.0000, FALSE, 'labor'),
    ('11111111-1111-4111-8111-111111122005', pilot_tenant_id, init_controls_id, 'Controls evidence tooling', 2026, 1, 45000.0000, 42000.0000, TRUE, 'software');

  INSERT INTO initiative_financial_selections (tenant_id, initiative_id, item_key, item_type, is_active)
  SELECT pilot_tenant_id, initiative_id, item_key, item_type, TRUE
  FROM (
    VALUES
      (init_rev_asia_id, 'revenue_uplift_base', 'metric'),
      (init_rev_asia_id, 'gm_uplift_base', 'metric'),
      (init_rev_asia_id, 'implementation', 'cost_category'),
      (init_ap_auto_id, 'gm_uplift_base', 'metric'),
      (init_ap_auto_id, 'software', 'cost_category'),
      (init_procure_id, 'gm_uplift_base', 'metric'),
      (init_procure_id, 'implementation', 'cost_category'),
      (init_workforce_id, 'gm_uplift_base', 'metric'),
      (init_workforce_id, 'labor', 'cost_category'),
      (init_controls_id, 'gm_uplift_base', 'metric'),
      (init_controls_id, 'software', 'cost_category')
  ) AS seeded(initiative_id, item_key, item_type)
  ON CONFLICT (tenant_id, initiative_id, item_key, item_type) DO UPDATE SET
    is_active = TRUE,
    updated_at = NOW();

  INSERT INTO status_updates (
    id,
    tenant_id,
    initiative_id,
    author_id,
    rag_status,
    summary,
    achievements,
    issues,
    next_steps,
    is_draft,
    submitted_at
  )
  VALUES
    ('11111111-1111-4111-8111-111111123001', pilot_tenant_id, init_rev_asia_id, owner_user_id, 'green', 'Japan pilot is performing ahead of forecast with Q1 GM uplift of $392K against a $320K base case.', 'Japan cohort converted ahead of target; Korea launch playbook drafted.', 'Pricing governance sign-off still needed for Korea.', 'Secure Korea pricing decision and launch first account wave.', FALSE, '2026-05-24T09:00:00+08:00'),
    ('11111111-1111-4111-8111-111111123002', pilot_tenant_id, init_ap_auto_id, finance_user_id, 'amber', 'AP automation value case remains positive, but ERP integration is overdue and delaying rollout.', 'Invoice baseline completed and exception taxonomy agreed.', 'ERP event bridge access is delayed.', 'Escalate environment access and reset rollout timeline.', FALSE, '2026-05-24T10:00:00+08:00'),
    ('11111111-1111-4111-8111-111111123003', pilot_tenant_id, init_workforce_id, risk_user_id, 'red', 'Shared services transition needs steering support due to people risk and delayed training.', 'Role inventory completed.', 'Consultation and training dates slipped.', 'Confirm revised consultation plan and training wave owners.', FALSE, '2026-05-24T11:00:00+08:00');

  INSERT INTO meetings (id, tenant_id, name, workstream_id, scope, recurrence, description, owner_id)
  VALUES
    (mtg_steer_id, pilot_tenant_id, 'Transformation Steering Committee', NULL, 'all', 'weekly', 'Executive steering forum for RAG, value, risk, and dependency decisions.', admin_user_id),
    (mtg_north_asia_id, pilot_tenant_id, 'North Asia Workstream Review', ws_growth_id, 'workstream', 'weekly', 'Commercial growth review across Japan and Korea waves.', owner_user_id);

  INSERT INTO meeting_attendees (tenant_id, meeting_id, user_id)
  VALUES
    (pilot_tenant_id, mtg_steer_id, admin_user_id),
    (pilot_tenant_id, mtg_steer_id, viewer_user_id),
    (pilot_tenant_id, mtg_steer_id, finance_user_id),
    (pilot_tenant_id, mtg_steer_id, risk_user_id),
    (pilot_tenant_id, mtg_north_asia_id, owner_user_id),
    (pilot_tenant_id, mtg_north_asia_id, admin_user_id),
    (pilot_tenant_id, mtg_north_asia_id, finance_user_id)
  ON CONFLICT (meeting_id, user_id) DO NOTHING;

  INSERT INTO meeting_initiatives (tenant_id, meeting_id, initiative_id)
  VALUES
    (pilot_tenant_id, mtg_steer_id, init_rev_asia_id),
    (pilot_tenant_id, mtg_steer_id, init_ap_auto_id),
    (pilot_tenant_id, mtg_steer_id, init_workforce_id),
    (pilot_tenant_id, mtg_north_asia_id, init_rev_asia_id)
  ON CONFLICT (meeting_id, initiative_id) DO NOTHING;

  INSERT INTO meeting_sessions (
    id,
    tenant_id,
    meeting_id,
    session_date,
    status,
    has_transcript,
    ai_optimised,
    transcript_text,
    notes,
    minutes_markdown,
    minutes_status,
    minutes_generated_at,
    transcript_source
  )
  VALUES
    (sess_steer_id, pilot_tenant_id, mtg_steer_id, '2026-05-31', 'completed', TRUE, TRUE, 'Vishwa: AP integration remains the top blocker. Dhruva: value bridge still positive. Prahari: workforce transition needs risk treatment.', 'Steering reviewed amber/red items and agreed escalation actions.', '## Steering Committee Minutes\n\n- AP integration remains amber and requires environment access.\n- Shared services transition remains red pending consultation plan.\n- North Asia commercial lift remains green.', 'draft', NOW(), 'seeded'),
    (sess_north_asia_id, pilot_tenant_id, mtg_north_asia_id, '2026-05-30', 'completed', TRUE, TRUE, 'Rupa: Japan pilot is ahead of base case. Vishwa: Korea launch needs pricing governance. Dhruva: update value bridge after the first Korea cohort.', 'North Asia workstream confirmed Japan outperformance and Korea launch dependency.', '## North Asia Review\n\n- Japan pilot ahead of base case.\n- Korea launch waits on pricing governance.', 'draft', NOW(), 'seeded');

  INSERT INTO agenda_items (id, tenant_id, meeting_id, initiative_id, text, sort_order)
  VALUES
    ('11111111-1111-4111-8111-111111124001', pilot_tenant_id, mtg_steer_id, init_ap_auto_id, 'Resolve ERP integration blocker and owner decision', 10),
    ('11111111-1111-4111-8111-111111124002', pilot_tenant_id, mtg_steer_id, init_workforce_id, 'Review workforce transition red status', 20),
    ('11111111-1111-4111-8111-111111124003', pilot_tenant_id, mtg_north_asia_id, init_rev_asia_id, 'Japan pilot conversion and Korea launch readiness', 10);

  INSERT INTO action_items (
    id,
    tenant_id,
    session_id,
    initiative_id,
    description,
    assignee_id,
    priority,
    status,
    due_date
  )
  VALUES
    (action_erp_id, pilot_tenant_id, sess_steer_id, init_ap_auto_id, 'Confirm ERP event bridge environment access and revised integration date.', finance_user_id, 'high', 'open', '2026-06-07'),
    (action_korea_id, pilot_tenant_id, sess_north_asia_id, init_rev_asia_id, 'Schedule Korea pricing governance decision and confirm launch cohort.', owner_user_id, 'high', 'in_progress', '2026-06-10');

  INSERT INTO meeting_artifacts (
    id,
    tenant_id,
    meeting_id,
    session_id,
    initiative_id,
    artifact_type,
    title,
    description,
    status,
    priority,
    owner_id,
    assignee_id,
    due_date,
    linked_record_type,
    linked_record_id
  )
  VALUES
    ('11111111-1111-4111-8111-111111125001', pilot_tenant_id, mtg_steer_id, sess_steer_id, init_ap_auto_id, 'action', 'ERP access escalation', 'Escalate integration environment access and report date confidence.', 'open', 'high', admin_user_id, finance_user_id, '2026-06-07', 'action_items', action_erp_id),
    ('11111111-1111-4111-8111-111111125002', pilot_tenant_id, mtg_north_asia_id, sess_north_asia_id, init_rev_asia_id, 'decision', 'Korea launch waits on pricing governance', 'Commercial wave can launch once the pricing governance decision is complete.', 'open', 'medium', owner_user_id, owner_user_id, '2026-06-10', NULL, NULL);

  INSERT INTO initiative_dependencies (
    id,
    tenant_id,
    upstream_initiative_id,
    downstream_initiative_id,
    dependency_type,
    status,
    severity,
    owner_id,
    due_date,
    linked_milestone_id,
    linked_action_item_id
  )
  VALUES
    ('11111111-1111-4111-8111-111111126001', pilot_tenant_id, init_ap_auto_id, init_rev_asia_id, 'enables', 'at_risk', 'high', finance_user_id, '2026-06-07', ms_ap_erp_id, action_erp_id),
    ('11111111-1111-4111-8111-111111126002', pilot_tenant_id, init_workforce_id, init_procure_id, 'requires_decision', 'blocking', 'high', risk_user_id, '2026-06-14', ms_workforce_launch_id, NULL);

  INSERT INTO shared_cost_pools (
    id,
    tenant_id,
    name,
    description,
    category_key,
    year,
    quarter,
    amount_plan,
    amount_actual,
    is_recurring,
    status
  )
  VALUES (
    shared_pool_id,
    pilot_tenant_id,
    'Transformation PMO Shared Support',
    'Shared PMO, analytics, and change support allocated by benefit weight.',
    'labor',
    2026,
    2,
    240000.0000,
    210000.0000,
    TRUE,
    'active'
  );

  INSERT INTO shared_cost_allocation_rules (
    id,
    tenant_id,
    pool_id,
    name,
    allocation_method,
    filters,
    weights,
    is_active
  )
  VALUES (
    shared_rule_id,
    pilot_tenant_id,
    shared_pool_id,
    'Benefit weighted pilot allocation',
    'benefit_weighted',
    '{"target_year":2026}'::jsonb,
    '{}'::jsonb,
    TRUE
  );

  INSERT INTO shared_cost_allocation_runs (
    id,
    tenant_id,
    pool_id,
    rule_id,
    scenario,
    status,
    total_amount_plan,
    total_amount_actual,
    created_by
  )
  VALUES (
    shared_run_id,
    pilot_tenant_id,
    shared_pool_id,
    shared_rule_id,
    'plan',
    'completed',
    240000.0000,
    210000.0000,
    admin_user_id
  );

  INSERT INTO shared_cost_allocations (
    tenant_id,
    run_id,
    pool_id,
    rule_id,
    initiative_id,
    allocation_basis,
    basis_value,
    allocated_plan,
    allocated_actual
  )
  VALUES
    (pilot_tenant_id, shared_run_id, shared_pool_id, shared_rule_id, init_rev_asia_id, 'benefit_weighted', 700000.0000, 96000.0000, 84000.0000),
    (pilot_tenant_id, shared_run_id, shared_pool_id, shared_rule_id, init_ap_auto_id, 'benefit_weighted', 210000.0000, 48000.0000, 42000.0000),
    (pilot_tenant_id, shared_run_id, shared_pool_id, shared_rule_id, init_procure_id, 'benefit_weighted', 260000.0000, 48000.0000, 42000.0000),
    (pilot_tenant_id, shared_run_id, shared_pool_id, shared_rule_id, init_workforce_id, 'benefit_weighted', 180000.0000, 48000.0000, 42000.0000);

  INSERT INTO initiative_value_realization_notes (
    id,
    tenant_id,
    initiative_id,
    author_id,
    note_type,
    period_label,
    planned_value,
    actual_value,
    explanation
  )
  VALUES
    ('11111111-1111-4111-8111-111111127001', pilot_tenant_id, init_rev_asia_id, finance_user_id, 'variance', '2026 Q1', 320000.0000, 392000.0000, 'Japan pilot outperformed base case because strategic accounts converted faster than the original playbook assumption.'),
    ('11111111-1111-4111-8111-111111127002', pilot_tenant_id, init_ap_auto_id, finance_user_id, 'benefit_confidence', '2026 Q2', 210000.0000, 125000.0000, 'Benefit confidence remains moderate until ERP integration is unblocked and rollout timing is reset.'),
    ('11111111-1111-4111-8111-111111127003', pilot_tenant_id, init_workforce_id, risk_user_id, 'board_note', '2026 Q2', 180000.0000, 60000.0000, 'Steering support is needed to stabilize workforce transition risk and protect the value timeline.');

  RAISE NOTICE 'Seeded Transmuter pilot tenant %, admin login admin@ishirock.dev / Transmuter2026!', pilot_tenant_id;
END
$$;

COMMIT;
