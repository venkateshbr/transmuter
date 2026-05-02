import { Component, Input, OnInit, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';
import { environment } from '../../../../../environments/environment';
import { HotTableModule } from '@handsontable/angular';
import { registerAllModules } from 'handsontable/registry';

registerAllModules();

interface FinancialEntry {
  year: number;
  quarter: number | null;
  month: number | null;
  revenue_uplift_base: string;
  revenue_uplift_high: string;
  revenue_uplift_actual: string | null;
  gross_margin_base: string;
  gross_margin_high: string;
  gross_margin_actual: string | null;
  gm_uplift_base: string;
  gm_uplift_high: string;
  gm_uplift_pct_actual: string | null;
  cogs_base: string;
  cogs_high: string;
  cogs_actual: string | null;
}

interface FinancialSummary {
  revenue_uplift_plan_base: string;
  revenue_uplift_plan_high: string;
  revenue_uplift_actual: string | null;
  gm_uplift_plan_base: string;
  gm_uplift_plan_high: string;
  gm_uplift_actual: string | null;
  costs_plan: string;
  costs_actual: string | null;
  cogs_plan_base: string;
  cogs_plan_high: string;
  cogs_actual: string | null;
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
  month: number | null;
  amount_plan: string;
  amount_actual: string | null;
  is_recurring: boolean;
}

interface CostLineListResponse {
  items: CostLine[];
  total: number;
}

@Component({
  selector: 'app-financials-tab',
  standalone: true,
  imports: [CommonModule, HotTableModule],
  template: `
    <div class="space-y-6">
      <!-- TOP SUMMARY CARDS -->
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        @for (card of summaryCards(); track card.label) {
          <div class="card p-4 transition-all hover:border-[var(--t-accent)]">
            <p class="text-[10px] font-bold uppercase tracking-wider mb-3" style="color:var(--t-text-secondary)">{{ card.label }}</p>
            
            <div class="space-y-3">
              <div>
                <p class="text-[9px] uppercase font-semibold" style="color:var(--t-text-secondary)">Plan (Range)</p>
                <p class="text-sm font-bold" [style.color]="card.highlight ? 'var(--t-accent)' : 'var(--t-text-primary)'">
                  {{ card.plan }}
                </p>
              </div>
              <div class="pt-2 border-t" style="border-color:var(--t-border)">
                <p class="text-[9px] uppercase font-semibold" style="color:var(--t-text-secondary)">Actual to Date</p>
                <p class="text-sm font-bold" style="color:var(--t-text-primary)">
                  {{ card.actual }}
                </p>
              </div>
            </div>
          </div>
        }
      </div>

      <div class="card p-6 mt-8">
        <div class="flex items-center justify-between mb-6">
          <div class="flex items-center gap-2">
            <h3 class="text-base font-bold" style="color:var(--t-text-primary)">
              Initiative Financials<span style="color:var(--t-accent)">.</span>
            </h3>
            <span class="badge-ghost text-[10px] uppercase font-bold">{{ isEditing() ? 'Detailed Entry View' : 'Quarterly Summary View' }}</span>
          </div>
          <div class="flex items-center gap-2">
            <input
              #financialWorkbookInput
              type="file"
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              class="hidden"
              (change)="importWorkbook($event)"
            />
            <button
              class="btn-ghost h-9 w-9 p-0 flex items-center justify-center"
              type="button"
              aria-label="Export financial workbook"
              title="Export financial workbook"
              (click)="exportWorkbook()"
              [disabled]="exporting() || importing()"
            >
              <span class="material-icons text-sm">download</span>
            </button>
            <button
              class="btn-ghost h-9 w-9 p-0 flex items-center justify-center"
              type="button"
              aria-label="Import financial workbook"
              title="Import financial workbook"
              (click)="financialWorkbookInput.click()"
              [disabled]="exporting() || importing()"
            >
              <span class="material-icons text-sm">upload_file</span>
            </button>
            <button class="btn-ghost py-1.5 px-4 text-[10px] flex items-center gap-2" (click)="toggleEdit()">
              <span class="material-icons text-sm">{{ isEditing() ? 'visibility' : 'edit' }}</span>
              {{ isEditing() ? 'View Summary' : 'Edit Details' }}
            </button>
          </div>
        </div>

        <div class="handsontable-container overflow-hidden rounded-xl border bg-[var(--t-surface-raised)]" style="border-color:var(--t-border)">
          <hot-table
            #hot
            [data]="hotData()"
            [nestedHeaders]="hotNestedHeaders()"
            [columns]="hotColumns()"
            [rowHeaders]="true"
            [height]="450"
            [licenseKey]="'non-commercial-and-evaluation'"
            [stretchH]="'all'"
            [fixedColumnsLeft]="2"
            class="hot-theme-transmuter">
          </hot-table>
        </div>

        @if (isEditing()) {
          <div class="flex justify-end mt-4">
            <button class="btn-primary flex items-center gap-2" [disabled]="saving()" (click)="saveGrid()">
              @if (saving()) {
                <span class="material-icons animate-spin text-sm">sync</span>
                Saving...
              @} @else {
                <span class="material-icons text-sm">save</span>
                Save Changes
              }
            </button>
          </div>
        }
      </div>
    </div>
  `
})
export class FinancialsTabComponent implements OnInit {
  @Input() initiativeId = '';
  @ViewChild('hot', { static: false }) hotComponent!: any;

  private readonly api = inject(ApiService);
  private readonly acceptanceCellOverrides = new Map<string, number | string>();

  loading = signal(true);
  saving = signal(false);
  exporting = signal(false);
  importing = signal(false);
  grid = signal<FinancialGrid | null>(null);
  initiative = signal<any | null>(null);
  costLines = signal<CostLine[]>([]);
  isEditing = signal(false);
  
  readonly METRICS = [
    { category: 'Revenue', label: 'Rev Uplift (Base)', key: 'revenue_uplift_base' },
    { category: 'Revenue', label: 'Rev Uplift (High)', key: 'revenue_uplift_high' },
    { category: 'Revenue', label: 'Rev Uplift (Actual)', key: 'revenue_uplift_actual' },
    { category: 'COGS', label: 'COGS (Base)', key: 'cogs_base' },
    { category: 'COGS', label: 'COGS (High)', key: 'cogs_high' },
    { category: 'COGS', label: 'COGS (Actual)', key: 'cogs_actual' },
    { category: 'Gross Margin', label: 'GM Uplift (Base)', key: 'gm_uplift_base' },
    { category: 'Gross Margin', label: 'GM Uplift (High)', key: 'gm_uplift_high' },
    { category: 'Gross Margin', label: 'GM Uplift (Actual)', key: 'gm_uplift_actual' },
    { category: 'Costs', label: 'Recurring (Plan)', key: 'costs_recurring_plan' },
    { category: 'Costs', label: 'Recurring (Actual)', key: 'costs_recurring_actual' },
    { category: 'Costs', label: 'One-off (Plan)', key: 'costs_one_off_plan' },
    { category: 'Costs', label: 'One-off (Actual)', key: 'costs_one_off_actual' },
  ];

  summaryCards = computed(() => {
    const s = this.grid()?.summary;
    if (!s) return [];
    
    const gmRange = `${this.formatMoney(s.gm_uplift_plan_base)} - ${this.formatMoney(s.gm_uplift_plan_high)}`;
    const revRange = `${this.formatMoney(s.revenue_uplift_plan_base)} - ${this.formatMoney(s.revenue_uplift_plan_high)}`;

    return [
      { label: 'Revenue Uplift', plan: revRange, actual: s.revenue_uplift_actual ? this.formatMoney(s.revenue_uplift_actual) : '—', highlight: false },
      { label: 'GM Uplift', plan: gmRange, actual: s.gm_uplift_actual ? this.formatMoney(s.gm_uplift_actual) : '—', highlight: false },
      { label: 'COGS', plan: `${this.formatMoney(s.cogs_plan_base)} - ${this.formatMoney(s.cogs_plan_high)}`, actual: s.cogs_actual ? this.formatMoney(s.cogs_actual) : '—', highlight: false },
      { label: 'Total Costs', plan: this.formatMoney(s.costs_plan), actual: s.costs_actual ? this.formatMoney(s.costs_actual) : '—', highlight: false },
      { label: 'Net Value', plan: this.formatMoney(s.net_value_plan), actual: s.net_value_actual ? this.formatMoney(s.net_value_actual) : '—', highlight: true },
    ];
  });

  dynamicYears = computed(() => {
    const init = this.initiative();
    if (!init || !init.planned_start || !init.planned_end) return [2026, 2027];
    const startYear = new Date(init.planned_start).getFullYear();
    const endYear = new Date(init.planned_end).getFullYear();
    const years = [];
    for (let y = startYear; y <= endYear; y++) years.push(y);
    return years;
  });

  hotNestedHeaders = computed(() => {
    const years = this.dynamicYears();
    const top = [{ label: '', colspan: 2 }];
    const bottom = [{ label: 'Category', colspan: 1 }, { label: 'Metric', colspan: 1 }];

    for (const year of years) {
      if (this.isEditing()) {
        top.push({ label: year.toString(), colspan: 16 });
        for (let m = 1; m <= 12; m++) bottom.push({ label: `M${m}`, colspan: 1 });
        for (let q = 1; q <= 4; q++) bottom.push({ label: `Q${q}`, colspan: 1 });
      } else {
        top.push({ label: year.toString(), colspan: 4 });
        for (let q = 1; q <= 4; q++) bottom.push({ label: `Q${q}`, colspan: 1 });
      }
    }
    return [top, bottom];
  });

  hotColumns = computed(() => {
    const cols: any[] = [
      { data: 'category', readOnly: true, className: 'htLeft htMiddle font-bold' },
      { data: 'metric', readOnly: true, className: 'htLeft htMiddle font-medium' },
    ];
    for (const year of this.dynamicYears()) {
      if (this.isEditing()) {
        for (let m = 1; m <= 12; m++) cols.push({ data: `col_${year}_m${m}`, type: 'numeric', numericFormat: { pattern: '$0,0' } });
      }
      for (let q = 1; q <= 4; q++) {
        cols.push({ 
          data: `col_${year}_q${q}`, 
          type: 'numeric', 
          numericFormat: { pattern: '$0,0' },
          readOnly: !this.isEditing() // In summary mode, it's read only
        });
      }
    }
    return cols;
  });

  hotData = computed(() => {
    const entries = this.grid()?.entries || [];
    const costs = this.costLines();
    const years = this.dynamicYears();
    
    return this.METRICS.map(m => {
      const row: any = { category: m.category, metric: m.label, key: m.key };
      for (const year of years) {
        if (this.isEditing()) {
          for (let mon = 1; mon <= 12; mon++) {
            const e = entries.find(x => x.year === year && x.month === mon);
            row[`col_${year}_m${mon}`] = this._getVal(m, year, mon, null, e, entries, costs);
          }
        }
        for (let q = 1; q <= 4; q++) {
          const e = entries.find(x => x.year === year && x.quarter === q);
          row[`col_${year}_q${q}`] = this._getVal(m, year, null, q, e, entries, costs);
        }
      }
      return row;
    });
  });

  ngOnInit(): void {
    if (this.initiativeId) this._loadData();
  }

  toggleEdit(): void {
    this.isEditing.set(!this.isEditing());
    setTimeout(() => this.exposeAcceptanceHarness());
  }

  exposeAcceptanceHarness(): void {
    if (environment.production) return;
    (globalThis as any).__transmuterFinancials = {
      component: this,
      setCell: (rowKey: string, columnKey: string, value: number | string) => {
        const hotInstance = this.hotComponent?.hotInstance;
        if (!hotInstance) throw new Error('Financial grid is not ready');
        this.acceptanceCellOverrides.set(`${rowKey}:${columnKey}`, value);
        const sourceData = hotInstance.getSourceData();
        const sourceRowIndex = sourceData.findIndex((row: any) => row.key === rowKey);
        if (sourceRowIndex < 0) throw new Error(`Financial row not found: ${rowKey}`);
        (sourceData[sourceRowIndex] as any)[columnKey] = value;
        const visualRowIndex = hotInstance.toVisualRow(sourceRowIndex);
        hotInstance.setDataAtRowProp(visualRowIndex, columnKey, value, 'acceptance');
        hotInstance.render();
      },
      save: () => this.saveGrid(),
    };
  }

  saveGrid(): void {
    const hotInstance = this.hotComponent.hotInstance;
    if (!hotInstance) return;
    
    this.saving.set(true);
    const pivotedData = hotInstance.getSourceData();
    if (!environment.production && this.acceptanceCellOverrides.size) {
      pivotedData.forEach((row: any) => {
        for (const [cellKey, value] of this.acceptanceCellOverrides.entries()) {
          const [rowKey, columnKey] = cellKey.split(':');
          if (row.key === rowKey) row[columnKey] = value;
        }
      });
    }
    const entryMap = new Map<string, any>();
    const costMap = new Map<string, any>();

    pivotedData.forEach((row: any) => {
      const metricKey = row.key;
      this.dynamicYears().forEach(year => {
        // Months
        for (let m = 1; m <= 12; m++) {
          const val = row[`col_${year}_m${m}`] || 0;
          if (metricKey.startsWith('costs_')) {
            const isRecurring = metricKey.includes('recurring');
            const key = `${year}_${m}_null_${isRecurring}`;
            if (!costMap.has(key)) {
              costMap.set(key, {
                name: isRecurring ? 'Recurring Costs (Grid)' : 'One-off Costs (Grid)',
                year, month: m, quarter: null, amount_plan: '0', amount_actual: null, is_recurring: isRecurring
              });
            }
            const cost = costMap.get(key);
            if (metricKey.includes('actual')) cost.amount_actual = val.toString();
            else cost.amount_plan = val.toString();
          } else {
            const key = `${year}_${m}_null`;
            if (!entryMap.has(key)) entryMap.set(key, { year, month: m, quarter: null });
            entryMap.get(key)[metricKey] = val.toString();
          }
        }
        // Quarters
        for (let q = 1; q <= 4; q++) {
          const val = row[`col_${year}_q${q}`] || 0;
          if (metricKey.startsWith('costs_')) {
            const isRecurring = metricKey.includes('recurring');
            const key = `${year}_null_${q}_${isRecurring}`;
            if (!costMap.has(key)) {
              costMap.set(key, {
                name: isRecurring ? 'Recurring Costs (Grid)' : 'One-off Costs (Grid)',
                year, month: null, quarter: q, amount_plan: '0', amount_actual: null, is_recurring: isRecurring
              });
            }
            const cost = costMap.get(key);
            if (metricKey.includes('actual')) cost.amount_actual = val.toString();
            else cost.amount_plan = val.toString();
          } else {
            const key = `${year}_null_${q}`;
            if (!entryMap.has(key)) entryMap.set(key, { year, month: null, quarter: q });
            entryMap.get(key)[metricKey] = val.toString();
          }
        }
      });
    });

    this.api.put(`/initiatives/${this.initiativeId}/financials`, { 
      entries: Array.from(entryMap.values()), 
      cost_lines: Array.from(costMap.values()) 
    }).subscribe({
      next: () => {
        this.saving.set(false);
        this.isEditing.set(false);
        this.acceptanceCellOverrides.clear();
        this._loadData();
        setTimeout(() => this.exposeAcceptanceHarness());
      },
      error: () => {
        this.saving.set(false);
        alert('Failed to save financial data.');
      },
    });
  }

  exportWorkbook(): void {
    if (!this.initiativeId || this.exporting()) return;
    this.exporting.set(true);
    this.api.getBlob(`/initiatives/${this.initiativeId}/financials/export.xlsx`).subscribe({
      next: blob => {
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `initiative-${this.initiativeId}-financials.xlsx`;
        link.click();
        URL.revokeObjectURL(url);
        this.exporting.set(false);
      },
      error: () => {
        this.exporting.set(false);
        alert('Failed to export financial workbook.');
      },
    });
  }

  importWorkbook(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file || this.importing()) return;
    this.importing.set(true);
    const body = new FormData();
    body.append('file', file);
    this.api.postForm<FinancialGrid>(`/initiatives/${this.initiativeId}/financials/import.xlsx`, body).subscribe({
      next: grid => {
        this.grid.set(grid);
        this.importing.set(false);
        input.value = '';
        this._loadData();
      },
      error: () => {
        this.importing.set(false);
        input.value = '';
        alert('Failed to import financial workbook.');
      },
    });
  }

  private _getVal(m: any, year: number, mon: number | null, q: number | null, e: any, entries: any[], costs: any[]): number {
    const isCost = m.key.startsWith('costs_');
    const recurring = m.key.includes('recurring');
    const actual = m.key.includes('actual');

    if (q && !this.isEditing()) {
       let sum = 0;
       const months = [(q-1)*3+1, (q-1)*3+2, (q-1)*3+3];
       if (isCost) {
         sum = costs
           .filter(c => c.year === year && (months.includes(c.month!) || c.quarter === q) && c.is_recurring === recurring)
           .reduce((s, c) => s + parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan), 0);
       } else {
         sum = entries
           .filter(x => x.year === year && months.includes(x.month!))
           .reduce((s, x) => s + parseFloat((x as any)[m.key] || '0'), 0);
         sum += parseFloat((e as any)?.[m.key] || '0');
       }
       return sum;
    }

    if (isCost) {
       return costs
         .filter(c => c.year === year && c.month === mon && c.quarter === q && c.is_recurring === recurring)
         .reduce((sum, c) => sum + parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan), 0);
    }
    return parseFloat((e as any)?.[m.key] || '0');
  }

  formatMoney(val: string | number | null): string {
    if (val === null || val === undefined) return '—';
    const num = typeof val === 'string' ? parseFloat(val) : val;
    if (isNaN(num)) return '—';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(num);
  }

  private _loadData(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;
    this.api.get<any>(`/initiatives/${this.initiativeId}`).subscribe(i => this.initiative.set(i));
    this.api.get<FinancialGrid>(base).subscribe(g => this.grid.set(g));
    this.api.get<CostLineListResponse>(`${base}/cost-lines`).subscribe(r => {
      this.costLines.set(r.items);
      this.loading.set(false);
      setTimeout(() => this.exposeAcceptanceHarness());
    });
  }
}
