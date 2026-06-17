import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';

type BenefitValidationStatus = 'draft' | 'submitted' | 'finance_validated' | 'rejected';

interface BenefitsRegisterItem {
  initiative_id: string;
  initiative_code?: string | null;
  initiative_name: string;
  stage?: string | null;
  workstream_name?: string | null;
  benefit_line_id: string;
  benefit_line_name: string;
  metric_label: string;
  validation_status: BenefitValidationStatus;
  confidence?: string | null;
  risk_rating: 'low' | 'medium' | 'high';
  risk_adjustment_pct: string;
  plan: string;
  actual: string;
  variance: string;
  risk_adjusted_plan: string;
  evidence_url?: string | null;
  evidence_label?: string | null;
  handoff_status: string;
}

interface BenefitsRegisterResponse {
  year?: number | null;
  validation_status?: BenefitValidationStatus | null;
  totals: {
    plan: string;
    actual: string;
    variance: string;
    risk_adjusted_plan: string;
    validated_plan: string;
    submitted_plan: string;
    rejected_plan: string;
  };
  items: BenefitsRegisterItem[];
}

@Component({
  selector: 'app-benefits-register',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen p-8 space-y-6" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financials / Benefits Register</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Benefits Register<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Portfolio benefit lines with Finance validation, evidence, risk adjustment, and realization handoff status.
          </p>
        </div>
        <div class="flex flex-wrap items-center justify-end gap-3">
          <input class="input-field w-28 py-2 text-xs" type="number" [ngModel]="year()" (ngModelChange)="setYear($event)" aria-label="Filter benefits register year">
          <select class="input-field w-52 py-2 text-xs" [ngModel]="validationStatus()" (ngModelChange)="setValidationStatus($event)" aria-label="Filter validation status">
            <option value="">All validation states</option>
            <option value="draft">Draft</option>
            <option value="submitted">Submitted</option>
            <option value="finance_validated">Finance validated</option>
            <option value="rejected">Rejected</option>
          </select>
          <a routerLink="/financials" class="btn-ghost px-3 py-2 text-[10px]">Financial Overview</a>
        </div>
      </header>

      <section class="grid gap-4 md:grid-cols-4">
        @for (card of totalCards(); track card.label) {
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5 shadow-sm">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ card.label }}</p>
            <p class="mt-4 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(card.value) }}</p>
          </div>
        }
      </section>

      <section class="card overflow-hidden">
        <div class="border-b border-[var(--t-border)] p-5">
          <h2 class="text-base font-black text-[var(--t-text-primary)]">Benefit lines</h2>
          <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ data()?.items?.length || 0 }} lines</p>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full min-w-[1100px] text-left text-xs">
            <thead class="bg-[var(--t-surface-raised)] text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
              <tr>
                <th class="px-4 py-3">Initiative</th>
                <th class="px-4 py-3">Benefit line</th>
                <th class="px-4 py-3">Status</th>
                <th class="px-4 py-3 text-right">Plan</th>
                <th class="px-4 py-3 text-right">Actual</th>
                <th class="px-4 py-3 text-right">Risk adjusted</th>
                <th class="px-4 py-3">Risk / handoff</th>
                <th class="px-4 py-3">Evidence</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (item of data()?.items || []; track item.benefit_line_id) {
                <tr>
                  <td class="px-4 py-3">
                    <a [routerLink]="['/initiatives', item.initiative_id]" class="font-black text-[var(--t-text-primary)] hover:text-[var(--t-accent)]">{{ item.initiative_name }}</a>
                    <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.initiative_code || 'No code' }} · {{ item.workstream_name || 'Unassigned' }}</p>
                  </td>
                  <td class="px-4 py-3">
                    <p class="font-black text-[var(--t-text-primary)]">{{ item.benefit_line_name }}</p>
                    <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.metric_label }}</p>
                  </td>
                  <td class="px-4 py-3">
                    <span class="text-[9px] font-black uppercase tracking-widest" [class.text-emerald-600]="item.validation_status === 'finance_validated'" [class.text-red-500]="item.validation_status === 'rejected'" [class.text-[var(--t-accent)]]="item.validation_status === 'submitted'" [class.text-[var(--t-text-tertiary)]]="item.validation_status === 'draft'">
                      {{ validationLabel(item.validation_status) }}
                    </span>
                  </td>
                  <td class="px-4 py-3 text-right font-bold">{{ formatMoney(item.plan) }}</td>
                  <td class="px-4 py-3 text-right">{{ formatMoney(item.actual) }}</td>
                  <td class="px-4 py-3 text-right font-black text-[var(--t-accent)]">{{ formatMoney(item.risk_adjusted_plan) }}</td>
                  <td class="px-4 py-3">
                    <p class="font-bold text-[var(--t-text-primary)]">{{ item.risk_rating }} · {{ item.risk_adjustment_pct }}%</p>
                    <p class="mt-1 text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ handoffLabel(item.handoff_status) }}</p>
                  </td>
                  <td class="px-4 py-3">
                    @if (item.evidence_url) {
                      <a [href]="item.evidence_url" target="_blank" rel="noopener" class="font-bold underline text-[var(--t-accent)]">{{ item.evidence_label || 'Evidence' }}</a>
                    } @else {
                      <span class="text-[var(--t-text-tertiary)]">None</span>
                    }
                  </td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="8" class="px-4 py-10 text-sm font-bold text-[var(--t-text-secondary)]">No benefit lines match the selected filters.</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </section>
    </div>
  `,
})
export class BenefitsRegisterComponent implements OnInit {
  private readonly api = inject(ApiService);

  data = signal<BenefitsRegisterResponse | null>(null);
  year = signal<number | null>(null);
  validationStatus = signal('');

  ngOnInit(): void {
    this.load();
  }

  setYear(value: string | number | null): void {
    const year = Number(value);
    this.year.set(Number.isFinite(year) && year > 0 ? year : null);
    this.load();
  }

  setValidationStatus(value: string): void {
    this.validationStatus.set(value || '');
    this.load();
  }

  load(): void {
    const params = new URLSearchParams();
    if (this.year()) params.set('year', String(this.year()));
    if (this.validationStatus()) params.set('validation_status', this.validationStatus());
    this.api.get<BenefitsRegisterResponse>(`/portfolio/benefits-register?${params.toString()}`).subscribe({
      next: data => this.data.set(data),
      error: () => this.data.set(null),
    });
  }

  totalCards(): Array<{ label: string; value: string }> {
    const totals = this.data()?.totals;
    if (!totals) return [];
    return [
      { label: 'Plan benefits', value: totals.plan },
      { label: 'Actual benefits', value: totals.actual },
      { label: 'Risk-adjusted plan', value: totals.risk_adjusted_plan },
      { label: 'Finance validated', value: totals.validated_plan },
    ];
  }

  formatMoney(value: string | number | null | undefined): string {
    const parsed = Number(value || 0);
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(Number.isFinite(parsed) ? parsed : 0);
  }

  validationLabel(status: BenefitValidationStatus): string {
    if (status === 'finance_validated') return 'Finance validated';
    if (status === 'submitted') return 'Submitted';
    if (status === 'rejected') return 'Rejected';
    return 'Draft';
  }

  handoffLabel(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, char => char.toUpperCase());
  }
}
