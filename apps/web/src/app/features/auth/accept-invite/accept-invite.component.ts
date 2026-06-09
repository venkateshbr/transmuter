import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-accept-invite',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    <main class="flex min-h-screen items-center justify-center bg-[var(--t-bg)] px-6 text-[var(--t-text-primary)]">
      <section class="w-full max-w-xl border border-[var(--t-border)] bg-[var(--t-surface)] p-8">
        <p class="text-xs font-black uppercase tracking-[0.3em] text-[var(--t-accent)]">Team invitation</p>
        <h1 class="mt-4 text-3xl font-black">Set your Transmuter password.</h1>
        <p class="mt-4 text-sm leading-7 text-[var(--t-text-secondary)]">
          Create your password to activate your account and join your transformation workspace.
        </p>

        @if (!token()) {
          <div class="mt-6 border border-[var(--t-red)] bg-[var(--t-surface-raised)] p-4 text-sm font-bold text-[var(--t-red)]">
            This invite link is missing its secure token. Ask your workspace admin to resend the invite.
          </div>
          <a routerLink="/auth/login" class="btn-secondary mt-6 inline-flex px-5 py-3 text-xs">Go to login</a>
        } @else {
          <form class="mt-8 grid gap-4" (ngSubmit)="submit()">
            <label class="block">
              <span class="field-label">Password</span>
              <input
                class="input-field w-full"
                type="password"
                name="password"
                [(ngModel)]="password"
                required
                minlength="12"
                autocomplete="new-password"
                aria-label="Password">
            </label>
            <label class="block">
              <span class="field-label">Confirm password</span>
              <input
                class="input-field w-full"
                type="password"
                name="confirmPassword"
                [(ngModel)]="confirmPassword"
                required
                minlength="12"
                autocomplete="new-password"
                aria-label="Confirm password">
            </label>

            @if (error()) {
              <div class="border border-[var(--t-red)] bg-[var(--t-surface-raised)] p-3 text-sm font-bold text-[var(--t-red)]">
                {{ error() }}
              </div>
            }

            <button type="submit" class="btn-primary mt-2 h-11 text-xs" [disabled]="loading()">
              {{ loading() ? 'Activating...' : 'Activate account' }}
            </button>
          </form>
        }
      </section>
    </main>
  `,
})
export class AcceptInviteComponent {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  protected readonly token = signal(this.route.snapshot.queryParamMap.get('token') || '');
  protected readonly loading = signal(false);
  protected readonly error = signal<string | null>(null);
  protected password = '';
  protected confirmPassword = '';

  protected submit(): void {
    if (!this.password || !this.confirmPassword) {
      this.error.set('Enter and confirm your password.');
      return;
    }
    if (this.password !== this.confirmPassword) {
      this.error.set('Password and confirmation must match.');
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.auth.acceptInvite(this.token(), this.password, this.confirmPassword).subscribe({
      next: () => this.router.navigate(['/dashboard']),
      error: err => {
        this.error.set(this.formatError(err));
        this.loading.set(false);
      },
    });
  }

  private formatError(err: unknown): string {
    const fallback = 'Invite could not be accepted. Ask your workspace admin to resend it.';
    if (!err || typeof err !== 'object') return fallback;
    const detail = (err as { error?: { detail?: unknown } }).error?.detail;
    return typeof detail === 'string' ? detail : fallback;
  }
}
