import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen flex items-center justify-center p-6 bg-[var(--t-bg)]">
      <div class="w-full max-w-2xl">
        <div class="mb-8">
          <div class="text-4xl font-bold tracking-tight">
            <span class="text-[var(--t-text-primary)]">Transmuter</span>
            <span class="text-[var(--t-accent)]" style="font-size:1.4em;line-height:1">.</span>
          </div>
          <p class="mt-2 text-[var(--t-text-secondary)]">Create the organization workspace.</p>
        </div>

        <div class="card border border-[var(--t-border)] p-8 shadow-2xl">
          <form (ngSubmit)="submit()" class="grid gap-5 md:grid-cols-2">
            <label class="block md:col-span-2">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Organization name</span>
              <input [(ngModel)]="form.organization_name" name="organization_name" required class="input-field w-full" aria-label="Organization name">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Workspace slug</span>
              <input [(ngModel)]="form.organization_slug" name="organization_slug" required class="input-field w-full" aria-label="Organization slug">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Admin name</span>
              <input [(ngModel)]="form.admin_display_name" name="admin_display_name" required class="input-field w-full" aria-label="Admin display name">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Admin email</span>
              <input type="email" [(ngModel)]="form.admin_email" name="admin_email" required class="input-field w-full" aria-label="Admin email">
            </label>
            <label class="block">
              <span class="block text-xs font-bold uppercase tracking-widest text-[var(--t-text-secondary)] mb-2">Admin password</span>
              <input type="password" [(ngModel)]="form.admin_password" name="admin_password" required class="input-field w-full" aria-label="Admin password">
            </label>

            @if (error()) {
              <div class="md:col-span-2 border border-red-500/20 bg-red-500/10 p-3 text-sm text-red-500">
                {{ error() }}
              </div>
            }

            <div class="md:col-span-2 flex justify-end">
              <button type="submit" [disabled]="loading()" class="btn-primary px-6 py-3">
                {{ loading() ? 'Creating...' : 'Create workspace' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  `,
})
export class RegisterComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  loading = signal(false);
  error = signal<string | null>(null);
  form = {
    organization_name: '',
    organization_slug: '',
    admin_display_name: '',
    admin_email: '',
    admin_password: '',
  };

  submit(): void {
    this.loading.set(true);
    this.error.set(null);
    this.auth.registerBlankTenant(this.form).subscribe({
      next: (resp) => {
        this.router.navigate([resp.must_change_password ? '/auth/change-password' : '/dashboard']);
      },
      error: (err) => {
        this.error.set(err.error?.detail || 'Workspace could not be created');
        this.loading.set(false);
      },
    });
  }
}
