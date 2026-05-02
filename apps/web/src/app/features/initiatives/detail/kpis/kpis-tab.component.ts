import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-kpis-tab',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="space-y-6">
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-xl font-semibold text-[var(--t-text-primary)]">Key Performance Indicators</h2>
        <button class="btn-primary">Add KPI</button>
      </div>

      <div *ngIf="loading()" class="text-center p-8 text-[var(--t-text-secondary)]">Loading KPIs...</div>

      <div *ngIf="!loading() && kpis().length === 0" class="card text-center py-12">
        <div class="text-[var(--t-text-secondary)]">No KPIs defined for this initiative.</div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div *ngFor="let kpi of kpis()" class="card glass-panel hover-card">
          <div class="flex justify-between items-start mb-4">
            <div>
              <h3 class="font-medium text-lg text-[var(--t-text-primary)]">{{ kpi.name }}</h3>
              <div class="text-sm text-[var(--t-text-secondary)] mt-1 flex gap-2">
                <span class="badge badge-purple">{{ kpi.type }}</span>
                <span class="badge">{{ kpi.frequency }}</span>
              </div>
            </div>
            <button class="text-[var(--t-text-secondary)] hover:text-[var(--t-primary)]">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
            </button>
          </div>
          
          <div class="mt-4">
            <h4 class="text-xs font-semibold text-[var(--t-text-tertiary)] uppercase tracking-wider mb-2">Targets vs Actuals</h4>
            <div class="space-y-2">
              <div *ngFor="let entry of kpi.entries" class="flex justify-between items-center text-sm p-2 bg-[var(--t-bg-card)] rounded-md border border-[var(--t-border)]">
                <span class="text-[var(--t-text-secondary)] font-medium">{{ entry.year }} Q{{ entry.quarter }}</span>
                <div class="flex items-center gap-4">
                  <div class="text-right">
                    <div class="text-xs text-[var(--t-text-tertiary)]">Target</div>
                    <div class="font-medium">{{ entry.value_base || '-' }} {{kpi.unit}}</div>
                  </div>
                  <div class="text-right">
                    <div class="text-xs text-[var(--t-text-tertiary)]">Actual</div>
                    <div class="font-medium" [class.text-green-500]="isHitting(entry)" [class.text-red-500]="isMissing(entry)">
                      {{ entry.value_actual || '-' }} {{kpi.unit}}
                    </div>
                  </div>
                </div>
              </div>
              <div *ngIf="kpi.entries.length === 0" class="text-sm text-[var(--t-text-tertiary)] italic">
                No tracking entries yet.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  `
})
export class KpisTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  kpis = signal<any[]>([]);
  loading = signal(true);

  ngOnInit() {
    this.fetchKpis();
  }

  fetchKpis() {
    this.loading.set(true);
    this.api.get<any>(`/initiatives/${this.initiativeId}/kpis`).subscribe({
      next: (data) => {
        this.kpis.set(data.items || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  isHitting(entry: any): boolean {
    if (!entry.value_actual || !entry.value_base) return false;
    return parseFloat(entry.value_actual) >= parseFloat(entry.value_base);
  }
  
  isMissing(entry: any): boolean {
    if (!entry.value_actual || !entry.value_base) return false;
    return parseFloat(entry.value_actual) < parseFloat(entry.value_base);
  }
}
