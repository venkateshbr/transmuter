import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-kpis-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Key Performance Indicators<span class="text-[var(--t-accent)]">.</span></h2>
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">Track strategic metrics and targets</p>
        </div>
        <button class="btn-primary flex items-center gap-2" (click)="onOpenAddModal()">
          <span class="material-icons text-sm">add</span>
          Add KPI
        </button>
      </div>

      @if (loading()) {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          @for (i of [1,2,3,4]; track i) {
            <div class="card animate-pulse h-48 bg-[var(--t-surface-raised)]"></div>
          }
        </div>
      }

      @if (!loading() && kpis().length === 0) {
        <div class="card text-center py-20 opacity-75">
          <div class="w-16 h-16 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center mx-auto mb-4">
             <span class="material-icons text-3xl" style="color:var(--t-text-secondary)">insights</span>
          </div>
          <h3 class="text-lg font-bold">No KPIs defined yet</h3>
          <p class="text-sm text-[var(--t-text-secondary)] mt-1">Add key metrics to monitor the success of this initiative.</p>
          <button class="btn-secondary text-xs mt-6" (click)="onOpenAddModal()">+ Add First KPI</button>
        </div>
      }

      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        @for (kpi of kpis(); track kpi.id) {
          <div class="card p-0 overflow-hidden flex flex-col">
            <!-- Card Header -->
            <div class="p-5 border-b" style="border-color:var(--t-border)">
              <div class="flex justify-between items-start mb-2">
                <div class="flex-1 min-w-0">
                  <h3 class="font-bold text-lg text-[var(--t-text-primary)] truncate">{{ kpi.name }}</h3>
                  <div class="flex items-center gap-2 mt-1">
                    <span class="badge-purple text-[10px] font-bold uppercase tracking-wider">{{ kpi.type }}</span>
                    <span class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">{{ kpi.frequency }}</span>
                  </div>
                </div>
                <div class="flex gap-1">
                   <button class="btn-ghost p-1.5" title="Edit KPI" aria-label="Edit KPI" (click)="onOpenEditModal(kpi)">
                     <span class="material-icons text-sm">edit</span>
                   </button>
                   @if (confirmDeleteId() === kpi.id) {
                     <button class="btn-ghost p-1.5 text-red-600 bg-red-50 font-black text-[9px] uppercase tracking-widest px-3 rounded-lg" (click)="onDeleteKpi(kpi.id)">
                       Confirm
                     </button>
                     <button class="btn-ghost p-1.5 text-[var(--t-text-tertiary)]" (click)="confirmDeleteId.set(null)">
                       <span class="material-icons text-sm">close</span>
                     </button>
                   } @else {
                     <button class="btn-ghost p-1.5 text-red-500 hover:bg-red-50" title="Delete KPI" aria-label="Delete KPI" (click)="confirmDeleteId.set(kpi.id)">
                       <span class="material-icons text-sm">delete</span>
                     </button>
                   }
                </div>
              </div>
            </div>
            
            <!-- Entries -->
            <div class="flex-1 p-5 space-y-4 bg-[var(--t-bg)]">
              @for (entry of kpi.entries; track entry.id) {
                <div class="card p-3 shadow-none border-[var(--t-border)] hover:bg-[var(--t-surface)] group transition-all">
                  <div class="flex justify-between items-center mb-3">
                    <span class="text-xs font-bold uppercase tracking-tight" style="color:var(--t-text-secondary)">
                      {{ entry.year }} Q{{ entry.quarter }}
                    </span>
                    @if (entry.value_actual) {
                      <span class="text-[10px] font-bold px-2 py-0.5 rounded-full"
                            [style.background]="isHitting(entry) ? 'var(--t-green)' : 'var(--t-red)'"
                            style="color:white">
                        {{ isHitting(entry) ? 'ON TRACK' : 'OFF TRACK' }}
                      </span>
                    }
                  </div>

                  <div class="grid grid-cols-2 gap-4">
                    <div>
                      <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Plan Target</p>
                      <p class="text-sm font-bold">{{ entry.value_base || '—' }} <span class="text-[10px] font-medium text-[var(--t-text-secondary)]">{{ kpi.unit }}</span></p>
                    </div>
                    <div class="text-right">
                      <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Actual Result</p>
                      <p class="text-sm font-bold" [style.color]="isHitting(entry) ? 'var(--t-green)' : 'var(--t-red)'">
                        {{ entry.value_actual || '—' }} <span class="text-[10px] font-medium text-[var(--t-text-secondary)]">{{ kpi.unit }}</span>
                      </p>
                    </div>
                  </div>

                  <!-- Progress Bar -->
                  @if (entry.value_base && entry.value_actual) {
                    <div class="mt-3">
                      <div class="h-1.5 w-full rounded-full bg-[var(--t-surface-raised)] overflow-hidden">
                        <div class="h-full rounded-full transition-all duration-700"
                             [style.width.%]="getPct(entry)"
                             [style.background]="isHitting(entry) ? 'var(--t-green)' : 'var(--t-amber)'"></div>
                      </div>
                    </div>
                  }
                </div>
              }
              @if (kpi.entries.length === 0) {
                <div class="text-center py-6 border-2 border-dashed rounded-xl" style="border-color:var(--t-border)">
                  <p class="text-xs font-medium text-[var(--t-text-secondary)]">No actuals reported for this KPI yet.</p>
                </div>
              }

              <div class="rounded-lg border border-[var(--t-border)] bg-[var(--t-surface)] p-3 space-y-3">
                <p class="text-[10px] font-bold uppercase tracking-wider" style="color:var(--t-text-secondary)">Quarterly Entry</p>
                <div class="grid grid-cols-2 md:grid-cols-5 gap-2">
                  <input class="input-field text-xs" type="number" min="2020" max="2100" aria-label="KPI entry year"
                         [(ngModel)]="entryDrafts[kpi.id].year"/>
                  <select class="input-field text-xs" aria-label="KPI entry quarter" [(ngModel)]="entryDrafts[kpi.id].quarter">
                    <option [ngValue]="1">Q1</option>
                    <option [ngValue]="2">Q2</option>
                    <option [ngValue]="3">Q3</option>
                    <option [ngValue]="4">Q4</option>
                  </select>
                  <input class="input-field text-xs" inputmode="decimal" placeholder="Base" aria-label="KPI base target"
                         [(ngModel)]="entryDrafts[kpi.id].value_base"/>
                  <input class="input-field text-xs" inputmode="decimal" placeholder="High" aria-label="KPI high target"
                         [(ngModel)]="entryDrafts[kpi.id].value_high"/>
                  <input class="input-field text-xs" inputmode="decimal" placeholder="Actual" aria-label="KPI actual result"
                         [(ngModel)]="entryDrafts[kpi.id].value_actual"/>
                </div>
                <div class="flex justify-end">
                  <button class="btn-secondary text-xs" (click)="onSaveEntry(kpi)">Save Entry</button>
                </div>
              </div>
            </div>
          </div>
        }
      </div>
    </div>

    <!-- ADD KPI MODAL -->
    @if (showAddModal()) {
      <div class="overlay animate-fade-in" (click)="onCloseAddModal()">
        <div class="modal-content card p-8 space-y-6 shadow-2xl" (click)="$event.stopPropagation()">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-bold">{{ editingKpiId ? 'Edit KPI' : 'New KPI Definition' }}<span class="text-[var(--t-accent)]">.</span></h2>
            <button class="btn-ghost p-1" (click)="onCloseAddModal()">
               <span class="material-icons">close</span>
            </button>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">KPI Name</label>
              <input type="text" [(ngModel)]="addForm.name" class="input-field" placeholder="e.g. Monthly Active Users"/>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Type</label>
                <select [(ngModel)]="addForm.type" class="input-field">
                  <option value="operational">Operational</option>
                  <option value="gross_margin">Gross Margin</option>
                  <option value="custom">Custom</option>
                </select>
              </div>
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Unit</label>
                <input type="text" [(ngModel)]="addForm.unit" class="input-field" placeholder="e.g. % or USD"/>
              </div>
            </div>

            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Frequency</label>
              <select [(ngModel)]="addForm.frequency" class="input-field">
                <option value="quarterly">Quarterly</option>
                <option value="monthly">Monthly</option>
                <option value="annual">Annual</option>
              </select>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t" style="border-color:var(--t-border)">
            <button class="btn-ghost" (click)="onCloseAddModal()">Cancel</button>
            <button class="btn-primary px-8" [disabled]="!addForm.name" (click)="onSaveKpi()">{{ editingKpiId ? 'Save KPI' : 'Create KPI' }}</button>
          </div>
        </div>
      </div>
    }
  `
})
export class KpisTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  kpis = signal<any[]>([]);
  loading = signal(true);
  editingKpiId: string | null = null;
  entryDrafts: Record<string, {
    year: number;
    quarter: number;
    value_base: string;
    value_high: string;
    value_actual: string;
  }> = {};
  confirmDeleteId = signal<string | null>(null);

  // Modal state
  showAddModal = signal(false);
  addForm = {
    name: '',
    type: 'custom',
    frequency: 'quarterly',
    unit: ''
  };

  ngOnInit() {
    (globalThis as any).__transmuterKpis = this;
    this.fetchKpis();
  }

  fetchKpis() {
    this.loading.set(true);
    this.api.get<any>(`/initiatives/${this.initiativeId}/kpis`).subscribe({
      next: (data) => {
        const items = data.items || [];
        for (const kpi of items) {
          this.entryDrafts[kpi.id] ||= this.defaultEntryDraft(kpi);
        }
        this.kpis.set(items);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  onOpenAddModal() {
    this.editingKpiId = null;
    this.addForm = {
      name: '',
      type: 'custom',
      frequency: 'quarterly',
      unit: ''
    };
    this.showAddModal.set(true);
  }

  onCloseAddModal() {
    this.showAddModal.set(false);
    this.editingKpiId = null;
  }

  onSaveKpi() {
    if (!this.addForm.name) return;
    const request = this.editingKpiId
      ? this.api.put(`/initiatives/${this.initiativeId}/kpis/${this.editingKpiId}`, this.addForm)
      : this.api.post(`/initiatives/${this.initiativeId}/kpis`, this.addForm);
    request.subscribe({
      next: () => {
        this.fetchKpis();
        this.onCloseAddModal();
      },
      error: () => alert('Failed to create KPI.')
    });
  }

  onOpenEditModal(kpi: any) {
    this.editingKpiId = kpi.id;
    this.addForm = {
      name: kpi.name,
      type: kpi.type,
      frequency: kpi.frequency,
      unit: kpi.unit || ''
    };
    this.showAddModal.set(true);
  }

  onDeleteKpi(kpiId: string) {
    this.api.delete(`/initiatives/${this.initiativeId}/kpis/${kpiId}`).subscribe({
      next: () => {
        this.confirmDeleteId.set(null);
        this.fetchKpis();
      },
      error: () => {
        this.confirmDeleteId.set(null);
        alert('Failed to delete KPI.');
      }
    });
  }

  onSaveEntry(kpi: any) {
    const draft = this.entryDrafts[kpi.id] || this.defaultEntryDraft(kpi);
    this.api.put(`/initiatives/${this.initiativeId}/kpis/${kpi.id}/entries`, [{
      year: Number(draft.year),
      quarter: Number(draft.quarter),
      value_base: draft.value_base || null,
      value_high: draft.value_high || null,
      value_actual: draft.value_actual || null
    }]).subscribe({
      next: () => this.fetchKpis(),
      error: () => alert('Failed to save KPI entry.')
    });
  }

  isHitting(entry: any): boolean {
    if (!entry.value_actual || !entry.value_base) return false;
    const a = parseFloat(entry.value_actual);
    const b = parseFloat(entry.value_base);
    return a >= b;
  }
  
  isMissing(entry: any): boolean {
    if (!entry.value_actual || !entry.value_base) return false;
    return !this.isHitting(entry);
  }

  getPct(entry: any): number {
    if (!entry.value_actual || !entry.value_base) return 0;
    const a = parseFloat(entry.value_actual);
    const b = parseFloat(entry.value_base);
    if (b === 0) return 0;
    return Math.min((a / b) * 100, 100);
  }

  private defaultEntryDraft(kpi: any) {
    const latest = [...(kpi.entries || [])].sort((a, b) => {
      if (a.year !== b.year) return b.year - a.year;
      return (b.quarter || 0) - (a.quarter || 0);
    })[0];
    return {
      year: latest?.year || new Date().getFullYear(),
      quarter: latest?.quarter || Math.floor(new Date().getMonth() / 3) + 1,
      value_base: latest?.value_base || '',
      value_high: latest?.value_high || '',
      value_actual: latest?.value_actual || ''
    };
  }
}
