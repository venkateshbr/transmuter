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
            Performance KPIs<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Real-time tracking of portfolio health and value realization.</p>
        </div>
        <div class="flex gap-2">
          <button class="btn-ghost text-sm">Download Report</button>
          <button class="btn-primary text-sm flex items-center gap-2">
            <span>+</span> Configure KPI
          </button>
        </div>
      </div>

      <!-- Pulse Cards -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6" *ngIf="pulse()">
        <div class="card p-6 flex flex-col justify-between group hover:border-[var(--t-accent)] transition-all">
          <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">Total Metrics</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-4xl font-black text-[var(--t-text-primary)]">{{ pulse()?.total_kpis }}</span>
          </div>
          <div class="mt-4 h-1 bg-[var(--t-surface-raised)] rounded-full overflow-hidden">
            <div class="h-full bg-[var(--t-accent)]" style="width: 100%"></div>
          </div>
        </div>

        <div class="card p-6 flex flex-col justify-between group hover:border-green-500/50 transition-all">
          <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">On Track</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-4xl font-black text-green-500">{{ pulse()?.hitting_base }}</span>
            <span class="text-xs text-[var(--t-text-tertiary)]">KPIs</span>
          </div>
          <div class="mt-4 h-1 bg-[var(--t-surface-raised)] rounded-full overflow-hidden">
            <div class="h-full bg-green-500" [style.width.%]="(pulse()?.hitting_base || 0) / (pulse()?.total_kpis || 1) * 100"></div>
          </div>
        </div>

        <div class="card p-6 flex flex-col justify-between group hover:border-red-500/50 transition-all">
          <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">Off Track</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-4xl font-black text-red-500">{{ pulse()?.missing_base }}</span>
            <span class="text-xs text-[var(--t-text-tertiary)]">KPIs</span>
          </div>
          <div class="mt-4 h-1 bg-[var(--t-surface-raised)] rounded-full overflow-hidden">
            <div class="h-full bg-red-500" [style.width.%]="(pulse()?.missing_base || 0) / (pulse()?.total_kpis || 1) * 100"></div>
          </div>
        </div>

        <div class="card p-6 flex flex-col justify-between bg-[var(--t-accent)] text-white border-none shadow-[0_10px_40px_rgba(124,58,237,0.3)]">
          <span class="text-[10px] font-bold opacity-80 uppercase tracking-widest">Health Score</span>
          <div class="flex items-baseline gap-2 mt-2">
            <span class="text-4xl font-black">{{ pulse()?.health_score }}%</span>
          </div>
          <p class="text-[10px] font-medium opacity-80 mt-4 leading-tight">Average performance across all tracked value levers.</p>
        </div>
      </div>

      <!-- KPI List -->
      <div class="card overflow-hidden">
        <div class="px-6 py-4 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] flex justify-between items-center">
          <h3 class="text-sm font-bold text-[var(--t-text-primary)] uppercase tracking-widest">Global Metrics Registry</h3>
          <div class="flex gap-4">
            <input type="text" placeholder="Search KPIs..." 
                   class="bg-transparent border-b border-[var(--t-border)] text-xs py-1 focus:border-[var(--t-accent)] outline-none text-[var(--t-text-primary)]"
                   [(ngModel)]="searchQuery">
          </div>
        </div>
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="border-b border-[var(--t-border)]">
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Metric</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Frequency</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Latest Actual</th>
              <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</th>
              <th class="px-6 py-4"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[var(--t-border)]">
            @for (kpi of filteredKpis(); track kpi.id) {
              <tr class="hover:bg-[var(--t-surface-raised)] transition-colors group">
                <td class="px-6 py-4">
                  <div class="flex flex-col">
                    <span class="text-sm font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">{{ kpi.name }}</span>
                    <span class="text-[10px] text-[var(--t-text-tertiary)] mt-0.5 uppercase tracking-tighter">{{ kpi.type }}</span>
                  </div>
                </td>
                <td class="px-6 py-4">
                  <span class="text-xs text-[var(--t-text-secondary)]">{{ kpi.initiative_code || 'Portfolio' }}</span>
                </td>
                <td class="px-6 py-4">
                  <span class="text-[10px] font-bold uppercase text-[var(--t-text-tertiary)]">{{ kpi.frequency }}</span>
                </td>
                <td class="px-6 py-4">
                  <div class="flex flex-col">
                    @if (getLatestEntry(kpi); as latest) {
                      <span class="text-sm font-black text-[var(--t-text-primary)]">{{ latest.value_actual || '-' }} {{ kpi.unit }}</span>
                      <span class="text-[10px] text-[var(--t-text-tertiary)]">Base: {{ latest.value_base }}</span>
                    } @else {
                      <span class="text-[var(--t-text-tertiary)] italic text-xs">No entries</span>
                    }
                  </div>
                </td>
                <td class="px-6 py-4">
                  <div class="flex items-center gap-2">
                    <div class="w-2 h-2 rounded-full" [style.background]="getStatusColor(kpi)"></div>
                    <span class="text-[10px] font-bold uppercase tracking-widest" [style.color]="getStatusColor(kpi)">
                      {{ getStatusText(kpi) }}
                    </span>
                  </div>
                </td>
                <td class="px-6 py-4 text-right">
                  <button class="text-[var(--t-text-tertiary)] hover:text-[var(--t-accent)] transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12c0 1.2-4.03 6-9 6s-9-4.8-9-6c0-1.2 4.03-6 9-6s9 4.8 9 6Z"/><circle cx="12" cy="12" r="3"/></svg>
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
export class KPIsComponent implements OnInit {
  private readonly api = inject(ApiService);
  
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
