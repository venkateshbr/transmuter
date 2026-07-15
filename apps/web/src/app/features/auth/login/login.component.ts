import { Component, ElementRef, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen flex items-center justify-center p-6 bg-[var(--t-bg)]">
      <div class="w-full max-w-md animate-fade-in">
        <!-- Logo -->
        <div class="flex flex-col items-center mb-10">
          <div class="text-4xl font-bold tracking-tight mb-2">
            <span class="text-[var(--t-text-primary)]">Transmuter</span>
            <span class="text-[var(--t-accent)]" style="font-size:1.4em;line-height:1">.</span>
          </div>
          <p class="text-[var(--t-text-secondary)]">Transformation Office Command Center</p>
        </div>

        <!-- Login Card -->
        <div class="card p-8 glass-panel shadow-2xl border border-[var(--t-border)]">
          <h2 class="text-2xl font-bold text-[var(--t-text-primary)] mb-6">Welcome back</h2>
          
          <form (ngSubmit)="onSubmit()" class="space-y-5" aria-label="Sign in to Transmuter">
            <div>
              <label for="login-email" class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Email Address</label>
              <input 
                #emailInput
                id="login-email"
                type="email" 
                [(ngModel)]="email" 
                name="email"
                required
                autocomplete="username"
                [attr.aria-invalid]="error() ? 'true' : null"
                [attr.aria-describedby]="error() ? 'login-error' : null"
                placeholder="admin@ishirock.dev"
                class="input-field w-full"
              />
            </div>

            <div>
              <label for="login-password" class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Password</label>
              <input 
                id="login-password"
                type="password" 
                [(ngModel)]="password" 
                name="password"
                required
                autocomplete="current-password"
                [attr.aria-invalid]="error() ? 'true' : null"
                [attr.aria-describedby]="error() ? 'login-error' : null"
                placeholder="••••••••"
                class="input-field w-full"
              />
            </div>

            @if (error()) {
              <div id="login-error" role="alert" aria-live="assertive" class="p-3 border border-red-500/20 bg-red-500/10 text-sm text-red-500">
                {{ error() }}
              </div>
            }

            @if (sessionExpired()) {
              <div class="p-3 rounded-lg border border-amber-500/20 bg-amber-500/10 text-amber-600 text-sm">
                Your session expired. Please sign in again.
              </div>
            }

            <button 
              type="submit" 
              [disabled]="loading()"
              aria-label="Sign in to Transmuter"
              class="btn-primary w-full py-3 mt-4 flex items-center justify-center gap-2">
              @if (loading()) {
                <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Signing in...
              } @else {
                Sign in →
              }
            </button>
          </form>

          <!-- Footer -->
          <div class="mt-8 pt-6 border-t border-[var(--t-border)]">
            <p class="text-center text-xs text-[var(--t-text-tertiary)]">
              Restricted access. Authorized personnel only.
            </p>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  @ViewChild('emailInput') private emailInput?: ElementRef<HTMLInputElement>;

  email = '';
  password = '';
  loading = signal(false);
  error = signal<string | null>(null);
  sessionExpired = signal(false);

  constructor() {
    this.sessionExpired.set(this.route.snapshot.queryParamMap.get('session') === 'expired');
  }

  onSubmit() {
    this.loading.set(true);
    this.error.set(null);
    this.sessionExpired.set(false);

    this.auth.login(this.email, this.password).subscribe({
      next: (resp) => {
        if (resp.must_change_password) {
          this.router.navigate(['/auth/change-password']);
          return;
        }
        this.router.navigate([this.auth.getRole() === 'platform_admin' ? '/platform' : '/dashboard']);
      },
      error: (err) => {
        this.error.set(err.error?.detail || 'Authentication failed');
        this.loading.set(false);
        queueMicrotask(() => this.emailInput?.nativeElement.focus());
      }
    });
  }
}
