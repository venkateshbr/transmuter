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
          @for (tab of ['General', 'Billing', 'Data Cleanup', 'Strategic Parameters', 'Financial Configuration', 'Dashboard Configuration', 'Access Control', 'Governance Engine', 'Audit Logs']; track tab) {
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
               <section class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-5">
                 <div class="flex items-start justify-between gap-4">
                   <div>
                     <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">First-run setup</p>
                     <h3 class="mt-1 text-xl font-black text-[var(--t-text-primary)]">{{ setupStatus().completed || 0 }}/{{ setupStatus().total || 0 }} complete</h3>
                   </div>
                   <button type="button" (click)="loadSetupStatus()" class="btn-secondary px-4 py-2 text-xs" aria-label="Refresh setup status">Refresh</button>
                 </div>
                 <div class="mt-5 grid gap-3 md:grid-cols-3">
                   @for (check of setupStatus().checks || []; track check.key) {
                     <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3">
                       <p class="text-[9px] font-black uppercase tracking-widest" [class.text-emerald-500]="check.complete" [class.text-amber-500]="!check.complete">
                         {{ check.complete ? 'Complete' : 'Open' }}
                       </p>
                       <p class="mt-1 text-xs font-black text-[var(--t-text-primary)]">{{ check.label }}</p>
                       @if (check.key === 'gate_criteria' && check.details?.gates_missing_criteria > 0) {
                         <p class="mt-2 text-[10px] font-bold uppercase tracking-widest text-[var(--t-text-tertiary)]">
                           Missing criteria for gate{{ check.details.gates_missing_criteria === 1 ? '' : 's' }}
                           {{ check.details.missing_gate_numbers?.join(', ') }}
                         </p>
                       }
                     </div>
                   }
                 </div>
               </section>
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

            <div class="card overflow-hidden">
              <section class="border-b border-red-500/30 bg-red-500/10 p-8">
                <p class="text-[10px] font-black uppercase tracking-widest text-red-500">Destructive initiative operation</p>
                <h3 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">Delete one initiative</h3>
                <p class="mt-2 max-w-2xl text-sm leading-6 text-[var(--t-text-secondary)]">
                  Removes the selected initiative and its dependent financials, KPIs, risks, milestones,
                  status updates, governance submissions, team assignments, meeting links, agenda items, and action items.
                </p>
              </section>

              <section class="grid gap-6 p-8 lg:grid-cols-[1fr_0.8fr]">
                <div class="space-y-3">
                  @for (initiative of initiativeDeleteCandidates(); track initiative.id) {
                    <button
                      type="button"
                      class="w-full border p-4 text-left transition-colors"
                      [class.border-red-500]="selectedInitiativeDeleteId() === initiative.id"
                      [class.bg-red-500/10]="selectedInitiativeDeleteId() === initiative.id"
                      [class.border-[var(--t-border)]]="selectedInitiativeDeleteId() !== initiative.id"
                      [class.bg-[var(--t-surface-raised)]]="selectedInitiativeDeleteId() !== initiative.id"
                      (click)="selectInitiativeForDelete(initiative.id)"
                      [attr.aria-label]="'Select ' + initiative.name + ' for deletion'">
                      <div class="flex items-start justify-between gap-4">
                        <div class="min-w-0">
                          <p class="font-mono text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ initiative.initiative_code }}</p>
                          <p class="mt-1 truncate text-sm font-black text-[var(--t-text-primary)]">{{ initiative.name }}</p>
                        </div>
                        <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ labelize(initiative.stage || '') }}</span>
                      </div>
                    </button>
                  }
                  @if (!initiativeDeleteCandidates().length) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 text-sm font-bold text-[var(--t-text-secondary)]">
                      No initiatives available.
                    </div>
                  }
                </div>

                <div class="border border-red-500/30 bg-[var(--t-surface-raised)] p-5">
                  <p class="text-sm font-black text-[var(--t-text-primary)]">
                    {{ selectedInitiativeForDelete()?.name || 'Select an initiative' }}
                  </p>
                  <p class="mt-1 font-mono text-xs text-[var(--t-text-tertiary)]">
                    {{ selectedInitiativeForDelete()?.initiative_code || 'No initiative selected' }}
                  </p>

                  <label class="mt-5 block">
                    <span class="text-[10px] font-black uppercase tracking-widest text-red-500">
                      Type initiative code to confirm
                    </span>
                    <input
                      class="input-field mt-2 w-full font-mono"
                      [ngModel]="initiativeDeleteConfirmation()"
                      (ngModelChange)="initiativeDeleteConfirmation.set($event)"
                      [placeholder]="selectedInitiativeForDelete()?.initiative_code || ''"
                      aria-label="Initiative delete confirmation code">
                  </label>

                  @if (initiativeDeleteError()) {
                    <div class="mt-4 border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
                      {{ initiativeDeleteError() }}
                    </div>
                  }

                  @if (initiativeDeleteResult()) {
                    <div class="mt-4 border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-600">
                      Deleted {{ initiativeDeleteResult().initiative_code }}.
                    </div>
                  }

                  <div class="mt-5 flex justify-end gap-3">
                    <button type="button" class="btn-ghost border border-[var(--t-border)] px-4 py-2 text-xs font-black uppercase" (click)="loadInitiativeDeleteCandidates()" aria-label="Refresh initiative delete list">
                      Refresh
                    </button>
                    <button
                      type="button"
                      class="border border-red-500 bg-red-500 px-4 py-2 text-xs font-black uppercase text-white disabled:cursor-not-allowed disabled:opacity-40"
                      [disabled]="!canDeleteSelectedInitiative() || initiativeDeleting()"
                      (click)="deleteSelectedInitiative()"
                      aria-label="Delete selected initiative">
                      {{ initiativeDeleting() ? 'Deleting...' : 'Delete initiative' }}
                    </button>
                  </div>
                </div>
              </section>
            </div>

            <div class="card overflow-hidden">
              <section class="border-b border-red-500/30 bg-red-500/10 p-8">
                <p class="text-[10px] font-black uppercase tracking-widest text-red-500">Destructive meeting operation</p>
                <h3 class="mt-2 text-2xl font-black text-[var(--t-text-primary)]">Delete selected meetings</h3>
                <p class="mt-2 max-w-2xl text-sm leading-6 text-[var(--t-text-secondary)]">
                  Select one or more meeting series to delete. This removes sessions, notes, transcripts, agenda items,
                  attendees, meeting links, Teams sync rows, artifacts, and meeting-created action/risk records.
                </p>
              </section>

              <section class="grid gap-6 p-8 lg:grid-cols-[1fr_0.8fr]">
                <div class="space-y-3">
                  @for (meeting of meetingCleanupCandidates(); track meeting.id) {
                    <label
                      class="block border p-4 transition-colors"
                      [class.border-red-500]="selectedMeetingCleanupIds().includes(meeting.id)"
                      [class.bg-red-500/10]="selectedMeetingCleanupIds().includes(meeting.id)"
                      [class.border-[var(--t-border)]]="!selectedMeetingCleanupIds().includes(meeting.id)"
                      [class.bg-[var(--t-surface-raised)]]="!selectedMeetingCleanupIds().includes(meeting.id)">
                      <div class="flex items-start gap-3">
                        <input
                          type="checkbox"
                          class="mt-1 h-4 w-4"
                          [checked]="selectedMeetingCleanupIds().includes(meeting.id)"
                          (change)="toggleMeetingCleanupSelection(meeting.id, $any($event.target).checked)"
                          [attr.aria-label]="'Select meeting ' + meeting.name + ' for cleanup'" />
                        <div class="min-w-0 flex-1">
                          <div class="flex items-start justify-between gap-4">
                            <div class="min-w-0">
                              <p class="truncate text-sm font-black text-[var(--t-text-primary)]">{{ meeting.name }}</p>
                              <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                                {{ recurrenceLabel(meeting.recurrence) }} · {{ meeting.users?.display_name || 'No owner' }}
                              </p>
                            </div>
                            <span class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">
                              {{ meeting.dependent_count || 0 }} rows
                            </span>
                          </div>
                        </div>
                      </div>
                    </label>
                  }
                  @if (!meetingCleanupCandidates().length) {
                    <div class="border border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 text-sm font-bold text-[var(--t-text-secondary)]">
                      No meeting series available.
                    </div>
                  }
                </div>

                <div class="border border-red-500/30 bg-[var(--t-surface-raised)] p-5">
                  <p class="text-sm font-black text-[var(--t-text-primary)]">
                    {{ selectedMeetingCleanupIds().length }} meeting{{ selectedMeetingCleanupIds().length === 1 ? '' : 's' }} selected
                  </p>
                  <p class="mt-2 text-sm leading-6 text-[var(--t-text-secondary)]">
                    Type <span class="font-mono font-black">DELETE MEETINGS</span> to confirm bulk deletion.
                  </p>

                  <label class="mt-5 block">
                    <span class="text-[10px] font-black uppercase tracking-widest text-red-500">
                      Confirmation
                    </span>
                    <input
                      class="input-field mt-2 w-full font-mono"
                      [ngModel]="meetingCleanupConfirmation()"
                      (ngModelChange)="meetingCleanupConfirmation.set($event)"
                      placeholder="DELETE MEETINGS"
                      aria-label="Meeting cleanup confirmation phrase">
                  </label>

                  @if (meetingCleanupError()) {
                    <div class="mt-4 border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500">
                      {{ meetingCleanupError() }}
                    </div>
                  }

                  @if (meetingCleanupResult()) {
                    <div class="mt-4 border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm font-bold text-emerald-600">
                      Deleted {{ meetingCleanupResult().deleted_meetings?.length || 0 }} meeting series.
                    </div>
                  }

                  <div class="mt-5 flex justify-end gap-3">
                    <button type="button" class="btn-ghost border border-[var(--t-border)] px-4 py-2 text-xs font-black uppercase" (click)="loadMeetingCleanupCandidates()" aria-label="Refresh meeting cleanup list">
                      Refresh
                    </button>
                    <button
                      type="button"
                      class="border border-red-500 bg-red-500 px-4 py-2 text-xs font-black uppercase text-white disabled:cursor-not-allowed disabled:opacity-40"
                      [disabled]="!canDeleteSelectedMeetings() || meetingCleanupDeleting()"
                      (click)="deleteSelectedMeetings()"
                      aria-label="Delete selected meetings">
                      {{ meetingCleanupDeleting() ? 'Deleting...' : 'Delete meetings' }}
                    </button>
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
                    <div class="grid gap-4 p-4 rounded-xl border border-[var(--t-border)] hover:bg-[var(--t-surface-raised)]/30 transition-all sm:grid-cols-[1fr_auto] sm:items-center">
                      <div class="flex items-center gap-4 min-w-0">
                        <div class="w-8 h-8 rounded-lg bg-[var(--t-accent-soft)] flex items-center justify-center text-[var(--t-accent)]">
                          <span class="material-icons text-sm">hub</span>
                        </div>
                        <input type="text" [ngModel]="ws.name" (ngModelChange)="ws.name = $event" (blur)="updateWorkstream(ws)" aria-label="Workstream name" class="bg-transparent border-none outline-none font-bold text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                      </div>
                      <button type="button" (click)="deleteWorkstream(ws.id)" aria-label="Delete workstream" class="btn-ghost p-2 text-red-500/60 hover:text-red-500 hover:bg-red-500/10">
                        <span class="material-icons text-sm">delete</span>
                      </button>
                    </div>
                  }
                  
                  <!-- Inline Add -->
                  <div class="grid gap-4 p-4 rounded-xl border border-dashed border-[var(--t-border)] sm:grid-cols-[1fr_auto] sm:items-center">
                    <div class="flex items-center gap-4 min-w-0">
                      <div class="w-8 h-8 rounded-lg bg-[var(--t-surface-raised)] flex items-center justify-center text-[var(--t-text-tertiary)]">
                        <span class="material-icons text-sm">add</span>
                      </div>
                      <input type="text" [ngModel]="newWorkstreamName()" (ngModelChange)="newWorkstreamName.set($event)" (keyup.enter)="addWorkstream()" aria-label="New workstream name" placeholder="Type new workstream name..." class="bg-transparent border-none outline-none text-sm text-[var(--t-text-primary)] min-w-0 w-full">
                    </div>
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

          @if (activeTab === 'Financial Configuration') {
            <div class="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
              <div class="card p-8 xl:col-span-2">
                <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Financial Metric Engine</h3>
                    <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Tenant-owned metrics, scenarios, currency, and fiscal calendar</p>
                  </div>
                  <div class="flex flex-wrap items-center gap-3">
                    <label class="grid gap-1">
                      <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Currency</span>
                      <input class="input-field w-24 py-2 text-xs uppercase" [ngModel]="reportingSettings().reporting_currency" (ngModelChange)="updateReportingCurrency($event)" maxlength="3" aria-label="Reporting currency">
                    </label>
                    <label class="grid gap-1">
                      <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Fiscal Start</span>
                      <select class="input-field w-36 py-2 text-xs" [ngModel]="reportingSettings().fiscal_year_start_month" (ngModelChange)="updateFiscalStartMonth($event)" aria-label="Fiscal year start month">
                        @for (month of fiscalMonths; track month.value) {
                          <option [ngValue]="month.value">{{ month.label }}</option>
                        }
                      </select>
                    </label>
                    <button type="button" class="btn-primary px-4 py-2 text-[10px]" (click)="saveReportingSettings()" aria-label="Save reporting settings">Save Settings</button>
                  </div>
                </div>

                <div class="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
                  <section class="border border-[var(--t-border)]">
                    <div class="flex items-center justify-between gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                      <div>
                        <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Metric Definitions</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">{{ metricDefinitions().length }} configured metrics</p>
                      </div>
                      <button type="button" class="btn-secondary px-3 py-2 text-[10px]" (click)="addMetricDefinition()" aria-label="Add metric definition">Add Metric</button>
                    </div>
                    <div class="divide-y divide-[var(--t-border)]">
                      @for (metric of metricDefinitions(); track metric.id || metric.key) {
                        <div class="grid gap-3 p-4 lg:grid-cols-[1fr_120px_120px_120px_auto] lg:items-end">
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                            <input class="input-field py-2 text-xs font-bold" [ngModel]="metric.label" (ngModelChange)="metric.label = $event" aria-label="Metric definition label">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Type</span>
                            <select class="input-field py-2 text-xs" [ngModel]="metric.value_type" (ngModelChange)="metric.value_type = $event" aria-label="Metric value type">
                              <option value="currency">Currency</option>
                              <option value="percent">Percent</option>
                              <option value="number">Number</option>
                            </select>
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Aggregation</span>
                            <select class="input-field py-2 text-xs" [ngModel]="metric.aggregation" (ngModelChange)="metric.aggregation = $event" aria-label="Metric aggregation">
                              <option value="sum">Sum</option>
                              <option value="avg">Average</option>
                              <option value="last">Last</option>
                              <option value="formula">Formula</option>
                            </select>
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Benefit</span>
                            <select class="input-field py-2 text-xs" [ngModel]="metric.benefit_class || ''" (ngModelChange)="updateMetricBenefitClass(metric, $event)" aria-label="Benefit class">
                              <option value="">No</option>
                              <option value="revenue">Revenue</option>
                              <option value="margin">Margin</option>
                              <option value="savings">Savings</option>
                              <option value="avoidance">Avoidance</option>
                              <option value="other">Other</option>
                            </select>
                          </label>
                          <div class="flex items-center gap-2">
                            <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="metric.is_active = !metric.is_active" [attr.aria-label]="'Toggle ' + metric.label">{{ metric.is_active ? 'Active' : 'Hidden' }}</button>
                            <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveMetricDefinition(metric)" aria-label="Save metric definition">Save</button>
                          </div>
                          @if (metric.aggregation === 'formula') {
                            <label class="grid gap-1 lg:col-span-5">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Formula</span>
                              <input class="input-field py-2 text-xs font-mono" [ngModel]="metric.formula || ''" (ngModelChange)="metric.formula = $event || null" aria-label="Metric formula" placeholder="revenue_uplift / baseline_revenue * 100">
                            </label>
                          }
                        </div>
                      }
                    </div>
                  </section>

                  <section class="border border-[var(--t-border)]">
                    <div class="flex flex-wrap items-end justify-between gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                      <div>
                        <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Annual Baselines</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">Tenant-wide original operating metrics</p>
                      </div>
                      <div class="flex items-end gap-2">
                        <label class="grid gap-1">
                          <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Fiscal Year</span>
                          <input type="number" min="2020" max="2060" class="input-field w-28 py-2 text-xs" [ngModel]="tenantBaselineYear()" (ngModelChange)="setTenantBaselineYear($event)" aria-label="Tenant baseline fiscal year">
                        </label>
                        <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveTenantAnnualBaselines()" aria-label="Save tenant annual baselines">Save</button>
                      </div>
                    </div>
                    <div class="grid gap-3 p-4 md:grid-cols-2">
                      @for (metric of tenantBaselineMetrics(); track metric.id || metric.key) {
                        <label class="grid gap-1">
                          <span class="truncate text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ metric.label }}</span>
                          <input
                            type="number"
                            class="input-field py-2 text-xs"
                            [ngModel]="tenantBaselineValue(metric.id)"
                            (ngModelChange)="setTenantBaselineValue(metric.id, $event)"
                            [attr.aria-label]="'Tenant annual baseline for ' + metric.label">
                        </label>
                      }
                    </div>
                  </section>

                  <section class="border border-[var(--t-border)]">
                    <div class="flex items-center justify-between gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                      <div>
                        <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Scenarios</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">Plan, actual, baseline, and tenant-specific lanes</p>
                      </div>
                      <button type="button" class="btn-secondary px-3 py-2 text-[10px]" (click)="addScenarioDefinition()" aria-label="Add scenario">Add Scenario</button>
                    </div>
                    <div class="divide-y divide-[var(--t-border)]">
                      @for (scenario of scenarioDefinitions(); track scenario.id || scenario.key) {
                        <div class="grid gap-3 p-4 sm:grid-cols-[1fr_120px_auto] sm:items-end">
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                            <input class="input-field py-2 text-xs font-bold" [ngModel]="scenario.label" (ngModelChange)="scenario.label = $event" aria-label="Scenario label">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Kind</span>
                            <select class="input-field py-2 text-xs" [ngModel]="scenario.kind" (ngModelChange)="scenario.kind = $event" aria-label="Scenario kind">
                              <option value="baseline">Baseline</option>
                              <option value="plan">Plan</option>
                              <option value="forecast">Forecast</option>
                              <option value="actual">Actual</option>
                            </select>
                          </label>
                          <div class="flex items-center gap-2">
                            <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="scenario.is_active = !scenario.is_active" [attr.aria-label]="'Toggle ' + scenario.label">{{ scenario.is_active ? 'Active' : 'Hidden' }}</button>
                            <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveScenarioDefinition(scenario)" aria-label="Save scenario">Save</button>
                          </div>
                        </div>
                      }
                    </div>
                  </section>

                  <section class="border border-[var(--t-border)]">
                    <div class="flex items-center justify-between gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                      <div>
                        <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Value Bridge Rows</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">Tenant-defined bridge lines for portfolio and initiative value reporting</p>
                      </div>
                      <button type="button" class="btn-secondary px-3 py-2 text-[10px]" (click)="addBridgeRowDefinition()" aria-label="Add value bridge row">Add Row</button>
                    </div>
                    <div class="divide-y divide-[var(--t-border)]">
                      @for (row of bridgeRows(); track row.id || row.key) {
                        <div class="grid gap-4 p-4">
                          <div class="grid gap-3 lg:grid-cols-[1fr_150px_110px_100px_auto] lg:items-end">
                            <label class="grid gap-1">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                              <input class="input-field py-2 text-xs font-bold" [ngModel]="row.label" (ngModelChange)="row.label = $event" aria-label="Bridge row label">
                            </label>
                            <label class="grid gap-1">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Kind</span>
                              <select class="input-field py-2 text-xs" [ngModel]="row.row_kind" (ngModelChange)="row.row_kind = $event" aria-label="Bridge row kind">
                                <option value="metric_set">Metrics</option>
                                <option value="cost_set">Costs</option>
                                <option value="subtotal">Subtotal</option>
                                <option value="net">Net</option>
                              </select>
                            </label>
                            <label class="grid gap-1">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Sign</span>
                              <select class="input-field py-2 text-xs" [ngModel]="row.sign" (ngModelChange)="row.sign = numberValue($event)" aria-label="Bridge row sign">
                                <option [ngValue]="1">Positive</option>
                                <option [ngValue]="-1">Negative</option>
                              </select>
                            </label>
                            <label class="grid gap-1">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Order</span>
                              <input type="number" class="input-field py-2 text-xs" [ngModel]="row.display_order" (ngModelChange)="row.display_order = numberValue($event)" aria-label="Bridge row display order">
                            </label>
                            <div class="flex items-center gap-2">
                              <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="row.is_active = !row.is_active" [attr.aria-label]="'Toggle ' + row.label">{{ row.is_active ? 'Active' : 'Hidden' }}</button>
                              <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveBridgeRowDefinition(row)" aria-label="Save value bridge row">Save</button>
                            </div>
                          </div>

                          @if (row.row_kind !== 'net') {
                            <div class="grid gap-4 lg:grid-cols-2">
                              <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3">
                                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Metric Inputs</p>
                                <div class="mt-3 grid gap-2 sm:grid-cols-2">
                                  @for (metric of metricDefinitions(); track metric.id || metric.key) {
                                    <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-primary)]">
                                      <input type="checkbox" [checked]="bridgeRowMetricSelected(row, metric.id)" (change)="toggleBridgeRowMetric(row, metric.id)" [attr.aria-label]="'Use metric ' + metric.label + ' in bridge row'">
                                      <span>{{ metric.label }}</span>
                                    </label>
                                  }
                                </div>
                              </div>
                              <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-3">
                                <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Cost Category Inputs</p>
                                <div class="mt-3 grid gap-2 sm:grid-cols-2">
                                  @for (category of activeCostCategoryItems(); track category.key) {
                                    <label class="flex items-center gap-2 text-xs font-bold text-[var(--t-text-primary)]">
                                      <input type="checkbox" [checked]="bridgeRowCostCategorySelected(row, category.id)" (change)="toggleBridgeRowCostCategory(row, category.id)" [attr.aria-label]="'Use cost category ' + category.label + ' in bridge row'">
                                      <span>{{ category.label }}</span>
                                    </label>
                                  }
                                </div>
                              </div>
                            </div>
                          }
                        </div>
                      }
                    </div>
                  </section>

                  <section class="border border-[var(--t-border)]">
                    <div class="flex items-center justify-between gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] px-4 py-3">
                      <div>
                        <p class="text-xs font-black uppercase tracking-widest text-[var(--t-accent)]">Line Attribute Registry</p>
                        <p class="mt-1 text-[10px] text-[var(--t-text-tertiary)]">Reusable fields for benefit and cost lines</p>
                      </div>
                      <button type="button" class="btn-secondary px-3 py-2 text-[10px]" (click)="addAttributeDefinition()" aria-label="Add financial line attribute">Add Attribute</button>
                    </div>
                    <div class="divide-y divide-[var(--t-border)]">
                      @for (attribute of attributeDefinitions(); track attribute.id || attribute.key) {
                        <div class="grid gap-3 p-4 lg:grid-cols-[1fr_130px_130px_90px_auto] lg:items-end">
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                            <input class="input-field py-2 text-xs font-bold" [ngModel]="attribute.label" (ngModelChange)="attribute.label = $event" aria-label="Attribute label">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Applies To</span>
                            <select class="input-field py-2 text-xs" [ngModel]="attribute.entity_type" (ngModelChange)="attribute.entity_type = $event" aria-label="Attribute entity type">
                              <option value="benefit_line">Benefit Lines</option>
                              <option value="cost_line">Cost Lines</option>
                            </select>
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Value Type</span>
                            <select class="input-field py-2 text-xs" [ngModel]="attribute.value_type" (ngModelChange)="attribute.value_type = $event" aria-label="Attribute value type">
                              <option value="text">Text</option>
                              <option value="number">Number</option>
                              <option value="currency">Currency</option>
                              <option value="percent">Percent</option>
                              <option value="date">Date</option>
                              <option value="select">Select</option>
                              <option value="boolean">Boolean</option>
                            </select>
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Order</span>
                            <input type="number" class="input-field py-2 text-xs" [ngModel]="attribute.display_order" (ngModelChange)="attribute.display_order = numberValue($event)" aria-label="Attribute display order">
                          </label>
                          <div class="flex items-center gap-2">
                            <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="attribute.is_required = !attribute.is_required" [attr.aria-label]="'Toggle required for ' + attribute.label">{{ attribute.is_required ? 'Required' : 'Optional' }}</button>
                            <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="attribute.is_active = !attribute.is_active" [attr.aria-label]="'Toggle ' + attribute.label">{{ attribute.is_active ? 'Active' : 'Hidden' }}</button>
                            <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveAttributeDefinition(attribute)" aria-label="Save attribute definition">Save</button>
                          </div>
                          @if (attribute.value_type === 'select') {
                            <label class="grid gap-1 lg:col-span-5">
                              <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Select Options</span>
                              <input class="input-field py-2 text-xs" [ngModel]="attributeOptionsText(attribute)" (ngModelChange)="setAttributeOptionsText(attribute, $event)" aria-label="Attribute select options" placeholder="Option A, Option B, Option C">
                            </label>
                          }
                        </div>
                      }
                    </div>
                  </section>
                </div>
              </div>

              <div class="card p-8 xl:col-span-2">
                <div class="mb-6 flex items-start justify-between gap-4">
                  <div>
                    <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Cost Categories</h3>
                    <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Engine-owned taxonomy for initiative cost lines and bridge rows</p>
                  </div>
                  <button type="button" class="btn-secondary px-4 py-2 text-[10px]" (click)="addCostCategoryDefinition()" aria-label="Add cost category">Add Category</button>
                </div>
                <div class="divide-y divide-[var(--t-border)] border border-[var(--t-border)]">
                  @for (category of costCategories(); track category.id || category.key) {
                    <div class="grid gap-3 p-4 lg:grid-cols-[1fr_140px_140px_90px_auto] lg:items-end">
                      <label class="grid gap-1">
                        <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                        <input class="input-field py-2 text-xs font-bold" [ngModel]="category.label" (ngModelChange)="category.label = $event" aria-label="Cost category label">
                      </label>
                      <label class="grid gap-1">
                        <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Group</span>
                        <input class="input-field py-2 text-xs" [ngModel]="category.group_key || ''" (ngModelChange)="category.group_key = $event || null" aria-label="Cost category group">
                      </label>
                      <label class="grid gap-1">
                        <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Rollup</span>
                        <select class="input-field py-2 text-xs" [ngModel]="category.rollup_type || ''" (ngModelChange)="category.rollup_type = $event || null" aria-label="Cost category rollup">
                          <option value="">Unclassified</option>
                          <option value="recurring_cost">Recurring</option>
                          <option value="one_off_cost">One-time</option>
                          <option value="total_cost">Total cost</option>
                        </select>
                      </label>
                      <label class="grid gap-1">
                        <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Order</span>
                        <input type="number" class="input-field py-2 text-xs" [ngModel]="category.display_order" (ngModelChange)="category.display_order = numberValue($event)" aria-label="Cost category display order">
                      </label>
                      <div class="flex items-center gap-2">
                        <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="category.is_active = !category.is_active" [attr.aria-label]="'Toggle ' + category.label">
                          {{ category.is_active ? 'Active' : 'Hidden' }}
                        </button>
                        <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveCostCategoryDefinition(category)" aria-label="Save cost category">Save</button>
                      </div>
                    </div>
                  }
                </div>
              </div>
            </div>
          }

          @if (activeTab === 'Dashboard Configuration') {
            <div class="card p-8">
              <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Dashboard Configuration</h3>
                  <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Tenant menu visibility, labels, and dashboard order</p>
                </div>
                <button type="button" class="btn-primary px-4 py-2 text-[10px]" (click)="saveDashboardConfiguration()" aria-label="Save dashboard configuration">Save Configuration</button>
              </div>
              <div class="divide-y divide-[var(--t-border)] border border-[var(--t-border)]">
                @for (dashboard of dashboardConfiguration(); track dashboard.dashboard_key) {
                  <div class="grid gap-3 p-4 lg:grid-cols-[110px_1fr_170px_90px_120px] lg:items-end">
                    <label class="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-[var(--t-text-primary)]">
                      <input type="checkbox" [ngModel]="dashboard.is_enabled" (ngModelChange)="dashboard.is_enabled = $event" [attr.aria-label]="'Enable ' + dashboard.label">
                      Enabled
                    </label>
                    <label class="grid gap-1">
                      <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                      <input class="input-field py-2 text-xs font-bold" [ngModel]="dashboard.label" (ngModelChange)="dashboard.label = $event" aria-label="Dashboard label">
                    </label>
                    <label class="grid gap-1">
                      <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Menu Group</span>
                      <select class="input-field py-2 text-xs" [ngModel]="dashboard.menu_group" (ngModelChange)="dashboard.menu_group = $event" aria-label="Dashboard menu group">
                        <option value="dashboard">Dashboard menu</option>
                        <option value="primary">Primary nav</option>
                        <option value="hidden">Hidden</option>
                      </select>
                    </label>
                    <label class="grid gap-1">
                      <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Order</span>
                      <input type="number" class="input-field py-2 text-xs" [ngModel]="dashboard.display_order" (ngModelChange)="dashboard.display_order = numberValue($event)" aria-label="Dashboard display order">
                    </label>
                    <div>
                      <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Route</p>
                      <p class="mt-2 truncate font-mono text-[10px] text-[var(--t-text-secondary)]">{{ dashboard.route_path }}</p>
                    </div>
                  </div>
                }
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
                <div class="card p-8">
                  <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Stage Gates</h3>
                      <p class="mt-1 text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Configure tenant stage transitions, approval rules, and movement criteria</p>
                    </div>
                    <button type="button" (click)="addStageGateDefinition()" aria-label="Add stage gate" class="btn-primary px-4 py-2 text-[10px]">Add Gate</button>
                  </div>

                  <div class="space-y-5">
                    @for (gate of stageGateDefinitions(); track gate.id || gate.key) {
                      <section class="border border-[var(--t-border)] bg-[var(--t-surface)]">
                        <div class="grid gap-3 border-b border-[var(--t-border)] bg-[var(--t-surface-raised)] p-4 lg:grid-cols-[80px_1fr_1fr_1fr_auto] lg:items-end">
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Gate</span>
                            <input type="number" min="1" max="10" class="input-field py-2 text-xs" [ngModel]="gate.gate_number" (ngModelChange)="gate.gate_number = numberValue($event)" aria-label="Gate number">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Label</span>
                            <input class="input-field py-2 text-xs font-bold" [ngModel]="gate.label" (ngModelChange)="gate.label = $event" aria-label="Gate label">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">From Stage</span>
                            <input class="input-field py-2 text-xs" [ngModel]="gate.from_stage" (ngModelChange)="gate.from_stage = $event" aria-label="Gate from stage">
                          </label>
                          <label class="grid gap-1">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">To Stage</span>
                            <input class="input-field py-2 text-xs" [ngModel]="gate.to_stage" (ngModelChange)="gate.to_stage = $event" aria-label="Gate to stage">
                          </label>
                          <div class="flex items-center gap-2">
                            <button type="button" class="btn-ghost px-3 py-2 text-[10px]" (click)="gate.is_active = !gate.is_active" [attr.aria-label]="'Toggle ' + gate.label">{{ gate.is_active ? 'Active' : 'Hidden' }}</button>
                            <button type="button" class="btn-primary px-3 py-2 text-[10px]" (click)="saveStageGateDefinition(gate)" aria-label="Save stage gate">Save</button>
                          </div>
                        </div>

                        <div class="grid gap-4 p-4 lg:grid-cols-[1fr_1fr]">
                          <label class="flex items-center gap-3 text-xs font-bold text-[var(--t-text-primary)]">
                            <input type="checkbox" [checked]="gate.approval_required" (change)="gate.approval_required = !gate.approval_required" aria-label="Approval required">
                            Approval required
                          </label>
                          <label class="flex items-center gap-3 text-xs font-bold text-[var(--t-text-primary)]">
                            <input type="checkbox" [checked]="gate.require_all_criteria" (change)="gate.require_all_criteria = !gate.require_all_criteria" aria-label="Require all criteria">
                            Require all active criteria
                          </label>
                          <label class="grid gap-1 lg:col-span-2">
                            <span class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Approver Roles</span>
                            <input class="input-field py-2 text-xs font-mono" [ngModel]="rolesText(gate.approver_roles)" (ngModelChange)="gate.approver_roles = splitRoles($event)" aria-label="Approver roles" placeholder="transformation_office, initiative_owner">
                          </label>
                        </div>

                        <div class="border-t border-[var(--t-border)] p-4">
                          <div class="mb-3 flex items-center justify-between gap-3">
                            <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Checklist Criteria</p>
                            <span class="text-[10px] text-[var(--t-text-tertiary)]">{{ criteriaForGate(gate.gate_number).length }} rules</span>
                          </div>

                          <div class="space-y-2">
                            @for (criterion of criteriaForGate(gate.gate_number); track criterion.id) {
                              <div class="grid gap-3 border border-[var(--t-border)] p-3 sm:grid-cols-[auto_1fr_auto] sm:items-center">
                                <input type="checkbox" [checked]="criterion.is_active" (change)="toggleCriterion(criterion)" aria-label="Toggle gate criterion" class="h-4 w-4 border-[var(--t-border)] text-[var(--t-accent)]">
                                <input class="input-field py-2 text-xs font-bold" [ngModel]="criterion.label" (ngModelChange)="criterion.label = $event" (blur)="saveCriterion(criterion)" aria-label="Gate criterion label">
                                <button type="button" (click)="deleteCriterion(criterion.id)" aria-label="Delete gate criterion" class="btn-ghost px-3 py-2 text-[10px]">Delete</button>
                              </div>
                            }

                            <div class="grid gap-3 border border-dashed border-[var(--t-border)] p-3 sm:grid-cols-[1fr_auto]">
                              <input type="text" [ngModel]="newCriterionForGate(gate.gate_number)" (ngModelChange)="setNewCriterionForGate(gate.gate_number, $event)" (keyup.enter)="addCriterion(gate.gate_number)" aria-label="New gate criterion" placeholder="Add movement criterion..." class="input-field py-2 text-xs">
                              <button type="button" (click)="addCriterion(gate.gate_number)" [disabled]="!newCriterionForGate(gate.gate_number).trim()" aria-label="Create gate criterion" class="btn-primary px-4 py-2 text-[10px]">Add Rule</button>
                            </div>
                          </div>
                        </div>
                      </section>
                    }
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
  setupStatus = signal<any>({ checks: [], completed: 0, total: 0 });
  billingError = signal<string | null>(null);
  cleanupPreview = signal<any>({ object_counts: {}, preserved_objects: [] });
  cleanupResult = signal<any | null>(null);
  cleanupError = signal<string | null>(null);
  cleanupDeleting = signal(false);
  cleanupConfirmation = signal('');
  initiativeDeleteCandidates = signal<any[]>([]);
  selectedInitiativeDeleteId = signal('');
  initiativeDeleteConfirmation = signal('');
  initiativeDeleting = signal(false);
  initiativeDeleteError = signal<string | null>(null);
  initiativeDeleteResult = signal<any | null>(null);
  meetingCleanupCandidates = signal<any[]>([]);
  selectedMeetingCleanupIds = signal<string[]>([]);
  meetingCleanupConfirmation = signal('');
  meetingCleanupDeleting = signal(false);
  meetingCleanupError = signal<string | null>(null);
  meetingCleanupResult = signal<any | null>(null);
  gateCriteria = signal<any[]>([]);
  stageGateDefinitions = signal<any[]>([]);
  auditLogs = signal<any[]>([]);
  financialGroups = signal<any[]>([]);
  financialItems = signal<any[]>([]);
  metricDefinitions = signal<any[]>([]);
  scenarioDefinitions = signal<any[]>([]);
  costCategories = signal<any[]>([]);
  bridgeRows = signal<any[]>([]);
  attributeDefinitions = signal<any[]>([]);
  dashboardConfiguration = signal<any[]>([]);
  reportingSettings = signal<any>({ fiscal_year_start_month: 1, reporting_currency: 'USD' });
  tenantBaselineYear = signal(new Date().getFullYear());
  tenantAnnualBaselineValues = signal<Record<string, string>>({});

  // Inline add state
  newWorkstreamName = signal('');
  newBusinessUnitName = signal('');
  newMarketName = signal('');
  newThemeName = signal('');
  newTagName = signal('');
  newCriterionG1 = signal('');
  newCriterionG2 = signal('');
  newCriteriaByGate = signal<Record<number, string>>({});
  newMetricNames = signal<Record<string, string>>({});
  newCostCategoryNames = signal<Record<string, string>>({});

  private readonly defaultTags = ['automation', 'offshoring', 'commercial', 'other'];
  readonly fiscalMonths = [
    { value: 1, label: 'January' },
    { value: 2, label: 'February' },
    { value: 3, label: 'March' },
    { value: 4, label: 'April' },
    { value: 5, label: 'May' },
    { value: 6, label: 'June' },
    { value: 7, label: 'July' },
    { value: 8, label: 'August' },
    { value: 9, label: 'September' },
    { value: 10, label: 'October' },
    { value: 11, label: 'November' },
    { value: 12, label: 'December' },
  ];

  ngOnInit() {
    this.loadAll();
  }

  loadAll() {
    this.loadWorkstreams();
    this.loadBusinessUnits();
    this.loadUsers();
    this.loadSettings();
    this.loadBilling();
    this.loadSetupStatus();
    this.loadCleanupPreview();
    this.loadInitiativeDeleteCandidates();
    this.loadMeetingCleanupCandidates();
    this.loadGateCriteria();
    this.loadStageGateDefinitions();
    this.loadAuditLogs();
    this.loadFinancialConfiguration();
    this.loadFinancialEngineConfiguration();
    this.loadDashboardConfiguration();
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

  loadSetupStatus() {
    this.api.get<any>('/admin/setup-status').subscribe(res => this.setupStatus.set(res));
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

  loadInitiativeDeleteCandidates() {
    this.initiativeDeleteError.set(null);
    this.api.get<any>('/initiatives?page_size=200&sort_by=initiative_code').subscribe({
      next: res => this.initiativeDeleteCandidates.set(res.items || []),
      error: err => this.initiativeDeleteError.set(err.error?.detail || 'Could not load initiatives'),
    });
  }

  loadMeetingCleanupCandidates() {
    this.meetingCleanupError.set(null);
    this.api.get<any>('/admin/meeting-cleanup-candidates').subscribe({
      next: res => this.meetingCleanupCandidates.set(res.items || []),
      error: err => this.meetingCleanupError.set(err.error?.detail || 'Could not load meetings'),
    });
  }

  loadGateCriteria() {
    this.api.get<any>('/admin/governance/gate-criteria').subscribe(res => this.gateCriteria.set(Array.isArray(res) ? res : (res.items || [])));
  }

  loadStageGateDefinitions() {
    this.api.get<any[]>('/admin/governance/stage-gates').subscribe(res => this.stageGateDefinitions.set(res || []));
  }

  loadAuditLogs() {
    this.api.get<any>('/admin/audit-logs').subscribe(res => this.auditLogs.set(res.items || []));
  }

  loadFinancialConfiguration() {
    this.api.get<any>('/admin/financial-configuration').subscribe(res => {
      this.financialGroups.set(res.groups || []);
      this.financialItems.set(res.items || []);
    });
  }

  loadFinancialEngineConfiguration() {
    this.api.get<any>('/financial-engine-configuration').subscribe(res => {
      this.metricDefinitions.set(res.definitions || []);
      this.scenarioDefinitions.set(res.scenarios || []);
      this.costCategories.set(res.cost_categories || []);
      this.bridgeRows.set(res.bridge_rows || []);
      this.attributeDefinitions.set(res.attribute_definitions || []);
      this.reportingSettings.set(res.settings || { fiscal_year_start_month: 1, reporting_currency: 'USD' });
      this.loadTenantAnnualBaselines();
    });
  }

  loadDashboardConfiguration() {
    this.api.get<any>('/admin/dashboard-configuration').subscribe({
      next: res => this.dashboardConfiguration.set(res.dashboards || []),
      error: () => this.dashboardConfiguration.set([]),
    });
  }

  saveDashboardConfiguration() {
    const dashboards = this.dashboardConfiguration().map(item => ({
      ...item,
      display_order: Number(item.display_order || 0),
      is_enabled: item.is_enabled !== false,
      menu_group: item.menu_group || 'dashboard',
      allowed_roles: item.allowed_roles?.length
        ? item.allowed_roles
        : ['transformation_office', 'initiative_owner', 'viewer'],
      metadata: item.metadata || {},
    }));
    this.api.put<any>('/admin/dashboard-configuration', { dashboards }).subscribe(res => {
      this.dashboardConfiguration.set(res.dashboards || []);
      window.dispatchEvent(new CustomEvent('dashboard-configuration-updated'));
      this.loadAuditLogs();
    });
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
    }).subscribe(() => {
      this.loadWorkstreams();
      this.newWorkstreamName.set('');
    });
  }

  updateWorkstream(ws: any) {
    const name = String(ws.name || '').trim();
    if (!name) return;
    this.api.put(`/workstreams/${ws.id}`, {
      name,
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

  financialGroupsByKind(kind: 'calculation' | 'metric' | 'cost_category'): any[] {
    return this.financialGroups()
      .filter(group => group.kind === kind && group.is_active !== false)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
  }

  financialItemsForGroup(groupKey: string, itemType: 'metric' | 'cost_category'): any[] {
    return this.financialItems()
      .filter(item =>
        item.group_key === groupKey
        && item.item_type === itemType
        && (itemType === 'metric' || item.is_active !== false)
      )
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
  }

  saveFinancialConfiguration() {
    this.api.put('/admin/financial-configuration', {
      groups: this.financialGroups(),
      items: this.financialItems(),
    }).subscribe(() => {
      this.loadFinancialConfiguration();
      this.loadAuditLogs();
    });
  }

  updateReportingCurrency(value: string) {
    const currency = String(value || '').toUpperCase().slice(0, 3);
    this.reportingSettings.update(settings => ({ ...settings, reporting_currency: currency }));
  }

  updateFiscalStartMonth(value: number | string) {
    this.reportingSettings.update(settings => ({ ...settings, fiscal_year_start_month: this.numberValue(value) }));
  }

  saveReportingSettings() {
    const settings = this.reportingSettings();
    this.api.put('/admin/financial-engine/reporting-settings', {
      fiscal_year_start_month: Number(settings.fiscal_year_start_month || 1),
      reporting_currency: String(settings.reporting_currency || 'USD').toUpperCase().slice(0, 3),
    }).subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  loadTenantAnnualBaselines() {
    this.api.get<any>('/admin/financial-engine/annual-baselines').subscribe({
      next: response => {
        const values: Record<string, string> = {};
        const rows = response?.values || [];
        for (const row of rows) {
          if (Number(row.baseline_year) === Number(this.tenantBaselineYear())) {
            values[row.metric_definition_id] = row.value;
          }
        }
        this.tenantAnnualBaselineValues.set(values);
      },
      error: () => this.tenantAnnualBaselineValues.set({}),
    });
  }

  tenantBaselineMetrics(): any[] {
    return this.metricDefinitions()
      .filter(metric => metric?.is_active !== false && metric?.aggregation !== 'formula')
      .sort((a, b) =>
        Number(a.display_order || 0) - Number(b.display_order || 0)
        || String(a.label || '').localeCompare(String(b.label || '')),
      );
  }

  tenantBaselineValue(metricDefinitionId: string): string {
    return this.tenantAnnualBaselineValues()[metricDefinitionId] || '';
  }

  setTenantBaselineYear(value: number | string) {
    this.tenantBaselineYear.set(this.numberValue(value));
    this.loadTenantAnnualBaselines();
  }

  setTenantBaselineValue(metricDefinitionId: string, value: string | number) {
    this.tenantAnnualBaselineValues.update(values => ({
      ...values,
      [metricDefinitionId]: String(value ?? ''),
    }));
  }

  saveTenantAnnualBaselines() {
    const baselineYear = Number(this.tenantBaselineYear());
    const values = Object.entries(this.tenantAnnualBaselineValues())
      .map(([metric_definition_id, raw]) => ({
        metric_definition_id,
        baseline_year: baselineYear,
        value: String(raw ?? '').trim(),
      }))
      .filter(row => row.value !== '');
    this.api.put('/admin/financial-engine/annual-baselines', { values }).subscribe(() => {
      this.loadTenantAnnualBaselines();
      this.loadAuditLogs();
    });
  }

  addMetricDefinition() {
    const index = this.metricDefinitions().length + 1;
    const key = `custom_metric_${Date.now()}`;
    this.metricDefinitions.update(metrics => [
      ...metrics,
      {
        key,
        label: `Custom Metric ${index}`,
        group_key: 'custom',
        value_type: 'currency',
        unit: null,
        direction: 'increase_good',
        aggregation: 'sum',
        rollup_type: 'benefit',
        is_benefit: true,
        benefit_class: 'other',
        cost_behavior: null,
        formula: null,
        formula_inputs: [],
        precision: 4,
        display_order: 1000 + index,
        applies_to: 'opt_in',
        validation: {},
        is_system: false,
        is_active: true,
      },
    ]);
  }

  saveMetricDefinition(metric: any) {
    const payload = {
      key: metric.key || this.uniqueEngineKey(metric.label, 'metric', this.metricDefinitions()),
      label: metric.label,
      description: metric.description || null,
      group_key: metric.group_key || null,
      value_type: metric.value_type || 'currency',
      unit: metric.unit || null,
      direction: metric.direction || 'increase_good',
      aggregation: metric.aggregation || 'sum',
      rollup_type: metric.rollup_type || null,
      is_benefit: Boolean(metric.is_benefit),
      benefit_class: metric.benefit_class || null,
      cost_behavior: metric.cost_behavior || null,
      formula: metric.formula || null,
      formula_inputs: metric.formula_inputs || [],
      precision: Number(metric.precision ?? 4),
      display_order: Number(metric.display_order || 0),
      applies_to: metric.applies_to || 'opt_in',
      validation: metric.validation || {},
      is_system: Boolean(metric.is_system),
      is_active: metric.is_active !== false,
    };
    const request = metric.id
      ? this.api.patch(`/admin/financial-engine/metrics/${metric.id}`, payload)
      : this.api.post('/admin/financial-engine/metrics', payload);
    request.subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  updateMetricBenefitClass(metric: any, value: string) {
    metric.benefit_class = value || null;
    metric.is_benefit = Boolean(value);
    metric.rollup_type = value ? 'benefit' : null;
  }

  addScenarioDefinition() {
    const index = this.scenarioDefinitions().length + 1;
    this.scenarioDefinitions.update(scenarios => [
      ...scenarios,
      {
        key: `custom_scenario_${Date.now()}`,
        label: `Scenario ${index}`,
        kind: 'plan',
        is_primary: false,
        is_system: false,
        is_active: true,
        display_order: 1000 + index,
      },
    ]);
  }

  saveScenarioDefinition(scenario: any) {
    const payload = {
      key: scenario.key || this.uniqueEngineKey(scenario.label, 'scenario', this.scenarioDefinitions()),
      label: scenario.label,
      kind: scenario.kind || 'plan',
      is_primary: Boolean(scenario.is_primary),
      is_system: Boolean(scenario.is_system),
      is_active: scenario.is_active !== false,
      display_order: Number(scenario.display_order || 0),
    };
    const request = scenario.id
      ? this.api.patch(`/admin/financial-engine/scenarios/${scenario.id}`, payload)
      : this.api.post('/admin/financial-engine/scenarios', payload);
    request.subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  addCostCategoryDefinition() {
    const index = this.costCategories().length + 1;
    this.costCategories.update(categories => [
      ...categories,
      {
        key: `custom_cost_category_${Date.now()}`,
        label: `Cost Category ${index}`,
        group_key: 'costs',
        rollup_type: 'one_off_cost',
        display_order: 1000 + index,
        attributes: {},
        is_system: false,
        is_active: true,
      },
    ]);
  }

  saveCostCategoryDefinition(category: any) {
    const payload = {
      id: category.id || null,
      key: category.key || this.uniqueEngineKey(category.label, 'cost_category', this.costCategories()),
      label: category.label,
      group_key: category.group_key || null,
      rollup_type: category.rollup_type || null,
      display_order: Number(category.display_order || 0),
      attributes: category.attributes || {},
      is_system: Boolean(category.is_system),
      is_active: category.is_active !== false,
    };
    const request = category.id
      ? this.api.patch(`/admin/financial-engine/cost-categories/${category.id}`, payload)
      : this.api.post('/admin/financial-engine/cost-categories', payload);
    request.subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  addBridgeRowDefinition() {
    const index = this.bridgeRows().length + 1;
    this.bridgeRows.update(rows => [
      ...rows,
      {
        key: `custom_bridge_row_${Date.now()}`,
        label: `Bridge Row ${index}`,
        row_kind: 'metric_set',
        metric_definition_ids: [],
        cost_category_ids: [],
        cost_category_keys: [],
        sign: 1,
        display_order: 1000 + index,
        is_active: true,
      },
    ]);
  }

  saveBridgeRowDefinition(row: any) {
    const payload = {
      id: row.id || null,
      key: row.key || this.uniqueEngineKey(row.label, 'bridge_row', this.bridgeRows()),
      label: row.label,
      row_kind: row.row_kind || 'metric_set',
      metric_definition_ids: row.row_kind === 'net' ? [] : (row.metric_definition_ids || []),
      cost_category_ids: row.row_kind === 'net' ? [] : (row.cost_category_ids || []),
      cost_category_keys: row.row_kind === 'net' ? [] : (row.cost_category_keys || []),
      sign: Number(row.sign || 1) < 0 ? -1 : 1,
      display_order: Number(row.display_order || 0),
      is_active: row.is_active !== false,
    };
    const request = row.id
      ? this.api.patch(`/admin/financial-engine/bridge-rows/${row.id}`, payload)
      : this.api.post('/admin/financial-engine/bridge-rows', payload);
    request.subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  addAttributeDefinition() {
    const index = this.attributeDefinitions().length + 1;
    this.attributeDefinitions.update(attributes => [
      ...attributes,
      {
        key: `custom_attribute_${Date.now()}`,
        label: `Line Attribute ${index}`,
        entity_type: 'benefit_line',
        value_type: 'text',
        options: [],
        is_required: false,
        display_order: 1000 + index,
        is_active: true,
      },
    ]);
  }

  saveAttributeDefinition(attribute: any) {
    const payload = {
      id: attribute.id || null,
      key: attribute.key || this.uniqueEngineKey(attribute.label, 'attribute', this.attributeDefinitions()),
      label: attribute.label,
      entity_type: attribute.entity_type || 'benefit_line',
      value_type: attribute.value_type || 'text',
      options: this.normalizeConfigList(attribute.options),
      is_required: Boolean(attribute.is_required),
      display_order: Number(attribute.display_order || 0),
      is_active: attribute.is_active !== false,
    };
    const request = attribute.id
      ? this.api.patch(`/admin/financial-engine/attribute-definitions/${attribute.id}`, payload)
      : this.api.post('/admin/financial-engine/attribute-definitions', payload);
    request.subscribe(() => {
      this.loadFinancialEngineConfiguration();
      this.loadAuditLogs();
    });
  }

  attributeOptionsText(attribute: any): string {
    return this.normalizeConfigList(attribute.options).join(', ');
  }

  setAttributeOptionsText(attribute: any, value: string) {
    attribute.options = String(value || '')
      .split(',')
      .map(option => option.trim())
      .filter(Boolean);
  }

  activeCostCategoryItems(): any[] {
    return this.costCategories()
      .filter(item => item.id && item.is_active !== false)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0) || String(a.label || '').localeCompare(String(b.label || '')));
  }

  bridgeRowMetricSelected(row: any, metricId: string): boolean {
    return (row.metric_definition_ids || []).includes(metricId);
  }

  toggleBridgeRowMetric(row: any, metricId: string) {
    const current = new Set<string>(row.metric_definition_ids || []);
    current.has(metricId) ? current.delete(metricId) : current.add(metricId);
    row.metric_definition_ids = Array.from(current);
  }

  bridgeRowCostCategorySelected(row: any, categoryId: string): boolean {
    return (row.cost_category_ids || []).includes(categoryId);
  }

  toggleBridgeRowCostCategory(row: any, categoryId: string) {
    const current = new Set<string>(row.cost_category_ids || []);
    current.has(categoryId) ? current.delete(categoryId) : current.add(categoryId);
    row.cost_category_ids = Array.from(current);
  }

  addMetricGroup() {
    const index = this.financialGroupsByKind('metric').length + 1;
    this.financialGroups.update(groups => [
      ...groups,
      {
        key: `metric_group_${Date.now()}`,
        label: `Metric Category ${index}`,
        kind: 'metric',
        rollup_type: null,
        display_order: 100 + index,
        is_system: false,
        is_active: true,
      },
    ]);
  }

  addMetric(groupKey: string) {
    const label = this.newMetricNameForGroup(groupKey).trim();
    if (!label) return;
    const key = this.uniqueFinancialKey(label, 'metric');
    this.financialItems.update(items => [
      ...items,
      {
        key,
        label,
        item_type: 'metric',
        group_key: groupKey,
        system_metric_key: null,
        rollup_type: 'benefit',
        display_order: items.length + 10,
        is_system: false,
        is_active: true,
      },
    ]);
    this.setNewMetricName(groupKey, '');
    this.saveFinancialConfiguration();
  }

  newMetricNameForGroup(groupKey: string): string {
    return this.newMetricNames()[groupKey] || '';
  }

  setNewMetricName(groupKey: string, value: string) {
    this.newMetricNames.update(names => ({ ...names, [groupKey]: value }));
  }

  deleteFinancialItem(item: any) {
    if (item.is_system) item.is_active = false;
    else this.financialItems.update(items => items.filter(candidate => candidate !== item));
    this.saveFinancialConfiguration();
  }

  deleteFinancialGroup(group: any) {
    if (group.is_system) return;
    const childItems = this.financialItems().filter(item => item.group_key === group.key);
    const activeCostItems = childItems.filter(item => item.item_type === 'cost_category' && item.is_active !== false);
    const replacement = this.financialItems().find(item =>
      item.item_type === 'cost_category'
      && item.group_key !== group.key
      && item.is_active !== false
    );

    const removeGroup = () => {
      this.financialGroups.update(groups => groups.filter(candidate => candidate !== group));
      this.financialItems.update(items => items.filter(item => item.group_key !== group.key));
      this.saveFinancialConfiguration();
    };

    if (!activeCostItems.length || !replacement) {
      removeGroup();
      return;
    }

    const resetNext = (index: number) => {
      const item = activeCostItems[index];
      if (!item) {
        removeGroup();
        return;
      }
      this.api.post('/admin/financial-configuration/cost-categories/delete', {
        category_key: item.key,
        replacement_key: replacement.key,
      }).subscribe({
        next: () => resetNext(index + 1),
        error: () => resetNext(index + 1),
      });
    };
    resetNext(0);
  }

  addCostCategoryGroup() {
    const index = this.financialGroupsByKind('cost_category').length + 1;
    this.financialGroups.update(groups => [
      ...groups,
      {
        key: `cost_group_${Date.now()}`,
        label: `Cost Group ${index}`,
        kind: 'cost_category',
        rollup_type: null,
        display_order: 100 + index,
        is_system: false,
        is_active: true,
      },
    ]);
  }

  addCostCategory(groupKey: string) {
    const label = this.newCostCategoryNameForGroup(groupKey).trim();
    if (!label) return;
    const key = this.uniqueFinancialKey(label, 'category');
    const rollup = groupKey === 'operating' ? 'recurring_cost' : 'one_off_cost';
    this.financialItems.update(items => [
      ...items,
      {
        key,
        label,
        item_type: 'cost_category',
        group_key: groupKey,
        system_metric_key: null,
        rollup_type: rollup,
        display_order: items.length + 10,
        is_system: false,
        is_active: true,
      },
    ]);
    this.setNewCostCategoryName(groupKey, '');
    this.saveFinancialConfiguration();
  }

  newCostCategoryNameForGroup(groupKey: string): string {
    return this.newCostCategoryNames()[groupKey] || '';
  }

  setNewCostCategoryName(groupKey: string, value: string) {
    this.newCostCategoryNames.update(names => ({ ...names, [groupKey]: value }));
  }

  deleteCostCategory(item: any) {
    const replacement = this.financialItems().find(candidate =>
      candidate.item_type === 'cost_category'
      && candidate.key !== item.key
      && candidate.is_active !== false
    );
    if (!replacement) return;
    this.api.post('/admin/financial-configuration/cost-categories/delete', {
      category_key: item.key,
      replacement_key: replacement.key,
    }).subscribe(() => {
      item.is_active = false;
      this.saveFinancialConfiguration();
    });
  }

  private uniqueFinancialKey(label: string, fallbackPrefix: string): string {
    const base = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || `${fallbackPrefix}_${Date.now()}`;
    const existing = new Set(this.financialItems().map(item => item.key));
    if (!existing.has(base)) return base;
    let index = 2;
    while (existing.has(`${base}_${index}`)) index += 1;
    return `${base}_${index}`;
  }

  private uniqueEngineKey(label: string, fallbackPrefix: string, rows: any[]): string {
    const base = String(label || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || `${fallbackPrefix}_${Date.now()}`;
    const existing = new Set(rows.map(row => row.key));
    if (!existing.has(base)) return base;
    let index = 2;
    while (existing.has(`${base}_${index}`)) index += 1;
    return `${base}_${index}`;
  }

  private uniqueCriterionKey(gate: number, label: string): string {
    const base = String(label || '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '') || `gate_${gate}_criterion_${Date.now()}`;
    const prefixed = `g${gate}_${base}`;
    const existing = new Set(this.gateCriteria().map(row => row.criterion_id));
    if (!existing.has(prefixed)) return prefixed;
    let index = 2;
    while (existing.has(`${prefixed}_${index}`)) index += 1;
    return `${prefixed}_${index}`;
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
    const label = this.newCriterionForGate(gate).trim();
    if (!label) return;
    const criterion_id = this.uniqueCriterionKey(gate, label);
    this.api.post('/admin/governance/gate-criteria', {
      gate_number: gate,
      label,
      criterion_id,
      is_active: true,
      sort_order: this.gateCriteria().filter(c => c.gate_number === gate).length + 1
    }).subscribe(() => {
      this.loadGateCriteria();
      this.setNewCriterionForGate(gate, '');
    });
  }

  toggleCriterion(c: any) {
    this.api.patch(`/admin/governance/gate-criteria/${c.id}`, { is_active: !c.is_active }).subscribe(() => this.loadGateCriteria());
  }

  saveCriterion(c: any) {
    this.api.patch(`/admin/governance/gate-criteria/${c.id}`, {
      gate_number: Number(c.gate_number),
      criterion_id: c.criterion_id,
      label: c.label,
      guidance: c.guidance || null,
      sort_order: Number(c.sort_order || 0),
      is_active: c.is_active !== false,
    }).subscribe(() => this.loadGateCriteria());
  }

  deleteCriterion(id: string) {
    this.api.delete(`/admin/governance/gate-criteria/${id}`).subscribe(() => this.loadGateCriteria());
  }

  criteriaForGate(gateNumber: number): any[] {
    return this.gateCriteria()
      .filter(c => Number(c.gate_number) === Number(gateNumber))
      .sort((a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0));
  }

  addStageGateDefinition() {
    const nextGate = Math.min(Math.max(...this.stageGateDefinitions().map(g => Number(g.gate_number || 0)), 0) + 1, 10);
    this.stageGateDefinitions.update(gates => [
      ...gates,
      {
        gate_number: nextGate,
        key: `custom_gate_${Date.now()}`,
        label: `Gate ${nextGate}`,
        from_stage: 'current',
        to_stage: 'next',
        description: null,
        approval_required: true,
        approver_roles: ['transformation_office'],
        require_all_criteria: true,
        sort_order: nextGate * 10,
        is_system: false,
        is_active: true,
      },
    ]);
  }

  saveStageGateDefinition(gate: any) {
    const payload = {
      gate_number: Number(gate.gate_number || 1),
      key: gate.key || this.uniqueEngineKey(gate.label, 'gate', this.stageGateDefinitions()),
      label: gate.label,
      from_stage: gate.from_stage,
      to_stage: gate.to_stage,
      description: gate.description || null,
      approval_required: gate.approval_required !== false,
      approver_roles: gate.approver_roles?.length ? gate.approver_roles : ['transformation_office'],
      require_all_criteria: gate.require_all_criteria !== false,
      sort_order: Number(gate.sort_order || 0),
      is_system: Boolean(gate.is_system),
      is_active: gate.is_active !== false,
    };
    const request = gate.id
      ? this.api.patch(`/admin/governance/stage-gates/${gate.id}`, payload)
      : this.api.post('/admin/governance/stage-gates', payload);
    request.subscribe(() => {
      this.loadStageGateDefinitions();
      this.loadAuditLogs();
    });
  }

  newCriterionForGate(gate: number): string {
    return this.newCriteriaByGate()[gate] || '';
  }

  setNewCriterionForGate(gate: number, value: string) {
    this.newCriteriaByGate.update(current => ({ ...current, [gate]: value }));
  }

  rolesText(roles: string[] | null | undefined): string {
    return (roles || []).join(', ');
  }

  splitRoles(value: string): string[] {
    return String(value || '')
      .split(',')
      .map(role => role.trim())
      .filter(Boolean);
  }

  numberValue(value: number | string): number {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 1;
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

  selectInitiativeForDelete(initiativeId: string) {
    this.selectedInitiativeDeleteId.set(initiativeId);
    this.initiativeDeleteConfirmation.set('');
    this.initiativeDeleteError.set(null);
    this.initiativeDeleteResult.set(null);
  }

  selectedInitiativeForDelete(): any | null {
    return this.initiativeDeleteCandidates().find(item => item.id === this.selectedInitiativeDeleteId()) || null;
  }

  canDeleteSelectedInitiative(): boolean {
    const selected = this.selectedInitiativeForDelete();
    return Boolean(
      selected
      && this.initiativeDeleteConfirmation().trim() === selected.initiative_code,
    );
  }

  deleteSelectedInitiative() {
    const selected = this.selectedInitiativeForDelete();
    if (!selected || !this.canDeleteSelectedInitiative() || this.initiativeDeleting()) return;

    this.initiativeDeleting.set(true);
    this.initiativeDeleteError.set(null);
    this.api.delete(`/initiatives/${selected.id}`).subscribe({
      next: () => {
        this.initiativeDeleteResult.set(selected);
        this.initiativeDeleting.set(false);
        this.selectedInitiativeDeleteId.set('');
        this.initiativeDeleteConfirmation.set('');
        this.loadInitiativeDeleteCandidates();
        this.loadMeetingCleanupCandidates();
        this.loadCleanupPreview();
        this.loadAuditLogs();
      },
      error: err => {
        this.initiativeDeleteError.set(err.error?.detail || 'Could not delete initiative');
        this.initiativeDeleting.set(false);
      },
    });
  }

  toggleMeetingCleanupSelection(meetingId: string, checked: boolean): void {
    const ids = new Set(this.selectedMeetingCleanupIds());
    if (checked) ids.add(meetingId);
    else ids.delete(meetingId);
    this.selectedMeetingCleanupIds.set(Array.from(ids));
    this.meetingCleanupError.set(null);
    this.meetingCleanupResult.set(null);
  }

  canDeleteSelectedMeetings(): boolean {
    return this.selectedMeetingCleanupIds().length > 0
      && this.meetingCleanupConfirmation().trim() === 'DELETE MEETINGS';
  }

  deleteSelectedMeetings() {
    if (!this.canDeleteSelectedMeetings() || this.meetingCleanupDeleting()) return;

    this.meetingCleanupDeleting.set(true);
    this.meetingCleanupError.set(null);
    this.api.post<any>('/admin/meeting-cleanup/delete', {
      meeting_ids: this.selectedMeetingCleanupIds(),
      confirm_phrase: this.meetingCleanupConfirmation().trim(),
    }).subscribe({
      next: res => {
        this.meetingCleanupResult.set(res);
        this.meetingCleanupDeleting.set(false);
        this.selectedMeetingCleanupIds.set([]);
        this.meetingCleanupConfirmation.set('');
        this.loadMeetingCleanupCandidates();
        this.loadCleanupPreview();
        this.loadAuditLogs();
      },
      error: err => {
        this.meetingCleanupError.set(err.error?.detail || 'Could not delete selected meetings');
        this.meetingCleanupDeleting.set(false);
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

  labelize(value: string): string {
    return value.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  }

  recurrenceLabel(value: string): string {
    const labels: Record<string, string> = {
      ad_hoc: 'One-off',
      weekly: 'Weekly',
      biweekly: 'Biweekly',
      monthly: 'Monthly',
    };
    return labels[value] || this.labelize(value || '');
  }

  formatCents(cents: number | undefined, currency: string | undefined): string {
    if (!cents) return 'Custom';
    return `${String(currency || 'usd').toUpperCase()} ${(Number(cents) / 100).toFixed(2)}`;
  }
}
