import { CommonModule } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import {
  WorkstreamOption,
  WorkstreamTargetLockResponse,
  WorkstreamTargetLockVersion,
  WorkstreamTargetPreviewResponse,
  formatDateTime,
  formatMoney,
} from './financials-view.models';

@Component({
  selector: 'app-waterline',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Workstream Target Lock</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">
            Waterline<span class="text-[var(--t-blue-light)]">.</span>
          </h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Preview approved initiatives by cutoff date, lock the per-workstream net run-rate target, and compare actual realization against the frozen target line.
          </p>
        </div>

        <div class="flex flex-wrap items-center gap-3">
          <select
            class="input-field min-w-72 py-2 text-xs"
            [ngModel]="selectedWorkstreamId()"
            (ngModelChange)="setSelectedWorkstream($event)"
            aria-label="Select workstream for target lock">
            @for (workstream of workstreams(); track workstream.id) {
              <option [value]="workstream.id">{{ workstream.name }}</option>
            }
          </select>
          <input
            type="date"
            class="input-field py-2 text-xs"
            [ngModel]="lockDate()"
            (ngModelChange)="setLockDate($event)"
            aria-label="Workstream target lock date">
          <button
            type="button"
            class="btn-secondary text-[10px]"
            [disabled]="loading()"
            (click)="loadPreview()"
            aria-label="Preview workstream target lock">
            Preview
          </button>
          <button
            type="button"
            class="btn-primary text-[10px]"
            [disabled]="loading() || !preview()"
            (click)="lockTarget()"
            aria-label="Lock workstream target snapshot">
            Lock target
          </button>
        </div>
      </header>

      @if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      <section class="grid gap-4 md:grid-cols-4">
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Target basis</p>
          <p class="mt-3 text-lg font-black text-[var(--t-text-primary)]">{{ targetBasisLabel() }}</p>
          <p class="mt-2 text-xs font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Run-rate valuation</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked target</p>
          <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(preview()?.locked_run_rate_value) }}</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Actuals</p>
          <p class="mt-3 text-2xl font-black text-[var(--t-text-primary)]">{{ formatMoney(preview()?.actual_total) }}</p>
        </div>
        <div class="card p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Variance</p>
          <p class="mt-3 text-2xl font-black" [class.text-emerald-600]="varianceNumber() >= 0" [class.text-red-500]="varianceNumber() < 0">
            {{ formatMoney(preview()?.variance) }}
          </p>
        </div>
      </section>

      <section class="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <div class="card overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--t-border)] p-5">
            <div>
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Included initiatives</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">{{ selectedWorkstreamName() }}</h2>
            </div>
            <span class="badge-muted">{{ preview()?.included?.length || 0 }} approved by cutoff</span>
          </div>

          <div class="overflow-x-auto">
            <table class="w-full min-w-[820px] text-left text-xs">
              <thead class="bg-[var(--t-surface-raised)] text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                <tr>
                  <th class="px-4 py-3">Initiative</th>
                  <th class="px-4 py-3">Approved</th>
                  <th class="px-4 py-3">Source</th>
                  <th class="px-4 py-3 text-right">Net run-rate</th>
                  <th class="px-4 py-3 text-right">Actual</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--t-border)]">
                @for (initiative of preview()?.included || []; track initiative.initiative_id) {
                  <tr class="hover:bg-[var(--t-surface-raised)]">
                    <td class="px-4 py-3">
                      <p class="font-black text-[var(--t-text-primary)]">{{ initiative.initiative_code || 'INIT' }} · {{ initiative.name }}</p>
                      <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ initiative.stage || 'unknown' }}</p>
                    </td>
                    <td class="px-4 py-3 text-[var(--t-text-secondary)]">{{ formatDateTime(initiative.approved_at) }}</td>
                    <td class="px-4 py-3">
                      <span class="badge-muted">{{ sourceLabel(initiative.value_source, initiative.bankable_plan_version) }}</span>
                    </td>
                    <td class="px-4 py-3 text-right font-black text-[var(--t-text-primary)]">{{ formatMoney(initiative.net_run_rate_value) }}</td>
                    <td class="px-4 py-3 text-right font-bold text-[var(--t-text-secondary)]">{{ formatMoney(initiative.actual_value) }}</td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="5" class="px-4 py-8 text-sm font-bold text-[var(--t-text-secondary)]">
                      No approved initiatives qualify for the selected workstream and cutoff date.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <div class="space-y-6">
          <div class="card overflow-hidden">
            <div class="border-b border-[var(--t-border)] p-5">
              <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Excluded / pending</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Below cutoff</h2>
            </div>
            <div class="divide-y divide-[var(--t-border)]">
              @for (initiative of preview()?.excluded || []; track initiative.initiative_id) {
                <article class="p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-black text-[var(--t-text-primary)]">{{ initiative.initiative_code || 'INIT' }} · {{ initiative.name }}</p>
                      <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ initiative.stage || 'unknown' }}</p>
                    </div>
                    <span class="badge-muted">Pending</span>
                  </div>
                  <p class="mt-3 text-xs text-[var(--t-text-secondary)]">Preview value: {{ formatMoney(initiative.net_run_rate_value) }}</p>
                </article>
              } @empty {
                <div class="p-5 text-sm font-bold text-[var(--t-text-secondary)]">No pending initiatives below the line.</div>
              }
            </div>
          </div>

          <div class="card overflow-hidden">
            <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
              <div>
                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Lock history</p>
                <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Immutable snapshots</h2>
              </div>
              <span class="badge-muted">{{ history().length }} versions</span>
            </div>
            <div class="divide-y divide-[var(--t-border)]">
              @for (version of history(); track version.id) {
                <article class="p-4">
                  <div class="flex items-start justify-between gap-3">
                    <div>
                      <p class="text-sm font-black text-[var(--t-text-primary)]">v{{ version.version }} · {{ formatMoney(version.locked_run_rate_value) }}</p>
                      <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">Locked {{ formatDateTime(version.locked_at) }}</p>
                    </div>
                    <span class="badge-muted">{{ version.locked_value_basis.replace('_', ' ') }}</span>
                  </div>
                  <p class="mt-3 text-xs text-[var(--t-text-secondary)]">
                    {{ version.included_initiative_ids.length }} included · variance {{ formatMoney(version.variance) }}
                  </p>
                </article>
              } @empty {
                <div class="p-5 text-sm font-bold text-[var(--t-text-secondary)]">No workstream target locks yet.</div>
              }
            </div>
          </div>
        </div>
      </section>
    </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; }
    .badge-muted {
      @apply inline-flex items-center border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-2.5 py-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-secondary)];
    }
  `],
})
export class WaterlineComponent implements OnInit {
  private readonly api = inject(ApiService);

  readonly formatMoney = formatMoney;
  readonly formatDateTime = formatDateTime;

  readonly workstreams = signal<WorkstreamOption[]>([]);
  readonly selectedWorkstreamId = signal('');
  readonly lockDate = signal(new Date().toISOString().slice(0, 10));
  readonly preview = signal<WorkstreamTargetPreviewResponse | null>(null);
  readonly lockResponse = signal<WorkstreamTargetLockResponse | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  readonly selectedWorkstreamName = computed(() => {
    const selected = this.workstreams().find(item => item.id === this.selectedWorkstreamId());
    return selected?.name || 'Select a workstream';
  });
  readonly history = computed<WorkstreamTargetLockVersion[]>(() => this.lockResponse()?.history || []);
  readonly varianceNumber = computed(() => Number(this.preview()?.variance || 0));
  readonly targetBasisLabel = computed(() => {
    const basis = this.preview()?.settings?.locked_value_basis || 'net_run_rate';
    return basis.replace(/_/g, ' ');
  });

  ngOnInit(): void {
    this.loadWorkstreams();
  }

  setSelectedWorkstream(workstreamId: string): void {
    if (!workstreamId || workstreamId === this.selectedWorkstreamId()) return;
    this.selectedWorkstreamId.set(workstreamId);
    this.loadAll();
  }

  setLockDate(value: string): void {
    this.lockDate.set(value || new Date().toISOString().slice(0, 10));
    this.loadPreview();
  }

  lockTarget(): void {
    const workstreamId = this.selectedWorkstreamId();
    if (!workstreamId) return;
    this.loading.set(true);
    this.error.set(null);
    this.api.post<WorkstreamTargetLockVersion>(`/workstreams/${workstreamId}/target-lock`, {
      lock_date: this.lockDate(),
    }).subscribe({
      next: () => {
        this.loading.set(false);
        this.loadAll();
      },
      error: err => {
        this.loading.set(false);
        this.error.set(err?.error?.detail || 'Could not lock workstream target.');
      },
    });
  }

  loadPreview(): void {
    const workstreamId = this.selectedWorkstreamId();
    if (!workstreamId) return;
    this.loading.set(true);
    this.error.set(null);
    const params = new URLSearchParams({ lock_date: this.lockDate() });
    this.api.get<WorkstreamTargetPreviewResponse>(`/workstreams/${workstreamId}/target-lock/preview?${params.toString()}`).subscribe({
      next: response => {
        this.preview.set(response);
        this.loading.set(false);
      },
      error: err => {
        this.preview.set(null);
        this.loading.set(false);
        this.error.set(err?.error?.detail || 'Could not preview workstream target.');
      },
    });
  }

  sourceLabel(source: string, version?: number | null): string {
    if (source === 'bankable_plan') return version ? `Bankable v${version}` : 'Bankable plan';
    return 'Current preview';
  }

  private loadWorkstreams(): void {
    this.api.get<{ items?: WorkstreamOption[]; data?: WorkstreamOption[] }>('/workstreams').subscribe({
      next: response => {
        const items = response.items || response.data || [];
        this.workstreams.set(items);
        const nextId = this.selectedWorkstreamId() || items[0]?.id || '';
        this.selectedWorkstreamId.set(nextId);
        if (nextId) this.loadAll();
      },
      error: err => this.error.set(err?.error?.detail || 'Could not load workstreams.'),
    });
  }

  private loadAll(): void {
    this.loadPreview();
    this.loadHistory();
  }

  private loadHistory(): void {
    const workstreamId = this.selectedWorkstreamId();
    if (!workstreamId) return;
    this.api.get<WorkstreamTargetLockResponse>(`/workstreams/${workstreamId}/target-lock`).subscribe({
      next: response => this.lockResponse.set(response),
      error: () => this.lockResponse.set(null),
    });
  }
}
