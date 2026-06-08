import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import {
  BankablePlanResponse,
  BankablePlanVersion,
  GovernanceGate,
  GovernanceStatusResponse,
  GovernanceSubmission,
  InitiativeOption,
  PortfolioGovernanceResponse,
  decisionBadgeClass,
  formatDateTime,
  formatMoney,
  initiativeLabel,
  initiativeStage,
  selectDefaultInitiative,
} from './financials-view.models';

interface WaterlineGateRow {
  gate: GovernanceGate;
  submission: GovernanceSubmission | null;
  above: boolean;
}

@Component({
  selector: 'app-waterline',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Governance Waterline</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">
            Waterline<span class="text-[var(--t-blue-light)]">.</span>
          </h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Track which stage-gate submissions sit above the waterline, which ones are still below it, and how the locked plan snapshot aligns with the current governance stack.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <select
            class="input-field min-w-72 py-2 text-xs"
            [ngModel]="selectedInitiativeId()"
            (ngModelChange)="setSelectedInitiative($event)"
            aria-label="Select initiative for waterline view">
            @for (initiative of initiatives(); track initiative.id) {
              <option [value]="initiative.id">{{ initiativeLabel(initiative) }}</option>
            }
          </select>
          <a
            [routerLink]="['/initiatives', selectedInitiativeId(), 'financial-scope']"
            class="btn-secondary text-[10px]"
            [attr.aria-label]="'Open editable scope for ' + selectedInitiativeLabel()">
            Editable scope
          </a>
        </div>
      </header>

      @if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      <section class="grid gap-4 md:grid-cols-4">
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Health score</p>
          <p class="mt-3 text-3xl font-black text-[var(--t-text-primary)]">{{ portfolioGovernance()?.health_score || '0/0' }}</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Approved</p>
          <p class="mt-3 text-3xl font-black text-emerald-600">{{ portfolioGovernance()?.approved || 0 }}</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Pending</p>
          <p class="mt-3 text-3xl font-black text-[var(--t-amber)]">{{ portfolioGovernance()?.pending || 0 }}</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Rejected</p>
          <p class="mt-3 text-3xl font-black text-[var(--t-red)]">{{ portfolioGovernance()?.rejected || 0 }}</p>
        </div>
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div class="card overflow-hidden">
          <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
            <div>
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Stage-gate stack</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ selectedInitiativeLabel() }}</h2>
            </div>
            <span class="badge-muted">{{ initiativeStage(selectedInitiative()) }}</span>
          </div>

          <div class="divide-y divide-[var(--t-border)]">
            @for (row of gateRows(); track row.gate.gate_number) {
              <article class="grid gap-4 p-5 md:grid-cols-[120px_minmax(0,1fr)_180px] md:items-start">
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Gate</p>
                  <p class="mt-1 text-3xl font-black text-[var(--t-text-primary)]">{{ row.gate.gate_number }}</p>
                </div>
                <div>
                  <p class="text-sm font-black text-[var(--t-text-primary)]">{{ row.gate.label }}</p>
                  <p class="mt-2 text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    {{ row.gate.from_stage.replace('_', ' ') }} → {{ row.gate.to_stage.replace('_', ' ') }}
                  </p>
                  <p class="mt-2 text-xs text-[var(--t-text-secondary)]">
                    {{ row.submission?.commentary || 'No submission commentary recorded.' }}
                  </p>
                </div>
                <div class="space-y-2">
                  @if (row.submission) {
                    <span [ngClass]="decisionBadgeClass(row.submission.decision)">
                      {{ row.submission.decision }}
                    </span>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                      {{ formatDateTime(row.submission.submitted_at) }}
                    </p>
                    <p class="text-xs text-[var(--t-text-secondary)]">
                      Submitted by {{ row.submission.submitted_by_name || row.submission.submitted_by_id }}
                    </p>
                  } @else {
                    <span class="badge-muted">No submission</span>
                  }
                </div>
              </article>
            } @empty {
              <div class="p-8 text-sm font-bold text-[var(--t-text-secondary)]">
                No stage-gate context is available for the selected initiative.
              </div>
            }
          </div>
        </div>

        <div class="space-y-6">
          <div class="card p-5">
            <div class="flex items-center justify-between gap-3">
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Above / below waterline</p>
                <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Waterline visual</h2>
              </div>
              <span class="badge-muted">{{ gateRows().length }} gates</span>
            </div>

            <div class="mt-5 rounded-[1px] border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
              <div class="grid gap-5 lg:grid-cols-2">
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-emerald-600">Above waterline</p>
                  <div class="mt-3 space-y-3">
                    @for (row of aboveWaterlineRows(); track row.gate.gate_number) {
                      <div class="border-l-4 border-emerald-600 bg-[var(--t-surface)] p-3">
                        <p class="text-xs font-black text-[var(--t-text-primary)]">Gate {{ row.gate.gate_number }} · {{ row.gate.label }}</p>
                        <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.submission?.decision || 'approved' }}</p>
                      </div>
                    } @empty {
                      <p class="text-sm font-bold text-[var(--t-text-secondary)]">No approved submissions are above the line yet.</p>
                    }
                  </div>
                </div>

                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-red)]">Below waterline</p>
                  <div class="mt-3 space-y-3">
                    @for (row of belowWaterlineRows(); track row.gate.gate_number) {
                      <div class="border-l-4 border-[var(--t-red)] bg-[var(--t-surface)] p-3">
                        <p class="text-xs font-black text-[var(--t-text-primary)]">Gate {{ row.gate.gate_number }} · {{ row.gate.label }}</p>
                        <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ row.submission?.decision || 'pending' }}</p>
                      </div>
                    } @empty {
                      <p class="text-sm font-bold text-[var(--t-text-secondary)]">No pending or rejected submissions are below the line.</p>
                    }
                  </div>
                </div>
              </div>

              <div class="relative mt-6 border-t-2 border-[var(--t-border)] pt-4">
                <div class="absolute left-1/2 top-[-10px] -translate-x-1/2 bg-[var(--t-surface-raised)] px-3 text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
                  Waterline
                </div>
                <p class="text-xs font-bold text-[var(--t-text-secondary)]">
                  Approved submissions sit above the line; pending and rejected gates remain below it until the next decision.
                </p>
              </div>
            </div>
          </div>

          <div class="card border-l-4 border-[var(--t-accent)] p-5">
            <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked plan line</p>
            @if (currentPlan()) {
              <div class="mt-3 space-y-3">
                <div class="flex items-center justify-between gap-3">
                  <p class="text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(lockedPlanValue()) }}</p>
                  <span class="badge-muted">v{{ currentPlan()?.version }}</span>
                </div>
                <p class="text-sm font-bold text-[var(--t-text-secondary)]">
                  Locked {{ formatDateTime(currentPlan()?.locked_at) }}
                </p>
                <p class="text-sm leading-6 text-[var(--t-text-secondary)]">
                  {{ currentPlan()?.locked_reason || 'No lock reason supplied.' }}
                </p>
              </div>
            } @else {
              <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">
                No locked plan line exists yet. Once a submission is approved, the locked snapshot appears here and the plan line becomes read-only.
              </p>
            }
          </div>
        </div>
      </section>
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
export class WaterlineComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly initiativeLabel = initiativeLabel;
  readonly initiativeStage = initiativeStage;
  readonly formatMoney = formatMoney;
  readonly formatDateTime = formatDateTime;
  readonly decisionBadgeClass = decisionBadgeClass;

  readonly initiatives = signal<InitiativeOption[]>([]);
  readonly selectedInitiativeId = signal('');
  readonly selectedInitiative = computed(() => this.initiatives().find(item => item.id === this.selectedInitiativeId()) || null);
  readonly selectedInitiativeLabel = computed(() => initiativeLabel(this.selectedInitiative()));
  readonly portfolioGovernance = signal<PortfolioGovernanceResponse | null>(null);
  readonly governanceStatus = signal<GovernanceStatusResponse | null>(null);
  readonly bankablePlan = signal<BankablePlanResponse | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly currentPlan = computed(() => this.bankablePlan()?.current || null);
  readonly currentSnapshot = computed(() => this.currentPlan()?.snapshot || null);
  readonly lockedPlanValue = computed(() => this.currentSnapshot()?.summary.net_value_plan || '0.0000');
  readonly gateRows = computed<WaterlineGateRow[]>(() => {
    const status = this.governanceStatus();
    const gates = (status?.gates || []).slice().sort((a, b) => a.gate_number - b.gate_number);
    return gates.map(gate => {
      const submission = this.submissionForGate(gate.gate_number);
      return {
        gate,
        submission,
        above: Boolean(submission && ['approved', 'conditional'].includes(submission.decision)),
      };
    });
  });
  readonly aboveWaterlineRows = computed(() => this.gateRows().filter(row => row.above));
  readonly belowWaterlineRows = computed(() => this.gateRows().filter(row => !row.above));

  ngOnInit(): void {
    this.loadInitiatives();
  }

  setSelectedInitiative(initiativeId: string): void {
    if (!initiativeId || initiativeId === this.selectedInitiativeId()) return;
    this.selectedInitiativeId.set(initiativeId);
    this.loadSelectedViews();
  }

  private loadInitiatives(): void {
    this.api.get<any>('/initiatives', { page_size: 200 }).subscribe({
      next: response => {
        const items = (response.items || []) as InitiativeOption[];
        this.initiatives.set(items);
        const nextId = selectDefaultInitiative(items, this.selectedInitiativeId() || null);
        this.selectedInitiativeId.set(nextId);
        if (nextId) this.loadSelectedViews();
      },
      error: err => this.error.set(err?.error?.detail || 'Could not load initiatives.'),
    });
  }

  private loadSelectedViews(): void {
    const initiativeId = this.selectedInitiativeId();
    if (!initiativeId) return;

    this.loading.set(true);
    this.error.set(null);

    this.api.get<PortfolioGovernanceResponse>('/portfolio/governance').subscribe({
      next: response => this.portfolioGovernance.set(response),
      error: () => undefined,
    });

    this.api.get<GovernanceStatusResponse>(`/initiatives/${initiativeId}/governance`).subscribe({
      next: response => {
        this.governanceStatus.set(response);
        this.loading.set(false);
      },
      error: err => {
        this.error.set(err?.error?.detail || 'Could not load governance status.');
        this.governanceStatus.set(null);
        this.loading.set(false);
      },
    });

    this.api.get<BankablePlanResponse>(`/initiatives/${initiativeId}/bankable-plan`).subscribe({
      next: response => this.bankablePlan.set(response),
      error: () => this.bankablePlan.set(null),
    });
  }

  private submissionForGate(gateNumber: number): GovernanceSubmission | null {
    const status = this.governanceStatus();
    if (!status) return null;
    const active = status.active_submission;
    if (active?.gate_number === gateNumber) return active;
    const historyMatches = (status.history || []).filter(item => item.gate_number === gateNumber);
    return historyMatches.length ? historyMatches[0] : null;
  }
}
