# Aethos Frontend Codebase Review

> **Owner**: Rupa (UI Engineer)
> **Last Updated**: 2026-04-03
> **Status**: Living Document

---

## Table of Contents
1. [Frontend Architecture Summary](#frontend-architecture-summary)
2. [Component Inventory](#component-inventory)
3. [Routing Structure](#routing-structure)
4. [State Management Assessment](#state-management-assessment)
5. [Design System Compliance](#design-system-compliance)
6. [Accessibility Audit](#accessibility-audit)
7. [Performance Assessment](#performance-assessment)
8. [Code Quality & Consistency](#code-quality--consistency)
9. [Technical Debt & Known Issues](#technical-debt--known-issues)
10. [Improvement Recommendations](#improvement-recommendations)

---

## Frontend Architecture Summary

The frontend is an **Angular 18** standalone-component application using **Tailwind CSS** with a CSS-variable-based theme system. Components are **inline-template** (template strings in `.ts` files), not separate `.html` files. There are no NgModules — all components are standalone.

### Architecture Layers
```
┌─ App Shell ──────────────────────────────────────────────────┐
│  app.component.ts (sidebar + topbar + router-outlet)         │
├─ Core Layer (13 files) ──────────────────────────────────────┤
│  api.service.ts (937 LoC monolith), auth, theme, toast,      │
│  sidebar, topbar, 3 interceptors, 1 store, 10 services       │
├─ Features Layer (53 components in 17 directories) ───────────┤
│  All standalone, inline-template, lazy-loaded                 │
├─ Shared Layer (1 component) ─────────────────────────────────┤
│  loading-indicator only                                       │
├─ Design System (styles.css, 288 LoC) ────────────────────────┤
│  CSS variables, Tailwind components, glass-panel, buttons     │
└──────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Angular 18** with standalone components
- **Tailwind CSS** with custom `t-*` semantic color tokens via CSS variables
- **Inter** font (Google Fonts)
- **No UI library** — all components are custom-built (no Angular Material in use)
- **No NgRx Signal Store** used — despite being in the tech stack spec
- **3 interceptors**: auth (JWT token injection), loading (global loader), http-error (error handling)
- **1 auth guard** protecting all app routes

---

## Component Inventory

### Feature Components (53 files across 17 directories + 3 standalone)

| Area | Components | Key Files |
|------|-----------|-----------|
| **Admin** (22) | Users, roles, audit log, AP settings, workflows, payment proposal, GL settings, asset mgmt, cost accounting, AI insights, agent dashboard/HITL/activity/corrections, CoA, tax rates, payment terms/methods, fiscal periods, org settings, login, signup | Largest feature area |
| **Invoices** (2) | `invoice-list`, `invoice-create` | Core AR |
| **Banking** (3) | `bank-rec`, `reconciliation-review`, `cash-coding` | Bank reconciliation |
| **Bills** (3) | `bill-upload`, `bill-create`, `invoice-review` | AP processing |
| **Budgets** (3) | `budget-plans`, `budget-vs-actual`, `capex-tracking` | Financial planning |
| **Collections** (2) | `collections`, `recurring-invoices` | AR follow-up |
| **General Ledger** (2) | `general-ledger`, `period-close` | GL operations |
| **AI** (1) | `ai-copilot` | Natural language interface |
| **Reports** (1) | `reports` | Financial reporting |
| **Settings** (3) | `settings`, `user-settings`, `tax-rates`, `tracking` | Configuration |
| **Others** (8) | `quotes`, `credit-notes`, `contacts`, `expenses`, `purchase-orders`, `items`, `fixed-assets` | 1 component each |
| **Standalone** (3) | `dashboard` (18KB), `home` (13KB), `about` (14KB) | Top-level pages |

### Core Services (10 specialized + 1 monolith)

| Service | Size | Purpose |
|---------|------|---------|
| `api.service.ts` | **937 LoC** | Monolith API client — handles ALL endpoints |
| `auth.service.ts` | — | Authentication logic |
| `base-api.service.ts` | — | Base HTTP patterns |
| `invoice-api.service.ts` | — | Invoice-specific API |
| `banking-api.service.ts` | — | Banking-specific API |
| `budget.service.ts` | — | Budget-specific API |
| `accounting-api.service.ts` | — | GL/accounting API |
| `contact-api.service.ts` | — | Contact-specific API |
| `payment-api.service.ts` | — | Payment-specific API |
| `account.service.ts` | — | Account/CoA API |
| `invoice.service.ts` | — | Invoice domain logic |

> ⚠️ **Concern**: `api.service.ts` (937 lines) is a god-object. It handles everything — invoices, payments, contacts, agents, banking, budgets, reports, etc. Some domains have been split into dedicated services, but inconsistently.

### Shared Components (1 only)
- `loading-indicator.component.ts`

> ⚠️ **Major gap**: Only 1 shared component. Common patterns like data tables, form fields, status badges, empty states, and confirmation dialogs are duplicated across feature components.

---

## Routing Structure

**50 routes** total (4 public + 46 protected).

- ✅ **All feature routes use lazy loading** (`loadComponent` with dynamic `import()`)
- ⚠️ **Exception**: `DashboardComponent` is eagerly loaded (imported directly)
- ✅ **Auth guard** on all protected routes via `canActivate: [authGuard]`
- ✅ Routes are well-organized by domain with clear comments

### Public Routes
| Path | Component |
|------|-----------|
| `/` | `HomeComponent` (lazy) |
| `/login` | `LoginComponent` (lazy) |
| `/signup` | `TenantSignupComponent` (lazy) |
| `/about` | `AboutComponent` (lazy) |

### Protected Route Count by Area
| Area | Routes |
|------|--------|
| Sales (invoices, quotes, credit-notes, contacts) | 5 |
| Purchases (POs, bills, expenses) | 6 |
| Banking & GL | 6 |
| Admin & RBAC | 15 |
| Budgets | 3 |
| AI & Settings | 5 |
| Collections & Recurring | 2 |
| Master Data | 6 |

---

## State Management Assessment

### Current State
- **No centralized state management** — Despite NgRx Signals being in the tech stack
- `auth.store.ts` exists but is the only store file
- Most components manage their own state inline with component-level variables
- `ApiService` uses `BehaviorSubject` for `currentUser$` — acts as a pseudo-store
- HTTP data is fetched directly in components, not cached

### Impact
- No shared state cache → duplicate API calls when navigating between views
- No optimistic updates → user sees loading spinners on every navigation
- No undo/redo capability
- Difficult to implement real-time updates or cross-component communication

---

## Design System Compliance

### ✅ Well-Implemented
1. **CSS variable system** — Comprehensive `--t-*` tokens for all semantic colors (28 tokens)
2. **Light + Dark themes** — Both fully defined in `styles.css` with `.dark` class toggle
3. **Component classes** — `glass-panel`, `btn-primary`, `btn-secondary`, `input-field`, `t-table`, `t-tabs`, `t-modal`, `t-badge` — all theme-aware
4. **Tailwind integration** — Custom `t-*` colors mapped to CSS variables in `tailwind.config.js`
5. **Typography** — Inter font with correct weight range
6. **Custom scrollbar** — Theme-aware, subtle styling

### ⚠️ Issues Found
1. **Dark theme not set as default** — `:root` defines light theme; the `GEMINI.md` spec says "dark theme only" but both themes exist (which is actually better for users)
2. **Hardcoded colors in components** — Some inline templates may use raw Tailwind colors (e.g., `bg-slate-800`) instead of `t-*` tokens
3. **No Angular Material** — The tech stack specifies Angular Material, but it's not in use. All UI components are custom-built with Tailwind.
4. **Dashboard (18KB)** — Large inline template with potential hardcoded styles

---

## Accessibility Audit

### ⚠️ Likely Gaps (based on architecture patterns)
1. **No ARIA patterns visible** in `app.component.ts` shell
2. **Sidebar navigation** — No `role="navigation"` or `aria-label` observed
3. **Modal pattern** — `t-modal-overlay` exists but no focus trap or `role="dialog"` in the CSS
4. **No keyboard navigation system** — No skip-to-content link, no focus management on route changes
5. **Color contrast** — Light theme text (`#475569` on `#f4f6f8`) may not meet WCAG AA for small text

> **Recommendation**: Full accessibility audit with component-level ARIA review needed

---

## Performance Assessment

### ✅ Good Practices
1. **Lazy loading** — All 46 protected routes use `loadComponent()` dynamic imports
2. **Zone coalescing** — `provideZoneChangeDetection({ eventCoalescing: true })` enabled
3. **Inline templates** — No separate HTML files to load (trade-off: no template caching)
4. **CSS variable theming** — Efficient runtime theme switching

### ⚠️ Concerns
1. **`api.service.ts` (937 LoC)** — This monolith is loaded eagerly in `app.component.ts`. All 937 lines of API configurations load on first page view regardless of which feature is used.
2. **No `OnPush` change detection** — Component templates likely use default change detection, which is heavier
3. **Dashboard eagerly loaded** — Only route not lazy-loaded; its 18KB template loads at app startup
4. **No service workers** — No PWA/offline capability
5. **No image optimization** — No lazy-loading images or next-gen format handling

---

## Code Quality & Consistency

### ✅ Strengths
1. **Consistent standalone pattern** — All components use `standalone: true`
2. **Inline templates** — Consistent across the entire app
3. **Functional interceptors** — Modern Angular functional style (not class-based)
4. **Clean app shell** — `app.component.ts` is well-organized with clear responsibilities
5. **Theme service** — Centralized theme toggling with `ThemeService`

### ⚠️ Weaknesses
1. **Zero test files** — `find src/app -name "*.spec.ts" | wc -l` returns **0**. No unit tests exist.
2. **God-object API service** — 937-line `api.service.ts` handles all domains
3. **Inconsistent service splitting** — Some domains have dedicated API services (`banking-api`, `invoice-api`), others rely on the monolith
4. **Minimal shared components** — Only 1 shared component; heavy code duplication likely
5. **`window` access in components** — `app.component.ts` directly accesses `window.innerWidth` and `window.location.pathname` — breaks SSR compatibility
6. **Type `any` usage** — `NavigationEnd` subscriber uses `(event: any)` cast in `app.component.ts:69`

---

## Technical Debt & Known Issues

### 🔴 Critical
1. **Zero test coverage** — No `.spec.ts` files anywhere in the frontend. This means zero Jasmine/Karma tests exist.
2. **`api.service.ts` (937 LoC)** — Unmaintainable monolith that will only grow.

### 🟡 Important
3. **No NgRx Signal Store** — Despite being specified in the tech stack, no signal-based state management is implemented.
4. **No Angular Material** — Specified in tech stack but not used; all components are custom Tailwind.
5. **Missing shared component library** — Tables, forms, badges, confirmation dialogs are likely duplicated.
6. **Dashboard eagerly loaded** — Should use `loadComponent()` like all other routes.

### 🟢 Minor
7. **`window` direct access** — Should use Angular's `DOCUMENT` token or a platform-agnostic approach.
8. **Hardcoded sidebar widths** — `260px` and `72px` in `app.component.ts` should use CSS variables.
9. **No environment files** — API base URL likely hardcoded or derived from `window.location`.

---

## Improvement Recommendations

### Priority 1 — Testing (Critical)
1. **Add Jasmine/Karma tests** — Start with core services (`api.service.ts`, `auth.service.ts`)
2. **Add component tests** for high-value features (invoice-create, bill-upload, dashboard)
3. **Playwright is the E2E framework** — config at `erpcore/frontend/playwright.config.ts`. Target critical user flows (login → dashboard → create invoice)

### Priority 2 — Architecture
4. **Split `api.service.ts`** — Extract domain-specific methods into `*-api.service.ts` files (some already exist, complete the migration)
5. **Implement NgRx Signal Store** — Start with `auth.store.ts`, then add stores for invoices, contacts, dashboard data
6. **Build shared component library** — Extract common patterns: data table, form field, status badge, empty state, confirm dialog

### Priority 3 — Quality
7. **Lazy-load dashboard** — Change from eager import to `loadComponent()`
8. **Add `OnPush` change detection** — Component-by-component migration
9. **Eliminate `any` types** — Add proper TypeScript interfaces for all API responses
10. **Add accessibility** — ARIA labels, focus management, skip-to-content, keyboard navigation

### Priority 4 — Consistency
11. **Audit hardcoded colors** — Find and replace raw Tailwind colors with `t-*` tokens
12. **Platform-agnostic patterns** — Replace `window` access with Angular tokens
13. **Document component API** — Add JSDoc comments to shared services and components

---

## Changelog

### [2026-04-03] - Initial comprehensive review
- Audited full frontend: 53 feature components, 10 core services, 50 routes, 288-line design system
- **Critical finding: ZERO test files** — no .spec.ts files exist in the entire frontend
- Found `api.service.ts` (937 LoC) god-object serving all domains
- Confirmed good patterns: standalone components, lazy loading, CSS variable theming, functional interceptors
- Identified: no NgRx state management, no Angular Material, no shared component library
- Documented 13 improvement recommendations across 4 priority tiers
