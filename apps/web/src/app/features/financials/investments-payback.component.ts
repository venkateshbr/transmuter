import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

interface PaybackSummary {
  benefits_total: string;
  recurring_costs: string;
  one_off_investment: string;
  net_run_rate_value: string;
  payback_months?: string | null;
  payback_label: string;
  initiatives_with_payback: number;
  initiatives_not_reached: number;
}

interface PaybackRow {
  initiative_id: string;
  initiative_code?: string | null;
  initiative_name: string;
  stage?: string | null;
  workstream_name?: string | null;
  benefits_total: string;
  recurring_costs: string;
  one_off_investment: string;
  net_run_rate_value: string;
  payback_months?: string | null;
  payback_label: string;
  payback_status: 'immediate' | 'payback' | 'not_reached' | 'no_investment';
}

interface PaybackResponse {
  value_year?: number | null;
  scenario: string;
  summary: PaybackSummary;
  rows: PaybackRow[];
}

@Component({
  selector: 'app-investments-payback',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="space-y-6 p-8" style="background:var(--t-bg)">
      <section class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financials</p>
          <h1 class="mt-1 text-2xl font-black text-[var(--t-text-primary)]">Investments & Payback</h1>
        </div>
        <div class="flex flex-wrap items-end gap-3">
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Value Year</span>
            <input type="number" min="2020" max="2060" class="input-field w-28 py-2 text-xs" [ngModel]="valueYear()" (ngModelChange)="setValueYear($event)" aria-label="Payback value year">
          </label>
          <label class="grid gap-1">
            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Scenario</span>
            <select class="input-field w-36 py-2 text-xs" [ngModel]="scenario()" (ngModelChange)="setScenario($event)" aria-label="Payback scenario">
              <option value="plan_base">Plan Base</option>
              <option value="plan_high">Plan High</option>
              <option value="actual">Actual</option>
            </select>
          </label>
          <button type="button" class="btn-secondary px-4 py-2 text-[10px]" (click)="load()" aria-label="Refresh investments and payback">Refresh</button>
        </div>
      </section>

      <section class="grid gap-4 md:grid-cols-5">
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">One-off Investment</p>
          <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().one_off_investment) }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Net Run-rate Value</p>
          <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().net_run_rate_value) }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Portfolio Payback</p>
          <p class="mt-2 text-xl font-black text-[var(--t-accent)]">{{ summary().payback_label || 'N/A' }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">With Payback</p>
          <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ summary().initiatives_with_payback || 0 }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Not Reached</p>
          <p class="mt-2 text-xl font-black text-[var(--t-text-primary)]">{{ summary().initiatives_not_reached || 0 }}</p>
        </div>
      </section>

      <section class="card overflow-hidden">
        <div class="flex items-center justify-between border-b border-[var(--t-border)] px-5 py-4">
          <div>
            <h2 class="text-sm font-black uppercase tracking-widest text-[var(--t-text-primary)]">Initiative Payback Ranking</h2>
            <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ response()?.value_year || 'Latest year' }} / {{ scenarioLabel() }}</p>
          </div>
          <a routerLink="/financials/initiative-portfolio" class="btn-ghost px-3 py-2 text-[10px]">Initiative Portfolio</a>
        </div>
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-[var(--t-border)] text-left text-xs">
            <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              <tr>
                <th class="px-4 py-3">Initiative</th>
                <th class="px-4 py-3">Workstream</th>
                <th class="px-4 py-3 text-right">Benefits</th>
                <th class="px-4 py-3 text-right">Recurring Costs</th>
                <th class="px-4 py-3 text-right">One-off Investment</th>
                <th class="px-4 py-3 text-right">Net Run-rate</th>
                <th class="px-4 py-3 text-right">Payback</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (row of rows(); track row.initiative_id) {
                <tr class="hover:bg-[var(--t-surface-raised)]">
                  <td class="px-4 py-3">
                    <a [routerLink]="['/initiatives', row.initiative_id]" class="font-black text-[var(--t-text-primary)] hover:text-[var(--t-accent)]">{{ row.initiative_code || '-' }} · {{ row.initiative_name }}</a>
                    <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.stage || 'Unstaged' }}</p>
                  </td>
                  <td class="px-4 py-3">{{ row.workstream_name || '-' }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMoney(row.benefits_total) }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMoney(row.recurring_costs) }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMoney(row.one_off_investment) }}</td>
                  <td class="px-4 py-3 text-right font-black text-[var(--t-text-primary)]">{{ formatMoney(row.net_run_rate_value) }}</td>
                  <td class="px-4 py-3 text-right font-black" [ngClass]="row.payback_status === 'not_reached' ? 'text-red-500' : 'text-[var(--t-accent)]'">{{ row.payback_label }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="px-4 py-8 text-center text-sm font-bold text-[var(--t-text-secondary)]">No investment or run-rate value data is available.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
})
export class InvestmentsPaybackComponent implements OnInit {
  private readonly api = inject(ApiService);
  response = signal<PaybackResponse | null>(null);
  valueYear = signal<number | null>(null);
  scenario = signal('plan_base');

  ngOnInit(): void {
    this.load();
  }

  summary(): PaybackSummary {
    return this.response()?.summary || {
      benefits_total: '0',
      recurring_costs: '0',
      one_off_investment: '0',
      net_run_rate_value: '0',
      payback_label: 'N/A',
      initiatives_with_payback: 0,
      initiatives_not_reached: 0,
    };
  }

  rows(): PaybackRow[] {
    return this.response()?.rows || [];
  }

  setValueYear(value: number | string): void {
    const numeric = Number(value || 0);
    this.valueYear.set(numeric > 0 ? numeric : null);
    this.load();
  }

  setScenario(value: string): void {
    this.scenario.set(value || 'plan_base');
    this.load();
  }

  load(): void {
    const params: Record<string, string | number> = { scenario: this.scenario() };
    if (this.valueYear()) params['value_year'] = this.valueYear() as number;
    this.api.get<PaybackResponse>('/portfolio/investments-payback', params).subscribe({
      next: response => this.response.set(response),
      error: () => this.response.set(null),
    });
  }

  scenarioLabel(): string {
    return this.scenario() === 'actual'
      ? 'Actual'
      : this.scenario() === 'plan_high'
        ? 'Plan High'
        : 'Plan Base';
  }

  formatMoney(value: string | number | null | undefined): string {
    const amount = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(amount);
  }
}
