import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

interface PortfolioMetricColumn {
  metric_definition_id: string;
  key: string;
  label: string;
  value_type: 'currency' | 'percent' | 'number';
  unit?: string | null;
}

interface PortfolioBaselineReconciliation {
  metric_key: string;
  metric_label: string;
  tenant_value: string;
  initiative_total: string;
  variance: string;
  reconciled: boolean;
}

interface PortfolioInitiativeRow {
  initiative_id: string;
  initiative_code?: string | null;
  initiative_name: string;
  stage?: string | null;
  tag?: string | null;
  workstream_id?: string | null;
  workstream_name?: string | null;
  business_unit_ids: string[];
  business_unit_names: string[];
  baseline_values: Record<string, string>;
  baseline_complete: boolean;
  value_metric_values: Record<string, string>;
  benefits_total: string;
  recurring_costs: string;
  one_off_costs: string;
  net_run_rate_value: string;
}

interface PortfolioTotals {
  baseline_values: Record<string, string>;
  value_metric_values: Record<string, string>;
  benefits_total: string;
  recurring_costs: string;
  one_off_costs: string;
  net_run_rate_value: string;
}

interface InitiativePortfolioResponse {
  baseline_year: number | null;
  value_year: number | null;
  scenario: string;
  available_baseline_years: number[];
  available_value_years: number[];
  baseline_metrics: PortfolioMetricColumn[];
  value_metrics: PortfolioMetricColumn[];
  tenant_baseline_values: Record<string, string>;
  baseline_reconciliation: PortfolioBaselineReconciliation[];
  rows: PortfolioInitiativeRow[];
  totals: PortfolioTotals;
}

@Component({
  selector: 'app-initiative-portfolio',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="p-8 space-y-8" data-testid="initiative-portfolio-page">
      <header class="flex flex-wrap items-start justify-between gap-4 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Portfolio Financials</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Initiative Portfolio</h1>
          <p class="mt-2 max-w-4xl text-sm font-semibold text-[var(--t-text-secondary)]">
            Initiative-level baseline allocation and selected value-year delivery from the configurable financial engine.
          </p>
        </div>
        <div class="flex flex-wrap gap-2">
          <a routerLink="/financials" class="btn-ghost px-3 py-2 text-[10px]">
            <span class="material-icons text-sm">arrow_back</span>
            Financial Overview
          </a>
          <a routerLink="/financials/benefits-register" class="btn-secondary px-3 py-2 text-[10px]">
            <span class="material-icons text-sm">fact_check</span>
            Benefits Register
          </a>
        </div>
      </header>

      <section class="border bg-[var(--t-surface-raised)] p-4" style="border-color:var(--t-border)" data-testid="initiative-portfolio-filters">
        <div class="grid gap-3 md:grid-cols-2 xl:grid-cols-7">
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Baseline Year</span>
            <select class="input-field py-2 text-xs" [ngModel]="effectiveBaselineYear()" (ngModelChange)="setBaselineYear($event)" aria-label="Select baseline year">
              @for (year of baselineYearOptions(); track year) {
                <option [value]="year">{{ year }}</option>
              }
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Value Year</span>
            <select class="input-field py-2 text-xs" [ngModel]="effectiveValueYear()" (ngModelChange)="setValueYear($event)" aria-label="Select value year">
              @for (year of valueYearOptions(); track year) {
                <option [value]="year">{{ year }}</option>
              }
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Scenario</span>
            <select class="input-field py-2 text-xs" [ngModel]="scenario()" (ngModelChange)="setScenario($event)" aria-label="Select scenario">
              <option value="plan_base">Plan Base</option>
              <option value="plan_high">Plan High</option>
              <option value="actual">Actual</option>
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Workstream</span>
            <select class="input-field py-2 text-xs" [ngModel]="workstreamId()" (ngModelChange)="setWorkstream($event)" aria-label="Filter by workstream">
              <option value="">All</option>
              @for (item of workstreamOptions(); track item.id) {
                <option [value]="item.id">{{ item.name }}</option>
              }
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Business Unit</span>
            <select class="input-field py-2 text-xs" [ngModel]="businessUnitId()" (ngModelChange)="setBusinessUnit($event)" aria-label="Filter by business unit">
              <option value="">All</option>
              @for (item of businessUnitOptions(); track item.id) {
                <option [value]="item.id">{{ item.name }}</option>
              }
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Stage</span>
            <select class="input-field py-2 text-xs" [ngModel]="stage()" (ngModelChange)="setStage($event)" aria-label="Filter by stage">
              <option value="">All</option>
              @for (item of stageOptions(); track item) {
                <option [value]="item">{{ stageLabel(item) }}</option>
              }
            </select>
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Tag</span>
            <select class="input-field py-2 text-xs" [ngModel]="tag()" (ngModelChange)="setTag($event)" aria-label="Filter by tag">
              <option value="">All</option>
              @for (item of tagOptions(); track item) {
                <option [value]="item">{{ item }}</option>
              }
            </select>
          </label>
        </div>
      </section>

      <section class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div class="card border-l-4 border-[var(--t-accent)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiatives</p>
          <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ response()?.rows?.length || 0 }}</p>
        </div>
        <div class="card p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">EBITDA Benefits</p>
          <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMetric(response()?.totals?.benefits_total, 'currency') }}</p>
        </div>
        <div class="card p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Recurring Costs</p>
          <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMetric(response()?.totals?.recurring_costs, 'currency') }}</p>
        </div>
        <div class="card p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Net Run-rate Value</p>
          <p class="mt-2 text-2xl font-black text-[var(--t-accent)]">{{ formatMetric(response()?.totals?.net_run_rate_value, 'currency') }}</p>
        </div>
      </section>

      <section class="card overflow-hidden" data-testid="initiative-portfolio-table">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Baseline Allocation and Value Delivery</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">
              FY{{ response()?.baseline_year || 'n/a' }} baseline to FY{{ response()?.value_year || 'n/a' }} {{ scenarioLabel() }}
            </h2>
          </div>
          <div class="flex flex-wrap gap-2">
            @for (item of response()?.baseline_reconciliation || []; track item.metric_key) {
              <span
                class="border px-3 py-2 text-[10px] font-black uppercase tracking-widest"
                [class.text-emerald-600]="item.reconciled"
                [class.text-red-500]="!item.reconciled"
                style="border-color:var(--t-border)">
                {{ item.metric_label }}: {{ item.reconciled ? 'Reconciles' : 'Variance ' + formatMetric(item.variance, 'currency') }}
              </span>
            }
          </div>
        </div>

        <div class="overflow-auto">
          <table class="min-w-full border-collapse text-left text-xs">
            <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-secondary)]">
              <tr>
                <th class="sticky left-0 z-10 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">Code</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3">Initiative</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3">BU</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3">Workstream</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3">Stage</th>
                @for (metric of response()?.baseline_metrics || []; track metric.key) {
                  <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">FY{{ response()?.baseline_year }} {{ metric.label }}</th>
                }
                @for (metric of response()?.value_metrics || []; track metric.key) {
                  <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">FY{{ response()?.value_year }} {{ metric.label }}</th>
                }
                <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">EBITDA Benefits</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">Recurring Cost</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">One-off Cost</th>
                <th class="border-b border-[var(--t-border)] px-4 py-3 text-right">Net Run-rate</th>
              </tr>
            </thead>
            <tbody>
              @for (row of response()?.rows || []; track row.initiative_id) {
                <tr class="border-b border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]">
                  <td class="sticky left-0 z-10 bg-[var(--t-surface)] px-4 py-3 font-black text-[var(--t-text-primary)]">
                    <a [routerLink]="['/initiatives', row.initiative_id]" class="hover:text-[var(--t-accent)]">{{ row.initiative_code || '-' }}</a>
                  </td>
                  <td class="min-w-64 px-4 py-3 font-bold text-[var(--t-text-primary)]">{{ row.initiative_name }}</td>
                  <td class="min-w-44 px-4 py-3 text-[var(--t-text-secondary)]">{{ row.business_unit_names.join(', ') || '-' }}</td>
                  <td class="min-w-44 px-4 py-3 text-[var(--t-text-secondary)]">{{ row.workstream_name || '-' }}</td>
                  <td class="px-4 py-3 text-[var(--t-text-secondary)]">{{ stageLabel(row.stage || '') }}</td>
                  @for (metric of response()?.baseline_metrics || []; track metric.key) {
                    <td class="px-4 py-3 text-right font-bold" [class.text-red-500]="!row.baseline_complete">
                      {{ formatMetric(row.baseline_values[metric.key], metric.value_type) }}
                    </td>
                  }
                  @for (metric of response()?.value_metrics || []; track metric.key) {
                    <td class="px-4 py-3 text-right">{{ formatMetric(row.value_metric_values[metric.key], metric.value_type) }}</td>
                  }
                  <td class="px-4 py-3 text-right font-bold">{{ formatMetric(row.benefits_total, 'currency') }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMetric(row.recurring_costs, 'currency') }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMetric(row.one_off_costs, 'currency') }}</td>
                  <td class="px-4 py-3 text-right font-black text-[var(--t-accent)]">{{ formatMetric(row.net_run_rate_value, 'currency') }}</td>
                </tr>
              }
              @if (!loading() && !(response()?.rows || []).length) {
                <tr>
                  <td class="px-4 py-8 text-center text-sm font-bold text-[var(--t-text-secondary)]" [attr.colspan]="tableColspan()">No initiatives match the selected filters.</td>
                </tr>
              }
            </tbody>
            @if (response()?.rows?.length) {
              <tfoot class="bg-[var(--t-primary)] text-white">
                <tr>
                  <td class="sticky left-0 z-10 bg-[var(--t-primary)] px-4 py-4 font-black">Total</td>
                  <td class="px-4 py-4"></td>
                  <td class="px-4 py-4"></td>
                  <td class="px-4 py-4"></td>
                  <td class="px-4 py-4"></td>
                  @for (metric of response()?.baseline_metrics || []; track metric.key) {
                    <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.baseline_values?.[metric.key], metric.value_type) }}</td>
                  }
                  @for (metric of response()?.value_metrics || []; track metric.key) {
                    <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.value_metric_values?.[metric.key], metric.value_type) }}</td>
                  }
                  <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.benefits_total, 'currency') }}</td>
                  <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.recurring_costs, 'currency') }}</td>
                  <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.one_off_costs, 'currency') }}</td>
                  <td class="px-4 py-4 text-right font-black">{{ formatMetric(response()?.totals?.net_run_rate_value, 'currency') }}</td>
                </tr>
              </tfoot>
            }
          </table>
        </div>
      </section>
    </div>
  `,
})
export class InitiativePortfolioComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly loading = signal(false);
  readonly response = signal<InitiativePortfolioResponse | null>(null);
  readonly baselineYear = signal<number | null>(null);
  readonly valueYear = signal<number | null>(null);
  readonly scenario = signal('plan_base');
  readonly workstreamId = signal('');
  readonly businessUnitId = signal('');
  readonly stage = signal('');
  readonly tag = signal('');

  readonly baselineYearOptions = computed(() => this.withCurrentYear(
    this.response()?.available_baseline_years || [],
    this.effectiveBaselineYear(),
  ));

  readonly valueYearOptions = computed(() => this.withCurrentYear(
    this.response()?.available_value_years || [],
    this.effectiveValueYear(),
  ));

  readonly workstreamOptions = computed(() => {
    const options = new Map<string, string>();
    for (const row of this.response()?.rows || []) {
      if (row.workstream_id) options.set(row.workstream_id, row.workstream_name || row.workstream_id);
    }
    return Array.from(options, ([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  });

  readonly businessUnitOptions = computed(() => {
    const options = new Map<string, string>();
    for (const row of this.response()?.rows || []) {
      row.business_unit_ids.forEach((id, index) => options.set(id, row.business_unit_names[index] || id));
    }
    return Array.from(options, ([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  });

  readonly stageOptions = computed(() => this.uniqueRowValues(row => row.stage));
  readonly tagOptions = computed(() => this.uniqueRowValues(row => row.tag));

  ngOnInit(): void {
    this.load();
  }

  effectiveBaselineYear(): number | null {
    return this.baselineYear() ?? this.response()?.baseline_year ?? null;
  }

  effectiveValueYear(): number | null {
    return this.valueYear() ?? this.response()?.value_year ?? null;
  }

  setBaselineYear(value: string | number): void {
    this.baselineYear.set(this.numberOrNull(value));
    this.load();
  }

  setValueYear(value: string | number): void {
    this.valueYear.set(this.numberOrNull(value));
    this.load();
  }

  setScenario(value: string): void {
    this.scenario.set(value || 'plan_base');
    this.load();
  }

  setWorkstream(value: string): void {
    this.workstreamId.set(value || '');
    this.load();
  }

  setBusinessUnit(value: string): void {
    this.businessUnitId.set(value || '');
    this.load();
  }

  setStage(value: string): void {
    this.stage.set(value || '');
    this.load();
  }

  setTag(value: string): void {
    this.tag.set(value || '');
    this.load();
  }

  load(): void {
    this.loading.set(true);
    const params = new URLSearchParams({ scenario: this.scenario() });
    if (this.baselineYear()) params.set('baseline_year', String(this.baselineYear()));
    if (this.valueYear()) params.set('value_year', String(this.valueYear()));
    if (this.workstreamId()) params.set('workstream_id', this.workstreamId());
    if (this.businessUnitId()) params.set('business_unit_id', this.businessUnitId());
    if (this.stage()) params.set('stage', this.stage());
    if (this.tag()) params.set('tag', this.tag());
    this.api.get<InitiativePortfolioResponse>(`/portfolio/initiative-portfolio?${params.toString()}`).subscribe({
      next: response => {
        this.response.set(response);
        this.loading.set(false);
      },
      error: () => {
        this.response.set(null);
        this.loading.set(false);
      },
    });
  }

  scenarioLabel(): string {
    if (this.scenario() === 'plan_high') return 'Plan High';
    if (this.scenario() === 'actual') return 'Actual';
    return 'Plan Base';
  }

  stageLabel(value: string): string {
    if (!value) return '-';
    return value.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
  }

  tableColspan(): number {
    const response = this.response();
    return 5
      + (response?.baseline_metrics?.length || 0)
      + (response?.value_metrics?.length || 0)
      + 4;
  }

  formatMetric(value: string | number | null | undefined, type: PortfolioMetricColumn['value_type'] | 'currency'): string {
    const parsed = this.parseNumber(value);
    if (type === 'percent') {
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(parsed) + '%';
    }
    if (type === 'number') {
      return new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(parsed);
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(parsed);
  }

  private parseNumber(value: string | number | null | undefined): number {
    if (value === null || value === undefined || value === '') return 0;
    const parsed = typeof value === 'number' ? value : Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  private numberOrNull(value: string | number): number | null {
    const parsed = typeof value === 'number' ? value : Number.parseInt(value || '', 10);
    return Number.isFinite(parsed) ? parsed : null;
  }

  private withCurrentYear(years: number[], current: number | null): number[] {
    const set = new Set(years);
    if (current) set.add(current);
    return Array.from(set).sort((a, b) => a - b);
  }

  private uniqueRowValues(project: (row: PortfolioInitiativeRow) => string | null | undefined): string[] {
    const values = new Set<string>();
    for (const row of this.response()?.rows || []) {
      const value = project(row);
      if (value) values.add(value);
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b));
  }
}
