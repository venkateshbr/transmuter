# Rupa — Frontend Engineering Skills

## Skill: Angular 21 Component Pattern

All components must be standalone. No NgModules.
Use the existing app pattern first: standalone components, Angular signals, service-backed state, lazy routes, Tailwind utilities, and CSS variable design tokens. Do not introduce Angular Material or NgRx unless the existing feature area already uses it or Vastu approves the dependency.

### New Feature Component Template
```typescript
// feature.component.ts
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../core/services/api.service';

interface FeatureItem {
  id: string;
  name: string;
  amount: string; // Amounts are always strings from the API
}

@Component({
  selector: 'app-feature',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="space-y-5 p-8" style="background:var(--t-bg)">
      <header class="border-b border-[var(--t-border)] pb-4">
        <h1 class="text-2xl font-black text-[var(--t-text-primary)]">Feature</h1>
      </header>

      @if (loading()) {
        <p class="text-sm text-[var(--t-text-secondary)]">Loading...</p>
      } @else if (error()) {
        <div class="border border-red-500/30 bg-red-500/10 p-4 text-sm font-bold text-red-500">
          {{ error() }}
        </div>
      } @else if (!items().length) {
        <p class="text-sm text-[var(--t-text-secondary)]">No items yet.</p>
      } @else {
        <div class="divide-y divide-[var(--t-border)] border border-[var(--t-border)]">
          @for (item of items(); track item.id) {
            <div class="grid grid-cols-2 gap-4 p-4">
              <span class="font-bold text-[var(--t-text-primary)]">{{ item.name }}</span>
              <span class="text-right text-[var(--t-text-secondary)]">{{ item.amount }}</span>
            </div>
          }
        </div>
      }
    </section>
  `,
})
export class FeatureComponent implements OnInit {
  private readonly api = inject(ApiService);
  loading = signal(true);
  error = signal<string | null>(null);
  items = signal<FeatureItem[]>([]);
  itemCount = computed(() => this.items().length);

  ngOnInit() {
    this.api.get<{ items: FeatureItem[] }>('/features').subscribe({
      next: (data) => {
        this.items.set(data.items || []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load feature data.');
        this.loading.set(false);
      },
    });
  }
}
```

### Lazy Route Registration
```typescript
// app.routes.ts
{
  path: 'features',
  loadComponent: () => import('./features/feature.component').then(m => m.FeatureComponent),
  canActivate: [authGuard],
}
```

## Skill: Service/Signal State Pattern

Prefer simple injectable services with signals for shared feature state. Promote to a store library only after Vastu agrees the feature has real cross-component state complexity.

```typescript
import { Injectable, computed, inject, signal } from '@angular/core';
import { ApiService } from '../core/services/api.service';

interface FeatureItem {
  id: string;
  name: string;
}

@Injectable({ providedIn: 'root' })
export class FeatureStateService {
  private readonly api = inject(ApiService);

  readonly items = signal<FeatureItem[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly count = computed(() => this.items().length);

  load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.get<{ items: FeatureItem[] }>('/features').subscribe({
      next: response => {
        this.items.set(response.items || []);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Could not load feature data.');
        this.loading.set(false);
      },
    });
  }
}
```

## Skill: Theme Compliance Checklist

Before submitting any component:
- [ ] Uses `var(--t-bg)` for page background or an established layout wrapper
- [ ] Cards/panels use `card`, `var(--t-surface)`, `var(--t-surface-raised)`, and `var(--t-border)`
- [ ] Text uses `var(--t-text-primary)`, `var(--t-text-secondary)`, and `var(--t-text-tertiary)`
- [ ] Accents use `var(--t-accent)` and existing semantic tokens
- [ ] Works in both light and dark mode
- [ ] Hover/focus/active states present on all interactive elements
- [ ] No hardcoded hex colors
- [ ] Monetary values preserve API string precision; do not use `parseFloat` for financial calculations
- [ ] Responsive at `sm`, `md`, and `lg` breakpoints

## Skill: Component Testing Standard

Every new or materially changed component must include a focused spec for component logic unless Vishwa explicitly waives it for a docs-only or markup-only change.

- Test signal state transitions, computed values, and API success/error handling.
- Use Angular TestBed with mocked services for unit tests.
- Do not count mocked unit tests as product acceptance; Aksha still requires real API/browser coverage for touched workflows.
- Prefer small component specs over broad brittle snapshots.

## Skill: Frontend Error Handling Standard

- Never leave an empty `catch {}` block.
- Every error path must do at least one of: recover deterministically, show a user-facing message, or report telemetry.
- User-facing messages must be safe and actionable; do not expose database, stack, or provider internals.
- Keep the full technical detail in telemetry/console only when it does not include PII.

## Skill: API Client Resilience Pattern

When changing `ApiService` or shared API behavior:
- Add explicit timeout behavior for network calls.
- Retry only idempotent reads, with bounded backoff.
- Do not retry writes unless the endpoint is explicitly idempotent.
- Map HTTP errors into typed, user-safe messages before they reach components.
- Preserve auth/session-expiry handling in the existing interceptor flow.

## Skill: Frontend Security Checklist

Before submitting any component that handles user data, auth, or financial info:

### XSS Prevention
- [ ] **Never use `innerHTML`** with user-controlled content — use Angular's template binding `{{ }}` instead
- [ ] **Never use `[innerHTML]`** unless content is sanitized via Angular's `DomSanitizer`
- [ ] Never use `bypassSecurityTrustHtml()`, `bypassSecurityTrustUrl()`, or other trust bypass methods without documented justification
- [ ] User-generated content rendered via `{{ variable }}` — Angular auto-escapes this

### Secure Data Handling
```typescript
// Avoid adding new sensitive localStorage values.
// If auth-token storage changes, Prahari must review the XSS/session tradeoff.
```

- [ ] No new sensitive localStorage/sessionStorage values without Prahari review
- [ ] No sensitive data (account numbers, tax IDs) rendered in component state longer than needed
- [ ] Payment card numbers masked: show only last 4 digits

### Content Security Policy (CSP) Headers
These are set by the backend/nginx — Rupa verifies the Angular app does not break under them:
- [ ] No inline `<script>` tags in templates
- [ ] No `javascript:` URLs in `[href]` bindings
- [ ] All external resources (fonts, CDN) must be in the CSP allowlist — flag to Sthira if new ones needed

### CSRF Protection
- [ ] Auth interceptor sends `Authorization: Bearer <token>` header — not cookies
- [ ] Angular `HttpClient` does not use cookies for auth — stateless JWT flow is CSRF-safe by design

### Sensitive Form Fields
```typescript
// Password fields — prevent browser autofill on sensitive forms
<input type="password" autocomplete="current-password" />

// Financial data — never autocomplete account numbers
<input type="text" autocomplete="off" [attr.aria-label]="'Bank account number'" />
```

### Error Messages — Don't Leak Internals
```typescript
// BAD — exposes internal error details to users
this.error.set(err.error.detail);  // Might show "supabase: column X does not exist"

// GOOD — map to user-friendly messages
this.error.set('Something went wrong. Please try again.');
console.error('API error:', err);  // Full details in console for debugging only
```
