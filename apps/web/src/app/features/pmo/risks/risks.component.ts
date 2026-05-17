import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-risks',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Risk Intel Center<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Strategic risk monitoring, probability modeling, and mitigation tracking.</p>
        </div>
        <div class="flex gap-3 items-center">
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="material-icons text-xs">shield</span>
            <span class="text-[10px] font-black uppercase tracking-widest">{{ risks().length }} ACTIVE THREATS</span>
          </div>
          <button class="btn-primary text-sm flex items-center gap-2 h-10">
            <span>+</span> Capture Risk
          </button>
        </div>
      </div>

      <!-- Risk Summary & Heatmap -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Premium Heatmap -->
        <div class="lg:col-span-2 card p-8 flex flex-col">
          <div class="flex justify-between items-center mb-8">
            <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)] flex items-center gap-2">
              <span class="material-icons text-sm">grid_view</span>
              Strategic Risk Matrix
            </h3>
            <div class="flex gap-4">
               <div class="flex items-center gap-2">
                 <span class="w-2 h-2 rounded-full bg-red-500"></span>
                 <span class="text-[9px] font-bold text-[var(--t-text-tertiary)] uppercase">Critical</span>
               </div>
               <div class="flex items-center gap-2">
                 <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                 <span class="text-[9px] font-bold text-[var(--t-text-tertiary)] uppercase">Elevated</span>
               </div>
            </div>
          </div>
          
          <div class="flex-1 grid grid-cols-[3rem_1fr] grid-rows-[1fr_3rem] gap-4">
            <!-- Y-Axis Label -->
            <div class="flex flex-col justify-between py-8 text-[9px] font-black text-[var(--t-text-tertiary)] uppercase [writing-mode:vertical-lr] rotate-180 items-center gap-2">
               <span>High Impact</span>
               <div class="flex-1 w-px bg-gradient-to-b from-[var(--t-border)] to-transparent"></div>
               <span>Low</span>
            </div>
            
            <!-- Matrix Grid -->
            <div class="grid grid-cols-3 grid-rows-3 gap-3">
               @for (imp of impactLevels; track imp) {
                 @for (lik of likelihoodLevels; track lik) {
                   <div class="rounded-2xl flex flex-col items-center justify-center transition-all hover:scale-[1.03] active:scale-95 cursor-pointer border border-white/5 shadow-inner group relative"
                        [style.background]="getHeatmapColor(imp, lik)">
                     <span class="text-2xl font-black text-white drop-shadow-md group-hover:scale-125 transition-transform">
                       {{ getRiskCount(imp, lik) }}
                     </span>
                     <div class="absolute inset-0 bg-white/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-2xl"></div>
                   </div>
                 }
               }
            </div>
            
            <!-- X-Axis Label -->
            <div class="col-start-2 flex justify-between px-8 text-[9px] font-black text-[var(--t-text-tertiary)] uppercase items-center gap-2">
               <span>Low Likelihood</span>
               <div class="flex-1 h-px bg-gradient-to-r from-transparent via-[var(--t-border)] to-transparent"></div>
               <span>High</span>
            </div>
          </div>
        </div>

        <!-- Risk Distribution -->
        <div class="card p-8 flex flex-col gap-8">
           <h3 class="text-xs font-black uppercase tracking-widest text-[var(--t-text-tertiary)] flex items-center gap-2">
             <span class="material-icons text-sm">pie_chart</span>
             Risk Exposure by Type
           </h3>
           <div class="space-y-6">
              @for (type of riskTypes; track type) {
                <div class="space-y-2">
                  <div class="flex justify-between items-end">
                    <span class="text-[10px] font-black uppercase tracking-tight text-[var(--t-text-primary)]">
                      {{ type.replace('_', ' ') }}
                    </span>
                    <span class="text-[10px] font-mono text-[var(--t-accent)] font-black">
                      {{ getTypeCount(type) }} EXPOSURES
                    </span>
                  </div>
                  <div class="h-1.5 bg-[var(--t-surface-raised)] rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-[var(--t-accent)] to-[var(--t-blue-light)] transition-all duration-1000" 
                         [style.width.%]="getTypePercentage(type)"></div>
                  </div>
                </div>
              }
           </div>
           
           <div class="mt-auto p-4 rounded-2xl bg-[var(--t-accent-soft)] border border-[var(--t-accent)]/10">
              <div class="flex items-center gap-2 mb-2">
                 <span class="material-icons text-xs text-[var(--t-accent)]">info</span>
                 <span class="text-[9px] font-black uppercase text-[var(--t-accent)]">Risk Posture</span>
              </div>
              <p class="text-[10px] font-medium leading-relaxed text-[var(--t-text-primary)]">
                Financial risks represent 42% of the total portfolio exposure. Mitigation priority: **Critical**.
              </p>
           </div>
        </div>
      </div>

      <!-- Risk Registry List -->
      <div class="grid grid-cols-1 gap-4">
        @for (r of filteredRisks(); track r.id) {
          <div class="card p-6 flex items-center gap-8 hover:border-[var(--t-accent)] hover:shadow-xl transition-all group">
            
            <!-- Severity Indicator -->
            <div class="flex-none w-1 h-12 rounded-full" 
                 [style.background]="getRatingFg(r.rating)"></div>

            <div class="flex-1 min-w-0">
               <div class="flex items-center gap-3 mb-1">
                 <span class="text-[9px] font-black uppercase tracking-widest" [style.color]="getRatingFg(r.rating)">
                   {{ r.rating }} Priority
                 </span>
                 <span class="w-1 h-1 rounded-full bg-[var(--t-border)]"></span>
                 <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">{{ (r.type || 'N/A').replace('_', ' ') }}</span>
               </div>
               <h3 class="text-sm font-black text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors truncate">
                 {{ r.description }}
               </h3>
               <p class="text-[10px] text-[var(--t-text-tertiary)] mt-1 flex items-center gap-2">
                 <span class="material-icons text-xs">rocket_launch</span>
                 {{ r.initiative_name || 'Portfolio-wide Risk' }}
               </p>
            </div>

            <div class="flex-none flex items-center gap-8">
               <div class="flex flex-col items-end gap-1">
                 <span class="text-[8px] font-black uppercase text-[var(--t-text-tertiary)]">Risk Owner</span>
                 <div class="flex items-center gap-2">
                    <div class="w-6 h-6 rounded-full bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex items-center justify-center text-[10px] font-black">
                      {{ (r.owner_name || 'U').substring(0,1) }}
                    </div>
                    <span class="text-xs font-bold text-[var(--t-text-primary)]">{{ r.owner_name || 'Unassigned' }}</span>
                 </div>
               </div>
               
               <button class="w-10 h-10 rounded-xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] hover:border-[var(--t-accent)] transition-all">
                 <span class="material-icons text-sm">chevron_right</span>
               </button>
            </div>
          </div>
        }
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class RisksComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);
  
  risks = signal<any[]>([]);
  filteredRisks = signal<any[]>([]);
  heatmap = signal<any[]>([]);
  
  statusFilter = 'open';
  impactFilter = '';
  likelihoodFilter = '';
  riskTypes = ['operational', 'people', 'financial', 'technology'];
  impactLevels = ['high', 'medium', 'low'];
  likelihoodLevels = ['low', 'medium', 'high'];

  ngOnInit() {
    this.route.queryParamMap.subscribe(params => {
      this.impactFilter = params.get('impact') || '';
      this.likelihoodFilter = params.get('likelihood') || '';
      this.loadRisks();
      this.loadHeatmap();
    });
  }

  loadRisks() {
    this.api.get<any>('/portfolio/risks', { status: this.statusFilter }).subscribe(res => {
      const items = res.items || [];
      this.risks.set(items);
      this.filteredRisks.set(
        items.filter((risk: any) =>
          (!this.impactFilter || risk.impact === this.impactFilter)
          && (!this.likelihoodFilter || risk.likelihood === this.likelihoodFilter)
        )
      );
    });
  }

  loadHeatmap() {
    this.api.get<any>('/portfolio/risks/heatmap').subscribe(res => {
      this.heatmap.set(res.cells || []);
    });
  }

  applyFilters() {
    this.loadRisks();
  }

  getRiskCount(impact: string, likelihood: string): number {
    const cell = this.heatmap().find(c => c.impact === impact && c.likelihood === likelihood);
    return cell ? cell.count : 0;
  }

  getHeatmapColor(impact: string, likelihood: string): string {
    const i = impact === 'high' ? 3 : (impact === 'medium' ? 2 : 1);
    const l = likelihood === 'high' ? 3 : (likelihood === 'medium' ? 2 : 1);
    const score = i * l;
    if (score >= 6) return 'rgba(239, 68, 68, 0.8)'; // Red
    if (score >= 4) return 'rgba(245, 158, 11, 0.8)'; // Amber
    return 'rgba(34, 197, 94, 0.8)'; // Green
  }

  getHeatmapTextColor(impact: string, likelihood: string): string {
    return '#fff';
  }

  getTypeCount(type: string): number {
    return this.risks().filter(r => r.type === type).length;
  }

  getTypePercentage(type: string): number {
    if (this.risks().length === 0) return 0;
    return (this.getTypeCount(type) / this.risks().length) * 100;
  }

  getRatingBg(rating: string): string {
    switch (rating) {
      case 'high': return 'rgba(239, 68, 68, 0.1)';
      case 'medium': return 'rgba(245, 158, 11, 0.1)';
      case 'low': return 'rgba(34, 197, 94, 0.1)';
      default: return 'var(--t-surface-raised)';
    }
  }

  getRatingFg(rating: string): string {
    switch (rating) {
      case 'high': return '#ef4444';
      case 'medium': return '#f59e0b';
      case 'low': return '#22c55e';
      default: return 'var(--t-text-tertiary)';
    }
  }
}
