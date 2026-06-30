-- Platform-managed Stripe Price ID configuration.
-- NULL stripe_price_id means no platform override; the API falls back to environment config.

CREATE TABLE IF NOT EXISTS platform_billing_price_config (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id         UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000000',
  plan_code         TEXT NOT NULL CHECK (plan_code IN ('team','business')),
  plan_name         TEXT NOT NULL,
  billing_interval  TEXT NOT NULL CHECK (billing_interval IN ('month','year')),
  amount_cents      INTEGER NOT NULL CHECK (amount_cents > 0),
  currency          TEXT NOT NULL DEFAULT 'usd',
  stripe_price_id   TEXT,
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by        UUID,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (tenant_id, plan_code, billing_interval)
);

CREATE INDEX IF NOT EXISTS platform_billing_price_config_tenant_idx
  ON platform_billing_price_config(tenant_id);

ALTER TABLE platform_billing_price_config ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "platform_billing_price_config_select" ON platform_billing_price_config;
CREATE POLICY "platform_billing_price_config_select"
  ON platform_billing_price_config
  FOR SELECT
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'platform_admin'
  );

DROP POLICY IF EXISTS "platform_billing_price_config_insert" ON platform_billing_price_config;
CREATE POLICY "platform_billing_price_config_insert"
  ON platform_billing_price_config
  FOR INSERT
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'platform_admin'
  );

DROP POLICY IF EXISTS "platform_billing_price_config_update" ON platform_billing_price_config;
CREATE POLICY "platform_billing_price_config_update"
  ON platform_billing_price_config
  FOR UPDATE
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'platform_admin'
  )
  WITH CHECK (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'platform_admin'
  );

DROP POLICY IF EXISTS "platform_billing_price_config_delete" ON platform_billing_price_config;
CREATE POLICY "platform_billing_price_config_delete"
  ON platform_billing_price_config
  FOR DELETE
  USING (
    tenant_id = current_tenant_id()
    AND current_user_role() = 'platform_admin'
  );

INSERT INTO platform_billing_price_config (
  tenant_id,
  plan_code,
  plan_name,
  billing_interval,
  amount_cents,
  currency,
  stripe_price_id
)
VALUES
  (
    '00000000-0000-0000-0000-000000000000',
    'team',
    'Transmuter Team',
    'month',
    99900,
    'usd',
    NULL
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    'team',
    'Transmuter Team',
    'year',
    999000,
    'usd',
    NULL
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    'business',
    'Transmuter Business',
    'month',
    199900,
    'usd',
    NULL
  ),
  (
    '00000000-0000-0000-0000-000000000000',
    'business',
    'Transmuter Business',
    'year',
    1999000,
    'usd',
    NULL
  )
ON CONFLICT (tenant_id, plan_code, billing_interval) DO UPDATE
SET
  plan_name = EXCLUDED.plan_name,
  amount_cents = EXCLUDED.amount_cents,
  currency = EXCLUDED.currency,
  is_active = TRUE,
  updated_at = NOW();
