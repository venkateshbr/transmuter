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
            Governance Dashboard<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Stage gate review, approvals, and portfolio compliance tracking.</p>
        </div>
        @if (auth.getRole() === 'transformation_office') {
          <div class="flex gap-2">
            <span class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm">
              <span class="w-2 h-2 rounded-full bg-[var(--t-accent)] animate-pulse mr-2"></span>
              Transformation Office Active
            </span>
          </div>
        }
      </div>

      <!-- Stats Row -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div class="card bg-gradient-to-br from-[var(--t-surface)] to-[var(--t-accent-soft)]">
          <div class="text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)] font-bold mb-1">Total Submissions</div>
          <div class="text-3xl font-bold text-[var(--t-text-primary)]">{{ submissions().length }}</div>
        </div>
        <div class="card">
          <div class="text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)] font-bold mb-1">Pending Review</div>
          <div class="text-3xl font-bold text-[var(--t-accent)]">{{ getCount('pending') }}</div>
        </div>
        <div class="card">
          <div class="text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)] font-bold mb-1">Approved</div>
          <div class="text-3xl font-bold text-[var(--t-green)]">{{ getCount('approved') }}</div>
        </div>
        <div class="card">
          <div class="text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)] font-bold mb-1">Rejected</div>
          <div class="text-3xl font-bold text-[var(--t-red)]">{{ getCount('rejected') }}</div>
        </div>
      </div>

      <!-- Governance Table -->
      <div class="card !p-0 overflow-hidden border-[var(--t-border)]">
        <div class="p-6 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)]/50 flex justify-between items-center">
          <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Stage Gate Submissions</h3>
          <button (click)="fetchSubmissions()" class="btn-ghost text-xs">
            Refresh Data
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead>
              <tr class="bg-[var(--t-bg-page)] border-b border-[var(--t-border)]">
                <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Initiative</th>
                <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Gate</th>
                <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Submitted</th>
                <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</th>
                <th class="px-6 py-4 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Decision By</th>
                <th class="px-6 py-4"></th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--t-border)]">
              @for (s of submissions(); track s.id) {
                <tr class="hover:bg-[var(--t-surface-raised)] transition-colors group">
                  <td class="px-6 py-4">
                    <div class="flex flex-col">
                      <span class="text-sm font-bold text-[var(--t-text-primary)]">TRN-{{ s.initiative_id.substring(0,3).toUpperCase() }}</span>
                      <span class="text-[10px] text-[var(--t-text-tertiary)] font-mono">{{ s.initiative_id.substring(0,8) }}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                      <div class="w-7 h-7 rounded-lg bg-[var(--t-accent-soft)] text-[var(--t-accent)] text-xs flex items-center justify-center font-bold border border-[var(--t-accent)]/10">
                        G{{ s.gate_number }}
                      </div>
                      <span class="text-xs text-[var(--t-text-secondary)]">Gate Review</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <div class="flex flex-col">
                      <span class="text-xs text-[var(--t-text-primary)] font-medium">{{ s.submitted_by_name || 'System' }}</span>
                      <span class="text-[10px] text-[var(--t-text-tertiary)]">{{ s.submitted_at | date:'MMM d, HH:mm' }}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <span class="badge" [class]="getDecisionClass(s.decision)">
                      {{ s.decision | uppercase }}
                    </span>
                  </td>
                  <td class="px-6 py-4">
                    @if (s.decided_by_name) {
                      <div class="flex flex-col">
                        <span class="text-xs text-[var(--t-text-primary)] font-medium">{{ s.decided_by_name }}</span>
                        <span class="text-[10px] text-[var(--t-text-tertiary)]">{{ s.decided_at | date:'MMM d, HH:mm' }}</span>
                      </div>
                    } @else {
                      <span class="text-[10px] text-[var(--t-text-tertiary)] italic">Awaiting Decision</span>
                    }
                  </td>
                  <td class="px-6 py-4 text-right">
                    @if (s.decision === 'pending' && auth.getRole() === 'transformation_office') {
                      <div class="flex gap-2 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
                        <button (click)="decide(s.id, 'approved')" class="btn-primary !py-1 !px-3 text-[10px] h-7">Approve</button>
                        <button (click)="decide(s.id, 'rejected')" class="btn-secondary !py-1 !px-3 text-[10px] h-7 !text-red-500 !border-red-500/20">Reject</button>
                      </div>
                    }
                  </td>
                </tr>
              }
              @if (submissions().length === 0) {
                <tr>
                  <td colspan="6" class="px-6 py-12 text-center">
                    <div class="flex flex-col items-center gap-2 opacity-40">
                      <svg class="w-8 h-8 text-[var(--t-text-tertiary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span class="text-xs text-[var(--t-text-tertiary)] font-medium tracking-wide uppercase">No Submissions Found</span>
                    </div>
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
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
