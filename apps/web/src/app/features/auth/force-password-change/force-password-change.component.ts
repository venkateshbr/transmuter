import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-force-password-change',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen flex items-center justify-center p-6 bg-[var(--t-bg)]">
      <div class="w-full max-w-md">
        <div class="mb-8 text-center">
          <div class="text-4xl font-bold tracking-tight">
            <span class="text-[var(--t-text-primary)]">Transmuter</span>
            <span class="text-[var(--t-accent)]" style="font-size:1.4em;line-height:1">.</span>
          </div>
        </div>

        <div class="card border border-[var(--t-border)] p-8 shadow-2xl">
          <h1 class="text-2xl font-bold text-[var(--t-text-primary)]">Change password</h1>
          <form (ngSubmit)="submit()" class="mt-6 space-y-5">
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Current password</span>
              <input type="password" [(ngModel)]="currentPassword" name="currentPassword" required class="input-field w-full" aria-label="Current password">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">New password</span>
              <input type="password" [(ngModel)]="newPassword" name="newPassword" required class="input-field w-full" aria-label="New password">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Confirm password</span>
              <input type="password" [(ngModel)]="confirmPassword" name="confirmPassword" required class="input-field w-full" aria-label="Confirm new password">
            </label>

            @if (error()) {
              <div class="border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-500">
                {{ error() }}
              </div>
            }

            <button type="submit" [disabled]="loading()" class="btn-primary w-full py-3">
              {{ loading() ? 'Saving...' : 'Save password' }}
            </button>
          </form>
        </div>
      </div>
    </div>
  `,
})
export class ForcePasswordChangeComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  currentPassword = '';
  newPassword = '';
  confirmPassword = '';
  loading = signal(false);
  error = signal<string | null>(null);

  submit(): void {
    this.loading.set(true);
    this.error.set(null);
    this.auth.changePassword(this.currentPassword, this.newPassword, this.confirmPassword).subscribe({
      next: () => {
        this.router.navigate([this.auth.getRole() === 'platform_admin' ? '/platform' : '/dashboard']);
      },
      error: (err) => {
        this.error.set(err.error?.detail || 'Password could not be changed');
        this.loading.set(false);
      },
    });
  }
}
