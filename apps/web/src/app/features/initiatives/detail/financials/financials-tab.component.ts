import { Component, Input, OnInit, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

interface FinancialEntry {
  year: number;
  quarter: number | null;
  month: number | null;
  revenue_uplift_base: string;
  revenue_uplift_high: string;
  revenue_uplift_actual: string | null;
  revenue_uplift_pct_base: string;
  revenue_uplift_pct_high: string;
  revenue_uplift_pct_actual: string | null;
  gross_margin_base: string;
  gross_margin_high: string;
  gross_margin_actual: string | null;
  gm_pct_base: string;
  gm_pct_high: string;
  gm_pct_actual: string | null;
  gm_uplift_base: string;
  gm_uplift_high: string;
  gm_uplift_actual: string | null;
  gm_uplift_pct_base: string;
  gm_uplift_pct_high: string;
  gm_uplift_pct_actual: string | null;
}

interface FinancialSummary {
  revenue_uplift_plan_base: string;
  revenue_uplift_plan_high: string;
  revenue_uplift_actual: string | null;
  gross_margin_plan_base: string;
  gross_margin_plan_high: string;
  gross_margin_actual: string | null;
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

import { HotTableModule } from '@handsontable/angular-wrapper';
import { registerAllModules } from 'handsontable/registry';

// register Handsontable's modules
registerAllModules();

@Component({
  selector: 'app-financials-tab',
  standalone: true,
  imports: [CommonModule, HotTableModule],
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

      <!-- Excel-like Financial Grid -->
      @if (filteredEntries().length > 0) {
        <div class="card p-4">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold uppercase tracking-wider" style="color:var(--t-text-secondary)">
              Financial Entry Grid ({{ selectedYear() === 0 ? 'All Years' : selectedYear() }})
            </h3>
            <button (click)="saveGrid()" class="btn-primary py-1.5 px-4 text-xs">Save Changes</button>
          </div>
          
          <div class="handsontable-container overflow-hidden rounded-lg border" style="border-color:var(--t-border)">
            <hot-table
              #hot
              [data]="hotData()"
              [colHeaders]="hotColHeaders"
              [columns]="hotColumns"
              [rowHeaders]="true"
              [height]="400"
              [licenseKey]="'non-commercial-and-evaluation'"
              [stretchH]="'all'"
              [contextMenu]="true"
              [fixedColumnsLeft]="1"
              [manualColumnResize]="true"
              [manualRowResize]="true"
              (afterChange)="onHotChange($event)"
              class="hot-theme-transmuter">
            </hot-table>
          </div>
          <p class="text-[10px] mt-3" style="color:var(--t-text-secondary)">
            * Use Ctrl+C / Ctrl+V to copy-paste from Excel. All changes are saved locally until you click "Save Changes".
          </p>
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
  @ViewChild('hot', { static: false }) hotRegisterer!: any;

  private readonly api = inject(ApiService);

  loading = signal(true);
  grid = signal<FinancialGrid | null>(null);
  costLines = signal<CostLine[]>([]);
  valueBridge = signal<ValueBridge | null>(null);
  selectedYear = signal(0); // 0 = All Years
  viewMode = signal<'summary' | 'advanced'>('summary');
  readonly years = [2026, 2027, 2028, 2029, 2030];
  readonly bridgeColumns = [
    { key: 'gross_margin', label: 'Benefits' },
    { key: 'costs', label: 'Costs' },
    { key: 'net', label: 'Net' },
  ];

  hotColHeaders = [
    'Period', 
    'Rev Uplift (Base)', 'Rev Uplift (High)', 'Rev Uplift (Actual)',
    'GM Uplift (Base)', 'GM Uplift (High)', 'GM Uplift (Actual)',
    'Recurring (Plan)', 'Recurring (Actual)',
    'One-time (Plan)', 'One-time (Actual)'
  ];

  hotColumns = [
    { data: 'period', readOnly: true, className: 'htLeft font-bold' },
    { data: 'revenue_uplift_base', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'revenue_uplift_high', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'revenue_uplift_actual', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'gm_uplift_base', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'gm_uplift_high', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'gm_uplift_actual', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'costs_recurring_plan', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'costs_recurring_actual', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'costs_one_off_plan', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
    { data: 'costs_one_off_actual', type: 'numeric', numericFormat: { pattern: '$0,0.00' } },
  ];

  hotData = computed(() => {
    const entries = this.grid()?.entries || [];
    const costs = this.costLines();
    const yr = this.selectedYear();
    
    // Build 12 monthly rows + 4 quarterly rows for the selected year
    const data: any[] = [];
    const targetYear = yr === 0 ? 2026 : yr; // Default to 2026 if all years (just for the grid)

    // Helper to find entry
    const findEntry = (m: number | null, q: number | null) => 
      entries.find(e => e.year === targetYear && e.month === m && e.quarter === q);

    // Helper to sum costs for period
    const sumCosts = (m: number | null, q: number | null, recurring: boolean) => {
      return costs
        .filter(c => c.year === targetYear && c.month === m && c.quarter === q && c.is_recurring === recurring)
        .reduce((sum, c) => sum + parseFloat(c.amount_plan || '0'), 0);
    };

    // 12 Months
    for (let m = 1; m <= 12; m++) {
      const e = findEntry(m, null);
      data.push({
        period: `Month ${m}`,
        month: m,
        quarter: null,
        year: targetYear,
        revenue_uplift_base: e?.revenue_uplift_base || 0,
        revenue_uplift_high: e?.revenue_uplift_high || 0,
        revenue_uplift_actual: e?.revenue_uplift_actual || null,
        gm_uplift_base: e?.gm_uplift_base || 0,
        gm_uplift_high: e?.gm_uplift_high || 0,
        gm_uplift_actual: e?.gm_uplift_actual || null,
        costs_recurring_plan: sumCosts(m, null, true),
        costs_one_off_plan: sumCosts(m, null, false),
      });
    }

    // 4 Quarters
    for (let q = 1; q <= 4; q++) {
      const e = findEntry(null, q);
      data.push({
        period: `Quarter ${q}`,
        month: null,
        quarter: q,
        year: targetYear,
        revenue_uplift_base: e?.revenue_uplift_base || 0,
        revenue_uplift_high: e?.revenue_uplift_high || 0,
        revenue_uplift_actual: e?.revenue_uplift_actual || null,
        gm_uplift_base: e?.gm_uplift_base || 0,
        gm_uplift_high: e?.gm_uplift_high || 0,
        gm_uplift_actual: e?.gm_uplift_actual || null,
        costs_recurring_plan: sumCosts(null, q, true),
        costs_one_off_plan: sumCosts(null, q, false),
      });
    }

    return data;
  });

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
      { label: 'GM Uplift Plan', value: this.formatMoney(s.gm_uplift_plan_base), highlight: false },
      { label: 'GM Uplift Actual', value: s.gm_uplift_actual ? this.formatMoney(s.gm_uplift_actual) : '—', highlight: false },
      { label: 'Total Costs Plan', value: this.formatMoney(s.costs_plan), highlight: false },
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
    this.selectedYear.set(2026); // Default to current planning year
    if (!this.initiativeId) {
      this.loading.set(false);
      return;
    }
    this._loadData();
  }

  onHotChange(changes: any): void {
    if (!changes) return;
    // We can handle real-time calculations here if needed
  }

  saveGrid(): void {
    const hotInstance = (this.hotRegisterer as any).hotInstance;
    if (!hotInstance) return;
    
    const data = hotInstance.getSourceData();
    const entries = data.map((d: any) => ({
      year: d.year,
      quarter: d.quarter,
      month: d.month,
      revenue_uplift_base: d.revenue_uplift_base,
      revenue_uplift_high: d.revenue_uplift_high,
      revenue_uplift_actual: d.revenue_uplift_actual,
      gm_uplift_base: d.gm_uplift_base,
      gm_uplift_high: d.gm_uplift_high,
      gm_uplift_actual: d.gm_uplift_actual,
    }));

    this.loading.set(true);
    this.api.put(`/initiatives/${this.initiativeId}/financials`, { entries }).subscribe({
      next: () => this._loadData(),
      error: () => this.loading.set(false),
    });
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
