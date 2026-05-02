import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-risks-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-6">
      <div class="flex justify-between items-center mb-6">
        <div>
          <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Risk Register<span class="text-[var(--t-accent)]">.</span></h2>
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">Identify and mitigate initiative blockers</p>
        </div>
        <button class="btn-primary flex items-center gap-2" (click)="onOpenAddModal()">
          <span class="material-icons text-sm">add</span>
          Add Risk
        </button>
      </div>

      @if (loading()) {
        <div class="space-y-4">
          @for (i of [1,2,3]; track i) {
            <div class="card animate-pulse h-32 bg-[var(--t-surface-raised)]"></div>
          }
        </div>
      }

      @if (!loading() && risks().length === 0) {
        <div class="card text-center py-20 opacity-75">
          <div class="w-16 h-16 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center mx-auto mb-4">
             <span class="material-icons text-3xl" style="color:var(--t-text-secondary)">warning_amber</span>
          </div>
          <h3 class="text-lg font-bold">No risks registered</h3>
          <p class="text-sm text-[var(--t-text-secondary)] mt-1">Great! No active risks reported for this initiative.</p>
          <button class="btn-secondary text-xs mt-6" (click)="onOpenAddModal()">+ Add Risk</button>
        </div>
      }

      <div class="space-y-4">
        @for (risk of risks(); track risk.id) {
          <div class="card glass-panel hover-card group relative">
            <div class="flex flex-col md:flex-row justify-between gap-6">
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-3 mb-3">
                  <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                        [class]="'badge-' + ratingColor(risk.rating)">
                    {{ risk.rating || 'LOW' }} RATING
                  </span>
                  <span class="text-[10px] font-bold uppercase tracking-widest" style="color:var(--t-text-secondary)">
                    {{ risk.type }}
                  </span>
                  @if (risk.status === 'closed') {
                    <span class="badge-gray text-[10px] font-bold uppercase">CLOSED</span>
                  }
                </div>
                
                <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-2" [class.opacity-50]="risk.status === 'closed'">
                  {{ risk.description }}
                </h3>

                <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
                  <div>
                    <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Impact</p>
                    <p class="text-sm font-semibold capitalize">{{ risk.impact || 'Medium' }}</p>
                  </div>
                  <div>
                    <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Likelihood</p>
                    <p class="text-sm font-semibold capitalize">{{ risk.likelihood || 'Medium' }}</p>
                  </div>
                  <div>
                    <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-text-secondary)">Owner</p>
                    <p class="text-sm font-semibold">{{ risk.owner_name || 'Unassigned' }}</p>
                  </div>
                  @if (risk.escalated) {
                    <div>
                      <p class="text-[9px] font-bold uppercase tracking-wider mb-1" style="color:var(--t-red)">Alert</p>
                      <p class="text-xs font-bold text-[var(--t-red)] uppercase tracking-tighter">ESCALATED</p>
                    </div>
                  }
                </div>
              </div>

              <div class="flex md:flex-col items-center justify-center gap-2 border-l md:pl-6 border-transparent md:border-[var(--t-border)]">
                @if (risk.status === 'open') {
                  <button class="btn-secondary py-1.5 px-4 text-xs w-full" (click)="onOpenEditModal(risk)">Edit</button>
                  <button class="btn-primary py-1.5 px-4 text-xs w-full" (click)="onCloseRisk(risk.id)">Close</button>
                  <button class="btn-ghost p-2 text-red-500 hover:bg-red-50" (click)="onDeleteRisk(risk.id)">
                    <span class="material-icons text-sm">delete</span>
                  </button>
                } @else {
                   <span class="material-icons text-green-500">check_circle</span>
                   <p class="text-[10px] font-bold text-green-500 uppercase">Resolved</p>
                }
              </div>
            </div>

            @if (risk.mitigation) {
              <div class="mt-5 p-4 rounded-xl bg-[var(--t-bg)] border border-[var(--t-border)]">
                <div class="flex items-center gap-2 mb-2">
                  <span class="material-icons text-sm text-[var(--t-accent)]">shield</span>
                  <h4 class="text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)]">Mitigation Strategy</h4>
                </div>
                <p class="text-sm leading-relaxed text-[var(--t-text-primary)]">{{ risk.mitigation }}</p>
              </div>
            }
          </div>
        }
      </div>
    </div>

    <!-- ADD RISK MODAL -->
    @if (showAddModal()) {
      <div class="overlay animate-fade-in" (click)="onCloseAddModal()">
        <div class="modal-content card p-8 space-y-6 shadow-2xl" (click)="$event.stopPropagation()">
          <div class="flex justify-between items-center">
            <h2 class="text-xl font-bold">{{ editingRiskId ? 'Edit Risk' : 'Register New Risk' }}<span class="text-[var(--t-accent)]">.</span></h2>
            <button class="btn-ghost p-1" (click)="onCloseAddModal()">
               <span class="material-icons">close</span>
            </button>
          </div>

          <div class="space-y-4">
            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Description</label>
              <textarea [(ngModel)]="addForm.description" rows="3" class="input-field" placeholder="What is the potential risk or blocker?"></textarea>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Type</label>
                <select [(ngModel)]="addForm.type" class="input-field">
                  <option value="operational">Operational</option>
                  <option value="financial">Financial</option>
                  <option value="technology">Technology</option>
                  <option value="people">People</option>
                </select>
              </div>
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Impact</label>
                <select [(ngModel)]="addForm.impact" class="input-field">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Likelihood</label>
                <select [(ngModel)]="addForm.likelihood" class="input-field">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
              <div class="flex items-end">
                 <label class="flex items-center gap-2 cursor-pointer pb-2">
                   <input type="checkbox" [(ngModel)]="addForm.escalated" class="accent-[var(--t-red)]"/>
                   <span class="text-xs font-bold uppercase text-[var(--t-red)]">Escalate to Steering</span>
                 </label>
              </div>
            </div>

            <div>
              <label class="text-[10px] font-bold uppercase tracking-wider block mb-1.5 text-[var(--t-text-secondary)]">Mitigation Plan</label>
              <textarea [(ngModel)]="addForm.mitigation" rows="2" class="input-field" placeholder="How will we address this risk?"></textarea>
            </div>
          </div>

          <div class="flex justify-end gap-3 pt-4 border-t" style="border-color:var(--t-border)">
            <button class="btn-ghost" (click)="onCloseAddModal()">Cancel</button>
            <button class="btn-primary px-8" [disabled]="!addForm.description" (click)="onSaveRisk()">{{ editingRiskId ? 'Save Risk' : 'Create Risk' }}</button>
          </div>
        </div>
      </div>
    }
  `
})
export class RisksTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  risks = signal<any[]>([]);
  loading = signal(true);
  editingRiskId: string | null = null;

  // Modal state
  showAddModal = signal(false);
  addForm = {
    description: '',
    type: 'operational',
    impact: 'medium',
    likelihood: 'medium',
    mitigation: '',
    escalated: false,
    status: 'open'
  };

  ngOnInit() {
    this.fetchRisks();
  }

  fetchRisks() {
    this.loading.set(true);
    this.api.get<any>(`/initiatives/${this.initiativeId}/risks`).subscribe({
      next: (data) => {
        this.risks.set(data.items || []);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      }
    });
  }

  ratingColor(rating: string): string {
    const map: Record<string, string> = {
      high: 'red',
      medium: 'amber',
      low: 'green'
    };
    return map[rating?.toLowerCase()] || 'gray';
  }

  onOpenAddModal() {
    this.editingRiskId = null;
    this.addForm = {
      description: '',
      type: 'operational',
      impact: 'medium',
      likelihood: 'medium',
      mitigation: '',
      escalated: false,
      status: 'open'
    };
    this.showAddModal.set(true);
  }

  onCloseAddModal() {
    this.showAddModal.set(false);
    this.editingRiskId = null;
  }

  onSaveRisk() {
    if (!this.addForm.description) return;
    const request = this.editingRiskId
      ? this.api.put(`/initiatives/${this.initiativeId}/risks/${this.editingRiskId}`, this.addForm)
      : this.api.post(`/initiatives/${this.initiativeId}/risks`, this.addForm);
    request.subscribe({
      next: () => {
        this.fetchRisks();
        this.onCloseAddModal();
      },
      error: () => alert('Failed to create risk.')
    });
  }

  onOpenEditModal(risk: any) {
    this.editingRiskId = risk.id;
    this.addForm = {
      description: risk.description || '',
      type: risk.type || 'operational',
      impact: risk.impact || 'medium',
      likelihood: risk.likelihood || 'medium',
      mitigation: risk.mitigation || '',
      escalated: Boolean(risk.escalated),
      status: risk.status || 'open'
    };
    this.showAddModal.set(true);
  }

  onCloseRisk(riskId: string) {
    this.api.put(`/initiatives/${this.initiativeId}/risks/${riskId}`, { status: 'closed' }).subscribe({
      next: () => this.fetchRisks()
    });
  }

  onDeleteRisk(riskId: string) {
    if (!confirm('Are you sure you want to delete this risk?')) return;
    this.api.delete(`/initiatives/${this.initiativeId}/risks/${riskId}`).subscribe({
      next: () => this.fetchRisks()
    });
  }
}
