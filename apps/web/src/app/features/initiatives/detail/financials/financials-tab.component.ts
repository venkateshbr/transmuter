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

type FinancialScenario = 'base' | 'high' | 'actual';

interface ValueBridgeCase {
  revenue_uplift: string;
  gross_margin: string;
  gm_uplift: string;
  costs_recurring: string;
  costs_one_off: string;
  costs_total: string;
  net: string;
}

interface BreakEvenPoint {
  period: string;
  cumulative_gm_uplift: string;
  cumulative_costs: string;
  cumulative_net: string;
  run_rate_gm_uplift: string;
  run_rate_costs: string;
  is_break_even: boolean;
}

interface BreakEvenResponse {
  scenario: FinancialScenario;
  break_even_period: string | null;
  points: BreakEvenPoint[];
}

interface CellAssumption {
  id: string;
  initiative_id: string;
  row_key: string;
  column_key: string;
  comment: string;
}

interface CellAssumptionListResponse {
  items: CellAssumption[];
  total: number;
}

@Component({
  selector: 'app-financials-tab',
  standalone: true,
  imports: [CommonModule, HotTableModule],
  template: `
    <div class="space-y-6">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div class="inline-flex rounded-lg border bg-[var(--t-surface-raised)] p-1" style="border-color:var(--t-border)" data-testid="financial-scenario-toggle">
          @for (option of scenarios; track option.id) {
            <button
              type="button"
              class="h-8 px-3 text-[11px] font-bold uppercase transition-colors rounded-md"
              [class.bg-white]="scenario() === option.id"
              [class.text-[var(--t-primary)]]="scenario() === option.id"
              [class.text-[var(--t-text-secondary)]]="scenario() !== option.id"
              [attr.aria-pressed]="scenario() === option.id"
              (click)="setScenario(option.id)"
            >
              {{ option.label }}
            </button>
          }
        </div>
        <div class="text-right">
          <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">Break-even</p>
          <p class="text-sm font-bold" style="color:var(--t-text-primary)" data-testid="financial-break-even-period">
            {{ breakEven()?.break_even_period || 'Not reached' }}
          </p>
        </div>
      </div>

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
            [contextMenu]="hotContextMenu"
            [cells]="hotCells"
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

      <div class="card p-6" data-testid="financial-break-even-chart">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="text-base font-bold" style="color:var(--t-text-primary)">
              Break-even & Run-rate<span style="color:var(--t-accent)">.</span>
            </h3>
          </div>
          <span class="badge-ghost text-[10px] uppercase font-bold">{{ scenarioLabel() }}</span>
        </div>
        @if (breakEvenPoints().length) {
          <div class="h-56 border-b border-l relative px-2" style="border-color:var(--t-border)">
            @for (point of breakEvenPoints(); track point.period) {
              <div
                class="absolute bottom-0 w-2 rounded-t-sm bg-[var(--t-accent)] opacity-80"
                [style.left.%]="point.x"
                [style.height.%]="point.gmHeight"
                [attr.title]="point.period + ' GM ' + formatMoney(point.gm)"
              ></div>
              <div
                class="absolute bottom-0 w-2 rounded-t-sm bg-[var(--t-red)] opacity-55"
                [style.left.%]="point.x + 1.1"
                [style.height.%]="point.costHeight"
                [attr.title]="point.period + ' Costs ' + formatMoney(point.costs)"
              ></div>
              @if (point.isBreakEven) {
                <div class="absolute top-0 bottom-0 border-l-2 border-[var(--t-green)]" [style.left.%]="point.x + 1.1"></div>
              }
            }
          </div>
          <div class="mt-4 flex flex-wrap items-center justify-between gap-3 text-[10px] font-semibold uppercase" style="color:var(--t-text-secondary)">
            <span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-[var(--t-accent)]"></span>Cumulative GM uplift</span>
            <span class="inline-flex items-center gap-1.5"><span class="h-2.5 w-2.5 rounded-sm bg-[var(--t-red)] opacity-60"></span>Cumulative costs</span>
            <span>Run-rate GM {{ formatMoney(latestRunRate().gm) }} / Costs {{ formatMoney(latestRunRate().costs) }}</span>
          </div>
        } @else {
          <div class="h-40 flex items-center justify-center text-sm" style="color:var(--t-text-secondary)">No financial periods available.</div>
        }
      </div>

      @if (assumptions().length) {
        <div class="card p-6" data-testid="financial-assumptions-list">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-base font-bold" style="color:var(--t-text-primary)">Cell Assumptions<span style="color:var(--t-accent)">.</span></h3>
            <span class="badge-ghost text-[10px] uppercase font-bold">{{ assumptions().length }}</span>
          </div>
          <div class="grid md:grid-cols-2 gap-3">
            @for (item of assumptions(); track item.id) {
              <button
                type="button"
                class="text-left rounded-lg border p-3 hover:border-[var(--t-accent)] transition-colors bg-[var(--t-surface-raised)]"
                style="border-color:var(--t-border)"
                (click)="editAssumption(item)"
              >
                <p class="text-[10px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">{{ item.row_key }} / {{ item.column_key }}</p>
                <p class="text-sm" style="color:var(--t-text-primary)">{{ item.comment }}</p>
              </button>
            }
          </div>
        </div>
      }

      @if (assumptionEditor()) {
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div class="w-full max-w-md rounded-xl border bg-[var(--t-surface)] p-5 shadow-xl" style="border-color:var(--t-border)">
            <div class="flex items-start justify-between gap-4 mb-4">
              <div>
                <h3 class="text-base font-bold" style="color:var(--t-text-primary)">Cell Assumption</h3>
                <p class="text-[11px] font-semibold uppercase tracking-wider" style="color:var(--t-text-secondary)">
                  {{ assumptionEditor()?.row_key }} / {{ assumptionEditor()?.column_key }}
                </p>
              </div>
              <button type="button" class="btn-ghost h-8 w-8 p-0" aria-label="Close assumption editor" (click)="closeAssumptionEditor()">
                <span class="material-icons text-sm">close</span>
              </button>
            </div>
            <textarea
              class="w-full min-h-32 rounded-lg border bg-[var(--t-surface-raised)] p-3 text-sm outline-none focus:border-[var(--t-accent)]"
              style="border-color:var(--t-border); color:var(--t-text-primary)"
              data-testid="financial-assumption-comment"
              [value]="assumptionDraft()"
              (input)="assumptionDraft.set($any($event.target).value)"
            ></textarea>
            <div class="flex justify-between items-center mt-4">
              <button type="button" class="btn-ghost text-[11px]" [disabled]="!assumptionEditor()?.id" (click)="deleteAssumption()">Delete</button>
              <button type="button" class="btn-primary text-[11px]" data-testid="financial-assumption-save" [disabled]="!assumptionDraft().trim()" (click)="saveAssumption()">Save Assumption</button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host ::ng-deep .hot-assumption-cell {
      box-shadow: inset 0 0 0 2px var(--t-accent);
    }
  `],
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
  valueBridge = signal<any | null>(null);
  breakEven = signal<BreakEvenResponse | null>(null);
  assumptions = signal<CellAssumption[]>([]);
  assumptionEditor = signal<(Partial<CellAssumption> & { row_key: string; column_key: string }) | null>(null);
  assumptionDraft = signal('');
  initiative = signal<any | null>(null);
  costLines = signal<CostLine[]>([]);
  isEditing = signal(false);
  scenario = signal<FinancialScenario>('base');
  readonly scenarios: { id: FinancialScenario; label: string }[] = [
    { id: 'base', label: 'Base' },
    { id: 'high', label: 'High' },
    { id: 'actual', label: 'Actuals' },
  ];
  
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
    const s = this.selectedScenarioCase();
    if (!s) return [];
    const cogs = this.parseMoney(s.revenue_uplift) - this.parseMoney(s.gross_margin);

    return [
      { label: 'Revenue Uplift', plan: this.formatMoney(s.revenue_uplift), actual: this.scenarioLabel(), highlight: false },
      { label: 'GM Uplift', plan: this.formatMoney(s.gm_uplift), actual: this.scenarioLabel(), highlight: false },
      { label: 'COGS', plan: this.formatMoney(cogs), actual: this.scenarioLabel(), highlight: false },
      { label: 'Total Costs', plan: this.formatMoney(s.costs_total), actual: this.scenarioLabel(), highlight: false },
      { label: 'Net Value', plan: this.formatMoney(s.net), actual: this.scenarioLabel(), highlight: true },
    ];
  });

  selectedScenarioCase = computed<ValueBridgeCase | null>(() => {
    const bridge = this.valueBridge();
    if (!bridge) return null;
    if (this.scenario() === 'high') return bridge.high_case;
    if (this.scenario() === 'actual') return bridge.actual;
    return bridge.base_case;
  });

  breakEvenPoints = computed(() => {
    const points = this.breakEven()?.points || [];
    const max = Math.max(
      1,
      ...points.map(point => Math.max(this.parseMoney(point.cumulative_gm_uplift), this.parseMoney(point.cumulative_costs))),
    );
    return points.map((point, index) => {
      const gm = this.parseMoney(point.cumulative_gm_uplift);
      const costs = this.parseMoney(point.cumulative_costs);
      return {
        period: point.period,
        x: points.length === 1 ? 48 : (index / Math.max(1, points.length - 1)) * 94,
        gm,
        costs,
        gmHeight: Math.max(3, (gm / max) * 100),
        costHeight: Math.max(3, (costs / max) * 100),
        isBreakEven: point.is_break_even,
      };
    });
  });

  latestRunRate = computed(() => {
    const point = (this.breakEven()?.points || []).at(-1);
    return {
      gm: this.parseMoney(point?.run_rate_gm_uplift || '0'),
      costs: this.parseMoney(point?.run_rate_costs || '0'),
    };
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

  hotContextMenu: any = {
    items: {
      assumption: {
        name: 'Add/Edit Assumption',
        callback: (_key: string, selection: any[]) => this.openAssumptionForSelection(selection?.[0]),
      },
      copy: {},
    },
  };

  hotCells = (row: number, col: number) => {
    const data = this.hotComponent?.hotInstance?.getSourceDataAtRow(row);
    const prop = this.hotComponent?.hotInstance?.colToProp(col);
    if (!data || !prop || !this.hasAssumption(data.key, String(prop))) return {};
    return { className: 'hot-assumption-cell' };
  };

  setScenario(next: FinancialScenario): void {
    this.scenario.set(next);
    this._loadBreakEven();
  }

  scenarioLabel(): string {
    return this.scenarios.find(item => item.id === this.scenario())?.label || 'Base';
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
      setScenario: (scenario: FinancialScenario) => this.setScenario(scenario),
      openAssumption: (rowKey: string, columnKey: string) => {
        this.openAssumption(rowKey, columnKey);
        return true;
      },
      setAssumption: (rowKey: string, columnKey: string, comment: string) => {
        this.openAssumption(rowKey, columnKey);
        this.assumptionDraft.set(comment);
        this.saveAssumption();
      },
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

  parseMoney(val: string | number | null | undefined): number {
    if (val === null || val === undefined) return 0;
    const num = typeof val === 'string' ? parseFloat(val) : val;
    return Number.isFinite(num) ? num : 0;
  }

  openAssumptionForSelection(selection: any): void {
    if (!selection) return;
    const hotInstance = this.hotComponent?.hotInstance;
    const rowIndex = selection.start?.row ?? selection.from?.row ?? 0;
    const colIndex = selection.start?.col ?? selection.from?.col ?? 0;
    const row = hotInstance?.getSourceDataAtRow(rowIndex);
    const prop = hotInstance?.colToProp(colIndex);
    if (!row?.key || !prop || ['category', 'metric'].includes(String(prop))) return;
    this.openAssumption(row.key, String(prop));
  }

  openAssumption(rowKey: string, columnKey: string): void {
    const existing = this.assumptions().find(item => item.row_key === rowKey && item.column_key === columnKey);
    this.assumptionEditor.set(existing || { row_key: rowKey, column_key: columnKey });
    this.assumptionDraft.set(existing?.comment || '');
  }

  editAssumption(item: CellAssumption): void {
    this.assumptionEditor.set(item);
    this.assumptionDraft.set(item.comment);
  }

  closeAssumptionEditor(): void {
    this.assumptionEditor.set(null);
    this.assumptionDraft.set('');
  }

  saveAssumption(): void {
    const current = this.assumptionEditor();
    const comment = this.assumptionDraft().trim();
    if (!current || !comment) return;
    const body = { row_key: current.row_key, column_key: current.column_key, comment };
    const request = current.id
      ? this.api.put<CellAssumption>(`/initiatives/${this.initiativeId}/financials/assumptions/${current.id}`, { comment })
      : this.api.post<CellAssumption>(`/initiatives/${this.initiativeId}/financials/assumptions`, body);
    request.subscribe({
      next: () => {
        this.closeAssumptionEditor();
        this._loadAssumptions();
      },
      error: () => alert('Failed to save cell assumption.'),
    });
  }

  deleteAssumption(): void {
    const current = this.assumptionEditor();
    if (!current?.id) return;
    this.api.delete(`/initiatives/${this.initiativeId}/financials/assumptions/${current.id}`).subscribe({
      next: () => {
        this.closeAssumptionEditor();
        this._loadAssumptions();
      },
      error: () => alert('Failed to delete cell assumption.'),
    });
  }

  hasAssumption(rowKey: string, columnKey: string): boolean {
    return this.assumptions().some(item => item.row_key === rowKey && item.column_key === columnKey);
  }

  private _loadData(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;
    this.api.get<any>(`/initiatives/${this.initiativeId}`).subscribe(i => this.initiative.set(i));
    this.api.get<FinancialGrid>(base).subscribe(g => this.grid.set(g));
    this.api.get<any>(`${base}/value-bridge`).subscribe(v => this.valueBridge.set(v));
    this._loadBreakEven();
    this._loadAssumptions();
    this.api.get<CostLineListResponse>(`${base}/cost-lines`).subscribe(r => {
      this.costLines.set(r.items);
      this.loading.set(false);
      setTimeout(() => this.exposeAcceptanceHarness());
    });
  }

  private _loadBreakEven(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;
    this.api.get<BreakEvenResponse>(`${base}/break-even?scenario=${this.scenario()}`).subscribe(data => this.breakEven.set(data));
  }

  private _loadAssumptions(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;
    this.api.get<CellAssumptionListResponse>(`${base}/assumptions`).subscribe(response => {
      this.assumptions.set(response.items);
      setTimeout(() => this.hotComponent?.hotInstance?.render());
    });
  }
}
