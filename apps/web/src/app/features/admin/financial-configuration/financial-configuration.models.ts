export type FinancialSubtab = 'settings' | 'metrics' | 'planning' | 'bridge' | 'taxonomy';

export type FinancialMetricOrigin = 'default_catalog' | 'tenant' | 'legacy_default';

export interface FinancialMetricDefinition {
  id?: string;
  key: string;
  label: string;
  description?: string | null;
  group_key?: string | null;
  value_type: 'currency' | 'percent' | 'number';
  unit?: string | null;
  direction?: 'increase_good' | 'decrease_good' | 'neutral';
  aggregation: 'sum' | 'avg' | 'last' | 'formula';
  rollup_type?: string | null;
  is_benefit: boolean;
  benefit_class?: string | null;
  cost_behavior?: string | null;
  formula?: string | null;
  formula_inputs: string[];
  precision: number;
  display_order: number;
  applies_to?: string;
  validation?: Record<string, unknown>;
  origin?: FinancialMetricOrigin | null;
  catalog_version?: string | null;
  semantic_role?: string | null;
  is_system?: boolean;
  is_active: boolean;
  keyManuallyEdited?: boolean;
}

export interface FinancialMetricDeletionReference {
  id: string;
  initiative_id?: string | null;
  initiative_name?: string | null;
  label: string;
}

export interface FinancialMetricDeletionCategory {
  count: number;
  references: FinancialMetricDeletionReference[];
}

export interface FinancialMetricDeletionImpact {
  metric: Pick<
    FinancialMetricDefinition,
    | 'id'
    | 'key'
    | 'label'
    | 'origin'
    | 'catalog_version'
    | 'semantic_role'
    | 'is_system'
    | 'is_active'
  >;
  can_delete: boolean;
  /** @deprecated Compatibility with pre-catalogue deletion-impact responses. */
  blocked_by_system?: boolean;
  blocker_total: number;
  blockers: Record<string, FinancialMetricDeletionCategory>;
  cleanup: { tenant_annual_baselines: FinancialMetricDeletionCategory };
  confirmation_key: string;
}

export interface FinancialBridgeRow {
  id?: string;
  key: string;
  label: string;
  row_kind: 'metric_set' | 'cost_set' | 'subtotal' | 'net';
  metric_definition_ids: string[];
  cost_category_ids: string[];
  cost_category_keys?: string[];
  sign: 1 | -1;
  display_order: number;
  is_active: boolean;
  keyManuallyEdited?: boolean;
}

export interface FinancialScenario {
  id?: string;
  key: string;
  label: string;
  kind: 'baseline' | 'plan' | 'forecast' | 'actual';
  is_primary?: boolean;
  is_system?: boolean;
  is_active: boolean;
  display_order: number;
}

export interface FinancialCostCategory {
  id?: string;
  key: string;
  label: string;
  group_key?: string | null;
  rollup_type?: string | null;
  display_order: number;
  attributes?: Record<string, unknown>;
  is_system?: boolean;
  is_active: boolean;
}

export interface FinancialAttributeDefinition {
  id?: string;
  key: string;
  label: string;
  entity_type: 'benefit_line' | 'cost_line';
  value_type: 'text' | 'number' | 'currency' | 'percent' | 'date' | 'select' | 'boolean';
  options: string[];
  is_required: boolean;
  display_order: number;
  is_active: boolean;
}

export interface FinancialReportingSettings {
  fiscal_year_start_month: number;
  reporting_currency: string;
  recurring_cost_inflation_mode: 'manual_entry' | 'optional_per_line' | 'default_on';
  default_annual_inflation_rate_pct: string | number;
  allow_cost_line_inflation_override: boolean;
}

export interface FinancialEngineConfiguration {
  definitions: FinancialMetricDefinition[];
  scenarios: FinancialScenario[];
  cost_categories: FinancialCostCategory[];
  bridge_rows: FinancialBridgeRow[];
  attribute_definitions: FinancialAttributeDefinition[];
  settings: Partial<FinancialReportingSettings>;
}

export interface AnnualBaselineRow {
  metric_definition_id: string;
  baseline_year: number;
  value: string;
}
