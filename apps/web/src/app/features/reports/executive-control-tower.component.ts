import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { financialModeUsesActuals, resolveFinancialMode, type FinancialModeDescriptor } from '../financials/financials-view.models';

type Persona = 'management' | 'investor' | 'owner';

@Component({
  selector: 'app-executive-control-tower',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Phase 2A</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Executive Control Tower<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Dependency risk, burdened value, and persona-ready governance signals from live portfolio data.
          </p>
          <div class="mt-3 inline-flex flex-wrap items-center gap-2 border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-3 py-2 text-[10px] font-black uppercase tracking-widest">
            <span class="text-[var(--t-text-tertiary)]">Mode</span>
            <span class="text-[var(--t-accent)]">{{ modeLabel() }}</span>
            @if (modeDescription()) {
              <span class="text-[var(--t-text-secondary)] normal-case tracking-normal">{{ modeDescription() }}</span>
            }
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <div class="inline-flex border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-1">
            @for (option of personas; track option.id) {
              <button
                type="button"
                class="px-3 py-2 text-[10px] font-black uppercase tracking-widest"
                [class.bg-[var(--t-primary)]]="persona() === option.id"
                [class.text-white]="persona() === option.id"
                [class.text-[var(--t-text-secondary)]]="persona() !== option.id"
                [attr.aria-pressed]="persona() === option.id"
                (click)="setPersona(option.id)"
              >{{ option.label }}</button>
            }
          </div>
          <input class="input-field w-28 py-2 text-xs" type="number" [ngModel]="targetYear()" (ngModelChange)="targetYear.set($event); load()" aria-label="Target year">
          <a routerLink="/shared-costs" class="btn-secondary text-[10px]">Shared Costs</a>
        </div>
      </header>

      <section class="grid gap-4 md:grid-cols-5">
        @for (card of summaryCards(); track card.label) {
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
            <p class="mt-4 text-2xl font-black text-[var(--t-text-primary)]">{{ card.value }}</p>
          </div>
        }
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div class="card overflow-hidden">
          <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Burdened Value Bridge</h2>
            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Direct + allocated costs</span>
          </div>
          <div class="grid gap-px bg-[var(--t-border)] md:grid-cols-3">
            @for (row of valueRows(); track row.label) {
              <div class="bg-[var(--t-surface)] p-5">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.label }}</p>
                <p class="mt-3 text-xl font-black text-[var(--t-text-primary)]">{{ formatMoney(row.plan) }}</p>
                @if (showActuals() && row.actual !== null) {
                  <p class="mt-1 text-xs font-bold text-[var(--t-accent)]">Actual {{ formatMoney(row.actual) }}</p>
                  <p class="mt-1 text-[10px] font-black uppercase tracking-widest" [class.text-emerald-600]="row.variance >= 0" [class.text-red-500]="row.variance < 0">Variance {{ formatMoney(row.variance) }}</p>
                }
              </div>
            }
          </div>
        </div>

        <div class="card overflow-hidden">
          <div class="border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Dependency Risk</h2>
          </div>
          <div class="grid grid-cols-2 gap-px bg-[var(--t-border)]">
            @for (row of dependencyRows(); track row.label) {
              <div class="bg-[var(--t-surface)] p-5">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.label }}</p>
                <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ row.value }}</p>
              </div>
            }
          </div>
        </div>
      </section>

      <section class="grid gap-6 xl:grid-cols-[0.8fr_1.2fr]">
        <div class="card overflow-hidden">
          <div class="border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Needs Attention</h2>
          </div>
          <div class="divide-y divide-[var(--t-border)]">
            @for (item of data()?.needs_attention || []; track item.initiative_id + item.reason) {
              <div class="p-4">
                <p class="text-xs font-black text-[var(--t-text-primary)]">{{ item.reason }}</p>
                <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.initiative_id }}</p>
              </div>
            } @empty {
              <div class="p-6 text-sm text-[var(--t-text-secondary)]">No control-tower exceptions for the selected view.</div>
            }
          </div>
        </div>

        <div class="card overflow-hidden">
          <div class="border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Initiative Burdening</h2>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[860px] text-left text-xs">
              <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                <tr>
                  <th class="px-4 py-3">Initiative</th>
                  <th class="px-4 py-3">RAG</th>
                  <th class="px-4 py-3">Realization</th>
                  <th class="px-4 py-3 text-right">Benefits</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3 text-right">Benefits Actual</th>
                  }
                  <th class="px-4 py-3 text-right">Burdened Cost</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3 text-right">Burdened Actual</th>
                  }
                  <th class="px-4 py-3 text-right">Net After Allocation</th>
                  @if (showActuals()) {
                    <th class="px-4 py-3 text-right">Net Actual</th>
                  }
                </tr>
              </thead>
              <tbody>
                @for (row of data()?.initiatives || []; track row.id) {
                  <tr class="border-t border-[var(--t-border)]">
                    <td class="px-4 py-4">
                      <a [routerLink]="['/initiatives', row.id]" class="font-black text-[var(--t-accent)]">{{ row.initiative_code }} · {{ row.name }}</a>
                    </td>
                    <td class="px-4 py-4 uppercase">{{ row.rag_status }}</td>
                    <td class="px-4 py-4 uppercase">{{ row.realization_status?.replace('_', ' ') }}</td>
                    <td class="px-4 py-4 text-right">{{ formatMoney(row.benefits_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-4 text-right">{{ formatMoney(row.benefits_actual) }}</td>
                    }
                    <td class="px-4 py-4 text-right">{{ formatMoney(row.total_burdened_costs_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-4 text-right">{{ formatMoney(row.total_burdened_costs_actual) }}</td>
                    }
                    <td class="px-4 py-4 text-right font-black">{{ formatMoney(row.net_after_allocation_plan) }}</td>
                    @if (showActuals()) {
                      <td class="px-4 py-4 text-right font-black">{{ formatMoney(row.net_after_allocation_actual) }}</td>
                    }
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  `,
})
export class ExecutiveControlTowerComponent implements OnInit {
  private readonly api = inject(ApiService);
  data = signal<any | null>(null);
  persona = signal<Persona>('management');
  targetYear = signal<number | null>(new Date().getFullYear());
  financialMode = computed<FinancialModeDescriptor>(() => resolveFinancialMode(this.data()?.financial_mode, this.data()?.value_bridge, this.data()?.summary, this.data()));
  showActuals = computed(() => financialModeUsesActuals(this.financialMode()) || Boolean(this.data()?.value_bridge?.benefits_actual || this.data()?.value_bridge?.net_actual || this.data()?.initiatives?.some?.((row: any) => row?.benefits_actual !== undefined || row?.total_burdened_costs_actual !== undefined || row?.net_after_allocation_actual !== undefined)));
  readonly personas: { id: Persona; label: string }[] = [
    { id: 'management', label: 'Management' },
    { id: 'investor', label: 'Investor' },
    { id: 'owner', label: 'Owner' },
  ];

  summaryCards = computed(() => {
    const summary = this.data()?.summary || {};
    return [
      { label: 'Initiatives', value: summary.initiative_count || 0 },
      { label: 'Red', value: summary.red || 0 },
      { label: 'Amber', value: summary.amber || 0 },
      { label: 'Realized', value: summary.realized || 0 },
      { label: 'Attention', value: summary.needs_attention || 0 },
    ];
  });

  valueRows = computed(() => {
    const bridge = this.data()?.value_bridge || {};
    return [
      { label: 'Benefits', plan: bridge.benefits_plan, actual: this.showActuals() ? (bridge.benefits_actual ?? bridge.actual?.benefits_total ?? null) : null, variance: Number(bridge.benefits_actual ?? bridge.actual?.benefits_total ?? bridge.benefits_plan ?? 0) - Number(bridge.benefits_plan ?? 0) },
      { label: 'Direct Costs', plan: bridge.direct_costs_plan, actual: this.showActuals() ? (bridge.direct_costs_actual ?? bridge.actual?.direct_costs_total ?? null) : null, variance: Number(bridge.direct_costs_actual ?? bridge.actual?.direct_costs_total ?? bridge.direct_costs_plan ?? 0) - Number(bridge.direct_costs_plan ?? 0) },
      { label: 'Allocated Costs', plan: bridge.allocated_costs_plan, actual: this.showActuals() ? (bridge.allocated_costs_actual ?? bridge.actual?.allocated_costs_total ?? null) : null, variance: Number(bridge.allocated_costs_actual ?? bridge.actual?.allocated_costs_total ?? bridge.allocated_costs_plan ?? 0) - Number(bridge.allocated_costs_plan ?? 0) },
      { label: 'Burdened Costs', plan: bridge.total_burdened_costs_plan, actual: this.showActuals() ? (bridge.total_burdened_costs_actual ?? bridge.actual?.costs_total ?? null) : null, variance: Number(bridge.total_burdened_costs_actual ?? bridge.actual?.costs_total ?? bridge.total_burdened_costs_plan ?? 0) - Number(bridge.total_burdened_costs_plan ?? 0) },
      { label: 'Net Before Allocation', plan: bridge.net_before_allocation_plan, actual: this.showActuals() ? (bridge.net_before_allocation_actual ?? bridge.actual?.net_before_allocation ?? null) : null, variance: Number(bridge.net_before_allocation_actual ?? bridge.actual?.net_before_allocation ?? bridge.net_before_allocation_plan ?? 0) - Number(bridge.net_before_allocation_plan ?? 0) },
      { label: 'Net After Allocation', plan: bridge.net_after_allocation_plan, actual: this.showActuals() ? (bridge.net_after_allocation_actual ?? bridge.actual?.net_after_allocation ?? null) : null, variance: Number(bridge.net_after_allocation_actual ?? bridge.actual?.net_after_allocation ?? bridge.net_after_allocation_plan ?? 0) - Number(bridge.net_after_allocation_plan ?? 0) },
    ];
  });

  dependencyRows = computed(() => {
    const rollups = this.data()?.dependency_risk || {};
    return [
      { label: 'Total', value: rollups.total || 0 },
      { label: 'Blocking', value: rollups.blocking || 0 },
      { label: 'At Risk', value: rollups.at_risk || 0 },
      { label: 'Overdue', value: rollups.overdue || 0 },
      { label: 'Critical Path', value: rollups.critical_path_risk || 0 },
      { label: 'Resolved', value: rollups.resolved || 0 },
    ];
  });

  modeLabel(): string {
    return this.financialMode().label;
  }

  modeDescription(): string | null {
    return this.financialMode().description || null;
  }

  ngOnInit(): void {
    this.load();
  }

  setPersona(next: Persona): void {
    this.persona.set(next);
    this.load();
  }

  load(): void {
    const route = this.persona() === 'owner'
      ? '/reports/owner-cockpit'
      : this.persona() === 'investor'
        ? '/reports/investor-summary'
        : '/reports/executive-control-tower';
    const params: Record<string, string | number> = {};
    if (this.targetYear()) params['target_year'] = this.targetYear() as number;
    this.api.get<any>(route, params).subscribe(res => this.data.set(res));
  }

  formatMoney(value: string | number | null | undefined): string {
    const n = Number(value || 0);
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
  }
}
