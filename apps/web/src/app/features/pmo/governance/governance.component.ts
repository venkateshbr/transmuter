import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../../core/services/api.service';
import { AuthService } from '../../../core/services/auth.service';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

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
        @if (auth.hasPermission('governance.manage')) {
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
            <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-wider">Health Score</p>
            <p class="text-2xl font-black text-[var(--t-text-primary)]">{{ healthScore() }}</p>
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
              <span class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase">{{ isRebaseline(s) ? 'Base' : 'Gate' }}</span>
              <span class="text-3xl font-black text-[var(--t-accent)]">{{ isRebaseline(s) ? ('v' + (s.requested_bankable_plan_version || '2')) : s.gate_number }}</span>
            </div>

            <!-- Initiative Detail -->
            <div class="flex-1 min-w-0">
               <div class="flex items-center gap-3 mb-1">
                 <span class="text-[10px] font-black px-2 py-0.5 rounded bg-[var(--t-accent-soft)] text-[var(--t-accent)]">
                   {{ submissionCode(s) }}
                 </span>
                 <span class="text-[10px] font-black px-2 py-0.5 rounded border border-[var(--t-border)] text-[var(--t-text-secondary)]">
                   {{ requestLabel(s) }}
                 </span>
                 <span class="text-xs font-bold text-[var(--t-text-secondary)] uppercase tracking-tighter italic">{{ isRebaseline(s) ? 'Pending finance baseline approval' : 'Pending Transformation Review' }}</span>
               </div>
               <h3 class="text-lg font-black text-[var(--t-text-primary)] truncate">
                 {{ submissionName(s) }}
               </h3>
               <p class="text-xs font-bold text-[var(--t-text-secondary)] uppercase tracking-tight">
                 {{ countTickedCriteria(s) }} of {{ s.criteria_snapshot?.length || 0 }} criteria ready
               </p>
               <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                 Approvers:
                 <span class="text-[var(--t-text-secondary)]">
                   {{ rolesText(isRebaseline(s) ? ['transformation_office'] : (gateDefinition(s.gate_number)?.approver_roles || ['transformation_office'])) }}
                 </span>
                 <span class="mx-2">|</span>
                 <span [class.text-emerald-600]="gateDefinition(s.gate_number)?.approval_required !== false">
                   {{ gateDefinition(s.gate_number)?.approval_required === false ? 'No approval required' : 'Approval required' }}
                 </span>
               </p>
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

            <div class="hidden xl:flex flex-none w-64 p-4 rounded-2xl bg-[var(--t-surface-raised)] border border-[var(--t-border)] flex-col gap-2">
               <div class="flex items-center gap-2">
                  <span class="material-icons text-xs text-[var(--t-accent)]">rule</span>
                  <span class="text-[8px] font-black uppercase tracking-widest text-[var(--t-accent)]">Review Notes</span>
               </div>
               <p class="text-[10px] font-medium leading-relaxed text-[var(--t-text-secondary)] italic">
                 "{{ s.commentary || 'No submission commentary recorded.' }}"
               </p>
               @if (isRebaseline(s)) {
                 <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                   Approval creates bankable plan v{{ s.requested_bankable_plan_version || 'next' }}
                 </p>
               }
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
                @if (s.decision === 'pending' && auth.hasPermission('governance.manage')) {
                  <button (click)="decide(s.id, 'approved')" [attr.aria-label]="'Approve ' + submissionLabel(s)" class="w-10 h-10 rounded-xl bg-green-500 text-white flex items-center justify-center shadow-lg shadow-green-500/20 hover:scale-110 active:scale-95 transition-all">
                    <span class="material-icons">check</span>
                  </button>
                  <button (click)="decide(s.id, 'rejected')" [attr.aria-label]="'Reject ' + submissionLabel(s)" class="w-10 h-10 rounded-xl bg-red-500 text-white flex items-center justify-center shadow-lg shadow-red-500/20 hover:scale-110 active:scale-95 transition-all">
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
  private readonly route = inject(ActivatedRoute);
  protected readonly auth = inject(AuthService);
  
  allSubmissions = signal<any[]>([]);
  stageGateDefinitions = signal<any[]>([]);
  healthScore = signal('0/0');
  statusFilter = signal('');

  submissions = computed(() => {
    const status = this.statusFilter();
    return status
      ? this.allSubmissions().filter(submission => submission.decision === status)
      : this.allSubmissions();
  });

  ngOnInit() {
    this.route.queryParamMap.subscribe(params => {
      this.statusFilter.set(params.get('status') ?? '');
    });
    this.fetchSubmissions();
    this.fetchStageGateDefinitions();
  }

  fetchSubmissions() {
    this.api.get<any>('/portfolio/governance').subscribe({
      next: (data) => {
        this.healthScore.set(data.health_score || '0/0');
        this.allSubmissions.set(data.submissions || []);
      },
      error: (err) => console.error('Failed to fetch submissions', err)
    });
  }

  fetchStageGateDefinitions() {
    this.api.get<any[]>('/governance/stage-gates').subscribe({
      next: data => this.stageGateDefinitions.set(Array.isArray(data) ? data : []),
      error: err => console.error('Failed to fetch stage gate definitions', err),
    });
  }

  getCount(status: string): number {
    return this.allSubmissions().filter(s => s.decision === status).length;
  }

  countTickedCriteria(submission: any): number {
    return (submission.criteria_snapshot || []).filter((criterion: any) => criterion?.ticked).length;
  }

  gateDefinition(gateNumber: number): any | undefined {
    return this.stageGateDefinitions().find(gate => Number(gate.gate_number) === Number(gateNumber));
  }

  rolesText(roles: string[] | null | undefined): string {
    return (roles || []).join(', ');
  }

  isRebaseline(submission: any): boolean {
    return submission?.submission_type === 'bankable_plan_rebaseline';
  }

  submissionCode(submission: any): string {
    return submission?.initiative_code || submission?.initiatives?.initiative_code || 'Initiative';
  }

  submissionName(submission: any): string {
    return submission?.initiative_name || submission?.initiatives?.name || 'Gate submission';
  }

  submissionLabel(submission: any): string {
    const code = this.submissionCode(submission);
    const name = this.submissionName(submission);
    return name === 'Gate submission' ? code : `${code} ${name}`;
  }

  requestLabel(submission: any): string {
    if (this.isRebaseline(submission)) {
      return `Bankable plan rebaseline v${submission.requested_bankable_plan_version || 'next'}`;
    }
    return this.gateDefinition(submission.gate_number)?.label || (`Gate ${submission.gate_number}`);
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
    this.api.patch(`/governance/submissions/${submissionId}/decide`, {
      decision,
      commentary: `${decision.charAt(0).toUpperCase() + decision.slice(1)} via Governance Dashboard`
    }).subscribe({
      next: () => this.fetchSubmissions(),
      error: (err) => alert('Failed to record decision: ' + (err.error?.detail || 'Unknown error'))
    });
  }
}
