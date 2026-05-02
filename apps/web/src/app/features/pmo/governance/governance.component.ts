import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-governance',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Governance Authority<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Centralized stage-gate oversight and portfolio compliance management.</p>
        </div>
        @if (auth.getRole() === 'transformation_office') {
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-lg flex items-center gap-2">
            <span class="relative flex h-2 w-2">
              <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--t-accent)] opacity-75"></span>
              <span class="relative inline-flex rounded-full h-2 w-2 bg-[var(--t-accent)]"></span>
            </span>
            <span class="text-[10px] font-black uppercase tracking-widest">Transformation Office Active</span>
          </div>
        }
      </div>

      <!-- Governance Stats -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="card p-6 flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center text-blue-500">
            <span class="material-icons text-2xl">file_present</span>
          </div>
          <div>
            <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-wider">Total Queue</p>
            <p class="text-2xl font-black text-[var(--t-text-primary)]">{{ submissions().length }}</p>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-4 border-l-4 border-[var(--t-accent)]">
          <div class="w-12 h-12 rounded-2xl bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
            <span class="material-icons text-2xl">pending_actions</span>
          </div>
          <div>
            <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-wider">Awaiting Decision</p>
            <p class="text-2xl font-black text-[var(--t-accent)]">{{ getCount('pending') }}</p>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-green-500/10 flex items-center justify-center text-green-500">
            <span class="material-icons text-2xl">verified_user</span>
          </div>
          <div>
            <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-wider">Total Approved</p>
            <p class="text-2xl font-black text-green-500">{{ getCount('approved') }}</p>
          </div>
        </div>
        <div class="card p-6 flex items-center gap-4">
          <div class="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center text-red-500">
            <span class="material-icons text-2xl">gpp_bad</span>
          </div>
          <div>
            <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-wider">Total Rejected</p>
            <p class="text-2xl font-black text-red-500">{{ getCount('rejected') }}</p>
          </div>
        </div>
      </div>

      <!-- Submissions Grid -->
      <div class="grid grid-cols-1 gap-6">
        @for (s of submissions(); track s.id) {
          <div class="card p-6 flex items-center gap-8 hover:border-[var(--t-accent)] hover:shadow-xl transition-all group">
            
            <!-- Gate Indicator -->
            <div class="flex-none flex flex-col items-center justify-center w-20 h-20 rounded-3xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] group-hover:border-[var(--t-accent)]/30 transition-all">
              <span class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase">Gate</span>
              <span class="text-3xl font-black text-[var(--t-accent)]">{{ s.gate_number }}</span>
            </div>

            <!-- Initiative Detail -->
            <div class="flex-1 min-w-0">
               <div class="flex items-center gap-3 mb-1">
                 <span class="text-[10px] font-black px-2 py-0.5 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                   TRN-{{ s.initiative_id.substring(0,3).toUpperCase() }}
                 </span>
                 <span class="text-xs font-bold text-[var(--t-text-secondary)] uppercase tracking-tighter italic">Pending Transformation Review</span>
               </div>
               <h3 class="text-lg font-black text-[var(--t-text-primary)] truncate">
                 Review Submission for Phase {{ s.gate_number }} Transition
               </h3>
               <div class="mt-2 flex items-center gap-6">
                 <div class="flex items-center gap-2">
                    <div class="w-5 h-5 rounded-full bg-[var(--t-surface-raised)] flex items-center justify-center">
                       <span class="material-icons text-[10px] text-[var(--t-text-tertiary)]">person</span>
                    </div>
                    <span class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Submitted by</span>
                    <span class="text-[10px] font-black text-[var(--t-text-secondary)]">{{ s.submitted_by_name || 'System' }}</span>
                 </div>
                 <div class="flex items-center gap-2">
                    <span class="material-icons text-xs text-[var(--t-text-tertiary)]">schedule</span>
                    <span class="text-[10px] font-bold text-[var(--t-text-secondary)] uppercase">{{ s.submitted_at | date:'MMM d, HH:mm' }}</span>
                 </div>
               </div>
            </div>

            <!-- AI Insight Placeholder -->
            <div class="hidden xl:flex flex-none w-64 p-4 rounded-2xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex-col gap-2">
               <div class="flex items-center gap-2">
                  <span class="material-icons text-xs text-[var(--t-accent)]">psychology</span>
                  <span class="text-[8px] font-black uppercase tracking-widest text-[var(--t-accent)]">AI Recommendation</span>
               </div>
               <p class="text-[10px] font-medium leading-relaxed text-[var(--t-text-secondary)] italic">
                 "Critical milestones are 100% complete. Financial variance is within 5% tolerance. Approval suggested."
               </p>
            </div>

            <!-- Status & Actions -->
            <div class="flex-none flex items-center gap-6">
              <div class="flex flex-col items-end gap-1">
                <span class="text-[8px] font-black uppercase text-[var(--t-text-tertiary)]">Current Status</span>
                <span class="badge !px-4 !py-1.5" [class]="getDecisionClass(s.decision)">
                  {{ s.decision | uppercase }}
                </span>
              </div>

              <div class="h-10 w-px bg-[var(--t-border)]"></div>

              <div class="flex gap-2">
                @if (s.decision === 'pending' && auth.getRole() === 'transformation_office') {
                  <button (click)="decide(s.id, 'approved')" class="w-10 h-10 rounded-xl bg-green-500 text-white flex items-center justify-center shadow-lg shadow-green-500/20 hover:scale-110 active:scale-95 transition-all">
                    <span class="material-icons">check</span>
                  </button>
                  <button (click)="decide(s.id, 'rejected')" class="w-10 h-10 rounded-xl bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-500/20 hover:scale-110 active:scale-95 transition-all">
                    <span class="material-icons">close</span>
                  </button>
                } @else {
                  <button class="w-10 h-10 rounded-xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] text-[var(--t-text-tertiary)] flex items-center justify-center hover:text-[var(--t-accent)] hover:border-[var(--t-accent)] transition-all">
                    <span class="material-icons text-sm">visibility</span>
                  </button>
                }
              </div>
            </div>

          </div>
        }
        
        @if (submissions().length === 0) {
          <div class="py-24 text-center border-2 border-dashed border-[var(--t-border)] rounded-[2rem] opacity-50">
             <span class="material-icons text-4xl mb-2 text-[var(--t-text-tertiary)]">inventory_2</span>
             <p class="text-sm font-black uppercase tracking-widest">Decision Queue Empty</p>
             <p class="text-xs font-bold text-[var(--t-text-tertiary)] mt-1">All stage-gate submissions have been processed.</p>
          </div>
        }
      </div>

    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }
    .badge {
      @apply inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border;
    }
  `]
})
export class GovernanceComponent implements OnInit {
  private readonly api = inject(ApiService);
  protected readonly auth = inject(AuthService);
  
  submissions = signal<any[]>([]);

  ngOnInit() {
    this.fetchSubmissions();
  }

  fetchSubmissions() {
    this.api.get<any[]>('/governance/submissions').subscribe({
      next: (data) => this.submissions.set(data),
      error: (err) => console.error('Failed to fetch submissions', err)
    });
  }

  getCount(status: string): number {
    return this.submissions().filter(s => s.decision === status).length;
  }

  getDecisionClass(decision: string): string {
    switch (decision) {
      case 'approved': return 'badge-purple !bg-[var(--t-accent)] !text-white';
      case 'rejected': return 'badge-red';
      case 'pending': return 'badge-gray';
      default: return 'badge-gray';
    }
  }

  decide(submissionId: string, decision: 'approved' | 'rejected') {
    if (!confirm(`Are you sure you want to ${decision} this submission?`)) return;

    this.api.patch(`/governance/submissions/${submissionId}/decide`, {
      decision,
      commentary: `${decision.charAt(0).toUpperCase() + decision.slice(1)} via Governance Dashboard`
    }).subscribe({
      next: () => this.fetchSubmissions(),
      error: (err) => alert('Failed to record decision: ' + (err.error?.detail || 'Unknown error'))
    });
  }
}
