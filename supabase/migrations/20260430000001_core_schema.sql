-- Transmuter core schema migration
-- Covers all 21 entities from domain_packs/transmuter/entities.yaml
-- Rules: tenant_id NOT NULL on every table, NUMERIC(15,4) for money,
--        RLS enabled on every table, UUID PK via gen_random_uuid()

-- ─────────────────────────────────────────────────────────────────────────────
-- HELPER FUNCTION: extract tenant_id from JWT claim
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS uuid
  LANGUAGE sql STABLE
  AS $$ SELECT (auth.jwt() ->> 'tenant_id')::uuid $$;

CREATE OR REPLACE FUNCTION current_user_role() RETURNS text
  LANGUAGE sql STABLE
  AS $$ SELECT auth.jwt() ->> 'role' $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. ORGANIZATIONS (tenants)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE organizations (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name       TEXT NOT NULL,
  slug       TEXT NOT NULL UNIQUE,
  logo_url   TEXT,
  settings   JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
-- Org members can read their own org; only service role can write
CREATE POLICY "orgs_select" ON organizations FOR SELECT
  USING (id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 1A. BILLING / SUBSCRIPTION RECORDS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE subscription_plans (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES organizations(id),
  code              TEXT NOT NULL CHECK (code IN ('team','business','enterprise')),
  name              TEXT NOT NULL,
  user_limit_min    INTEGER NOT NULL CHECK (user_limit_min > 0),
  user_limit_max    INTEGER CHECK (user_limit_max IS NULL OR user_limit_max >= user_limit_min),
  amount_cents      INTEGER CHECK (amount_cents IS NULL OR amount_cents >= 0),
  currency          TEXT NOT NULL DEFAULT 'usd',
  billing_interval  TEXT NOT NULL DEFAULT 'month' CHECK (billing_interval IN ('month','year','custom')),
  stripe_price_id   TEXT,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, code, billing_interval)
);

CREATE INDEX sub_plans_tenant_idx ON subscription_plans(tenant_id);
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sub_plans_select" ON subscription_plans FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "sub_plans_insert" ON subscription_plans FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "sub_plans_update" ON subscription_plans FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE signup_intents (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                  UUID NOT NULL REFERENCES organizations(id),
  organization_name          TEXT NOT NULL,
  organization_slug          TEXT NOT NULL,
  admin_email                TEXT NOT NULL,
  admin_display_name         TEXT NOT NULL,
  planned_user_count         INTEGER NOT NULL CHECK (planned_user_count > 0),
  plan_code                  TEXT NOT NULL CHECK (plan_code IN ('team','business','enterprise')),
  billing_interval           TEXT NOT NULL DEFAULT 'month' CHECK (billing_interval IN ('month','year','custom')),
  status                     TEXT NOT NULL DEFAULT 'pending_checkout'
    CHECK (status IN ('pending_checkout','checkout_created','paid','provisioned','failed','abandoned')),
  stripe_checkout_session_id TEXT UNIQUE,
  stripe_customer_id         TEXT,
  stripe_subscription_id     TEXT,
  metadata                   JSONB DEFAULT '{}'::jsonb,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX signup_intents_tenant_idx ON signup_intents(tenant_id);
CREATE INDEX signup_intents_status_idx ON signup_intents(status, created_at DESC);
ALTER TABLE signup_intents ENABLE ROW LEVEL SECURITY;
CREATE POLICY "signup_intents_select" ON signup_intents FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "signup_intents_insert" ON signup_intents FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "signup_intents_update" ON signup_intents FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE tenant_subscriptions (
  id                         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id                  UUID NOT NULL REFERENCES organizations(id),
  plan_id                    UUID REFERENCES subscription_plans(id),
  signup_intent_id           UUID REFERENCES signup_intents(id),
  provider                   TEXT NOT NULL DEFAULT 'stripe',
  status                     TEXT NOT NULL DEFAULT 'not_configured',
  checkout_status            TEXT,
  payment_status             TEXT,
  planned_user_count         INTEGER NOT NULL DEFAULT 1 CHECK (planned_user_count > 0),
  stripe_customer_id         TEXT,
  stripe_subscription_id     TEXT UNIQUE,
  stripe_checkout_session_id TEXT,
  current_period_end         TIMESTAMPTZ,
  cancel_at_period_end       BOOLEAN NOT NULL DEFAULT FALSE,
  metadata                   JSONB DEFAULT '{}'::jsonb,
  created_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id)
);

CREATE INDEX tenant_subscriptions_tenant_idx ON tenant_subscriptions(tenant_id);
ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "tenant_subs_select" ON tenant_subscriptions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "tenant_subs_insert" ON tenant_subscriptions FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "tenant_subs_update" ON tenant_subscriptions FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. USERS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE users (
  id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  tenant_id    UUID NOT NULL REFERENCES organizations(id),
  email        TEXT NOT NULL,           -- PII: never send to LLM
  display_name TEXT,                    -- PII
  phone        TEXT,                    -- PII
  title        TEXT,
  department   TEXT,
  market       TEXT,
  timezone     TEXT DEFAULT 'UTC',
  role         TEXT NOT NULL CHECK (role IN ('transformation_office','initiative_owner','viewer')),
  status       TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','ghost','deactivated')),
  last_login_at TIMESTAMPTZ,
  onboarding_completed BOOLEAN DEFAULT FALSE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX users_tenant_idx ON users(tenant_id);
CREATE INDEX users_tenant_role_idx ON users(tenant_id, role);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
CREATE POLICY "users_select" ON users FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "users_insert" ON users FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "users_update" ON users FOR UPDATE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. BUSINESS UNITS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE business_units (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  UUID NOT NULL REFERENCES organizations(id),
  name       TEXT NOT NULL,
  code       TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX bus_tenant_idx ON business_units(tenant_id);
ALTER TABLE business_units ENABLE ROW LEVEL SECURITY;
CREATE POLICY "bus_select" ON business_units FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "bus_insert" ON business_units FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "bus_update" ON business_units FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "bus_delete" ON business_units FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. WORKSTREAMS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE workstreams (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES organizations(id),
  business_unit_id UUID REFERENCES business_units(id),
  name             TEXT NOT NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX workstreams_tenant_idx ON workstreams(tenant_id);
ALTER TABLE workstreams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ws_select" ON workstreams FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ws_insert" ON workstreams FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ws_update" ON workstreams FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "ws_delete" ON workstreams FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. USER ↔ WORKSTREAM ASSIGNMENTS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE user_workstreams (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  user_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  workstream_id UUID NOT NULL REFERENCES workstreams(id) ON DELETE CASCADE,
  UNIQUE (user_id, workstream_id)
);

CREATE INDEX uw_tenant_idx ON user_workstreams(tenant_id);
ALTER TABLE user_workstreams ENABLE ROW LEVEL SECURITY;
CREATE POLICY "uw_select" ON user_workstreams FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "uw_insert" ON user_workstreams FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "uw_delete" ON user_workstreams FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 6. INITIATIVES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE initiatives (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES organizations(id),
  initiative_code  TEXT NOT NULL,   -- e.g. TRN-001, unique per tenant
  name             TEXT NOT NULL,
  workstream_id    UUID REFERENCES workstreams(id),
  owner_id         UUID REFERENCES users(id),
  group_owner_id   UUID REFERENCES users(id),
  type             TEXT CHECK (type IN ('revenue_growth','cost_reduction','cost_avoidance','compliance','capability_building')),
  impact_type      TEXT CHECK (impact_type IN ('recurring','one_off')),
  theme            TEXT,
  country          TEXT,
  tag              TEXT CHECK (tag IN ('automation','offshoring','commercial','other')),
  priority         TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
  rag_status       TEXT NOT NULL DEFAULT 'green' CHECK (rag_status IN ('red','amber','green')),
  stage            TEXT NOT NULL DEFAULT 'scoping' CHECK (stage IN ('scoping','in_progress','complete')),
  summary          TEXT,
  value_logic      TEXT,
  dependencies_text TEXT,
  planned_start    DATE,
  actual_start     DATE,
  planned_end      DATE,
  actual_end       DATE,
  -- Pressure score (recalculated on save)
  pressure_score   NUMERIC(4,1),
  pressure_sub     JSONB DEFAULT '{}'::jsonb,
  pressure_updated_at TIMESTAMPTZ,
  archived_at      TIMESTAMPTZ,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, initiative_code)
);

CREATE INDEX initiatives_tenant_idx ON initiatives(tenant_id);
CREATE INDEX initiatives_tenant_stage_idx ON initiatives(tenant_id, stage) WHERE archived_at IS NULL;
CREATE INDEX initiatives_tenant_rag_idx ON initiatives(tenant_id, rag_status) WHERE archived_at IS NULL;
CREATE INDEX initiatives_owner_idx ON initiatives(tenant_id, owner_id);

ALTER TABLE initiatives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "init_select" ON initiatives FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "init_insert" ON initiatives FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "init_update" ON initiatives FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "init_delete" ON initiatives FOR DELETE USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 7. MILESTONES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE milestones (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id      UUID NOT NULL REFERENCES organizations(id),
  initiative_id  UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  name           TEXT NOT NULL,
  description    TEXT,
  owner_id       UUID REFERENCES users(id),
  priority       TEXT NOT NULL DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
  status         TEXT NOT NULL DEFAULT 'not_started' CHECK (status IN ('not_started','in_progress','complete','overdue')),
  sort_order     INTEGER DEFAULT 0,
  planned_start  DATE,
  actual_start   DATE,
  planned_end    DATE,
  actual_end     DATE,
  -- Pressure sub-scores stored for UI tooltip
  pressure_score         NUMERIC(4,1),
  pressure_blast_radius  NUMERIC(4,2),
  pressure_dep_urgency   NUMERIC(4,2),
  pressure_cluster       NUMERIC(4,2),
  pressure_slack         NUMERIC(4,2),
  pressure_checklist     NUMERIC(4,2),
  pressure_self_status   NUMERIC(4,2),
  pressure_updated_at    TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX milestones_initiative_idx ON milestones(initiative_id);
CREATE INDEX milestones_tenant_idx ON milestones(tenant_id);
CREATE INDEX milestones_owner_idx ON milestones(tenant_id, owner_id);
CREATE INDEX milestones_due_idx ON milestones(tenant_id, planned_end) WHERE status != 'complete';

ALTER TABLE milestones ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ms_select" ON milestones FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ms_insert" ON milestones FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ms_update" ON milestones FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "ms_delete" ON milestones FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 8. MILESTONE CHECKLIST ITEMS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE milestone_checklist (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id    UUID NOT NULL REFERENCES organizations(id),
  milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  text         TEXT NOT NULL,
  completed    BOOLEAN NOT NULL DEFAULT FALSE,
  sort_order   INTEGER DEFAULT 0,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX checklist_milestone_idx ON milestone_checklist(milestone_id);
ALTER TABLE milestone_checklist ENABLE ROW LEVEL SECURITY;
CREATE POLICY "chk_select" ON milestone_checklist FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "chk_insert" ON milestone_checklist FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "chk_update" ON milestone_checklist FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "chk_delete" ON milestone_checklist FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 9. MILESTONE DEPENDENCIES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE milestone_dependencies (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id            UUID NOT NULL REFERENCES organizations(id),
  upstream_milestone_id   UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  downstream_milestone_id UUID NOT NULL REFERENCES milestones(id) ON DELETE CASCADE,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  -- Prevent self-reference and duplicates
  CHECK (upstream_milestone_id != downstream_milestone_id),
  UNIQUE (upstream_milestone_id, downstream_milestone_id)
);

CREATE INDEX deps_upstream_idx ON milestone_dependencies(upstream_milestone_id);
CREATE INDEX deps_downstream_idx ON milestone_dependencies(downstream_milestone_id);
ALTER TABLE milestone_dependencies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "deps_select" ON milestone_dependencies FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "deps_insert" ON milestone_dependencies FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "deps_delete" ON milestone_dependencies FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 10. KPIs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE kpis (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  type          TEXT CHECK (type IN ('gross_margin','operational','custom')),
  category      TEXT,
  frequency     TEXT NOT NULL DEFAULT 'quarterly' CHECK (frequency IN ('quarterly','monthly','annual')),
  unit          TEXT,   -- '%', 'USD', 'Hours', etc.
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX kpis_initiative_idx ON kpis(initiative_id);
ALTER TABLE kpis ENABLE ROW LEVEL SECURITY;
CREATE POLICY "kpi_select" ON kpis FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "kpi_insert" ON kpis FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "kpi_update" ON kpis FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "kpi_delete" ON kpis FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 11. KPI ENTRIES (values per period)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE kpi_entries (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  kpi_id        UUID NOT NULL REFERENCES kpis(id) ON DELETE CASCADE,
  year          INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2040),
  quarter       INTEGER CHECK (quarter BETWEEN 1 AND 4),  -- null = full year
  value_base    NUMERIC(15,4),
  value_high    NUMERIC(15,4),
  value_actual  NUMERIC(15,4),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (kpi_id, year, quarter)
);

CREATE INDEX kpi_entries_kpi_idx ON kpi_entries(kpi_id);
ALTER TABLE kpi_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "kpie_select" ON kpi_entries FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "kpie_insert" ON kpi_entries FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "kpie_update" ON kpi_entries FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "kpie_delete" ON kpi_entries FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 12. RISKS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE risks (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  description   TEXT NOT NULL,
  type          TEXT CHECK (type IN ('operational','people','financial','technology')),
  impact        TEXT CHECK (impact IN ('high','medium','low')),
  likelihood    TEXT CHECK (likelihood IN ('high','medium','low')),
  rating        TEXT CHECK (rating IN ('high','medium','low')),  -- auto-derived
  status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','closed')),
  owner_id      UUID REFERENCES users(id),
  mitigation    TEXT,
  escalated     BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX risks_initiative_idx ON risks(initiative_id);
CREATE INDEX risks_tenant_status_idx ON risks(tenant_id, status);
ALTER TABLE risks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "risk_select" ON risks FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "risk_insert" ON risks FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "risk_update" ON risks FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "risk_delete" ON risks FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 13. FINANCIAL ENTRIES (multi-year quarterly)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE financial_entries (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id             UUID NOT NULL REFERENCES organizations(id),
  initiative_id         UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  year                  INTEGER NOT NULL CHECK (year BETWEEN 2020 AND 2040),
  quarter               INTEGER CHECK (quarter BETWEEN 1 AND 4),  -- null = full year row
  revenue_uplift_base   NUMERIC(15,4) DEFAULT 0,
  revenue_uplift_high   NUMERIC(15,4) DEFAULT 0,
  revenue_uplift_actual NUMERIC(15,4),
  gross_margin_base     NUMERIC(15,4) DEFAULT 0,
  gross_margin_high     NUMERIC(15,4) DEFAULT 0,
  gross_margin_actual   NUMERIC(15,4),
  gm_pct_base           NUMERIC(8,4) DEFAULT 0,
  gm_pct_high           NUMERIC(8,4) DEFAULT 0,
  gm_pct_actual         NUMERIC(8,4),
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (initiative_id, year, quarter)
);

CREATE INDEX fin_initiative_idx ON financial_entries(initiative_id);
ALTER TABLE financial_entries ENABLE ROW LEVEL SECURITY;
CREATE POLICY "fin_select" ON financial_entries FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "fin_insert" ON financial_entries FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "fin_update" ON financial_entries FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "fin_delete" ON financial_entries FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 14. FINANCIAL COST LINES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE financial_cost_lines (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  name          TEXT NOT NULL,
  year          INTEGER NOT NULL,
  quarter       INTEGER CHECK (quarter BETWEEN 1 AND 4),
  amount_plan   NUMERIC(15,4) DEFAULT 0,
  amount_actual NUMERIC(15,4),
  is_recurring  BOOLEAN DEFAULT FALSE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX cost_lines_initiative_idx ON financial_cost_lines(initiative_id);
ALTER TABLE financial_cost_lines ENABLE ROW LEVEL SECURITY;
CREATE POLICY "cl_select" ON financial_cost_lines FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "cl_insert" ON financial_cost_lines FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "cl_update" ON financial_cost_lines FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "cl_delete" ON financial_cost_lines FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 15. STATUS UPDATES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE status_updates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  author_id     UUID NOT NULL REFERENCES users(id),
  rag_status    TEXT NOT NULL CHECK (rag_status IN ('red','amber','green')),
  summary       TEXT NOT NULL,
  achievements  TEXT,
  issues        TEXT,
  next_steps    TEXT,
  is_draft      BOOLEAN NOT NULL DEFAULT TRUE,
  submitted_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX su_initiative_idx ON status_updates(initiative_id);
CREATE INDEX su_submitted_idx ON status_updates(tenant_id, submitted_at DESC) WHERE NOT is_draft;
ALTER TABLE status_updates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "su_select" ON status_updates FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "su_insert" ON status_updates FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "su_update" ON status_updates FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "su_delete" ON status_updates FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 16. NUDGE LOG
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE nudge_log (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  sent_by_id    UUID REFERENCES users(id),
  channel       TEXT DEFAULT 'email' CHECK (channel IN ('email','in_app','both')),
  sent_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX nudge_initiative_idx ON nudge_log(initiative_id);
ALTER TABLE nudge_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "nudge_select" ON nudge_log FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "nudge_insert" ON nudge_log FOR INSERT WITH CHECK (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 17. STAGE GATES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE stage_gates (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  gate_number   INTEGER NOT NULL CHECK (gate_number IN (1,2)),
  label         TEXT NOT NULL,
  from_stage    TEXT NOT NULL,
  to_stage      TEXT NOT NULL,
  UNIQUE (initiative_id, gate_number)
);

CREATE INDEX gates_initiative_idx ON stage_gates(initiative_id);
ALTER TABLE stage_gates ENABLE ROW LEVEL SECURITY;
CREATE POLICY "gates_select" ON stage_gates FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "gates_insert" ON stage_gates FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "gates_update" ON stage_gates FOR UPDATE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 18. GATE CRITERIA (configurable per tenant — loaded from gates.yaml defaults)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE gate_criteria (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  gate_number   INTEGER NOT NULL CHECK (gate_number IN (1,2)),
  criterion_id  TEXT NOT NULL,    -- e.g. 'g1-01'
  label         TEXT NOT NULL,
  guidance      TEXT,
  sort_order    INTEGER DEFAULT 0,
  is_active     BOOLEAN DEFAULT TRUE,
  UNIQUE (tenant_id, gate_number, criterion_id)
);

CREATE INDEX gc_tenant_gate_idx ON gate_criteria(tenant_id, gate_number);
ALTER TABLE gate_criteria ENABLE ROW LEVEL SECURITY;
CREATE POLICY "gc_select" ON gate_criteria FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "gc_insert" ON gate_criteria FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "gc_update" ON gate_criteria FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 19. GATE SUBMISSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE gate_submissions (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id          UUID NOT NULL REFERENCES organizations(id),
  initiative_id      UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  gate_number        INTEGER NOT NULL,
  submitted_by_id    UUID NOT NULL REFERENCES users(id),
  submitted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  decision           TEXT NOT NULL DEFAULT 'pending' CHECK (decision IN ('pending','approved','rejected','conditional')),
  decided_by_id      UUID REFERENCES users(id),
  decided_at         TIMESTAMPTZ,
  commentary         TEXT,
  criteria_snapshot  JSONB   -- [{criterion_id, label, ticked, ticked_by, ticked_at}]
);

CREATE INDEX gs_initiative_idx ON gate_submissions(initiative_id);
CREATE INDEX gs_tenant_decision_idx ON gate_submissions(tenant_id, decision);
ALTER TABLE gate_submissions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "gs_select" ON gate_submissions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "gs_insert" ON gate_submissions FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "gs_update" ON gate_submissions FOR UPDATE USING (
  tenant_id = current_tenant_id() AND current_user_role() = 'transformation_office'
);


-- ─────────────────────────────────────────────────────────────────────────────
-- 20. MEETINGS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE meetings (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  name          TEXT NOT NULL,
  workstream_id UUID REFERENCES workstreams(id),
  scope         TEXT DEFAULT 'all' CHECK (scope IN ('workstream','all')),
  recurrence    TEXT DEFAULT 'weekly' CHECK (recurrence IN ('weekly','biweekly','monthly','ad_hoc')),
  description   TEXT,
  owner_id      UUID REFERENCES users(id),
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX meetings_tenant_idx ON meetings(tenant_id);
ALTER TABLE meetings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "mtg_select" ON meetings FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "mtg_insert" ON meetings FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "mtg_update" ON meetings FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "mtg_delete" ON meetings FOR DELETE USING (tenant_id = current_tenant_id());


-- Meeting attendees
CREATE TABLE meeting_attendees (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id  UUID NOT NULL REFERENCES organizations(id),
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  UNIQUE (meeting_id, user_id)
);
ALTER TABLE meeting_attendees ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ma_select" ON meeting_attendees FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ma_insert" ON meeting_attendees FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ma_delete" ON meeting_attendees FOR DELETE USING (tenant_id = current_tenant_id());

-- Meeting ↔ Initiative links
CREATE TABLE meeting_initiatives (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  meeting_id    UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  initiative_id UUID NOT NULL REFERENCES initiatives(id) ON DELETE CASCADE,
  UNIQUE (meeting_id, initiative_id)
);
ALTER TABLE meeting_initiatives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "mi_select" ON meeting_initiatives FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "mi_insert" ON meeting_initiatives FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "mi_delete" ON meeting_initiatives FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 21. MEETING SESSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE meeting_sessions (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES organizations(id),
  meeting_id       UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  session_date     DATE NOT NULL,
  status           TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','in_progress','completed')),
  has_transcript   BOOLEAN DEFAULT FALSE,
  ai_optimised     BOOLEAN DEFAULT FALSE,
  transcript_text  TEXT,
  notes            TEXT,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX sessions_meeting_idx ON meeting_sessions(meeting_id);
ALTER TABLE meeting_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "sess_select" ON meeting_sessions FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "sess_insert" ON meeting_sessions FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "sess_update" ON meeting_sessions FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "sess_delete" ON meeting_sessions FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 22. AGENDA ITEMS (persistent — carry forward to next session)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE agenda_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  meeting_id    UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,  -- belongs to series, not session
  initiative_id UUID REFERENCES initiatives(id),
  text          TEXT NOT NULL,
  sort_order    INTEGER DEFAULT 0,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX agenda_meeting_idx ON agenda_items(meeting_id);
ALTER TABLE agenda_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ag_select" ON agenda_items FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ag_insert" ON agenda_items FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ag_update" ON agenda_items FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "ag_delete" ON agenda_items FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 23. ACTION ITEMS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE action_items (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id     UUID NOT NULL REFERENCES organizations(id),
  session_id    UUID NOT NULL REFERENCES meeting_sessions(id) ON DELETE CASCADE,
  initiative_id UUID REFERENCES initiatives(id),
  description   TEXT NOT NULL,
  assignee_id   UUID REFERENCES users(id),
  priority      TEXT DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
  status        TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','completed','cancelled')),
  due_date      DATE,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ai_session_idx ON action_items(session_id);
CREATE INDEX ai_assignee_idx ON action_items(tenant_id, assignee_id) WHERE status != 'completed';
ALTER TABLE action_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ai_select" ON action_items FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ai_insert" ON action_items FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "ai_update" ON action_items FOR UPDATE USING (tenant_id = current_tenant_id());
CREATE POLICY "ai_delete" ON action_items FOR DELETE USING (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 24. AGENT OBSERVABILITY TABLES
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE agent_audit_log (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES organizations(id),
  agent_id          TEXT NOT NULL,        -- e.g. 'netra', 'karya'
  skill_name        TEXT,
  workflow_run_id   UUID,
  action            TEXT,
  confidence        NUMERIC(5,4),
  latency_ms        INTEGER,
  input_summary     TEXT,                 -- no raw PII
  output_summary    TEXT,
  requires_review   BOOLEAN DEFAULT FALSE,
  human_action      TEXT,                 -- 'approved', 'modified', 'rejected'
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX aal_tenant_agent_idx ON agent_audit_log(tenant_id, agent_id, created_at DESC);
ALTER TABLE agent_audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "aal_select" ON agent_audit_log FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "aal_insert" ON agent_audit_log FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
-- No UPDATE or DELETE — append-only

CREATE TABLE agent_corrections (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL REFERENCES organizations(id),
  agent_id          TEXT NOT NULL,
  audit_log_id      UUID REFERENCES agent_audit_log(id),
  agent_prediction  JSONB,
  human_correction  JSONB,
  correction_type   TEXT,   -- 'field_edit', 'full_reject', 'add_item', 'remove_item'
  corrected_by      UUID REFERENCES users(id),
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX ac_tenant_agent_idx ON agent_corrections(tenant_id, agent_id, created_at DESC);
ALTER TABLE agent_corrections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ac_select" ON agent_corrections FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "ac_insert" ON agent_corrections FOR INSERT WITH CHECK (tenant_id = current_tenant_id());

CREATE TABLE agent_metrics (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id        UUID NOT NULL REFERENCES organizations(id),
  metric_date      DATE NOT NULL,
  agent_id         TEXT NOT NULL,
  total_runs       INTEGER DEFAULT 0,
  auto_approved    INTEGER DEFAULT 0,
  hitl_required    INTEGER DEFAULT 0,
  correction_count INTEGER DEFAULT 0,
  avg_latency_ms   NUMERIC(8,2),
  avg_confidence   NUMERIC(5,4),
  UNIQUE (tenant_id, metric_date, agent_id)
);
CREATE INDEX am_tenant_agent_idx ON agent_metrics(tenant_id, agent_id, metric_date DESC);
ALTER TABLE agent_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "am_select" ON agent_metrics FOR SELECT USING (tenant_id = current_tenant_id());
CREATE POLICY "am_insert" ON agent_metrics FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
CREATE POLICY "am_update" ON agent_metrics FOR UPDATE USING (tenant_id = current_tenant_id()) WITH CHECK (tenant_id = current_tenant_id());


-- ─────────────────────────────────────────────────────────────────────────────
-- 25. AUDIT LOG (append-only — all data mutations)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE audit_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id   UUID NOT NULL REFERENCES organizations(id),
  user_id     UUID REFERENCES users(id),
  entity_type TEXT NOT NULL,
  entity_id   UUID NOT NULL,
  action      TEXT NOT NULL CHECK (action IN ('create','update','delete','archive','submit','approve','reject')),
  before_data JSONB,
  after_data  JSONB,
  ip_address  TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
  -- Never UPDATE or DELETE this table
);

CREATE INDEX alog_entity_idx ON audit_log(tenant_id, entity_type, entity_id, created_at DESC);
CREATE INDEX alog_tenant_idx ON audit_log(tenant_id, created_at DESC);
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
CREATE POLICY "alog_select" ON audit_log FOR SELECT USING (
  tenant_id = current_tenant_id()
  AND current_user_role() = 'transformation_office'
);
CREATE POLICY "alog_insert" ON audit_log FOR INSERT WITH CHECK (tenant_id = current_tenant_id());
-- No UPDATE or DELETE policies — truly append-only
