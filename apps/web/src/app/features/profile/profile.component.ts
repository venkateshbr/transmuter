import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService, type UserProfile } from '../../core/services/auth.service';
import { operatingModelRoleLabel } from '../../core/rbac/operating-model-permissions';

@Component({
  selector: 'app-profile',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="min-h-screen p-8 space-y-8" style="background:var(--t-bg)">
      <header class="flex flex-wrap items-end justify-between gap-5 border-b border-[var(--t-border)] pb-6">
        <div>
          <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Account Control</p>
          <h1 class="mt-2 text-3xl font-black text-[var(--t-text-primary)]">Profile<span class="text-[var(--t-blue-light)]">.</span></h1>
          <p class="mt-2 max-w-3xl text-sm leading-6 text-[var(--t-text-secondary)]">
            Manage your workspace identity and password for the current authenticated session.
          </p>
        </div>
        <div class="border border-[var(--t-border)] bg-[var(--t-surface)] px-4 py-3 text-right">
          <p class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Session Role</p>
          <p class="mt-1 text-sm font-black uppercase text-[var(--t-accent)]">{{ roleLabel(profile()?.role) }}</p>
        </div>
      </header>

      @if (loading()) {
        <section class="card p-8 text-sm font-bold text-[var(--t-text-secondary)]" role="status" aria-live="polite">
          Loading profile...
        </section>
      } @else {
        <section class="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <aside class="card p-0 overflow-hidden">
            <div class="executive-surface relative overflow-hidden p-6">
              <div class="absolute right-6 top-6 h-14 w-14 border-r-4 border-t-4 border-[var(--t-blue-light)]/70"></div>
              <p class="text-[10px] font-black uppercase tracking-widest text-white/65">Signed-in user</p>
              <div class="mt-6 flex items-center gap-4">
                <div class="flex h-16 w-16 items-center justify-center bg-white text-2xl font-black text-[var(--t-primary)] shadow-[inset_0_-4px_0_var(--t-blue-light)]">
                  {{ initials() }}
                </div>
                <div class="min-w-0">
                  <h2 class="truncate text-2xl font-black text-white">{{ displayName() }}</h2>
                  <p class="mt-1 truncate text-xs font-bold text-white/70">{{ profile()?.email }}</p>
                </div>
              </div>
            </div>

            <dl class="divide-y divide-[var(--t-border)]">
              <div class="grid grid-cols-[9rem_1fr] gap-4 px-6 py-4">
                <dt class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">User ID</dt>
                <dd class="break-all text-xs font-bold text-[var(--t-text-secondary)]">{{ profile()?.id }}</dd>
              </div>
              <div class="grid grid-cols-[9rem_1fr] gap-4 px-6 py-4">
                <dt class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Tenant ID</dt>
                <dd class="break-all text-xs font-bold text-[var(--t-text-secondary)]">{{ profile()?.tenant_id }}</dd>
              </div>
              <div class="grid grid-cols-[9rem_1fr] gap-4 px-6 py-4">
                <dt class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Status</dt>
                <dd><span class="badge-green">{{ profile()?.status || 'active' }}</span></dd>
              </div>
              <div class="grid grid-cols-[9rem_1fr] gap-4 px-6 py-4">
                <dt class="text-[9px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Onboarding</dt>
                <dd class="text-xs font-bold text-[var(--t-text-secondary)]">{{ profile()?.onboarding_completed ? 'Completed' : 'In progress' }}</dd>
              </div>
            </dl>
          </aside>

          <div class="space-y-6">
            <section class="card p-6">
              <div class="flex items-start justify-between gap-4 border-b border-[var(--t-border)] pb-5">
                <div>
                  <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Profile Details</p>
                  <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Workspace Identity</h2>
                </div>
                @if (!canEditProfile()) {
                  <span class="badge-gray">Directory Managed</span>
                }
              </div>

              <form class="mt-5 grid gap-4 md:grid-cols-2" (ngSubmit)="saveProfile()">
                <label class="block">
                  <span class="mb-2 block text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Display Name</span>
                  <input
                    class="input-field"
                    name="displayName"
                    [(ngModel)]="displayNameDraft"
                    [disabled]="!canEditProfile() || savingProfile()"
                    autocomplete="name"
                    aria-label="Display name">
                </label>
                <label class="block">
                  <span class="mb-2 block text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Title</span>
                  <input
                    class="input-field"
                    name="title"
                    [(ngModel)]="titleDraft"
                    [disabled]="!canEditProfile() || savingProfile()"
                    autocomplete="organization-title"
                    aria-label="Job title">
                </label>

                <div class="md:col-span-2 flex flex-wrap items-center justify-between gap-3 border-t border-[var(--t-border)] pt-5">
                  <p class="text-xs font-bold text-[var(--t-text-secondary)]">
                    @if (profileSaved()) {
                      Profile saved.
                    } @else {
                      {{ canEditProfile() ? 'Changes update your Transmuter workspace profile.' : 'Platform operator profile data is managed by configuration.' }}
                    }
                  </p>
                  <button
                    type="submit"
                    class="btn-primary"
                    [disabled]="!canEditProfile() || savingProfile()"
                    aria-label="Save profile changes">
                    {{ savingProfile() ? 'Saving...' : 'Save Profile' }}
                  </button>
                </div>
              </form>
            </section>

            <section class="card p-6">
              <div class="border-b border-[var(--t-border)] pb-5">
                <p class="text-[10px] font-black uppercase tracking-widest text-[var(--t-accent)]">Security</p>
                <h2 class="mt-1 text-lg font-black text-[var(--t-text-primary)]">Change Password</h2>
              </div>

              <form class="mt-5 grid gap-4" (ngSubmit)="changePassword()">
                <label class="block">
                  <span class="mb-2 block text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Current Password</span>
                  <input
                    class="input-field"
                    type="password"
                    name="currentPassword"
                    [(ngModel)]="currentPassword"
                    [disabled]="changingPassword()"
                    autocomplete="current-password"
                    required
                    aria-label="Current password">
                </label>

                <div class="grid gap-4 md:grid-cols-2">
                  <label class="block">
                    <span class="mb-2 block text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">New Password</span>
                    <input
                      class="input-field"
                      type="password"
                      name="newPassword"
                      [(ngModel)]="newPassword"
                      [disabled]="changingPassword()"
                      autocomplete="new-password"
                      required
                      aria-label="New password">
                  </label>
                  <label class="block">
                    <span class="mb-2 block text-[10px] font-black uppercase tracking-widest text-[var(--t-text-tertiary)]">Confirm Password</span>
                    <input
                      class="input-field"
                      type="password"
                      name="confirmPassword"
                      [(ngModel)]="confirmPassword"
                      [disabled]="changingPassword()"
                      autocomplete="new-password"
                      required
                      aria-label="Confirm new password">
                  </label>
                </div>

                @if (passwordError()) {
                  <div class="border border-red-500/30 bg-red-500/10 p-3 text-sm font-bold text-red-500" role="alert">
                    {{ passwordError() }}
                  </div>
                }
                @if (passwordSaved()) {
                  <div class="border border-[var(--t-green)]/30 bg-[var(--t-green)]/10 p-3 text-sm font-bold text-[var(--t-green)]" role="status" aria-live="polite">
                    Password changed.
                  </div>
                }

                <div class="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--t-border)] pt-5">
                  <p class="text-xs font-bold text-[var(--t-text-secondary)]">
                    Minimum 12 characters with uppercase, lowercase, and a number.
                  </p>
                  <button
                    type="submit"
                    class="btn-primary"
                    [disabled]="changingPassword()"
                    aria-label="Change password">
                    {{ changingPassword() ? 'Changing...' : 'Change Password' }}
                  </button>
                </div>
              </form>
            </section>
          </div>
        </section>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }
    .executive-surface {
      background: var(--t-executive, #071f3c) !important;
      color: var(--t-executive-text, #ffffff) !important;
    }
  `],
})
export class ProfileComponent implements OnInit {
  private readonly auth = inject(AuthService);

  readonly profile = signal<UserProfile | null>(null);
  readonly loading = signal(true);
  readonly savingProfile = signal(false);
  readonly changingPassword = signal(false);
  readonly profileSaved = signal(false);
  readonly passwordSaved = signal(false);
  readonly passwordError = signal<string | null>(null);

  displayNameDraft = '';
  titleDraft = '';
  currentPassword = '';
  newPassword = '';
  confirmPassword = '';

  ngOnInit(): void {
    this.auth.loadProfile().subscribe({
      next: profile => {
        this.profile.set(profile);
        this.displayNameDraft = profile.display_name || '';
        this.titleDraft = profile.title || '';
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  displayName(): string {
    return this.profile()?.display_name || this.profile()?.email || 'User';
  }

  initials(): string {
    const source = this.displayName();
    return source
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map(part => part.slice(0, 1).toUpperCase())
      .join('') || 'U';
  }

  canEditProfile(): boolean {
    return this.profile()?.role !== 'platform_admin';
  }

  roleLabel(role: string | null | undefined): string {
    return operatingModelRoleLabel(role);
  }

  saveProfile(): void {
    if (!this.canEditProfile() || this.savingProfile()) return;
    this.profileSaved.set(false);
    this.savingProfile.set(true);
    this.auth.updateProfile({
      display_name: this.displayNameDraft.trim() || null,
      title: this.titleDraft.trim() || null,
    }).subscribe({
      next: profile => {
        this.profile.set(profile);
        this.profileSaved.set(true);
        this.savingProfile.set(false);
      },
      error: () => this.savingProfile.set(false),
    });
  }

  changePassword(): void {
    this.passwordError.set(null);
    this.passwordSaved.set(false);
    const validation = this.validatePassword();
    if (validation) {
      this.passwordError.set(validation);
      return;
    }

    this.changingPassword.set(true);
    this.auth.changePassword(this.currentPassword, this.newPassword, this.confirmPassword).subscribe({
      next: () => {
        this.currentPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
        this.passwordSaved.set(true);
        this.changingPassword.set(false);
      },
      error: error => {
        this.passwordError.set(error.error?.detail || 'Password could not be changed');
        this.changingPassword.set(false);
      },
    });
  }

  private validatePassword(): string | null {
    if (!this.currentPassword) return 'Current password is required';
    if (this.newPassword.length < 12) return 'New password must be at least 12 characters';
    if (this.newPassword !== this.confirmPassword) return 'New password and confirmation do not match';
    if (this.currentPassword === this.newPassword) return 'New password must be different from the current password';
    if (!/[a-z]/.test(this.newPassword)) return 'New password must include a lowercase letter';
    if (!/[A-Z]/.test(this.newPassword)) return 'New password must include an uppercase letter';
    if (!/[0-9]/.test(this.newPassword)) return 'New password must include a number';
    return null;
  }
}
