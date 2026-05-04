import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

@Component({
  selector: 'app-get-started',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="min-h-screen bg-[var(--t-bg)] text-[var(--t-text-primary)]">
      <header class="border-b border-[var(--t-border)] bg-[var(--t-surface)]">
        <div class="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
          <a routerLink="/" class="text-lg font-black uppercase">Transmuter</a>
          <a routerLink="/auth/login" class="btn-ghost px-4 py-2 text-xs font-black uppercase">Login</a>
        </div>
      </header>

      <section class="mx-auto grid max-w-6xl gap-10 px-6 py-12 lg:grid-cols-[0.8fr_1.2fr]">
        <aside>
          <p class="mb-4 text-xs font-black uppercase tracking-[0.3em] text-[var(--t-accent)]">
            Subscription setup
          </p>
          <h1 class="text-4xl font-black leading-tight md:text-5xl">Create your enterprise workspace.</h1>
          <p class="mt-6 text-sm leading-7 text-[var(--t-text-secondary)]">
            Select the program scale for your transformation office. After checkout, Transmuter
            provisions the tenant and initial transformation-office admin from the verified Stripe event.
          </p>

          <div class="mt-8 grid gap-3">
            @for (plan of planCards; track plan.name) {
              <div class="border border-[var(--t-border)] bg-[var(--t-surface)] p-5">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">{{ plan.range }}</p>
                    <p class="mt-2 text-lg font-black">{{ plan.name }}</p>
                  </div>
                  <p class="text-right text-xl font-black">{{ plan.price }}</p>
                </div>
              </div>
            }
          </div>
        </aside>

        <form (ngSubmit)="startCheckout()" class="border border-[var(--t-border)] bg-[var(--t-surface)] p-6 md:p-8">
          <div class="grid gap-5 md:grid-cols-2">
            <label class="block md:col-span-2">
              <span class="field-label">Organization name</span>
              <input class="input-field w-full" name="organizationName" [(ngModel)]="form.organization_name" (ngModelChange)="syncSlug()" required>
            </label>
            <label class="block md:col-span-2">
              <span class="field-label">Organization short name</span>
              <input
                class="input-field w-full"
                name="organizationSlug"
                [(ngModel)]="form.organization_slug"
                required
                pattern="[a-z0-9-]+"
                aria-describedby="organization-short-name-help"
              >
              <p id="organization-short-name-help" class="mt-2 text-xs font-medium text-[var(--t-text-tertiary)]">
                Used as the unique workspace identifier. Lowercase letters, numbers, and hyphens only.
              </p>
            </label>
            <label class="block">
              <span class="field-label">Initial admin name</span>
              <input class="input-field w-full" name="adminName" [(ngModel)]="form.admin_display_name" required>
            </label>
            <label class="block">
              <span class="field-label">Initial admin email</span>
              <input type="email" class="input-field w-full" name="adminEmail" [(ngModel)]="form.admin_email" required>
            </label>
            <label class="block">
              <span class="field-label">Planned users</span>
              <input type="number" min="1" max="5000" class="input-field w-full" name="plannedUsers" [(ngModel)]="form.planned_user_count" required>
            </label>
            <label class="block">
              <span class="field-label">Billing interval</span>
              <select class="input-field w-full" name="billingInterval" [(ngModel)]="form.billing_interval" required>
                <option value="month">Monthly</option>
                <option value="year">Annual</option>
              </select>
            </label>
          </div>

          @if (error()) {
            <div class="mt-5 border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-500">
              {{ error() }}
            </div>
          }

          <button type="submit" class="btn-primary mt-8 w-full py-3 text-xs" [disabled]="loading()">
            {{ loading() ? 'Creating checkout...' : 'Continue to Stripe Checkout' }}
          </button>
        </form>
      </section>
    </main>
  `,
})
export class GetStartedComponent {
  private readonly api = inject(ApiService);

  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);

  protected form = {
    organization_name: '',
    organization_slug: '',
    admin_display_name: '',
    admin_email: '',
    planned_user_count: 10,
    billing_interval: 'month',
  };

  protected readonly planCards = [
    { name: 'Transmuter Team', range: '1-50 users', price: '$999/mo' },
    { name: 'Transmuter Business', range: '51-100 users', price: '$1,999/mo' },
    { name: 'Enterprise', range: '101+ users', price: 'Contact sales' },
  ];

  protected syncSlug(): void {
    this.form.organization_slug = this.form.organization_name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '')
      .slice(0, 80);
  }

  protected startCheckout(): void {
    this.loading.set(true);
    this.error.set(null);
    const origin = window.location.origin;
    this.api.post<{ checkout_url: string }>('/billing/checkout-session', {
      ...this.form,
      success_url: `${origin}/subscription/success?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/get-started?checkout=cancelled`,
    }).subscribe({
      next: (response) => {
        window.location.href = response.checkout_url;
      },
      error: (err) => {
        this.error.set(err.error?.detail || 'Could not start checkout');
        this.loading.set(false);
      },
    });
  }
}
