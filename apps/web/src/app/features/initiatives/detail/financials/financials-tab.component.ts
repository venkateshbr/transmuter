import { Component, Input, OnInit, inject, signal, computed, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
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
  cogs_base: string;
  cogs_high: string;
  cogs_actual: string | null;
  cogs_pct_base: string;
  cogs_pct_high: string;
  cogs_pct_actual: string | null;
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
  definitions?: FinancialMetricDefinition[];
  scenarios?: FinancialScenarioDefinition[];
  benefit_lines?: FinancialBenefitLine[];
  values?: ConfigurableMetricValue[];
  settings?: { fiscal_year_start_month: number; reporting_currency: string };
  entries: FinancialEntry[];
  metric_values: FinancialMetricValue[];
  selections: InitiativeFinancialSelections;
  locked: boolean;
  lock_reason: string | null;
  summary: FinancialSummary;
}

interface FinancialMetricValue {
  metric_key: string;
  year: number;
  quarter: number | null;
  month: number | null;
  value_base: string;
  value_high: string;
  value_actual: string | null;
}

interface FinancialMetricDefinition {
  id: string;
  key: string;
  label: string;
  group_key?: string | null;
  value_type: 'currency' | 'percent' | 'number';
  aggregation: 'sum' | 'avg' | 'last' | 'formula';
  formula?: string | null;
  is_benefit: boolean;
  benefit_class?: string | null;
  is_active: boolean;
}

interface FinancialScenarioDefinition {
  id: string;
  key: string;
  label: string;
  kind: 'baseline' | 'plan' | 'forecast' | 'actual';
  is_primary: boolean;
  is_active: boolean;
}

interface ConfigurableMetricValue {
  id: string;
  metric_definition_id: string;
  scenario_id: string;
  benefit_line_id?: string | null;
  year: number;
  month: number;
  value: string;
  status: 'draft' | 'submitted' | 'approved';
  note?: string | null;
}

interface FinancialBenefitLine {
  id: string;
  metric_definition_id: string;
  name: string;
  description?: string | null;
  impact_type?: 'recurring' | 'one_time' | null;
  timing?: string | null;
  confidence?: string | number | null;
  show_in_summary: boolean;
  display_order: number;
}

interface InitiativeFinancialSelections {
  metric_keys: string[];
  cost_category_keys: string[];
}

interface CostLine {
  id: string;
  initiative_id: string;
  name: string;
  category_key: string;
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
  other_benefits?: string;
  benefits_total?: string;
  cogs: string;
  costs_recurring: string;
  costs_one_off: string;
  costs_total: string;
  net: string;
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

interface FinancialConfigGroup {
  id?: string;
  key: string;
  label: string;
  kind: 'calculation' | 'metric' | 'cost_category';
  rollup_type?: string | null;
  display_order: number;
  is_system: boolean;
  is_active: boolean;
}

interface FinancialConfigItem {
  id?: string;
  group_id?: string | null;
  group_key?: string | null;
  key: string;
  label: string;
  item_type: 'metric' | 'cost_category';
  system_metric_key?: string | null;
  rollup_type?: string | null;
  display_order: number;
  is_system: boolean;
  is_active: boolean;
}

interface FinancialConfiguration {
  groups: FinancialConfigGroup[];
  items: FinancialConfigItem[];
}

interface FinancialPeriodMonth {
  year: number;
  month: number;
  label: string;
}

interface GridMetric {
  category: string;
  label: string;
  key: string;
  source: 'financial_entry' | 'cost_line' | 'metric_value';
  costCategoryKey?: string;
  metricValueKey?: string;
  metricDefinitionId?: string;
  benefitLineId?: string | null;
  scenarioId?: string;
  metricScenario?: FinancialScenario;
  isRecurring?: boolean;
  actual?: boolean;
  readOnly?: boolean;
  formula?: string | null;
}

@Component({
  selector: 'app-financials-tab',
  standalone: true,
  imports: [CommonModule, FormsModule, HotTableModule, RouterLink],
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
            <a
              [routerLink]="['/initiatives', initiativeId, 'financial-scope']"
              class="btn-secondary py-1.5 px-3 text-[10px] flex items-center gap-2"
              aria-label="Configure initiative financial metrics and cost categories"
              title="Configure financial metrics and cost categories"
            >
              <span class="material-icons text-sm">tune</span>
              Configure Scope
            </a>
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
              [disabled]="exporting() || importing() || isLocked()"
            >
              <span class="material-icons text-sm">upload_file</span>
            </button>
            <button class="btn-ghost py-1.5 px-4 text-[10px] flex items-center gap-2" [disabled]="isLocked()" (click)="toggleEdit()">
              <span class="material-icons text-sm">{{ isEditing() ? 'visibility' : 'edit' }}</span>
              {{ isEditing() ? 'View Summary' : 'Edit Details' }}
            </button>
          </div>
        </div>

        @if (isLocked()) {
          <div class="mb-4 border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3 text-sm" style="color:var(--t-text-secondary)">
            <span class="font-bold" style="color:var(--t-text-primary)">Financials locked.</span>
            {{ grid()?.lock_reason || 'Changes require transformation office approval.' }}
          </div>
        }

        @if (!isLocked() && benefitMetricDefinitions().length) {
          <div class="mb-4 grid gap-3 border bg-[var(--t-surface-raised)] p-4 lg:grid-cols-[180px_1fr_120px_140px_120px_140px_140px_auto]" style="border-color:var(--t-border)">
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Benefit Metric</span>
              <select class="input-field py-2 text-xs" [ngModel]="newBenefitLineMetricId()" (ngModelChange)="newBenefitLineMetricId.set($event)" aria-label="Benefit line metric">
                <option value="">Select metric</option>
                @for (metric of benefitMetricDefinitions(); track metric.id) {
                  <option [value]="metric.id">{{ metric.label }}</option>
                }
              </select>
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Named Benefit Line</span>
              <input class="input-field py-2 text-xs font-bold" [ngModel]="newBenefitLineName()" (ngModelChange)="newBenefitLineName.set($event)" aria-label="Benefit line name" placeholder="Revenue uplift from improved retention">
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Confidence %</span>
              <input type="number" min="0" max="100" class="input-field py-2 text-xs" [ngModel]="newBenefitLineConfidence()" (ngModelChange)="newBenefitLineConfidence.set(numberValueOrNull($event))" aria-label="Benefit line confidence">
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Phasing</span>
              <select class="input-field py-2 text-xs" [ngModel]="newBenefitLinePhasingMode()" (ngModelChange)="setBenefitLinePhasingMode($event)" aria-label="Benefit line phasing mode">
                <option value="manual">Manual</option>
                <option value="one_off">One-off</option>
                <option value="spread">Spread</option>
              </select>
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Amount</span>
              <input type="number" class="input-field py-2 text-xs" [ngModel]="newBenefitLineAmount()" (ngModelChange)="newBenefitLineAmount.set(numberValueOrNullUnbounded($event))" aria-label="Benefit line phased amount">
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">Start</span>
              <input type="month" class="input-field py-2 text-xs" [ngModel]="newBenefitLineStartMonth()" (ngModelChange)="newBenefitLineStartMonth.set($event)" aria-label="Benefit line start month">
            </label>
            <label class="grid gap-1">
              <span class="text-[9px] font-black uppercase tracking-widest" style="color:var(--t-text-secondary)">End</span>
              <input type="month" class="input-field py-2 text-xs" [ngModel]="newBenefitLineEndMonth()" (ngModelChange)="newBenefitLineEndMonth.set($event)" [disabled]="newBenefitLinePhasingMode() !== 'spread'" aria-label="Benefit line end month">
            </label>
            <div class="flex items-end">
              <button type="button" class="btn-primary px-4 py-2 text-[10px]" [disabled]="!canAddBenefitLine()" (click)="addBenefitLine()" aria-label="Add benefit line">Add Line</button>
            </div>
          </div>
        }

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
            <button class="btn-primary flex items-center gap-2" [disabled]="saving() || isLocked()" (click)="saveGrid()">
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
    :host ::ng-deep .hot-computed-cell {
      background: color-mix(in srgb, var(--t-surface-raised) 78%, var(--t-accent) 22%) !important;
      color: var(--t-text-secondary) !important;
      font-style: italic;
    }
    :host ::ng-deep .hot-assumption-cell.hot-computed-cell {
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
  assumptions = signal<CellAssumption[]>([]);
  configuration = signal<FinancialConfiguration | null>(null);
  assumptionEditor = signal<(Partial<CellAssumption> & { row_key: string; column_key: string }) | null>(null);
  assumptionDraft = signal('');
  initiative = signal<any | null>(null);
  costLines = signal<CostLine[]>([]);
  isEditing = signal(false);
  scenario = signal<FinancialScenario>('base');
  newBenefitLineMetricId = signal('');
  newBenefitLineName = signal('');
  newBenefitLineConfidence = signal<number | null>(null);
  newBenefitLinePhasingMode = signal<'manual' | 'one_off' | 'spread'>('manual');
  newBenefitLineAmount = signal<number | null>(null);
  newBenefitLineStartMonth = signal('');
  newBenefitLineEndMonth = signal('');
  readonly scenarios: { id: FinancialScenario; label: string }[] = [
    { id: 'base', label: 'Base' },
    { id: 'high', label: 'High' },
    { id: 'actual', label: 'Actuals' },
  ];
  
  readonly METRICS: GridMetric[] = [
    { category: 'Revenue', label: 'Revenue Uplift ($) (Base)', key: 'revenue_uplift_base', source: 'financial_entry' },
    { category: 'Revenue', label: 'Revenue Uplift ($) (High)', key: 'revenue_uplift_high', source: 'financial_entry' },
    { category: 'Revenue', label: 'Revenue Uplift ($) (Actual)', key: 'revenue_uplift_actual', source: 'financial_entry' },
    { category: 'Revenue', label: 'Rev Uplift % (Base)', key: 'revenue_uplift_pct_base', source: 'financial_entry' },
    { category: 'Revenue', label: 'Rev Uplift % (High)', key: 'revenue_uplift_pct_high', source: 'financial_entry' },
    { category: 'Revenue', label: 'Rev Uplift % (Actual)', key: 'revenue_uplift_pct_actual', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS (Base)', key: 'cogs_base', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS (High)', key: 'cogs_high', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS (Actual)', key: 'cogs_actual', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS % (Base)', key: 'cogs_pct_base', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS % (High)', key: 'cogs_pct_high', source: 'financial_entry' },
    { category: 'COGS', label: 'COGS % (Actual)', key: 'cogs_pct_actual', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin (Base)', key: 'gross_margin_base', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin (High)', key: 'gross_margin_high', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin (Actual)', key: 'gross_margin_actual', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin % (Base)', key: 'gm_pct_base', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin % (High)', key: 'gm_pct_high', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin % (Actual)', key: 'gm_pct_actual', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin Uplift ($) (Base)', key: 'gm_uplift_base', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin Uplift ($) (High)', key: 'gm_uplift_high', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'Gross Margin Uplift ($) (Actual)', key: 'gm_uplift_actual', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'GM Uplift % (Base)', key: 'gm_uplift_pct_base', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'GM Uplift % (High)', key: 'gm_uplift_pct_high', source: 'financial_entry' },
    { category: 'Gross Margin', label: 'GM Uplift % (Actual)', key: 'gm_uplift_pct_actual', source: 'financial_entry' },
    { category: 'Costs', label: 'Recurring (Plan)', key: 'costs_recurring_plan', source: 'cost_line', isRecurring: true, actual: false },
    { category: 'Costs', label: 'Recurring (Actual)', key: 'costs_recurring_actual', source: 'cost_line', isRecurring: true, actual: true },
    { category: 'Costs', label: 'One-off (Plan)', key: 'costs_one_off_plan', source: 'cost_line', isRecurring: false, actual: false },
    { category: 'Costs', label: 'One-off (Actual)', key: 'costs_one_off_actual', source: 'cost_line', isRecurring: false, actual: true },
  ];

  readonly DEFAULT_METRIC_KEYS = new Set([
    'revenue_uplift_base',
    'revenue_uplift_high',
    'revenue_uplift_actual',
    'gm_uplift_base',
    'gm_uplift_high',
    'gm_uplift_actual',
    'cost_savings',
  ]);

  readonly DEFAULT_COST_CATEGORY_KEYS = new Set([
    'implementation',
    'software_subscriptions',
    'support_maintenance',
    'maintenance',
  ]);

  isLocked = computed(() => Boolean(this.grid()?.locked));

  configuredMetrics = computed<GridMetric[]>(() => {
    const cleanDefinitions = this.grid()?.definitions || [];
    const cleanScenario = this.selectedScenarioDefinition();
    if (cleanDefinitions.length && cleanScenario) {
      const benefitLines = this.grid()?.benefit_lines || [];
      const metricRows = cleanDefinitions
        .filter(definition => definition.is_active !== false)
        .sort((a, b) => (a.group_key || '').localeCompare(b.group_key || '') || a.label.localeCompare(b.label))
        .flatMap((definition): GridMetric[] => {
          const matchingLines = benefitLines
            .filter(line => line.metric_definition_id === definition.id && line.show_in_summary !== false)
            .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0) || a.name.localeCompare(b.name));
          const lines = matchingLines.length ? matchingLines : [null];
          return lines.map(line => ({
            category: this.metricCategoryLabel(definition),
            label: `${line ? `${line.name} / ` : ''}${definition.label} (${cleanScenario.label})${definition.aggregation === 'formula' ? ' - computed' : ''}`,
            key: `metric_${definition.id}_${cleanScenario.id}_${line?.id || 'default'}`,
            source: 'metric_value' as const,
            metricDefinitionId: definition.id,
            benefitLineId: line?.id || null,
            scenarioId: cleanScenario.id,
            metricValueKey: definition.key,
            metricScenario: this.scenario(),
            readOnly: definition.aggregation === 'formula',
            formula: definition.aggregation === 'formula' ? definition.formula || null : null,
          }));
        });
      const costRows: GridMetric[] = [
        { category: 'Costs', label: 'Recurring Costs (Plan)', key: 'costs_recurring_plan', source: 'cost_line', isRecurring: true, actual: false },
        { category: 'Costs', label: 'Recurring Costs (Actual)', key: 'costs_recurring_actual', source: 'cost_line', isRecurring: true, actual: true },
        { category: 'Costs', label: 'One-off Costs (Plan)', key: 'costs_one_off_plan', source: 'cost_line', isRecurring: false, actual: false },
        { category: 'Costs', label: 'One-off Costs (Actual)', key: 'costs_one_off_actual', source: 'cost_line', isRecurring: false, actual: true },
      ];
      return [...metricRows, ...costRows];
    }

    const config = this.configuration();
    const selectedMetrics = this.selectedMetricKeySet();
    const selectedCosts = this.selectedCostCategoryKeySet();
    if (!config) return this.METRICS.filter(metric => this.metricSelected(metric, selectedMetrics, selectedCosts));
    const groups = new Map(config.groups.map(group => [group.key, group]));
    const configuredMetrics = config.items
      .filter(item =>
        item.item_type === 'metric'
        && item.is_active
        && selectedMetrics.has(item.system_metric_key || item.key)
        && !this.isDuplicateCustomSystemMetric(item, config.items)
      )
      .sort((a, b) => {
        const groupA = groups.get(a.group_key || '')?.display_order || 0;
        const groupB = groups.get(b.group_key || '')?.display_order || 0;
        return groupA - groupB || a.display_order - b.display_order || a.label.localeCompare(b.label);
      })
      .flatMap((item): GridMetric[] => {
        const category = groups.get(item.group_key || '')?.label || 'Financials';
        if (item.system_metric_key) {
          return [{
            category,
            label: item.label,
            key: item.system_metric_key,
            source: 'financial_entry' as const,
          }];
        }
        return ([
          ['base', 'Base'],
          ['high', 'High'],
          ['actual', 'Actual'],
        ] as const).map(([scenario, label]) => ({
          category,
          label: `${item.label} (${label})`,
          key: `custom_${item.key}_${scenario}`,
          source: 'metric_value' as const,
          metricValueKey: item.key,
          metricScenario: scenario,
        }));
      });

    const configuredCosts = config.items
      .filter(item => item.item_type === 'cost_category' && item.is_active && selectedCosts.has(item.key))
      .sort((a, b) => {
        const groupA = groups.get(a.group_key || '')?.display_order || 0;
        const groupB = groups.get(b.group_key || '')?.display_order || 0;
        return groupA - groupB || a.display_order - b.display_order || a.label.localeCompare(b.label);
      })
      .flatMap(item => {
        const isRecurring = item.rollup_type === 'recurring_cost';
        const category = `Costs / ${this.costRollupLabel(item.rollup_type)}`;
        return [
          {
            category,
            label: `${item.label} (Plan)`,
            key: `cost_${item.key}_plan`,
            source: 'cost_line' as const,
            costCategoryKey: item.key,
            isRecurring,
            actual: false,
          },
          {
            category,
            label: `${item.label} (Actual)`,
            key: `cost_${item.key}_actual`,
            source: 'cost_line' as const,
            costCategoryKey: item.key,
            isRecurring,
            actual: true,
          },
        ];
      });

    const configured = [...configuredMetrics, ...configuredCosts];
    return configured;
  });

  selectedScenarioDefinition(): FinancialScenarioDefinition | null {
    const scenarios = (this.grid()?.scenarios || []).filter(item => item.is_active !== false);
    const keyByScenario: Record<FinancialScenario, string[]> = {
      base: ['plan_base', 'base'],
      high: ['plan_high', 'high'],
      actual: ['actual'],
    };
    const preferredKeys = keyByScenario[this.scenario()];
    return scenarios.find(item => preferredKeys.includes(item.key))
      || (this.scenario() === 'base' ? scenarios.find(item => item.kind === 'plan' && item.is_primary) : null)
      || scenarios.find(item => item.kind === (this.scenario() === 'actual' ? 'actual' : 'plan'))
      || scenarios[0]
      || null;
  }

  metricCategoryLabel(definition: FinancialMetricDefinition): string {
    if (definition.group_key) {
      return definition.group_key
        .split(/[_\s-]+/)
        .map(part => part ? part.charAt(0).toUpperCase() + part.slice(1) : part)
        .join(' ');
    }
    if (definition.is_benefit) return 'Benefits';
    return 'Financials';
  }

  private metricSelected(metric: GridMetric, selectedMetrics: Set<string>, selectedCosts: Set<string>): boolean {
    if (metric.source === 'cost_line') {
      if (!metric.costCategoryKey) return true;
      return selectedCosts.has(metric.costCategoryKey);
    }
    return selectedMetrics.has(metric.metricValueKey || metric.key);
  }

  private isDuplicateCustomSystemMetric(item: FinancialConfigItem, items: FinancialConfigItem[]): boolean {
    if (item.item_type !== 'metric' || item.is_system || item.system_metric_key) return false;
    return items.some(candidate =>
      candidate.item_type === 'metric'
      && candidate.is_active
      && candidate.is_system
      && Boolean(candidate.system_metric_key)
      && candidate.label === item.label
    );
  }

  private selectedMetricKeySet(): Set<string> {
    const selections = this.grid()?.selections;
    return new Set(selections ? selections.metric_keys : Array.from(this.DEFAULT_METRIC_KEYS));
  }

  private selectedCostCategoryKeySet(): Set<string> {
    const selections = this.grid()?.selections;
    return new Set(selections ? selections.cost_category_keys : Array.from(this.DEFAULT_COST_CATEGORY_KEYS));
  }

  private hasSelectedMetric(keys: string[]): boolean {
    const selected = this.selectedMetricKeySet();
    return keys.some(key => selected.has(key));
  }

  defaultCategoryKey(recurring: boolean): string {
    const items = this.configuration()?.items || [];
    const match = items.find(item =>
      item.item_type === 'cost_category'
      && item.is_active
      && item.rollup_type === (recurring ? 'recurring_cost' : 'one_off_cost')
    );
    return match?.key || 'other';
  }

  costRollupLabel(rollupType?: string | null): string {
    if (rollupType === 'recurring_cost') return 'Recurring';
    if (rollupType === 'one_off_cost') return 'One-time';
    return 'Unclassified';
  }

  summaryCards = computed(() => {
    const s = this.selectedScenarioCase();
    if (!s) return [];

    const cards: Array<{ label: string; plan: string; actual: string; highlight: boolean }> = [];
    if (this.hasSelectedMetric(['revenue_uplift_base', 'revenue_uplift_high', 'revenue_uplift_actual'])) {
      cards.push({ label: 'Revenue Uplift', plan: this.formatMoney(s.revenue_uplift), actual: this.scenarioLabel(), highlight: false });
    }
    if (this.hasSelectedMetric(['gm_uplift_base', 'gm_uplift_high', 'gm_uplift_actual'])) {
      cards.push({ label: 'GM Uplift', plan: this.formatMoney(s.gm_uplift), actual: this.scenarioLabel(), highlight: false });
    }
    if (Number(s.other_benefits || '0') !== 0) {
      cards.push({ label: 'Total Benefits', plan: this.formatMoney(s.benefits_total || s.gm_uplift), actual: this.scenarioLabel(), highlight: false });
    }
    if (this.hasSelectedMetric(['cogs_base', 'cogs_high', 'cogs_actual'])) {
      cards.push({ label: 'COGS', plan: this.formatMoney(s.cogs), actual: this.scenarioLabel(), highlight: false });
    }
    if (this.selectedCostCategoryKeySet().size > 0) {
      cards.push({ label: 'Total Costs', plan: this.formatMoney(s.costs_total), actual: this.scenarioLabel(), highlight: false });
    }
    cards.push({ label: 'Net Run-rate Impact', plan: this.formatMoney(s.net), actual: this.scenarioLabel(), highlight: true });
    return cards;
  });

  selectedScenarioCase = computed<ValueBridgeCase | null>(() => {
    const bridge = this.valueBridge();
    if (!bridge) return null;
    if (this.scenario() === 'high') return bridge.high_case;
    if (this.scenario() === 'actual') return bridge.actual;
    return bridge.base_case;
  });

  benefitMetricDefinitions = computed(() =>
    (this.grid()?.definitions || [])
      .filter(definition => definition.is_active !== false && definition.is_benefit && definition.aggregation !== 'formula')
      .sort((a, b) => a.label.localeCompare(b.label)),
  );

  dynamicYears = computed(() => {
    const planned = this.plannedMonthRange();
    const valueYears = this.valueBearingMonths().map(period => period.year);
    const minYear = Math.min(...planned.map(period => period.year), ...valueYears);
    const maxYear = Math.max(...planned.map(period => period.year), ...valueYears);
    if (!Number.isFinite(minYear) || !Number.isFinite(maxYear)) return [2026, 2027];
    const years: number[] = [];
    const startYear = Math.min(minYear, maxYear);
    const endYear = Math.max(minYear, maxYear);
    for (let y = startYear; y <= endYear; y++) years.push(y);
    return years;
  });

  editableMonths = computed<FinancialPeriodMonth[]>(() => {
    const byKey = new Map<string, FinancialPeriodMonth>();
    for (const period of [...this.plannedMonthRange(), ...this.valueBearingMonths()]) {
      byKey.set(`${period.year}-${period.month}`, period);
    }
    return Array.from(byKey.values()).sort((a, b) => a.year - b.year || a.month - b.month);
  });

  editableMonthsForYear(year: number): FinancialPeriodMonth[] {
    return this.editableMonths().filter(period => period.year === year);
  }

  hotNestedHeaders = computed(() => {
    const years = this.dynamicYears();
    const top = [{ label: '', colspan: 2 }];
    const bottom = [{ label: 'Category', colspan: 1 }, { label: 'Metric', colspan: 1 }];

    for (const year of years) {
      if (this.isEditing()) {
        const months = this.editableMonthsForYear(year);
        if (!months.length) continue;
        top.push({ label: year.toString(), colspan: months.length });
        for (const period of months) bottom.push({ label: period.label, colspan: 1 });
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
        for (const period of this.editableMonthsForYear(year)) {
          cols.push({ data: `col_${year}_m${period.month}`, type: 'numeric', numericFormat: { pattern: '$0,0' } });
        }
      } else {
        for (let q = 1; q <= 4; q++) {
          cols.push({
            data: `col_${year}_q${q}`,
            type: 'numeric',
            numericFormat: { pattern: '$0,0' },
            readOnly: true,
          });
        }
      }
    }
    return cols;
  });

  hotData = computed(() => {
    const entries = this.grid()?.entries || [];
    const metricValues = this.grid()?.metric_values || [];
    const costs = this.costLines();
    const years = this.dynamicYears();
    
    return this.configuredMetrics().map(m => {
      const row: any = {
        category: m.category,
        metric: m.label,
        key: m.key,
        source: m.source,
        costCategoryKey: m.costCategoryKey,
        isRecurring: m.isRecurring,
        actual: m.actual,
        readOnly: Boolean(m.readOnly),
        formula: m.formula || null,
        benefitLineId: m.benefitLineId || null,
      };
      for (const year of years) {
        if (this.isEditing()) {
          for (const period of this.editableMonthsForYear(year)) {
            const e = entries.find(x => x.year === year && x.month === period.month);
            row[`col_${year}_m${period.month}`] = this._getVal(m, year, period.month, null, e, entries, costs, metricValues);
          }
        } else {
          for (let q = 1; q <= 4; q++) {
            const e = entries.find(x => x.year === year && x.quarter === q);
            row[`col_${year}_q${q}`] = this._getVal(m, year, null, q, e, entries, costs, metricValues);
          }
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
    if (!data || !prop) return {};
    const classes = [];
    if (data.readOnly) classes.push('hot-computed-cell');
    if (this.hasAssumption(data.key, String(prop))) classes.push('hot-assumption-cell');
    if (!classes.length) return {};
    return {
      readOnly: data.readOnly || col < 2,
      className: classes.join(' '),
      renderer: data.readOnly ? 'text' : undefined,
    };
  };

  setScenario(next: FinancialScenario): void {
    this.scenario.set(next);
  }

  scenarioLabel(): string {
    return this.scenarios.find(item => item.id === this.scenario())?.label || 'Base';
  }

  toggleEdit(): void {
    if (this.isLocked()) return;
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
        if ((sourceData[sourceRowIndex] as any).readOnly) {
          throw new Error(`Financial row is computed and read-only: ${rowKey}`);
        }
        (sourceData[sourceRowIndex] as any)[columnKey] = value;
        const visualRowIndex = hotInstance.toVisualRow(sourceRowIndex);
        hotInstance.setDataAtRowProp(visualRowIndex, columnKey, value, 'acceptance');
        hotInstance.render();
      },
      save: () => this.saveGrid(),
      setScenario: (scenario: FinancialScenario) => this.setScenario(scenario),
      columns: () => this.hotColumns().map(column => column.data),
      rows: () => this.hotData().map(row => ({
        category: row.category,
        metric: row.metric,
        key: row.key,
        source: row.source,
        costCategoryKey: row.costCategoryKey,
        isRecurring: row.isRecurring,
        actual: row.actual,
        readOnly: row.readOnly,
        formula: row.formula,
        benefitLineId: row.benefitLineId,
      })),
      editableMonths: () => this.editableMonths(),
      hasColumn: (columnKey: string) => this.hotColumns().some(column => column.data === columnKey),
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
    if (this.isLocked()) return;
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
    const metricValueMap = new Map<string, any>();
    const cleanValueMap = new Map<string, any>();

    pivotedData.forEach((row: any) => {
      if (row.readOnly) return;
      const metricKey = row.key;
      this.editableMonths().forEach(period => {
        const val = row[`col_${period.year}_m${period.month}`] || 0;
        const numericVal = this.parseMoney(val);
        if (row.source === 'metric_value' && row.metricDefinitionId && row.scenarioId) {
          const benefitLineId = row.benefitLineId || null;
          const key = `${row.metricDefinitionId}_${row.scenarioId}_${benefitLineId || 'default'}_${period.year}_${period.month}`;
          if (!numericVal && !this.hasExistingConfigurableValue(period.year, period.month, row.metricDefinitionId, row.scenarioId, benefitLineId)) return;
          cleanValueMap.set(key, {
            metric_definition_id: row.metricDefinitionId,
            scenario_id: row.scenarioId,
            benefit_line_id: benefitLineId,
            year: period.year,
            month: period.month,
            value: numericVal.toString(),
            status: 'draft',
          });
        } else if (row.source === 'metric_value') {
          const customMetricKey = row.metricValueKey || metricKey;
          const scenario = row.metricScenario || 'base';
          const key = `${customMetricKey}_${period.year}_${period.month}_null`;
          if (!numericVal && !this.hasExistingMetricValue(period.year, period.month, customMetricKey)) return;
          if (!metricValueMap.has(key)) {
            metricValueMap.set(key, {
              metric_key: customMetricKey,
              year: period.year,
              month: period.month,
              quarter: null,
              value_base: '0',
              value_high: '0',
              value_actual: null,
            });
          }
          const metricValue = metricValueMap.get(key);
          if (scenario === 'actual') metricValue.value_actual = numericVal.toString();
          else if (scenario === 'high') metricValue.value_high = numericVal.toString();
          else metricValue.value_base = numericVal.toString();
        } else if (row.source === 'cost_line' || metricKey.startsWith('costs_')) {
          const isRecurring = row.isRecurring ?? metricKey.includes('recurring');
          const categoryKey = row.costCategoryKey || this.defaultCategoryKey(isRecurring);
          const key = `${period.year}_${period.month}_null_${isRecurring}_${categoryKey}`;
          const hasExisting = this.hasExistingCostLine(period.year, period.month, categoryKey, isRecurring);
          if (!numericVal && !hasExisting) return;
          if (!costMap.has(key)) {
            costMap.set(key, {
              name: row.costCategoryKey ? `${row.metric.replace(/\s+\((Plan|Actual)\)$/i, '')} (Grid)` : (isRecurring ? 'Recurring Costs (Grid)' : 'One-off Costs (Grid)'),
              category_key: categoryKey,
              year: period.year, month: period.month, quarter: null, amount_plan: '0', amount_actual: null, is_recurring: isRecurring
            });
          }
          const cost = costMap.get(key);
          if (row.actual ?? metricKey.includes('actual')) cost.amount_actual = numericVal.toString();
          else cost.amount_plan = numericVal.toString();
        } else {
          const key = `${period.year}_${period.month}_null`;
          const hasExisting = this.hasExistingEntry(period.year, period.month);
          if (!numericVal && !hasExisting) return;
          if (!entryMap.has(key)) entryMap.set(key, { year: period.year, month: period.month, quarter: null });
          entryMap.get(key)[metricKey] = numericVal.toString();
        }
      });
    });

    this.api.put(`/initiatives/${this.initiativeId}/financials`, { 
      entries: Array.from(entryMap.values()), 
      cost_lines: Array.from(costMap.values()),
      metric_values: Array.from(metricValueMap.values()),
      values: Array.from(cleanValueMap.values()),
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
    if (!file || this.importing() || this.isLocked()) return;
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

  private _getVal(m: GridMetric, year: number, mon: number | null, q: number | null, e: any, entries: any[], costs: any[], metricValues: FinancialMetricValue[]): number {
    const isCost = m.source === 'cost_line' || m.key.startsWith('costs_');
    const recurring = m.isRecurring ?? m.key.includes('recurring');
    const actual = m.actual ?? m.key.includes('actual');
    const metricValueKey = m.metricValueKey || m.key;
    const metricValueField = m.metricScenario === 'actual' ? 'value_actual' : (m.metricScenario === 'high' ? 'value_high' : 'value_base');
    const costMatchesMetric = (cost: any) =>
      cost.is_recurring === recurring
      && (!m.costCategoryKey || cost.category_key === m.costCategoryKey);

    if (q && !this.isEditing()) {
       let sum = 0;
       const months = [(q-1)*3+1, (q-1)*3+2, (q-1)*3+3];
       if (m.source === 'metric_value') {
         if (m.metricDefinitionId && m.scenarioId) {
           return (this.grid()?.values || [])
             .filter(x => x.metric_definition_id === m.metricDefinitionId && x.scenario_id === m.scenarioId && (x.benefit_line_id || null) === (m.benefitLineId || null) && x.year === year && months.includes(x.month))
             .reduce((s, x) => s + parseFloat(x.value || '0'), 0);
         }
         const monthlyValues = metricValues.filter(x => x.metric_key === metricValueKey && x.year === year && months.includes(x.month!) && this.metricValueHasValue(x));
         const periodValues = monthlyValues.length
           ? monthlyValues
           : metricValues.filter(x => x.metric_key === metricValueKey && x.year === year && x.month === null && x.quarter === q);
         sum = periodValues.reduce((s, x) => s + parseFloat((x as any)[metricValueField] || '0'), 0);
         sum += metricValues
           .filter(x => x.metric_key === metricValueKey && x.year === year && x.month === null && x.quarter === null)
           .reduce((s, x) => s + (parseFloat((x as any)[metricValueField] || '0') / 4), 0);
       } else if (isCost) {
         const monthlyCosts = costs.filter(c => c.year === year && months.includes(c.month!) && costMatchesMetric(c) && this.costLineHasValue(c));
         const periodCosts = monthlyCosts.length
           ? monthlyCosts
           : costs.filter(c => c.year === year && c.month === null && c.quarter === q && costMatchesMetric(c));
         sum = periodCosts
           .reduce((s, c) => s + parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan), 0);
         sum += costs
           .filter(c => c.year === year && c.month === null && c.quarter === null && costMatchesMetric(c))
           .reduce((s, c) => s + (parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan) / 4), 0);
       } else {
         const monthlyEntries = entries.filter(x => x.year === year && months.includes(x.month!) && this.entryHasValue(x));
         sum = monthlyEntries.length
           ? monthlyEntries.reduce((s, x) => s + parseFloat((x as any)[m.key] || '0'), 0)
           : parseFloat((e as any)?.[m.key] || '0');
         sum += entries
           .filter(x => x.year === year && x.month === null && x.quarter === null)
           .reduce((s, x) => s + (parseFloat((x as any)[m.key] || '0') / 4), 0);
       }
       return sum;
    }

    if (m.source === 'metric_value') {
      if (m.metricDefinitionId && m.scenarioId) {
        const cleanValues = this.grid()?.values || [];
        if (mon) {
          return cleanValues
            .filter(x => x.metric_definition_id === m.metricDefinitionId && x.scenario_id === m.scenarioId && (x.benefit_line_id || null) === (m.benefitLineId || null) && x.year === year && x.month === mon)
            .reduce((sum, x) => sum + parseFloat(x.value || '0'), 0);
        }
        if (q) {
          const months = [(q-1)*3+1, (q-1)*3+2, (q-1)*3+3];
          return cleanValues
            .filter(x => x.metric_definition_id === m.metricDefinitionId && x.scenario_id === m.scenarioId && (x.benefit_line_id || null) === (m.benefitLineId || null) && x.year === year && months.includes(x.month))
            .reduce((sum, x) => sum + parseFloat(x.value || '0'), 0);
        }
        return cleanValues
          .filter(x => x.metric_definition_id === m.metricDefinitionId && x.scenario_id === m.scenarioId && (x.benefit_line_id || null) === (m.benefitLineId || null) && x.year === year)
          .reduce((sum, x) => sum + parseFloat(x.value || '0'), 0);
      }
      const exactRows = metricValues
        .filter(x => x.metric_key === metricValueKey && x.year === year && x.month === mon && x.quarter === q);
      if (exactRows.length) {
        return exactRows.reduce((sum, x) => sum + parseFloat((x as any)[metricValueField] || '0'), 0);
      }

      if (mon) {
        const quarter = this.quarterForMonth(mon);
        const quarterTotal = metricValues
          .filter(x => x.metric_key === metricValueKey && x.year === year && x.month === null && x.quarter === quarter)
          .reduce((sum, x) => sum + parseFloat((x as any)[metricValueField] || '0'), 0);
        if (quarterTotal) return quarterTotal / this.editableMonthCountInQuarter(year, quarter);
      }

      return metricValues
        .filter(x => x.metric_key === metricValueKey && x.year === year && x.month === null && x.quarter === null)
        .reduce((sum, x) => sum + (parseFloat((x as any)[metricValueField] || '0') / (mon ? this.editableMonthCountInYear(year) : 4)), 0);
    }

    if (isCost) {
       const exactRows = costs
         .filter(c => c.year === year && c.month === mon && c.quarter === q && costMatchesMetric(c));
       if (exactRows.length) {
         return exactRows.reduce((sum, c) => sum + parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan), 0);
       }

       if (mon) {
         const quarter = this.quarterForMonth(mon);
         const quarterTotal = costs
           .filter(c => c.year === year && c.month === null && c.quarter === quarter && costMatchesMetric(c))
           .reduce((sum, c) => sum + parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan), 0);
         if (quarterTotal) return quarterTotal / this.editableMonthCountInQuarter(year, quarter);
       }

       return costs
         .filter(c => c.year === year && c.month === null && c.quarter === null && costMatchesMetric(c))
         .reduce((sum, c) => sum + (parseFloat(actual ? (c.amount_actual || '0') : c.amount_plan) / (mon ? this.editableMonthCountInYear(year) : 4)), 0);
    }
    if (e) return parseFloat((e as any)?.[m.key] || '0');

    if (mon) {
      const quarter = this.quarterForMonth(mon);
      const quarterEntry = entries.find(x => x.year === year && x.month === null && x.quarter === quarter);
      const quarterTotal = parseFloat((quarterEntry as any)?.[m.key] || '0');
      if (quarterTotal) return quarterTotal / this.editableMonthCountInQuarter(year, quarter);
    }

    return entries
      .filter(x => x.year === year && x.month === null && x.quarter === null)
      .reduce((sum, x) => sum + (parseFloat((x as any)[m.key] || '0') / (mon ? this.editableMonthCountInYear(year) : 4)), 0);
  }

  private plannedMonthRange(): FinancialPeriodMonth[] {
    const init = this.initiative();
    if (!init?.planned_start || !init?.planned_end) {
      return [2026, 2027].flatMap(year =>
        Array.from({ length: 12 }, (_, index) => this.periodMonth(year, index + 1)),
      );
    }

    const start = this.parseDateParts(init.planned_start);
    const end = this.parseDateParts(init.planned_end);
    if (!start || !end || start.year > end.year || (start.year === end.year && start.month > end.month)) {
      return [2026, 2027].flatMap(year =>
        Array.from({ length: 12 }, (_, index) => this.periodMonth(year, index + 1)),
      );
    }

    const periods: FinancialPeriodMonth[] = [];
    let year = start.year;
    let month = start.month;
    while (year < end.year || (year === end.year && month <= end.month)) {
      periods.push(this.periodMonth(year, month));
      month += 1;
      if (month > 12) {
        month = 1;
        year += 1;
      }
    }
    return periods;
  }

  private valueBearingMonths(): FinancialPeriodMonth[] {
    const byKey = new Map<string, FinancialPeriodMonth>();
    const addMonth = (year: number, month: number) => {
      byKey.set(`${year}-${month}`, this.periodMonth(year, month));
    };

    for (const entry of this.grid()?.entries || []) {
      if (!this.entryHasValue(entry)) continue;
      if (entry.month) {
        addMonth(entry.year, entry.month);
      } else if (entry.quarter) {
        for (const month of this.monthsForQuarter(entry.quarter)) addMonth(entry.year, month);
      }
    }

    for (const cost of this.costLines()) {
      if (!this.costLineHasValue(cost)) continue;
      if (cost.month) {
        addMonth(cost.year, cost.month);
      } else if (cost.quarter) {
        for (const month of this.monthsForQuarter(cost.quarter)) addMonth(cost.year, month);
      }
    }

    for (const metric of this.grid()?.metric_values || []) {
      if (!this.metricValueHasValue(metric)) continue;
      if (metric.month) {
        addMonth(metric.year, metric.month);
      } else if (metric.quarter) {
        for (const month of this.monthsForQuarter(metric.quarter)) addMonth(metric.year, month);
      }
    }

    return Array.from(byKey.values()).sort((a, b) => a.year - b.year || a.month - b.month);
  }

  private entryHasValue(entry: Partial<FinancialEntry>): boolean {
    return [
      entry.revenue_uplift_base,
      entry.revenue_uplift_high,
      entry.revenue_uplift_actual,
      entry.revenue_uplift_pct_base,
      entry.revenue_uplift_pct_high,
      entry.revenue_uplift_pct_actual,
      entry.gross_margin_base,
      entry.gross_margin_high,
      entry.gross_margin_actual,
      entry.gm_pct_base,
      entry.gm_pct_high,
      entry.gm_pct_actual,
      entry.gm_uplift_base,
      entry.gm_uplift_high,
      entry.gm_uplift_actual,
      entry.gm_uplift_pct_base,
      entry.gm_uplift_pct_high,
      entry.gm_uplift_pct_actual,
      entry.cogs_base,
      entry.cogs_high,
      entry.cogs_actual,
      entry.cogs_pct_base,
      entry.cogs_pct_high,
      entry.cogs_pct_actual,
    ].some(value => this.parseMoney(value) !== 0);
  }

  private costLineHasValue(cost: Partial<CostLine>): boolean {
    return this.parseMoney(cost.amount_plan) !== 0 || this.parseMoney(cost.amount_actual) !== 0;
  }

  private metricValueHasValue(metric: Partial<FinancialMetricValue>): boolean {
    return this.parseMoney(metric.value_base) !== 0
      || this.parseMoney(metric.value_high) !== 0
      || this.parseMoney(metric.value_actual) !== 0;
  }

  private hasExistingEntry(year: number, month: number): boolean {
    return (this.grid()?.entries || []).some(entry => entry.year === year && entry.month === month);
  }

  private hasExistingCostLine(year: number, month: number, categoryKey: string, isRecurring: boolean): boolean {
    return this.costLines().some(cost =>
      cost.year === year
      && cost.month === month
      && cost.category_key === categoryKey
      && cost.is_recurring === isRecurring
    );
  }

  private hasExistingMetricValue(year: number, month: number, metricKey: string): boolean {
    return (this.grid()?.metric_values || []).some(metric =>
      metric.metric_key === metricKey
      && metric.year === year
      && metric.month === month
    );
  }

  private hasExistingConfigurableValue(year: number, month: number, metricDefinitionId: string, scenarioId: string, benefitLineId: string | null): boolean {
    return (this.grid()?.values || []).some(value =>
      value.metric_definition_id === metricDefinitionId
      && value.scenario_id === scenarioId
      && (value.benefit_line_id || null) === benefitLineId
      && value.year === year
      && value.month === month
    );
  }

  private quarterForMonth(month: number): number {
    return Math.floor((month - 1) / 3) + 1;
  }

  private monthsForQuarter(quarter: number): number[] {
    const first = (quarter - 1) * 3 + 1;
    return [first, first + 1, first + 2];
  }

  private editableMonthCountInQuarter(year: number, quarter: number): number {
    return Math.max(
      1,
      this.editableMonths().filter(period => period.year === year && this.quarterForMonth(period.month) === quarter).length,
    );
  }

  private editableMonthCountInYear(year: number): number {
    return Math.max(1, this.editableMonths().filter(period => period.year === year).length);
  }

  private periodMonth(year: number, month: number): FinancialPeriodMonth {
    return {
      year,
      month,
      label: new Intl.DateTimeFormat('en-US', { month: 'short' }).format(new Date(year, month - 1, 1)),
    };
  }

  private parseDateParts(value: string): { year: number; month: number } | null {
    const match = /^(\d{4})-(\d{2})-\d{2}/.exec(value);
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null;
    return { year, month };
  }

  private parseMonthInput(value: string): { year: number; month: number } | null {
    const match = /^(\d{4})-(\d{2})$/.exec(value || '');
    if (!match) return null;
    const year = Number(match[1]);
    const month = Number(match[2]);
    if (!Number.isInteger(year) || !Number.isInteger(month) || month < 1 || month > 12) return null;
    return { year, month };
  }

  private monthRange(
    start: { year: number; month: number },
    end: { year: number; month: number },
  ): FinancialPeriodMonth[] {
    if (start.year > end.year || (start.year === end.year && start.month > end.month)) return [];
    const periods: FinancialPeriodMonth[] = [];
    let year = start.year;
    let month = start.month;
    while (year < end.year || (year === end.year && month <= end.month)) {
      periods.push(this.periodMonth(year, month));
      month += 1;
      if (month > 12) {
        month = 1;
        year += 1;
      }
    }
    return periods;
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

  numberValueOrNull(value: string | number | null): number | null {
    if (value === null || value === '') return null;
    const num = Number(value);
    return Number.isFinite(num) ? Math.max(0, Math.min(100, num)) : null;
  }

  numberValueOrNullUnbounded(value: string | number | null): number | null {
    if (value === null || value === '') return null;
    const num = Number(value);
    return Number.isFinite(num) ? num : null;
  }

  setBenefitLinePhasingMode(value: string): void {
    if (value === 'one_off' || value === 'spread') {
      this.newBenefitLinePhasingMode.set(value);
      return;
    }
    this.newBenefitLinePhasingMode.set('manual');
  }

  canAddBenefitLine(): boolean {
    if (!this.newBenefitLineMetricId() || !this.newBenefitLineName().trim()) return false;
    if (this.newBenefitLinePhasingMode() === 'manual') return true;
    if (this.newBenefitLineAmount() === null || !this.newBenefitLineStartMonth()) return false;
    if (this.newBenefitLinePhasingMode() === 'spread' && !this.newBenefitLineEndMonth()) return false;
    return true;
  }

  addBenefitLine(): void {
    if (!this.canAddBenefitLine() || this.isLocked()) return;
    const metricDefinitionId = this.newBenefitLineMetricId();
    const name = this.newBenefitLineName().trim();
    const confidence = this.newBenefitLineConfidence();
    const displayOrder = (this.grid()?.benefit_lines || []).length + 1;
    const phasingMode = this.newBenefitLinePhasingMode();
    this.saving.set(true);
    this.api.put<FinancialGrid>(`/initiatives/${this.initiativeId}/financials`, {
      values: [],
      benefit_lines: [{
        metric_definition_id: metricDefinitionId,
        name,
        description: null,
        impact_type: 'recurring',
        timing: null,
        confidence,
        phasing: {
          mode: phasingMode,
          amount: this.newBenefitLineAmount(),
          start_month: this.newBenefitLineStartMonth() || null,
          end_month: this.newBenefitLineEndMonth() || null,
        },
        attributes: {},
        show_in_summary: true,
        display_order: displayOrder,
      }],
    }).subscribe({
      next: grid => {
        const createdLine = (grid.benefit_lines || [])
          .filter(line => line.metric_definition_id === metricDefinitionId && line.name === name)
          .sort((a, b) => Number(b.display_order || 0) - Number(a.display_order || 0))[0];
        const generatedValues = createdLine ? this.generatedBenefitLineValues(createdLine.id) : [];
        if (!generatedValues.length) {
          this.finishBenefitLineAdd(grid);
          return;
        }
        this.api.put<FinancialGrid>(`/initiatives/${this.initiativeId}/financials`, {
          values: generatedValues,
        }).subscribe({
          next: updatedGrid => this.finishBenefitLineAdd(updatedGrid),
          error: () => {
            this.saving.set(false);
            alert('Benefit line was created, but phased values could not be generated.');
            this._loadData();
          },
        });
      },
      error: () => {
        this.saving.set(false);
        alert('Failed to add benefit line.');
      },
    });
  }

  private finishBenefitLineAdd(grid: FinancialGrid): void {
    this.grid.set(grid);
    this.newBenefitLineMetricId.set('');
    this.newBenefitLineName.set('');
    this.newBenefitLineConfidence.set(null);
    this.newBenefitLinePhasingMode.set('manual');
    this.newBenefitLineAmount.set(null);
    this.newBenefitLineStartMonth.set('');
    this.newBenefitLineEndMonth.set('');
    this.saving.set(false);
    this._loadData();
  }

  private generatedBenefitLineValues(benefitLineId: string): any[] {
    const mode = this.newBenefitLinePhasingMode();
    if (mode === 'manual') return [];
    const scenario = this.selectedScenarioDefinition();
    const amount = this.newBenefitLineAmount();
    const start = this.parseMonthInput(this.newBenefitLineStartMonth());
    const end = mode === 'spread'
      ? this.parseMonthInput(this.newBenefitLineEndMonth())
      : start;
    if (!scenario || amount === null || !start || !end) return [];
    const months = this.monthRange(start, end);
    if (!months.length) return [];
    const value = mode === 'spread' ? amount / months.length : amount;
    return months.map(period => ({
      metric_definition_id: this.newBenefitLineMetricId(),
      scenario_id: scenario.id,
      benefit_line_id: benefitLineId,
      year: period.year,
      month: period.month,
      value: value.toString(),
      status: 'draft',
    }));
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
    this.api.get<FinancialConfiguration>('/financial-configuration').subscribe({
      next: config => this.configuration.set(config),
      error: () => this.configuration.set(null),
    });
    this.api.get<FinancialGrid>(base).subscribe(g => this.grid.set(g));
    this.api.get<any>(`${base}/value-bridge`).subscribe(v => this.valueBridge.set(v));
    this._loadAssumptions();
    this.api.get<CostLineListResponse>(`${base}/cost-lines`).subscribe(r => {
      this.costLines.set(r.items);
      this.loading.set(false);
      setTimeout(() => this.exposeAcceptanceHarness());
    });
  }

  private _loadAssumptions(): void {
    const base = `/initiatives/${this.initiativeId}/financials`;
    this.api.get<CellAssumptionListResponse>(`${base}/assumptions`).subscribe(response => {
      this.assumptions.set(response.items);
      setTimeout(() => this.hotComponent?.hotInstance?.render());
    });
  }
}
