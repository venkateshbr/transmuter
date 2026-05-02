import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';

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
            Risk Register<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Portfolio-wide risk monitoring and mitigation tracking.</p>
        </div>
        <div class="flex gap-2">
          <button class="btn-ghost text-sm">Export CSV ↗</button>
          <button class="btn-primary text-sm flex items-center gap-2">
            <span>+</span> Log Risk
          </button>
        </div>
      </div>

      <!-- Top Section: Heatmap & Stats -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Heatmap -->
        <div class="lg:col-span-2 card p-6">
          <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Risk Heatmap</h3>
          <div class="grid grid-cols-4 gap-2 aspect-video lg:aspect-auto lg:h-64">
            <!-- Labels -->
            <div class="col-start-1 flex flex-col justify-between py-2 text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase text-right pr-4">
              <span>High Impact</span>
              <span>Medium</span>
              <span>Low</span>
            </div>
            <!-- Grid -->
            <div class="col-span-3 grid grid-cols-3 grid-rows-3 gap-2">
               @for (imp of impactLevels; track imp) {
                 @for (lik of likelihoodLevels; track lik) {
                   <div class="rounded-lg flex items-center justify-center text-sm font-black transition-all hover:scale-105 cursor-pointer"
                        [style.background]="getHeatmapColor(imp, lik)"
                        [style.color]="getHeatmapTextColor(imp, lik)">
                     {{ getRiskCount(imp, lik) }}
                   </div>
                 }
               }
            </div>
            <!-- Bottom Labels -->
            <div class="col-start-2 col-span-3 flex justify-between px-4 mt-2 text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">
               <span>Low Likelihood</span>
               <span>Medium</span>
               <span>High</span>
            </div>
          </div>
        </div>

        <!-- Risk Type Breakdown -->
        <div class="card p-6">
          <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Risk Type</h3>
          <div class="space-y-4">
            @for (type of riskTypes; track type) {
              <div class="space-y-1">
                <div class="flex justify-between text-xs">
                  <span class="capitalize font-medium">{{ type.replace('_', ' ') }}</span>
                  <span class="text-[var(--t-text-tertiary)]">{{ getTypeCount(type) }}</span>
                </div>
                <div class="h-2 bg-[var(--t-surface-raised)] rounded-full overflow-hidden">
                  <div class="h-full bg-[var(--t-accent)]" [style.width.%]="getTypePercentage(type)"></div>
                </div>
              </div>
            }
          </div>
        </div>
      </div>

      <!-- Risk List -->
      <div class="card overflow-hidden">
        <div class="px-6 py-4 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] flex justify-between items-center">
          <h3 class="text-sm font-bold text-[var(--t-text-primary)] uppercase tracking-widest">Active Risks</h3>
          <div class="flex gap-4">
            <select [(ngModel)]="statusFilter" (change)="applyFilters()" class="bg-transparent text-xs font-bold text-[var(--t-text-secondary)] outline-none border-none cursor-pointer">
              <option value="">All Status</option>
              <option value="open">Open</option>
              <option value="mitigated">Mitigated</option>
              <option value="closed">Closed</option>
            </select>
          </div>
        </div>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-[var(--t-border)]">
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Risk Description</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Rating</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Owner</th>
              <th class="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--t-border)]">
            @for (r of filteredRisks(); track r.id) {
              <tr class="hover:bg-[var(--t-surface-raised)] transition-colors group">
                <td class="px-6 py-4">
                  <div class="flex flex-col">
                    <span class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors line-clamp-1">{{ r.description }}</span>
                    <span class="text-[10px] text-[var(--t-text-tertiary)] mt-0.5">{{ (r.type || 'N/A').replace('_', ' ') | uppercase }}</span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs text-[var(--t-text-secondary)]">{{ r.initiative_name || 'N/A' }}</span>
                </td>
                <td class="px-6 py-4">
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-full"
                        [style.background]="getRatingBg(r.rating)"
                        [style.color]="getRatingFg(r.rating)">
                    {{ r.rating | uppercase }}
                  </span>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs text-[var(--t-text-secondary)]">{{ r.owner_name || 'Unassigned' }}</span>
                </td>
                <td class="px-6 py-4 text-right">
                  <button class="text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                  </button>
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class RisksComponent implements OnInit {
  private readonly api = inject(ApiService);
  
  risks = signal<any[]>([]);
  filteredRisks = signal<any[]>([]);
  heatmap = signal<any[]>([]);
  
  statusFilter = 'open';
  riskTypes = ['operational', 'people', 'financial', 'technology'];
  impactLevels = ['high', 'medium', 'low'];
  likelihoodLevels = ['low', 'medium', 'high'];

  ngOnInit() {
    this.loadRisks();
    this.loadHeatmap();
  }

  loadRisks() {
    this.api.get<any>('/portfolio/risks', { status: this.statusFilter }).subscribe(res => {
      this.risks.set(res.items || []);
      this.filteredRisks.set(res.items || []);
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
