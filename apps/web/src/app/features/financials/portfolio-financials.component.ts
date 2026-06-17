import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { financialModeUsesActuals, resolveFinancialMode, type FinancialModeDescriptor } from './financials-view.models';
import { PortfolioFinancialTrendComponent } from './portfolio-financial-trend.component';

type Granularity = 'monthly' | 'quarterly' | 'yearly';

interface SummaryCard {
  key: string;
  label: string;
  plan: string;
  actual: string;
  variance: string;
}

interface PeriodRow {
  period: string;
  year: number;
  quarter: number | null;
  month: number | null;
  benefits_plan: string;
  benefits_actual: string;
  recurring_costs_plan: string;
  recurring_costs_actual: string;
  one_off_costs_plan: string;
  one_off_costs_actual: string;
  total_costs_plan: string;
  total_costs_actual: string;
  net_value_plan: string;
  net_value_actual: string;
}

interface BreakdownRow {
  key: string;
  label: string;
  group_label?: string | null;
  plan: string;
  actual: string;
  variance: string;
}

interface PortfolioFinancialsResponse {
  granularity: Granularity;
  summary: SummaryCard[];
  periods: PeriodRow[];
  broader_period_totals: PeriodRow[];
  cost_breakdown: BreakdownRow[];
  metric_breakdown: BreakdownRow[];
  financial_mode?: unknown;
}

interface CostLineContribution {
  id: string;
  name: string;
  category_key: string;
  category_label?: string | null;
  is_recurring: boolean;
  plan: string;
  actual: string;
}

interface InitiativeContribution {
  initiative_id: string;
  initiative_name: string;
  benefits_plan: string;
  benefits_actual: string;
  recurring_costs_plan: string;
  recurring_costs_actual: string;
  one_off_costs_plan: string;
  one_off_costs_actual: string;
  total_costs_plan: string;
  total_costs_actual: string;
  net_value_plan: string;
  net_value_actual: string;
  cost_lines: CostLineContribution[];
}

interface ContributorsResponse {
  period: string;
  granularity: Granularity;
  contributors: InitiativeContribution[];
}

interface FinancialConfiguration {
  items: Array<{ key: string; label: string; item_type: string; is_active: boolean }>;
}

interface StageGateDefinition {
  id: string;
  label: string;
  from_stage: string;
  to_stage: string;
  is_active: boolean;
}

interface ValueRampPeriod extends PeriodRow {
  cumulative_net_value_plan: string;
  cumulative_net_value_actual: string;
}

interface ValueRampResponse {
  granularity: Granularity;
  run_rate_year: number | null;
  as_of_date: string | null;
  stage: string | null;
  periods: ValueRampPeriod[];
  in_year: SummaryCard[];
  financial_mode?: unknown;
}

interface AnnualBaselineValue {
  metric_definition_id: string;
  metric_key?: string | null;
  metric_label?: string | null;
  baseline_year: number;
  value: string;
}

interface TenantAnnualBaselineResponse {
  values: AnnualBaselineValue[];
}

@Component({
  selector: 'app-portfolio-financials',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, PortfolioFinancialTrendComponent],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Portfolio Office</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Financials<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Tenant-wide planned costs, optional benefits, and actual performance drilldowns by period.
          </p>
          <div class="mt-3 inline-flex items-center gap-2 border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2">
            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Data Basis</span>
            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Plan · Actuals · Original Baseline</span>
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-end gap-3">
          <div class="inline-flex border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-1">
            @for (option of granularities; track option.id) {
              <button
                type="button"
                class="px-3 py-2 text-[10px] font-black uppercase tracking-widest"
                [class.bg-[var(--t-primary)]]="granularity() === option.id"
                [class.text-white]="granularity() === option.id"
                [class.text-[var(--t-text-secondary)]]="granularity() !== option.id"
                [attr.aria-pressed]="granularity() === option.id"
                (click)="setGranularity(option.id)">
                {{ option.label }}
              </button>
            }
          </div>
          <button
            type="button"
            class="border px-3 py-2 text-[10px] font-black uppercase tracking-widest"
            [class.border-[var(--t-accent)]]="showBenefits()"
            [class.bg-[var(--t-accent-soft)]]="showBenefits()"
            [class.text-[var(--t-accent)]]="showBenefits()"
            [class.border-[var(--t-border)]]="!showBenefits()"
            [class.text-[var(--t-text-secondary)]]="!showBenefits()"
            [attr.aria-pressed]="showBenefits()"
            (click)="showBenefits.set(!showBenefits())">
            Benefits {{ showBenefits() ? 'On' : 'Off' }}
          </button>
          <button
            type="button"
            class="border px-3 py-2 text-[10px] font-black uppercase tracking-widest"
            [class.border-[var(--t-accent)]]="showActuals()"
            [class.bg-[var(--t-accent-soft)]]="showActuals()"
            [class.text-[var(--t-accent)]]="showActuals()"
            [class.border-[var(--t-border)]]="!showActuals()"
            [class.text-[var(--t-text-secondary)]]="!showActuals()"
            [class.opacity-50]="!actualsAvailable()"
            [class.cursor-not-allowed]="!actualsAvailable()"
            [attr.aria-pressed]="showActuals()"
            [disabled]="!actualsAvailable()"
            (click)="showActuals.set(!showActuals())">
            Actuals {{ actualsAvailable() ? (showActuals() ? 'On' : 'Off') : 'Unavailable' }}
          </button>
          <input class="input-field w-28 py-2 text-xs" type="number" [ngModel]="year()" (ngModelChange)="setYear($event)" aria-label="Filter financial year">
          <input class="input-field w-40 py-2 text-xs" type="date" [ngModel]="asOfDate()" (ngModelChange)="setAsOfDate($event)" aria-label="Plan as-of date">
          <select class="input-field w-52 py-2 text-xs" [ngModel]="stage()" (ngModelChange)="setStage($event)" aria-label="Filter stage">
            <option value="">All stages</option>
            @for (option of stageOptions(); track option.id) {
              <option [value]="option.id">{{ option.label }}</option>
            }
          </select>
          <select class="input-field w-48 py-2 text-xs" [ngModel]="categoryKey()" (ngModelChange)="setCategory($event)" aria-label="Filter cost category">
            <option value="">All categories</option>
            @for (category of costCategories(); track category.key) {
              <option [value]="category.key">{{ category.label }}</option>
            }
          </select>
        </div>
      </header>

      @if (hasPortfolioBaseline()) {
        <section class="grid gap-4 md:grid-cols-3">
          <div class="border border-[var(--t-border)] bg-[var(--t-primary)] p-5 text-white shadow-sm">
            <p class="text-[9px] font-black uppercase tracking-widest text-white/70">FY{{ portfolioBaselineYear() }} Portfolio Baseline</p>
            <p class="mt-4 text-2xl font-black">{{ formatMoney(annualRevenueBaseline()) }}</p>
            <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-white/70">Annual revenue</p>
          </div>
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5 shadow-sm">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">FY{{ portfolioBaselineYear() }} Portfolio Baseline</p>
            <p class="mt-4 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(annualGrossMarginBaseline()) }}</p>
            <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Annual gross margin</p>
          </div>
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5 shadow-sm">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Baseline Margin Rate</p>
            <p class="mt-4 text-2xl font-black text-[var(--t-text-primary)]">{{ baselineGrossMarginRateLabel() }}</p>
            <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Gross margin / revenue</p>
          </div>
        </section>
      }

      <section class="grid gap-4" [class.md:grid-cols-5]="showBenefits()" [class.md:grid-cols-3]="!showBenefits()">
        @for (card of visibleSummaryCards(); track card.key) {
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5 shadow-sm">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
            <p class="mt-4 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(card.plan) }}</p>
            <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Plan</p>
            @if (showActuals()) {
              <div class="mt-4 grid grid-cols-2 gap-2 border-t border-[var(--t-border)] pt-3 text-xs">
                <div>
                  <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Actual</p>
                  <p class="font-bold text-[var(--t-text-secondary)]">{{ formatMoney(card.actual) }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Variance</p>
                  <p class="font-bold" [class.text-emerald-600]="parseMoney(card.variance) >= 0" [class.text-red-500]="parseMoney(card.variance) < 0">{{ formatMoney(card.variance) }}</p>
                </div>
              </div>
            }
          </div>
        }
      </section>

      <app-portfolio-financial-trend
        [rows]="response()?.periods || []"
        [granularity]="granularity()"
        [showActuals]="showActuals()"
        [baselineValue]="grossMarginBaselinePerPeriod()"
        [baselineLabel]="trendBaselineLabel()"
        (periodSelected)="openTrendPeriod($event)" />

      <section class="grid gap-6 xl:grid-cols-[1fr_1.4fr]">
        <div class="card p-5">
          <div class="flex items-start justify-between gap-4">
            <div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">In-year value</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ year() || 'All years' }}</h2>
            </div>
            <span class="border border-[var(--t-border)] px-2 py-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              {{ selectedStageLabel() }}
            </span>
          </div>
          <div class="mt-5 grid gap-3 sm:grid-cols-2">
            @for (card of valueRamp()?.in_year || []; track card.key) {
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
                <p class="mt-2 text-lg font-black text-[var(--t-text-primary)]">{{ formatMoney(card.plan) }}</p>
                @if (showActuals()) {
                  <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">
                    {{ formatMoney(card.actual) }} actual · {{ formatMoney(card.variance) }} variance
                  </p>
                }
              </div>
            } @empty {
              <p class="text-sm font-bold text-[var(--t-text-secondary)]">No in-year value is available for the selected filters.</p>
            }
          </div>
        </div>

        <div class="card overflow-hidden">
          <div class="border-b border-[var(--t-border)] p-5">
            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Run-rate value ramp</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Cumulative net value</h2>
            <p class="mt-2 text-xs font-bold text-[var(--t-text-secondary)]">
              {{ valueRamp()?.periods?.length || 0 }} periods
              @if (asOfDate()) {
                <span> · as of {{ asOfDate() }}</span>
              }
            </p>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[680px] text-left text-xs">
              <thead class="bg-[var(--t-surface-raised)] text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                <tr>
                  <th class="px-4 py-3">Period</th>
                  <th class="px-4 py-3">Net Plan</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3">Net Actual</th>
                  }
                  <th class="px-4 py-3">Cumulative Plan</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3">Cumulative Actual</th>
                  }
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--t-border)]">
                @for (row of valueRamp()?.periods || []; track row.period) {
                  <tr>
                    <td class="px-4 py-3 font-black text-[var(--t-text-primary)]">{{ row.period }}</td>
                    <td class="px-4 py-3">{{ formatMoney(row.net_value_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-3">{{ formatMoney(row.net_value_actual) }}</td>
                    }
                    <td class="px-4 py-3 font-black text-[var(--t-accent)]">{{ formatMoney(row.cumulative_net_value_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-3 font-black text-[var(--t-accent)]">{{ formatMoney(row.cumulative_net_value_actual) }}</td>
                    }
                  </tr>
                } @empty {
                  <tr>
                    <td class="px-4 py-8 text-sm font-bold text-[var(--t-text-secondary)]" [attr.colspan]="showActuals() ? 5 : 3">No value ramp is available for the selected filters.</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <div class="card overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">{{ showActuals() ? 'Plan vs Actuals' : 'Planned Financials' }}</h2>
            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ granularity() }} · click a row for initiatives</span>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[900px] text-left text-xs">
              <thead class="bg-[var(--t-surface-raised)] text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                <tr>
                  <th class="px-4 py-3">Period</th>
                  @if (showBenefits()) {
                    <th class="px-4 py-3">Benefits Plan</th>
                    @if (showActuals()) {
                      <th class="px-4 py-3">Benefits Actual</th>
                      <th class="px-4 py-3">Benefits Var</th>
                    }
                  }
                  <th class="px-4 py-3">Recurring Plan</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3">Recurring Actual</th>
                    <th class="px-4 py-3">Recurring Var</th>
                  }
                  <th class="px-4 py-3">One-time Plan</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3">One-time Actual</th>
                    <th class="px-4 py-3">One-time Var</th>
                  }
                  <th class="px-4 py-3">Total Plan</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3">Total Actual</th>
                    <th class="px-4 py-3">Total Var</th>
                  }
                  @if (showBenefits()) {
                    <th class="px-4 py-3">Net Run-rate Plan</th>
                    @if (showActuals()) {
                      <th class="px-4 py-3">Net Run-rate Actual</th>
                      <th class="px-4 py-3">Net Run-rate Var</th>
                    }
                  }
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--t-border)]">
                @for (row of response()?.periods || []; track row.period) {
                  <tr
                    class="cursor-pointer hover:bg-[var(--t-surface-raised)]"
                    tabindex="0"
                    role="button"
                    [attr.aria-label]="'Show initiatives for ' + row.period"
                    (click)="openPeriod(row)"
                    (keyup.enter)="openPeriod(row)">
                    <td class="px-4 py-3 font-black text-[var(--t-text-primary)]">{{ row.period }}</td>
                    @if (showBenefits()) {
                      <td class="px-4 py-3">{{ formatMoney(row.benefits_plan) }}</td>
                      @if (showActuals()) {
                        <td class="px-4 py-3">{{ formatMoney(row.benefits_actual) }}</td>
                        <td class="px-4 py-3" [class.text-emerald-600]="delta(row.benefits_actual, row.benefits_plan) >= 0" [class.text-red-500]="delta(row.benefits_actual, row.benefits_plan) < 0">{{ formatMoney(delta(row.benefits_actual, row.benefits_plan)) }}</td>
                      }
                    }
                    <td class="px-4 py-3">{{ formatMoney(row.recurring_costs_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-3">{{ formatMoney(row.recurring_costs_actual) }}</td>
                      <td class="px-4 py-3" [class.text-emerald-600]="delta(row.recurring_costs_actual, row.recurring_costs_plan) <= 0" [class.text-red-500]="delta(row.recurring_costs_actual, row.recurring_costs_plan) > 0">{{ formatMoney(delta(row.recurring_costs_actual, row.recurring_costs_plan)) }}</td>
                    }
                    <td class="px-4 py-3">{{ formatMoney(row.one_off_costs_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-3">{{ formatMoney(row.one_off_costs_actual) }}</td>
                      <td class="px-4 py-3" [class.text-emerald-600]="delta(row.one_off_costs_actual, row.one_off_costs_plan) <= 0" [class.text-red-500]="delta(row.one_off_costs_actual, row.one_off_costs_plan) > 0">{{ formatMoney(delta(row.one_off_costs_actual, row.one_off_costs_plan)) }}</td>
                    }
                    <td class="px-4 py-3 font-bold">{{ formatMoney(row.total_costs_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-3">{{ formatMoney(row.total_costs_actual) }}</td>
                      <td class="px-4 py-3" [class.text-emerald-600]="delta(row.total_costs_actual, row.total_costs_plan) <= 0" [class.text-red-500]="delta(row.total_costs_actual, row.total_costs_plan) > 0">{{ formatMoney(delta(row.total_costs_actual, row.total_costs_plan)) }}</td>
                    }
                    @if (showBenefits()) {
                      <td class="px-4 py-3 font-black text-[var(--t-accent)]">{{ formatMoney(row.net_value_plan) }}</td>
                      @if (showActuals()) {
                        <td class="px-4 py-3 font-black text-[var(--t-accent)]">{{ formatMoney(row.net_value_actual) }}</td>
                        <td class="px-4 py-3" [class.text-emerald-600]="delta(row.net_value_actual, row.net_value_plan) >= 0" [class.text-red-500]="delta(row.net_value_actual, row.net_value_plan) < 0">{{ formatMoney(delta(row.net_value_actual, row.net_value_plan)) }}</td>
                      }
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <aside class="space-y-6">
          <div class="card p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Cost Breakdown</h2>
            <div class="mt-4 space-y-3">
              @for (row of response()?.cost_breakdown || []; track row.key) {
                <div class="border-l-2 border-[var(--t-blue-light)] pl-3">
                  <p class="text-sm font-black text-[var(--t-text-primary)]">{{ row.label }}</p>
                  <p class="text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.group_label || 'Category' }}</p>
                  <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">
                    {{ formatMoney(row.plan) }} plan
                    @if (showActuals()) {
                      <span> / {{ formatMoney(row.actual) }} actual</span>
                    }
                  </p>
                </div>
              }
            </div>
          </div>

          @if ((response()?.broader_period_totals || []).length) {
            <div class="card p-5">
              <h2 class="text-base font-black text-[var(--t-text-primary)]">Broader Period Rows</h2>
              <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Shown separately, not allocated</p>
              <div class="mt-4 space-y-3">
                @for (row of response()?.broader_period_totals || []; track row.period) {
                  <button
                    type="button"
                    class="flex w-full items-center justify-between border-b border-[var(--t-border)] pb-2 text-left"
                    (click)="openPeriod(row)"
                    [attr.aria-label]="'Show initiatives for broader period ' + row.period">
                    <span class="text-xs font-black text-[var(--t-text-primary)]">{{ row.period }}</span>
                    <span class="text-xs font-bold text-[var(--t-text-secondary)]">{{ formatMoney(row.total_costs_plan) }}</span>
                  </button>
                }
              </div>
            </div>
          }
        </aside>
      </section>

      @if (selectedPeriod()) {
        <div class="fixed inset-0 z-40 bg-black/40" (click)="closeDrawer()" aria-hidden="true"></div>
        <aside class="fixed right-0 top-0 z-50 h-full w-full max-w-2xl overflow-y-auto border-l border-[var(--t-border)] bg-[var(--t-surface)] p-6 shadow-2xl">
          <div class="flex items-start justify-between gap-4 border-b border-[var(--t-border)] pb-5">
            <div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Contributing initiatives</p>
              <h2 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ selectedPeriod()?.period }}</h2>
            </div>
            <button type="button" class="btn-ghost h-9 w-9 p-0" (click)="closeDrawer()" aria-label="Close contributor drawer">
              <span class="material-icons text-sm">close</span>
            </button>
          </div>

          @if (contributorsLoading()) {
            <div class="py-10 text-sm font-bold text-[var(--t-text-secondary)]">Loading contributors...</div>
          } @else if (!(contributors()?.contributors || []).length) {
            <div class="py-10 text-sm font-bold text-[var(--t-text-secondary)]">No initiatives contributed to this period under the current filters.</div>
          } @else {
            <div class="mt-6 space-y-5">
              @for (item of contributors()?.contributors || []; track item.initiative_id) {
                <section class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-5">
                  <div class="flex items-start justify-between gap-4">
                    <div>
                      <a [routerLink]="['/initiatives', item.initiative_id]" class="text-base font-black text-[var(--t-text-primary)] hover:text-[var(--t-accent)]">
                        {{ item.initiative_name }}
                      </a>
                      <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                        {{ formatMoney(item.total_costs_plan) }} planned costs
                      </p>
                    </div>
                    @if (showBenefits()) {
                      <div class="text-right">
                        <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Net Plan</p>
                        <p class="text-sm font-black text-[var(--t-accent)]">{{ formatMoney(item.net_value_plan) }}</p>
                      </div>
                    }
                  </div>

                  <div class="mt-5 grid gap-3 text-xs sm:grid-cols-3">
                    @if (showBenefits()) {
                      <div>
                        <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Benefits Plan</p>
                        <p class="font-bold">{{ formatMoney(item.benefits_plan) }}</p>
                      </div>
                    }
                    <div>
                      <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Recurring Plan</p>
                      <p class="font-bold">{{ formatMoney(item.recurring_costs_plan) }}</p>
                    </div>
                    <div>
                      <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">One-time Plan</p>
                      <p class="font-bold">{{ formatMoney(item.one_off_costs_plan) }}</p>
                    </div>
                  </div>

                  @if (showActuals()) {
                    <div class="mt-3 grid gap-3 border-t border-[var(--t-border)] pt-3 text-xs sm:grid-cols-3">
                      @if (showBenefits()) {
                        <div>
                          <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Benefits Actual</p>
                          <p class="font-bold">{{ formatMoney(item.benefits_actual) }}</p>
                        </div>
                      }
                      <div>
                        <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">Recurring Actual</p>
                        <p class="font-bold">{{ formatMoney(item.recurring_costs_actual) }}</p>
                      </div>
                      <div>
                        <p class="text-[9px] font-black uppercase text-[var(--t-text-tertiary)]">One-time Actual</p>
                        <p class="font-bold">{{ formatMoney(item.one_off_costs_actual) }}</p>
                      </div>
                    </div>
                  }

                  @if (item.cost_lines.length) {
                    <div class="mt-5 divide-y divide-[var(--t-border)] border-t border-[var(--t-border)] pt-2">
                      @for (line of item.cost_lines; track line.id) {
                        <div class="grid gap-2 py-3 text-xs sm:grid-cols-[1fr_auto] sm:items-center">
                          <div>
                            <p class="font-black text-[var(--t-text-primary)]">{{ line.name }}</p>
                            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                              {{ line.category_label || line.category_key }} · {{ line.is_recurring ? 'Recurring' : 'One-time' }}
                            </p>
                          </div>
                          <p class="font-bold text-[var(--t-text-secondary)]">
                            {{ formatMoney(line.plan) }} plan
                            @if (showActuals()) {
                              <span> / {{ formatMoney(line.actual) }} actual</span>
                            }
                          </p>
                        </div>
                      }
                    </div>
                  }
                </section>
              }
            </div>
          }
        </aside>
      }
    </div>
  `,
})
export class PortfolioFinancialsComponent implements OnInit {
  private readonly api = inject(ApiService);

  response = signal<PortfolioFinancialsResponse | null>(null);
  valueRamp = signal<ValueRampResponse | null>(null);
  contributors = signal<ContributorsResponse | null>(null);
  selectedPeriod = signal<PeriodRow | null>(null);
  contributorsLoading = signal(false);
  configuration = signal<FinancialConfiguration | null>(null);
  tenantAnnualBaselines = signal<AnnualBaselineValue[]>([]);
  stageGateDefinitions = signal<StageGateDefinition[]>([]);
  granularity = signal<Granularity>('monthly');
  year = signal<number | null>(new Date().getFullYear());
  categoryKey = signal('');
  stage = signal('');
  asOfDate = signal('');
  showBenefits = signal(false);
  showActuals = signal(false);
  financialMode = computed(() => resolveFinancialMode(this.response()?.financial_mode, this.response(), this.configuration()));
  actualsAvailable = computed(() => financialModeUsesActuals(this.financialMode()) || (this.response()?.periods || []).some(row => this.parseMoney(row.benefits_actual) !== 0 || this.parseMoney(row.total_costs_actual) !== 0 || this.parseMoney(row.net_value_actual) !== 0));

  readonly granularities: { id: Granularity; label: string }[] = [
    { id: 'monthly', label: 'Monthly' },
    { id: 'quarterly', label: 'Quarterly' },
    { id: 'yearly', label: 'Yearly' },
  ];

  costCategories = computed(() => (this.configuration()?.items || [])
    .filter(item => item.item_type === 'cost_category' && item.is_active));
  stageOptions = computed(() => {
    const seen = new Set<string>();
    const options: Array<{ id: string; label: string }> = [];
    for (const gate of this.stageGateDefinitions().filter(item => item.is_active !== false)) {
      for (const [id, label] of [[gate.from_stage, this.stageLabel(gate.from_stage)], [gate.to_stage, this.stageLabel(gate.to_stage)]]) {
        if (!id || seen.has(id)) continue;
        options.push({ id, label });
        seen.add(id);
      }
    }
    return options;
  });

  visibleSummaryCards = computed(() => {
    const summary = this.response()?.summary || [];
    if (this.showBenefits()) return summary;
    return summary.filter(card => !['benefits', 'net_value'].includes(card.key));
  });

  ngOnInit(): void {
    this.api.get<FinancialConfiguration>('/financial-configuration').subscribe({
      next: config => this.configuration.set(config),
      error: () => this.configuration.set({ items: [] }),
    });
    this.api.get<StageGateDefinition[]>('/governance/stage-gates').subscribe({
      next: gates => this.stageGateDefinitions.set(Array.isArray(gates) ? gates : []),
      error: () => this.stageGateDefinitions.set([]),
    });
    this.api.get<TenantAnnualBaselineResponse>('/financial-engine/annual-baselines').subscribe({
      next: res => this.tenantAnnualBaselines.set(Array.isArray(res.values) ? res.values : []),
      error: () => this.tenantAnnualBaselines.set([]),
    });
    this.load();
  }

  setGranularity(value: Granularity): void {
    this.granularity.set(value);
    this.closeDrawer();
    this.load();
  }

  setYear(value: string | number | null): void {
    const year = Number(value);
    this.year.set(Number.isFinite(year) && year > 0 ? year : null);
    this.closeDrawer();
    this.load();
  }

  setCategory(value: string): void {
    this.categoryKey.set(value || '');
    this.closeDrawer();
    this.load();
  }

  setStage(value: string): void {
    this.stage.set(value || '');
    this.closeDrawer();
    this.load();
  }

  setAsOfDate(value: string): void {
    this.asOfDate.set(value || '');
    this.loadValueRamp();
  }

  load(): void {
    const params = new URLSearchParams({ granularity: this.granularity() });
    if (this.year()) params.set('year', String(this.year()));
    if (this.categoryKey()) params.set('category_key', this.categoryKey());
    if (this.stage()) params.set('stage', this.stage());
    this.api.get<PortfolioFinancialsResponse>(`/portfolio/financials?${params.toString()}`)
      .subscribe(res => this.response.set(res));
    this.loadValueRamp();
  }

  loadValueRamp(): void {
    const params = new URLSearchParams({ granularity: this.granularity() });
    if (this.year()) params.set('run_rate_year', String(this.year()));
    if (this.categoryKey()) params.set('category_key', this.categoryKey());
    if (this.stage()) params.set('stage', this.stage());
    if (this.asOfDate()) params.set('as_of_date', this.asOfDate());
    this.api.get<ValueRampResponse>(`/portfolio/value-ramp?${params.toString()}`)
      .subscribe({
        next: res => this.valueRamp.set(res),
        error: () => this.valueRamp.set(null),
      });
  }

  openPeriod(row: PeriodRow): void {
    this.selectedPeriod.set(row);
    this.contributors.set(null);
    this.contributorsLoading.set(true);
    const params = new URLSearchParams({
      granularity: this.granularity(),
      period: row.period,
      year: String(row.year),
    });
    if (this.categoryKey()) params.set('category_key', this.categoryKey());
    if (this.stage()) params.set('stage', this.stage());
    this.api.get<ContributorsResponse>(`/portfolio/financials/contributors?${params.toString()}`)
      .subscribe({
        next: res => {
          this.contributors.set(res);
          this.contributorsLoading.set(false);
        },
        error: () => {
          this.contributors.set({ period: row.period, granularity: this.granularity(), contributors: [] });
          this.contributorsLoading.set(false);
        },
      });
  }

  openTrendPeriod(row: { period: string }): void {
    const period = (this.response()?.periods || []).find(item => item.period === row.period);
    if (period) this.openPeriod(period);
  }

  closeDrawer(): void {
    this.selectedPeriod.set(null);
    this.contributors.set(null);
    this.contributorsLoading.set(false);
  }

  delta(actual: string | number | null | undefined, plan: string | number | null | undefined): number {
    return this.parseMoney(actual) - this.parseMoney(plan);
  }

  formatMoney(value: string | number | null | undefined): string {
    const parsed = this.parseMoney(value);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(parsed);
  }

  parseMoney(value: string | number | null | undefined): number {
    if (value === null || value === undefined) return 0;
    const parsed = typeof value === 'string' ? Number(value) : value;
    return Number.isFinite(parsed) ? parsed : 0;
  }

  portfolioBaselineYear(): number | null {
    const years = this.baselineCandidateYears();
    if (!years.length) return null;
    const selectedYear = this.year();
    const eligibleYears = selectedYear ? years.filter(year => year <= selectedYear) : years;
    return Math.max(...(eligibleYears.length ? eligibleYears : years));
  }

  annualRevenueBaseline(): string | null {
    return this.baselineValue('annual_revenue_baseline');
  }

  annualGrossMarginBaseline(): string | null {
    return this.baselineValue('annual_gross_margin_baseline');
  }

  hasPortfolioBaseline(): boolean {
    return this.parseMoney(this.annualRevenueBaseline()) > 0 || this.parseMoney(this.annualGrossMarginBaseline()) > 0;
  }

  baselineGrossMarginRateLabel(): string {
    const revenue = this.parseMoney(this.annualRevenueBaseline());
    const margin = this.parseMoney(this.annualGrossMarginBaseline());
    if (revenue <= 0 || margin <= 0) return 'n/a';
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      maximumFractionDigits: 1,
    }).format(margin / revenue);
  }

  grossMarginBaselinePerPeriod(): number | null {
    const margin = this.parseMoney(this.annualGrossMarginBaseline());
    if (margin <= 0) return null;
    if (this.granularity() === 'monthly') return margin / 12;
    if (this.granularity() === 'quarterly') return margin / 4;
    return margin;
  }

  trendBaselineLabel(): string {
    const year = this.portfolioBaselineYear();
    return year ? `FY${year} GM baseline` : 'GM baseline';
  }

  selectedStageLabel(): string {
    const stage = this.stage();
    if (!stage) return 'All stages';
    return this.stageOptions().find(option => option.id === stage)?.label || this.stageLabel(stage);
  }

  private stageLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
  }

  private baselineCandidateYears(): number[] {
    const years = new Set<number>();
    for (const row of this.tenantAnnualBaselines()) {
      if (!['annual_revenue_baseline', 'annual_gross_margin_baseline'].includes(row.metric_key || '')) continue;
      const year = Number(row.baseline_year);
      if (Number.isFinite(year)) years.add(year);
    }
    return Array.from(years).sort((a, b) => a - b);
  }

  private baselineValue(metricKey: 'annual_revenue_baseline' | 'annual_gross_margin_baseline'): string | null {
    const year = this.portfolioBaselineYear();
    if (!year) return null;
    return this.tenantAnnualBaselines()
      .find(row => row.metric_key === metricKey && Number(row.baseline_year) === year)
      ?.value || null;
  }
}
