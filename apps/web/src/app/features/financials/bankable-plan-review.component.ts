import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import {
  BankablePlanResponse,
  BankablePlanVersion,
  GovernanceStatusResponse,
  GovernanceSubmission,
  InitiativeOption,
  formatDateTime,
  formatMoney,
  initiativeLabel,
  initiativeStage,
  selectDefaultInitiative,
} from './financials-view.models';

@Component({
  selector: 'app-bankable-plan-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financial Review</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">
            Bankable Plan<span class="text-[var(--t-blue-light)]">.</span>
          </h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Review the locked bankable plan snapshot, compare versions, and jump to the editable financial scope for the selected initiative.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <select
            class="input-field min-w-72 py-2 text-xs"
            [ngModel]="selectedInitiativeId()"
            (ngModelChange)="setSelectedInitiative($event)"
            aria-label="Select initiative for bankable plan review">
            @for (initiative of initiatives(); track initiative.id) {
              <option [value]="initiative.id">{{ initiativeLabel(initiative) }}</option>
            }
          </select>
          <a
            [routerLink]="['/initiatives', selectedInitiativeId(), 'financial-scope']"
            class="btn-secondary text-[10px]"
            [attr.aria-label]="'Open editable financial scope for ' + selectedInitiativeLabel()">
            Edit scope
          </a>
          <button
            type="button"
            class="btn-primary text-[10px]"
            [disabled]="!currentPlan() || !!pendingRebaseline() || submittingRebaseline()"
            (click)="openRebaselineModal()"
            aria-label="Request bankable plan rebaseline">
            Request rebaseline
          </button>
        </div>
      </header>

      @if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      @if (pendingRebaseline()) {
        <section class="border-l-4 border-amber-500 bg-[var(--t-surface)] p-5">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-[9px] font-black uppercase tracking-widest text-amber-600">Rebaseline request pending</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">
                v{{ pendingRebaseline()?.requested_bankable_plan_version || 'next' }} is awaiting governance approval.
              </h2>
              <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
                {{ pendingRebaseline()?.commentary || 'No request reason supplied.' }}
              </p>
            </div>
            <a routerLink="/pmo/governance" [queryParams]="{ status: 'pending' }" class="btn-secondary text-[10px]" aria-label="Open governance approval queue">
              Open governance queue
            </a>
          </div>
        </section>
      }

      <section class="grid gap-4 md:grid-cols-3">
        <div class="card p-5 md:col-span-2">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Selected initiative</p>
              <h2 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ selectedInitiativeLabel() }}</h2>
              <p class="mt-2 text-sm font-bold text-[var(--t-text-secondary)]">Stage: {{ selectedInitiativeStage() }}</p>
            </div>
            <div class="flex flex-wrap items-center gap-2">
              <span
                class="badge"
                [class.bg-[var(--t-red-soft)]]="planState() === 'locked'"
                [class.text-[var(--t-red)]]="planState() === 'locked'"
                [class.border-[var(--t-red)]/20]="planState() === 'locked'"
                [class.bg-[var(--t-accent-soft)]]="planState() === 'editable'"
                [class.text-[var(--t-accent)]]="planState() === 'editable'"
                [class.border-[var(--t-accent)]/20]="planState() === 'editable'"
                aria-label="Plan state badge">
                {{ planState() === 'locked' ? 'Locked' : 'Editable' }}
              </span>
              <span class="badge-muted">{{ planVersionLabel() }}</span>
            </div>
          </div>

          <div class="mt-6 grid gap-4 md:grid-cols-2">
            <div class="border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] p-5">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked bankable plan</p>
              @if (currentPlan()) {
                <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().net_value_plan) }}</p>
                <p class="mt-1 text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                  Locked {{ formatDateTime(currentPlan()?.locked_at) }}
                </p>
                <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">
                  {{ currentPlan()?.locked_reason || 'No lock reason supplied.' }}
                </p>
              } @else {
                <p class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">No locked plan</p>
                <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">
                  This initiative is still in editable mode. Once governance approves a submission, the bankable plan snapshot appears here as read-only.
                </p>
              }
            </div>

            <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Editable source</p>
              <p class="mt-2 text-lg font-black text-[var(--t-text-primary)]">Financial scope</p>
              <p class="mt-2 text-sm leading-6 text-[var(--t-text-secondary)]">
                Review which metrics and cost categories feed the plan. This is the editable control surface; the locked bankable plan below does not change until a new approval or rebaseline.
              </p>
              <a
                [routerLink]="['/initiatives', selectedInitiativeId(), 'financial-scope']"
                class="btn-primary mt-4 inline-flex text-[10px]"
                [attr.aria-label]="'Open editable financial scope for ' + selectedInitiativeLabel()">
                Open editable scope
              </a>
            </div>
          </div>
        </div>

        <aside class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Snapshot summary</p>
          <div class="mt-4 space-y-4">
            <div>
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Net value plan</p>
              <p class="mt-1 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(summary().net_value_plan) }}</p>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div class="border border-[var(--t-border)] p-3">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Entries</p>
                <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ entryCount() }}</p>
              </div>
              <div class="border border-[var(--t-border)] p-3">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Cost lines</p>
                <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ costLineCount() }}</p>
              </div>
              <div class="border border-[var(--t-border)] p-3">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Metrics</p>
                <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ metricValueCount() }}</p>
              </div>
              <div class="border border-[var(--t-border)] p-3">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Selections</p>
                <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">
                  {{ selectionCount() }}
                </p>
              </div>
            </div>
          </div>
        </aside>
      </section>

      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
          <div>
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Version history</p>
            <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Locked snapshots and rebaseline trail</h2>
          </div>
          <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
            {{ history().length }} version{{ history().length === 1 ? '' : 's' }}
          </span>
        </div>

        <div class="divide-y divide-[var(--t-border)]">
          @if (history().length) {
            @for (version of history(); track version.id) {
              <article class="grid gap-4 p-5 md:grid-cols-[140px_minmax(0,1fr)_220px] md:items-start">
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Version</p>
                  <p class="mt-1 text-2xl font-black text-[var(--t-text-primary)]">v{{ version.version }}</p>
                  <span class="badge-muted mt-3 inline-flex">{{ version.trigger_type }}</span>
                </div>
                <div>
                  <p class="text-sm font-black text-[var(--t-text-primary)]">{{ version.locked_reason || 'No lock reason supplied' }}</p>
                  <p class="mt-2 text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    Locked {{ formatDateTime(version.locked_at) }}
                  </p>
                  <p class="mt-2 text-xs text-[var(--t-text-secondary)]">
                    Trigger submission: {{ version.trigger_submission_id || '—' }} · Locked by: {{ version.locked_by_id || '—' }}
                  </p>
                </div>
                <div class="grid gap-2 text-xs">
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                    <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Net plan</p>
                    <p class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ formatMoney(version.snapshot.summary.net_value_plan) }}</p>
                  </div>
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-3">
                    <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Lock status</p>
                    <p class="mt-1 text-sm font-black" [class.text-[var(--t-red)]]="true">Read only</p>
                  </div>
                </div>
              </article>
            }
          } @else {
            <div class="p-8 text-sm font-bold text-[var(--t-text-secondary)]">
              No locked versions yet for this initiative.
            </div>
          }
        </div>
      </section>

      @if (showRebaselineModal()) {
        <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true" aria-label="Request bankable plan rebaseline">
          <div class="w-full max-w-2xl border border-[var(--t-border)] bg-[var(--t-surface)] p-6 shadow-2xl">
            <div class="flex items-start justify-between gap-4 border-b border-[var(--t-border)] pb-4">
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-accent)]">Governed baseline change</p>
                <h2 class="mt-1 text-xl font-black text-[var(--t-text-primary)]">Request rebaseline approval</h2>
                <p class="mt-2 text-sm leading-6 text-[var(--t-text-secondary)]">
                  Approval will create v{{ nextRebaselineVersion() }} from the current editable financial scope. Until approved, Benefit Tracking, Waterline, dashboards, and board-pack exports continue using v{{ currentPlan()?.version }}.
                </p>
              </div>
              <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="closeRebaselineModal()" aria-label="Close rebaseline request dialog">
                Close
              </button>
            </div>

            <div class="mt-5 grid gap-4 md:grid-cols-2">
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Current locked version</p>
                <p class="mt-1 text-2xl font-black text-[var(--t-text-primary)]">v{{ currentPlan()?.version }}</p>
                <p class="mt-2 text-sm font-bold text-[var(--t-text-secondary)]">{{ formatMoney(summary().net_value_plan) }}</p>
              </div>
              <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Requested version</p>
                <p class="mt-1 text-2xl font-black text-[var(--t-text-primary)]">v{{ nextRebaselineVersion() }}</p>
                <p class="mt-2 text-sm font-bold text-[var(--t-text-secondary)]">Captured only after approval</p>
              </div>
            </div>

            <label class="mt-5 block">
              <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Reason for rebaseline</span>
              <textarea
                class="input-field mt-2 min-h-32 w-full text-sm"
                [(ngModel)]="rebaselineReason"
                aria-label="Reason for bankable plan rebaseline"
                placeholder="Describe the approved scope, timing, assumption, or value change that requires a new baseline."></textarea>
            </label>

            @if (rebaselineError()) {
              <p class="mt-3 text-sm font-bold text-red-500">{{ rebaselineError() }}</p>
            }

            <div class="mt-6 flex justify-end gap-3">
              <button type="button" class="btn-secondary text-[10px]" (click)="closeRebaselineModal()" aria-label="Cancel rebaseline request">
                Cancel
              </button>
              <button
                type="button"
                class="btn-primary text-[10px]"
                [disabled]="submittingRebaseline() || rebaselineReason.trim().length < 10"
                (click)="submitRebaselineRequest()"
                aria-label="Submit rebaseline request for governance approval">
                Submit request
              </button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }
    .badge {
      @apply inline-flex items-center border px-2.5 py-1 text-[10px] font-black uppercase tracking-widest;
    }
    .badge-muted {
      @apply inline-flex items-center border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)];
    }
  `],
})
export class BankablePlanReviewComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly initiativeLabel = initiativeLabel;
  readonly initiativeStage = initiativeStage;
  readonly formatMoney = formatMoney;
  readonly formatDateTime = formatDateTime;

  readonly initiatives = signal<InitiativeOption[]>([]);
  readonly selectedInitiativeId = signal('');
  readonly selectedInitiative = computed(() => this.initiatives().find(item => item.id === this.selectedInitiativeId()) || null);
  readonly selectedInitiativeLabel = computed(() => initiativeLabel(this.selectedInitiative()));
  readonly selectedInitiativeStage = computed(() => initiativeStage(this.selectedInitiative()));
  readonly bankablePlan = signal<BankablePlanResponse | null>(null);
  readonly history = signal<BankablePlanVersion[]>([]);
  readonly governance = signal<GovernanceStatusResponse | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly showRebaselineModal = signal(false);
  readonly submittingRebaseline = signal(false);
  readonly rebaselineError = signal<string | null>(null);
  rebaselineReason = '';

  readonly currentPlan = computed(() => this.bankablePlan()?.current || null);
  readonly currentSnapshot = computed(() => this.currentPlan()?.snapshot || null);
  readonly planState = computed(() => (this.currentPlan() ? 'locked' : 'editable'));
  readonly planVersionLabel = computed(() => this.currentPlan() ? `v${this.currentPlan()?.version}` : 'No version locked');
  readonly summary = computed(() => this.currentSnapshot()?.summary || { net_value_plan: '0.0000', net_value_actual: null });
  readonly entryCount = computed(() => this.currentSnapshot() ? this.currentSnapshot()!.entries.length : 0);
  readonly costLineCount = computed(() => this.currentSnapshot() ? this.currentSnapshot()!.cost_lines.length : 0);
  readonly metricValueCount = computed(() => this.currentSnapshot() ? this.currentSnapshot()!.metric_values.length : 0);
  readonly selectionCount = computed(() => {
    const snapshot = this.currentSnapshot();
    const selections = snapshot?.selections;
    return (selections?.metric_keys.length || 0) + (selections?.cost_category_keys.length || 0);
  });
  readonly pendingRebaseline = computed<GovernanceSubmission | null>(() => {
    const rows = this.governance()?.history || [];
    return rows.find(row => row.submission_type === 'bankable_plan_rebaseline' && row.decision === 'pending') || null;
  });
  readonly nextRebaselineVersion = computed(() => (this.currentPlan()?.version || 0) + 1);

  ngOnInit(): void {
    this.loadInitiatives();
  }

  setSelectedInitiative(initiativeId: string): void {
    if (!initiativeId || initiativeId === this.selectedInitiativeId()) return;
    this.selectedInitiativeId.set(initiativeId);
    this.loadPlan();
  }

  private loadInitiatives(): void {
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe({
      next: response => {
        const items = (response.items || []) as InitiativeOption[];
        this.initiatives.set(items);
        const nextId = selectDefaultInitiative(items, this.selectedInitiativeId() || response?.selected_initiative_id || null);
        this.selectedInitiativeId.set(nextId);
        if (nextId) this.loadPlan();
      },
      error: err => {
        this.error.set(err?.error?.detail || 'Could not load initiatives.');
      },
    });
  }

  private loadPlan(): void {
    const initiativeId = this.selectedInitiativeId();
    if (!initiativeId) return;

    this.loading.set(true);
    this.error.set(null);

    this.api.get<BankablePlanResponse>(`/initiatives/${initiativeId}/bankable-plan`).subscribe({
      next: response => {
        this.bankablePlan.set(response);
        this.history.set((response.history || []).slice().sort((a, b) => b.version - a.version));
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err?.error?.detail || 'Could not load bankable plan.');
        this.bankablePlan.set(null);
        this.history.set([]);
        this.loading.set(false);
      },
    });

    this.api.get<BankablePlanVersion[]>(`/initiatives/${initiativeId}/bankable-plan/history`).subscribe({
      next: history => {
        if (history?.length) {
          this.history.set(history.slice().sort((a, b) => b.version - a.version));
        }
      },
      error: () => undefined,
    });
    this.loadGovernance();
  }

  openRebaselineModal(): void {
    if (!this.currentPlan() || this.pendingRebaseline()) return;
    this.rebaselineReason = '';
    this.rebaselineError.set(null);
    this.showRebaselineModal.set(true);
  }

  closeRebaselineModal(): void {
    if (this.submittingRebaseline()) return;
    this.showRebaselineModal.set(false);
    this.rebaselineError.set(null);
  }

  submitRebaselineRequest(): void {
    const initiativeId = this.selectedInitiativeId();
    const reason = this.rebaselineReason.trim();
    if (!initiativeId || reason.length < 10) return;

    this.submittingRebaseline.set(true);
    this.rebaselineError.set(null);
    this.api.post<GovernanceSubmission>(`/initiatives/${initiativeId}/bankable-plan/rebaseline`, { reason }).subscribe({
      next: () => {
        this.submittingRebaseline.set(false);
        this.showRebaselineModal.set(false);
        this.loadPlan();
      },
      error: err => {
        this.submittingRebaseline.set(false);
        this.rebaselineError.set(err?.error?.detail || 'Could not submit rebaseline request.');
      },
    });
  }

  private loadGovernance(): void {
    const initiativeId = this.selectedInitiativeId();
    if (!initiativeId) return;
    this.api.get<GovernanceStatusResponse>(`/initiatives/${initiativeId}/governance`).subscribe({
      next: response => this.governance.set(response),
      error: () => this.governance.set(null),
    });
  }
}
