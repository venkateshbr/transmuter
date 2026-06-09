export type FinancialLedgerGranularity = 'weekly' | 'monthly' | 'yearly';

export interface InitiativeOption {
  id: string;
  initiative_code?: string | null;
  name?: string | null;
  stage?: string | null;
  rag_status?: string | null;
  locked?: boolean | null;
  workstream_id?: string | null;
  workstream_name?: string | null;
  workstreams?: {
    name?: string | null;
  } | null;
}

export interface BankablePlanSummary {
  net_value_plan: string;
  net_value_actual?: string | null;
}

export interface BankablePlanSnapshot {
  entries: unknown[];
  cost_lines: unknown[];
  metric_values: unknown[];
  selections: {
    metric_keys: string[];
    cost_category_keys: string[];
  };
  financial_mode?: unknown;
  summary: BankablePlanSummary;
}

export interface BankablePlanVersion {
  id: string;
  initiative_id: string;
  version: number;
  trigger_type: 'approval' | 'rebaseline';
  trigger_submission_id?: string | null;
  locked_by_id?: string | null;
  locked_at: string;
  locked_reason?: string | null;
  snapshot: BankablePlanSnapshot;
}

export interface BankablePlanResponse {
  current: BankablePlanVersion | null;
  history: BankablePlanVersion[];
}

export type FinancialModeKey = 'pre_lock' | 'planned_vs_actual' | 'multi_scenario' | 'bankable_locked';

export interface FinancialModeDescriptor {
  key: FinancialModeKey;
  label: string;
  description?: string | null;
  locked: boolean;
  scenarios: string[];
}

const FINANCIAL_MODE_DEFAULTS: Record<FinancialModeKey, Pick<FinancialModeDescriptor, 'label' | 'description' | 'scenarios'>> = {
  pre_lock: {
    label: 'Pre-lock plan',
    description: 'Editable planning surface before approval.',
    scenarios: ['planned'],
  },
  planned_vs_actual: {
    label: 'Planned vs actual',
    description: 'Planned vs actual reporting is active.',
    scenarios: ['planned', 'actual'],
  },
  multi_scenario: {
    label: 'Multi-scenario plan',
    description: 'Base, high, and actual scenarios are available.',
    scenarios: ['base', 'high', 'actual'],
  },
  bankable_locked: {
    label: 'Locked bankable plan',
    description: 'Immutable baseline created from an approved stage-gate submission.',
    scenarios: ['approval', 'rebaseline'],
  },
};

export function resolveFinancialMode(...candidates: unknown[]): FinancialModeDescriptor {
  for (const candidate of candidates) {
    const descriptor = normalizeFinancialMode(candidate);
    if (descriptor) return descriptor;
  }

  for (const candidate of candidates) {
    const inferred = inferFinancialMode(candidate);
    if (inferred) return inferred;
  }

  return {
    key: 'planned_vs_actual',
    label: FINANCIAL_MODE_DEFAULTS.planned_vs_actual.label,
    description: FINANCIAL_MODE_DEFAULTS.planned_vs_actual.description,
    locked: false,
    scenarios: [...FINANCIAL_MODE_DEFAULTS.planned_vs_actual.scenarios],
  };
}

export function normalizeFinancialMode(value: unknown): FinancialModeDescriptor | null {
  if (!value) return null;
  if (typeof value === 'string') {
    const key = value as FinancialModeKey;
    return {
      key,
      label: FINANCIAL_MODE_DEFAULTS[key]?.label || value,
      description: FINANCIAL_MODE_DEFAULTS[key]?.description || null,
      locked: key === 'bankable_locked',
      scenarios: [...(FINANCIAL_MODE_DEFAULTS[key]?.scenarios || [])],
    };
  }

  if (!isRecord(value)) return null;
  const key = typeof value['key'] === 'string' ? (value['key'] as FinancialModeKey) : null;
  if (!key && typeof value['label'] !== 'string' && typeof value['description'] !== 'string' && !Array.isArray(value['scenarios'])) {
    return null;
  }

  const defaults = key ? FINANCIAL_MODE_DEFAULTS[key] : FINANCIAL_MODE_DEFAULTS.planned_vs_actual;
  return {
    key: key || 'planned_vs_actual',
    label: typeof value['label'] === 'string' ? value['label'] : defaults.label,
    description: typeof value['description'] === 'string' ? value['description'] : defaults.description,
    locked: typeof value['locked'] === 'boolean' ? value['locked'] : key === 'bankable_locked',
    scenarios: Array.isArray(value['scenarios'])
      ? value['scenarios'].filter((scenario): scenario is string => typeof scenario === 'string')
      : [...defaults.scenarios],
  };
}

export function financialModeHasScenario(mode: FinancialModeDescriptor | null | undefined, scenario: string): boolean {
  return Boolean(mode?.scenarios?.includes(scenario));
}

export function financialModeUsesActuals(mode: FinancialModeDescriptor | null | undefined): boolean {
  return financialModeHasScenario(mode, 'actual') || mode?.key === 'planned_vs_actual' || mode?.key === 'multi_scenario' || mode?.key === 'bankable_locked';
}

function inferFinancialMode(candidate: unknown): FinancialModeDescriptor | null {
  if (!isRecord(candidate)) return null;

  const nestedMode =
    normalizeFinancialMode(candidate['financial_mode'])
    || normalizeFinancialMode(candidate['value_bridge'] && isRecord(candidate['value_bridge']) ? candidate['value_bridge']['financial_mode'] : undefined)
    || normalizeFinancialMode(candidate['summary'] && isRecord(candidate['summary']) ? candidate['summary']['financial_mode'] : undefined)
    || normalizeFinancialMode(candidate['snapshot'] && isRecord(candidate['snapshot']) ? candidate['snapshot']['financial_mode'] : undefined)
    || normalizeFinancialMode(candidate['current'] && isRecord(candidate['current']) && isRecord(candidate['current']['snapshot']) ? candidate['current']['snapshot']['financial_mode'] : undefined);
  if (nestedMode) return nestedMode;

  if (hasAnyScenarioShape(candidate)) {
    if (hasAnyMultiScenarioShape(candidate)) {
      return {
        key: 'multi_scenario',
        ...FINANCIAL_MODE_DEFAULTS.multi_scenario,
        locked: false,
      };
    }
    if (hasAnyActualShape(candidate)) {
      return {
        key: 'planned_vs_actual',
        ...FINANCIAL_MODE_DEFAULTS.planned_vs_actual,
        locked: false,
      };
    }
    return {
      key: 'pre_lock',
      ...FINANCIAL_MODE_DEFAULTS.pre_lock,
      locked: false,
    };
  }

  return null;
}

function hasAnyScenarioShape(value: Record<string, unknown>): boolean {
  return [
    'base_case',
    'high_case',
    'actual',
    'benefits_base',
    'benefits_high',
    'benefits_plan',
    'net_base',
    'net_high',
    'net_plan',
    'net_value_plan',
    'net_after_allocation_plan',
  ].some(key => key in value);
}

function hasAnyMultiScenarioShape(value: Record<string, unknown>): boolean {
  return Boolean(
    value['base_case'] || value['high_case'] || value['benefits_base'] || value['benefits_high'] || value['net_base'] || value['net_high'],
  );
}

function hasAnyActualShape(value: Record<string, unknown>): boolean {
  return Boolean(
    value['actual'] || value['benefits_actual'] || value['net_actual'] || value['net_value_actual'] || value['net_after_allocation_actual'] || value['revenue_uplift_actual'],
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export interface BenefitLedgerPeriodSummary {
  period: string;
  year: number;
  week?: number | null;
  month?: number | null;
  period_start?: string | null;
  period_end?: string | null;
  period_granularity: FinancialLedgerGranularity;
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
}

export interface BenefitLedgerSummaryResponse {
  initiative_id: string;
  granularity: FinancialLedgerGranularity;
  locked_bankable_plan_version: number | null;
  periods: BenefitLedgerPeriodSummary[];
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
}

export interface BenefitLedgerInitiativeRollup {
  initiative_id: string;
  initiative_code?: string | null;
  name: string;
  stage?: string | null;
  workstream_id?: string | null;
  workstream_name?: string | null;
  locked_bankable_plan_version?: number | null;
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
}

export interface BenefitLedgerWorkstreamRollup {
  workstream_id?: string | null;
  workstream_name: string;
  initiative_count: number;
  locked_initiative_count: number;
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
}

export interface BenefitLedgerRollupSummaryResponse {
  scope: 'portfolio' | 'workstream' | string;
  scope_id?: string | null;
  scope_name: string;
  granularity: FinancialLedgerGranularity;
  periods: BenefitLedgerPeriodSummary[];
  bankable_plan_amount: string;
  actual_amount: string;
  variance: string;
  workstreams: BenefitLedgerWorkstreamRollup[];
  initiatives: BenefitLedgerInitiativeRollup[];
}

export interface GovernanceGate {
  id?: string | null;
  initiative_id: string;
  gate_number: number;
  label: string;
  from_stage: string;
  to_stage: string;
}

export interface GovernanceSubmission {
  id: string;
  initiative_id: string;
  gate_number: number;
  submitted_by_id: string;
  submitted_by_name?: string | null;
  submitted_at: string;
  decision: 'pending' | 'approved' | 'rejected' | 'conditional' | string;
  decided_by_id?: string | null;
  decided_by_name?: string | null;
  decided_at?: string | null;
  commentary?: string | null;
  criteria_snapshot?: Array<Record<string, unknown>> | null;
}

export interface GovernanceStatusResponse {
  gates: GovernanceGate[];
  active_submission: GovernanceSubmission | null;
  history: GovernanceSubmission[];
}

export interface PortfolioGovernanceResponse {
  health_score: string;
  approved: number;
  pending: number;
  rejected: number;
  conditional: number;
  total_submissions: number;
  submissions: GovernanceSubmission[];
}

export interface WorkstreamOption {
  id: string;
  name: string;
  business_unit_id?: string | null;
}

export interface FinancialGovernanceSettings {
  initiative_plan_lock_gate_number: number;
  plan_lock_on_approval: boolean;
  allow_rebaseline: boolean;
  rebaseline_roles: string[];
  workstream_lock_cadence: 'one_off' | 'annual' | 'cycle_based';
  initiative_inclusion_cutoff: 'approved_at_lte_lock_date';
  valuation_method: 'run_rate';
  locked_value_basis: 'net_run_rate' | 'benefit_run_rate';
  workstream_target_versioning: boolean;
}

export interface WorkstreamTargetInitiative {
  initiative_id: string;
  initiative_code?: string | null;
  name: string;
  stage?: string | null;
  approved_at?: string | null;
  bankable_plan_version?: number | null;
  value_source: string;
  net_run_rate_value: string;
  actual_value: string;
}

export interface WorkstreamTargetSnapshot {
  workstream_id: string;
  workstream_name?: string | null;
  lock_date: string;
  settings: FinancialGovernanceSettings;
  included: WorkstreamTargetInitiative[];
  excluded: WorkstreamTargetInitiative[];
  locked_run_rate_value: string;
  plan_total: string;
  actual_total: string;
  variance: string;
}

export interface WorkstreamTargetPreviewResponse extends WorkstreamTargetSnapshot {
  latest_locked_version?: number | null;
}

export interface WorkstreamTargetLockVersion {
  id: string;
  workstream_id: string;
  version: number;
  lock_date: string;
  locked_at: string;
  locked_by_id?: string | null;
  lock_cadence: 'one_off' | 'annual' | 'cycle_based';
  cutoff_rule: 'approved_at_lte_lock_date';
  valuation_method: 'run_rate';
  locked_value_basis: 'net_run_rate' | 'benefit_run_rate';
  included_initiative_ids: string[];
  excluded_initiative_ids: string[];
  locked_run_rate_value: string;
  plan_total: string;
  actual_total: string;
  variance: string;
  snapshot: WorkstreamTargetSnapshot;
}

export interface WorkstreamTargetLockResponse {
  current: WorkstreamTargetLockVersion | null;
  history: WorkstreamTargetLockVersion[];
}

export function initiativeLabel(initiative: InitiativeOption | null | undefined): string {
  if (!initiative) return 'Select an initiative';
  const code = initiative.initiative_code?.trim();
  const name = initiative.name?.trim();
  if (code && name) return `${code} · ${name}`;
  return name || code || initiative.id;
}

export function initiativeStage(initiative: InitiativeOption | null | undefined): string {
  if (!initiative?.stage) return 'unknown';
  return initiative.stage.replace(/_/g, ' ');
}

export function isInitiativeLocked(initiative: InitiativeOption | null | undefined): boolean {
  return Boolean(initiative?.locked);
}

export function selectDefaultInitiative<T extends { id: string }>(items: T[], preferredId?: string | null): string {
  if (preferredId && items.some(item => item.id === preferredId)) return preferredId;
  return items[0]?.id || '';
}

export function formatMoney(value: string | number | null | undefined, maximumFractionDigits = 0): string {
  const numeric = parseNumeric(value);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits,
  }).format(numeric);
}

export function formatCompactMoney(value: string | number | null | undefined): string {
  const numeric = parseNumeric(value);
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(numeric);
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

export function formatDateOnly(value: string | null | undefined): string {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' }).format(date);
}

export function parseNumeric(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  const parsed = typeof value === 'string' ? Number(value) : value;
  return Number.isFinite(parsed) ? parsed : 0;
}

export function delta(actual: string | number | null | undefined, plan: string | number | null | undefined): number {
  return parseNumeric(actual) - parseNumeric(plan);
}

export function toneClass(value: string | number | null | undefined): string {
  return parseNumeric(value) >= 0 ? 'text-emerald-600' : 'text-red-500';
}

export function decisionBadgeClass(decision: string): string {
  switch (decision) {
    case 'approved':
      return 'inline-flex items-center border border-emerald-600/20 bg-emerald-600/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-emerald-600';
    case 'rejected':
      return 'inline-flex items-center border border-[var(--t-red)]/20 bg-[var(--t-red)]/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-red)]';
    case 'conditional':
      return 'inline-flex items-center border border-[var(--t-amber)]/20 bg-[var(--t-amber)]/10 px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-amber)]';
    default:
      return 'inline-flex items-center border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]';
  }
}
