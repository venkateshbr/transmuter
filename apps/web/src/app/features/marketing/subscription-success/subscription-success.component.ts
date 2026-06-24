import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../../core/services/api.service';

interface CheckoutCompletionResponse {
  login_ready: boolean;
  provisioning_status?: string;
  error_detail?: string | null;
}

@Component({
  selector: 'app-subscription-success',
  standalone: true,
  imports: [RouterLink],
  template: `
    <main class="flex min-h-screen items-center justify-center bg-[var(--t-bg)] px-6 text-[var(--t-text-primary)]">
      <section class="max-w-xl border border-[var(--t-border)] bg-[var(--t-surface)] p-8">
        <p class="text-xs font-black uppercase tracking-[0.3em] text-[var(--t-accent)]">Account setup complete</p>
        <h1 class="mt-4 text-4xl font-black">Welcome to Transmuter.</h1>
        @if (setupState() === 'checking') {
          <p class="mt-5 text-sm leading-7 text-[var(--t-text-secondary)]">
            We are finalizing your workspace setup. This usually takes just a moment.
          </p>
        } @else if (setupState() === 'ready') {
          <p class="mt-5 text-sm leading-7 text-[var(--t-text-secondary)]">
            Your account has been set up successfully. We are excited to help your team turn
            transformation priorities into measurable business value.
          </p>
          <a routerLink="/auth/login" class="btn-primary mt-8 inline-flex px-5 py-3 text-xs">Go to login</a>
        } @else if (setupState() === 'failed') {
          <p class="mt-5 text-sm leading-7 text-[var(--t-text-secondary)]">
            Your checkout completed, but workspace setup could not finish automatically.
            {{ setupError() || 'Contact support before retrying checkout.' }}
          </p>
          <a routerLink="/get-started" class="btn-secondary mt-8 inline-flex px-5 py-3 text-xs">Return to checkout</a>
        } @else {
          <p class="mt-5 text-sm leading-7 text-[var(--t-text-secondary)]">
            Your checkout is complete, and we are finishing your workspace setup. Please try
            signing in shortly.
          </p>
          <a routerLink="/auth/login" class="btn-secondary mt-8 inline-flex px-5 py-3 text-xs">Go to login</a>
        }
      </section>
    </main>
  `,
})
export class SubscriptionSuccessComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly route = inject(ActivatedRoute);

  protected readonly setupState = signal<'checking' | 'ready' | 'pending' | 'failed'>('checking');
  protected readonly setupError = signal<string | null>(null);

  ngOnInit(): void {
    const sessionId = this.route.snapshot.queryParamMap.get('session_id');
    if (!sessionId) {
      this.setupState.set('ready');
      return;
    }

    this.api.post<CheckoutCompletionResponse>('/billing/checkout-completion', {
      session_id: sessionId,
    }).subscribe({
      next: response => {
        if (response.login_ready) {
          this.setupState.set('ready');
          return;
        }
        if (response.provisioning_status === 'failed') {
          this.setupError.set(response.error_detail || null);
          this.setupState.set('failed');
          return;
        }
        this.setupState.set('pending');
      },
      error: err => {
        this.setupError.set(err?.error?.detail || null);
        this.setupState.set('failed');
      },
    });
  }
}
