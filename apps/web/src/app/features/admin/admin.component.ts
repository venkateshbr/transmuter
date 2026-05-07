import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';
import { ApiService } from '../../core/services/api.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-8 space-y-10 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Control Center<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Enterprise governance, system configuration, and audit accountability.</p>
        </div>
        <div class="flex gap-3">
          <div class="badge-purple px-4 py-2 border border-[var(--t-accent)]/20 shadow-sm flex items-center gap-2">
            <span class="material-icons text-xs">verified_user</span>
            <span class="text-[10px] font-black uppercase tracking-widest">SYSTEM SECURED</span>
          </div>
        </div>
      </div>

      <!-- Admin Navigation -->
      <div class="border-b border-[var(--t-border)]">
        <nav class="-mb-px flex space-x-8">
          @for (tab of ['General', 'Billing', 'Data Cleanup', 'Strategic Parameters', 'Access Control', 'Governance Engine', 'Audit Logs']; track tab) {
            <button
              type="button"
              (click)="activeTab = tab"
              [ngClass]="activeTab === tab ? 'border-[var(--t-accent)] text-[var(--t-accent)]' : 'border-transparent text-[var(--t-text-tertiary)]'"
              [attr.aria-label]="'Open ' + tab + ' admin tab'"
              class="whitespace-nowrap pb-4 px-1 border-b-2 font-black text-[10px] uppercase tracking-widest transition-all">
              {{ tab }}
            </button>
          }
        </nav>
      </div>

      <div class="grid grid-cols-1 gap-8">
        
        <!-- Left: Main Content -->
        <div class="space-y-8">
          
          @if (activeTab === 'General') {
            <div class="card p-8 space-y-8">
               <section>
                 <div class="flex justify-between items-center mb-6">
                   <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Organization Identity</h3>
                   <button type="button" (click)="saveSettings()" aria-label="Save organization settings" class="btn-primary text-[10px] py-2 px-4 rounded-xl font-black uppercase tracking-widest">Save Changes</button>
                 </div>
                 <div class="grid grid-cols-2 gap-8">
                    <div class="space-y-1">
                      <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Legal Entity Name</p>
                      <input type="text" [ngModel]="settings().name" (ngModelChange)="updateSettingField('name', $event)" aria-label="Legal entity name" class="input-field w-full">
                    </div>
                    <div class="space-y-1">
                      <p class="text-[10px] font-black text-[var(--t-text-tertiary)] uppercase tracking-widest">Logo URL</p>
                      <input type="text" [ngModel]="settings().logo_url" (ngModelChange)="updateSettingField('logo_url', $event)" aria-label="Logo URL" class="input-field w-full" placeholder="https://...">
                    </div>
                 </div>
               </section>
            </div>
          }

          @if (activeTab === 'Billing') {
            <div class="card p-8 space-y-8">
              <section class="flex items-start justify-between gap-8">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Subscription</p>
                  <h3 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">{{ formatBillingStatus(billing().subscription_status) }}</h3>
                  <p class="mt-2 max-w-xl text-sm leading-6 text-[var(--t-text-secondary)]">
                    Stripe subscription metadata is captured from verified checkout webhooks and tied to this tenant.
                  </p>
                </div>
                <span class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-2 text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">
                  {{ billing().provider || 'stripe' }}
                </span>
              </section>

              @if (billingError()) {
                <div class="border border-amber-500/30 bg-amber-500/10 p-3 text-sm font-bold text-amber-600">
                  {{ billingError() }}
                </div>
              }

              <section class="grid gap-4 md:grid-cols-4">
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Planned Seats</p>
                  <p class="mt-2 text-2xl font-black">{{ billing().planned_user_count || 'Not set' }}</p>
                </div>
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Active Users</p>
                  <p class="mt-2 text-2xl font-black">{{ billing().active_user_count || 0 }}</p>
                </div>
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Plan</p>
                  <p class="mt-2 text-2xl font-black">{{ billing().plan_name || 'Not set' }}</p>
                </div>
                <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Payment</p>
                  <p class="mt-2 text-2xl font-black">{{ formatBillingStatus(billing().payment_status || billing().checkout_status || 'pending') }}</p>
                </div>
              </section>

              <section class="grid gap-3 border-t border-[var(--t-border)] pt-6 md:grid-cols-2">
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Recurring Price</p>
                  <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">{{ formatRecurringPrice() }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Stripe Price</p>
                  <p class="mt-1 break-all font-mono text-xs text-[var(--t-text-secondary)]">{{ billing().stripe_price_id || 'Sandbox inline price' }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Stripe Customer</p>
                  <p class="mt-1 break-all font-mono text-xs text-[var(--t-text-secondary)]">{{ billing().stripe_customer_id || 'Pending checkout completion' }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Stripe Subscription</p>
                  <p class="mt-1 break-all font-mono text-xs text-[var(--t-text-secondary)]">{{ billing().stripe_subscription_id || 'Pending checkout completion' }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Checkout Session</p>
                  <p class="mt-1 break-all font-mono text-xs text-[var(--t-text-secondary)]">{{ billing().stripe_checkout_session_id || 'Not started' }}</p>
                </div>
                <div>
                  <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Last Billing Event</p>
                  <p class="mt-1 text-xs font-bold text-[var(--t-text-secondary)]">{{ billing().last_event_at ? (billing().last_event_at | date:'medium') : 'No webhook received' }}</p>
                </div>
              </section>

              <button type="button" (click)="openBillingPortal()" class="btn-primary text-xs" aria-label="Open Stripe billing portal">
                Open Stripe Billing Portal
              </button>
            </div>

            <div class="card p-8 space-y-6">
              <section class="flex items-start justify-between gap-8">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Production Catalog</p>
                  <h3 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">Stripe Price IDs</h3>
                  <p class="mt-2 max-w-xl text-sm leading-6 text-[var(--t-text-secondary)]">
                    These are read from the API environment and should match the live Stripe Product catalog before production launch.
                  </p>
                </div>
                <span
                  class="border px-4 py-2 text-[10px] font-black uppercase tracking-widest"
                  [class.border-emerald-500]="configuredPriceCount() === priceConfiguration().length"
                  [class.text-emerald-500]="configuredPriceCount() === priceConfiguration().length"
                  [class.border-amber-500]="configuredPriceCount() !== priceConfiguration().length"
                  [class.text-amber-500]="configuredPriceCount() !== priceConfiguration().length">
                  {{ configuredPriceCount() }}/{{ priceConfiguration().length }} configured
                </span>
              </section>

              <section class="grid gap-3 md:grid-cols-2">
                @for (price of priceConfiguration(); track price.env_key) {
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                    <div class="flex items-start justify-between gap-4">
                      <div>
                        <p class="text-sm font-black text-[var(--t-text-primary)]">{{ price.plan_name }}</p>
                        <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                          {{ price.billing_interval }} · {{ formatCents(price.amount_cents, price.currency) }}
                        </p>
                      </div>
                      <span
                        class="text-[9px] font-black uppercase tracking-widest"
                        [class.text-emerald-500]="price.configured"
                        [class.text-amber-500]="!price.configured">
                        {{ price.configured ? 'Configured' : 'Missing' }}
                      </span>
                    </div>
                    <p class="mt-4 font-mono text-[10px] text-[var(--t-text-tertiary)]">{{ price.env_key }}</p>
                    <p class="mt-1 break-all font-mono text-xs text-[var(--t-text-secondary)]">
                      {{ price.price_id || 'Add live price ID to API environment' }}
                    </p>
                  </div>
                }
              </section>
            </div>
          }

          @if (activeTab === 'Data Cleanup') {
            <div class="card overflow-hidden">
              <section class="border-b border-red-500/30 bg-red-500/10 p-8">
                <p class="text-[10px] font-black uppercase tracking-widest text-red-500">Destructive tenant operation</p>
                <h3 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">Delete portfolio data</h3>
                <p class="mt-2 max-w-2xl text-sm leading-6 text-[var(--t-text-secondary)]">
                  Remove initiatives and their dependent KPIs, risks, milestones, financials, meetings,
                  action items, status updates, and gate submissions for this tenant only.
                </p>
              </section>

              <section class="grid gap-4 p-8 md:grid-cols-3">
                @for (item of cleanupObjects(); track item.key) {
                  <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4">
                    <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ item.label }}</p>
                    <p class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">{{ item.count }}</p>
                  </div>
                }
              </section>

              <section class="border-t border-[var(--t-border)] p-8">
                <div class="grid gap-6 lg:grid-cols-[1fr_0.8fr]">
                  <div>
                    <p class="text-sm font-black text-[var(--t-text-primary)]">Preserved tenant records</p>
                    <p class="mt-2 text-sm leading-6 text-[var(--t-text-secondary)]">
                      This action does not delete the tenant organization, users, auth users, billing/subscription records,
                      workstreams, business units, gate criteria, or audit history.
                    </p>
                    <p class="mt-4 font-mono text-xs text-[var(--t-text-tertiary)]">
                      Tenant slug: {{ cleanupPreview().tenant_slug || 'Loading' }}
                    </p>
                  </div>

                  <div class="border border-red-500/30 bg-[var(--t-surface-raised)] p-5">
                    <label class="block">
                      <span class="text-[10px] font-black uppercase tracking-widest text-red-500">
                        Type tenant slug to confirm
                      </span>
                      <input
                        class="input-field mt-2 w-full font-mono"
                        [ngModel]="cleanupConfirmation()"
                        (ngModelChange)="cleanupConfirmation.set($event)"
                        [placeholder]="cleanupPreview().tenant_slug || ''"
                        aria-label="Portfolio cleanup confirmation slug">
                    </label>

                    @if (cleanupError()) {
                      <div class="mt-4 border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
                        {{ cleanupError() }}
                      </div>
                    }

                    @if (cleanupResult()) {
                      <div class="mt-4 border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-600">
                        Portfolio cleanup completed for {{ cleanupResult().tenant_name }}.
                      </div>
                    }

                    <div class="mt-5 flex justify-end gap-3">
                      <button type="button" class="btn-ghost border border-[var(--t-border)] px-4 py-2 text-xs font-black uppercase" (click)="loadCleanupPreview()" aria-label="Refresh portfolio cleanup preview">
                        Refresh
                      </button>
                      <button
                        type="button"
                        class="border border-red-500 bg-red-500 px-4 py-2 text-xs font-black uppercase text-white disabled:cursor-not-allowed disabled:opacity-40"
                        [disabled]="!normalizedCleanupConfirmation() || cleanupDeleting()"
                        (click)="deletePortfolioData()"
                        aria-label="Delete all tenant portfolio data">
                        {{ cleanupDeleting() ? 'Deleting...' : 'Delete portfolio data' }}
                      </button>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          }

          @if (activeTab === 'Strategic Parameters') {
            <div class="grid gap-6 xl:grid-cols-2">
              <!-- Workstreams CRUD -->
              <div class="card p-8">
                <div class="flex justify-between items-center mb-6">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Workstream Management</h3>
                    <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Configure primary portfolio streams</p>
                  </div>
                </div>
                
                <div class="space-y-3">
                  @for (ws of workstreams(); track ws.id) {
                    <div class="grid gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all sm:grid-cols-[1fr_220px_auto] sm:items-center">
                      <div class="flex items-center gap-4 min-w-0">
                        <div class="w-8 h-8 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
                          <span class="material-icons text-sm">hub</span>
                        </div>
                        <input type="text" [ngModel]="ws.name" (ngModelChange)="ws.name = $event" (blur)="updateWorkstream(ws)" aria-label="Workstream name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                      </div>
                      <select
                        [ngModel]="ws.business_unit_id || ''"
                        (ngModelChange)="ws.business_unit_id = $event || null; updateWorkstream(ws)"
                        aria-label="Workstream business unit"
                        class="input-field w-full py-2 text-xs">
                        <option value="">No business unit</option>
                        @for (bu of businessUnits(); track bu.id) {
                          <option [value]="bu.id">{{ bu.name }}</option>
                        }
                      </select>
                      <button type="button" (click)="deleteWorkstream(ws.id)" aria-label="Delete workstream" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }
                  
                  <!-- Inline Add -->
                  <div class="grid gap-4 p-4 rounded-xl border border-dashed border-[var(--t-border)] sm:grid-cols-[1fr_220px_auto] sm:items-center">
                    <div class="flex items-center gap-4 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newWorkstreamName()" (ngModelChange)="newWorkstreamName.set($event)" (keyup.enter)="addWorkstream()" aria-label="New workstream name" placeholder="Type new workstream name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                    </div>
                    <select
                      [ngModel]="newWorkstreamBusinessUnitId()"
                      (ngModelChange)="newWorkstreamBusinessUnitId.set($event)"
                      aria-label="New workstream business unit"
                      class="input-field w-full py-2 text-xs">
                      <option value="">No business unit</option>
                      @for (bu of businessUnits(); track bu.id) {
                        <option [value]="bu.id">{{ bu.name }}</option>
                      }
                    </select>
                    <button type="button" (click)="addWorkstream()" [disabled]="!newWorkstreamName().trim()" aria-label="Create workstream" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-40">Create</button>
                  </div>
                </div>
              </div>

              <!-- Business Units CRUD -->
              <div class="card p-8">
                <div class="flex justify-between items-center mb-6">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Business Units</h3>
                    <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Market and functional segments</p>
                  </div>
                </div>
                
                <div class="space-y-3">
                  @for (bu of businessUnits(); track bu.id) {
                    <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4">
                        <div class="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-500">
                          <span class="material-icons text-sm">business_center</span>
                        </div>
                        <input type="text" [ngModel]="bu.name" (ngModelChange)="bu.name = $event" (blur)="updateBusinessUnit(bu)" aria-label="Business unit name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-[200px]">
                      </div>
                      <button type="button" (click)="deleteBusinessUnit(bu.id)" aria-label="Delete business unit" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }

                  <!-- Inline Add -->
                  <div class="flex items-center justify-between p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                    <div class="flex items-center gap-4">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newBusinessUnitName()" (ngModelChange)="newBusinessUnitName.set($event)" (keyup.enter)="addBusinessUnit()" aria-label="New business unit name" placeholder="Type new segment name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-[200px]">
                    </div>
                    @if (newBusinessUnitName()) {
                      <button type="button" (click)="addBusinessUnit()" aria-label="Create business unit" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest">Create</button>
                    }
                  </div>
                </div>
              </div>

              <!-- Markets Configuration -->
              <div class="card p-8">
                <div class="mb-6">
                  <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Markets</h3>
                  <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Tenant market configuration</p>
                </div>

                <div class="space-y-3">
                  @for (market of markets(); track $index) {
                    <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4 min-w-0 flex-1">
                        <div class="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-500">
                          <span class="material-icons text-sm">public</span>
                        </div>
                        <input type="text" [ngModel]="market" (ngModelChange)="updateMarket($index, $event)" (blur)="saveStrategicParameterConfig()" aria-label="Market name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                      </div>
                      <button type="button" (click)="deleteMarket($index)" aria-label="Delete market" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }

                  <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                    <div class="flex items-center gap-4 min-w-0 flex-1">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newMarketName()" (ngModelChange)="newMarketName.set($event)" (keyup.enter)="addMarket()" aria-label="New market name" placeholder="Type new market name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                    </div>
                    <button type="button" (click)="addMarket()" [disabled]="!newMarketName().trim()" aria-label="Create market" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-40">Create</button>
                  </div>
                </div>
              </div>

              <!-- Themes Configuration -->
              <div class="card p-8">
                <div class="mb-6">
                  <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Themes</h3>
                  <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Strategic theme configuration</p>
                </div>

                <div class="space-y-3">
                  @for (theme of themes(); track $index) {
                    <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4 min-w-0 flex-1">
                        <div class="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-500">
                          <span class="material-icons text-sm">category</span>
                        </div>
                        <input type="text" [ngModel]="theme" (ngModelChange)="updateTheme($index, $event)" (blur)="saveStrategicParameterConfig()" aria-label="Theme name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                      </div>
                      <button type="button" (click)="deleteTheme($index)" aria-label="Delete theme" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }

                  <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                    <div class="flex items-center gap-4 min-w-0 flex-1">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newThemeName()" (ngModelChange)="newThemeName.set($event)" (keyup.enter)="addTheme()" aria-label="New theme name" placeholder="Type new theme name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                    </div>
                    <button type="button" (click)="addTheme()" [disabled]="!newThemeName().trim()" aria-label="Create theme" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-40">Create</button>
                  </div>
                </div>
              </div>

              <!-- Tags Configuration -->
              <div class="card p-8">
                <div class="mb-6">
                  <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Tags</h3>
                  <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase tracking-widest font-black mt-1">Initiative value-matrix tags</p>
                </div>

                <div class="space-y-3">
                  @for (tag of tags(); track $index) {
                    <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all">
                      <div class="flex items-center gap-4 min-w-0 flex-1">
                        <div class="w-8 h-8 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
                          <span class="material-icons text-sm">sell</span>
                        </div>
                        <input type="text" [ngModel]="tag" (ngModelChange)="updateTag($index, $event)" (blur)="saveStrategicParameterConfig()" aria-label="Tag name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                      </div>
                      <button type="button" (click)="deleteTag($index)" aria-label="Delete tag" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }

                  <div class="flex items-center justify-between gap-4 p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                    <div class="flex items-center gap-4 min-w-0 flex-1">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newTagName()" (ngModelChange)="newTagName.set($event)" (keyup.enter)="addTag()" aria-label="New tag name" placeholder="Type new tag name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                    </div>
                    <button type="button" (click)="addTag()" [disabled]="!newTagName().trim()" aria-label="Create tag" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest disabled:cursor-not-allowed disabled:opacity-40">Create</button>
                  </div>
                </div>
              </div>
            </div>
          }

          @if (activeTab === 'Access Control') {
            <div class="card p-0 overflow-hidden">
               <table class="w-full text-left">
                 <thead class="bg-[var(--t-surface-raised)] border-b border-[var(--t-border)]">
                   <tr>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Identity</th>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">System Role</th>
                     <th class="px-8 py-4 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</th>
                   </tr>
                 </thead>
                 <tbody class="divide-y divide-[var(--t-border)]">
                    @for (u of users(); track u.id) {
                      <tr class="hover:bg-[var(--t-surface-raised)]/30 transition-colors">
                        <td class="px-8 py-6 flex items-center gap-4">
                          <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-[var(--t-accent)] to-[var(--t-blue-light)] flex items-center justify-center text-white font-black">
                            {{ u.display_name?.charAt(0) || u.email.charAt(0) }}
                          </div>
                          <div>
                            <p class="text-sm font-black text-[var(--t-text-primary)]">{{ u.display_name || 'Anonymous' }}</p>
                            <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ u.email }}</p>
                          </div>
                        </td>
                        <td class="px-8 py-6">
                          <span class="badge-purple font-black text-[9px] uppercase tracking-widest">{{ u.role.replace('_', ' ') }}</span>
                        </td>
                        <td class="px-8 py-6">
                           <span [class]="u.status === 'active' ? 'text-emerald-500' : 'text-amber-500'" class="font-bold text-[10px] uppercase">
                             {{ u.status }}
                           </span>
                        </td>
                      </tr>
                    }
                 </tbody>
               </table>
            </div>
          }

          @if (activeTab === 'Governance Engine') {
             <div class="space-y-8">
                <!-- Gate 1 Criteria -->
                <div class="card p-8">
                  <div class="flex justify-between items-center mb-6">
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Stage Gate 1 Criteria (Scoping → Execution)</h3>
                    <button type="button" (click)="addCriterion(1)" aria-label="Add gate 1 criterion" class="btn-primary text-[10px] py-2 px-4 rounded-xl font-black uppercase">Add Rule</button>
                  </div>
                  <div class="space-y-3">
                    @for (c of gateCriteria(); track c.id) {
                      @if (c.gate_number === 1) {
                        <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)]">
                          <div class="flex items-center gap-4">
                            <input type="checkbox" [checked]="c.is_active" (change)="toggleCriterion(c)" aria-label="Toggle gate criterion" class="w-4 h-4 rounded border-[var(--t-border)] text-[var(--t-accent)]">
                            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ c.label }}</p>
                          </div>
                          <button type="button" (click)="deleteCriterion(c.id)" aria-label="Delete gate criterion" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                            <span class="material-icons text-sm">delete</span>
                          </button>
                        </div>
                      }
                    }
                    
                    <!-- Inline Add -->
                    <div class="flex items-center justify-between p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                      <div class="flex items-center gap-4">
                        <span class="material-icons text-sm text-[var(--t-text-tertiary)]">add</span>
                        <input type="text" [ngModel]="newCriterionG1()" (ngModelChange)="newCriterionG1.set($event)" (keyup.enter)="addCriterion(1)" aria-label="New gate 1 criterion" placeholder="Add scoping criterion..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-[300px]">
                      </div>
                      @if (newCriterionG1()) {
                        <button type="button" (click)="addCriterion(1)" aria-label="Create gate 1 criterion" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest">Add</button>
                      }
                    </div>
                  </div>
                </div>

                <!-- Gate 2 Criteria -->
                <div class="card p-8">
                  <div class="flex justify-between items-center mb-6">
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Stage Gate 2 Criteria (Execution → Complete)</h3>
                  </div>
                  <div class="space-y-3">
                    @for (c of gateCriteria(); track c.id) {
                      @if (c.gate_number === 2) {
                        <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)]">
                          <div class="flex items-center gap-4">
                            <input type="checkbox" [checked]="c.is_active" (change)="toggleCriterion(c)" aria-label="Toggle gate criterion" class="w-4 h-4 rounded border-[var(--t-border)] text-[var(--t-accent)]">
                            <p class="text-sm font-bold text-[var(--t-text-primary)]">{{ c.label }}</p>
                          </div>
                          <button type="button" (click)="deleteCriterion(c.id)" aria-label="Delete gate criterion" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                            <span class="material-icons text-sm">delete</span>
                          </button>
                        </div>
                      }
                    }

                    <!-- Inline Add -->
                    <div class="flex items-center justify-between p-4 rounded-xl border border-dashed border-[var(--t-border)]">
                      <div class="flex items-center gap-4">
                        <span class="material-icons text-sm text-[var(--t-text-tertiary)]">add</span>
                        <input type="text" [ngModel]="newCriterionG2()" (ngModelChange)="newCriterionG2.set($event)" (keyup.enter)="addCriterion(2)" aria-label="New gate 2 criterion" placeholder="Add execution criterion..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-[300px]">
                      </div>
                      @if (newCriterionG2()) {
                        <button type="button" (click)="addCriterion(2)" aria-label="Create gate 2 criterion" class="text-[var(--t-accent)] font-black text-[10px] uppercase tracking-widest">Add</button>
                      }
                    </div>
                  </div>
                </div>
             </div>
          }

          @if (activeTab === 'Audit Logs') {
            <div class="card p-0 overflow-hidden">
               <div class="p-6 border-b border-[var(--t-border)]">
                 <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Platform Audit Accountability</h3>
                 <p class="text-[10px] text-[var(--t-text-tertiary)] uppercase font-black tracking-widest mt-1">Immutable record of system changes</p>
               </div>
               <div class="max-h-[600px] overflow-y-auto">
                 <table class="w-full text-left">
                   <tbody class="divide-y divide-[var(--t-border)]">
                     @for (log of auditLogs(); track log.id) {
                       <tr class="hover:bg-[var(--t-surface-raised)]/30 transition-colors">
                         <td class="px-8 py-4">
                            <div class="flex items-center gap-3">
                               <span class="material-icons text-[var(--t-accent)] text-lg">{{ getAuditIcon(log.action) }}</span>
                               <span class="text-sm font-bold text-[var(--t-text-primary)]">{{ log.action.toUpperCase() }}</span>
                            </div>
                         </td>
                         <td class="px-8 py-4">
                            <p class="text-sm text-[var(--t-text-secondary)]">{{ log.entity_type }}</p>
                            <p class="text-[10px] text-[var(--t-text-tertiary)] font-mono">{{ log.entity_id.substring(0,8) }}</p>
                         </td>
                         <td class="px-8 py-4">
                            <p class="text-xs font-bold text-[var(--t-text-primary)]">{{ log.users?.display_name || 'System' }}</p>
                            <p class="text-[10px] text-[var(--t-text-tertiary)]">{{ log.created_at | date:'short' }}</p>
                         </td>
                       </tr>
                     }
                   </tbody>
                 </table>
               </div>
            </div>
          }
        </div>

      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class AdminComponent implements OnInit {
  protected readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);

  activeTab = 'General';
  
  // Signals for data
  workstreams = signal<any[]>([]);
  businessUnits = signal<any[]>([]);
  users = signal<any[]>([]);
  settings = signal<any>({ name: '', logo_url: '', settings: {} });
  markets = signal<string[]>([]);
  themes = signal<string[]>([]);
  tags = signal<string[]>([]);
  billing = signal<any>({});
  billingError = signal<string | null>(null);
  cleanupPreview = signal<any>({ object_counts: {}, preserved_objects: [] });
  cleanupResult = signal<any | null>(null);
  cleanupError = signal<string | null>(null);
  cleanupDeleting = signal(false);
  cleanupConfirmation = signal('');
  gateCriteria = signal<any[]>([]);
  auditLogs = signal<any[]>([]);

  // Inline add state
  newWorkstreamName = signal('');
  newWorkstreamBusinessUnitId = signal('');
  newBusinessUnitName = signal('');
  newMarketName = signal('');
  newThemeName = signal('');
  newTagName = signal('');
  newCriterionG1 = signal('');
  newCriterionG2 = signal('');

  private readonly defaultTags = ['automation', 'offshoring', 'commercial', 'other'];

  ngOnInit() {
    this.loadAll();
  }

  loadAll() {
    this.loadWorkstreams();
    this.loadBusinessUnits();
    this.loadUsers();
    this.loadSettings();
    this.loadBilling();
    this.loadCleanupPreview();
    this.loadGateCriteria();
    this.loadAuditLogs();
  }

  loadWorkstreams() {
    this.api.get<any>('/workstreams').subscribe(res => this.workstreams.set(res.items || res.data || []));
  }

  loadBusinessUnits() {
    this.api.get<any>('/business-units').subscribe(res => this.businessUnits.set(res.items || res.data || []));
  }

  loadUsers() {
    this.api.get<any>('/people').subscribe(res => this.users.set(res.items || res.data || []));
  }

  loadSettings() {
    this.api.get<any>('/admin/settings').subscribe(res => {
      this.settings.set(res);
      const strategicParameters = res.settings?.strategic_parameters || {};
      this.markets.set(this.normalizeConfigList(strategicParameters.markets));
      this.themes.set(this.normalizeConfigList(strategicParameters.themes));
      this.tags.set(this.normalizeConfigList(strategicParameters.tags).length ? this.normalizeConfigList(strategicParameters.tags) : this.defaultTags);
    });
  }

  loadBilling() {
    this.api.get<any>('/admin/billing').subscribe(res => this.billing.set(res));
  }

  openBillingPortal() {
    this.billingError.set(null);
    this.api.post<{ portal_url: string }>('/billing/portal-session', {
      return_url: `${window.location.origin}/admin`,
    }).subscribe({
      next: response => {
        window.location.href = response.portal_url;
      },
      error: err => {
        this.billingError.set(err.error?.detail || 'Billing portal is not available yet.');
      },
    });
  }

  loadCleanupPreview() {
    this.cleanupError.set(null);
    this.cleanupResult.set(null);
    this.cleanupConfirmation.set('');
    this.api.get<any>('/admin/portfolio-cleanup-preview').subscribe({
      next: res => this.cleanupPreview.set(res),
      error: err => this.cleanupError.set(err.error?.detail || 'Could not load portfolio cleanup preview'),
    });
  }

  loadGateCriteria() {
    this.api.get<any>('/admin/gate-criteria').subscribe(res => this.gateCriteria.set(res.items || []));
  }

  loadAuditLogs() {
    this.api.get<any>('/admin/audit-logs').subscribe(res => this.auditLogs.set(res.items || []));
  }

  updateSettingField(field: 'name' | 'logo_url', value: string) {
    this.settings.update(current => ({ ...current, [field]: value }));
  }

  saveSettings() {
    this.api.put('/admin/settings', this.settings()).subscribe(() => {
      // Show success toast or similar if implemented
    });
  }

  addWorkstream() {
    const name = this.newWorkstreamName().trim();
    if (!name) return;
    this.api.post('/workstreams', {
      name,
      business_unit_id: this.newWorkstreamBusinessUnitId() || null,
    }).subscribe(() => {
      this.loadWorkstreams();
      this.newWorkstreamName.set('');
      this.newWorkstreamBusinessUnitId.set('');
    });
  }

  updateWorkstream(ws: any) {
    const name = String(ws.name || '').trim();
    if (!name) return;
    this.api.put(`/workstreams/${ws.id}`, {
      name,
      business_unit_id: ws.business_unit_id || null,
    }).subscribe(() => {
      this.loadWorkstreams();
      this.loadAuditLogs();
    });
  }

  deleteWorkstream(id: string) {
    this.api.delete(`/workstreams/${id}`).subscribe(() => {
      this.loadWorkstreams();
      this.loadAuditLogs();
    });
  }

  addBusinessUnit() {
    const name = this.newBusinessUnitName().trim();
    if (!name) return;
    this.api.post('/business-units', { name }).subscribe(() => {
      this.loadBusinessUnits();
      this.newBusinessUnitName.set('');
    });
  }

  updateBusinessUnit(bu: any) {
    const name = String(bu.name || '').trim();
    if (!name) return;
    this.api.put(`/business-units/${bu.id}`, { name }).subscribe(() => {
      this.loadBusinessUnits();
      this.loadAuditLogs();
    });
  }

  deleteBusinessUnit(id: string) {
    this.api.delete(`/business-units/${id}`).subscribe(() => {
      this.loadBusinessUnits();
      this.loadWorkstreams();
      this.loadAuditLogs();
    });
  }

  addMarket() {
    const name = this.newMarketName().trim();
    if (!name) return;
    this.markets.update(markets => [...markets, name]);
    this.newMarketName.set('');
    this.saveStrategicParameterConfig();
  }

  updateMarket(index: number, value: string) {
    this.markets.update(markets => markets.map((market, idx) => idx === index ? value : market));
  }

  deleteMarket(index: number) {
    const value = this.markets()[index];
    this.resetStrategicParameterReferences('market', value, () => {
      this.markets.update(markets => markets.filter((_, idx) => idx !== index));
      this.saveStrategicParameterConfig();
    });
  }

  addTheme() {
    const name = this.newThemeName().trim();
    if (!name) return;
    this.themes.update(themes => [...themes, name]);
    this.newThemeName.set('');
    this.saveStrategicParameterConfig();
  }

  updateTheme(index: number, value: string) {
    this.themes.update(themes => themes.map((theme, idx) => idx === index ? value : theme));
  }

  deleteTheme(index: number) {
    const value = this.themes()[index];
    this.resetStrategicParameterReferences('theme', value, () => {
      this.themes.update(themes => themes.filter((_, idx) => idx !== index));
      this.saveStrategicParameterConfig();
    });
  }

  addTag() {
    const name = this.newTagName().trim();
    if (!name) return;
    this.tags.update(tags => [...tags, name]);
    this.newTagName.set('');
    this.saveStrategicParameterConfig();
  }

  updateTag(index: number, value: string) {
    this.tags.update(tags => tags.map((tag, idx) => idx === index ? value : tag));
  }

  deleteTag(index: number) {
    const value = this.tags()[index];
    this.resetStrategicParameterReferences('tag', value, () => {
      this.tags.update(tags => tags.filter((_, idx) => idx !== index));
      this.saveStrategicParameterConfig();
    });
  }

  saveStrategicParameterConfig() {
    const current = this.settings();
    const currentSettings = current.settings || {};
    const strategicParameters = currentSettings.strategic_parameters || {};
    const nextSettings = {
      ...currentSettings,
      strategic_parameters: {
        ...strategicParameters,
        markets: this.normalizeConfigList(this.markets()),
        themes: this.normalizeConfigList(this.themes()),
        tags: this.normalizeConfigList(this.tags()),
      },
    };

    this.api.put('/admin/settings', {
      name: current.name,
      logo_url: current.logo_url,
      settings: nextSettings,
    }).subscribe(() => {
      this.loadSettings();
      this.loadAuditLogs();
    });
  }

  private normalizeConfigList(values: unknown): string[] {
    if (!Array.isArray(values)) return [];
    return [...new Set(values.map(value => String(value).trim()).filter(Boolean))];
  }

  private resetStrategicParameterReferences(
    parameterType: 'market' | 'theme' | 'tag',
    value: string | undefined,
    next: () => void,
  ) {
    const normalizedValue = String(value || '').trim();
    if (!normalizedValue) {
      next();
      return;
    }
    this.api.post('/admin/strategic-parameters/reset-references', {
      parameter_type: parameterType,
      value: normalizedValue,
    }).subscribe(() => {
      next();
      this.loadAuditLogs();
    });
  }

  addCriterion(gate: number) {
    const label = gate === 1 ? this.newCriterionG1() : this.newCriterionG2();
    if (!label) return;
    const criterion_id = 'g' + gate + '-' + Math.random().toString(36).substring(2, 5);
    this.api.post('/admin/gate-criteria', { 
      gate_number: gate, 
      label, 
      criterion_id,
      is_active: true,
      sort_order: this.gateCriteria().filter(c => c.gate_number === gate).length + 1
    }).subscribe(() => {
      this.loadGateCriteria();
      if (gate === 1) this.newCriterionG1.set('');
      else this.newCriterionG2.set('');
    });
  }

  toggleCriterion(c: any) {
    this.api.post('/admin/gate-criteria', { ...c, is_active: !c.is_active }).subscribe(() => this.loadGateCriteria());
  }

  deleteCriterion(id: string) {
    this.api.delete(`/admin/gate-criteria/${id}`).subscribe(() => this.loadGateCriteria());
  }

  deletePortfolioData() {
    const confirmation = this.normalizedCleanupConfirmation();
    if (!confirmation || this.cleanupDeleting()) return;

    this.cleanupDeleting.set(true);
    this.cleanupError.set(null);
    this.api.post('/admin/portfolio-cleanup/delete', { confirm_slug: confirmation }).subscribe({
      next: res => {
        this.cleanupResult.set(res);
        this.cleanupPreview.set(res);
        this.cleanupConfirmation.set('');
        this.cleanupDeleting.set(false);
        this.loadWorkstreams();
        this.loadBusinessUnits();
        this.loadUsers();
        this.loadAuditLogs();
      },
      error: err => {
        this.cleanupError.set(err.error?.detail || 'Could not delete portfolio data');
        this.cleanupDeleting.set(false);
      },
    });
  }

  getAuditIcon(action: string): string {
    switch(action) {
      case 'create': return 'add_circle';
      case 'update': return 'edit';
      case 'delete': return 'delete';
      case 'approve': return 'check_circle';
      case 'reject': return 'cancel';
      default: return 'history';
    }
  }

  formatBillingStatus(value: string | undefined): string {
    return (value || 'not configured').replace(/_/g, ' ');
  }

  formatRecurringPrice(): string {
    const cents = Number(this.billing().amount_cents || this.billing().price_per_user_cents || 0);
    const currency = String(this.billing().currency || 'usd').toUpperCase();
    const interval = this.billing().billing_interval || 'month';
    if (!cents) return 'Not configured';
    return `${currency} ${(cents / 100).toFixed(2)} / ${interval}`;
  }

  priceConfiguration(): any[] {
    return this.billing().stripe_price_configuration || [];
  }

  configuredPriceCount(): number {
    return this.priceConfiguration().filter(price => price.configured).length;
  }

  cleanupObjects(): { key: string; label: string; count: number }[] {
    const counts = this.cleanupPreview().object_counts || {};
    return [
      { key: 'initiatives', label: 'Initiatives', count: Number(counts.initiatives || 0) },
      { key: 'financials', label: 'Financials', count: Number(counts.financials || 0) },
      { key: 'kpis', label: 'KPIs', count: Number(counts.kpis || 0) },
      { key: 'risks', label: 'Risks', count: Number(counts.risks || 0) },
      { key: 'milestones', label: 'Milestones', count: Number(counts.milestones || 0) },
      { key: 'meetings', label: 'Meetings', count: Number(counts.meetings || 0) },
      { key: 'action_items', label: 'Action items', count: Number(counts.action_items || 0) },
      { key: 'governance', label: 'Gate submissions', count: Number(counts.governance || 0) },
      { key: 'status_updates', label: 'Status updates', count: Number(counts.status_updates || 0) },
    ];
  }

  normalizedCleanupConfirmation(): string {
    return this.cleanupConfirmation().trim();
  }

  formatCents(cents: number | undefined, currency: string | undefined): string {
    if (!cents) return 'Custom';
    return `${String(currency || 'usd').toUpperCase()} ${(Number(cents) / 100).toFixed(2)}`;
  }
}
