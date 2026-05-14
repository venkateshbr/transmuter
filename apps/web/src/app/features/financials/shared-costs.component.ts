import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-shared-costs',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Financial Governance</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Shared Cost Pools<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Technology, group PMO, vendor, cloud, and shared-team costs allocated without overwriting direct initiative cost lines.
          </p>
        </div>
        <button class="btn-primary text-[10px]" type="button" (click)="createPool()" aria-label="Create shared cost pool">Create Pool</button>
      </header>

      <section class="grid gap-4 md:grid-cols-6">
        <input class="input-field md:col-span-2" [(ngModel)]="draft.name" placeholder="Pool name" aria-label="Shared cost pool name">
        <input class="input-field" [(ngModel)]="draft.category_key" placeholder="Category" aria-label="Cost category">
        <input class="input-field" type="number" [(ngModel)]="draft.year" aria-label="Pool year">
        <input class="input-field" type="number" [(ngModel)]="draft.amount_plan" placeholder="Plan" aria-label="Planned amount">
        <input class="input-field" type="number" [(ngModel)]="draft.amount_actual" placeholder="Actual" aria-label="Actual amount">
      </section>

      <section class="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <div class="card overflow-hidden">
          <div class="border-b border-[var(--t-border)] p-5">
            <h2 class="text-base font-black text-[var(--t-text-primary)]">Pools</h2>
          </div>
          <div class="divide-y divide-[var(--t-border)]">
            @for (pool of pools(); track pool.id) {
              <button type="button" class="block w-full p-5 text-left hover:bg-[var(--t-surface-raised)]" (click)="selectPool(pool)" [attr.aria-label]="'Select ' + pool.name">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ pool.name }}</p>
                    <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ pool.category_key }} · {{ pool.year }}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-sm font-black text-[var(--t-text-primary)]">{{ formatMoney(pool.amount_plan) }}</p>
                    <p class="mt-1 text-[10px] font-bold text-[var(--t-text-tertiary)]">Allocated {{ formatMoney(pool.allocated_plan) }}</p>
                  </div>
                </div>
              </button>
            } @empty {
              <div class="p-6 text-sm text-[var(--t-text-secondary)]">No shared cost pools yet.</div>
            }
          </div>
        </div>

        <div class="card overflow-hidden">
          <div class="flex items-center justify-between border-b border-[var(--t-border)] p-5">
            <div>
              <h2 class="text-base font-black text-[var(--t-text-primary)]">Allocation Rules</h2>
              <p class="mt-1 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ selectedPool()?.name || 'Select a pool' }}</p>
            </div>
            <button class="btn-secondary text-[10px]" type="button" [disabled]="!selectedPool()" (click)="createRule()" aria-label="Create allocation rule">Add Rule</button>
          </div>

          @if (selectedPool()) {
            <div class="grid gap-3 border-b border-[var(--t-border)] p-5 md:grid-cols-4">
              <input class="input-field md:col-span-2" [(ngModel)]="ruleDraft.name" placeholder="Rule name" aria-label="Allocation rule name">
              <select class="input-field" [(ngModel)]="ruleDraft.allocation_method" aria-label="Allocation method">
                <option value="equal_split">Equal split</option>
                <option value="fixed_percentage">Fixed percentage</option>
                <option value="manual_amount">Manual amount</option>
                <option value="benefit_weighted">Benefit weighted</option>
                <option value="revenue_weighted">Revenue weighted</option>
                <option value="headcount_weighted">Headcount weighted</option>
              </select>
              <button class="btn-primary text-[10px]" type="button" (click)="createRule()" aria-label="Save allocation rule">Save Rule</button>
              <textarea class="input-field md:col-span-2" rows="3" [(ngModel)]="filtersJson" placeholder='Filters JSON, e.g. {"tag":"automation"}' aria-label="Allocation filters JSON"></textarea>
              <textarea class="input-field md:col-span-2" rows="3" [(ngModel)]="weightsJson" placeholder="Weights JSON for fixed, manual, or headcount methods" aria-label="Allocation weights JSON"></textarea>
            </div>
            @if (error()) {
              <p class="border-b border-[var(--t-border)] px-5 py-3 text-xs font-bold text-red-500">{{ error() }}</p>
            }
            <div class="divide-y divide-[var(--t-border)]">
              @for (rule of rules(); track rule.id) {
                <div class="p-5">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <p class="text-sm font-black text-[var(--t-text-primary)]">{{ rule.name }}</p>
                      <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ rule.allocation_method.replace('_', ' ') }}</p>
                    </div>
                    <button class="btn-secondary text-[10px]" type="button" (click)="runAllocation(rule)" aria-label="Run allocation">Run</button>
                  </div>
                </div>
              } @empty {
                <div class="p-6 text-sm text-[var(--t-text-secondary)]">No rules for this pool.</div>
              }
            </div>
            <div class="border-t border-[var(--t-border)] p-5">
              <h3 class="text-sm font-black text-[var(--t-text-primary)]">Run History</h3>
              <div class="mt-4 overflow-x-auto">
                <table class="w-full min-w-[720px] text-left text-xs">
                  <thead class="bg-[var(--t-surface-raised)] text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    <tr>
                      <th class="px-3 py-2">Created</th>
                      <th class="px-3 py-2">Scenario</th>
                      <th class="px-3 py-2 text-right">Plan</th>
                      <th class="px-3 py-2 text-right">Actual</th>
                      <th class="px-3 py-2 text-right">Allocations</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (run of runs(); track run.id) {
                      <tr class="border-t border-[var(--t-border)]">
                        <td class="px-3 py-3">{{ run.created_at | date:'medium' }}</td>
                        <td class="px-3 py-3 uppercase">{{ run.scenario }}</td>
                        <td class="px-3 py-3 text-right">{{ formatMoney(run.total_amount_plan) }}</td>
                        <td class="px-3 py-3 text-right">{{ formatMoney(run.total_amount_actual) }}</td>
                        <td class="px-3 py-3 text-right">{{ run.allocations?.length || 0 }}</td>
                      </tr>
                    } @empty {
                      <tr><td colspan="5" class="px-3 py-6 text-center text-[var(--t-text-secondary)]">No allocation runs yet.</td></tr>
                    }
                  </tbody>
                </table>
              </div>
            </div>
          } @else {
            <div class="p-8 text-sm text-[var(--t-text-secondary)]">Select a shared cost pool to manage allocation rules and runs.</div>
          }
        </div>
      </section>
    </div>
  `,
})
export class SharedCostsComponent implements OnInit {
  private readonly api = inject(ApiService);
  pools = signal<any[]>([]);
  rules = signal<any[]>([]);
  runs = signal<any[]>([]);
  selectedPool = signal<any | null>(null);
  draft: any = { name: '', category_key: 'technology', year: new Date().getFullYear(), amount_plan: '0', amount_actual: null };
  ruleDraft: any = { name: '', allocation_method: 'equal_split', filters: {}, weights: {} };
  filtersJson = '{}';
  weightsJson = '{}';
  error = signal('');

  ngOnInit(): void {
    this.loadPools();
  }

  loadPools(): void {
    this.api.get<any>('/shared-cost-pools').subscribe(res => this.pools.set(res.items || []));
  }

  selectPool(pool: any): void {
    this.selectedPool.set(pool);
    this.api.get<any[]>(`/shared-cost-pools/${pool.id}/allocation-rules`).subscribe(res => this.rules.set(res || []));
    this.loadRuns(pool.id);
  }

  createPool(): void {
    if (!this.draft.name?.trim()) return;
    this.api.post<any>('/shared-cost-pools', this.draft).subscribe(pool => {
      this.pools.set([pool, ...this.pools()]);
      this.selectPool(pool);
      this.draft = { name: '', category_key: 'technology', year: new Date().getFullYear(), amount_plan: '0', amount_actual: null };
    });
  }

  createRule(): void {
    const pool = this.selectedPool();
    if (!pool || !this.ruleDraft.name?.trim()) return;
    this.error.set('');
    try {
      this.ruleDraft.filters = JSON.parse(this.filtersJson || '{}');
      this.ruleDraft.weights = JSON.parse(this.weightsJson || '{}');
    } catch {
      this.error.set('Filters and weights must be valid JSON.');
      return;
    }
    this.api.post<any>(`/shared-cost-pools/${pool.id}/allocation-rules`, this.ruleDraft).subscribe(rule => {
      this.rules.set([...this.rules(), rule]);
      this.ruleDraft = { name: '', allocation_method: 'equal_split', filters: {}, weights: {} };
      this.filtersJson = '{}';
      this.weightsJson = '{}';
    });
  }

  runAllocation(rule: any): void {
    const pool = this.selectedPool();
    if (!pool) return;
    this.api.post<any>(`/shared-cost-pools/${pool.id}/allocation-runs`, { rule_id: rule.id, scenario: 'plan' }).subscribe(() => {
      this.loadPools();
      this.loadRuns(pool.id);
    });
  }

  loadRuns(poolId: string): void {
    this.api.get<any[]>(`/shared-cost-pools/${poolId}/allocation-runs`).subscribe(res => this.runs.set(res || []));
  }

  formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value || 0));
  }
}
