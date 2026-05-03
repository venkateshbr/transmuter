import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Premium Hero Section -->
      <section class="relative p-10 rounded-[2.5rem] overflow-hidden bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] text-white shadow-2xl shadow-purple-500/20">
        <!-- Abstract Background Elements -->
        <div class="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
        <div class="absolute bottom-0 left-0 w-64 h-64 bg-black/10 rounded-full blur-2xl -ml-20 -mb-20"></div>
        
        <div class="relative z-10 flex flex-col md:flex-row justify-between items-center gap-8">
          <div class="flex-1">
            <div class="flex items-center gap-2 mb-4">
              <span class="w-2 h-2 rounded-full bg-green-400 animate-pulse"></span>
              <span class="text-[10px] font-black uppercase tracking-[0.2em] opacity-80">Portfolio Live Context</span>
            </div>
            <h1 class="text-4xl font-black tracking-tight leading-tight">
              Operational Excellence <br/>
              & Strategic Yield Dashboard<span class="opacity-50">.</span>
            </h1>
            <p class="text-sm font-medium opacity-80 mt-4 max-w-xl leading-relaxed">
              Real-time synchronization across {{ data()?.summary?.total_initiatives }} strategic workstreams. 
              The current portfolio health score is <span class="font-black text-green-300">{{ getHealthScore() }}%</span> with 
              <span class="font-black text-amber-300">{{ data()?.summary?.pending_approvals }} pending gate decisions</span>.
            </p>
          </div>
          
          <div class="flex-none flex flex-col items-end gap-4">
              <div class="flex gap-2">
                <button (click)="generateReport()" class="px-6 py-3 rounded-2xl bg-white/10 hover:bg-white/20 border border-white/10 text-xs font-black uppercase tracking-widest transition-all">
                  {{ reporting() ? 'Generating...' : 'Generate Report' }}
                </button>
                <button routerLink="/initiatives/new" class="px-6 py-3 rounded-2xl bg-white text-[var(--t-accent)] hover:scale-105 active:scale-95 text-xs font-black uppercase tracking-widest shadow-lg transition-all">
                  + Executive Action
                </button>
              </div>
             <p class="text-[9px] font-bold opacity-60 uppercase tracking-widest mt-2">Last System Sync: Just Now</p>
          </div>
        </div>
      </section>

      <!-- Summary Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <a
          routerLink="/initiatives/pipeline"
          data-testid="dashboard-total-initiatives"
          class="card block p-6 border-l-4 border-[var(--t-accent)] cursor-pointer hover:-translate-y-0.5 hover:border-[var(--t-accent)] hover:shadow-xl transition-all"
          aria-label="Open all initiatives"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Total Initiatives</p>
          <p class="text-3xl font-bold text-[var(--t-text-primary)]">{{ data()?.summary?.total_initiatives || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            <span class="text-green-500">↑ 2</span> from last week
          </p>
        </a>
        <a
          routerLink="/initiatives/pipeline"
          [queryParams]="{ rag_status: 'red' }"
          data-testid="dashboard-at-risk"
          class="card block p-6 border-l-4 border-red-500 cursor-pointer hover:-translate-y-0.5 hover:border-red-500 hover:shadow-xl transition-all"
          aria-label="Open red at-risk initiatives"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">At Risk</p>
          <p class="text-3xl font-bold text-red-500">{{ data()?.summary?.at_risk || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2 flex items-center gap-1">
            Requires immediate attention
          </p>
        </a>
        <a
          routerLink="/pmo/governance"
          [queryParams]="{ status: 'pending' }"
          data-testid="dashboard-pending-approvals"
          class="card block p-6 border-l-4 border-amber-500 cursor-pointer hover:-translate-y-0.5 hover:border-amber-500 hover:shadow-xl transition-all"
          aria-label="Open pending governance approvals"
        >
          <p class="text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)] mb-1">Pending Approvals</p>
          <p class="text-3xl font-bold text-amber-500">{{ data()?.summary?.pending_approvals || 0 }}</p>
          <p class="text-xs text-[var(--t-text-secondary)] mt-2">Gate submissions awaiting review</p>
        </a>
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
                <a
                  routerLink="/initiatives/pipeline"
                  [queryParams]="{ stage: stage.id }"
                  [attr.data-testid]="'dashboard-stage-' + stage.id"
                  class="flex-1 flex flex-col items-center group cursor-pointer rounded-lg hover:bg-[var(--t-surface-raised)]/60 transition-colors"
                  [attr.aria-label]="'Open initiatives in ' + stage.label + ' stage'"
                >
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
                </a>
              }
            </div>
          </div>

          <!-- RAG Breakdown -->
          <div class="card p-6">
            <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Health Breakdown (RAG)</h3>
            <div class="flex items-center gap-8">
              <div class="flex-1 space-y-4">
                @for (rag of ['green', 'amber', 'red']; track rag) {
                  <a
                    routerLink="/initiatives/pipeline"
                    [queryParams]="{ rag_status: rag }"
                    [attr.data-testid]="'dashboard-rag-' + rag"
                    class="block space-y-1 rounded-lg p-2 -mx-2 cursor-pointer hover:bg-[var(--t-surface-raised)] transition-colors"
                    [attr.aria-label]="'Open ' + rag + ' initiatives'"
                  >
                    <div class="flex justify-between text-xs">
                      <span class="capitalize font-medium">{{ rag }}</span>
                      <span class="text-[var(--t-text-tertiary)]">{{ data()?.rag_breakdown?.[rag] || 0 }} initiatives</span>
                    </div>
                    <div class="h-2 bg-[var(--t-bg-page)] rounded-full overflow-hidden border border-[var(--t-border)]">
                      <div class="h-full transition-all duration-1000"
                           [style.width.%]="getRagPercentage(rag)"
                           [style.background]="getRagColor(rag)"></div>
                    </div>
                  </a>
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
          <a
            routerLink="/progress"
            data-testid="dashboard-pressure"
            class="card block p-6 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]/10 cursor-pointer hover:-translate-y-0.5 hover:border-[var(--t-accent)] hover:shadow-xl transition-all"
            aria-label="Open milestone tracker"
          >
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
          </a>

          <!-- My Milestones -->
          <div class="card p-6">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-lg font-bold text-[var(--t-text-primary)]">My Milestones</h3>
              <a routerLink="/progress" class="text-xs text-[var(--t-accent)] font-semibold">View all →</a>
            </div>
            <div class="space-y-4">
              @for (m of data()?.my_milestones; track m.id) {
                <a
                  [routerLink]="['/initiatives', m.initiative_id]"
                  [attr.data-testid]="'dashboard-milestone-' + m.id"
                  class="block p-3 rounded-lg border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)] hover:border-[var(--t-accent)] transition-colors cursor-pointer"
                  [attr.aria-label]="'Open initiative for milestone ' + m.name"
                >
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
                </a>
              }
              @if (!data()?.my_milestones?.length) {
                <p class="text-center py-8 text-xs text-[var(--t-text-tertiary)]">No upcoming milestones.</p>
              }
            </div>
          </div>

        </div>

      </div>

    </div>

    <!-- Onboarding / Welcome Modal -->
    @if (showWelcome()) {
      <div class="overlay flex items-center justify-center p-6 bg-black/40 backdrop-blur-md">
        <div class="card max-w-2xl w-full p-0 overflow-hidden shadow-2xl animate-scale-in">
           <div class="h-48 bg-gradient-to-br from-[var(--t-accent)] to-[#a855f7] p-10 relative overflow-hidden">
              <div class="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -mr-20 -mt-20"></div>
              <div class="relative z-10">
                 <h2 class="text-3xl font-black text-white leading-tight">Welcome to <br/>Transmuter Platform<span class="opacity-50">.</span></h2>
                 <p class="text-white/70 text-xs font-bold uppercase tracking-widest mt-2">Executive Onboarding (May 2026 Release)</p>
              </div>
           </div>
           <div class="p-10 space-y-8 bg-[var(--t-surface)]">
              <div class="grid grid-cols-2 gap-6">
                 <div class="flex gap-4">
                    <div class="w-10 h-10 rounded-xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] shrink-0">
                       <span class="material-icons">dashboard</span>
                    </div>
                    <div>
                       <p class="text-sm font-black text-[var(--t-text-primary)]">Strategic Dashboard</p>
                       <p class="text-[10px] text-[var(--t-text-secondary)] mt-0.5">Real-time health & pressure scores.</p>
                    </div>
                 </div>
                 <div class="flex gap-4">
                    <div class="w-10 h-10 rounded-xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)] shrink-0">
                       <span class="material-icons">psychology</span>
                    </div>
                    <div>
                       <p class="text-sm font-black text-[var(--t-text-primary)]">AI Assistant</p>
                       <p class="text-[10px] text-[var(--t-text-secondary)] mt-0.5">Natural language portfolio queries.</p>
                    </div>
                 </div>
              </div>
              <p class="text-sm text-[var(--t-text-secondary)] leading-relaxed">
                 You are logged in as the **Transformation Office Administrator**. You have full visibility across 4 workstreams and 24 strategic initiatives. 
              </p>
              <div class="flex gap-4 pt-4">
                 <button (click)="showWelcome.set(false)" class="flex-1 btn-primary py-4 rounded-2xl shadow-xl shadow-purple-500/20 font-black uppercase text-[10px] tracking-widest">Enter Command Center</button>
                 <button (click)="showWelcome.set(false)" class="px-8 py-4 rounded-2xl border border-[var(--t-border)] font-black uppercase text-[10px] tracking-widest hover:bg-[var(--t-surface-raised)] transition-all">Quick Tour</button>
              </div>
           </div>
        </div>
      </div>
    }
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
  reporting = signal(false);
  showWelcome = signal(true);
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

  generateReport() {
    if (this.reporting()) return;
    this.reporting.set(true);
    
    // Simulate high-fidelity report generation
    setTimeout(() => {
      this.reporting.set(false);
      alert('Portfolio Executive Briefing (Q2 2026) has been generated and is ready for review.');
    }, 2500);
  }
}
