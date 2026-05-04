import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-kpis',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Performance Engine<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Real-time value realization tracking across strategic portfolio pillars.</p>
        </div>
        <div class="flex gap-3">
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="material-icons text-xs">trending_up</span>
            <span class="text-[10px] font-black uppercase tracking-widest">{{ pulse()?.health_score }}% PORTFOLIO EFFICIENCY</span>
          </div>
          <button class="btn-primary text-sm flex items-center gap-2 h-10">
            <span>+</span> Define Metric
          </button>
        </div>
      </div>

      <!-- High-Fidelity KPI Pulse -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" *ngIf="pulse()">
        
        <div class="card p-8 bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]/20 border-l-4 border-[var(--t-accent)]">
          <div class="flex justify-between items-start mb-6">
            <span class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Global Reach</span>
            <span class="material-icons text-[var(--t-accent)] text-xl">language</span>
          </div>
          <p class="text-3xl font-black text-[var(--t-text-primary)]">{{ pulse()?.total_kpis }}</p>
          <p class="text-[10px] font-bold text-[var(--t-text-secondary)] uppercase mt-2">Active Strategic Metrics</p>
        </div>

        <div class="card p-8 border-l-4 border-green-500">
          <div class="flex justify-between items-start mb-6">
            <span class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Base Target Hit</span>
            <span class="material-icons text-green-500 text-xl">check_circle</span>
          </div>
          <p class="text-3xl font-black text-green-500">{{ pulse()?.hitting_base }}</p>
          <p class="text-[10px] font-bold text-[var(--t-text-secondary)] uppercase mt-2">Performing Above Threshold</p>
        </div>

        <div class="card p-8 border-l-4 border-red-500">
          <div class="flex justify-between items-start mb-6">
            <span class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Variance Alert</span>
            <span class="material-icons text-red-500 text-xl">warning</span>
          </div>
          <p class="text-3xl font-black text-red-500">{{ pulse()?.missing_base }}</p>
          <p class="text-[10px] font-bold text-[var(--t-text-secondary)] uppercase mt-2">Metrics Underperforming</p>
        </div>

        <div class="card p-8 bg-gradient-to-br from-[var(--t-accent)] to-[var(--t-blue-light)] text-white border-none shadow-xl shadow-blue-900/10">
          <div class="flex justify-between items-start mb-6">
            <span class="text-[10px] font-black opacity-70 uppercase tracking-widest">Value Score</span>
            <span class="material-icons opacity-70 text-xl">insights</span>
          </div>
          <p class="text-3xl font-black">{{ pulse()?.health_score }}%</p>
          <p class="text-[10px] font-bold opacity-70 uppercase mt-2">Realized Portfolio Yield</p>
        </div>
      </div>

      <!-- KPI Grid: The "Metric Wall" -->
      <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        @for (kpi of filteredKpis(); track kpi.id) {
          <div class="card p-6 flex flex-col gap-6 hover:border-[var(--t-accent)] hover:shadow-2xl transition-all group relative overflow-hidden">
            
            <!-- Background Glow on Hover -->
            <div class="absolute -right-8 -top-8 w-32 h-32 bg-[var(--t-accent)]/5 rounded-full blur-3xl opacity-0 group-hover:opacity-100 transition-opacity"></div>

            <div class="flex justify-between items-start">
               <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-[8px] font-black px-1.5 py-0.5 rounded bg-[var(--t-surface-raised)] text-[var(--t-text-tertiary)] uppercase">
                      {{ kpi.type }}
                    </span>
                    <span class="text-[8px] font-black text-[var(--t-accent)] uppercase tracking-widest">{{ kpi.frequency }}</span>
                  </div>
                  <h3 class="text-sm font-black text-[var(--t-text-primary)] truncate group-hover:text-[var(--t-accent)] transition-colors">
                    {{ kpi.name }}
                  </h3>
               </div>
               <div class="flex flex-col items-end">
                  @if (getLatestEntry(kpi); as latest) {
                    <span class="text-lg font-black" [style.color]="getStatusColor(kpi)">
                      {{ latest.value_actual }}<small class="ml-1 text-[10px] opacity-70">{{ kpi.unit }}</small>
                    </span>
                    <div class="flex items-center gap-1">
                       <span class="material-icons text-[10px]" [style.color]="getStatusColor(kpi)">
                         {{ parseFloat(latest.value_actual) >= parseFloat(latest.value_base || '0') ? 'north_east' : 'south_east' }}
                       </span>
                       <span class="text-[8px] font-bold text-[var(--t-text-tertiary)] uppercase">vs {{ latest.value_base }}</span>
                    </div>
                  }
               </div>
            </div>

            <!-- Mini Sparkline Placeholder -->
            <div class="h-16 flex items-end gap-1 px-2">
               @for (i of [1,2,3,4,5,6,7,8,9,10]; track i) {
                 <div class="flex-1 rounded-t-sm transition-all duration-500 bg-[var(--t-surface-raised)] group-hover:bg-[var(--t-accent-soft)]"
                      [style.height.%]="20 + (i * 7) % 80"></div>
               }
            </div>

            <div class="flex justify-between items-center pt-4 border-t border-[var(--t-border)]/50">
               <div class="flex items-center gap-2">
                  <span class="text-[9px] font-black text-[var(--t-text-tertiary)] uppercase">Initiative</span>
                  <span class="text-[9px] font-black text-[var(--t-text-secondary)]">{{ kpi.initiative_code || 'PORTFOLIO' }}</span>
               </div>
               <button class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] hover:bg-[var(--t-accent-soft)] transition-all">
                 <span class="material-icons text-xs">open_in_new</span>
               </button>
            </div>
          </div>
        }

        @if (filteredKpis().length === 0) {
           <div class="col-span-full py-24 text-center border-2 border-dashed border-[var(--t-border)] rounded-[2rem] opacity-50">
              <span class="material-icons text-4xl mb-2 text-[var(--t-text-tertiary)]">analytics</span>
              <p class="text-sm font-black uppercase tracking-widest">No Performance Data</p>
              <p class="text-xs font-bold text-[var(--t-text-tertiary)] mt-1">Configure your first KPI to begin tracking value.</p>
           </div>
        }
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class KPIsComponent implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly parseFloat = parseFloat;
  
  kpis = signal<any[]>([]);
  pulse = signal<any | null>(null);
  searchQuery = '';

  filteredKpis = computed(() => {
    const query = this.searchQuery.toLowerCase();
    if (!query) return this.kpis();
    return this.kpis().filter(k => 
      k.name.toLowerCase().includes(query) || 
      (k.initiative_code && k.initiative_code.toLowerCase().includes(query))
    );
  });

  ngOnInit() {
    this.loadPulse();
    this.loadKpis();
  }

  loadPulse() {
    this.api.get<any>('/portfolio/kpi-pulse').subscribe(res => {
      this.pulse.set(res);
    });
  }

  loadKpis() {
    this.api.get<any>('/portfolio/kpis').subscribe(res => {
      this.kpis.set(res.items || []);
    });
  }

  getLatestEntry(kpi: any) {
    if (!kpi.entries || kpi.entries.length === 0) return null;
    return kpi.entries[kpi.entries.length - 1];
  }

  getStatusColor(kpi: any): string {
    const latest = this.getLatestEntry(kpi);
    if (!latest || !latest.value_actual) return 'var(--t-text-tertiary)';
    
    const actual = parseFloat(latest.value_actual);
    const base = parseFloat(latest.value_base || '0');
    
    if (actual >= base) return '#22c55e'; // Green-500
    return '#ef4444'; // Red-500
  }

  getStatusText(kpi: any): string {
    const latest = this.getLatestEntry(kpi);
    if (!latest || !latest.value_actual) return 'Pending';
    
    const actual = parseFloat(latest.value_actual);
    const base = parseFloat(latest.value_base || '0');
    
    return actual >= base ? 'On Track' : 'Off Track';
  }
}
