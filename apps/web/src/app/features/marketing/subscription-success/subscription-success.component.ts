import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-subscription-success',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="flex min-h-screen items-center justify-center bg-[var(--t-bg)] px-6 text-[var(--t-text-primary)]">
      <section class="max-w-xl border border-[var(--t-border)] bg-[var(--t-surface)] p-8">
        <p class="text-xs font-black uppercase tracking-[0.3em] text-[var(--t-accent)]">Checkout complete</p>
        <h1 class="mt-4 text-4xl font-black">Subscription received.</h1>
        <p class="mt-5 text-sm leading-7 text-[var(--t-text-secondary)]">
          Stripe returned successfully. Tenant provisioning will be completed by the billing webhook
          once the provisioning tables are added.
        </p>
        <a routerLink="/auth/login" class="btn-primary mt-8 inline-flex px-5 py-3 text-xs">Go to login</a>
      </section>
    </main>
  `,
})
export class SubscriptionSuccessComponent {}
