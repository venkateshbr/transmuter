import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

interface FinancialEntry {
  year: number;
  quarter: number | null;
  revenue_uplift_base: string;
  revenue_uplift_high: string;
  revenue_uplift_actual: string | null;
  gross_margin_base: string;
  gross_margin_high: string;
  gross_margin_actual: string | null;
  gm_pct_base: string;
  gm_pct_high: string;
  gm_pct_actual: string | null;
}

interface FinancialSummary {
  gross_margin_plan_base: string;
  gross_margin_plan_high: string;
  gross_margin_actual: string | null;
  costs_plan: string;
  costs_actual: string | null;
  net_value_plan: string;
  net_value_actual: string | null;
}

interface FinancialGrid {
  initiative_id: string;
  entries: FinancialEntry[];
  summary: FinancialSummary;
}

interface CostLine {
  id: string;
  initiative_id: string;
  name: string;
  year: number;
  quarter: number | null;
  amount_plan: string;
  amount_actual: string | null;
  is_recurring: boolean;
}

interface ValueBridgeCase {
  revenue_uplift: string;
  gross_margin: string;
  costs: string;
  net: string;
}

interface ValueBridge {
  initiative_id: string | null;
  base_case: ValueBridgeCase;
  high_case: ValueBridgeCase;
  actual: ValueBridgeCase;
}

interface CostLineListResponse {
  items: CostLine[];
  total: number;
}

@Component({
  selector: 'app-financials-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <!-- Year toggle -->
      <div class="flex items-center gap-2 flex-wrap">
        @for (y of years; track y) {
          <button
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            [style.background]="selectedYear() === y ? 'var(--t-accent)' : 'var(--t-surface-raised)'"
            [style.color]="selectedYear() === y ? '#fff' : 'var(--t-text-secondary)'"
            [style.border]="'1px solid ' + (selectedYear() === y ? 'var(--t-accent)' : 'var(--t-border)')"
            (click)="selectedYear.set(y)"
            [attr.aria-label]="'Select year ' + (y === 0 ? 'All Years' : y)">
            {{ y === 0 ? 'All Years' : y }}
          </button>
        }
        <div class="ml-auto flex items-center gap-2">
          <button
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            [style.background]="viewMode() === 'summary' ? 'var(--t-accent-soft)' : 'transparent'"
            [style.color]="viewMode() === 'summary' ? 'var(--t-accent)' : 'var(--t-text-secondary)'"
            (click)="viewMode.set('summary')"
            aria-label="Summary view">Summary</button>
          <button
            class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
            [style.background]="viewMode() === 'advanced' ? 'var(--t-accent-soft)' : 'transparent'"
            [style.color]="viewMode() === 'advanced' ? 'var(--t-accent)' : 'var(--t-text-secondary)'"
            (click)="viewMode.set('advanced')"
            aria-label="Advanced view">Advanced</button>
        </div>
      </div>

      <!-- Summary cards -->
      @if (grid()) {
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          @for (card of summaryCards(); track card.label) {
            <div class="card p-4">
              <p class="text-xs font-medium mb-1"
                 style="color:var(--t-text-secondary)">{{ card.label }}</p>
              <p class="text-lg font-bold"
                 [style.color]="card.highlight ? 'var(--t-accent)' : 'var(--t-text-primary)'">
                {{ card.value }}
              </p>
            </div>
          }
        </div>
      }

      <!-- Quarterly grid table -->
      @if (filteredEntries().length > 0) {
        <div class="card p-0 overflow-x-auto">
          <table class="w-full text-sm" style="border-collapse:collapse">
            <thead>
              <tr style="border-bottom:1px solid var(--t-border)">
                <th class="text-left px-4 py-3 text-[10px] font-semibold uppercase"
                    style="color:var(--t-text-secondary)">Metric</th>
                @for (q of [1,2,3,4]; track q) {
                  <th class="text-right px-4 py-3 text-[10px] font-semibold uppercase"
                      style="color:var(--t-text-secondary)">Q{{ q }}</th>
                }
                <th class="text-right px-4 py-3 text-[10px] font-semibold uppercase"
                    style="color:var(--t-accent)">Full Year</th>
              </tr>
            </thead>
            <tbody>
              <!-- Revenue Uplift section -->
              <tr style="background:var(--t-surface-raised)">
                <td colspan="6" class="px-4 py-2 text-xs font-semibold uppercase"
                    style="color:var(--t-text-secondary)">Revenue Uplift</td>
              </tr>
              @for (row of revenueRows(); track row.label) {
                <tr style="border-bottom:1px solid var(--t-border)"
                    class="hover:bg-[var(--t-surface-raised)] transition-colors">
                  <td class="px-4 py-2.5 text-sm" style="color:var(--t-text-secondary)">{{ row.label }}</td>
                  @for (val of row.values; track $index) {
                    <td class="text-right px-4 py-2.5 font-mono text-sm"
                        [style.color]="val === '—' ? 'var(--t-text-secondary)' : 'var(--t-text-primary)'">
                      {{ val }}
                    </td>
                  }
                </tr>
              }
              <!-- Gross Margin section -->
              <tr style="background:var(--t-surface-raised)">
                <td colspan="6" class="px-4 py-2 text-xs font-semibold uppercase"
                    style="color:var(--t-text-secondary)">Gross Margin</td>
              </tr>
              @for (row of marginRows(); track row.label) {
                <tr style="border-bottom:1px solid var(--t-border)"
                    class="hover:bg-[var(--t-surface-raised)] transition-colors">
                  <td class="px-4 py-2.5 text-sm" style="color:var(--t-text-secondary)">{{ row.label }}</td>
                  @for (val of row.values; track $index) {
                    <td class="text-right px-4 py-2.5 font-mono text-sm"
                        [style.color]="val === '—' ? 'var(--t-text-secondary)' : 'var(--t-text-primary)'">
                      {{ val }}
                    </td>
                  }
                </tr>
              }
              <!-- Costs section -->
              @if (costLines().length > 0) {
                <tr style="background:var(--t-surface-raised)">
                  <td colspan="6" class="px-4 py-2 text-xs font-semibold uppercase"
                      style="color:var(--t-text-secondary)">Costs</td>
                </tr>
                @for (cl of costLines(); track cl.id) {
                  <tr style="border-bottom:1px solid var(--t-border)"
                      class="hover:bg-[var(--t-surface-raised)] transition-colors">
                    <td class="px-4 py-2.5 text-sm" style="color:var(--t-text-secondary)">
                      {{ cl.name }}
                      @if (cl.is_recurring) {
                        <span class="badge-purple ml-1">Recurring</span>
                      }
                    </td>
                    <td class="text-right px-4 py-2.5 font-mono text-sm"
                        colspan="4" style="color:var(--t-text-primary)">
                      {{ formatMoney(cl.amount_plan) }}
                    </td>
                    <td class="text-right px-4 py-2.5 font-mono text-sm"
                        style="color:var(--t-text-primary)">
                      {{ cl.amount_actual ? formatMoney(cl.amount_actual) : '—' }}
                    </td>
                  </tr>
                }
              }
            </tbody>
          </table>
        </div>
      }

      <!-- Value Bridge -->
      @if (valueBridge()) {
        <div class="card">
          <h3 class="text-base font-semibold mb-4"
              style="color:var(--t-text-primary)">
            Value Bridge<span style="color:var(--t-accent)">.</span>
          </h3>
          <div class="grid grid-cols-3 gap-4 text-center">
            @for (col of bridgeColumns; track col.key) {
              <div>
                <p class="text-[10px] font-semibold uppercase mb-3"
                   style="color:var(--t-text-secondary)">{{ col.label }}</p>
                @for (row of bridgeRows(); track row.label) {
                  <div class="py-2" style="border-bottom:1px solid var(--t-border)">
                    <p class="text-[10px] uppercase mb-1"
                       style="color:var(--t-text-secondary)">{{ row.label }}</p>
                    <p class="text-sm font-semibold font-mono"
                       [style.color]="col.key === 'net' ? 'var(--t-accent)' : 'var(--t-text-primary)'">
                      {{ row.values[col.key] }}
                    </p>
                  </div>
                }
              </div>
            }
          </div>
          <div class="flex items-center gap-4 mt-4 pt-3"
               style="border-top:1px solid var(--t-border)">
            <span class="flex items-center gap-1.5 text-xs" style="color:var(--t-text-secondary)">
              <span class="w-2.5 h-2.5 rounded-full" style="background:var(--t-accent)"></span> Base
            </span>
            <span class="flex items-center gap-1.5 text-xs" style="color:var(--t-text-secondary)">
              <span class="w-2.5 h-2.5 rounded-full" style="background:var(--t-accent-hover)"></span> High
            </span>
            <span class="flex items-center gap-1.5 text-xs" style="color:var(--t-text-secondary)">
              <span class="w-2.5 h-2.5 rounded-full" style="background:var(--t-green)"></span> Actual
            </span>
          </div>
        </div>
      }

      <!-- Empty state -->
      @if (!loading() && filteredEntries().length === 0 && !grid()) {
        <div class="card text-center py-12">
          <p class="text-lg font-semibold" style="color:var(--t-text-primary)">
            No financial data yet<span style="color:var(--t-accent)">.</span>
          </p>
          <p class="text-sm mt-2" style="color:var(--t-text-secondary)">
            Financial entries will appear here once added.
          </p>
        </div>
      }

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="space-y-4">
          <div class="grid grid-cols-4 gap-4">
            @for (i of [1,2,3,4]; track i) {
              <div class="card p-4 animate-pulse">
                <div class="h-3 rounded w-20 mb-2" style="background:var(--t-border)"></div>
                <div class="h-6 rounded w-16" style="background:var(--t-border)"></div>
              </div>
            }
          </div>
          <div class="card p-4 animate-pulse">
            <div class="h-4 rounded w-40 mb-4" style="background:var(--t-border)"></div>
            @for (i of [1,2,3,4,5]; track i) {
              <div class="h-8 rounded w-full mb-2" style="background:var(--t-border)"></div>
            }
          </div>
        </div>
      }
    </div>
  `,
})
export class FinancialsTabComponent implements OnInit {
  @Input() initiativeId = '';

  private readonly api = inject(ApiService);

  loading = signal(true);
  grid = signal<FinancialGrid | null>(null);
  costLines = signal<CostLine[]>([]);
  valueBridge = signal<ValueBridge | null>(null);
  selectedYear = signal(0); // 0 = All Years
  viewMode = signal<'summary' | 'advanced'>('summary');

  readonly years = [0, 2026, 2027, 2028, 2029, 2030];
  readonly bridgeColumns = [
    { key: 'gross_margin', label: 'Benefits' },
    { key: 'costs', label: 'Costs' },
    { key: 'net', label: 'Net' },
  ];

  filteredEntries = computed(() => {
    const g = this.grid();
    if (!g) return [];
    const yr = this.selectedYear();
    if (yr === 0) return g.entries;
    return g.entries.filter(e => e.year === yr);
  });

  summaryCards = computed(() => {
    const s = this.grid()?.summary;
    if (!s) return [];
    return [
      { label: 'Gross Margin Plan', value: this.formatMoney(s.gross_margin_plan_base), highlight: false },
      { label: 'Gross Margin Actual', value: s.gross_margin_actual ? this.formatMoney(s.gross_margin_actual) : '—', highlight: false },
      { label: 'Costs Plan', value: this.formatMoney(s.costs_plan), highlight: false },
      { label: 'Net Value (Plan)', value: this.formatMoney(s.net_value_plan), highlight: true },
    ];
  });

  revenueRows = computed(() => this._buildMetricRows('revenue_uplift'));
  marginRows = computed(() => this._buildMetricRows('gross_margin'));

  bridgeRows = computed((): { label: string; values: Record<string, string> }[] => {
    const vb = this.valueBridge();
    if (!vb) return [];
    return [
      {
        label: 'Base Case',
        values: {
          gross_margin: this.formatMoney(vb.base_case.gross_margin),
          costs: this.formatMoney(vb.base_case.costs),
          net: this.formatMoney(vb.base_case.net),
        },
      },
      {
        label: 'High Case',
        values: {
          gross_margin: this.formatMoney(vb.high_case.gross_margin),
          costs: this.formatMoney(vb.high_case.costs),
          net: this.formatMoney(vb.high_case.net),
        },
      },
      {
        label: 'Actual',
        values: {
          gross_margin: this.formatMoney(vb.actual.gross_margin),
          costs: this.formatMoney(vb.actual.costs),
          net: this.formatMoney(vb.actual.net),
        },
      },
    ];
  });

  ngOnInit(): void {
    if (!this.initiativeId) {
      this.loading.set(false);
      return;
    }
    this._loadData();
  }

  formatMoney(val: string | null): string {
    if (!val || val === '0' || val === '0.0000') return '$0';
    const n = parseFloat(val);
    if (isNaN(n)) return '$0';
    if (Math.abs(n) >= 1_000_000) {
      return `$${(n / 1_000_000).toFixed(2)}m`;
    }
    if (Math.abs(n) >= 1_000) {
      return `$${(n / 1_000).toFixed(1)}k`;
    }
    return `$${n.toFixed(2)}`;
  }

  private _loadData(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;

    this.fetchGrid(base);
    this.fetchCostLines(base);
    this.fetchValueBridge(base);
  }

  private fetchGrid(base: string): void {
    this.api.get<FinancialGrid>(base).subscribe({
      next: (g: FinancialGrid) => this.grid.set(g),
      error: () => this.grid.set(null),
    });
  }

  private fetchCostLines(base: string): void {
    this.api.get<CostLineListResponse>(`${base}/cost-lines`).subscribe({
      next: (r: CostLineListResponse) => this.costLines.set(r.items),
      error: () => this.costLines.set([]),
    });
  }

  private fetchValueBridge(base: string): void {
    this.api.get<ValueBridge>(`${base}/value-bridge`).subscribe({
      next: (vb: ValueBridge) => {
        this.valueBridge.set(vb);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  private _buildMetricRows(prefix: string): { label: string; values: string[] }[] {
    const entries = this.filteredEntries();
    const qEntries = [1, 2, 3, 4].map(
      q => entries.find(e => e.quarter === q)
    );
    const baseKey = `${prefix}_base` as keyof FinancialEntry;
    const highKey = `${prefix}_high` as keyof FinancialEntry;
    const actualKey = `${prefix}_actual` as keyof FinancialEntry;

    const sumQ = (key: keyof FinancialEntry): string => {
      const total = qEntries.reduce((acc, e) => {
        const v = e ? e[key] : null;
        return acc + (v ? parseFloat(v as string) : 0);
      }, 0);
      return this.formatMoney(total.toString());
    };

    const qVals = (key: keyof FinancialEntry): string[] => {
      const qs = qEntries.map(e => {
        const v = e ? e[key] : null;
        return v ? this.formatMoney(v as string) : '—';
      });
      qs.push(sumQ(key));
      return qs;
    };

    const rows = [
      { label: 'Planned (Base)', values: qVals(baseKey) },
      { label: 'Planned (High)', values: qVals(highKey) },
      { label: 'Actual', values: qVals(actualKey) },
    ];

    if (this.viewMode() === 'summary') {
      return [rows[0], rows[2]]; // Base + Actual only
    }
    return rows;
  }
}
