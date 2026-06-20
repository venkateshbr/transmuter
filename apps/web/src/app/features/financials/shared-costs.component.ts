import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  Calculator,
  CircleDollarSign,
  Eye,
  LockKeyhole,
  LucideAngularModule,
  Play,
  Plus,
  RefreshCw,
  Save,
  Settings2,
  Target,
  Trash2,
} from 'lucide-angular';
import { ApiService } from '../../core/services/api.service';

type SharedCostReportingTreatment = 'report_only' | 'post_cost_lines' | 'report_and_post';
type AllocationMethod =
  | 'equal_split'
  | 'fixed_percentage'
  | 'manual_amount'
  | 'benefit_weighted'
  | 'revenue_weighted'
  | 'savings_weighted'
  | 'direct_cost_weighted'
  | 'headcount_weighted'
  | 'metric_weighted';
type TargetDimension =
  | 'all'
  | 'initiative'
  | 'workstream'
  | 'business_unit'
  | 'tag'
  | 'country'
  | 'stage'
  | 'owner'
  | 'rag_status';

interface SharedCostPool {
  id: string;
  name: string;
  description?: string | null;
  category_key: string;
  cost_category_id?: string | null;
  category_label?: string | null;
  scenario_id?: string | null;
  scenario_label?: string | null;
  year: number;
  quarter?: number | null;
  month?: number | null;
  amount_plan: string;
  amount_actual?: string | null;
  allocated_plan: string;
  allocated_actual: string;
  unallocated_plan: string;
  unallocated_actual: string;
  period_grain: string;
  reporting_treatment: SharedCostReportingTreatment;
  latest_run_status?: string | null;
  status: string;
}

interface SharedCostPoolListResponse {
  items: SharedCostPool[];
  total: number;
}

interface AllocationTargetItem {
  id?: string;
  target_mode: 'include' | 'exclude';
  dimension_type: TargetDimension;
  dimension_value?: string | null;
  label?: string | null;
}

interface AllocationWeightItem {
  id?: string;
  initiative_id?: string | null;
  dimension_type?: TargetDimension | null;
  dimension_value?: string | null;
  weight_value?: string | null;
  percentage?: string | null;
  manual_amount?: string | null;
  label?: string | null;
}

interface AllocationRule {
  id: string;
  pool_id: string;
  name: string;
  allocation_method: AllocationMethod;
  driver_metric_definition_id?: string | null;
  driver_metric_label?: string | null;
  driver_cost_category_id?: string | null;
  driver_cost_category_label?: string | null;
  driver_scenario_id?: string | null;
  driver_scenario_label?: string | null;
  driver_period_mode: string;
  missing_basis_behavior: string;
  policy_status: string;
  version: number;
  targets: AllocationTargetItem[];
  structured_weights: AllocationWeightItem[];
}

interface AllocationRun {
  id: string;
  status: string;
  scenario: string;
  total_amount_plan: string;
  total_amount_actual?: string | null;
  created_at: string;
  locked_at?: string | null;
  allocations: SharedCostAllocation[];
  exception_summary?: { count?: number; blocking?: number; warning?: number };
}

interface SharedCostAllocation {
  id: string;
  initiative_id: string;
  initiative_name?: string | null;
  allocation_basis: string;
  basis_label?: string | null;
  basis_value: string;
  allocated_plan: string;
  allocated_actual?: string | null;
  allocation_share: string;
  rounding_adjustment: string;
  explanation?: string | null;
}

interface AllocationPreview {
  candidate_count: number;
  excluded_count: number;
  allocations: SharedCostAllocation[];
  exceptions: {
    exception_type: string;
    severity: 'info' | 'warning' | 'blocking';
    message: string;
    initiative_id?: string | null;
  }[];
  reconciliation: {
    pool_amount_plan: string;
    allocated_plan: string;
    unallocated_plan: string;
    pool_amount_actual?: string | null;
    allocated_actual?: string | null;
    unallocated_actual?: string | null;
    reconciled: boolean;
  };
  reporting_impact: Record<string, string>;
}

interface SharedCostConfig {
  cost_categories: Array<{ id: string; key: string; label: string; rollup_type?: string }>;
  scenarios: Array<{ id: string; key: string; label: string; kind: string; is_primary?: boolean }>;
  metric_definitions: Array<{
    id: string;
    key: string;
    label: string;
    benefit_class?: string | null;
    rollup_type?: string | null;
  }>;
  initiatives: Array<{
    id: string;
    initiative_code?: string | null;
    name: string;
    workstream_id?: string | null;
    tag?: string | null;
    stage?: string | null;
    rag_status?: string | null;
  }>;
  workstreams: Array<{ id: string; name: string }>;
  business_units: Array<{ id: string; name: string; code?: string | null }>;
  tags: string[];
  countries: string[];
  stages: string[];
  allocation_methods: Array<{ key: AllocationMethod; label: string }>;
  reporting_settings: SharedCostReportingSettings;
}

interface SharedCostReportingSettings {
  include_in_executive_control_tower: boolean;
  include_in_dashboard_executive_brief: boolean;
  include_in_portfolio_financials: boolean;
  include_in_initiative_financials: boolean;
  include_in_bankable_plan: boolean;
  posting_mode: SharedCostReportingTreatment;
}

interface SelectOption {
  value: string;
  label: string;
}

const DEFAULT_REPORTING_SETTINGS: SharedCostReportingSettings = {
  include_in_executive_control_tower: true,
  include_in_dashboard_executive_brief: true,
  include_in_portfolio_financials: false,
  include_in_initiative_financials: true,
  include_in_bankable_plan: false,
  posting_mode: 'report_only',
};

@Component({
  selector: 'app-shared-costs',
  standalone: true,
  imports: [CommonModule, FormsModule, LucideAngularModule],
  template: `
    <div class="min-h-screen p-6 md:p-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financial Governance</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Shared Cost Pools<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-4xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Configure central cost pools, allocation policies, target initiatives, and locked burdening runs without hiding shared spend inside direct initiative cost lines.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <button class="btn-secondary gap-2 text-[10px]" type="button" (click)="loadAll()" aria-label="Refresh shared costs">
            <lucide-icon [img]="refreshIcon" [size]="14"></lucide-icon>
            Refresh
          </button>
          <button class="btn-primary gap-2 text-[10px]" type="button" (click)="createPool()" [disabled]="saving()" aria-label="Create shared cost pool">
            <lucide-icon [img]="plusIcon" [size]="14"></lucide-icon>
            Create Pool
          </button>
        </div>
      </header>

      @if (error()) {
        <div class="mt-5 border border-red-300 bg-red-50 px-4 py-3 text-xs font-bold text-red-700 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200">
          {{ error() }}
        </div>
      }

      <section class="mt-6 grid gap-4 md:grid-cols-4">
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Pool Plan</p>
          <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().poolPlan) }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Allocated Plan</p>
          <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().allocatedPlan) }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Unallocated</p>
          <p class="mt-3 text-2xl font-black" [class.text-red-500]="summary().unallocatedPlan > 0" [class.text-[var(--t-text-primary)]]="summary().unallocatedPlan <= 0">
            {{ formatMoney(summary().unallocatedPlan) }}
          </p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked Runs</p>
          <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ summary().lockedRuns }}</p>
        </div>
      </section>

      <section class="mt-6 border border-[var(--t-border)] bg-[var(--t-surface)]">
        <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--t-border)] p-5">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Reporting Treatment</p>
            <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Dashboard and Report Impact</h2>
          </div>
          <button class="btn-secondary gap-2 text-[10px]" type="button" (click)="saveReportingSettings()" [disabled]="settingsSaving()" aria-label="Save shared cost reporting settings">
            <lucide-icon [img]="settingsIcon" [size]="14"></lucide-icon>
            Save Settings
          </button>
        </div>
        <div class="grid gap-4 p-5 lg:grid-cols-6">
          <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
            <input type="checkbox" [(ngModel)]="reportingSettings.include_in_executive_control_tower" aria-label="Include shared costs in executive control tower">
            Control Tower
          </label>
          <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
            <input type="checkbox" [(ngModel)]="reportingSettings.include_in_dashboard_executive_brief" aria-label="Include shared costs in dashboard executive brief">
            Executive Brief
          </label>
          <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
            <input type="checkbox" [(ngModel)]="reportingSettings.include_in_portfolio_financials" aria-label="Include shared costs in portfolio financials">
            Portfolio Financials
          </label>
          <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
            <input type="checkbox" [(ngModel)]="reportingSettings.include_in_initiative_financials" aria-label="Include shared costs in initiative financials">
            Initiative Financials
          </label>
          <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-secondary)]">
            <input type="checkbox" [(ngModel)]="reportingSettings.include_in_bankable_plan" aria-label="Include shared costs in bankable plan">
            Bankable Plan
          </label>
          <select class="input-field py-2 text-xs" [(ngModel)]="reportingSettings.posting_mode" aria-label="Default shared cost posting mode">
            <option value="report_only">Report only</option>
            <option value="post_cost_lines">Post cost lines</option>
            <option value="report_and_post">Report and post</option>
          </select>
        </div>
      </section>

      <section class="mt-6 grid gap-6 xl:grid-cols-[0.75fr_1.25fr]">
        <div class="space-y-6">
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
            <div class="border-b border-[var(--t-border)] p-5">
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Create Pool</p>
              <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Shared Cost Definition</h2>
            </div>
            <div class="grid gap-3 p-5 md:grid-cols-2">
              <input class="input-field md:col-span-2" [(ngModel)]="poolDraft.name" placeholder="Pool name" aria-label="Shared cost pool name">
              <select class="input-field" [(ngModel)]="poolDraft.cost_category_id" (ngModelChange)="syncPoolCategoryKey()" aria-label="Shared cost category">
                @for (category of config()?.cost_categories || []; track category.id) {
                  <option [value]="category.id">{{ category.label }}</option>
                }
              </select>
              <select class="input-field" [(ngModel)]="poolDraft.scenario_id" aria-label="Shared cost scenario">
                @for (scenario of config()?.scenarios || []; track scenario.id) {
                  <option [value]="scenario.id">{{ scenario.label }}</option>
                }
              </select>
              <input class="input-field" type="number" [(ngModel)]="poolDraft.year" aria-label="Shared cost year">
              <select class="input-field" [(ngModel)]="poolDraft.period_grain" aria-label="Shared cost period grain">
                <option value="annual">Annual</option>
                <option value="quarterly">Quarterly</option>
                <option value="monthly">Monthly</option>
              </select>
              <input class="input-field" type="number" step="0.0001" [(ngModel)]="poolDraft.amount_plan" placeholder="Plan amount" aria-label="Shared cost planned amount">
              <input class="input-field" type="number" step="0.0001" [(ngModel)]="poolDraft.amount_actual" placeholder="Actual amount" aria-label="Shared cost actual amount">
              <select class="input-field md:col-span-2" [(ngModel)]="poolDraft.reporting_treatment" aria-label="Shared cost reporting treatment">
                <option value="report_only">Report only</option>
                <option value="post_cost_lines">Post cost lines</option>
                <option value="report_and_post">Report and post</option>
              </select>
              <textarea class="input-field md:col-span-2" rows="3" [(ngModel)]="poolDraft.description" placeholder="Purpose and scope" aria-label="Shared cost pool description"></textarea>
            </div>
          </div>

          <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
            <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
              <div>
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Pools</p>
                <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Shared Cost Pools</h2>
              </div>
              <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ pools().length }} Total</span>
            </div>
            <div class="max-h-[720px] divide-y divide-[var(--t-border)] overflow-y-auto">
              @for (pool of pools(); track pool.id) {
                <button type="button" class="block w-full p-5 text-left transition hover:bg-[var(--t-surface-raised)]" [class.bg-[var(--t-surface-raised)]]="selectedPool()?.id === pool.id" (click)="selectPool(pool)" [attr.aria-label]="'Select ' + pool.name">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <p class="text-sm font-black text-[var(--t-text-primary)]">{{ pool.name }}</p>
                      <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                        {{ pool.category_label || pool.category_key }} · {{ pool.year }} · {{ pool.reporting_treatment.replace('_', ' ') }}
                      </p>
                    </div>
                    <div class="text-right">
                      <p class="text-sm font-black text-[var(--t-text-primary)]">{{ formatMoney(pool.amount_plan) }}</p>
                      <p class="mt-1 text-[10px] font-bold text-[var(--t-text-tertiary)]">Allocated {{ formatMoney(pool.allocated_plan) }}</p>
                    </div>
                  </div>
                  <div class="mt-4 h-1.5 bg-[var(--t-surface-muted)]">
                    <div class="h-1.5 bg-[var(--t-accent)]" [style.width.%]="allocationPercent(pool)"></div>
                  </div>
                </button>
              } @empty {
                <div class="p-6 text-sm text-[var(--t-text-secondary)]">No shared cost pools yet.</div>
              }
            </div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
            <div class="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--t-border)] p-5">
              <div>
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Allocation Policy</p>
                <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Rules, Targets, and Weights</h2>
                <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ selectedPool()?.name || 'Select a pool' }}</p>
              </div>
              <button class="btn-primary gap-2 text-[10px]" type="button" [disabled]="!selectedPool() || saving()" (click)="createRule()" aria-label="Save allocation rule">
                <lucide-icon [img]="saveIcon" [size]="14"></lucide-icon>
                Save Rule
              </button>
            </div>

            @if (selectedPool()) {
              <div class="grid gap-3 border-b border-[var(--t-border)] p-5 lg:grid-cols-4">
                <input class="input-field lg:col-span-2" [(ngModel)]="ruleDraft.name" placeholder="Rule name" aria-label="Allocation rule name">
                <select class="input-field" [(ngModel)]="ruleDraft.allocation_method" (ngModelChange)="onMethodChange()" aria-label="Allocation method">
                  @for (method of config()?.allocation_methods || []; track method.key) {
                    <option [value]="method.key">{{ method.label }}</option>
                  }
                </select>
                <select class="input-field" [(ngModel)]="ruleDraft.missing_basis_behavior" aria-label="Missing basis behavior">
                  <option value="fail">Fail on missing basis</option>
                  <option value="equal_split">Fallback equal split</option>
                  <option value="zero">Allocate zero</option>
                </select>
                @if (usesMetricDriver(ruleDraft.allocation_method)) {
                  <select class="input-field lg:col-span-2" [(ngModel)]="ruleDraft.driver_metric_definition_id" aria-label="Allocation driver metric">
                    <option [ngValue]="null">Auto-select metric</option>
                    @for (metric of config()?.metric_definitions || []; track metric.id) {
                      <option [value]="metric.id">{{ metric.label }}</option>
                    }
                  </select>
                }
                @if (ruleDraft.allocation_method === 'direct_cost_weighted') {
                  <select class="input-field lg:col-span-2" [(ngModel)]="ruleDraft.driver_cost_category_id" aria-label="Allocation direct cost category">
                    <option [ngValue]="null">All direct cost categories</option>
                    @for (category of config()?.cost_categories || []; track category.id) {
                      <option [value]="category.id">{{ category.label }}</option>
                    }
                  </select>
                }
                <select class="input-field lg:col-span-2" [(ngModel)]="ruleDraft.driver_scenario_id" aria-label="Allocation driver scenario">
                  <option [ngValue]="null">Use pool scenario</option>
                  @for (scenario of config()?.scenarios || []; track scenario.id) {
                    <option [value]="scenario.id">{{ scenario.label }}</option>
                  }
                </select>
              </div>

              <div class="grid gap-6 p-5 xl:grid-cols-[0.9fr_1.1fr]">
                <div class="border border-[var(--t-border)]">
                  <div class="flex items-center justify-between border-b border-[var(--t-border)] p-4">
                    <div>
                      <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Saved Rules</p>
                      <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">Policy Versions</p>
                    </div>
                    <lucide-icon [img]="calculatorIcon" class="text-[var(--t-accent)]" [size]="18"></lucide-icon>
                  </div>
                  <div class="divide-y divide-[var(--t-border)]">
                    @for (rule of rules(); track rule.id) {
                      <button type="button" class="block w-full p-4 text-left transition hover:bg-[var(--t-surface-raised)]" [class.bg-[var(--t-surface-raised)]]="selectedRule()?.id === rule.id" (click)="selectRule(rule)" [attr.aria-label]="'Select allocation rule ' + rule.name">
                        <div class="flex items-start justify-between gap-3">
                          <div>
                            <p class="text-sm font-black text-[var(--t-text-primary)]">{{ rule.name }}</p>
                            <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                              {{ methodLabel(rule.allocation_method) }} · v{{ rule.version }}
                            </p>
                          </div>
                          <span class="border border-[var(--t-border)] px-2 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">{{ rule.policy_status }}</span>
                        </div>
                        <p class="mt-2 text-xs text-[var(--t-text-secondary)]">
                          {{ rule.targets.length || 0 }} targets · {{ rule.structured_weights.length || 0 }} structured weights
                        </p>
                      </button>
                    } @empty {
                      <div class="p-5 text-sm text-[var(--t-text-secondary)]">Create a rule before configuring targets and previewing allocations.</div>
                    }
                  </div>
                </div>

                <div class="space-y-5">
                  @if (selectedRule(); as rule) {
                    <div class="border border-[var(--t-border)]">
                      <div class="flex items-center justify-between border-b border-[var(--t-border)] p-4">
                        <div>
                          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Targeting</p>
                          <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">Included and Excluded Scope</p>
                        </div>
                        <button class="btn-secondary gap-2 text-[10px]" type="button" (click)="addTarget()" aria-label="Add allocation target">
                          <lucide-icon [img]="targetIcon" [size]="14"></lucide-icon>
                          Add
                        </button>
                      </div>
                      <div class="grid gap-3 p-4 md:grid-cols-4">
                        <select class="input-field py-2 text-xs" [(ngModel)]="targetDraft.target_mode" aria-label="Allocation target mode">
                          <option value="include">Include</option>
                          <option value="exclude">Exclude</option>
                        </select>
                        <select class="input-field py-2 text-xs" [(ngModel)]="targetDraft.dimension_type" (ngModelChange)="targetDraft.dimension_value = null" aria-label="Allocation target dimension">
                          @for (dimension of targetDimensions; track dimension.value) {
                            <option [value]="dimension.value">{{ dimension.label }}</option>
                          }
                        </select>
                        <select class="input-field py-2 text-xs md:col-span-2" [(ngModel)]="targetDraft.dimension_value" [disabled]="targetDraft.dimension_type === 'all'" aria-label="Allocation target value">
                          <option [ngValue]="null">{{ targetDraft.dimension_type === 'all' ? 'All initiatives' : 'Select value' }}</option>
                          @for (option of targetValueOptions(targetDraft.dimension_type); track option.value) {
                            <option [value]="option.value">{{ option.label }}</option>
                          }
                        </select>
                      </div>
                      <div class="divide-y divide-[var(--t-border)]">
                        @for (target of rule.targets; track target.id || target.target_mode + target.dimension_type + target.dimension_value) {
                          <div class="flex items-center justify-between gap-4 px-4 py-3">
                            <div>
                              <p class="text-xs font-black uppercase tracking-widest text-[var(--t-text-primary)]">{{ target.target_mode }} {{ dimensionLabel(target.dimension_type) }}</p>
                              <p class="mt-1 text-xs text-[var(--t-text-secondary)]">{{ target.label || targetDisplayValue(target) }}</p>
                            </div>
                            <button class="btn-secondary px-3 py-2" type="button" (click)="removeTarget(target)" [attr.aria-label]="'Remove target ' + targetDisplayValue(target)">
                              <lucide-icon [img]="trashIcon" [size]="14"></lucide-icon>
                            </button>
                          </div>
                        } @empty {
                          <div class="px-4 py-5 text-xs text-[var(--t-text-secondary)]">No explicit target rows. The rule applies to all visible initiatives.</div>
                        }
                      </div>
                    </div>

                    @if (requiresWeights(rule.allocation_method)) {
                      <div class="border border-[var(--t-border)]">
                        <div class="flex items-center justify-between border-b border-[var(--t-border)] p-4">
                          <div>
                            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Weights</p>
                            <p class="mt-1 text-sm font-black text-[var(--t-text-primary)]">{{ weightLabel(rule.allocation_method) }}</p>
                          </div>
                          <button class="btn-secondary gap-2 text-[10px]" type="button" (click)="addWeight()" aria-label="Add allocation weight">
                            <lucide-icon [img]="plusIcon" [size]="14"></lucide-icon>
                            Add
                          </button>
                        </div>
                        <div class="grid gap-3 p-4 md:grid-cols-[1fr_160px]">
                          <select class="input-field py-2 text-xs" [(ngModel)]="weightDraft.initiative_id" aria-label="Allocation weight initiative">
                            <option [ngValue]="null">Select initiative</option>
                            @for (initiative of config()?.initiatives || []; track initiative.id) {
                              <option [value]="initiative.id">{{ initiative.initiative_code }} · {{ initiative.name }}</option>
                            }
                          </select>
                          <input class="input-field py-2 text-xs" type="number" step="0.0001" [(ngModel)]="weightDraft.value" [placeholder]="weightInputPlaceholder(rule.allocation_method)" aria-label="Allocation weight value">
                        </div>
                        <div class="divide-y divide-[var(--t-border)]">
                          @for (weight of rule.structured_weights; track weight.id || weight.initiative_id) {
                            <div class="flex items-center justify-between gap-4 px-4 py-3">
                              <div>
                                <p class="text-xs font-black text-[var(--t-text-primary)]">{{ initiativeLabel(weight.initiative_id) }}</p>
                                <p class="mt-1 text-xs text-[var(--t-text-secondary)]">{{ weightDisplay(weight, rule.allocation_method) }}</p>
                              </div>
                              <button class="btn-secondary px-3 py-2" type="button" (click)="removeWeight(weight)" [attr.aria-label]="'Remove weight for ' + initiativeLabel(weight.initiative_id)">
                                <lucide-icon [img]="trashIcon" [size]="14"></lucide-icon>
                              </button>
                            </div>
                          } @empty {
                            <div class="px-4 py-5 text-xs text-[var(--t-text-secondary)]">Add structured rows before previewing percentage, manual amount, or headcount policies.</div>
                          }
                        </div>
                        @if (rule.allocation_method === 'fixed_percentage') {
                          <div class="border-t border-[var(--t-border)] px-4 py-3 text-xs font-bold text-[var(--t-text-secondary)]">
                            Configured percentage total: {{ configuredPercentageTotal(rule) }}%
                          </div>
                        }
                      </div>
                    }

                    <div class="flex flex-wrap gap-2">
                      <button class="btn-secondary gap-2 text-[10px]" type="button" (click)="previewRule()" [disabled]="previewing()" aria-label="Preview shared cost allocation">
                        <lucide-icon [img]="eyeIcon" [size]="14"></lucide-icon>
                        Preview Allocation
                      </button>
                      <button class="btn-primary gap-2 text-[10px]" type="button" (click)="postRun()" [disabled]="posting() || !preview()?.reconciliation?.reconciled" aria-label="Post locked shared cost allocation run">
                        <lucide-icon [img]="lockIcon" [size]="14"></lucide-icon>
                        Post Locked Run
                      </button>
                    </div>
                  } @else {
                    <div class="border border-[var(--t-border)] p-6 text-sm text-[var(--t-text-secondary)]">Select or create a rule to configure target scope, structured weights, and preview allocation impact.</div>
                  }
                </div>
              </div>
            } @else {
              <div class="p-8 text-sm text-[var(--t-text-secondary)]">Select a shared cost pool to manage allocation rules and runs.</div>
            }
          </div>

          <div class="grid gap-6 2xl:grid-cols-2">
            <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
              <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Preview</p>
                  <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Reconciliation and Exceptions</h2>
                </div>
                <lucide-icon [img]="playIcon" class="text-[var(--t-accent)]" [size]="18"></lucide-icon>
              </div>
              @if (preview(); as currentPreview) {
                <div class="grid gap-3 border-b border-[var(--t-border)] p-5 sm:grid-cols-3">
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Candidates</p>
                    <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ currentPreview.candidate_count }}</p>
                  </div>
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Allocated</p>
                    <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ formatMoney(currentPreview.reconciliation.allocated_plan) }}</p>
                  </div>
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</p>
                    <p class="mt-2 text-xl font-black" [class.text-emerald-600]="currentPreview.reconciliation.reconciled" [class.text-red-500]="!currentPreview.reconciliation.reconciled">
                      {{ currentPreview.reconciliation.reconciled ? 'Reconciled' : 'Blocked' }}
                    </p>
                  </div>
                </div>
                <div class="max-h-[360px] overflow-y-auto">
                  <table class="w-full min-w-[720px] text-left text-xs">
                    <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      <tr>
                        <th class="px-4 py-3">Initiative</th>
                        <th class="px-4 py-3">Basis</th>
                        <th class="px-4 py-3 text-right">Share</th>
                        <th class="px-4 py-3 text-right">Plan</th>
                        <th class="px-4 py-3 text-right">Actual</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (allocation of currentPreview.allocations; track allocation.initiative_id) {
                        <tr class="border-t border-[var(--t-border)]">
                          <td class="px-4 py-3 font-bold text-[var(--t-text-primary)]">{{ allocation.initiative_name || allocation.initiative_id }}</td>
                          <td class="px-4 py-3 text-[var(--t-text-secondary)]">{{ allocation.basis_label || allocation.allocation_basis }}</td>
                          <td class="px-4 py-3 text-right">{{ formatPercent(allocation.allocation_share) }}</td>
                          <td class="px-4 py-3 text-right font-bold">{{ formatMoney(allocation.allocated_plan) }}</td>
                          <td class="px-4 py-3 text-right">{{ formatMoney(allocation.allocated_actual) }}</td>
                        </tr>
                      } @empty {
                        <tr><td colspan="5" class="px-4 py-8 text-center text-[var(--t-text-secondary)]">No preview allocations yet.</td></tr>
                      }
                    </tbody>
                  </table>
                </div>
                @if (currentPreview.exceptions.length) {
                  <div class="border-t border-[var(--t-border)] p-5">
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Exceptions</p>
                    <div class="mt-3 space-y-2">
                      @for (exception of currentPreview.exceptions; track exception.exception_type + exception.message) {
                        <div class="border px-3 py-2 text-xs" [class.border-red-300]="exception.severity === 'blocking'" [class.border-amber-300]="exception.severity === 'warning'" [class.border-[var(--t-border)]]="exception.severity === 'info'">
                          <span class="font-black uppercase tracking-widest">{{ exception.severity }}</span>
                          <span class="ml-2 text-[var(--t-text-secondary)]">{{ exception.message }}</span>
                        </div>
                      }
                    </div>
                  </div>
                }
              } @else {
                <div class="p-8 text-sm text-[var(--t-text-secondary)]">Preview a selected rule to see candidate count, reconciliation, exceptions, and allocation rows before posting.</div>
              }
            </div>

            <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
              <div class="border-b border-[var(--t-border)] p-5">
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Run History</p>
                <h2 class="mt-1 text-base font-black text-[var(--t-text-primary)]">Posted Allocation Runs</h2>
              </div>
              <div class="max-h-[540px] overflow-y-auto">
                <table class="w-full min-w-[720px] text-left text-xs">
                  <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    <tr>
                      <th class="px-4 py-3">Created</th>
                      <th class="px-4 py-3">Status</th>
                      <th class="px-4 py-3">Scenario</th>
                      <th class="px-4 py-3 text-right">Plan</th>
                      <th class="px-4 py-3 text-right">Rows</th>
                      <th class="px-4 py-3 text-right">Exceptions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (run of runs(); track run.id) {
                      <tr class="border-t border-[var(--t-border)]">
                        <td class="px-4 py-3">{{ run.created_at | date:'medium' }}</td>
                        <td class="px-4 py-3 font-black uppercase tracking-widest">{{ run.status }}</td>
                        <td class="px-4 py-3 uppercase">{{ run.scenario }}</td>
                        <td class="px-4 py-3 text-right font-bold">{{ formatMoney(run.total_amount_plan) }}</td>
                        <td class="px-4 py-3 text-right">{{ run.allocations.length || 0 }}</td>
                        <td class="px-4 py-3 text-right">{{ run.exception_summary?.count || 0 }}</td>
                      </tr>
                    } @empty {
                      <tr><td colspan="6" class="px-4 py-8 text-center text-[var(--t-text-secondary)]">No allocation runs for this pool.</td></tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  `,
})
export class SharedCostsComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly plusIcon = Plus;
  readonly saveIcon = Save;
  readonly playIcon = Play;
  readonly refreshIcon = RefreshCw;
  readonly settingsIcon = Settings2;
  readonly targetIcon = Target;
  readonly calculatorIcon = Calculator;
  readonly lockIcon = LockKeyhole;
  readonly eyeIcon = Eye;
  readonly trashIcon = Trash2;
  readonly moneyIcon = CircleDollarSign;

  readonly pools = signal<SharedCostPool[]>([]);
  readonly rules = signal<AllocationRule[]>([]);
  readonly runs = signal<AllocationRun[]>([]);
  readonly config = signal<SharedCostConfig | null>(null);
  readonly selectedPool = signal<SharedCostPool | null>(null);
  readonly selectedRule = signal<AllocationRule | null>(null);
  readonly preview = signal<AllocationPreview | null>(null);
  readonly error = signal('');
  readonly saving = signal(false);
  readonly settingsSaving = signal(false);
  readonly previewing = signal(false);
  readonly posting = signal(false);

  reportingSettings: SharedCostReportingSettings = { ...DEFAULT_REPORTING_SETTINGS };
  poolDraft = this.defaultPoolDraft();
  ruleDraft = this.defaultRuleDraft();
  targetDraft: {
    target_mode: 'include' | 'exclude';
    dimension_type: TargetDimension;
    dimension_value: string | null;
  } = { target_mode: 'include', dimension_type: 'all', dimension_value: null };
  weightDraft: { initiative_id: string | null; value: string } = {
    initiative_id: null,
    value: '',
  };

  readonly targetDimensions: SelectOption[] = [
    { value: 'all', label: 'All initiatives' },
    { value: 'initiative', label: 'Initiative' },
    { value: 'workstream', label: 'Workstream' },
    { value: 'business_unit', label: 'Business unit' },
    { value: 'tag', label: 'Tag' },
    { value: 'country', label: 'Country' },
    { value: 'stage', label: 'Stage' },
    { value: 'rag_status', label: 'RAG status' },
  ];

  readonly summary = computed(() => {
    const pools = this.pools();
    const runs = this.runs();
    return {
      poolPlan: pools.reduce((total, pool) => total + this.parseMoney(pool.amount_plan), 0),
      allocatedPlan: pools.reduce((total, pool) => total + this.parseMoney(pool.allocated_plan), 0),
      unallocatedPlan: pools.reduce((total, pool) => total + Math.max(this.parseMoney(pool.unallocated_plan), 0), 0),
      lockedRuns: runs.filter(run => ['locked', 'posted', 'completed'].includes(run.status)).length,
    };
  });

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.error.set('');
    this.loadConfig();
    this.loadPools();
  }

  loadConfig(): void {
    this.api.get<SharedCostConfig>('/shared-costs/config').subscribe({
      next: config => {
        this.config.set(config);
        this.reportingSettings = { ...DEFAULT_REPORTING_SETTINGS, ...config.reporting_settings };
        this.setDraftDefaultsFromConfig();
      },
      error: err => this.handleError(err, 'Unable to load shared cost configuration.'),
    });
  }

  loadPools(selectPoolId?: string): void {
    this.api.get<SharedCostPoolListResponse>('/shared-cost-pools').subscribe({
      next: response => {
        const pools = response.items || [];
        this.pools.set(pools);
        const selected =
          pools.find(pool => pool.id === selectPoolId) ||
          pools.find(pool => pool.id === this.selectedPool()?.id) ||
          pools[0] ||
          null;
        if (selected) this.selectPool(selected, false);
      },
      error: err => this.handleError(err, 'Unable to load shared cost pools.'),
    });
  }

  selectPool(pool: SharedCostPool, clearPreview = true): void {
    this.selectedPool.set(pool);
    if (clearPreview) this.preview.set(null);
    this.loadRules(pool.id);
    this.loadRuns(pool.id);
  }

  loadRules(poolId: string, selectRuleId?: string): void {
    this.api.get<AllocationRule[]>(`/shared-cost-pools/${poolId}/allocation-rules`).subscribe({
      next: rules => {
        this.rules.set(rules || []);
        const selected =
          rules.find(rule => rule.id === selectRuleId) ||
          rules.find(rule => rule.id === this.selectedRule()?.id) ||
          rules[0] ||
          null;
        this.selectedRule.set(selected);
      },
      error: err => this.handleError(err, 'Unable to load allocation rules.'),
    });
  }

  loadRuns(poolId: string): void {
    this.api.get<AllocationRun[]>(`/shared-cost-pools/${poolId}/allocation-runs`).subscribe({
      next: runs => this.runs.set(runs || []),
      error: err => this.handleError(err, 'Unable to load allocation runs.'),
    });
  }

  createPool(): void {
    const name = this.poolDraft.name.trim();
    if (!name) {
      this.error.set('Pool name is required.');
      return;
    }
    this.syncPoolCategoryKey();
    this.saving.set(true);
    this.api.post<SharedCostPool>('/shared-cost-pools', {
      ...this.poolDraft,
      name,
      status: 'active',
      amount_actual: this.poolDraft.amount_actual === '' ? null : this.poolDraft.amount_actual,
    }).subscribe({
      next: pool => {
        this.saving.set(false);
        this.poolDraft = this.defaultPoolDraft();
        this.setDraftDefaultsFromConfig();
        this.loadPools(pool.id);
      },
      error: err => {
        this.saving.set(false);
        this.handleError(err, 'Unable to create shared cost pool.');
      },
    });
  }

  createRule(): void {
    const pool = this.selectedPool();
    const name = this.ruleDraft.name.trim();
    if (!pool || !name) {
      this.error.set('Select a pool and enter a rule name.');
      return;
    }
    this.saving.set(true);
    this.api.post<AllocationRule>(`/shared-cost-pools/${pool.id}/allocation-rules`, {
      ...this.ruleDraft,
      name,
      driver_metric_definition_id: this.ruleDraft.driver_metric_definition_id || null,
      driver_cost_category_id: this.ruleDraft.driver_cost_category_id || null,
      driver_scenario_id: this.ruleDraft.driver_scenario_id || null,
    }).subscribe({
      next: rule => {
        this.saving.set(false);
        this.ruleDraft = this.defaultRuleDraft();
        this.loadRules(pool.id, rule.id);
      },
      error: err => {
        this.saving.set(false);
        this.handleError(err, 'Unable to create allocation rule.');
      },
    });
  }

  selectRule(rule: AllocationRule): void {
    this.selectedRule.set(rule);
    this.preview.set(null);
  }

  addTarget(): void {
    const rule = this.selectedRule();
    const pool = this.selectedPool();
    if (!rule || !pool) return;
    if (this.targetDraft.dimension_type !== 'all' && !this.targetDraft.dimension_value) {
      this.error.set('Select a target value before adding the policy row.');
      return;
    }
    const payload: AllocationTargetItem = {
      target_mode: this.targetDraft.target_mode,
      dimension_type: this.targetDraft.dimension_type,
      dimension_value: this.targetDraft.dimension_type === 'all' ? null : this.targetDraft.dimension_value,
      label: this.targetDraft.dimension_type === 'all' ? 'All initiatives' : this.targetOptionLabel(this.targetDraft.dimension_type, this.targetDraft.dimension_value),
    };
    this.saveTargets(pool.id, rule.id, [...rule.targets, payload]);
  }

  removeTarget(target: AllocationTargetItem): void {
    const rule = this.selectedRule();
    const pool = this.selectedPool();
    if (!rule || !pool) return;
    const rows = rule.targets.filter(item => item !== target);
    this.saveTargets(pool.id, rule.id, rows);
  }

  addWeight(): void {
    const rule = this.selectedRule();
    const pool = this.selectedPool();
    if (!rule || !pool) return;
    if (!this.weightDraft.initiative_id || this.weightDraft.value === '') {
      this.error.set('Select an initiative and enter a weight value.');
      return;
    }
    const row: AllocationWeightItem = {
      initiative_id: this.weightDraft.initiative_id,
      label: this.initiativeLabel(this.weightDraft.initiative_id),
    };
    if (rule.allocation_method === 'fixed_percentage') row.percentage = this.weightDraft.value;
    else if (rule.allocation_method === 'manual_amount') row.manual_amount = this.weightDraft.value;
    else row.weight_value = this.weightDraft.value;
    const rows = [
      ...rule.structured_weights.filter(item => item.initiative_id !== row.initiative_id),
      row,
    ];
    this.saveWeights(pool.id, rule.id, rows);
  }

  removeWeight(weight: AllocationWeightItem): void {
    const rule = this.selectedRule();
    const pool = this.selectedPool();
    if (!rule || !pool) return;
    this.saveWeights(pool.id, rule.id, rule.structured_weights.filter(item => item !== weight));
  }

  previewRule(): void {
    const pool = this.selectedPool();
    const rule = this.selectedRule();
    if (!pool || !rule) return;
    this.previewing.set(true);
    this.preview.set(null);
    this.api.post<AllocationPreview>(`/shared-cost-pools/${pool.id}/allocation-runs/preview`, {
      rule_id: rule.id,
      scenario: 'plan',
      scenario_id: pool.scenario_id || null,
    }).subscribe({
      next: preview => {
        this.previewing.set(false);
        this.preview.set(preview);
      },
      error: err => {
        this.previewing.set(false);
        this.handleError(err, 'Unable to preview allocation rule.');
      },
    });
  }

  postRun(): void {
    const pool = this.selectedPool();
    const rule = this.selectedRule();
    if (!pool || !rule) return;
    this.posting.set(true);
    this.api.post<AllocationRun>(`/shared-cost-pools/${pool.id}/allocation-runs`, {
      rule_id: rule.id,
      scenario: 'plan',
      scenario_id: pool.scenario_id || null,
      run_type: 'posting',
      status: 'locked',
    }).subscribe({
      next: () => {
        this.posting.set(false);
        this.preview.set(null);
        this.loadPools(pool.id);
        this.loadRuns(pool.id);
      },
      error: err => {
        this.posting.set(false);
        this.handleError(err, 'Unable to post locked allocation run.');
      },
    });
  }

  saveReportingSettings(): void {
    this.settingsSaving.set(true);
    this.api.put<SharedCostReportingSettings>('/shared-costs/reporting-settings', this.reportingSettings).subscribe({
      next: settings => {
        this.settingsSaving.set(false);
        this.reportingSettings = settings;
      },
      error: err => {
        this.settingsSaving.set(false);
        this.handleError(err, 'Unable to save reporting settings.');
      },
    });
  }

  saveTargets(poolId: string, ruleId: string, targets: AllocationTargetItem[]): void {
    this.saving.set(true);
    this.api.put<AllocationTargetItem[]>(
      `/shared-cost-pools/${poolId}/allocation-rules/${ruleId}/targets`,
      targets.map(target => ({
        target_mode: target.target_mode,
        dimension_type: target.dimension_type,
        dimension_value: target.dimension_value || null,
        label: target.label || null,
      })),
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.targetDraft = { target_mode: 'include', dimension_type: 'all', dimension_value: null };
        this.loadRules(poolId, ruleId);
      },
      error: err => {
        this.saving.set(false);
        this.handleError(err, 'Unable to save allocation targets.');
      },
    });
  }

  saveWeights(poolId: string, ruleId: string, weights: AllocationWeightItem[]): void {
    this.saving.set(true);
    this.api.put<AllocationWeightItem[]>(
      `/shared-cost-pools/${poolId}/allocation-rules/${ruleId}/weights`,
      weights.map(weight => ({
        initiative_id: weight.initiative_id || null,
        dimension_type: weight.dimension_type || null,
        dimension_value: weight.dimension_value || null,
        weight_value: weight.weight_value || null,
        percentage: weight.percentage || null,
        manual_amount: weight.manual_amount || null,
        label: weight.label || null,
      })),
    ).subscribe({
      next: () => {
        this.saving.set(false);
        this.weightDraft = { initiative_id: null, value: '' };
        this.loadRules(poolId, ruleId);
      },
      error: err => {
        this.saving.set(false);
        this.handleError(err, 'Unable to save allocation weights.');
      },
    });
  }

  onMethodChange(): void {
    if (!this.usesMetricDriver(this.ruleDraft.allocation_method)) {
      this.ruleDraft.driver_metric_definition_id = null;
    }
    if (this.ruleDraft.allocation_method !== 'direct_cost_weighted') {
      this.ruleDraft.driver_cost_category_id = null;
    }
  }

  syncPoolCategoryKey(): void {
    const category = this.config()?.cost_categories.find(item => item.id === this.poolDraft.cost_category_id);
    if (category) this.poolDraft.category_key = category.key;
  }

  usesMetricDriver(method: AllocationMethod): boolean {
    return ['benefit_weighted', 'revenue_weighted', 'savings_weighted', 'metric_weighted'].includes(method);
  }

  requiresWeights(method: AllocationMethod): boolean {
    return ['fixed_percentage', 'manual_amount', 'headcount_weighted'].includes(method);
  }

  methodLabel(method: string): string {
    return this.config()?.allocation_methods.find(item => item.key === method)?.label || method.replace(/_/g, ' ');
  }

  weightLabel(method: AllocationMethod): string {
    if (method === 'fixed_percentage') return 'Fixed Percentages';
    if (method === 'manual_amount') return 'Manual Amounts';
    return 'Headcount / FTE Weights';
  }

  weightInputPlaceholder(method: AllocationMethod): string {
    if (method === 'fixed_percentage') return 'Percent';
    if (method === 'manual_amount') return 'Amount';
    return 'Weight';
  }

  weightDisplay(weight: AllocationWeightItem, method: AllocationMethod): string {
    if (method === 'fixed_percentage') return `${this.parseMoney(weight.percentage).toFixed(4)}%`;
    if (method === 'manual_amount') return this.formatMoney(weight.manual_amount);
    return `Weight ${this.parseMoney(weight.weight_value).toFixed(4)}`;
  }

  configuredPercentageTotal(rule: AllocationRule): string {
    return rule.structured_weights
      .reduce((total, row) => total + this.parseMoney(row.percentage), 0)
      .toFixed(4);
  }

  allocationPercent(pool: SharedCostPool): number {
    const amount = this.parseMoney(pool.amount_plan);
    if (!amount) return 0;
    return Math.max(0, Math.min(100, (this.parseMoney(pool.allocated_plan) / amount) * 100));
  }

  dimensionLabel(dimension: string): string {
    return this.targetDimensions.find(item => item.value === dimension)?.label || dimension;
  }

  targetValueOptions(dimension: TargetDimension): SelectOption[] {
    const config = this.config();
    if (!config) return [];
    if (dimension === 'initiative') {
      return config.initiatives.map(item => ({
        value: item.id,
        label: `${item.initiative_code || 'INIT'} · ${item.name}`,
      }));
    }
    if (dimension === 'workstream') {
      return config.workstreams.map(item => ({ value: item.id, label: item.name }));
    }
    if (dimension === 'business_unit') {
      return config.business_units.map(item => ({
        value: item.id,
        label: item.code ? `${item.code} · ${item.name}` : item.name,
      }));
    }
    if (dimension === 'tag') return config.tags.map(item => ({ value: item, label: item }));
    if (dimension === 'country') return config.countries.map(item => ({ value: item, label: item }));
    if (dimension === 'stage') return config.stages.map(item => ({ value: item, label: item }));
    if (dimension === 'rag_status') {
      return ['green', 'amber', 'red', 'not_started'].map(item => ({ value: item, label: item.replace(/_/g, ' ') }));
    }
    return [];
  }

  targetOptionLabel(dimension: TargetDimension, value: string | null): string {
    if (!value) return 'All initiatives';
    return this.targetValueOptions(dimension).find(item => item.value === value)?.label || value;
  }

  targetDisplayValue(target: AllocationTargetItem): string {
    if (target.dimension_type === 'all') return 'All initiatives';
    return this.targetOptionLabel(target.dimension_type, target.dimension_value || null);
  }

  initiativeLabel(initiativeId?: string | null): string {
    const initiative = this.config()?.initiatives.find(item => item.id === initiativeId);
    if (!initiative) return initiativeId || 'Unknown initiative';
    return `${initiative.initiative_code || 'INIT'} · ${initiative.name}`;
  }

  formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(this.parseMoney(value));
  }

  formatPercent(value: string | number | null | undefined): string {
    return `${(this.parseMoney(value) * 100).toFixed(2)}%`;
  }

  parseMoney(value: string | number | null | undefined): number {
    const parsed = Number(value || 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private setDraftDefaultsFromConfig(): void {
    const config = this.config();
    if (!config) return;
    if (!this.poolDraft.cost_category_id && config.cost_categories.length) {
      this.poolDraft.cost_category_id = config.cost_categories[0].id;
      this.poolDraft.category_key = config.cost_categories[0].key;
    }
    if (!this.poolDraft.scenario_id && config.scenarios.length) {
      const primaryPlan = config.scenarios.find(item => item.kind === 'plan' && item.is_primary);
      this.poolDraft.scenario_id = (primaryPlan || config.scenarios[0]).id;
    }
  }

  private defaultPoolDraft(): {
    name: string;
    description: string;
    category_key: string;
    cost_category_id: string | null;
    scenario_id: string | null;
    year: number;
    amount_plan: string;
    amount_actual: string;
    period_grain: string;
    reporting_treatment: SharedCostReportingTreatment;
    currency_code: string;
  } {
    return {
      name: '',
      description: '',
      category_key: 'other',
      cost_category_id: null,
      scenario_id: null,
      year: new Date().getFullYear(),
      amount_plan: '0',
      amount_actual: '',
      period_grain: 'annual',
      reporting_treatment: 'report_only',
      currency_code: 'USD',
    };
  }

  private defaultRuleDraft(): {
    name: string;
    allocation_method: AllocationMethod;
    driver_metric_definition_id: string | null;
    driver_cost_category_id: string | null;
    driver_scenario_id: string | null;
    driver_period_mode: string;
    missing_basis_behavior: string;
  } {
    return {
      name: '',
      allocation_method: 'equal_split',
      driver_metric_definition_id: null,
      driver_cost_category_id: null,
      driver_scenario_id: null,
      driver_period_mode: 'pool_period',
      missing_basis_behavior: 'fail',
    };
  }

  private handleError(err: unknown, fallback: string): void {
    const detail = (err as { error?: { detail?: unknown; message?: string } })?.error?.detail;
    if (typeof detail === 'string') {
      this.error.set(detail);
      return;
    }
    if (detail && typeof detail === 'object' && 'message' in detail) {
      this.error.set(String((detail as { message: unknown }).message));
      return;
    }
    const message = (err as { error?: { message?: string }; message?: string })?.error?.message ||
      (err as { message?: string })?.message;
    this.error.set(message || fallback);
  }
}
