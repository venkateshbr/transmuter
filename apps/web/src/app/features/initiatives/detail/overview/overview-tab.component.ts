import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

interface FinancialSummary {
  revenue_uplift_plan_base: string;
  revenue_uplift_plan_high: string;
  revenue_uplift_actual: string | null;
  gross_margin_plan_base: string;
  gross_margin_plan_high: string;
  gross_margin_actual: string | null;
  gm_pct_plan_base: string;
  gm_pct_plan_high: string;
  gm_pct_actual: string | null;
  gm_uplift_plan_base: string;
  gm_uplift_plan_high: string;
  gm_uplift_actual: string | null;
  costs_recurring_plan: string;
  costs_recurring_actual: string | null;
  costs_one_off_plan: string;
  costs_one_off_actual: string | null;
  costs_plan: string;
  costs_actual: string | null;
  net_value_plan: string;
  net_value_actual: string | null;
  benefit_run_rate: string;
  cost_run_rate: string;
}

interface PressureBreakdown {
  schedule: string | null;
  milestone_health: string | null;
  risk_exposure: string | null;
  kpi_performance: string | null;
  financial: string | null;
  self_reported: string | null;
}

interface InitiativeCounts {
  milestones_total: number;
  milestones_complete: number;
  milestones_overdue: number;
  kpis_total: number;
  risks_open: number;
  risks_high: number;
  status_updates_total: number;
}

interface InitiativeDetail {
  id: string;
  initiative_code: string;
  name: string;
  workstream_name: string | null;
  owner_name: string | null;
  type: string | null;
  impact_type: string | null;
  priority: string;
  rag_status: string;
  stage: string;
  summary: string | null;
  value_logic: string | null;
  planned_start: string | null;
  planned_end: string | null;
  pressure_score: string | null;
  pressure_breakdown: PressureBreakdown | null;
  counts: InitiativeCounts;
  financial_summary: FinancialSummary | null;
}

@Component({
  selector: 'app-overview-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <!-- Loading State -->
      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 animate-pulse">
          <div class="card h-32 bg-[var(--t-surface-raised)]"></div>
          <div class="card h-32 bg-[var(--t-surface-raised)]"></div>
          <div class="card h-32 bg-[var(--t-surface-raised)]"></div>
        </div>
      }

      @if (!loading() && detail()) {
        <!-- TOP SECTION: Executive Summary & Context -->
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <!-- Description Card -->
          <div class="lg:col-span-2 space-y-6">
            <div class="card">
              <h3 class="text-sm font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Executive Summary
              </h3>
              <p class="text-sm leading-relaxed" style="color:var(--t-text-primary)">
                {{ detail()!.summary || 'No summary provided.' }}
              </p>
              @if (detail()!.value_logic) {
                <div class="mt-6 pt-6 border-t" style="border-color:var(--t-border)">
                  <h4 class="text-xs font-semibold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">
                    Value Logic & Assumptions
                  </h4>
                  <p class="text-sm italic" style="color:var(--t-text-secondary)">
                    "{{ detail()!.value_logic }}"
                  </p>
                </div>
              }
            </div>

            <!-- Value Metrics Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div class="card bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)]">
                <p class="text-xs font-semibold uppercase mb-1" style="color:var(--t-text-secondary)">GM Uplift</p>
                <p class="text-2xl font-bold" style="color:var(--t-text-primary)">{{ formatCurrency(detail()!.financial_summary?.gm_uplift_plan_base) }}</p>
                <p class="text-[10px] mt-1" style="color:var(--t-text-secondary)">Planned (Base Case)</p>
              </div>
              <div class="card bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)]">
                <p class="text-xs font-semibold uppercase mb-1" style="color:var(--t-text-secondary)">Net Value</p>
                <p class="text-2xl font-bold" style="color:var(--t-accent)">{{ formatCurrency(detail()!.financial_summary?.net_value_plan) }}</p>
                <p class="text-[10px] mt-1" style="color:var(--t-text-secondary)">GM Uplift - Recurring Costs</p>
              </div>
              <div class="card bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-surface-raised)]">
                <p class="text-xs font-semibold uppercase mb-1" style="color:var(--t-text-secondary)">Revenue Uplift</p>
                <p class="text-2xl font-bold" style="color:var(--t-text-primary)">{{ formatCurrency(detail()!.financial_summary?.revenue_uplift_plan_base) }}</p>
                <p class="text-[10px] mt-1" style="color:var(--t-text-secondary)">Planned (Base Case)</p>
              </div>
            </div>
          </div>

          <!-- SIDEBAR: Timeline & Pressure -->
          <div class="space-y-6">
            <!-- Timeline Card -->
            <div class="card">
              <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Timeline
              </h3>
              <div class="space-y-4">
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Start</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.planned_start || '—' }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span style="color:var(--t-text-secondary)">Completion</span>
                  <span class="font-medium" style="color:var(--t-text-primary)">{{ detail()!.planned_end || '—' }}</span>
                </div>
                <!-- Progress Bar -->
                <div class="pt-2">
                  <div class="flex justify-between text-[10px] mb-1">
                    <span style="color:var(--t-text-secondary)">Overall Progress</span>
                    <span class="font-bold" style="color:var(--t-accent)">{{ progressPct() }}%</span>
                  </div>
                  <div class="h-2 rounded-full" style="background:var(--t-surface-raised)">
                    <div class="h-full rounded-full transition-all duration-500"
                         [style.width]="progressPct() + '%'"
                         style="background:var(--t-accent-gradient)"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Pressure Card -->
            <div class="card">
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-xs font-semibold uppercase tracking-wider" style="color:var(--t-text-secondary)">
                  Value Pressure
                </h3>
                <span class="text-xl font-bold" [style.color]="pressureColor(detail()!.pressure_score)">
                  {{ detail()!.pressure_score || '0.0' }}
                </span>
              </div>
              <div class="space-y-3">
                @for (p of pressureGauges(); track p.label) {
                  <div>
                    <div class="flex justify-between text-[10px] mb-1">
                      <span style="color:var(--t-text-secondary)">{{ p.label }}</span>
                      <span class="font-mono" style="color:var(--t-text-primary)">{{ p.value }}/10</span>
                    </div>
                    <div class="h-1 rounded-full overflow-hidden" style="background:var(--t-surface-raised)">
                      <div class="h-full rounded-full transition-all duration-500"
                           [style.width]="(p.value * 10) + '%'"
                           [style.background]="pressureColor(p.value)"></div>
                    </div>
                  </div>
                }
              </div>
            </div>

            <!-- Team Quick View -->
            <div class="card">
               <h3 class="text-xs font-semibold uppercase tracking-wider mb-4" style="color:var(--t-text-secondary)">
                Lead Team
              </h3>
              <div class="space-y-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] font-bold text-xs">
                    {{ getInitials(detail()!.owner_name) }}
                  </div>
                  <div>
                    <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ detail()!.owner_name || 'Unassigned' }}</p>
                    <p class="text-[10px]" style="color:var(--t-text-secondary)">Market Owner</p>
                  </div>
                </div>
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-secondary)] font-bold text-xs">
                    {{ getInitials(detail()!.workstream_name) }}
                  </div>
                  <div>
                    <p class="text-xs font-bold" style="color:var(--t-text-primary)">{{ detail()!.workstream_name || 'N/A' }}</p>
                    <p class="text-[10px]" style="color:var(--t-text-secondary)">Workstream</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .card {
      @apply rounded-xl border p-5 shadow-sm bg-[var(--t-surface)] transition-all duration-200;
      border-color: var(--t-border);
    }
  `]
})
export class OverviewTabComponent implements OnInit {
  @Input() initiativeId = '';

  private readonly api = inject(ApiService);

  loading = signal(true);
  detail = signal<InitiativeDetail | null>(null);

  pressureGauges = computed(() => {
    const b = this.detail()?.pressure_breakdown;
    if (!b) return [];
    return [
      { label: 'Schedule', value: parseFloat(b.schedule || '0') },
      { label: 'Milestones', value: parseFloat(b.milestone_health || '0') },
      { label: 'Financials', value: parseFloat(b.financial || '0') },
      { label: 'Risks', value: parseFloat(b.risk_exposure || '0') },
    ];
  });

  progressPct = computed(() => {
    const c = this.detail()?.counts;
    if (!c || c.milestones_total === 0) return 0;
    return Math.round((c.milestones_complete / c.milestones_total) * 100);
  });

  ngOnInit(): void {
    if (!this.initiativeId) return;
    this.loadDetail();
  }

  private loadDetail(): void {
    this.loading.set(true);
    this.api.get<InitiativeDetail>(`/initiatives/${this.initiativeId}`).subscribe({
      next: (d) => {
        this.detail.set(d);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  formatCurrency(val: string | null | undefined): string {
    if (!val) return '$0';
    const n = parseFloat(val);
    if (isNaN(n)) return '$0';
    if (n >= 1000000) return `$${(n / 1000000).toFixed(1)}M`;
    if (n >= 1000) return `$${(n / 1000).toFixed(0)}K`;
    return `$${n.toLocaleString()}`;
  }

  pressureColor(score: string | number | null | undefined): string {
    if (!score) return 'var(--t-text-secondary)';
    const n = typeof score === 'string' ? parseFloat(score) : score;
    if (n >= 7) return 'var(--t-red)';
    if (n >= 4) return 'var(--t-amber)';
    return 'var(--t-green)';
  }

  getInitials(name: string | null | undefined): string {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
  }
}
