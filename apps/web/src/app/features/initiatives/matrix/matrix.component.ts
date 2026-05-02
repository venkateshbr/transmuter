import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

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
  imports: [CommonModule, RouterLink],
  template: `
    <div class="min-h-screen space-y-8 p-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Portfolio Matrix<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Impact vs. Stage analysis of the initiative pipeline.</p>
        </div>
        <div class="flex rounded-lg p-0.5 border text-xs bg-[var(--t-surface-raised)] border-[var(--t-border)]">
          <a routerLink="/initiatives/pipeline" class="px-3 py-1.5 rounded-md text-[var(--t-text-secondary)] hover:text-[var(--t-primary)]">Pipeline</a>
          <span class="px-3 py-1.5 rounded-md font-medium shadow-sm bg-[var(--t-surface)] text-[var(--t-text-primary)]">Matrix</span>
        </div>
      </div>

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
  
  items = signal<MatrixItem[]>([]);

  // Quadrant Logic
  quickWins = computed(() => this.items().filter(i => this.isEarly(i) && this.isHighImpact(i)));
  strategicBets = computed(() => this.items().filter(i => !this.isEarly(i) && this.isHighImpact(i)));
  fillIns = computed(() => this.items().filter(i => this.isEarly(i) && !this.isHighImpact(i)));
  reviewItems = computed(() => this.items().filter(i => !this.isEarly(i) && !this.isHighImpact(i)));

  ngOnInit() {
    this.api.get<any>('/initiatives', { page_size: 500 }).subscribe(res => {
      this.items.set(res.items || []);
    });
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
    return n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}m` : `$${(n / 1000).toFixed(0)}k`;
  }
}
