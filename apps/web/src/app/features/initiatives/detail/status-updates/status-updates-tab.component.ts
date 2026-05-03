import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-status-updates-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-8 animate-fade-in">
      <!-- Header Actions -->
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-xl font-bold text-[var(--t-text-primary)]">Status Heartbeat<span class="text-[var(--t-accent)]">.</span></h2>
          <p class="text-xs font-semibold uppercase tracking-wider text-[var(--t-text-secondary)]">Executive progress reporting & timeline</p>
        </div>
        <button 
          *ngIf="!isEditing()" 
          (click)="startNewUpdate()" 
          class="btn-primary flex items-center gap-2">
          <span class="material-icons text-sm">add_task</span>
          Create Update
        </button>
      </div>

      <!-- Draft / Edit Form -->
      @if (isEditing()) {
        <div class="card glass-panel border-l-4 p-8 animate-in slide-in-from-top-4 duration-300"
             [style.border-color]="editForm.rag_status === 'green' ? 'var(--t-green)' : (editForm.rag_status === 'amber' ? 'var(--t-amber)' : 'var(--t-red)')">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-bold">{{ draft()?.id ? 'Edit Draft Update' : 'New Status Report' }}</h3>
            <div class="flex items-center gap-2">
              @if (generatedDraft()) {
                <span class="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">AI Draft</span>
              }
              <span class="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded bg-[var(--t-surface-raised)]">Drafting Mode</span>
            </div>
          </div>

          <div class="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--t-border)] bg-[var(--t-surface)] p-4">
            <div>
              <p class="text-sm font-bold text-[var(--t-text-primary)]">AI-assisted draft</p>
              <p class="text-xs text-[var(--t-text-secondary)]">Generate a reviewable status update from initiative milestones, risks, and KPIs.</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" (click)="generateDraft()" [disabled]="drafting()" class="btn-secondary text-sm" data-testid="generate-status-draft">
                <span class="material-icons text-sm align-middle">auto_awesome</span>
                {{ drafting() ? 'Generating...' : 'Generate Draft' }}
              </button>
              @if (generatedDraft()) {
                <button type="button" (click)="acceptGeneratedDraft()" class="btn-primary text-sm" data-testid="accept-status-draft">Accept</button>
                <button type="button" (click)="editGeneratedDraft()" class="btn-ghost text-sm" data-testid="edit-status-draft">Edit</button>
                <button type="button" (click)="discardGeneratedDraft()" class="btn-ghost text-sm" data-testid="discard-status-draft">Discard</button>
              }
            </div>
          </div>
          
          <div class="grid grid-cols-1 gap-8">
            <!-- RAG Selection -->
            <div>
              <label class="block text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)] mb-3">Initiative Health (RAG)</label>
              <div class="flex gap-4">
                @for (status of ['green', 'amber', 'red']; track status) {
                  <button 
                    (click)="setRag(status)"
                    [class.ring-2]="editForm.rag_status === status"
                    [class.ring-offset-2]="editForm.rag_status === status"
                    [style.background]="status === 'green' ? 'var(--t-green)' : (status === 'amber' ? 'var(--t-amber)' : 'var(--t-red)')"
                    class="flex-1 py-3 rounded-xl text-white font-bold uppercase text-[10px] tracking-widest shadow-sm hover:scale-[1.02] transition-all opacity-40"
                    [class.!opacity-100]="editForm.rag_status === status">
                    {{ status }}
                  </button>
                }
              </div>
            </div>

            <!-- Summary -->
            <div>
              <label class="block text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)] mb-2">Executive Summary</label>
              <textarea 
                [(ngModel)]="editForm.summary"
                name="status_summary"
                rows="3" 
                class="input-field w-full text-base" 
                placeholder="High-level status of the initiative..."></textarea>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label class="block text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)] mb-2">Key Achievements</label>
                <textarea [(ngModel)]="editForm.achievements" name="status_achievements" rows="3" class="input-field w-full" placeholder="What significant milestones were reached?"></textarea>
              </div>
              <div>
                <label class="block text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)] mb-2">Blocking Issues</label>
                <textarea [(ngModel)]="editForm.issues" name="status_issues" rows="3" class="input-field w-full border-[var(--t-red)]/30" placeholder="Any blockers requiring attention?"></textarea>
              </div>
            </div>

            <div>
              <label class="block text-[10px] font-bold uppercase tracking-wider text-[var(--t-text-secondary)] mb-2">Next Steps</label>
              <textarea [(ngModel)]="editForm.next_steps" name="status_next_steps" rows="2" class="input-field w-full" placeholder="Priorities for the upcoming period..."></textarea>
            </div>

            <div class="flex justify-end gap-3 mt-4 pt-6 border-t border-[var(--t-border)]">
              <button (click)="isEditing.set(false)" class="btn-ghost">Discard</button>
              <button (click)="saveDraft()" class="btn-secondary">Save as Draft</button>
              <button (click)="submitUpdate()" class="btn-primary px-10">Submit Final Report</button>
            </div>
          </div>
        </div>
      }

      <!-- History Timeline -->
      <div class="space-y-6">
        <div class="flex items-center gap-4">
          <h3 class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest shrink-0">Historical Timeline</h3>
          <div class="h-px w-full bg-[var(--t-border)]"></div>
        </div>
        
        @if (loading()) {
          <div class="space-y-6">
            @for (i of [1,2]; track i) {
              <div class="card animate-pulse h-32 bg-[var(--t-surface-raised)]"></div>
            }
          </div>
        }
        
        @if (!loading() && history().length === 0) {
          <div class="text-center py-20 card border-dashed border-2 opacity-50">
            <span class="material-icons text-4xl mb-2">history</span>
            <p class="text-sm font-medium">No submitted updates yet.</p>
          </div>
        }

        <div class="relative pl-10 space-y-10 before:absolute before:left-[11px] before:top-2 before:bottom-2 before:w-[2px] before:bg-gradient-to-b before:from-[var(--t-accent)] before:to-transparent">
          @for (update of history(); track update.id) {
            <div class="relative animate-in slide-in-from-left-4 duration-500">
              <!-- Timeline Marker -->
              <div class="absolute -left-[41px] mt-1.5 w-6 h-6 rounded-full border-4 border-[var(--t-bg)] shadow-md flex items-center justify-center transition-transform hover:scale-125 z-10"
                   [style.background]="update.rag_status === 'green' ? 'var(--t-green)' : (update.rag_status === 'amber' ? 'var(--t-amber)' : 'var(--t-red)')">
                <span class="material-icons text-[10px] text-white">check</span>
              </div>

              <div class="card p-6 group hover:border-[var(--t-accent)] transition-all">
                <div class="flex justify-between items-start mb-6">
                  <div>
                    <div class="flex items-center gap-3 mb-2">
                      <span class="text-sm font-bold text-[var(--t-text-primary)]">{{ update.submitted_at | date:'MMMM d, y' }}</span>
                      <span class="badge-purple text-[9px] font-bold uppercase tracking-tighter">Verified</span>
                      <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">• By {{ update.author_name }}</span>
                    </div>
                    <p class="text-lg font-medium leading-relaxed text-[var(--t-text-primary)]">{{ update.summary }}</p>
                  </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-8 mt-6 pt-6 border-t border-[var(--t-border)]">
                  @if (update.achievements) {
                    <div>
                      <span class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-3">
                        <span class="material-icons text-sm text-[var(--t-green)]">stars</span>
                        Achievements
                      </span>
                      <p class="text-sm leading-relaxed text-[var(--t-text-secondary)]">{{ update.achievements }}</p>
                    </div>
                  }
                  @if (update.issues) {
                    <div>
                      <span class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-3">
                        <span class="material-icons text-sm text-[var(--t-red)]">error_outline</span>
                        Blocking Issues
                      </span>
                      <p class="text-sm leading-relaxed text-[var(--t-red)] font-medium">{{ update.issues }}</p>
                    </div>
                  }
                  @if (update.next_steps) {
                    <div>
                      <span class="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-3">
                        <span class="material-icons text-sm text-[var(--t-accent)]">next_plan</span>
                        Next Steps
                      </span>
                      <p class="text-sm leading-relaxed text-[var(--t-text-secondary)]">{{ update.next_steps }}</p>
                    </div>
                  }
                </div>
              </div>
            </div>
          }
        </div>
      </div>
    </div>
  `
})
export class StatusUpdatesTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  
  history = signal<any[]>([]);
  draft = signal<any>(null);
  generatedDraft = signal<any>(null);
  drafting = signal(false);
  loading = signal(true);
  isEditing = signal(false);

  editForm = {
    rag_status: 'green',
    summary: '',
    achievements: '',
    issues: '',
    next_steps: ''
  };

  ngOnInit() {
    this.fetchHistory();
    this.fetchDraft();
  }

  startNewUpdate() {
    this.editForm = {
      rag_status: 'green',
      summary: '',
      achievements: '',
      issues: '',
      next_steps: ''
    };
    this.generatedDraft.set(null);
    this.isEditing.set(true);
  }

  setRag(status: string) {
    this.editForm.rag_status = status;
  }

  generateDraft() {
    this.drafting.set(true);
    this.api.post<any>(`/initiatives/${this.initiativeId}/status-updates/generate-draft`, {}).subscribe({
      next: (data) => {
        this.generatedDraft.set(data);
        this.editForm = {
          rag_status: data.rag_status || 'green',
          summary: data.summary || '',
          achievements: data.achievements || '',
          issues: data.issues || '',
          next_steps: data.next_steps || ''
        };
        this.drafting.set(false);
      },
      error: () => this.drafting.set(false)
    });
  }

  acceptGeneratedDraft() {
    this.saveDraft();
    this.generatedDraft.set(null);
  }

  editGeneratedDraft() {
    this.generatedDraft.set({ ...this.generatedDraft(), editing: true });
  }

  discardGeneratedDraft() {
    this.generatedDraft.set(null);
    this.editForm = {
      rag_status: 'green',
      summary: '',
      achievements: '',
      issues: '',
      next_steps: ''
    };
  }

  fetchHistory() {
    this.loading.set(true);
    this.api.get<any>(`/initiatives/${this.initiativeId}/status-updates`).subscribe({
      next: (data) => {
        this.history.set(data.items || []);
        this.loading.set(false);
      },
      error: () => this.loading.set(false)
    });
  }

  fetchDraft() {
    this.api.get<any>(`/initiatives/${this.initiativeId}/status-updates/draft`).subscribe({
      next: (data) => {
        if (data) {
          this.draft.set(data);
          this.editForm = { ...data };
          this.isEditing.set(true);
        }
      }
    });
  }

  saveDraft() {
    const body = { ...this.editForm, is_draft: true };
    this.performSave(body);
  }

  submitUpdate() {
    const body = { ...this.editForm, is_draft: false };
    this.performSave(body);
  }

  private performSave(body: any) {
    const request = this.draft() 
      ? this.api.put(`/initiatives/${this.initiativeId}/status-updates/${this.draft().id}`, body)
      : this.api.post(`/initiatives/${this.initiativeId}/status-updates`, body);

    request.subscribe(() => {
      this.isEditing.set(false);
      this.generatedDraft.set(null);
      this.fetchDraft();
      this.fetchHistory();
    });
  }
}
