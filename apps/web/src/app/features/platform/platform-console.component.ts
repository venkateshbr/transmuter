import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-platform-console',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <main class="min-h-screen bg-[var(--t-bg)] p-8 text-[var(--t-text-primary)]">
      <section class="mb-8 flex items-end justify-between gap-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-[0.28em] text-[var(--t-accent)]">SaaS Operator</p>
          <h1 class="mt-2 text-3xl font-black tracking-tight">Platform Control</h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Cross-tenant signup, billing, and readiness visibility for Transmuter operations.
          </p>
        </div>
        <button type="button" class="btn-ghost border border-[var(--t-border)] px-4 py-2 text-xs font-black uppercase" (click)="load()" aria-label="Refresh platform console">
          Refresh
        </button>
      </section>

      @if (error()) {
        <div class="mb-6 border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      }

      <section class="grid gap-4 md:grid-cols-5">
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Tenants</p>
          <p class="mt-2 text-3xl font-black">{{ overview().summary?.tenant_count || 0 }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Active</p>
          <p class="mt-2 text-3xl font-black text-emerald-500">{{ overview().summary?.active_tenant_count || 0 }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Pending Signups</p>
          <p class="mt-2 text-3xl font-black text-amber-500">{{ overview().summary?.pending_signup_count || 0 }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Stripe Prices</p>
          <p class="mt-2 text-3xl font-black">{{ overview().summary?.configured_price_count || 0 }}/{{ overview().summary?.required_price_count || 0 }}</p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Generated</p>
          <p class="mt-3 text-xs font-bold text-[var(--t-text-secondary)]">{{ overview().generated_at ? (overview().generated_at | date:'medium') : 'Loading' }}</p>
        </div>
      </section>

      <section class="mt-8 grid gap-8 xl:grid-cols-[1.2fr_0.8fr]">
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)]">
          <div class="border-b border-[var(--t-border)] p-5">
            <h2 class="text-lg font-black">Tenant Billing</h2>
            <p class="mt-1 text-xs text-[var(--t-text-secondary)]">Latest tenant subscription and user-count state.</p>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full min-w-[980px] text-left text-sm">
              <thead class="border-b border-[var(--t-border)] text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                <tr>
                  <th class="px-5 py-3">Tenant</th>
                  <th class="px-5 py-3">Status</th>
                  <th class="px-5 py-3">Users</th>
                  <th class="px-5 py-3">Planned</th>
                  <th class="px-5 py-3">Stripe Customer</th>
                  <th class="px-5 py-3">Created</th>
                  <th class="px-5 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (tenant of overview().tenants || []; track tenant.tenant_id) {
                  <tr class="border-b border-[var(--t-border)] last:border-0">
                    <td class="px-5 py-4">
                      <p class="font-black">{{ tenant.name }}</p>
                      <p class="mt-1 font-mono text-[10px] text-[var(--t-text-tertiary)]">{{ tenant.slug }}</p>
                    </td>
                    <td class="px-5 py-4">
                      <span class="text-[10px] font-black uppercase tracking-widest" [class.text-emerald-500]="tenant.subscription_status === 'active'" [class.text-amber-500]="tenant.subscription_status !== 'active'">
                        {{ formatStatus(tenant.subscription_status) }}
                      </span>
                    </td>
                    <td class="px-5 py-4 font-bold">{{ tenant.active_user_count }}/{{ tenant.total_user_count }}</td>
                    <td class="px-5 py-4 font-bold">{{ tenant.planned_user_count || 'Not set' }}</td>
                    <td class="px-5 py-4 font-mono text-xs text-[var(--t-text-secondary)]">{{ tenant.stripe_customer_id || 'Pending' }}</td>
                    <td class="px-5 py-4 text-xs text-[var(--t-text-secondary)]">{{ tenant.created_at | date:'mediumDate' }}</td>
                    <td class="px-5 py-4 text-right">
                      <button
                        type="button"
                        class="border border-red-500/40 px-3 py-2 text-[10px] font-black uppercase tracking-widest text-red-500 hover:bg-red-500/10"
                        (click)="openDeleteTenant(tenant)"
                        [attr.aria-label]="'Delete tenant ' + tenant.name">
                        Delete
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </div>

        <div class="space-y-8">
          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
            <h2 class="text-lg font-black">Production Price IDs</h2>
            <div class="mt-5 space-y-3">
              @for (price of overview().stripe_price_configuration || []; track price.env_key) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <div class="flex justify-between gap-4">
                    <p class="font-black">{{ price.plan_name }}</p>
                    <span class="text-[9px] font-black uppercase tracking-widest" [class.text-emerald-500]="price.configured" [class.text-amber-500]="!price.configured">
                      {{ price.configured ? 'Configured' : 'Missing' }}
                    </span>
                  </div>
                  <p class="mt-1 text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ price.billing_interval }} · {{ formatMoney(price.amount_cents, price.currency) }}</p>
                  <p class="mt-3 break-all font-mono text-[10px] text-[var(--t-text-secondary)]">{{ price.price_id || price.env_key }}</p>
                </div>
              }
            </div>
          </div>

          <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
            <h2 class="text-lg font-black">Recent Signups</h2>
            <div class="mt-5 space-y-3">
              @for (intent of overview().signup_intents || []; track intent.id) {
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <div class="flex justify-between gap-4">
                    <div>
                      <p class="font-black">{{ intent.organization_name }}</p>
                      <p class="mt-1 text-xs text-[var(--t-text-secondary)]">{{ intent.admin_email }}</p>
                    </div>
                    <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-accent)]">{{ formatStatus(intent.status) }}</span>
                  </div>
                  <p class="mt-3 text-[10px] uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    {{ intent.plan_code }} · {{ intent.planned_user_count }} users · {{ intent.billing_interval }}
                  </p>
                </div>
              }
            </div>
          </div>
        </div>
      </section>

      @if (deleteTarget()) {
        <div class="fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-black/60 p-4 sm:items-center sm:p-6">
          <section
            class="flex max-h-[calc(100vh-2rem)] w-full max-w-xl flex-col border border-red-500/40 bg-[var(--t-surface)] shadow-2xl sm:max-h-[calc(100vh-3rem)]"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-tenant-title">
            <div class="overflow-y-auto p-6">
              <p class="text-[10px] font-black uppercase tracking-[0.28em] text-red-500">Destructive cleanup</p>
              <h2 id="delete-tenant-title" class="mt-3 text-2xl font-black">Delete tenant data</h2>
              <p class="mt-3 text-sm leading-6 text-[var(--t-text-secondary)]">
                This permanently deletes the tenant, users, initiatives, financials, meetings, risks, KPIs,
                billing records, and related tenant data. This is intended only for demo cleanup.
              </p>

              <div class="mt-5 border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                <p class="text-sm font-black">{{ deleteTarget()?.name }}</p>
                <p class="mt-1 font-mono text-xs text-[var(--t-text-tertiary)]">{{ deleteTarget()?.slug }}</p>
              </div>

              <label class="mt-5 block">
                <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                  Type tenant slug to confirm
                </span>
                <input
                  class="input-field mt-2 w-full font-mono"
                  [(ngModel)]="deleteConfirmation"
                  [placeholder]="deleteTarget()?.slug"
                  aria-label="Tenant deletion confirmation slug">
              </label>

              @if (deleteError()) {
                <div class="mt-4 border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
                  {{ deleteError() }}
                </div>
              }

              <div class="mt-5 border border-[var(--t-border)]">
                <div class="border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                    {{ deleteResult() ? 'Deletion completed' : deleting() ? 'Deletion in progress' : 'Objects queued for deletion' }}
                  </p>
                </div>
                <div class="grid gap-0 md:grid-cols-2">
                  @for (item of deletionObjects(); track item.key) {
                    <div class="flex items-center justify-between border-b border-[var(--t-border)] px-4 py-3 md:odd:border-r">
                      <div class="flex items-center gap-3">
                        <span
                          class="flex h-6 w-6 items-center justify-center border text-[10px] font-black"
                          [class.border-emerald-500]="deleteResult()"
                          [class.text-emerald-500]="deleteResult()"
                          [class.border-amber-500]="deleting() && !deleteResult()"
                          [class.text-amber-500]="deleting() && !deleteResult()"
                          [class.border-[var(--t-border)]]="!deleting() && !deleteResult()">
                          {{ deleteResult() ? '✓' : deleting() ? '...' : item.count }}
                        </span>
                        <p class="text-sm font-black">{{ item.label }}</p>
                      </div>
                      <p class="text-xs font-bold text-[var(--t-text-secondary)]">
                        {{ deleteResult() ? item.count + ' deleted' : item.count + ' found' }}
                      </p>
                    </div>
                  }
                </div>
              </div>

              @if (deleteResult()) {
                <div class="mt-4 border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-600">
                  Tenant deleted. Organization row: {{ deleteResult().organization_deleted }}. Auth users deleted: {{ deleteResult().auth_users_deleted }}.
                </div>
              }
            </div>

            <div class="sticky bottom-0 flex justify-end gap-3 border-t border-[var(--t-border)] bg-[var(--t-surface)] p-4 shadow-[0_-14px_24px_rgba(7,31,60,0.08)]">
              <button type="button" class="btn-ghost border border-[var(--t-border)] px-4 py-2 text-xs font-black uppercase" (click)="closeDeleteTenant()">
                {{ deleteResult() ? 'Close' : 'Cancel' }}
              </button>
              <button
                *ngIf="!deleteResult()"
                type="button"
                class="border border-red-500 bg-red-500 px-4 py-2 text-xs font-black uppercase text-white disabled:cursor-not-allowed disabled:opacity-40"
                [disabled]="deleteConfirmation !== deleteTarget()?.slug || deleting()"
                (click)="deleteTenant()">
                {{ deleting() ? 'Deleting...' : 'Delete tenant' }}
              </button>
            </div>
          </section>
        </div>
      }
    </main>
  `,
})
export class PlatformConsoleComponent implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly overview = signal<any>({ summary: {}, tenants: [], signup_intents: [], stripe_price_configuration: [] });
  protected readonly error = signal<string | null>(null);
  protected readonly deleteTarget = signal<any | null>(null);
  protected readonly deleteError = signal<string | null>(null);
  protected readonly deletePreview = signal<any | null>(null);
  protected readonly deleteResult = signal<any | null>(null);
  protected readonly deleting = signal(false);
  protected deleteConfirmation = '';
  private readonly objectLabels: Record<string, string> = {
    users: 'Users',
    initiatives: 'Initiatives',
    financials: 'Financials',
    kpis: 'KPIs',
    risks: 'Risks',
    milestones: 'Milestones',
    meetings: 'Meetings',
    action_items: 'Action items',
    governance: 'Governance',
    billing: 'Billing',
    status_updates: 'Status updates',
    audit_and_ai: 'Audit and AI',
    master_data: 'Master data',
  };

  ngOnInit(): void {
    this.load();
  }

  protected load(): void {
    this.error.set(null);
    this.api.get<any>('/platform/overview').subscribe({
      next: response => this.overview.set(response),
      error: err => this.error.set(err.error?.detail || 'Could not load platform console'),
    });
  }

  protected formatStatus(value: string | undefined): string {
    return (value || 'unknown').replace(/_/g, ' ');
  }

  protected formatMoney(cents: number | undefined, currency: string | undefined): string {
    if (!cents) return 'Custom';
    return `${String(currency || 'usd').toUpperCase()} ${(Number(cents) / 100).toFixed(2)}`;
  }

  protected openDeleteTenant(tenant: any): void {
    this.deleteTarget.set(tenant);
    this.deleteConfirmation = '';
    this.deleteError.set(null);
    this.deletePreview.set(null);
    this.deleteResult.set(null);
    this.api.get<any>(`/platform/tenants/${tenant.tenant_id}/delete-preview`).subscribe({
      next: response => this.deletePreview.set(response),
      error: err => this.deleteError.set(err.error?.detail || 'Could not load deletion preview'),
    });
  }

  protected closeDeleteTenant(): void {
    this.deleteTarget.set(null);
    this.deleteConfirmation = '';
    this.deleteError.set(null);
    this.deletePreview.set(null);
    this.deleteResult.set(null);
    this.deleting.set(false);
  }

  protected deleteTenant(): void {
    const tenant = this.deleteTarget();
    if (!tenant || this.deleteConfirmation !== tenant.slug || this.deleting()) return;
    this.deleting.set(true);
    this.deleteError.set(null);
    this.api.delete(`/platform/tenants/${tenant.tenant_id}`, { confirm_slug: this.deleteConfirmation }).subscribe({
      next: (response: any) => {
        this.deleteResult.set(response);
        this.deletePreview.set(response);
        this.deleting.set(false);
        this.load();
      },
      error: err => {
        this.deleteError.set(err.error?.detail || 'Could not delete tenant');
        this.deleting.set(false);
      },
    });
  }

  protected deletionObjects(): { key: string; label: string; count: number }[] {
    const counts = (this.deleteResult() || this.deletePreview())?.object_counts || {};
    return Object.keys(this.objectLabels).map(key => ({
      key,
      label: this.objectLabels[key],
      count: Number(counts[key] || 0),
    }));
  }
}
