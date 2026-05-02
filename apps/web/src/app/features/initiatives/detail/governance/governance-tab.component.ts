import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../../../core/services/api.service';
import { AuthService } from '../../../../core/services/auth.service';

@Component({
  selector: 'app-governance-tab',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-8 animate-fade-in">
      <!-- Gate Stepper -->
      <div class="flex items-center justify-between max-w-2xl mx-auto mb-12">
        <div *ngFor="let gate of gates(); let i = index" class="flex items-center flex-1 last:flex-none">
          <div class="relative flex flex-col items-center">
            <div 
              [class]="getGateCircleClass(gate)"
              class="w-12 h-12 rounded-full border-4 flex items-center justify-center transition-all duration-500">
              <span class="font-bold">{{ gate.gate_number }}</span>
            </div>
            <span class="absolute -bottom-6 text-xs font-semibold whitespace-nowrap text-[var(--t-text-secondary)]">
              {{ gate.label }}
            </span>
          </div>
          <div 
            *ngIf="i < gates().length - 1" 
            class="flex-1 h-1 mx-4 bg-[var(--t-border)] rounded-full">
            <div 
              class="h-full bg-[var(--t-primary)] transition-all duration-1000"
              [style.width]="isGatePassed(gate) ? '100%' : '0%'">
            </div>
          </div>
        </div>
      </div>

      <!-- Active Gate Workspace -->
      <div *ngIf="activeGate()" class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Left: Checklist -->
        <div class="lg:col-span-2 space-y-6">
          <div class="card p-6">
            <div class="flex justify-between items-center mb-6">
              <h3 class="text-lg font-semibold text-[var(--t-text-primary)]">
                {{ activeGate().label }} Checklist
              </h3>
              <span class="badge" [class.badge-purple]="!activeSubmission()">
                {{ activeSubmission() ? 'Awaiting Review' : 'Ready to Submit' }}
              </span>
            </div>

            <div class="space-y-3">
              <div *ngFor="let item of criteria()" 
                   class="flex items-start gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-bg-card)] transition-colors group">
                <input 
                  type="checkbox" 
                  [(ngModel)]="item.ticked"
                  [disabled]="!!activeSubmission()"
                  class="mt-1 w-5 h-5 rounded border-[var(--t-border)] text-[var(--t-primary)] focus:ring-[var(--t-primary)]">
                <div class="flex-1">
                  <span class="block font-medium text-[var(--t-text-primary)] group-hover:text-[var(--t-primary)] transition-colors">
                    {{ item.label }}
                  </span>
                  <span class="text-sm text-[var(--t-text-tertiary)]">{{ item.guidance }}</span>
                </div>
              </div>
            </div>

            <div class="mt-8 flex justify-end gap-3" *ngIf="!activeSubmission()">
              <button (click)="submitGate()" 
                      [disabled]="!allCriteriaTicked()"
                      class="btn-primary px-8 disabled:opacity-50">
                Submit for Approval
              </button>
            </div>
          </div>
        </div>

        <!-- Right: Actions & Decision -->
        <div class="space-y-6">
          <!-- Pending Decision Panel (Admin only) -->
          <div *ngIf="activeSubmission() && auth.getRole() === 'transformation_office'" class="card glass-panel border-l-4 border-amber-500 p-6 animate-pulse-subtle">
            <h4 class="font-bold text-amber-500 mb-4 flex items-center gap-2">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
              Pending Approval
            </h4>
            <p class="text-sm text-[var(--t-text-secondary)] mb-6">
              Please review the checklist submitted by {{ activeSubmission().submitted_by_name }}.
            </p>
            
            <textarea 
              [(ngModel)]="decisionCommentary"
              class="input-field w-full mb-4 text-sm" 
              placeholder="Add review comments..."></textarea>
            
            <div class="flex gap-2">
              <button (click)="recordDecision('approved')" class="flex-1 btn-primary bg-green-600 hover:bg-green-700 border-none">Approve</button>
              <button (click)="recordDecision('rejected')" class="flex-1 btn-ghost text-red-500 hover:bg-red-500/10">Reject</button>
            </div>
          </div>

          <!-- History Audit -->
          <div class="card p-5">
            <h4 class="text-xs font-bold text-[var(--t-text-tertiary)] uppercase tracking-widest mb-4">Decision History</h4>
            <div class="space-y-4">
              <div *ngFor="let entry of history()" class="text-sm p-3 rounded-lg bg-[var(--t-bg-page)] border border-[var(--t-border)]">
                <div class="flex justify-between items-center mb-2">
                  <span class="font-bold" [class.text-green-500]="entry.decision === 'approved'" [class.text-red-500]="entry.decision === 'rejected'">
                    {{ entry.decision | uppercase }}
                  </span>
                  <span class="text-[var(--t-text-tertiary)] text-xs">{{ entry.decided_at | date:'shortDate' }}</span>
                </div>
                <p class="text-xs text-[var(--t-text-secondary)] italic">"{{ entry.commentary }}"</p>
                <div class="mt-2 text-[10px] text-[var(--t-text-tertiary)]">Reviewed by {{ entry.decided_by_name }}</div>
              </div>
              <div *ngIf="history().length === 0" class="text-center py-4 text-[var(--t-text-tertiary)] text-xs">No history yet.</div>
            </div>
          </div>
        </div>
      </div>
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
      // If we have an active submission, use the snapshot instead of fresh list
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
    return this.criteria().length > 0 && this.criteria().every(c => c.ticked);
  }

  getGateCircleClass(gate: any) {
    const isPassed = this.isGatePassed(gate);
    const isPending = this.activeSubmission()?.gate_number === gate.gate_number;
    
    if (isPassed) return 'bg-[var(--t-primary)] border-[var(--t-primary)] text-white';
    if (isPending) return 'border-amber-500 text-amber-500';
    return 'border-[var(--t-border)] text-[var(--t-text-tertiary)]';
  }

  isGatePassed(gate: any) {
    return this.history().some(h => h.gate_number === gate.gate_number && h.decision === 'approved');
  }

  activeGate() {
    const num = this.activeSubmission() ? this.activeSubmission().gate_number : this.getNextGateNumber();
    return this.gates().find(g => g.gate_number === num);
  }

  submitGate() {
    const gateNum = this.getNextGateNumber();
    this.api.post(`/initiatives/${this.initiativeId}/gates/${gateNum}/submit`, {
      criteria_snapshot: this.criteria(),
      commentary: 'Submitted for review'
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
