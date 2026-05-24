import { CommonModule } from '@angular/common';
import { Component, Input, OnInit, WritableSignal, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface FinancialConfigGroup {
  key: string;
  label: string;
  kind: 'calculation' | 'metric' | 'cost_category';
  display_order: number;
  is_active: boolean;
}

interface FinancialConfigItem {
  key: string;
  label: string;
  item_type: 'metric' | 'cost_category';
  system_metric_key?: string | null;
  rollup_type?: string | null;
  group_key?: string | null;
  display_order: number;
  is_system: boolean;
  is_active: boolean;
}

interface FinancialSelectionsResponse {
  available: {
    groups: FinancialConfigGroup[];
    items: FinancialConfigItem[];
  };
  selected: {
    metric_keys: string[];
    cost_category_keys: string[];
  };
  locked: boolean;
  lock_reason: string | null;
}

@Component({
  selector: 'app-financial-scope',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <div class="mx-auto max-w-6xl space-y-6 p-8">
      <div class="flex items-center justify-between gap-4">
        <div>
          <a [routerLink]="['/initiatives', id]" class="text-xs font-bold uppercase text-[var(--t-text-secondary)] hover:text-[var(--t-accent)]">
            Back to initiative
          </a>
          <h1 class="mt-3 text-3xl font-black tracking-tight text-[var(--t-text-primary)]">
            Financial Scope<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="mt-2 text-sm text-[var(--t-text-secondary)]">{{ initiativeName() || 'Select which financial rows are active for this initiative.' }}</p>
        </div>
        <button
          type="button"
          class="btn-primary inline-flex items-center gap-2"
          [disabled]="saving() || !loaded()"
          (click)="save()"
          aria-label="Save financial scope">
          <span class="material-icons text-base">save</span>
          {{ saving() ? 'Saving...' : 'Save Scope' }}
        </button>
      </div>

      @if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      @if (saved()) {
        <div class="border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm font-bold text-emerald-600">
          Financial scope saved.
        </div>
      }

      @if (locked()) {
        <div class="border-l-4 border-[var(--t-accent)] bg-[var(--t-surface-raised)] px-4 py-3 text-sm text-[var(--t-text-secondary)]">
          <span class="font-bold text-[var(--t-text-primary)]">Financial values are locked.</span>
          Scope changes are still available to the transformation office.
        </div>
      }

      @if (loaded()) {
        <div class="grid gap-6 xl:grid-cols-2">
          <section class="card p-6">
            <div class="mb-5">
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Financial Metrics</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Rows shown in Initiative Financials</h2>
            </div>
            <div class="space-y-5">
              @for (group of metricGroups(); track group.key) {
                <div class="border border-[var(--t-border)]">
                  <div class="bg-[var(--t-surface-raised)] px-4 py-3">
                    <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">{{ group.label }}</p>
                  </div>
                  <div class="divide-y divide-[var(--t-border)]">
                    @for (metric of itemsForGroup(group.key, 'metric'); track metric.key) {
                      <label class="flex items-center gap-3 px-4 py-3 text-sm text-[var(--t-text-primary)]">
                        <input
                          type="checkbox"
                          [checked]="isMetricSelected(metric)"
                          (change)="toggleMetric(metric, $any($event.target).checked)"
                          aria-label="Toggle financial metric">
                        <span class="min-w-0 flex-1 truncate">{{ metric.label }}</span>
                        <span class="font-mono text-[10px] text-[var(--t-text-tertiary)]">{{ financialMetricKey(metric) }}</span>
                      </label>
                    }
                  </div>
                </div>
              }
            </div>
          </section>

          <section class="card p-6">
            <div class="mb-5">
              <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Cost Categories</p>
              <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">One-time and recurring cost rows</h2>
              <p class="mt-2 text-xs font-semibold leading-relaxed text-[var(--t-text-secondary)]">
                Unchecked categories are hidden from the financial grid and excluded from initiative summaries. Existing values are retained.
              </p>
            </div>
            <div class="space-y-5">
              @for (group of costGroups(); track group.key) {
                <div class="border border-[var(--t-border)]">
                  <div class="bg-[var(--t-surface-raised)] px-4 py-3">
                    <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">{{ group.label }}</p>
                  </div>
                  <div class="divide-y divide-[var(--t-border)]">
                    @for (cost of itemsForGroup(group.key, 'cost_category'); track cost.key) {
                      <label class="flex items-center gap-3 px-4 py-3 text-sm text-[var(--t-text-primary)]">
                        <input
                          type="checkbox"
                          [checked]="isCostSelected(cost)"
                          (change)="toggleCost(cost, $any($event.target).checked)"
                          aria-label="Toggle cost category">
                        <span class="min-w-0 flex-1 truncate">{{ cost.label }}</span>
                        <span class="text-[10px] font-black uppercase text-[var(--t-text-tertiary)]">
                          {{ costRollupLabel(cost.rollup_type) }}
                        </span>
                      </label>
                    }
                  </div>
                </div>
              }
            </div>
          </section>
        </div>
      }
    </div>
  `,
})
export class FinancialScopeComponent implements OnInit {
  @Input() id = '';

  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  initiativeName = signal('');
  groups = signal<FinancialConfigGroup[]>([]);
  items = signal<FinancialConfigItem[]>([]);
  metricKeys = signal<string[]>([]);
  costKeys = signal<string[]>([]);
  loaded = signal(false);
  locked = signal(false);
  saving = signal(false);
  saved = signal(false);
  error = signal<string | null>(null);

  ngOnInit(): void {
    if (!this.id) return;
    this.load();
  }

  load(): void {
    this.loaded.set(false);
    this.error.set(null);
    this.api.get<any>(`/initiatives/${this.id}`).subscribe({
      next: initiative => this.initiativeName.set(initiative?.name || ''),
      error: () => {},
    });
    this.api.get<FinancialSelectionsResponse>(`/initiatives/${this.id}/financials/selections`).subscribe({
      next: response => {
        this.groups.set(response.available.groups || []);
        this.items.set(response.available.items || []);
        this.metricKeys.set(response.selected.metric_keys || []);
        this.costKeys.set(response.selected.cost_category_keys || []);
        this.locked.set(Boolean(response.locked));
        this.loaded.set(true);
      },
      error: err => {
        this.error.set(err.error?.detail || 'Could not load financial scope.');
        this.loaded.set(true);
      },
    });
  }

  metricGroups(): FinancialConfigGroup[] {
    return this.groupsForKind('metric');
  }

  costGroups(): FinancialConfigGroup[] {
    return this.groupsForKind('cost_category');
  }

  itemsForGroup(groupKey: string, itemType: 'metric' | 'cost_category'): FinancialConfigItem[] {
    return this.items()
      .filter(item =>
        item.group_key === groupKey
        && item.item_type === itemType
        && item.is_active !== false
        && !this.isDuplicateCustomSystemMetric(item)
      )
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0) || a.label.localeCompare(b.label));
  }

  financialMetricKey(item: FinancialConfigItem): string {
    return item.system_metric_key || item.key;
  }

  isMetricSelected(item: FinancialConfigItem): boolean {
    return this.metricKeys().includes(this.financialMetricKey(item));
  }

  isCostSelected(item: FinancialConfigItem): boolean {
    return this.costKeys().includes(item.key);
  }

  toggleMetric(item: FinancialConfigItem, checked: boolean): void {
    this.toggleSelection(this.metricKeys, this.financialMetricKey(item), checked);
    this.saved.set(false);
  }

  toggleCost(item: FinancialConfigItem, checked: boolean): void {
    this.toggleSelection(this.costKeys, item.key, checked);
    this.saved.set(false);
  }

  costRollupLabel(rollupType?: string | null): string {
    if (rollupType === 'recurring_cost') return 'Recurring';
    if (rollupType === 'one_off_cost') return 'One-time';
    return 'Unclassified';
  }

  save(): void {
    if (this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    this.api.put<FinancialSelectionsResponse>(`/initiatives/${this.id}/financials/selections`, {
      metric_keys: this.metricKeys(),
      cost_category_keys: this.costKeys(),
    }).subscribe({
      next: response => {
        this.metricKeys.set(response.selected.metric_keys || []);
        this.costKeys.set(response.selected.cost_category_keys || []);
        this.locked.set(Boolean(response.locked));
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.router.navigate(['/initiatives', this.id]), 300);
      },
      error: err => {
        this.error.set(err.error?.detail || 'Could not save financial scope.');
        this.saving.set(false);
      },
    });
  }

  private groupsForKind(kind: 'metric' | 'cost_category'): FinancialConfigGroup[] {
    return this.groups()
      .filter(group => group.kind === kind && group.is_active !== false)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0) || a.label.localeCompare(b.label));
  }

  private isDuplicateCustomSystemMetric(item: FinancialConfigItem): boolean {
    if (item.item_type !== 'metric' || item.is_system || item.system_metric_key) return false;
    return this.items().some(candidate =>
      candidate.item_type === 'metric'
      && candidate.is_active !== false
      && candidate.is_system
      && Boolean(candidate.system_metric_key)
      && candidate.label === item.label
    );
  }

  private toggleSelection(target: WritableSignal<string[]>, key: string, checked: boolean): void {
    const current = new Set(target());
    if (checked) current.add(key);
    else current.delete(key);
    target.set(Array.from(current));
  }
}
