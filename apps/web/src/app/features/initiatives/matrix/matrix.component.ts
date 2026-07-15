import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { TenantReportingContextService } from '../../../core/services/tenant-reporting-context.service';
import { forkJoin } from 'rxjs';

interface MatrixItem {
  id: string;
  name: string;
  stage: string;
  planned_value_base: string | null;
  rag_status: string;
  priority: string;
}

@Component({
  selector: 'app-matrix',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule],
  template: `
    <div class="min-h-screen space-y-8 p-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Portfolio Matrix<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Reconcile portfolio value by workstream and strategic tag, with impact-stage analysis retained as a secondary view.</p>
        </div>
        <div class="flex rounded-lg p-0.5 border text-xs bg-[var(--t-surface-raised)] border-[var(--t-border)]">
          <a routerLink="/initiatives/pipeline" class="px-3 py-1.5 rounded-md text-[var(--t-text-secondary)] hover:text-[var(--t-primary)]">Pipeline</a>
          <span class="px-3 py-1.5 rounded-md font-medium shadow-sm bg-[var(--t-surface)] text-[var(--t-text-primary)]">Matrix</span>
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
        <div class="inline-flex border border-[var(--t-border)] bg-[var(--t-surface)] p-1">
          <button type="button" class="px-3 py-2 text-[10px] font-black uppercase tracking-widest" [class.bg-[var(--t-primary)]]="viewMode() === 'reconciliation'" [class.text-white]="viewMode() === 'reconciliation'" (click)="viewMode.set('reconciliation')" aria-label="Show workstream by tag value matrix">Workstream × Tag</button>
          <button type="button" class="px-3 py-2 text-[10px] font-black uppercase tracking-widest" [class.bg-[var(--t-primary)]]="viewMode() === 'impact'" [class.text-white]="viewMode() === 'impact'" (click)="viewMode.set('impact')" aria-label="Show impact versus stage matrix">Impact vs Stage</button>
        </div>
        @if (viewMode() === 'reconciliation') {
          <label class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Target year
            <select class="input-field ml-2 py-2 text-xs" [ngModel]="valueMatrix()?.selected_year" (ngModelChange)="loadValueMatrix($event)" aria-label="Select matrix target year">
              @for (year of valueMatrix()?.available_years || []; track year) { <option [ngValue]="year">FY{{ year }}</option> }
            </select>
          </label>
        }
      </div>

      @if (matrixError()) {
        <section class="border border-red-500/40 bg-red-500/10 p-6" role="alert">
          <p class="text-sm font-black text-[var(--t-text-primary)]">{{ matrixError() }}</p>
          <button type="button" class="btn-secondary mt-4" (click)="loadValueMatrix()" aria-label="Retry value matrix">Try again</button>
        </section>
      }

      @if (viewMode() === 'reconciliation' && !matrixError()) {
        <section class="card overflow-hidden" data-testid="initiative-value-matrix">
          <div class="overflow-x-auto">
            <table class="w-full min-w-[900px] border-collapse text-left">
              <thead class="bg-[var(--t-primary)] text-white"><tr><th class="px-4 py-4 text-xs font-black uppercase">Workstream</th>@for (tag of valueMatrix()?.tags || []; track tag.id) { <th class="px-4 py-4 text-center text-xs font-black uppercase">{{ tag.label }}</th> }<th class="px-4 py-4 text-center text-xs font-black uppercase">Total</th></tr></thead>
              <tbody>
                @for (row of valueMatrix()?.rows || []; track row.workstream_id || row.workstream_name) {
                  <tr class="border-b border-[var(--t-border)] odd:bg-[var(--t-surface)] even:bg-[var(--t-surface-raised)]">
                    <th class="px-4 py-3"><span class="block text-sm font-black text-[var(--t-text-primary)]">{{ row.workstream_name }}</span><span class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">{{ row.business_unit_name || 'Portfolio' }}</span></th>
                    @for (tag of valueMatrix()?.tags || []; track tag.id) { <td class="px-2 py-2 text-center"><button type="button" class="w-full border border-[var(--t-border)] p-3 text-xs font-black text-[var(--t-text-primary)] hover:border-[var(--t-accent)]" (click)="openCell(row.workstream_name, tag.label, row.cells?.[tag.id])" [attr.aria-label]="'Open ' + row.workstream_name + ' ' + tag.label + ' contributors'"><span class="block">{{ formatRange(row.cells?.[tag.id]) }}</span><span class="mt-1 block text-[9px] text-[var(--t-text-tertiary)]">{{ row.cells?.[tag.id]?.initiative_count || 0 }} initiatives</span></button></td> }
                    <td class="px-2 py-2 text-center"><button type="button" class="w-full bg-[var(--t-primary)] p-3 text-xs font-black text-white" (click)="openCell(row.workstream_name, 'Total', row.total)" [attr.aria-label]="'Open all contributors for ' + row.workstream_name">{{ formatRange(row.total) }}</button></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          @if (selectedCell(); as selection) {
            <aside class="border-t border-[var(--t-border)] bg-[var(--t-surface-raised)] p-5" aria-label="Value matrix contributors">
              <div class="flex items-center justify-between"><h2 class="text-lg font-black text-[var(--t-text-primary)]">{{ selection.row }} · {{ selection.tag }}</h2><button type="button" class="btn-ghost" (click)="selectedCell.set(null)" aria-label="Close matrix contributors">Close</button></div>
              <div class="mt-4 grid gap-2 md:grid-cols-2">@for (initiative of selection.cell?.initiatives || []; track initiative.initiative_id) { <a [routerLink]="['/initiatives', initiative.initiative_id]" class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3 text-sm font-black text-[var(--t-text-primary)] hover:border-[var(--t-accent)]">{{ initiative.initiative_code }} · {{ initiative.name }}<span class="mt-1 block text-xs font-bold text-[var(--t-text-tertiary)]">{{ formatRange(initiative) }}</span></a> }</div>
            </aside>
          }
        </section>
      } @else if (viewMode() === 'impact' && !matrixError()) {

      <!-- Matrix Grid -->
      <div class="grid grid-cols-2 grid-rows-2 gap-4 h-[700px] relative">
        
        <!-- Axis Labels -->
        <div class="absolute -left-12 top-1/2 -rotate-90 text-[10px] font-bold uppercase tracking-[0.3em] text-[var(--t-text-tertiary)]">Impact (Planned Value)</div>
        <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[10px] font-bold uppercase tracking-[0.3em] text-[var(--t-text-tertiary)]">Execution Stage</div>

        <!-- Quadrant 1: Strategic Bets (High Impact, Late Stage) -->
        <div class="card bg-[var(--t-surface)] border-2 border-[var(--t-border)] p-6 flex flex-col overflow-hidden group hover:border-[var(--t-accent)] transition-all">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-primary)]">Strategic Bets</h3>
            <span class="text-[9px] font-bold text-[var(--t-text-tertiary)]">LATE STAGE | HIGH IMPACT</span>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            @for (item of strategicBets(); track item.id) {
              <ng-container *ngTemplateOutlet="itemCard; context: { $implicit: item }"></ng-container>
            }
          </div>
        </div>

        <!-- Quadrant 2: Quick Wins (High Impact, Early Stage) -->
        <div class="card bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]/10 border-2 border-[var(--t-accent)] p-6 flex flex-col overflow-hidden shadow-xl">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Quick Wins</h3>
            <span class="text-[9px] font-bold text-[var(--t-text-tertiary)]">EARLY STAGE | HIGH IMPACT</span>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            @for (item of quickWins(); track item.id) {
              <ng-container *ngTemplateOutlet="itemCard; context: { $implicit: item }"></ng-container>
            }
          </div>
        </div>

        <!-- Quadrant 3: Review (Low Impact, Late Stage) -->
        <div class="card bg-[var(--t-surface-raised)]/50 border-2 border-[var(--t-border)] border-dashed p-6 flex flex-col overflow-hidden opacity-80">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-secondary)]">Review / Deprioritize</h3>
            <span class="text-[9px] font-bold text-[var(--t-text-tertiary)]">LATE STAGE | LOW IMPACT</span>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            @for (item of reviewItems(); track item.id) {
              <ng-container *ngTemplateOutlet="itemCard; context: { $implicit: item }"></ng-container>
            }
          </div>
        </div>

        <!-- Quadrant 4: Fill-Ins (Low Impact, Early Stage) -->
        <div class="card bg-[var(--t-surface)] border-2 border-[var(--t-border)] p-6 flex flex-col overflow-hidden">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-primary)]">Fill-Ins</h3>
            <span class="text-[9px] font-bold text-[var(--t-text-tertiary)]">EARLY STAGE | LOW IMPACT</span>
          </div>
          <div class="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
            @for (item of fillIns(); track item.id) {
              <ng-container *ngTemplateOutlet="itemCard; context: { $implicit: item }"></ng-container>
            }
          </div>
        </div>
      </div>
      }
    </div>

    <!-- Shared Item Card Template -->
    <ng-template #itemCard let-item>
      <div [routerLink]="['/initiatives', item.id]" 
           class="p-3 rounded-xl border border-[var(--t-border)] bg-[var(--t-surface)] hover:bg-[var(--t-surface-raised)] hover:scale-[1.02] transition-all cursor-pointer group/card shadow-sm">
        <div class="flex justify-between items-start gap-2">
          <span class="text-[11px] font-bold text-[var(--t-text-primary)] leading-tight group-hover/card:text-[var(--t-accent)] transition-colors line-clamp-2">
            {{ item.name }}
          </span>
          <div class="w-2 h-2 rounded-full shrink-0" [style.background]="getRagColor(item.rag_status)"></div>
        </div>
        <div class="flex justify-between items-center mt-3 pt-3 border-t border-[var(--t-border)]/50">
          <span class="text-[9px] font-mono text-[var(--t-text-tertiary)]">{{ formatValue(item.planned_value_base) }}</span>
          <span class="text-[8px] font-bold uppercase tracking-tighter px-1.5 py-0.5 rounded bg-[var(--t-surface-raised)] text-[var(--t-text-tertiary)]">
            {{ item.stage.replace('_', ' ') }}
          </span>
        </div>
      </div>
    </ng-template>
  `,
  styles: [`
    :host { display: block; }
    .custom-scrollbar::-webkit-scrollbar { width: 4px; }
    .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: var(--t-border); border-radius: 10px; }
    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--t-accent); }
  `]
})
export class MatrixComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly reportingContext = inject(TenantReportingContextService);
  
  items = signal<MatrixItem[]>([]);
  viewMode = signal<'reconciliation' | 'impact'>('reconciliation');
  valueMatrix = signal<any | null>(null);
  selectedCell = signal<any | null>(null);
  matrixError = signal<string | null>(null);

  // Quadrant Logic
  quickWins = computed(() => this.items().filter(i => this.isEarly(i) && this.isHighImpact(i)));
  strategicBets = computed(() => this.items().filter(i => !this.isEarly(i) && this.isHighImpact(i)));
  fillIns = computed(() => this.items().filter(i => this.isEarly(i) && !this.isHighImpact(i)));
  reviewItems = computed(() => this.items().filter(i => !this.isEarly(i) && !this.isHighImpact(i)));

  ngOnInit() {
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe(res => {
      this.items.set(res.items || []);
    });
    this.loadValueMatrix();
  }

  loadValueMatrix(targetYear?: number): void {
    this.matrixError.set(null);
    const params: Record<string, string | number | boolean> = targetYear
      ? { target_year: targetYear }
      : {};
    forkJoin({
      reporting: this.reportingContext.load(),
      response: this.api.get<any>('/dashboard', params),
    }).subscribe({
      next: ({ response }) => this.valueMatrix.set(response?.value_matrix || null),
      error: () => {
        this.valueMatrix.set(null);
        this.matrixError.set('The workstream-by-tag value matrix could not be loaded. Retry before reconciling portfolio totals.');
      },
    });
  }

  openCell(row: string, tag: string, cell: any): void {
    this.selectedCell.set({ row, tag, cell });
  }

  formatRange(cell: any): string {
    if (!cell || (!Number(cell.base || 0) && !Number(cell.high || 0))) return '—';
    return `${this.reportingContext.formatMoney(cell.base, { notation: 'compact', maximumFractionDigits: 1 })} – ${this.reportingContext.formatMoney(cell.high, { notation: 'compact', maximumFractionDigits: 1 })}`;
  }

  isEarly(item: MatrixItem): boolean {
    return ['scoping', 'ideation', 'design'].includes(item.stage.toLowerCase());
  }

  isHighImpact(item: MatrixItem): boolean {
    const val = parseFloat(item.planned_value_base || '0');
    // Threshold for "High Impact" is 500k in this context
    return val >= 500000 || item.priority === 'high';
  }

  getRagColor(rag: string): string {
    return rag === 'red' ? 'var(--t-red)' : rag === 'amber' ? 'var(--t-amber)' : 'var(--t-green)';
  }

  formatValue(v: string | null): string {
    if (!v) return '—';
    const n = parseFloat(v);
    if (!n) return '—';
    return this.reportingContext.formatMoney(n, { notation: 'compact', maximumFractionDigits: 1 });
  }
}
