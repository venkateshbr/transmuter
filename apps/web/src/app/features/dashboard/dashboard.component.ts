import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Portfolio Dashboard<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Real-time transformation performance across all workstreams.</p>
        </div>
        <div class="flex gap-3">
          <button class="btn-ghost text-sm">Export Report ↗</button>
          <button class="btn-primary text-sm flex items-center gap-2">
            <span>+</span> Executive Summary
          </button>
        </div>
      </div>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div class="card p-6 border-l-4 border-[var(--t-accent)]">
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Initiatives</p>
          <p class="text-3xl font-bold text-[var(--t-text-primary)]">{{ data()?.summary?.total_initiatives || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            <span class="text-green-500">↑ 2</span> from last week
          </p>
        </div>
        <div class="card p-6 border-l-4 border-red-500">
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">At Risk</p>
          <p class="text-3xl font-bold text-red-500">{{ data()?.summary?.at_risk || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            Requires immediate attention
          </p>
        </div>
        <div class="card p-6 border-l-4 border-amber-500">
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Pending Approvals</p>
          <p class="text-3xl font-bold text-amber-500">{{ data()?.summary?.pending_approvals || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2">Gate submissions awaiting review</p>
        </div>
      </div>

      <!-- Main Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Left Column: Pipeline & RAG -->
        <div class="lg:col-span-2 space-y-8">
          
          <!-- Pipeline by Stage -->
          <div class="card p-6">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Pipeline by Stage</h3>
            <div class="flex items-end gap-2 h-40">
              @for (stage of stages; track stage.id) {
                <div class="flex-1 flex flex-col items-center group">
                  <div class="w-full bg-[var(--t-accent-soft)] rounded-t-lg transition-all duration-500 group-hover:bg-[var(--t-accent)]"
                       [style.height.%]="getStagePercentage(stage.id)">
                    <div class="opacity-0 group-hover:opacity-100 transition-opacity bg-[var(--t-surface)] text-[var(--t-text-primary)] text-[10px] font-bold px-2 py-1 rounded shadow-lg -mt-8 mx-auto w-fit">
                      {{ data()?.pipeline_by_stage?.[stage.id] || 0 }}
                    </div>
                  </div>
                  <div class="w-full h-1 bg-[var(--t-border)] mt-2"></div>
                  <p class="text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mt-3">
                    {{ stage.label }}
                  </p>
                </div>
              }
            </div>
          </div>

          <!-- RAG Breakdown -->
          <div class="card p-6">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Health Breakdown (RAG)</h3>
            <div class="flex items-center gap-8">
              <div class="flex-1 space-y-4">
                @for (rag of ['green', 'amber', 'red']; track rag) {
                  <div class="space-y-1">
                    <div class="flex justify-between text-xs">
                      <span class="capitalize font-medium">{{ rag }}</span>
                      <span class="text-[var(--t-text-tertiary)]">{{ data()?.rag_breakdown?.[rag] || 0 }} initiatives</span>
                    </div>
                    <div class="h-2 bg-[var(--t-bg-page)] rounded-full overflow-hidden border border-[var(--t-border)]">
                      <div class="h-full transition-all duration-1000"
                           [style.width.%]="getRagPercentage(rag)"
                           [style.background]="getRagColor(rag)"></div>
                    </div>
                  </div>
                }
              </div>
              <div class="w-32 h-32 rounded-full border-8 border-[var(--t-surface-raised)] flex items-center justify-center relative">
                <div class="text-center">
                  <p class="text-2xl font-bold text-[var(--t-text-primary)]">
                    {{ getHealthScore() }}%
                  </p>
                  <p class="text-[10px] uppercase font-bold text-[var(--t-text-tertiary)]">Healthy</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Right Column: Pressure & Milestones -->
        <div class="space-y-8">
          
          <!-- Pressure Gauge -->
          <div class="card p-6 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]/10">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Portfolio Pressure</h3>
            <div class="relative pt-10 flex flex-col items-center">
               <div class="w-48 h-24 overflow-hidden relative">
                  <div class="w-48 h-48 rounded-full border-[16px] border-[var(--t-border)] absolute top-0 left-0"></div>
                  <div class="w-48 h-48 rounded-full border-[16px] border-[var(--t-accent)] absolute top-0 left-0 transition-all duration-1000"
                       style="clip-path: polygon(0 0, 100% 0, 100% 50%, 0 50%)"
                       [style.transform]="getPressureRotation()"></div>
               </div>
               <div class="text-center -mt-4">
                 <p class="text-3xl font-black text-[var(--t-text-primary)]">
                   {{ (data()?.portfolio_pressure?.score || 0).toFixed(1) }}
                 </p>
                 <p class="text-xs font-bold uppercase tracking-widest"
                    [style.color]="getPressureColor()">
                   {{ data()?.portfolio_pressure?.label }}
                 </p>
               </div>
            </div>
          </div>

          <!-- My Milestones -->
          <div class="card p-6">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-lg font-bold text-[var(--t-text-primary)]">My Milestones</h3>
              <a routerLink="/progress" class="text-xs text-[var(--t-accent)] font-semibold">View all →</a>
            </div>
            <div class="space-y-4">
              @for (m of data()?.my_milestones; track m.id) {
                <div class="p-3 rounded-lg border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] transition-colors cursor-pointer">
                  <p class="text-xs font-bold text-[var(--t-text-primary)] truncate">{{ m.name }}</p>
                  <p class="text-[10px] text-[var(--t-text-secondary)] mt-1 truncate">{{ m.initiative?.name }}</p>
                  <div class="flex justify-between items-center mt-3">
                    <span class="text-[10px] font-mono text-[var(--t-text-tertiary)]">{{ m.planned_end | date:'MMM d' }}</span>
                    <span class="text-[10px] px-2 py-0.5 rounded-full border"
                          [class.text-red-500]="m.status === 'delayed'"
                          [class.border-red-500]="m.status === 'delayed'">
                      {{ m.status | uppercase }}
                    </span>
                  </div>
                </div>
              }
              @if (!data()?.my_milestones?.length) {
                <p class="text-center py-8 text-xs text-[var(--t-text-tertiary)]">No upcoming milestones.</p>
              }
            </div>
          </div>

        </div>

      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
    .animate-pulse-subtle {
      animation: pulse-subtle 3s infinite ease-in-out;
    }
    @keyframes pulse-subtle {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.8; }
    }
  `]
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(ApiService);
  
  data = signal<any>(null);
  stages = [
    { id: 'scoping', label: 'Scoping' },
    { id: 'in_progress', label: 'In-Progress' },
    { id: 'complete', label: 'Complete' }
  ];

  ngOnInit() {
    this.api.get<any>('/dashboard').subscribe(d => this.data.set(d));
  }

  getStagePercentage(stage: string): number {
    const total = this.data()?.summary?.total_initiatives || 1;
    const val = this.data()?.pipeline_by_stage?.[stage] || 0;
    return (val / total) * 100;
  }

  getRagPercentage(rag: string): number {
    const total = this.data()?.summary?.total_initiatives || 1;
    const val = this.data()?.rag_breakdown?.[rag] || 0;
    return (val / total) * 100;
  }

  getRagColor(rag: string): string {
    return rag === 'red' ? 'var(--t-red)' : rag === 'amber' ? 'var(--t-amber)' : 'var(--t-green)';
  }

  getHealthScore(): number {
    const total = this.data()?.summary?.total_initiatives || 0;
    if (total === 0) return 0;
    const red = this.data()?.rag_breakdown?.red || 0;
    return Math.round(((total - red) / total) * 100);
  }

  getPressureRotation(): string {
    const score = this.data()?.portfolio_pressure?.score || 0;
    // 0 to 10 score maps to -180 to 0 degrees rotation (approx)
    const deg = (score / 10) * 180 - 180;
    return `rotate(${deg}deg)`;
  }

  getPressureColor(): string {
    const score = this.data()?.portfolio_pressure?.score || 0;
    if (score < 3.4) return 'var(--t-green)';
    if (score < 6.7) return 'var(--t-amber)';
    return 'var(--t-red)';
  }
}
