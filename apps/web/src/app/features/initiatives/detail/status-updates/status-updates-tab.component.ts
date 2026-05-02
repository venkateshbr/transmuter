import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';

@Component({
  selector: 'app-status-updates-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-8">
      <!-- Header Actions -->
      <div class="flex justify-between items-center">
        <h2 class="text-xl font-semibold text-[var(--t-text-primary)]">Status Updates</h2>
        <button 
          *ngIf="!draft() && !isEditing()" 
          (click)="startNewUpdate()" 
          class="btn-primary">
          Create Update
        </button>
      </div>

      <!-- Draft / Edit Form -->
      <div *ngIf="isEditing()" class="card glass-panel border-l-4 border-[var(--t-primary)] p-6 animate-fade-in">
        <h3 class="text-lg font-medium mb-4">{{ draft()?.id ? 'Edit Draft' : 'New Status Update' }}</h3>
        
        <div class="grid grid-cols-1 gap-6">
          <!-- RAG Selection -->
          <div>
            <label class="block text-sm font-medium text-[var(--t-text-secondary)] mb-2">RAG Status</label>
            <div class="flex gap-4">
              <button 
                (click)="setRag('green')"
                [class.ring-2]="editForm.rag_status === 'green'"
                class="flex-1 py-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-500 font-medium hover:bg-green-500/20 transition-all">
                Green
              </button>
              <button 
                (click)="setRag('amber')"
                [class.ring-2]="editForm.rag_status === 'amber'"
                class="flex-1 py-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-500 font-medium hover:bg-amber-500/20 transition-all">
                Amber
              </button>
              <button 
                (click)="setRag('red')"
                [class.ring-2]="editForm.rag_status === 'red'"
                class="flex-1 py-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-500 font-medium hover:bg-red-500/20 transition-all">
                Red
              </button>
            </div>
          </div>

          <!-- Summary -->
          <div>
            <label class="block text-sm font-medium text-[var(--t-text-secondary)] mb-2">Executive Summary</label>
            <textarea 
              [(ngModel)]="editForm.summary"
              rows="3" 
              class="input-field w-full" 
              placeholder="High-level status of the initiative..."></textarea>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label class="block text-sm font-medium text-[var(--t-text-secondary)] mb-2">Key Achievements</label>
              <textarea [(ngModel)]="editForm.achievements" rows="3" class="input-field w-full" placeholder="What went well?"></textarea>
            </div>
            <div>
              <label class="block text-sm font-medium text-[var(--t-text-secondary)] mb-2">Blocking Issues</label>
              <textarea [(ngModel)]="editForm.issues" rows="3" class="input-field w-full" placeholder="Any blockers?"></textarea>
            </div>
          </div>

          <div>
            <label class="block text-sm font-medium text-[var(--t-text-secondary)] mb-2">Next Steps</label>
            <textarea [(ngModel)]="editForm.next_steps" rows="2" class="input-field w-full" placeholder="Priorities for next week..."></textarea>
          </div>

          <div class="flex justify-end gap-3 mt-4">
            <button (click)="isEditing.set(false)" class="btn-ghost">Cancel</button>
            <button (click)="saveDraft()" class="btn-secondary">Save Draft</button>
            <button (click)="submitUpdate()" class="btn-primary px-8">Submit Final</button>
          </div>
        </div>
      </div>

      <!-- History Timeline -->
      <div class="space-y-6">
        <h3 class="text-sm font-semibold text-[var(--t-text-tertiary)] uppercase tracking-wider">History</h3>
        
        <div *ngIf="loading()" class="text-center py-8 text-[var(--t-text-secondary)]">Loading history...</div>
        
        <div *ngIf="!loading() && history().length === 0" class="text-center py-12 card border-dashed">
          <p class="text-[var(--t-text-secondary)]">No submitted updates yet.</p>
        </div>

        <div class="relative pl-8 space-y-8 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-px before:bg-[var(--t-border)]">
          <div *ngFor="let update of history()" class="relative animate-fade-in">
            <!-- Timeline Marker -->
            <div class="absolute -left-8 mt-1.5 w-6 h-6 rounded-full border-4 border-[var(--t-bg-page)]"
                 [class.bg-green-500]="update.rag_status === 'green'"
                 [class.bg-amber-500]="update.rag_status === 'amber'"
                 [class.bg-red-500]="update.rag_status === 'red'">
            </div>

            <div class="card p-5 hover-card">
              <div class="flex justify-between items-start mb-4">
                <div>
                  <div class="flex items-center gap-2 mb-1">
                    <span class="text-sm font-bold text-[var(--t-text-primary)]">{{ update.submitted_at | date:'mediumDate' }}</span>
                    <span class="text-xs text-[var(--t-text-tertiary)]">• By {{ update.author_name }}</span>
                  </div>
                  <p class="text-[var(--t-text-secondary)] leading-relaxed">{{ update.summary }}</p>
                </div>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 pt-4 border-t border-[var(--t-border)] text-sm">
                <div *ngIf="update.achievements">
                  <span class="block font-semibold text-[var(--t-text-primary)] mb-1">Achievements</span>
                  <span class="text-[var(--t-text-secondary)]">{{ update.achievements }}</span>
                </div>
                <div *ngIf="update.issues">
                  <span class="block font-semibold text-[var(--t-text-primary)] mb-1">Issues</span>
                  <span class="text-[var(--t-text-secondary)] text-red-500">{{ update.issues }}</span>
                </div>
                <div *ngIf="update.next_steps">
                  <span class="block font-semibold text-[var(--t-text-primary)] mb-1">Next Steps</span>
                  <span class="text-[var(--t-text-secondary)]">{{ update.next_steps }}</span>
                </div>
              </div>
            </div>
          </div>
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
    this.isEditing.set(true);
  }

  setRag(status: string) {
    this.editForm.rag_status = status;
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
      this.fetchDraft();
      this.fetchHistory();
    });
  }
}
