# Aethos Design System

**Owner**: Chitra (Frontend Designer)
**Last Updated**: 2026-04-03
**Status**: Living Document

---

## Design Philosophy

Aethos is an AI-agent-native financial ERP. The design philosophy centers on five principles:

1. **Dark theme, always** -- Financial professionals work long hours; dark surfaces reduce eye strain. The slate-900 base with carefully chosen accent colors creates a premium, modern workspace feel.
2. **Information density done right** -- SME finance users need data (numbers, tables, statuses), but it must be scannable. We use visual hierarchy, muted labels, and bold values to guide the eye.
3. **Agent transparency** -- Users always know when AI is acting and can override. Confidence badges, "AI Scored" pills, and HITL review flows make AI actions visible without being intrusive.
4. **Consistency over novelty** -- Every component follows the design system. Glass panels, the `t-*` CSS utility classes, and the `--t-*` CSS variable tokens ensure visual uniformity.
5. **Mobile-aware, desktop-first** -- SME users primarily work on desktop/laptop. The sidebar collapses on mobile with an overlay pattern; content uses responsive grid breakpoints (sm/md/lg/xl).

---

## Color System

### CSS Variable Tokens (Theme-Aware)

All theme tokens are defined as CSS custom properties in `frontend/src/styles.css` and mapped into Tailwind via `frontend/tailwind.config.js`.

#### Light Theme (Default `:root`)

| Token | Value | Usage |
|-------|-------|-------|
| `--t-bg` | `#f8fafc` | Page background (Slate-50) |
| `--t-surface` | `#ffffff` | Primary panel surface (White) |
| `--t-sidebar` | `#f1f5f9` | Sidebar/Sidenav background (Slate-100) |
| `--t-border` | `#e2e8f0` | Primary border color (Slate-200) |
| `--t-text-primary` | `#0f172a` | High-contrast text (Slate-900) |
| `--t-text-secondary`| `#475569` | Secondary content text (Slate-600) |
| `--t-text-muted` | `#94a3b8` | Muted labels/stamps (Slate-400) |

#### Dark Theme (`.dark`)

| Token | Value | Usage |
|-------|-------|-------|
| `--t-bg` | `#030712` | Deep rich background |
| `--t-surface` | `#0f172a` | Primary panel surface (Slate-900) |
| `--t-sidebar` | `#0f172a` | Sidebar background |
| `--t-border` | `#1e293b` | Primary border color (Slate-800) |
| `--t-text-primary` | `#f8fafc` | High-contrast text (Slate-50) |
| `--t-text-secondary`| `#cbd5e1` | Secondary content text (Slate-300) |
| `--t-text-muted` | `#94a3b8` | Muted labels/stamps (Slate-400) |

### Brand Colors (Static, Tailwind Extended)

| Name | Hex | Usage |
|------|-----|-------|
| `brand-dark` | `#0F172A` | Legacy dark bg reference |
| `brand-card` | `#1E293B` | Legacy card bg reference |
| `brand-primary` | `#6366F1` | Indigo-500. Primary action, active states, links |
| `brand-accent` | `#8B5CF6` | Purple-500. Gradients, revenue metrics |
| `brand-success` | `#10B981` | Emerald-500. Positive values, approvals, paid status |

### Semantic Status Colors

| Status | Background Pattern | Text Color |
|--------|-------------------|------------|
| Draft | `bg-slate-500/20` | `text-slate-400` |
| Sent / Awaiting | `bg-yellow-500/20` | `text-yellow-500` |
| Paid / Reconciled | `bg-brand-success/20` | `text-brand-success` |
| Overdue / Void / Error | `bg-red-500/20` | `text-red-400` |
| Processing | `bg-brand-primary/20` | `text-brand-primary` |
| Customer type | `bg-blue-500/20` | `text-blue-400` |
| Vendor type | `bg-purple-500/20` | `text-purple-400` |
| Credit (bank txn) | `bg-blue-500/20` | `text-blue-400` |
| Debit (bank txn) | `bg-purple-500/20` | `text-purple-400` |

### Gradient Patterns

- **Primary CTA**: `linear-gradient(135deg, #6366f1, #8b5cf6)` with `box-shadow: 0 4px 20px rgba(99,102,241,0.4)`
- **User avatar**: `bg-gradient-to-br from-brand-primary to-brand-accent`
- **Toast success**: `linear-gradient(135deg, rgba(16,185,129,0.95), rgba(5,150,105,0.95))`
- **Toast error**: `linear-gradient(135deg, rgba(239,68,68,0.95), rgba(220,38,38,0.95))`
- **Toast warning**: `linear-gradient(135deg, rgba(245,158,11,0.95), rgba(217,119,6,0.95))`
- **Toast info**: `linear-gradient(135deg, rgba(59,130,246,0.95), rgba(37,99,235,0.95))`

---

## Typography Scale

**Font Family**: `Inter` (300/400/500/600/700 weights), loaded via Google Fonts.

Configured in Tailwind as `fontFamily.sans: ['Inter', 'sans-serif']`.

| Element | Class/Size | Weight | Color Token |
|---------|-----------|--------|-------------|
| Page heading | `text-2xl font-bold` (1.5rem) | 700 | `--t-text` |
| Section heading | `text-lg font-semibold` (1.125rem) | 600 | `--t-text` |
| Copilot heading | `text-3xl font-bold` (1.875rem) | 700 | `--t-text` |
| Stat card value | `text-2xl font-bold` (1.5rem) | 700 | Contextual (success/accent/text) |
| Report net total | `text-2xl font-bold` | 700 | Contextual |
| Table header | `text-xs font-semibold uppercase tracking-wider` (0.75rem) | 600 | `--t-text-m` |
| Table cell | `text-sm` (0.875rem) | 400 | `--t-text` or `--t-text-s` |
| Form label | `text-sm font-medium` (0.875rem) | 500 | `--t-text-m` |
| Body text | `text-sm` (0.875rem) | 400 | `--t-text-s` |
| Muted / timestamps | `text-xs` (0.75rem) | 400 | `--t-text-m` |
| Badge / pill | `text-xs font-semibold` (0.75rem) | 600 | Contextual |
| Micro text | `text-[10px]` (0.625rem) | 600-700 | Various |

### Typography Utility Classes

| Class | Definition |
|-------|-----------|
| `.t-heading` | `text-2xl font-bold; color: var(--t-text)` |
| `.t-subtext` | `text-sm; color: var(--t-text-m)` |
| `.t-label` | `text-sm font-medium; color: var(--t-text-m)` |
| `.t-text` | `color: var(--t-text)` |
| `.t-text-s` | `color: var(--t-text-s)` |
| `.t-text-m` | `color: var(--t-text-m)` |

---

## Spacing & Layout System

### Global Layout

The app uses a sidebar + topbar shell defined in `AppComponent`:

- **Sidebar width**: 260px (expanded), 72px (collapsed)
- **Topbar height**: 64px (`h-16`)
- **Content area**: `flex-1` with `p-6 lg:p-8`, `max-w-[1400px]` centered
- **Page transition**: `transition-all duration-300` on margin-left changes

### Spacing Scale (Tailwind defaults)

| Token | Value | Common Usage |
|-------|-------|-------------|
| `gap-1` | 4px | Tab groups, filter pills |
| `gap-2` | 8px | Button groups, inline actions |
| `gap-3` | 12px | Icon + text pairs, nav links |
| `gap-4` | 16px | Grid gaps, form field spacing |
| `gap-6` | 24px | Section spacing, major grid gaps |
| `gap-8` | 32px | Split-screen panels |
| `p-4` | 16px | Table cells, filter bars |
| `p-5` | 20px | Stat cards |
| `p-6` | 24px | Card/panel padding, modal padding |
| `p-8` | 32px | Feature cards, empty states |
| `mb-6` | 24px | Standard section margin |
| `mb-8` | 32px | Dashboard section margin |

### Grid Patterns

| Pattern | Breakpoints | Usage |
|---------|------------|-------|
| 4-column stats | `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` | Dashboard stat cards |
| 6-column shortcuts | `grid-cols-2 sm:grid-cols-3 lg:grid-cols-6` | Dashboard quick actions |
| 3-column layout | `grid-cols-1 lg:grid-cols-3` | Dashboard cash flow + alerts |
| 2-column split | `grid-cols-2` | Bill upload (doc + form), invoice review |
| 3-column form | `grid-cols-3` | Invoice create (form 2/3 + totals 1/3) |
| Agent grid | `grid-cols-1 md:grid-cols-2 xl:grid-cols-3` | Agent dashboard cards |
| Forecast stats | `grid-cols-4` | AI insights stat cards |

### Border Radius Scale

| Usage | Radius |
|-------|--------|
| Buttons (primary) | `rounded-xl` (12px) |
| Cards / panels | `0.875rem` (14px, via `.glass-panel`) |
| Input fields | `rounded-xl` (12px) for `.input-field`, `rounded-lg` (8px) for `.t-input` |
| Badges / pills | `rounded-full` (9999px) or `rounded` (4px) |
| Modals | `rounded-2xl` (16px) |
| Tabs | `rounded-lg` (8px) within `rounded-xl` (12px) container |
| Avatars | `rounded-full` |

---

## Component Inventory

### Core Components (Persistent Shell)

#### `SidebarComponent` (`core/sidebar.component.ts`)
- **Purpose**: Primary navigation with collapsible groups
- **Features**: Mobile overlay with backdrop blur, collapse toggle (72px), grouped nav items with expand/collapse arrows, user profile card at bottom
- **Pattern**: Fixed left sidebar, `z-50`, with `slide-in-left` animation on mobile
- **Icons**: Emoji-based nav icons (not SVG icon library)

#### `TopbarComponent` (`core/topbar.component.ts`)
- **Purpose**: Top navigation bar with search, theme toggle, notifications, profile
- **Features**: Sticky `top-0 z-30`, backdrop blur (`blur(16px)`), period badge, currency selector, notification bell with dot indicator, profile dropdown
- **Pattern**: Frosted glass effect via `--t-topbar` semi-transparent background

#### `ToastComponent` + `ToastService` (`core/toast.component.ts`, `core/toast.service.ts`)
- **Purpose**: Non-blocking notification system
- **Types**: success (emerald gradient), error (red gradient), warning (amber gradient), info (blue gradient)
- **Position**: Fixed bottom-right, column-reverse stacking
- **Animation**: `toast-in` slide from right with scale
- **Behavior**: Auto-dismiss (4-8s by type), click to dismiss

#### `ThemeService` (`core/theme.service.ts`)
- **Purpose**: Light/dark theme toggle with persistence
- **Mechanism**: Toggles `.dark` class on `<html>`, stores preference in `localStorage`
- **Default**: Respects `prefers-color-scheme` system preference

#### `LoadingService` + Global Loader (`core/loading.service.ts`, `app.component.ts`)
- **Purpose**: Full-page loading overlay
- **Pattern**: Fixed overlay with `bg-black/20 backdrop-blur-[2px]`, spinning indigo ring

#### `ConfidenceBadgeComponent` (`core/confidence-badge.component.ts`)
- **Purpose**: Display AI confidence as colored percentage badge
- **Thresholds**: >= 85% green (#22c55e), 70-84% amber (#f59e0b), < 70% red (#ef4444)
- **Pattern**: Pill badge with transparent colored background, `input.required<number>()`

#### `LoadingIndicatorComponent` (`shared/components/loading-indicator/loading-indicator.component.ts`)
- **Purpose**: Material spinner overlay (alternative to global loader)
- **Issue**: Uses `rgba(255, 255, 255, 0.7)` background -- **VIOLATES dark theme rule** (see Consistency Issues)

### Feature Components

#### Dashboard (`features/dashboard.component.ts`)
- 4 stat cards with left-border color coding (profit/receivables/cash/revenue)
- 6 quick action shortcut cards with emoji icons and hover elevation
- Custom bar chart for cash flow (pure CSS/div bars, not a chart library)
- Alert cards with left-border severity (red/yellow/indigo/purple)
- Approval queue table with expandable AI briefing sections

#### Invoice List (`features/invoices/invoice-list.component.ts`)
- Status filter pills (All/Draft/Awaiting/Paid/Overdue)
- Full data table with inline status badges
- Detail modal with line items table and totals summary
- Send modal with email input
- Payment recording modal

#### Invoice Create (`features/invoices/invoice-create.component.ts`)
- 3-column layout: 2/3 form + 1/3 sticky totals panel
- Editable line items table with inline inputs (transparent borders)
- AI auto-fill suggestions button for customer-based line item generation
- Account selector dropdowns per line item

#### Bill Upload (`features/bills/bill-upload.component.ts`)
- Split-screen: left = document preview (iframe), right = extracted form
- Drag-and-drop upload zone with dashed border
- AI extraction loading overlay with blur
- Confidence display and auto-matched contact

#### Invoice Review (`features/bills/invoice-review.component.ts`)
- Split-screen: left = read-only AI extraction, right = editable correction form
- Per-field confidence badges on AI side
- Change tracking with "Modified" pills on edited fields
- Warning banner for AI extraction issues
- Reactive forms with validation

#### Reconciliation Review (`features/banking/reconciliation-review.component.ts`)
- Stats bar: Pending/Resolved/High Confidence counts
- Batch accept for high-confidence matches (>= 90%)
- Per-row actions: Accept Match, Override (choose different invoice), Code GL (choose account)
- Expandable sub-panels for override/manual code selection
- Progress bar footer showing completion percentage
- Error and success banners

#### Bank Reconciliation (`features/banking/bank-rec.component.ts`)
- Bank account selector dropdown
- Auto-reconciliation button with spinner
- CSV import via hidden file input
- Transaction table with type/status badges and suggested match indicators

#### AI Copilot (`features/ai/ai-copilot.component.ts`)
- Tab interface: Chat, Reconciliation, Smart Reminders
- Chat: Bubble UI (user = indigo right-aligned, AI = dark left-aligned), typing indicator with bouncing dots, suggestion chips, glowing input border
- Reconciliation: Auto-match table with confidence badges, confirm buttons
- Reminders: Generated reminder cards with overdue badges

#### Agent Dashboard (`features/admin/agent-dashboard.component.ts`)
- Grid of agent cards with enable/disable toggles
- Autonomy level indicator (4-segment bar: L0-L3)
- HITL classification badges (always/conditional/optional/none)
- Domain filter tabs
- Invoke button with trace modal (glassmorphism style with timeline steps)
- Guardian agent locked indicator

#### Agent HITL Review (`features/admin/agent-hitl-review.component.ts`)
- Bulk select with checkboxes
- Per-item confidence meter (progress bar + percentage)
- Specialized card layouts per agent type (bank rec vs AP invoice vs generic JSON)
- Approve/Reject buttons with status badges after action

#### Agent Activity Log (`features/admin/agent-activity-log.component.ts`)
- Domain filter tabs
- Expandable log entries with system prompt, input context, agent reasoning/tools, final output
- Status badges (Needs Review / Auto-applied)
- Confidence percentage and latency display

#### Agent Corrections (`features/admin/agent-corrections.component.ts`)
- Filter by agent dropdown
- Expandable diff view: original vs corrected output side-by-side
- Custom CSS (not using global `t-*` classes) -- **CONSISTENCY ISSUE**

#### AI Insights (`features/admin/ai-insights.component.ts`)
- Tab interface: Cash Flow Forecast, Anomalies, Messaging
- Forecast: stat cards + daily projected balance table
- Anomalies: severity badges with resolve/false-positive actions
- Messaging: template management table + queue table + create template modal
- Uses non-standard token names (`--t-accent`, `--t-card-bg`, `--t-table-header`) -- **CONSISTENCY ISSUE**

#### Reports (`features/reports/reports.component.ts`)
- Tab navigation with underline style (not pill style)
- Financial statement layouts: P&L, Balance Sheet, Trial Balance, Cash Flow, Aged AR, Aged AP
- Totals with heavy border separators
- CSV export

#### General Ledger (`features/general-ledger/general-ledger.component.ts`)
- Account selector dropdown
- Summary bar with debit/credit/closing balance
- Journal lines table with alternating row backgrounds
- New journal entry modal with balanced debit/credit validation

#### Contacts CRM (`features/contacts/contacts-list.component.ts`)
- Search + type filter (All/Customers/Vendors)
- Avatar initials in indigo circle
- Create/edit modal using `.t-modal-overlay` + `.t-modal` classes

#### Expenses (`features/expenses/expense-list.component.ts`)
- AI upload zone with dashed border
- AI extraction status column (Verified/Review Needed/Processing)
- Upload receipt modal

#### Settings (`features/settings/settings.component.ts`)
- Tab navigation (pill style)
- Organisation settings: grid label/input layout
- Tax rates: table with add form
- Tracking categories: chip-style options with inline add
- Locked periods: table with unlock actions

#### Home / Landing Page (`features/home.component.ts`)
- Public navigation with dropdown menus (hover reveal)
- Hero section with logo, badge, CTA buttons
- Feature grid (3 cards with hover icon transitions)

#### Login (`features/admin/login.component.ts`)
- Centered card layout, max-w-sm
- Logo + form in glass panel
- Gradient submit button with loading spinner

---

## Page Layouts

### Authenticated Shell
```
+------------------+------------------------------------+
|                  |  Topbar (h-16, sticky, blur)       |
|   Sidebar        +------------------------------------+
|   (260px/72px)   |                                    |
|   fixed left     |  Content Area                      |
|   z-50           |  p-6 lg:p-8                        |
|                  |  max-w-[1400px] centered            |
|                  |                                    |
+------------------+------------------------------------+
```

### Standard List Page
```
Header: Title + Subtitle | Action Button (btn-primary)
Filters: Status pills or search + type buttons
Table:  glass-panel with t-table or custom table
        Header row with t-header background
        Hover rows, status badges, action buttons
Empty:  Centered icon + text
```

### Split-Screen Page (Bill Upload, Invoice Review, Reconciliation Review)
```
Header: Back link + Title | Confidence/Stats
+--------------------+--------------------+
| Left Panel         | Right Panel        |
| glass-panel        | glass-panel        |
| Document/ReadOnly  | Editable Form      |
| h-[calc(100vh-Xpx)]                    |
+--------------------+--------------------+
```

### Form Page (Invoice Create)
```
Header: Back link + Title | Draft + Submit buttons
+---------------------------+-----------+
| Form (col-span-2)         | Summary   |
| glass-panel               | glass-panel|
| Customer, dates, line     | sticky    |
| items table               | top-24    |
+---------------------------+-----------+
```

### Dashboard Page
```
Header: Title + Welcome
Stats:  4-column stat cards with left-border indicators
Actions: 6-column shortcut grid
Content: 2/3 chart + 1/3 alerts (3-column grid)
Queue:  Full-width table with expandable rows
```

---

## Agent UI Patterns

### Confidence Display
- **Badge**: `ConfidenceBadgeComponent` -- colored pill (green/amber/red)
- **Meter**: Progress bar with percentage label (used in HITL Review)
- **Inline text**: `(extractedData().confidence * 100).toFixed(0)%` in bill upload

### HITL Review Flow
1. Agent produces output with confidence score
2. Items queue in `/agents/hitl-queue`
3. Review page shows pending items with bulk/single approve/reject
4. Specialized card layouts per agent domain (bank rec shows side-by-side match, AP shows extracted bill data)
5. After action, status badge shows approved/rejected with opacity reduction

### Agent Invocation Trace Modal
- Glassmorphism modal with timeline UI
- Steps appear sequentially with green/orange dot indicators
- Polling for job status with simulated intermediate steps
- "Agent is thinking..." state with spinner

### AI Auto-Fill Pattern
- "Auto-Fill Suggestions" button on invoice create (sparkle emoji)
- Sends prompt to AI, parses JSON response, maps to form fields
- Toast success/error on completion
- Loading state with spinner on button

### Copilot Chat
- Full-height chat panel with message bubbles
- User messages: indigo bg, right-aligned, rounded-tr-none
- AI messages: dark bg with border, left-aligned, rounded-tl-none
- Typing indicator: 3 bouncing dots
- Suggestion chips below input
- Glowing border effect on input focus

### AI Extraction Overlay
- Used during bill upload document processing
- Blur overlay with spinner and status text
- Confidence display after extraction completes

### Agent Dashboard Cards
- Enable/disable toggle per agent
- 4-level autonomy bar (L0 Disabled -> L3 Full Auto)
- Color coding: L0=gray, L1=blue, L2=orange, L3=green
- HITL classification badge with semantic coloring
- Guardian agent has locked "Always On" badge

---

## Form Patterns

### Input Variants

1. **`.input-field`** (standard form inputs):
   - `rounded-xl px-4 py-2.5`
   - Focus: `ring-2 ring-brand-primary/40 border-brand-primary`
   - Used in: Invoice create, modals, login

2. **`.t-input`** (compact variant):
   - `rounded-lg px-3 py-2 text-sm`
   - Focus: `ring-2 ring-brand-primary/30 border-brand-primary`
   - Used in: Settings, contacts, GL, search, reconciliation

3. **Inline table inputs** (transparent):
   - `input-field w-full bg-transparent border-transparent`
   - Used in invoice create line items; border appears only on focus

### Form Layout Patterns
- **Grid label/input**: `grid grid-cols-[140px_1fr]` (settings)
- **Stacked**: `space-y-4` or `space-y-5` (modals)
- **2-column**: `grid grid-cols-2 gap-4` or `gap-6` (date pairs, invoice header)
- **Labels**: `block text-sm font-medium t-text-m mb-1` or `mb-2`

### Validation & Error States
- Required field errors: `text-xs text-red-400 mt-1` below input
- Journal balance error: `text-xs text-red-400` with currency diff display
- Invoice review: `changed-pill` amber badge for modified fields
- Ring highlight on changed fields: `ring-1` with amber ring color

### Select Dropdowns
- Use native `<select>` with `appearance-none` class
- Styled with `input-field` or `t-input` classes
- No custom dropdown component exists

### File Upload
- Dashed border zone: `border-2 border-dashed rounded-xl` with hover to `border-brand-primary/50`
- Hidden `<input type="file">` overlaid with `absolute inset-0 opacity-0`
- Extraction loading overlay with backdrop blur

---

## Data Display Patterns

### Tables

1. **Standard table** (`.t-table`):
   - Full-width, header with uppercase labels, `text-xs font-semibold tracking-wider`
   - Row hover: `var(--t-card-hover)` background
   - Row borders: `var(--t-border-subtle)`
   - Cell padding: `px-4 py-3 text-sm`

2. **Custom inline table** (invoices, banking, GL):
   - Explicit `style="border-bottom: 1px solid var(--t-border)"` on rows
   - Header row with `background: var(--t-header)`
   - Hover via `onmouseenter`/`onmouseleave` inline styles (older pattern)

### Cards

1. **`.glass-panel`**:
   - Background: `var(--t-card)`, border: `var(--t-border)`, `border-radius: 0.875rem`
   - Box shadow with hover elevation
   - Backdrop blur: `blur(12px)`
   - Used everywhere as the primary container

2. **Stat cards**: `.glass-panel` + `.stat-card` with colored left-border (`::before` pseudo-element)

3. **Alert cards**: `.glass-panel` with `border-l-4` and severity color

### Metrics / Numbers
- Currency values: `| currency` pipe, `font-bold` or `font-semibold`
- Positive amounts: `text-brand-success` or contextual color
- Negative amounts: `text-red-400`
- Monospace numbers: `font-mono` class for alignment

### Status Badges
- Standard: `px-2 py-1 rounded text-xs font-semibold capitalize`
- Pill: `px-2.5 py-1 rounded-full text-xs font-semibold`
- Background: `{color}-500/20` with `text-{color}-400` or `text-{color}-500`

### Charts
- **Cash flow bar chart**: Pure CSS bars in flexbox container (`h-44`)
- Bars use `bg-emerald-500/80` (in) and `bg-red-400/80` (out) with hover to full opacity
- No charting library (e.g., Chart.js, D3) is integrated

### Empty States
- `.t-empty`: `p-12 text-center; color: var(--t-text-m)`
- SVG icon (12x12, muted) + descriptive text
- Used in tables and panel bodies

### Progress Indicators
- **Spinner**: `.t-spinner` (border-based, indigo top)
- **Material spinner**: `MatProgressSpinner` in loading indicator component
- **Inline spinner**: SVG circle/path animation pattern (used in buttons)
- **Progress bar**: Colored div inside gray track (reconciliation review footer)

---

## Navigation & Routing

### Sidebar Navigation Groups

| Group | Icon | Expanded Default | Items |
|-------|------|-----------------|-------|
| Sales | Chart | Yes | Invoices, Quotes, Credit Notes, Recurring Invoices, Collections |
| Purchases | Cart | Yes | Expenses, Upload Bill, Purchase Orders, Payment Proposal |
| Accounting | Books | Yes | Banking, General Ledger, Contacts, Products & Services, Fixed Assets, Budget Plans, Budget vs Actual, CAPEX Tracking, Reports |
| AI Agents | Robot | No | AI Copilot, Agent Dashboard, Agent Activity Log, Review Extraction, AI Insights, Agent Corrections |
| Administration | Wrench | No | Chart of Accounts, Tax Rates, Payment Terms, Payment Methods, Fiscal Periods, Organization, Settings, User Management, Roles & Permissions, AP Configuration, GL Configuration, Asset Management, Cost Accounting, Approval Workflows, Audit Log |
| Settings | Gear | No | Tax Rates, Tracking |

### Active Link Style
- Background: `var(--t-sidebar-active)` = `rgba(99, 102, 241, 0.1)` (light) / `rgba(99, 102, 241, 0.15)` (dark)
- Text: `#a5b4fc` (indigo-300)

### Public Routes
- `/` -- Home/landing page (no sidebar/topbar)
- `/login` -- Login page (no sidebar/topbar)
- `/signup` -- Tenant signup (no sidebar/topbar)
- `/about` -- About page (no sidebar/topbar)

### Route Guards
- `AuthGuard` on authenticated routes
- Topbar period badge shows `Q1 2026`

---

## Dark Theme Implementation Details

### Toggle Mechanism
- `ThemeService` uses Angular `signal<Theme>()` with `effect()` to reactively toggle `.dark` class on `document.documentElement`
- Persisted to `localStorage` key `sme-finance-os-theme`
- Falls back to `prefers-color-scheme: dark` media query
- Tailwind `darkMode: 'class'` configuration

### CSS Variable Architecture
- All theme-sensitive values defined as CSS custom properties in `:root` and `.dark` selectors
- Tailwind config maps `t-*` color names to `var(--t-*)` for use in utility classes
- Components use a mix of:
  1. Tailwind utilities: `t-text`, `t-text-m`, `bg-brand-primary`
  2. Inline `style` attributes: `style="color: var(--t-text);"` or `style="background: var(--t-card);"`
  3. CSS utility classes: `.t-heading`, `.t-label`, `.t-input`

### Transition
- Body: `transition: background-color 0.3s ease, color 0.3s ease`
- `.glass-panel`: `transition: background-color 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease`

### Scrollbar
- Custom webkit scrollbar: 6px width, transparent track, `var(--t-text-m)` thumb with rounded corners

### Angular Material MDC Text Rendering
- Modern Angular Material components (`<mat-select>`, `<mat-form-field>`) hardcode text values to `rgba(0,0,0,0.87)` internally using MDC web tokens.
- **Do not** attempt to override them with Tailwind classes inline.
- Standard overrides for `.mdc-list-item__primary-text` and `.mdc-floating-label` are maintained centrally in `styles.scss` bound to `--t-text-primary`. All new forms automatically inherit this.

---

## Accessibility Status

### Current State: PARTIAL

#### Implemented
- Keyboard navigation for sidebar links via standard `<a>` and `<button>` elements
- Focus ring on inputs via `focus:ring-2 focus:ring-brand-primary/40`
- `title` attributes on collapsed sidebar items for tooltip context
- `alt` text on logo images
- Semantic `<header>`, `<main>`, `<nav>`, `<aside>` elements
- Native form controls (`<input>`, `<select>`, `<button>`)
- Toast notifications are dismissible by click

#### Missing / Needs Improvement
- **ARIA labels**: No `aria-label` on icon-only buttons (theme toggle, notification bell, hamburger, close buttons)
- **ARIA roles**: No `role="dialog"` or `aria-modal="true"` on custom modals
- **ARIA live regions**: No `aria-live` on toast container or dynamic content updates
- **Focus trapping**: Custom modals do not trap focus; Tab can escape to background content
- **Skip to content**: No skip link for keyboard users to bypass sidebar
- **Color contrast**: Some muted text (`--t-text-m: #9ca3af` on `--t-bg: #030712`) may not meet WCAG AA 4.5:1 ratio for small text (calculated ~5.2:1 -- borderline pass)
- **Status badge colors**: Some color-only status indicators lack text alternatives for colorblind users (partially mitigated by text labels)
- **Form error association**: No `aria-describedby` linking error messages to inputs
- **Table semantics**: Some tables use `@for` with `<tr>` but lack `<caption>` or `aria-label`
- **Agent activity log**: Expandable rows lack `aria-expanded` attributes
- **Keyboard operability**: Custom toggle switches (agent dashboard) are not keyboard accessible

---

## Consistency Issues Found

### 1. Token Naming Drift in Agent Components
**Severity**: Medium
**Location**: `agent-dashboard.component.ts`, `agent-hitl-review.component.ts`, `agent-activity-log.component.ts`, `ai-insights.component.ts`, `agent-corrections.component.ts`

These components use non-standard CSS variable names that do not exist in the global `styles.css`:
- `--t-muted` (should be `--t-text-m`)
- `--t-brand` (should use Tailwind `brand-primary` or `--t-text` context)
- `--t-brand-rgb` (not defined)
- `--t-card-border` (should be `--t-border`)
- `--t-card-bg` (should be `--t-card`)
- `--t-table-header` (should be `--t-header`)
- `--t-input-bg` (should be `--t-input`)
- `--t-text-muted` (should be `--t-text-m`)
- `--t-accent` (should be `brand-primary` or a defined token)
- `--t-row-hover` (not defined)
- `--t-row-active` (not defined)
- `--t-code-text` (not defined)
- `--t-diff-bg` (not defined)

**Impact**: These components silently fall back to the hardcoded fallback values in their CSS, which means they do not respond to the light/dark theme toggle properly.

### 2. Light Background in HITL Review and Agent Dashboard Trace Modal
**Severity**: High
**Location**: `agent-hitl-review.component.ts` (lines 120-162), `agent-dashboard.component.ts` (trace modal)

The bank reconciliation card, AP invoice card, and trace modal use hardcoded light backgrounds:
- `bg-gray-50/50`, `bg-blue-50/30`, `bg-purple-50/30`
- `text-gray-900`, `text-gray-700`, `text-gray-500`
- Trace modal: `background: rgba(255, 255, 255, 0.7)` with `text-gray-900`

These **violate the dark theme rule** and will appear as jarring white patches in dark mode.

### 3. LoadingIndicatorComponent White Background
**Severity**: Medium
**Location**: `shared/components/loading-indicator/loading-indicator.component.ts`

Uses `background-color: rgba(255, 255, 255, 0.7)` -- this should use `var(--t-modal-overlay)` or a semi-transparent dark background.

### 4. Inline Style vs CSS Class Inconsistency
**Severity**: Low
**Location**: Throughout codebase

Two patterns coexist for applying theme colors:
- **Newer pattern**: `style="color: var(--t-text);"` (inline, verbose)
- **Older pattern**: `class="t-text"` (CSS class, cleaner)

Some components mix both approaches on the same page. The `t-text`, `t-text-s`, `t-text-m` CSS classes exist specifically for this but are used inconsistently.

### 5. Table Hover Implementation Split
**Severity**: Low
**Location**: Invoice list, dashboard approval queue vs. contacts, banking

Two hover patterns:
- `onmouseenter="this.style.background='var(--t-card-hover)'"` (inline JS events)
- `class="hover:bg-white/5"` (Tailwind utility)

The `hover:bg-white/5` only works correctly in dark mode. Should use the `t-table` hover pattern or `var(--t-card-hover)` consistently.

### 6. Input Field Variant Inconsistency
**Severity**: Low
**Location**: Various forms

Two input classes with different padding/radius:
- `.input-field`: `rounded-xl px-4 py-2.5` (larger)
- `.t-input`: `rounded-lg px-3 py-2 text-sm` (compact)

Some components (invoice-review, reconciliation-review) redefine `.t-input` in component styles, overriding the global definition with different border-radius (6px vs 8px).

### 7. Duplicated Settings Navigation
**Severity**: Low
**Location**: Sidebar navigation

"Tax Rates" appears in both the "Administration" group and the "Settings" group. "Settings" link `/settings` is in Administration, but there's also a separate Settings group with `/settings/tax-rates` and `/settings/tracking`.

### 8. Report Tab Style Differs from Rest
**Severity**: Low
**Location**: `reports.component.ts`

Reports uses underline-style tabs (`border-b-2 border-brand-primary`) while all other tabbed interfaces use the pill/button style (`bg-brand-primary text-white rounded-lg`). This breaks navigation pattern consistency.

---

## Design Improvement Recommendations

### Priority 1: Critical Fixes

1. **Standardize CSS variable names in agent components**
   Add missing tokens to `styles.css` or migrate agent components to use existing tokens. This is the single biggest source of visual inconsistency and broken theme switching.

2. **Fix light backgrounds in HITL review cards and trace modal**
   Replace all hardcoded `bg-gray-50`, `text-gray-900`, `rgba(255,255,255,0.7)` with theme-aware alternatives using `var(--t-*)` tokens.

3. **Fix LoadingIndicatorComponent overlay**
   Change from `rgba(255,255,255,0.7)` to `var(--t-modal-overlay)` with `backdrop-blur`.

### Priority 2: Consistency Improvements

4. **Establish a single input component or strict class rule**
   Standardize on `.t-input` for all compact form contexts and `.input-field` for standalone/modal forms. Remove component-level `.t-input` overrides. Document when to use each.

5. **Unify table hover pattern**
   Replace all `onmouseenter`/`onmouseleave` inline handlers with the `.t-table` hover pattern or a consistent Tailwind utility using `var(--t-card-hover)`.

6. **Standardize tab navigation**
   Choose one tab pattern (pill or underline) and apply it everywhere. The pill style (`.t-tabs` / `.t-tab`) is already defined in the global CSS; use it consistently.

7. **Deduplicate sidebar navigation**
   Remove duplicate "Tax Rates" entry and consolidate the Settings group items into the Administration group, or create a clear separation of user-facing settings vs admin configuration.

### Priority 3: Accessibility

8. **Add ARIA labels to all icon-only buttons**
   Theme toggle, notification bell, hamburger menu, close buttons, and sidebar collapse toggle all need `aria-label` attributes.

9. **Implement focus trapping in modals**
   Use Angular CDK `FocusTrap` or a custom directive to trap focus within modal dialogs when open.

10. **Add `role="dialog"` and `aria-modal="true"`** to all overlay modals (currently 10+ modal patterns across the app).

11. **Add skip navigation link**
    Add a visually-hidden "Skip to main content" link at the top of the DOM for keyboard users.

12. **Add `aria-live="polite"`** to the toast container for screen reader announcements.

### Priority 4: Component Library Growth

13. **Create a shared `StatusBadgeComponent`**
    The status badge pattern (colored bg + text) is repeated in nearly every feature. A shared component with `@Input() status` and `@Input() variant` would reduce duplication.

14. **Create a shared `PageHeaderComponent`**
    The page header pattern (title + subtitle + action buttons, sometimes with back link) is identical across all features. Extract it.

15. **Create a shared `EmptyStateComponent`**
    Empty states follow the same pattern (icon + title + description) but are duplicated everywhere.

16. **Create a shared `DataTableComponent`**
    While table structures vary, the header/row/hover/border patterns are repeated. A configurable data table component would reduce boilerplate.

17. **Introduce a proper charting library**
    The dashboard cash flow chart is pure CSS divs. As the product matures, integrate a library like ngx-charts or Chart.js for proper data visualization with tooltips, axis labels, and responsiveness.

---

*This document is the authoritative design reference for the Aethos frontend. All new components must follow the patterns and tokens described here. When in doubt, use the CSS variable tokens from `styles.css` and the utility classes defined in the `@layer components` block.*
