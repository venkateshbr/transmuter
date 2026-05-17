-- Transmuter schema backup before Executive Control Tower Phase 2A migration
-- Created: 2026-05-10
-- Scope: public schema DDL metadata generated from PostgreSQL catalogs

-- Functions
CREATE OR REPLACE FUNCTION public.current_tenant_id()
 RETURNS uuid
 LANGUAGE sql
 STABLE
AS $function$ SELECT (auth.jwt() ->> 'tenant_id')::uuid $function$;

CREATE OR REPLACE FUNCTION public.current_user_role()
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$ SELECT auth.jwt() ->> 'role' $function$;

CREATE OR REPLACE FUNCTION public.rls_auto_enable()
 RETURNS event_trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog'
AS $function$
DECLARE
  cmd record;
BEGIN
  FOR cmd IN
    SELECT *
    FROM pg_event_trigger_ddl_commands()
    WHERE command_tag IN ('CREATE TABLE', 'CREATE TABLE AS', 'SELECT INTO')
      AND object_type IN ('table','partitioned table')
  LOOP
     IF cmd.schema_name IS NOT NULL AND cmd.schema_name IN ('public') AND cmd.schema_name NOT IN ('pg_catalog','information_schema') AND cmd.schema_name NOT LIKE 'pg_toast%' AND cmd.schema_name NOT LIKE 'pg_temp%' THEN
      BEGIN
        EXECUTE format('alter table if exists %s enable row level security', cmd.object_identity);
        RAISE LOG 'rls_auto_enable: enabled RLS on %', cmd.object_identity;
      EXCEPTION
        WHEN OTHERS THEN
          RAISE LOG 'rls_auto_enable: failed to enable RLS on %', cmd.object_identity;
      END;
     ELSE
        RAISE LOG 'rls_auto_enable: skip % (either system schema or not in enforced list: %.)', cmd.object_identity, cmd.schema_name;
     END IF;
  END LOOP;
END;
$function$;

-- Table: public.action_items
CREATE TABLE public.action_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  session_id uuid NOT NULL,
  initiative_id uuid,
  description text NOT NULL,
  assignee_id uuid,
  priority text DEFAULT 'medium'::text,
  status text DEFAULT 'open'::text NOT NULL,
  due_date date,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.action_items ADD CONSTRAINT action_items_assignee_id_fkey FOREIGN KEY (assignee_id) REFERENCES users(id);
ALTER TABLE public.action_items ADD CONSTRAINT action_items_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id);
ALTER TABLE public.action_items ADD CONSTRAINT action_items_pkey PRIMARY KEY (id);
ALTER TABLE public.action_items ADD CONSTRAINT action_items_priority_check CHECK ((priority = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.action_items ADD CONSTRAINT action_items_session_id_fkey FOREIGN KEY (session_id) REFERENCES meeting_sessions(id) ON DELETE CASCADE;
ALTER TABLE public.action_items ADD CONSTRAINT action_items_status_check CHECK ((status = ANY (ARRAY['open'::text, 'in_progress'::text, 'completed'::text, 'cancelled'::text])));
ALTER TABLE public.action_items ADD CONSTRAINT action_items_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.agenda_items
CREATE TABLE public.agenda_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  meeting_id uuid NOT NULL,
  initiative_id uuid,
  text text NOT NULL,
  sort_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.agenda_items ADD CONSTRAINT agenda_items_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id);
ALTER TABLE public.agenda_items ADD CONSTRAINT agenda_items_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
ALTER TABLE public.agenda_items ADD CONSTRAINT agenda_items_pkey PRIMARY KEY (id);
ALTER TABLE public.agenda_items ADD CONSTRAINT agenda_items_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.agent_audit_log
CREATE TABLE public.agent_audit_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  agent_id text NOT NULL,
  skill_name text,
  workflow_run_id uuid,
  action text,
  confidence numeric(5,4),
  latency_ms integer,
  input_summary text,
  output_summary text,
  requires_review boolean DEFAULT false,
  human_action text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.agent_audit_log ADD CONSTRAINT agent_audit_log_pkey PRIMARY KEY (id);
ALTER TABLE public.agent_audit_log ADD CONSTRAINT agent_audit_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.agent_corrections
CREATE TABLE public.agent_corrections (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  agent_id text NOT NULL,
  audit_log_id uuid,
  agent_prediction jsonb,
  human_correction jsonb,
  correction_type text,
  corrected_by uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.agent_corrections ADD CONSTRAINT agent_corrections_audit_log_id_fkey FOREIGN KEY (audit_log_id) REFERENCES agent_audit_log(id);
ALTER TABLE public.agent_corrections ADD CONSTRAINT agent_corrections_corrected_by_fkey FOREIGN KEY (corrected_by) REFERENCES users(id);
ALTER TABLE public.agent_corrections ADD CONSTRAINT agent_corrections_pkey PRIMARY KEY (id);
ALTER TABLE public.agent_corrections ADD CONSTRAINT agent_corrections_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.agent_metrics
CREATE TABLE public.agent_metrics (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  metric_date date NOT NULL,
  agent_id text NOT NULL,
  total_runs integer DEFAULT 0,
  auto_approved integer DEFAULT 0,
  hitl_required integer DEFAULT 0,
  correction_count integer DEFAULT 0,
  avg_latency_ms numeric(8,2),
  avg_confidence numeric(5,4),
  tenant_id uuid NOT NULL
);

ALTER TABLE public.agent_metrics ADD CONSTRAINT agent_metrics_pkey PRIMARY KEY (id);
ALTER TABLE public.agent_metrics ADD CONSTRAINT agent_metrics_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.agent_metrics ADD CONSTRAINT agent_metrics_tenant_metric_date_agent_id_key UNIQUE (tenant_id, metric_date, agent_id);

-- Table: public.audit_log
CREATE TABLE public.audit_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  user_id uuid,
  entity_type text NOT NULL,
  entity_id uuid NOT NULL,
  action text NOT NULL,
  before_data jsonb,
  after_data jsonb,
  ip_address text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_action_check CHECK ((action = ANY (ARRAY['create'::text, 'update'::text, 'delete'::text, 'archive'::text, 'submit'::text, 'approve'::text, 'reject'::text])));
ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);
ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.audit_log ADD CONSTRAINT audit_log_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id);

-- Table: public.business_units
CREATE TABLE public.business_units (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  code text,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.business_units ADD CONSTRAINT business_units_pkey PRIMARY KEY (id);
ALTER TABLE public.business_units ADD CONSTRAINT business_units_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.financial_cell_assumptions
CREATE TABLE public.financial_cell_assumptions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  row_key text NOT NULL,
  column_key text NOT NULL,
  comment text NOT NULL,
  created_by uuid,
  updated_by uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_comment_check CHECK ((length(TRIM(BOTH FROM comment)) > 0));
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id);
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_pkey PRIMARY KEY (id);
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_tenant_id_initiative_id_row_key__key UNIQUE (tenant_id, initiative_id, row_key, column_key);
ALTER TABLE public.financial_cell_assumptions ADD CONSTRAINT financial_cell_assumptions_updated_by_fkey FOREIGN KEY (updated_by) REFERENCES users(id);

-- Table: public.financial_config_groups
CREATE TABLE public.financial_config_groups (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  key text NOT NULL,
  label text NOT NULL,
  kind text NOT NULL,
  rollup_type text,
  display_order integer DEFAULT 0 NOT NULL,
  is_system boolean DEFAULT false NOT NULL,
  is_active boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.financial_config_groups ADD CONSTRAINT financial_config_groups_kind_check CHECK ((kind = ANY (ARRAY['calculation'::text, 'metric'::text, 'cost_category'::text])));
ALTER TABLE public.financial_config_groups ADD CONSTRAINT financial_config_groups_pkey PRIMARY KEY (id);
ALTER TABLE public.financial_config_groups ADD CONSTRAINT financial_config_groups_rollup_type_check CHECK ((rollup_type = ANY (ARRAY['benefit'::text, 'recurring_cost'::text, 'one_off_cost'::text, 'total_cost'::text, 'net_value'::text])));
ALTER TABLE public.financial_config_groups ADD CONSTRAINT financial_config_groups_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.financial_config_groups ADD CONSTRAINT financial_config_groups_tenant_id_key_key UNIQUE (tenant_id, key);

-- Table: public.financial_config_items
CREATE TABLE public.financial_config_items (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  group_id uuid NOT NULL,
  key text NOT NULL,
  label text NOT NULL,
  item_type text NOT NULL,
  system_metric_key text,
  rollup_type text,
  display_order integer DEFAULT 0 NOT NULL,
  is_system boolean DEFAULT false NOT NULL,
  is_active boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_group_id_fkey FOREIGN KEY (group_id) REFERENCES financial_config_groups(id) ON DELETE CASCADE;
ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_item_type_check CHECK ((item_type = ANY (ARRAY['metric'::text, 'cost_category'::text])));
ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_pkey PRIMARY KEY (id);
ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_rollup_type_check CHECK ((rollup_type = ANY (ARRAY['benefit'::text, 'recurring_cost'::text, 'one_off_cost'::text, 'total_cost'::text, 'net_value'::text])));
ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.financial_config_items ADD CONSTRAINT financial_config_items_tenant_id_key_key UNIQUE (tenant_id, key);

-- Table: public.financial_cost_lines
CREATE TABLE public.financial_cost_lines (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  name text NOT NULL,
  year integer NOT NULL,
  quarter integer,
  amount_plan numeric(15,4) DEFAULT 0,
  amount_actual numeric(15,4),
  is_recurring boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  month integer,
  category_key text DEFAULT 'other'::text NOT NULL
);

ALTER TABLE public.financial_cost_lines ADD CONSTRAINT cl_unique_period_name UNIQUE (initiative_id, name, year, quarter, month);
ALTER TABLE public.financial_cost_lines ADD CONSTRAINT financial_cost_lines_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.financial_cost_lines ADD CONSTRAINT financial_cost_lines_month_check CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public.financial_cost_lines ADD CONSTRAINT financial_cost_lines_pkey PRIMARY KEY (id);
ALTER TABLE public.financial_cost_lines ADD CONSTRAINT financial_cost_lines_quarter_check CHECK (((quarter >= 1) AND (quarter <= 4)));
ALTER TABLE public.financial_cost_lines ADD CONSTRAINT financial_cost_lines_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.financial_entries
CREATE TABLE public.financial_entries (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  year integer NOT NULL,
  quarter integer,
  revenue_uplift_base numeric(15,4) DEFAULT 0,
  revenue_uplift_high numeric(15,4) DEFAULT 0,
  revenue_uplift_actual numeric(15,4),
  gross_margin_base numeric(15,4) DEFAULT 0,
  gross_margin_high numeric(15,4) DEFAULT 0,
  gross_margin_actual numeric(15,4),
  gm_pct_base numeric(8,4) DEFAULT 0,
  gm_pct_high numeric(8,4) DEFAULT 0,
  gm_pct_actual numeric(8,4),
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  month integer,
  revenue_uplift_pct_base numeric(8,4) DEFAULT 0,
  revenue_uplift_pct_high numeric(8,4) DEFAULT 0,
  revenue_uplift_pct_actual numeric(8,4),
  gm_uplift_base numeric(15,4) DEFAULT 0,
  gm_uplift_high numeric(15,4) DEFAULT 0,
  gm_uplift_actual numeric(15,4),
  gm_uplift_pct_base numeric(8,4) DEFAULT 0,
  gm_uplift_pct_high numeric(8,4) DEFAULT 0,
  gm_uplift_pct_actual numeric(8,4),
  cogs_base numeric(15,4) DEFAULT 0,
  cogs_high numeric(15,4) DEFAULT 0,
  cogs_actual numeric(15,4),
  cogs_pct_base numeric(8,4) DEFAULT 0,
  cogs_pct_high numeric(8,4) DEFAULT 0,
  cogs_pct_actual numeric(8,4)
);

ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_month_check CHECK (((month >= 1) AND (month <= 12)));
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_pkey PRIMARY KEY (id);
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_quarter_check CHECK (((quarter >= 1) AND (quarter <= 4)));
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_tenant_initiative_year_period_key UNIQUE NULLS NOT DISTINCT (tenant_id, initiative_id, year, quarter, month);
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_unique_period UNIQUE (initiative_id, year, quarter, month);
ALTER TABLE public.financial_entries ADD CONSTRAINT financial_entries_year_check CHECK (((year >= 2020) AND (year <= 2040)));

-- Table: public.gate_criteria
CREATE TABLE public.gate_criteria (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  gate_number integer NOT NULL,
  criterion_id text NOT NULL,
  label text NOT NULL,
  guidance text,
  sort_order integer DEFAULT 0,
  is_active boolean DEFAULT true
);

ALTER TABLE public.gate_criteria ADD CONSTRAINT gate_criteria_gate_number_check CHECK ((gate_number = ANY (ARRAY[1, 2])));
ALTER TABLE public.gate_criteria ADD CONSTRAINT gate_criteria_pkey PRIMARY KEY (id);
ALTER TABLE public.gate_criteria ADD CONSTRAINT gate_criteria_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.gate_criteria ADD CONSTRAINT gate_criteria_tenant_id_gate_number_criterion_id_key UNIQUE (tenant_id, gate_number, criterion_id);

-- Table: public.gate_submissions
CREATE TABLE public.gate_submissions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  gate_number integer NOT NULL,
  submitted_by_id uuid NOT NULL,
  submitted_at timestamp with time zone DEFAULT now() NOT NULL,
  decision text DEFAULT 'pending'::text NOT NULL,
  decided_by_id uuid,
  decided_at timestamp with time zone,
  commentary text,
  criteria_snapshot jsonb
);

ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_decided_by_id_fkey FOREIGN KEY (decided_by_id) REFERENCES users(id);
ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_decision_check CHECK ((decision = ANY (ARRAY['pending'::text, 'approved'::text, 'rejected'::text, 'conditional'::text])));
ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_pkey PRIMARY KEY (id);
ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_submitted_by_id_fkey FOREIGN KEY (submitted_by_id) REFERENCES users(id);
ALTER TABLE public.gate_submissions ADD CONSTRAINT gate_submissions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.initiative_team
CREATE TABLE public.initiative_team (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  user_id uuid NOT NULL,
  role text DEFAULT 'member'::text NOT NULL,
  created_at timestamp with time zone DEFAULT now()
);

ALTER TABLE public.initiative_team ADD CONSTRAINT initiative_team_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.initiative_team ADD CONSTRAINT initiative_team_initiative_id_user_id_key UNIQUE (initiative_id, user_id);
ALTER TABLE public.initiative_team ADD CONSTRAINT initiative_team_pkey PRIMARY KEY (id);
ALTER TABLE public.initiative_team ADD CONSTRAINT initiative_team_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.initiative_team ADD CONSTRAINT initiative_team_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Table: public.initiatives
CREATE TABLE public.initiatives (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_code text NOT NULL,
  name text NOT NULL,
  workstream_id uuid,
  owner_id uuid,
  group_owner_id uuid,
  type text,
  impact_type text,
  theme text,
  country text,
  tag text,
  priority text DEFAULT 'medium'::text NOT NULL,
  rag_status text DEFAULT 'green'::text NOT NULL,
  stage text DEFAULT 'scoping'::text NOT NULL,
  summary text,
  value_logic text,
  dependencies_text text,
  planned_start date,
  actual_start date,
  planned_end date,
  actual_end date,
  pressure_score numeric(4,1),
  pressure_sub jsonb DEFAULT '{}'::jsonb,
  pressure_updated_at timestamp with time zone,
  archived_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL,
  lessons_learned text
);

ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_group_owner_id_fkey FOREIGN KEY (group_owner_id) REFERENCES users(id);
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_impact_type_check CHECK ((impact_type = ANY (ARRAY['recurring'::text, 'one_off'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id);
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_pkey PRIMARY KEY (id);
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_priority_check CHECK ((priority = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_rag_status_check CHECK ((rag_status = ANY (ARRAY['red'::text, 'amber'::text, 'green'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_stage_check CHECK ((stage = ANY (ARRAY['scoping'::text, 'in_progress'::text, 'complete'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_tag_check CHECK ((tag = ANY (ARRAY['automation'::text, 'offshoring'::text, 'commercial'::text, 'other'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_tenant_id_initiative_code_key UNIQUE (tenant_id, initiative_code);
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_type_check CHECK ((type = ANY (ARRAY['revenue_growth'::text, 'cost_reduction'::text, 'cost_avoidance'::text, 'compliance'::text, 'capability_building'::text])));
ALTER TABLE public.initiatives ADD CONSTRAINT initiatives_workstream_id_fkey FOREIGN KEY (workstream_id) REFERENCES workstreams(id);

-- Table: public.kpi_entries
CREATE TABLE public.kpi_entries (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  kpi_id uuid NOT NULL,
  year integer NOT NULL,
  quarter integer,
  value_base numeric(15,4),
  value_high numeric(15,4),
  value_actual numeric(15,4),
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_kpi_id_fkey FOREIGN KEY (kpi_id) REFERENCES kpis(id) ON DELETE CASCADE;
ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_kpi_id_year_quarter_key UNIQUE (kpi_id, year, quarter);
ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_pkey PRIMARY KEY (id);
ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_quarter_check CHECK (((quarter >= 1) AND (quarter <= 4)));
ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.kpi_entries ADD CONSTRAINT kpi_entries_year_check CHECK (((year >= 2020) AND (year <= 2040)));

-- Table: public.kpis
CREATE TABLE public.kpis (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  name text NOT NULL,
  type text,
  category text,
  frequency text DEFAULT 'quarterly'::text NOT NULL,
  unit text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.kpis ADD CONSTRAINT kpis_frequency_check CHECK ((frequency = ANY (ARRAY['quarterly'::text, 'monthly'::text, 'annual'::text])));
ALTER TABLE public.kpis ADD CONSTRAINT kpis_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.kpis ADD CONSTRAINT kpis_pkey PRIMARY KEY (id);
ALTER TABLE public.kpis ADD CONSTRAINT kpis_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.kpis ADD CONSTRAINT kpis_type_check CHECK ((type = ANY (ARRAY['gross_margin'::text, 'operational'::text, 'custom'::text])));

-- Table: public.meeting_attendees
CREATE TABLE public.meeting_attendees (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  meeting_id uuid NOT NULL,
  user_id uuid NOT NULL
);

ALTER TABLE public.meeting_attendees ADD CONSTRAINT meeting_attendees_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
ALTER TABLE public.meeting_attendees ADD CONSTRAINT meeting_attendees_meeting_id_user_id_key UNIQUE (meeting_id, user_id);
ALTER TABLE public.meeting_attendees ADD CONSTRAINT meeting_attendees_pkey PRIMARY KEY (id);
ALTER TABLE public.meeting_attendees ADD CONSTRAINT meeting_attendees_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.meeting_attendees ADD CONSTRAINT meeting_attendees_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- Table: public.meeting_initiatives
CREATE TABLE public.meeting_initiatives (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  meeting_id uuid NOT NULL,
  initiative_id uuid NOT NULL
);

ALTER TABLE public.meeting_initiatives ADD CONSTRAINT meeting_initiatives_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.meeting_initiatives ADD CONSTRAINT meeting_initiatives_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
ALTER TABLE public.meeting_initiatives ADD CONSTRAINT meeting_initiatives_meeting_id_initiative_id_key UNIQUE (meeting_id, initiative_id);
ALTER TABLE public.meeting_initiatives ADD CONSTRAINT meeting_initiatives_pkey PRIMARY KEY (id);
ALTER TABLE public.meeting_initiatives ADD CONSTRAINT meeting_initiatives_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.meeting_sessions
CREATE TABLE public.meeting_sessions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  meeting_id uuid NOT NULL,
  session_date date NOT NULL,
  status text DEFAULT 'scheduled'::text NOT NULL,
  has_transcript boolean DEFAULT false,
  ai_optimised boolean DEFAULT false,
  transcript_text text,
  notes text,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.meeting_sessions ADD CONSTRAINT meeting_sessions_meeting_id_fkey FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE;
ALTER TABLE public.meeting_sessions ADD CONSTRAINT meeting_sessions_pkey PRIMARY KEY (id);
ALTER TABLE public.meeting_sessions ADD CONSTRAINT meeting_sessions_status_check CHECK ((status = ANY (ARRAY['scheduled'::text, 'in_progress'::text, 'completed'::text])));
ALTER TABLE public.meeting_sessions ADD CONSTRAINT meeting_sessions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.meetings
CREATE TABLE public.meetings (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  name text NOT NULL,
  workstream_id uuid,
  scope text DEFAULT 'all'::text,
  recurrence text DEFAULT 'weekly'::text,
  description text,
  owner_id uuid,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.meetings ADD CONSTRAINT meetings_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id);
ALTER TABLE public.meetings ADD CONSTRAINT meetings_pkey PRIMARY KEY (id);
ALTER TABLE public.meetings ADD CONSTRAINT meetings_recurrence_check CHECK ((recurrence = ANY (ARRAY['weekly'::text, 'biweekly'::text, 'monthly'::text, 'ad_hoc'::text])));
ALTER TABLE public.meetings ADD CONSTRAINT meetings_scope_check CHECK ((scope = ANY (ARRAY['workstream'::text, 'all'::text])));
ALTER TABLE public.meetings ADD CONSTRAINT meetings_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.meetings ADD CONSTRAINT meetings_workstream_id_fkey FOREIGN KEY (workstream_id) REFERENCES workstreams(id);

-- Table: public.milestone_checklist
CREATE TABLE public.milestone_checklist (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  milestone_id uuid NOT NULL,
  text text NOT NULL,
  completed boolean DEFAULT false NOT NULL,
  sort_order integer DEFAULT 0,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.milestone_checklist ADD CONSTRAINT milestone_checklist_milestone_id_fkey FOREIGN KEY (milestone_id) REFERENCES milestones(id) ON DELETE CASCADE;
ALTER TABLE public.milestone_checklist ADD CONSTRAINT milestone_checklist_pkey PRIMARY KEY (id);
ALTER TABLE public.milestone_checklist ADD CONSTRAINT milestone_checklist_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.milestone_dependencies
CREATE TABLE public.milestone_dependencies (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  upstream_milestone_id uuid NOT NULL,
  downstream_milestone_id uuid NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_check CHECK ((upstream_milestone_id <> downstream_milestone_id));
ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_downstream_milestone_id_fkey FOREIGN KEY (downstream_milestone_id) REFERENCES milestones(id) ON DELETE CASCADE;
ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_pkey PRIMARY KEY (id);
ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_upstream_milestone_id_downstream_mil_key UNIQUE (upstream_milestone_id, downstream_milestone_id);
ALTER TABLE public.milestone_dependencies ADD CONSTRAINT milestone_dependencies_upstream_milestone_id_fkey FOREIGN KEY (upstream_milestone_id) REFERENCES milestones(id) ON DELETE CASCADE;

-- Table: public.milestones
CREATE TABLE public.milestones (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  name text NOT NULL,
  description text,
  owner_id uuid,
  priority text DEFAULT 'medium'::text NOT NULL,
  status text DEFAULT 'not_started'::text NOT NULL,
  sort_order integer DEFAULT 0,
  planned_start date,
  actual_start date,
  planned_end date,
  actual_end date,
  pressure_score numeric(4,1),
  pressure_blast_radius numeric(4,2),
  pressure_dep_urgency numeric(4,2),
  pressure_cluster numeric(4,2),
  pressure_slack numeric(4,2),
  pressure_checklist numeric(4,2),
  pressure_self_status numeric(4,2),
  pressure_updated_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.milestones ADD CONSTRAINT milestones_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.milestones ADD CONSTRAINT milestones_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id);
ALTER TABLE public.milestones ADD CONSTRAINT milestones_pkey PRIMARY KEY (id);
ALTER TABLE public.milestones ADD CONSTRAINT milestones_priority_check CHECK ((priority = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.milestones ADD CONSTRAINT milestones_status_check CHECK ((status = ANY (ARRAY['not_started'::text, 'in_progress'::text, 'complete'::text, 'overdue'::text])));
ALTER TABLE public.milestones ADD CONSTRAINT milestones_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.nudge_log
CREATE TABLE public.nudge_log (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  sent_by_id uuid,
  channel text DEFAULT 'email'::text,
  sent_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.nudge_log ADD CONSTRAINT nudge_log_channel_check CHECK ((channel = ANY (ARRAY['email'::text, 'in_app'::text, 'both'::text])));
ALTER TABLE public.nudge_log ADD CONSTRAINT nudge_log_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.nudge_log ADD CONSTRAINT nudge_log_pkey PRIMARY KEY (id);
ALTER TABLE public.nudge_log ADD CONSTRAINT nudge_log_sent_by_id_fkey FOREIGN KEY (sent_by_id) REFERENCES users(id);
ALTER TABLE public.nudge_log ADD CONSTRAINT nudge_log_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.organizations
CREATE TABLE public.organizations (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  name text NOT NULL,
  slug text NOT NULL,
  logo_url text,
  settings jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.organizations ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);
ALTER TABLE public.organizations ADD CONSTRAINT organizations_slug_key UNIQUE (slug);

-- Table: public.risks
CREATE TABLE public.risks (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  description text NOT NULL,
  type text,
  impact text,
  likelihood text,
  rating text,
  status text DEFAULT 'open'::text NOT NULL,
  owner_id uuid,
  mitigation text,
  escalated boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.risks ADD CONSTRAINT risks_impact_check CHECK ((impact = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.risks ADD CONSTRAINT risks_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.risks ADD CONSTRAINT risks_likelihood_check CHECK ((likelihood = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.risks ADD CONSTRAINT risks_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES users(id);
ALTER TABLE public.risks ADD CONSTRAINT risks_pkey PRIMARY KEY (id);
ALTER TABLE public.risks ADD CONSTRAINT risks_rating_check CHECK ((rating = ANY (ARRAY['high'::text, 'medium'::text, 'low'::text])));
ALTER TABLE public.risks ADD CONSTRAINT risks_status_check CHECK ((status = ANY (ARRAY['open'::text, 'closed'::text])));
ALTER TABLE public.risks ADD CONSTRAINT risks_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.risks ADD CONSTRAINT risks_type_check CHECK ((type = ANY (ARRAY['operational'::text, 'people'::text, 'financial'::text, 'technology'::text])));

-- Table: public.signup_intents
CREATE TABLE public.signup_intents (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  organization_name text NOT NULL,
  organization_slug text NOT NULL,
  admin_email text NOT NULL,
  admin_display_name text NOT NULL,
  planned_user_count integer NOT NULL,
  plan_code text NOT NULL,
  billing_interval text DEFAULT 'month'::text NOT NULL,
  status text DEFAULT 'pending_checkout'::text NOT NULL,
  stripe_checkout_session_id text,
  stripe_customer_id text,
  stripe_subscription_id text,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_billing_interval_check CHECK ((billing_interval = ANY (ARRAY['month'::text, 'year'::text, 'custom'::text])));
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_pkey PRIMARY KEY (id);
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_plan_code_check CHECK ((plan_code = ANY (ARRAY['team'::text, 'business'::text, 'enterprise'::text])));
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_planned_user_count_check CHECK ((planned_user_count > 0));
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_status_check CHECK ((status = ANY (ARRAY['pending_checkout'::text, 'checkout_created'::text, 'paid'::text, 'provisioned'::text, 'failed'::text, 'abandoned'::text])));
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_stripe_checkout_session_id_key UNIQUE (stripe_checkout_session_id);
ALTER TABLE public.signup_intents ADD CONSTRAINT signup_intents_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.stage_gates
CREATE TABLE public.stage_gates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  gate_number integer NOT NULL,
  label text NOT NULL,
  from_stage text NOT NULL,
  to_stage text NOT NULL
);

ALTER TABLE public.stage_gates ADD CONSTRAINT stage_gates_gate_number_check CHECK ((gate_number = ANY (ARRAY[1, 2])));
ALTER TABLE public.stage_gates ADD CONSTRAINT stage_gates_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.stage_gates ADD CONSTRAINT stage_gates_initiative_id_gate_number_key UNIQUE (initiative_id, gate_number);
ALTER TABLE public.stage_gates ADD CONSTRAINT stage_gates_pkey PRIMARY KEY (id);
ALTER TABLE public.stage_gates ADD CONSTRAINT stage_gates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.status_updates
CREATE TABLE public.status_updates (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  initiative_id uuid NOT NULL,
  author_id uuid NOT NULL,
  rag_status text NOT NULL,
  summary text NOT NULL,
  achievements text,
  issues text,
  next_steps text,
  is_draft boolean DEFAULT true NOT NULL,
  submitted_at timestamp with time zone,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.status_updates ADD CONSTRAINT status_updates_author_id_fkey FOREIGN KEY (author_id) REFERENCES users(id);
ALTER TABLE public.status_updates ADD CONSTRAINT status_updates_initiative_id_fkey FOREIGN KEY (initiative_id) REFERENCES initiatives(id) ON DELETE CASCADE;
ALTER TABLE public.status_updates ADD CONSTRAINT status_updates_pkey PRIMARY KEY (id);
ALTER TABLE public.status_updates ADD CONSTRAINT status_updates_rag_status_check CHECK ((rag_status = ANY (ARRAY['red'::text, 'amber'::text, 'green'::text])));
ALTER TABLE public.status_updates ADD CONSTRAINT status_updates_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.subscription_plans
CREATE TABLE public.subscription_plans (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  code text NOT NULL,
  name text NOT NULL,
  user_limit_min integer NOT NULL,
  user_limit_max integer,
  amount_cents integer,
  currency text DEFAULT 'usd'::text NOT NULL,
  billing_interval text DEFAULT 'month'::text NOT NULL,
  stripe_price_id text,
  is_active boolean DEFAULT true NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_amount_cents_check CHECK (((amount_cents IS NULL) OR (amount_cents >= 0)));
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_billing_interval_check CHECK ((billing_interval = ANY (ARRAY['month'::text, 'year'::text, 'custom'::text])));
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_check CHECK (((user_limit_max IS NULL) OR (user_limit_max >= user_limit_min)));
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_code_check CHECK ((code = ANY (ARRAY['team'::text, 'business'::text, 'enterprise'::text])));
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_tenant_id_code_billing_interval_key UNIQUE (tenant_id, code, billing_interval);
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.subscription_plans ADD CONSTRAINT subscription_plans_user_limit_min_check CHECK ((user_limit_min > 0));

-- Table: public.tenant_subscriptions
CREATE TABLE public.tenant_subscriptions (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  plan_id uuid,
  signup_intent_id uuid,
  provider text DEFAULT 'stripe'::text NOT NULL,
  status text DEFAULT 'not_configured'::text NOT NULL,
  checkout_status text,
  payment_status text,
  planned_user_count integer DEFAULT 1 NOT NULL,
  stripe_customer_id text,
  stripe_subscription_id text,
  stripe_checkout_session_id text,
  current_period_end timestamp with time zone,
  cancel_at_period_end boolean DEFAULT false NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_pkey PRIMARY KEY (id);
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES subscription_plans(id);
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_planned_user_count_check CHECK ((planned_user_count > 0));
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_signup_intent_id_fkey FOREIGN KEY (signup_intent_id) REFERENCES signup_intents(id);
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_stripe_subscription_id_key UNIQUE (stripe_subscription_id);
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.tenant_subscriptions ADD CONSTRAINT tenant_subscriptions_tenant_id_key UNIQUE (tenant_id);

-- Table: public.user_workstreams
CREATE TABLE public.user_workstreams (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  user_id uuid NOT NULL,
  workstream_id uuid NOT NULL
);

ALTER TABLE public.user_workstreams ADD CONSTRAINT user_workstreams_pkey PRIMARY KEY (id);
ALTER TABLE public.user_workstreams ADD CONSTRAINT user_workstreams_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);
ALTER TABLE public.user_workstreams ADD CONSTRAINT user_workstreams_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE public.user_workstreams ADD CONSTRAINT user_workstreams_user_id_workstream_id_key UNIQUE (user_id, workstream_id);
ALTER TABLE public.user_workstreams ADD CONSTRAINT user_workstreams_workstream_id_fkey FOREIGN KEY (workstream_id) REFERENCES workstreams(id) ON DELETE CASCADE;

-- Table: public.users
CREATE TABLE public.users (
  id uuid NOT NULL,
  tenant_id uuid NOT NULL,
  email text NOT NULL,
  display_name text,
  phone text,
  title text,
  department text,
  market text,
  timezone text DEFAULT 'UTC'::text,
  role text NOT NULL,
  status text DEFAULT 'active'::text NOT NULL,
  last_login_at timestamp with time zone,
  onboarding_completed boolean DEFAULT false,
  created_at timestamp with time zone DEFAULT now() NOT NULL,
  updated_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.users ADD CONSTRAINT users_id_fkey FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.users ADD CONSTRAINT users_pkey PRIMARY KEY (id);
ALTER TABLE public.users ADD CONSTRAINT users_role_check CHECK ((role = ANY (ARRAY['transformation_office'::text, 'initiative_owner'::text, 'viewer'::text])));
ALTER TABLE public.users ADD CONSTRAINT users_status_check CHECK ((status = ANY (ARRAY['active'::text, 'ghost'::text, 'deactivated'::text])));
ALTER TABLE public.users ADD CONSTRAINT users_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Table: public.workstreams
CREATE TABLE public.workstreams (
  id uuid DEFAULT gen_random_uuid() NOT NULL,
  tenant_id uuid NOT NULL,
  business_unit_id uuid,
  name text NOT NULL,
  created_at timestamp with time zone DEFAULT now() NOT NULL
);

ALTER TABLE public.workstreams ADD CONSTRAINT workstreams_business_unit_id_fkey FOREIGN KEY (business_unit_id) REFERENCES business_units(id);
ALTER TABLE public.workstreams ADD CONSTRAINT workstreams_pkey PRIMARY KEY (id);
ALTER TABLE public.workstreams ADD CONSTRAINT workstreams_tenant_id_fkey FOREIGN KEY (tenant_id) REFERENCES organizations(id);

-- Indexes
CREATE UNIQUE INDEX action_items_pkey ON public.action_items USING btree (id);
CREATE INDEX ai_assignee_idx ON public.action_items USING btree (tenant_id, assignee_id) WHERE (status <> 'completed'::text);
CREATE INDEX ai_session_idx ON public.action_items USING btree (session_id);
CREATE UNIQUE INDEX agenda_items_pkey ON public.agenda_items USING btree (id);
CREATE INDEX agenda_meeting_idx ON public.agenda_items USING btree (meeting_id);
CREATE INDEX aal_tenant_agent_idx ON public.agent_audit_log USING btree (tenant_id, agent_id, created_at DESC);
CREATE UNIQUE INDEX agent_audit_log_pkey ON public.agent_audit_log USING btree (id);
CREATE INDEX ac_tenant_agent_idx ON public.agent_corrections USING btree (tenant_id, agent_id, created_at DESC);
CREATE UNIQUE INDEX agent_corrections_pkey ON public.agent_corrections USING btree (id);
CREATE UNIQUE INDEX agent_metrics_pkey ON public.agent_metrics USING btree (id);
CREATE UNIQUE INDEX agent_metrics_tenant_metric_date_agent_id_key ON public.agent_metrics USING btree (tenant_id, metric_date, agent_id);
CREATE INDEX am_tenant_agent_idx ON public.agent_metrics USING btree (tenant_id, agent_id, metric_date DESC);
CREATE INDEX alog_entity_idx ON public.audit_log USING btree (tenant_id, entity_type, entity_id, created_at DESC);
CREATE INDEX alog_tenant_idx ON public.audit_log USING btree (tenant_id, created_at DESC);
CREATE UNIQUE INDEX audit_log_pkey ON public.audit_log USING btree (id);
CREATE INDEX bus_tenant_idx ON public.business_units USING btree (tenant_id);
CREATE UNIQUE INDEX business_units_pkey ON public.business_units USING btree (id);
CREATE INDEX fca_tenant_initiative_idx ON public.financial_cell_assumptions USING btree (tenant_id, initiative_id);
CREATE UNIQUE INDEX financial_cell_assumptions_pkey ON public.financial_cell_assumptions USING btree (id);
CREATE UNIQUE INDEX financial_cell_assumptions_tenant_id_initiative_id_row_key__key ON public.financial_cell_assumptions USING btree (tenant_id, initiative_id, row_key, column_key);
CREATE UNIQUE INDEX financial_config_groups_pkey ON public.financial_config_groups USING btree (id);
CREATE UNIQUE INDEX financial_config_groups_tenant_id_key_key ON public.financial_config_groups USING btree (tenant_id, key);
CREATE INDEX financial_config_groups_tenant_idx ON public.financial_config_groups USING btree (tenant_id, kind, display_order);
CREATE INDEX financial_config_items_group_idx ON public.financial_config_items USING btree (group_id, display_order);
CREATE UNIQUE INDEX financial_config_items_pkey ON public.financial_config_items USING btree (id);
CREATE UNIQUE INDEX financial_config_items_tenant_id_key_key ON public.financial_config_items USING btree (tenant_id, key);
CREATE INDEX financial_config_items_tenant_idx ON public.financial_config_items USING btree (tenant_id, item_type, display_order);
CREATE UNIQUE INDEX cl_unique_period_name ON public.financial_cost_lines USING btree (initiative_id, name, year, quarter, month);
CREATE INDEX cost_lines_category_idx ON public.financial_cost_lines USING btree (tenant_id, category_key);
CREATE INDEX cost_lines_initiative_idx ON public.financial_cost_lines USING btree (initiative_id);
CREATE UNIQUE INDEX financial_cost_lines_pkey ON public.financial_cost_lines USING btree (id);
CREATE INDEX fin_initiative_idx ON public.financial_entries USING btree (initiative_id);
CREATE INDEX fin_tenant_initiative_year_month_idx ON public.financial_entries USING btree (tenant_id, initiative_id, year, month);
CREATE UNIQUE INDEX financial_entries_pkey ON public.financial_entries USING btree (id);
CREATE UNIQUE INDEX financial_entries_tenant_initiative_year_period_key ON public.financial_entries USING btree (tenant_id, initiative_id, year, quarter, month) NULLS NOT DISTINCT;
CREATE UNIQUE INDEX financial_entries_unique_period ON public.financial_entries USING btree (initiative_id, year, quarter, month);
CREATE UNIQUE INDEX gate_criteria_pkey ON public.gate_criteria USING btree (id);
CREATE UNIQUE INDEX gate_criteria_tenant_id_gate_number_criterion_id_key ON public.gate_criteria USING btree (tenant_id, gate_number, criterion_id);
CREATE INDEX gc_tenant_gate_idx ON public.gate_criteria USING btree (tenant_id, gate_number);
CREATE UNIQUE INDEX gate_submissions_pkey ON public.gate_submissions USING btree (id);
CREATE INDEX gs_initiative_idx ON public.gate_submissions USING btree (initiative_id);
CREATE INDEX gs_tenant_decision_idx ON public.gate_submissions USING btree (tenant_id, decision);
CREATE UNIQUE INDEX initiative_team_initiative_id_user_id_key ON public.initiative_team USING btree (initiative_id, user_id);
CREATE UNIQUE INDEX initiative_team_pkey ON public.initiative_team USING btree (id);
CREATE INDEX it_init_idx ON public.initiative_team USING btree (initiative_id);
CREATE INDEX it_tenant_idx ON public.initiative_team USING btree (tenant_id);
CREATE INDEX initiatives_owner_idx ON public.initiatives USING btree (tenant_id, owner_id);
CREATE UNIQUE INDEX initiatives_pkey ON public.initiatives USING btree (id);
CREATE UNIQUE INDEX initiatives_tenant_id_initiative_code_key ON public.initiatives USING btree (tenant_id, initiative_code);
CREATE INDEX initiatives_tenant_idx ON public.initiatives USING btree (tenant_id);
CREATE INDEX initiatives_tenant_rag_idx ON public.initiatives USING btree (tenant_id, rag_status) WHERE (archived_at IS NULL);
CREATE INDEX initiatives_tenant_stage_idx ON public.initiatives USING btree (tenant_id, stage) WHERE (archived_at IS NULL);
CREATE UNIQUE INDEX kpi_entries_kpi_id_year_quarter_key ON public.kpi_entries USING btree (kpi_id, year, quarter);
CREATE INDEX kpi_entries_kpi_idx ON public.kpi_entries USING btree (kpi_id);
CREATE UNIQUE INDEX kpi_entries_pkey ON public.kpi_entries USING btree (id);
CREATE INDEX kpis_initiative_idx ON public.kpis USING btree (initiative_id);
CREATE UNIQUE INDEX kpis_pkey ON public.kpis USING btree (id);
CREATE UNIQUE INDEX meeting_attendees_meeting_id_user_id_key ON public.meeting_attendees USING btree (meeting_id, user_id);
CREATE UNIQUE INDEX meeting_attendees_pkey ON public.meeting_attendees USING btree (id);
CREATE UNIQUE INDEX meeting_initiatives_meeting_id_initiative_id_key ON public.meeting_initiatives USING btree (meeting_id, initiative_id);
CREATE UNIQUE INDEX meeting_initiatives_pkey ON public.meeting_initiatives USING btree (id);
CREATE UNIQUE INDEX meeting_sessions_pkey ON public.meeting_sessions USING btree (id);
CREATE INDEX sessions_meeting_idx ON public.meeting_sessions USING btree (meeting_id);
CREATE UNIQUE INDEX meetings_pkey ON public.meetings USING btree (id);
CREATE INDEX meetings_tenant_idx ON public.meetings USING btree (tenant_id);
CREATE INDEX checklist_milestone_idx ON public.milestone_checklist USING btree (milestone_id);
CREATE UNIQUE INDEX milestone_checklist_pkey ON public.milestone_checklist USING btree (id);
CREATE INDEX deps_downstream_idx ON public.milestone_dependencies USING btree (downstream_milestone_id);
CREATE INDEX deps_upstream_idx ON public.milestone_dependencies USING btree (upstream_milestone_id);
CREATE UNIQUE INDEX milestone_dependencies_pkey ON public.milestone_dependencies USING btree (id);
CREATE UNIQUE INDEX milestone_dependencies_upstream_milestone_id_downstream_mil_key ON public.milestone_dependencies USING btree (upstream_milestone_id, downstream_milestone_id);
CREATE INDEX milestones_due_idx ON public.milestones USING btree (tenant_id, planned_end) WHERE (status <> 'complete'::text);
CREATE INDEX milestones_initiative_idx ON public.milestones USING btree (initiative_id);
CREATE INDEX milestones_owner_idx ON public.milestones USING btree (tenant_id, owner_id);
CREATE UNIQUE INDEX milestones_pkey ON public.milestones USING btree (id);
CREATE INDEX milestones_tenant_idx ON public.milestones USING btree (tenant_id);
CREATE INDEX nudge_initiative_idx ON public.nudge_log USING btree (initiative_id);
CREATE UNIQUE INDEX nudge_log_pkey ON public.nudge_log USING btree (id);
CREATE UNIQUE INDEX organizations_pkey ON public.organizations USING btree (id);
CREATE UNIQUE INDEX organizations_slug_key ON public.organizations USING btree (slug);
CREATE INDEX risks_initiative_idx ON public.risks USING btree (initiative_id);
CREATE UNIQUE INDEX risks_pkey ON public.risks USING btree (id);
CREATE INDEX risks_tenant_status_idx ON public.risks USING btree (tenant_id, status);
CREATE UNIQUE INDEX signup_intents_pkey ON public.signup_intents USING btree (id);
CREATE INDEX signup_intents_status_idx ON public.signup_intents USING btree (status, created_at DESC);
CREATE UNIQUE INDEX signup_intents_stripe_checkout_session_id_key ON public.signup_intents USING btree (stripe_checkout_session_id);
CREATE INDEX signup_intents_tenant_idx ON public.signup_intents USING btree (tenant_id);
CREATE INDEX gates_initiative_idx ON public.stage_gates USING btree (initiative_id);
CREATE UNIQUE INDEX stage_gates_initiative_id_gate_number_key ON public.stage_gates USING btree (initiative_id, gate_number);
CREATE UNIQUE INDEX stage_gates_pkey ON public.stage_gates USING btree (id);
CREATE UNIQUE INDEX status_updates_pkey ON public.status_updates USING btree (id);
CREATE INDEX su_initiative_idx ON public.status_updates USING btree (initiative_id);
CREATE INDEX su_submitted_idx ON public.status_updates USING btree (tenant_id, submitted_at DESC) WHERE (NOT is_draft);
CREATE INDEX sub_plans_tenant_idx ON public.subscription_plans USING btree (tenant_id);
CREATE UNIQUE INDEX subscription_plans_pkey ON public.subscription_plans USING btree (id);
CREATE UNIQUE INDEX subscription_plans_tenant_id_code_billing_interval_key ON public.subscription_plans USING btree (tenant_id, code, billing_interval);
CREATE UNIQUE INDEX tenant_subscriptions_pkey ON public.tenant_subscriptions USING btree (id);
CREATE UNIQUE INDEX tenant_subscriptions_stripe_subscription_id_key ON public.tenant_subscriptions USING btree (stripe_subscription_id);
CREATE UNIQUE INDEX tenant_subscriptions_tenant_id_key ON public.tenant_subscriptions USING btree (tenant_id);
CREATE INDEX tenant_subscriptions_tenant_idx ON public.tenant_subscriptions USING btree (tenant_id);
CREATE UNIQUE INDEX user_workstreams_pkey ON public.user_workstreams USING btree (id);
CREATE UNIQUE INDEX user_workstreams_user_id_workstream_id_key ON public.user_workstreams USING btree (user_id, workstream_id);
CREATE INDEX uw_tenant_idx ON public.user_workstreams USING btree (tenant_id);
CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);
CREATE INDEX users_tenant_idx ON public.users USING btree (tenant_id);
CREATE INDEX users_tenant_role_idx ON public.users USING btree (tenant_id, role);
CREATE UNIQUE INDEX workstreams_pkey ON public.workstreams USING btree (id);
CREATE INDEX workstreams_tenant_idx ON public.workstreams USING btree (tenant_id);

-- RLS policies
CREATE POLICY ai_delete ON public.action_items AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ai_insert ON public.action_items AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ai_select ON public.action_items AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ai_update ON public.action_items AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ag_delete ON public.agenda_items AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ag_insert ON public.agenda_items AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ag_select ON public.agenda_items AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ag_update ON public.agenda_items AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY aal_insert ON public.agent_audit_log AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY aal_select ON public.agent_audit_log AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ac_insert ON public.agent_corrections AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ac_select ON public.agent_corrections AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY am_insert ON public.agent_metrics AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY am_select ON public.agent_metrics AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY am_update ON public.agent_metrics AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY alog_insert ON public.audit_log AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY alog_select ON public.audit_log AS PERMISSIVE FOR SELECT TO public USING (((tenant_id = current_tenant_id()) AND (current_user_role() = 'transformation_office'::text)));
CREATE POLICY bus_delete ON public.business_units AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY bus_insert ON public.business_units AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY bus_select ON public.business_units AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY bus_update ON public.business_units AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fca_delete ON public.financial_cell_assumptions AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fca_insert ON public.financial_cell_assumptions AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY fca_select ON public.financial_cell_assumptions AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fca_update ON public.financial_cell_assumptions AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fcg_delete ON public.financial_config_groups AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fcg_insert ON public.financial_config_groups AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY fcg_select ON public.financial_config_groups AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fcg_update ON public.financial_config_groups AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fci_delete ON public.financial_config_items AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fci_insert ON public.financial_config_items AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY fci_select ON public.financial_config_items AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fci_update ON public.financial_config_items AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY cl_delete ON public.financial_cost_lines AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY cl_insert ON public.financial_cost_lines AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY cl_select ON public.financial_cost_lines AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY cl_update ON public.financial_cost_lines AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fin_delete ON public.financial_entries AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fin_insert ON public.financial_entries AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY fin_select ON public.financial_entries AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY fin_update ON public.financial_entries AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY gc_insert ON public.gate_criteria AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY gc_select ON public.gate_criteria AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY gc_update ON public.gate_criteria AS PERMISSIVE FOR UPDATE TO public USING (((tenant_id = current_tenant_id()) AND (current_user_role() = 'transformation_office'::text)));
CREATE POLICY gs_insert ON public.gate_submissions AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY gs_select ON public.gate_submissions AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY gs_update ON public.gate_submissions AS PERMISSIVE FOR UPDATE TO public USING (((tenant_id = current_tenant_id()) AND (current_user_role() = 'transformation_office'::text)));
CREATE POLICY it_delete ON public.initiative_team AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = ( SELECT users.tenant_id
   FROM users
  WHERE (users.id = auth.uid()))));
CREATE POLICY it_insert ON public.initiative_team AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = ( SELECT users.tenant_id
   FROM users
  WHERE (users.id = auth.uid()))));
CREATE POLICY it_select ON public.initiative_team AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = ( SELECT users.tenant_id
   FROM users
  WHERE (users.id = auth.uid()))));
CREATE POLICY it_update ON public.initiative_team AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = ( SELECT users.tenant_id
   FROM users
  WHERE (users.id = auth.uid()))));
CREATE POLICY init_delete ON public.initiatives AS PERMISSIVE FOR DELETE TO public USING (((tenant_id = current_tenant_id()) AND (current_user_role() = 'transformation_office'::text)));
CREATE POLICY init_insert ON public.initiatives AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY init_select ON public.initiatives AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY init_update ON public.initiatives AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpie_delete ON public.kpi_entries AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpie_insert ON public.kpi_entries AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY kpie_select ON public.kpi_entries AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpie_update ON public.kpi_entries AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpi_delete ON public.kpis AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpi_insert ON public.kpis AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY kpi_select ON public.kpis AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY kpi_update ON public.kpis AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ma_delete ON public.meeting_attendees AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ma_insert ON public.meeting_attendees AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ma_select ON public.meeting_attendees AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY mi_delete ON public.meeting_initiatives AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY mi_insert ON public.meeting_initiatives AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY mi_select ON public.meeting_initiatives AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY sess_delete ON public.meeting_sessions AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY sess_insert ON public.meeting_sessions AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY sess_select ON public.meeting_sessions AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY sess_update ON public.meeting_sessions AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY mtg_delete ON public.meetings AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY mtg_insert ON public.meetings AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY mtg_select ON public.meetings AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY mtg_update ON public.meetings AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY chk_delete ON public.milestone_checklist AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY chk_insert ON public.milestone_checklist AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY chk_select ON public.milestone_checklist AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY chk_update ON public.milestone_checklist AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY deps_delete ON public.milestone_dependencies AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY deps_insert ON public.milestone_dependencies AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY deps_select ON public.milestone_dependencies AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ms_delete ON public.milestones AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ms_insert ON public.milestones AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ms_select ON public.milestones AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ms_update ON public.milestones AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY nudge_insert ON public.nudge_log AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY nudge_select ON public.nudge_log AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY orgs_select ON public.organizations AS PERMISSIVE FOR SELECT TO public USING ((id = current_tenant_id()));
CREATE POLICY risk_delete ON public.risks AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY risk_insert ON public.risks AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY risk_select ON public.risks AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY risk_update ON public.risks AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY signup_intents_insert ON public.signup_intents AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY signup_intents_select ON public.signup_intents AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY signup_intents_update ON public.signup_intents AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY gates_insert ON public.stage_gates AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY gates_select ON public.stage_gates AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY gates_update ON public.stage_gates AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY su_delete ON public.status_updates AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY su_insert ON public.status_updates AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY su_select ON public.status_updates AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY su_update ON public.status_updates AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY sub_plans_insert ON public.subscription_plans AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY sub_plans_select ON public.subscription_plans AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY sub_plans_update ON public.subscription_plans AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_subs_insert ON public.tenant_subscriptions AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_subs_select ON public.tenant_subscriptions AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY tenant_subs_update ON public.tenant_subscriptions AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id())) WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY uw_delete ON public.user_workstreams AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY uw_insert ON public.user_workstreams AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY uw_select ON public.user_workstreams AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY users_insert ON public.users AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY users_select ON public.users AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY users_update ON public.users AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ws_delete ON public.workstreams AS PERMISSIVE FOR DELETE TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ws_insert ON public.workstreams AS PERMISSIVE FOR INSERT TO public WITH CHECK ((tenant_id = current_tenant_id()));
CREATE POLICY ws_select ON public.workstreams AS PERMISSIVE FOR SELECT TO public USING ((tenant_id = current_tenant_id()));
CREATE POLICY ws_update ON public.workstreams AS PERMISSIVE FOR UPDATE TO public USING ((tenant_id = current_tenant_id()));

