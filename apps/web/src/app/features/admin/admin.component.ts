import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="p-8 space-y-8 animate-fade-in" style="background:var(--t-bg)">
      
      <!-- Header -->
      <div class="flex justify-between items-end">
        <div>
          <h1 class="text-3xl font-bold tracking-tight text-[var(--t-text-primary)]">
            Administration<span class="text-[var(--t-accent)]">.</span>
          </h1>
          <p class="text-[var(--t-text-secondary)] mt-1">Platform governance, tenant settings, and user permissions.</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        <!-- Tenant Info -->
        <div class="card p-6 space-y-6">
          <h3 class="text-lg font-bold text-[var(--t-text-primary)]">Organization</h3>
          <div class="space-y-4">
            <div>
              <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Tenant ID</p>
              <p class="text-xs font-mono text-[var(--t-text-secondary)]">{{ auth.user()?.tenant_id }}</p>
            </div>
            <div>
              <p class="text-[10px] font-bold text-[var(--t-text-tertiary)] uppercase">Plan</p>
              <span class="badge badge-purple mt-1">Enterprise Plus</span>
            </div>
          </div>
        </div>

        <!-- Security -->
        <div class="lg:col-span-2 card p-6">
          <h3 class="text-lg font-bold text-[var(--t-text-primary)] mb-6">Security & Auth</h3>
          <div class="space-y-4">
            <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)]">
              <div>
                <p class="text-sm font-bold text-[var(--t-text-primary)]">Role-Based Access Control</p>
                <p class="text-xs text-[var(--t-text-tertiary)]">Enforce strict RLS policies on all portfolio data.</p>
              </div>
              <span class="text-green-500 font-bold text-xs uppercase tracking-widest">Active</span>
            </div>
            <div class="flex items-center justify-between p-4 rounded-xl border border-[var(--t-border)]">
              <div>
                <p class="text-sm font-bold text-[var(--t-text-primary)]">AI Data Masking</p>
                <p class="text-xs text-[var(--t-text-tertiary)]">Automatically mask PII before sending to external LLM providers.</p>
              </div>
              <span class="text-green-500 font-bold text-xs uppercase tracking-widest">Active</span>
            </div>
          </div>
        </div>

      </div>

    </div>
  `,
  styles: [`
    :host { display: block; }
  `]
})
export class AdminComponent {
  protected readonly auth = inject(AuthService);
}
