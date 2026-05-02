import { Component, Input, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-governance-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-12 animate-fade-in">
      <!-- Premium Gate Stepper -->
      <div class="max-w-4xl mx-auto">
        <div class="flex items-center justify-between relative px-4">
          <!-- Background Line -->
          <div class="absolute top-6 left-10 right-10 h-1 bg-[var(--t-surface-raised)] rounded-full -z-10">
             <div class="h-full bg-gradient-to-r from-[var(--t-accent)] to-[var(--t-primary)] transition-all duration-1000"
                  [style.width.%]="stepperProgress()"></div>
          </div>

          @for (gate of gates(); track gate.id) {
            <div class="flex flex-col items-center group">
              <div 
                [class]="getGateCircleClass(gate)"
                class="w-12 h-12 rounded-full border-4 flex items-center justify-center transition-all duration-500 relative bg-[var(--t-bg)] z-10">
                @if (isGatePassed(gate)) {
                  <span class="material-icons text-white text-base">check</span>
                } @else {
                  <span class="font-bold text-sm">{{ gate.gate_number }}</span>
                }
                
                <!-- Active Pulse -->
                @if (isActiveGate(gate)) {
                  <div class="absolute inset-0 rounded-full animate-ping bg-[var(--t-accent)] opacity-20"></div>
                }
              </div>
              <div class="mt-4 text-center">
                <span class="block text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-primary)]">
                  {{ gate.label }}
                </span>
                <span class="text-[9px] font-medium text-[var(--t-text-tertiary)] uppercase tracking-tighter">
                  {{ getGateStatusText(gate) }}
                </span>
              </div>
            </div>
          }
        </div>
      </div>

      <!-- Active Gate Workspace -->
      @if (activeGate()) {
        <div class="grid grid-cols-1 xl:grid-cols-3 gap-8">
          
          <!-- Left: Submission Workspace -->
          <div class="xl:col-span-2 space-y-6">
            <div class="card p-0 overflow-hidden border-t-4 border-[var(--t-accent)]">
              <div class="p-8 border-b border-[var(--t-border)] flex justify-between items-start">
                <div>
                  <h3 class="text-xl font-bold text-[var(--t-text-primary)]">
                    {{ activeGate().label }} Readiness Review<span class="text-[var(--t-accent)]">.</span>
                  </h3>
                  <p class="text-xs font-medium text-[var(--t-text-secondary)] mt-1">Verify all criteria before submitting for transformation office approval.</p>
                </div>
                <span class="badge-purple font-bold text-[10px] uppercase tracking-widest px-3 py-1">
                  {{ activeSubmission() ? 'UNDER REVIEW' : 'DRAFTING' }}
                </span>
              </div>

              <div class="p-8 space-y-4">
                @for (item of criteria(); track item.id) {
                  <label class="flex items-start gap-4 p-5 rounded-2xl border border-[var(--t-border)] hover:bg-[var(--t-surface)] transition-all group cursor-pointer"
                         [class.opacity-60]="!!activeSubmission()">
                    <div class="relative mt-1">
                      <input 
                        type="checkbox" 
                        [(ngModel)]="item.ticked"
                        [disabled]="!!activeSubmission()"
                        class="peer sr-only">
                      <div class="w-6 h-6 rounded-lg border-2 border-[var(--t-border)] peer-checked:bg-[var(--t-accent)] peer-checked:border-[var(--t-accent)] transition-all flex items-center justify-center">
                        <span class="material-icons text-white text-sm scale-0 peer-checked:scale-100 transition-transform">check</span>
                      </div>
                    </div>
                    <div class="flex-1">
                      <span class="block font-bold text-[var(--t-text-primary)] group-hover:text-[var(--t-accent)] transition-colors">
                        {{ item.label }}
                      </span>
                      <p class="text-xs text-[var(--t-text-secondary)] mt-1 leading-relaxed">{{ item.guidance }}</p>
                    </div>
                  </label>
                }
              </div>

              @if (!activeSubmission()) {
                <div class="p-8 bg-[var(--t-surface-raised)] flex justify-end">
                  <button (click)="submitGate()" 
                          [disabled]="!allCriteriaTicked()"
                          class="btn-primary px-12 py-3 rounded-xl disabled:opacity-50 disabled:grayscale">
                    Submit for Approval
                  </button>
                </div>
              }
            </div>
          </div>

          <!-- Right: Decision & History -->
          <div class="space-y-6">
            <!-- Decision Panel (Admin only) -->
            @if (activeSubmission() && auth.getRole() === 'transformation_office') {
              <div class="card glass-panel border-l-4 border-amber-500 p-8 shadow-xl animate-fade-in">
                <div class="flex items-center gap-3 mb-6">
                  <div class="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                    <span class="material-icons text-amber-600">gavel</span>
                  </div>
                  <div>
                    <h4 class="font-bold text-[var(--t-text-primary)]">Pending Approval</h4>
                    <p class="text-[10px] text-[var(--t-text-secondary)] font-bold uppercase tracking-widest">Stage Gate Review</p>
                  </div>
                </div>
                
                <p class="text-xs text-[var(--t-text-secondary)] mb-6 leading-relaxed">
                  Review the checklist submitted by <span class="text-[var(--t-text-primary)] font-bold">{{ activeSubmission().submitted_by_name }}</span> and record a decision.
                </p>
                
                <textarea 
                  [(ngModel)]="decisionCommentary"
                  rows="3"
                  class="input-field w-full mb-6 text-sm" 
                  placeholder="Review comments or requirements..."></textarea>
                
                <div class="flex gap-3">
                  <button (click)="recordDecision('approved')" class="flex-1 btn-primary bg-green-600 hover:bg-green-700 border-none rounded-xl">Approve</button>
                  <button (click)="recordDecision('rejected')" class="flex-1 btn-ghost text-red-500 hover:bg-red-50 rounded-xl">Reject</button>
                </div>
              </div>
            }

            <!-- Decision History -->
            <div class="card p-0 overflow-hidden">
              <div class="p-5 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)]">
                <h4 class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">Decision History</h4>
              </div>
              <div class="p-5 space-y-4 max-h-[400px] overflow-y-auto">
                @for (entry of history(); track entry.id) {
                  <div class="p-4 rounded-2xl bg-[var(--t-bg)] border border-[var(--t-border)] relative">
                    <div class="flex justify-between items-center mb-3">
                      <span class="text-[10px] font-bold uppercase tracking-tighter px-2 py-0.5 rounded-full"
                            [style.background]="entry.decision === 'approved' ? 'var(--t-green)' : 'var(--t-red)'"
                            style="color:white">
                        {{ entry.decision }}
                      </span>
                      <span class="text-[var(--t-text-tertiary)] text-[10px] font-bold uppercase">{{ entry.decided_at | date:'MMM d' }}</span>
                    </div>
                    <p class="text-xs text-[var(--t-text-primary)] italic leading-relaxed mb-3">"{{ entry.commentary || 'No commentary provided.' }}"</p>
                    <div class="flex items-center gap-2 text-[9px] font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest">
                       <span class="material-icons text-[12px]">person</span>
                       {{ entry.decided_by_name }}
                    </div>
                  </div>
                }
                @if (history().length === 0) {
                  <div class="text-center py-10 opacity-50">
                    <span class="material-icons text-3xl mb-2">history</span>
                    <p class="text-xs font-medium uppercase tracking-widest">No history</p>
                  </div>
                }
              </div>
            </div>
          </div>
        </div>
      }
    </div>
  `
})
export class GovernanceTabComponent implements OnInit {
  @Input() initiativeId!: string;
  
  private readonly api = inject(ApiService);
  protected readonly auth = inject(AuthService);
  
  gates = signal<any[]>([]);
  criteria = signal<any[]>([]);
  activeSubmission = signal<any>(null);
  history = signal<any[]>([]);
  
  decisionCommentary = '';

  stepperProgress = computed(() => {
    const all = this.gates();
    if (all.length === 0) return 0;
    const passedCount = all.filter(g => this.isGatePassed(g)).length;
    return (passedCount / (all.length - 1)) * 100;
  });

  ngOnInit() {
    this.fetchStatus();
  }

  fetchStatus() {
    this.api.get<any>(`/initiatives/${this.initiativeId}/governance`).subscribe(data => {
      this.gates.set(data.gates || []);
      this.activeSubmission.set(data.active_submission);
      this.history.set(data.history || []);
      
      const currentGateNum = this.activeSubmission() ? this.activeSubmission().gate_number : (this.getNextGateNumber());
      this.fetchCriteria(currentGateNum);
    });
  }

  fetchCriteria(gateNum: number) {
    if (!gateNum) return;
    this.api.get<any[]>(`/governance/criteria/${gateNum}`).subscribe(list => {
      if (this.activeSubmission()) {
        this.criteria.set(this.activeSubmission().criteria_snapshot);
      } else {
        this.criteria.set(list.map((c: any) => ({ ...c, ticked: false })));
      }
    });
  }

  getNextGateNumber() {
    const passed = this.history().filter(h => h.decision === 'approved').map(h => h.gate_number);
    if (passed.length === 0) return 1;
    return Math.max(...passed) + 1;
  }

  allCriteriaTicked() {
    const list = this.criteria();
    return list.length > 0 && list.every(c => c.ticked);
  }

  getGateCircleClass(gate: any) {
    const isPassed = this.isGatePassed(gate);
    const isPending = this.activeSubmission()?.gate_number === gate.gate_number;
    
    if (isPassed) return 'bg-[var(--t-accent)] border-[var(--t-accent)] text-white';
    if (isPending) return 'border-amber-500 text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.3)]';
    return 'border-[var(--t-surface-raised)] text-[var(--t-text-tertiary)]';
  }

  getGateStatusText(gate: any) {
    if (this.isGatePassed(gate)) return 'Approved';
    if (this.activeSubmission()?.gate_number === gate.gate_number) return 'Reviewing';
    if (this.getNextGateNumber() === gate.gate_number) return 'In Progress';
    return 'Locked';
  }

  isGatePassed(gate: any) {
    return this.history().some(h => h.gate_number === gate.gate_number && h.decision === 'approved');
  }

  isActiveGate(gate: any) {
    const num = this.activeSubmission() ? this.activeSubmission().gate_number : this.getNextGateNumber();
    return gate.gate_number === num;
  }

  activeGate() {
    const num = this.activeSubmission() ? this.activeSubmission().gate_number : this.getNextGateNumber();
    return this.gates().find(g => g.gate_number === num);
  }

  submitGate() {
    const gateNum = this.getNextGateNumber();
    this.api.post(`/initiatives/${this.initiativeId}/gates/${gateNum}/submit`, {
      criteria_snapshot: this.criteria(),
      commentary: 'Ready for executive review'
    }).subscribe(() => this.fetchStatus());
  }

  recordDecision(decision: string) {
    if (!this.activeSubmission()) return;
    this.api.patch(`/governance/submissions/${this.activeSubmission().id}/decide`, {
      decision,
      commentary: this.decisionCommentary
    }).subscribe(() => {
      this.decisionCommentary = '';
      this.fetchStatus();
    });
  }
}
